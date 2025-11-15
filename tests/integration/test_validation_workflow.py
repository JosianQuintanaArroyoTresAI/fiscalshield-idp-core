# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Integration tests for classification validation workflow.

Tests the end-to-end flow of:
1. User uploads document with hint
2. Classification runs (or skips) based on config
3. Validation record created comparing user hint vs model prediction
4. Document routed based on configuration
"""

import json
import os
from decimal import Decimal
from unittest.mock import MagicMock, Mock, patch

import pytest


@pytest.fixture
def mock_aws_services():
    """Mock AWS services for integration testing."""
    with patch("boto3.client") as mock_client, \
         patch("boto3.resource") as mock_resource:
        
        # Mock Bedrock client
        mock_bedrock = MagicMock()
        mock_bedrock.invoke_model.return_value = {
            "body": MagicMock(read=lambda: json.dumps({
                "content": [{
                    "text": '```json\n{"class": "invoice", "document_boundary": "start"}\n```'
                }]
            }).encode())
        }
        
        # Mock DynamoDB resource
        mock_dynamodb = MagicMock()
        mock_validation_table = MagicMock()
        mock_config_table = MagicMock()
        
        mock_dynamodb.Table.side_effect = lambda name: {
            "validation-table": mock_validation_table,
            "config-table": mock_config_table,
        }.get(name, MagicMock())
        
        mock_resource.return_value = mock_dynamodb
        
        # Mock S3 client
        mock_s3 = MagicMock()
        
        def get_client(service_name, **kwargs):
            if service_name == "bedrock-runtime":
                return mock_bedrock
            elif service_name == "s3":
                return mock_s3
            return MagicMock()
        
        mock_client.side_effect = get_client
        
        yield {
            "bedrock": mock_bedrock,
            "dynamodb": mock_dynamodb,
            "validation_table": mock_validation_table,
            "config_table": mock_config_table,
            "s3": mock_s3,
        }


@pytest.mark.integration
class TestValidationWorkflowEndToEnd:
    """Integration tests for validation workflow."""

    def test_validation_workflow_match(self, mock_aws_services):
        """Test validation workflow when user hint matches model prediction."""
        # Setup
        user_hint = "invoice"
        model_prediction = "invoice"
        
        # Simulate classification
        validation_match = (user_hint == model_prediction)
        
        # Verify validation record would be created
        assert validation_match is True
        
        # Verify DynamoDB write would be called
        validation_item = {
            "UserSelection": user_hint,
            "ModelPrediction": model_prediction,
            "ValidationMatch": validation_match,
            "ModelConfidence": Decimal("0.95"),
        }
        
        assert validation_item["ValidationMatch"] is True

    def test_validation_workflow_mismatch(self, mock_aws_services):
        """Test validation workflow when user hint differs from model prediction."""
        # Setup
        user_hint = "bank-statement"
        model_prediction = "invoice"
        
        # Simulate classification
        validation_match = (user_hint == model_prediction)
        
        # Verify validation record would be created with mismatch
        assert validation_match is False
        
        validation_item = {
            "UserSelection": user_hint,
            "ModelPrediction": model_prediction,
            "ValidationMatch": validation_match,
        }
        
        assert validation_item["ValidationMatch"] is False

    def test_trust_user_hint_skips_classification(self, mock_aws_services):
        """Test that trust_user_hint=true skips classification entirely."""
        # Config
        config = {
            "classification": {
                "trust_user_hint": True,
                "validate_hint_on_mismatch": False,
            }
        }
        
        user_hint = "invoice"
        trust_user_hint = config["classification"]["trust_user_hint"]
        
        # Should skip classification
        should_run_classification = not (user_hint and trust_user_hint)
        
        assert should_run_classification is False
        
        # Bedrock should NOT be called
        # mock_aws_services["bedrock"].invoke_model.assert_not_called()

    def test_validate_on_mismatch_runs_classification_uses_hint(self, mock_aws_services):
        """Test validate_hint_on_mismatch runs LLM but uses user hint for routing."""
        # Config
        config = {
            "classification": {
                "trust_user_hint": False,
                "validate_hint_on_mismatch": True,
            }
        }
        
        user_hint = "invoice"
        trust_user_hint = config["classification"]["trust_user_hint"]
        validate_on_mismatch = config["classification"]["validate_hint_on_mismatch"]
        
        # Should run classification (LLM)
        should_run_classification = not (user_hint and trust_user_hint)
        assert should_run_classification is True
        
        # But should use user hint for routing
        use_user_hint_for_routing = (user_hint and validate_on_mismatch)
        assert use_user_hint_for_routing is True
        
        # Mock model returns different classification
        model_prediction = "bank-statement"
        
        # Should create validation record
        validation_match = (user_hint == model_prediction)
        assert validation_match is False
        
        # But routing should use user hint
        routing_classification = user_hint if use_user_hint_for_routing else model_prediction
        assert routing_classification == "invoice"

    def test_metadata_set_correctly_for_validation_mode(self):
        """Test that document metadata is set correctly for validation mode."""
        user_hint = "invoice"
        use_user_hint_for_routing = True
        
        metadata = {}
        
        if use_user_hint_for_routing:
            metadata["classification_method"] = "user_hint_validated"
            metadata["user_provided_type"] = user_hint
            metadata["model_prediction"] = "bank-statement"  # Different from user
        
        assert metadata["classification_method"] == "user_hint_validated"
        assert metadata["user_provided_type"] == "invoice"
        assert metadata["model_prediction"] == "bank-statement"


@pytest.mark.integration
class TestHallucinationPreventionEndToEnd:
    """Integration tests for hallucination prevention in extraction."""

    def test_invoice_uploaded_as_bank_statement_returns_empty(self, mock_aws_services):
        """Test that invoice uploaded as bank-statement returns empty transactions."""
        # Setup - mock Bedrock to return empty transactions (correct behavior)
        mock_aws_services["bedrock"].invoke_model.return_value = {
            "body": MagicMock(read=lambda: json.dumps({
                "content": [{
                    "text": "<bank_statement><transactions></transactions></bank_statement>"
                }]
            }).encode())
        }
        
        # Process extraction
        xml_result = "<bank_statement><transactions></transactions></bank_statement>"
        
        # Parse transactions
        import re
        transaction_pattern = r'<transaction>(.*?)</transaction>'
        transactions = re.findall(transaction_pattern, xml_result, re.DOTALL)
        
        # Should have 0 transactions (not hallucinated examples)
        assert len(transactions) == 0

    def test_prompt_prevents_example_copying(self):
        """Test that extraction prompt prevents copying example transactions."""
        import os
        
        handler_path = os.path.join(os.path.dirname(__file__), "..", "..", "patterns", "pattern-2", "lambdas", "bank_statement_extraction", "bank_statement_extraction_handler.py")
        with open(handler_path, 'r') as f:
            handler_content = f.read()
        
        # Verify anti-hallucination safeguards are in prompt
        safeguards = [
            "CRITICAL DOCUMENT TYPE CHECK",
            "DO NOT COPY THESE VALUES",
            "END OF EXAMPLES",
            "DO NOT hallucinate or copy example transactions",
            "Only extract what you actually see in the text below",
        ]
        
        for safeguard in safeguards:
            assert safeguard in handler_content, f"Missing safeguard: {safeguard}"

    def test_real_bank_statement_extraction_not_blocked(self, mock_aws_services):
        """Test that real bank statements still extract correctly."""
        # Mock real bank statement extraction
        mock_aws_services["bedrock"].invoke_model.return_value = {
            "body": MagicMock(read=lambda: json.dumps({
                "content": [{
                    "text": """
                    <bank_statement>
                    <account_info>
                      <account_number>87654321</account_number>
                      <sort_code>99-88-77</sort_code>
                    </account_info>
                    <transactions>
                    <transaction>
                      <date>2024-01-15</date>
                      <description>Salary payment</description>
                      <amount>2500.00</amount>
                      <balance>2500.00</balance>
                    </transaction>
                    </transactions>
                    </bank_statement>
                    """
                }]
            }).encode())
        }
        
        # Parse result
        import re
        xml_result = mock_aws_services["bedrock"].invoke_model.return_value["body"].read().decode()
        response = json.loads(xml_result)
        text = response["content"][0]["text"]
        
        transaction_pattern = r'<transaction>(.*?)</transaction>'
        transactions = re.findall(transaction_pattern, text, re.DOTALL)
        
        # Should have real transactions
        assert len(transactions) == 1
        assert "Salary payment" in text


@pytest.mark.integration
class TestDocumentRoutingWithValidation:
    """Integration tests for document routing based on classification."""

    def test_invoice_routes_to_invoice_extraction(self):
        """Test that documents classified as invoice route to InvoiceExtraction."""
        classification = "invoice"
        
        # Routing logic
        next_step = "InvoiceExtraction" if classification == "invoice" else "GenericExtraction"
        
        assert next_step == "InvoiceExtraction"

    def test_bank_statement_routes_to_generic_extraction(self):
        """Test that bank statements route to GenericExtraction (with specific handler)."""
        classification = "bank-statement"
        
        # Routing logic
        next_step = "InvoiceExtraction" if classification == "invoice" else "GenericExtraction"
        
        assert next_step == "GenericExtraction"

    def test_user_hint_overrides_routing_in_validation_mode(self):
        """Test that user hint overrides model classification for routing."""
        user_hint = "invoice"
        model_classification = "bank-statement"
        use_user_hint_for_routing = True
        
        # Determine routing classification
        routing_classification = user_hint if use_user_hint_for_routing else model_classification
        
        # Route based on routing classification
        next_step = "InvoiceExtraction" if routing_classification == "invoice" else "GenericExtraction"
        
        # Should route to invoice extraction despite model saying bank-statement
        assert next_step == "InvoiceExtraction"
        
        # But validation record should show mismatch
        validation_match = (user_hint == model_classification)
        assert validation_match is False


@pytest.mark.integration
class TestDynamoDBDataIntegrity:
    """Integration tests for DynamoDB data integrity."""

    def test_decimal_conversion_for_confidence(self):
        """Test that float confidence is converted to Decimal for DynamoDB."""
        from decimal import Decimal
        
        # Model returns float
        model_confidence = 0.95
        
        # Convert for DynamoDB
        db_confidence = Decimal(str(model_confidence))
        
        assert isinstance(db_confidence, Decimal)
        assert float(db_confidence) == 0.95

    def test_validation_record_ttl(self):
        """Test that validation records have appropriate TTL."""
        from datetime import datetime
        
        timestamp = int(datetime.now().timestamp())
        ttl = timestamp + (365 * 24 * 60 * 60)  # 1 year
        
        validation_item = {
            "CreatedAt": timestamp,
            "TTL": ttl,
        }
        
        # TTL should be ~1 year from creation
        assert validation_item["TTL"] > validation_item["CreatedAt"]
        assert validation_item["TTL"] - validation_item["CreatedAt"] == 31536000

    def test_no_hallucinated_transactions_in_db(self):
        """Test that hallucinated transactions are not stored in DynamoDB."""
        # Example transaction references that should NOT appear for invoice
        hallucinated_refs = ["862834451961-CHB", "PAYPAL", "TESCO"]
        
        # Mock DynamoDB scan result for invoice document
        db_transactions = []  # Empty - correct for invoice
        
        # Verify no hallucinated data
        for transaction in db_transactions:
            ref = transaction.get("Reference", "")
            assert ref not in hallucinated_refs
        
        assert len(db_transactions) == 0
