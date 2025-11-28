# Smart Chunking Implementation Plan
## Page-Level Header/Footer Detection + Cost-Efficient Batching

**Date:** November 28, 2025  
**Status:** Planning - Not Implemented  
**Goal:** Handle 100+ invoice documents efficiently without timeouts, maintaining batch extraction cost savings

---

## ACTUAL PIPELINE (Current State)

```
┌─────────────────────────────────────────────────────────────────────┐
│ Step 1: Document Upload → S3                                        │
├─────────────────────────────────────────────────────────────────────┤
│ User uploads PDF to S3 bucket                                       │
│ → Triggers Step Functions workflow execution                        │
└─────────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Step 2: OCR Lambda (OCRFunction)                                    │
├─────────────────────────────────────────────────────────────────────┤
│ File: patterns/pattern-2/src/ocr_function/index.py                 │
│                                                                      │
│ Input: PDF file from S3                                             │
│ Process:                                                             │
│   1. Converts PDF to images (one per page)                          │
│   2. Calls AWS Textract OR Amazon Nova (configurable)               │
│   3. Extracts text from each page                                   │
│   4. Stores per-page results:                                       │
│      - page.image_uri → S3 (PNG image)                              │
│      - page.raw_text_uri → S3 (text file per page)                  │
│      - page.parsed_text_uri → S3 (structured text per page)         │
│                                                                      │
│ Output: Document object with pages[] populated                      │
│   - document.pages = {                                              │
│       "1": {image_uri, raw_text_uri, parsed_text_uri},             │
│       "2": {image_uri, raw_text_uri, parsed_text_uri},             │
│       ...                                                            │
│     }                                                                │
│   - NO sections created yet                                         │
│   - NO classification done yet                                      │
└─────────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Step 3: Classification Lambda (ClassificationFunction)              │
├─────────────────────────────────────────────────────────────────────┤
│ File: patterns/pattern-2/src/classification_function/index.py      │
│                                                                      │
│ Input: Document with OCR text (pages populated)                     │
│ Process:                                                             │
│   1. Parallel page classification (20 workers via ThreadPoolExecutor)│
│      For each page:                                                  │
│        - Load page.raw_text_uri from S3                             │
│        - Load page.image_uri from S3                                │
│        - Call Bedrock LLM to classify:                              │
│          → page.classification = "invoice" | "bank-statement" | etc.│
│          → page.confidence = 0.95                                   │
│          → page.metadata['document_boundary'] = "start" | "continue"│
│                                                                      │
│   2. Group pages into sections based on document_boundary:           │
│      Algorithm (in service.py line 506-544):                        │
│        current_section_pages = []                                   │
│        for page in sorted_pages:                                    │
│            boundary = page.metadata['document_boundary']            │
│            if boundary == "start":                                  │
│                # New section starts!                                │
│                sections.append(Section(pages=current_section_pages))│
│                current_section_pages = [page]                       │
│            else:  # boundary == "continue"                          │
│                current_section_pages.append(page)                   │
│                                                                      │
│      Example with 10 invoices (20 pages):                           │
│        - Page 1: boundary="start" → Section 1 starts               │
│        - Page 2: boundary="continue" → Section 1 continues          │
│        - Page 3: boundary="start" → Section 2 starts               │
│        - Page 4: boundary="start" → Section 3 starts               │
│        ...                                                           │
│        Result: 10 sections created (one per invoice)                │
│                                                                      │
│   3. (Optional) Structure analysis for complex sections:            │
│      - Only runs if section has MANY pages (e.g., 50+)             │
│      - Loads pages for that section into memory                     │
│      - Detects sub-boundaries within section                        │
│      - Stores in section.attributes['boundaries']                   │
│                                                                      │
│ Output: Document object with sections[] populated                   │
│   - document.sections = [                                           │
│       Section(id="1", classification="invoice", page_ids=[1,2]),   │
│       Section(id="2", classification="invoice", page_ids=[3]),     │
│       Section(id="3", classification="invoice", page_ids=[4,5,6]), │
│       ...                                                            │
│     ]                                                                │
│   - ✅ Multiple sections already created based on document_boundary!│
│   - ⚠️ BUT: Only if LLM sets boundary="start" correctly            │
└─────────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Step 4: Step Functions Map State (ProcessSections)                  │
├─────────────────────────────────────────────────────────────────────┤
│ File: patterns/pattern-3/statemachine/workflow.asl.json            │
│                                                                      │
│ Type: "Map"                                                          │
│ ItemsPath: "$.ClassificationResult.document.sections"              │
│ MaxConcurrency: 10                                                   │
│                                                                      │
│ Iterates over document.sections array:                              │
│   For each section:                                                  │
│     - Invokes ExtractionFunction Lambda                             │
│     - Passes: {                                                      │
│         section_id: "1",                                            │
│         document: <full_document_object>                            │
│       }                                                              │
│                                                                      │
│ Example with 10 invoices (20 pages):                                │
│   DEV (working): 5 sections → 5 Lambda invocations (parallel!)     │
│   PROD (bug): 1 section → 1 Lambda invocation (timeout!)           │
│                                                                      │
│ ⚠️ THE BUG: LLM in production doesn't set document_boundary="start"│
│    correctly, so all pages get grouped into ONE section!            │
└─────────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Step 5: Extraction Lambda (ExtractionFunction OR InvoiceExtraction) │
├─────────────────────────────────────────────────────────────────────┤
│ Files:                                                               │
│  - patterns/pattern-2/src/extraction_function/index.py (generic)    │
│  - patterns/pattern-2/lambdas/invoice_extraction/... (specialized)  │
│                                                                      │
│ Input: {section_id: "1", document: {...}}                          │
│ Process:                                                             │
│   1. Extract section from document.sections by section_id           │
│   2. Load text for pages in section.page_ids:                       │
│      section_text = ""                                              │
│      for page_id in section.page_ids:                               │
│          page_text = load_from_s3(page.raw_text_uri)                │
│          section_text += f"\n[PAGE:{page_id}]\n{page_text}"        │
│                                                                      │
│   3. (Current) Chunking logic:                                      │
│      if USE_CHUNKED_EXTRACTION and len(section_text) > 60000:      │
│          chunks = create_semantic_chunks(section_text)              │
│          for chunk in chunks:                                       │
│              invoices += extract_from_chunk(chunk)                  │
│          deduplicate_invoices(invoices)                             │
│      else:                                                           │
│          prompt = template.format(section_text=section_text)        │
│          xml = invoke_bedrock(prompt)  ← BATCH EXTRACTION!         │
│          invoices = parse_xml(xml)                                  │
│                                                                      │
│   4. Write extracted invoices to DynamoDB (ExtractionResultsTable)  │
│                                                                      │
│ Output: {section_id: "1", invoices_extracted: 10}                  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## KEY INSIGHT: The Batching Happens in Bedrock Prompt!

**You're right!** The extraction lambda processes **multiple invoices in ONE Bedrock call** by sending the full section text to the LLM, which then extracts ALL invoices and returns them as an XML array:

```xml
<invoices>
  <invoice>
    <invoice_number>INV-001</invoice_number>
    <supplier_name>ABC Ltd</supplier_name>
    ...
  </invoice>
  <invoice>
    <invoice_number>INV-002</invoice_number>
    <supplier_name>XYZ Corp</supplier_name>
    ...
  </invoice>
  ...
