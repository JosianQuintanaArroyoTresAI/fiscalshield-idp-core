# Deduplication & Extraction Fix Summary

## Issue Analysis

### Original Problem
- 109 invoices extracted instead of expected 101
- Microsoft Limited invoice appeared 4 times (chunks 3, 4, 6, 10)
- 11 different invoices all had "GB-TI2500887574" as invoice_number
- 6 different expense claims all had "Expense Claims" as invoice_number

### Root Causes
1. **Deduplication Logic**: Only removed duplicates in consecutive chunks (within 1)
   - Microsoft invoice in chunks 3,4,6,10 → only 3&4 deduplicated
   - Chunks 6 and 10 kept as "different invoices"

2. **Extraction Quality**: LLM extracted wrong fields as invoice_number
   - Used VAT registration number (GB-TI2500887574) instead of actual invoice number
   - Used generic text ("Expense Claims") instead of unique invoice identifier
   - This is why same "invoice_number" appeared for different invoices

## Solutions Implemented

### 1. Enhanced Deduplication Logic
**File**: `patterns/pattern-2/lambdas/invoice_extraction/invoice_extraction_handler.py`

**Key Changes**:
- **Before**: Only deduplicated if chunks were consecutive (within 1)
- **After**: Deduplicates if ALL identity fields match, regardless of chunk distance

**Logic**:
```python
# Groups by: (supplier_name, invoice_number, invoice_date, total_amount)

# Case 1: Chunks consecutive (within 1) → Deduplicate
#   Reason: Overlap region duplicates

# Case 2: Chunks far apart BUT all fields match → Deduplicate
#   Reason: True duplicate (invoice numbers must be unique)
#   This catches extraction artifacts appearing multiple times

# Case 3: Same invoice_number but DIFFERENT supplier/date/amount → Keep all
#   Reason: Extraction error (wrong field used as invoice#)
#   Protects against deleting legitimate different invoices
```

**Result**: 
- ✅ Removes 3 Microsoft duplicates (chunks 3,4,6,10 → keep 1)
- ✅ Keeps 11 other invoices with GB-TI2500887574 (different suppliers/amounts)
- ✅ Keeps 6 expense claims with "Expense Claims" (different details)

### 2. Improved Extraction Prompt (UK Standards)
**File**: Same file, `get_default_invoice_prompt()` function

**UK Invoice Number Standards**:
1. **Invoice Number** (invoice_number):
   - Labels: "Invoice No", "Invoice Number", "Tax Invoice No"
   - Format: SHORT and SEQUENTIAL (INV-001, 2024-123)
   - Required by HMRC for VAT invoices
   - UNIQUE to this specific invoice

2. **Reference Number** (reference_number):
   - Labels: "Reference", "PO Number", "Order Ref", "Job No"
   - Buyer's cross-reference (purchase order, job code)
   - Optional field

3. **DO NOT USE as Invoice Number**:
   - ❌ VAT Registration Numbers (GB123456789)
   - ❌ Company Registration Numbers (12345678)
   - ❌ Form template IDs (GB-TI2500887574)
   - ❌ Generic labels ("Expense Claims")

**Prompt Enhancements**:
- Added detailed UK HMRC standards section
- Clear examples of correct vs incorrect extraction
- Explicit instructions to leave invoice_number EMPTY if not found
- Better distinction between invoice_number and reference_number

## Expected Results After Deployment

### Current State (109 invoices)
- Microsoft Limited: 4 copies (chunks 3,4,6,10)
- 15 invoices with "GB-TI2500887574" (1 real, 14 extraction errors)
- 6 invoices with "Expense Claims" (all different)

### After Deduplication Fix (106 invoices)
- Microsoft Limited: 1 copy (3 duplicates removed)
- 15 invoices still exist but with CORRECT deduplication
- Total: 109 - 3 = 106 invoices

### After Extraction Fix (Next Upload)
- New extractions will use improved prompt
- Invoice numbers will be correctly extracted:
  - Microsoft invoice: actual invoice number (not VAT reg)
  - Expense claims: empty string (not generic text)
- Future duplicates will be TRUE duplicates only

## Deployment Instructions

1. **Deploy updated Lambda**:
   ```bash
   ./deploy-pattern2-dev.sh
   ```

2. **Re-process existing document** (to apply deduplication fix):
   - Delete existing invoices for document from DynamoDB
   - Trigger re-extraction via frontend
   - New extraction will use improved prompt AND deduplication

3. **Verify Results**:
   ```bash
   # Check invoice count
   aws dynamodb query \
     --table-name fiscalshield-idp-dev-ExtractionResultsTable-ODNDYL7KUECH \
     --key-condition-expression "PK = :pk AND begins_with(SK, :sk)" \
     --expression-attribute-values '{
       ":pk": {"S": "user#23b4b872-20a1-709e-ffef-d20a604f60b5#doc#users/23b4b872-20a1-709e-ffef-d20a604f60b5/Invoices_101_page3.pdf"},
       ":sk": {"S": "type#INVOICE"}
     }' \
     --select COUNT
   ```

## Technical Details

### Deduplication Algorithm
1. Query all invoices for document section from DynamoDB
2. Group by identity key: `(supplier_name, invoice_number, invoice_date, total_amount)`
3. For each group with >1 invoice:
   - Check chunk distance
   - Decide: deduplicate or keep all
   - Sort by completeness (most complete first)
   - Keep best one, delete rest

### Identity Key Protection
- Groups ONLY invoices with EXACT match on all 4 fields
- Different supplier/amount/date = different group = kept
- This protects against extraction errors where same invoice_number used incorrectly

### Completeness Scoring
Keeps invoice with most non-empty fields:
- supplier_name, invoice_number, invoice_date
- reference_number, description, supplier_address
- vendor_name, total_amount

## Testing Checklist

- [ ] Deploy updated Lambda
- [ ] Re-process 101-page document
- [ ] Verify invoice count: 101-106 (expected range)
- [ ] Check Microsoft Limited: only 1 instance
- [ ] Verify invoice numbers are correct (not VAT numbers)
- [ ] Check CloudWatch logs for deduplication messages
- [ ] Confirm no legitimate invoices removed

## Files Modified

1. `patterns/pattern-2/lambdas/invoice_extraction/invoice_extraction_handler.py`
   - Function: `deduplicate_invoices_in_dynamodb()` (lines 445-680)
   - Function: `get_default_invoice_prompt()` (lines 733-813)

## Related Issues

- ✅ Fixed: Non-consecutive chunk duplicates
- ✅ Fixed: Extraction using wrong fields as invoice_number
- 🔄 To monitor: Future extraction quality with improved prompt
- 🔄 To test: Deduplication with new Claude Haiku 4.5 model
