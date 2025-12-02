# Chunked Invoice Extraction Implementation Guide

**Goal**: Implement robust multi-invoice extraction using chunking with overlap and deduplication, based on proven production approach.

**Date**: November 4, 2025  
**Branch**: `dev`

---

## Overview

This guide implements a chunked extraction strategy for invoices that:
- ✅ Handles PDFs with multiple invoices (1-50+ invoices)
- ✅ Uses text chunking with overlap to prevent invoice splitting
- ✅ Implements deduplication to remove duplicate extractions
- ✅ Captures user document type hints for faster processing
- ✅ Validates user hints against classification for quality control

---

## Architecture Changes

```
User Upload (with document_type hint)
    ↓
QueueSender (capture user_id + document_type + company metadata)
    ↓
OCR Step (unchanged - page-by-page extraction)
    ↓
Classification Step (validate user hint OR classify if missing)
    ↓
Extraction Step ← MODIFIED
    ├─ For invoices: Use chunking + deduplication
    ├─ For other docs: Use existing extraction logic
    └─ Write to DynamoDB
    ↓
Assessment Step (unchanged)
```

---

## Implementation Steps

### **Phase 1: Capture User Document Type Hint**

#### Step 1.1: Update Web UI Upload Component (Frontend)

**File**: `(Your upload component - likely in UI code)`

Add document type selection to upload form:

```javascript
// Example React/Vue component
<select v-model="documentType" label="Document Type">
  <option value="">Auto-detect</option>
  <option value="invoice">Invoice</option>
  <option value="bank-statement">Bank Statement</option>
  <option value="payslip">Payslip</option>
  <option value="drivers-license">Driver's License</option>
  <option value="w2">W2 Tax Form</option>
  <option value="check">Check</option>
  <option value="homeowners-insurance">Homeowners Insurance</option>
</select>
```

#### Step 1.2: Include Document Type in S3 Upload Metadata

**File**: `(Your S3 upload handler - backend API or frontend)`

When uploading to S3, add document type to metadata:

```python
# Python example (backend)
s3_client.put_object(
    Bucket=input_bucket,
    Key=f"users/{user_id}/{filename}",
    Body=file_content,
    Metadata={
        'user-document-type': document_type,  # NEW: Add user hint
        'company-number': company_number,
        'company-name': company_name,
    }
)
```

```javascript
// JavaScript example (frontend with presigned URL)
const formData = new FormData();
formData.append('file', file);

// Add metadata headers
const headers = {
  'x-amz-meta-user-document-type': documentType,
  'x-amz-meta-company-number': companyNumber,
  'x-amz-meta-company-name': companyName,
};

await axios.put(presignedUrl, file, { headers });
```

#### Step 1.3: Update QueueSender to Extract Document Type

**File**: `src/lambda/queue_sender/index.py`

**Location**: Around lines 96-110 in the `handler()` function

**Find this code:**
```python
        # Extract company metadata from S3 object if available
        company_number = None
        company_name = None
        try:
            # Get object metadata to extract company information
            head_response = boto3.client("s3").head_object(
                Bucket=bucket_name, Key=object_key
            )
            metadata = head_response.get("Metadata", {})
            company_number = metadata.get("company-number")
            company_name = metadata.get("company-name")
            if company_number:
                logger.info(
                    f"Extracted company metadata: {company_name} ({company_number})"
                )
        except Exception as e:
            logger.warning(f"Could not retrieve object metadata: {str(e)}")
            # Continue without company metadata
```

**Replace with:**
```python
        # Extract company metadata from S3 object if available
        company_number = None
        company_name = None
        user_document_type = None  # NEW
        try:
            # Get object metadata to extract company information
            head_response = boto3.client("s3").head_object(
                Bucket=bucket_name, Key=object_key
            )
            metadata = head_response.get("Metadata", {})
            company_number = metadata.get("company-number")
            company_name = metadata.get("company-name")
            user_document_type = metadata.get("user-document-type")  # NEW
            if company_number:
                logger.info(
                    f"Extracted company metadata: {company_name} ({company_number})"
                )
            if user_document_type:  # NEW
                logger.info(f"User indicated document type: {user_document_type}")
        except Exception as e:
            logger.warning(f"Could not retrieve object metadata: {str(e)}")
            # Continue without company metadata
```

