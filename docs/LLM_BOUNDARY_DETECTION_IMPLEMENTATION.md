# LLM Boundary Detection - Implementation Guide

## ✅ What Was Implemented

We've successfully implemented **LLM-based boundary detection** for the classification lambda as specified in the refactor guide.

### Key Components Created

1. **New Module:** `lib/idp_common_pkg/idp_common/classification/llm_boundary_detection.py`
   - `LLMBoundaryDetector` class - Uses Claude Sonnet 3.5 for intelligent boundary detection
   - `get_section_text()` helper - Extracts section text with PAGE markers
  - Comprehensive validation logic with coverage + gap heuristics (Phase 2)
  - Deterministic fallback generator that emits PAGE-chunked ranges when LLM output is unusable
   - Prompt caching support (90% cost savings)

2. **Updated:** `patterns/pattern-2/src/classification_function/index.py`
   - Integrated LLM boundary detection after SmartBatcher
   - Feature flag support (`enable_llm_boundary_detection`)
   - Stores boundaries in `section.attributes`

3. **Updated:** `config_library/pattern-2/fiscalshield-production/config.yaml`
   - Added configuration for boundary detection
   - Model selection (defaults to Sonnet 3.5)
   - Prompt caching enabled

4. **New Tests:** `tests/test_llm_boundary_detection.py`
  - Unit tests for all boundary detection functions
  - Validation + fallback tests
  - Mock Bedrock integration tests

---

## ♻️ Phase 2 Enhancements

- **Stricter validation:** Minimum coverage now 92% with a max-gap heuristic (default 12%) and detailed coverage stats in logs.
- **Automatic fallback:** Deterministic PAGE-chunk boundaries keep extraction moving when LLM output is empty or invalid.
- **Observability:** New metrics (`LLMBoundaryValidationPassed`, `LLMBoundaryValidationFailed`, `LLMBoundaryFallbackUsed`) surface health in CloudWatch.

---

## 🚀 Deployment Steps

### 1. Install Dependencies

```bash
# Navigate to idp_common package
cd lib/idp_common_pkg

# Install in development mode (if not already)
pip install -e .

# Or rebuild the layer if using Lambda layers
cd ../..
./scripts/build-idp-common-layer.sh  # If this script exists
```

### 2. Run Tests Locally

```bash
# Install test dependencies
pip install pytest pytest-mock boto3

# Run boundary detection tests
python tests/test_llm_boundary_detection.py

# Or use pytest
pytest tests/test_llm_boundary_detection.py -v
```

### 3. Deploy Classification Lambda

```bash
# Deploy using SAM
sam build
sam deploy --config-env dev

# Or if using specific stack
cd patterns/pattern-2
sam build
sam deploy --stack-name fiscalshield-pattern2-dev
```

### 4. Update Configuration

The configuration is already updated in `config_library/pattern-2/fiscalshield-production/config.yaml`.

Upload to S3 if using S3-based config:
```bash
aws s3 cp config_library/pattern-2/fiscalshield-production/config.yaml \
  s3://your-config-bucket/config.yaml
```

---

## 🧪 Testing the Implementation

### Test 1: Unit Tests (Local)

```bash
pytest tests/test_llm_boundary_detection.py -v -s
```

**Expected output:**
```
test_initialization PASSED
test_parse_json_response_valid PASSED
test_validate_boundaries_success PASSED
test_validate_boundaries_overlapping PASSED
...
```

### Test 2: Integration Test (Upload Invoice PDF)

1. **Upload a multi-invoice PDF** through the UI
2. **Check CloudWatch logs** for classification lambda:

```bash
aws logs tail /aws/lambda/classification-lambda --follow
```

