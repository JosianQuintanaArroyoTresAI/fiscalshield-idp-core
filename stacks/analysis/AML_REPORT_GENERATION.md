# AML Report Generation Feature

## Overview

The AML Report Generation feature generates professional Customer Due Diligence (CDD) reports for UK accounting firms using Amazon Bedrock (Claude 3.5 Sonnet v2). Reports follow MLR 2017 requirements and provide actionable recommendations for accountants.

## Architecture

### Components

1. **GenerateReport Lambda Function**
   - Retrieves intelligence data from Analysis Stack
   - Formats data for Claude
   - Calls Bedrock API to generate professional report
   - Stores report in S3 with presigned URL

2. **AML Reports S3 Bucket**
   - Stores generated markdown reports
   - Encrypted at rest (AES256)
   - 90-day lifecycle policy
   - Presigned URLs valid for 7 days

3. **API Gateway Endpoint**
   - `POST /company/{company_number}/report`
   - CORS enabled for frontend access
   - Integrated with Lambda function

4. **Frontend Integration**
   - "Generate AML Report" button on Company Intelligence page
   - Shows download link after generation
   - Error handling for missing data

## Prerequisites

### 1. Amazon Bedrock Access

You need access to **Claude 3.5 Sonnet v2** in **eu-west-2** (London) region.

#### Enable Bedrock Model Access

1. Go to AWS Console → Amazon Bedrock → Model access
2. Request access to: `anthropic.claude-3-5-sonnet-20241022-v2:0`
3. Wait for approval (usually instant for standard accounts)

#### Check Model Availability

```bash
aws bedrock list-foundation-models \
  --region eu-west-2 \
  --query 'modelSummaries[?contains(modelId, `claude-3-5-sonnet`)].{ModelId:modelId,Status:modelLifecycle.status}' \
  --output table
```

### 2. Required IAM Permissions

The Lambda execution role includes:

- **Bedrock**: `bedrock:InvokeModel` for Claude models
- **S3**: Read/Write to AML Reports bucket
- **DynamoDB**: Read from CompanyIntelligenceTable and Data Collection tables

## Deployment

### 1. Deploy Analysis Stack

```bash
cd /home/josian/git/fiscalshield-idp-core/stacks/analysis

# Build and deploy
sam build
sam deploy --config-env dev --region eu-central-1
```

The stack will create:
- ✅ S3 bucket: `fiscalshield-analysis-dev-aml-reports-{AccountId}`
- ✅ Lambda function: `fiscalshield-analysis-dev-GenerateReport`
- ✅ API endpoint: `POST /company/{company_number}/report`

### 2. Verify Deployment

```bash
# Get API URL
aws ssm get-parameter \
  --name /fiscalshield/analysis/dev/api-url \
  --region eu-central-1 \
  --query 'Parameter.Value' \
  --output text

# Test report generation endpoint
COMPANY_NUMBER="04409952"
API_URL=$(aws ssm get-parameter --name /fiscalshield/analysis/dev/api-url --region eu-central-1 --query 'Parameter.Value' --output text)

curl -X POST "$API_URL/company/$COMPANY_NUMBER/report" \
  -H "Content-Type: application/json"
```

Expected response:
```json
{
  "success": true,
  "company_number": "04409952",
  "company_name": "AMAZON UK SERVICES LTD.",
  "risk_level": "LOW",
  "report_id": "report_20251102_120000",
  "download_url": "https://...",
  "tokens_used": {
    "input": 2500,
    "output": 1800,
    "total": 4300
  }
}
```

### 3. Deploy Frontend

The frontend changes are already in place. After deploying the Analysis Stack, rebuild and deploy the UI:

```bash
cd /home/josian/git/fiscalshield-idp-core

# Frontend will automatically detect the new endpoint
sam build UIFunction
sam deploy --config-env dev --region eu-central-1
```

## Usage Flow

### 1. User Journey

1. User navigates to **Company Intelligence** page
2. Views risk assessment and AML screening results
3. Clicks **"Generate AML Report"** button
4. Lambda generates professional report using Claude (20-40 seconds)
5. Download link appears (valid for 7 days)
6. User downloads markdown report for client files

### 2. Report Structure

Generated reports include:

- **Executive Summary**: Risk rating and recommendation
- **Entity Overview**: Company structure and business
- **Screening Results**: Companies House, Sanctions, PEP, Media
- **Risk Assessment**: Detailed analysis with MLR 2017 context
- **Red Flags**: Critical and high-risk issues
- **CDD Recommendations**: Specific actions required
- **Compliance Notes**: MLR 2017 requirements and record keeping

