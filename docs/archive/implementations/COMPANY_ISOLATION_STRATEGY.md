# Company Isolation Strategy - Field Naming Clarification

## Current State Analysis

### TrackingTable (fiscalshield-idp-dev-TrackingTable-46U1QT8I1WG8)
- **Purpose**: Document processing workflow tracking
- **PK**: `user#{userId}#doc#{objectKey}`
- **SK**: `none` (or used for list items like `list#date#shard`)
- **Issue**: SK is sometimes used, no dedicated company field

### ExtractionResultsTable (fiscalshield-idp-dev-ExtractionResultsTable-1UK9NUFATW5DI)
- **Purpose**: Extracted document data storage
- **Current Fields**:
  - `ClientId` - Currently placeholder, intended for client/company identification
  - `CompanyName` - Currently set to vendor/bank name (supplier of the invoice)
  - `SupplierName` - The actual supplier/vendor name
- **GSI3**: `GSI3PK = {CompanyId}#{DocumentType}` - For company/vendor queries
- **GSI6**: `GSI6PK = {ClientId}#{DocumentType}` - For client-level reporting

## The Semantic Problem

**Current naming is confusing**:
- `ClientId` → Placeholder, unclear if it's the user's company or something else
- `CompanyName` → Set to supplier name (the company that issued the invoice)
- `SupplierName` → Also the supplier name (redundant)

**What we actually need**:
1. **User's Company** - The company that the logged-in user works for (e.g., "Acme Corp")
2. **Supplier/Vendor** - The company that issued the document (e.g., "Microsoft Ltd")

## Proposed Solution

### Semantic Clarity

**For User's Company** (the company registered via Companies House):
- `CompanyNumber` - UK Companies House number (e.g., "12345678")
- `CompanyName` - User's company name from Companies House (e.g., "Acme Corporation Ltd")

**For Document Supplier/Vendor**:
- `SupplierName` - Extracted from invoice/document (e.g., "Microsoft Limited")
- `VendorName` - Alias for SupplierName (keep for backward compatibility)
- `VendorAddress`, `VendorVatNumber`, etc. - Related vendor fields

### Implementation Strategy

#### Option 1: Minimal Changes (Recommended)
**Keep existing fields, add new ones**:

```python
# ExtractionResultsTable Item
{
    # User context (from company registration)
    "UserId": "cognito-user-id",
    "CompanyNumber": "12345678",  # NEW - from Companies House
    "CompanyName": "Acme Corp Ltd",  # CHANGE meaning - user's company
    
    # Document supplier context (extracted from document)
    "SupplierName": "Microsoft Limited",  # Document issuer
    "VendorName": "Microsoft Limited",  # Alias (backward compat)
    "VendorAddress": "...",
    "VendorVatNumber": "...",
    
    # Legacy/Deprecated
    "ClientId": "12345678",  # DEPRECATED - use CompanyNumber instead
    
    # GSI keys
    "GSI3PK": "COMPANY#12345678#INVOICE",  # Company-based queries
    "GSI6PK": "CLIENT#12345678#INVOICE",  # Client reporting (legacy)
}
```

#### Option 2: Clean Break (More Disruptive)
**Rename everything clearly**:

```python
{
    # User's company (from registration)
    "UserCompanyNumber": "12345678",
    "UserCompanyName": "Acme Corp Ltd",
    
    # Document supplier
    "SupplierName": "Microsoft Limited",
    "SupplierAddress": "...",
    "SupplierVatNumber": "...",
}
```

## Recommended Approach: **Option 1** (Minimal Changes)

### Changes Required:

#### 1. TrackingTable
**Add new field** (no schema change needed, DynamoDB is schemaless):
- `CompanyNumber` - Added to items when company is selected

```python
# In create_document_resolver
item = {
    "PK": f"user#{user_id}#doc#{object_key}",
    "SK": "none",
    "UserId": user_id,
    "CompanyNumber": company_number,  # NEW
    "ObjectKey": object_key,
    # ... other fields
}
```

#### 2. ExtractionResultsTable
**Semantic Shift** (no schema change):
- `CompanyNumber` → User's Companies House number (NEW)
- `CompanyName` → User's company name (CHANGE meaning from supplier to user's company)
- `SupplierName` → Keep as document issuer
- `ClientId` → Mark as deprecated, map to CompanyNumber