**Then find this code** (around line 135):
```python
        document = Document(
            id=object_key,
            input_bucket=bucket_name,
            input_key=object_key,
            output_bucket=OUTPUT_BUCKET,
            status=Status.QUEUED,
            queued_time=event_time,
            initial_event_time=event_time,
            user_id=user_id,
            company_number=company_number,
            company_name=company_name,
            pages={},
            sections=[],
        )
```

**Replace with:**
```python
        document = Document(
            id=object_key,
            input_bucket=bucket_name,
            input_key=object_key,
            output_bucket=OUTPUT_BUCKET,
            status=Status.QUEUED,
            queued_time=event_time,
            initial_event_time=event_time,
            user_id=user_id,
            company_number=company_number,
            company_name=company_name,
            user_document_type=user_document_type,  # NEW
            pages={},
            sections=[],
        )
```

#### Step 1.4: Update Document Model to Support User Hint

**File**: `lib/idp_common_pkg/idp_common/models.py`

**Find the Document class definition** (search for `class Document:`):

Add the new field to the `__init__` method:

```python
def __init__(
    self,
    id: str,
    input_bucket: Optional[str] = None,
    input_key: Optional[str] = None,
    output_bucket: Optional[str] = None,
    status: Status = Status.QUEUED,
    user_id: Optional[str] = None,
    client_id: Optional[str] = None,
    company_number: Optional[str] = None,  # Existing
    company_name: Optional[str] = None,    # Existing
    user_document_type: Optional[str] = None,  # NEW - Add this line
    # ... rest of parameters
):
    self.user_document_type = user_document_type  # NEW - Add this line
    # ... rest of initialization
```

Also update the `to_dict()` and `from_dict()` methods to include the new field.

---

### **Phase 2: Smart Classification with User Hint Validation**

#### Step 2.1: Update Classification Configuration

**File**: `config_library/pattern-2/lending-package-sample/config.yaml`

**Add to the classification section** (around line 300):

```yaml
classification:
  classificationMethod: multimodalPageLevelClassification
  maxPagesForClassification: "ALL"
  
  # NEW: User hint behavior
  trust_user_hint: true  # If true, skip LLM classification when user provides hint
  validate_hint_threshold: 0.8  # If validating, confidence threshold to override hint
  
  image:
    target_height: ""
    target_width: ""
  model: eu.amazon.nova-pro-v1:0
  # ... rest of classification config
```

#### Step 2.2: Update Classification Function to Use Hints

**File**: `patterns/pattern-2/src/classification_function/index.py`

**Location**: At the start of the `handler()` function, after loading the document

**Find this code** (around line 60):
```python
    # Intelligent Classification detection: Skip if pages already have classifications
    pages_with_classification = 0
    for page in document.pages.values():
        if page.classification and page.classification.strip():
            pages_with_classification += 1

    if pages_with_classification == len(document.pages) and len(document.pages) > 0:
        logger.info(
            f"Skipping classification for document {document.id} - all {len(document.pages)} pages already classified"
        )
```

**Add BEFORE the above code:**
```python
    # NEW: Check if user provided a document type hint
    user_hint = document.user_document_type
    trust_user_hint = config.get("classification", {}).get("trust_user_hint", True)
    
    if user_hint and trust_user_hint:
        logger.info(
            f"User indicated document type: {user_hint}. "
            f"trust_user_hint=True, skipping LLM classification"
        )
        
        # Set all pages to user hint
        for page_id, page in document.pages.items():
            page.classification = user_hint
            page.confidence = 1.0
        
        # Create single section with all pages
        section = Section(
            section_id="1",
            classification=user_hint,
            confidence=1.0,
            page_ids=list(document.pages.keys()),
        )
        document.sections = [section]
        
        # Update document status
        document_service = create_document_service()
        logger.info("Updating document with user-hinted classification")
        document_service.update_document(document)
        
        # Prepare output
        response = {
            "document": document.serialize_document(
                working_bucket, "classification_user_hint", logger
            )
        }
        
        logger.info(
            f"Classification skipped (user hint) - Response: {json.dumps(response, default=str)}"
        )
        return response
```

