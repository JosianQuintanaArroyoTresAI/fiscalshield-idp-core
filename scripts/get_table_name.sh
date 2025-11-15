#!/bin/bash
# Get the ExtractionResultsTable name from CloudFormation stack

STACK_NAME="${1:-fiscalshield-idp-dev}"

echo "Getting ExtractionResultsTable name from stack: $STACK_NAME"

TABLE_NAME=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='ExtractionResultsTableName'].OutputValue" \
  --output text)

if [ -z "$TABLE_NAME" ]; then
  echo "❌ Could not find ExtractionResultsTableName output in stack"
  echo "Trying to get from resources..."
  
  TABLE_NAME=$(aws cloudformation describe-stack-resources \
    --stack-name "$STACK_NAME" \
    --logical-resource-id ExtractionResultsTable \
    --query "StackResources[0].PhysicalResourceId" \
    --output text)
fi

if [ -z "$TABLE_NAME" ]; then
  echo "❌ Could not determine table name"
  exit 1
fi

echo "✅ Table name: $TABLE_NAME"
echo ""
echo "To run the migration script:"
echo "  python3 scripts/fix_gsi6pk_extraction_results.py --table-name $TABLE_NAME --dry-run"
echo ""
echo "To apply the fix:"
echo "  python3 scripts/fix_gsi6pk_extraction_results.py --table-name $TABLE_NAME"
