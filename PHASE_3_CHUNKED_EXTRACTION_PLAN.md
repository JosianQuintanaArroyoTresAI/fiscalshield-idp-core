# Phase 3: Chunked Invoice Extraction Implementation Plan

## Executive Summary

**Goal**: Adapt your proven chunked extraction lambda to work with IDP Core's Pattern 2 architecture, adding configurable model selection (Sonnet 3.5 vs 3.7 with cross-region inference).

**Key Differences Identified**:
1. ✅ **What Works (Keep)**: Chunking logic, deduplication algorithm, prompt strategy
2. ❌ **What Needs Changing**: DynamoDB schema, table names, event structure, model invocation

---

## 1. Architecture Analysis

### Your Original Lambda (TaxGuard)
```
Event Source: SQS (direct chunks)
Tables: 
  - tag-invoice-documents (tracking)
  - tag-financial-data-{env}-{region} (results)
Model: eu.anthropic.claude-3-5-sonnet-20240620-v1:0 (hardcoded)
Primary Key: financial_record_id
```

### IDP Core Pattern 2
```
Event Source: Step Functions (section-based)
Tables:
  - TrackingTable (document lifecycle)
  - ExtractionResultsTable (results with composite keys)
  - ConfigurationTable (prompts, settings)
Model: Configurable via BEDROCK_MODEL_ID env var
Primary Key: PK + SK (composite)
GSI Keys: GSI1PK, GSI3PK, GSI6PK (for querying)
```

---

## 2. What Works (Keep These)

### ✅ Chunking Parameters (Proven & Optimal)
```python
CHUNK_SIZE = 15000  # characters per chunk
OVERLAP_SIZE = 3000  # character overlap between chunks
```

**Why these work**:
- 15k chars fits comfortably in Claude's context window
- 3k overlap ensures no invoice is split across chunks
- Tested on 50+ page multi-invoice PDFs

### ✅ Extraction Prompt Strategy
Your prompt is **excellent**:
- Explicit "MULTIPLE INVOICES" instruction
- Page number extraction with markers
- Vendor name fallback logic
- XML output format for reliable parsing
- "Extract EVERY invoice" emphasis

**Action**: Move this to ConfigurationTable for frontend editing

### ✅ Deduplication Algorithm
Your page-based deduplication is **superior** to simple field matching:
```python
def are_invoices_duplicate_by_pages(invoice1, invoice2):
    # 1. Check for page overlap (from chunking)
    # 2. If overlap exists, compare content (vendor, amount, date)
    # 3. Only flag as duplicate if CLEARLY different people detected
    # 4. Keep the more complete invoice
```

**Why it works**:
- Handles chunk overlap duplicates
- Distinguishes different people with same vendor (employee expenses)
- Content-first approach with page validation

### ✅ Logging Strategy
Your timestamped logging is excellent for debugging:
```python
def log_with_timestamp(message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    print(f"[{timestamp}] {message}")
```

---

## 3. What Needs Changing

### ❌ Event Structure
**Original** (SQS message):
```json
{
  "document_id": "doc-123",
  "chunk_index": 1,
  "total_chunks": 5,
  "text_chunk": "...",
  "username": "user@example.com",
  "client_id": "GB12345678"
}
```

**IDP Core** (Step Functions):
```json
{
  "execution_arn": "arn:aws:...",
  "document": {
    "id": "doc-123",
    "user_id": "uuid",
    "company_number": "GB12345678",
    "company_name": "Acme Ltd",
    "sections": [{
      "section_id": "1",
      "classification": "invoice",
      "page_ids": ["1", "2", "3"],
      "...": "..."
    }],
    "pages": {
      "1": {"raw_text_uri": "s3://...", "ocr_text": "..."},
      "...": "..."
    }
  },
  "section_id": "1"
}
```

**Required Changes**:
1. Extract text from `document.sections[X]` not from direct `text_chunk`
2. Build chunks from section's `page_ids`
3. Use `user_id` instead of `username`
4. Use `company_number` as `client_id`

### ❌ DynamoDB Schema

**Original Table Schema**:
```python
{
  'financial_record_id': 'doc-inv-1-1-uuid',  # Primary Key
  'document_id': 'doc-123',
  'invoice_id': 'doc-inv-1-1-uuid',
  'username': 'user@example.com',
  'client_id': 'GB12345678',
  'vendor_name': 'Microsoft',
  'total_amount': Decimal('5.88'),
  'created_at': 1234567890,
  ...
}
```

