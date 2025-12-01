#!/bin/bash
# Query field-level accuracy metrics from the evaluation stack

REGION="eu-central-1"
TABLE_NAME="fiscalshield-idp-dev-EvaluationMetrics"

echo "=========================================="
echo "Field-Level Accuracy Metrics"
echo "=========================================="
echo ""

# Get the most recent evaluation ID
LATEST_EVAL=$(aws dynamodb scan \
  --table-name "$TABLE_NAME" \
  --region "$REGION" \
  --filter-expression "MetricType = :type" \
  --expression-attribute-values '{":type":{"S":"FIELD_LEVEL"}}' \
  --projection-expression "EvaluationId,EvaluationDate" \
  --max-items 1 \
  --output json | jq -r '.Items[0].EvaluationId.S' 2>/dev/null)

if [ -z "$LATEST_EVAL" ] || [ "$LATEST_EVAL" = "null" ]; then
  echo "No field-level metrics found yet."
  echo "Run an evaluation and wait for it to complete (6-24 hours for batch mode)."
  exit 0
fi

echo "Latest Evaluation: $LATEST_EVAL"
echo ""

# Query all field-level metrics for this evaluation
echo "Querying field-level metrics..."
aws dynamodb query \
  --table-name "$TABLE_NAME" \
  --region "$REGION" \
  --key-condition-expression "PK = :pk AND begins_with(SK, :sk)" \
  --expression-attribute-values "{\":pk\":{\"S\":\"EVALUATION#$LATEST_EVAL\"},\":sk\":{\"S\":\"FIELD#\"}}" \
  --output json | jq -r '
    .Items | sort_by(.ErrorRate.N | tonumber) | reverse | .[] | 
    "Field: \(.FieldName.S)
  Accuracy: \((.Accuracy.N | tonumber * 100))%
  Error Rate: \((.ErrorRate.N | tonumber * 100))%
  Total Occurrences: \(.TotalOccurrences.N)
  Exact Matches: \(.ExactMatches.N)
  Fuzzy Matches: \(.FuzzyMatches.N)
  Mismatches: \(.Mismatches.N)
  ----------------------------------------"
'

echo ""
echo "=========================================="
echo "Top 5 Most Problematic Fields"
echo "=========================================="
echo ""

# Show top 5 fields with highest error rates
aws dynamodb query \
  --table-name "$TABLE_NAME" \
  --region "$REGION" \
  --key-condition-expression "PK = :pk AND begins_with(SK, :sk)" \
  --expression-attribute-values "{\":pk\":{\"S\":\"EVALUATION#$LATEST_EVAL\"},\":sk\":{\"S\":\"FIELD#\"}}" \
  --output json | jq -r '
    .Items | sort_by(.ErrorRate.N | tonumber) | reverse | .[0:5] | .[] | 
    "\(.FieldName.S): \((.ErrorRate.N | tonumber * 100 | floor))% error rate (\(.Mismatches.N)/\(.TotalOccurrences.N) errors)"
' | nl

echo ""
echo "To see error examples for a specific field:"
echo "  aws dynamodb query \\"
echo "    --table-name $TABLE_NAME \\"
echo "    --region $REGION \\"
echo "    --key-condition-expression 'PK = :pk AND SK = :sk' \\"
echo "    --expression-attribute-values '{\":pk\":{\"S\":\"EVALUATION#$LATEST_EVAL\"},\":sk\":{\"S\":\"FIELD#<field_name>#<timestamp>\"}}' \\"
echo "    --output json | jq -r '.Items[0].ErrorExamples.S | fromjson'"
echo ""
