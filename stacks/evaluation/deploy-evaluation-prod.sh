#!/bin/bash
set -e

# =========================================================================
# Production Evaluation Stack Deployment Script
# =========================================================================
# Deploys evaluation infrastructure for production IDP stack
# Uses EU-based models for GDPR compliance in production
# =========================================================================

# Configuration
ENVIRONMENT="prod"
PRODUCTION_STACK="fiscalshield-idp-prod"
EVAL_STACK="${PRODUCTION_STACK}-evaluation"
PROD_REGION="eu-central-1"
EVAL_REGION="eu-central-1"  # EU models for production compliance

# Model configuration
# Production: Use EU-based models for GDPR compliance
EVALUATION_MODEL="eu.anthropic.claude-3-7-sonnet-20250219-v1:0"

# Sampling configuration
SAMPLING_RATE=10
LOW_CONFIDENCE_THRESHOLD=0.7
MEDIUM_SAMPLING_RATE=20
HIGH_SAMPLING_RATE=5

# Batch inference configuration
# Note: Bedrock batch inference requires minimum batch size
# Recommended: 100+ documents for cost-effectiveness
BATCH_INFERENCE_ENABLED="true"
BATCH_MIN_SIZE=100  # Minimum documents to use batch mode

# Schedule (daily at 3 AM UTC)
EVALUATION_SCHEDULE="cron(0 3 * * ? *)"

LOG_LEVEL="INFO"

echo "========================================"
echo "IDP Evaluation Stack Deployment - PROD"
echo "========================================"
echo ""
echo "Environment: $ENVIRONMENT"
echo "Production Stack: $PRODUCTION_STACK"
echo "Evaluation Stack: $EVAL_STACK"
echo "Production Region: $PROD_REGION"
echo "Evaluation Region: $EVAL_REGION"
echo "Evaluation Model: $EVALUATION_MODEL"
echo "Inference Mode: $([ "$BATCH_INFERENCE_ENABLED" = "true" ] && echo "batch (requires $BATCH_MIN_SIZE+ docs)" || echo "direct")"
echo ""

# Check production stack exists
echo "Checking if production stack exists..."
if ! aws cloudformation describe-stacks \
    --stack-name "$PRODUCTION_STACK" \
    --region "$PROD_REGION" \
    --query 'Stacks[0].StackStatus' \
    --output text &>/dev/null; then
    echo "❌ Error: Production stack '$PRODUCTION_STACK' not found in $PROD_REGION"
    exit 1
fi
echo "✓ Production stack found"

# Verify ExtractionResultsTable exists
echo "Verifying ExtractionResultsTable..."
EXTRACTION_TABLE=$(aws dynamodb list-tables \
    --region "$PROD_REGION" \
    --query "TableNames[?starts_with(@, '${PRODUCTION_STACK}-ExtractionResultsTable')]" \
    --output text | head -n1)

if [ -z "$EXTRACTION_TABLE" ]; then
    echo "❌ Error: ExtractionResultsTable not found for stack $PRODUCTION_STACK"
    exit 1
fi
echo "✓ Found table: $EXTRACTION_TABLE"

if [ "$BATCH_INFERENCE_ENABLED" = "true" ]; then
    echo "Using batch inference (50% discount, 6-24hr delay, requires ${BATCH_MIN_SIZE}+ documents)"
else
    echo "Using direct inference (immediate results, full cost)"
fi
echo ""

# Build
echo "Building evaluation stack..."
sam build --parallel --cached

if [ $? -ne 0 ]; then
    echo "❌ Build failed"
    exit 1
fi
echo "✓ Build successful"
echo ""

# Deploy
echo "Deploying evaluation stack..."
sam deploy \
    --stack-name "$EVAL_STACK" \
    --region "$PROD_REGION" \
    --capabilities CAPABILITY_NAMED_IAM \
    --no-confirm-changeset \
    --no-fail-on-empty-changeset \
    --parameter-overrides \
        StackName="$PRODUCTION_STACK" \
        EvaluationRegion="$EVAL_REGION" \
        EvaluationModelId="$EVALUATION_MODEL" \
        SamplingRate="$SAMPLING_RATE" \
        LowConfidenceThreshold="$LOW_CONFIDENCE_THRESHOLD" \
        MediumConfidenceSamplingRate="$MEDIUM_SAMPLING_RATE" \
        HighConfidenceSamplingRate="$HIGH_SAMPLING_RATE" \
        BatchInferenceEnabled="$BATCH_INFERENCE_ENABLED" \
        EvaluationSchedule="$EVALUATION_SCHEDULE" \
        LogLevel="$LOG_LEVEL"

if [ $? -ne 0 ]; then
    echo "❌ Deployment failed"
    exit 1
fi

echo ""
echo "========================================"
echo "✅ Deployment Complete - PRODUCTION"
echo "========================================"
echo ""
echo "Stack: $EVAL_STACK"
echo "Region: $PROD_REGION"
echo "Evaluation Model: $EVALUATION_MODEL (EU-based for GDPR)"
echo ""

# Get outputs
STATE_MACHINE_ARN=$(aws cloudformation describe-stacks \
    --stack-name "$EVAL_STACK" \
    --region "$PROD_REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`EvaluationStateMachineArn`].OutputValue' \
    --output text 2>/dev/null)

if [ -n "$STATE_MACHINE_ARN" ]; then
    echo "State Machine ARN:"
    echo "  $STATE_MACHINE_ARN"
    echo ""
    echo "Manual execution:"
    echo "  aws stepfunctions start-execution \\"
    echo "    --state-machine-arn $STATE_MACHINE_ARN \\"
    echo "    --region $PROD_REGION"
fi

echo ""
echo "⚠️  Production Notes:"
echo "  - Uses EU models for GDPR compliance"
echo "  - Batch inference requires $BATCH_MIN_SIZE+ documents"
echo "  - Schedule: Daily at 3 AM UTC"
echo "  - Monitor costs via CloudWatch/Cost Explorer"
echo ""
