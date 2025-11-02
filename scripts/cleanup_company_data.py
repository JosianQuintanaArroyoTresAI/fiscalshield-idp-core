#!/usr/bin/env python3
"""
Cleanup Script - Remove All Company Data from DynamoDB Tables

This script deletes all items from company-related DynamoDB tables to remove
dirty data from old deployments. Use with caution - this is irreversible!

Usage:
    python3 scripts/cleanup_company_data.py --environment dev [--confirm]
    
Options:
    --environment: Target environment (dev/prod)
    --confirm: Skip confirmation prompt (dangerous!)
    --dry-run: Show what would be deleted without actually deleting
"""

import argparse
import boto3
from botocore.exceptions import ClientError
import sys
from typing import List, Dict

# DynamoDB tables to clean (by category)
COMPANY_TABLES = {
    'data_collection': [
        'CompanyEvents',
        'FilingEvents',
        'HMRCData',
        'RateLimits',
    ],
    'analysis': [
        'CompanyIntelligence',
    ],
    'user_data': [
        'UserProfileTable',  # Only company associations, not user profiles
    ],
}

class TableCleaner:
    def __init__(self, environment: str, region: str = 'eu-central-1', dry_run: bool = False):
        self.environment = environment
        self.region = region
        self.dry_run = dry_run
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.client = boto3.client('dynamodb', region_name=region)
        
    def get_table_name(self, stack: str, table_suffix: str) -> str:
        """Construct full table name from stack and suffix."""
        if stack == 'data_collection':
            return f'fiscalshield-dc-{self.environment}-{table_suffix}'
        elif stack == 'analysis':
            return f'fiscalshield-analysis-{self.environment}-{table_suffix}'
        elif stack == 'user_data':
            # UserProfileTable has unique suffix, need to find it
            tables = self.client.list_tables()['TableNames']
            for table_name in tables:
                if f'fiscalshield-idp-{self.environment}-{table_suffix}' in table_name:
                    return table_name
        return None
    
    def table_exists(self, table_name: str) -> bool:
        """Check if table exists."""
        try:
            self.dynamodb.Table(table_name).load()
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                return False
            raise
    
    def get_table_info(self, table_name: str) -> Dict:
        """Get table metadata."""
        table = self.dynamodb.Table(table_name)
        return {
            'name': table_name,
            'item_count': table.item_count,
            'size_bytes': table.table_size_bytes,
            'keys': [key['AttributeName'] for key in table.key_schema],
        }
    
    def delete_all_items(self, table_name: str) -> int:
        """Delete all items from a table."""
        table = self.dynamodb.Table(table_name)
        
        # Get key schema
        key_names = [key['AttributeName'] for key in table.key_schema]
        
        if self.dry_run:
            print(f"    [DRY RUN] Would scan and delete all items from {table_name}")
            return table.item_count or 0
        
        # Scan and delete
        scan_kwargs = {'ProjectionExpression': ','.join(key_names)}
        deleted_count = 0
        
        try:
            while True:
                response = table.scan(**scan_kwargs)
                items = response.get('Items', [])
                
                if not items:
                    break
                
                # Batch delete
                with table.batch_writer() as batch:
                    for item in items:
                        # Extract only key attributes
                        key = {k: item[k] for k in key_names if k in item}
                        batch.delete_item(Key=key)
                        deleted_count += 1
                
                # Check for more items
                if 'LastEvaluatedKey' not in response:
                    break
                    
                scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
                
        except ClientError as e:
            print(f"    ❌ Error deleting from {table_name}: {e}")
            return deleted_count
        
        return deleted_count
    
    def clean_user_companies(self, table_name: str) -> int:
        """
        Clean only company associations from UserProfileTable, 
        keeping user profiles intact.
        """
        table = self.dynamodb.Table(table_name)
        
        if self.dry_run:
            print(f"    [DRY RUN] Would clean company associations from {table_name}")
            # Count companies
            response = table.scan(
                FilterExpression='begins_with(SK, #comp)',
                ExpressionAttributeNames={'#comp': 'COMPANY#'}
            )
            return len(response.get('Items', []))
        
        deleted_count = 0
        
        try:
            # Scan for items where SK starts with "COMPANY#"
            response = table.scan(
                FilterExpression='begins_with(SK, #comp)',
                ExpressionAttributeNames={'#comp': 'COMPANY#'}
            )
            
            items = response.get('Items', [])
            
            if items:
                with table.batch_writer() as batch:
                    for item in items:
                        batch.delete_item(Key={
                            'PK': item['PK'],
                            'SK': item['SK']
                        })
                        deleted_count += 1
                        
        except ClientError as e:
            print(f"    ❌ Error cleaning companies from {table_name}: {e}")
            return deleted_count
        
        return deleted_count
    
    def cleanup_all(self, skip_user_data: bool = False) -> Dict:
        """Clean all company data tables."""
        results = {
            'cleaned': [],
            'skipped': [],
            'errors': [],
        }
        
        print(f"\n{'='*70}")
        print(f"🧹 Company Data Cleanup - Environment: {self.environment.upper()}")
        if self.dry_run:
            print("🔍 DRY RUN MODE - No data will be deleted")
        print(f"{'='*70}\n")
        
        # Process each stack's tables
        for stack, tables in COMPANY_TABLES.items():
            if stack == 'user_data' and skip_user_data:
                print(f"⏭️  Skipping {stack} (user data preserved)")
                continue
                
            print(f"\n📦 Stack: {stack}")
            print(f"{'-'*70}")
            
            for table_suffix in tables:
                table_name = self.get_table_name(stack, table_suffix)
                
                if not table_name:
                    print(f"  ⚠️  Table {table_suffix} not found")
                    results['skipped'].append(table_suffix)
                    continue
                
                if not self.table_exists(table_name):
                    print(f"  ⏭️  {table_name} - doesn't exist, skipping")
                    results['skipped'].append(table_name)
                    continue
                
                # Get table info
                info = self.get_table_info(table_name)
                print(f"\n  📋 {table_name}")
                print(f"     Items: {info['item_count']:,}")
                print(f"     Size: {info['size_bytes']:,} bytes")
                
                # Delete items
                if stack == 'user_data' and table_suffix == 'UserProfileTable':
                    # Only delete company associations, not user profiles
                    print(f"     🗑️  Cleaning company associations only...")
                    deleted = self.clean_user_companies(table_name)
                else:
                    # Delete all items
                    print(f"     🗑️  Deleting all items...")
                    deleted = self.delete_all_items(table_name)
                
                if deleted > 0:
                    action = "Would delete" if self.dry_run else "Deleted"
                    print(f"     ✅ {action} {deleted:,} items")
                    results['cleaned'].append({
                        'table': table_name,
                        'deleted': deleted
                    })
                else:
                    print(f"     ℹ️  No items to delete")
        
        return results


