#!/bin/bash
# Force update Lambda functions with latest code from local source
# Use this when CloudFormation doesn't detect changes

set -e

STACK_NAME="fiscalshield-idp-dev"
REGION="eu-central-1"

echo "======================================================================"
echo "Force Update Lambda Functions"
echo "======================================================================"
echo ""
echo "This will package and deploy Lambda functions directly, bypassing"
echo "CloudFormation's change detection."
echo ""

# Functions to update (add more as needed)
FUNCTIONS=(
    "upload_resolver:UploadResolverFunction"
    "queue_sender:QueueSender"
    "create_document_resolver:CreateDocumentResolverFunction"
)

# Build temp directory
TEMP_DIR="/tmp/lambda-updates-$$"
mkdir -p "$TEMP_DIR"

echo "Building and updating Lambda functions..."
echo "----------------------------------------------"

for func_def in "${FUNCTIONS[@]}"; do
    IFS=':' read -r source_dir logical_id <<< "$func_def"
    
    echo ""
    echo "📦 Processing: $source_dir → $logical_id"
    
    # Get physical function name from CloudFormation
    FUNCTION_NAME=$(aws cloudformation describe-stack-resource \
        --stack-name "$STACK_NAME" \
        --logical-resource-id "$logical_id" \
        --query 'StackResourceDetail.PhysicalResourceId' \
        --output text 2>/dev/null)
    
    if [ -z "$FUNCTION_NAME" ] || [ "$FUNCTION_NAME" == "None" ]; then
        echo "   ⚠️  Function $logical_id not found in stack, skipping..."
        continue
    fi
    
    echo "   Function Name: $FUNCTION_NAME"
    
    # Build package
    PACKAGE_DIR="$TEMP_DIR/$source_dir"
    mkdir -p "$PACKAGE_DIR"
    
    SOURCE_PATH="src/lambda/$source_dir"
    
    if [ ! -d "$SOURCE_PATH" ]; then
        echo "   ⚠️  Source directory not found: $SOURCE_PATH, skipping..."
        continue
    fi
    
    echo "   Building package from $SOURCE_PATH..."
    
    # Copy source code
    cp -r "$SOURCE_PATH"/* "$PACKAGE_DIR/" 2>/dev/null || true
    
    # Install dependencies if requirements.txt exists
    if [ -f "$SOURCE_PATH/requirements.txt" ]; then
        echo "   Installing dependencies..."
        pip install -q -r "$SOURCE_PATH/requirements.txt" -t "$PACKAGE_DIR/" --upgrade 2>&1 | grep -v "already satisfied" || true
    fi
    
    # Create zip using Python (zip command not available)
    ZIP_FILE="$TEMP_DIR/${source_dir}.zip"
    echo "   Creating deployment package..."
    python3 -c "
import zipfile
import os
from pathlib import Path

zip_path = '$ZIP_FILE'
source_dir = '$PACKAGE_DIR'

with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk(source_dir):
        # Skip __pycache__ and .git directories
        dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git']]
        for file in files:
            if not file.endswith('.pyc'):
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, source_dir)
                zipf.write(file_path, arcname)
"
    
    # Update function code
    echo "   Uploading to Lambda..."
    aws lambda update-function-code \
        --function-name "$FUNCTION_NAME" \
        --zip-file "fileb://$ZIP_FILE" \
        --region "$REGION" \
        --output json > /dev/null
    
    if [ $? -eq 0 ]; then
        echo "   ✅ Updated successfully!"
        
        # Wait for update to complete
        echo "   Waiting for update to complete..."
        aws lambda wait function-updated \
            --function-name "$FUNCTION_NAME" \
            --region "$REGION" 2>/dev/null || true
    else
        echo "   ❌ Update failed!"
    fi
done

# Cleanup
rm -rf "$TEMP_DIR"

echo ""
echo "======================================================================"
echo "✅ Lambda update complete!"
echo "======================================================================"
echo ""
echo "Next steps:"
echo "  1. Test document upload via Web UI"
echo "  2. Check logs:"
echo "     aws logs tail /aws/lambda/fiscalshield-idp-dev-UploadResolverFunction-* --follow"
echo "  3. Verify S3 path contains Cognito UUID"
echo ""