</invoices>
```

This is **cost-efficient** because:
- 1 Bedrock API call extracts 10 invoices
- vs. 10 separate API calls if done individually

---

## Problem Statement

**Current Issues with 100+ Invoice Documents:**
- ❌ Classification Lambda loads all 100+ pages into memory (6+ MB)
- ❌ Sequential boundary detection times out at ~60 seconds
- ❌ Semantic chunking with 60k char chunks creates overlap/deduplication overhead
- ❌ Single extraction Lambda processes all invoices sequentially

**Current Strength to Preserve:**
- ✅ Batch extraction: 10 invoices extracted in 1 Bedrock call (cost-efficient!)
- ✅ Parallel page classification: 20 workers process pages concurrently
- ✅ Step Functions Map state enables parallel section processing

---

## Proposed Solution: Hybrid Approach

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 1: Classification Lambda (Page-Level Analysis)           │
├─────────────────────────────────────────────────────────────────┤
│ ThreadPoolExecutor (20 workers) - Parallel page processing     │
│                                                                  │
│ For each page:                                                  │
│   1. Classify type: "invoice" | "bank-statement" | etc.        │
│   2. Detect invoice_boundary: "start" | "continue"             │
│   3. Detect invoice_markers:                                    │
│      - has_header: bool (e.g., "Invoice Number:", "Bill To:")  │
│      - has_total: bool (e.g., "AMOUNT DUE", "Total GBP")       │
│      - has_grand_total: bool (summary across multiple invoices)│
│      - invoice_number: str (for validation)                    │
│      - page_hash: str (for Merkle tree validation)             │
│                                                                  │
│ Result: 100 pages analyzed in ~20 seconds (parallel)           │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 2: Invoice Boundary Assembly (Sequential - Fast)         │
├─────────────────────────────────────────────────────────────────┤
│ Linear scan through pages to identify invoice boundaries:      │
│                                                                  │
│ Algorithm:                                                      │
│   boundaries = []                                               │
│   current_invoice = None                                        │
│                                                                  │
│   for page in sorted_pages:                                     │
│       if page.has_header AND page.boundary == "start":          │
│           # New invoice starts here                             │
│           if current_invoice:                                   │
│               boundaries.append(current_invoice)                │
│           current_invoice = {                                   │
│               'start_page': page.id,                            │
│               'pages': [page.id],                               │
│               'invoice_number': page.invoice_number             │
│           }                                                      │
│       elif current_invoice:                                     │
│           # Continuation of current invoice                     │
│           current_invoice['pages'].append(page.id)              │
│                                                                  │
│           if page.has_total:                                    │
│               # Invoice complete                                │
│               current_invoice['end_page'] = page.id             │
│               current_invoice['complete'] = True                │
│                                                                  │
│   # Validation                                                  │
│   headers_detected = count(page.has_header)                     │
│   totals_detected = count(page.has_total)                       │
│   grand_totals = count(page.has_grand_total)                    │
│                                                                  │
│   expected_invoices = totals_detected - grand_totals            │
│   if headers_detected != expected_invoices:                     │
│       log_warning("Boundary detection mismatch!")               │
│                                                                  │
│ Result: 50 invoice boundaries identified in ~2 seconds          │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 3: Smart Batching (Cost-Efficient Grouping)              │
├─────────────────────────────────────────────────────────────────┤
│ Group invoices into batches of 3-5 invoices per section:       │
│                                                                  │
│ Algorithm:                                                      │
│   BATCH_SIZE = 5  # Configurable (3-10 invoices)               │
│   sections = []                                                 │
│                                                                  │
│   for batch in chunk(boundaries, size=BATCH_SIZE):              │
│       section_pages = []                                        │
│       for invoice in batch:                                     │
│           section_pages.extend(invoice['pages'])                │
│                                                                  │
│       sections.append(Section(                                  │
│           section_id=str(len(sections) + 1),                    │
│           classification='invoice',                             │
│           page_ids=section_pages,                               │
│           attributes={                                          │
│               'invoice_count': len(batch),                      │
│               'invoice_boundaries': batch,                      │
│               'batching_strategy': 'smart_boundary_batching'    │
│           }                                                      │
│       ))                                                         │
│                                                                  │
│ Result: 50 invoices → 10 sections (5 invoices each)            │
│         Each section triggers ONE parallel extraction Lambda    │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 4: Step Functions Map State (Parallel Processing)        │
├─────────────────────────────────────────────────────────────────┤
│ ProcessSections (MaxConcurrency: 10)                            │
│   ├─ Section 1 → ExtractionLambda (Invoices 1-5)   [Parallel] │
│   ├─ Section 2 → ExtractionLambda (Invoices 6-10)  [Parallel] │
│   ├─ Section 3 → ExtractionLambda (Invoices 11-15) [Parallel] │
│   └─ ...10 sections total                                       │
│                                                                  │
│ Result: 10 parallel Lambda invocations process 50 invoices     │
│         Total time: ~30 seconds (vs. 300+ seconds sequential)  │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 5: Extraction Lambda (Batch Processing - No Chunking!)   │
├─────────────────────────────────────────────────────────────────┤
│ Receives: Section with 5 invoices (e.g., pages [1-15])         │
│                                                                  │
│ Processing:                                                     │
│   # Load section text                                           │
│   section_text = ""                                             │
│   for page_id in section.page_ids:                              │
│       section_text += get_page_text(page_id)                    │
│                                                                  │
│   # NO CHUNKING - section already contains exact invoices!     │
│   invoice_boundaries = section.attributes['invoice_boundaries'] │
│                                                                  │
│   # Single Bedrock call for all invoices in section             │
│   prompt = template.format(                                     │
│       section_text=section_text,                                │
│       expected_invoices=len(invoice_boundaries)                 │
│   )                                                              │
│   xml_response = invoke_bedrock(prompt)                         │
│   invoices = parse_invoices_from_xml(xml_response)              │
│                                                                  │
│   # Validation: Did we extract expected number?                 │
│   if len(invoices) != len(invoice_boundaries):                  │
│       log_warning(f"Expected {len(invoice_boundaries)} but "    │
│                   f"extracted {len(invoices)}")                  │
│                                                                  │
│   # Write all invoices to DynamoDB                              │
│   for invoice in invoices:                                      │
│       write_invoice_to_dynamodb(invoice, ...)                   │
│                                                                  │
│ Result: 5 invoices extracted in 1 Bedrock call                 │
│         Cost: 1 prompt (vs. 5 prompts if individual)           │
│         NO DEDUPLICATION NEEDED (no overlap!)                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Detailed Component Changes

### 1. Enhanced Page Classification Prompt

**File:** Configuration stored in DynamoDB `ConfigurationTable`  
**Current:** Prompt only detects page type and `document_boundary`  
**New:** Add invoice marker detection

**Enhanced Response Schema:**
```json
{
  "class": "invoice",
  "confidence": 0.95,
  "document_boundary": "start",
  "invoice_markers": {
    "has_header": true,
    "has_total": false,
    "has_grand_total": false,
    "confidence": {
      "header": 0.98,
      "total": 0.0,
      "grand_total": 0.0
    },
    "detected_patterns": {
      "invoice_number": "INV-12345",
      "amount_due": null,
      "page_position": "top_section"
    }
  },
  "page_hash": "sha256:abc123..."
}
```

**Prompt Enhancement:**
```
TASK: Classify this page AND detect invoice structural markers.

