# User Company Registration Display - Implementation Summary

## Overview

Added functionality to display all companies registered under a user on the landing page. Users can now see company cards for all their registered companies and quickly access their documents.

## What Was Implemented

### 1. Backend - Lambda Function (`src/lambda/list_user_companies/lambda_function.py`)

**Purpose**: Query DynamoDB to find all companies a user has registered documents for.

**Key Features**:
- Queries `ExtractionResultsTable` using `GSI2-UserAllDocs` index
- Groups documents by `CompanyNumber` to find unique companies
- Aggregates company metadata:
  - Document count per company
  - First registration date
  - Last activity timestamp
  - Document types processed
- Returns sorted list (most recent activity first)

**How It Works**:
```python
# Queries DynamoDB GSI2-UserAllDocs by UserId
response = table.query(
    IndexName="GSI2-UserAllDocs",
    KeyConditionExpression=Key("UserId").eq(user_id)
)

# Groups by CompanyNumber and aggregates stats
# Returns: [{ company_number, company_name, document_count, ... }]
```

### 2. GraphQL Schema Updates (`src/api/schema.graphql`)

**Added Type**:
```graphql
type UserCompany @aws_cognito_user_pools @aws_iam {
  company_number: String!
  company_name: String!
  user_id: String!
  document_count: Int!
  first_registered: AWSTimestamp!
  last_activity: AWSTimestamp!
  document_types: [String]
}
```

**Added Query**:
```graphql
getUserCompanies: [UserCompany] @aws_cognito_user_pools
```

### 3. Frontend Service (`src/ui/src/services/userCompanies.js`)

**Purpose**: Service layer to interact with GraphQL API.

**Functions**:
- `fetchUserCompanies()` - Fetches all user companies via GraphQL
- `formatCompanyDate(timestamp)` - Formats timestamp to readable date
- `formatRelativeTime(timestamp)` - Converts to relative time (e.g., "2 days ago")

### 4. React Component - CompanyCard (`src/ui/src/components/company-card/CompanyCard.jsx`)

**Purpose**: Reusable card component to display company information.

**Features**:
- Displays company name and number
- Shows document count, last activity, and registration date
- Lists document types as badges
- "View Documents" button to navigate to company's documents

**Visual Layout**:
```
┌─────────────────────────────────────────────┐
│ Company Name                                │
│ Company #12345678                           │
│                                             │
│ Documents: 15    Last: 2 days ago  First:  │
│                  Oct 25, 2025     Jan 2025 │
│                                             │
│ Document Types: [Invoice] [Receipt] [PO]   │
│                                             │
│                      [View Documents →]     │
└─────────────────────────────────────────────┘
```

### 5. Landing Page Updates (`src/ui/src/components/company-select/CompanySelect.jsx`)

**New Section**: "Your Registered Companies"
- Appears at the top of the landing page
- Shows grid of company cards (3 columns)
- Only displays if user has registered companies
- Loading state with spinner
- Error handling

**User Flow**:
1. User logs in → Redirected to `/company-select`
2. **NEW**: Automatically loads user's registered companies
3. **NEW**: Displays company cards at the top
4. User can either:
   - Click "View Documents" on existing company card → Goes to documents
   - Register a new company using the search form below

### 6. CloudFormation Template (`template.yaml`)

**Added Resources**:
- `ListUserCompaniesFunction` - Lambda function
- `ListUserCompaniesFunctionLogGroup` - CloudWatch log group
- `ListUserCompaniesDataSource` - AppSync data source
- `ListUserCompaniesResolver` - AppSync resolver for `getUserCompanies` query

**Permissions**:
- Read access to `ExtractionResultsTable`
- Query access to `GSI2-UserAllDocs` index
- KMS decrypt for encrypted data

## Data Flow

```
┌──────────────┐
│   User UI    │
│ CompanySelect│
└──────┬───────┘
       │
       │ 1. useEffect → fetchUserCompanies()
       ▼
┌──────────────────┐
│  GraphQL Query   │
│ getUserCompanies │
└──────┬───────────┘
       │
       │ 2. AppSync routes to Lambda
       ▼
┌─────────────────────────┐
│ ListUserCompaniesFunction│
└──────┬──────────────────┘
       │
       │ 3. Query DynamoDB
       ▼
┌────────────────────────┐
│ ExtractionResultsTable │
│ GSI2-UserAllDocs       │
│ (UserId → Companies)   │
└──────┬─────────────────┘
       │
       │ 4. Aggregate & Return
       ▼
┌──────────────┐
│  Company     │
│  Cards UI    │
└──────────────┘
```

## Files Created

