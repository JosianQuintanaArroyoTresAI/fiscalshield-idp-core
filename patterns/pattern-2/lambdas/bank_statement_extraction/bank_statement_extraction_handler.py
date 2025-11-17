# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Bank Statement Extraction Lambda
Processes bank statement sections and writes individual transaction records to DynamoDB

Features:
- Page-based chunking (optimal for bank statements)
- Stateful processing with resume capability (handles 100+ page statements)
- Multiple statement detection (detects new account headers in same PDF)
- Per-transaction account info (handles statement changes mid-document)
- Robust error handling with DLQ integration
"""

import json
import boto3
import re
import os
import time
import uuid
import random
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Any, Optional
import logging
from botocore.exceptions import ClientError, ParamValidationError, ReadTimeoutError

# Set up logger
logger = logging.getLogger(__name__)


# ==============================================================================
# BankStatementChunker Class - Page-Based Chunking
# ==============================================================================

class BankStatementChunker:
    """
    Handles page-based chunking for bank statements.
    
    Unlike invoices (which use semantic chunking), bank statements benefit from
    page-based chunking because:
    - Transactions never span pages
    - OCR provides clear [PAGE:X] markers
    - No duplication risk
    - Simple and reliable
    """
    
    def __init__(self):
        self.min_page_size = 100  # Minimum chars for valid page
    
    def extract_page_numbers(self, text: str) -> List[int]:
        """Extract all page numbers from [PAGE:X] markers"""
        page_pattern = r'\[PAGE:(\d+)\]'
        matches = re.findall(page_pattern, text)
        pages = sorted(set(int(page_num) for page_num in matches))
        return pages if pages else [1]
    
    def create_page_based_chunks(self, text: str) -> List[Dict[str, Any]]:
        """
        Create chunks based on page breaks - optimal for bank statements.
        
        Returns:
            List of chunk dicts with 'text', 'chunk_index', 'pages', 'chunking_strategy'
        """
        
        # Extract page markers
        page_pattern = r'\[PAGE:(\d+)\](.*?)(?=\[PAGE:\d+\]|$)'
        matches = re.findall(page_pattern, text, re.DOTALL)
        
        if not matches:
            # Fallback: treat as single page
            log_with_timestamp("⚠️ No page markers found - treating as single page")
            return [{
                'text': text,
                'chunk_index': 0,
                'pages': [1],
                'chunking_strategy': 'single_page',
                'size': len(text)
            }]
        
        chunks = []
        for idx, (page_num, page_text) in enumerate(matches):
            page_text_clean = page_text.strip()
            
            # Skip empty or tiny pages
            if len(page_text_clean) < self.min_page_size:
                log_with_timestamp(
                    f"⚠️ Skipping page {page_num} - too small ({len(page_text_clean)} chars)"
                )
                continue
            
            chunks.append({
                'text': page_text_clean,
                'chunk_index': idx,
                'pages': [int(page_num)],
                'chunking_strategy': 'page_based',
                'size': len(page_text_clean)
            })
        
        if chunks:
            avg_size = sum(c['size'] for c in chunks) // len(chunks)
            log_with_timestamp(
                f"✅ Created {len(chunks)} page-based chunks "
                f"(avg size: {avg_size} chars, ~{avg_size//4} tokens)"
            )
        
        return chunks


# ==============================================================================
# Environment variables
# ==============================================================================

LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
EXTRACTION_RESULTS_TABLE = os.environ.get('EXTRACTION_RESULTS_TABLE')
CONFIGURATION_TABLE = os.environ.get('CONFIGURATION_TABLE')
TRACKING_TABLE = os.environ.get('TRACKING_TABLE')
BEDROCK_MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'eu.anthropic.claude-3-7-sonnet-20250219-v1:0')
AWS_REGION = os.environ.get('AWS_REGION', 'eu-central-1')
BEDROCK_INFERENCE_PROFILE_ARN = os.environ.get('BEDROCK_INFERENCE_PROFILE_ARN', '').strip()
FALLBACK_BEDROCK_MODEL_ID = os.environ.get('FALLBACK_BEDROCK_MODEL_ID', '').strip()
FALLBACK_BEDROCK_INFERENCE_PROFILE_ARN = os.environ.get('FALLBACK_BEDROCK_INFERENCE_PROFILE_ARN', '').strip()
BEDROCK_MAX_RETRIES = int(os.environ.get('BEDROCK_MAX_RETRIES', '6'))
BEDROCK_BACKOFF_BASE_SECONDS = float(os.environ.get('BEDROCK_BACKOFF_BASE_SECONDS', '2.0'))
BEDROCK_BACKOFF_MAX_SECONDS = float(os.environ.get('BEDROCK_BACKOFF_MAX_SECONDS', '45.0'))
BEDROCK_FALLBACK_AFTER_ATTEMPT = int(os.environ.get('BEDROCK_FALLBACK_AFTER_ATTEMPT', '3'))

# Timeout management
LAMBDA_TIMEOUT_BUFFER_SECONDS = int(os.environ.get('LAMBDA_TIMEOUT_BUFFER_SECONDS', '120'))  # Reserve 2 minutes


def _parse_csv(value: str) -> List[str]:
    """Parse a comma-separated string into a list, trimming whitespace."""
    if not value:
        return []
    return [part.strip() for part in value.split(',') if part is not None]


def _build_model_chain() -> List[Dict[str, str]]:
    """Build an ordered list of Bedrock models with optional inference profiles."""
    chain: List[Dict[str, str]] = []

    primary_model_id = (BEDROCK_MODEL_ID or '').strip()
    if primary_model_id:
        chain.append({
            'model_id': primary_model_id,
            'inference_profile_arn': BEDROCK_INFERENCE_PROFILE_ARN
        })

    fallback_model_ids = [model_id for model_id in _parse_csv(FALLBACK_BEDROCK_MODEL_ID) if model_id]
    fallback_profile_arns = _parse_csv(FALLBACK_BEDROCK_INFERENCE_PROFILE_ARN)

    for index, fallback_model_id in enumerate(fallback_model_ids):
        profile_arn = fallback_profile_arns[index] if index < len(fallback_profile_arns) else ''
        chain.append({
            'model_id': fallback_model_id,
            'inference_profile_arn': profile_arn
        })

    return chain


BEDROCK_MODEL_CHAIN = _build_model_chain()
if not BEDROCK_MODEL_CHAIN:
    raise ValueError("At least one Bedrock model must be configured via BEDROCK_MODEL_ID")

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
bedrock_runtime = boto3.client('bedrock-runtime', region_name=AWS_REGION)
extraction_table = dynamodb.Table(EXTRACTION_RESULTS_TABLE) if EXTRACTION_RESULTS_TABLE else None
config_table = dynamodb.Table(CONFIGURATION_TABLE) if CONFIGURATION_TABLE else None
tracking_table = dynamodb.Table(TRACKING_TABLE) if TRACKING_TABLE else None

THROTTLING_ERROR_CODES = {"ThrottlingException", "TooManyRequestsException"}


def log_with_timestamp(message: str):
    """Helper function to log messages with timestamps"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    print(f"[{timestamp}] {message}")


