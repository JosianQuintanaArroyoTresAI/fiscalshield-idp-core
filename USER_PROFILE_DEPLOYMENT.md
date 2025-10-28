# User Profile Table - Quick Deployment Reference

## Pre-Deployment Checklist

✅ UserProfileTable added to template.yaml
✅ RegisterUserCompany Lambda created
✅ ListUserCompanies Lambda updated
✅ GraphQL schema updated
✅ Frontend GraphQL mutation created
✅ Frontend service function added
✅ CompanySelect component updated

## Deployment Commands

### 1. Build and Deploy Backend

```bash
# From project root
sam build

# Deploy to dev environment
sam deploy --config-env dev --no-confirm-changeset

# Or use the shortcut
./deploy-pattern2-dev.sh
```

### 2. Build and Deploy Frontend

The frontend will be built and deployed automatically by the CDN stack during SAM deployment.

If you need to manually rebuild the frontend:

```bash
cd src/ui
npm run build
```

## Post-Deployment Verification

### 1. Check CloudFormation Stack

```bash
aws cloudformation describe-stacks \
  --stack-name fiscalshield-idp-dev \
  --query 'Stacks[0].StackStatus'
```

Expected: `UPDATE_COMPLETE`

### 2. Verify UserProfileTable Exists

```bash
aws dynamodb describe-table \
  --table-name fiscalshield-idp-dev-UserProfileTable
```

### 3. Check Lambda Functions

```bash
# RegisterUserCompanyFunction
aws lambda get-function \
  --function-name fiscalshield-idp-dev-RegisterUserCompanyFunction

# ListUserCompaniesFunction (updated)
aws lambda get-function \
  --function-name fiscalshield-idp-dev-ListUserCompaniesFunction
```

### 4. Test GraphQL Mutation

Navigate to AppSync console or use the AWS CLI:

```bash
# Get your AppSync endpoint
aws appsync list-graphql-apis \
  --query 'graphqlApis[?name==`fiscalshield-idp-dev-api`].{endpoint:uris.GRAPHQL}' \
  --output text
```

Then test the mutation in the AppSync console:

```graphql
mutation {
  registerUserCompany(
    companyNumber: "00000006"
    companyName: "TESCO PLC"
  )
}
```

Expected: `{ "data": { "registerUserCompany": true } }`

### 5. Verify in DynamoDB Console

Check UserProfileTable for new entries:
- PK: `cognito-userId`
- SK: `COMPANY#00000006`

### 6. Test End-to-End Flow

1. **Login to the UI**
   - Navigate to your CloudFront URL
   - Login with Cognito credentials

2. **Search and Register Company**
   - On landing page, search for "Tesco"
   - Select company from results
   - Click "Confirm and Research"

3. **Verify Persistence**
   - Check DynamoDB console for new entry
   - Log out
   - Log back in
   - **Expected**: Company card appears on landing page

4. **Test Document Count**
   - Click on company card to view documents
   - Upload a test document
   - Return to landing page
   - **Expected**: Document count increments on card

## Troubleshooting

### Issue: Company card doesn't appear after login

**Check 1**: UserProfileTable entry exists
```bash
aws dynamodb query \
  --table-name fiscalshield-idp-dev-UserProfileTable \
  --key-condition-expression "PK = :userId" \
  --expression-attribute-values '{":userId":{"S":"YOUR_COGNITO_USER_ID"}}'
```

**Check 2**: ListUserCompaniesFunction logs
```bash
aws logs tail /aws/lambda/fiscalshield-idp-dev-ListUserCompaniesFunction --follow
```

**Check 3**: Browser console for GraphQL errors
- Open browser DevTools → Console
- Look for `getUserCompanies` query errors

### Issue: RegisterUserCompany mutation fails

**Check 1**: Lambda execution logs
```bash
aws logs tail /aws/lambda/fiscalshield-idp-dev-RegisterUserCompanyFunction --follow
```

**Check 2**: IAM permissions
```bash
aws iam get-role-policy \
  --role-name fiscalshield-idp-dev-RegisterUserCompanyFunctionRole-xxx \
  --policy-name DynamoDBWritePolicy
```

