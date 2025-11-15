#!/usr/bin/env python3
"""
Script to clear all items from ExtractionResultsTable and TrackingTable.
Use this during development to reset the tables.

Usage: python scripts/clear_extraction_results.py [--dry-run]
"""

import boto3
import sys
from botocore.exceptions import ClientError

# Table names
EXTRACTION_TABLE = "fiscalshield-idp-dev-ExtractionResultsTable-ODNDYL7KUECH"
TRACKING_TABLE = "fiscalshield-idp-dev-TrackingTable-TRSVOO9HY881"

def clear_table(table_name, dry_run=False):
    """Delete all items from a DynamoDB table"""
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)
    
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Scanning table: {table_name}")
    
    # Scan the table to get all items
    response = table.scan()
    items = response.get('Items', [])
    
    total_items = len(items)
    deleted_count = 0
    
    # Handle pagination
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response.get('Items', []))
        total_items = len(items)
        print(f"Scanned {total_items} items so far...")
    
    print(f"Found {total_items} total items to delete")
    
    if total_items == 0:
        print(f"✅ Table {table_name} is already empty!")
        return 0
    
    # Delete each item
    for item in items:
        pk = item['PK']
        sk = item['SK']
        
        if dry_run:
            print(f"[DRY RUN] Would delete: PK={pk}, SK={sk}")
            deleted_count += 1
        else:
            try:
                table.delete_item(Key={'PK': pk, 'SK': sk})
                deleted_count += 1
                if deleted_count % 10 == 0:
                    print(f"Deleted {deleted_count}/{total_items} items...")
            except ClientError as e:
                print(f"Error deleting item PK={pk}, SK={sk}: {e}")
    
    print(f"{'[DRY RUN] Would delete' if dry_run else '✅ Successfully deleted'} {deleted_count} items from {table_name}")
    return deleted_count

if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    
    if dry_run:
        print("=" * 60)
        print("Running in DRY RUN mode - no items will be deleted")
        print("=" * 60)
    else:
        print("=" * 60)
        print("⚠️  WARNING: This will DELETE ALL items from:")
        print(f"  - {EXTRACTION_TABLE}")
        print(f"  - {TRACKING_TABLE}")
        print("=" * 60)
        confirm = input("Are you sure? Type 'yes' to confirm: ")
        if confirm.lower() != 'yes':
            print("Aborted.")
            sys.exit(0)
    
    total_deleted = 0
    
    # Clear ExtractionResultsTable
    print("\n" + "=" * 60)
    print("CLEARING EXTRACTION RESULTS TABLE")
    print("=" * 60)
    total_deleted += clear_table(EXTRACTION_TABLE, dry_run=dry_run)
    
    # Clear TrackingTable
    print("\n" + "=" * 60)
    print("CLEARING TRACKING TABLE")
    print("=" * 60)
    total_deleted += clear_table(TRACKING_TABLE, dry_run=dry_run)
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"{'[DRY RUN] Would delete' if dry_run else 'Successfully deleted'} {total_deleted} total items")
    print("=" * 60)
    
    if not dry_run:
        print("\n✅ Tables cleared! You can now re-upload invoices.")
        print("   New invoices will use the correct GSI6PK format.")
