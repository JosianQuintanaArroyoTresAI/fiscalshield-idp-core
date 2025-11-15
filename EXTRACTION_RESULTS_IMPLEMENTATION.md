# Extraction Results Implementation Summary

## Overview
Successfully implemented full-stack feature to display extracted invoice and bank statement data in the Documents page tabs, replacing previous placeholders with real data from DynamoDB.

## Implementation Date
2024-01-XX (Commit: 1929787e)

## What Was Built

### 1. Backend API (Lambda + GraphQL)

**New Lambda Function:**
- `src/lambda/list_extraction_results/lambda_function.py`
- Queries `ExtractionResultsTable` using GSI6-ClientTypeDate index
- Filters by: `CompanyNumber`, `DocumentType`, `UserId` (security)
- Returns paginated results with support for nextToken

**GraphQL Schema Updates:**
```graphql
type ExtractionResult {
  # Invoice fields: InvoiceNumber, VendorName, TotalAmount, etc.
  # Bank statement fields: BankName, AccountNumber, OpeningBalance, etc.
  # Common fields: DocumentId, ExtractionStatus, ConfidenceScore, etc.
}

type Query {
  listExtractionResults(
    companyNumber: String!
    documentType: String!
    limit: Int
    nextToken: String
  ): ExtractionResultsConnection
}
```

**Infrastructure:**
- Added Lambda configuration in `template.yaml`
- Wired to AppSync via DataSource and Resolver
- Granted DynamoDB read permissions on GSI6 index
- Added to AppSyncServiceRole invoke permissions

### 2. Frontend Service Layer

**New Service:** `src/ui/src/services/extractionService.js`
- `fetchExtractionResults()` - Query GraphQL API
- `formatInvoiceData()` - Format invoice records for display
- `formatBankStatementData()` - Format bank statement records for display
- Utility functions:
  - `formatCurrency()` - Format amounts with currency symbols
  - `formatDate()` - Convert ISO dates to readable format
  - `maskAccountNumber()` - Security masking for account numbers
  - `getStatusVariant()` - Map status to Cloudscape badge colors

**New GraphQL Query:** `src/ui/src/graphql/queries/listExtractionResults.js`
- Defines query with all extraction result fields
- Supports pagination (limit, nextToken)

### 3. Frontend UI Updates

**DocumentList.jsx Changes:**
- Replaced placeholder functions with real data tables
- Added state management for invoices and bank statements
- Integrated with `useCompany()` hook for company-scoped queries
- Lazy loading: only fetches data when tab is active
- Dynamic tab badges showing record counts
- Proper loading and empty states

**Invoice Table Columns:**
- Invoice #, Vendor, Invoice Date, Due Date
- Amount (formatted currency)
- Status (with colored badge)
- Confidence score

**Bank Statement Table Columns:**
- Bank, Account (masked), Statement Date, Period
- Opening/Closing Balance (formatted currency)
- Status (with colored badge)
- Confidence score

## Data Flow

```
User selects company → CompanyProvider updates context
                     ↓
DocumentList detects company change + active tab
                     ↓
fetchExtractionResults(companyNumber, documentType)
                     ↓
GraphQL query to AppSync
                     ↓
Lambda queries DynamoDB GSI6: client#{CompanyNumber}#type#{DocumentType}
                     ↓
Filters by UserId (security layer)
                     ↓
Returns formatted extraction results
                     ↓
UI displays in Table component
```

## DynamoDB Query Details

**Table:** `ExtractionResultsTable` (823 items in dev)

**Index Used:** `GSI6-ClientTypeDate`
- Partition Key: `GSI6PK = client#{CompanyNumber}#type#{DocumentType}`
- Sort Key: `ProcessedAt` (timestamp, descending)

**Query Pattern:**
```python
gsi6_pk = f"client#{company_number}#type#{document_type}"
query(
  IndexName="GSI6-ClientTypeDate",
  KeyConditionExpression=Key("GSI6PK").eq(gsi6_pk),
  ScanIndexForward=False  # Newest first
)
```

