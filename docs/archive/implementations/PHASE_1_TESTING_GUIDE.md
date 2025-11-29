# Testing Phase 1 - Upload Interface

## 🧪 Quick Test Checklist

### Pre-Deployment Testing (Local Dev)

If you're running the UI locally:

```bash
cd src/ui
npm install
npm start
```

Then test these scenarios:

- [ ] **Test 1**: Page loads, upload area is greyed out and disabled
- [ ] **Test 2**: Click "Invoices" button → area becomes active
- [ ] **Test 3**: Click "Bank Statements" → switches, clears files if any
- [ ] **Test 4**: Try "Other Document Types" dropdown → select "Payslip"
- [ ] **Test 5**: Drag files without selecting type → shows error
- [ ] **Test 6**: Drag a PDF file onto active upload area → file appears in list
- [ ] **Test 7**: Click "Browse Files" → file picker opens
- [ ] **Test 8**: Select multiple files → all appear in list with sizes

### Post-Deployment Testing (Production/Dev Environment)

#### Step 1: Deploy the Changes

```bash
# From project root
sam build
sam deploy --guided

# OR if already configured
sam deploy
```

#### Step 2: Test Upload Flow

1. **Open your IDP web application**
2. **Navigate to Upload Documents page**
3. **Select "Invoices" document type**
4. **Drag and drop a test PDF** (or click Browse Files)
5. **Click "Upload 1 invoice(s)"**
6. **Wait for success message**

#### Step 3: Verify S3 Metadata

```bash
# Get the uploaded file's metadata
aws s3api head-object \
  --bucket <YOUR_INPUT_BUCKET> \
  --key users/<USER_ID>/<FILENAME>.pdf

# Should output something like:
# {
#   "Metadata": {
#     "user-document-type": "invoice",
#     "company-number": "12345678",
#     "company-name": "Test Company"
#   },
#   ...
# }
```

#### Step 4: Check Lambda Logs

```bash
# Check upload resolver logs
aws logs tail /aws/lambda/<STACK_NAME>-UploadResolverFunction --follow
```

Look for:
```
Adding user document type hint: invoice
Generated presigned POST data for user <USER_ID>
```

#### Step 5: Verify Document Processing

```bash
# Check queue sender logs
aws logs tail /aws/lambda/<STACK_NAME>-QueueSenderFunction --follow
```

**Note**: In Phase 1, QueueSender doesn't use the document type yet. 
You'll implement that in Phase 2.

## 🐛 Troubleshooting

### Issue: "Cannot read property 'InputBucket' of undefined"

**Cause**: Settings context not loaded  
**Fix**: Check that your Amplify configuration is correct and user is logged in

### Issue: Upload button stays disabled

**Checklist**:
- [ ] Document type selected? (button should be blue)
- [ ] Files selected? (should see file list)
- [ ] Not currently uploading? (no loading spinner)

### Issue: "No user ID found in identity context"

**Cause**: User not authenticated  
**Fix**: Log in via Cognito, check AppSync authentication

### Issue: Files upload but metadata missing

**Cause**: Lambda not updated  
**Fix**: 
```bash
sam build
sam deploy
# Wait for deployment to complete (~2-3 minutes)
```

### Issue: UI doesn't show new design

**Cause**: Browser cache or UI not rebuilt  
**Fix**:
```bash
# Hard refresh browser (Ctrl+Shift+R or Cmd+Shift+R)

# OR rebuild UI
cd src/ui
npm run build
# Redeploy built files
```

## 📊 Expected Results

### ✅ Success Criteria

After Phase 1 implementation, you should see:

1. **UI Level**:
   - Clean document type selector with 2 main buttons + dropdown
   - Large drag-and-drop upload area
   - No confusing "folder prefix" field
   - Clear visual feedback (active/inactive states)

2. **Backend Level**:
   - S3 objects have `user-document-type` in metadata
   - Upload resolver logs show document type
   - No errors in CloudWatch logs

3. **Data Level**:
   ```bash
   # This command should work and show metadata
   aws s3api head-object \
     --bucket YOUR_BUCKET \
     --key users/USER_ID/file.pdf \
     | jq '.Metadata["user-document-type"]'
   
   # Output: "invoice"
   ```

## 🎯 What Phase 1 Enables

### Completed ✅

- User can indicate document type during upload
- Document type stored in S3 metadata
- UI is intuitive and user-friendly
- No more confusing folder prefix field

### Not Yet Used ⏳ (Future Phases)

The `user-document-type` metadata is now stored, but:
- ❌ QueueSender doesn't extract it yet (Phase 2)
- ❌ Classification doesn't use it yet (Phase 2)
- ❌ Chunked extraction doesn't exist yet (Phase 3-4)

This is expected! Phase 1 just captures the user's intent.

## 📝 Test Scenarios

### Scenario 1: Single Invoice Upload

```
1. Click "📄 Invoices"
2. Drag "invoice-jan-2025.pdf" 
3. Click "Upload 1 invoice(s)"
4. Wait for success ✅
5. Verify metadata in S3
```

Expected metadata:
```json
{
  "user-document-type": "invoice",
  "company-number": "12345678",
  "company-name": "Acme Corp"
}
```

### Scenario 2: Multiple Bank Statements

```
1. Click "🏦 Bank Statements"
2. Click "Browse Files"
3. Select 3 PDFs: statement1.pdf, statement2.pdf, statement3.pdf
4. See all 3 in file list
5. Click "Upload 3 bank-statement(s)"
6. Wait for all 3 to complete ✅
```

Expected: 3 separate S3 objects, each with `user-document-type: "bank-statement"`

### Scenario 3: Switch Document Type

```
1. Click "📄 Invoices"
2. Select invoice.pdf (appears in list)
3. Click "🏦 Bank Statements" 
4. File list should clear ✅
5. Select statement.pdf
6. Upload
```

Expected: Only statement.pdf uploaded with `user-document-type: "bank-statement"`

### Scenario 4: Error Handling

```
1. DON'T select document type
2. Try to drag files
3. Should show error ❌ "Please select a document type first"
```

### Scenario 5: Large File

```
1. Select document type
2. Try to upload 150MB PDF
3. Should either:
   - Be rejected by file picker
   - OR fail at backend (100MB limit)
```

## 🔍 Manual Inspection

### Check UI Code Changes

```bash
# View the updated upload component
cat src/ui/src/components/upload-document/UploadDocumentPanel.jsx | grep -A 5 "documentType"
```

### Check Backend Code Changes

```bash
# View the updated upload resolver
cat src/lambda/upload_resolver/index.py | grep -A 3 "document_type"
```

### Check GraphQL Schema

```bash
# Verify documentType parameter added
cat src/api/schema.graphql | grep uploadDocument
```

## 📅 Next Steps After Testing

Once Phase 1 is tested and working:

1. ✅ Mark Phase 1 complete in `CHUNKED_INVOICE_EXTRACTION_IMPLEMENTATION_GUIDE.md`
2. 📋 Move to Phase 2: Update QueueSender Lambda
3. 📋 Move to Phase 2: Update Classification function
4. Continue through phases 3-6

## 🚨 Important Notes

- **Don't skip testing**: Phase 1 is the foundation for all other phases
- **Verify metadata**: If S3 metadata doesn't have `user-document-type`, Phase 2 won't work
- **Check CloudWatch**: Always verify Lambda logs to catch issues early
- **Test both paths**: Drag-and-drop AND browse files button

---

**Ready to deploy?** Run `sam build && sam deploy` from the project root! 🚀
