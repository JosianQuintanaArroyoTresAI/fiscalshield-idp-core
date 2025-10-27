# How to Ensure CompanyNumber is Stored in DynamoDB

## Overview

For the company cards to display, your document processing workflow must store the `CompanyNumber` attribute in the `ExtractionResultsTable` when documents are processed.

## Where This Happens

The `CompanyNumber` should be stored when a document is processed and saved to DynamoDB. This typically occurs in your document processing Lambda functions or Step Functions workflow.

## Current Setup - What to Check

### 1. Check Your CompanySelect Flow

In `/src/ui/src/components/company-select/CompanySelect.jsx`, when a user confirms a company:

```javascript
const handleConfirmAndResearch = async () => {
  if (!companyData) return;

  // Store company selection
  const companyContext = {
    company_number: companyData.company_number,
    company_name: companyData.company_name,
    selected_at: new Date().toISOString(),
    user_id: user?.username || 'unknown',
  };

  localStorage.setItem('active_company', JSON.stringify(companyContext));
```

This stores the company in localStorage, but you need to **pass this to your document processing workflow**.

### 2. Update Document Upload Process

When documents are uploaded, retrieve the active company and include it:

```javascript
// In your document upload handler
const activeCompany = JSON.parse(localStorage.getItem('active_company'));

const documentMetadata = {
  UserId: user.username,
  CompanyNumber: activeCompany?.company_number,  // ← ADD THIS
  CompanyName: activeCompany?.company_name,      // ← ADD THIS
  DocumentType: 'invoice', // or whatever type
  // ... other metadata
};
```

### 3. Ensure DynamoDB Item Includes Company Data

When saving to `ExtractionResultsTable`, the item should look like:

```python
# In your Lambda function that saves to DynamoDB
item = {
    'PK': f'USER#{user_id}#DOC#{document_id}',
    'SK': f'SECTION#{section_id}',
    'UserId': user_id,
    'CompanyNumber': company_number,     # ← REQUIRED for company cards
    'CompanyName': company_name,         # ← REQUIRED for company cards
    'DocumentId': document_id,
    'DocumentType': document_type,
    'ProcessedAt': int(time.time()),
    # ... other attributes
}
```

## GSI2-UserAllDocs Index Requirements

The `GSI2-UserAllDocs` index is already configured in your template:

```yaml
GlobalSecondaryIndexes:
  - IndexName: GSI2-UserAllDocs
    KeySchema:
      - AttributeName: UserId
        KeyType: HASH
      - AttributeName: ProcessedAt
        KeyType: RANGE
    Projection:
      ProjectionType: ALL  # This projects all attributes including CompanyNumber
```

This means as long as you store `CompanyNumber` in the item, it will be available when querying.

## Example: Update Document Processing Lambda

If you have a Lambda function that processes documents, update it like this:

```python
# src/lambda/process_document/handler.py (example)

def lambda_handler(event, context):
    # Extract from event
    user_id = event.get('user_id')
    document_id = event.get('document_id')
    company_number = event.get('company_number')  # ← NEW
    company_name = event.get('company_name')      # ← NEW
    
    # Process document...
    
    # Save to DynamoDB
    table = dynamodb.Table(EXTRACTION_RESULTS_TABLE)
    
    item = {
        'PK': f'USER#{user_id}#DOC#{document_id}',
        'SK': f'METADATA',
        'UserId': user_id,
        'CompanyNumber': company_number,   # ← ENSURE THIS IS SET
        'CompanyName': company_name,       # ← ENSURE THIS IS SET
        'DocumentId': document_id,
        'DocumentType': document_type,
        'ProcessedAt': int(time.time()),
        'GSI1PK': f'USER#{user_id}#TYPE#{document_type}',
        'GSI3PK': f'COMPANY#{company_number}',  # ← For company queries
        # ... other fields
    }
    
    table.put_item(Item=item)
```

## Example: Step Functions State Machine

If you use Step Functions, pass company data through the workflow:

```json
{
  "StartAt": "ProcessDocument",
  "States": {
    "ProcessDocument": {
      "Type": "Task",
      "Resource": "${ProcessDocumentLambda}",
      "Parameters": {
        "user_id.$": "$.user_id",
        "document_id.$": "$.document_id",
        "company_number.$": "$.company_number",
        "company_name.$": "$.company_name",
        "s3_key.$": "$.s3_key"
      }
    }
  }
}
```

## Verification Steps

### 1. Check DynamoDB Items

After processing a document, verify the item in DynamoDB:

```bash
# Query DynamoDB
aws dynamodb query \
  --table-name fiscalshield-idp-dev-ExtractionResults \
  --index-name GSI2-UserAllDocs \
  --key-condition-expression "UserId = :user_id" \
  --expression-attribute-values '{":user_id":{"S":"your-user-id"}}'
```

**Look for**:
- `CompanyNumber` attribute
- `CompanyName` attribute

### 2. Test the Lambda Directly

```bash
# Invoke the Lambda
aws lambda invoke \
  --function-name <stack-name>-ListUserCompaniesFunction \
  --payload '{"identity":{"username":"your-user-id"}}' \
  response.json

# Check response
cat response.json
```

**Expected output**:
```json
[
  {
    "company_number": "12345678",
    "company_name": "Acme Corp Ltd",
    "user_id": "user-123",
    "document_count": 5,
    "first_registered": 1698156000,
    "last_activity": 1698242400,
    "document_types": ["invoice", "receipt"]
  }
]
```

## Common Issues

### Issue: No companies showing up

**Cause**: `CompanyNumber` not stored in DynamoDB items

**Fix**:
1. Check document upload flow includes company context
2. Verify Lambda functions save `CompanyNumber` attribute
3. Re-process some documents to populate the field

### Issue: Some companies missing

**Cause**: Old documents don't have `CompanyNumber`

**Fix**: Either:
- **Option A**: Ignore old documents (only new ones will show)
- **Option B**: Backfill data with a migration script:

```python
# migration_script.py
def backfill_company_numbers():
    """Backfill CompanyNumber for existing documents"""
    
    # Query all documents without CompanyNumber
    response = table.scan(
        FilterExpression='attribute_not_exists(CompanyNumber)'
    )
    
    for item in response['Items']:
        # Extract company from document content or metadata
        company_number = extract_company_from_doc(item)
        
        if company_number:
            # Update the item
            table.update_item(
                Key={'PK': item['PK'], 'SK': item['SK']},
                UpdateExpression='SET CompanyNumber = :cn',
                ExpressionAttributeValues={':cn': company_number}
            )
```

## Summary Checklist

✅ Store `CompanyNumber` when user selects company  
✅ Pass `CompanyNumber` through document upload  
✅ Save `CompanyNumber` in DynamoDB items  
✅ Verify GSI2-UserAllDocs projects all attributes  
✅ Test Lambda function returns companies  
✅ Test UI displays company cards  

## Next Steps

1. **Review your document processing code** - Find where documents are saved to DynamoDB
2. **Add CompanyNumber field** - Update Lambda functions to include this attribute
3. **Re-deploy** - Deploy updated code
4. **Test** - Upload a new document with company selected
5. **Verify** - Check if company card appears on landing page

Need help finding where to make these changes? Let me know which document processing pattern you're using (Pattern 1, 2, or 3) and I can provide specific guidance!
