"""
Tests for ListExtractionResults Lambda handler.

Tests the critical batch_get_item workaround for GSI projection limitations.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal
import json
import os
import sys
from pathlib import Path

# Add lambda to path
LAMBDA_DIR = Path(__file__).parent.parent.parent.parent.parent / 'src' / 'lambda' / 'list_extraction_results'
sys.path.insert(0, str(LAMBDA_DIR))

# Set environment variables before importing lambda_function
os.environ['EXTRACTION_RESULTS_TABLE'] = 'test-table'
os.environ['LOG_LEVEL'] = 'DEBUG'

import lambda_function


@pytest.mark.unit
@pytest.mark.lambda
class TestDecimalEncoder:
    """Tests for DecimalEncoder - ensures timestamps are int, amounts are float."""
    
    def test_converts_whole_decimals_to_int(self):
        """Should convert whole number Decimals to int (for timestamps)."""
        timestamp = Decimal('1762966408')
        result = json.dumps({"timestamp": timestamp}, cls=lambda_function.DecimalEncoder)
        
        # Should be int, not float
        assert '"timestamp": 1762966408' in result
        assert '1762966408.0' not in result
    
    def test_converts_fractional_decimals_to_float(self):
        """Should convert fractional Decimals to float (for amounts)."""
        amount = Decimal('18.50')
        result = json.dumps({"amount": amount}, cls=lambda_function.DecimalEncoder)
        
        # Should be float
        assert '"amount": 18.5' in result
    
    def test_handles_confidence_scores(self):
        """Should handle confidence scores as floats."""
        confidence = Decimal('0.975')
        result = json.dumps({"confidence": confidence}, cls=lambda_function.DecimalEncoder)
        
        assert '"confidence": 0.975' in result


@pytest.mark.unit
@pytest.mark.lambda
class TestListExtractionResults:
    """Tests for list_extraction_results function."""
    
    @patch('lambda_function.dynamodb')
    def test_queries_gsi6_index(self, mock_dynamodb, mock_gsi_response, mock_batch_get_response):
        """Should query GSI7-ClientTypeDate index."""
        mock_table = MagicMock()
        mock_table.query.return_value = mock_gsi_response
        mock_dynamodb.Table.return_value = mock_table
        mock_dynamodb.batch_get_item.return_value = mock_batch_get_response
        
        result = lambda_function.list_extraction_results(
            user_id="23b4b872-20a1-709e-ffef-d20a604f60b5",
            company_number="15944206",
            document_type="INVOICE",
            limit=50
        )
        
        # Verify GSI query was called
        mock_table.query.assert_called_once()
        call_kwargs = mock_table.query.call_args[1]
        assert call_kwargs["IndexName"] == "GSI7-ClientTypeDate"
    
    @patch('lambda_function.dynamodb')
    def test_uses_batch_get_for_full_items(self, mock_dynamodb, mock_gsi_response, mock_batch_get_response):
        """Should use batch_get_item to fetch full items after GSI query."""
        mock_table = MagicMock()
        mock_table.query.return_value = mock_gsi_response
        mock_dynamodb.Table.return_value = mock_table
        mock_dynamodb.batch_get_item.return_value = mock_batch_get_response
        
        result = lambda_function.list_extraction_results(
            user_id="23b4b872-20a1-709e-ffef-d20a604f60b5",
            company_number="15944206",
            document_type="INVOICE"
        )
        
        # Verify batch_get_item was called
        mock_dynamodb.batch_get_item.assert_called_once()
        
        # Verify it requested the correct keys
        call_args = mock_dynamodb.batch_get_item.call_args[1]
        request_items = call_args["RequestItems"]
        assert "test-table" in request_items
        assert len(request_items["test-table"]["Keys"]) == 2
    
    @patch('lambda_function.dynamodb')
    def test_returns_items_with_document_type(self, mock_dynamodb, mock_gsi_response, mock_batch_get_response):
        """Should return full items including DocumentType field."""
        mock_table = MagicMock()
        mock_table.query.return_value = mock_gsi_response
        mock_dynamodb.Table.return_value = mock_table
        mock_dynamodb.batch_get_item.return_value = mock_batch_get_response
        
        result = lambda_function.list_extraction_results(
            user_id="23b4b872-20a1-709e-ffef-d20a604f60b5",
            company_number="15944206",
            document_type="INVOICE"
        )
        
        # Verify items have DocumentType (which GSI projection doesn't include)
        assert len(result["items"]) == 2
        assert all("DocumentType" in item for item in result["items"])
        assert all(item["DocumentType"] == "INVOICE" for item in result["items"])
    
    @patch('lambda_function.dynamodb')
    def test_filters_by_user_id(self, mock_dynamodb, mock_gsi_response, mock_batch_get_response):
        """Should filter results to only include items for the authenticated user."""
        # Add item from different user
        different_user_item = {
            "PK": "user#different-user-id#doc#test.pdf",
            "SK": "type#INVOICE#section#1#invoice#1",
            "GSI6PK": "client#15944206#type#INVOICE",
            "UserId": "different-user-id",
            "DocumentId": "test.pdf",
            "ProcessedAt": Decimal("1762966408")
        }
        mock_gsi_response["Items"].append(different_user_item)
        mock_gsi_response["Count"] = 3
        
        mock_table = MagicMock()
        mock_table.query.return_value = mock_gsi_response
        mock_dynamodb.Table.return_value = mock_table
        mock_dynamodb.batch_get_item.return_value = mock_batch_get_response
        
        result = lambda_function.list_extraction_results(
            user_id="23b4b872-20a1-709e-ffef-d20a604f60b5",
            company_number="15944206",
            document_type="INVOICE"
        )
        
        # Should only return 2 items (not 3) - filtered by user
        assert len(result["items"]) == 2
        assert all(item["UserId"] == "23b4b872-20a1-709e-ffef-d20a604f60b5" for item in result["items"])


@pytest.mark.unit
@pytest.mark.lambda
class TestLambdaHandler:
    """Tests for the main Lambda handler function."""
    
    @patch('lambda_function.list_extraction_results')
    def test_handler_success(self, mock_list_fn, valid_appsync_event, mock_lambda_context):
        """Should process valid AppSync event successfully."""
        mock_list_fn.return_value = {"items": [], "nextToken": None}
        
        result = lambda_function.handler(valid_appsync_event, mock_lambda_context)
        
        assert "items" in result
        assert isinstance(result["items"], list)
    
    @patch('lambda_function.list_extraction_results')
    def test_extracts_user_from_identity(self, mock_list_fn, valid_appsync_event, mock_lambda_context):
        """Should extract user ID from Cognito identity.sub."""
        mock_list_fn.return_value = {"items": [], "nextToken": None}
        
        lambda_function.handler(valid_appsync_event, mock_lambda_context)
        
        # Verify user_id was extracted from identity.sub
        call_kwargs = mock_list_fn.call_args[1]
        assert call_kwargs["user_id"] == "23b4b872-20a1-709e-ffef-d20a604f60b5"
    
    def test_raises_error_on_missing_company_number(self, valid_appsync_event, mock_lambda_context):
        """Should raise error if companyNumber is missing."""
        del valid_appsync_event["arguments"]["companyNumber"]
        
        with pytest.raises(ValueError, match="companyNumber is required"):
            lambda_function.handler(valid_appsync_event, mock_lambda_context)
    
    def test_raises_error_on_invalid_document_type(self, valid_appsync_event, mock_lambda_context):
        """Should raise error for invalid documentType."""
        valid_appsync_event["arguments"]["documentType"] = "INVALID_TYPE"
        
        with pytest.raises(ValueError, match="documentType must be one of"):
            lambda_function.handler(valid_appsync_event, mock_lambda_context)
    
    def test_raises_error_on_missing_user_id(self, valid_appsync_event, mock_lambda_context):
        """Should raise error if user ID cannot be extracted."""
        del valid_appsync_event["identity"]["sub"]
        valid_appsync_event["identity"]["username"] = None
        
        with pytest.raises(ValueError, match="User ID not found"):
            lambda_function.handler(valid_appsync_event, mock_lambda_context)
