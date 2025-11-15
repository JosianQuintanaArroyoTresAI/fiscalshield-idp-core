# Testing Guide for Validation Logging and Hallucination Prevention

This directory contains critical tests for the validation logging system and LLM hallucination prevention features.

## Test Coverage

### 1. Classification Validation Logging (`tests/unit/classification/test_validation_logging.py`)

Tests the validation logging system that compares user document type hints against model predictions:

- **Validation Record Creation**: Tests that validation records are created in DynamoDB
- **Match vs Mismatch Logic**: Verifies correct comparison of user hint vs model prediction
- **Decimal Conversion**: Tests float→Decimal conversion for DynamoDB compatibility
- **User Hint Routing**: Tests trust_user_hint and validate_hint_on_mismatch configurations
- **Document.pages Dict Iteration**: Tests correct iteration of pages dictionary
- **Metadata Setting**: Verifies classification metadata is set correctly

**Run:** `pytest tests/unit/classification/test_validation_logging.py -v`

### 2. LLM Hallucination Prevention (`tests/unit/extraction/test_hallucination_prevention.py`)

Tests the extraction prompt safeguards that prevent the model from copying example transactions:

- **Document Type Check**: Verifies prompt has critical document type check
- **Example Warnings**: Tests that prompt warns model not to copy examples
- **Empty XML Format**: Verifies prompt shows how to return empty results
- **Invoice Handling**: Tests explicit instructions for non-bank-statement documents
- **XML Parsing**: Tests parsing of empty and populated transaction XML
- **Extraction Storage**: Tests correct DynamoDB record structure

**Run:** `pytest tests/unit/extraction/test_hallucination_prevention.py -v`

### 3. PyYAML None Handling (`lib/idp_common_pkg/tests/unit/test_yaml_none_handling.py`)

Tests the fix for AttributeError when PyYAML is not installed in Lambda:

- **yaml=None Handling**: Tests graceful handling when PyYAML unavailable
- **No AttributeError**: Verifies no AttributeError on yaml.YAMLError access
- **JSON Fallback**: Tests fallback to JSON parsing when YAML unavailable
- **Safe isinstance Checks**: Tests safe pattern for checking YAMLError
- **Classification Parsing**: Tests that classification works without PyYAML
- **No "Unclassified" Error**: Verifies parsing errors don't cause "unclassified" result

**Run:** `pytest lib/idp_common_pkg/tests/unit/test_yaml_none_handling.py -v`

### 4. Integration Tests (`tests/integration/test_validation_workflow.py`)

End-to-end integration tests for the complete validation workflow:

- **Validation Workflow**: Tests user hint vs model prediction comparison
- **trust_user_hint**: Tests LLM skip behavior
- **validate_hint_on_mismatch**: Tests LLM run + user hint routing
- **Hallucination Prevention**: Tests invoice→bank-statement returns empty
- **Document Routing**: Tests correct Lambda routing based on classification
- **Data Integrity**: Tests DynamoDB Decimal conversion and TTL

**Run:** `pytest tests/integration/test_validation_workflow.py -v`

## Running All Tests

```bash
# Run all validation-related tests
pytest tests/unit/classification/test_validation_logging.py \
       tests/unit/extraction/test_hallucination_prevention.py \
       lib/idp_common_pkg/tests/unit/test_yaml_none_handling.py \
       tests/integration/test_validation_workflow.py -v

# Run with coverage
pytest tests/unit/classification/test_validation_logging.py \
       tests/unit/extraction/test_hallucination_prevention.py \
       lib/idp_common_pkg/tests/unit/test_yaml_none_handling.py \
       tests/integration/test_validation_workflow.py \
       --cov=patterns.pattern_2.src.classification_function \
       --cov=patterns.pattern_2.lambdas.bank_statement_extraction \
       --cov=lib.idp_common_pkg.idp_common.utils \
       --cov-report=html

# Run only unit tests
pytest tests/unit/classification/ tests/unit/extraction/ lib/idp_common_pkg/tests/unit/test_yaml_none_handling.py -v -m unit

# Run only integration tests
pytest tests/integration/test_validation_workflow.py -v -m integration
```

## Key Test Scenarios