# ==============================================================================
# Progress Tracking Functions
# ==============================================================================

def update_chunk_progress(
    document_id: str,
    section_id: str,
    chunks_completed: int,
    total_chunks: int,
    status: str,
    last_account_info: Optional[Dict] = None,
    error: Optional[str] = None
):
    """Save chunk processing progress for resume capability"""
    
    if not tracking_table:
        log_with_timestamp("⚠️ TRACKING_TABLE not configured - progress tracking disabled")
        return
    
    try:
        item = {
            'PK': f"progress#{document_id}#section#{section_id}",
            'SK': 'bank_statement_extraction',
            'DocumentId': document_id,
            'SectionId': section_id,
            'ChunksCompleted': chunks_completed,
            'TotalChunks': total_chunks,
            'Status': status,
            'Progress': f"{chunks_completed}/{total_chunks}",
            'ProgressPercent': Decimal(str((chunks_completed / total_chunks * 100) if total_chunks > 0 else 0)),
            'LastAccountInfo': last_account_info or {},
            'UpdatedAt': int(time.time()),
            'TTL': int(time.time()) + (24 * 60 * 60)  # 24 hours
        }
        
        if error:
            item['Error'] = error
        
        tracking_table.put_item(Item=item)
        
        log_with_timestamp(
            f"📊 Progress saved: {chunks_completed}/{total_chunks} chunks "
            f"({status})"
        )
        
    except Exception as e:
        log_with_timestamp(f"⚠️ Failed to save progress: {str(e)}")


def get_chunk_progress(document_id: str, section_id: str) -> Optional[Dict]:
    """Retrieve saved progress for resume capability"""
    
    if not tracking_table:
        return None
    
    try:
        response = tracking_table.get_item(
            Key={
                'PK': f"progress#{document_id}#section#{section_id}",
                'SK': 'bank_statement_extraction'
            }
        )
        
        if 'Item' in response:
            log_with_timestamp(f"📥 Retrieved progress: {response['Item'].get('Progress')}")
            return response['Item']
        
    except Exception as e:
        log_with_timestamp(f"⚠️ Failed to retrieve progress: {str(e)}")
    
    return None


# ==============================================================================
# Bedrock Invocation with Retry Logic
# ==============================================================================

def invoke_bedrock_with_retry(prompt: str, model_used_tracker: List[str]) -> str:
    """
    Invoke Bedrock with sophisticated retry logic and model fallback.
    
    Returns:
        XML response from Bedrock
    
    Raises:
        Exception if all models and retries exhausted
    """
    
    for model_config in BEDROCK_MODEL_CHAIN:
        model_id = model_config['model_id']
        inference_profile_arn = model_config['inference_profile_arn']
        
        log_with_timestamp(f"🤖 Attempting extraction with model: {model_id}")
        
        for attempt in range(1, BEDROCK_MAX_RETRIES + 1):
            try:
                # Prepare request body
                body = json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 4000,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                })
                
                # Use inference profile if provided, otherwise use model ID
                model_param = inference_profile_arn if inference_profile_arn else model_id
                
                # Invoke Bedrock
                response = bedrock_runtime.invoke_model(
                    body=body,
                    modelId=model_param,
                    accept='application/json',
                    contentType='application/json'
                )
                
                response_body = json.loads(response.get('body').read())
                xml_result = response_body['content'][0]['text']
                
                model_used_tracker.append(model_id)
                log_with_timestamp(f"✅ Bedrock invocation successful (attempt {attempt})")
                
                return xml_result
                
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', '')
                
                if error_code in THROTTLING_ERROR_CODES:
                    # Calculate backoff with jitter
                    backoff = min(
                        BEDROCK_BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)) + random.uniform(0, 1),
                        BEDROCK_BACKOFF_MAX_SECONDS
                    )
                    
                    log_with_timestamp(
                        f"⚠️ Throttled (attempt {attempt}/{BEDROCK_MAX_RETRIES}). "
                        f"Retrying in {backoff:.1f}s..."
                    )
                    
                    time.sleep(backoff)
                    continue
                else:
                    # Non-throttling error
                    log_with_timestamp(f"❌ Bedrock error: {error_code} - {str(e)}")
                    raise
            
            except Exception as e:
                log_with_timestamp(f"❌ Unexpected error invoking Bedrock: {str(e)}")
                raise
        
        # Max retries exhausted for this model
        log_with_timestamp(f"⚠️ Max retries exhausted for model {model_id}")
    
    # All models exhausted
    raise Exception("All Bedrock models and retries exhausted")


# ==============================================================================
# Prompt Management
# ==============================================================================

def get_bank_statement_prompt() -> str:
    """
    Retrieve bank statement extraction prompt from ConfigurationTable.
    Falls back to default prompt if not found.
    """
    
    if not config_table:
        log_with_timestamp("⚠️ ConfigurationTable not configured - using default prompt")
        return get_default_bank_statement_prompt()
    
    try:
        response = config_table.get_item(
            Key={'Configuration': 'BANK_STATEMENT_EXTRACTION_PROMPT'}
        )
        
        if 'Item' in response and 'PromptTemplate' in response['Item']:
            log_with_timestamp("✅ Retrieved custom bank statement prompt from ConfigurationTable")
            return response['Item']['PromptTemplate']
        else:
            log_with_timestamp("⚠️ No prompt found in ConfigurationTable - using default")
            return get_default_bank_statement_prompt()
    
    except Exception as e:
        log_with_timestamp(f"⚠️ Error retrieving prompt from ConfigurationTable: {str(e)}")
        return get_default_bank_statement_prompt()