---

### **Phase 3: Create Chunked Invoice Extractor**

#### Step 3.1: Create the ChunkedInvoiceExtractor Class

**File**: `lib/idp_common_pkg/idp_common/extraction/chunked_invoice_extractor.py` (NEW FILE)

**Create the directory structure:**
```bash
mkdir -p lib/idp_common_pkg/idp_common/extraction
touch lib/idp_common_pkg/idp_common/extraction/__init__.py
```

**Create the file with this content:**

```python
"""
Chunked invoice extraction with overlap and deduplication.
Based on proven production approach for multi-invoice documents.

This module implements:
- Text chunking with configurable overlap
- Page boundary markers for spatial context
- Deduplication based on invoice similarity
- Completeness scoring for selecting best duplicate
"""

import logging
import re
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class InvoiceChunk:
    """Represents a chunk of text for processing"""
    chunk_id: str
    text: str
    start_page: int
    end_page: int
    overlap_before: bool
    overlap_after: bool


class ChunkedInvoiceExtractor:
    """
    Extracts invoices from large documents using chunking with overlap
    and deduplication logic.
    
    Usage:
        extractor = ChunkedInvoiceExtractor(chunk_size=15000, overlap_size=3000)
        chunks = extractor.create_chunks_with_overlap(pages_dict)
        # ... extract from each chunk ...
        unique_invoices = extractor.deduplicate_invoices(all_invoices)
    """
    
    def __init__(
        self,
        chunk_size: int = 15000,  # ~15k chars per chunk (adjust based on model)
        overlap_size: int = 3000,  # 3k char overlap to catch invoices at boundaries
        max_invoices_per_chunk: int = 10,  # Limit per chunk for quality
    ):
        """
        Initialize the chunked invoice extractor.
        
        Args:
            chunk_size: Maximum characters per chunk
            overlap_size: Characters to overlap between chunks
            max_invoices_per_chunk: Maximum invoices to extract per chunk
        """
        self.chunk_size = chunk_size
        self.overlap_size = overlap_size
        self.max_invoices_per_chunk = max_invoices_per_chunk
        
        logger.info(
            f"ChunkedInvoiceExtractor initialized: "
            f"chunk_size={chunk_size}, overlap={overlap_size}, "
            f"max_per_chunk={max_invoices_per_chunk}"
        )
    
    def create_chunks_with_overlap(
        self, 
        pages: Dict[str, Any]
    ) -> List[InvoiceChunk]:
        """
        Create overlapping text chunks from pages with clear page markers.
        
        This method:
        1. Builds full text with page boundary markers (e.g., "=== PAGE 1 ===")
        2. Splits into chunks of chunk_size with overlap_size overlap
        3. Tracks which pages are in each chunk
        
        Args:
            pages: Dictionary of page_id -> page data
            
        Returns:
            List of InvoiceChunk objects
        """
        chunks = []
        full_text = ""
        page_boundaries = {}  # Track where each page starts in full_text
        
        # Build full text with page markers
        current_position = 0
        for page_id in sorted(pages.keys(), key=lambda x: int(x)):
            page_data = pages[page_id]
            page_text = self._get_page_text(page_data)
            
            # Add visual page marker (makes it easy for LLM to track pages)
            page_marker = f"\n\n{'='*50}\n=== PAGE {page_id} ===\n{'='*50}\n\n"
            page_boundaries[int(page_id)] = current_position + len(page_marker)
            
            full_text += page_marker + page_text
            current_position = len(full_text)
        
        logger.info(f"Built full text: {len(full_text)} chars from {len(pages)} pages")
        
        # Create overlapping chunks
        text_length = len(full_text)
        chunk_start = 0
        chunk_id = 0
        
        while chunk_start < text_length:
            chunk_id += 1
            chunk_end = min(chunk_start + self.chunk_size, text_length)
            
            # Extract chunk text
            chunk_text = full_text[chunk_start:chunk_end]
            
            # Determine which pages are in this chunk
            start_page = self._get_page_at_position(chunk_start, page_boundaries)
            end_page = self._get_page_at_position(chunk_end, page_boundaries)
            
            chunk = InvoiceChunk(
                chunk_id=f"chunk_{chunk_id}",
                text=chunk_text,
                start_page=start_page,
                end_page=end_page,
                overlap_before=(chunk_start > 0),
                overlap_after=(chunk_end < text_length),
            )
            chunks.append(chunk)
            
            logger.debug(
                f"Created {chunk.chunk_id}: pages {start_page}-{end_page}, "
                f"{len(chunk_text)} chars"
            )
            
            # Move to next chunk with overlap
            if chunk_end >= text_length:
                break
            
            chunk_start = chunk_end - self.overlap_size
        
        logger.info(
            f"Created {len(chunks)} chunks from {len(pages)} pages "
            f"(chunk_size={self.chunk_size}, overlap={self.overlap_size})"
        )
        
        return chunks
    
    def deduplicate_invoices(
        self,
        all_invoices: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Deduplicate invoices that appear in multiple chunks.
        
        Logic:
        1. Group invoices by similarity key (invoice_number + total_amount)
        2. For each group, select the most complete invoice
        3. Completeness = count of non-empty fields
        4. If tied, prefer earlier chunk (less likely to be cut off)
        
        Args:
            all_invoices: List of all extracted invoices from all chunks
            
        Returns:
            Deduplicated list of invoices
        """
        if not all_invoices:
            return []
        
        logger.info(f"Deduplicating {len(all_invoices)} invoices...")
        
        # Group by similarity key
        invoice_groups = {}
        
        for invoice in all_invoices:
            # Create similarity key
            key = self._create_similarity_key(invoice)
            
            if key not in invoice_groups:
                invoice_groups[key] = []
            
            invoice_groups[key].append(invoice)
        
        # Deduplicate each group
        deduplicated = []
        duplicates_removed = 0
        
        for key, group in invoice_groups.items():
            if len(group) == 1:
                # No duplicates
                deduplicated.append(group[0])
            else:
                # Multiple invoices with same key - pick best one
                best_invoice = self._select_best_invoice(group)
                deduplicated.append(best_invoice)
                duplicates_removed += len(group) - 1
                
                logger.info(
                    f"Deduplicated {len(group)} similar invoices for key '{key}', "
                    f"kept invoice from {best_invoice.get('chunk_id', 'unknown')}"
                )
        
        logger.info(
            f"Deduplication complete: {len(all_invoices)} → {len(deduplicated)} "
            f"({duplicates_removed} duplicates removed)"
        )
        
        return deduplicated
    
    def _create_similarity_key(self, invoice: Dict[str, Any]) -> str:
        """
        Create a key for identifying similar invoices.
        Uses invoice_number + total_amount (normalized).
        
        If no invoice number, uses supplier + amount + date.
        """
        invoice_num = str(invoice.get('invoice_number', '')).strip().lower()
        total = str(invoice.get('total_amount', '0')).strip()
        
        # Normalize amounts: remove currency symbols, spaces
        total_normalized = re.sub(r'[£$€,\s]', '', total)
        
        # If no invoice number, use supplier + amount + date
        if not invoice_num:
            supplier = str(invoice.get('supplier_name', '')).strip().lower()
            date = str(invoice.get('invoice_date', '')).strip()
            return f"{supplier}|{total_normalized}|{date}"
        
        return f"{invoice_num}|{total_normalized}"
    
    def _select_best_invoice(
        self,
        candidates: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Select the most complete invoice from a group of similar ones.
        
        Criteria:
        1. Most non-empty fields (completeness score)
        2. If tie, prefer earlier chunk (less likely to be cut off)
        
        Args:
            candidates: List of similar invoices
            
        Returns:
            The best (most complete) invoice
        """
        def score_completeness(invoice):
            """Count non-empty fields"""
            score = 0
            for key, value in invoice.items():
                # Skip metadata fields
                if key in ['chunk_id', 'source_page']:
                    continue
                # Count non-empty values
                if value and str(value).strip() and str(value) not in ['0', '0.0', 'None', 'null']:
                    score += 1
            return score
        
        # Score each candidate
        scored = [
            (score_completeness(inv), inv.get('chunk_id', 'unknown'), inv)
            for inv in candidates
        ]
        
        # Sort by completeness (desc), then chunk_id (asc)
        scored.sort(key=lambda x: (-x[0], x[1]))
        
        best = scored[0][2]
        
        logger.debug(
            f"Selected invoice with {scored[0][0]} fields "
            f"from {scored[0][1]}"
        )
        
        return best
    
    def _get_page_text(self, page_data: Dict[str, Any]) -> str:
        """
        Extract text from page data (handles different formats).
        
        Tries:
        1. Inline 'ocr_text' field
        2. Fetch from 'parsed_text_uri' in S3
        """
        # Try inline text first
        if 'ocr_text' in page_data:
            return page_data['ocr_text']
        
        # Fetch from S3 if needed
        if 'parsed_text_uri' in page_data:
            try:
                from idp_common import s3
                return s3.get_text_content(page_data['parsed_text_uri'])
            except Exception as e:
                logger.warning(f"Failed to fetch page text from S3: {e}")
                return ""
        
        return ""
    
    def _get_page_at_position(
        self,
        position: int,
        page_boundaries: Dict[int, int]
    ) -> int:
        """
        Find which page a text position belongs to.
        
        Args:
            position: Character position in full text
            page_boundaries: Dict of page_num -> start_position
            
        Returns:
            Page number
        """
        for page_num in sorted(page_boundaries.keys(), reverse=True):
            if position >= page_boundaries[page_num]:
                return page_num
        return 1  # Default to first page
```

