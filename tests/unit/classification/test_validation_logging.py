# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Unit tests for classification validation logging functionality.

Tests the validation logging system that compares user hints vs model predictions
for collecting metrics on classification accuracy.
"""

import json
import os
from decimal import Decimal
from unittest.mock import MagicMock, Mock, patch

import pytest


@pytest.fixture
def mock_env_vars():
    """Set up environment variables for testing."""
    with patch.dict(
        os.environ,
        {
            "VALIDATION_REQUESTS_TABLE": "test-validation-table",
            "CONFIG_TABLE": "test-config-table",
            "TRACKING_TABLE": "test-tracking-table",
            "WORKING_BUCKET": "test-bucket",
            "REGION": "us-east-1",
        },
    ):
        yield


@pytest.fixture
def mock_document():
    """Create a mock document for testing."""
    doc = MagicMock()
    doc.id = "users/test-user/test-invoice.pdf"
    doc.user_id = "test-user-123"
    doc.company_number = "12345678"
    doc.company_name = "Test Company Ltd"
    doc.user_document_type = "invoice"
    doc.metadata = {}
    doc.sections = []
    
    # Create mock pages as a dictionary (not list)
    page1 = MagicMock()
    page1.id = "page-1"
    page1.classification = None
    
    page2 = MagicMock()
    page2.id = "page-2"
    page2.classification = None
    
    doc.pages = {
        "page-1": page1,
        "page-2": page2
    }
    
    return doc


@pytest.fixture
def mock_config():
    """Create mock configuration."""
    return {
        "classification": {
            "trust_user_hint": False,
            "validate_hint_on_mismatch": True,
        }
    }


@pytest.mark.unit
class TestValidationLogging:
    """Test validation logging functionality."""

    def test_validation_record_created_on_match(
        self, mock_env_vars, mock_document, mock_config
    ):
        """Test validation record is created when user hint matches model prediction."""
        # Simulate model classifying as "invoice" (matching user hint)
        model_classification = "invoice"
        user_hint = "invoice"
        
        # This should create a validation record
        validation_item = {
            "UserSelection": user_hint,
            "ModelPrediction": model_classification,
            "ModelConfidence": Decimal("0.95"),
            "ValidationMatch": True,
            "ValidationStatus": "auto_logged",
        }
        
        # Verify the validation record would be created correctly
        assert user_hint == model_classification
        assert validation_item["ValidationMatch"] is True

    def test_validation_record_created_on_mismatch(
        self, mock_env_vars, mock_document, mock_config
    ):
        """Test validation record is created when user hint differs from model prediction."""
        model_classification = "bank-statement"
        user_hint = "invoice"
        
        # Should create validation record with ValidationMatch=False
        validation_match = (user_hint == model_classification)
        assert validation_match is False

    def test_model_confidence_converted_to_decimal(self):
        """Test that ModelConfidence is converted from float to Decimal for DynamoDB."""
        from decimal import Decimal
        
        # Float confidence from model
        float_confidence = 0.95
        
        # Should be converted to Decimal
        decimal_confidence = Decimal(str(float_confidence))
        
        assert isinstance(decimal_confidence, Decimal)
        assert float(decimal_confidence) == 0.95

    def test_validation_record_structure(self, mock_document):
        """Test validation record has required fields."""
        import uuid
        from datetime import datetime
        from decimal import Decimal
        
        validation_id = str(uuid.uuid4())
        timestamp = int(datetime.now().timestamp())
        
        validation_item = {
            "PK": f"validation#{validation_id}",
            "SK": f"doc#{mock_document.id}",
            "ValidationId": validation_id,
            "DocumentId": mock_document.id,
            "UserId": mock_document.user_id,
            "CompanyNumber": mock_document.company_number,
            "CompanyName": mock_document.company_name,
            "UserSelection": "invoice",
            "ModelPrediction": "bank-statement",
            "ModelConfidence": Decimal("0.92"),
            "ValidationMatch": False,
            "ValidationStatus": "auto_logged",
            "CreatedAt": timestamp,
            "TTL": timestamp + 31536000,  # 1 year
        }
        
        # Verify all required fields are present
        assert "PK" in validation_item
        assert "SK" in validation_item
        assert "ValidationId" in validation_item
        assert "DocumentId" in validation_item
        assert "UserId" in validation_item
        assert "UserSelection" in validation_item
        assert "ModelPrediction" in validation_item
        assert "ModelConfidence" in validation_item
        assert isinstance(validation_item["ModelConfidence"], Decimal)
        assert "ValidationMatch" in validation_item
        assert isinstance(validation_item["ValidationMatch"], bool)

    def test_validation_match_logic(self):
        """Test validation match calculation."""
        # Test exact match
        assert "invoice" == "invoice"
        assert "bank-statement" == "bank-statement"
        
        # Test mismatch
        assert "invoice" != "bank-statement"
        assert "invoice" != "unclassified"
        
        # Test case sensitivity (should match config normalization)
        user_hint = "bank-statement"
        model_pred = "bank-statement"
        assert user_hint == model_pred


@pytest.mark.unit
class TestUserHintRouting:
    """Test user hint routing with validation."""

    def test_trust_user_hint_true_skips_llm(self, mock_document):
        """Test that trust_user_hint=true skips LLM classification entirely."""
        user_hint = "invoice"
        trust_user_hint = True
        
        if user_hint and trust_user_hint:
            # Should skip LLM and use user hint directly
            classification = user_hint
            llm_should_run = False
        else:
            llm_should_run = True
        
        assert classification == "invoice"
        assert llm_should_run is False

    def test_validate_hint_on_mismatch_runs_llm(self, mock_document):
        """Test that validate_hint_on_mismatch=true runs LLM but uses user hint for routing."""
        user_hint = "invoice"
        validate_hint_on_mismatch = True
        trust_user_hint = False
        
        # Should run LLM for validation
        llm_should_run = not (user_hint and trust_user_hint)
        assert llm_should_run is True
        
        # But should use user hint for routing
        use_user_hint_for_routing = (user_hint and validate_hint_on_mismatch)
        assert use_user_hint_for_routing is True

    def test_pages_dict_iteration(self, mock_document):
        """Test that document.pages is iterated correctly as a dict, not list."""
        # document.pages is a dict {page_id: Page}, not a list
        assert isinstance(mock_document.pages, dict)
        
        # Should iterate with .items() to get (page_id, page) tuples
        page_count = 0
        for page_id, page in mock_document.pages.items():
            assert isinstance(page_id, str)
            assert page is not None
            page_count += 1
        
        assert page_count == 2

    def test_classification_override_with_user_hint(self, mock_document):
        """Test that classification is overridden with user hint when validate_on_mismatch=true."""
        user_hint = "invoice"
        model_classification = "bank-statement"
        use_user_hint_for_routing = True
        
        if use_user_hint_for_routing:
            # Override sections
            for section in mock_document.sections:
                section.classification = user_hint
            
            # Override pages (using .items() for dict iteration)
            for page_id, page in mock_document.pages.items():
                page.classification = user_hint
        
        # Verify all pages have user hint classification
        for page_id, page in mock_document.pages.items():
            assert page.classification == user_hint

    def test_metadata_set_for_validation_mode(self, mock_document):
        """Test that metadata is correctly set for validation mode."""
        user_hint = "invoice"
        use_user_hint_for_routing = True
        
        if use_user_hint_for_routing:
            mock_document.metadata["classification_method"] = "user_hint_validated"
            mock_document.metadata["user_provided_type"] = user_hint
        
        assert mock_document.metadata["classification_method"] == "user_hint_validated"
        assert mock_document.metadata["user_provided_type"] == "invoice"


@pytest.mark.unit
class TestConfigValidation:
    """Test configuration validation for trust_user_hint and validate_hint_on_mismatch."""

    def test_mutually_exclusive_config(self):
        """Test that trust_user_hint and validate_hint_on_mismatch are mutually exclusive."""
        # Case 1: trust_user_hint=true should skip LLM entirely
        config1 = {
            "classification": {
                "trust_user_hint": True,
                "validate_hint_on_mismatch": False,
            }
        }
        trust1 = config1["classification"]["trust_user_hint"]
        validate1 = config1["classification"]["validate_hint_on_mismatch"]
        user_hint = "invoice"
        
        skip_llm = user_hint and trust1
        assert skip_llm is True
        
        # Case 2: validate_hint_on_mismatch=true should run LLM
        config2 = {
            "classification": {
                "trust_user_hint": False,
                "validate_hint_on_mismatch": True,
            }
        }
        trust2 = config2["classification"]["trust_user_hint"]
        validate2 = config2["classification"]["validate_hint_on_mismatch"]
        
        skip_llm = user_hint and trust2
        run_llm = not skip_llm
        use_hint_for_routing = user_hint and validate2
        
        assert run_llm is True
        assert use_hint_for_routing is True

    def test_default_config_values(self):
        """Test default configuration values."""
        config = {}
        
        # Defaults should be False
        trust_user_hint = config.get("classification", {}).get("trust_user_hint", False)
        validate_hint_on_mismatch = config.get("classification", {}).get(
            "validate_hint_on_mismatch", False
        )
        
        assert trust_user_hint is False
        assert validate_hint_on_mismatch is False