### 3. Data Sources

Reports analyze:
- Company Intelligence assessment (from Analysis Stack)
- Risk scoring and flags
- Sanctions and PEP screening results
- Adverse media findings
- Companies House data
- Governance and financial compliance

## Cost Considerations

### Bedrock Pricing (Claude 3.5 Sonnet v2)

- **Input tokens**: ~2,500 per report (~$0.0075)
- **Output tokens**: ~1,800 per report (~$0.0135)
- **Total per report**: ~$0.021

### S3 Storage

- **Storage**: $0.023 per GB/month (minimal, ~500KB per report)
- **Requests**: $0.0004 per request
- **Data transfer**: First 1GB free, $0.09/GB after

### Example Monthly Cost

- 100 reports/month: ~$2.10 (Bedrock) + $0.50 (S3) = **~$2.60/month**
- 1,000 reports/month: ~$21 (Bedrock) + $3 (S3) = **~$24/month**

## Monitoring

### CloudWatch Metrics

```bash
# View report generation metrics
aws cloudwatch get-metric-statistics \
  --namespace FiscalShield/Analysis \
  --metric-name ReportGenerated \
  --start-time 2025-11-01T00:00:00Z \
  --end-time 2025-11-02T00:00:00Z \
  --period 3600 \
  --statistics Sum \
  --region eu-central-1
```

### Lambda Logs

```bash
# View report generation logs
aws logs tail /aws/lambda/fiscalshield-analysis-dev-GenerateReport \
  --region eu-central-1 \
  --follow
```

### S3 Report Inventory

```bash
# List generated reports
aws s3 ls s3://fiscalshield-analysis-dev-aml-reports-{AccountId}/aml-reports/ \
  --recursive \
  --human-readable
```

## Troubleshooting

### "Analysis Stack is not available"

- Check Analysis Stack is deployed: `sam list stack-outputs --stack-name fiscalshield-analysis-dev`
- Verify SSM parameter exists: `aws ssm get-parameter --name /fiscalshield/analysis/dev/api-url`

### "No intelligence data found for this company"

- Company intelligence must be generated first
- Visit Company Intelligence page and click "Refresh Intelligence"
- Ensure Data Collection Stack has company data

### "Failed to generate report"

Check Lambda logs:
```bash
aws logs tail /aws/lambda/fiscalshield-analysis-dev-GenerateReport --follow
```

Common issues:
- **Bedrock access denied**: Enable model access in Bedrock console
- **DynamoDB access**: Verify IAM role has read permissions
- **Timeout**: Increase Lambda timeout (currently 120 seconds)

### "Access Denied" on Download Link

- Presigned URLs expire after 7 days
- Regenerate report to get new download link
- Check S3 bucket permissions if issue persists

## Security

### Data Protection

- **Encryption at rest**: S3 bucket uses AES256 encryption
- **Encryption in transit**: HTTPS only for API and S3
- **Access control**: Private bucket, presigned URLs only

### IAM Best Practices

- Lambda role follows least privilege
- Bedrock access scoped to Claude models only
- S3 access limited to reports bucket only

### Data Retention

- Reports stored for 90 days (lifecycle policy)
- Old reports automatically deleted
- Noncurrent versions deleted after 30 days

## Next Steps

### Planned Enhancements

1. **PDF Generation**: Convert markdown to PDF using Lambda layer
2. **Email Delivery**: Send reports via SES
3. **Report History**: Store metadata in DynamoDB
4. **Custom Templates**: Allow firm-specific branding
5. **Batch Generation**: Generate reports for multiple companies

### Configuration Options

Add to `template.yaml`:
```yaml
Parameters:
  ReportRetentionDays:
    Type: Number
    Default: 90
  
  PresignedUrlExpiryDays:
    Type: Number
    Default: 7
  
  ClaudeModelId:
    Type: String
    Default: anthropic.claude-3-5-sonnet-20241022-v2:0
```

## Support

For issues or questions:
1. Check CloudWatch logs for Lambda errors
2. Verify Bedrock model access in AWS Console
3. Review IAM permissions for Lambda role
4. Test API endpoint directly with curl

## References

- [Amazon Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Claude Model IDs](https://docs.aws.amazon.com/bedrock/latest/userguide/model-ids-arns.html)
- [MLR 2017 Requirements](https://www.legislation.gov.uk/uksi/2017/692/contents/made)
- [ICAEW AML Guidance](https://www.icaew.com/technical/practice-resources/anti-money-laundering)