**Update extraction_results_writer.py**:
```python
def write_extraction_result(
    self,
    user_id: str,
    document_id: str,
    section_id: str,
    document_type: str,
    extraction_data: Dict[str, Any],
    extraction_status: str = "COMPLETED",
    processed_at: Optional[int] = None,
    confidence_score: Optional[float] = None,
    execution_id: Optional[str] = None,
    model_id: Optional[str] = None,
    username: Optional[str] = None,
    company_number: Optional[str] = None,  # NEW - User's company
    company_name: Optional[str] = None,  # NEW - User's company name
    client_id: Optional[str] = None,  # DEPRECATED
    company_id: Optional[str] = None,  # DEPRECATED
    section_index: Optional[int] = None,
    total_sections: Optional[int] = None,
):
    # Map legacy fields
    if client_id and not company_number:
        company_number = client_id  # Backward compat
    
    if company_id and not company_number:
        company_number = company_id  # Backward compat
    
    # Add to item
    if company_number:
        item["CompanyNumber"] = company_number
        item["GSI3PK"] = f"COMPANY#{company_number}#{document_type}"
        item["ClientId"] = company_number  # For legacy compatibility
    
    if company_name:
        item["CompanyName"] = company_name
    
    # Extract supplier from document
    inference_result = extraction_data.get("inference_result", {})
    if "vendor_name" in inference_result:
        item["SupplierName"] = inference_result["vendor_name"]
        item["VendorName"] = inference_result["vendor_name"]  # Alias
```

#### 3. Update Document Processing to Pass Company Context

**When documents are uploaded**, pass company context from localStorage:

```javascript
// In upload handler
const activeCompany = JSON.parse(localStorage.getItem('active_company'));

// Pass to backend
const metadata = {
    company_number: activeCompany?.company_number,
    company_name: activeCompany?.company_name,
};
```

**In Step Functions/Lambda**, extract and pass through:

```python
# In workflow
event = {
    'user_id': user_id,
    'object_key': object_key,
    'company_number': company_number,  # NEW
    'company_name': company_name,  # NEW
    # ... other fields
}
```

#### 4. Update GraphQL Queries for Filtering

**Add CompanyNumber filter to list queries**:

```graphql
type Query {
  listDocuments(
    startDateTime: AWSDateTime
    endDateTime: AWSDateTime
    companyNumber: String  # NEW - optional filter
  ): DocumentList
  
  listDocumentsDateHour(
    date: AWSDate
    hour: Int
    companyNumber: String  # NEW - optional filter
  ): DocumentList
  
  listDocumentsDateShard(
    date: AWSDate
    shard: Int
    companyNumber: String  # NEW - optional filter
  ): DocumentList
}
```

**Update VTL templates**:

```vtl
## ListDocumentResolver
{
    "version": "2018-05-29",
    "operation": "Scan",
    "filter": {
        #set($expressions = [])
        #set($values = {})
        
        ## User isolation (always applied)
        #set($expr = "UserId = :userId")
        $util.qr($expressions.add($expr))
        $util.qr($values.put(":userId", {"S": $ctx.identity.sub}))
        
        ## Company filter (optional)
        #if($ctx.arguments.companyNumber)
            #set($expr = "CompanyNumber = :companyNumber")
            $util.qr($expressions.add($expr))
            $util.qr($values.put(":companyNumber", {"S": $ctx.arguments.companyNumber}))
        #end
        
        ## Date range filter
        #if($ctx.arguments.startDateTime && $ctx.arguments.endDateTime)
            #set($expr = "InitialEventTime BETWEEN :startDateTime AND :endDateTime")
            $util.qr($expressions.add($expr))
            $util.qr($values.put(":startDateTime", {"S": $ctx.arguments.startDateTime}))
            $util.qr($values.put(":endDateTime", {"S": $ctx.arguments.endDateTime}))
        #end
        
        "expression": "$util.join(" AND ", $expressions)",
        "expressionValues": $util.toJson($values)
    },
    "limit": 50
}
```

## Migration Path

### Phase 1: Add Fields (Non-Breaking)
1. ✅ Add `CompanyNumber` and `CompanyName` fields to new documents
2. ✅ Update extraction_results_writer to accept company parameters
3. ✅ Keep `ClientId` for backward compatibility (map to `CompanyNumber`)

### Phase 2: Update Queries (Non-Breaking)
1. ✅ Add optional `companyNumber` parameter to GraphQL queries
2. ✅ Update VTL templates to filter when parameter provided
3. ✅ Update frontend to pass company context from localStorage

### Phase 3: Backfill (Optional)
1. Run script to add `CompanyNumber` to existing documents (if needed)
2. Update old documents where `ClientId` exists

### Phase 4: Deprecation (Future)
1. Mark `ClientId` and `CompanyId` as deprecated in documentation
2. Eventually remove after migration period

## Summary

**Key Changes**:
1. `CompanyNumber` (NEW) → User's Companies House number
2. `CompanyName` (SEMANTIC CHANGE) → User's company name (not supplier)
3. `SupplierName` (CLARIFIED) → Document issuer/vendor
4. `ClientId` (DEPRECATED) → Maps to `CompanyNumber` for compatibility

**Benefits**:
- ✅ Clear semantic meaning
- ✅ Backward compatible
- ✅ Enables company-based filtering
- ✅ Works with Companies House integration
- ✅ No schema migration required (DynamoDB schemaless)

**Next Steps**:
1. Update `extraction_results_writer.py` to add company fields
2. Update document upload to pass company context
3. Update GraphQL schema to add company filter
4. Update VTL templates for filtering
5. Update frontend to pass company context to queries
