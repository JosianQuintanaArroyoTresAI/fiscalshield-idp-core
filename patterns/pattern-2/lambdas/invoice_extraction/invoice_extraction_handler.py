# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Invoice Extraction Lambda
Processes invoice sections and writes individual invoice records to DynamoDB
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
from typing import Dict, List, Any, Set
import logging
from botocore.exceptions import ClientError, ParamValidationError, ReadTimeoutError

# Set up logger
logger = logging.getLogger(__name__)


# ==============================================================================
# ChunkedInvoiceExtractor Class (Inlined for Lambda deployment)
# ==============================================================================

class ChunkProcessingError(Exception):
    """Raised when a chunk fails to process."""


class ChunkedInvoiceExtractor:
    """Handles chunked extraction and deduplication of invoices from large documents."""
    
    def __init__(self, chunk_size: int = 60000, overlap_size: int = 5000):
        self.chunk_size = chunk_size
        self.overlap_size = overlap_size
    
    def extract_page_numbers(self, text: str) -> List[int]:
        page_pattern = r'\[PAGE:(\d+)\]'
        matches = re.findall(page_pattern, text)
        pages = sorted(set(int(page_num) for page_num in matches))
        return pages if pages else [1]
    
    def create_chunks_with_overlap(self, text: str) -> List[Dict[str, Any]]:
        chunks = []
        start = 0
        chunk_index = 0
        
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            chunk_text = text[start:end]
            pages = self.extract_page_numbers(chunk_text)
            
            chunk_data = {
                'chunk': chunk_text,
                'start': start,
                'end': end,
                'pages': pages,
                'chunk_index': chunk_index
            }
            
            chunks.append(chunk_data)
            
            if end < len(text):
                start = end - self.overlap_size
            else:
                break
            
            chunk_index += 1
        
        return chunks
    
    def contains_different_people(self, desc1: str, desc2: str) -> bool:
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails1 = set(re.findall(email_pattern, desc1))
        emails2 = set(re.findall(email_pattern, desc2))
        
        if emails1 and emails2 and emails1.isdisjoint(emails2):
            return True
        
        name_pattern = r'\b[A-Z][a-z]+ [A-Z][a-z]+\b'
        names1 = set(re.findall(name_pattern, desc1))
        names2 = set(re.findall(name_pattern, desc2))
        
        if names1 and names2 and len(names1) == 1 and len(names2) == 1 and names1.isdisjoint(names2):
            return True
        
        return False
    
    def are_invoices_similar_content(self, invoice1: Dict, invoice2: Dict) -> bool:
        vendor1 = str(invoice1.get('supplier_name', '') or invoice1.get('vendor_name', '')).strip().lower()
        vendor2 = str(invoice2.get('supplier_name', '') or invoice2.get('vendor_name', '')).strip().lower()
        vendor_match = vendor1 == vendor2 and vendor1 != ''
        
        try:
            amount1 = float(invoice1.get('total_amount', 0) or 0)
            amount2 = float(invoice2.get('total_amount', 0) or 0)
            amount_match = abs(amount1 - amount2) < 0.01
        except (ValueError, TypeError):
            amount_match = False
        
        date1 = str(invoice1.get('invoice_date', '')).strip()
        date2 = str(invoice2.get('invoice_date', '')).strip()
        date_match = date1 == date2 and date1 != ''
        
        if vendor_match and amount_match and date_match:
            desc1 = str(invoice1.get('description', '')).lower()
            desc2 = str(invoice2.get('description', '')).lower()
            
            if self.contains_different_people(desc1, desc2):
                return False
            
            return True
        
        return False
    
    def are_invoices_duplicate_by_pages(self, invoice1: Dict, invoice2: Dict) -> bool:
        pages1 = set(invoice1.get('pages', []))
        pages2 = set(invoice2.get('pages', []))
        
        if not pages1 or not pages2:
            return self.are_invoices_similar_content(invoice1, invoice2)
        
        overlap = pages1.intersection(pages2)
        
        if len(overlap) > 0:
            return self.are_invoices_similar_content(invoice1, invoice2)
        
        return False
    
    def is_more_complete_invoice(self, invoice1: Dict, invoice2: Dict) -> bool:
        score1 = sum([
            1 if (invoice1.get('supplier_name') or invoice1.get('vendor_name', '')).strip() else 0,
            1 if invoice1.get('reference_number', '').strip() else 0,
            1 if invoice1.get('description', '').strip() else 0,
            1 if invoice1.get('supplier_address', '').strip() else 0,
            1 if invoice1.get('invoice_number', '').strip() else 0,
        ])
        
        score2 = sum([
            1 if (invoice2.get('supplier_name') or invoice2.get('vendor_name', '')).strip() else 0,
            1 if invoice2.get('reference_number', '').strip() else 0,
            1 if invoice2.get('description', '').strip() else 0,
            1 if invoice2.get('supplier_address', '').strip() else 0,
            1 if invoice2.get('invoice_number', '').strip() else 0,
        ])
        
        return score1 > score2
    
    def deduplicate_invoices(self, invoices: List[Dict]) -> List[Dict]:
        if len(invoices) <= 1:
            return invoices
        
        processed_invoices = []
        
        for current_invoice in invoices:
            is_duplicate = False
            
            for existing_invoice in processed_invoices:
                if self.are_invoices_duplicate_by_pages(current_invoice, existing_invoice):
                    if self.is_more_complete_invoice(current_invoice, existing_invoice):
                        processed_invoices = [
                            inv for inv in processed_invoices 
                            if id(inv) != id(existing_invoice)
                        ]
                        processed_invoices.append(current_invoice)
                    
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                processed_invoices.append(current_invoice)
        
        return processed_invoices
    
    def deduplicate_chunk_boundaries(self, invoices: List[Dict], chunks: List[Dict]) -> List[Dict]:
        """
        OPTIMIZED deduplication for chunked extraction.
        
        Key insights:
        1. Invoices within same chunk cannot be duplicates (no overlap within chunk)
        2. Invoices on different pages cannot be duplicates
        3. Only check invoices at chunk boundaries (overlap zones)
        
        This reduces complexity from O(n²) to O(k*m) where:
        - k = number of chunk boundaries
        - m = average invoices per overlap zone (typically 1-3)
        """
        if len(invoices) <= 1:
            return invoices
        
        # Group invoices by chunk
        invoices_by_chunk = {}
        for invoice in invoices:
            chunk_idx = invoice.get('chunk_index', 0)
            if chunk_idx not in invoices_by_chunk:
                invoices_by_chunk[chunk_idx] = []
            invoices_by_chunk[chunk_idx].append(invoice)
        
        # Start with all invoices from first chunk (no duplicates possible within chunk)
        if 0 not in invoices_by_chunk:
            return []
        
        result = list(invoices_by_chunk[0])
        
        # Process each subsequent chunk
        for chunk_idx in range(1, len(chunks)):
            if chunk_idx not in invoices_by_chunk:
                continue
            
            current_chunk_invoices = invoices_by_chunk[chunk_idx]
            
            # Only compare with invoices from previous chunk that share pages
            # (invoices in overlap zone)
            previous_chunk_invoices = invoices_by_chunk.get(chunk_idx - 1, [])
            
            for current_invoice in current_chunk_invoices:
                current_pages = set(current_invoice.get('pages', []))
                is_duplicate = False
                
                # Only check against invoices from previous chunk with overlapping pages
                for prev_invoice in previous_chunk_invoices:
                    prev_pages = set(prev_invoice.get('pages', []))
                    
                    # If no page overlap, cannot be duplicates
                    if not current_pages.intersection(prev_pages):
                        continue
                    
                    # Check if they're duplicates
                    if self.are_invoices_duplicate_by_pages(current_invoice, prev_invoice):
                        if self.is_more_complete_invoice(current_invoice, prev_invoice):
                            # Replace previous invoice with more complete one
                            result = [inv for inv in result if id(inv) != id(prev_invoice)]
                            result.append(current_invoice)
                        # Either way, it's a duplicate
                        is_duplicate = True
                        break
                
                # If not a duplicate, add to results
                if not is_duplicate:
                    result.append(current_invoice)
        
        return result


# ==============================================================================
# Environment variables
# ==============================================================================

LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
EXTRACTION_RESULTS_TABLE = os.environ.get('EXTRACTION_RESULTS_TABLE')
CONFIGURATION_TABLE = os.environ.get('CONFIGURATION_TABLE')
TRACKING_TABLE = os.environ.get('TRACKING_TABLE')  # For chunk progress tracking
BEDROCK_MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-3-7-sonnet-20250219-v1:0')
AWS_REGION = os.environ.get('AWS_REGION', 'eu-central-1')
BEDROCK_INFERENCE_PROFILE_ARN = os.environ.get('BEDROCK_INFERENCE_PROFILE_ARN', '').strip()
FALLBACK_BEDROCK_MODEL_ID = os.environ.get('FALLBACK_BEDROCK_MODEL_ID', '').strip()
FALLBACK_BEDROCK_INFERENCE_PROFILE_ARN = os.environ.get('FALLBACK_BEDROCK_INFERENCE_PROFILE_ARN', '').strip()
BEDROCK_MAX_RETRIES = int(os.environ.get('BEDROCK_MAX_RETRIES', '6'))
BEDROCK_BACKOFF_BASE_SECONDS = float(os.environ.get('BEDROCK_BACKOFF_BASE_SECONDS', '2.0'))
BEDROCK_BACKOFF_MAX_SECONDS = float(os.environ.get('BEDROCK_BACKOFF_MAX_SECONDS', '45.0'))
BEDROCK_FALLBACK_AFTER_ATTEMPT = int(os.environ.get('BEDROCK_FALLBACK_AFTER_ATTEMPT', '3'))


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

# Chunking configuration (Phase 3)
USE_CHUNKED_EXTRACTION = os.environ.get('USE_CHUNKED_EXTRACTION', 'false').lower() == 'true'
CHUNK_SIZE = int(os.environ.get('CHUNK_SIZE', '60000'))  # Optimized: ~15k tokens (vs 15k chars = 3.75k tokens)
OVERLAP_SIZE = int(os.environ.get('OVERLAP_SIZE', '5000'))  # Covers 3-page invoices with minimal duplicates
USE_PROMPT_CACHING = os.environ.get('USE_PROMPT_CACHING', 'true').lower() == 'true'  # 60-70% cost savings

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
bedrock_runtime = boto3.client('bedrock-runtime', region_name=AWS_REGION)
extraction_table = dynamodb.Table(EXTRACTION_RESULTS_TABLE)
config_table = dynamodb.Table(CONFIGURATION_TABLE)
tracking_table = dynamodb.Table(TRACKING_TABLE) if TRACKING_TABLE else None


THROTTLING_ERROR_CODES = {"ThrottlingException", "TooManyRequestsException"}