#### Step 3.2: Update the extraction __init__.py

**File**: `lib/idp_common_pkg/idp_common/extraction/__init__.py`

```python
"""
Extraction module for IDP common library.
"""

from idp_common.extraction.chunked_invoice_extractor import (
    ChunkedInvoiceExtractor,
    InvoiceChunk,
)

__all__ = [
    "ChunkedInvoiceExtractor",
    "InvoiceChunk",
]
```

---

### **Phase 4: Update Invoice Extraction Lambda**

#### Step 4.1: Import ChunkedInvoiceExtractor

**File**: `patterns/pattern-2/lambdas/invoice_extraction/invoice_extraction_handler.py`

**At the top of the file** (after existing imports around line 17):

```python
# Add this import
from idp_common.extraction import ChunkedInvoiceExtractor
```

#### Step 4.2: Add Chunked Processing Function

**File**: Same file as above

**Add this new function BEFORE `lambda_handler`** (around line 180):

```python
def process_invoices_with_chunking(
    event, document_dict, section_data, section_id,
    user_id, client_id, company_number, company_name
):
    """
    Process invoices using chunked extraction with deduplication.
    
    This function:
    1. Creates overlapping text chunks from section pages
    2. Extracts invoices from each chunk using Bedrock
    3. Deduplicates invoices that appear in multiple chunks
    4. Writes unique invoices to DynamoDB
    """
    log_with_timestamp("🔧 Using chunked extraction for invoices")
    
    # Initialize chunked extractor with configurable parameters
    # TODO: Make these configurable via environment variables or config
    extractor = ChunkedInvoiceExtractor(
        chunk_size=15000,      # ~15k chars per chunk
        overlap_size=3000,     # 3k char overlap
        max_invoices_per_chunk=10
    )
    
    # Get pages for this section
    section_pages = section_data.get('page_ids', [])
    pages_dict = document_dict.get('pages', {})
    
    # Filter to only pages in this section
    section_pages_data = {
        pid: pages_dict[pid] for pid in section_pages if pid in pages_dict
    }
    
    log_with_timestamp(f"📚 Section has {len(section_pages_data)} pages")
    
    # Create chunks with overlap
    chunks = extractor.create_chunks_with_overlap(section_pages_data)
    log_with_timestamp(f"📦 Created {len(chunks)} chunks for processing")
    
    # Extract from each chunk
    all_invoices = []
    for chunk in chunks:
        log_with_timestamp(
            f"📦 Processing {chunk.chunk_id} "
            f"(pages {chunk.start_page}-{chunk.end_page}, "
            f"{len(chunk.text)} chars)"
        )
        
        try:
            # Get extraction prompt
            prompt_template = get_invoice_extraction_prompt()
            prompt = prompt_template.format(section_text=chunk.text)
            
            # Invoke Bedrock
            xml_response = invoke_bedrock(prompt)
            
            # Parse invoices from XML
            chunk_invoices = parse_invoices_from_xml(xml_response)
            
            # Tag with chunk_id for deduplication tracking
            for inv in chunk_invoices:
                inv['chunk_id'] = chunk.chunk_id
            
            all_invoices.extend(chunk_invoices)
            
            log_with_timestamp(
                f"✅ Extracted {len(chunk_invoices)} invoices from {chunk.chunk_id}"
            )
            
        except Exception as e:
            log_with_timestamp(
                f"❌ Error processing {chunk.chunk_id}: {str(e)}"
            )
            # Continue with other chunks even if one fails
            continue
    
    log_with_timestamp(f"📊 Total invoices before deduplication: {len(all_invoices)}")
    
    # Deduplicate invoices
    log_with_timestamp(f"🔍 Deduplicating invoices...")
    unique_invoices = extractor.deduplicate_invoices(all_invoices)
    
    log_with_timestamp(f"✅ Unique invoices after deduplication: {len(unique_invoices)}")
    
    # Write to DynamoDB
    if unique_invoices:
        log_with_timestamp(f"💾 Writing {len(unique_invoices)} invoices to DynamoDB...")
        inserted_count = write_invoices_to_dynamodb(
            unique_invoices,
            document_dict['id'],
            section_id,
            user_id,
            client_id,
            company_number,
            company_name
        )
    else:
        inserted_count = 0
        log_with_timestamp("⚠️ No invoices to write to DynamoDB")
    
    return {
        'section_id': section_id,
        'document': event.get('document'),  # Pass through for next step
        'invoices_extracted': len(unique_invoices),
        'invoices_inserted': inserted_count,
        'chunks_processed': len(chunks),
        'duplicates_removed': len(all_invoices) - len(unique_invoices),
        'processing_method': 'chunked_extraction',
        'message': f'Extracted {len(unique_invoices)} unique invoices from {len(chunks)} chunks'
    }
```