1. PAGE TYPE CLASSIFICATION:
   - invoice
   - bank-statement
   - receipt
   - other

2. INVOICE BOUNDARY DETECTION (if type=invoice):
   - document_boundary: "start" | "continue"
   
   "start" indicators:
   - Fresh "Invoice Number:" or "Reference Number:" at top
   - "Bill To:" or "To:" header section
   - Company letterhead/logo at page top
   - New invoice date (not continuation of line items)
   
   "continue" indicators:
   - Mid-page start (continuation of previous page)
   - Line items without header
   - Subtotals (not final total)

3. INVOICE MARKERS (if type=invoice):
   
   has_header (bool):
   - "Invoice Number:", "Bill To:", company name at top
   - Fresh invoice metadata (not continuation)
   
   has_total (bool):
   - "AMOUNT DUE", "Total GBP", "Balance Due"
   - Final payment amount
   - Payment terms/due date nearby
   - "Thank you for your business" footer
   
   has_grand_total (bool):
   - "Grand Total" (summary across multiple invoices)
   - "Total for All Invoices"
   - Multi-invoice summary table

4. VALIDATION DATA (if type=invoice):
   - invoice_number: Extract if visible
   - amount_due: Extract if has_total=true
   - page_position: "top_section" | "middle" | "bottom_section"

