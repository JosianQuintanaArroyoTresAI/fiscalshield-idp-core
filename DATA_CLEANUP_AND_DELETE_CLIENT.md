# Data Cleanup & Delete Client Feature

## Summary

Two new capabilities added to FiscalShield IDP:

1. **Database Cleanup Script** - Remove dirty data from old deployments
2. **Delete Client Button** - Allow users to remove companies from their list

---

## 1. Database Cleanup Script ✅

### Location
`/scripts/cleanup_company_data.py`

### Purpose
Safely remove all company data from DynamoDB tables to start fresh after old deployments with incompatible schemas.

### Usage

**Dry Run (Safe - See What Would Be Deleted):**
```bash
python3 scripts/cleanup_company_data.py --environment dev --dry-run
```

**Actually Clean Data:**
```bash
python3 scripts/cleanup_company_data.py --environment dev
```

### What Gets Deleted
- **Data Collection Stack**: CompanyEvents (91 items), FilingEvents, HMRCData, RateLimits
- **Analysis Stack**: CompanyIntelligence (3 items)  
- **User Data**: Only company associations (user profiles preserved)

### Safety Features
- ✅ Dry-run mode shows what will be deleted
- ✅ Confirmation prompts before deleting
- ✅ Extra protection for production
- ✅ Preserves user profiles
- ✅ Idempotent (safe to run multiple times)

### Example Output
```
🧹 Company Data Cleanup - Environment: DEV
📦 Stack: data_collection
  📋 fiscalshield-dc-dev-CompanyEvents: 91 items → ✅ Deleted
📦 Stack: analysis  
  📋 fiscalshield-analysis-dev-CompanyIntelligence: 3 items → ✅ Deleted
📊 CLEANUP SUMMARY: Deleted 94 items from 2 tables
```

---

## 2. Delete Client Button ✅

### User Experience

**Location**: Company cards in "Your Registered Companies" section

**UI Changes**:
- New **actions menu (⋮)** button on each company card
- Menu contains: "Delete Company" option with trash icon
- Clicking shows **confirmation modal**:
  - "Are you sure you want to delete [Company Name] (#12345678)?"
  - Warning: "Cached data and documents will remain in the system"
  - Cancel / Delete buttons

### Flow
1. User clicks **⋮** actions button
2. Selects "Delete Company"
3. Sees confirmation modal
4. Clicks "Delete"
5. Company removed from list
6. List refreshes automatically

### Implementation

#### Frontend Changes

**CompanyCard.jsx**:
- Added `onDelete` prop
- Added `showDeleteModal` state
- Added `ButtonDropdown` for actions menu
- Added `Modal` for deletion confirmation
- Handlers: `handleDeleteClick`, `handleDeleteConfirm`, `handleDeleteCancel`

**CompanySelect.jsx**:
- Imported `deleteCompany` from service
- Added `handleDeleteCompany` function
- Passes `onDelete={handleDeleteCompany}` to CompanyCard
- Refreshes company list after deletion

**userCompanies.js Service**:
- New `deleteCompany(companyNumber)` function
- Calls GraphQL `deleteUserCompany` mutation

#### Backend Changes

**GraphQL Schema** (`src/api/schema.graphql`):
```graphql
deleteUserCompany(companyNumber: String!): Boolean! @aws_cognito_user_pools
```

**Lambda Function** (`src/lambda/delete_user_company/index.py`):
- Deletes item from UserProfileTable
- Key: `PK=user_id, SK=COMPANY#{company_number}`
- Idempotent (returns success even if already deleted)
- Proper error handling and logging

**CloudFormation** (`template.yaml`):
- `DeleteUserCompanyFunction` - Lambda resource
- `DeleteUserCompanyFunctionLogGroup` - CloudWatch logs
- `DeleteUserCompanyDataSource` - AppSync data source
- `DeleteUserCompanyResolver` - GraphQL resolver

### Security
- ✅ User can only delete their own companies (enforced by Cognito identity)
- ✅ Confirmation modal prevents accidental deletion
- ✅ Cached data preserved (documents in S3 unaffected)
- ✅ Audit trail in CloudWatch logs