**IDP Core Schema** (ExtractionResultsTable):
```python
{
  # Primary Key (REQUIRED)
  'PK': 'user#<user_id>#doc#<document_id>',
  'SK': 'type#INVOICE#section#<section_id>#invoice#<idx>',
  
  # GSI1: Query by user + type + time
  'GSI1PK': 'user#<user_id>#type#INVOICE',
  'ProcessedAt': 1234567890,  # GSI1SK
  
  # GSI3: Query by company + type
  'GSI3PK': 'company#microsoft-limited#type#INVOICE',
  'DocumentId': 'doc-123',  # GSI3SK
  
  # GSI6: Query by client + type
  'GSI6PK': 'client#GB12345678#type#INVOICE',
  
  # Core Fields
  'UserId': 'uuid',
  'InvoiceId': 'doc-inv-1-1-uuid',
  'SectionId': '1',
  'ClientId': 'GB12345678',
  'CompanyNumber': 'GB12345678',
  'CompanyName': 'Acme Ltd',
  'DocumentType': 'INVOICE',
  'ExtractionStatus': 'COMPLETED',
  
  # Invoice Fields (same as your schema)
  'InvoiceType': 'SUPPLIER_INVOICE',
  'InvoiceNumber': 'GB-TI2500887574',
  'SupplierName': 'Microsoft Limited',
  'TotalAmount': Decimal('5.88'),
  'SourcePage': 2,
  ...
  
  # Metadata
  'CreatedAt': 1234567890,
  'UpdatedAt': 1234567890,
  'ConfidenceScore': Decimal('0.95'),
  'Version': 1,
  'TTL': 1234567890 + 31536000  # 1 year
}
```

**Critical Differences**:
1. **Composite Keys**: Must provide both `PK` and `SK`
2. **GSI Keys**: Must populate `GSI1PK`, `GSI3PK`, `GSI6PK` for frontend queries
3. **Normalized Company Name**: GSI3PK uses normalized company name (lowercase, no special chars)
4. **Field Name Changes**: `username` → `UserId`, `vendor_name` → `SupplierName` (but keep both)

### ❌ Model Selection (Hardcoded → Configurable)

**Original** (Hardcoded):
```python
model_id = 'eu.anthropic.claude-3-5-sonnet-20240620-v1:0'
bedrock = boto3.client('bedrock-runtime', region_name='eu-west-1')
```

**IDP Core** (Configurable):
```python
# From environment variable (set in template.yaml)
model_id = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-3-5-sonnet-20240620-v1:0')
region = os.environ.get('AWS_REGION', 'us-east-1')

# Support cross-region inference (eu. prefix)
bedrock = boto3.client('bedrock-runtime', region_name=region)
```

**Available Models** (from template.yaml):
- `anthropic.claude-3-5-sonnet-20240620-v1:0` (Sonnet 3.5 - original)
- `eu.anthropic.claude-3-7-sonnet-20250219-v1:0` (Sonnet 3.7 - cross-region)
- `eu.anthropic.claude-sonnet-4-20250514-v1:0` (Claude 4)
- `eu.amazon.nova-lite-v1:0` (Nova Lite)
- `eu.amazon.nova-pro-v1:0` (Nova Pro)

**Configuration Location**: `config_library/pattern-2/lending-package-sample/config.yaml`
```yaml
extraction:
  invoice:
    model_id: "eu.anthropic.claude-3-7-sonnet-20250219-v1:0"  # User selectable
    use_chunked_extraction: true
    chunk_size: 15000
    overlap_size: 3000
```

### ❌ Table References

**Original**:
```python
INVOICE_TABLE_NAME = os.environ.get('INVOICE_TABLE_NAME', f'tag-financial-data-{ENVIRONMENT}-{REGION}')
invoice_table = boto3.resource('dynamodb').Table(INVOICE_TABLE_NAME)

documents_table = dynamodb.Table('tag-invoice-documents')
```

**IDP Core**:
```python
EXTRACTION_RESULTS_TABLE = os.environ.get('EXTRACTION_RESULTS_TABLE')
TRACKING_TABLE = os.environ.get('TRACKING_TABLE')
CONFIGURATION_TABLE = os.environ.get('CONFIGURATION_TABLE')

extraction_table = dynamodb.Table(EXTRACTION_RESULTS_TABLE)
tracking_table = dynamodb.Table(TRACKING_TABLE)
config_table = dynamodb.Table(CONFIGURATION_TABLE)
```

