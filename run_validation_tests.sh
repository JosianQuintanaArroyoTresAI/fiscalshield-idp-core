#!/bin/bash
# Test runner for validation logging and hallucination prevention tests

set -e

echo "=========================================="
echo "Running Validation & Hallucination Tests"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Run unit tests
echo -e "${BLUE}1. Running Classification Validation Logging Tests${NC}"
pytest tests/unit/classification/test_validation_logging.py -v --tb=short

echo ""
echo -e "${BLUE}2. Running Hallucination Prevention Tests${NC}"
pytest tests/unit/extraction/test_hallucination_prevention.py -v --tb=short

echo ""
echo -e "${BLUE}3. Running PyYAML None Handling Tests${NC}"
pytest lib/idp_common_pkg/tests/unit/test_yaml_none_handling.py -v --tb=short

echo ""
echo -e "${BLUE}4. Running Integration Tests${NC}"
pytest tests/integration/test_validation_workflow.py -v --tb=short

echo ""
echo -e "${GREEN}=========================================="
echo "All Tests Completed Successfully!"
echo "==========================================${NC}"
echo ""
echo "Test Summary:"
echo "  ✅ Classification validation logging"
echo "  ✅ LLM hallucination prevention"
echo "  ✅ PyYAML None handling"
echo "  ✅ End-to-end validation workflow"
echo ""
echo "Fixes Tested:"
echo "  • e8f8eb4e - Decimal conversion for DynamoDB"
echo "  • b82086fe - User hint routing logic"
echo "  • 37eca6f4 - Document.pages dict iteration"
echo "  • 392551eb - PyYAML library handling"
echo "  • 5348b398 - LLM hallucination prevention"