def get_default_bank_statement_prompt() -> str:
    """
    Default bank statement extraction prompt with:
    - Multiple statement detection
    - Per-transaction account info
    - Field-level confidence scores
    - Page number extraction
    """
    
    return """Extract bank statement transactions from this OCR text. The text may have formatting issues from OCR processing.

CRITICAL DOCUMENT TYPE CHECK:
⚠️ BEFORE extracting anything, verify this is actually a BANK STATEMENT.
- If the document is an INVOICE, RECEIPT, or OTHER document type: Return EMPTY XML: <bank_statement><transactions></transactions></bank_statement>
- DO NOT extract transactions from invoices, receipts, or other non-bank-statement documents
- DO NOT use the example transactions below - they are EXAMPLES ONLY, not real data
- Only extract transactions if you see clear evidence of bank statement formatting (account numbers, sort codes, transaction tables)

CRITICAL: This PDF may contain MULTIPLE bank statements.

PAGE NUMBER EXTRACTION:
- Look for [PAGE:X] markers in the text
- For each transaction, determine which page it appears on
- Include <source_page>X</source_page> in each transaction block
- If no page markers found, use <source_page>1</source_page>

IMPORTANT: This is OCR text from a bank statement PDF, so expect:
- Irregular spacing and line breaks
- Descriptions split across multiple lines
- Headers mixed with transaction data
- Missing or misaligned columns

ACCOUNT HEADER DETECTION:
- Look for account headers on EVERY page (accounts may change mid-document)
- Extract: account number, sort code, statement period
- If you find a NEW account number/sort code, this is a NEW statement
- Include account info in EVERY transaction (critical for multi-statement PDFs)

TRANSACTION PATTERNS TO LOOK FOR:
1. DATE PATTERNS: "27 Jul", "Aug", "14 Jul", "2020-07-27", etc.
2. TRANSACTION TYPES: "Direct debit", "Bank credit", "PAYPAL", "Contactless Payment", "Transfer", "DD", "SO", etc.
3. AMOUNTS: Numbers with decimal points (£X.XX format or just X.XX)
4. BALANCES: Running balance numbers (may be negative)
5. DESCRIPTIONS: Merchant names, payment references

EXTRACTION RULES:
1. Extract EVERY transaction you can identify, even if formatting is poor
2. Use negative amounts for debits (money out)
3. Use positive amounts for credits (money in)
4. If balance is missing, leave empty
5. Clean up descriptions by removing extra whitespace
6. Skip obvious non-transaction text (headers, terms, page numbers)
7. MUST include account_number, sort_code, statement_period in EVERY transaction
8. Extract compliance fields:
   - <counterparty_name>: Who was paid/who paid (merchant, company, person)
   - <direction>: INBOUND or OUTBOUND
   - <payment_method>: BACS, CHAPS, FASTER_PAYMENT, CARD, ATM, DD, SO, CASH, TRANSFER
   - <counterparty_country>: Extract if visible in description (e.g., "USA", "GBR", "LONDON GBR")
     * For UK domestic payments (Faster Payments, Direct Debit, UK companies): use "UK"
     * If country not visible and cannot be inferred: use "UNKNOWN"

FIELD-LEVEL CONFIDENCE SCORES (0.0 to 1.0):
For each transaction, provide confidence scores:
- <date_confidence>0.95</date_confidence> - How confident in transaction date?
- <amount_confidence>0.98</amount_confidence> - How confident in amount?
- <description_confidence>0.85</description_confidence> - How clear is description?
- <account_info_confidence>0.95</account_info_confidence> - How confident in account header?

Confidence Guidelines:
- 0.95-1.0: Field explicitly visible, clear value
- 0.80-0.94: Field clear but minor OCR issues
- 0.60-0.79: Field inferred from context or ambiguous
- 0.40-0.59: Significant uncertainty
- 0.0-0.39: Field missing or very unclear

⚠️ EXAMPLE OUTPUT FORMAT (DO NOT COPY THESE VALUES - EXTRACT FROM THE ACTUAL TEXT BELOW):
Return in XML format:
<bank_statement>
<account_info>
  <account_number>10766329</account_number>
  <sort_code>07-04-36</sort_code>
  <statement_period>14 Aug 2020</statement_period>
  <bank_name>Barclays</bank_name>
</account_info>
<transactions>
<transaction>
  <account_number>10766329</account_number>
  <sort_code>07-04-36</sort_code>
  <statement_period>14 Aug 2020</statement_period>
  <date>2020-07-27</date>
  <description>Bank credit 862834451961-CHB</description>
  <amount>84.20</amount>
  <balance>150.50</balance>
  <transaction_type>CREDIT</transaction_type>
  <reference>862834451961-CHB</reference>
  <counterparty_name>CHB</counterparty_name>
  <direction>INBOUND</direction>
  <payment_method>BACS</payment_method>
  <counterparty_country>UK</counterparty_country>
  <source_page>2</source_page>
  <date_confidence>0.95</date_confidence>
  <amount_confidence>0.98</amount_confidence>
  <description_confidence>0.90</description_confidence>
  <account_info_confidence>0.95</account_info_confidence>
</transaction>
<transaction>
  <account_number>10766329</account_number>
  <sort_code>07-04-36</sort_code>
  <statement_period>14 Aug 2020</statement_period>
  <date>2020-07-27</date>
  <description>Direct debit PAYPAL PAYMENT</description>
  <amount>-20.80</amount>
  <balance>129.70</balance>
  <transaction_type>DD</transaction_type>
  <reference>PAYPAL</reference>
  <counterparty_name>PAYPAL</counterparty_name>
  <direction>OUTBOUND</direction>
  <payment_method>DD</payment_method>
  <counterparty_country>USA</counterparty_country>
  <source_page>2</source_page>
  <date_confidence>0.95</date_confidence>
  <amount_confidence>0.98</amount_confidence>
  <description_confidence>0.88</description_confidence>
  <account_info_confidence>0.95</account_info_confidence>
</transaction>
</transactions>
</bank_statement>

<!-- If NEW statement detected with different account -->
<bank_statement>
<account_info>
  <account_number>98765432</account_number>
  <sort_code>04-52-18</sort_code>
  <statement_period>15 Aug 2020</statement_period>
  <bank_name>HSBC</bank_name>
</account_info>
<transactions>
<transaction>
  <account_number>98765432</account_number>
  <sort_code>04-52-18</sort_code>
  <statement_period>15 Aug 2020</statement_period>
  <date>2020-08-01</date>
  <description>Contactless payment TESCO</description>
  <amount>-15.50</amount>
  <balance>85.20</balance>
  <transaction_type>DEBIT</transaction_type>
  <reference>TESCO</reference>
  <source_page>7</source_page>
  <date_confidence>0.95</date_confidence>
  <amount_confidence>0.98</amount_confidence>
  <description_confidence>0.92</description_confidence>
  <account_info_confidence>0.95</account_info_confidence>
</transaction>
</transactions>
</bank_statement>
⚠️ END OF EXAMPLES - DO NOT USE THESE VALUES IN YOUR OUTPUT ⚠️

REMEMBER:
- If the text below is NOT a bank statement (e.g., it's an invoice, receipt, etc.), return: <bank_statement><transactions></transactions></bank_statement>
- DO NOT hallucinate or copy example transactions
- Only extract what you actually see in the text below

TEXT TO PROCESS:
{section_text}"""


