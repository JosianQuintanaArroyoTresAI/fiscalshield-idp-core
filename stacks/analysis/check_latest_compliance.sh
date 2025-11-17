#!/bin/bash
# Quick check for latest compliance risk scores

echo "🔍 Checking latest analyzed transactions with compliance scores..."
echo ""

aws dynamodb scan \
    --table-name fiscalshield-idp-dev-ExtractionResultsTable-ODNDYL7KUECH \
    --filter-expression "attribute_exists(ComplianceRiskScore)" \
    --limit 10 \
    --output json | python3 << 'EOF'
import json, sys
from datetime import datetime

data = json.load(sys.stdin)
items = data.get('Items', [])

if not items:
    print("❌ No transactions with compliance scores found yet.")
    print("   Upload a bank statement and press 'Analysis' to test.")
    sys.exit(0)

print(f"✅ Found {len(items)} transactions with compliance risk scores!\n")

# Sort by AnalyzedAt timestamp (most recent first)
items_with_time = []
for item in items:
    analyzed_at = item.get('AnalyzedAt', {}).get('N')
    if analyzed_at:
        items_with_time.append((int(analyzed_at), item))

items_with_time.sort(reverse=True)

for i, (timestamp, item) in enumerate(items_with_time[:5], 1):
    print("━" * 70)
    print(f"#{i} - Analyzed: {datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Counterparty: {item.get('CounterpartyName', {}).get('S', 'N/A')}")
    print(f"Amount: £{item.get('TransactionAmount', {}).get('N', 'N/A')}")
    print(f"Country: {item.get('CounterpartyCountry', {}).get('S', 'N/A')}")
    print(f"Category: {item.get('ExpenseCategory', {}).get('S', 'N/A')}")
    
    score = item.get('ComplianceRiskScore', {}).get('N', '0')
    tier = item.get('ComplianceRiskTier', {}).get('S', 'UNKNOWN')
    flags = item.get('ComplianceFlags', {}).get('L', [])
    flag_list = [f.get('S', '') for f in flags]
    
    # Color code by tier
    tier_emoji = {
        'CRITICAL': '🔴',
        'HIGH': '🟠', 
        'MEDIUM': '🟡',
        'LOW': '🟢'
    }.get(tier, '⚪')
    
    print(f"\n{tier_emoji} COMPLIANCE RISK: {score}/100 ({tier})")
    if flag_list:
        print(f"   Flags: {', '.join(flag_list)}")
    else:
        print(f"   Flags: None (clean transaction)")
    print()

print("━" * 70)
print(f"\n💡 All {len(items)} transactions have compliance data stored in DynamoDB")
print("   Ready for frontend to query and display!")
EOF
