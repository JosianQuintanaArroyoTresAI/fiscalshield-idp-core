"""
Critical Unit Tests for Invoice Categorization Lambda - Two-Stage Architecture

Tests the most important business logic for invoice tax deductibility analysis:
- Two-stage processing logic (Stage 1 classification → Stage 2 deep testing)
- Partial success handling (per-invoice error resilience)
- Progressive DynamoDB updates
- Filtering logic (NeedsDeepTesting flag)
- Error handling and recovery

These tests ensure the two-stage architecture and partial success handling work correctly.
Priority 1 & 2 tests as identified in optimization review.
"""
import pytest
import sys
import json
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal

# Mock AWS services BEFORE importing handler (boto3 not available in test environment)
mock_boto3 = MagicMock()
mock_dynamodb = MagicMock()
mock_bedrock = MagicMock()
mock_boto3.resource.return_value = mock_dynamodb
mock_boto3.client.return_value = mock_bedrock
sys.modules['boto3'] = mock_boto3

# Add invoice categorization handler to path
CATEGORIZATION_PATH = Path(__file__).parent.parent.parent.parent / 'stacks' / 'analysis' / 'lambdas' / 'invoice_categorization'
sys.path.insert(0, str(CATEGORIZATION_PATH))

from handler import (
    parse_stage1_classification,
    parse_stage2_deep_testing,
    MODEL_ID
)


# =============================================================================
# PRIORITY 1: TWO-STAGE LOGIC TESTS
# =============================================================================