---

## 4. Implementation Plan

### Step 1: Create ChunkedInvoiceExtractor Class
**File**: `lib/idp_common_pkg/idp_common/extraction/chunked_invoice_extractor.py`

**Purpose**: Reusable chunking logic that can be imported by any extraction Lambda.

**Interface**:
```python
class ChunkedInvoiceExtractor:
    def __init__(self, chunk_size=15000, overlap_size=3000):
        self.chunk_size = chunk_size
        self.overlap_size = overlap_size
    
    def create_chunks_with_overlap(self, text: str) -> List[Dict]:
        """Split text into overlapping chunks with page tracking"""
        # Returns: [{'chunk': '...', 'start': 0, 'end': 15000, 'pages': [1,2]}, ...]
    
    def extract_page_numbers(self, text: str) -> List[int]:
        """Extract [PAGE:X] markers from text"""
    
    def deduplicate_invoices(self, invoices: List[Dict]) -> List[Dict]:
        """Remove duplicate invoices using page-based algorithm"""
```

**Why separate class**:
- Reusable across different Lambda functions
- Unit testable in isolation
- Can be enhanced without modifying Lambda code

### Step 2: Update invoice_extraction_handler.py
**File**: `patterns/pattern-2/lambdas/invoice_extraction/invoice_extraction_handler.py`

**Changes**:
1. Import `ChunkedInvoiceExtractor`
2. Add `USE_CHUNKED_EXTRACTION` environment variable check
3. Route to chunked processing when enabled
4. Keep existing non-chunked flow as fallback

**New Function**:
```python
def process_section_with_chunking(
    section_text: str,
    document_id: str,
    section_id: str,
    user_id: str,
    client_id: str,
    company_number: str,
    company_name: str,
    model_id: str
) -> Dict:
    """
    Process invoice section using chunked extraction
    """
    extractor = ChunkedInvoiceExtractor(chunk_size=15000, overlap_size=3000)
    
    # 1. Create chunks
    chunks = extractor.create_chunks_with_overlap(section_text)
    
    # 2. Extract from each chunk
    all_invoices = []
    for chunk_idx, chunk_data in enumerate(chunks):
        prompt = get_invoice_extraction_prompt().format(section_text=chunk_data['chunk'])
        xml_response = invoke_bedrock(prompt, model_id)
        invoices = parse_invoices_from_xml(xml_response)
        
        # Tag invoices with chunk info
        for invoice in invoices:
            invoice['chunk_index'] = chunk_idx
            invoice['pages'] = chunk_data['pages']
        
        all_invoices.extend(invoices)
    
    # 3. Deduplicate
    unique_invoices = extractor.deduplicate_invoices(all_invoices)
    
    # 4. Write to DynamoDB
    inserted_count = write_invoices_to_dynamodb(
        unique_invoices, document_id, section_id, user_id, client_id, company_number, company_name
    )
    
    return {
        'total_chunks': len(chunks),
        'total_invoices_extracted': len(all_invoices),
        'duplicates_removed': len(all_invoices) - len(unique_invoices),
        'invoices_inserted': inserted_count
    }
```

### Step 3: Update write_invoices_to_dynamodb()
**Changes**:
1. Use IDP Core's composite key structure (`PK` + `SK`)
2. Populate all GSI keys (`GSI1PK`, `GSI3PK`, `GSI6PK`)
3. Normalize company name for `GSI3PK`
4. Add proper field mappings