**Look for these log messages:**
```
🔍 LLM boundary detection enabled (model: arn:aws:bedrock:eu-central-1:864899848062:inference-profile/eu.anthropic.claude-3-5-sonnet-20240620-v1:0)
🔍 Detecting boundaries for invoice section 1
📄 Section text length: 15234 chars
🔍 Invoking arn:aws:bedrock:eu-central-1:864899848062:inference-profile/eu.anthropic.claude-3-5-sonnet-20240620-v1:0 for boundary detection...
📊 Token usage: 3500 input, 250 output
💰 Cache: 3150 read, 350 created
✅ LLM detected 3 invoice boundaries
✅ Boundary validation passed: 3 invoices, 95.2% coverage
✅ Detected 3 invoices in section 1
```

3. **Check DynamoDB** - TrackingTable should have section with boundaries:

```bash
aws dynamodb get-item \
  --table-name TrackingTable \
  --key '{"PK": {"S": "USER#<user-id>#doc#<doc-path>"}, "SK": {"S": "none"}}'
```

**Expected structure:**
```json
{
  "sections": [
    {
      "section_id": "1",
      "classification": "invoice",
      "page_ids": ["page-1", "page-2", "page-3"],
      "attributes": {
        "boundaries": [
          {
            "id": 1,
            "start_char": 0,
            "end_char": 2847,
            "confidence": "high",
            "page_numbers": [1],
            "start_indicator": "Invoice Number: INV-001",
            "end_indicator": "AMOUNT DUE £296.74"
          },
          {
            "id": 2,
            "start_char": 2848,
            "end_char": 5690,
            "confidence": "high",
            "page_numbers": [2, 3],
            "start_indicator": "Invoice Number: INV-002",
            "end_indicator": "Thank you for your business"
          }
        ],
        "boundary_strategy": "llm_detected",
        "invoice_count": 2,
        "boundary_model": "arn:aws:bedrock:eu-central-1:864899848062:inference-profile/eu.anthropic.claude-3-5-sonnet-20240620-v1:0"
      }
    }
  ]
}
```

### Test 3: Cost Verification

Check CloudWatch metrics for token usage:

```bash
# View custom metrics
aws cloudwatch get-metric-statistics \
  --namespace TaxGuard/BoundaryDetection \
  --metric-name BoundariesDetected \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum
```

---

## 🔧 Configuration Options

### Model Selection

You can use different models for boundary detection:

```yaml
classification:
  # Fast and cheap (for testing)
  boundary_detection_model: "anthropic.claude-3-haiku-20240307-v1:0"
  
  # Recommended: EU inference profile for Sonnet 3.5 (best accuracy/cost balance)
  boundary_detection_model: "arn:aws:bedrock:eu-central-1:864899848062:inference-profile/eu.anthropic.claude-3-5-sonnet-20240620-v1:0"
  
  # Most accurate (for complex documents)
  boundary_detection_model: "anthropic.claude-3-7-sonnet-20250219-v1:0"
```

### Phase 2 Validation & Fallback Controls

```yaml
classification:
  boundary_min_coverage: 0.92       # % of characters covered by invoices
  boundary_max_gap_ratio: 0.12      # Max uncovered span fraction (largest gap / text length)
  fallback_pages_per_boundary: 2    # Number of pages per deterministic fallback chunk
```

### Feature Flags

```yaml
classification:
  # Enable/disable boundary detection
  enable_llm_boundary_detection: true  # false to disable
  
  # Enable prompt caching (recommended)
  use_prompt_caching: true  # false to disable caching

> **Note:** Prompt caching is only applied when invoking a direct model ID that supports cache points. Bedrock inference profiles currently ignore cache hints, so set this to `false` if you exclusively use inference profiles.
```

### Validation Thresholds

Runtime defaults (Phase 2) are configured via YAML, but you can still override in code if needed:

```python
detector.validate_boundaries(
  boundaries,
  section_text,
  min_coverage=0.92,          # Minimum 92% coverage
  max_boundaries=100,         # Maximum 100 boundaries per section
  max_gap_ratio=0.12          # Largest uncovered span allowed
)
```

---

## 📊 Monitoring

### Key Metrics to Track

1. **Boundary Validation Health**
  - Namespace: `TaxGuard/BoundaryDetection`
  - Metrics: `LLMBoundaryValidationPassed`, `LLMBoundaryValidationFailed`
  - Target: >90% pass, <10% fail