#### Step 4.3: Update lambda_handler to Use Chunking

**File**: Same file

**Find the lambda_handler function** (around line 250)

**Find this section** (after section_text is built):

```python
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
        prompt = prompt_template.format(section_text=section_text)
```

**Replace with:**

```python
        log_with_timestamp(f"🚀 Starting invoice extraction for document {document_id}, section {section_id}")
        log_with_timestamp(f"   User: {user_id}, Client: {client_id}")
        log_with_timestamp(f"   Section pages: {section_pages}")

        # Validate required fields
        if not all([document_id, section_id, user_id, client_id]):
            raise ValueError("Missing required fields in event")

        # Check section classification
        section_classification = section_data.get('classification', '').lower()
        
        # NEW: Use chunked extraction for invoices
        use_chunking = os.environ.get('USE_CHUNKED_EXTRACTION', 'true').lower() == 'true'
        
        if section_classification == 'invoice' and use_chunking:
            log_with_timestamp("📦 Using CHUNKED extraction for invoice section")
            return process_invoices_with_chunking(
                event, document_dict, section_data, section_id,
                user_id, client_id, company_number, company_name
            )
        
        # FALLBACK: Use original single-pass extraction
        log_with_timestamp(f"📄 Using STANDARD extraction for {section_classification} section")
        log_with_timestamp(f"   Section text length: {len(section_text)} chars")
        
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
        prompt = prompt_template.format(section_text=section_text)
```

