"""
Transaction Categorization Lambda
Analyzes bank transactions using Claude for expense categorization and risk scoring.
Adapted from PoC for IDP Core ExtractionResultsTable.
"""

import re
import json
import boto3
import time
import os
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Any, Optional

def log_with_timestamp(message):
    """Helper function to log messages with timestamps"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    print(f"[{timestamp}] {message}")

# AWS clients
dynamodb = boto3.resource('dynamodb')
bedrock = boto3.client('bedrock-runtime', region_name=os.environ.get('AWS_REGION', 'eu-west-1'))
sqs = boto3.client('sqs')

# Environment variables
EXTRACTION_RESULTS_TABLE = os.environ.get('EXTRACTION_RESULTS_TABLE')
CATEGORIZATION_QUEUE_URL = os.environ.get('CATEGORIZATION_QUEUE_URL')
BEDROCK_MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'eu.anthropic.claude-3-5-sonnet-20240620-v1:0')

# Categories for bank transactions
TRANSACTION_EXPENSE_CATEGORIES = """
Office Costs
Travel costs
Clothing costs
Staff costs
Things you buy to sell on
Financial costs
Costs of your business premises
Advertising or marketing
Training course
Accommodation
Bank charges
Bonuses
Business travel mileage for employees' own vehicles
Car parking charges
Cash sum payments to employees
Childcare
Christmas bonuses
Clothing
Club membership
Company cars and fuel
Company vans and fuel
Credit, debit and charge cards
Employee liabilities and indemnity insurance
Entertainment
Food and groceries
Holidays
Home phones
Homeworking
Income tax paid on directors' behalf
Items for disabled employees
Loans provided to employees
Long-service awards
Lost-time payments
Meals for employees and directors
Medical or dental treatment and insurance
Mobile phones
Office and workshop equipment and supplies
Parking spaces
Personal bills
Private use of heavy goods vehicles
Public transport
Relocation costs
Retirement benefit schemes
School fees for an employee's child
Social functions and parties
Sporting or recreational facilities
Subscriptions and professional fees
Training payments
Travel
Trivial benefits
Vouchers
Software
Computer Hardware
Cash withdrawal
Direct debit payments
Standing order payments
Transfer payments
Salary payments
Interest received
Interest paid
Loan repayments
Insurance payments
Utility payments
"""

def get_day_of_week(date_string):
    """Get day of week from date string"""
    if not date_string:
        return "Unknown"
    try:
        date_obj = datetime.strptime(date_string, '%Y-%m-%d')
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        return days[date_obj.weekday()]
    except:
        return "Unknown"

def get_counterparty_name(transaction: Dict) -> str:
    """Extract counterparty name with fallback to description"""
    counterparty = transaction.get('CounterpartyName')
    if counterparty and counterparty != 'NOT_AVAILABLE':
        return counterparty
    # Fallback to description for backward compatibility
    return transaction.get('TransactionDescription') or transaction.get('Description') or 'Unknown'

def get_direction(transaction: Dict) -> str:
    """Extract transaction direction with fallback logic"""
    # First, check for new Direction field
    direction = transaction.get('Direction')
    if direction and direction != 'UNKNOWN':
        return direction
    
    # Fallback: infer from TransactionType
    txn_type = transaction.get('TransactionType', '').upper()
    if txn_type == 'DEBIT':
        return 'OUTBOUND'
    elif txn_type == 'CREDIT':
        return 'INBOUND'
    
    # Fallback: infer from MoneyIn/MoneyOut
    if transaction.get('MoneyOut'):
        return 'OUTBOUND'
    elif transaction.get('MoneyIn'):
        return 'INBOUND'
    
    # Fallback: infer from amount sign
    amount = transaction.get('TransactionAmount')
    if amount:
        try:
            amount_val = float(amount)
            return 'INBOUND' if amount_val > 0 else 'OUTBOUND'
        except:
            pass
    
    return 'UNKNOWN'

def get_payment_method(transaction: Dict) -> str:
    """Extract payment method with fallback to description parsing"""
    # First, check for new PaymentMethod field
    method = transaction.get('PaymentMethod')
    if method and method != 'UNKNOWN':
        return method
    
    # Fallback: infer from description
    description = transaction.get('TransactionDescription') or transaction.get('Description') or ''
    description_upper = description.upper()
    
    # Common payment method keywords
    if 'CARD' in description_upper or 'VISA' in description_upper or 'MASTERCARD' in description_upper:
        return 'CARD'
    elif 'ATM' in description_upper:
        return 'ATM'
    elif 'CASH' in description_upper:
        return 'CASH'
    elif 'BACS' in description_upper:
        return 'BACS'
    elif 'CHAPS' in description_upper:
        return 'CHAPS'
    elif 'FP' in description_upper or 'FASTER PAYMENT' in description_upper:
        return 'FASTER_PAYMENT'
    elif 'DD' in description_upper or 'DIRECT DEBIT' in description_upper:
        return 'DIRECT_DEBIT'
    elif 'SO' in description_upper or 'STANDING ORDER' in description_upper:
        return 'STANDING_ORDER'
    elif 'CHQ' in description_upper or 'CHEQUE' in description_upper:
        return 'CHEQUE'
    elif 'TRANSFER' in description_upper:
        return 'TRANSFER'
    
    return 'UNKNOWN'

def create_batch_categorization_prompt(transaction_batch, categories: str):
    """Create sophisticated prompt for Claude to categorize bank transactions"""
    
    # Convert transactions to formatted text with context
    transaction_list = []
    for transaction in transaction_batch:
        counterparty = get_counterparty_name(transaction)
        direction = get_direction(transaction)
        payment_method = get_payment_method(transaction)
        country = transaction.get('CounterpartyCountry', 'NOT_AVAILABLE')
        
        transaction_text = f"""
