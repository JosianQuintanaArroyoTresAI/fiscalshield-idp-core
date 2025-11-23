# Evaluation Stack

**Purpose**: Automated model performance evaluation pipeline using batch inference and weighted confidence-based sampling.

## Overview

This stack provides a complete evaluation infrastructure to:

1. **Sample documents** from production extractions based on confidence scores
2. **Re-evaluate** using more powerful models (e.g., Claude Sonnet 4 in us-east-1)
3. **Compare** baseline vs evaluation results field-by-field
4. **Track metrics** over time for model performance monitoring

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Production Stack (fiscalshield-idp-dev)                     │
│  • ExtractionResultsTable (read-only access)                │
│  • S3 buckets with original documents                       │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  Evaluation Stack (this stack)                              │
├─────────────────────────────────────────────────────────────┤
│  EventBridge Schedule (nightly/weekly)                      │
│           ↓                                                  │
│  Step Functions State Machine                               │
│    1. Sampler Lambda                                         │
│       • Queries ExtractionResultsTable                      │
│       • Weighted sampling by confidence                     │
│       • Creates batch manifest                              │
│    2. Re-Evaluator Lambda                                   │
│       • Option A: Bedrock Batch API (50% discount)         │
│       • Option B: Direct inference (faster)                 │
│    3. Batch Monitor Lambda (if using batch)                 │
│       • Polls job status every hour                         │
│    4. Comparator Lambda                                     │
│       • Field-by-field comparison                           │
│       • Writes metrics to EvaluationMetricsTable           │
└─────────────────────────────────────────────────────────────┘
```

## Table Discovery

The stack automatically discovers the production `ExtractionResultsTable` using:

1. **Pattern matching**: Looks for tables with prefix `{StackName}-ExtractionResultsTable`
2. **Handles CloudFormation suffixes**: Works with names like `fiscalshield-idp-dev-ExtractionResultsTable-ODNDYL7KUECH`
3. **Cross-region support**: Can read from EU tables while using US models

## Sampling Strategy

| Confidence Tier | Threshold | Sampling Rate | Rationale |
|-----------------|-----------|---------------|-----------|
| **Low** | < 0.7 | **100%** | Highest value - likely errors |
| **Medium** | 0.7 - 0.9 | **20%** | Some uncertainty |
| **High** | > 0.9 | **5%** | Baseline monitoring |

## Deployment

### Prerequisites

1. Existing IDP stack deployed (e.g., `fiscalshield-idp-dev`)
2. AWS CLI configured
3. SAM CLI installed

### Deploy Stack

```bash
# Build the stack
sam build --template stacks/evaluation/template.yaml

# Deploy with parameters
sam deploy \
  --template-file .aws-sam/build/template.yaml \
  --stack-name fiscalshield-evaluation-dev \
  --parameter-overrides \
    StackName=fiscalshield-idp-dev \
    EvaluationRegion=us-east-1 \
    EvaluationModelId=us.anthropic.claude-sonnet-4-20250514-v1:0 \
    SamplingRate=10 \
    BatchInferenceEnabled=true \
  --capabilities CAPABILITY_NAMED_IAM \
  --resolve-s3
```

### Configuration Parameters

- `StackName`: Name of production IDP stack (default: `fiscalshield-idp-dev`)
- `EvaluationRegion`: Region for evaluation models (default: `us-east-1`)
- `EvaluationModelId`: Model to use for re-evaluation
- `SamplingRate`: Base percentage of documents to evaluate (default: 10%)
- `LowConfidenceThreshold`: Threshold below which all docs are evaluated (default: 0.7)
- `EvaluationSchedule`: Cron expression for automated runs (default: daily at 2 AM)
- `BatchInferenceEnabled`: Use batch API for 50% cost savings (default: true)

## Database Schema

### EvaluationMetricsTable

```
PK: evaluation#{evaluationId}
SK: doc#{documentId}

Attributes:
  • BaselineModel: "claude-3-7-sonnet"
  • EvaluationModel: "claude-sonnet-4"
  • DocumentType: "INVOICE"
  • ConfidenceTier: "low|medium|high"
  • FieldAccuracy: {
      InvoiceNumber: 1.0,
      TotalAmount: 0.95,
      ...
    }
  • ExactMatches: 12
  • FuzzyMatches: 3
  • Mismatches: 2
  • CostBaseline: 0.015
  • CostEvaluation: 0.003
  • EvaluationDate: 1700000000

