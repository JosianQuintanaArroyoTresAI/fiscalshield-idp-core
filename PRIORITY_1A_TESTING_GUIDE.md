# Priority 1A Testing Guide: JSON Format Verification

**Status**: Deployment in progress  
**Test Target**: Verify JSON format reduces failure rate from 18% → ~10%  

---

## Pre-Test Checklist

### 1. Confirm Deployment Complete
```bash
aws cloudformation describe-stacks \
  --stack-name fiscalshield-idp-dev \
  --region eu-central-1 \
  --query 'Stacks[0].StackStatus' \
  --output text
```

**Expected**: `UPDATE_COMPLETE`  
**If**: `UPDATE_IN_PROGRESS` → Wait 5-10 more minutes  
**If**: `UPDATE_FAILED` → Check CloudFormation events for errors

### 2. Verify Lambda Updated
```bash
aws lambda get-function \
  --function-name fiscalshield-idp-dev-InvoiceCategorizationFunction-* \
  --region eu-central-1 \
  --query 'Configuration.LastModified'
```

**Expected**: Timestamp within last hour

### 3. Get Lambda Function Name
```bash
aws cloudformation describe-stack-resources \
  --stack-name fiscalshield-idp-dev \
  --region eu-central-1 \
  --logical-resource-id InvoiceCategorizationFunction \
  --query 'StackResources[0].PhysicalResourceId' \
  --output text
```

Save this for CloudWatch logs access.

---

## Test 1: Upload Sample Invoices

### Option A: Use Existing 28 Invoices (Recommended)

These are the invoices that previously showed 18% failure rate (5-6 failures).

1. **Navigate to Frontend**:
   ```
   https://[your-cloudfront-domain]/upload
   ```

2. **Upload Invoices**:
   - Use the same 28 invoices from previous test
   - Note the upload timestamp

3. **Wait for Processing**:
   - Expected time: ~3-5 minutes for 28 invoices
   - Batch size: 8 invoices per batch = 4 batches total

### Option B: Generate Test Invoice

If you don't have the original 28, use a simple test:

```bash
# Create test invoice JSON
cat > test-invoice.json << 'EOF'
{
  "invoice_type": "SUPPLIER_INVOICE",
  "invoice_number": "TEST-001",
  "supplier_name": "Test Supplier Ltd",
  "total_amount": 500.00,
  "description": "Office supplies - printer ink and paper"
}
EOF

# Upload via S3 (adjust bucket name)
aws s3 cp test-invoice.json s3://fiscalshield-idp-dev-uploads/test-user/TEST-001.json --region eu-central-1
```

---

## Test 2: Monitor Processing

### CloudWatch Logs - Real-time

```bash
# Get log group name
LOG_GROUP="/aws/lambda/fiscalshield-idp-dev-InvoiceCategorizationFunction-*"

# Tail logs
aws logs tail $LOG_GROUP \
  --region eu-central-1 \
  --follow \
  --format short
```

**Look for**:
- ✅ `[INFO] Successfully parsed X invoice analyses from JSON`
- ✅ `[SUMMARY] Successfully processed 8/8 invoices`
- ❌ `[ERROR] JSON parsing failed` (should be minimal)
- ❌ `[WARNING] X invoices failed to parse from JSON response` (should be 0-1)

### CloudWatch Insights - Success Rate Analysis

```sql
fields @timestamp, @message
| filter @message like /Successfully parsed/
| parse @message /Successfully parsed (?<parsed>\d+) invoice/
| stats count() as batches, 
        sum(parsed) as total_parsed,
        avg(parsed) as avg_per_batch
| sort @timestamp desc
```

**Expected**:
- `avg_per_batch`: 7-8 (up from 6-7 with XML)
- `total_parsed`: 25-26 out of 28 (up from 22-23)

### CloudWatch Insights - Failure Analysis

```sql
fields @timestamp, @message, @logStream
| filter @message like /JSON parsing failed/ 
        or @message like /Failed invoice/
        or @message like /ERROR/
| sort @timestamp desc
| limit 50
```

