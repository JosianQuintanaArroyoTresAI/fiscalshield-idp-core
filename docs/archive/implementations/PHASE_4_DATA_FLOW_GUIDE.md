# Phase 4: Data Flow & Integration Guide

## How Boundaries Flow Through the System

### Complete Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. CLASSIFICATION LAMBDA                                         │
│    patterns/pattern-2/src/classification_function/index.py      │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  service.classify_document(document)                            │
│    ↓                                                             │
│  for section in document.sections:                              │
│      if section.classification == 'invoice':                    │
│          section.attributes = {                                 │
│              'structure_hint': {...},                           │
│              'boundaries': [...],  # ← ADDED HERE               │
│              'fallback_chunking': {...}                         │
│          }                                                       │
│                                                                   │
│  document.serialize_document(working_bucket, "classification")  │
│    ↓                                                             │
│  Document.to_dict() serializes sections:                        │
│      section_dict["attributes"] = section.attributes  ← PRESERVED│
│                                                                   │
│  Return: {"document": {...sections with attributes...}}        │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. STEP FUNCTIONS WORKFLOW                                       │
│    patterns/pattern-2/statemachine/workflow.asl.json            │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ClassificationStep returns:                                    │
│      $.ClassificationResult.document                            │
│                                                                   │
│  ProcessSections (Map State):                                  │
│      ItemsPath: "$.ClassificationResult.document.sections"     │
│      Iterator Parameters:                                       │
│          {                                                       │
│              "section.$": "$$.Map.Item.Value",  ← Section obj   │
│              "document.$": "$.ClassificationResult.document"    │
│              "execution_arn.$": "$$.Execution.Id"               │
│          }                                                       │
│                                                                   │
│  RouteByDocumentType → InvoiceExtraction:                      │
│      Parameters:                                                │
│          {                                                       │
│              "document.$": "$.document",  ← FULL DOC + SECTIONS │
│              "section_id.$": "$.section.section_id"             │
│          }                                                       │
│                                                                   │
│  ✅ Full document (with all sections + attributes) is passed!  │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. INVOICE EXTRACTION LAMBDA                                     │
│    patterns/pattern-2/lambdas/invoice_extraction/...            │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  event = {                                                       │
│      "document": {...},  ← Compressed or inline dict            │
│      "section_id": "1"                                          │
│  }                                                               │
│                                                                   │
│  # Load document                                                │
│  if document_data.get('compressed'):                            │
│      document_dict = fetch_from_s3(document_data['s3_uri'])     │
│  else:                                                          │
│      document_dict = document_data                              │
│                                                                   │
│  # Find section                                                 │
│  sections = document_dict.get('sections', [])                  │
│  section_data = find_section_by_id(sections, section_id)       │
│                                                                   │
│  # Extract boundaries! ✨                                       │
│  pre_computed_boundaries = None                                 │
│  if 'attributes' in section_data:                              │
│      if 'boundaries' in section_data['attributes']:            │
│          pre_computed_boundaries = section_data['attributes']['boundaries'] │
│          # ↑ THIS IS WHERE WE GET THE BOUNDARIES!              │
│                                                                   │
│  # Use boundaries for optimal chunking                         │
│  if pre_computed_boundaries:                                   │
│      chunks = create_chunks_from_boundaries(text, boundaries)  │
│      # ← 1 chunk per invoice, no overlap! ✅                   │
│  else:                                                          │
│      chunks = semantic_or_overlap_chunking(text)  # Fallback  │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. Section.attributes Field

**File**: `lib/idp_common_pkg/idp_common/models.py`

```python
@dataclass
class Section:
    """Represents a section of pages with the same classification."""
    section_id: str
    classification: str
    confidence: float = 1.0
    page_ids: List[str] = field(default_factory=list)
    extraction_result_uri: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None  # ← KEY FIELD FOR METADATA
    confidence_threshold_alerts: List[Dict[str, Any]] = field(default_factory=list)
```

**Purpose**: Flexible metadata storage for any section-specific data

### 2. Document Serialization

**File**: `lib/idp_common_pkg/idp_common/models.py` (lines 302-311)

```python
def to_dict(self) -> Dict[str, Any]:
    """Convert document to dictionary representation."""
    ...
    # Convert sections
    result["sections"] = []
    for section in self.sections:
        section_dict = {
            "section_id": section.section_id,
            "classification": section.classification,
            "confidence": section.confidence,
            "page_ids": section.page_ids,
            "extraction_result_uri": section.extraction_result_uri,
            "confidence_threshold_alerts": section.confidence_threshold_alerts,
        }
        if section.attributes:  # ← Attributes included if present!
            section_dict["attributes"] = section.attributes
        result["sections"].append(section_dict)
```

**Critical**: `attributes` is conditionally included (only if not None/empty)

### 3. Step Functions Parameters

**File**: `patterns/pattern-2/statemachine/workflow.asl.json` (lines 60-73)