RESPOND IN JSON:
{
  "class": "...",
  "confidence": 0.0-1.0,
  "document_boundary": "start" | "continue",
  "invoice_markers": {
    "has_header": bool,
    "has_total": bool,
    "has_grand_total": bool,
    "confidence": {
      "header": 0.0-1.0,
      "total": 0.0-1.0,
      "grand_total": 0.0-1.0
    },
    "detected_patterns": {
      "invoice_number": "..." or null,
      "amount_due": "..." or null,
      "page_position": "..."
    }
  }
}
```

### 2. Classification Lambda Handler Updates

**File:** `patterns/pattern-2/src/classification_function/index.py`

**Current Behavior:**
```python
# After parallel page classification
for section in document.sections:
    if section.classification.lower() == 'invoice':
        # Load ALL pages (SLOW, memory intensive)
        section_text = combine_all_pages(section.page_ids)
        boundaries = detector.detect_boundaries(section_text)
```

**New Behavior:**
```python
# After parallel page classification
invoice_pages = [p for p in document.pages.values() if p.classification == 'invoice']

# PHASE 2: Assemble invoice boundaries (fast, O(n) scan)
invoice_boundaries = []
current_invoice = None

for page in sorted(invoice_pages, key=lambda p: p.page_id):
    markers = page.metadata.get('invoice_markers', {})
    boundary = page.metadata.get('document_boundary', 'continue')
    
    # New invoice starts here
    if markers.get('has_header') and boundary == 'start':
        if current_invoice:
            invoice_boundaries.append(current_invoice)
        
        current_invoice = {
            'id': len(invoice_boundaries) + 1,
            'start_page': page.page_id,
            'pages': [page.page_id],
            'invoice_number': markers.get('detected_patterns', {}).get('invoice_number'),
            'complete': False
        }
    elif current_invoice:
        # Continuation of current invoice
        current_invoice['pages'].append(page.page_id)
        
        # Check if invoice is complete
        if markers.get('has_total'):
            current_invoice['end_page'] = page.page_id
            current_invoice['complete'] = True
            current_invoice['amount_due'] = markers.get('detected_patterns', {}).get('amount_due')