@pytest.mark.unit
class TestStage1ClassificationParsing:
    """Critical tests for Stage 1 classification parsing logic."""
    
    def test_supplier_invoice_fully_deductible_no_deep_testing(self):
        """
        CRITICAL: SUPPLIER_INVOICE for business goods should be:
        - FULLY_DEDUCTIBLE (100%)
        - needs_deep_testing: false (skip Stage 2)
        """
        # Mock LLM response
        llm_response = json.dumps({
            "classifications": [{
                "invoice_id": "INV-001",
                "status": "FULLY_DEDUCTIBLE",
                "percentage": 100,
                "needs_deep_testing": False,
                "reason": "Business supplies"
            }]
        })
        
        # Invoice batch
        invoice_batch = [{
            'InvoiceId': 'INV-001',
            'InvoiceType': 'SUPPLIER_INVOICE',
            'SupplierName': 'Office Depot',
            'TotalAmount': 150.00,
            'Description': 'Office supplies',
            'PK': 'client#12345#type#INVOICE',
            'SK': 'invoice#INV-001'
        }]
        
        # Parse
        result = parse_stage1_classification(llm_response, invoice_batch)
        
        # Assertions
        assert len(result) == 1
        assert result[0]['DeductibilityStatus'] == 'FULLY_DEDUCTIBLE'
        assert result[0]['DeductibilityPercentage'] == 100
        assert result[0]['NeedsDeepTesting'] is False  # Should skip Stage 2
        assert result[0]['AnalysisStatus'] == 'ANALYZED'
        assert result[0]['AnalysisStage'] == 'STAGE1_CLASSIFICATION'
        assert result[0]['ModelUsed'] == MODEL_ID
        assert 'AnalyzedAt' in result[0]
    
    def test_obvious_personal_not_deductible_no_deep_testing(self):
        """
        CRITICAL: Obvious personal expenses should be:
        - NOT_DEDUCTIBLE (0%)
        - needs_deep_testing: false (skip Stage 2)
        """
        llm_response = json.dumps({
            "classifications": [{
                "invoice_id": "INV-002",
                "status": "NOT_DEDUCTIBLE",
                "percentage": 0,
                "needs_deep_testing": False,
                "reason": "Personal gym membership"
            }]
        })
        
        invoice_batch = [{
            'InvoiceId': 'INV-002',
            'InvoiceType': 'EXPENSE_CLAIM',
            'SupplierName': 'Gym Ltd',
            'TotalAmount': 50.00,
            'Description': 'Monthly gym membership',
            'PK': 'client#12345#type#INVOICE',
            'SK': 'invoice#INV-002'
        }]
        
        result = parse_stage1_classification(llm_response, invoice_batch)
        
        assert len(result) == 1
        assert result[0]['DeductibilityStatus'] == 'NOT_DEDUCTIBLE'
        assert result[0]['DeductibilityPercentage'] == 0
        assert result[0]['NeedsDeepTesting'] is False
        assert result[0]['AnalysisStage'] == 'STAGE1_CLASSIFICATION'
    
    def test_expense_claim_requires_review_needs_deep_testing(self):
        """
        CRITICAL: EXPENSE_CLAIM with unclear deductibility should be:
        - REQUIRES_REVIEW (null %)
        - needs_deep_testing: true (go to Stage 2)
        """
        llm_response = json.dumps({
            "classifications": [{
                "invoice_id": "INV-003",
                "status": "REQUIRES_REVIEW",
                "percentage": None,
                "needs_deep_testing": True,
                "reason": "Business travel - needs BIM compliance check"
            }]
        })
        
        invoice_batch = [{
            'InvoiceId': 'INV-003',
            'InvoiceType': 'EXPENSE_CLAIM',
            'SupplierName': 'Uber',
            'TotalAmount': 45.00,
            'Description': 'Taxi to client meeting',
            'PK': 'client#12345#type#INVOICE',
            'SK': 'invoice#INV-003'
        }]
        
        result = parse_stage1_classification(llm_response, invoice_batch)
        
        assert len(result) == 1
        assert result[0]['DeductibilityStatus'] == 'REQUIRES_REVIEW'
        assert result[0]['DeductibilityPercentage'] is None
        assert result[0]['NeedsDeepTesting'] is True  # Should go to Stage 2
        assert result[0]['AnalysisStage'] == 'STAGE1_CLASSIFICATION'
    
    def test_mixed_batch_classification(self):
        """
        CRITICAL: Mixed batch should classify each invoice correctly:
        - SUPPLIER_INVOICE → FULLY_DEDUCTIBLE, no deep testing
        - Personal EXPENSE_CLAIM → NOT_DEDUCTIBLE, no deep testing  
        - Unclear EXPENSE_CLAIM → REQUIRES_REVIEW, needs deep testing
        """
        llm_response = json.dumps({
            "classifications": [
                {
                    "invoice_id": "INV-100",
                    "status": "FULLY_DEDUCTIBLE",
                    "percentage": 100,
                    "needs_deep_testing": False,
                    "reason": "Business software"
                },
                {
                    "invoice_id": "INV-101",
                    "status": "NOT_DEDUCTIBLE",
                    "percentage": 0,
                    "needs_deep_testing": False,
                    "reason": "Personal clothing"
                },
                {
                    "invoice_id": "INV-102",
                    "status": "REQUIRES_REVIEW",
                    "percentage": None,
                    "needs_deep_testing": True,
                    "reason": "Entertainment - need to verify business purpose"
                }
            ]
        })
        
        invoice_batch = [
            {
                'InvoiceId': 'INV-100',
                'InvoiceType': 'SUPPLIER_INVOICE',
                'SupplierName': 'Adobe',
                'TotalAmount': 600.00,
                'Description': 'Annual software license',
                'PK': 'client#12345#type#INVOICE',
                'SK': 'invoice#INV-100'
            },
            {
                'InvoiceId': 'INV-101',
                'InvoiceType': 'EXPENSE_CLAIM',
                'SupplierName': 'Next',
                'TotalAmount': 150.00,
                'Description': 'Casual clothes',
                'PK': 'client#12345#type#INVOICE',
                'SK': 'invoice#INV-101'
            },
            {
                'InvoiceId': 'INV-102',
                'InvoiceType': 'EXPENSE_CLAIM',
                'SupplierName': 'Restaurant',
                'TotalAmount': 200.00,
                'Description': 'Client dinner',
                'PK': 'client#12345#type#INVOICE',
                'SK': 'invoice#INV-102'
            }
        ]
        
        result = parse_stage1_classification(llm_response, invoice_batch)
        
        assert len(result) == 3
        
        # Invoice 100: SUPPLIER_INVOICE
        assert result[0]['InvoiceId'] == 'INV-100'
        assert result[0]['NeedsDeepTesting'] is False
        assert result[0]['DeductibilityStatus'] == 'FULLY_DEDUCTIBLE'
        
        # Invoice 101: Personal
        assert result[1]['InvoiceId'] == 'INV-101'
        assert result[1]['NeedsDeepTesting'] is False
        assert result[1]['DeductibilityStatus'] == 'NOT_DEDUCTIBLE'
        
        # Invoice 102: Needs review
        assert result[2]['InvoiceId'] == 'INV-102'
        assert result[2]['NeedsDeepTesting'] is True
        assert result[2]['DeductibilityStatus'] == 'REQUIRES_REVIEW'
    
    def test_markdown_code_block_removal(self):
        """
        CRITICAL: LLM sometimes wraps JSON in markdown.
        Parser should handle ```json ... ``` wrapping.
        """
        llm_response = """```json
{
  "classifications": [{
    "invoice_id": "INV-004",
    "status": "FULLY_DEDUCTIBLE",
    "percentage": 100,
    "needs_deep_testing": false,
    "reason": "Business expense"
  }]
}
```"""
        
        invoice_batch = [{
            'InvoiceId': 'INV-004',
            'InvoiceType': 'SUPPLIER_INVOICE',
            'SupplierName': 'Vendor',
            'TotalAmount': 100.00,
            'PK': 'client#12345#type#INVOICE',
            'SK': 'invoice#INV-004'
        }]
        
        result = parse_stage1_classification(llm_response, invoice_batch)
        
        assert len(result) == 1
        assert result[0]['DeductibilityStatus'] == 'FULLY_DEDUCTIBLE'