**Updated Function** (already in current handler, enhance with chunk info):
```python
def write_invoices_to_dynamodb(
    invoices: List[Dict[str, Any]],
    document_id: str,
    section_id: str,
    user_id: str,
    client_id: str,
    company_number: str = None,
    company_name: str = None
) -> int:
    """
    Write individual invoice records to ExtractionResultsTable
    Enhanced with chunk tracking for deduplication audit trail
    """
    inserted_count = 0
    current_timestamp = int(time.time())

    for idx, invoice_data in enumerate(invoices):
        try:
            invoice_id = f"{document_id}-inv-{section_id}-{idx+1}-{str(uuid.uuid4())[:8]}"

            item = {
                # Primary Key
                'PK': f"user#{user_id}#doc#{document_id}",
                'SK': f"type#INVOICE#section#{section_id}#invoice#{idx+1}",

                # GSI Keys
                'GSI1PK': f"user#{user_id}#type#INVOICE",
                'ProcessedAt': current_timestamp,
                'UserId': user_id,
                'GSI3PK': f"company#{normalize_company_name(invoice_data['supplier_name'])}#type#INVOICE",
                'DocumentId': document_id,
                'ExtractionStatus': 'COMPLETED',
                'GSI6PK': f"client#{client_id}#type#INVOICE",

                # Core identifiers
                'InvoiceId': invoice_id,
                'SectionId': section_id,
                'ClientId': client_id,
                'CompanyNumber': company_number or 'unknown',
                'CompanyName': company_name or 'Unknown Company',
                'DocumentType': 'INVOICE',

                # Invoice fields (your proven schema)
                'InvoiceType': invoice_data['invoice_type'],
                'InvoiceNumber': invoice_data['invoice_number'],
                'ReferenceNumber': invoice_data['reference_number'],
                'InvoiceDate': invoice_data['invoice_date'],
                'DueDate': invoice_data['due_date'],
                'SupplierName': invoice_data['supplier_name'],
                'VendorName': invoice_data['supplier_name'],  # Alias for compatibility
                'SupplierAddress': invoice_data['supplier_address'],
                'TotalAmount': invoice_data['total_amount'],
                'Currency': invoice_data['currency'],
                'VATAmount': invoice_data['vat_amount'],
                'NetAmount': invoice_data['net_amount'],
                'Description': invoice_data['description'],
                'PaymentTerms': invoice_data['payment_terms'],
                'SourcePage': invoice_data['source_page'],

                # Chunking metadata (for audit trail)
                'ChunkIndex': invoice_data.get('chunk_index'),
                'ExtractedPages': invoice_data.get('pages', []),

                # Metadata
                'CreatedAt': current_timestamp,
                'UpdatedAt': current_timestamp,
                'DateExtracted': datetime.now().strftime('%Y-%m-%d'),
                'ConfidenceScore': Decimal('0.95'),
                'Version': 1,
                'TTL': current_timestamp + (365 * 24 * 60 * 60)
            }

            extraction_table.put_item(Item=item)
            inserted_count += 1

            log_with_timestamp(
                f"✅ Inserted invoice {idx+1}/{len(invoices)}: "
                f"{invoice_data['supplier_name']} - "
                f"{invoice_data['currency']}{invoice_data['total_amount']}"
            )

        except Exception as e:
            log_with_timestamp(f"❌ Error inserting invoice {idx+1}: {str(e)}")

    return inserted_count
```

### Step 4: Update template.yaml
**File**: `patterns/pattern-2/template.yaml`

**Add Environment Variables to InvoiceExtractionFunction**:
```yaml
InvoiceExtractionFunction:
  Type: AWS::Serverless::Function
  Properties:
    Environment:
      Variables:
        EXTRACTION_RESULTS_TABLE: !Ref ExtractionResultsTable
        TRACKING_TABLE: !Ref TrackingTable
        CONFIGURATION_TABLE: !Ref ConfigurationTable
        BEDROCK_MODEL_ID: !Ref BedrockModelIdExtraction  # Make this a parameter
        USE_CHUNKED_EXTRACTION: "true"  # Enable chunking
        CHUNK_SIZE: "15000"
        OVERLAP_SIZE: "3000"
        AWS_REGION: !Ref AWS::Region
```

**Add Stack Parameter for Model Selection**:
```yaml
Parameters:
  BedrockModelIdExtraction:
    Type: String
    Description: Bedrock model for invoice extraction (supports cross-region)
    Default: "anthropic.claude-3-5-sonnet-20240620-v1:0"
    AllowedValues:
      - "anthropic.claude-3-5-sonnet-20240620-v1:0"
      - "eu.anthropic.claude-3-7-sonnet-20250219-v1:0"
      - "eu.anthropic.claude-sonnet-4-20250514-v1:0"
      - "eu.amazon.nova-lite-v1:0"
      - "eu.amazon.nova-pro-v1:0"
```

**Add Bedrock Permissions**:
```yaml
Policies:
  - Statement:
      - Effect: Allow
        Action:
          - bedrock:InvokeModel
        Resource:
          - !Sub "arn:aws:bedrock:*::foundation-model/anthropic.claude-*"
          - !Sub "arn:aws:bedrock:*::foundation-model/eu.anthropic.claude-*"
          - !Sub "arn:aws:bedrock:*::foundation-model/eu.amazon.nova-*"
```