# Add final invoice
if current_invoice:
    invoice_boundaries.append(current_invoice)

# VALIDATION: Cross-check counts
headers_count = sum(1 for p in invoice_pages if p.metadata.get('invoice_markers', {}).get('has_header'))
totals_count = sum(1 for p in invoice_pages if p.metadata.get('invoice_markers', {}).get('has_total'))
grand_totals = sum(1 for p in invoice_pages if p.metadata.get('invoice_markers', {}).get('has_grand_total'))

expected_invoices = totals_count - grand_totals
detected_invoices = len(invoice_boundaries)

logger.info(f"Invoice boundary validation:")
logger.info(f"  Headers detected: {headers_count}")
logger.info(f"  Totals detected: {totals_count}")
logger.info(f"  Grand totals: {grand_totals}")
logger.info(f"  Expected invoices: {expected_invoices}")
logger.info(f"  Detected invoices: {detected_invoices}")

if abs(detected_invoices - expected_invoices) > 1:  # Allow 1 invoice tolerance
    logger.warning(
        f"Boundary detection mismatch: expected ~{expected_invoices}, "
        f"detected {detected_invoices}. Review may be needed."
    )

# PHASE 3: Smart batching (group invoices into cost-efficient sections)
BATCH_SIZE = int(os.environ.get('INVOICE_BATCH_SIZE', '5'))  # 3-10 invoices per section
sections = []

