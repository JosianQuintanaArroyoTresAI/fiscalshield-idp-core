#!/bin/bash
################################################################################
# Copy AML Secrets from eu-west-2 to eu-central-1
#
# This script copies the OpenSanctions and NewsAPI secrets from the eu-west-2
# region (where they currently exist) to eu-central-1 (where the data collection
# stack is deployed).
#
# Usage: ./copy-aml-secrets.sh [environment]
#
# Environment: dev (default), staging, prod
################################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT="${1:-dev}"
SOURCE_REGION="eu-west-2"
TARGET_REGION="eu-central-1"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}AML Secrets Migration${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "Environment: ${GREEN}${ENVIRONMENT}${NC}"
echo -e "Source Region: ${GREEN}${SOURCE_REGION}${NC}"
echo -e "Target Region: ${GREEN}${TARGET_REGION}${NC}"
echo ""

# Validate AWS CLI
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI not found. Please install it first.${NC}"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ AWS credentials not configured or invalid.${NC}"
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "AWS Account: ${GREEN}${ACCOUNT_ID}${NC}"
echo ""

################################################################################
# Function: Copy Secret
################################################################################
copy_secret() {
    local SOURCE_NAME=$1
    local TARGET_NAME=$2
    local DESCRIPTION=$3
    
    echo -e "${YELLOW}Copying: ${SOURCE_NAME} → ${TARGET_NAME}${NC}"
    
    # Fetch secret from source region
    echo "  📥 Fetching from ${SOURCE_REGION}..."
    SECRET_VALUE=$(aws secretsmanager get-secret-value \
        --secret-id "${SOURCE_NAME}" \
        --region "${SOURCE_REGION}" \
        --query SecretString \
        --output text 2>/dev/null)
    
    if [ -z "$SECRET_VALUE" ]; then
        echo -e "  ${RED}❌ Failed to fetch secret from ${SOURCE_REGION}${NC}"
        return 1
    fi
    
    # Check if target secret already exists
    if aws secretsmanager describe-secret \
        --secret-id "${TARGET_NAME}" \
        --region "${TARGET_REGION}" &> /dev/null; then
        
        echo "  ♻️  Secret exists in ${TARGET_REGION}, updating..."
        aws secretsmanager update-secret \
            --secret-id "${TARGET_NAME}" \
            --secret-string "${SECRET_VALUE}" \
            --region "${TARGET_REGION}" \
            --description "${DESCRIPTION}" > /dev/null
        
        echo -e "  ${GREEN}✅ Secret updated in ${TARGET_REGION}${NC}"
    else
        echo "  📤 Creating secret in ${TARGET_REGION}..."
        aws secretsmanager create-secret \
            --name "${TARGET_NAME}" \
            --secret-string "${SECRET_VALUE}" \
            --region "${TARGET_REGION}" \
            --description "${DESCRIPTION}" \
            --tags Key=Environment,Value=${ENVIRONMENT} Key=Stack,Value=fiscalshield-dc Key=CopiedFrom,Value=${SOURCE_REGION} > /dev/null
        
        echo -e "  ${GREEN}✅ Secret created in ${TARGET_REGION}${NC}"
    fi
    
    echo ""
}

################################################################################
# Copy OpenSanctions Secret
################################################################################
echo -e "${BLUE}Step 1: OpenSanctions API${NC}"
copy_secret \
    "taxguard/opensanctions/api-key" \
    "fiscalshield-dc-${ENVIRONMENT}-OpenSanctionsAPI" \
    "OpenSanctions API key for sanctions and PEP screening (copied from ${SOURCE_REGION})"

################################################################################
# Copy NewsAPI Secret
################################################################################
echo -e "${BLUE}Step 2: NewsAPI${NC}"
copy_secret \
    "taxguard/newsapi/api-key" \
    "fiscalshield-dc-${ENVIRONMENT}-NewsAPI" \
    "NewsAPI key for adverse media screening (copied from ${SOURCE_REGION})"

################################################################################
# Verification
################################################################################
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Verification${NC}"
echo -e "${BLUE}========================================${NC}"

echo -e "${YELLOW}Checking secrets in ${TARGET_REGION}...${NC}"

# Verify OpenSanctions
if aws secretsmanager describe-secret \
    --secret-id "fiscalshield-dc-${ENVIRONMENT}-OpenSanctionsAPI" \
    --region "${TARGET_REGION}" &> /dev/null; then
    echo -e "${GREEN}✅ OpenSanctions secret exists${NC}"
else
    echo -e "${RED}❌ OpenSanctions secret NOT found${NC}"
fi

# Verify NewsAPI
if aws secretsmanager describe-secret \
    --secret-id "fiscalshield-dc-${ENVIRONMENT}-NewsAPI" \
    --region "${TARGET_REGION}" &> /dev/null; then
    echo -e "${GREEN}✅ NewsAPI secret exists${NC}"
else
    echo -e "${RED}❌ NewsAPI secret NOT found${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Secret migration complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Deploy the updated CloudFormation stack:"
echo "   cd stacks/data-collection && ./deploy-dc-dev.sh"
echo ""
echo "2. The new secrets are now available to Lambda functions via:"
echo "   - fiscalshield-dc-${ENVIRONMENT}-OpenSanctionsAPI"
echo "   - fiscalshield-dc-${ENVIRONMENT}-NewsAPI"
echo ""