**Check 3**: Cognito identity in request
- Ensure user is authenticated
- Check AppSync request headers for `Authorization`

### Issue: Document counts don't update

**Check 1**: TrackingTable has CompanyNumber
```bash
aws dynamodb scan \
  --table-name fiscalshield-idp-dev-TrackingTable \
  --filter-expression "attribute_exists(CompanyNumber)" \
  --limit 5
```

**Check 2**: GSI1 index exists
```bash
aws dynamodb describe-table \
  --table-name fiscalshield-idp-dev-TrackingTable \
  --query 'Table.GlobalSecondaryIndexes[?IndexName==`GSI1`]'
```

### Issue: CORS errors in browser

**Check**: AppSync CORS configuration in template.yaml
- Should allow your CloudFront domain
- Check browser Network tab for preflight OPTIONS requests

## Rollback Plan

If deployment causes issues:

### Option 1: Rollback CloudFormation Stack
```bash
aws cloudformation cancel-update-stack \
  --stack-name fiscalshield-idp-dev

# Or rollback to previous version
aws cloudformation continue-update-rollback \
  --stack-name fiscalshield-idp-dev
```

### Option 2: Remove New Resources
The new resources are non-breaking. Existing functionality still works because:
- localStorage fallback in CompanySelect.jsx
- ListUserCompanies falls back to empty array if table missing
- RegisterUserCompany errors are caught and logged

To remove:
1. Comment out UserProfileTable and RegisterUserCompany resources in template.yaml
2. Redeploy
3. Frontend will continue using localStorage

## Performance Monitoring

### CloudWatch Metrics to Watch

1. **UserProfileTable Metrics**
   - ConsumedReadCapacityUnits
   - ConsumedWriteCapacityUnits
   - UserErrors (should be 0)

2. **Lambda Metrics**
   - RegisterUserCompanyFunction:
     - Invocations
     - Duration
     - Errors
   - ListUserCompaniesFunction:
     - Invocations
     - Duration
     - Throttles

3. **AppSync Metrics**
   - registerUserCompany mutation:
     - 4xx errors (client errors)
     - 5xx errors (server errors)
     - Latency

### Set Up Alarms

```bash
# Example: Alert on RegisterUserCompany errors
aws cloudwatch put-metric-alarm \
  --alarm-name RegisterUserCompanyErrors \
  --alarm-description "Alert on RegisterUserCompany Lambda errors" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=FunctionName,Value=fiscalshield-idp-dev-RegisterUserCompanyFunction
```

## Cost Estimates

**New Monthly Costs** (assuming 1000 users, 10 companies each):

- **UserProfileTable**:
  - Storage: 10,000 items × 1KB = 10MB = ~$0.25/month
  - Reads: 1000 logins × 1 query = 1000 RCU = ~$0.00025/month
  - Writes: 100 new registrations = 100 WCU = ~$0.00125/month

- **RegisterUserCompanyFunction**:
  - 100 invocations/month × 512MB × 100ms = ~$0.00002/month

- **ListUserCompaniesFunction** (updated):
  - 1000 invocations/month × 512MB × 500ms = ~$0.00104/month

**Total Additional Cost**: ~$0.26/month

## Documentation References

- [USER_PROFILE_IMPLEMENTATION.md](./USER_PROFILE_IMPLEMENTATION.md) - Full implementation details
- [COMPANY_ISOLATION_IMPLEMENTATION.md](./COMPANY_ISOLATION_IMPLEMENTATION.md) - Company metadata flow
- [GDPR Compliance Guide] - (TODO: Create comprehensive GDPR documentation)

## Success Criteria

After deployment, verify:

✅ UserProfileTable exists in DynamoDB
✅ RegisterUserCompany mutation works in AppSync console
✅ Company registration creates entry in UserProfileTable
✅ Company cards persist across login sessions
✅ Document counts display correctly on cards
✅ Multiple companies can be registered
✅ No errors in CloudWatch logs
✅ No increase in user-reported issues

## Next Steps

Once deployed and verified:

1. Monitor for 24-48 hours
2. Gather user feedback on company card functionality
3. Implement GDPR deletion endpoint
4. Add user preferences to UserProfileTable
5. Consider adding company logo/branding
6. Add analytics for company usage patterns
