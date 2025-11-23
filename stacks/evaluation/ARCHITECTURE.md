# Evaluation Stack - Architecture & Design Decisions

## Key Design Decisions

### 1. **Table Discovery Strategy**

**Problem**: CloudFormation generates random suffixes for resources:
```
fiscalshield-idp-dev-ExtractionResultsTable-ODNDYL7KUECH
                                           ^^^^^^^^^^^^^^
                                           Random suffix
```

**Solution**: Multi-tiered discovery approach:

1. **SSM Parameters** (Recommended for production):
   ```yaml
   # In main stack template.yaml - ADD THIS
   ExtractionResultsTableParameter:
     Type: AWS::SSM::Parameter
     Properties:
       Name: /fiscalshield-idp-dev/extraction/table-name
       Value: !Ref ExtractionResultsTable
       Type: String
   ```

2. **Pattern Matching** (Current implementation):
   ```python
   # In sampler Lambda
   def discover_extraction_table():
       client = boto3.client("dynamodb")
       tables = client.list_tables()
       
       # Find table matching pattern
       prefix = f"{STACK_NAME}-ExtractionResultsTable"
       matching = [t for t in tables if t.startswith(prefix)]
       return matching[0]  # Returns full name with suffix
   ```

3. **CloudFormation Exports** (Alternative):
   ```yaml
   # In main stack
   Outputs:
     ExtractionResultsTableName:
       Value: !Ref ExtractionResultsTable
       Export:
         Name: !Sub "${StackName}-ExtractionTable"
   
   # In evaluation stack
   ExtractionResultsTable:
     Type: String
     Default: ""
   
   # Then use Fn::ImportValue in Lambda environment
   ```

**Why Pattern Matching?**
- ✅ No changes needed to existing stack
- ✅ Works across environments (dev/prod)
- ✅ Handles CloudFormation updates
- ❌ Requires ListTables permission
- ❌ Slightly slower (one-time cost at Lambda cold start)

### 2. **Cross-Region Model Access**

**Architecture**:
```
Production Stack (eu-central-1)          Evaluation Stack (eu-central-1)
┌────────────────────────┐              ┌────────────────────────────┐
│ ExtractionResultsTable │              │ Lambda Functions           │
│ (Read-only access)     │◄─────────────│ • Sampler                  │
│                        │              │ • Comparator               │
│ S3 Buckets             │              │ • Re-evaluator             │
│ (Original documents)   │              │                            │
└────────────────────────┘              └────────────────────────────┘
                                                    │
                                                    ▼
                                         Bedrock Runtime API
                                         (us-east-1)
                                         ┌──────────────────────┐
                                         │ Claude Sonnet 4      │
                                         │ (Best OCR model)     │
                                         └──────────────────────┘
```

**Code Implementation**:
```python
# In re-evaluator Lambda
import boto3

# Create Bedrock client in evaluation region
bedrock_us = boto3.client(
    "bedrock-runtime",
    region_name=os.environ["EVALUATION_REGION"]  # us-east-1
)

# Invoke best model
response = bedrock_us.invoke_model(
    modelId="us.anthropic.claude-sonnet-4-20250514-v1:0",
    body=json.dumps({...})
)
```

**Benefits**:
- Data stays in EU (GDPR compliant at AWS level)
- Access to latest US-only models
- Production traffic unaffected
- Clear separation dev vs production

### 3. **Batch Inference vs Direct**

**Comparison**:

| Aspect | Batch Inference | Direct Inference |
|--------|----------------|------------------|
| **Cost** | **$1.50/1M tokens** (50% off) | $3/1M tokens |
| **Latency** | 6-24 hours | <5 minutes |
| **Concurrency** | Unlimited | Limited by quotas |
| **Use Case** | Overnight evaluation | Real-time validation |
| **API** | `CreateModelInvocationJob` | `InvokeModel` |

**Implementation**:
```python
# Batch mode
if batch_enabled:
    response = bedrock.create_model_invocation_job(
        modelId=model_id,
        inputDataConfig={
            "s3InputDataConfig": {
                "s3Uri": f"s3://{bucket}/batch-inputs/{eval_id}/manifest.jsonl"
            }
        },
        outputDataConfig={
            "s3OutputDataConfig": {
                "s3Uri": f"s3://{bucket}/batch-outputs/{eval_id}/"
            }
        },
        roleArn=batch_role_arn
    )
    
    # State machine waits and polls status
    
# Direct mode
else:
    for document in documents:
        response = bedrock.invoke_model(
            modelId=model_id,
            body=json.dumps({...})
        )
```

**Recommendation**: Use batch for scheduled evaluations (nightly), direct for ad-hoc testing.

### 4. **Sampling Strategy**

**Why Weighted Sampling?**

Not all documents are equally valuable for evaluation:

```python
# Distribution of typical production data
Total: 1000 documents
├─ High confidence (>0.9): 850 docs (85%)  ← Model is confident
├─ Medium confidence (0.7-0.9): 120 docs (12%)  ← Some uncertainty
└─ Low confidence (<0.7): 30 docs (3%)  ← Likely errors

# Naive 10% sampling (100 docs)
├─ High: 85 docs (mostly correct, low value)
├─ Medium: 12 docs
└─ Low: 3 docs (missed errors!)

# Smart weighted sampling (100 docs)
├─ Low: 30 docs (100% of low-conf) ← High value!
├─ Medium: 24 docs (20% of medium)
└─ High: 43 docs (5% of high) ← Baseline check
```

