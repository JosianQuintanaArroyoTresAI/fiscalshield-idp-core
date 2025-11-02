# AML Customer Due Diligence System

An automated Anti-Money Laundering (AML) Customer Due Diligence system for UK accountants, built on AWS serverless architecture.

## 🎯 Project Status

**Phase 1: Companies House Checker** - ✅ **COMPLETE AND DEPLOYED**  
**Phase 2: Sanctions & PEP Checker** - ✅ **COMPLETE AND DEPLOYED**  
**Phase 4: Risk Aggregator** - ✅ **COMPLETE AND DEPLOYED**  
**Phase 5: Report Generator (AI)** - ✅ **COMPLETE AND DEPLOYED**  
**Phase 8: Web Frontend** - ✅ **COMPLETE AND DEPLOYED**

🎉 **PROOF OF CONCEPT FULLY OPERATIONAL** - Complete end-to-end automated screening workflow with interactive web UI and AI-powered professional reports!  
🤖 **AI-POWERED REPORT GENERATOR LIVE** - Professional CDD reports using Claude 3.7 Sonnet via Amazon Bedrock!

### What's Been Implemented

#### ✅ Infrastructure (CloudFormation)
- **DynamoDB Table**: `aml-screening-results-dev` - Stores all screening results
- **S3 Bucket**: `aml-cdd-data-{account-id}-dev` - Stores raw API responses and documents
- **Lambda Function**: `aml-companies-house-checker-dev` - Production-ready with enhanced AML risk analysis
- **Secrets Manager**: Secure storage for Companies House API key
- **IAM Roles**: Least-privilege access for Lambda execution

#### ✅ Companies House Checker Lambda
**Status**: Deployed and tested against real data (Tesco PLC)

**Features**:
- ✅ Retrieves Companies House API key from AWS Secrets Manager
- ✅ Searches companies by name or number
- ✅ Fetches comprehensive company data:
  - Company profile and status
  - Current and historical officers
  - Persons with Significant Control (PSCs)
  - Filing history and compliance status
- ✅ **Enhanced AML Risk Analysis**:
  - High officer turnover relative to company size
  - Rapid officer churn (phoenixing detection)
  - Multiple directors at same non-company address (nominee arrangements)
  - Offshore registered offices and beneficial owners
  - Young companies with complex structures
  - Dormant/dissolved status indicators
  - Late or missing filings
  - PSC structure complexity
- ✅ Risk scoring with severity weights (low/medium/high)
- ✅ Stores raw API responses in S3
- ✅ Stores processed results in DynamoDB
- ✅ CloudWatch logging and metrics
- ✅ AWS X-Ray tracing enabled

**Key Improvements Made**:
- Address normalization to handle Companies House format variations
- Exclusion of company registered office from shared address checks
- Only checks active directors (excludes resigned historical officers)
- Relative turnover calculations (considers company size)
- UK AML-specific red flag detection

#### ✅ Sanctions & PEP Checker Lambda
**Status**: Deployed and tested against real data (Vladimir Putin - sanctions match confirmed)

**Features**:
- ✅ Retrieves OpenSanctions API key from AWS Secrets Manager
- ✅ Searches comprehensive sanctions lists:
  - OFAC (US Treasury)
  - UK HM Treasury (HMT)
  - EU Sanctions
  - UN Sanctions
  - Canada, Australia, Japan, Switzerland, New Zealand
  - Ukraine sanctions lists
- ✅ **PEP (Politically Exposed Persons) Detection**:
  - Current PEPs (active government officials)
  - Former PEPs (within 12-month cooling period)
  - International PEP databases
  - Risk-weighted scoring (current=0.7, former=0.4)
- ✅ **Fuzzy Name Matching**:
  - SequenceMatcher algorithm (70% threshold)
  - Handles name variations and aliases
  - Multiple match detection
- ✅ **Comprehensive Risk Analysis**:
  - Sanctions matches = 0.9 risk score (CRITICAL)
  - Current PEP = 0.7 risk score (HIGH)
  - Former PEP = 0.4 risk score (MEDIUM)
  - Detailed flag reporting with severity levels
- ✅ Stores raw API responses in S3
- ✅ CloudWatch logging and metrics
- ✅ AWS X-Ray tracing enabled

**API Integration**:
- OpenSanctions Commercial API (trial available)
- Bearer token authentication
- Dataset-based sanctions detection
- 14+ jurisdiction coverage

**Key Improvements Made**:
- Dataset-based detection (more reliable than topics field)
- Enhanced sanctions list identification (OFAC, HMT, EU, etc.)
- Current vs former PEP distinction
- Multiple match handling with aggregated risk scores
- Detailed sanctions metadata extraction

#### ✅ Risk Aggregator Lambda
**Status**: Deployed and tested with real data (Tesco PLC - 11 directors screened)

**Features**:
- ✅ Retrieves Companies House and Sanctions results from DynamoDB
- ✅ **Automated Director Screening**:
  - Extracts active directors from Companies House data
  - Invokes Sanctions Lambda for each director
  - Parallel screening workflow (Lambda-to-Lambda invocation)
  - Filters out resigned/inactive officers
