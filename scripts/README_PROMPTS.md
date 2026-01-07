# Prompt Management Architecture

## Overview

This system uses a **dual-source approach** for managing extraction prompts:

1. **Lambda Code** = Source of truth (default prompts)
2. **DynamoDB** = User customizations + version tracking

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                    DEPLOYMENT (CI/CD)                        │
│                                                              │
│  1. Deploy Lambda with updated code                         │
│  2. Run sync_prompts_to_dynamodb.py                         │
│     ├─ Reads prompt from Lambda code                        │
│     ├─ Checks DynamoDB for existing prompt                  │
│     └─ Decision:                                            │
│        • If NO prompt exists → Create v1                    │
│        • If DEFAULT prompt → Update to new version          │
│        • If CUSTOM prompt → Preserve, track new version     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    RUNTIME (Lambda)                          │
│                                                              │
│  1. Lambda receives extraction request                      │
│  2. Checks DynamoDB ConfigurationTable                      │
│     ├─ If prompt exists → Use it                            │
│     └─ If NOT found → Use default from code                 │
│  3. Process extraction with prompt                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Architecture Benefits

✅ **Code as Source of Truth** - Developers update prompts in code
✅ **User Customization** - Frontend users can override via UI
✅ **Version Tracking** - Knows when custom prompts are outdated
✅ **No Drift** - Automated sync ensures consistency
✅ **Safe Updates** - Preserves user customizations
✅ **Audit Trail** - Tracks who changed what and when

## Files

### Core Scripts
- `sync_prompts_to_dynamodb.py` - Automated sync (runs in CI/CD)
- `init_invoice_prompt.py` - Manual initialization (legacy)

### Prompt Sources (Lambda Code)
- `patterns/pattern-2/lambdas/invoice_extraction/invoice_extraction_handler.py`
  - Function: `get_default_invoice_prompt()`
  - Key: `INVOICE_EXTRACTION_PROMPT`

### CI/CD Integration
- `.github/workflows/deploy-dev.yml` - Auto-sync on dev deploy
- `.github/workflows/deploy-prod.yml` - Auto-sync on prod deploy

## Usage

### Automatic (Recommended)
Prompts sync automatically on every deployment. No action needed!

### Manual Sync
```bash
# Sync all prompts from code to DynamoDB
python scripts/sync_prompts_to_dynamodb.py \
  --stack-name fiscalshield-idp-dev \
  --region eu-central-1

# Force update (overwrites custom versions - DANGEROUS!)
python scripts/sync_prompts_to_dynamodb.py \
  --stack-name fiscalshield-idp-dev \
  --region eu-central-1 \
  --force
```

### Check Prompt Status
```bash
# Query DynamoDB to see current prompt version
aws dynamodb get-item \
  --table-name <ConfigurationTable-name> \
  --key '{"Configuration": {"S": "INVOICE_EXTRACTION_PROMPT"}}' \
  --region eu-central-1
```

## DynamoDB Schema

```python
{
    'Configuration': 'INVOICE_EXTRACTION_PROMPT',  # Partition key
    'PromptTemplate': '<prompt text>',              # The actual prompt
    'Version': 3,                                   # Current version
    'IsCustom': False,                              # True if user customized
    'AvailableVersion': 4,                          # Latest from code (if IsCustom=True)
    'LastUpdated': '2026-01-07T10:30:00',          # Last modification
    'LastCodeUpdate': '2026-01-07T10:30:00',       # Last code update
    'UpdatedBy': 'cicd-deployment',                # Who updated
    'Source': 'lambda-code-sync'                    # How it was updated
}
```

## Workflow Examples

### Scenario 1: New Deployment (No Existing Prompt)
```
1. Deploy code with new prompt
2. sync_prompts_to_dynamodb.py runs
3. Creates prompt in DynamoDB (v1, IsCustom=False)
4. Lambda uses this prompt
```

### Scenario 2: Update Default Prompt
```
1. Developer updates prompt in Lambda code
2. Deploy to dev
3. sync_prompts_to_dynamodb.py detects default prompt
4. Updates DynamoDB (v2, IsCustom=False)
5. Lambda immediately uses new version
```

### Scenario 3: User Customized Prompt
```
1. User edits prompt via frontend UI
2. Frontend sets IsCustom=True in DynamoDB
3. Developer updates prompt in code
4. sync_prompts_to_dynamodb.py detects custom version
5. Preserves user's version
6. Sets AvailableVersion to notify of update
7. User can review and adopt new version via UI
```

## Adding New Prompts

To add a new prompt to auto-sync:

1. **Add function to Lambda handler:**
```python
def get_default_your_prompt() -> str:
    return """Your prompt here..."""
```

2. **Update sync script** (`sync_prompts_to_dynamodb.py`):
```python
prompts_to_sync = [
    # ... existing prompts ...
    {
        'path': 'patterns/pattern-2/lambdas/your_extraction/handler.py',
        'function': 'get_default_your_prompt',
        'key': 'YOUR_EXTRACTION_PROMPT',
        'name': 'Your Extraction'
    },
]
```

3. **Deploy** - Auto-sync handles the rest!

## Troubleshooting

### Prompt not updating after deployment?
```bash
# Check if it's a custom version
aws dynamodb get-item \
  --table-name <table> \
  --key '{"Configuration": {"S": "INVOICE_EXTRACTION_PROMPT"}}' \
  --query 'Item.IsCustom.BOOL' \
  --region eu-central-1
```

### Force update (use with caution!)
```bash
python scripts/sync_prompts_to_dynamodb.py \
  --stack-name fiscalshield-idp-dev \
  --region eu-central-1 \
  --force
```

### Lambda using old prompt?
Check CloudWatch logs for:
- `✅ Retrieved custom invoice prompt from ConfigurationTable`
- `⚠️ No custom prompt found, using default`

## Best Practices

1. ✅ **Always update prompts in Lambda code first**
2. ✅ **Test in dev before promoting to prod**
3. ✅ **Document major prompt changes in commits**
4. ✅ **Never use `--force` in production without backup**
5. ✅ **Communicate prompt updates to users with custom versions**

## Date Format Example (Current Issue Fixed)

**Before:** Mixed formats in DynamoDB
```
InvoiceDate: "15/03/2020"  ❌
InvoiceDate: "2020-09-14"  ✅
InvoiceDate: "14/09/2020"  ❌
```

**After:** Consistent YYYY-MM-DD
```
InvoiceDate: "2020-03-15"  ✅
InvoiceDate: "2020-09-14"  ✅
InvoiceDate: "2020-09-14"  ✅
```

**How it was fixed:**
1. Updated `get_default_invoice_prompt()` to require YYYY-MM-DD
2. Added `normalize_date_to_iso()` function in Lambda
3. Added auto-sync to CI/CD pipeline
4. Next deployment will propagate the fix automatically! 🎉
