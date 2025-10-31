# Force UI Rebuild - Quick Reference

## Problem
Sometimes the UI doesn't rebuild properly during deployment, causing:
- Old JavaScript code to be served even after pushing changes
- Browser cache issues
- CloudFront serving stale content

## Solution: Force UI Rebuild Script

### Quick Command
```bash
./scripts/force-rebuild-ui.sh
```

Or with custom stack/region:
```bash
./scripts/force-rebuild-ui.sh fiscalshield-idp-dev eu-central-1
```

### What It Does
1. ✅ Clears all local build caches (`build/`, `node_modules/.cache/`, `.cache/`)
2. ✅ Runs clean npm install (`npm ci`)
3. ✅ Builds UI with no cache (`CI=true npm run build`)
4. ✅ Uploads to S3 with proper cache headers
5. ✅ Creates CloudFront invalidation
6. ✅ Waits for invalidation to complete

### When to Use
- After pushing UI changes that don't appear in the deployed app
- When browser shows old code after hard refresh
- When you need to force a clean UI build locally before deployment
- During troubleshooting of UI-related issues

## Automatic Prevention

### GitHub Actions Changes
The deployment workflow now includes:

1. **Pre-build cache clearing** (line ~75):
   ```yaml
   - name: Force clean UI build (clear all caches)
     run: |
       cd src/ui
       rm -rf node_modules/.cache build .cache dist
   ```

2. **Environment variables for clean builds**:
   ```yaml
   env:
     CI: true
     GENERATE_SOURCEMAP: false
   ```

3. **Post-deployment verification** (line ~118):
   - Checks S3 bucket for recent file timestamps
   - Warns if UI files weren't updated

### Manual Verification After Deployment

1. **Check S3 directly**:
   ```bash
   aws s3 ls s3://fiscalshield-idp-dev-webuibucket-*/static/js/ --recursive | grep main | tail -5
   ```
   Look for recent timestamps (within last 5-10 minutes)

2. **Check CloudFront invalidations**:
   ```bash
   aws cloudfront list-invalidations --distribution-id E2WCI3ZY73T3GV --max-items 3
   ```

3. **Verify in browser**:
   - Open DevTools (F12)
   - Network tab
   - Disable cache checkbox
   - Hard refresh (Ctrl+Shift+R)
   - Check `main.*.js` file timestamp in response headers

## Comparison: Lambda vs UI Force Updates

| Aspect | Force Update Lambdas | Force Rebuild UI |
|--------|---------------------|------------------|
| **What it updates** | Lambda function code | React UI bundle |
| **Storage** | Lambda service | S3 + CloudFront |
| **Cache location** | CloudFormation + Lambda | npm + browser + CloudFront |
| **Update speed** | ~30-60 seconds | ~2-3 minutes |
| **When needed** | Lambda code not updated by CFN | UI changes not appearing |
| **Script** | `force-update-lambdas.sh` | `force-rebuild-ui.sh` |

## Troubleshooting

### Issue: Script can't find WebUI bucket
**Fix**: Manually specify bucket name
```bash
WEBUI_BUCKET=fiscalshield-idp-dev-webuibucket-xyz ./scripts/force-rebuild-ui.sh
```

### Issue: CloudFront invalidation not working
**Fix**: Manually invalidate
```bash
aws cloudfront create-invalidation \
  --distribution-id E2WCI3ZY73T3GV \
  --paths "/*"
```

### Issue: Browser still showing old code
**Fix**: Clear all browser data
1. DevTools → Application tab
2. Clear storage → Clear site data
3. Close all tabs
4. Open in new incognito window

## Best Practices

### For Developers
1. ✅ Always hard refresh after UI deployments (Ctrl+Shift+R)
2. ✅ Use incognito mode for testing new deployments
3. ✅ Check DevTools Network tab for file timestamps
4. ✅ If in doubt, run `./scripts/force-rebuild-ui.sh`

### For CI/CD
1. ✅ Cache clearing step now runs automatically
2. ✅ Verification step checks file timestamps
3. ✅ Failed builds are more visible
4. ⚠️ Consider adding Slack/email notifications for failed UI builds

## Files Changed
- `.github/workflows/deploy-dev.yml` - Added cache clearing and verification steps
- `scripts/force-rebuild-ui.sh` - New script for manual force rebuilds

## Related Issues
- GraphQL mutation format inconsistency (fixed: `registerUserCompany.js`)
- UI not showing registered companies (root cause: old cached code)
