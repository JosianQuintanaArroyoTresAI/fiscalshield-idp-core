#!/bin/bash

# Force rebuild and redeploy the UI
# This script clears all caches and forces a clean build of the React UI
# Usage: ./scripts/force-rebuild-ui.sh [stack-name] [region]

set -e

STACK_NAME="${STACK_NAME:-${1:-fiscalshield-idp-dev}}"
REGION="${REGION:-${2:-eu-central-1}}"

echo "🔄 Force UI Rebuild Script"
echo "Stack: $STACK_NAME"
echo "Region: $REGION"
echo ""

# Get the WebUI bucket name from CloudFormation
echo "📦 Finding WebUI S3 bucket..."
WEBUI_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --query 'Stacks[0].Outputs[?OutputKey==`WebUIBucketName`].OutputValue' \
  --output text 2>/dev/null || echo "")

if [ -z "$WEBUI_BUCKET" ]; then
  # Try to find bucket by prefix
  WEBUI_BUCKET=$(aws s3 ls | grep "${STACK_NAME}-webuibucket" | tail -1 | awk '{print $3}')
fi

if [ -z "$WEBUI_BUCKET" ]; then
  echo "❌ Could not find WebUI bucket for stack $STACK_NAME"
  exit 1
fi

echo "✅ Found bucket: $WEBUI_BUCKET"
echo ""

# Clear local build artifacts
echo "🧹 Clearing local build caches..."
cd "$(dirname "$0")/.."
if [ -d "src/ui/build" ]; then
  rm -rf src/ui/build
  echo "  ✓ Removed build/"
fi
if [ -d "src/ui/node_modules/.cache" ]; then
  rm -rf src/ui/node_modules/.cache
  echo "  ✓ Removed node_modules/.cache"
fi
if [ -d "src/ui/.cache" ]; then
  rm -rf src/ui/.cache
  echo "  ✓ Removed .cache/"
fi
echo ""

# Rebuild UI
echo "🔨 Building UI with clean slate..."
cd src/ui
npm ci --prefer-offline --no-audit
GENERATE_SOURCEMAP=false CI=true npm run build
echo "✅ UI build complete"
echo ""

# Sync to S3
echo "📤 Uploading to S3..."
aws s3 sync build/ "s3://$WEBUI_BUCKET/" \
  --region "$REGION" \
  --delete \
  --cache-control "public, max-age=31536000, immutable" \
  --exclude "*.html" \
  --exclude "service-worker.js" \
  --exclude "asset-manifest.json"

# Upload index.html with no-cache
aws s3 cp build/index.html "s3://$WEBUI_BUCKET/index.html" \
  --region "$REGION" \
  --cache-control "no-cache, no-store, must-revalidate" \
  --content-type "text/html"

echo "✅ Upload complete"
echo ""

# Get CloudFront distribution
echo "🌐 Finding CloudFront distribution..."
DISTRIBUTION_ID=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontDistributionId`].OutputValue' \
  --output text 2>/dev/null || echo "")

if [ -z "$DISTRIBUTION_ID" ]; then
  # Try to find by resource
  DISTRIBUTION_ID=$(aws cloudformation describe-stack-resources \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'StackResources[?ResourceType==`AWS::CloudFront::Distribution`].PhysicalResourceId' \
    --output text 2>/dev/null || echo "")
fi

if [ -z "$DISTRIBUTION_ID" ]; then
  echo "⚠️  Could not find CloudFront distribution - skipping invalidation"
  echo "✅ UI rebuild complete (but cache not invalidated)"
  exit 0
fi

echo "✅ Found distribution: $DISTRIBUTION_ID"
echo ""

# Create CloudFront invalidation
echo "🔄 Creating CloudFront invalidation..."
INVALIDATION_ID=$(aws cloudfront create-invalidation \
  --distribution-id "$DISTRIBUTION_ID" \
  --paths "/*" \
  --query 'Invalidation.Id' \
  --output text)

echo "✅ Invalidation created: $INVALIDATION_ID"
echo ""
echo "⏳ Waiting for invalidation to complete (this may take 1-2 minutes)..."

aws cloudfront wait invalidation-completed \
  --distribution-id "$DISTRIBUTION_ID" \
  --id "$INVALIDATION_ID" 2>/dev/null || true

echo ""
echo "✅ Force UI rebuild complete!"
echo ""
echo "📋 Summary:"
echo "  • Cleared all build caches"
echo "  • Fresh UI build created"
echo "  • Uploaded to S3: s3://$WEBUI_BUCKET/"
echo "  • CloudFront invalidated: $DISTRIBUTION_ID"
echo ""
echo "🔍 Next steps:"
echo "  1. Hard refresh your browser (Ctrl+Shift+R or Cmd+Shift+R)"
echo "  2. Check browser DevTools → Network tab for new file timestamps"
echo "  3. Test your changes"
echo ""