# ==============================================================================
# XML Parsing Functions
# ==============================================================================

def extract_account_info_from_xml(xml_result: str) -> List[Dict[str, Any]]:
    """
    Extract all account info sections from XML.
    Returns list of account info dicts (supports multiple statements in one PDF).
    """
    
    account_infos = []
    
    # Pattern to match account_info blocks
    account_pattern = r'<account_info>(.*?)</account_info>'
    field_pattern = r'<(\w+)>(.*?)</\1>'
    
    account_matches = re.finditer(account_pattern, xml_result, re.DOTALL)
    
    for account_match in account_matches:
        account_data = account_match.group(1)
        account_info = {}
        
        for field_match in re.finditer(field_pattern, account_data):
            field_name, value = field_match.groups()
            account_info[field_name] = value.strip()
        
        if account_info:
            account_infos.append(account_info)
    
    return account_infos


def parse_transactions_from_xml(
    xml_result: str,
    chunk_index: int,
    fallback_account_info: Optional[Dict] = None
) -> tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    Parse transactions from XML response.
    
    Returns:
        Tuple of (transactions_list, last_account_info)
    """
    
    transactions = []
    last_account_info = fallback_account_info
    
    # Extract account info from XML
    account_infos = extract_account_info_from_xml(xml_result)
    if account_infos:
        last_account_info = account_infos[-1]  # Use last found account info
        log_with_timestamp(
            f"📋 Found {len(account_infos)} account header(s) in chunk {chunk_index}"
        )
    
    # Extract transactions
    transaction_pattern = r'<transaction>(.*?)</transaction>'
    field_pattern = r'<(\w+)>(.*?)</\1>'
    
    transaction_matches = list(re.finditer(transaction_pattern, xml_result, re.DOTALL))
    
    if not transaction_matches:
        log_with_timestamp(f"⚠️ No transactions found in chunk {chunk_index}")
        return transactions, last_account_info
    
    log_with_timestamp(f"📄 Found {len(transaction_matches)} transactions in chunk {chunk_index}")
    
    for idx, transaction_match in enumerate(transaction_matches, 1):
        transaction_data = transaction_match.group(1)
        row_data = {}
        
        # Extract fields from XML
        for field_match in re.finditer(field_pattern, transaction_data):
            field_name, value = field_match.groups()
            row_data[field_name] = value.strip()
        
        # Validate essential fields
        if not row_data.get('date') or not row_data.get('amount'):
            log_with_timestamp(
                f"⚠️ Skipping transaction {idx} in chunk {chunk_index} - missing date or amount"
            )
            continue
        
        # Use transaction's account info if present, else fallback to header
        transaction_account_info = {
            'account_number': row_data.get('account_number') or (last_account_info or {}).get('account_number', ''),
            'sort_code': row_data.get('sort_code') or (last_account_info or {}).get('sort_code', ''),
            'statement_period': row_data.get('statement_period') or (last_account_info or {}).get('statement_period', ''),
            'bank_name': row_data.get('bank_name') or (last_account_info or {}).get('bank_name', '')
        }
        
        # Parse amounts with proper decimal handling
        try:
            amount = Decimal(str(row_data.get('amount', '0')))
        except:
            amount = Decimal('0')
        
        try:
            balance = Decimal(str(row_data.get('balance', ''))) if row_data.get('balance') else None
        except:
            balance = None
        
        # Parse source page
        try:
            source_page = int(row_data.get('source_page', '1'))
        except:
            source_page = 1
        
        # Parse confidence scores
        try:
            date_confidence = Decimal(str(row_data.get('date_confidence', '0.85')))
        except:
            date_confidence = Decimal('0.85')
        
        try:
            amount_confidence = Decimal(str(row_data.get('amount_confidence', '0.85')))
        except:
            amount_confidence = Decimal('0.85')
        
        try:
            description_confidence = Decimal(str(row_data.get('description_confidence', '0.85')))
        except:
            description_confidence = Decimal('0.85')
        
        try:
            account_info_confidence = Decimal(str(row_data.get('account_info_confidence', '0.85')))
        except:
            account_info_confidence = Decimal('0.85')
        
        # Calculate composite confidence
        composite_confidence = (
            date_confidence + amount_confidence + description_confidence + account_info_confidence
        ) / Decimal('4')
        
        # Build transaction record
        transaction_record = {
            'date': row_data.get('date', ''),
            'description': row_data.get('description', ''),
            'amount': amount,
            'balance': balance,
            'transaction_type': row_data.get('transaction_type', 'DEBIT' if amount < 0 else 'CREDIT'),
            'reference': row_data.get('reference', ''),
            
            # New HMRC compliance fields
            'counterparty_name': row_data.get('counterparty_name', ''),
            'direction': row_data.get('direction', 'OUTBOUND' if amount < 0 else 'INBOUND'),
            'payment_method': row_data.get('payment_method', ''),
            'counterparty_country': row_data.get('counterparty_country', 'UNKNOWN'),
            
            'source_page': source_page,
            'chunk_index': chunk_index,
            
            # Account info (duplicated per transaction for easy filtering)
            'account_number': transaction_account_info['account_number'],
            'sort_code': transaction_account_info['sort_code'],
            'statement_period': transaction_account_info['statement_period'],
            'bank_name': transaction_account_info['bank_name'],
            
            # Confidence scores
            'date_confidence': date_confidence,
            'amount_confidence': amount_confidence,
            'description_confidence': description_confidence,
            'account_info_confidence': account_info_confidence,
            'composite_confidence': composite_confidence,
            
            # Quality tier
            'quality_tier': 'EXCELLENT' if composite_confidence >= Decimal('0.95') else
                           'GOOD' if composite_confidence >= Decimal('0.80') else
                           'FAIR' if composite_confidence >= Decimal('0.60') else 'POOR'
        }
        
        transactions.append(transaction_record)
    
    return transactions, last_account_info


# ==============================================================================
# DynamoDB Write Functions
# ==============================================================================

def write_transactions_to_dynamodb(
    transactions: List[Dict[str, Any]],
    document_id: str,
    section_id: str,
    user_id: str,
    client_id: str,
    company_number: Optional[str] = None,
    company_name: Optional[str] = None,
    model_used: str = 'unknown'
) -> int:
    """
    Write individual transaction records to ExtractionResultsTable.
    Each transaction gets its own DynamoDB row with unique SK.
    
    Returns:
        Number of transactions inserted
    """
    
    if not extraction_table:
        log_with_timestamp("⚠️ EXTRACTION_RESULTS_TABLE not configured - skipping DynamoDB write")
        return 0
    
    inserted_count = 0
    current_timestamp = int(time.time())
    
    for idx, txn_data in enumerate(transactions):
        try:
            # Generate unique transaction ID
            transaction_id = f"{document_id}-bank-{section_id}-{idx+1}-{str(uuid.uuid4())[:8]}"
            
            # Create DynamoDB item
            item = {
                # Primary Key
                'PK': f"user#{user_id}#doc#{document_id}",
                'SK': f"type#BANK_STATEMENT#section#{section_id}#txn#{idx+1}",
                
                # GSI Keys
                'GSI1PK': f"user#{user_id}#type#BANK_STATEMENT",
                'ProcessedAt': current_timestamp,
                'UserId': user_id,
                'GSI3PK': f"account#{txn_data['account_number']}#type#BANK_STATEMENT",
                'DocumentId': document_id,
                'ExtractionStatus': 'COMPLETED',
                'AnalysisStatus': 'PENDING',
                'GSI6PK': f"client#{client_id}#type#BANK_STATEMENT",
                
                # Core identifiers
                'TransactionId': transaction_id,
                'SectionId': section_id,
                'ClientId': client_id,
                'CompanyNumber': company_number,  # Required field from frontend
                'CompanyName': company_name,  # Required field from frontend
                'DocumentType': 'BANK_STATEMENT',
                
                # Account information (duplicated for easy filtering)
                'AccountNumber': txn_data['account_number'],
                'SortCode': txn_data['sort_code'],
                'StatementPeriod': txn_data['statement_period'],
                'BankName': txn_data['bank_name'],
                
                # Transaction fields
                'TransactionDate': txn_data['date'],
                'TransactionDescription': txn_data['description'],
                'TransactionAmount': txn_data['amount'],
                'AccountBalance': txn_data['balance'] if txn_data['balance'] is not None else Decimal('0'),
                'TransactionType': txn_data['transaction_type'],
                'Reference': txn_data['reference'],
                
                # HMRC compliance fields
                'CounterpartyName': txn_data['counterparty_name'],
                'Direction': txn_data['direction'],
                'PaymentMethod': txn_data['payment_method'],
                'CounterpartyCountry': txn_data['counterparty_country'],
                
                'SourcePage': txn_data['source_page'],
                
                # Chunk metadata
                'ChunkIndex': txn_data['chunk_index'],
                
                # Metadata
                'CreatedAt': current_timestamp,
                'UpdatedAt': current_timestamp,
                'DateExtracted': datetime.now().strftime('%Y-%m-%d'),
                'ModelUsed': model_used,
                
                # Confidence scores
                'DateConfidence': txn_data['date_confidence'],
                'AmountConfidence': txn_data['amount_confidence'],
                'DescriptionConfidence': txn_data['description_confidence'],
                'AccountInfoConfidence': txn_data['account_info_confidence'],
                'CompositeConfidence': txn_data['composite_confidence'],
                'QualityTier': txn_data['quality_tier'],
                
                # TTL (optional - 1 year)
                'TTL': current_timestamp + (365 * 24 * 60 * 60)
            }
            
            # Write to DynamoDB
            extraction_table.put_item(Item=item)
            inserted_count += 1
            
            log_with_timestamp(
                f"✅ Inserted transaction {idx+1}/{len(transactions)}: "
                f"{txn_data['description'][:40]} - "
                f"£{txn_data['amount']} (page {txn_data['source_page']})"
            )
            
        except Exception as e:
            log_with_timestamp(f"❌ Error inserting transaction {idx+1}: {str(e)}")
    
    return inserted_count


def write_statement_summary_to_dynamodb(
    document_id: str,
    section_id: str,
    user_id: str,
    client_id: str,
    account_info: Dict[str, Any],
    transactions: List[Dict[str, Any]],
    company_number: Optional[str] = None,
    company_name: Optional[str] = None,
    model_used: str = 'unknown'
) -> bool:
    """
    Write a bank statement summary record to ExtractionResultsTable.
    This creates a single record per statement (similar to how invoices work)
    that can be displayed in the frontend list view.
    
    Returns:
        True if successful, False otherwise
    """
    
    if not extraction_table:
        log_with_timestamp("⚠️ EXTRACTION_RESULTS_TABLE not configured - skipping statement summary write")
        return False
    
    if not transactions:
        log_with_timestamp("⚠️ No transactions to summarize")
        return False
    
    try:
        current_timestamp = int(time.time())
        
        # Calculate summary statistics
        opening_balance = Decimal('0')
        closing_balance = Decimal('0')
        total_debits = Decimal('0')
        total_credits = Decimal('0')
        transaction_count = len(transactions)
        
        # Get opening and closing balances from first and last transactions
        if transactions:
            # Sort by date to find first and last
            sorted_txns = sorted(transactions, key=lambda t: t.get('date', ''))
            
            # Opening balance from first transaction's balance (if available)
            first_txn = sorted_txns[0]
            if first_txn.get('balance') is not None:
                opening_balance = Decimal(str(first_txn['balance']))
            
            # Closing balance from last transaction
            last_txn = sorted_txns[-1]
            if last_txn.get('balance') is not None:
                closing_balance = Decimal(str(last_txn['balance']))
            
            # Calculate totals
            for txn in transactions:
                amount = Decimal(str(txn.get('amount', 0)))
                if amount > 0:
                    total_credits += amount
                else:
                    total_debits += abs(amount)
        
        # Get statement date and period from account info or transactions
        statement_date = account_info.get('statement_period', '')
        if not statement_date and transactions:
            # Use the last transaction date as statement date
            statement_date = sorted_txns[-1].get('date', '')
        
        # Calculate statement period from first and last transaction dates
        statement_period = account_info.get('statement_period', '')
        if transactions and len(sorted_txns) > 0:
            first_date = sorted_txns[0].get('date', '')
            last_date = sorted_txns[-1].get('date', '')
            if first_date and last_date:
                statement_period = f"{first_date} to {last_date}"
        
        # Calculate composite confidence from transaction confidences
        confidence_scores = [
            txn.get('composite_confidence', 0) for txn in transactions
        ]
        composite_confidence = Decimal(str(sum(confidence_scores) / len(confidence_scores))) if confidence_scores else Decimal('0')
        
        # Determine quality tier based on composite confidence
        if composite_confidence >= 0.9:
            quality_tier = 'EXCELLENT'
        elif composite_confidence >= 0.75:
            quality_tier = 'GOOD'
        elif composite_confidence >= 0.6:
            quality_tier = 'ACCEPTABLE'
        else:
            quality_tier = 'NEEDS_REVIEW'
        
        # Generate unique statement ID
        statement_id = f"{document_id}-stmt-{section_id}-{str(uuid.uuid4())[:8]}"
        
        # Create DynamoDB item for statement summary
        item = {
            # Primary Key
            'PK': f"user#{user_id}#doc#{document_id}",
            'SK': f"type#BANK_STATEMENT#section#{section_id}#statement#summary",
            
            # GSI Keys
            'GSI1PK': f"user#{user_id}#type#BANK_STATEMENT",
            'ProcessedAt': current_timestamp,
            'UserId': user_id,
            'GSI3PK': f"account#{account_info.get('account_number', 'unknown')}#type#BANK_STATEMENT",
            'DocumentId': document_id,
            'ExtractionStatus': 'COMPLETED',
            'GSI6PK': f"client#{company_number or client_id}#type#BANK_STATEMENT",
            
            # Core identifiers
            'StatementId': statement_id,
            'SectionId': section_id,
            'ClientId': client_id,
            'CompanyNumber': company_number or 'unknown',
            'CompanyName': company_name or 'Unknown Company',
            'DocumentType': 'BANK_STATEMENT',
            
            # Bank statement summary fields
            'BankName': account_info.get('bank_name', 'Unknown Bank'),
            'AccountNumber': account_info.get('account_number', 'Unknown'),
            'SortCode': account_info.get('sort_code', ''),
            'StatementDate': statement_date,
            'StatementPeriod': statement_period,
            'OpeningBalance': opening_balance,
            'ClosingBalance': closing_balance,
            'TotalDebits': total_debits,
            'TotalCredits': total_credits,
            'TransactionCount': transaction_count,
            'Currency': 'GBP',  # Default to GBP for UK bank statements
            
            # Confidence and quality
            'ConfidenceScore': composite_confidence,
            'CompositeConfidence': composite_confidence,
            'QualityTier': quality_tier,
            'HITLRequired': quality_tier == 'NEEDS_REVIEW',
            'HITLReason': 'Low confidence score' if quality_tier == 'NEEDS_REVIEW' else None,
            
            # Metadata
            'CreatedAt': current_timestamp,
            'UpdatedAt': current_timestamp,
            'DateExtracted': datetime.now().strftime('%Y-%m-%d'),
            'ModelUsed': model_used,
            
            # TTL (optional - 1 year)
            'TTL': current_timestamp + (365 * 24 * 60 * 60)
        }
        
        # Write to DynamoDB
        extraction_table.put_item(Item=item)
        
        log_with_timestamp(
            f"✅ Inserted statement summary: {account_info.get('bank_name')} "
            f"Account {account_info.get('account_number')} - "
            f"{transaction_count} transactions, "
            f"Balance: £{opening_balance} → £{closing_balance}"
        )
        
        return True
        
    except Exception as e:
        log_with_timestamp(f"❌ Error inserting statement summary: {str(e)}")
        import traceback
        log_with_timestamp(traceback.format_exc())
        return False


# ==============================================================================
# Single Chunk Processing
# ==============================================================================

def process_single_chunk(
    chunk_text: str,
    chunk_index: int,
    previous_account_info: Optional[Dict],
    document_id: str,
    section_id: str,
    user_id: str,
    client_id: str,
    company_number: Optional[str] = None,
    company_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Process a single chunk (page) of a bank statement.
    
    Returns:
        Dict with 'transactions', 'account_info', 'transactions_inserted'
    """
    
    log_with_timestamp(f"🔄 Processing chunk {chunk_index}...")
    
    # Get prompt template
    prompt_template = get_bank_statement_prompt()
    
    # Fill in the section text
    prompt = prompt_template.replace('{section_text}', chunk_text)
    
    # Invoke Bedrock
    model_used_tracker = []
    xml_result = invoke_bedrock_with_retry(prompt, model_used_tracker)
    model_used = model_used_tracker[0] if model_used_tracker else 'unknown'
    
    # Parse transactions
    transactions, current_account_info = parse_transactions_from_xml(
        xml_result,
        chunk_index,
        previous_account_info
    )
    
    # Detect statement boundary
    if current_account_info and previous_account_info:
        if (current_account_info.get('account_number') != previous_account_info.get('account_number') or
            current_account_info.get('sort_code') != previous_account_info.get('sort_code')):
            log_with_timestamp(
                f"🔄 NEW BANK STATEMENT DETECTED in chunk {chunk_index}!"
            )
            log_with_timestamp(
                f"   Previous: Account {previous_account_info.get('account_number')}, "
                f"Sort Code {previous_account_info.get('sort_code')}"
            )
            log_with_timestamp(
                f"   New: Account {current_account_info.get('account_number')}, "
                f"Sort Code {current_account_info.get('sort_code')}"
            )
    
    # Write to DynamoDB
    transactions_inserted = write_transactions_to_dynamodb(
        transactions=transactions,
        document_id=document_id,
        section_id=section_id,
        user_id=user_id,
        client_id=client_id,
        company_number=company_number,
        company_name=company_name,
        model_used=model_used
    )
    
    return {
        'transactions': transactions,
        'account_info': current_account_info,
        'transactions_inserted': transactions_inserted
    }