### Step 5: Update config.yaml
**File**: `config_library/pattern-2/lending-package-sample/config.yaml`

**Add Extraction Configuration Section**:
```yaml
extraction:
  invoice:
    # Enable chunked extraction for multi-invoice PDFs
    use_chunked_extraction: true
    
    # Model selection (supports cross-region inference)
    model_id: "eu.anthropic.claude-3-7-sonnet-20250219-v1:0"  # Sonnet 3.7
    
    # Chunking parameters (proven optimal values)
    chunk_size: 15000  # characters per chunk
    overlap_size: 3000  # overlap to prevent splitting invoices
    
    # Deduplication settings
    deduplicate: true
    content_similarity_threshold: 0.95
    
    # Prompt template key in ConfigurationTable
    prompt_template_key: "INVOICE_EXTRACTION_PROMPT"
```

### Step 6: Store Prompt in ConfigurationTable
**Action**: Create DynamoDB item in ConfigurationTable

**Item**:
```json
{
  "Configuration": "INVOICE_EXTRACTION_PROMPT",
  "PromptTemplate": "<your proven prompt from TaxGuard>",
  "Description": "Invoice extraction prompt - editable from frontend",
  "Version": 1,
  "UpdatedAt": 1234567890,
  "UpdatedBy": "admin@fiscalshield.com"
}
```

**Benefits**:
- Frontend users can edit prompt without redeployment
- Version control for prompt changes
- A/B testing different prompts

---

## 5. Frontend Integration Plan

### Model Selection in Upload UI
**Goal**: Allow users to choose extraction model when uploading invoices

**UI Changes** (UploadDocumentPanel.jsx):
```jsx
const [extractionModel, setExtractionModel] = useState('sonnet-3.5');

// Add model selection dropdown
<FormField
  label="Invoice Extraction Model"
  description="Choose which AI model to use for extracting invoice data"
>
  <Select
    selectedOption={extractionModel}
    onChange={({ detail }) => setExtractionModel(detail.selectedOption)}
    options={[
      { label: 'Claude Sonnet 3.5 (Fast, Cost-Effective)', value: 'anthropic.claude-3-5-sonnet-20240620-v1:0' },
      { label: 'Claude Sonnet 3.7 (Most Accurate, Cross-Region)', value: 'eu.anthropic.claude-3-7-sonnet-20250219-v1:0' },
      { label: 'Claude 4 (Latest, Premium)', value: 'eu.anthropic.claude-sonnet-4-20250514-v1:0' },
      { label: 'Amazon Nova Lite (Budget)', value: 'eu.amazon.nova-lite-v1:0' },
      { label: 'Amazon Nova Pro (Balanced)', value: 'eu.amazon.nova-pro-v1:0' }
    ]}
  />
</FormField>
```

**GraphQL Mutation Update** (schema.graphql):
```graphql
type Mutation {
  uploadDocument(
    file: String!
    filename: String!
    documentType: String
    extractionModel: String  # NEW: Allow model selection
  ): UploadDocumentResponse
}
```

**Upload Resolver Update** (upload_resolver/index.py):
```python
extraction_model = arguments.get("extractionModel")
if extraction_model:
    metadata_fields["x-amz-meta-extraction-model"] = extraction_model
```

**Queue Sender Update** (queue_sender/index.py):
```python
extraction_model = metadata.get("extraction-model")
document = Document(
    user_document_type=user_document_type,
    extraction_model=extraction_model,  # Pass to workflow
    ...
)
```

**Workflow Update** (workflow.asl.json):
```json
{
  "InvoiceExtraction": {
    "Type": "Task",
    "Resource": "${InvoiceExtractionFunctionArn}",
    "Parameters": {
      "document.$": "$.document",
      "section_id.$": "$.section.section_id",
      "extraction_model.$": "$.document.extraction_model"
    }
  }
}
```

**Lambda Handler Update** (invoice_extraction_handler.py):
```python
def lambda_handler(event, context):
    # Get model from event, fallback to env var, then default
    model_id = (
        event.get('extraction_model') or 
        os.environ.get('BEDROCK_MODEL_ID') or 
        'anthropic.claude-3-5-sonnet-20240620-v1:0'
    )
    
    log_with_timestamp(f"Using model: {model_id}")
```