- ✅ **Comprehensive Risk Aggregation**:
  - Weighted risk scoring algorithm
  - Sanctions matches: 0.95 weight (CRITICAL)
  - Current PEP: 0.70 weight (HIGH)
  - Former PEP: 0.40 weight (MEDIUM)
  - Companies House flags: 0.50 (high), 0.30 (medium), 0.10 (low)
- ✅ **Risk Level Classification**:
  - LOW: Score 0.0-0.4 (Standard CDD procedures)
  - MEDIUM: Score 0.4-0.7 (Enhanced due diligence)
  - HIGH: Score 0.7+ (Senior management approval required)
- ✅ **Detailed Flag Analysis**:
  - Categorizes all flags by severity (critical/high/medium/low)
  - Identifies sanctioned directors
  - Identifies PEP directors (current and former)
  - Counts total flags across all sources
- ✅ **Human-Readable Summaries**:
  - Overall risk assessment
  - CDD recommendations
  - Director-level breakdown
- ✅ Stores aggregated results in DynamoDB
- ✅ CloudWatch logging and metrics
- ✅ AWS X-Ray tracing enabled

**Test Results** (Tesco PLC):
- Directors screened: 11
- Overall risk score: 0.0
- Risk level: LOW
- Sanctioned directors: 0
- PEP directors: 0
- Recommendation: Standard CDD procedures sufficient

**Key Technical Achievements**:
- Lambda-to-Lambda invocation with IAM permissions
- Decimal type handling for DynamoDB compatibility
- Robust error handling and logging
- Efficient batch processing of directors

#### ✅ Web Frontend (S3 Static Website)
**Status**: Deployed and accessible via public URL

**Features**:
- ✅ **Beautiful, Modern UI** with gradient design and smooth animations
- ✅ **Real-time Progress Tracking**:
  - Active step indicators (bold text for current step)
  - Completed step markers (faded text)
  - Progress details with italic sub-text
  - Auto-scrolling progress section
  - Custom styled scrollbar
- ✅ **Detailed Information Display**:
  - Company information cards (number, status, incorporation date, industry)
  - Director names listed as they're being screened
  - Compliance flags breakdown by severity (🔴 High, 🟡 Medium, 🟢 Low)
  - Real-time sanctions and PEP match notifications
  - Risk score calculation progress
- ✅ **Comprehensive Results Dashboard**:
  - Risk level badge (LOW/MEDIUM/HIGH) with color coding
  - Statistics grid showing:
    - Overall risk score (0.00 - 1.00)
    - Number of directors screened
    - Sanctions matches count
    - PEP matches count
    - Total compliance flags
  - Risk factors breakdown section
  - Severity distribution chart
  - Detailed summary with CDD recommendations
  - List of flagged directors (if any)
- ✅ **Enhanced User Experience**:
  - Responsive design for desktop and mobile
  - Loading spinners and progress indicators
  - Error handling with user-friendly messages
  - "New Screening" button to start over
  - Auto-focus on search input
  - Enter key support for quick searches
- ✅ **Lambda Function URL Integration**:
  - Direct invocation of Companies House Lambda
  - Direct invocation of Risk Aggregator Lambda
  - CORS enabled for browser access
  - JSON payload handling
- ✅ **Professional Design**:
  - Gradient purple/blue theme
  - Card-based layout
  - Smooth transitions and hover effects
  - Color-coded risk levels (green/yellow/red)
  - Clean, modern typography

**Deployment**:
- Hosted on S3 static website hosting
- Public URL: `http://aml-frontend-864899848062-eu-west-2.s3-website.eu-west-2.amazonaws.com`
- One-command deployment: `cd frontend && echo "2" | bash deploy.sh`
- Automatic bucket policy for public access

**User Journey**:
1. Enter company name or number
2. See detailed progress as system:
   - Searches Companies House database
   - Displays company information
   - Analyzes compliance and structure
   - Shows director names
   - Screens each director for sanctions/PEP
   - Calculates aggregate risk score
3. View comprehensive results with:
   - Clear risk level indicator
   - Detailed statistics
   - Risk factor breakdown
   - CDD recommendations
4. **Generate professional AI report**:
   - Click "📄 Generate AI Report" button
   - Watch progress indicators (30-40 seconds)
   - Claude 3.7 Sonnet analyzes all screening data
   - Comprehensive professional CDD report displayed
   - Download as Markdown file
5. Start new screening with one click

**Technical Stack**:
- Pure HTML/CSS/JavaScript (no frameworks required)
- Fetch API for Lambda invocation
- Modern CSS Grid and Flexbox
- Responsive design with media queries
- Progressive disclosure of information

#### ✅ Report Generator Lambda (AI-Powered)
**Status**: Deployed and tested - generating professional reports in 30-40 seconds

**Features**:
- ✅ **AI-Powered Analysis** using Amazon Bedrock (Claude 3.7 Sonnet)
- ✅ Retrieves all screening data from DynamoDB
- ✅ **Professional UK Accountant Reports**:
  - Executive summary for partners
  - Entity overview and structure
  - Detailed screening results analysis
  - Risk assessment with MLR 2017 context
  - Red flags and concerns (or clean confirmation)
  - CDD recommendations (Standard/Enhanced/Simplified DD)
  - Specific actions to take
  - Questions to ask client
  - Compliance notes and record keeping
  - Clear accept/reject/enhanced DD conclusion