@pytest.mark.unit
class TestStage2DeepTestingParsing:
    """Critical tests for Stage 2 deep testing parsing logic."""
    
    def test_stage2_parses_compliance_tests(self):
        """
        CRITICAL: Stage 2 should parse all 7 BIM compliance tests.
        """
        llm_response = json.dumps({
            "analyses": [{
                "invoice_id": "INV-200",
                "status": "PARTIALLY_DEDUCTIBLE",
                "percentage": 50,
                "reasoning": "Mixed business/personal use",
                "bim_sections": "BIM37000",
                "tests": {
                    "test_1": {"result": "PASS", "reasoning": "Wholly for business"},
                    "test_2": {"result": "NOT_APPLICABLE"},
                    "test_3": {"result": "BUSINESS_TRAVEL"},
                    "test_4": {"result": "NOT_APPLICABLE"},
                    "test_5": {"result": "NOT_APPLICABLE"},
                    "test_6": {"result": "APPORTIONABLE", "business_pct": 50},
                    "test_7": {"result": "PASS"},
                    "addback_amount": "25.00"
                }
            }]
        })
        
        invoice_batch = [{
            'InvoiceId': 'INV-200',
            'InvoiceType': 'EXPENSE_CLAIM',
            'SupplierName': 'Hotel',
            'TotalAmount': 100.00,
            'Description': 'Hotel stay',
            'PK': 'client#12345#type#INVOICE',
            'SK': 'invoice#INV-200'
        }]
        
        result = parse_stage2_deep_testing(llm_response, invoice_batch)
        
        assert len(result) == 1
        assert result[0]['DeductibilityStatus'] == 'PARTIALLY_DEDUCTIBLE'
        assert result[0]['DeductibilityPercentage'] == 50
        assert result[0]['BIMSections'] == 'BIM37000'
        assert result[0]['AnalysisStage'] == 'STAGE2_DEEP_TESTING'
        
        # Check all test results parsed
        assert result[0]['Test1_WhollyExclusively'] == 'PASS'
        assert result[0]['Test3_Travel'] == 'BUSINESS_TRAVEL'
        assert result[0]['Test6_MixedUse'] == 'APPORTIONABLE'
        assert result[0]['Test6_BusinessPercentage'] == 50
        assert result[0]['Test7_Duality'] == 'PASS'
        assert result[0]['AddbackAmount'] == '25.00'
    
    def test_stage2_handles_fully_deductible_expense_claim(self):
        """
        CRITICAL: Stage 2 should confirm FULLY_DEDUCTIBLE for compliant expenses.
        """
        llm_response = json.dumps({
            "analyses": [{
                "invoice_id": "INV-201",
                "status": "FULLY_DEDUCTIBLE",
                "percentage": 100,
                "reasoning": "Legitimate business travel",
                "bim_sections": "BIM37000",
                "tests": {
                    "test_1": {"result": "PASS", "reasoning": "Wholly for business"},
                    "test_2": {"result": "NOT_APPLICABLE"},
                    "test_3": {"result": "BUSINESS_TRAVEL"},
                    "test_4": {"result": "NOT_APPLICABLE"},
                    "test_5": {"result": "NOT_APPLICABLE"},
                    "test_6": {"result": "NO_MIXED_USE"},
                    "test_7": {"result": "PASS"},
                    "addback_amount": "0.00"
                }
            }]
        })
        
        invoice_batch = [{
            'InvoiceId': 'INV-201',
            'InvoiceType': 'EXPENSE_CLAIM',
            'SupplierName': 'Train Company',
            'TotalAmount': 75.00,
            'PK': 'client#12345#type#INVOICE',
            'SK': 'invoice#INV-201'
        }]
        
        result = parse_stage2_deep_testing(llm_response, invoice_batch)
        
        assert result[0]['DeductibilityStatus'] == 'FULLY_DEDUCTIBLE'
        assert result[0]['DeductibilityPercentage'] == 100
        assert result[0]['Test1_WhollyExclusively'] == 'PASS'
        assert result[0]['Test3_Travel'] == 'BUSINESS_TRAVEL'
        assert result[0]['AddbackAmount'] == '0.00'