**Code**:
```python
def sample_by_confidence(items):
    sampled = {"low": [], "medium": [], "high": []}
    
    for item in items:
        confidence = float(item.get("ConfidenceScore", 1.0))
        
        if confidence < 0.7:
            sampled["low"].append(item)  # 100% sampling
        elif confidence < 0.9:
            if random.random() < 0.2:  # 20% sampling
                sampled["medium"].append(item)
        else:
            if random.random() < 0.05:  # 5% sampling
                sampled["high"].append(item)
    
    return sampled
```

### 5. **Metrics Schema Design**

**DynamoDB Access Patterns**:

1. Get all results for one evaluation run:
   ```python
   table.query(
       KeyConditionExpression=Key("PK").eq("evaluation#20251123-140530")
   )
   ```

2. Query by date range:
   ```python
   table.query(
       IndexName="GSI1-ByEvaluationDate",
       KeyConditionExpression=
           Key("GSI1PK").eq("metrics") & 
           Key("EvaluationDate").between(start, end)
   )
   ```

3. Compare models over time:
   ```python
   table.query(
       IndexName="GSI2-ByModel",
       KeyConditionExpression=
           Key("GSI1SK").eq("model#claude-sonnet-4") &
           Key("EvaluationDate").gte(last_month)
   )
   ```

**Item Structure**:
```json
{
  "PK": "evaluation#20251123-140530",
  "SK": "doc#abc-123-def",
  "GSI1PK": "metrics",
  "GSI1SK": "model#claude-sonnet-4",
  "EvaluationDate": 1700000000,
  
  "DocumentId": "abc-123-def",
  "DocumentType": "INVOICE",
  "ConfidenceTier": "low",
  
  "BaselineModel": "claude-3-7-sonnet",
  "EvaluationModel": "claude-sonnet-4",
  
  "FieldAccuracy": {
    "InvoiceNumber": 1.0,
    "TotalAmount": 0.95,
    "InvoiceDate": 1.0,
    "VendorName": 0.85
  },
  
  "ExactMatches": 3,
  "FuzzyMatches": 1,
  "Mismatches": 0,
  
  "CostBaseline": 0.015,
  "CostEvaluation": 0.003,
  
  "BaselineExtraction": {...},
  "EvaluationExtraction": {...}
}
```

## Deployment Architecture

```
1. Deploy Production Stack (if not exists)
   ├─ CloudFormation: fiscalshield-idp-dev
   ├─ Region: eu-central-1
   └─ Creates: ExtractionResultsTable-XXXXX

2. Deploy Evaluation Stack
   ├─ CloudFormation: fiscalshield-idp-dev-evaluation
   ├─ Region: eu-central-1
   ├─ Discovers: ExtractionResultsTable via pattern matching
   └─ Creates:
       ├─ EvaluationMetricsTable
       ├─ BatchJobsTable
       ├─ Lambda functions (4)
       ├─ Step Functions state machine
       └─ EventBridge schedule

3. Automatic Nightly Runs
   ├─ EventBridge triggers at 2 AM
   ├─ Sampler queries last 24h extractions
   ├─ Re-evaluator uses us-east-1 models
   ├─ Comparator writes metrics
   └─ Results queryable next morning
```

## Cost Breakdown (Production Scale)

**Assumptions**: 10,000 documents/month, 10% sampling rate (1000 docs)

| Component | Calculation | Monthly Cost |
|-----------|-------------|--------------|
| **Batch Inference** | 1000 pages × 2000 tokens/page × $1.50/1M tokens | **$3.00** |
| **Lambda Execution** | 4 functions × 1000 invocations × $0.20/1M req | $0.80 |
| **DynamoDB Writes** | 1000 writes × $1.25/1M writes | $0.001 |
| **DynamoDB Reads** | 5000 reads × $0.25/1M reads | $0.001 |
| **S3 Storage** | 5 GB × $0.023/GB | $0.12 |
| **S3 API Calls** | 5000 PUTs × $0.005/1000 | $0.03 |
| **Step Functions** | 30 executions × $0.025/1000 transitions | $0.01 |
| **CloudWatch Logs** | 2 GB × $0.50/GB | $1.00 |
| **TOTAL** | | **~$5.00/month** |

**Comparison**:
- Textract baseline (1000 pages): **$65/month**
- Direct LLM inference: **$15/month**
- **Batch LLM (this solution): $5/month** ✅

## Security Considerations

1. **IAM Permissions**: Evaluation stack has read-only access to production tables
2. **Encryption**: All data encrypted at rest (S3, DynamoDB)
3. **Network**: No VPC required (AWS service-to-service)
4. **Data Residency**: Original docs stay in EU, only API calls to US Bedrock
5. **Access Control**: Separate CloudFormation stacks for isolation

## Monitoring

Built-in CloudWatch metrics:
- `EvaluationSamplingRate` - Documents sampled per tier
- `FieldAccuracyRate` - Per-field accuracy over time
- `ModelComparisonCost` - Cost difference between models
- `BatchJobDuration` - Time to complete evaluation
- `ErrorRate` - Failed comparisons

## Next Steps

1. **Deploy to dev**: `./deploy-evaluation.sh dev --batch`
2. **Run test evaluation**: Trigger manually via console
3. **Query metrics**: Check DynamoDB for results
4. **Tune sampling**: Adjust rates based on volume
5. **Add dashboards**: Create CloudWatch/QuickSight visualizations
6. **Consider fine-tuning**: Use low-accuracy docs for training data

---

**Status**: Ready for deployment ✅

**Note**: This is designed for **development testing with US models**. For production client deployments, switch `EvaluationRegion` to `eu-central-1` to maintain full GDPR compliance.
