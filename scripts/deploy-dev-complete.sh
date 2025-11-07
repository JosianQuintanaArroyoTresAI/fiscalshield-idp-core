#!/bin/bash
# Complete Dev Deployment - Publish + Deploy + Force Lambda Updates
# This is the ONE script you should run for dev deployments

set -euo pipefail

NON_INTERACTIVE=${NON_INTERACTIVE:-false}
SKIP_FORCE_UPDATE=${SKIP_FORCE_UPDATE:-false}

if [ "${CI:-false}" = "true" ]; then
  NON_INTERACTIVE=true
fi

print_usage() {
  cat <<"USAGE"
Usage: ./scripts/deploy-dev-complete.sh [options]

Options:
  --non-interactive, -y   Skip interactive prompts/countdown (default when CI=true)
  --skip-force-update     Skip Lambda force-update step
  --help, -h              Show this help message

Environment overrides (forwarded to child scripts):
  STACK_NAME, REGION, ADMIN_EMAIL
  BUCKET_BASENAME, S3_BUCKET, ARTIFACT_PREFIX
  PUBLISH_PREFIX, PUBLISH_REGION, PUBLISH_VENV_PATH, PUBLISH_EXTRA_ARGS
  SKIP_FORCE_UPDATE, NON_INTERACTIVE
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --non-interactive|-y)
      NON_INTERACTIVE=true
      ;;
    --skip-force-update)
      SKIP_FORCE_UPDATE=true
      ;;
    --help|-h)
      print_usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      print_usage
      exit 1
      ;;
  esac
  shift
done

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

if [ ! -t 1 ] || [ "${NO_COLOR:-}" != "" ] || [ "$NON_INTERACTIVE" = true ]; then
  RED=""
  GREEN=""
  YELLOW=""
  BLUE=""
  NC=""
fi

# Shared configuration that downstream scripts also consume
STACK_NAME="${STACK_NAME:-fiscalshield-idp-dev}"
REGION="${REGION:-eu-central-1}"
BUCKET_BASENAME="${BUCKET_BASENAME:-fiscalshield-templates}"
ARTIFACT_PREFIX="${ARTIFACT_PREFIX:-fiscalshield/dev}"
PUBLISH_PREFIX="${PUBLISH_PREFIX:-$ARTIFACT_PREFIX}"
PUBLISH_REGION="${PUBLISH_REGION:-$REGION}"
S3_BUCKET="${S3_BUCKET:-${BUCKET_BASENAME}-${REGION}}"
ADMIN_EMAIL="${ADMIN_EMAIL:-josian@protonmail.com}"

export STACK_NAME REGION BUCKET_BASENAME ARTIFACT_PREFIX PUBLISH_PREFIX PUBLISH_REGION S3_BUCKET ADMIN_EMAIL

if [ -f "VERSION" ]; then
  CURRENT_VERSION=$(tr -d '\r' < VERSION)
else
  CURRENT_VERSION="unknown"
fi

echo "======================================================================"
echo "FiscalShield IDP - Complete Dev Deployment"
echo "======================================================================"
echo ""
echo "This script will:"
echo "  1. Build and publish artifacts to S3"
echo "  2. Deploy/update CloudFormation stack"
if [ "$SKIP_FORCE_UPDATE" = true ]; then
  echo "  3. Force update Lambda functions (skipped via flag)"
else
  echo "  3. Force update Lambda functions (bypass CF caching)"
fi
echo ""
echo "Configuration:"
echo "  Stack Name    : ${STACK_NAME}"
echo "  Region        : ${REGION}"
echo "  Artifacts S3  : ${S3_BUCKET}/${ARTIFACT_PREFIX}/${CURRENT_VERSION}"
echo "  Admin Email   : ${ADMIN_EMAIL}"
echo ""
if [ "$NON_INTERACTIVE" = true ]; then
  echo -e "${YELLOW}Running in non-interactive mode (countdown disabled).${NC}"
else
  echo -e "${YELLOW}Press Ctrl+C within 5 seconds to cancel...${NC}"
  sleep 5
