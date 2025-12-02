# Dev Environment Deployment Plan
## After merging KMS fix changes to dev branch

### **Problem:**
After merging the KMS fix to dev, the analysis stack will expect:
1. `ExtractionResultsKMSKeyArn` parameter (now required)
2. `KMSEncryptionKeyArn` output from main IDP stack (doesn't exist yet in dev)

### **Solution: Deploy in correct order**

---

## Step 1: Deploy Main IDP Stack First
This adds the `KMSEncryptionKeyArn` output that the analysis stack needs.

```bash
cd /home/josian/git/fiscalshield-idp-core

# Build and deploy main stack
sam build
sam deploy --config-env dev
```

**What this does:**
- Adds `KMSEncryptionKeyArn` output to dev stack
- No breaking changes - just adds a new output
- Takes ~2-5 minutes

**Verify:**
```bash
aws cloudformation describe-stacks \
  --stack-name fiscalshield-idp-dev \
  --region eu-central-1 \
  --query 'Stacks[0].Outputs[?OutputKey==`KMSEncryptionKeyArn`].OutputValue' \
  --output text
```

Expected output: `arn:aws:kms:eu-central-1:864899848062:key/a960f907-4d93-49c2-b05f-acc470fcf9cb`

---

## Step 2: Deploy Analysis Stack
Now the analysis stack can get the KMS key from the main stack.

```bash
cd /home/josian/git/fiscalshield-idp-core/stacks/analysis

# Build and deploy analysis stack
sam build
sam deploy --config-env dev
```

**What this does:**
- Uses the KMS key ARN from samconfig.toml (already configured)
- Updates IAM role with correct KMS permissions
- Takes ~3-5 minutes

**Verify:**
```bash
# Test the trigger analysis lambda
aws lambda invoke \
  --function-name fiscalshield-analysis-dev-TriggerAnalysis \
  --payload '{"companyNumber":"12121572","userId":"test-user-id"}' \
  --region eu-central-1 \
  response.json

cat response.json
```

---

## Step 3: Verify End-to-End
Test transaction categorization from the frontend to ensure everything works.

```bash
# Check CloudWatch logs for any KMS errors
aws logs tail /aws/lambda/fiscalshield-analysis-dev-TriggerAnalysis --follow
```

---

## Quick Reference

### Dev Stack Info:
- **Main IDP Stack:** `fiscalshield-idp-dev`
- **Analysis Stack:** `fiscalshield-analysis-dev`
- **ExtractionResults Table:** `fiscalshield-idp-dev-ExtractionResultsTable-ODNDYL7KUECH`
- **KMS Key ARN:** `arn:aws:kms:eu-central-1:864899848062:key/a960f907-4d93-49c2-b05f-acc470fcf9cb`

### If Something Goes Wrong:

**Issue:** Analysis stack deployment fails with "Parameter ExtractionResultsKMSKeyArn is required"
**Fix:** The samconfig.toml already has it configured, but you can manually pass it:
```bash
sam deploy \
  --stack-name fiscalshield-analysis-dev \
  --parameter-overrides \
    Environment=dev \
    ExtractionResultsTableName=fiscalshield-idp-dev-ExtractionResultsTable-ODNDYL7KUECH \
    ExtractionResultsKMSKeyArn=arn:aws:kms:eu-central-1:864899848062:key/a960f907-4d93-49c2-b05f-acc470fcf9cb
```

**Issue:** Main stack output doesn't exist
**Fix:** Main stack needs to be deployed first (Step 1)

---

## Why This Order Matters:

1. ✅ **Main stack first** - Creates the output that analysis stack needs
2. ✅ **Analysis stack second** - Reads from main stack output via parameter
3. ❌ **Wrong order** - Analysis stack would fail because output doesn't exist yet

---

## Changes Summary:

### Main IDP Stack (`template.yaml`):
- Added `KMSEncryptionKeyArn` output (non-breaking change)

### Analysis Stack (`stacks/analysis/template.yaml`):
- Added `ExtractionResultsKMSKeyArn` parameter (required)
- Changed hardcoded KMS key to parameter reference
- Now works across all environments dynamically

### Analysis Dev Config (`stacks/analysis/samconfig.toml`):
- Already configured with correct KMS key ARN for dev

---

## Estimated Total Time: 5-10 minutes
