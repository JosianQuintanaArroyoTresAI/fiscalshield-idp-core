# Phase 3 Deployment Guide

## 🎯 What's Being Deployed

**Phase 3: Chunked Invoice Extraction with Optimization**
- ChunkedInvoiceExtractor class (reusable, tested)
- Optimized chunking: 60k chars with 5k overlap
- Prompt caching support (60-70% savings)
- Feature-flagged (disabled by default for safety)

---

## 📋 Pre-Deployment Checklist

- ✅ Code committed and pushed (commit f232c018)
- ✅ 13/13 unit tests passing
- ✅ Syntax validation passed
- ✅ Template.yaml updated with environment variables
- ✅ Backward compatible (can rollback)
- ✅ Feature flag defaults to OFF

---

## 🚀 Deployment Steps

### **Step 1: Build the Lambda Layer** (if not already done)

```bash
cd /home/josian/git/fiscalshield-idp-core

# Build the common package layer
cd lib/idp_common_pkg
./build_layer.sh  # Or your specific build command

# Verify the new class is included
unzip -l ../../.aws-sam/build/idp_common_layer/python/idp_common/extraction/chunked_invoice_extractor.py
```

### **Step 2: Deploy Pattern 2 Stack**

```bash
cd /home/josian/git/fiscalshield-idp-core/patterns/pattern-2

# Option A: Using deploy script (if you have one)
./deploy-pattern2-dev.sh

# Option B: Using SAM directly
sam build
sam deploy --config-env dev --no-confirm-changeset
```

### **Step 3: Verify Deployment**

```bash
# Check Lambda environment variables
aws lambda get-function-configuration \
  --function-name <stack-name>-InvoiceExtractionFunction \
  --query 'Environment.Variables' \
  --output json

# Expected output:
{
  "USE_CHUNKED_EXTRACTION": "false",
  "CHUNK_SIZE": "60000",
  "OVERLAP_SIZE": "5000",
  "USE_PROMPT_CACHING": "true",
  ...
}
```

---

## 🧪 Testing Phase

### **Phase 1: Smoke Test (Feature OFF)**

With `USE_CHUNKED_EXTRACTION=false`, verify existing functionality still works:

```bash
# Upload a test document
# Verify it processes correctly with old flow
# Check CloudWatch logs for "Using standard extraction"
```

**Expected Log Output**:
```
[2025-11-04 12:00:00] ℹ️  Chunked extraction DISABLED (USE_CHUNKED_EXTRACTION=false)
[2025-11-04 12:00:00]    Using standard extraction
```

### **Phase 2: Enable Chunking for Small Test**

Update Lambda environment variable:

```bash
aws lambda update-function-configuration \
  --function-name <stack-name>-InvoiceExtractionFunction \
  --environment Variables="{
    USE_CHUNKED_EXTRACTION=true,
    CHUNK_SIZE=60000,
    OVERLAP_SIZE=5000,
    USE_PROMPT_CACHING=true,
    ...other existing vars...
  }"
```

**Test with a small document first**:
- Upload 5-page PDF with 3-5 invoices
- Check CloudWatch logs for chunk creation
- Verify all invoices extracted
- Check for duplicates (should be 0-1 for small doc)

**Expected Log Output**:
```
[2025-11-04 12:05:00] 📝 Total section text length: 12000 chars
[2025-11-04 12:05:00] ℹ️  Section text (12000 chars) fits in single chunk
[2025-11-04 12:05:00]    Using standard extraction (no chunking needed)
```

### **Phase 3: Test Large Multi-Invoice PDF**

Upload 50-page PDF with 20+ invoices:

**Expected Log Output**:
```
[2025-11-04 12:10:00] 📝 Total section text length: 150000 chars
[2025-11-04 12:10:00] 🔄 Section text (150000 chars) exceeds chunk size (60000)
[2025-11-04 12:10:00]    Using CHUNKED extraction strategy...
[2025-11-04 12:10:00] 🔄 Using CHUNKED extraction (chunk_size=60000, overlap=5000)
[2025-11-04 12:10:00] 📚 Created 3 chunks from 150000 chars
[2025-11-04 12:10:01] 📤 Processing chunk 1/3 (chars 0-60000, pages [1, 2, 3, 4, 5, 6, 7, 8])
[2025-11-04 12:10:01] 📌 Using prompt caching (60-70% cost savings on repeated calls)
[2025-11-04 12:10:02] ✅ Chunk 1 yielded 8 invoices
[2025-11-04 12:10:02] 📤 Processing chunk 2/3 (chars 55000-115000, pages [7, 8, 9, 10, 11, 12, 13, 14, 15])
[2025-11-04 12:10:02] 💰 Cache hit: 2500 cached tokens, 100 new tokens
[2025-11-04 12:10:03] ✅ Chunk 2 yielded 9 invoices
[2025-11-04 12:10:03] 📤 Processing chunk 3/3 (chars 110000-150000, pages [14, 15, 16, 17, 18, 19, 20])
[2025-11-04 12:10:03] 💰 Cache hit: 2500 cached tokens, 100 new tokens
[2025-11-04 12:10:04] ✅ Chunk 3 yielded 7 invoices
[2025-11-04 12:10:04] 📊 Total invoices before deduplication: 24
[2025-11-04 12:10:04] ✅ Deduplication complete: 24 → 22 (removed 2 duplicates)
```

**Validation**:
- ✅ All invoices extracted (count matches manual count)
- ✅ No duplicates in final results
- ✅ Different-people invoices kept separate
- ✅ Processing time reduced vs baseline
- ✅ Costs reduced (check CloudWatch Insights)

---

## 📊 Monitoring

### **Key Metrics to Watch**

1. **Processing Time**
   ```sql
   # CloudWatch Insights Query
   fields @timestamp, @message
   | filter @message like /processing completed/
   | parse @message /processing completed.*in (?<duration>[0-9.]+)s/
   | stats avg(duration) as avg_duration by bin(5m)
   ```

2. **Chunk Count**
   ```sql
   fields @timestamp, @message
   | filter @message like /Created .* chunks/
   | parse @message /Created (?<chunks>[0-9]+) chunks from (?<chars>[0-9]+) chars/
   | stats avg(chunks) as avg_chunks, avg(chars) as avg_chars
   ```

3. **Deduplication Rate**
   ```sql
   fields @timestamp, @message
   | filter @message like /Deduplication complete/
   | parse @message /complete: (?<before>[0-9]+) → (?<after>[0-9]+)/
   | fields (before - after) / before * 100 as dedup_rate
   | stats avg(dedup_rate) as avg_dedup_rate
   ```

4. **Cost Impact (Bedrock Invocations)**
   ```sql
   fields @timestamp
   | filter @message like /Calling Bedrock/
   | stats count() as bedrock_calls by bin(1h)
   ```

### **Expected Results**

| Metric | Before (15k/3k) | After (60k/5k) | Target |
|--------|-----------------|----------------|--------|
| Avg Chunks/Doc | 10-15 | 2-4 | <5 |
| Deduplication Rate | 25-35% | 8-12% | <15% |
| Processing Time | 45-60s | 10-15s | <20s |
| Bedrock Calls/Doc | 10-15 | 2-4 | <5 |

---

## 🚨 Rollback Plan

### **If Quality Degrades**

**Option 1: Reduce chunk size (Quick Fix)**
```bash
aws lambda update-function-configuration \
  --function-name <stack-name>-InvoiceExtractionFunction \
  --environment Variables="{USE_CHUNKED_EXTRACTION=true,CHUNK_SIZE=30000,...}"
```

**Option 2: Disable chunking (Safe Rollback)**
```bash
aws lambda update-function-configuration \
  --function-name <stack-name>-InvoiceExtractionFunction \
  --environment Variables="{USE_CHUNKED_EXTRACTION=false,...}"
```

**Option 3: Full Stack Rollback**
```bash
# Revert to previous commit
git revert HEAD
git push

# Redeploy previous version
sam build
sam deploy --no-confirm-changeset
```

### **Rollback Triggers**