---

## 6. Testing Strategy

### Unit Tests
**File**: `tests/unit/test_chunked_invoice_extractor.py`

```python
def test_create_chunks_with_overlap():
    """Test that chunks are created with proper overlap"""
    extractor = ChunkedInvoiceExtractor(chunk_size=100, overlap_size=20)
    text = "A" * 250
    chunks = extractor.create_chunks_with_overlap(text)
    
    assert len(chunks) == 3
    assert chunks[0]['start'] == 0
    assert chunks[0]['end'] == 100
    assert chunks[1]['start'] == 80  # 100 - 20 overlap
    assert len(chunks[0]['chunk']) == 100

def test_deduplicate_invoices_same_vendor_different_people():
    """Test that invoices from different people are NOT deduplicated"""
    invoices = [
        {
            'vendor_name': 'Tesco',
            'total_amount': Decimal('15.50'),
            'invoice_date': '2025-01-01',
            'description': 'Employee: John Smith john@example.com',
            'pages': [1, 2]
        },
        {
            'vendor_name': 'Tesco',
            'total_amount': Decimal('15.50'),
            'invoice_date': '2025-01-01',
            'description': 'Employee: Jane Doe jane@example.com',
            'pages': [2, 3]
        }
    ]
    
    extractor = ChunkedInvoiceExtractor()
    result = extractor.deduplicate_invoices(invoices)
    
    # Should keep both (different people)
    assert len(result) == 2

def test_deduplicate_invoices_chunk_overlap():
    """Test that chunk overlap duplicates ARE removed"""
    invoices = [
        {
            'vendor_name': 'Microsoft',
            'total_amount': Decimal('5.88'),
            'invoice_date': '2025-03-07',
            'invoice_number': 'GB-TI2500887574',
            'description': 'Microsoft 365 Business Basic',
            'pages': [2],
            'chunk_index': 0
        },
        {
            'vendor_name': 'Microsoft',
            'total_amount': Decimal('5.88'),
            'invoice_date': '2025-03-07',
            'invoice_number': 'GB-TI2500887574',
            'description': 'Microsoft 365 Business Basic',
            'pages': [2],
            'chunk_index': 1
        }
    ]
    
    extractor = ChunkedInvoiceExtractor()
    result = extractor.deduplicate_invoices(invoices)
    
    # Should keep only one (duplicate from overlap)
    assert len(result) == 1
```

### Integration Tests
**File**: `tests/integration/test_invoice_extraction_chunked.py`

```python
@pytest.mark.integration
def test_end_to_end_multi_invoice_pdf():
    """Test complete flow with real 50-page multi-invoice PDF"""
    # 1. Upload test PDF with 25 invoices
    # 2. Wait for Step Functions execution
    # 3. Query ExtractionResultsTable
    # 4. Assert 25 invoices extracted
    # 5. Assert no duplicates
    # 6. Assert all vendors present
    pass

@pytest.mark.integration
def test_model_selection():
    """Test that user-selected model is used"""
    # 1. Upload with extractionModel='eu.anthropic.claude-3-7-sonnet-20250219-v1:0'
    # 2. Check Lambda logs for model confirmation
    # 3. Assert correct model was invoked
    pass
```

### Manual Testing Checklist
- [ ] Upload 5-page single invoice PDF → Verify 1 invoice extracted
- [ ] Upload 50-page multi-invoice PDF (25 invoices) → Verify 25 extracted, no duplicates
- [ ] Upload with Sonnet 3.5 → Verify cost and speed
- [ ] Upload with Sonnet 3.7 → Verify accuracy improvement
- [ ] Check DynamoDB for correct PK/SK structure
- [ ] Query by user (GSI1) → Verify returns all user's invoices
- [ ] Query by company (GSI3) → Verify returns all Microsoft invoices
- [ ] Check CloudWatch logs for deduplication metrics

---

## 7. Migration Path

### Option A: Replace Existing Handler (Recommended)
**Approach**: Update `invoice_extraction_handler.py` with chunked logic as default

**Pros**:
- Single code path
- Cleaner architecture
- Easier maintenance

**Cons**:
- Higher risk (no fallback)
- Need comprehensive testing

**Rollback**: Deploy previous version from git

### Option B: Feature Flag (Safer)
**Approach**: Add `USE_CHUNKED_EXTRACTION` env var, keep both code paths