- ✅ **Fast Generation**: 30-40 seconds for comprehensive report
- ✅ **Cost Effective**: ~£0.04-£0.06 per report (~2,500 tokens)
- ✅ **Lambda Function URL**: Direct browser access with 90-second timeout support
- ✅ Stores reports in S3 (Markdown) and DynamoDB (metadata)
- ✅ Full report returned in API response for immediate display
- ✅ CloudWatch logging and token usage metrics
- ✅ Frontend integration with progress indicators

**Key Capabilities**:
- Analyzes complex compliance scenarios like senior compliance officer
- Understands UK MLR 2017 requirements in depth
- Provides specific, actionable recommendations  
- Professional tone suitable for client files and audit
- Consistent quality across all risk levels (LOW/MEDIUM/HIGH)
- Complete audit trail for regulatory compliance
- Handles timeout gracefully with extended frontend wait time

**Production Ready**:
- ✅ Bedrock model access configured (Claude 3.7 Sonnet)
- ✅ IAM permissions configured for Bedrock access
- ✅ Lambda Function URL with public access
- ✅ Frontend integrated with "Generate AI Report" button
- ✅ Extended timeout handling (90 seconds in browser)
- ✅ Progress indicators while generating
- ✅ Markdown to HTML conversion for display
- ✅ Download report as .md file

**Technical Implementation**:
- Lambda Function URL: `https://4zovurj2bldnmdtzgzl44ri5xi0yizzz.lambda-url.eu-west-2.on.aws/`
- Model: `anthropic.claude-3-7-sonnet-20250219-v1:0`
- Timeout: 300 seconds (Lambda), 90 seconds (browser with AbortController)
- Temperature: 0.3 (consistent, professional output)
- Max tokens: 4000 (comprehensive reports)
- System prompt: UK AML compliance officer and chartered accountant context

**Documentation**:
- `IMPLEMENTATION_SUMMARY.md` - Complete overview
- `REPORT_GENERATOR_IMPLEMENTATION.md` - Full technical guide
- `REPORT_GENERATOR_QUICK_REFERENCE.md` - Quick start
- `DEPLOYMENT_ACTION_PLAN.md` - Step-by-step deployment
- `test_report_generator.sh` - Automated test script

#### ✅ Deployment Tooling
- **Script**: `infrastructure/deploy-single-lambda.sh` - Fast, reliable Lambda deployment
- **Script**: `infrastructure/deploy-lambdas.sh` - Batch deployment (for future lambdas)
- **Script**: `infrastructure/deploy-yaml.sh` - CloudFormation stack management

## 🏗️ Architecture

```
                        ┌─────────────────────────┐
                        │   Web Browser (User)    │
                        │  S3 Static Website UI   │
                        └───────────┬─────────────┘
                                    │ HTTPS
                                    │
            ┌───────────────────────┴───────────────────────┐
            │                                               │
            ▼                                               ▼
┌───────────────────────────────┐               ┌───────────────────────────────┐
│  Lambda Function URL          │               │  Lambda Function URL          │
│  Companies House Checker      │               │  Risk Aggregator              │
└───────────────┬───────────────┘               └───────────┬───────────────────┘
                │                                           │
                │                                           │ invokes
                │                                           ▼
┌───────────────▼───────────────────────────────────────────────────────────┐
│                     AWS Secrets Manager                                    │
│         (Companies House API Key, OpenSanctions Key)                       │
└───────────────┬────────────────────────────────┬──────────────────────────┘
                │                                │
                │                                │
┌───────────────▼────────────────┐  ┌───────────▼─────────────────────────┐
│   Lambda: Companies            │  │   Lambda: Sanctions                 │
│   House Checker                │  │   Checker                           │
│                                │  │                                     │
│  • Retrieves company data      │  │  • 14+ sanctions lists              │
│  • AML risk analysis           │  │  • PEP detection                    │
│  • Director extraction         │  │  • Fuzzy name matching              │
│  • Red flag detection          │  │  • Risk scoring                     │
└──────┬─────────────────────────┘  └──────┬──────────────────────────────┘
       │                                   │
       │        ┌──────────────────────────┘
       │        │
       ▼        ▼
┌──────────────────────┐
│  DynamoDB Table      │◄─────────────┐
│  (All Results)       │              │
│                      │              │
│  • companies_house   │              │
│  • sanctions_pep     │              │
│  • risk_aggregation  │              │
└──────┬───────────────┘              │
       │                              │
       │                              │
       ▼                         ┌────┴────────────────────────┐
┌─────────────────┐              │   Lambda: Risk              │
│   S3 Bucket     │              │   Aggregator                │
│  (Raw Data)     │              │                             │
│                 │              │  • Reads CH + Sanctions     │
│  /raw-data/     │              │  • Screens all directors ───┘
│  /documents/    │              │  • Calculates aggregate risk│
│  /reports/      │              │  • Generates summary        │
└─────────────────┘              └─────────────────────────────┘
```

**End-to-End Workflow**:
1. **User enters company name** in web frontend
2. **Frontend invokes** Companies House Lambda via Function URL
3. Companies House Lambda retrieves company data + directors
4. **Frontend invokes** Risk Aggregator Lambda via Function URL
5. Risk Aggregator reads CH results from DynamoDB
6. Risk Aggregator invokes Sanctions Lambda for each director
7. Risk Aggregator calculates weighted aggregate risk score
8. Risk Aggregator stores final assessment in DynamoDB
9. **Frontend displays** comprehensive results with risk breakdown