for i in range(0, len(invoice_boundaries), BATCH_SIZE):
    batch = invoice_boundaries[i:i + BATCH_SIZE]
    
    # Collect all pages for this batch
    section_pages = []
    for invoice in batch:
        section_pages.extend(invoice['pages'])
    
    section = Section(
        section_id=str(len(sections) + 1),
        classification='invoice',
        confidence=1.0,
        page_ids=section_pages,
        attributes={
            'invoice_count': len(batch),
            'invoice_boundaries': batch,
            'batching_strategy': 'smart_boundary_batching',
            'batch_size': len(batch),
            'expected_extractions': len(batch)
        }
    )
    
    sections.append(section)

document.sections = sections

logger.info(
    f"Created {len(sections)} sections from {len(invoice_boundaries)} invoices "
    f"({BATCH_SIZE} invoices/section)"
)
```

### 3. Extraction Lambda Simplification

**File:** `patterns/pattern-2/lambdas/invoice_extraction/invoice_extraction_handler.py`

**Current Behavior:**
```python
# Complex chunking logic
if USE_CHUNKED_EXTRACTION and len(section_text) > CHUNK_SIZE:
    chunks = extractor.create_semantic_chunks(section_text)
    for chunk in chunks:
        invoices = extract_from_chunk(chunk)
    deduplicate_invoices(invoices)
```

**New Behavior (Simplified):**
```python
# Get section metadata
invoice_count = section.attributes.get('invoice_count', 1)
invoice_boundaries = section.attributes.get('invoice_boundaries', [])
batching_strategy = section.attributes.get('batching_strategy', 'unknown')

logger.info(
    f"Processing section {section_id} with {invoice_count} invoices "
    f"(strategy: {batching_strategy})"
)

# Load section text (already scoped to exact invoice boundaries!)
section_text = ""
for page_id in section.page_ids:
    page_text = get_page_text(page_id)
    section_text += f"\n[PAGE:{page_id}]\n{page_text}"

# Get extraction prompt
prompt_template = get_invoice_extraction_prompt()

# Enhance prompt with expected count
prompt = prompt_template.format(
    section_text=section_text,
    expected_invoice_count=invoice_count,
    invoice_boundaries_hint=json.dumps(invoice_boundaries, indent=2)
)

# Single Bedrock call for entire batch
xml_response = invoke_bedrock(prompt)
invoices = parse_invoices_from_xml(xml_response)

# Validation: Did we extract the expected number?
if len(invoices) != invoice_count:
    logger.warning(
        f"Extraction mismatch: expected {invoice_count} invoices, "
        f"extracted {len(invoices)}. Boundaries: {invoice_boundaries}"
    )
    
    # Flag for HITL review
    for invoice in invoices:
        invoice['extraction_quality'] = 'needs_review'
        invoice['extraction_warning'] = f'Expected {invoice_count}, got {len(invoices)}'

# NO DEDUPLICATION NEEDED - boundaries are exact!

# Write all invoices to DynamoDB
for idx, invoice in enumerate(invoices):
    invoice['batch_index'] = idx
    invoice['batch_size'] = invoice_count
    invoice['batching_strategy'] = batching_strategy
    write_invoice_to_dynamodb(invoice, ...)
```

### 4. Enhanced Extraction Prompt

**Update the prompt template to leverage boundary metadata:**

```xml
CONTEXT:
This text contains EXACTLY {expected_invoice_count} complete invoices.
Invoice boundaries have been pre-identified:

{invoice_boundaries_hint}

Each invoice spans the indicated pages. Extract ALL invoices.

IMPORTANT VALIDATION:
- You MUST extract exactly {expected_invoice_count} invoices
- If you extract fewer, you missed an invoice - review carefully
- If you extract more, you split one invoice incorrectly
- Cross-reference invoice numbers with the boundary hints above

[... rest of existing prompt ...]
```

---

## Merkle Tree Validation (Optional Enhancement)

**Purpose:** Ensure page integrity and detect missing/duplicate pages

**Implementation:**
```python
# In Classification Lambda (after page analysis)
import hashlib

page_hashes = []
for page in sorted(document.pages.values(), key=lambda p: p.page_id):
    # Hash page content
    page_text = get_page_text(page.page_id)
    page_hash = hashlib.sha256(page_text.encode()).hexdigest()[:16]
    
    page.metadata['page_hash'] = page_hash
    page_hashes.append(page_hash)