---

### **Phase 5: Update Configuration**

#### Step 5.1: Add Chunking Config to Pattern-2 Config

**File**: `config_library/pattern-2/lending-package-sample/config.yaml`

**Add this new section** (after the `extraction` section, around line 450):

```yaml
extraction:
  # ... existing extraction config ...
  
  # NEW: Chunking configuration for invoice extraction
  chunking:
    enabled: true  # Enable chunked extraction
    chunk_size: 15000  # Characters per chunk (~15k works well for most models)
    overlap_size: 3000  # Character overlap between chunks (prevents splitting)
    max_invoices_per_chunk: 10  # Limit extractions per chunk for quality
    
    # Document types that should use chunked extraction
    document_types:
      - invoice
      - receipt
      - expense-claim
    
    # Deduplication settings
    deduplication:
      enabled: true  # Enable deduplication of invoices across chunks
      similarity_threshold: 0.9  # How similar invoices must be to be considered duplicates
```

#### Step 5.2: Add Environment Variable to Template

**File**: `patterns/pattern-2/template.yaml`

**Find the InvoiceExtractionFunction definition** (search for `InvoiceExtractionFunction:`)

**In the Environment Variables section, add:**

```yaml
      Environment:
        Variables:
          LOG_LEVEL: !Ref LogLevel
          EXTRACTION_RESULTS_TABLE: !Ref ExtractionResultsTable
          CONFIGURATION_TABLE: !Ref ConfigurationTable
          BEDROCK_MODEL_ID: !Ref BedrockModelId
          USE_CHUNKED_EXTRACTION: "true"  # NEW - Enable chunked extraction
```