# ==============================================================================
# Main Lambda Handler
# ==============================================================================

def lambda_handler(event, context):
    """
    Stateful bank statement extraction with resume capability.
    
    Processes chunks one at a time, saves progress, and signals if more work needed.
    Handles large statements (100+ pages) without hitting Lambda timeout.
    """
    
    start_time = time.time()
    
    try:
        log_with_timestamp("🚀 Bank Statement Extraction Lambda started")
        log_with_timestamp(f"📥 Event: {json.dumps(event, default=str)[:500]}...")
        
        # Get document and section info
        section_id = event.get('section_id')
        if not section_id:
            raise ValueError("No section_id found in event")
        
        document_data = event.get('document', {})
        log_with_timestamp(f"📄 Document data type: {type(document_data)}")
        
        # Handle compressed document - check both string format and dict with compressed flag
        if isinstance(document_data, str):
            # Document is passed as S3 URI string - fetch from S3
            s3_client = boto3.client('s3')
            from urllib.parse import urlparse
            parsed_uri = urlparse(document_data)
            bucket = parsed_uri.netloc
            key = parsed_uri.path.lstrip('/')
            
            log_with_timestamp(f"📥 Fetching document from S3: s3://{bucket}/{key}")
            s3_obj = s3_client.get_object(Bucket=bucket, Key=key)
            document_dict = json.loads(s3_obj['Body'].read().decode('utf-8'))
            
        elif isinstance(document_data, dict) and (document_data.get('compressed') or 's3_uri' in document_data):
            # Document is compressed and stored in S3 - fetch it
            s3_uri = document_data.get('s3_uri')
            if not s3_uri:
                raise ValueError("Document marked as compressed but no s3_uri provided")
                
            log_with_timestamp(f"� Document is compressed, fetching from S3: {s3_uri}")
            
            s3_client = boto3.client('s3')
            from urllib.parse import urlparse
            parsed_uri = urlparse(s3_uri)
            bucket = parsed_uri.netloc
            key = parsed_uri.path.lstrip('/')
            
            s3_obj = s3_client.get_object(Bucket=bucket, Key=key)
            document_dict = json.loads(s3_obj['Body'].read().decode('utf-8'))
            
        elif isinstance(document_data, dict):
            # Document is inline dict (already decompressed)
            document_dict = document_data
        else:
            raise ValueError(f"Invalid document format: {type(document_data)}")
        
        # Log document structure for debugging
        log_with_timestamp(f"📦 Document keys: {list(document_dict.keys())}")
        log_with_timestamp(f"📦 Document has {len(document_dict.get('pages', {}))} pages")
        log_with_timestamp(f"📦 Document has {len(document_dict.get('sections', []))} sections")
        
        # Extract document metadata (matching invoice extraction pattern)
        document_id = (
            document_dict.get('id')
            or document_dict.get('document_id')
            or document_dict.get('documentId')
        )
        user_id = document_dict.get('user_id')
        company_number = document_dict.get('company_number')
        company_name = document_dict.get('company_name')
        client_id = company_number or document_dict.get('client_id')  # Use company_number as client_id
        
        # DIAGNOSTIC LOGGING: Check all metadata fields in document
        log_with_timestamp(f"🔍 ALL document_dict keys: {sorted(document_dict.keys())}")
        log_with_timestamp(f"🔍 company_number in dict: {company_number}")
        log_with_timestamp(f"🔍 company_name in dict: {company_name}")
        log_with_timestamp(f"🔍 client_id in dict: {document_dict.get('client_id')}")
        log_with_timestamp(f"🔍 Extracted metadata - ID: {document_id}, User: {user_id}, Client: {client_id}, Company: {company_name} ({company_number})")
        
        # CRITICAL SECURITY: Validate required fields to prevent document leaks between users/companies
        # Both user_id and client_id (company_number) MUST be present to ensure proper document isolation
        if not all([document_id, section_id, user_id, client_id]):
            raise ValueError(
                f"SECURITY ERROR: Missing required fields for document isolation. "
                f"document_id={document_id}, section_id={section_id}, "
                f"user_id={user_id}, client_id={client_id}, company_number={company_number}. "
                f"All bank statements MUST be associated with a company to prevent data leakage."
            )
        
        log_with_timestamp(
            f"📄 Document: {document_id}, Section: {section_id}, "
            f"User: {user_id}, Client: {client_id}"
        )
        
        # Check if this is a resume (continuation)
        resume_state = event.get('resume_state')
        
        if resume_state:
            log_with_timestamp(
                f"🔄 RESUMING extraction from chunk {resume_state['next_chunk_index']}"
            )
            chunk_start_index = resume_state['next_chunk_index']
            stored_account_info = resume_state.get('last_account_info')
            total_transactions_inserted = resume_state.get('total_transactions_inserted', 0)
            all_transactions = resume_state.get('all_transactions', [])  # Restore collected transactions
        else:
            log_with_timestamp("🆕 Starting NEW bank statement extraction")
            chunk_start_index = 0
            stored_account_info = None
            total_transactions_inserted = 0
            all_transactions = []  # Initialize for new extraction
        
        # Load section text (matching invoice extraction logic)
        sections = document_dict.get('sections', [])
        section_data = None
        
        for section in sections:
            if str(section.get('section_id')) == str(section_id):
                section_data = section
                break
        
        if not section_data:
            raise ValueError(f"Section {section_id} not found in document. Available sections: {[s.get('section_id') for s in sections]}")
        
        log_with_timestamp(f"📋 Section data keys: {list(section_data.keys())}")
        log_with_timestamp(f"📋 Section data: {json.dumps(section_data, default=str)[:500]}")
        
        # Get section text from OCR results
        section_text = ""
        section_pages = section_data.get('page_ids', [])
        
        log_with_timestamp(f"📄 Section has {len(section_pages)} page IDs: {section_pages}")
        
        # Check if section has ocr_text directly
        if 'ocr_text' in section_data:
            section_text = section_data['ocr_text']
            log_with_timestamp(f"✅ Found ocr_text directly in section ({len(section_text)} chars)")
        
        # Build section text from pages if not found in section
        if not section_text:
            pages = document_dict.get('pages', {})
            log_with_timestamp(f"📚 Document has {len(pages)} pages (dict format)")
            
            # Pages is a dict with page_id as key
            for page_id in section_pages:
                if page_id in pages:
                    page_data = pages[page_id]
                    log_with_timestamp(f"📄 Processing page {page_id}, keys: {list(page_data.keys())}")
                    
                    # Extract page number from page_id
                    page_number = 1
                    try:
                        if page_id.startswith('page-'):
                            page_number = int(page_id.split('-')[1])
                        elif page_id.isdigit():
                            page_number = int(page_id)
                    except (ValueError, IndexError):
                        page_number = section_pages.index(page_id) + 1
                    
                    # Add page marker for chunk tracking
                    page_marker = f"\n[PAGE:{page_number}]\n"
                    
                    # Check if page has inline ocr_text
                    if 'ocr_text' in page_data:
                        page_text = page_data['ocr_text']
                        section_text += page_marker + page_text + "\n"
                        log_with_timestamp(f"✅ Added inline text from page {page_id} (page #{page_number}, {len(page_text)} chars)")
                    
                    # Otherwise fetch from raw_text_uri
                    elif 'raw_text_uri' in page_data:
                        raw_text_uri = page_data['raw_text_uri']
                        log_with_timestamp(f"📥 Fetching OCR text from: {raw_text_uri}")
                        
                        from urllib.parse import urlparse
                        parsed_uri = urlparse(raw_text_uri)
                        bucket = parsed_uri.netloc
                        key = parsed_uri.path.lstrip('/')
                        
                        s3_obj = s3_client.get_object(Bucket=bucket, Key=key)
                        raw_text_data = json.loads(s3_obj['Body'].read().decode('utf-8'))
                        
                        log_with_timestamp(f"📋 rawText.json keys: {list(raw_text_data.keys())}")
                        
                        # rawText.json contains the extracted text
                        page_text = raw_text_data.get('text', '') or raw_text_data.get('Text', '') or raw_text_data.get('content', '')
                        
                        # Try Bedrock Nova response format
                        if not page_text and 'output' in raw_text_data:
                            try:
                                page_text = raw_text_data['output']['message']['content'][0]['text']
                                log_with_timestamp(f"📝 Extracted text from Bedrock response format")
                            except (KeyError, IndexError, TypeError):
                                pass
                        
                        # Try Textract format
                        if not page_text and 'Blocks' in raw_text_data:
                            blocks = raw_text_data.get('Blocks', [])
                            lines = [block.get('Text', '') for block in blocks if block.get('BlockType') == 'LINE']
                            page_text = '\n'.join(lines)
                            log_with_timestamp(f"📝 Extracted {len(lines)} lines from Textract Blocks")
                        
                        if page_text:
                            section_text += page_marker + page_text + "\n"
                            log_with_timestamp(f"✅ Added text from S3 for page {page_id} (page #{page_number}, {len(page_text)} chars)")
                        else:
                            log_with_timestamp(f"⚠️ No text found in rawText.json for page {page_id}")
                    else:
                        log_with_timestamp(f"⚠️ No OCR text found for page {page_id}")
                else:
                    log_with_timestamp(f"⚠️ Page {page_id} not found in pages dict")
        
        if not section_text or len(section_text.strip()) == 0:
            raise ValueError(f"No OCR text content found for section_id: {section_id}")
        
        log_with_timestamp(f"📝 Total section text length: {len(section_text)} characters")
        
        # Create page-based chunks
        chunker = BankStatementChunker()
        all_chunks = chunker.create_page_based_chunks(section_text)
        
        log_with_timestamp(
            f"📊 Total chunks: {len(all_chunks)}, "
            f"Starting from: {chunk_start_index}, "
            f"Remaining: {len(all_chunks) - chunk_start_index}"
        )
        
        # Process chunks until timeout or completion
        chunks_processed_this_run = 0
        
        for chunk_index in range(chunk_start_index, len(all_chunks)):
            # Check remaining time
            elapsed = time.time() - start_time
            remaining = context.get_remaining_time_in_millis() / 1000
            
            if remaining < LAMBDA_TIMEOUT_BUFFER_SECONDS:
                log_with_timestamp(
                    f"⏱️ Approaching timeout ({remaining:.0f}s remaining). "
                    f"Processed {chunks_processed_this_run} chunks this run. "
                    f"Saving progress and signaling for resume..."
                )
                
                # Save progress state
                resume_state = {
                    'next_chunk_index': chunk_index,
                    'last_account_info': stored_account_info,
                    'total_transactions_inserted': total_transactions_inserted,
                    'all_transactions': all_transactions  # Save collected transactions for resume
                }
                
                # Update tracking table
                update_chunk_progress(
                    document_id=document_id,
                    section_id=section_id,
                    chunks_completed=chunk_index,
                    total_chunks=len(all_chunks),
                    status='IN_PROGRESS',
                    last_account_info=stored_account_info
                )
                
                # Return signal to Step Functions to continue
                return {
                    'status': 'MORE_CHUNKS',
                    'resume_state': resume_state,
                    'document': document_dict,
                    'section_id': section_id,
                    'execution_arn': event.get('execution_arn'),
                    'chunks_processed_this_run': chunks_processed_this_run,
                    'total_transactions_inserted': total_transactions_inserted,
                    'progress': f"{chunk_index}/{len(all_chunks)}"
                }
            
            # Process this chunk
            chunk = all_chunks[chunk_index]
            log_with_timestamp(
                f"📄 Processing chunk {chunk_index + 1}/{len(all_chunks)} "
                f"(page {chunk['pages']}, {chunk['size']} chars)"
            )
            
            result = process_single_chunk(
                chunk_text=chunk['text'],
                chunk_index=chunk_index,
                previous_account_info=stored_account_info,
                document_id=document_id,
                section_id=section_id,
                user_id=user_id,
                client_id=client_id,
                company_number=company_number,
                company_name=company_name
            )
            
            # Update stored account info
            if result['account_info']:
                stored_account_info = result['account_info']
            
            # Collect transactions for statement summary
            all_transactions.extend(result['transactions'])
            
            total_transactions_inserted += result['transactions_inserted']
            chunks_processed_this_run += 1
        
        # All chunks processed successfully
        log_with_timestamp(
            f"✅ COMPLETED extraction: {len(all_chunks)} chunks, "
            f"{total_transactions_inserted} transactions inserted"
        )
        
        # Write statement summary record (for frontend display)
        if stored_account_info and all_transactions:
            log_with_timestamp("📝 Writing bank statement summary record...")
            write_statement_summary_to_dynamodb(
                document_id=document_id,
                section_id=section_id,
                user_id=user_id,
                client_id=client_id,
                account_info=stored_account_info,
                transactions=all_transactions,
                company_number=company_number,
                company_name=company_name,
                model_used='bedrock-claude'  # Can be updated to track actual model
            )
        else:
            log_with_timestamp(f"⚠️ Skipping statement summary - account_info: {stored_account_info is not None}, transactions: {len(all_transactions)}")
        
        # Update final status
        update_chunk_progress(
            document_id=document_id,
            section_id=section_id,
            chunks_completed=len(all_chunks),
            total_chunks=len(all_chunks),
            status='COMPLETED',
            last_account_info=stored_account_info
        )
        
        # Return completion signal
        return {
            'status': 'COMPLETE',
            'document': document_dict,
            'section_id': section_id,
            'execution_arn': event.get('execution_arn'),
            'total_chunks_processed': len(all_chunks),
            'total_transactions_inserted': total_transactions_inserted
        }
        
    except Exception as e:
        log_with_timestamp(f"❌ ERROR in bank statement extraction: {str(e)}")
        
        # Save error state if possible
        if 'document_id' in locals() and 'section_id' in locals():
            update_chunk_progress(
                document_id=document_id,
                section_id=section_id,
                chunks_completed=chunk_index if 'chunk_index' in locals() else 0,
                total_chunks=len(all_chunks) if 'all_chunks' in locals() else 0,
                status='FAILED',
                error=str(e)
            )
        
        raise
