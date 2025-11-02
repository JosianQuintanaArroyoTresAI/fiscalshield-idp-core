# Company Data Cleanup Script

## Overview

This script safely removes all company data from DynamoDB tables to clean up dirty data from old deployments.

## What it Does

Deletes items from these tables:

### Data Collection Stack
- `fiscalshield-dc-{env}-CompanyEvents` - All company events
- `fiscalshield-dc-{env}-FilingEvents` - All filing events
- `fiscalshield-dc-{env}-HMRCData` - All HMRC data
- `fiscalshield-dc-{env}-RateLimits` - All rate limits

### Analysis Stack
- `fiscalshield-analysis-{env}-CompanyIntelligence` - All intelligence data

### User Data (Optional)
- `fiscalshield-idp-{env}-UserProfileTable` - Only company associations (preserves user profiles)

## Usage

### Dry Run (Recommended First Step)
```bash
# See what would be deleted without actually deleting
python3 scripts/cleanup_company_data.py --environment dev --dry-run
```

### Clean Dev Environment
```bash
# Clean all company data in dev
python3 scripts/cleanup_company_data.py --environment dev
```

### Clean Without User Data
```bash
# Clean everything except user-company associations
python3 scripts/cleanup_company_data.py --environment dev --skip-user-data
```

### Clean Production (DANGEROUS!)
```bash
# Requires typing 'DELETE PRODUCTION DATA' to confirm
python3 scripts/cleanup_company_data.py --environment prod
```

### Skip Confirmation Prompt
```bash
# Dangerous - use only in scripts
python3 scripts/cleanup_company_data.py --environment dev --confirm
```

## Options

- `--environment {dev|prod}` - Target environment (required)
- `--dry-run` - Show what would be deleted without actually deleting
- `--confirm` - Skip confirmation prompt (dangerous!)
- `--skip-user-data` - Keep user-company associations in UserProfileTable

## Safety Features

1. **Dry Run Mode**: Always shows what will be deleted before actually deleting
2. **Confirmation Prompts**: Requires explicit confirmation before deleting
3. **Production Protection**: Extra confirmation for production environment
4. **User Data Protection**: Only deletes company associations, not user profiles
5. **Idempotent**: Safe to run multiple times

## Example Output

```
======================================================================
🧹 Company Data Cleanup - Environment: DEV
======================================================================

📦 Stack: data_collection
----------------------------------------------------------------------
  📋 fiscalshield-dc-dev-CompanyEvents
     Items: 91
     Size: 983,288 bytes
     🗑️  Deleting all items...
     ✅ Deleted 91 items

📦 Stack: analysis
----------------------------------------------------------------------
  📋 fiscalshield-analysis-dev-CompanyIntelligence
     Items: 3
     Size: 2,847 bytes
     🗑️  Deleting all items...
     ✅ Deleted 3 items

======================================================================
📊 CLEANUP SUMMARY
======================================================================
✅ Deleted: 94 items from 2 tables
   • fiscalshield-dc-dev-CompanyEvents: 91 items
   • fiscalshield-analysis-dev-CompanyIntelligence: 3 items
======================================================================
```

## When to Use

- After old deployments with incompatible data schemas
- Before testing with fresh data
- To remove test data from development environment
- To reset demo environments

## What Happens to Documents?

- **Documents in S3**: Not deleted (remain accessible)
- **Document metadata**: Deleted from tracking tables
- **User profiles**: Preserved (unless deleting associations)
- **Cached analysis**: Deleted (will be recalculated on next request)

## Recovery

⚠️ **This operation is IRREVERSIBLE**

There is no way to recover deleted data except from backups. Always:
1. Run with `--dry-run` first
2. Confirm you want to delete the data
3. Consider taking a backup before running in production

## Requirements

- Python 3.x
- boto3 library
- AWS credentials configured
- Appropriate IAM permissions:
  - `dynamodb:Scan`
  - `dynamodb:DeleteItem`
  - `dynamodb:BatchWriteItem`

## Notes

- **Performance**: Large tables may take several minutes to clean
- **Capacity**: Uses on-demand capacity, no performance impact
- **Concurrency**: Safe to run while applications are running
- **Partial Cleanup**: If interrupted, can be safely rerun