---

### **Phase 6: Testing**

#### Step 6.1: Unit Test the ChunkedInvoiceExtractor

**File**: `tests/unit/test_chunked_invoice_extractor.py` (NEW FILE)

```python
"""Unit tests for ChunkedInvoiceExtractor"""

import pytest
from idp_common.extraction import ChunkedInvoiceExtractor


def test_create_chunks_basic():
    """Test basic chunk creation"""
    extractor = ChunkedInvoiceExtractor(chunk_size=100, overlap_size=20)
    
    pages = {
        "1": {"ocr_text": "A" * 50},
        "2": {"ocr_text": "B" * 50},
        "3": {"ocr_text": "C" * 50},
    }
    
    chunks = extractor.create_chunks_with_overlap(pages)
    
    assert len(chunks) > 0
    assert all(chunk.chunk_id for chunk in chunks)


def test_deduplication():
    """Test invoice deduplication"""
    extractor = ChunkedInvoiceExtractor()
    
    invoices = [
        {
            "invoice_number": "INV001",
            "total_amount": "100.00",
            "supplier_name": "Acme Corp",
            "chunk_id": "chunk_1"
        },
        {
            "invoice_number": "INV001",
            "total_amount": "100.00",
            "supplier_name": "Acme Corp",
            "invoice_date": "2024-01-01",  # More complete
            "chunk_id": "chunk_2"
        },
        {
            "invoice_number": "INV002",
            "total_amount": "200.00",
            "supplier_name": "Other Corp",
            "chunk_id": "chunk_1"
        }
    ]
    
    unique = extractor.deduplicate_invoices(invoices)
    
    assert len(unique) == 2  # Should keep INV001 (more complete) and INV002
    
    # The INV001 kept should be the more complete one
    inv001 = [i for i in unique if i["invoice_number"] == "INV001"][0]
    assert "invoice_date" in inv001


def test_similarity_key():
    """Test similarity key creation"""
    extractor = ChunkedInvoiceExtractor()
    
    invoice1 = {"invoice_number": "INV001", "total_amount": "£100.00"}
    invoice2 = {"invoice_number": "INV001", "total_amount": "100.00"}
    
    key1 = extractor._create_similarity_key(invoice1)
    key2 = extractor._create_similarity_key(invoice2)
    
    # Should normalize amounts
    assert key1 == key2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

#### Step 6.2: Integration Test

**File**: `tests/integration/test_invoice_extraction_chunked.py` (NEW FILE)

```python
"""Integration test for chunked invoice extraction"""

import boto3
import json
import os

def test_invoice_extraction_with_chunking():
    """
    Test invoice extraction with chunked processing.
    
    Prerequisites:
    - Deploy the stack with chunked extraction enabled
    - Upload a multi-invoice PDF (e.g., 10 invoices)
    - Set USE_CHUNKED_EXTRACTION=true
    """
    
    # TODO: Implement integration test
    # 1. Upload test document with 10+ invoices
    # 2. Wait for processing
    # 3. Query DynamoDB for extracted invoices
    # 4. Verify correct number extracted
    # 5. Verify no duplicates
    
    pass


if __name__ == "__main__":
    test_invoice_extraction_with_chunking()