# =============================================================================
# PRIORITY 2: PARTIAL SUCCESS HANDLING TESTS
# =============================================================================

@pytest.mark.unit
class TestPartialSuccessHandling:
    """Critical tests for per-invoice error handling (Priority 1C)."""
    
    def test_stage1_one_malformed_invoice_doesnt_fail_batch(self):
        """
        CRITICAL: If one invoice has parsing errors, others should succeed.
        Partial success > total failure.
        """
        # LLM response has invalid data for INV-302 (missing invoice_id)
        llm_response = json.dumps({
            "classifications": [
                {
                    "invoice_id": "INV-301",
                    "status": "FULLY_DEDUCTIBLE",
                    "percentage": 100,
                    "needs_deep_testing": False,
                    "reason": "Valid"
                },
                {
                    # Missing invoice_id - will cause KeyError
                    "status": "FULLY_DEDUCTIBLE",
                    "percentage": 100,
                    "needs_deep_testing": False,
                    "reason": "Malformed"
                },
                {
                    "invoice_id": "INV-303",
                    "status": "FULLY_DEDUCTIBLE",
                    "percentage": 100,
                    "needs_deep_testing": False,
                    "reason": "Valid"
                }
            ]
        })
        
        invoice_batch = [
            {
                'InvoiceId': 'INV-301',
                'InvoiceType': 'SUPPLIER_INVOICE',
                'PK': 'client#12345#type#INVOICE',
                'SK': 'invoice#INV-301'
            },
            {
                'InvoiceId': 'INV-302',
                'InvoiceType': 'SUPPLIER_INVOICE',
                'PK': 'client#12345#type#INVOICE',
                'SK': 'invoice#INV-302'
            },
            {
                'InvoiceId': 'INV-303',
                'InvoiceType': 'SUPPLIER_INVOICE',
                'PK': 'client#12345#type#INVOICE',
                'SK': 'invoice#INV-303'
            }
        ]
        
        result = parse_stage1_classification(llm_response, invoice_batch)
        
        # Should have 2 successful + 0 failed (malformed classification has no invoice_id to match)
        assert len(result) == 2
        assert result[0]['InvoiceId'] == 'INV-301'
        assert result[0]['AnalysisStatus'] == 'ANALYZED'
        assert result[1]['InvoiceId'] == 'INV-303'
        assert result[1]['AnalysisStatus'] == 'ANALYZED'
    
    def test_stage1_invoice_not_in_batch_continues_processing(self):
        """
        CRITICAL: If LLM returns invoice_id not in batch, skip it and continue.
        """
        llm_response = json.dumps({
            "classifications": [
                {
                    "invoice_id": "INV-401",
                    "status": "FULLY_DEDUCTIBLE",
                    "percentage": 100,
                    "needs_deep_testing": False,
                    "reason": "Valid"
                },
                {
                    "invoice_id": "INV-NONEXISTENT",  # Not in batch
                    "status": "FULLY_DEDUCTIBLE",
                    "percentage": 100,
                    "needs_deep_testing": False,
                    "reason": "Hallucination"
                },
                {
                    "invoice_id": "INV-402",
                    "status": "FULLY_DEDUCTIBLE",
                    "percentage": 100,
                    "needs_deep_testing": False,
                    "reason": "Valid"
                }
            ]
        })
        
        invoice_batch = [
            {
                'InvoiceId': 'INV-401',
                'PK': 'client#12345#type#INVOICE',
                'SK': 'invoice#INV-401'
            },
            {
                'InvoiceId': 'INV-402',
                'PK': 'client#12345#type#INVOICE',
                'SK': 'invoice#INV-402'
            }
        ]
        
        result = parse_stage1_classification(llm_response, invoice_batch)
        
        # Should process 2 valid invoices, skip nonexistent
        assert len(result) == 2
        assert result[0]['InvoiceId'] == 'INV-401'
        assert result[1]['InvoiceId'] == 'INV-402'
    
    def test_stage1_complete_json_parsing_failure_marks_all_failed(self):
        """
        CRITICAL: If JSON parsing completely fails, all invoices marked FAILED.
        Prevents silent data loss.
        """
        llm_response = "This is not valid JSON {broken"
        
        invoice_batch = [
            {
                'InvoiceId': 'INV-501',
                'PK': 'client#12345#type#INVOICE',
                'SK': 'invoice#INV-501'
            },
            {
                'InvoiceId': 'INV-502',
                'PK': 'client#12345#type#INVOICE',
                'SK': 'invoice#INV-502'
            }
        ]
        
        result = parse_stage1_classification(llm_response, invoice_batch)
        
        # All invoices should be marked FAILED
        assert len(result) == 2
        assert all(inv['AnalysisStatus'] == 'FAILED' for inv in result)
        assert all('AnalysisError' in inv for inv in result)
        assert all('Stage 1 JSON parsing failed' in inv['AnalysisError'] for inv in result)
        assert all(inv['AnalysisStage'] == 'STAGE1_CLASSIFICATION' for inv in result)
    
    def test_stage2_partial_success_handling(self):
        """
        CRITICAL: Stage 2 should also handle per-invoice errors gracefully.
        """
        # One invoice missing required fields
        llm_response = json.dumps({
            "analyses": [
                {
                    "invoice_id": "INV-601",
                    "status": "FULLY_DEDUCTIBLE",
                    "percentage": 100,
                    "reasoning": "Valid",
                    "bim_sections": "BIM37000",
                    "tests": {
                        "test_1": {"result": "PASS", "reasoning": "OK"}
                    }
                },
                {
                    # Missing invoice_id
                    "status": "FULLY_DEDUCTIBLE",
                    "percentage": 100,
                    "reasoning": "Malformed"
                }
            ]
        })
        
        invoice_batch = [
            {
                'InvoiceId': 'INV-601',
                'PK': 'client#12345#type#INVOICE',
                'SK': 'invoice#INV-601'
            },
            {
                'InvoiceId': 'INV-602',
                'PK': 'client#12345#type#INVOICE',
                'SK': 'invoice#INV-602'
            }
        ]
        
        result = parse_stage2_deep_testing(llm_response, invoice_batch)
        
        # Should have 1 successful invoice
        assert len(result) == 1
        assert result[0]['InvoiceId'] == 'INV-601'
        assert result[0]['AnalysisStatus'] == 'ANALYZED'
        assert result[0]['AnalysisStage'] == 'STAGE2_DEEP_TESTING'
    
    def test_stage2_complete_failure_preserves_stage1_results(self):
        """
        CRITICAL: If Stage 2 completely fails, Stage 1 results are preserved.
        Users still see basic classification.
        """
        llm_response = "Invalid JSON for stage 2"
        
        # These invoices already have Stage 1 data
        invoice_batch = [
            {
                'InvoiceId': 'INV-701',
                'DeductibilityStatus': 'REQUIRES_REVIEW',  # From Stage 1
                'DeductibilityPercentage': None,
                'NeedsDeepTesting': True,
                'AnalysisStatus': 'ANALYZED',
                'AnalysisStage': 'STAGE1_CLASSIFICATION',
                'PK': 'client#12345#type#INVOICE',
                'SK': 'invoice#INV-701'
            }
        ]
        
        result = parse_stage2_deep_testing(llm_response, invoice_batch)
        
        # Should mark Stage 2 as failed but preserve invoice data
        assert len(result) == 1
        assert result[0]['InvoiceId'] == 'INV-701'
        assert 'AnalysisError' in result[0]
        assert 'Stage 2 JSON parsing failed' in result[0]['AnalysisError']
        assert result[0]['AnalysisStage'] == 'STAGE2_DEEP_TESTING_FAILED'