1. `/src/lambda/list_user_companies/lambda_function.py` - Lambda handler
2. `/src/ui/src/graphql/queries/getUserCompanies.js` - GraphQL query
3. `/src/ui/src/services/userCompanies.js` - Service layer
4. `/src/ui/src/components/company-card/CompanyCard.jsx` - Card component

## Files Modified

1. `/src/api/schema.graphql` - Added UserCompany type and getUserCompanies query
2. `/src/ui/src/components/company-select/CompanySelect.jsx` - Added company cards section
3. `/template.yaml` - Added Lambda function, data source, and resolver

## How Companies Are Tracked

The system identifies companies from the `ExtractionResultsTable` in DynamoDB. When documents are processed:

1. Documents are stored with `UserId` and `CompanyNumber` attributes
2. GSI2-UserAllDocs index allows efficient querying by UserId
3. Lambda function groups results by CompanyNumber
4. Returns unique companies with aggregated statistics

**Key DynamoDB Pattern**:
```
Table: ExtractionResultsTable
GSI2-UserAllDocs:
  PK: UserId (e.g., "user123")
  SK: ProcessedAt (timestamp for sorting)
  Attributes: CompanyNumber, CompanyName, DocumentType, etc.
```

## Security

- **Authentication**: Query requires Cognito authentication (`@aws_cognito_user_pools`)
- **Authorization**: Lambda receives user ID from Cognito identity
- **Data Isolation**: Users can only see their own companies
- **Encryption**: 
  - Data encrypted at rest with KMS
  - Lambda has decrypt permissions for read operations

## Testing the Feature

### After Deployment:

1. **Login** to the application
2. **Upload documents** with company information
3. **Navigate to landing page** (`/company-select`)
4. **Verify**:
   - Companies display in cards at top
   - Document count is accurate
   - Last activity shows correct time
   - "View Documents" navigates correctly

### Expected Behavior:

**First-time user** (no companies):
- Only sees "Select Your Company" section
- No company cards displayed

**Returning user** (has companies):
- Sees "Your Registered Companies" section at top
- Company cards show statistics
- Can click "View Documents" to access company's documents
- Can still register new companies below

## Performance Considerations

- **Query Efficiency**: Uses GSI2-UserAllDocs for fast lookups
- **Pagination**: Lambda handles large result sets with pagination
- **Caching**: Results cached in component state during session
- **Lazy Loading**: Companies loaded only when landing page is accessed

## Future Enhancements

1. **Search/Filter**: Add ability to search companies by name/number
2. **Sorting Options**: Allow sorting by name, document count, activity
3. **Company Details**: Click company name to see detailed view
4. **Recent Activity**: Show recent document uploads per company
5. **Company Logo**: Integrate Companies House logo/branding if available
6. **Favorites**: Allow users to pin favorite companies to top

## Deployment Notes

### Prerequisites:
- ExtractionResultsTable must have GSI2-UserAllDocs index (already exists)
- Documents must be stored with CompanyNumber attribute

### Deploy Command:
```bash
sam build && sam deploy
```

### Verify Deployment:
```bash
# Check Lambda function exists
aws lambda get-function --function-name <stack-name>-ListUserCompaniesFunction

# Check AppSync resolver
aws appsync get-resolver --api-id <api-id> --type-name Query --field-name getUserCompanies
```

## Troubleshooting

### Issue: Companies not displaying
**Check**:
1. Documents have `CompanyNumber` attribute set
2. GSI2-UserAllDocs index exists
3. Lambda has permissions to query index
4. Check CloudWatch logs for Lambda errors

### Issue: Loading indefinitely
**Check**:
1. GraphQL query syntax in frontend
2. AppSync resolver connected correctly
3. Lambda function invocation succeeds

### Issue: Wrong company data
**Check**:
1. Document processing sets correct CompanyNumber
2. Company name extraction is working
3. Lambda aggregation logic is correct

## Cost Impact

**Minimal additional costs**:
- Lambda: Pay per query (typically <100ms execution)
- DynamoDB: Uses existing GSI, no additional reads beyond user's data
- AppSync: Standard API call pricing

**Estimated monthly cost** for 1000 users with 10 companies each:
- Lambda: ~1000 invocations/month × $0.0000002 = $0.0002
- DynamoDB: Included in existing read capacity
- **Total**: < $0.01/month

## Summary

✅ Users can now see all their registered companies on the landing page  
✅ Company cards display key metrics (documents, activity, types)  
✅ Quick access to company documents via "View Documents" button  
✅ Efficient DynamoDB queries using existing GSI  
✅ Secure, user-isolated data access  
✅ Responsive UI with loading and error states  

The landing page now serves as a dashboard showing users all their registered companies at a glance!