# Build Merkle tree
def build_merkle_tree(hashes):
    if len(hashes) == 1:
        return hashes[0]
    
    next_level = []
    for i in range(0, len(hashes), 2):
        if i + 1 < len(hashes):
            combined = hashlib.sha256(
                (hashes[i] + hashes[i+1]).encode()
            ).hexdigest()[:16]
        else:
            combined = hashes[i]
        next_level.append(combined)
    
    return build_merkle_tree(next_level)

merkle_root = build_merkle_tree(page_hashes)

document.metadata['merkle_root'] = merkle_root
document.metadata['page_count'] = len(page_hashes)
document.metadata['page_hashes'] = page_hashes

logger.info(f"Merkle tree validation: {len(page_hashes)} pages, root={merkle_root}")

# In Extraction Lambda (validation)
expected_root = document.metadata.get('merkle_root')
expected_pages = document.metadata.get('page_count')

if len(section.page_ids) != expected_pages:
    logger.warning(
        f"Page count mismatch: expected {expected_pages}, "
        f"processing {len(section.page_ids)}"
    )
```

---

## Performance Analysis

### Current System (100 invoices, 150 pages)

| Phase | Time | Memory | Cost |
|-------|------|--------|------|
| Classification (parallel) | 20s | 200 MB | $0.01 |
| Structure Analysis (sequential) | 60s+ | 6+ GB | - |
| **TIMEOUT** | ❌ | ❌ | - |

### Proposed System (100 invoices, 150 pages)

| Phase | Time | Memory | Cost | Parallel |
|-------|------|--------|------|----------|
| Page Classification | 20s | 200 MB | $0.01 | 20 workers |
| Boundary Assembly | 2s | 10 MB | - | Sequential |
| Smart Batching | 1s | 5 MB | - | Sequential |
| Step Functions Map | - | - | - | 10 sections |
| Extraction (per section) | 25s | 100 MB | $0.02 | 10 parallel |
| **Total** | **~48s** | **100 MB** | **$0.23** | ✅ |

**Benefits:**
- ✅ **75% faster** (48s vs. 180s estimated)
- ✅ **95% less memory** (100 MB vs. 6 GB)
- ✅ **No timeout risk** (all operations < 60s)
- ✅ **Cost-efficient** (batch extraction preserved)
- ✅ **Scalable** (works with 1000+ invoices)

---

## Configuration Parameters

**Environment Variables:**

```yaml
# Classification Lambda
MAX_WORKERS: 20                    # Parallel page classification workers
INVOICE_BATCH_SIZE: 5               # Invoices per section (3-10 recommended)
ENABLE_MERKLE_VALIDATION: true      # Optional integrity checking
ENABLE_BOUNDARY_VALIDATION: true    # Cross-check header/total counts

# Extraction Lambda
USE_CHUNKED_EXTRACTION: false       # DISABLE old chunking (no longer needed)
VALIDATE_EXTRACTION_COUNT: true     # Verify extracted count matches expected
```

---

## Migration Strategy

### Phase 1: Update Classification (Week 1)
1. ✅ Update classification prompt to detect invoice markers
2. ✅ Add boundary assembly logic to classification handler
3. ✅ Add smart batching logic
4. ✅ Test with small documents (1-10 invoices)

### Phase 2: Update Extraction (Week 2)
1. ✅ Simplify extraction lambda (remove chunking)
2. ✅ Add validation logic (expected count)
3. ✅ Update extraction prompt with boundary hints
4. ✅ Test with medium documents (10-50 invoices)

### Phase 3: Production Testing (Week 3)
1. ✅ Test with large documents (50-200 invoices)
2. ✅ Monitor CloudWatch metrics
3. ✅ Validate cost savings
4. ✅ Gradual rollout to production

### Phase 4: Optimization (Week 4)
1. ✅ Add Merkle tree validation (optional)
2. ✅ Tune BATCH_SIZE based on metrics
3. ✅ Add automated alerting for mismatches
4. ✅ Documentation and training

---

## Rollback Plan

If issues arise, system can rollback gracefully:

```python
# Feature flag in configuration
USE_SMART_BATCHING = os.environ.get('USE_SMART_BATCHING', 'false').lower() == 'true'

