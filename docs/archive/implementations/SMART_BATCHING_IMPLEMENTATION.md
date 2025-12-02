# Smart Batching Implementation - Complete Invoice Processing

## Problem Statement

**Issue**: Timeouts when processing 100+ invoice documents
- Classification lambda exceeds 60-second timeout
- All invoices grouped into 1 section instead of multiple sections
- Production bug: `document_boundary` not set correctly

**Root Cause**: Classification prompt not explicit enough about invoice boundary detection

## Solution: Two-Phase Smart Batching

### Phase 1: Enhanced Classification Prompt
Updated classification prompt with explicit invoice boundary detection rules:
- Clear rules for invoice start/end detection
- Separate logic for invoices vs bank statements
- Explicit `document_boundary` setting: 'start' or 'continue'

**File**: `config_library/pattern-2/fiscalshield-production/config.yaml`

### Phase 2: SmartBatcher Class
Created intelligent batching algorithm to group pages into optimal sections:
- **Target**: 10 pages per batch (flexible)
- **Max**: 30 pages per batch (safety limit)
- **Max Invoices**: 20 per batch
- **Key Constraint**: Batches contain ONLY complete invoices

**File**: `lib/idp_common_pkg/idp_common/classification/smart_batcher.py`

## Architecture

```
┌─────────────┐
│  OCR Lambda │ → Convert PDF to text (page by page)
└─────────────┘
       ↓
┌─────────────────────┐
│ Classification      │ → Parallel classification (20 workers)
│ - Claude 3 Haiku    │   + Document boundary detection
│ - SmartBatcher      │   + Group into optimal batches
└─────────────────────┘
       ↓
┌─────────────────────┐
│ Step Functions Map  │ → Parallel extraction (MaxConcurrency: 10)
│ - Iterate sections  │   Each section = 1 Lambda invocation
└─────────────────────┘
       ↓
┌─────────────────────┐
│ Extraction Lambda   │ → Single Bedrock call per section
│ - Claude 3.7 Sonnet │   Extract multiple invoices in 1 API call
│ - Batch extraction  │   Write to DynamoDB
└─────────────────────┘
```

## Implementation Details

### 1. SmartBatcher Algorithm

**Key Method**: `_should_add_invoice_to_batch()`

```python
Logic:
- If batch empty → add invoice
- If adding invoice keeps batch ≤ target_pages → add
- If adding invoice exceeds target by ≤50% → add (include complete invoice)
- Else → start new batch

Example:
- Target: 10 pages/batch
- Current batch: 9 pages
- Next invoice: 2 pages
- Result: Add (total 11 pages) to keep invoice complete
```

**Edge Cases Handled**:
1. **Page 10 contains complete invoice**: Batch pages 1-10
2. **Invoice ends at page 11**: Batch pages 1-11 (50% overage allowed)
3. **Invoice spans pages 10-15**: Close batch at page 9, start new batch

### 2. Classification Integration

**File**: `patterns/pattern-2/src/classification_function/index.py`

```python
# After page classification:
if enable_smart_batching:
    batcher = SmartBatcher(
        target_pages_per_batch=10,
        max_pages_per_batch=30,
        max_invoices_per_batch=20
    )
    document.sections = batcher.create_optimized_sections(
        pages=document.pages,
        document_type=user_hint
    )
```

### 3. Configuration

**File**: `config_library/pattern-2/fiscalshield-production/config.yaml`

```yaml
classification:
  enable_smart_batching: true
  target_pages_per_batch: 10
  max_pages_per_batch: 30
  max_invoices_per_batch: 20
  max_statements_per_batch: 1  # Bank statements: 1 per section
```

**Environment Variables** (optional overrides):
- `BATCH_TARGET_PAGES`: Default 10
- `BATCH_MAX_PAGES`: Default 30
- `BATCH_MAX_INVOICES`: Default 20

## Benefits

### Cost Efficiency
✅ **Batch Extraction**: Extract multiple invoices in 1 Bedrock API call
- Example: 5 invoices in 1 section = 1 API call (vs 5 separate calls)
- Estimated savings: 60-80% on extraction costs

### Performance
✅ **Parallel Processing**: Step Functions Map handles concurrency
- MaxConcurrency: 10 → Up to 10 sections processed simultaneously
- Example: 100 invoices → 10 sections → ~10 concurrent extractions

✅ **No Timeouts**: Sections limited to 30 pages max
- Classification: Processes pages in parallel (no timeout risk)
- Extraction: Each section small enough to complete in <60 seconds

### Reliability
✅ **Complete Invoices Only**: No partial invoices in batches
- SmartBatcher ensures invoice boundaries respected
- No deduplication needed (no overlap between sections)

✅ **Flexible Batching**: Adapts to invoice sizes
- Small invoices (1 page): Batch up to 10
- Large invoices (5 pages): Batch 2-3
- Mixed sizes: Dynamically adjusts

## Testing Strategy

