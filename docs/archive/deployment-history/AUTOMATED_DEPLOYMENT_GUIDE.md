# Automated Cross-Stack Deployment Guide

## Overview

The Analysis Stack and Core Stack are integrated via **SSM Parameter Store**, eliminating manual ARN copying between deployments.

## How It Works

### Analysis Stack → SSM Parameter Store

When the Analysis Stack deploys, it automatically writes state machine ARNs to SSM:

```
/fiscalshield/analysis/dev/transaction-categorization-state-machine-arn
/fiscalshield/analysis/dev/invoice-analysis-state-machine-arn
```

### Core Stack ← SSM Parameter Store

The Core Stack parameters use **dynamic SSM resolution** with `{{resolve:ssm-safe:...}}`:

- If the SSM parameter exists → automatically uses the ARN
- If the SSM parameter doesn't exist → defaults to empty string (feature disabled)
- Can be manually overridden at deployment time if needed

## Deployment Sequence

### First Time Setup

```bash
# 1. Deploy Analysis Stack
cd stacks/analysis
sam build && sam deploy

# 2. Deploy Core Stack (automatically picks up ARNs from SSM)
cd ../..
sam build && sam deploy
```

**That's it!** No manual copying required.

### Subsequent Deployments

```bash
# Update either stack independently
sam build && sam deploy
```

The integration is maintained automatically via SSM Parameter Store.

## Environment-Specific Deployments

For non-dev environments, update the SSM path in Core Stack parameters:

```yaml
# template.yaml
Parameters:
  TransactionCategorizationStateMachineArn:
    Default: '{{resolve:ssm-safe:/fiscalshield/analysis/prod/transaction-categorization-state-machine-arn}}'
```

Or override at deployment:

```bash
sam deploy --parameter-overrides Environment=prod
```

## Manual Override (Optional)

If you need to manually specify ARNs:

```bash
sam deploy --parameter-overrides \
  TransactionCategorizationStateMachineArn=arn:aws:states:REGION:ACCOUNT:stateMachine:NAME \
  InvoiceAnalysisStateMachineArn=arn:aws:states:REGION:ACCOUNT:stateMachine:NAME
```

## Verification

Check SSM Parameter Store values:

```bash
# View transaction categorization ARN
aws ssm get-parameter \
  --name /fiscalshield/analysis/dev/transaction-categorization-state-machine-arn \
  --query 'Parameter.Value' --output text

# View invoice analysis ARN
aws ssm get-parameter \
  --name /fiscalshield/analysis/dev/invoice-analysis-state-machine-arn \
  --query 'Parameter.Value' --output text
```

## Benefits

✅ **Zero manual copying** - ARNs flow automatically via SSM  
✅ **Environment-aware** - Different environments use different SSM paths  
✅ **Fail-safe** - Missing parameters default to empty (disables feature)  
✅ **Override-friendly** - Can manually specify ARNs when needed  
✅ **Convention-based** - Predictable SSM parameter naming

## SSM Parameter Naming Convention

```
/fiscalshield/analysis/${Environment}/${feature}-state-machine-arn
```

Examples:
- `/fiscalshield/analysis/dev/transaction-categorization-state-machine-arn`
- `/fiscalshield/analysis/dev/invoice-analysis-state-machine-arn`
- `/fiscalshield/analysis/prod/transaction-categorization-state-machine-arn`
- `/fiscalshield/analysis/prod/invoice-analysis-state-machine-arn`
