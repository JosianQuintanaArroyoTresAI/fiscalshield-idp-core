#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Script to fix GSI6PK values in ExtractionResultsTable.

This script scans the ExtractionResultsTable and updates records where:
- GSI6PK uses client_id instead of company_number
- Updates GSI6PK to use company_number from CompanyNumber field

Usage:
    python scripts/fix_gsi6pk_extraction_results.py --table-name <table_name> [--dry-run]
"""

import argparse
import boto3
from decimal import Decimal
import sys

def fix_gsi6pk(table_name: str, dry_run: bool = True):
    """
    Scan ExtractionResultsTable and fix GSI6PK values.
    
    Args:
        table_name: Name of the DynamoDB table
        dry_run: If True, only report what would be changed without making changes
    """
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)
    
    print(f"{'🔍 DRY RUN MODE - No changes will be made' if dry_run else '✍️  LIVE MODE - Changes will be applied'}")
    print(f"Scanning table: {table_name}\n")
    
    updated_count = 0
    skipped_count = 0
    error_count = 0
    
    # Scan the entire table
    scan_kwargs = {}
    
    while True:
        response = table.scan(**scan_kwargs)
        items = response.get('Items', [])
        
        for item in items:
            try:
                pk = item.get('PK', '')
                sk = item.get('SK', '')
                current_gsi6pk = item.get('GSI6PK', '')
                company_number = item.get('CompanyNumber', '')
                document_type = item.get('DocumentType', 'INVOICE')
                
                # Expected GSI6PK format
                expected_gsi6pk = f"client#{company_number}#type#{document_type}"
                
                # Check if GSI6PK needs updating
                if current_gsi6pk != expected_gsi6pk:
                    print(f"📝 Record needs update:")
                    print(f"   PK: {pk}")
                    print(f"   SK: {sk}")
                    print(f"   Current GSI6PK:  {current_gsi6pk}")
                    print(f"   Expected GSI6PK: {expected_gsi6pk}")
                    print(f"   CompanyNumber: {company_number}")
                    
                    if not dry_run:
                        # Update the item
                        table.update_item(
                            Key={'PK': pk, 'SK': sk},
                            UpdateExpression='SET GSI6PK = :new_gsi6pk',
                            ExpressionAttributeValues={
                                ':new_gsi6pk': expected_gsi6pk
                            }
                        )
                        print(f"   ✅ Updated!\n")
                    else:
                        print(f"   ⏭️  Would update (dry-run)\n")
                    
                    updated_count += 1
                else:
                    skipped_count += 1
                    
            except Exception as e:
                print(f"❌ Error processing item {item.get('PK')}: {str(e)}\n")
                error_count += 1
        
        # Check if there are more items to scan
        if 'LastEvaluatedKey' in response:
            scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
        else:
            break
    
    print("\n" + "="*60)
    print("Summary:")
    print(f"  Records needing update: {updated_count}")
    print(f"  Records already correct: {skipped_count}")
    print(f"  Errors: {error_count}")
    
    if dry_run and updated_count > 0:
        print("\n⚠️  Run without --dry-run to apply these changes")
    elif updated_count > 0:
        print("\n✅ All records updated successfully!")
    else:
        print("\n✅ All records already have correct GSI6PK values!")


def main():
    parser = argparse.ArgumentParser(
        description='Fix GSI6PK values in ExtractionResultsTable'
    )
    parser.add_argument(
        '--table-name',
        required=True,
        help='Name of the DynamoDB ExtractionResultsTable'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be changed without making changes'
    )
    
    args = parser.parse_args()
    
    # Confirm before running in live mode
    if not args.dry_run:
        confirm = input(f"\n⚠️  You are about to modify records in {args.table_name}. Continue? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Cancelled.")
            sys.exit(0)
    
    fix_gsi6pk(args.table_name, args.dry_run)


if __name__ == '__main__':
    main()