**Security Filtering:**
Results are filtered by `UserId` from Cognito identity to ensure users only see their own extraction results.

## Files Changed

**Backend:**
- `src/api/schema.graphql` - Added ExtractionResult types and query
- `src/lambda/list_extraction_results/lambda_function.py` - New Lambda function
- `template.yaml` - Lambda configuration and AppSync wiring

**Frontend:**
- `src/ui/src/components/document-list/DocumentList.jsx` - Integrated extraction data
- `src/ui/src/graphql/queries/listExtractionResults.js` - New GraphQL query
- `src/ui/src/services/extractionService.js` - New service with formatting logic

## Testing Checklist

After deployment (CloudFormation + force-update-lambdas):

- [ ] Select a company from dropdown
- [ ] Click "Invoices" tab - should load invoice records
- [ ] Click "Bank Statements" tab - should load bank statement records
- [ ] Verify tab badges show correct counts
- [ ] Verify loading states appear during fetch
- [ ] Verify empty states when no data exists
- [ ] Check console for proper GraphQL queries
- [ ] Verify data filtering by company (switch companies)
- [ ] Test with company that has no extraction results
- [ ] Verify user can only see their own extraction results (security test)

## Next Steps (Future Enhancements)

1. **Pagination Support**
   - Implement "Load More" button when nextToken exists
   - Support infinite scroll or page navigation

2. **Detail View**
   - Click invoice/statement row to view full extraction details
   - Display all fields from ExtractedData JSON
   - Show confidence scores per field

3. **Filtering & Search**
   - Add TextFilter for vendor/bank name search
   - Date range filtering
   - Amount range filtering
   - Status filtering

4. **Sorting**
   - Multi-column sorting
   - Custom sort preferences

5. **Export**
   - Export to Excel/CSV
   - Bulk download original documents

6. **Inline Editing** (inspired by old ParsedResults.js)
   - Edit extracted values
   - Save corrections back to DynamoDB
   - Track edit history

7. **Risk Scoring & Compliance** (Phase 2)
   - Display risk scores (1-5 scale)
   - BIM37000 compliance indicators
   - Category assignment
   - Legitimacy scores

8. **Bulk Operations**
   - Multi-select with checkboxes
   - Bulk approve/reject
   - Batch export

## Known Limitations

1. **No Pagination UI Yet**
   - Currently loads first 50 results only
   - nextToken is stored but not used for "Load More"

2. **No Caching**
   - Re-fetches on every tab switch
   - Consider implementing React Query or Apollo Client

3. **Bank Statement Detail**
   - Currently shows statement-level data only
   - Individual transactions not yet extracted/displayed

4. **No Real-time Updates**
   - Data refreshes only on company change or tab switch
   - Consider AppSync subscriptions for real-time updates

## Deployment Instructions

1. **Full Deployment** (if CloudFormation is not already running):
   ```bash
   sam build --cached
   sam deploy --config-env dev
   ```

2. **Quick Lambda Update** (if CloudFormation already deployed):
   ```bash
   ./scripts/force-update-lambdas.sh dev
   ```

3. **Frontend Only** (if only UI changes):
   - Changes auto-deploy via Amplify CI/CD on push to dev branch

## Related Documentation

- DynamoDB table schemas: See `aws dynamodb describe-table` output in conversation
- Sample data structure: See `aws dynamodb scan` output with invoice records
- Old UI reference: `src_old/pages/ParsedResults.js` (pre-production version)
- GraphQL API: `src/api/schema.graphql`

## Success Metrics

✅ All 6 planned tasks completed
✅ No syntax/linting errors in modified files
✅ Commit successfully pushed to dev branch
✅ Backend API properly secured with user-scoped filtering
✅ Frontend integrated with company context
✅ Lazy loading implemented (performance optimization)
✅ Proper error handling and empty states

---

**Commit:** 1929787e
**Author:** AI Assistant (via Josian's session)
**Branch:** dev
**Status:** Ready for deployment testing