**Expected**: 2-3 failures (down from 5-6)

---

## Test 3: Verify DynamoDB Results

### Count Analysis Status

```bash
# Get table name
TABLE_NAME=$(aws cloudformation describe-stack-resources \
  --stack-name fiscalshield-idp-dev \
  --region eu-central-1 \
  --logical-resource-id ExtractionResultsTable \
  --query 'StackResources[0].PhysicalResourceId' \
  --output text)

# Scan for analyzed invoices
aws dynamodb scan \
  --table-name $TABLE_NAME \
  --region eu-central-1 \
  --filter-expression "AnalysisStatus = :analyzed" \
  --expression-attribute-values '{":analyzed":{"S":"ANALYZED"}}' \
  --select COUNT
```

**Expected**: 25-26 analyzed (up from 22-23)

### Count Failed Invoices

```bash
aws dynamodb scan \
  --table-name $TABLE_NAME \
  --region eu-central-1 \
  --filter-expression "AnalysisStatus = :failed OR AnalysisStatus = :failed_perm" \
  --expression-attribute-values '{":failed":{"S":"FAILED"},":failed_perm":{"S":"FAILED_PERMANENT"}}' \
  --select COUNT
```

**Expected**: 2-3 failed (down from 5-6)

### Inspect Specific Failed Invoice

```bash
aws dynamodb scan \
  --table-name $TABLE_NAME \
  --region eu-central-1 \
  --filter-expression "AnalysisStatus = :failed" \
  --expression-attribute-values '{":failed":{"S":"FAILED"}}' \
  --query 'Items[0].[InvoiceId.S, DeductibilityReasoning.S, AnalysisRetryCount.N]' \
  --output table
```

**Check**:
- `DeductibilityReasoning`: Should say "JSON parsing failed - attempt X/3"
- `AnalysisRetryCount`: Should be 1, 2, or 3

---

## Test 4: Validate Frontend Display

### Check Invoice List

1. Navigate to: `https://[cloudfront-domain]/invoices`

2. **Verify Columns**:
   - ✅ Analysis Status shows: ANALYZED, PENDING, or FAILED
   - ✅ Tax Status shows percentage badges
   - ✅ NO columns for: Confidence, Quality, Review

3. **Check Statistics**:
   - Total Analyzed: Should be 25-26 out of 28
   - Success Rate: ~90% (up from 82%)

### Check Invoice Detail

1. Click on any ANALYZED invoice

2. **Verify Tax Deductibility Assessment Section**:
   - ✅ Status badge (FULLY_DEDUCTIBLE, PARTIALLY_DEDUCTIBLE, etc.)
   - ✅ Percentage (0%, 50%, 100%, etc.)
   - ✅ Reasoning text displayed below assessment
   - ✅ BIM Sections listed
   - ✅ Documentation Required (if applicable)
   - ✅ Recommended Action

3. **For EXPENSE_CLAIM invoices, verify Compliance Tests**:
   - ✅ Test 1-7 results displayed
   - ✅ Confidence levels shown
   - ✅ Reasoning for each test

---

## Success Criteria

### 🎯 Primary Metrics

| Metric | Baseline | Target | Pass/Fail |
|--------|----------|--------|-----------|
| Success Rate | 82% (23/28) | 90% (25/28) | ⬜ |
| Failure Rate | 18% (5/28) | 10% (2-3/28) | ⬜ |
| JSON Parse Errors | N/A | <5% | ⬜ |
| Avg Batch Success | 6.5/8 | 7.5/8 | ⬜ |

### 🔍 Secondary Metrics

| Metric | Baseline | Expected | Pass/Fail |
|--------|----------|----------|-----------|
| Token Usage | ~6500/batch | ~6000/batch | ⬜ |
| Processing Time | ~45s/batch | ~40s/batch | ⬜ |
| Retry Count | 5-6/cycle | 2-3/cycle | ⬜ |
| Manual Review Queue | 5-6 invoices | 2-3 invoices | ⬜ |

### 📊 CloudWatch Metrics