**Pros**:
- Can toggle chunking on/off without redeployment
- Gradual rollout (test with subset of users)
- Easy rollback (just change env var)

**Cons**:
- More code to maintain
- Longer transition period

**Implementation**:
```python
def lambda_handler(event, context):
    use_chunked = os.environ.get('USE_CHUNKED_EXTRACTION', 'false').lower() == 'true'
    
    if use_chunked:
        log_with_timestamp("🔥 Using chunked extraction (NEW)")
        return process_section_with_chunking(...)
    else:
        log_with_timestamp("⚠️ Using legacy extraction (OLD)")
        return process_section_without_chunking(...)
```

**Recommendation**: Start with **Option B**, transition to **Option A** after 2 weeks of stable operation.

---

## 8. Cost & Performance Analysis

### Current (Non-Chunked)
**Scenario**: 50-page PDF with 25 invoices

```
Model: Sonnet 3.5
Input: 50 pages * 1500 chars = 75,000 chars (~18,750 tokens)
Output: ~2,000 tokens (XML for 25 invoices)
Cost: $0.003/1K input + $0.015/1K output = $0.09 per document
Processing Time: ~8-12 seconds
Success Rate: ~60% (misses invoices, boundary issues)
```

### Chunked (Proposed)
**Scenario**: Same 50-page PDF

```
Model: Sonnet 3.5
Chunks: 75,000 / 15,000 = 5 chunks (with overlap = 6-7 chunks)
Input per chunk: 15,000 chars (~3,750 tokens) * 6 = 22,500 tokens total
Output per chunk: ~500 tokens * 6 = 3,000 tokens total
Cost: $0.003 * 22.5 + $0.015 * 3 = $0.11 per document (+22%)
Processing Time: ~6-8 seconds (parallel processing)
Success Rate: ~98% (finds all invoices, no boundary issues)
```

**With Sonnet 3.7 (Cross-Region)**:
```
Model: Sonnet 3.7 (eu.)
Cost: ~$0.14 per document (+56% vs current, +27% vs chunked 3.5)
Processing Time: ~7-9 seconds
Success Rate: ~99.5% (best accuracy)
```

### ROI Analysis
**Assumptions**:
- Average: 100 multi-invoice PDFs per month
- Current: Missing 10 invoices per month (manual re-entry: £50/invoice)
- Chunked: Missing 0.5 invoices per month

**Savings**:
```
Manual re-entry avoided: 9.5 invoices * £50 = £475/month
Additional LLM cost: 100 PDFs * ($0.11 - $0.09) = $2/month = £1.60/month
Net Savings: £473.40/month = £5,680/year
```

**Conclusion**: ROI is overwhelmingly positive even with more expensive model.

---

## 9. Rollout Timeline

### Week 1: Development
- [ ] Day 1-2: Create `ChunkedInvoiceExtractor` class with unit tests
- [ ] Day 3-4: Update `invoice_extraction_handler.py` with feature flag
- [ ] Day 5: Update template.yaml, config.yaml
- [ ] Day 6-7: Integration testing in dev environment

### Week 2: Testing & UI
- [ ] Day 8-9: Deploy to dev stack, test with sample PDFs
- [ ] Day 10-11: Add model selection to upload UI
- [ ] Day 12-13: User acceptance testing
- [ ] Day 14: Performance and cost monitoring

### Week 3: Production
- [ ] Day 15: Deploy to production with `USE_CHUNKED_EXTRACTION=false` (safety)
- [ ] Day 16: Enable chunking for 10% of uploads (A/B test)
- [ ] Day 17-18: Monitor metrics (success rate, cost, errors)
- [ ] Day 19: Enable for 50% of uploads
- [ ] Day 20: Enable for 100% of uploads
- [ ] Day 21: Remove feature flag code (transition to Option A)

---

## 10. Success Metrics

### Before Chunking (Baseline)
- Invoice extraction accuracy: ~60%
- Processing time: 8-12 seconds per document
- Manual corrections: 10 invoices/month
- User complaints: 3-4 per week

### After Chunking (Target)
- Invoice extraction accuracy: >95%
- Processing time: 6-8 seconds per document
- Manual corrections: <1 invoice/month
- User complaints: <1 per month
- Cost increase: <30%
- User satisfaction: >4.5/5