def log_with_timestamp(message: str):
    """Helper function to log messages with timestamps"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    print(f"[{timestamp}] {message}")


def update_chunk_status(
    document_id: str,
    section_id: str,
    chunk_index: int,
    status: str,
    invoice_count: int = 0,
    error_message: str = None,
    model_used: str = None
) -> None:
    """
    Update chunk processing status in TrackingTable
    
    Status values: PENDING | PROCESSING | COMPLETED | FAILED
    
    Args:
        model_used: ID of Bedrock model that processed this chunk (for quality evaluation)
    """
    if not tracking_table:
        log_with_timestamp("⚠️ TrackingTable not configured, skipping chunk status update")
        return
    
    try:
        current_timestamp = int(time.time())
        
        item = {
            'PK': f"document#{document_id}#section#{section_id}",
            'SK': f"chunk#{chunk_index}",
            'chunk_status': status,
            'chunk_index': chunk_index,
            'invoice_count': invoice_count,
            'updated_at': current_timestamp,
            'document_id': document_id,
            'section_id': section_id
        }
        
        if status == 'COMPLETED':
            item['completed_at'] = current_timestamp
        
        if error_message:
            item['error_message'] = error_message[:1000]  # Limit error message size
        
        if model_used:
            item['model_used'] = model_used  # Track which model processed this chunk
        
        tracking_table.put_item(Item=item)
        log_with_timestamp(f"✅ Updated chunk {chunk_index} status: {status}")
        
    except Exception as e:
        log_with_timestamp(f"⚠️ Failed to update chunk status in TrackingTable: {str(e)}")


def get_chunk_status(document_id: str, section_id: str, chunk_index: int) -> str:
    """
    Get chunk processing status from TrackingTable
    
    Returns: PENDING | PROCESSING | COMPLETED | FAILED | None (not found)
    """
    if not tracking_table:
        return None
    
    try:
        response = tracking_table.get_item(
            Key={
                'PK': f"document#{document_id}#section#{section_id}",
                'SK': f"chunk#{chunk_index}"
            }
        )
        
        if 'Item' in response:
            return response['Item'].get('chunk_status')
        
        return None
        
    except Exception as e:
        log_with_timestamp(f"⚠️ Failed to get chunk status from TrackingTable: {str(e)}")
        return None


def are_all_chunks_complete(document_id: str, section_id: str, total_chunks: int) -> bool:
    """
    Check if all chunks for a document section have been completed.
    
    Args:
        document_id: Document identifier
        section_id: Section identifier
        total_chunks: Total number of chunks for this section
    
    Returns:
        True if all chunks are COMPLETED, False otherwise
    """
    if not tracking_table:
        log_with_timestamp("⚠️ TrackingTable not configured, cannot check completion status")
        return False
    
    try:
        completed_count = 0
        
        for chunk_idx in range(total_chunks):
            status = get_chunk_status(document_id, section_id, chunk_idx)
            
            if status == 'COMPLETED':
                completed_count += 1
            elif status == 'FAILED':
                log_with_timestamp(f"⚠️ Chunk {chunk_idx} is marked as FAILED")
                return False
            else:
                # PENDING, PROCESSING, or not found
                log_with_timestamp(f"⏸️  Chunk {chunk_idx} not yet complete (status: {status})")
                return False
        
        # All chunks are COMPLETED
        log_with_timestamp(f"✅ All {completed_count}/{total_chunks} chunks completed!")
        return True
        
    except Exception as e:
        log_with_timestamp(f"❌ Error checking chunk completion status: {str(e)}")
        return False


def deduplicate_invoices_in_dynamodb(document_id: str, section_id: str, user_id: str) -> int:
    """
    Deduplicate invoices for a completed section by querying DynamoDB,
    identifying duplicates, and deleting duplicate records.
    
    This runs AFTER all chunks are complete to handle duplicates from overlapping chunks.
    
    Deduplication Strategy:
    - Two invoices are duplicates if they have the SAME identity:
      (supplier_name, invoice_number, invoice_date, total_amount)
    - Deduplication decisions:
      1. If ALL identity fields match → TRUE duplicate, deduplicate regardless of chunk distance
         (Invoice numbers must be unique per supplier/date/amount combination)
      2. If chunks are consecutive (within 1) → Likely overlap region duplicate
      3. Keeps records if same invoice# but DIFFERENT supplier/amount/date
         (Protects against extraction errors where wrong field used as invoice#)
    - When choosing which duplicate to keep:
      1. Keep the one with MORE complete fields (non-empty values)
      2. If both equally complete, keep the EARLIER one (lower chunk_index, earlier timestamp)
    
    Args:
        document_id: Document identifier
        section_id: Section identifier  
        user_id: User identifier for querying
    
    Returns:
        Number of duplicate invoices removed
    """
    if not extraction_table:
        log_with_timestamp("⚠️ ExtractionResultsTable not configured, skipping deduplication")
        return 0
    
    try:
        log_with_timestamp("🔍 Starting intelligent deduplication with chunk awareness...")
        
        # Query all invoices for this document section
        pk = f"user#{user_id}#doc#{document_id}"
        sk_prefix = f"type#INVOICE#section#{section_id}#"
        
        response = extraction_table.query(
            KeyConditionExpression='PK = :pk AND begins_with(SK, :sk)',
            ExpressionAttributeValues={
                ':pk': pk,
                ':sk': sk_prefix
            }
        )
        
        invoices = response.get('Items', [])
        log_with_timestamp(f"📊 Found {len(invoices)} invoices to check for duplicates")
        
        if len(invoices) <= 1:
            log_with_timestamp("✅ No deduplication needed (only 1 invoice)")
            return 0
        
        # Convert DynamoDB items to invoice dictionaries with chunk metadata
        invoice_items = []
        for item in invoices:
            chunk_index = item.get('ChunkIndex')
            # Convert Decimal to int if present
            if chunk_index is not None:
                chunk_index = int(chunk_index)
                
            invoice_dict = {
                'supplier_name': item.get('SupplierName', ''),
                'vendor_name': item.get('VendorName', ''),
                'total_amount': float(item.get('TotalAmount', 0)) if item.get('TotalAmount') else 0,
                'invoice_date': item.get('InvoiceDate', ''),
                'invoice_number': item.get('InvoiceNumber', ''),
                'reference_number': item.get('ReferenceNumber', ''),
                'description': item.get('Description', ''),
                'supplier_address': item.get('SupplierAddress', ''),
                'source_page': int(item.get('SourcePage', 0)) if item.get('SourcePage') else 0,
                'extraction_confidence': item.get('ExtractionConfidence', 'high'),  # Track extraction quality
                # Chunk metadata
                'chunk_index': chunk_index,
                'chunk_pages': item.get('ChunkPages', []),
                'created_at': int(item.get('CreatedAt', 0)) if item.get('CreatedAt') else 0,
                # Keep DynamoDB keys for deletion
                '_dynamodb_pk': item['PK'],
                '_dynamodb_sk': item['SK'],
                '_full_item': item  # Keep for completeness comparison
            }
            invoice_items.append(invoice_dict)
        
        # Group potential duplicates by core identity
        from collections import defaultdict
        duplicate_groups = defaultdict(list)
        
        for inv in invoice_items:
            # Create identity key from core fields
            identity_key = (
                inv['supplier_name'].lower().strip(),
                inv['invoice_number'].strip(),
                inv['invoice_date'],
                round(inv['total_amount'], 2)  # Round to avoid float precision issues
            )
            duplicate_groups[identity_key].append(inv)
        
        # Process each group to find duplicates
        duplicates_to_delete = []
        
        for identity_key, group in duplicate_groups.items():
            if len(group) <= 1:
                continue  # No duplicates in this group
            
            log_with_timestamp(f"🔍 Found {len(group)} potential duplicates: {identity_key[0]} - {identity_key[2]} - {identity_key[3]}")
            
            # Check if duplicates are from consecutive chunks (overlap region)
            chunk_indices = [inv['chunk_index'] for inv in group if inv['chunk_index'] is not None]
            source_pages = [inv['source_page'] for inv in group if inv.get('source_page')]
            
            # Decision logic for deduplication:
            # 1. If ALL identity fields match (supplier, invoice#, date, amount), they're TRUE duplicates
            #    → Deduplicate regardless of chunk distance (invoice numbers must be unique)
            # 2. If chunks are consecutive (within 1), likely from overlap region
            #    → Deduplicate (handles cases where invoice# might be missing/incomplete)
            # 3. If chunks far apart AND identity differs, keep all
            #    → Protects against extraction errors (same invoice# but different invoice)
            
            should_deduplicate = False
            reason = ""
            
            if chunk_indices:
                min_chunk = min(chunk_indices)
                max_chunk = max(chunk_indices)
                
                # Case 1: Chunks are consecutive (overlap region)
                if max_chunk - min_chunk <= 1:
                    should_deduplicate = True
                    reason = f"consecutive chunks ({min_chunk} to {max_chunk})"
                # Case 2: Chunks far apart BUT all identity fields match exactly
                # This means same supplier+number+date+amount = TRUE duplicate (extraction quality issue)
                else:
                    # Identity already matches (that's how they're grouped), so this is a true duplicate
                    # appearing multiple times in different parts of document
                    should_deduplicate = True
                    reason = f"exact match across non-consecutive chunks ({min_chunk} to {max_chunk})"
                    log_with_timestamp(f"   ⚠️  Same invoice appearing in distant chunks - likely extraction artifact")
            else:
                # No chunk info, deduplicate based on identity match
                should_deduplicate = True
                reason = "matching identity fields (no chunk info)"
            
            if not should_deduplicate:
                log_with_timestamp(f"   ℹ️  Keeping all - {reason}")
                continue
            
            log_with_timestamp(f"   ✅ Deduplicating: {reason}")
            
            # Enhanced heuristic for consecutive chunks: Check if SourcePage positions suggest overlap region
            if chunk_indices and max(chunk_indices) - min(chunk_indices) == 1:
                # Only apply enhanced heuristic for consecutive chunks
                if len(group) == 2 and len(chunk_indices) == 2 and len(source_pages) == 2:
                    min_chunk_val = min(chunk_indices)
                    max_chunk_val = max(chunk_indices)
                    # Get invoices from each chunk
                    inv_chunk_min = [inv for inv in group if inv['chunk_index'] == min_chunk_val][0]
                    inv_chunk_max = [inv for inv in group if inv['chunk_index'] == max_chunk_val][0]
                    
                    sp_min_chunk = inv_chunk_min.get('source_page', 0)
                    sp_max_chunk = inv_chunk_max.get('source_page', 0)
                    
                    # Pattern: chunk N has high SourcePage (near end) AND chunk N+1 has low SourcePage (near start)
                    # This suggests they're in the overlap region (5k chars = ~2-3 invoices)
                    is_overlap_pattern = (sp_min_chunk >= 8 and sp_max_chunk <= 3)  # Last few + First few
                    
                    if is_overlap_pattern:
                        log_with_timestamp(
                            f"   📍 SourcePages {sp_min_chunk},{sp_max_chunk} suggest overlap region (HIGH confidence)"
                        )
                    else:
                        log_with_timestamp(
                            f"   📍 SourcePages {sp_min_chunk},{sp_max_chunk}"
                        )
            
            # Sort by completeness (most complete first), then by chunk_index (earlier first), then by timestamp
            def count_non_empty_fields(inv):
                """Count how many fields have meaningful values, with confidence bonus"""
                count = 0
                if inv['supplier_name'] and inv['supplier_name'].strip(): count += 1
                if inv['invoice_number'] and inv['invoice_number'].strip(): count += 1
                if inv['invoice_date'] and inv['invoice_date'].strip(): count += 1
                if inv['reference_number'] and inv['reference_number'].strip(): count += 1
                if inv['description'] and inv['description'].strip(): count += 1
                if inv['supplier_address'] and inv['supplier_address'].strip(): count += 1
                if inv['vendor_name'] and inv['vendor_name'].strip(): count += 1
                if inv['total_amount'] > 0: count += 1
                
                # Add confidence bonus for prioritization
                confidence = inv.get('extraction_confidence', 'high')
                if confidence == 'high': count += 2  # High confidence gets bonus
                elif confidence == 'medium': count += 1  # Medium confidence gets smaller bonus
                # Low confidence gets no bonus
                
                return count
            
            sorted_group = sorted(
                group,
                key=lambda inv: (
                    -count_non_empty_fields(inv),  # More complete first (negative for descending)
                    inv['chunk_index'] if inv['chunk_index'] is not None else 999,  # Earlier chunk first
                    inv['created_at']  # Earlier timestamp first
                )
            )
            
            # Keep the first one (most complete, earliest), mark rest as duplicates
            keeper = sorted_group[0]
            to_delete = sorted_group[1:]
            
            completeness_keeper = count_non_empty_fields(keeper)
            confidence_keeper = keeper.get('extraction_confidence', 'high')
            log_with_timestamp(
                f"   ✅ Keeping: chunk={keeper['chunk_index']}, "
                f"completeness={completeness_keeper} fields, confidence={confidence_keeper}"
            )
            
            for dup in to_delete:
                completeness_dup = count_non_empty_fields(dup)
                confidence_dup = dup.get('extraction_confidence', 'high')
                log_with_timestamp(
                    f"   🗑️  Deleting: chunk={dup['chunk_index']}, "
                    f"completeness={completeness_dup} fields, confidence={confidence_dup}"
                )
                duplicates_to_delete.append(dup)
        
        # Delete duplicate records from DynamoDB
        deleted_count = 0
        for duplicate in duplicates_to_delete:
            try:
                extraction_table.delete_item(
                    Key={
                        'PK': duplicate['_dynamodb_pk'],
                        'SK': duplicate['_dynamodb_sk']
                    }
                )
                deleted_count += 1
            except Exception as e:
                log_with_timestamp(f"⚠️ Failed to delete duplicate {duplicate['_dynamodb_sk']}: {str(e)}")
        
        log_with_timestamp(
            f"✅ Deduplication complete: {len(invoices)} → {len(invoices) - deleted_count} "
            f"(removed {deleted_count} duplicates)"
        )
        
        return deleted_count
        
    except Exception as e:
        log_with_timestamp(f"❌ Error during deduplication: {str(e)}")
        import traceback
        log_with_timestamp(f"📋 Traceback: {traceback.format_exc()}")
        return 0


def _invoke_bedrock_runtime(model_id: str, profile_arn: str, body_json: str):
    """Invoke Bedrock runtime, handling inference profile compatibility.
    
    When using inference profiles, the profile ARN should be passed as the modelId,
    not as a separate inferenceProfileArn parameter.
    """
    # Use inference profile ARN as modelId if available, otherwise use the model ID
    effective_model_id = profile_arn if profile_arn else model_id
    
    if profile_arn:
        log_with_timestamp(f"🌍 Using Bedrock inference profile: {profile_arn}")
    else:
        log_with_timestamp(f"🌍 Using Bedrock model ID: {model_id}")

    invoke_kwargs = {
        'modelId': effective_model_id,
        'body': body_json
    }

    try:
        return bedrock_runtime.invoke_model(**invoke_kwargs)
    except ClientError as client_error:
        error_code = client_error.response.get('Error', {}).get('Code', '')
        # If inference profile fails, fall back to direct model ID
        if profile_arn and error_code in ['ValidationException', 'ResourceNotFoundException']:
            log_with_timestamp(f"⚠️ Inference profile failed ({error_code}), retrying with direct modelId")
            return bedrock_runtime.invoke_model(modelId=model_id, body=body_json)
        raise


def get_invoice_extraction_prompt() -> str:
    """
    Fetch invoice extraction prompt from ConfigurationTable
    This allows frontend users to edit the prompt without redeploying
    """
    try:
        response = config_table.get_item(
            Key={'Configuration': 'INVOICE_EXTRACTION_PROMPT'}
        )

        if 'Item' in response and 'PromptTemplate' in response['Item']:
            log_with_timestamp("✅ Retrieved custom invoice prompt from ConfigurationTable")
            return response['Item']['PromptTemplate']
        else:
            log_with_timestamp("⚠️ No custom prompt found, using default")
            return get_default_invoice_prompt()
    except Exception as e:
        log_with_timestamp(f"❌ Error fetching prompt from ConfigurationTable: {e}")
        return get_default_invoice_prompt()


def get_default_invoice_prompt() -> str:
    """
    Enhanced invoice extraction prompt with UK invoice numbering standards
    Includes VAT number disambiguation, incomplete invoice detection, and confidence tracking
    """
    return """DOCUMENT CONTEXT:
This text has been intelligently chunked to contain COMPLETE invoices.
- Each chunk should contain 1-3 full invoices
- Invoice boundaries have been detected (starts with "To:" or supplier name, ends with "AMOUNT DUE")
- If an invoice appears incomplete (missing header OR missing total), mark with low confidence

However, occasionally an invoice MAY be split. If you detect this:
→ Extract what you can from the partial invoice
→ Set <extraction_confidence>low</extraction_confidence>
→ The system will attempt reconciliation with adjacent chunks

CRITICAL: This text may contain MULTIPLE INVOICES. You must find and extract ALL of them.

TASK: Scan the ENTIRE text and extract EVERY invoice you find, even if there are many.

PAGE NUMBER EXTRACTION:
- Look for page indicators or invoice boundaries in the text
- For each invoice, determine which page it appears on
- Include <source_page>X</source_page> in each invoice block
- If page number unclear, use sequential numbering starting from 1

UK INVOICE LAYOUT PATTERNS (Recognition Hints):
📄 Typical UK invoice structure:
   TOP SECTION (first 30% of invoice):
   - "Invoice Number" or "Reference Number" labels
   - Invoice date
   - Supplier details (with VAT number in this section)
   
   MIDDLE SECTION:
   - "Bill To" or "To:" with customer details
   - Line items and descriptions
   
   BOTTOM SECTION (last 20%):
   - Subtotal, VAT amount, Total
   - "AMOUNT DUE" or "TOTAL GBP"
   - Payment terms
   - Often ends with: "This is not a tax invoice"

🔍 Invoice boundaries:
   - New invoice typically starts with: "To:", supplier name, or page break marker
   - Invoice ends with: "AMOUNT DUE", payment terms, or distinctive footer
   - Look for pattern: [Invoice details] → [Line items] → [Totals] → [Next invoice starts]

VENDOR NAME EXTRACTION RULES:
- Look for company names, business names, or service providers
- For expense claims: Use the business where money was spent (e.g., "Tesco", "Microsoft", "Train Company")
- For employee expenses: Use the merchant/vendor name, NOT the employee name
- If unclear, use descriptive vendor name (e.g., "Restaurant", "Transport Service", "Hotel")
- NEVER leave supplier_name empty - always provide something meaningful

INVOICE NUMBER vs REFERENCE NUMBER (UK HMRC Standards):
🔴 INVOICE NUMBER (invoice_number field):
   - Look for labels: "Invoice No", "Invoice Number", "Tax Invoice No", "Invoice #"
   - Usually SHORT and SEQUENTIAL (e.g., INV-001, 2024-123, 12345)
   - Located near the top of invoice, often with the date
   - UNIQUE to this specific invoice
   - Required by UK HMRC for VAT invoices
   - If NO invoice number found, leave EMPTY (do not use other numbers)
   
🟡 REFERENCE NUMBER (reference_number field):
   - Look for labels: "Reference", "PO Number", "Order Ref", "Job No", "Customer Ref"
   - This is the BUYER'S reference (purchase order, job code, etc.)
   - Optional field for tracking purposes
   
❌ DO NOT USE AS INVOICE NUMBER:
   - VAT Registration Numbers - CRITICAL TO AVOID:
     * UK format: GB followed by 9 digits (e.g., GB332734807, GB721741064)
     * UK format: 9 digits only (e.g., 201630957, 302792712)
     * UK format: GB followed by 12 digits (e.g., GB523127284, GB123456789012)
     * Always labeled "VAT Number:", "VAT No:", "VAT Registration:", or "VAT Reg No:"
     * Located in supplier details section, NOT near "Invoice Number" label
     * These are company tax IDs, NOT invoice numbers
   - Company Registration Numbers (12345678, SC123456) - these are Companies House IDs
   - Customer Account Numbers or Client IDs
   - Form template IDs or document type codes (e.g., "Tofes 17")
   - Generic labels like "Expense Claims" or "Invoice" without unique numbers
   - Date-based codes that look like invoice numbers (e.g., 2006547140 - Land Registry date codes)
   - Phone numbers (07xxx xxxxxx format)
   - Postcodes (e.g., GU52 8BF, EC2Y 5EB)

📋 UK INVOICE NUMBER EXAMPLES:

✅ CORRECT invoice_number extraction:
   Text: "Invoice Number: INV-60778" → invoice_number="INV-60778"
   Text: "Reference Number: 45485" → invoice_number="45485"
   Text: "Invoice: PP-13189876v1" → invoice_number="PP-13189876v1"
   Text: "Invoice No 1919" → invoice_number="1919"
   Text: "Ref: YEX49000800111" → invoice_number="YEX49000800111"
   Text: "Invoice Number: INV-20153" → invoice_number="INV-20153"
   Text: "Reference Number: 2501751" → invoice_number="2501751"

❌ WRONG extractions (DO NOT USE):
   Text: "VAT Number: GB332734807" → ❌ NOT invoice_number (this is a VAT number)
   Text: "VAT Number: 201630957" → ❌ NOT invoice_number (this is a VAT number)
   Text: "VAT Number: GB721741064" → ❌ NOT invoice_number (this is a VAT number)
   Text: "Expense Claims" (with no unique number) → invoice_number="" (leave empty)
   Text: "Invoice Date: 30 Jun 2024" → ❌ NOT invoice_number (this is a date)
   Text: "Mobile: 07376 129933" → ❌ NOT invoice_number (this is a phone number)

🔍 AMBIGUOUS CASES:
   If you see ONLY "Reference Number: 12345" (no "Invoice Number" label):
   → Use reference_number="12345", leave invoice_number=""
   
   If you see both:
   Text: "Invoice Number: INV-001\nReference Number: PO-5678"
   → invoice_number="INV-001", reference_number="PO-5678"
   
   If you see a 9-digit number near VAT section:
   Text: "VAT Number: 201630957\nInvoice Date: 30 Jun 2024"
   → invoice_number="" (the 9-digit number is VAT, not invoice)
   
   If invoice number is unclear or ambiguous:
   → invoice_number="", extraction_confidence="low"

INCOMPLETE INVOICE DETECTION:
⚠️ If the text appears to be a partial/incomplete invoice:
   - Missing clear "Invoice Number" or "Reference Number" label
   - Text starts mid-sentence or ends abruptly
   - Supplier name or total amount not clearly visible
   - Only seeing line items without header or footer
   → Mark as: <extraction_confidence>low</extraction_confidence>
   → Still extract what you can, but flag uncertainty
   → The system will attempt to reconstruct from adjacent chunks

CONFIDENCE LEVELS:
- <extraction_confidence>high</extraction_confidence>: All key fields present and clearly labeled
- <extraction_confidence>medium</extraction_confidence>: Most fields present, some minor ambiguity
- <extraction_confidence>low</extraction_confidence>: Missing key fields, text truncated, or ambiguous numbers

Use "low" confidence when:
  * Invoice number unclear, missing its label, or might be a VAT number
  * Might be mixing data from multiple invoices
  * Text appears truncated or incomplete
  * Supplier name or total amount not clearly identifiable

MULTIPLE INVOICE HANDLING:
- If you find 5 invoices → output 5 separate <invoice> blocks
- If you find 1 invoice → output 1 <invoice> block
- If you find 10 invoices → output 10 separate <invoice> blocks
- NEVER skip invoices because there are "too many"
- NEVER merge multiple invoices into one block
- Extract them in the order they appear in the text

REQUIRED FIELDS FOR EACH INVOICE:
- extraction_confidence: high, medium, or low (see guidelines above)
- supplier_name: Company/vendor name (ALWAYS required, never empty)
- total_amount: Final total (look for "Total", "Amount Due", "Balance Due", "TOTAL GBP")
- invoice_date: Date of invoice (DD/MM/YYYY or YYYY-MM-DD format)
- invoice_number: ONLY the actual invoice number (see rules above), leave EMPTY if not found
- reference_number: Purchase order or customer reference (optional)
- source_page: Page number where this invoice appears

CRITICAL: Extract EVERY invoice in the text. Do not stop after finding the first one.

Required XML format (repeat <invoice> block for each invoice found):
<invoices>
<invoice>
<extraction_confidence>high</extraction_confidence>
<invoice_type>SUPPLIER_INVOICE</invoice_type>
<invoice_number>INV-60778</invoice_number>
<reference_number>PO-5678</reference_number>
<invoice_date>2024-06-30</invoice_date>
<due_date>2024-07-15</due_date>
<supplier_name>Edozo</supplier_name>
<total_amount>296.74</total_amount>
<currency>GBP</currency>
<vat_amount>49.46</vat_amount>
<net_amount>247.28</net_amount>
<description>Edozo Usage - June 2024</description>
<supplier_address>6th Floor, 1 London Wall, London, Middlesex, EC2Y 5EB</supplier_address>
<payment_terms>Due 15 Jul 2024</payment_terms>
<source_page>1</source_page>
</invoice>
<invoice>
<extraction_confidence>high</extraction_confidence>
<invoice_type>SUPPLIER_INVOICE</invoice_type>
<invoice_number>INV-0144</invoice_number>
<reference_number></reference_number>
<invoice_date>2024-06-30</invoice_date>
<due_date>2024-07-30</due_date>
<supplier_name>Ceri Evans Marketing & Communications Ltd</supplier_name>
<total_amount>5568.00</total_amount>
<currency>GBP</currency>
<vat_amount>927.99</vat_amount>
<net_amount>4640.01</net_amount>
<description>General Marketing Support June 2024</description>
<supplier_address>21 Greenshields Road, Bedford, MK40 3TS</supplier_address>
<payment_terms>Due 30 Jul 2024</payment_terms>
<source_page>2</source_page>
</invoice>
</invoices>

Text to extract from:
{section_text}"""


def invoke_bedrock(prompt: str, use_caching: bool = None) -> tuple[str, str]:
    """
    Invoke Bedrock Claude model for invoice extraction
    
    Args:
        prompt: Full prompt with instructions and text
        use_caching: Enable prompt caching (saves 60-70% on multi-chunk docs)
                     Defaults to USE_PROMPT_CACHING env var
    
    Returns:
        Tuple of (extracted_xml, model_used) where model_used is the ID of the model that succeeded
    """
    if use_caching is None:
        use_caching = USE_PROMPT_CACHING
    
    try:
        # Split prompt into cacheable instructions and variable text
        # Assumes prompt format: "<instructions>Text to extract from:\n{text}"
        parts = prompt.split("Text to extract from:\n", 1)
        
        if use_caching and len(parts) == 2:
            # Use prompt caching: Cache the instructions, vary the text
            instructions = parts[0] + "Text to extract from:\n"
            text_content = parts[1]
            
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 16000,  # Increased for large documents
                "system": [
                    {
                        "type": "text",
                        "text": instructions,
                        "cache_control": {"type": "ephemeral"}  # Cache the prompt template
                    }
                ],
                "messages": [
                    {"role": "user", "content": text_content}
                ]
            }
            log_with_timestamp("📌 Using prompt caching (60-70% cost savings on repeated calls)")
        else:
            # Standard invocation (no caching)
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 16000,
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            }

        body_json = json.dumps(body)

        fallback_trigger = max(1, min(BEDROCK_FALLBACK_AFTER_ATTEMPT, BEDROCK_MAX_RETRIES))
        model_chain = BEDROCK_MODEL_CHAIN
        model_attempt_counters = [0] * len(model_chain)
        current_model_index = 0
        total_attempts = 0
        max_total_attempts = max(1, BEDROCK_MAX_RETRIES) * len(model_chain)
        chain_logged = False

        def describe_model(entry: Dict[str, str]) -> str:
            profile_arn = (entry.get('inference_profile_arn') or '').strip()
            if profile_arn:
                profile_suffix = profile_arn.split('/')[-1]
                return f"{entry['model_id']} [{profile_suffix}]"
            return entry['model_id']

        while current_model_index < len(model_chain):
            active_entry = model_chain[current_model_index]
            active_model_id = active_entry['model_id']
            active_profile_arn = active_entry.get('inference_profile_arn', '') or ''

            if not chain_logged:
                chain_summary = " → ".join(describe_model(entry) for entry in model_chain)
                log_with_timestamp(f"🧭 Bedrock model priority: {chain_summary}")
                chain_logged = True

            try:
                response = _invoke_bedrock_runtime(active_model_id, active_profile_arn, body_json)
                response_body = json.loads(response['body'].read())

                if 'usage' in response_body:
                    usage = response_body['usage']
                    if 'cache_read_input_tokens' in usage:
                        log_with_timestamp(
                            f"💰 Cache hit: {usage.get('cache_read_input_tokens', 0)} cached tokens, "
                            f"{usage.get('input_tokens', 0)} new tokens"
                        )

                # Return both the extracted text and the model that succeeded
                return response_body['content'][0]['text'], active_model_id

            except ClientError as client_error:
                error_code = client_error.response.get('Error', {}).get('Code', '')
                error_message = client_error.response.get('Error', {}).get('Message', str(client_error))
                message_lower = error_message.lower()
                is_throttle = (
                    error_code in THROTTLING_ERROR_CODES or
                    'too many tokens' in message_lower or
                    'please wait before trying again' in message_lower or
                    'throttl' in error_code.lower()
                )

                if is_throttle:
                    model_attempt_counters[current_model_index] += 1
                    total_attempts += 1
                    attempts_for_model = model_attempt_counters[current_model_index]

                    if attempts_for_model >= fallback_trigger and current_model_index < len(model_chain) - 1:
                        next_index = current_model_index + 1
                        next_entry = model_chain[next_index]
                        log_with_timestamp(
                            f"🔁 Switching to fallback model {describe_model(next_entry)} "
                            f"after {attempts_for_model} throttled attempts"
                        )
                        current_model_index = next_index
                        continue

                    if attempts_for_model >= BEDROCK_MAX_RETRIES:
                        if current_model_index < len(model_chain) - 1:
                            next_index = current_model_index + 1
                            next_entry = model_chain[next_index]
                            log_with_timestamp(
                                f"⚠️ Max attempts reached for {describe_model(active_entry)}. "
                                f"Escalating to {describe_model(next_entry)}"
                            )
                            current_model_index = next_index
                            continue
                        raise

                    if total_attempts >= max_total_attempts and current_model_index >= len(model_chain) - 1:
                        raise

                    backoff_seconds = min(
                        BEDROCK_BACKOFF_BASE_SECONDS * (2 ** max(0, attempts_for_model - 1)),
                        BEDROCK_BACKOFF_MAX_SECONDS
                    )
                    jitter_multiplier = random.uniform(0.8, 1.2)
                    wait_time = backoff_seconds * jitter_multiplier
                    log_with_timestamp(
                        f"⏳ Bedrock throttled on {describe_model(active_entry)} "
                        f"(attempt {attempts_for_model}/{BEDROCK_MAX_RETRIES}). Retrying in {wait_time:.2f}s"
                    )
                    time.sleep(wait_time)
                    continue

                raise

            except ReadTimeoutError as timeout_error:
                # Handle read timeouts - retry with fallback or same model
                log_with_timestamp(f"⏱️ Read timeout on {describe_model(active_entry)}")
                model_attempt_counters[current_model_index] += 1
                total_attempts += 1
                attempts_for_model = model_attempt_counters[current_model_index]

                # Try fallback model if available
                if attempts_for_model >= 2 and current_model_index < len(model_chain) - 1:
                    next_index = current_model_index + 1
                    next_entry = model_chain[next_index]
                    log_with_timestamp(
                        f"🔁 Switching to fallback model {describe_model(next_entry)} "
                        f"after {attempts_for_model} timeout(s)"
                    )
                    current_model_index = next_index
                    continue

                if attempts_for_model >= BEDROCK_MAX_RETRIES:
                    if current_model_index < len(model_chain) - 1:
                        next_index = current_model_index + 1
                        next_entry = model_chain[next_index]
                        log_with_timestamp(
                            f"⚠️ Max timeouts reached for {describe_model(active_entry)}. "
                            f"Escalating to {describe_model(next_entry)}"
                        )
                        current_model_index = next_index
                        continue
                    raise

                # Retry same model with short backoff
                wait_time = 5.0 * random.uniform(0.8, 1.2)
                log_with_timestamp(
                    f"⏳ Retrying {describe_model(active_entry)} after timeout "
                    f"(attempt {attempts_for_model}/{BEDROCK_MAX_RETRIES}). Waiting {wait_time:.2f}s"
                )
                time.sleep(wait_time)
                continue

            except Exception as e:
                message_lower = str(e).lower()
                is_throttle = 'too many tokens' in message_lower or 'please wait before trying again' in message_lower

                if is_throttle:
                    model_attempt_counters[current_model_index] += 1
                    total_attempts += 1
                    attempts_for_model = model_attempt_counters[current_model_index]

                    if attempts_for_model >= fallback_trigger and current_model_index < len(model_chain) - 1:
                        next_index = current_model_index + 1
                        next_entry = model_chain[next_index]
                        log_with_timestamp(
                            f"🔁 Switching to fallback model {describe_model(next_entry)} "
                            f"after {attempts_for_model} throttled attempts"
                        )
                        current_model_index = next_index
                        continue

                    if attempts_for_model >= BEDROCK_MAX_RETRIES:
                        if current_model_index < len(model_chain) - 1:
                            next_index = current_model_index + 1
                            next_entry = model_chain[next_index]
                            log_with_timestamp(
                                f"⚠️ Max attempts reached for {describe_model(active_entry)}. "
                                f"Escalating to {describe_model(next_entry)}"
                            )
                            current_model_index = next_index
                            continue
                        raise

                    if total_attempts >= max_total_attempts and current_model_index >= len(model_chain) - 1:
                        raise

                    backoff_seconds = min(
                        BEDROCK_BACKOFF_BASE_SECONDS * (2 ** max(0, attempts_for_model - 1)),
                        BEDROCK_BACKOFF_MAX_SECONDS
                    )
                    jitter_multiplier = random.uniform(0.8, 1.2)
                    wait_time = backoff_seconds * jitter_multiplier
                    log_with_timestamp(
                        f"⏳ Bedrock throttled on {describe_model(active_entry)} "
                        f"(attempt {attempts_for_model}/{BEDROCK_MAX_RETRIES}). Retrying in {wait_time:.2f}s"
                    )
                    time.sleep(wait_time)
                    continue

                raise

        raise RuntimeError("Bedrock invocation exhausted retry attempts across all configured models")
    except Exception as e:
        log_with_timestamp(f"❌ Error invoking Bedrock: {str(e)}")
        raise


def safe_decimal_convert(value: Any) -> Decimal:
    """Safely convert string to Decimal for DynamoDB"""
    if isinstance(value, (int, float)):
        return Decimal(str(value))

    if not value or not isinstance(value, str):
        return Decimal('0')

    # Clean the value - remove currency symbols and commas
    cleaned = re.sub(r'[£$€,\s]', '', str(value))
    cleaned = re.sub(r'[^\d.-]', '', cleaned)

    if not cleaned or cleaned in ['-', '.']:
        return Decimal('0')

    try:
        return Decimal(cleaned)
    except (ValueError, TypeError, ArithmeticError):
        return Decimal('0')


def parse_invoices_from_xml(xml_content: str) -> List[Dict[str, Any]]:
    """
    Parse invoices from XML response (HARDCODED logic - not editable from frontend)
    This ensures reliable structure and prevents parsing errors
    """
    invoice_pattern = r'<invoice>(.*?)</invoice>'
    field_pattern = r'<(\w+)>(.*?)</\1>'

    invoice_matches = list(re.finditer(invoice_pattern, xml_content, re.DOTALL))
    log_with_timestamp(f"📋 Found {len(invoice_matches)} invoices in XML response")

    invoices = []

    for idx, invoice_match in enumerate(invoice_matches, 1):
        invoice_data = invoice_match.group(1)
        row_data = {}

        # Extract fields from XML (HARDCODED parsing)
        for field_match in re.finditer(field_pattern, invoice_data):
            field_name, value = field_match.groups()
            row_data[field_name] = value.strip()

        # Skip incomplete invoices (must have supplier_name OR total_amount)
        if not row_data.get('supplier_name') and not row_data.get('total_amount'):
            log_with_timestamp(f"⚠️ Skipping incomplete invoice #{idx}")
            continue

        # Get supplier name with fallback
        supplier_name = row_data.get('supplier_name', '').strip()
        if not supplier_name:
            supplier_name = 'Unknown Vendor'

        # Extract and validate source_page
        source_page = row_data.get('source_page', '1')
        try:
            source_page = int(source_page)
        except (ValueError, TypeError):
            source_page = idx  # Use invoice index as fallback

        # Create standardized invoice record
        invoice_record = {
            'extraction_confidence': row_data.get('extraction_confidence', 'high'),  # Track extraction quality
            'invoice_type': row_data.get('invoice_type', 'SUPPLIER_INVOICE'),
            'invoice_number': row_data.get('invoice_number', ''),
            'reference_number': row_data.get('reference_number', ''),
            'invoice_date': row_data.get('invoice_date', datetime.now().strftime('%Y-%m-%d')),
            'due_date': row_data.get('due_date', ''),
            'supplier_name': supplier_name,
            'vendor_name': supplier_name,  # Duplicate for compatibility
            'supplier_address': row_data.get('supplier_address', ''),
            'total_amount': safe_decimal_convert(row_data.get('total_amount', '0')),
            'currency': row_data.get('currency', 'GBP'),
            'vat_amount': safe_decimal_convert(row_data.get('vat_amount', '0')),
            'net_amount': safe_decimal_convert(row_data.get('net_amount', '0')),
            'description': row_data.get('description', ''),
            'payment_terms': row_data.get('payment_terms', ''),
            'source_page': source_page
        }

        invoices.append(invoice_record)

    return invoices


def process_section_with_chunking(
    section_text: str,
    prompt_template: str,
    document_id: str,
    section_id: str,
    user_id: str
) -> List[Dict[str, Any]]:
    """
    Process large section text using chunking strategy (Phase 3)
    
    This function:
    1. Splits text into overlapping chunks (default 60k chars with 5k overlap)
    2. Processes each chunk separately with Bedrock
    3. Tracks chunk processing status in TrackingTable for resume capability
    4. Checks if all chunks complete and triggers deduplication
    5. Returns all extracted invoices (with duplicates removed if all chunks done)
    
    Args:
        section_text: Full OCR text from section
        prompt_template: Invoice extraction prompt template
        document_id: Document identifier
        section_id: Section identifier
        user_id: User identifier (for deduplication queries)
        
    Returns:
        List of invoice dictionaries (deduplicated if all chunks complete)
    """
    log_with_timestamp(f"🔄 Using CHUNKED extraction (chunk_size={CHUNK_SIZE}, overlap={OVERLAP_SIZE})")
    
    # Initialize chunking extractor
    extractor = ChunkedInvoiceExtractor(chunk_size=CHUNK_SIZE, overlap_size=OVERLAP_SIZE)
    
    # Create chunks with overlap
    chunks = extractor.create_chunks_with_overlap(section_text)
    log_with_timestamp(f"📚 Created {len(chunks)} chunks from {len(section_text)} chars")
    
    # Process each chunk
    # NOTE: Due to overlapping chunks, invoices at chunk boundaries will appear multiple times
    # This is intentional - deduplication will be handled by MergeAndDeduplicateFunction
    all_invoices = []
    failed_chunks = []
    
    for idx, chunk_info in enumerate(chunks):
        chunk_text = chunk_info['chunk']
        chunk_pages = chunk_info['pages']
        
        # Check if chunk already processed (resume capability)
        existing_status = get_chunk_status(document_id, section_id, idx)
        if existing_status == 'COMPLETED':
            log_with_timestamp(f"⏭️  Chunk {idx+1}/{len(chunks)} already completed, skipping...")
            # TODO: Load invoices from DynamoDB instead of reprocessing
            continue
        
        log_with_timestamp(
            f"📤 Processing chunk {idx+1}/{len(chunks)} "
            f"(chars {chunk_info['start']}-{chunk_info['end']}, "
            f"pages {chunk_pages})"
        )
        
        # Mark chunk as PROCESSING
        update_chunk_status(document_id, section_id, idx, 'PROCESSING')
        
        try:
            # Generate prompt for this chunk
            prompt = prompt_template.format(section_text=chunk_text)
            
            # Invoke Bedrock for this chunk
            # Enable prompt caching only if the feature is configured and this is not the first chunk
            chunk_use_caching = USE_PROMPT_CACHING and idx > 0
            xml_response, model_used = invoke_bedrock(prompt, use_caching=chunk_use_caching)
            
            # Parse invoices from chunk response
            chunk_invoices = parse_invoices_from_xml(xml_response)
            
            # Add chunk metadata to each invoice
            for invoice_idx, invoice in enumerate(chunk_invoices, start=1):
                invoice['chunk_index'] = idx
                invoice['chunk_pages'] = chunk_pages
                invoice['model_used'] = model_used  # Track which model extracted this invoice
                # Keep source_page as sequential position within chunk (for deduplication heuristic)
                # The model returns source_page, but we override with position in chunk for consistency
                invoice['source_page'] = invoice_idx  # Sequential: 1, 2, 3... within this chunk
                # If invoice doesn't have pages, use chunk pages
                if not invoice.get('pages'):
                    invoice['pages'] = chunk_pages
            
            all_invoices.extend(chunk_invoices)
            
            # Mark chunk as COMPLETED with model metadata
            update_chunk_status(
                document_id, section_id, idx, 
                'COMPLETED', 
                invoice_count=len(chunk_invoices),
                model_used=model_used
            )
            
            log_with_timestamp(f"✅ Chunk {idx+1} yielded {len(chunk_invoices)} invoices")
            
        except Exception as e:
            log_with_timestamp(f"❌ Error processing chunk {idx+1}: {str(e)}")
            
            # Mark chunk as FAILED
            update_chunk_status(
                document_id, section_id, idx,
                'FAILED',
                error_message=str(e)
            )
            
            raise ChunkProcessingError(
                f"Chunk {idx+1}/{len(chunks)} failed for document {document_id}, section {section_id}: {str(e)}"
            ) from e
    
    log_with_timestamp(f"📊 Total invoices extracted: {len(all_invoices)}")
    
    # Return invoices and completion status for deduplication to happen after writing to DynamoDB
    return {
        'invoices': all_invoices,
        'all_chunks_complete': are_all_chunks_complete(document_id, section_id, len(chunks))
    }


def write_invoices_to_dynamodb(
    invoices: List[Dict[str, Any]],
    document_id: str,
    section_id: str,
    user_id: str,
    client_id: str,
    company_number: str = None,
    company_name: str = None
) -> int:
    """
    Write individual invoice records to ExtractionResultsTable
    Each invoice gets its own DynamoDB row with unique SK
    """
    inserted_count = 0
    current_timestamp = int(time.time())

    for idx, invoice_data in enumerate(invoices):
        try:
            # Generate unique invoice ID
            invoice_id = f"{document_id}-inv-{section_id}-{idx+1}-{str(uuid.uuid4())[:8]}"

            # Create DynamoDB item matching your schema
            item = {
                # Primary Key
                'PK': f"user#{user_id}#doc#{document_id}",
                'SK': f"type#INVOICE#section#{section_id}#invoice#{idx+1}",

                # GSI Keys
                'GSI1PK': f"user#{user_id}#type#INVOICE",
                'ProcessedAt': current_timestamp,
                'UserId': user_id,
                'GSI3PK': f"company#{normalize_company_name(invoice_data['supplier_name'])}#type#INVOICE",
                'DocumentId': document_id,
                'ExtractionStatus': 'COMPLETED',
                'GSI6PK': f"client#{client_id}#type#INVOICE",

                # Core identifiers
                'InvoiceId': invoice_id,
                'SectionId': section_id,
                'ClientId': client_id,
                'CompanyNumber': company_number or 'unknown',
                'CompanyName': company_name or 'Unknown Company',
                'DocumentType': 'INVOICE',

                # Invoice-specific fields
                'InvoiceType': invoice_data['invoice_type'],
                'InvoiceNumber': invoice_data['invoice_number'],
                'ReferenceNumber': invoice_data['reference_number'],
                'InvoiceDate': invoice_data['invoice_date'],
                'DueDate': invoice_data['due_date'],
                'SupplierName': invoice_data['supplier_name'],
                'VendorName': invoice_data['vendor_name'],
                'CompanyName': invoice_data['supplier_name'],  # For GSI3 queries
                'SupplierAddress': invoice_data['supplier_address'],
                'TotalAmount': invoice_data['total_amount'],
                'Currency': invoice_data['currency'],
                'VATAmount': invoice_data['vat_amount'],
                'NetAmount': invoice_data['net_amount'],
                'Description': invoice_data['description'],
                'PaymentTerms': invoice_data['payment_terms'],
                'SourcePage': invoice_data['source_page'],

                # Chunk metadata for deduplication
                'ChunkIndex': invoice_data.get('chunk_index'),  # Which chunk extracted this invoice
                'ChunkPages': invoice_data.get('chunk_pages', []),  # Pages covered by this chunk

                # Metadata
                'CreatedAt': current_timestamp,
                'UpdatedAt': current_timestamp,
                'DateExtracted': datetime.now().strftime('%Y-%m-%d'),
                'ExtractionConfidence': invoice_data.get('extraction_confidence', 'high'),  # Track extraction quality
                'ConfidenceScore': (
                    Decimal('0.95') if invoice_data.get('extraction_confidence') == 'high' else
                    Decimal('0.75') if invoice_data.get('extraction_confidence') == 'medium' else
                    Decimal('0.50')  # low confidence
                ),
                'Version': 1,
                'ModelUsed': invoice_data.get('model_used', 'unknown'),  # Track which model extracted this

                # TTL (optional - set to 1 year from now)
                'TTL': current_timestamp + (365 * 24 * 60 * 60)
            }

            # Write to DynamoDB
            extraction_table.put_item(Item=item)
            inserted_count += 1

            log_with_timestamp(
                f"✅ Inserted invoice {idx+1}/{len(invoices)}: "
                f"{invoice_data['supplier_name']} - "
                f"{invoice_data['currency']}{invoice_data['total_amount']}"
            )

        except Exception as e:
            log_with_timestamp(f"❌ Error inserting invoice {idx+1}: {str(e)}")

    return inserted_count


def normalize_company_name(company_name: str) -> str:
    """Normalize company name for consistent GSI3PK keys"""
    if not company_name:
        return 'unknown'

    # Convert to lowercase, remove special chars, replace spaces with hyphens
    normalized = company_name.lower()
    normalized = re.sub(r'[^a-z0-9\s-]', '', normalized)
    normalized = re.sub(r'\s+', '-', normalized).strip('-')

    return normalized or 'unknown'


def lambda_handler(event, context):
    """
    Main Lambda handler for invoice extraction

    Expected event structure from Step Functions:
    {
        "execution_arn": "...",
        "document": { ... },  # Full document object (compressed or dict)
        "section_id": "1"
    }
    """
    start_time = time.time()

    try:
        # Log the full event for debugging
        log_with_timestamp(f"📥 Received event: {json.dumps(event, default=str)[:1000]}...")

        # Get section_id from event
        section_id = event.get('section_id')
        if not section_id:
            raise ValueError("No section_id found in event")

        log_with_timestamp(f"📋 Section ID: {section_id}")

        # Get document data (handle compressed S3 URI, inline S3 URI string, and inline dict)
        document_data = event.get('document', {})
        log_with_timestamp(f"📄 Document data type: {type(document_data)}")

        if isinstance(document_data, str):
            # Document is S3 URI string - fetch from S3
            s3_client = boto3.client('s3')
            from urllib.parse import urlparse
            parsed_uri = urlparse(document_data)
            bucket = parsed_uri.netloc
            key = parsed_uri.path.lstrip('/')

            log_with_timestamp(f"📦 Fetching document from S3: s3://{bucket}/{key}")
            s3_obj = s3_client.get_object(Bucket=bucket, Key=key)
            document_dict = json.loads(s3_obj['Body'].read().decode('utf-8'))

        elif isinstance(document_data, dict) and document_data.get('compressed') and document_data.get('s3_uri'):
            # Document is compressed and stored in S3 - fetch it
            s3_uri = document_data['s3_uri']
            log_with_timestamp(f"📦 Document is compressed, fetching from S3: {s3_uri}")

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
        log_with_timestamp(f"🔍 Full document structure (first 2000 chars): {json.dumps(document_dict, default=str)[:2000]}")

        # Extract metadata from document dict
        document_id = (
            document_dict.get('id')
            or document_dict.get('document_id')
            or document_dict.get('documentId')
        )
        user_id = document_dict.get('user_id')
        company_number = document_dict.get('company_number')  # Extract company_number
        company_name = document_dict.get('company_name')      # Extract company_name
        client_id = company_number or document_dict.get('client_id') or 'default-client'  # Use company_number as client_id

        log_with_timestamp(f"🔍 Extracted metadata - ID: {document_id}, User: {user_id}, Client: {client_id}, Company: {company_name} ({company_number})")

        # Find the section in the document
        sections = document_dict.get('sections', [])
        log_with_timestamp(f"📚 Found {len(sections)} sections in document")

        section_data = None
        for sec in sections:
            if sec.get('section_id') == section_id:
                section_data = sec
                break

        if not section_data:
            raise ValueError(f"Section {section_id} not found in document. Available sections: {[s.get('section_id') for s in sections]}")

        log_with_timestamp(f"📋 Section data keys: {list(section_data.keys())}")
        log_with_timestamp(f"📋 Section data: {json.dumps(section_data, default=str)[:500]}")

        # Get section text from OCR results
        section_text = ""
        section_pages = section_data.get('page_ids', [])

        log_with_timestamp(f"📄 Section has {len(section_pages)} page IDs: {section_pages}")

        # Check if section has ocr_result_uri or ocr_text directly
        if 'ocr_result_uri' in section_data:
            log_with_timestamp(f"📥 Found ocr_result_uri in section: {section_data['ocr_result_uri']}")
            # TODO: Fetch OCR text from S3
        elif 'ocr_text' in section_data:
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

                    # Extract page number from page_id (e.g., "page-5" -> 5)
                    page_number = 1
                    try:
                        if page_id.startswith('page-'):
                            page_number = int(page_id.split('-')[1])
                        elif page_id.isdigit():
                            page_number = int(page_id)
                    except (ValueError, IndexError):
                        log_with_timestamp(f"⚠️ Could not extract page number from {page_id}, using sequential")
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
                        log_with_timestamp(f"📋 rawText.json sample: {json.dumps(raw_text_data, default=str)[:500]}")

                        # rawText.json contains the extracted text - try different field names
                        page_text = raw_text_data.get('text', '') or raw_text_data.get('Text', '') or raw_text_data.get('content', '')

                        # Try Bedrock Nova response format: output.message.content[0].text
                        if not page_text and 'output' in raw_text_data:
                            try:
                                page_text = raw_text_data['output']['message']['content'][0]['text']
                                log_with_timestamp(f"📝 Extracted text from Bedrock response format")
                            except (KeyError, IndexError, TypeError):
                                pass

                        # If still empty, try to extract from blocks or lines
                        if not page_text and 'Blocks' in raw_text_data:
                            # Textract format - extract text from LINE blocks
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

        log_with_timestamp(f"📝 Total section text length: {len(section_text)} chars")

        log_with_timestamp(f"🚀 Starting invoice extraction for document {document_id}, section {section_id}")
        log_with_timestamp(f"   User: {user_id}, Client: {client_id}")
        log_with_timestamp(f"   Section text length: {len(section_text)} chars")
        log_with_timestamp(f"   Section pages: {section_pages}")

        # Validate required fields
        if not all([document_id, section_id, user_id, client_id]):
            raise ValueError("Missing required fields in event")

        # Check if section has text
        if not section_text or len(section_text.strip()) == 0:
            log_with_timestamp("⚠️ No text content in section - skipping invoice extraction")
            return {
                'section_id': section_id,
                'document': event.get('document'),
                'invoices_extracted': 0,
                'message': 'No text content in section'
            }

        # Get extraction prompt (dynamic from ConfigurationTable)
        prompt_template = get_invoice_extraction_prompt()
        
        # PHASE 3: Choose extraction strategy based on feature flag and section size
        if USE_CHUNKED_EXTRACTION and len(section_text) > CHUNK_SIZE:
            log_with_timestamp(
                f"🔄 Section text ({len(section_text)} chars) exceeds chunk size ({CHUNK_SIZE})"
            )
            log_with_timestamp("   Using CHUNKED extraction strategy...")
            
            result = process_section_with_chunking(
                section_text=section_text,
                prompt_template=prompt_template,
                document_id=document_id,
                section_id=section_id,
                user_id=user_id
            )
            
            invoices = result['invoices']
            all_chunks_complete = result['all_chunks_complete']
        else:
            # Original non-chunked flow (default/fallback)
            if USE_CHUNKED_EXTRACTION:
                log_with_timestamp(
                    f"ℹ️  Section text ({len(section_text)} chars) fits in single chunk"
                )
                log_with_timestamp("   Using standard extraction (no chunking needed)")
            else:
                log_with_timestamp("ℹ️  Chunked extraction DISABLED (USE_CHUNKED_EXTRACTION=false)")
                log_with_timestamp("   Using standard extraction")
            
            prompt = prompt_template.format(section_text=section_text)
            
            # Invoke Bedrock to extract invoices
            log_with_timestamp("📤 Calling Bedrock for invoice extraction...")
            xml_response, model_used = invoke_bedrock(prompt)
            
            # Parse invoices from XML (hardcoded logic)
            log_with_timestamp("🔍 Parsing invoices from XML response...")
            invoices = parse_invoices_from_xml(xml_response)
            
            # Add model metadata to invoices
            for invoice in invoices:
                invoice['model_used'] = model_used
            
            all_chunks_complete = False  # Non-chunked flow doesn't need deduplication

        if not invoices:
            log_with_timestamp("⚠️ No valid invoices found in section")
            return {
                'section_id': section_id,
                'document': event.get('document'),  # Pass through for next step
                'invoices_extracted': 0,
                'message': 'No invoices found'
            }

        # Write invoices to DynamoDB
        log_with_timestamp(f"💾 Writing {len(invoices)} invoices to DynamoDB...")
        inserted_count = write_invoices_to_dynamodb(
            invoices, document_id, section_id, user_id, client_id, company_number, company_name
        )
        
        # PHASE 3: Deduplicate AFTER writing to DynamoDB (only if all chunks complete)
        if all_chunks_complete:
            log_with_timestamp("✅ All chunks complete! Starting deduplication...")
            
            # Deduplicate invoices in DynamoDB
            # This handles duplicates from overlapping chunks
            deleted_count = deduplicate_invoices_in_dynamodb(document_id, section_id, user_id)
            
            if deleted_count > 0:
                log_with_timestamp(f"🎯 Deduplication removed {deleted_count} duplicate invoices")
            else:
                log_with_timestamp("✅ No duplicates found")
        else:
            log_with_timestamp("⏸️  Some chunks still pending - deduplication deferred")

        processing_time = time.time() - start_time
        log_with_timestamp(
            f"✅ Invoice extraction completed successfully in {processing_time:.2f}s"
        )
        log_with_timestamp(f"   Extracted: {len(invoices)} invoices")
        log_with_timestamp(f"   Inserted: {inserted_count} records")

        # Return response matching workflow expectations
        # Must include document and section_id for AssessmentStep
        return {
            'section_id': section_id,
            'document': event.get('document'),  # Pass through original document format
            'invoices_extracted': len(invoices),
            'invoices_inserted': inserted_count,
            'processing_time_seconds': processing_time,
            'message': f'Successfully extracted {len(invoices)} invoices'
        }

    except ChunkProcessingError as e:
        log_with_timestamp(f"💥 Chunk processing error: {str(e)}")
        raise

    except Exception as e:
        log_with_timestamp(f"💥 Error in invoice extraction: {str(e)}")
        import traceback
        log_with_timestamp(f"📋 Traceback: {traceback.format_exc()}")

        # Return error response but maintain workflow structure
        # Don't raise exception - let workflow continue even if invoice extraction fails
        return {
            'section_id': event.get('section_id', 'unknown'),
            'document': event.get('document'),  # Pass through for next step
            'invoices_extracted': 0,
            'error': str(e),
            'message': 'Invoice extraction failed'
        }