Transaction ID: {transaction.get('TransactionId', 'Unknown')}
Date: {transaction.get('TransactionDate') or 'Unknown'}
Day of Week: {get_day_of_week(transaction.get('TransactionDate'))}
Counterparty: {counterparty}
Description: {transaction.get('TransactionDescription') or transaction.get('Description') or 'No description'}
Amount: £{transaction.get('TransactionAmount') or transaction.get('MoneyOut') or transaction.get('MoneyIn') or '0'}
Direction: {direction}
Payment Method: {payment_method}
Country: {country if country and country != 'NOT_AVAILABLE' else 'Not stated'}
Reference: {transaction.get('Reference') or 'N/A'}
"""
        transaction_list.append(transaction_text)
    
    transactions_text = "\n".join(transaction_list)
    
    prompt = f"""You are an experienced forensic accountant reviewing bank transactions for potential tax and compliance issues. 
Analyze these transactions with professional skepticism while avoiding false positives for legitimate business expenses.

AVAILABLE EXPENSE CATEGORIES:
{categories}

BANK TRANSACTIONS TO ANALYZE:
{transactions_text}

ANALYSIS FRAMEWORK:

Consider these patterns and examples, but use your judgment based on the full context:

LEGITIMATE BUSINESS PATTERNS (typically score 4-5):
• Regular vendors with clear business purpose (utilities, rent, insurance, software subscriptions)
• Business travel with supporting context (client meetings, conferences)
• Professional services with proper references
• ATM withdrawals with business justification (e.g., "petty cash for market stall")
• Round amounts from ATMs are NORMAL and expected
• Weekend hospitality expenses for client entertainment
• Direct debits and standing orders to established vendors

CONTEXT-DEPENDENT PATTERNS (typically score 3):
• Weekend transactions - consider the business type:
  - Restaurant on Saturday might be client entertainment (legitimate)
  - Office supplies on Sunday might be unusual (investigate)
• Round number transfers - consider the context:
  - £500 to "John Smith" with no reference (suspicious)
  - £500 to "ABC Ltd - Monthly retainer" (legitimate)
• Foreign transactions - consider the business:
  - Tech company paying for US cloud services (legitimate)
  - Local bakery paying Panama company (suspicious)

RED FLAGS TO IDENTIFY (typically score 1-2):
• Structuring patterns:
  - Multiple £9,999 payments (just below £10k threshold)
  - Series of £4,999 transactions (below £5k threshold)
  - Split payments to same vendor on same day
• Vague descriptions hiding true purpose:
  - "Invoice" or "Services" with no detail
  - "Consultancy" to individuals without company designation
  - "Miscellaneous" for significant amounts
• Personal expenses without business justification:
  - Streaming services (Netflix, Spotify) not for business use
  - School fees, childcare without employee benefit documentation
  - Personal retail (jewelry, clothing) without business purpose
• Director/shareholder concerns:
  - Round number "loans" without documentation
  - Excessive drawings disguised as expenses
  - Personal bills paid by company
• Geographic/vendor risks:
  - Payments to tax havens without clear purpose
  - New vendors with immediately high values
  - Personal names for professional services