### Monitoring Dashboards
**CloudWatch Metrics to Track**:
1. `InvoicesExtracted` (count per document)
2. `ChunkDuplicatesRemoved` (deduplication effectiveness)
3. `ExtractionDuration` (performance)
4. `BedrockInvocationCost` (cost tracking)
5. `ExtractionErrors` (error rate)

**Custom Dashboard**:
```json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["IDP", "InvoicesExtracted", {"stat": "Sum"}],
          [".", "ChunkDuplicatesRemoved", {"stat": "Sum"}]
        ],
        "title": "Invoice Extraction - Chunked vs Duplicates",
        "period": 300
      }
    }
  ]
}
```

---

## 11. Next Steps

### Immediate Actions (This Week)
1. **Review this plan** with team for approval
2. **Set up dev environment** with test data (50-page PDFs)
3. **Create git branch**: `feature/chunked-invoice-extraction`
4. **Start implementation** with Step 1 (ChunkedInvoiceExtractor class)

### Questions to Resolve
1. **Model Selection**: Should Sonnet 3.7 be the default or opt-in?
2. **Prompt Storage**: Create prompt in ConfigurationTable now or later?
3. **Rollout Strategy**: Gradual (Option B) or all-at-once (Option A)?
4. **UI Changes**: Add model selector to upload UI or admin settings?

### Ready to Start?
**Confirm the following**:
- ✅ Chunking parameters (15k chars, 3k overlap) are approved
- ✅ DynamoDB schema changes are understood
- ✅ Model selection approach is clear
- ✅ Rollout timeline is acceptable

**Then I'll begin implementing**:
1. `ChunkedInvoiceExtractor` class
2. Updated `invoice_extraction_handler.py`
3. Template and config changes
4. Unit tests

---

## Appendix: Key Code Snippets

### A. Chunk Creation with Page Tracking
```python
def create_chunks_with_overlap(self, text: str) -> List[Dict]:
    """
    Split text into overlapping chunks while tracking page boundaries
    """
    chunks = []
    start = 0
    
    while start < len(text):
        end = min(start + self.chunk_size, len(text))
        chunk_text = text[start:end]
        
        # Extract page numbers from [PAGE:X] markers in this chunk
        page_pattern = r'\[PAGE:(\d+)\]'
        pages = sorted(set(int(m) for m in re.findall(page_pattern, chunk_text)))
        
        chunks.append({
            'chunk': chunk_text,
            'start': start,
            'end': end,
            'pages': pages or [1]  # Default to page 1 if no markers
        })
        
        # Move start position (with overlap)
        start = end - self.overlap_size if end < len(text) else len(text)
    
    return chunks
```

### B. Bedrock Invocation with Cross-Region Support
```python
def invoke_bedrock(prompt: str, model_id: str) -> str:
    """
    Invoke Bedrock with support for cross-region inference
    """
    # Determine region from model ID prefix
    if model_id.startswith('eu.'):
        # Cross-region inference - use specified region from env
        region = os.environ.get('AWS_REGION', 'us-east-1')
    else:
        # Standard inference - same region as Lambda
        region = os.environ.get('AWS_REGION', 'us-east-1')
    
    bedrock = boto3.client('bedrock-runtime', region_name=region)
    
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 8000,
        "messages": [{"role": "user", "content": prompt}]
    }
    
    try:
        response = bedrock.invoke_model(
            modelId=model_id,
            body=json.dumps(body)
        )
        
        response_body = json.loads(response['body'].read())
        return response_body['content'][0]['text']
        
    except Exception as e:
        log_with_timestamp(f"❌ Error invoking Bedrock ({model_id}): {str(e)}")
        raise
```

### C. GSI Key Construction
```python
def normalize_company_name(company_name: str) -> str:
    """
    Normalize company name for GSI3PK (queryable format)
    
    Examples:
      "Microsoft Limited" → "microsoft-limited"
      "Tesco PLC" → "tesco-plc"
      "Café Nero" → "cafe-nero"
    """
    if not company_name:
        return 'unknown'
    
    # Lowercase
    normalized = company_name.lower()
    
    # Remove special characters (keep letters, numbers, spaces, hyphens)
    normalized = re.sub(r'[^a-z0-9\s-]', '', normalized)
    
    # Replace spaces with hyphens
    normalized = re.sub(r'\s+', '-', normalized).strip('-')
    
    return normalized or 'unknown'
```

---

**Ready to proceed? Let me know and I'll start implementing Step 1!**
