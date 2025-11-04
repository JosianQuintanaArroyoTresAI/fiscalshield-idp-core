#!/bin/bash
# Invoice Routing Test Script
# Tests that invoice documents route to InvoiceExtractionFunction

set -e

echo "🧪 Invoice Routing Verification Test"
echo "===================================="
echo ""

# Get stack name from user
read -p "Enter your stack name (e.g., fiscalshield-idp-dev): " STACK_NAME

if [ -z "$STACK_NAME" ]; then
    echo "❌ Stack name is required"
    exit 1
fi

echo ""
echo "📋 Stack: $STACK_NAME"
echo ""

# Get TrackingTable name
echo "🔍 Looking up TrackingTable..."
TRACKING_TABLE=$(aws cloudformation describe-stack-resource \
    --stack-name "$STACK_NAME" \
    --logical-resource-id TrackingTable \
    --query 'StackResourceDetail.PhysicalResourceId' \
    --output text 2>/dev/null)

if [ -z "$TRACKING_TABLE" ]; then
    echo "❌ Could not find TrackingTable in stack"
    exit 1
fi

echo "✅ Found TrackingTable: $TRACKING_TABLE"
echo ""

# Get latest invoice document
echo "🔍 Finding latest invoice document..."
LATEST_DOC=$(aws dynamodb scan \
    --table-name "$TRACKING_TABLE" \
    --filter-expression "attribute_exists(user_document_type) AND user_document_type = :type" \
    --expression-attribute-values '{":type": {"S": "invoice"}}' \
    --limit 1 \
    --query 'Items[0]' 2>/dev/null)

if [ "$LATEST_DOC" == "null" ] || [ -z "$LATEST_DOC" ]; then
    echo "⚠️  No invoice documents found with user_document_type='invoice'"
    echo ""
    echo "To test:"
    echo "1. Upload a document via UI"
    echo "2. Select 'Invoice' document type"
    echo "3. Run this script again"
    exit 0
fi

# Extract key fields
OBJECT_KEY=$(echo "$LATEST_DOC" | jq -r '.ObjectKey.S // .id.S')
USER_DOC_TYPE=$(echo "$LATEST_DOC" | jq -r '.user_document_type.S')
EXEC_ARN=$(echo "$LATEST_DOC" | jq -r '.workflow_execution_arn.S // .WorkflowExecutionArn.S // empty')

echo "✅ Found document:"
echo "   Object Key: $OBJECT_KEY"
echo "   User Document Type: $USER_DOC_TYPE"
echo ""

# Check sections
SECTIONS=$(echo "$LATEST_DOC" | jq -r '.sections.L[0].M.classification.S // .Sections.L[0].M.classification.S // empty')
echo "📄 Section Classification: $SECTIONS"

if [ "$SECTIONS" == "invoice" ]; then
    echo "✅ Section classification is 'invoice' - routing should work!"
else
    echo "⚠️  Section classification is NOT 'invoice' - routing may fail"
    echo "   Expected: 'invoice'"
    echo "   Got: '$SECTIONS'"
fi
echo ""

# Check Step Functions execution if available
if [ -n "$EXEC_ARN" ] && [ "$EXEC_ARN" != "null" ]; then
    echo "🔍 Checking Step Functions execution..."
    echo "   Execution ARN: $EXEC_ARN"
    echo ""
    
    # Get execution history
    HISTORY=$(aws stepfunctions get-execution-history \
        --execution-arn "$EXEC_ARN" \
        --max-results 100 \
        --query 'events[?type==`TaskStateEntered`].stateEnteredEventDetails.name' \
        --output json 2>/dev/null || echo "[]")
    
    # Check if InvoiceExtraction was invoked
    if echo "$HISTORY" | grep -q "InvoiceExtraction"; then
        echo "✅ SUCCESS! InvoiceExtraction state was invoked"
        echo ""
        echo "📊 States executed:"
        echo "$HISTORY" | jq -r '.[]' | sed 's/^/   - /'
    else
        echo "❌ FAILED! InvoiceExtraction was NOT invoked"
        echo ""
        echo "📊 States executed:"
        echo "$HISTORY" | jq -r '.[]' | sed 's/^/   - /'
        echo ""
        echo "⚠️  Document routed to GenericExtraction instead of InvoiceExtraction"
        echo ""
        echo "Troubleshooting:"
        echo "1. Check trust_user_hint in config: should be 'true'"
        echo "2. Verify S3 metadata has user-document-type='invoice'"
        echo "3. Check Classification Lambda logs for 'using user hint'"
    fi
else
    echo "⚠️  No Step Functions execution ARN found"
    echo "   Document may still be processing"
fi

echo ""
echo "🔍 To verify manually:"
echo ""
echo "# Check Classification logs:"
echo "aws logs tail /aws/lambda/${STACK_NAME}-ClassificationFunction --follow"
echo ""
echo "# Check Invoice Extraction logs:"
echo "aws logs tail /aws/lambda/${STACK_NAME}-InvoiceExtractionFunction --follow"
echo ""
echo "# Check Step Functions execution:"
echo "aws stepfunctions describe-execution --execution-arn \"$EXEC_ARN\""
echo ""

# Check classification method in metadata
CLASS_METHOD=$(echo "$LATEST_DOC" | jq -r '.metadata.M.classification_method.S // empty')
if [ -n "$CLASS_METHOD" ]; then
    echo "📊 Classification Method: $CLASS_METHOD"
    if [ "$CLASS_METHOD" == "user_hint" ]; then
        echo "✅ Classification used user hint (Phase 2 working!)"
    else
        echo "⚠️  Classification method was '$CLASS_METHOD', not 'user_hint'"
    fi
fi

echo ""
echo "===================================="
echo "✅ Test Complete"