## 📋 Prerequisites

- AWS Account with appropriate permissions
- AWS CLI configured locally
- Python 3.12+ with pip
- Companies House API key (free from https://developer.company-information.service.gov.uk/)
- Bash shell (Linux/macOS/WSL)

## 🚀 Quick Start

### Proof of Concept Demo

The system is fully operational with an interactive web interface:

**🌐 Web Interface** (Recommended):
1. Open: `http://aml-frontend-864899848062-eu-west-2.s3-website.eu-west-2.amazonaws.com`
2. Enter a UK company name or number (e.g., "Tesco PLC" or "00445790")
3. Click "Start AML Screening"
4. Watch detailed progress as the system:
   - Searches Companies House
   - Analyzes company structure and compliance
   - Extracts and displays director names
   - Screens each director for sanctions/PEP
   - Calculates aggregate risk score
5. View comprehensive results with risk breakdown and CDD recommendations
6. Click "📄 Generate AI Report" to get a professional CDD report:
   - Wait 30-40 seconds (progress indicators shown)
   - View the AI-generated professional report
   - Download as Markdown file for your records

**📡 Command Line** (For Testing):

```bash
# Screen a UK company (e.g., Tesco PLC)
aws lambda invoke \
  --function-name aml-companies-house-checker-dev \
  --payload '{"entity_id":"demo_001","company_name":"Tesco PLC"}' \
  response.json

# Aggregate risk and screen all directors
aws lambda invoke \
  --function-name aml-risk-aggregator-dev \
  --payload '{"entity_id":"demo_001","screen_directors":true}' \
  response.json

# View the results
cat response.json
```

**Example Output**:
```json
{
  "statusCode": 200,
  "directors_screened": 11,
  "overall_risk_score": 0.0,
  "risk_level": "LOW",
  "sanctioned_directors": [],
  "pep_directors": [],
  "summary": "Overall Risk Level: LOW (Score: 0.00)\n✅ Recommendation: Standard CDD procedures sufficient"
}
```

This demonstrates the complete automated workflow: company lookup → director extraction → sanctions screening → risk aggregation → CDD recommendation.

---

### Full Setup Instructions

### 1. Clone and Setup

```bash
# Clone repository
git clone <repository-url>
cd money-laundering-detect

# Setup Python virtual environment
python3 -m venv aml
source activate_env.sh  # or source aml/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure AWS Credentials

```bash
# Configure AWS CLI
aws configure

# Set your region (default: eu-west-2)
export AWS_REGION=eu-west-2
export ENVIRONMENT=dev
```

### 3. Store API Keys

```bash
# Store Companies House API Key
aws secretsmanager create-secret \
  --name taxguard/companies-house/api-key \
  --description "Companies House API Key for AML screening" \
  --secret-string "YOUR_COMPANIES_HOUSE_KEY" \
  --region eu-west-2

# Store OpenSanctions API Key
aws secretsmanager create-secret \
  --name taxguard/opensanctions/api-key \
  --description "OpenSanctions API Key for sanctions/PEP screening" \
  --secret-string "YOUR_OPENSANCTIONS_KEY" \
  --region eu-west-2
```

### 4. Deploy Infrastructure

```bash
# Deploy CloudFormation stack
./infrastructure/deploy-yaml.sh

# Wait for stack creation to complete (~5 minutes)
# Stack name: aml-cdd-infrastructure-dev
```

### 5. Deploy Lambda Functions

```bash
# Deploy Companies House Checker
./infrastructure/deploy-single-lambda.sh companies-house-checker

# Deploy Sanctions Checker
./infrastructure/deploy-single-lambda.sh sanctions-checker

# Output will show deployment status and test command
```

### 6. Test the Lambdas

```bash
# Test Companies House Checker with a real UK company (Tesco)
aws lambda invoke \
  --function-name aml-companies-house-checker-dev \
  --region eu-west-2 \
  --cli-binary-format raw-in-base64-out \
  --payload '{"entity_id":"test_001","company_name":"Tesco PLC"}' \
  response.json

# Test Sanctions Checker with a known sanctioned individual
aws lambda invoke \
  --function-name aml-sanctions-checker-dev \
  --region eu-west-2 \
  --cli-binary-format raw-in-base64-out \
  --payload '{"entity_id":"test_putin","entity_name":"Vladimir Putin","entity_type":"individual"}' \
  response.json

# Test Risk Aggregator (requires existing CH data for entity_id)
# This will screen all directors and calculate aggregate risk
aws lambda invoke \
  --function-name aml-risk-aggregator-dev \
  --region eu-west-2 \
  --cli-binary-format raw-in-base64-out \
  --payload '{"entity_id":"test_001","screen_directors":true}' \
  response.json

# View results
cat response.json | python3 -m json.tool
```

### 7. Test End-to-End Workflow

**Option A: Using the Web Interface** (Recommended):

```bash
# Deploy the frontend (if not already deployed)
cd frontend
echo "2" | bash deploy.sh

# Open the URL in your browser
# http://aml-frontend-864899848062-eu-west-2.s3-website.eu-west-2.amazonaws.com

# Enter a company name (e.g., "Tesco PLC" or "00445790")
# Click "Start AML Screening"
# Watch the detailed progress and view results!
```

**Option B: Using Command Line**:

```bash
# Step 1: Screen a company
aws lambda invoke \
  --function-name aml-companies-house-checker-dev \
  --payload '{"entity_id":"tesco_screening","company_name":"Tesco PLC"}' \
  response.json

# Step 2: Aggregate risk (screens all directors automatically)
aws lambda invoke \
  --function-name aml-risk-aggregator-dev \
  --payload '{"entity_id":"tesco_screening","screen_directors":true}' \
  response.json

# Step 3: View aggregated results
cat response.json

# Expected output:
# {
#   "statusCode": 200,
#   "directors_screened": 11,
#   "overall_risk_score": 0.0,
#   "risk_level": "LOW",
#   "sanctioned_directors": [],
#   "pep_directors": [],
#   "summary": "Overall Risk Level: LOW (Score: 0.00)..."
# }
```

### 8. Deploy the Web Frontend (Optional)

If you want to share the screening tool with stakeholders:

```bash
# Navigate to frontend directory
cd frontend

# Deploy to S3 static website
echo "2" | bash deploy.sh

# The script will output your public URL like:
# http://aml-frontend-{account-id}-eu-west-2.s3-website.eu-west-2.amazonaws.com

# Share this URL with your team!
```

**Note**: The Lambda Function URLs are already configured in `index.html`. If you need to update them:

```bash
# Enable Lambda Function URLs (if not already enabled)
aws lambda create-function-url-config \
  --function-name aml-companies-house-checker-dev \
  --auth-type NONE \
  --cors '{"AllowOrigins":["*"],"AllowMethods":["POST"]}' \
  --region eu-west-2

aws lambda create-function-url-config \
  --function-name aml-risk-aggregator-dev \
  --auth-type NONE \
  --cors '{"AllowOrigins":["*"],"AllowMethods":["POST"]}' \
  --region eu-west-2

# Update the URLs in frontend/index.html (line ~455)
# Then re-deploy: cd frontend && echo "2" | bash deploy.sh
```

## 📁 Project Structure

```
money-laundering-detect/
├── README.md                           # This file
├── aml_cdd_implementation_guide.md     # Full implementation guide
├── requirements.txt                    # Python dependencies
├── activate_env.sh                     # Virtualenv activation helper
│
├── frontend/                           # ✅ Web UI (DEPLOYED)
│   ├── index.html                     # Single-page web application
│   ├── deploy.sh                      # S3 deployment script
│   └── README.md                      # Frontend documentation
│
├── infrastructure/                     # Deployment scripts and IaC
│   ├── aml-cdd-infrastructure.yaml    # CloudFormation template
│   ├── deploy-yaml.sh                 # Deploy stack
│   ├── deploy-single-lambda.sh        # Deploy individual Lambda
│   └── deploy-lambdas.sh              # Deploy all Lambdas
│
├── src/
│   └── lambdas/                       # Lambda function code
│       ├── companies_house_checker.py # ✅ DEPLOYED
│       ├── sanctions_checker.py       # ✅ DEPLOYED
│       ├── risk_aggregator.py         # ✅ DEPLOYED
│       ├── media_checker.py           # 🔜 TODO
│       └── report_generator.py        # 🔜 TODO
│
└── tests/                             # Test scripts
    ├── test_companies_house.py        # Local testing
    ├── test_sanctions.py              # Sanctions checker testing
    └── test_secrets_manager.py        # Secrets Manager testing
```

## 🧪 Testing

### Local Testing (Before Deployment)

```bash
# Test Companies House API connection
python test_companies_house.py

# Test Sanctions API connection
python test_sanctions.py

# Test Secrets Manager access
python test_secrets_manager.py
```

### Production Testing (After Deployment)

```bash
# Test Companies House Checker with known good company
aws lambda invoke \
  --function-name aml-companies-house-checker-dev \
  --payload '{"entity_id":"test_low_risk","company_name":"Tesco PLC"}' \
  response.json

# Test Sanctions Checker with known sanctioned individual
aws lambda invoke \
  --function-name aml-sanctions-checker-dev \
  --payload '{"entity_id":"test_sanctions","entity_name":"Vladimir Putin","entity_type":"individual"}' \
  response.json

# Test Sanctions Checker with clean entity
aws lambda invoke \
  --function-name aml-sanctions-checker-dev \
  --payload '{"entity_id":"test_clean","entity_name":"John Smith","entity_type":"individual"}' \
  response.json

# Test Risk Aggregator with full director screening
aws lambda invoke \
  --function-name aml-risk-aggregator-dev \
  --payload '{"entity_id":"test_low_risk","screen_directors":true}' \
  response.json

# Test Report Generator (requires existing screening data)
aws lambda invoke \
  --function-name aml-report-generator-dev \
  --payload '{"entity_id":"test_low_risk"}' \
  response.json

# Check DynamoDB for results (all source types including reports)
aws dynamodb scan \
  --table-name aml-screening-results-dev \
  --filter-expression "entity_id = :eid" \
  --expression-attribute-values '{":eid":{"S":"test_low_risk"}}' \
  --limit 10

# Check S3 for raw data and reports
aws s3 ls s3://aml-cdd-data-{your-account-id}-dev/raw-data/
aws s3 ls s3://aml-cdd-data-{your-account-id}-dev/reports/
```

## 📊 Monitoring & Logs

### CloudWatch Logs

```bash
# View Companies House Checker logs
aws logs tail /aws/lambda/aml-companies-house-checker-dev --follow

# View Sanctions Checker logs
aws logs tail /aws/lambda/aml-sanctions-checker-dev --follow

# View Risk Aggregator logs
aws logs tail /aws/lambda/aml-risk-aggregator-dev --follow

# View Report Generator logs
aws logs tail /aws/lambda/aml-report-generator-dev --follow

# View recent errors
aws logs filter-pattern /aws/lambda/aml-companies-house-checker-dev --filter-pattern "ERROR"
aws logs filter-pattern /aws/lambda/aml-sanctions-checker-dev --filter-pattern "ERROR"
aws logs filter-pattern /aws/lambda/aml-risk-aggregator-dev --filter-pattern "ERROR"
aws logs filter-pattern /aws/lambda/aml-report-generator-dev --filter-pattern "ERROR"
```

### CloudWatch Metrics

Key metrics automatically tracked:
- `CompaniesHouseCheck` - Number of checks performed
- `FlagsFound` - Number of red flags detected
- `CompaniesHouseError` - Error count

### X-Ray Tracing

View detailed execution traces in AWS X-Ray console to debug performance issues.

## 🔒 Security

### API Keys
- ✅ Stored in AWS Secrets Manager (never in code)
- ✅ Encrypted at rest
- ✅ Access logged via CloudTrail

### IAM Roles
- ✅ Least privilege access
- ✅ Separate roles per Lambda
- ✅ No hardcoded credentials

### Data Protection
- ✅ S3 bucket encryption enabled
- ✅ DynamoDB encryption at rest
- ✅ VPC configuration ready (if needed)

## 💰 Cost Estimation

### Current Implementation (Phases 1, 2, 4 & 5)

**Monthly Costs for Moderate Usage (100 screenings/month with reports)**:
- Lambda executions (4 functions): ~$9
- DynamoDB (on-demand): ~$5
- S3 storage: ~$2
- CloudWatch: ~$3
- Secrets Manager (2 secrets): ~$0.80
- Amazon Bedrock (Claude 3.7 Sonnet): ~$6 (100 reports × ~2,500 tokens × $0.003/1K tokens)
- OpenSanctions API (trial/paid): $0-$99
- **Total: ~$26-125/month** (depending on OpenSanctions plan)

**Per-Screening Cost (with AI report)**: ~$0.26-$1.25

### API Costs

**Companies House API**
- ✅ **FREE** - Unlimited queries
- ✅ No registration fees
- ✅ No rate limits (reasonable use)

**OpenSanctions API**
- Trial: Limited queries (testing only)
- Paid plans: Starting at ~$99/month
- Self-hosted option: Free (bulk data downloads)

## 🎯 AML Risk Detection Features

### Implemented Red Flags

1. **High Officer Turnover**
   - Calculates turnover relative to company size
   - Flags if ≥30% turnover in 6 months
   - High severity if ≥50%

2. **Rapid Officer Churn**
   - Detects ≥3 changes in 30 days
   - Indicates possible phoenixing
   - Automatic high severity

3. **Shared Address Red Flag**
   - Detects ≥3 directors at same non-company address
   - Excludes registered office
   - Indicates nominee arrangements

4. **Offshore Indicators**
   - Registered office outside UK
   - PSCs in offshore jurisdictions
   - Multiple offshore connections = high risk

5. **Young Company Complexity**
   - Companies <2 years with complex structures
   - Multiple offshore connections
   - High-risk SIC codes

6. **Compliance Issues**
   - Overdue accounts
   - Overdue confirmation statements
   - Missing filings

7. **Corporate Structure Flags**
   - Dissolved/liquidated status
   - PSC exemptions or super-secure PSCs
   - Frequent address changes

### Phase 2: Sanctions & PEP Detection

1. **Comprehensive Sanctions Screening**
   - OFAC (US Treasury) SDN list
   - UK HM Treasury sanctions
   - EU consolidated sanctions
   - UN Security Council sanctions
   - Canada, Australia, Japan, Switzerland, New Zealand
   - Ukraine war-related sanctions

2. **PEP (Politically Exposed Persons)**
   - Current PEPs (active officials)
   - Former PEPs (12-month cooling period)
   - Family members and close associates
   - International databases (Wikidata, OpenSanctions)

3. **Fuzzy Name Matching**
   - SequenceMatcher algorithm
   - 70% similarity threshold
   - Handles aliases and variations
   - Multiple match aggregation

4. **Risk Scoring**
   - Sanctions match: 0.9 (CRITICAL)
   - Current PEP: 0.7 (HIGH)
   - Former PEP: 0.4 (MEDIUM)
   - Multiple flags: Aggregated score

5. **Dataset Coverage**
   - 14+ international sanctions datasets
   - 2+ PEP databases
   - Real-time API integration
   - Regular updates via OpenSanctions

### Phase 4: Risk Aggregation (IMPLEMENTED)

1. **Comprehensive Data Integration**
   - Retrieves Companies House screening results
   - Retrieves Sanctions/PEP screening results
   - Merges data from multiple DynamoDB records
   - Maintains full audit trail

2. **Automated Director Screening**
   - Extracts active directors from Companies House data
   - Filters out resigned/inactive officers
   - Invokes Sanctions Lambda for each director
   - Parallel processing architecture
   - Lambda-to-Lambda invocation with IAM permissions

3. **Weighted Risk Scoring Algorithm**
   - Sanctions matches: 0.95 weight (CRITICAL)
   - Current PEP: 0.70 weight (HIGH)
   - Former PEP: 0.40 weight (MEDIUM)
   - Companies House high flags: 0.50 weight
   - Companies House medium flags: 0.30 weight
   - Companies House low flags: 0.10 weight
   - Aggregates all flags across company + directors

4. **Risk Level Classification**
   - LOW (0.0-0.4): Standard CDD procedures sufficient
   - MEDIUM (0.4-0.7): Enhanced due diligence required
   - HIGH (0.7+): Senior management approval + EDD required

5. **Detailed Flag Analysis**
   - Categorizes by severity (critical/high/medium/low)
   - Identifies all sanctioned directors
   - Identifies all PEP directors (current and former)
   - Counts total flags from all sources
   - Lists individual risk factors

6. **Human-Readable Reporting**
   - Overall risk assessment summary
   - CDD procedure recommendations
   - Director-level breakdown
   - Actionable next steps

7. **Real-World Testing**
   - Tested with Tesco PLC (11 directors)
   - Successfully screens all directors for sanctions/PEP
   - Correctly calculates aggregate risk (LOW for clean entity)
   - Generates comprehensive summary output

## 📈 Next Steps (Upcoming Phases)

### Phase 3: Adverse Media Search (Optional)
- [ ] Lambda 3: Media checker
- [ ] NewsAPI integration
- [ ] Google search integration
- [ ] Sentiment analysis
- [ ] Risk weight: 0.6 for adverse findings

### Phase 5: Report Generation ✅ **COMPLETE AND DEPLOYED**
- [x] Lambda 5: Report generator  
- [x] Amazon Bedrock/Claude integration
- [x] Professional UK accountant report templates
- [x] MLR 2017 compliance documentation
- [x] Markdown report generation
- [x] S3 storage with metadata
- [x] Lambda Function URL with extended timeout support
- [x] Frontend integration with "Generate AI Report" button
- [x] Download report functionality
- [ ] PDF generation (future enhancement)
- [ ] Email delivery (future enhancement)

**Status**: ✅ **Fully deployed and operational**. Generating professional CDD reports in 30-40 seconds using Claude 3.7 Sonnet.

### Phase 6: Orchestration
- [ ] AWS Step Functions workflow
- [ ] Parallel execution
- [ ] Error handling
- [ ] Retry logic

### Phase 7: API Gateway (Optional - Currently using Lambda Function URLs)
- [ ] REST API endpoints
- [ ] Authentication
- [ ] Rate limiting
- [ ] API documentation

### Phase 8: Web Frontend ✅ **COMPLETE**
- [x] S3 static website hosting
- [x] Interactive web UI
- [x] Real-time progress tracking
- [x] Comprehensive results dashboard
- [x] Lambda Function URL integration

### Phase 9: Enhanced Frontend Features (Future)
- [ ] User authentication (Cognito)
- [ ] Saved screening history
- [ ] Export to PDF
- [ ] Bulk screening upload
- [ ] Dashboard analytics

## 🐛 Troubleshooting

### Lambda Deployment Fails

```bash
# Check AWS credentials
aws sts get-caller-identity

# Check Python version
python3 --version  # Should be 3.12+

# Manually test deployment
cd /home/josian/git/money-laundering-detect
./infrastructure/deploy-single-lambda.sh companies-house-checker
```

### Lambda Execution Fails

```bash
# Check Companies House Checker logs
aws logs tail /aws/lambda/aml-companies-house-checker-dev

# Check Sanctions Checker logs
aws logs tail /aws/lambda/aml-sanctions-checker-dev

# Check Risk Aggregator logs
aws logs tail /aws/lambda/aml-risk-aggregator-dev

# Test Secrets Manager access
aws secretsmanager get-secret-value \
  --secret-id taxguard/companies-house/api-key

aws secretsmanager get-secret-value \
  --secret-id taxguard/opensanctions/api-key

# Verify IAM role permissions (Lambda invoke permission required)
aws iam get-role-policy \
  --role-name aml-lambda-execution-role-dev \
  --policy-name AMLResourceAccess
```

### Companies House API Issues

```bash
# Test API key locally
python test_companies_house.py

# Check API status
curl -u "YOUR_API_KEY:" \
  "https://api.company-information.service.gov.uk/company/00445790"
```

### OpenSanctions API Issues

```bash
# Test API key locally
python test_sanctions.py

# Check API status with your key
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "https://api.opensanctions.org/search/default?q=Putin"

# Verify API key in Secrets Manager
aws secretsmanager get-secret-value \
  --secret-id taxguard/opensanctions/api-key \
  --query SecretString \
  --output text
```

### Report Generator Timeout Issues

```bash
# Check Lambda timeout setting (should be 300 seconds)
aws lambda get-function-configuration \
  --function-name aml-report-generator-dev \
  --query 'Timeout'

# Check if Bedrock model access is enabled
aws bedrock list-foundation-models \
  --region eu-west-2 \
  --query 'modelSummaries[?contains(modelId, `claude-3-7-sonnet`)]'

# Test report generation directly
aws lambda invoke \
  --function-name aml-report-generator-dev \
  --payload '{"entity_id":"test_456"}' \
  --cli-read-timeout 120 \
  response.json

# Check for Bedrock permissions
aws iam get-role-policy \
  --role-name aml-lambda-execution-role-dev \
  --policy-name AMLResourceAccess | grep bedrock
```

**Frontend Timeout Issues**:
- The frontend now has a 90-second timeout to handle long report generation
- Progress indicators show Claude is working (updates every 6 seconds)
- If you still see timeouts, check CloudWatch logs for the actual error
- Lambda Function URLs have a hard 30-second limit - extended timeout helps but may still timeout for very complex reports

## 📖 Documentation

- **Full Implementation Guide**: See `aml_cdd_implementation_guide.md`
- **AWS Lambda Powertools**: https://docs.powertools.aws.dev/lambda/python/
- **Companies House API**: https://developer.company-information.service.gov.uk/
- **OpenSanctions API**: https://www.opensanctions.org/docs/api/
- **MLR 2017 Compliance**: See implementation guide

## 🤝 Contributing

1. Create feature branch
2. Make changes
3. Test locally
4. Deploy to dev environment
5. Test in AWS
6. Create pull request

## 📝 License

[Your License Here]

## ✅ Compliance

This system is designed to assist with UK Money Laundering Regulations 2017 (MLR 2017) compliance:
- ✅ Customer identification
- ✅ Risk assessment
- ✅ Record keeping
- ✅ Audit trail
- ⚠️ **Note**: Human review still required for final decisions

## 🏆 Key Achievements

### Proof of Concept Complete ✅
- ✅ **Interactive Web UI** - Beautiful, modern interface for non-technical users
- ✅ **AI-Powered Reports** - Professional CDD reports via Claude 3.7 Sonnet
- ✅ End-to-end automated CDD workflow operational
- ✅ Successfully tested with real UK companies (Tesco PLC - 11 directors screened)
- ✅ Integration with 14+ international sanctions lists
- ✅ Automated director screening via Lambda-to-Lambda invocation
- ✅ Weighted risk scoring algorithm with actionable recommendations
- ✅ Full data persistence and audit trail (DynamoDB + S3)
- ✅ Real-time progress tracking with detailed information display
- ✅ Public web interface accessible from any browser
- ✅ Report generation in 30-40 seconds with progress indicators
- ✅ Download reports as Markdown files

### Frontend Excellence
- ✅ **Zero Framework** - Pure HTML/CSS/JavaScript (fast, no dependencies)
- ✅ **Detailed Progress** - Shows every step of the screening process
- ✅ **Real-time Updates** - Users see exactly what work is being done:
  - Company information as it's retrieved
  - Director names as they're extracted
  - Compliance flags as they're discovered
  - Sanctions/PEP matches in real-time
  - Risk calculation breakdown
- ✅ **Professional Design** - Modern gradient UI with smooth animations
- ✅ **Comprehensive Results** - Multi-card dashboard with statistics
- ✅ **Mobile Responsive** - Works on desktop, tablet, and mobile
- ✅ **One-Command Deployment** - `echo "2" | bash deploy.sh` to S3

### Technical Solutions Implemented
- ✅ **DynamoDB Decimal Handling**: Fixed Python float/Decimal compatibility issue
- ✅ **Lambda IAM Permissions**: Configured cross-Lambda invocation permissions
- ✅ **Lambda Function URLs**: Direct browser-to-Lambda communication (no API Gateway needed)
- ✅ **CORS Configuration**: Enabled cross-origin requests for web frontend
- ✅ **CloudFormation IaC**: Complete infrastructure as code deployment
- ✅ **API Integration**: Companies House (free) + OpenSanctions (commercial)
- ✅ **Serverless Architecture**: Fully serverless, pay-per-use pricing model

### Production Ready Features
- ✅ CloudWatch logging and monitoring
- ✅ AWS X-Ray distributed tracing
- ✅ Secrets Manager for API key security
- ✅ Error handling and retry logic
- ✅ Structured logging with Lambda Powertools
- ✅ S3 static website hosting with public access
- ✅ User-friendly error messages in frontend

## 📞 Support

For issues or questions:
1. Check this README
2. Review implementation guide
3. Check AWS CloudWatch logs
4. Review Companies House API docs
5. Consult compliance professional for AML interpretation

---

**Built with ❤️ for UK accountants to automate AML compliance**

**Last Updated**: October 21, 2025  
**Status**: ✅ Proof of Concept Fully Operational - Phases 1, 2, 4, 5, and 8 Complete  
**Live Demo**: http://aml-frontend-864899848062-eu-west-2.s3-website.eu-west-2.amazonaws.com  
**AI Reports**: Powered by Claude 3.7 Sonnet via Amazon Bedrock 🤖

````
