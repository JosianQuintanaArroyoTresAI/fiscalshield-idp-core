# Smart Batching - Quick Testing Guide

## Pre-Deployment Checklist

### 1. Verify Configuration
```bash
# Check config.yaml has smart batching settings
grep -A 5 "enable_smart_batching" config_library/pattern-2/fiscalshield-production/config.yaml

# Expected output:
# enable_smart_batching: true
# target_pages_per_batch: 10
# max_pages_per_batch: 30
# max_invoices_per_batch: 20
# max_statements_per_batch: 1
```

### 2. Verify SmartBatcher Import
```bash
# Check classification lambda imports SmartBatcher
grep "smart_batcher" patterns/pattern-2/src/classification_function/index.py

# Expected output:
# from idp_common.classification.smart_batcher import SmartBatcher
```

### 3. Package and Deploy
```bash
# Package the IDP common library with SmartBatcher
cd lib/idp_common_pkg
pip install -e .

# Deploy classification lambda
cd ../../patterns/pattern-2
sam build
sam deploy --config-env production

# Or use your deployment script
./deploy-pattern2-dev.sh
```

## Testing

### Test 1: Small Document (10 invoices)
```bash
# Upload document with 10 invoices (1 page each)
# Expected: 1 section with 10 invoices

# Check CloudWatch logs (Classification):
aws logs tail /aws/lambda/fiscalshield-classification-function --follow

# Look for:
# ✅ Smart batching complete: 1 original sections → 1 optimized sections
#   Section section-0: invoice, 10 invoices, 10 pages
```

### Test 2: Large Document (50 invoices)
```bash
# Upload document with 50 invoices (1 page each)
# Expected: 5 sections with ~10 invoices each

# Check CloudWatch logs (Classification):
# Look for:
# ✅ Smart batching complete: 1 original sections → 5 optimized sections
#   Section section-0: invoice, 10 invoices, 10 pages
#   Section section-1: invoice, 10 invoices, 10 pages
#   Section section-2: invoice, 10 invoices, 10 pages
#   Section section-3: invoice, 10 invoices, 10 pages
#   Section section-4: invoice, 10 invoices, 10 pages
```

### Test 3: Very Large Document (100+ invoices)
```bash
# Upload document with 100+ invoices
# Expected: 10+ sections

# Check Step Functions execution:
aws stepfunctions list-executions --state-machine-arn <your-state-machine-arn>

# Get execution details:
aws stepfunctions describe-execution --execution-arn <execution-arn>

# Verify Map state processed multiple sections in parallel
```

### Test 4: Mixed Invoice Sizes
```bash
# Upload document with mixed invoice sizes (1-5 pages)
# Expected: Sections with ~10 pages, complete invoices only

# Check CloudWatch logs (Classification):
# Look for:
#   Section section-0: invoice, 3 invoices, 11 pages  (e.g., 3+4+4)
#   Section section-1: invoice, 4 invoices, 9 pages   (e.g., 2+2+2+3)
#   Section section-2: invoice, 2 invoices, 10 pages  (e.g., 5+5)
```

## Validation Checklist

### Classification Lambda
- [ ] SmartBatcher import successful (no import errors)
- [ ] Configuration loaded correctly (check logs)
- [ ] Page classification completes (document_boundary set)
- [ ] SmartBatcher creates sections (log shows section count)
- [ ] Section metadata includes page_count and invoice_count

### Step Functions
- [ ] Map state receives sections array
- [ ] Map state spawns multiple executions (for large docs)
- [ ] Parallel processing works (MaxConcurrency: 10)
- [ ] All section executions complete successfully

### Extraction Lambda
- [ ] Each section processed separately
- [ ] No chunking used (SmartBatcher handles batching)
- [ ] Single Bedrock call per section
- [ ] All invoices extracted successfully
- [ ] No duplicate invoices (no overlap between sections)

## Performance Metrics

### Before SmartBatcher
```
Document: 100 invoices
Sections: 1 (all invoices in one section)
Result: Classification timeout (>60 seconds)
```

### After SmartBatcher
```
Document: 100 invoices
Sections: 10 (10 invoices per section)
Classification Time: ~20 seconds (parallel processing)
Extraction Time: ~5 seconds per section (parallel)
Total Time: ~25 seconds (vs timeout before)
Cost: 1 Bedrock call per section = 10 calls (vs 1 call before, but that timed out)
```

## Debug Commands

### Check Section Count
```bash
# Get document from S3 after classification
aws s3 cp s3://your-bucket/documents/<document-id>.json - | jq '.sections | length'

# Expected: 10+ for large documents (was 1 before)
```

### Check Section Details
```bash
# Get section metadata
aws s3 cp s3://your-bucket/documents/<document-id>.json - | jq '.sections[] | {section_id, classification, page_count: (.attributes.page_count), invoice_count: (.attributes.invoice_count)}'

# Expected output:
# {
#   "section_id": "section-0",
#   "classification": "invoice",
#   "page_count": 10,
#   "invoice_count": 5
# }
```

### Check Page Boundaries
```bash
# Get page classifications
aws s3 cp s3://your-bucket/documents/<document-id>.json - | jq '.pages | to_entries[] | {page_id: .key, boundary: .value.metadata.document_boundary, classification: .value.classification}'

# Expected output:
# {"page_id": "page-1", "boundary": "start", "classification": "invoice"}
# {"page_id": "page-2", "boundary": "continue", "classification": "invoice"}
# {"page_id": "page-3", "boundary": "start", "classification": "invoice"}  <- New invoice
```

## Rollback Plan

If SmartBatcher causes issues:

### 1. Disable Smart Batching
```yaml
# config_library/pattern-2/fiscalshield-production/config.yaml
classification:
  enable_smart_batching: false  # Disable SmartBatcher
```

### 2. Enable Chunking in Extraction
```bash
# Set environment variable
aws lambda update-function-configuration \
  --function-name fiscalshield-extraction-function \
  --environment Variables={USE_CHUNKED_EXTRACTION=true}
```

### 3. Redeploy
```bash
sam deploy --config-env production
```

## Success Criteria

✅ **Classification completes in <30 seconds** (even for 100+ invoices)
✅ **Multiple sections created** (not just 1)
✅ **Each section has ~10 pages** (flexible based on invoice sizes)
✅ **No partial invoices** (each section has complete invoices only)
✅ **Extraction completes without timeout** (<60 seconds per section)
✅ **All invoices extracted** (no missing data)
✅ **No duplicate invoices** (no overlap between sections)

## Common Issues

### Issue: Import error for SmartBatcher
```
ModuleNotFoundError: No module named 'idp_common.classification.smart_batcher'
```
**Fix**: Rebuild Lambda layer with updated idp_common package
```bash
cd lib/idp_common_pkg
pip install -t python/lib/python3.x/site-packages .
zip -r layer.zip python
aws lambda publish-layer-version --layer-name idp-common --zip-file fileb://layer.zip
```

### Issue: Configuration not loaded
```
KeyError: 'classification'
```
**Fix**: Verify config.yaml is deployed to S3
```bash
aws s3 cp config_library/pattern-2/fiscalshield-production/config.yaml \
  s3://your-config-bucket/config.yaml
```

### Issue: Still only 1 section
```
Smart batching complete: 1 original sections → 1 optimized sections
```
**Fix**: Check document_boundary in pages
- If all pages have `boundary: continue`, classification prompt needs adjustment
- Verify prompt includes boundary detection rules
