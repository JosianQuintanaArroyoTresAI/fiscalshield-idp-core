# AML Infrastructure Setup - Complete ✅

**Date**: October 27, 2025  
**Stack**: `fiscalshield-dc-dev`  
**Region**: `eu-central-1`

---

## 📋 Summary

Successfully added AML (Anti-Money Laundering) infrastructure to the Data Collection Stack for collecting sanctions/PEP data and adverse media information.

---

## ✅ Resources Deployed

### 1. Secrets Manager (2 new secrets)

| Secret Name | Purpose | Status |
|------------|---------|--------|
| `fiscalshield-dc-dev-OpenSanctionsAPI` | Sanctions & PEP screening API key | ✅ Created with real key from eu-west-2 |
| `fiscalshield-dc-dev-NewsAPI` | Adverse media screening API key | ✅ Created with real key from eu-west-2 |

**Secret ARNs**:
```
OpenSanctions: arn:aws:secretsmanager:eu-central-1:864899848062:secret:fiscalshield-dc-dev-OpenSanctionsAPI-dtue6X
NewsAPI:       arn:aws:secretsmanager:eu-central-1:864899848062:secret:fiscalshield-dc-dev-NewsAPI-cKBMV9
```

**Secret Structure** (JSON):
```json
{
  "api_key": "<REAL_API_KEY>",
  "base_url": "https://api.opensanctions.org",
  "rate_limit": 100,
  "rate_limit_window": 60
}
```

### 2. IAM Permissions (Updated)

**Role**: `fiscalshield-dc-dev-LambdaExecutionRole`

