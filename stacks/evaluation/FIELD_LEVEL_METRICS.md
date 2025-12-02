# Field-Level Accuracy Metrics

## Overview

The evaluation stack now tracks accuracy for **each individual field** (e.g., VATNumber, TotalAmount, InvoiceDate, SupplierAddress) to help you identify which fields are most problematic.

## What Gets Tracked

For each field in your extraction schema, the system tracks:

- **Total Occurrences**: How many times this field appeared
- **Exact Matches**: Perfect matches between production and evaluation model
- **Fuzzy Matches**: Close matches (e.g., minor formatting differences)
- **Mismatches**: Wrong extractions
- **Accuracy**: (Exact + Fuzzy) / Total
- **Error Rate**: Mismatches / Total
- **Error Examples**: Up to 3 examples of mismatches per field

## How to Query Metrics

### Option 1: Use the Query Script

```bash
cd stacks/evaluation
./query-field-metrics.sh
```

This will show:
- All fields sorted by error rate (worst first)
- Top 5 most problematic fields

### Option 2: Direct DynamoDB Query

```bash
# Get all field metrics for latest evaluation
aws dynamodb scan \
  --table-name fiscalshield-idp-dev-EvaluationMetrics \
  --region eu-central-1 \
  --filter-expression "MetricType = :type" \
  --expression-attribute-values '{":type":{"S":"FIELD_LEVEL"}}' \
  --output json
```

### Option 3: Query Specific Field Over Time

```bash
# Track how a specific field performs over time
aws dynamodb query \
  --table-name fiscalshield-idp-dev-EvaluationMetrics \
  --region eu-central-1 \
  --index-name GSI1-ByEvaluationDate \
  --key-condition-expression "GSI1PK = :pk" \
  --expression-attribute-values '{":pk":{"S":"FIELD#VATNumber"}}' \
  --scan-index-forward false \
  --limit 10
```

## Example Output

```
Field: SupplierAddress
  Accuracy: 45%
  Error Rate: 55%
  Total Occurrences: 20
  Exact Matches: 5
  Fuzzy Matches: 4
  Mismatches: 11

Field: VATNumber
  Accuracy: 78%
  Error Rate: 22%
  Total Occurrences: 18
  Exact Matches: 12
  Fuzzy Matches: 2
  Mismatches: 4

Field: TotalAmount
  Accuracy: 95%
  Error Rate: 5%
  Total Occurrences: 20
  Exact Matches: 19
  Fuzzy Matches: 0
  Mismatches: 1
```

## Use Cases

### 1. **Prioritize Prompt Improvements**
If `SupplierAddress` has 55% error rate, focus on improving that field's extraction prompt.

### 2. **Adjust Confidence Thresholds**
If `VATNumber` has high error rate, lower the confidence threshold to route more VAT extractions to human review.

### 3. **Field-Specific Models**
Consider using different models for problematic fields (e.g., specialized OCR for addresses).

### 4. **Training Data Collection**
Use high-error fields to create targeted fine-tuning datasets.

### 5. **Document Type Analysis**
Cross-reference with document types to see if certain fields only fail on specific document types.

## DynamoDB Schema

Field-level metrics are stored with:

- **PK**: `EVALUATION#<evaluationId>`
- **SK**: `FIELD#<fieldName>#<timestamp>`
- **GSI1PK**: `FIELD#<fieldName>` (for querying field history)
- **GSI1SK**: `DATE#<timestamp>`

This allows querying:
- All fields for a specific evaluation run
- Historical performance of a single field
- Fields sorted by error rate

## Next Steps

Once you have a few days of data:

1. **Identify the top 3 problematic fields**
2. **Review error examples** to understand why they're failing
3. **Improve extraction prompts** for those fields
4. **Re-run evaluation** to measure improvement
5. **Iterate** until accuracy meets your requirements

## Automation Ideas

- **CloudWatch Alarm**: Alert when any field drops below 80% accuracy
- **QuickSight Dashboard**: Visualize field accuracy trends over time
- **Automated Retraining**: Feed low-accuracy fields into fine-tuning pipeline