IMPORTANT CONTEXTUAL FACTORS:
• Business type matters - retail has different patterns than consultancy
• Timing patterns - month-end clustering might indicate manipulation
• Historical patterns - sudden changes need investigation
• Amount reasonableness - £50 lunch vs £500 lunch
• Documentation quality - proper references vs vague descriptions

For each transaction, assess:
1. Does the expense align with the business nature?
2. Is the amount reasonable for the described purpose?
3. Is there sufficient documentation/reference?
4. Are there any patterns suggesting tax avoidance or personal use?
5. Would this transaction concern an HMRC inspector?

REQUIRED XML FORMAT:
<batch_analysis>
  <transaction id="[EXACT_TRANSACTION_ID]">
    <category>Category name from list above</category>
    <confidence>HIGH|MEDIUM|LOW</confidence>
    <legitimacy_score>4</legitimacy_score>
    <risk_flags>ATM_ROUND_NORMAL|WEEKEND_HOSPITALITY|VAGUE_DESCRIPTION|STRUCTURING|PERSONAL_EXPENSE|DIRECTOR_LOAN|HIGH_VALUE|etc</risk_flags>
    <reasoning>Detailed explanation of your assessment including why you chose specific flags</reasoning>
    <hmrc_concern>YES|NO - Would this likely concern a tax inspector?</hmrc_concern>
    <recommended_action>APPROVE|REVIEW_DOCUMENTATION|INVESTIGATE|REJECT</recommended_action>
  </transaction>
</batch_analysis>

Remember:
- Use the examples as guidance, not rigid rules
- Consider the full context of each transaction
- Round ATM amounts are NORMAL - don't flag without other concerns
- Be specific about WHY something is suspicious
- Provide actionable recommendations"""

    return prompt

def invoke_bedrock(prompt):
    """Invoke Claude via Bedrock for text processing"""
    
    try:
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
        
        response = bedrock.invoke_model(
            body=body,
            modelId=BEDROCK_MODEL_ID,
            accept='application/json',
            contentType='application/json'
        )
        
        response_body = json.loads(response.get('body').read())
        return response_body['content'][0]['text']
        
    except Exception as e:
        log_with_timestamp(f"Bedrock invocation failed: {str(e)}")
        return ""

def parse_categorization_response(response_text, transaction_batch):
    """Parse Claude's enhanced XML response into structured results"""
    
    results = {}
    
    try:
        # Extract each transaction analysis
        transaction_blocks = re.findall(r'<transaction id="([^"]+)">(.*?)</transaction>', response_text, re.DOTALL)
        
        for transaction_id, transaction_content in transaction_blocks:
            # Extract all fields from Claude's analysis
            category_match = re.search(r'<category>(.*?)</category>', transaction_content, re.DOTALL)
            confidence_match = re.search(r'<confidence>(.*?)</confidence>', transaction_content, re.DOTALL)
            score_match = re.search(r'<legitimacy_score>(\d+)</legitimacy_score>', transaction_content, re.DOTALL)
            flags_match = re.search(r'<risk_flags>(.*?)</risk_flags>', transaction_content, re.DOTALL)
            reasoning_match = re.search(r'<reasoning>(.*?)</reasoning>', transaction_content, re.DOTALL)
            hmrc_match = re.search(r'<hmrc_concern>(.*?)</hmrc_concern>', transaction_content, re.DOTALL)
            action_match = re.search(r'<recommended_action>(.*?)</recommended_action>', transaction_content, re.DOTALL)
            
            # Parse risk flags from Claude's response
            risk_flags = []
            if flags_match and flags_match.group(1).strip():
                flags_text = flags_match.group(1).strip()
                if flags_text and flags_text.upper() != 'NONE':
                    risk_flags = [flag.strip() for flag in flags_text.split('|')]
            
            if not risk_flags:
                risk_flags = ['CLEAN']
            
            results[transaction_id] = {
                'category': category_match.group(1).strip() if category_match else 'Uncategorized',
                'confidence': confidence_match.group(1).strip() if confidence_match else 'LOW',
                'legitimacy_score': int(score_match.group(1)) if score_match else 3,
                'risk_flags': risk_flags,
                'reasoning': reasoning_match.group(1).strip() if reasoning_match else 'No reasoning provided',
                'hmrc_concern': hmrc_match.group(1).strip() == 'YES' if hmrc_match else False,
                'recommended_action': action_match.group(1).strip() if action_match else 'REVIEW_DOCUMENTATION'
            }
            
    except Exception as e:
        log_with_timestamp(f"Error parsing categorization response: {str(e)}")
    
    return results

