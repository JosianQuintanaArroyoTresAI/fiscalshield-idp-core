# Agent Instructions - READ FIRST

This directory contains critical deployment and development documentation that should be referenced BEFORE attempting common tasks.

## Priority Documents

### 🔴 CRITICAL - Read Before Deploying

1. **[DOCKER_LAMBDA_DEPLOYMENT.md](./DOCKER_LAMBDA_DEPLOYMENT.md)** ⭐
   - **Read this if:** Pattern 2 Lambda code changes aren't deploying
   - **Covers:** Docker Lambda deployment flow, common mistakes, correct workflow
   - **TL;DR:** Always run `publish.py` with `--clean-build` before deploying
   - **Time saved:** Hours of debugging

## Quick Reference Commands

### Pattern 2 Deployment (Classification, OCR, Extraction)
```bash
source activate-env.sh
python publish.py fiscalshield-templates fiscalshield/dev eu-central-1 --clean-build --lint off
./deploy-pattern2-dev.sh
```

### Check if code is deployed
```bash
# Get current Lambda image version
aws lambda get-function \
  --function-name fiscalshield-idp-dev-PATTER-ClassificationFunction-ou0tVZHvC4hP \
  --region eu-central-1 \
  --query 'Code.ImageUri'

# Check CloudWatch logs
aws logs tail "/fiscalshield-idp-dev-PATTERN2STACK-12AZHXIRN6HYB/lambda/ClassificationFunction" \
  --since 5m --region eu-central-1
```

## Common Gotchas

| Problem | Solution | Reference |
|---------|----------|-----------|
| Lambda not reflecting code changes | Run `publish.py --clean-build` then full deploy | [DOCKER_LAMBDA_DEPLOYMENT.md](./DOCKER_LAMBDA_DEPLOYMENT.md) |
| "Git push didn't deploy" | CI/CD only runs on `main` branch, manual deploy needed on `dev` | [DOCKER_LAMBDA_DEPLOYMENT.md](./DOCKER_LAMBDA_DEPLOYMENT.md#mistake-1) |
| CodeBuild uses old code | Must run `publish.py` first to upload new S3 source | [DOCKER_LAMBDA_DEPLOYMENT.md](./DOCKER_LAMBDA_DEPLOYMENT.md#mistake-2) |
| Wrong bucket errors | Use `fiscalshield-templates` not `fiscalshield-dev` | [DOCKER_LAMBDA_DEPLOYMENT.md](./DOCKER_LAMBDA_DEPLOYMENT.md#bucket-configuration-reference) |

## Document Organization

```
.github/AGENT_INSTRUCTIONS/
├── README.md                        # This file
└── DOCKER_LAMBDA_DEPLOYMENT.md      # Symlink to docs/DOCKER_LAMBDA_DEPLOYMENT.md

docs/
├── DOCKER_LAMBDA_DEPLOYMENT.md      # Master copy
├── cicd-quick-reference.md          # CI/CD pipeline reference
├── deployment.md                    # General deployment docs
└── ...other docs...
```

## When to Add Documents Here

Add documents to this directory when:
1. The information would save >1 hour of debugging time
2. The mistake is commonly repeated
3. The workflow is non-obvious or counterintuitive
4. Future AI agents need this context to work effectively

## Maintenance

- Keep documents updated with real examples from production issues
- Include actual commands that worked, not theoretical ones
- Document WHY things work the way they do, not just HOW
- Add timestamps to examples to show they're tested and current