### 1. Unit Testing
Test SmartBatcher with various scenarios:
```python
# Test cases:
- 100 invoices, 1 page each → ~10 sections
- 20 invoices, 5 pages each → ~10 sections  
- Mixed: 1-10 pages per invoice → verify boundaries
- Edge case: Invoice ends exactly at page 10
- Edge case: Invoice ends at page 11 (overage)
```

### 2. Integration Testing
Test full pipeline with sample documents:
```bash
# Upload test document with 100+ invoices
# Verify:
- Classification creates multiple sections
- Each section has complete invoices only
- Step Functions Map processes sections in parallel
- Extraction completes without timeout
```

### 3. Production Validation
Monitor CloudWatch logs:
```
✅ Smart batching complete: 1 original sections → 10 optimized sections
  Section section-0: invoice, 5 invoices, 10 pages
  Section section-1: invoice, 4 invoices, 9 pages
  ...
```

## Deployment Checklist

- [x] Create SmartBatcher class
- [x] Update classification prompt with boundary rules
- [x] Integrate SmartBatcher into classification lambda
- [x] Add configuration to config.yaml
- [x] Document extraction lambda changes
- [ ] Deploy to dev environment
- [ ] Test with 100+ invoice document
- [ ] Verify CloudWatch metrics
- [ ] Compare costs (before/after)
- [ ] Deploy to production

## Backward Compatibility

### ChunkedInvoiceExtractor (Deprecated)
The extraction lambda still contains `ChunkedInvoiceExtractor` for backward compatibility:
- **Default**: `USE_CHUNKED_EXTRACTION=false` (use SmartBatcher)
- **Edge Cases**: Set `USE_CHUNKED_EXTRACTION=true` for 100+ invoices in single file

### Migration Path
1. Deploy SmartBatcher (classification lambda)
2. Monitor dev environment
3. Verify batching working correctly
4. Disable chunking in extraction: `USE_CHUNKED_EXTRACTION=false`
5. Remove ChunkedInvoiceExtractor code (future cleanup)

## Files Modified

### Created
- `lib/idp_common_pkg/idp_common/classification/smart_batcher.py` (416 lines)

### Modified
- `config_library/pattern-2/fiscalshield-production/config.yaml`
  - Added smart batching configuration
  - Enhanced classification prompt with boundary rules
  
- `patterns/pattern-2/src/classification_function/index.py`
  - Added SmartBatcher import
  - Integrated SmartBatcher after page classification
  - Added logging for batch creation
  
- `patterns/pattern-2/lambdas/invoice_extraction/invoice_extraction_handler.py`
  - Added architecture documentation
  - Marked ChunkedInvoiceExtractor as deprecated
  - Updated comments explaining new flow

## Monitoring & Metrics

### CloudWatch Logs (Classification)
```
🔧 Smart batching enabled - creating optimized sections
✅ Smart batching complete: 1 original sections → 10 optimized sections
  Section section-0: invoice, 5 invoices, 10 pages
  Section section-1: invoice, 4 invoices, 9 pages
```

### CloudWatch Logs (Extraction)
```
📋 Section has 10 pages
📝 Total section text length: 15000 chars
ℹ️  Section text (15000 chars) fits in single chunk
   Using standard extraction (no chunking needed)
📤 Calling Bedrock for invoice extraction...
✅ Extracted 5 invoices from section
```

### Key Metrics to Track
- **Section Count**: Should increase from 1 → 10+ for large documents
- **Invoices per Section**: Target 3-5 (optimal batch size)
- **Pages per Section**: Target ~10, max 30
- **Extraction Time**: Should stay <30 seconds per section
- **API Calls**: Should match section count (1 call per section)

## Troubleshooting

### Issue: All invoices still in 1 section
**Cause**: Classification prompt not detecting boundaries
**Fix**: Check `document_boundary` in page metadata
```python
# Debug: Print page classifications
for page in document.pages:
    print(f"Page {page.page_id}: {page.metadata.get('document_boundary')}")
```

### Issue: Sections too small (1-2 invoices each)
**Cause**: `target_pages_per_batch` too conservative
**Fix**: Increase target to 15-20 pages
```yaml
classification:
  target_pages_per_batch: 15  # Allow larger batches
```

### Issue: Extraction timeouts
**Cause**: Section too large (>30 pages)
**Fix**: Reduce `max_pages_per_batch`
```yaml
classification:
  max_pages_per_batch: 20  # Stricter limit
```

## Next Steps

1. **Deploy to Dev**: Test with real 100+ invoice documents
2. **Cost Analysis**: Compare API costs before/after
3. **Performance Testing**: Verify parallel processing works
4. **Production Rollout**: Deploy to production with monitoring
5. **Code Cleanup**: Remove ChunkedInvoiceExtractor (Phase 2)
6. **Documentation**: Update user-facing docs with new architecture

## References

- Classification Service: `lib/idp_common_pkg/idp_common/classification/service.py`
- Step Functions Workflow: `patterns/pattern-3/statemachine/workflow.asl.json`
- Configuration Template: `config_library/pattern-2/fiscalshield-production/config.yaml`
