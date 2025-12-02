# Deployment Guide

## Quick Deploy (Development)

```bash
# Complete deployment (recommended)
./scripts/deploy-dev-complete.sh

# Lambda-only updates (fast iteration)
./scripts/force-update-lambdas.sh
```

**Time:** 30 seconds (Lambda only) to 10 minutes (full deployment)

---

## Production Deployment

### 1. Create Pull Request

**GitHub Web UI** (Recommended):
1. Go to: https://github.com/JosianQuintanaArroyoTresAI/fiscalshield-idp-core/compare/main...dev
2. Click "Create pull request"
3. Title: Release summary (e.g., "Core Architecture Complete")
4. Add description with changes
5. Click "Create pull request"

**GitHub CLI**:
```bash
gh pr create --base main --head dev --title "Release: [Summary]" --body "Description"
```

### 2. Wait for PR Validation

GitHub Actions automatically runs:
- Python linting (ruff)
- Test suite with coverage
- CloudFormation validation
- UI checks

**Time:** 5-10 minutes

### 3. Merge PR

- Review all checks are green ✅
- Click "Merge pull request"
- Confirm merge

### 4. Deploy to Production

**Via GitHub Actions**:
1. Go to: https://github.com/JosianQuintanaArroyoTresAI/fiscalshield-idp-core/actions
2. Click "Deploy to Production"
3. Click "Run workflow"
4. Type: `DEPLOY`
5. Click "Run workflow"

**Monitor:**
- GitHub Actions: Progress logs
- CloudFormation: https://console.aws.amazon.com/cloudformation
- **Time:** 15-20 minutes

### 5. Post-Deployment Setup

```bash
# Get User Pool ID
USER_POOL_ID=$(aws cloudformation describe-stack-resource \
  --stack-name fiscalshield-idp-prod \
  --logical-resource-id CognitoUserPool \
  --region eu-central-1 \
  --query 'StackResourceDetail.PhysicalResourceId' \
  --output text)

# Create Cognito Groups
aws cognito-idp create-group \
  --user-pool-id $USER_POOL_ID \
  --group-name Admin \
  --description "System administrators" \
  --precedence 0 \
  --region eu-central-1

aws cognito-idp create-group \
  --user-pool-id $USER_POOL_ID \
  --group-name Users \
  --description "Regular users" \
  --precedence 1 \
  --region eu-central-1

# Assign admin user
ADMIN_EMAIL="josian@protonmail.com"
aws cognito-idp admin-add-user-to-group \
  --user-pool-id $USER_POOL_ID \
  --username $ADMIN_EMAIL \
  --group-name Admin \
  --region eu-central-1
```

### 6. Smoke Test Checklist

- [ ] CloudFormation status: `UPDATE_COMPLETE`
- [ ] Cognito groups exist (Admin, Users)
- [ ] Admin user can login
- [ ] Document upload works
- [ ] Processing completes successfully
- [ ] No errors in CloudWatch logs (15 minutes)

---

## Development Scenarios

### Daily Development
```bash
# After any code changes
./scripts/deploy-dev-complete.sh
```

### Fast Lambda Iteration
```bash
# Make Lambda code changes, then:
./scripts/force-update-lambdas.sh

# Update specific functions:
./scripts/force-update-lambdas.sh upload_resolver queue_sender
```

### Infrastructure Changes Only
```bash
# If you only changed template.yaml
./deploy-pattern2-dev.sh
```

### Test Build Without Deploying
```bash
./scripts/publish-dev.sh
```

---

## Rollback Plan

### Quick Rollback (Production)

```bash
# Via Git
git checkout main
git revert -m 1 HEAD
git push origin main

# Then re-run GitHub Actions deployment
```

### CloudFormation Rollback

```bash
# Get previous template from S3
aws s3 ls s3://fiscalshield-prod-eu-central-1/idp/ --recursive --human-readable

# Update stack with previous template
aws cloudformation update-stack \
  --stack-name fiscalshield-idp-prod \
  --template-url https://s3.eu-central-1.amazonaws.com/fiscalshield-prod-eu-central-1/idp/idp-main-PREVIOUS-VERSION.yaml \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND \
  --region eu-central-1
```

---

## Troubleshooting

### "Docker daemon not running"
```bash
sudo systemctl start docker  # Linux
# Or start Docker Desktop on Mac/Windows
```

### "Stack in ROLLBACK_COMPLETE"
```bash
aws cloudformation delete-stack --stack-name fiscalshield-idp-dev --region eu-central-1
aws cloudformation wait stack-delete-complete --stack-name fiscalshield-idp-dev --region eu-central-1
./scripts/deploy-dev-complete.sh
```

### "No changes detected" but code changed
```bash
# Force Lambda update
./scripts/force-update-lambdas.sh
```

### Verify Deployment
```bash
# Check stack status
aws cloudformation describe-stacks --stack-name fiscalshield-idp-dev --region eu-central-1

# Watch logs
aws logs tail /aws/lambda/fiscalshield-idp-dev-UploadResolverFunction-* --follow
```

---

## Monitoring

```bash
# CloudFormation Console
https://console.aws.amazon.com/cloudformation/home?region=eu-central-1

# Check specific Lambda logs
aws logs tail /aws/lambda/fiscalshield-idp-dev-FUNCTION-NAME --follow

# List all Lambda functions in stack
aws cloudformation describe-stack-resources \
  --stack-name fiscalshield-idp-dev \
  --region eu-central-1 \
  --query 'StackResources[?ResourceType==`AWS::Lambda::Function`].PhysicalResourceId'
```

---

## Time Estimates

| Operation | Duration | When to Use |
|-----------|----------|-------------|
| `deploy-dev-complete.sh` | 5-10 min | Full deployment |
| `force-update-lambdas.sh` | 30 sec | Lambda code only |
| Production deployment | 15-20 min | Release to prod |
| Post-deployment setup | 2-3 min | Initial prod setup |

---

## Best Practices

✅ **DO:**
- Use `deploy-dev-complete.sh` for most deployments
- Use `force-update-lambdas.sh` for rapid Lambda iteration
- Test in dev before deploying to prod
- Monitor logs after deployment

❌ **DON'T:**
- Deploy to prod without PR validation
- Skip smoke tests after production deployment
- Modify Lambda code directly in AWS console

---

## Additional Resources

- **CI/CD Setup:** `docs/cicd/CICD_SETUP.md`
- **Configuration Reload:** `docs/cicd/CONFIGURATION_RELOAD_GUIDE.md`
- **Scripts README:** `scripts/README.md`
- **Deployment History:** `docs/archive/deployment-history/`
