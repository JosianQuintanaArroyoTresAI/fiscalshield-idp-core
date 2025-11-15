#!/bin/bash

# Deploy Analysis Stack to Dev Environment
# Simple deployment script for fiscalshield-analysis stack

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=================================================="
echo "  FiscalShield Analysis Stack - Dev Deployment"
echo "=================================================="
echo ""

# Configuration
ENVIRONMENT="dev"
STACK_NAME="fiscalshield-analysis-dev"
REGION="eu-central-1"

echo "Environment: $ENVIRONMENT"
echo "Stack Name: $STACK_NAME"
echo "Region: $REGION"
echo ""

# Step 1: Build
echo "📦 Building Lambda functions..."
sam build

if [ $? -ne 0 ]; then
    echo "❌ Build failed!"
    exit 1
fi

echo "✅ Build successful"
echo ""

# Step 2: Deploy
echo "🚀 Deploying stack to AWS..."
sam deploy \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --parameter-overrides \
    Environment="$ENVIRONMENT" \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --no-confirm-changeset \
  --resolve-s3

if [ $? -ne 0 ]; then
    echo "❌ Deployment failed!"
    exit 1
fi

echo "✅ Deployment successful"
echo ""

# Step 3: Get outputs
echo "📊 Stack Outputs:"
echo "---"

API_URL=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiGatewayUrl`].OutputValue' \
  --output text 2>/dev/null || echo "Not available")

SSM_PARAM=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiUrlParameterName`].OutputValue' \
  --output text 2>/dev/null || echo "Not available")

STATE_MACHINE_ARN=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --query 'Stacks[0].Outputs[?OutputKey==`TransactionCategorizationStateMachineArn`].OutputValue' \
  --output text 2>/dev/null || echo "Not available")

echo "API Gateway URL: $API_URL"
echo "SSM Parameter: $SSM_PARAM"
echo "State Machine ARN: $STATE_MACHINE_ARN"
echo ""

# Step 4: Test health endpoint
if [ "$API_URL" != "Not available" ]; then
    echo "🏥 Testing health endpoint..."
    HEALTH_RESPONSE=$(curl -s "$API_URL/health" || echo "Failed to connect")
    
    if echo "$HEALTH_RESPONSE" | grep -q "available"; then
        echo "✅ Health check passed"
        echo "$HEALTH_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$HEALTH_RESPONSE"
    else
        echo "⚠️  Health check failed or pending"
        echo "$HEALTH_RESPONSE"
    fi
else
    echo "⚠️  Could not retrieve API URL, skipping health check"
fi

echo ""
echo "=================================================="
echo "  Deployment Complete!"
echo "=================================================="
echo ""
echo "📝 Next Steps:"
echo "  1. Test company intelligence endpoint:"
echo "     curl $API_URL/company/12345678/intelligence"
echo ""
echo "  2. Test transaction categorization workflow:"
echo "     aws stepfunctions start-execution \\"
echo "       --state-machine-arn $STATE_MACHINE_ARN \\"
echo "       --input '{\"companyNumber\":\"12345678\",\"userId\":\"test-user\"}'"
echo ""
echo "  3. Check Step Functions execution:"
echo "     aws stepfunctions list-executions --state-machine-arn $STATE_MACHINE_ARN"
echo ""
echo "  4. Check logs:"
echo "     aws logs tail /aws/lambda/fiscalshield-analysis-dev-TriggerAnalysis --follow"
echo "     aws logs tail /aws/lambda/fiscalshield-analysis-dev-Categorization --follow"
echo ""
echo "  5. Verify SSM parameter:"
echo "     aws ssm get-parameter --name $SSM_PARAM --region $REGION"
echo ""
