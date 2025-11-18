#!/bin/bash
# Verify compliance risk fields are being populated in DynamoDB after categorization

set -e

echo "=========================================="
echo "Verifying Compliance Risk Fields"
echo "=========================================="
echo ""

# Get latest analyzed transactions
echo "Querying for recently analyzed transactions..."
echo ""

aws dynamodb scan \
    --table-name fiscalshield-idp-dev-ExtractionResultsTable-ODNDYL7KUECH \
    --filter-expression "attribute_exists(AnalysisStatus) AND AnalysisStatus = :status" \
    --expression-attribute-values '{":status":{"S":"ANALYZED"}}' \
    --projection-expression "TransactionId,ExpenseCategory,ComplianceRiskScore,ComplianceRiskTier,ComplianceFlags,ThresholdFlag,GeographicRiskFlag,CashRiskFlag,StructuringFlag,VagueDescriptionFlag,TransactionAmount,CounterpartyCountry" \
    --limit 10 \
    --output json | jq -r '
    if .Items | length == 0 then
        "❌ No analyzed transactions found. Please trigger categorization first."
    else
        .Items[] | 
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "Transaction: \(.TransactionId.S // "N/A")",
        "Category: \(.ExpenseCategory.S // "N/A")",
        "Amount: £\(.TransactionAmount.N // .TransactionAmount.S // "N/A")",
        "Country: \(.CounterpartyCountry.S // "N/A")",
        "",
        "📊 COMPLIANCE RISK:",
        "   Score: \(.ComplianceRiskScore.N // "NOT SET") / 100",
        "   Tier: \(.ComplianceRiskTier.S // "NOT SET")",
        "   Active Flags: \((.ComplianceFlags.L // [] | map(.S) | join(", ")) // "NOT SET")",
        "",
        "🔍 INDIVIDUAL CHECKS:",
        "   Threshold: \(.ThresholdFlag.S // "NOT SET")",
        "   Geographic: \(.GeographicRiskFlag.S // "NOT SET")",
        "   Cash Risk: \(.CashRiskFlag.S // "NOT SET")",
        "   Structuring: \(.StructuringFlag.S // "NOT SET")",
        "   Vague Desc: \(.VagueDescriptionFlag.S // "NOT SET")",
        ""
    end
'

echo ""
echo "=========================================="
echo "Field Verification Summary"
echo "=========================================="

# Count how many transactions have compliance fields
TOTAL=$(aws dynamodb scan \
    --table-name fiscalshield-idp-dev-ExtractionResultsTable-ODNDYL7KUECH \
    --filter-expression "attribute_exists(AnalysisStatus) AND AnalysisStatus = :status" \
    --expression-attribute-values '{":status":{"S":"ANALYZED"}}' \
    --select COUNT \
    --output json | jq -r '.Count')

WITH_COMPLIANCE=$(aws dynamodb scan \
    --table-name fiscalshield-idp-dev-ExtractionResultsTable-ODNDYL7KUECH \
    --filter-expression "attribute_exists(ComplianceRiskScore)" \
    --select COUNT \
    --output json | jq -r '.Count')

echo ""
echo "Total analyzed transactions: $TOTAL"
echo "With compliance risk scores: $WITH_COMPLIANCE"
echo ""

if [ "$WITH_COMPLIANCE" -eq 0 ]; then
    echo "❌ No transactions have compliance risk scores yet."
    echo "   Action: Trigger categorization workflow to populate compliance data."
elif [ "$WITH_COMPLIANCE" -lt "$TOTAL" ]; then
    echo "⚠️  Only $WITH_COMPLIANCE of $TOTAL transactions have compliance scores."
    echo "   Some transactions may have been analyzed before compliance checking was deployed."
else
    echo "✅ All analyzed transactions have compliance risk scores!"
fi

echo ""