Rollback if any of these occur:
- ❌ Duplicate rate > 20%
- ❌ Extraction quality < 90%
- ❌ Processing time > baseline + 50%
- ❌ Errors in CloudWatch logs

---

## ✅ Success Criteria

### **Week 1: Validation Phase**
- ✅ Feature deployed with flag OFF
- ✅ Smoke tests pass with existing flow
- ✅ Enable for 10% of documents
- ✅ Monitor for 48 hours
- ✅ Duplicate rate < 15%
- ✅ Quality ≥ 95%

### **Week 2: Gradual Rollout**
- ✅ Increase to 50% of documents
- ✅ Monitor for 48 hours
- ✅ Cost reduction > 50%
- ✅ Processing time reduction > 50%
- ✅ No quality degradation

### **Week 3: Full Rollout**
- ✅ Enable for 100% of documents
- ✅ Monitor for 1 week
- ✅ Cost reduction stabilized at 75-80%
- ✅ Quality maintained at ≥ 95%
- ✅ Remove feature flag after stability

---

## 📈 Cost Tracking

### **Baseline (Before Phase 3)**
Track for 1 week before enabling:
```sql
# CloudWatch Insights - Bedrock invocation count
fields @timestamp
| filter @message like /Calling Bedrock/
| stats count() as calls by bin(1d)
```

**Expected baseline**: ~15 calls per 100-page document

### **After Enabling**
Track same metric:
**Expected optimized**: ~3 calls per 100-page document

**Savings calculation**:
```
Cost per call: ~$0.03 (input) + $0.02 (output) = $0.05
Before: 15 calls × $0.05 = $0.75 per document
After: 3 calls × $0.05 × 0.35 (with caching) = $0.05 per document
Savings: $0.70 per document (93%)
```

**Monthly savings** (1,000 docs):
- Before: $750/month
- After: $50/month
- **Savings: $700/month = $8,400/year** 💰

---

## 🔗 Related Documentation

- **Technical Analysis**: `docs/CHUNKING_ANALYSIS.md`
- **Optimization Summary**: `PHASE_3_OPTIMIZATION_SUMMARY.md`
- **Quick Reference**: `PHASE_3_QUICK_REF.md`
- **Prior Lambda Comparison**: `docs/PRIOR_LAMBDA_COMPARISON.md`
- **Implementation Progress**: `PHASE_3_IMPLEMENTATION_PROGRESS.md`

---

## 📞 Support

**CloudWatch Logs Location**:
```
/aws/lambda/<stack-name>-InvoiceExtractionFunction
```

**Key Log Patterns to Search**:
- `"Using CHUNKED extraction"` - Chunking enabled and triggered
- `"Using standard extraction"` - Chunking disabled or not needed
- `"Created .* chunks"` - Chunk creation count
- `"Deduplication complete"` - Deduplication results
- `"Cache hit"` - Prompt caching working

**Common Issues**:
1. **No invoices extracted**: Check if text length > 0
2. **Too many duplicates**: Reduce chunk size or increase overlap
3. **Invoices missing**: Check overlap size (increase if needed)
4. **High costs**: Verify prompt caching is enabled

---

## ✨ Next Steps After Successful Deployment

1. **Collect Metrics** (Week 1-2)
   - Baseline vs optimized comparison
   - Cost reduction validation
   - Quality metrics

2. **Optimize Further** (Week 3-4)
   - Consider Sonnet 3.7 for better accuracy
   - Fine-tune chunk size based on document types
   - Add dynamic chunk sizing

3. **Remove Feature Flag** (Week 4-5)
   - After 2 weeks of stable operation
   - Update template.yaml to remove flag
   - Redeploy with chunking as default

4. **Document Lessons Learned**
   - Update cost calculator
   - Share results with team
   - Consider applying to other document types

---

**Ready to Deploy!** 🚀

Current status:
- ✅ Code ready and tested
- ✅ Template.yaml updated
- ✅ Feature flag in safe state (OFF)
- ✅ Rollback plan documented
- ✅ Monitoring queries prepared

**Next command**: `sam build && sam deploy`
