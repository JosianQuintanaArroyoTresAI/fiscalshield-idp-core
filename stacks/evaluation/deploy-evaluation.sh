#!/bin/bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# Evaluation Stack Deployment Script
# Usage: ./deploy-evaluation.sh [dev|prod] [--batch|--direct]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ENVIRONMENT=${1:-dev}
INFERENCE_MODE=${2:-batch}

# Configuration
STACK_NAME="fiscalshield-idp-${ENVIRONMENT}"
EVALUATION_STACK_NAME="${STACK_NAME}-evaluation"
REGION="eu-central-1"  # Your production region
EVALUATION_REGION="us-east-1"  # Region with best models

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}IDP Evaluation Stack Deployment${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Environment: ${ENVIRONMENT}"
echo "Production Stack: ${STACK_NAME}"
echo "Evaluation Stack: ${EVALUATION_STACK_NAME}"
echo "Production Region: ${REGION}"
echo "Evaluation Region: ${EVALUATION_REGION}"
echo "Inference Mode: ${INFERENCE_MODE}"
echo ""

# Check if production stack exists
echo -e "${YELLOW}Checking if production stack exists...${NC}"
if ! aws cloudformation describe-stacks \
    --stack-name "${STACK_NAME}" \
    --region "${REGION}" \
    --query "Stacks[0].StackStatus" \
    --output text > /dev/null 2>&1; then
    echo -e "${RED}Error: Production stack '${STACK_NAME}' not found in ${REGION}${NC}"
    echo "Please deploy the main IDP stack first."
    exit 1
fi
echo -e "${GREEN}✓ Production stack found${NC}"

# Verify ExtractionResultsTable exists
echo -e "${YELLOW}Verifying ExtractionResultsTable...${NC}"
TABLE_NAME=$(aws dynamodb list-tables \
    --region "${REGION}" \
    --query "TableNames[?contains(@, '${STACK_NAME}-ExtractionResultsTable')]" \
    --output text)

if [ -z "$TABLE_NAME" ]; then
    echo -e "${RED}Error: ExtractionResultsTable not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Found table: ${TABLE_NAME}${NC}"

# Set parameters based on inference mode
if [ "$INFERENCE_MODE" = "--direct" ]; then
    BATCH_ENABLED="false"
    echo -e "${YELLOW}Using direct inference (faster, higher cost)${NC}"
else
    BATCH_ENABLED="true"
    echo -e "${YELLOW}Using batch inference (50% discount, 6-24hr delay)${NC}"
fi

# Build the stack
echo ""
echo -e "${YELLOW}Building evaluation stack...${NC}"
cd "$(dirname "$0")"
sam build --template template.yaml

if [ $? -ne 0 ]; then
    echo -e "${RED}Build failed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Build successful${NC}"

# Deploy the stack
echo ""
echo -e "${YELLOW}Deploying evaluation stack...${NC}"
sam deploy \
    --template-file .aws-sam/build/template.yaml \
    --stack-name "${EVALUATION_STACK_NAME}" \
    --region "${REGION}" \
    --parameter-overrides \
        StackName="${STACK_NAME}" \
        EvaluationRegion="${EVALUATION_REGION}" \
        EvaluationModelId="us.anthropic.claude-sonnet-4-20250514-v1:0" \
        SamplingRate=10 \
        LowConfidenceThreshold=0.7 \
        MediumConfidenceSamplingRate=20 \
        HighConfidenceSamplingRate=5 \
        BatchInferenceEnabled="${BATCH_ENABLED}" \
        EvaluationSchedule="'cron(0 2 * * ? *)'" \
        LogLevel=INFO \
    --capabilities CAPABILITY_NAMED_IAM \
    --resolve-s3 \
    --no-fail-on-empty-changeset

if [ $? -ne 0 ]; then
    echo -e "${RED}Deployment failed${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Successful!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Get stack outputs
echo "Retrieving stack outputs..."
STATE_MACHINE_ARN=$(aws cloudformation describe-stacks \
    --stack-name "${EVALUATION_STACK_NAME}" \
    --region "${REGION}" \
    --query "Stacks[0].Outputs[?OutputKey=='EvaluationStateMachineArn'].OutputValue" \
    --output text)

METRICS_TABLE=$(aws cloudformation describe-stacks \
    --stack-name "${EVALUATION_STACK_NAME}" \
    --region "${REGION}" \
    --query "Stacks[0].Outputs[?OutputKey=='EvaluationMetricsTableName'].OutputValue" \
    --output text)

BUCKET_NAME=$(aws cloudformation describe-stacks \
    --stack-name "${EVALUATION_STACK_NAME}" \
    --region "${REGION}" \
    --query "Stacks[0].Outputs[?OutputKey=='EvaluationDataBucketName'].OutputValue" \
    --output text)

echo ""
echo "Stack Outputs:"
echo "  State Machine ARN: ${STATE_MACHINE_ARN}"
echo "  Metrics Table: ${METRICS_TABLE}"
echo "  Data Bucket: ${BUCKET_NAME}"
echo ""

# Test execution
echo -e "${YELLOW}Would you like to trigger a test evaluation run? (y/n)${NC}"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo "Starting test evaluation..."
    
    EXECUTION_ARN=$(aws stepfunctions start-execution \
        --state-machine-arn "${STATE_MACHINE_ARN}" \
        --input '{"evaluationType": "manual", "lookbackDays": 1}' \
        --region "${REGION}" \
        --query "executionArn" \
        --output text)
    
    echo ""
    echo -e "${GREEN}Evaluation execution started!${NC}"
    echo "Execution ARN: ${EXECUTION_ARN}"
    echo ""
    echo "Monitor progress at:"
    echo "https://console.aws.amazon.com/states/home?region=${REGION}#/executions/details/${EXECUTION_ARN}"
    echo ""
    
    if [ "$BATCH_ENABLED" = "true" ]; then
        echo -e "${YELLOW}Note: Batch inference takes 6-24 hours to complete${NC}"
    else
        echo -e "${YELLOW}Direct inference should complete within 30-60 minutes${NC}"
    fi
fi

echo ""
echo -e "${GREEN}Next Steps:${NC}"
echo "1. Monitor the Step Functions execution in the AWS Console"
echo "2. Query metrics from DynamoDB table: ${METRICS_TABLE}"
echo "3. Review evaluation results in S3: ${BUCKET_NAME}"
echo "4. Adjust sampling rates or models as needed"
echo ""
echo -e "${GREEN}Deployment complete!${NC}"