# =============================================================================
# EDGE CASES & DATA INTEGRITY
# =============================================================================

@pytest.mark.unit
class TestDataIntegrity:
    """Tests to ensure data integrity throughout processing."""
    
    def test_original_invoice_data_preserved(self):
        """
        CRITICAL: Original invoice fields (PK, SK, amounts, etc.) must be preserved.
        """
        llm_response = json.dumps({
            "classifications": [{
                "invoice_id": "INV-800",
                "status": "FULLY_DEDUCTIBLE",
                "percentage": 100,
                "needs_deep_testing": False,
                "reason": "Business"
            }]
        })
        
        invoice_batch = [{
            'InvoiceId': 'INV-800',
            'InvoiceType': 'SUPPLIER_INVOICE',
            'SupplierName': 'Acme Corp',
            'TotalAmount': 500.00,
            'Description': 'Important original data',
            'PK': 'client#12345#type#INVOICE',
            'SK': 'invoice#INV-800',
            'CustomField': 'Should be preserved'
        }]
        
        result = parse_stage1_classification(llm_response, invoice_batch)
        
        # Original fields must be preserved
        assert result[0]['InvoiceId'] == 'INV-800'
        assert result[0]['InvoiceType'] == 'SUPPLIER_INVOICE'
        assert result[0]['SupplierName'] == 'Acme Corp'
        assert result[0]['TotalAmount'] == 500.00
        assert result[0]['Description'] == 'Important original data'
        assert result[0]['PK'] == 'client#12345#type#INVOICE'
        assert result[0]['SK'] == 'invoice#INV-800'
        assert result[0]['CustomField'] == 'Should be preserved'
        
        # New analysis fields added
        assert result[0]['DeductibilityStatus'] == 'FULLY_DEDUCTIBLE'
        assert result[0]['AnalysisStatus'] == 'ANALYZED'
    
    def test_stage2_merges_with_stage1_data(self):
        """
        CRITICAL: Stage 2 should update Stage 1 data, not replace it.
        """
        llm_response = json.dumps({
            "analyses": [{
                "invoice_id": "INV-900",
                "status": "FULLY_DEDUCTIBLE",  # Stage 2 confirmation
                "percentage": 100,
                "reasoning": "Detailed BIM analysis confirms deductibility",
                "bim_sections": "BIM37000",
                "tests": {
                    "test_1": {"result": "PASS", "reasoning": "Wholly for business"}
                }
            }]
        })
        
        # Invoice with Stage 1 data
        invoice_batch = [{
            'InvoiceId': 'INV-900',
            'InvoiceType': 'EXPENSE_CLAIM',
            'DeductibilityStatus': 'REQUIRES_REVIEW',  # Stage 1 said unclear
            'DeductibilityPercentage': None,
            'DeductibilityReasoning': 'Needs BIM check',  # Stage 1 reasoning
            'NeedsDeepTesting': True,
            'AnalysisStatus': 'ANALYZED',
            'AnalysisStage': 'STAGE1_CLASSIFICATION',
            'PK': 'client#12345#type#INVOICE',
            'SK': 'invoice#INV-900'
        }]
        
        result = parse_stage2_deep_testing(llm_response, invoice_batch)
        
        # Stage 2 should UPDATE the status
        assert result[0]['DeductibilityStatus'] == 'FULLY_DEDUCTIBLE'  # Updated
        assert result[0]['DeductibilityPercentage'] == 100  # Updated
        assert result[0]['DeductibilityReasoning'] == 'Detailed BIM analysis confirms deductibility'  # Updated
        assert result[0]['BIMSections'] == 'BIM37000'  # New field
        assert result[0]['Test1_WhollyExclusively'] == 'PASS'  # New field
        assert result[0]['AnalysisStage'] == 'STAGE2_DEEP_TESTING'  # Updated
        
        # Original fields preserved
        assert result[0]['InvoiceType'] == 'EXPENSE_CLAIM'
        assert result[0]['PK'] == 'client#12345#type#INVOICE'
    
    def test_timestamp_added_on_analysis(self):
        """
        CRITICAL: AnalyzedAt timestamp must be set for audit trail.
        """
        llm_response = json.dumps({
            "classifications": [{
                "invoice_id": "INV-999",
                "status": "FULLY_DEDUCTIBLE",
                "percentage": 100,
                "needs_deep_testing": False,
                "reason": "Business"
            }]
        })
        
        invoice_batch = [{
            'InvoiceId': 'INV-999',
            'PK': 'client#12345#type#INVOICE',
            'SK': 'invoice#INV-999'
        }]
        
        before_time = int(time.time())
        result = parse_stage1_classification(llm_response, invoice_batch)
        after_time = int(time.time())
        
        # Timestamp should be set and reasonable
        assert 'AnalyzedAt' in result[0]
        assert isinstance(result[0]['AnalyzedAt'], int)
        assert before_time <= result[0]['AnalyzedAt'] <= after_time