2. **Fallback Usage**
  - Metric: `LLMBoundaryFallbackUsed`
  - Expect near-zero steady state; spikes signal prompt/coverage drift

3. **Boundaries Detected**
  - Metric: `BoundariesDetected`
  - Should align with `invoice_count` stored per section

4. **Token Usage**
  - Check CloudWatch logs for token usage
  - Cache hit rate should be >80% after first call

5. **Cost per Section**
  - Sonnet 3.5: ~$0.06 per section (with caching: ~$0.02)
  - Still saves $9+ in extraction costs

### CloudWatch Insights Queries

**Boundary detection summary:**
```
fields @timestamp, section_id, invoice_count, boundary_strategy, validation_passed
| filter @message like /Detected.*invoices/
| sort @timestamp desc
```

**Token usage analysis:**
```
fields @timestamp, input_tokens, output_tokens, cache_read_input_tokens
| filter @message like /Token usage/
| stats sum(input_tokens) as total_input, 
        sum(output_tokens) as total_output,
        sum(cache_read_input_tokens) as cache_hits
```

---

## 🐛 Troubleshooting

### Issue: No boundaries detected

**Check:**
1. Is `enable_llm_boundary_detection: true` in config?
2. Are there PAGE markers in the section text?
3. Check CloudWatch logs for LLM response

**Debug:**
```python
# Add to classification lambda temporarily
logger.info(f"Section text preview: {section_text[:500]}")
```

### Issue: Validation failing

**Possible causes:**
1. LLM returned overlapping boundaries
2. Text coverage too low (<80%)
3. Too many boundaries (>100)
4. Largest uncovered gap exceeded threshold (>12%)

**Check logs for:**
```
❌ Overlapping boundaries detected
⚠️ Low text coverage: 45.2%
⚠️ Large uncovered region detected: 18.0% gap (allowed <12.0%)
❌ Too many boundaries: 150
```

When this happens repeatedly, the Lambda now emits deterministic fallback metadata (`boundary_strategy=fallback_page_chunks`) so extraction can continue, but you should still investigate prompt drift.

### Issue: High costs

**Check:**
1. Is prompt caching enabled? (`use_prompt_caching: true`)
2. Cache hit rate should be >80%
3. Consider switching to Haiku for testing

**View cache usage:**
```
fields @timestamp, cache_read_input_tokens, input_tokens
| filter @message like /Cache:/
| stats avg(cache_read_input_tokens / (cache_read_input_tokens + input_tokens)) as cache_hit_rate
```

---

## ✅ Success Criteria

Before proceeding to extraction lambda:

- [x] Unit tests passing (all 10+ tests)
- [ ] Classification lambda deployed successfully
- [ ] Test document uploaded and processed
- [ ] Boundaries detected and stored in DynamoDB
- [ ] Boundary validation passing (>90% success rate)
- [ ] Token usage reasonable (500-5000 tokens per section)
- [ ] Prompt caching working (>80% cache hits)
- [ ] No errors in CloudWatch logs

---

## 📈 Next Steps

Once classification is validated:

1. **Proceed to Extraction Lambda** (Week 2)
   - Implement PATH 1: Extract from boundaries
   - Implement PATH 2/3: Fallback paths
   - Add metrics tracking

2. **Monitor for 1 Week**
   - Boundary detection accuracy
   - Deduplication rates (should be <2%)
   - Cost savings validation

3. **Optimize** (Week 3-4)
   - Tune prompts if needed
   - Adjust validation thresholds
   - Clean up legacy code

---

## 📞 Support

**Issues or questions:**
- Check CloudWatch Logs: `/aws/lambda/classification-lambda`
- Review test results: `pytest tests/test_llm_boundary_detection.py -v`
- Contact team: #fiscalshield-engineering

**Configuration:**
- Config file: `config_library/pattern-2/fiscalshield-production/config.yaml`
- Module: `lib/idp_common_pkg/idp_common/classification/llm_boundary_detection.py`
- Lambda: `patterns/pattern-2/src/classification_function/index.py`
