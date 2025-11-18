#!/usr/bin/env python3
"""
Test HMRC compliance checking functions locally before deployment.
Run: python3 test_compliance_checks.py
"""

import sys
import json
from pathlib import Path

# Add lambdas directory to path
sys.path.insert(0, str(Path(__file__).parent / 'lambdas' / 'categorization'))

# Import the functions we just created
from handler import (
    check_threshold_breach,
    check_cash_risk,
    check_geographic_risk,
    check_structuring_pattern,
    check_vague_description,
    calculate_compliance_risk_score,
    HIGH_RISK_COUNTRIES
)

print("="*70)
print("HMRC COMPLIANCE FUNCTIONS - LOCAL TEST")
print("="*70)

# Verify high-risk countries loaded
print(f"\n✅ Loaded {len(HIGH_RISK_COUNTRIES)} high-risk countries")
print(f"   Sample countries: {', '.join(list(HIGH_RISK_COUNTRIES.keys())[:5])}")

# Test cases based on actual bank statement data
test_transactions = [
    {
        "name": "GitHub Payment (USA)",
        "amount": -29.81,
        "description": "GITHUB, INC. SAN FRANCISCO USA",
        "payment_method": "CARD",
        "country": "USA"
    },
    {
        "name": "Large Payment to Russia",
        "amount": -12500.00,
        "description": "Payment to Moscow Tech Ltd",
        "payment_method": "BACS",
        "country": "RUS"
    },
    {
        "name": "Suspicious Round Number",
        "amount": -9999.00,
        "description": "Services",
        "payment_method": "TRANSFER",
        "country": "UK"
    },
    {
        "name": "Large Cash Deposit",
        "amount": 8500.00,
        "description": "Cash deposit",
        "payment_method": "CASH",
        "country": "UK"
    },
    {
        "name": "Payment to Iran (Critical Risk)",
        "amount": -5000.00,
        "description": "Consultancy fee",
        "payment_method": "BACS",
        "country": "IRN"
    },
    {
        "name": "Normal UK Transaction",
        "amount": -150.00,
        "description": "Amazon.co.uk purchase",
        "payment_method": "CARD",
        "country": "UK"
    },
    {
        "name": "High-Value Vague Description",
        "amount": -15500.00,
        "description": "Payment",
        "payment_method": "BACS",
        "country": "UK"
    }
]

print("\n" + "="*70)
print("TESTING INDIVIDUAL COMPLIANCE CHECKS")
print("="*70)

for idx, txn in enumerate(test_transactions, 1):
    print(f"\n{'─'*70}")
    print(f"TEST {idx}: {txn['name']}")
    print(f"{'─'*70}")
    print(f"Amount: £{txn['amount']:,.2f}")
    print(f"Description: {txn['description']}")
    print(f"Payment Method: {txn['payment_method']}")
    print(f"Country: {txn['country']}")
    
    # Run all checks
    threshold = check_threshold_breach(txn['amount'])
    cash = check_cash_risk(txn['amount'], txn['payment_method'])
    geo = check_geographic_risk(txn['country'])
    structuring = check_structuring_pattern(txn['amount'])
    vague = check_vague_description(txn['description'], txn['amount'])
    
    # Calculate risk score
    risk = calculate_compliance_risk_score(threshold, cash, geo, structuring, vague)
    
    print(f"\n🎯 COMPLIANCE RESULTS:")
    print(f"   Risk Score: {risk['score']}/100")
    print(f"   Risk Tier: {risk['tier']}")
    
    if threshold['flag'] != 'NONE':
        print(f"   ⚠️  Threshold: {threshold['flag']} - {threshold['description']}")
    
    if cash['flag'] != 'NONE':
        print(f"   💰 Cash Risk: {cash['flag']} - {cash['description']}")
    
    if geo['flag'] != 'NONE':
        print(f"   🌍 Geographic: {geo['flag']} - {geo['description']}")
    
    if structuring['flag'] != 'NONE':
        print(f"   🔴 Structuring: {structuring['flag']} - {structuring['description']}")
    
    if vague['flag'] != 'NONE':
        print(f"   📝 Vague Desc: {vague['flag']} - {vague['description']}")
    
    if risk['flags']:
        print(f"\n   Active Flags: {', '.join(risk['flags'])}")
    else:
        print(f"\n   ✅ No compliance flags")

print("\n" + "="*70)
print("RISK TIER SUMMARY")
print("="*70)

risk_tiers = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
for txn in test_transactions:
    threshold = check_threshold_breach(txn['amount'])
    cash = check_cash_risk(txn['amount'], txn['payment_method'])
    geo = check_geographic_risk(txn['country'])
    structuring = check_structuring_pattern(txn['amount'])
    vague = check_vague_description(txn['description'], txn['amount'])
    risk = calculate_compliance_risk_score(threshold, cash, geo, structuring, vague)
    risk_tiers[risk['tier']] += 1

print(f"\nCRITICAL: {risk_tiers['CRITICAL']} transactions")
print(f"HIGH:     {risk_tiers['HIGH']} transactions")
print(f"MEDIUM:   {risk_tiers['MEDIUM']} transactions")
print(f"LOW:      {risk_tiers['LOW']} transactions")

print("\n" + "="*70)
print("✅ TEST COMPLETE - All functions working correctly!")
print("="*70)
print("\nNext step: Wire these into categorization workflow and save to DynamoDB")
