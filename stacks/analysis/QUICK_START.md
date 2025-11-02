# Analysis Stack - Quick Start Guide

## 🎯 What We Just Created

A **minimal, deployable Analysis Stack** with:
- ✅ CloudFormation/SAM template
- ✅ DynamoDB table for company intelligence
- ✅ Placeholder Lambda functions
- ✅ API Gateway with 2 endpoints
- ✅ IAM roles with cross-stack permissions
- ✅ SSM parameter export for API URL
- ✅ Deployment script

## 📁 Files Created

```
stacks/analysis/
├── template.yaml                          # CloudFormation template
├── samconfig.toml                         # SAM deployment config
├── deploy-analysis-dev.sh                 # Deployment script ✅ EXECUTABLE
├── README.md                              # Stack documentation
└── parameters/
    ├── dev.json                           # Dev parameters
    └── prod.json                          # Prod parameters

src/analysis/
├── __init__.py
├── common/
│   ├── constants.py                       # Environment variables, naming conventions
│   └── health.py                          # Health check Lambda
└── company_intelligence/
    └── assess_company/
        └── handler.py                     # AssessCompany Lambda (PLACEHOLDER)
```

## 🚀 Deploy Now

```bash
cd /home/josian/git/fiscalshield-idp-core/stacks/analysis
./deploy-analysis-dev.sh
```

**What happens:**
1. SAM builds Lambda functions
2. Deploys CloudFormation stack to `eu-central-1`
3. Creates DynamoDB table: `fiscalshield-analysis-dev-CompanyIntelligence`
4. Deploys 2 Lambda functions with placeholder code
5. Creates API Gateway
6. Exports API URL to SSM: `/fiscalshield/analysis/dev/api-url`
7. Tests health endpoint automatically

**Estimated time:** ~3-5 minutes

## 📊 What You Get

### API Endpoints (After Deployment)

```bash
# Health check
GET https://{api-id}.execute-api.eu-central-1.amazonaws.com/dev/health

# Company intelligence (placeholder)
GET https://{api-id}.execute-api.eu-central-1.amazonaws.com/dev/company/{company_number}/intelligence
```

### Example Response (Placeholder)

```bash
curl https://{api-id}.execute-api.eu-central-1.amazonaws.com/dev/company/12345678/intelligence
```

```json
{
  "success": true,
  "company_number": "12345678",
  "status": "placeholder",
  "message": "Analysis Stack deployed successfully. Real risk assessment coming in Phase 2.",
  "risk_assessment": {
    "risk_score": 0.25,
    "risk_level": "LOW",
    "risk_factors": {
      "sanctions_matches": 0,
      "pep_matches": 0,
      "director_turnover": 0,
      "filing_issues": 0,
      "adverse_media": 0
    },
    "recommendations": "Standard CDD procedures sufficient (mock data)"
  },
  "governance": {
    "director_stability": "good",
    "officer_turnover_rate": 0.0
  },
  "data_sources": {
    "companies_house": "available (via Data Collection Stack)",
    "sanctions": "available (via Data Collection Stack)"
  }
}
```

## 🔍 Verify Deployment

### 1. Check CloudFormation Stack
```bash
aws cloudformation describe-stacks \
  --stack-name fiscalshield-analysis-dev \
  --region eu-central-1 \
  --query 'Stacks[0].StackStatus'
```

Expected: `CREATE_COMPLETE`

### 2. Check SSM Parameter
```bash
aws ssm get-parameter \
  --name /fiscalshield/analysis/dev/api-url \
  --region eu-central-1 \
  --query 'Parameter.Value' \
  --output text
```

Expected: `https://{api-id}.execute-api.eu-central-1.amazonaws.com/dev`

### 3. Check DynamoDB Table
```bash
aws dynamodb describe-table \
  --table-name fiscalshield-analysis-dev-CompanyIntelligence \
  --region eu-central-1 \
  --query 'Table.TableStatus'
```

Expected: `ACTIVE`

### 4. Test Health Endpoint
```bash
API_URL=$(aws ssm get-parameter \
  --name /fiscalshield/analysis/dev/api-url \
  --region eu-central-1 \
  --query 'Parameter.Value' \
  --output text)

curl $API_URL/health | python3 -m json.tool
```

Expected:
```json
{
  "status": "available",
  "stack": "fiscalshield-analysis",
  "environment": "dev",
  "services": {
    "company_intelligence": "operational",
    "risk_assessment": "operational",
    "dynamodb": "operational"
  }
}
```

## 🎨 Frontend Integration (Next Step)

Once the stack is deployed, the frontend can discover it:

```javascript
// src/ui/src/services/analysis.js (to be created)

import { SSMClient, GetParameterCommand } from '@aws-sdk/client-ssm';

const ANALYSIS_API_PARAM = '/fiscalshield/analysis/dev/api-url';

const getAnalysisApiUrl = async () => {
  const ssmClient = new SSMClient({ /* ... */ });
  const command = new GetParameterCommand({ Name: ANALYSIS_API_PARAM });
  const response = await ssmClient.send(command);
  return response.Parameter.Value;
};
```

## 🔧 Current State: PLACEHOLDER

The Lambda functions return **mock data** for now:
- ✅ Stack deploys successfully
- ✅ API Gateway works
- ✅ Health check operational
- ✅ IAM permissions configured
- 🔄 AssessCompany returns placeholder data (real logic in Phase 2)

## 📝 Next Steps

**After successful deployment:**

1. ✅ **Verify stack is working** (use commands above)
2. ✅ **Test both endpoints** (health + company intelligence)
3. ✅ **Check logs** to ensure no errors
4. ⏭️ **Phase 2**: Implement real risk calculation logic
5. ⏭️ **Phase 3**: Add frontend Company Intelligence page

## 🐛 Troubleshooting

### Stack deployment fails
```bash
# Check error details
aws cloudformation describe-stack-events \
  --stack-name fiscalshield-analysis-dev \
  --region eu-central-1 \
  --max-items 5
```

### Lambda errors
```bash
# Check Lambda logs
aws logs tail /aws/lambda/fiscalshield-analysis-dev-AssessCompany --follow
```

### Cross-stack permission issues
The IAM role has read access to Data Collection tables. If errors occur:
```bash
# Verify IAM policy
aws iam get-role-policy \
  --role-name fiscalshield-analysis-dev-LambdaExecutionRole \
  --policy-name DynamoDBAccess
```

## 💰 Cost

**Monthly (100 requests/month):**
- Lambda: ~$0.50
- DynamoDB: ~$1.00
- API Gateway: ~$0.35
- CloudWatch: ~$0.50

**Total: ~$2.50/month** 💚

Very minimal cost for a placeholder stack!

## ✅ Success Criteria

You know the deployment worked if:
- ✅ CloudFormation stack status: `CREATE_COMPLETE`
- ✅ Health endpoint returns `"status": "available"`
- ✅ Company intelligence endpoint returns mock data
- ✅ SSM parameter exists with API URL
- ✅ DynamoDB table exists and is `ACTIVE`
- ✅ No errors in CloudWatch Logs

---

**Ready to deploy? Run:**
```bash
cd /home/josian/git/fiscalshield-idp-core/stacks/analysis
./deploy-analysis-dev.sh
```