GSI1-ByEvaluationDate:
  PK: evaluation#{evaluationId}
  SK: EvaluationDate
```

### BatchJobsTable

```
JobId: "20251123-140530"
Status: "PENDING|RUNNING|COMPLETED|FAILED"
CreatedAt: 1700000000
ManifestUri: "s3://bucket/batch-inputs/..."
TotalDocuments: 150
```

## Batch Inference vs Direct Processing

### Batch Inference (Recommended for Production)
- **Cost**: 50% discount ($1.50 vs $3.00 per 1M input tokens)
- **Latency**: 6-24 hours
- **Minimum**: ~100 documents recommended for cost-effectiveness
- **Best for**: Daily/weekly evaluation runs with high volume

### Direct Processing (Recommended for Development)
- **Cost**: Full price ($3.00 per 1M input tokens)
- **Latency**: Seconds to minutes
- **Minimum**: No minimum batch size
- **Best for**: Low volume, immediate feedback, testing

**Switch between modes**: Set `BatchInferenceEnabled` parameter to `true` or `false`

## Cost Estimation

### Example: 1000 documents/day, 10% sampling rate

| Component | Usage | Cost/Month |
|-----------|-------|------------|
| **Sampling Lambda** | 30 executions | $0.01 |
| **Batch Inference** | 3000 pages/month @ $0.0015/page | **$4.50** |
| **Comparator Lambda** | 3000 executions | $0.15 |
| **DynamoDB** | 3000 writes + reads | $1.50 |
| **S3 Storage** | 1 GB/month | $0.02 |
| **Total** | | **~$6.18/month** |

Compare to:
- Textract baseline: $195/month (3000 pages × $0.065)
- On-demand LLM: $9-15/month

**Note**: Production with higher volume (10,000+ docs/month) benefits significantly more from batch inference.

## Querying Metrics

### Get latest evaluation results

```python
import boto3
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("fiscalshield-idp-dev-EvaluationMetrics")

# Query by evaluation run
response = table.query(
    KeyConditionExpression=Key("PK").eq("evaluation#20251123-140530")
)

# Calculate aggregate metrics
total_docs = len(response["Items"])
exact_match_rate = sum(
    1 for item in response["Items"] 
    if item.get("ExactMatches", 0) > item.get("Mismatches", 0)
) / total_docs

print(f"Exact match rate: {exact_match_rate:.1%}")
```

### Query by date range

```python
from datetime import datetime, timedelta

cutoff = int((datetime.now() - timedelta(days=7)).timestamp())

response = table.query(
    IndexName="GSI1-ByEvaluationDate",
    KeyConditionExpression=Key("GSI1PK").eq("metrics") & Key("EvaluationDate").gte(cutoff)
)
```

## Manual Execution

Trigger evaluation manually via Step Functions:

```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:eu-central-1:123456:stateMachine:fiscalshield-idp-dev-EvaluationPipeline \
  --input '{"evaluationType": "manual", "lookbackDays": 7}'
```

## Monitoring

CloudWatch metrics automatically tracked:
- Documents sampled by confidence tier
- Batch job duration
- Field-level accuracy rates
- Cost per evaluation run

## Future Enhancements

1. **Athena integration**: Query metrics via SQL
2. **QuickSight dashboards**: Visualize model performance trends
3. **SNS alerts**: Notify when accuracy drops below threshold
4. **A/B testing**: Compare multiple models simultaneously
5. **Fine-tuning feedback loop**: Use low-accuracy samples for training data

## Related Documentation

- [Main IDP Stack](../../README.md)
- [Batch Inference Guide](https://docs.aws.amazon.com/bedrock/latest/userguide/batch-inference.html)
- [ExtractionResultsTable Schema](../../EXTRACTION_RESULTS_IMPLEMENTATION.md)

---

**Note**: This stack is designed for **development/testing**. For production deployment with client data, ensure all resources remain in EU regions for GDPR compliance.
