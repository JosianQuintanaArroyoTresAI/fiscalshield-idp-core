# Pattern 2 Deployment Checklist

Use this checklist for ANY code changes to Pattern 2 Lambda functions.

## Pre-Deployment

- [ ] Code changes made to `lib/idp_common_pkg/idp_common/` or `patterns/pattern-2/src/`
- [ ] Changes tested locally if possible
- [ ] Virtual environment activated: `source activate-env.sh`

## Deployment Steps

- [ ] **Step 1:** Publish artifacts
  ```bash
  python publish.py fiscalshield-templates fiscalshield/dev eu-central-1 --clean-build --lint off
  ```
  - `--clean-build` forces new content hash
  - `--lint off` bypasses lint errors temporarily

- [ ] **Step 2:** Verify upload
  ```bash
  aws s3 ls s3://fiscalshield-templates-eu-central-1/fiscalshield/dev/0.3.21/ | grep pattern-2-source | tail -1
  ```
  - Check timestamp is recent (within last few minutes)
  - Note the new hash (e.g., `pattern-2-source-e93a77dd.zip`)

- [ ] **Step 3:** Deploy stack
  ```bash
  ./deploy-pattern2-dev.sh
  ```

- [ ] **Step 4:** Wait for completion (15-20 minutes)
  ```bash
  aws cloudformation wait stack-update-complete --stack-name fiscalshield-idp-dev --region eu-central-1
  ```

## Post-Deployment Verification

- [ ] **Check Lambda image version**
  ```bash
  aws lambda get-function \
    --function-name fiscalshield-idp-dev-PATTER-ClassificationFunction-ou0tVZHvC4hP \
    --region eu-central-1 \
    --query 'Code.ImageUri' --output text
  ```
  - Image tag should match new hash
  - Example: `classification-function-e93a77dd`

- [ ] **Check Last Modified timestamp**
  ```bash
  aws lambda get-function \
    --function-name fiscalshield-idp-dev-PATTER-ClassificationFunction-ou0tVZHvC4hP \
    --region eu-central-1 \
    --query 'Configuration.LastModified' --output text
  ```
  - Should be within last 30 minutes

- [ ] **Test with actual document upload**
  - Upload test document via UI
  - Check CloudWatch logs for expected behavior
  
- [ ] **Check CloudWatch logs**
  ```bash
  aws logs tail "/fiscalshield-idp-dev-PATTERN2STACK-12AZHXIRN6HYB/lambda/ClassificationFunction" \
    --since 5m --region eu-central-1 --follow
  ```

## Troubleshooting

If Lambda still shows old behavior:

- [ ] Verify correct bucket used: `fiscalshield-templates-eu-central-1`
- [ ] Check Pattern 2 nested stack parameters:
  ```bash
  aws cloudformation describe-stacks \
    --stack-name fiscalshield-idp-dev-PATTERN2STACK-12AZHXIRN6HYB \
    --region eu-central-1 \
    --query 'Stacks[0].Parameters[?ParameterKey==`Pattern2SourceZipfile`]'
  ```
- [ ] Re-run with `--clean-build` to force new hash
- [ ] Check CodeBuild logs for build errors

## Common Mistakes to Avoid

- ❌ Don't manually trigger CodeBuild (uses stale S3 source)
- ❌ Don't use `force-update-lambdas.sh` (doesn't work for Docker)
- ❌ Don't publish to `fiscalshield-dev` bucket (wrong bucket)
- ❌ Don't skip `--clean-build` (may reuse old hash)
- ❌ Don't expect git push to trigger deployment (only on main branch)

## Time Estimates

- Publishing: ~2-3 minutes
- Deployment: ~15-20 minutes
- Total: ~20-25 minutes

**Set a timer and do something else. Don't try to optimize or shortcut the process.**
