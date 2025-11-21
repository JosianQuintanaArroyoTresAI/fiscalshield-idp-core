# CI/CD Deployment Guide

## Stack Deployment Order

Analysis Stack **must** deploy before Core Stack to populate SSM parameters.

## Deployment Options

### Option 1: Automatic (Recommended)
Push to `dev` branch and manually trigger the ordered workflow:

```bash
git push origin dev
```

Then go to GitHub Actions → **Deploy All Stacks - Dev (Ordered)** → Run workflow

This ensures:
1. Analysis Stack deploys first → writes SSM parameters
2. Core Stack deploys second → reads SSM parameters automatically

### Option 2: Independent Stack Deployments
The existing workflows still work independently:

**Analysis Stack only:**
- Push changes to `stacks/analysis/**` → triggers `deploy-analysis-dev.yml`

**Core Stack only:**  
- Push changes to other paths → triggers `deploy-dev.yml`
- Core Stack will read existing SSM parameters (if Analysis Stack was previously deployed)

### Option 3: Manual Deployment
Deploy stacks manually in order:

```bash
# 1. Deploy Analysis Stack
cd stacks/analysis
sam build && sam deploy --config-env dev

# 2. Deploy Core Stack (auto-reads SSM)
cd ../..
python3 publish.py fiscalshield-dev idp eu-central-1
aws cloudformation update-stack ...
```

## Lambda Function Names

### Analysis Stack Lambdas

**Transaction Analysis:**
- `fiscalshield-analysis-dev-TriggerAnalysis` - Queries pending transactions
- `fiscalshield-analysis-dev-TransactionCategorization` - ✨ Renamed from "Categorization"

**Invoice Analysis:**
- `fiscalshield-analysis-dev-TriggerInvoiceAnalysis` - Queries pending invoices  
- `fiscalshield-analysis-dev-InvoiceCategorization` - Analyzes tax deductibility

**Other:**
- `fiscalshield-analysis-dev-AssessCompany` - Company intelligence
- `fiscalshield-analysis-dev-GenerateReport` - AML reports
- `fiscalshield-analysis-dev-HealthCheck` - API health

### Core Stack Lambdas

**Transaction Analysis Trigger:**
- `fiscalshield-idp-dev-TriggerTransactionAnalysis` - AppSync resolver

**Invoice Analysis Trigger:**
- `fiscalshield-idp-dev-TriggerInvoiceAnalysis` - AppSync resolver

## SSM Parameter Paths

Analysis Stack writes:
- `/fiscalshield/analysis/dev/transaction-categorization-state-machine-arn`
- `/fiscalshield/analysis/dev/invoice-analysis-state-machine-arn`

Core Stack reads these automatically via `{{resolve:ssm-safe:...}}` syntax.

## Breaking Changes

⚠️ **Lambda Rename**: `fiscalshield-analysis-dev-Categorization` → `fiscalshield-analysis-dev-TransactionCategorization`

After deploying, the old Lambda will be deleted and replaced. This is a **zero-downtime change** as CloudFormation handles the replacement automatically.