Added permissions to access:
- ✅ Local secrets (eu-central-1): OpenSanctions, NewsAPI
- ✅ Cross-region secrets (eu-west-2): taxguard/opensanctions/*, taxguard/newsapi/*

### 3. Data Storage (Reused existing resources)

**No new DynamoDB tables or S3 buckets created** - reusing existing infrastructure:

| Resource | Purpose | Storage Pattern |
|----------|---------|----------------|
| `CompanyEventsTable` (DynamoDB) | Store sanctions/PEP data | SK: `SANCTIONS#OFFICER#{name}#{date}` |
| `CompanyEventsTable` (DynamoDB) | Store media summary | SK: `ADVERSE_MEDIA#{date}` |
| `DataArchiveBucket` (S3) | Store full article data | Prefix: `adverse-media/` |

**Cache TTL**:
- Sanctions/PEP: 30 days (changes slowly)
- Adverse Media: 7 days (time-sensitive)

---

## 🔧 Scripts Created

### `copy-aml-secrets.sh`

**Purpose**: Copy real API keys from eu-west-2 to eu-central-1

**Usage**:
```bash
cd stacks/data-collection
./copy-aml-secrets.sh dev
```

**What it does**:
1. Fetches secrets from `taxguard/opensanctions/api-key` and `taxguard/newsapi/api-key` (eu-west-2)
2. Updates CloudFormation-managed secrets in eu-central-1
3. Verifies secrets exist and are accessible

**Status**: ✅ Successfully executed - secrets updated with real keys

---

## 📝 Design Decisions

### Secret Management Strategy

**Chosen Approach**: CloudFormation-managed secrets with manual updates (Option A)

**Pattern** (consistent with existing Companies House secret):
1. CloudFormation creates secret with PLACEHOLDER value
2. Deployment succeeds
3. Script copies real API key from eu-west-2
4. Secret is updated with real credentials
5. Lambda functions can access via IAM permissions

**Alternative Rejected**: Externally-managed secrets (inconsistent with existing pattern)

### Resource Reuse

**No new tables or buckets** - following AWS best practices:
- ✅ Reuse `CompanyEventsTable` with different sort key patterns
- ✅ Reuse `DataArchiveBucket` with different S3 prefixes
- ✅ Saves costs (no additional DynamoDB/S3 charges)
- ✅ Simplifies architecture (fewer resources to manage)

---

## 🚀 Next Steps

### Phase 11.5: AML Lambda Functions (30% complete → Next: 70%)

**Remaining tasks**:

1. **Create Sanctions Checker Lambda**
   - Path: `src/data_collection/aml/sanctions_checker/`
   - Endpoint: `GET /sanctions/{officer_name}`
   - Features:
     - OpenSanctions API integration
     - Fuzzy name matching
     - PEP detection (current vs former)
     - DynamoDB caching (30-day TTL)
     - Rate limiting

2. **Create Media Checker Lambda**
   - Path: `src/data_collection/aml/media_checker/`
   - Endpoint: `GET /media/{company_name}`
   - Features:
     - NewsAPI integration
     - Keyword filtering (negative terms)
     - Optional LLM analysis (Bedrock)
     - S3 article storage (full data)
     - DynamoDB summary (7-day TTL)

3. **Add API Gateway Endpoints**
   - Update `template.yaml` to add Lambda functions
   - Add API Gateway routes
   - Enable CORS

4. **Update Step Functions**
   - Extend `CompanyResearchStateMachine`
   - Add AML screening branches (optional/parallel)
   - Handle graceful degradation if AML fails

5. **Testing**
   - Unit tests for sanctions matching
   - Integration tests with real APIs
   - End-to-end test with Step Functions

---

## 📊 Progress Tracker

**Phase 11.5: AML Data Collection** - 30% Complete

```
Infrastructure Setup          [██████████░░░░░░░░░░]  50% ✅
Secrets Management            [████████████████████] 100% ✅
IAM Permissions               [████████████████████] 100% ✅
Data Storage Strategy         [████████████████████] 100% ✅
Lambda Functions              [░░░░░░░░░░░░░░░░░░░░]   0% ❌
API Gateway Endpoints         [░░░░░░░░░░░░░░░░░░░░]   0% ❌
Step Functions Integration    [░░░░░░░░░░░░░░░░░░░░]   0% ❌
Testing                       [░░░░░░░░░░░░░░░░░░░░]   0% ❌
```

---

## 🔍 Verification Commands

### Check Secrets Exist
```bash
# OpenSanctions
aws secretsmanager describe-secret \
  --secret-id fiscalshield-dc-dev-OpenSanctionsAPI \
  --region eu-central-1

# NewsAPI
aws secretsmanager describe-secret \
  --secret-id fiscalshield-dc-dev-NewsAPI \
  --region eu-central-1
```

### Check IAM Permissions
```bash
aws iam get-role-policy \
  --role-name fiscalshield-dc-dev-LambdaExecutionRole \
  --policy-name SecretsManagerAccess \
  --region eu-central-1
```

### Test Secret Access from Lambda
```python
import boto3
import json

# From Lambda function
secrets_client = boto3.client('secretsmanager', region_name='eu-central-1')

# Get OpenSanctions key
response = secrets_client.get_secret_value(
    SecretId='fiscalshield-dc-dev-OpenSanctionsAPI'
)
credentials = json.loads(response['SecretString'])
api_key = credentials['api_key']  # Real key from eu-west-2
```

---

## 📚 Reference Documents

- **AML Technical Documentation**: `/docs/AML_TECHNICAL_DOCUMENTATION.md`
- **Data Collection Progress**: `/docs/DATA_COLLECTION_PROGRESS.md`
- **CloudFormation Template**: `/stacks/data-collection/template.yaml`
- **Secret Copy Script**: `/stacks/data-collection/copy-aml-secrets.sh`

---

## ✅ Deployment Checklist

- [x] Add secret definitions to CloudFormation template
- [x] Update IAM role with secret access permissions
- [x] Create secret copy script
- [x] Delete manually created secrets (to avoid conflicts)
- [x] Deploy CloudFormation stack
- [x] Run secret copy script to populate real keys
- [x] Verify secrets exist and are accessible
- [ ] Create Sanctions Checker Lambda (next)
- [ ] Create Media Checker Lambda (next)
- [ ] Add API Gateway endpoints (next)
- [ ] Update Step Functions (next)
- [ ] Integration testing (next)

---

**Status**: Infrastructure complete ✅  
**Next**: Implement Lambda functions 🚀
