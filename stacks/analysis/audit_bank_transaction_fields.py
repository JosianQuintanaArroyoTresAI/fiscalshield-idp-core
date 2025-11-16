#!/usr/bin/env python3
"""
Bank Transaction Data Field Audit Script

Purpose: Analyze what fields are actually available in extracted bank statement transactions
         to determine which HMRC compliance patterns are detectable.

Usage:
    # Run locally with AWS credentials configured
    python3 audit_bank_transaction_fields.py --env dev --limit 100
    
    # Or deploy as Lambda and invoke
    aws lambda invoke --function-name audit-bank-fields response.json

Output: Field availability report for updating BANK_TRANSACTION_HMRC_COMPLIANCE_ANALYSIS.md
"""

import boto3
import json
import argparse
from collections import Counter, defaultdict
from datetime import datetime
from typing import Dict, List, Any

def analyze_transaction_fields(table_name: str, limit: int = 100) -> Dict[str, Any]:
    """
    Scan DynamoDB table for bank statement transactions and analyze field availability.
    
    Args:
        table_name: Name of the ExtractionResults DynamoDB table
        limit: Maximum number of transactions to scan
    
    Returns:
        Dictionary with field availability statistics
    """
    print(f"\n🔍 Starting data audit for table: {table_name}")
    print(f"📊 Scanning up to {limit} bank statement transactions...\n")
    
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)
    
    # Scan for bank statement transactions
    response = table.scan(
        FilterExpression='begins_with(SK, :type)',
        ExpressionAttributeValues={
            ':type': 'type#BANK_STATEMENT'
        },
        Limit=limit
    )
    
    transactions = response.get('Items', [])
    total_scanned = len(transactions)
    
    if total_scanned == 0:
        return {
            'error': 'No bank statement transactions found in table',
            'suggestion': 'Check if bank statements have been uploaded and extracted'
        }
    
    print(f"✅ Found {total_scanned} bank statement transactions\n")
    
    # Track field availability
    field_counts = Counter()
    field_types = defaultdict(set)
    field_samples = defaultdict(list)
    
    # Essential fields we're looking for
    essential_fields = [
        'TransactionDate',
        'TransactionDescription', 
        'TransactionAmount',
        'TransactionType',
        'Reference'
    ]
    
    # Critical fields for advanced detection
    critical_fields = [
        'InboundOutbound',  # For circular transaction detection
        'Direction',  # Alternative name
        'DebitCredit',  # Alternative name
        'CounterpartyCountry',  # For geographic risk
        'Country',  # Alternative name
        'PaymentMethod',  # For cash detection
        'TransactionTimestamp',  # For same-day linked detection
        'Timestamp',  # Alternative name
        'CounterpartyName',  # For linked transaction detection
        'Payee',  # Alternative name
        'Payer',  # Alternative name
        'IBAN',  # For country extraction
        'SortCode',  # For domestic/international
        'BIC',  # For country extraction
        'SWIFT'  # Alternative name
    ]
    
    # Analyze each transaction
    for i, item in enumerate(transactions):
        for field_name, field_value in item.items():
            field_counts[field_name] += 1
            
            # Track field type
            field_types[field_name].add(type(field_value).__name__)
            
            # Collect samples (first 3 occurrences)
            if len(field_samples[field_name]) < 3 and field_value:
                # Sanitize sensitive data
                if isinstance(field_value, str) and len(field_value) > 50:
                    sample = field_value[:50] + "..."
                else:
                    sample = field_value
                field_samples[field_name].append(sample)
    
    # Generate report
    report = {
        'summary': {
            'table_name': table_name,
            'transactions_scanned': total_scanned,
            'unique_fields_found': len(field_counts),
            'audit_timestamp': datetime.utcnow().isoformat()
        },
        'essential_fields': {},
        'critical_fields': {},
        'all_fields': {},
        'compliance_capability': {}
    }
    
    # Analyze essential fields
    for field in essential_fields:
        count = field_counts.get(field, 0)
        percentage = (count / total_scanned * 100) if total_scanned > 0 else 0
        report['essential_fields'][field] = {
            'present': count > 0,
            'count': count,
            'percentage': round(percentage, 1),
            'types': list(field_types.get(field, [])),
            'samples': field_samples.get(field, [])
        }
    
    # Analyze critical fields
    for field in critical_fields:
        count = field_counts.get(field, 0)
        percentage = (count / total_scanned * 100) if total_scanned > 0 else 0
        if count > 0:  # Only include if found
            report['critical_fields'][field] = {
                'present': True,
                'count': count,
                'percentage': round(percentage, 1),
                'types': list(field_types.get(field, [])),
                'samples': field_samples.get(field, [])
            }
    
    # List all fields with counts
    for field, count in field_counts.most_common():
        percentage = (count / total_scanned * 100) if total_scanned > 0 else 0
        report['all_fields'][field] = {
            'count': count,
            'percentage': round(percentage, 1),
            'types': list(field_types.get(field, []))
        }
    
    # Determine compliance detection capabilities
    has_amount = field_counts.get('TransactionAmount', 0) > 0
    has_date = field_counts.get('TransactionDate', 0) > 0
    has_description = field_counts.get('TransactionDescription', 0) > 0
    
    # Check for direction indicator (multiple possible field names)
    has_direction = any([
        field_counts.get('InboundOutbound', 0) > 0,
        field_counts.get('Direction', 0) > 0,
        field_counts.get('DebitCredit', 0) > 0
    ])
    
    # Check for country indicator
    has_country = any([
        field_counts.get('CounterpartyCountry', 0) > 0,
        field_counts.get('Country', 0) > 0,
        field_counts.get('IBAN', 0) > 0,
        field_counts.get('BIC', 0) > 0,
        field_counts.get('SWIFT', 0) > 0
    ])
    
    # Check for payment method
    has_payment_method = field_counts.get('PaymentMethod', 0) > 0
    
    # Check for timestamp
    has_timestamp = any([
        field_counts.get('TransactionTimestamp', 0) > 0,
        field_counts.get('Timestamp', 0) > 0
    ])
    
    # Check for counterparty name
    has_counterparty = any([
        field_counts.get('CounterpartyName', 0) > 0,
        field_counts.get('Payee', 0) > 0,
        field_counts.get('Payer', 0) > 0,
        field_counts.get('TransactionDescription', 0) > 0  # Often contains counterparty
    ])
    
    report['compliance_capability'] = {
        'threshold_reporting': {
            'achievable': has_amount,
            'requires': ['TransactionAmount'],
            'status': '✅ YES' if has_amount else '❌ NO'
        },
        'linked_transactions': {
            'achievable': has_amount and has_date and has_counterparty,
            'requires': ['TransactionAmount', 'TransactionDate', 'CounterpartyName or Description'],
            'status': '✅ YES' if (has_amount and has_date and has_counterparty) else '❌ NO'
        },
        'geographic_risk': {
            'achievable': has_country,
            'requires': ['CounterpartyCountry or IBAN or BIC'],
            'status': '✅ YES' if has_country else '❌ NO'
        },
        'circular_transactions': {
            'achievable': has_direction and has_amount and has_counterparty,
            'requires': ['InboundOutbound or Direction', 'TransactionAmount', 'CounterpartyName'],
            'status': '✅ YES' if (has_direction and has_amount and has_counterparty) else '⚠️ PARTIAL (missing direction flag)' if (has_amount and has_counterparty) else '❌ NO'
        },
        'cash_detection': {
            'achievable': has_payment_method or has_description,
            'requires': ['PaymentMethod or TransactionDescription'],
            'status': '✅ YES' if has_payment_method else '⚠️ PARTIAL (from description only)' if has_description else '❌ NO'
        },
        'same_day_linked_detection': {
            'achievable': has_timestamp,
            'requires': ['TransactionTimestamp'],
            'status': '✅ YES' if has_timestamp else '⚠️ DATE-ONLY (can detect same-day, not same-hour)' if has_date else '❌ NO'
        }
    }
    
    return report