fi

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# ============================================================================
# STEP 1: BUILD & PUBLISH
# ============================================================================
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}STEP 1: Building and Publishing Artifacts${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [ -f "./scripts/publish-dev.sh" ]; then
  ./scripts/publish-dev.sh
else
    echo -e "${RED}ERROR: publish-dev.sh not found!${NC}"
    exit 1
fi

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Build/publish failed. Aborting deployment.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Build and publish completed successfully${NC}"

# ============================================================================
# STEP 2: DEPLOY CLOUDFORMATION STACK
# ============================================================================
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}STEP 2: Deploying CloudFormation Stack${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [ -f "./deploy-pattern2-dev.sh" ]; then
  ./deploy-pattern2-dev.sh
else
    echo -e "${RED}ERROR: deploy-pattern2-dev.sh not found!${NC}"
    exit 1
fi

DEPLOY_EXIT_CODE=$?

if [ $DEPLOY_EXIT_CODE -ne 0 ]; then
    echo -e "${YELLOW}⚠ CloudFormation deployment reported errors${NC}"
  if [ "$SKIP_FORCE_UPDATE" = true ]; then
    echo -e "${YELLOW}Force update step skipped; investigate deployment issues before retrying.${NC}"
  else
    echo -e "${YELLOW}Proceeding with Lambda force update anyway...${NC}"
  fi
fi

# ============================================================================
# STEP 3: FORCE UPDATE LAMBDAS
# ============================================================================
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}STEP 3: Force Updating Lambda Functions${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
if [ "$SKIP_FORCE_UPDATE" = true ]; then
  echo -e "${YELLOW}INFO: Force update disabled (SKIP_FORCE_UPDATE=true).${NC}"
else
  echo -e "${YELLOW}INFO: This step bypasses CloudFormation caching to ensure${NC}"
  echo -e "${YELLOW}      Lambda code is always refreshed with latest changes.${NC}"
fi
echo ""

# Wait for CloudFormation to complete
if [ $DEPLOY_EXIT_CODE -eq 0 ]; then
    echo "Waiting for CloudFormation stack to complete..."
    echo "This may take 15-20 minutes..."
    
    # Try update wait first, fall back to create wait
  aws cloudformation wait stack-update-complete --stack-name "$STACK_NAME" --region "$REGION" 2>/dev/null || \
  aws cloudformation wait stack-create-complete --stack-name "$STACK_NAME" --region "$REGION"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ CloudFormation stack completed successfully${NC}"
    else
        echo -e "${RED}✗ CloudFormation stack failed or timed out${NC}"
        echo -e "${YELLOW}You can check the status with:${NC}"
  echo "  aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION"
        exit 1
    fi
fi

if [ "$SKIP_FORCE_UPDATE" = true ]; then
  echo -e "${YELLOW}Skipping Lambda force update (SKIP_FORCE_UPDATE=true).${NC}"
else
  if [ -f "./scripts/force-update-lambdas.sh" ]; then
    ./scripts/force-update-lambdas.sh
  else
    echo -e "${RED}ERROR: force-update-lambdas.sh not found!${NC}"
    exit 1
  fi

  if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Lambda force update failed${NC}"
    exit 1
  fi
fi

# ============================================================================
# COMPLETION
# ============================================================================
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ Complete Dev Deployment Successful!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Deployment Summary:"
echo "  ✓ Artifacts built and published to S3"
echo "  ✓ CloudFormation stack deployed/updated"
if [ "$SKIP_FORCE_UPDATE" = true ]; then
  echo "  ⚙ Lambda force update skipped"
else
  echo "  ✓ Lambda functions force-updated with latest code"
fi
echo ""

# ============================================================================
# VERIFICATION: EU MODELS CHECK
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Verifying EU Model Configuration${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Get Configuration Table name from stack
CONFIG_TABLE=$(aws cloudformation list-stack-resources \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --query 'StackResourceSummaries[?LogicalResourceId==`ConfigurationTable`].PhysicalResourceId' \
  --output text 2>/dev/null)

if [ ! -z "$CONFIG_TABLE" ]; then
  echo "📥 Checking model configuration in DynamoDB..."
  
  # Get current configuration
  MODELS=$(aws dynamodb get-item \
    --table-name "$CONFIG_TABLE" \
    --key '{"Configuration": {"S": "Default"}}' \
    --region "$REGION" \
    --query 'Item.{classification: classification.M.model.S, extraction: extraction.M.model.S, summarization: summarization.M.model.S}' \
    --output json 2>/dev/null)
  
  if [ ! -z "$MODELS" ] && [ "$MODELS" != "null" ]; then
    # Parse and check models
    CLASSIFICATION=$(echo "$MODELS" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('classification', ''))" 2>/dev/null)
    EXTRACTION=$(echo "$MODELS" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('extraction', ''))" 2>/dev/null)
    SUMMARIZATION=$(echo "$MODELS" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('summarization', ''))" 2>/dev/null)
    
    ALL_EU=true
    if [[ ! $CLASSIFICATION == eu.* ]]; then ALL_EU=false; fi
    if [[ ! $EXTRACTION == eu.* ]]; then ALL_EU=false; fi
    if [[ ! $SUMMARIZATION == eu.* ]]; then ALL_EU=false; fi
    
    if [ "$ALL_EU" = true ]; then
      echo -e "${GREEN}✓ All models are EU-based:${NC}"
      echo "  - Classification: $CLASSIFICATION"
      echo "  - Extraction: $EXTRACTION"
      echo "  - Summarization: $SUMMARIZATION"
    else
      echo -e "${YELLOW}⚠ Non-EU models detected!${NC}"
      echo "  - Classification: $CLASSIFICATION"
      echo "  - Extraction: $EXTRACTION"
      echo "  - Summarization: $SUMMARIZATION"
      echo -e "${YELLOW}  To fix: python3 reload_config_from_s3.py${NC}"
    fi
  else
    echo -e "${YELLOW}⚠ Could not retrieve model configuration${NC}"
  fi
else
  echo -e "${YELLOW}⚠ ConfigurationTable not found, skipping verification${NC}"
fi

echo ""
echo "Next Steps:"
echo "  1. Test document upload via Web UI"
echo "  2. Monitor logs:"
echo "     aws logs tail /aws/lambda/${STACK_NAME}-UploadResolverFunction-* --follow"
echo "  3. Check Step Functions execution"
echo ""
echo -e "${BLUE}Tip: For faster iterations, you can run individual scripts:${NC}"
echo "  - ${YELLOW}./scripts/force-update-lambdas.sh${NC} (Lambda code only)"
echo "  - ${YELLOW}./scripts/publish-dev.sh${NC} (Build only)"
echo ""