### Scenario 1: User Hint Matches Model
- User selects "invoice"
- Model classifies as "invoice"
- ValidationMatch = True
- Document routes to InvoiceExtraction

### Scenario 2: User Hint Differs from Model
- User selects "bank-statement"
- Model classifies as "invoice"
- ValidationMatch = False
- validate_hint_on_mismatch=true → routes using user hint (GenericExtraction)
- Validation record logs mismatch for metrics

### Scenario 3: Hallucination Prevention
- Invoice uploaded with user_hint="bank-statement"
- Extraction Lambda runs
- Prompt instructs: return empty if not bank statement
- Model returns: `<bank_statement><transactions></transactions></bank_statement>`
- DynamoDB stores: TransactionCount = 0
- **NO** hallucinated example transactions (862834451961-CHB, PAYPAL, TESCO)

### Scenario 4: PyYAML Not Available
- Lambda environment without PyYAML
- Classification response in JSON format
- Code checks: `if yaml is not None` before accessing `yaml.YAMLError`
- Parsing succeeds with JSON
- **NO** AttributeError
- **NO** fallback to "unclassified"

## Critical Fixes Tested

1. **Decimal Conversion** (commit e8f8eb4e)
   - Float → Decimal for DynamoDB ModelConfidence
   - Fixes: "Float types are not supported" error

2. **User Hint Routing** (commit b82086fe)
   - validate_hint_on_mismatch uses user hint for routing
   - Runs LLM for validation metrics
   - Fixes: Documents routed based on user selection while collecting model predictions

3. **Dict Iteration** (commit 37eca6f4)
   - document.pages.items() not document.pages
   - Fixes: AttributeError 'str' object has no attribute 'classification'

4. **PyYAML Handling** (commit 392551eb)
   - Check `if yaml is not None` before yaml.YAMLError
   - Fixes: AttributeError when PyYAML not installed
   - Fixes: "unclassified" results from parsing failures

5. **Hallucination Prevention** (commit 5348b398)
   - Document type check in prompt
   - Example warnings before/after sample data
   - Empty XML format shown
   - Fixes: Model copying example transactions from prompt

## Configuration Requirements

For tests to pass, configuration should have:

```yaml
classification:
  trust_user_hint: false              # Run LLM for validation
  validate_hint_on_mismatch: true     # Use user hint for routing
```

## Environment Variables

Tests mock these environment variables:

- `VALIDATION_REQUESTS_TABLE`: DynamoDB table for validation records
- `CONFIG_TABLE`: Configuration table
- `TRACKING_TABLE`: Classification tracking
- `WORKING_BUCKET`: S3 bucket for document storage
- `REGION`: AWS region

## Test Data

Example validation record structure:
```python
{
    "PK": "validation#<uuid>",
    "SK": "doc#users/user-id/document.pdf",
    "ValidationId": "<uuid>",
    "DocumentId": "users/user-id/document.pdf",
    "UserId": "user-id",
    "CompanyNumber": "12345678",
    "CompanyName": "Company Name",
    "UserSelection": "invoice",
    "ModelPrediction": "bank-statement",
    "ModelConfidence": Decimal("0.95"),
    "ValidationMatch": False,
    "ValidationStatus": "auto_logged",
    "CreatedAt": 1234567890,
    "TTL": 1266103890
}
```

## Metrics Collection

These tests enable collection of:
- **Accuracy**: % of ValidationMatch=True records
- **Precision/Recall**: Per document type (invoice, bank-statement)
- **Confidence Distribution**: ModelConfidence values when match vs mismatch
- **Drift Detection**: User behavior vs model predictions over time

## Maintenance

When modifying:
- **Classification Logic**: Update `test_validation_logging.py`
- **Extraction Prompts**: Update `test_hallucination_prevention.py`
- **Parsing Logic**: Update `test_yaml_none_handling.py`
- **End-to-End Flow**: Update `test_validation_workflow.py`

## CI/CD Integration

Add to `.github/workflows/test.yml`:
```yaml
- name: Run Validation Tests
  run: |
    pytest tests/unit/classification/test_validation_logging.py \
           tests/unit/extraction/test_hallucination_prevention.py \
           lib/idp_common_pkg/tests/unit/test_yaml_none_handling.py \
           tests/integration/test_validation_workflow.py \
           --cov --cov-report=xml
```