def print_report(report: Dict[str, Any]) -> None:
    """Print formatted audit report to console"""
    
    print("\n" + "="*80)
    print("BANK TRANSACTION DATA FIELD AUDIT REPORT")
    print("="*80)
    
    summary = report['summary']
    print(f"\n📋 Summary:")
    print(f"   Table: {summary['table_name']}")
    print(f"   Transactions Scanned: {summary['transactions_scanned']}")
    print(f"   Unique Fields Found: {summary['unique_fields_found']}")
    print(f"   Audit Time: {summary['audit_timestamp']}")
    
    print(f"\n✅ Essential Fields (Required for Basic Analysis):")
    for field, data in report['essential_fields'].items():
        status = "✅" if data['present'] else "❌"
        print(f"   {status} {field}: {data['count']}/{summary['transactions_scanned']} ({data['percentage']}%)")
        if data['present'] and data['samples']:
            print(f"      Sample: {data['samples'][0]}")
    
    print(f"\n🔍 Critical Fields (For Advanced Detection):")
    if report['critical_fields']:
        for field, data in report['critical_fields'].items():
            print(f"   ✅ {field}: {data['count']}/{summary['transactions_scanned']} ({data['percentage']}%)")
            if data['samples']:
                print(f"      Sample: {data['samples'][0]}")
    else:
        print("   ❌ None found")
    
    print(f"\n📊 All Fields Found:")
    for field, data in sorted(report['all_fields'].items(), key=lambda x: x[1]['count'], reverse=True):
        print(f"   • {field}: {data['count']} ({data['percentage']}%) - Type: {', '.join(data['types'])}")
    
    print(f"\n🎯 COMPLIANCE DETECTION CAPABILITIES:")
    print("="*80)
    for pattern, capability in report['compliance_capability'].items():
        print(f"\n{pattern.upper().replace('_', ' ')}:")
        print(f"   Status: {capability['status']}")
        print(f"   Requires: {', '.join(capability['requires'])}")
    
    print("\n" + "="*80)
    print("RECOMMENDATIONS FOR ANALYSIS DOCUMENT UPDATE")
    print("="*80)
    
    # Generate recommendations
    cap = report['compliance_capability']
    
    print("\n✅ TIER 1 PATTERNS (Achievable):")
    if cap['threshold_reporting']['achievable']:
        print("   • Threshold reporting (£10k/£15k)")
    if cap['linked_transactions']['achievable']:
        print("   • Linked transaction detection (MLR 2017 requirement)")
    
    print("\n⚠️ TIER 2 PATTERNS (Partial or Limited):")
    if cap['cash_detection']['status'].startswith('⚠️'):
        print("   • Cash detection (limited - need PaymentMethod field for accuracy)")
    if cap['circular_transactions']['status'].startswith('⚠️'):
        print("   • Circular transactions (limited - need InboundOutbound flag)")
    if cap['same_day_linked_detection']['status'].startswith('⚠️'):
        print("   • Same-day linked detection (date-only, not hour precision)")
    
    print("\n❌ TIER 3 PATTERNS (Not Achievable):")
    if not cap['geographic_risk']['achievable']:
        print("   • Geographic risk detection (missing country/IBAN data)")
    if not cap['circular_transactions']['achievable']:
        print("   • Circular transaction detection (missing direction flag)")
    
    print("\n" + "="*80)
    print("\n✅ Audit Complete!")
    print(f"📄 Save this report and update BANK_TRANSACTION_HMRC_COMPLIANCE_ANALYSIS.md\n")


def lambda_handler(event, context):
    """AWS Lambda handler"""
    table_name = event.get('table_name') or 'tag-ExtractionResults-dev'
    limit = event.get('limit', 100)
    
    report = analyze_transaction_fields(table_name, limit)
    
    return {
        'statusCode': 200,
        'body': json.dumps(report, indent=2, default=str)
    }


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(description='Audit bank transaction field availability')
    parser.add_argument('--env', default='dev', help='Environment (dev, staging, prod)')
    parser.add_argument('--table', help='DynamoDB table name (overrides env)')
    parser.add_argument('--limit', type=int, default=100, help='Number of transactions to scan')
    parser.add_argument('--json', action='store_true', help='Output JSON instead of formatted report')
    
    args = parser.parse_args()
    
    # Determine table name
    if args.table:
        table_name = args.table
    else:
        table_name = f'tag-ExtractionResults-{args.env}'
    
    try:
        report = analyze_transaction_fields(table_name, args.limit)
        
        if 'error' in report:
            print(f"\n❌ Error: {report['error']}")
            print(f"💡 {report['suggestion']}")
            return 1
        
        if args.json:
            print(json.dumps(report, indent=2, default=str))
        else:
            print_report(report)
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error running audit: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())