def main():
    parser = argparse.ArgumentParser(
        description='Clean all company data from DynamoDB tables'
    )
    parser.add_argument(
        '--environment',
        choices=['dev', 'prod'],
        required=True,
        help='Target environment'
    )
    parser.add_argument(
        '--confirm',
        action='store_true',
        help='Skip confirmation prompt (dangerous!)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be deleted without actually deleting'
    )
    parser.add_argument(
        '--skip-user-data',
        action='store_true',
        help='Skip cleaning UserProfileTable (keep user-company associations)'
    )
    
    args = parser.parse_args()
    
    # Safety check
    if args.environment == 'prod' and not args.dry_run:
        print("\n⚠️  WARNING: You are about to delete PRODUCTION data!")
        print("This operation is IRREVERSIBLE.\n")
        if not args.confirm:
            confirm = input("Type 'DELETE PRODUCTION DATA' to confirm: ")
            if confirm != 'DELETE PRODUCTION DATA':
                print("❌ Aborted.")
                sys.exit(1)
    elif not args.dry_run and not args.confirm:
        print(f"\n⚠️  You are about to delete all company data in {args.environment.upper()}")
        print("This operation is IRREVERSIBLE.\n")
        confirm = input(f"Type 'yes' to confirm: ")
        if confirm.lower() != 'yes':
            print("❌ Aborted.")
            sys.exit(1)
    
    # Run cleanup
    cleaner = TableCleaner(
        environment=args.environment,
        dry_run=args.dry_run
    )
    
    results = cleaner.cleanup_all(skip_user_data=args.skip_user_data)
    
    # Summary
    print(f"\n{'='*70}")
    print("📊 CLEANUP SUMMARY")
    print(f"{'='*70}\n")
    
    if results['cleaned']:
        total_deleted = sum(r['deleted'] for r in results['cleaned'])
        action = "Would be deleted" if args.dry_run else "Deleted"
        print(f"✅ {action}: {total_deleted:,} items from {len(results['cleaned'])} tables")
        for result in results['cleaned']:
            print(f"   • {result['table']}: {result['deleted']:,} items")
    
    if results['skipped']:
        print(f"\n⏭️  Skipped: {len(results['skipped'])} tables")
        for table in results['skipped']:
            print(f"   • {table}")
    
    if results['errors']:
        print(f"\n❌ Errors: {len(results['errors'])}")
        for error in results['errors']:
            print(f"   • {error}")
    
    print(f"\n{'='*70}\n")
    
    if args.dry_run:
        print("💡 TIP: Remove --dry-run flag to actually delete the data")
    else:
        print("✅ Cleanup complete!")


if __name__ == '__main__':
    main()
