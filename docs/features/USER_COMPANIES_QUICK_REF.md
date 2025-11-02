# Quick Reference - User Companies Feature

## What I Built For You

Your landing page now shows **company cards** for all companies a user has registered under their account. Users can click on these cards to quickly access their documents.

## How It Works

### The Flow:
1. User logs in → Goes to landing page
2. **New!** → System queries DynamoDB for all companies linked to this user
3. **New!** → Displays cards showing each company with:
   - Company name and number
   - Number of documents
   - Last activity date
   - Document types processed
4. User clicks "View Documents" → Goes straight to that company's documents

### Where The Data Comes From:

Your `ExtractionResultsTable` in DynamoDB already stores:
- `UserId` - Which user owns the document
- `CompanyNumber` - Company identifier from registration
- `CompanyName` - Company name
- `DocumentType` - Type of document
- `ProcessedAt` - When processed

The new Lambda function queries this table by `UserId` using the `GSI2-UserAllDocs` index, groups by company, and returns unique companies with stats.

## What Was Added

### Backend (4 new components):
1. **Lambda Function**: `src/lambda/list_user_companies/lambda_function.py`
   - Queries DynamoDB for user's companies
   - Groups and aggregates data

2. **GraphQL Type**: `UserCompany` in `schema.graphql`
   - Defines company data structure

3. **GraphQL Query**: `getUserCompanies` in `schema.graphql`
   - API endpoint to fetch companies

4. **CloudFormation Resources** in `template.yaml`:
   - Lambda function, log group, data source, resolver

### Frontend (3 new components):
1. **Service**: `src/ui/src/services/userCompanies.js`
   - Calls GraphQL API
   - Formats dates/times

2. **Component**: `src/ui/src/components/company-card/CompanyCard.jsx`
   - Displays company information as a card
   - Reusable component

3. **Updated Page**: `src/ui/src/components/company-select/CompanySelect.jsx`
   - Shows company cards section at top
   - Loads companies on page load

## Deployment

```bash
# Build and deploy
sam build && sam deploy

# The feature will be live after deployment!
```

## Visual Result

**Before:**
```
┌─────────────────────────────────┐
│ Select Your Company             │
│ [Search box]                    │
│ [Search button]                 │
└─────────────────────────────────┘
```

**After:**
```
┌─────────────────────────────────────────────┐
│ Your Registered Companies (NEW!)            │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│ │Company A │ │Company B │ │Company C │    │
│ │15 docs   │ │8 docs    │ │23 docs   │    │
│ │[View →] │ │[View →] │ │[View →] │    │
│ └──────────┘ └──────────┘ └──────────┘    │
└─────────────────────────────────────────────┘
┌─────────────────────────────────┐
│ Register Another Company        │
│ [Search box]                    │
│ [Search button]                 │
└─────────────────────────────────┘
```

## Key Files to Review

1. **Lambda**: `/src/lambda/list_user_companies/lambda_function.py`
2. **Schema**: `/src/api/schema.graphql` (search for "UserCompany")
3. **Frontend**: `/src/ui/src/components/company-select/CompanySelect.jsx` (search for "userCompanies")
4. **Template**: `/template.yaml` (search for "ListUserCompanies")

## Testing After Deployment

1. Login to your app
2. Upload some documents with company information
3. Go back to landing page
4. You should see company cards at the top!
5. Click "View Documents" on any card
6. Should navigate to documents filtered by that company

## Important Notes

✅ **No breaking changes** - Existing functionality still works  
✅ **Backwards compatible** - Works even if no companies registered  
✅ **Secure** - Users only see their own companies  
✅ **Efficient** - Uses existing DynamoDB GSI  
✅ **Minimal cost** - Tiny additional Lambda/DynamoDB usage  

## Questions?

Check the full documentation: `USER_COMPANIES_FEATURE.md`