def categorize_transaction_batch(transaction_batch):
    """Categorize a batch of transactions using Claude"""
    
    log_with_timestamp(f"Starting batch categorization for {len(transaction_batch)} transactions")
    
    # Create batch categorization prompt
    prompt = create_batch_categorization_prompt(transaction_batch, TRANSACTION_EXPENSE_CATEGORIES)
    
    # Call Claude for categorization
    response = invoke_bedrock(prompt)
    
    if not response:
        log_with_timestamp("Failed to get categorization response from Claude")
        return {}
    
    # Parse the response
    analysis_results = parse_categorization_response(response, transaction_batch)
    log_with_timestamp(f"Parsed categorization results for {len(analysis_results)} transactions")
    
    return analysis_results

def get_transactions_by_ids(transaction_ids: List[str], company_number: str, user_id: str) -> List[Dict]:
    """Get specific transactions by their IDs for a company/user"""
    
    extraction_table = dynamodb.Table(EXTRACTION_RESULTS_TABLE)
    transactions = []
    
    for transaction_id in transaction_ids:
        try:
            # TransactionId format: users/{userId}/{document}.pdf-bank-{section}-{txn}-{hash}
            # Need to extract document path and transaction number to build PK/SK
            
            # Extract document path (everything before -bank-)
            parts = transaction_id.split('-bank-')
            if len(parts) < 2:
                log_with_timestamp(f"Invalid transaction ID format: {transaction_id}")
                continue
                
            document_path = parts[0]  # Already includes .pdf extension
            bank_parts = parts[1].split('-')  # e.g., ['1', '3', 'd4cf0ecb']
            
            if len(bank_parts) < 2:
                log_with_timestamp(f"Invalid transaction ID format: {transaction_id}")
                continue
                
            section_num = bank_parts[0]
            txn_num = bank_parts[1]
            
            # Build PK and SK based on actual table structure
            pk = f"user#{user_id}#doc#{document_path}"
            sk = f"type#BANK_STATEMENT#section#{section_num}#txn#{txn_num}"
            
            # Get item by primary key
            response = extraction_table.get_item(
                Key={'PK': pk, 'SK': sk}
            )
            
            if 'Item' in response:
                transactions.append(response['Item'])
                log_with_timestamp(f"Found transaction {transaction_id}")
            else:
                log_with_timestamp(f"Transaction {transaction_id} not found (PK: {pk}, SK: {sk})")
                
        except Exception as e:
            log_with_timestamp(f"Error retrieving transaction {transaction_id}: {str(e)}")
    
    return transactions

def update_transaction_analysis(pk: str, sk: str, analysis_result: Dict) -> bool:
    """Update transaction record in DynamoDB with Claude's analysis"""
    
    try:
        extraction_table = dynamodb.Table(EXTRACTION_RESULTS_TABLE)
        
        current_time = int(time.time())
        
        # Build update expression with Claude's complete analysis
        update_expression = """
            SET ExpenseCategory = :category,
                CategorizationConfidence = :confidence,
                LegitimacyScore = :score,
                RiskFlags = :flags,
                CategorizationReasoning = :reasoning,
                RecommendedAction = :action,
                HMRCConcern = :hmrc,
                AnalysisStatus = :status,
                AnalyzedAt = :timestamp,
                UpdatedAt = :timestamp
        """
        
        expression_values = {
            ':category': analysis_result['category'],
            ':confidence': analysis_result['confidence'],
            ':score': Decimal(str(analysis_result['legitimacy_score'])),
            ':flags': analysis_result['risk_flags'],
            ':reasoning': analysis_result['reasoning'],
            ':action': analysis_result['recommended_action'],
            ':hmrc': analysis_result['hmrc_concern'],
            ':status': 'ANALYZED',
            ':timestamp': current_time
        }
        
        # Perform the update
        extraction_table.update_item(
            Key={
                'PK': pk,
                'SK': sk
            },
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values
        )
        
        log_with_timestamp(
            f"Updated transaction: {analysis_result['category']} "
            f"(score: {analysis_result['legitimacy_score']}, action: {analysis_result['recommended_action']})"
        )
        
        return True
        
    except Exception as e:
        log_with_timestamp(f"Error updating transaction: {str(e)}")
        return False