```bash
# Average processing time
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=fiscalshield-idp-dev-InvoiceCategorizationFunction-* \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average \
  --region eu-central-1
```

---

## Troubleshooting

### Issue: Deployment Failed

**Symptoms**: Stack status = `UPDATE_FAILED`

**Fix**:
1. Check CloudFormation events:
   ```bash
   aws cloudformation describe-stack-events \
     --stack-name fiscalshield-idp-dev \
     --region eu-central-1 \
     --query 'StackEvents[?ResourceStatus==`UPDATE_FAILED`]'
   ```

2. Look for Lambda errors (likely permission or runtime issues)

3. Rollback if needed:
   ```bash
   git revert 5647c5b3 cf8f6739
   git push origin dev
   ./deploy-pattern2-dev.sh
   ```

### Issue: JSON Parsing Failures > 30%

**Symptoms**: More failures than before

**Diagnosis**:
1. Check error messages in CloudWatch:
   ```sql
   fields @message
   | filter @message like /JSON parsing failed/
   | display @message
   ```

2. Look for common patterns (e.g., markdown code blocks not stripped)

**Fix**: Add fallback to XML parser temporarily

### Issue: No Invoices Processed

**Symptoms**: All invoices stuck in PENDING

**Diagnosis**:
1. Check trigger lambda:
   ```bash
   aws logs tail /aws/lambda/fiscalshield-idp-dev-TriggerInvoiceAnalysis-* \
     --region eu-central-1 \
     --since 1h
   ```

2. Verify Step Functions execution:
   ```bash
   aws stepfunctions list-executions \
     --state-machine-arn $(aws cloudformation describe-stack-resource \
       --stack-name fiscalshield-idp-dev \
       --logical-resource-id AnalysisStateMachine \
       --query 'StackResourceDetail.PhysicalResourceId' \
       --output text) \
     --region eu-central-1
   ```

**Fix**: May be unrelated to JSON change - check batch processing logic

---

## Results Documentation

### Create Test Report

Once testing complete, document results:

```bash
cat > PRIORITY_1A_TEST_RESULTS.md << 'EOF'
# Priority 1A Test Results

**Date**: $(date +%Y-%m-%d)
**Environment**: DEV
**Test Set**: 28 invoices

## Results Summary

### Before (XML Format)
- Total Analyzed: 22-23 / 28 (82%)
- Failed: 5-6 / 28 (18%)
- Avg Batch Success: 6.5 / 8

### After (JSON Format)
- Total Analyzed: [FILL] / 28 ([FILL]%)
- Failed: [FILL] / 28 ([FILL]%)
- Avg Batch Success: [FILL] / 8

### Improvement
- Success Rate: [FILL] → [FILL] ([FILL]% improvement)
- Failure Reduction: [FILL] fewer failed invoices
- Batch Efficiency: [FILL] → [FILL] invoices/batch

## CloudWatch Logs Evidence

[Paste relevant log excerpts]

## DynamoDB Status Counts

[Paste scan results]

## Conclusion

✅ PASS / ❌ FAIL

[Brief explanation]

## Next Steps

[What to do next based on results]
EOF
```

---

## Next Actions Based on Results

### ✅ If Test Passes (90%+ success rate)

**Proceed to Priority 1B**: Streamline Prompt
- Goal: Reduce prompt from ~3000 to ~1200 tokens
- Expected additional improvement: 5-8% failure reduction
- Time estimate: 4-6 hours

### ⚠️ If Test Marginal (85-89% success rate)

**Investigate Further**:
1. Analyze specific failure patterns
2. Check if failures are consistent invoices (data quality issue)
3. Consider tweaking JSON schema
4. Still proceed to Priority 1B (compounding improvements)

### ❌ If Test Fails (<85% success rate)

**Rollback and Re-evaluate**:
1. Immediate rollback to XML
2. Deep dive into failure root cause
3. Consider hybrid approach (JSON primary, XML fallback)
4. May need to address underlying model issues

---

**Testing Time Estimate**: 30-45 minutes  
**Decision Point**: Can proceed to Priority 1B same day if test passes
