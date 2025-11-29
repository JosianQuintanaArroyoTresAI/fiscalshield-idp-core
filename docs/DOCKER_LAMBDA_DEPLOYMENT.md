# Docker Lambda Deployment Guide

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

### Option 1: Full Deployment (Recommended)

**When to use:** After any code changes to Pattern 2 functions or `idp_common`

```bash
cd /home/josian/git/fiscalshield-idp-core

# Commit your changes first
git add -A
git commit -m "Your commit message"
git push origin dev

# Run full deployment
./deploy-pattern2-dev.sh
```

**What happens:**
1. CloudFormation packages code
2. Uploads fresh source ZIP to S3 (with new content hash)
3. Triggers CodeBuild with new source
4. Builds Docker images
5. Updates Lambda to use new images

**Time:** ~15-20 minutes

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

## Common Mistakes

### ❌ Mistake 1: Git Push Without Deployment
```bash
git commit -m "Fix boundary detection"
git push origin dev
# Nothing happens! Lambda still runs old code
```

**Why:** Lambda doesn't automatically pull from Git. You need to deploy.

### ❌ Mistake 2: Manual CodeBuild Trigger Before Publishing
```bash
# You made code changes...
aws codebuild start-build --project-name pattern2-docker-build
# CodeBuild uses OLD source ZIP from S3!
```

**Why:** CodeBuild builds from S3, not Git. Must run `publish.py` first.

### ❌ Mistake 3: CodeBuild Success ≠ Lambda Updated
```bash
# CodeBuild completes successfully
# Lambda still runs old image!
```

**Why:** Lambda doesn't automatically update to new image. Must either:
- Run full CloudFormation deployment, OR
- Manually update Lambda image URI

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

## Summary

**The Golden Rule:** After ANY code changes to Pattern 2 functions or `idp_common`, run the full deployment:

```bash
./deploy-pattern2-dev.sh
```

This ensures:
1. Fresh source package created
2. Uploaded to S3
3. CodeBuild triggered automatically
4. Docker images built with latest code
5. Lambda updated to use new images
6. Everything stays in sync

Manual shortcuts only work if you understand the full flow and can verify each step.
