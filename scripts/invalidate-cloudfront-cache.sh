#!/bin/bash
# Invalidate CloudFront cache for UI updates

set -e

STACK_NAME="${1:-fiscalshield-idp-dev}"
REGION="${2:-eu-central-1}"

echo "🔍 Finding CloudFront distribution for stack: $STACK_NAME"

# Get CloudFront Distribution ID from CloudFormation outputs
DISTRIBUTION_ID=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --query 'Stacks[0].Outputs[?contains(OutputKey, `CloudFront`) || contains(OutputKey, `Distribution`)].OutputValue' \
  --output text 2>/dev/null || echo "")

if [ -z "$DISTRIBUTION_ID" ]; then
  echo "❌ Could not find CloudFront distribution ID"
  echo "Trying alternative method..."
  
  # Try to find distribution by tag
  DISTRIBUTION_ID=$(aws cloudfront list-distributions \
    --query "DistributionList.Items[?contains(Comment, '$STACK_NAME')].Id" \
    --output text 2>/dev/null | head -1)
fi

if [ -z "$DISTRIBUTION_ID" ]; then
  echo "❌ No CloudFront distribution found for stack $STACK_NAME"
  exit 1
fi

echo "✅ Found CloudFront Distribution: $DISTRIBUTION_ID"
echo "🔄 Creating invalidation for all files (/*)"

# Create invalidation
INVALIDATION_ID=$(aws cloudfront create-invalidation \
  --distribution-id "$DISTRIBUTION_ID" \
  --paths "/*" \
  --query 'Invalidation.Id' \
  --output text)

echo "✅ Invalidation created: $INVALIDATION_ID"
echo "⏳ Waiting for invalidation to complete (this may take 1-2 minutes)..."

# Wait for invalidation to complete
aws cloudfront wait invalidation-completed \
  --distribution-id "$DISTRIBUTION_ID" \
  --id "$INVALIDATION_ID"

echo "✅ CloudFront cache invalidated successfully!"
echo "🌐 UI changes should now be visible. Please hard refresh your browser (Ctrl+Shift+R)"
