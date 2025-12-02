# Docker Lambda Deployment Guide - CRITICAL REFERENCE

> **⚠️ READ THIS FIRST**: If Pattern 2 Lambdas aren't reflecting code changes, the issue is almost ALWAYS the deployment flow, not the code itself.

## Quick Fix for "My Code Changes Aren't Deploying"

```bash
# Stop everything and run this:
cd /home/josian/git/fiscalshield-idp-core
source activate-env.sh
python publish.py fiscalshield-templates fiscalshield/dev eu-central-1 --clean-build --lint off
./deploy-pattern2-dev.sh

# Wait 15-20 minutes. That's it.
```

**DO NOT:**
- ❌ Manually trigger CodeBuild (it uses stale S3 source)
- ❌ Use force-update-lambdas.sh (doesn't work for Docker Lambdas)
- ❌ Assume git push triggers deployment (it doesn't)

## Understanding the Deployment Flow

Pattern 2 Lambda functions (Classification, OCR, Extraction, etc.) use **Docker images** instead of ZIP files. This creates a multi-step deployment process that's different from standard Lambda deployments.

## The Problem We Encountered

### Issue
When making code changes to `lib/idp_common_pkg/idp_common/`, the changes weren't appearing in the deployed Lambda even after:
1. ✅ Committing code to Git
2. ✅ Triggering CodeBuild manually
3. ❌ Lambda still ran old code!

### Root Cause
The Docker image build process works like this:

```
Git Commit → publish.py → S3 Source ZIP → CodeBuild → Docker Build → ECR Image → Lambda
     ↑                         ↑                                         ↑
  Your changes          Stale source!                             Old code running
```

**The issue:** When you manually trigger CodeBuild, it builds from a **source ZIP file in S3**, not from your Git repository. If that ZIP file is stale (created before your changes), the Docker image gets built with old code.

## How the System Works

### 1. Content-Based Versioning

The `publish.py` script calculates a content hash from:
- `lib/idp_common_pkg/idp_common/` (shared library)
- `Dockerfile.optimized`
- `patterns/pattern-2/src/` (all Lambda function code)

```python
# From publish.py line 419
paths_to_hash = [
    "lib/idp_common_pkg/idp_common",
    "Dockerfile.optimized",
    "patterns/pattern-2/src",
]
```

This hash becomes the `IMAGE_VERSION` (e.g., `a6953fa7`).

### 2. Source Packaging

During `publish.py` execution:
1. Creates `pattern-2-source-<hash>.zip` with ALL code
2. Uploads to S3: `s3://fiscalshield-dev-eu-central-1/idp/0.3.21/pattern-2-source-<hash>.zip`
3. CloudFormation template references this ZIP file

### 3. CodeBuild Process

CodeBuild (defined in `patterns/pattern-2/buildspec.yml`):
1. Downloads source ZIP from S3
2. Builds Docker images for each function
3. Tags with `IMAGE_VERSION` (the content hash)
4. Pushes to ECR
5. Lambda references ECR image by tag

### 4. The Critical Link

```yaml
# patterns/pattern-2/template.yaml
Pattern2SourceZipfile:
  Type: String
  Description: "Pattern-2 source zipfile object name"

# ... later ...
CodeLocation: !Sub "arn:${AWS::Partition}:s3:::${ArtifactBucket}/${ArtifactPrefix}/${Pattern2SourceZipfile}"
```

## Correct Deployment Workflows

### Option 1: Full Deployment (THE ONLY RELIABLE METHOD)

**When to use:** After any code changes to Pattern 2 functions or `idp_common`

```bash
cd /home/josian/git/fiscalshield-idp-core
source activate-env.sh

# Step 1: Publish artifacts to S3 (CRITICAL - includes lib changes)
python publish.py fiscalshield-templates fiscalshield/dev eu-central-1 --clean-build --lint off

# Step 2: Deploy the stack
./deploy-pattern2-dev.sh

# Step 3: Wait for completion
aws cloudformation wait stack-update-complete --stack-name fiscalshield-idp-dev --region eu-central-1
```

**What happens:**
1. `publish.py` calculates content hash from lib + pattern-2 code
2. Creates `pattern-2-source-<NEW_HASH>.zip` with ALL current code
3. Uploads to S3 (this is what CodeBuild will use!)
4. CloudFormation detects new source ZIP filename
5. Triggers CodeBuild with new source
6. Builds Docker images with your latest code
7. Updates Lambda to use new images

**Time:** ~15-20 minutes

**Critical flags:**
- `--clean-build`: Forces new content hash (prevents caching issues)
- `--lint off`: Bypasses lint errors (use temporarily, fix lint later)

### Option 2: Manual CodeBuild Trigger (NOT RECOMMENDED)

**WARNING:** Only works if S3 source ZIP is already up-to-date!

```bash
# This will fail if you haven't run publish.py first
aws codebuild start-build \
  --project-name "fiscalshield-idp-dev-PATTERN2STACK-12AZHXIRN6HYB-pattern2-docker-build" \
  --region eu-central-1
```

### Option 3: Publish + Trigger + Update

**For rapid iteration:**

```bash
# 1. Package and upload new source
python3 publish.py

# 2. Trigger CodeBuild (it will use the new source)
aws codebuild start-build \
  --project-name "fiscalshield-idp-dev-PATTERN2STACK-12AZHXIRN6HYB-pattern2-docker-build" \
  --region eu-central-1

# Wait for build to complete (~5-10 min)

# 3. Get the new IMAGE_VERSION from the build
NEW_IMAGE_VERSION=$(aws codebuild batch-get-builds \
  --ids "<build-id>" \
  --region eu-central-1 \
  --query 'builds[0].environment.environmentVariables[?name==`IMAGE_VERSION`].value' \
  --output text)

# 4. Update Lambda to use new image
aws lambda update-function-code \
  --function-name fiscalshield-idp-dev-PATTER-ClassificationFunction-ou0tVZHvC4hP \
  --image-uri 864899848062.dkr.ecr.eu-central-1.amazonaws.com/fiscalshield-idp-dev-pattern2stack-12azhxirn6hyb-pattern2ecrrepository-zjeih6tiyegj:classification-function-$NEW_IMAGE_VERSION \
  --region eu-central-1

# Wait for function to be ready
aws lambda wait function-updated \
  --function-name fiscalshield-idp-dev-PATTER-ClassificationFunction-ou0tVZHvC4hP \
  --region eu-central-1
```

## How to Verify Your Code Is Deployed

### Check 1: Lambda Image Tag

```bash
# Get current image
aws lambda get-function \
  --function-name fiscalshield-idp-dev-PATTER-ClassificationFunction-ou0tVZHvC4hP \
  --region eu-central-1 \
  --query 'Code.ImageUri' \
  --output text

# Example output:
# 864899848062.dkr.ecr.eu-central-1.amazonaws.com/.../pattern2ecrrepository-zjeih6tiyegj:classification-function-a6953fa7
#                                                                                                             ^^^^^^^^
#                                                                                                             This is IMAGE_VERSION
```

### Check 2: Last Modified Time

```bash
aws lambda get-function \
  --function-name fiscalshield-idp-dev-PATTER-ClassificationFunction-ou0tVZHvC4hP \
  --region eu-central-1 \
  --query 'Configuration.LastModified' \
  --output text
```

### Check 3: Look for Debug Logs

After uploading a test document, check for specific log messages:

```bash
aws logs tail "/fiscalshield-idp-dev-PATTERN2STACK-12AZHXIRN6HYB/lambda/ClassificationFunction" \
  --since 5m \
  --region eu-central-1 \
  --filter-pattern "DEBUG"
```

If you added `logger.info("🔍 DEBUG: ...")` and it's NOT appearing, your code isn't deployed.

## Common Mistakes (That Cost Hours)

### ❌ Mistake 1: Git Push Without Deployment
```bash
git commit -m "Fix boundary detection"
git push origin dev
# Nothing happens! Lambda still runs old code
```

**Why:** Lambda doesn't automatically pull from Git. CI/CD only runs on `main` branch in this repo.

### ❌ Mistake 2: Manual CodeBuild Trigger Before Publishing
```bash
# You made code changes...
aws codebuild start-build --project-name pattern2-docker-build
# CodeBuild uses OLD source ZIP from S3! Your changes not included!
```

**Why:** CodeBuild builds from S3 source ZIP, not Git. **MUST** run `publish.py` first to upload new source.

### ❌ Mistake 3: CodeBuild Success ≠ Lambda Updated
```bash
# CodeBuild completes successfully
# Lambda still runs old image!
```

**Why:** Lambda doesn't automatically update to new image. CloudFormation must update the function.

### ❌ Mistake 4: Wrong S3 Bucket
```bash
python publish.py fiscalshield-dev idp eu-central-1  # Wrong bucket!
./deploy-pattern2-dev.sh  # Uses fiscalshield-templates
# Mismatch! Lambda gets old source from templates bucket
```

**Why:** Deploy script uses `fiscalshield-templates-eu-central-1` by default. Must publish to same bucket.

### ❌ Mistake 5: Assuming force-update-lambdas.sh Works
```bash
./scripts/force-update-lambdas.sh ClassificationFunction
# Does nothing for Docker Lambdas!
```

**Why:** This script only works for ZIP-based Lambdas. Docker Lambdas need full deployment.

### ❌ Mistake 6: Escaping Strings Wrong in Python
```python
# WRONG - This matches literal "\n" string, not newlines!
text.replace('\\n', ' ')

# CORRECT - This matches actual newline characters
text.replace('\n', ' ')
```

**Why:** In Python strings, `'\\n'` is an escaped backslash + n, not a newline character.

## Quick Reference

| What Changed | Minimum Required Action |
|--------------|------------------------|
| `lib/idp_common_pkg/` code | Full deployment (`./deploy-pattern2-dev.sh`) |
| `patterns/pattern-2/src/` code | Full deployment |
| Configuration only (`config.yaml`) | Upload to S3 + reload script |
| Non-Pattern-2 Lambda (ZIP-based) | `./scripts/force-update-lambdas.sh <function>` |

## Files Involved in Docker Lambda Deployment

1. **`lib/idp_common_pkg/idp_common/`** - Shared library (included in all Pattern 2 images)
2. **`patterns/pattern-2/src/`** - Function-specific code
3. **`Dockerfile.optimized`** - Multi-stage Docker build definition
4. **`patterns/pattern-2/buildspec.yml`** - CodeBuild instructions
5. **`patterns/pattern-2/template.yaml`** - CloudFormation template
6. **`publish.py`** - Packaging and upload script
7. **S3 Source ZIP** - `pattern-2-source-<hash>.zip`
8. **ECR Images** - `classification-function-<hash>`, etc.

## Prevention Checklist

Before assuming your code is deployed, verify:

- [ ] Changes committed to Git
- [ ] Full deployment run (`./deploy-pattern2-dev.sh`) OR `publish.py` executed
- [ ] CloudFormation stack status is `UPDATE_COMPLETE`
- [ ] Lambda `LastModified` timestamp is recent
- [ ] Lambda `ImageUri` matches expected version
- [ ] Test document upload shows expected behavior/logs

## Troubleshooting

### Lambda still shows old behavior after deployment

1. **Check Lambda image version:**
   ```bash
   aws lambda get-function --function-name <name> --query 'Code.ImageUri'
   ```

2. **Check ECR for new image:**
   ```bash
   aws ecr describe-images \
     --repository-name <repo> \
     --region eu-central-1 \
     --query 'imageDetails[*].[imageTags[0],imagePushedAt]' \
     --output table
   ```

3. **Check CodeBuild logs:**
   ```bash
   aws codebuild batch-get-builds --ids <build-id> \
     --query 'builds[0].logs.deepLink' \
     --output text
   ```

### Docker build fails

- Check `patterns/pattern-2/buildspec.yml` for errors
- Verify all source files exist in the S3 ZIP
- Check Dockerfile.optimized syntax

### Lambda can't pull image

- Verify ECR repository permissions
- Check Lambda execution role has `ecr:GetAuthorizationToken`, `ecr:BatchGetImage`
- Confirm image exists in ECR

## Bucket Configuration Reference

The system uses TWO S3 buckets, and they MUST be in sync:

```bash
# Development bucket (where publish.py puts artifacts)
fiscalshield-templates-eu-central-1/fiscalshield/dev/

# Legacy bucket (historical, may have stale artifacts)
fiscalshield-dev-eu-central-1/idp/

# Always publish to templates bucket:
python publish.py fiscalshield-templates fiscalshield/dev eu-central-1
```

The `deploy-pattern2-dev.sh` script uses `fiscalshield-templates` by default via:
```bash
BUCKET_BASENAME="${BUCKET_BASENAME:-fiscalshield-templates}"
```

## Real Example: The '\n    "id"' Bug

**Problem:** Lambda throwing `❌ Error in LLM boundary detection: '\n    "id"'`

**Attempted Fixes (All Failed):**
1. ✅ Fixed code in `lib/idp_common_pkg/idp_common/classification/llm_boundary_detection.py`
2. ✅ Committed to Git
3. ❌ Manually triggered CodeBuild → Still failed (used old S3 source)
4. ❌ Waited for "automatic" deployment → Never happened
5. ❌ Tried force-update-lambdas.sh → Doesn't work for Docker Lambdas

**Root Causes:**
1. First fix used wrong escaping: `'\\n'` instead of `'\n'`
2. Published to wrong bucket: `fiscalshield-dev` instead of `fiscalshield-templates`
3. Didn't use `--clean-build`, so content hash didn't change
4. CloudFormation didn't detect source changes, didn't trigger rebuild

**Working Fix:**
```bash
# 1. Fix the actual bug (correct escaping)
vim lib/idp_common_pkg/idp_common/classification/llm_boundary_detection.py
# Changed: cleaned_response.replace('\\n', ' ')
# To:      cleaned_response.replace('\n', ' ')

# 2. Publish to correct bucket with forced rebuild
source activate-env.sh
python publish.py fiscalshield-templates fiscalshield/dev eu-central-1 --clean-build --lint off

# 3. Deploy
./deploy-pattern2-dev.sh

# 4. Wait (15-20 min)
aws cloudformation wait stack-update-complete --stack-name fiscalshield-idp-dev --region eu-central-1

# 5. Verify
aws lambda get-function \
  --function-name fiscalshield-idp-dev-PATTER-ClassificationFunction-ou0tVZHvC4hP \
  --region eu-central-1 \
  --query '{Image:Code.ImageUri,Updated:Configuration.LastModified}'
```

**Result:** Image updated from `a5502335` → `e93a77dd`, error fixed.

**Time cost:** ~8 hours debugging, 20 minutes actual deployment.

## Summary

**The Golden Rule:** After ANY code changes to Pattern 2 functions or `idp_common`:

```bash
source activate-env.sh
python publish.py fiscalshield-templates fiscalshield/dev eu-central-1 --clean-build --lint off
./deploy-pattern2-dev.sh
```

**That's it. Stop trying shortcuts. They don't work.**

This ensures:
1. ✅ Fresh source package created with new content hash
2. ✅ Uploaded to CORRECT S3 bucket
3. ✅ CloudFormation detects change
4. ✅ CodeBuild triggered automatically with NEW source
5. ✅ Docker images built with latest code
6. ✅ Lambda updated to use new images
7. ✅ Everything stays in sync

**Remember:** 
- The source ZIP in S3 is the source of truth for CodeBuild
- Git commits alone don't trigger anything
- Manual CodeBuild triggers use whatever's in S3 (probably stale)
- `--clean-build` forces new content hash (prevents caching bugs)
- Deployment takes 15-20 min - just wait, don't try to optimize