```

#### Step 6.3: Manual Testing Steps

1. **Deploy the updated stack:**
   ```bash
   sam build
   sam deploy --guided
   ```

2. **Upload a multi-invoice test PDF:**
   - Use Web UI to upload an invoice PDF
   - Select "Invoice" as document type
   - Choose a PDF with 5-10 invoices

3. **Monitor CloudWatch Logs:**
   ```bash
   # Watch invoice extraction logs
   aws logs tail /aws/lambda/InvoiceExtractionFunction --follow
   ```

4. **Query DynamoDB for results:**
   ```bash
   aws dynamodb query \
     --table-name ExtractionResultsTable \
     --key-condition-expression "PK = :pk AND begins_with(SK, :sk)" \
     --expression-attribute-values '{
       ":pk": {"S": "user#YOUR_USER_ID#doc#YOUR_DOC_ID"},
       ":sk": {"S": "type#INVOICE"}
     }'
   ```

5. **Verify:**
   - ✅ Correct number of invoices extracted
   - ✅ No duplicate invoices
   - ✅ All invoices have required fields
   - ✅ Page numbers are accurate

---

## Configuration Options Summary

| **Parameter** | **Location** | **Default** | **Description** |
|---------------|--------------|-------------|-----------------|
| `trust_user_hint` | `config.yaml` → `classification` | `true` | Trust user document type without validation |
| `USE_CHUNKED_EXTRACTION` | Lambda env var | `true` | Enable chunked extraction for invoices |
| `chunk_size` | `config.yaml` → `extraction.chunking` | `15000` | Characters per chunk |
| `overlap_size` | `config.yaml` → `extraction.chunking` | `3000` | Overlap between chunks |
| `max_invoices_per_chunk` | `config.yaml` → `extraction.chunking` | `10` | Max invoices to extract per chunk |

---

## Troubleshooting

### Issue: Invoices still missing

**Check:**
1. CloudWatch logs for `InvoiceExtractionFunction`
2. Look for "Using CHUNKED extraction" log message
3. Verify `USE_CHUNKED_EXTRACTION=true` in Lambda environment
4. Check chunk sizes - may need to increase `chunk_size`

### Issue: Too many duplicates

**Solution:**
- Reduce `overlap_size` (currently 3000)
- Check deduplication logic is working (look for "Deduplication:" logs)

### Issue: Classification not using user hint

**Check:**
1. Verify S3 metadata contains `user-document-type`
2. Check `trust_user_hint=true` in config
3. Look for "User indicated document type" in classification logs

---

## Rollback Plan

If chunked extraction causes issues:

1. **Quick disable:**
   ```bash
   # Update Lambda environment variable
   aws lambda update-function-configuration \
     --function-name InvoiceExtractionFunction \
     --environment "Variables={USE_CHUNKED_EXTRACTION=false,...}"
   ```

2. **Full rollback:**
   ```bash
   # Revert to previous commit
   git revert HEAD
   sam build && sam deploy
   ```

---

## Success Criteria

✅ **Phase 1**: User can select document type on upload  
✅ **Phase 2**: Classification uses user hint when provided  
✅ **Phase 3**: ChunkedInvoiceExtractor class is functional  
✅ **Phase 4**: Invoice extraction uses chunking for multi-invoice PDFs  
✅ **Phase 5**: Configuration allows tuning chunk parameters  
✅ **Phase 6**: Tests pass and manual validation succeeds  

---

## Next Steps After Implementation

1. **Performance tuning:**
   - Monitor extraction times
   - Adjust chunk sizes based on model limits
   - Optimize overlap size for your documents

2. **Quality improvements:**
   - Collect extraction accuracy metrics
   - Refine deduplication logic if needed
   - Add confidence scoring for extracted invoices

3. **Feature enhancements:**
   - Support multi-page invoices (invoice spanning 2+ pages)
   - Add validation rules (e.g., total = sum of line items)
   - Implement human review for low-confidence extractions

---

## Support

For questions or issues during implementation:
1. Check CloudWatch logs for error messages
2. Review the inline code comments
3. Test each phase independently before moving to the next

**Good luck with the implementation!** 🚀