def process_transaction_batch(message_body: Dict) -> Dict:
    """Process a batch of transactions from SQS message"""
    
    transaction_ids = message_body.get('transaction_ids', [])
    company_number = message_body.get('company_number')
    user_id = message_body.get('user_id')
    
    log_with_timestamp(f"Processing batch of {len(transaction_ids)} transactions for company {company_number}")
    
    # Step 1: Get the transactions
    transaction_batch = get_transactions_by_ids(transaction_ids, company_number, user_id)
    
    if not transaction_batch:
        log_with_timestamp(f"No transactions found for IDs: {transaction_ids}")
        return {
            'successful_count': 0,
            'failed_count': len(transaction_ids),
            'failed_transaction_ids': transaction_ids
        }
    
    log_with_timestamp(f"Retrieved {len(transaction_batch)} transactions for processing")
    
    # Step 2: Categorize with Claude
    try:
        analysis_results = categorize_transaction_batch(transaction_batch)
        log_with_timestamp(f"Completed categorization for {len(analysis_results)} transactions")
    except Exception as e:
        log_with_timestamp(f"Categorization failed: {str(e)}")
        return {
            'successful_count': 0,
            'failed_count': len(transaction_ids),
            'failed_transaction_ids': transaction_ids
        }
    
    # Step 3: Update each transaction with analysis
    successful_count = 0
    failed_transaction_ids = []
    
    for transaction in transaction_batch:
        transaction_id = transaction.get('TransactionId')
        pk = transaction.get('PK')
        sk = transaction.get('SK')
        
        if transaction_id in analysis_results:
            analysis = analysis_results[transaction_id]
            
            try:
                if update_transaction_analysis(pk, sk, analysis):
                    successful_count += 1
                    flags_summary = ', '.join(analysis['risk_flags'][:3])
                    log_with_timestamp(
                        f"✅ {transaction_id}: {analysis['category']} "
                        f"(score: {analysis['legitimacy_score']}, flags: {flags_summary})"
                    )
                else:
                    failed_transaction_ids.append(transaction_id)
                    
            except Exception as e:
                log_with_timestamp(f"Error processing transaction {transaction_id}: {str(e)}")
                failed_transaction_ids.append(transaction_id)
        else:
            log_with_timestamp(f"No analysis result for transaction {transaction_id}")
            failed_transaction_ids.append(transaction_id)
    
    log_with_timestamp(
        f"Batch processing complete: {successful_count} successful, {len(failed_transaction_ids)} failed"
    )
    
    return {
        'successful_count': successful_count,
        'failed_count': len(failed_transaction_ids),
        'failed_transaction_ids': failed_transaction_ids
    }

def lambda_handler(event, context):
    """
    Lambda handler for categorizing bank transactions using Claude.
    Invoked by Step Functions Map state for each batch.
    
    Expected event from Step Functions:
    {
        "transaction_ids": ["txn-123", "txn-456", ...],
        "company_number": "12345678",
        "user_id": "user-id",
        "batch_index": 0,
        "batch_size": 15
    }
    
    Returns batch processing result for Step Functions.
    """
    
    log_with_timestamp("Starting batch bank transaction categorization")
    log_with_timestamp(f"Received event: {json.dumps(event, default=str)}")
    
    try:
        # Extract batch parameters directly from event (not from SQS Records)
        transaction_ids = event.get('transaction_ids', [])
        company_number = event.get('company_number')
        user_id = event.get('user_id')
        batch_index = event.get('batch_index', 0)
        
        if not transaction_ids:
            raise ValueError('No transaction IDs provided in batch')
        
        log_with_timestamp(f"Processing batch {batch_index} with {len(transaction_ids)} transactions")
        
        # Process the batch using existing helper function
        message_body = {
            'transaction_ids': transaction_ids,
            'company_number': company_number,
            'user_id': user_id
        }
        
        batch_result = process_transaction_batch(message_body)
        
        log_with_timestamp(
            f"Batch {batch_index} complete: {batch_result['successful_count']} succeeded, "
            f"{batch_result['failed_count']} failed"
        )
        
        # Return result for Step Functions
        return {
            'success': batch_result['successful_count'] > 0,
            'batch_index': batch_index,
            'processed': batch_result['successful_count'],
            'failed': batch_result['failed_count'],
            'failed_transaction_ids': batch_result.get('failed_transaction_ids', []),
            'total': len(transaction_ids)
        }
        
    except Exception as e:
        log_with_timestamp(f"Error in lambda handler: {str(e)}")
        import traceback
        log_with_timestamp(f"Full traceback: {traceback.format_exc()}")
        
        # Return error result for Step Functions retry logic
        raise  # Re-raise to trigger Step Functions retry