### What Happens
- **Deleted**: Company association in UserProfileTable
- **Preserved**: Documents in S3, cached analysis data
- **Result**: Company no longer appears in user's list
- **Recoverable**: User can re-register the company anytime

---

## Files Created/Modified

### New Files
- `scripts/cleanup_company_data.py` - Database cleanup script
- `scripts/README_CLEANUP.md` - Cleanup documentation
- `src/lambda/delete_user_company/index.py` - Delete Lambda
- `src/ui/src/graphql/queries/deleteUserCompany.js` - GraphQL mutation

### Modified Files
- `template.yaml` - Added DeleteUserCompany Lambda resources
- `src/api/schema.graphql` - Added deleteUserCompany mutation
- `src/ui/src/components/company-card/CompanyCard.jsx` - Added delete UI
- `src/ui/src/components/company-select/CompanySelect.jsx` - Added delete handler
- `src/ui/src/services/userCompanies.js` - Added deleteCompany function

---

## Testing

### Test Cleanup Script
```bash
# Dry run first
python3 scripts/cleanup_company_data.py --environment dev --dry-run

# If output looks good, run for real
python3 scripts/cleanup_company_data.py --environment dev
```

### Test Delete Button
1. Deploy stack with new changes
2. Login to frontend
3. Navigate to Company Select page
4. Find a registered company card
5. Click actions button (⋮)
6. Select "Delete Company"
7. Confirm deletion
8. Verify company disappears from list
9. Verify documents still accessible (if any)
10. Re-register company to verify it works

---

## Deployment Steps

### 1. Deploy Backend
```bash
sam build
sam deploy --guided
```

### 2. Deploy Frontend
```bash
cd src/ui
npm run build
# Deploy to S3/CloudFront
```

### 3. Run Cleanup (Optional)
```bash
# If you want to clean old data
python3 scripts/cleanup_company_data.py --environment dev
```

---

## Next Steps

### Potential Enhancements
1. **Bulk Delete**: Select multiple companies and delete at once
2. **Soft Delete**: Mark as deleted instead of removing (recoverable)
3. **Delete Cascade**: Option to also delete documents and cached data
4. **Audit Trail**: Show deletion history in UI
5. **Export Before Delete**: Download company data before deletion
6. **Scheduled Cleanup**: Cron job to auto-clean old test data

### Known Limitations
- Documents in S3 are not deleted (by design - safety feature)
- Cached intelligence data remains (will be recalculated on next request)
- No undo feature (deletion is immediate)
- No bulk delete (one company at a time)

---

## Troubleshooting

### Cleanup Script Issues

**"ModuleNotFoundError: No module named 'boto3'"**
- Solution: Activate virtual environment
  ```bash
  source idp-linux/bin/activate
  python3 scripts/cleanup_company_data.py --environment dev --dry-run
  ```

**"AccessDeniedException"**
- Solution: Check AWS credentials have DynamoDB permissions

### Delete Button Issues

**Button doesn't appear**
- Check: Lambda deployed successfully
- Check: GraphQL schema updated
- Check: Frontend rebuilt and deployed

**"Failed to delete company"**
- Check: User is authenticated (Cognito)
- Check: Lambda has DynamoDB write permissions
- Check: CloudWatch logs for detailed error

**Company still appears after deletion**
- Refresh the page (browser cache)
- Check: Lambda execution succeeded in CloudWatch
- Check: DynamoDB item actually deleted

---

## Security Considerations

### Cleanup Script
- ⚠️ Requires DynamoDB write permissions
- ⚠️ Irreversible operation
- ✅ Confirmation prompts protect against accidents
- ✅ Dry-run mode for safety

### Delete Button
- ✅ User can only delete their own companies
- ✅ Cognito identity enforced at GraphQL layer
- ✅ Lambda validates user ID matches
- ✅ Confirmation modal prevents accidental clicks
- ✅ Audit trail in CloudWatch

---

## Compliance Notes

For UK accounting firms using FiscalShield:

- **Data Retention**: Documents in S3 are preserved (compliance requirement)
- **Right to be Forgotten**: Company association deleted, but documents remain
- **Audit Trail**: All deletions logged in CloudWatch with timestamps
- **Recoverable**: Users can re-register companies if needed

---

**Status**: ✅ Ready to deploy and test