```json
"ProcessSections": {
    "Type": "Map",
    "ItemsPath": "$.ClassificationResult.document.sections",
    "Parameters": {
        "section.$": "$$.Map.Item.Value",
        "execution_arn.$": "$$.Execution.Id",
        "document.$": "$.ClassificationResult.document"  ← FULL DOCUMENT
    },
    "MaxConcurrency": 10,
    "Iterator": { ... }
}
```

**Key Point**: The FULL document (including all sections with their attributes) is passed to each Map iteration

### 4. InvoiceExtraction Step

**File**: `patterns/pattern-2/statemachine/workflow.asl.json` (lines 92-98)

```json
"InvoiceExtraction": {
    "Type": "Task",
    "Resource": "${InvoiceExtractionFunctionArn}",
    "Parameters": {
        "execution_arn.$": "$.execution_arn",
        "document.$": "$.document",        ← Full document with sections
        "section_id.$": "$.section.section_id"  ← Which section to process
    }
}
```

**Result**: Extraction Lambda receives:
- Full document (with ALL sections + attributes)
- Specific section_id to process

## Why No Workflow Changes Needed

### The Genius of the Current Design

1. **Document is a Data Container**
   - Classification enriches `document.sections[].attributes`
   - Document is passed through workflow unchanged
   - Extraction Lambda reads from the enriched document

2. **Step Functions is Just Routing**
   - No awareness of structure analysis
   - Just passes data: Classification → Extraction
   - Works with any section attributes

3. **Backward Compatible**
   - If `attributes` is None → fallback chunking
   - If `attributes.boundaries` exists → optimal chunking
   - Old code continues to work!

## Testing the Flow

### Verify Boundaries in CloudWatch

**Classification Lambda Logs**:
```
🔍 Analyzing structure for invoice section 1
📊 Structure Analysis: 101 invoices, pattern: 'Invoice Number:'
✅ Added structure hint (252000 chars, needs boundary detection)
```

**Step Functions Execution**:
```json
{
  "ClassificationResult": {
    "document": {
      "sections": [
        {
          "section_id": "1",
          "classification": "invoice",
          "attributes": {
            "boundaries": [ ... ],  ← CHECK THIS!
            "fallback_chunking": { ... }
          }
        }
      ]
    }
  }
}
```

**Extraction Lambda Logs**:
```
📋 Section data keys: ['section_id', 'classification', 'page_ids', 'attributes']
✨ Found pre-computed boundaries: 101 invoices (from classification structure analysis)
📚 Using 101 PRE-COMPUTED chunks (1 invoice per chunk)
```

### Verify in DynamoDB (TrackingTable)

```sql
# Check section metadata
PK: document#<docId>
SK: section#1

Attributes:
{
  "section_id": "1",
  "classification": "invoice",
  "attributes": {
    "boundaries": [...],  ← Should be here
    "fallback_chunking": {...}
  }
}
```

## Potential Issues & Solutions

### Issue 1: Attributes Not Serialized

**Symptom**: Extraction logs show "No boundaries found"

**Cause**: `section.attributes` is None or empty

**Debug**:
```python
# In classification_function/index.py (after structure analysis)
logger.info(f"Section attributes: {json.dumps(section.attributes, default=str)}")
```

**Fix**: Ensure `section.attributes` is initialized before adding data:
```python
if not section.attributes:
    section.attributes = {}
section.attributes['boundaries'] = boundaries
```

### Issue 2: Document Compressed - Attributes Lost

**Symptom**: Large documents get compressed, attributes missing after decompression

**Cause**: Compression/decompression bug (unlikely but possible)

**Debug**:
```python
# In invoice_extraction_handler.py
logger.info(f"Document data type: {type(document_data)}")
logger.info(f"Is compressed: {document_data.get('compressed', False)}")
logger.info(f"Sections count: {len(document_dict.get('sections', []))}")
logger.info(f"First section keys: {list(sections[0].keys()) if sections else 'none'}")
```

**Fix**: Check `Document.compress()` and `Document.decompress()` preserve attributes

### Issue 3: Step Functions Timeout

**Symptom**: Classification completes but extraction never starts

**Cause**: Document too large for Step Functions parameter size limit (256KB)

**Solution**: Already handled by `serialize_document()` auto-compression

## Summary

### ✅ No Workflow Changes Needed Because:

1. **Classification already passes full document to Map state**
2. **Map state already passes full document to extraction Lambda**
3. **Section.attributes already serialized by Document.to_dict()**
4. **Extraction Lambda already receives full sections array**

### 🎯 What We Added:

1. **Classification**: Populate `section.attributes['boundaries']`
2. **Extraction**: Read `section_data['attributes']['boundaries']`
3. **Helper Function**: `create_chunks_from_boundaries()`

### 🚀 Result:

**Zero workflow changes, maximum impact!**

The architecture was already designed to support this enhancement. We just:
- Added metadata at Classification
- Consumed metadata at Extraction
- Step Functions transparently passes it through

This is **exactly how good architecture should work** - extensible without modification! 🎉
