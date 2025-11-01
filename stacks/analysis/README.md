# FiscalShield Analysis Stack

**Stack Name:** `fiscalshield-analysis`  
**Purpose:** Company intelligence and risk assessment services  
**Status:** Phase 1 - Minimal Deployment (Placeholder Lambdas)

## Overview

This stack analyzes data from the Data Collection Stack to generate comprehensive company intelligence reports including:
- Risk assessment and scoring
- Governance insights (director stability, sanctions)
- Financial compliance (filing history)
- Reputational analysis (adverse media)
- AML screening (sanctions, PEP)

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Analysis Stack                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  API Gateway                                                │ │
│  │  ├─ GET /health                                             │ │
│  │  └─ GET /company/{company_number}/intelligence             │ │
│  └─────────────────────────┬──────────────────────────────────┘ │
│                            │                                     │
│  ┌─────────────────────────▼──────────────────────────────────┐ │
│  │  Lambda: AssessCompany                                      │ │
│  │  • Reads from Data Collection Stack tables                 │ │
│  │  • Calculates risk scores                                   │ │
│  │  • Caches results in CompanyIntelligenceTable              │ │
│  └─────────────────────────┬──────────────────────────────────┘ │
│                            │                                     │
│  ┌─────────────────────────▼──────────────────────────────────┐ │
│  │  DynamoDB: CompanyIntelligenceTable                         │ │
│  │  • Stores analysis results                                  │ │
│  │  • 24-hour cache TTL                                        │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                            │ Reads data from
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  Data Collection Stack (Read-Only Access)                        │
│  ├─ CompanyEventsTable (company, officers, PSC, sanctions)      │
│  ├─ FilingEventsTable (filing history)                          │
│  └─ HMRCGuidanceTable (compliance rules)                        │
└─────────────────────────────────────────────────────────────────┘
```

## Resources Created

### DynamoDB Tables
- `fiscalshield-analysis-{env}-CompanyIntelligence` - Analysis results cache

### Lambda Functions
- `fiscalshield-analysis-{env}-AssessCompany` - Generate company intelligence (PLACEHOLDER)
- `fiscalshield-analysis-{env}-HealthCheck` - Stack availability check

### API Gateway
- `/health` - Health check endpoint
- `/company/{company_number}/intelligence` - Get company intelligence report

### SSM Parameters
- `/fiscalshield/analysis/{env}/api-url` - API Gateway URL for cross-stack integration

## Deployment

### Prerequisites
```bash
# Install AWS SAM CLI
pip install aws-sam-cli

# Configure AWS credentials
aws configure

# Set environment variables
export ENVIRONMENT=dev
```

### Deploy to Dev
```bash
cd stacks/analysis
./deploy-analysis-dev.sh
```

This will:
1. Build Lambda functions with SAM
2. Deploy CloudFormation stack
3. Wait for completion
4. Display API Gateway URL and endpoints

## Configuration

### Environment Parameters

The stack uses convention-based naming for cross-stack resource access:
- Data Collection tables: `fiscalshield-dc-{env}-{TableName}`
- Analysis tables: `fiscalshield-analysis-{env}-{TableName}`

No additional configuration required for cross-stack access.

## Testing

### Health Check
```bash
# Get API URL from SSM Parameter Store
API_URL=$(aws ssm get-parameter \
  --name /fiscalshield/analysis/dev/api-url \
  --query 'Parameter.Value' \
  --output text)

# Test health endpoint
curl $API_URL/health
```

### Company Intelligence (Placeholder)
```bash
# Test company intelligence endpoint
curl $API_URL/company/12345678/intelligence
```

Expected response:
```json
{
  "success": true,
  "company_number": "12345678",
  "status": "placeholder",
  "message": "Analysis Stack deployed successfully. Real risk assessment coming in Phase 2.",
  "risk_assessment": {
    "risk_score": 0.25,
    "risk_level": "LOW"
  }
}
```

## Current Status: Phase 1 - Placeholder

✅ Infrastructure deployed  
✅ API Gateway operational  
✅ DynamoDB table created  
✅ IAM permissions configured  
✅ Health check working  
🔄 AssessCompany Lambda returns mock data (replace in Phase 2)

## Next Steps

**Phase 2: Real Risk Assessment**
- [ ] Implement risk calculation logic
- [ ] Read from Data Collection Stack tables
- [ ] Apply weighted risk scoring algorithm
- [ ] Cache results in DynamoDB

**Phase 3: Frontend Integration**
- [ ] Create Company Intelligence page in Core Stack
- [ ] Add SSM parameter reading
- [ ] Display risk assessment results

**Phase 4: Advanced Features**
- [ ] Historical tracking
- [ ] Trend analysis
- [ ] AI report generation

## Monitoring

### CloudWatch Logs
```bash
# View AssessCompany logs
aws logs tail /aws/lambda/fiscalshield-analysis-dev-AssessCompany --follow

# View Health Check logs
aws logs tail /aws/lambda/fiscalshield-analysis-dev-HealthCheck --follow
```

### CloudWatch Metrics
Key metrics automatically tracked:
- Lambda invocations
- Error rates
- Duration

## Cost Estimation

For 100 assessments/month:
- Lambda: ~$0.50
- DynamoDB: ~$1.00
- API Gateway: ~$0.35
- CloudWatch: ~$0.50

**Total: ~$2.50/month** 💚

## Cross-Stack Integration

### IAM Permissions
Analysis Stack Lambda has **read-only** access to:
- `fiscalshield-dc-{env}-CompanyEvents`
- `fiscalshield-dc-{env}-FilingEvents`
- `fiscalshield-dc-{env}-HMRCGuidance`

### SSM Parameter Store
Analysis Stack exports API URL:
```
/fiscalshield/analysis/dev/api-url
```

Core Stack frontend reads this parameter to discover the Analysis Stack.

## Support

For issues or questions, contact the FiscalShield Backend Team.

## References

- [Data Collection Stack](../data-collection/README.md)
- [AML Implementation Guide](../../AML_README.md)