if USE_SMART_BATCHING:
    # New approach
    sections = create_smart_batched_sections(invoice_boundaries)
else:
    # Old approach (fallback)
    sections = create_single_section(all_pages)
```

---

## Success Metrics

**KPIs to Track:**

1. **Processing Time**
   - Target: < 60s for 100 invoice documents
   - Current: Timeout at 60s+

2. **Accuracy**
   - Target: 99% correct invoice boundary detection
   - Measured by: (headers == totals - grand_totals)

3. **Cost Efficiency**
   - Target: Maintain batch extraction cost savings
   - Measured by: Bedrock API calls / invoices extracted

4. **Timeout Rate**
   - Target: 0% timeout rate
   - Current: ~100% for 100+ invoice documents

5. **Memory Usage**
   - Target: < 500 MB per Lambda invocation
   - Current: 6+ GB in structure analysis

---

## Open Questions

1. **Optimal Batch Size:** Should it be 3, 5, or 10 invoices per section?
   - Tradeoff: Smaller batches = more parallel = faster, but more API calls = higher cost
   - Recommendation: Start with 5, tune based on metrics

2. **Merkle Tree Overhead:** Is the validation worth the compute cost?
   - Tradeoff: Extra CPU for hashing vs. confidence in page integrity
   - Recommendation: Optional feature, enable for critical workflows

3. **Grand Total Handling:** How to distinguish multi-invoice summaries from single invoice totals?
   - Pattern: "Grand Total" vs. "Total" vs. "Amount Due"
   - Recommendation: Add LLM-based detection in enhanced prompt

4. **Incomplete Invoice Handling:** What if an invoice has header but no total (split across sections)?
   - Current plan: Flag as `complete: false`, merge in post-processing
   - Alternative: Look ahead to next section if current ends without total

---

## Next Steps

**Before Implementation:**
1. ✅ Review this plan with team
2. ✅ Decide on BATCH_SIZE (3, 5, or 10)
3. ✅ Decide on Merkle tree (yes/no)
4. ✅ Approve enhanced classification prompt
5. ✅ Set timeline for phased rollout

**After Approval:**
1. Create feature branch: `feature/smart-chunking`
2. Implement Phase 1 (Classification updates)
3. Test with sample documents
4. Proceed to Phase 2 if successful

---

## Appendix: Example Output

**100 Invoice Document (150 pages):**

```json
{
  "document_id": "doc-12345",
  "total_pages": 150,
  "classification_result": {
    "invoice_pages": 150,
    "headers_detected": 100,
    "totals_detected": 100,
    "grand_totals_detected": 0,
    "expected_invoices": 100,
    "invoice_boundaries": [
      {"id": 1, "pages": [1], "complete": true},
      {"id": 2, "pages": [2, 3], "complete": true},
      {"id": 3, "pages": [4], "complete": true},
      ...
      {"id": 100, "pages": [150], "complete": true}
    ]
  },
  "batching_result": {
    "batch_size": 5,
    "sections_created": 20,
    "section_breakdown": [
      {"section_id": "1", "invoices": [1, 2, 3, 4, 5], "pages": [1, 2, 3, 4, 5, 6, 7, 8]},
      {"section_id": "2", "invoices": [6, 7, 8, 9, 10], "pages": [9, 10, 11, 12, 13, 14]},
      ...
    ]
  },
  "extraction_result": {
    "sections_processed": 20,
    "parallel_executions": 10,
    "total_time_seconds": 48,
    "invoices_extracted": 100,
    "extraction_quality": {
      "perfect_matches": 98,
      "needs_review": 2
    }
  }
}
```

---

**END OF IMPLEMENTATION PLAN**
