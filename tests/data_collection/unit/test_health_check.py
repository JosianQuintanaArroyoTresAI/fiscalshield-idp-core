#!/usr/bin/env python3

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Unit tests for Data Collection Health Check Lambda function
"""

import json
import os
from unittest.mock import Mock, patch

import pytest
import sys

# Add the src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src"))

from data_collection.health import handler


class TestHealthCheckHandler:
    """Test health check Lambda handler"""

    @patch("data_collection.health.handler.secrets_manager")
    @patch("data_collection.health.handler.dynamodb")
    @patch("data_collection.health.handler.stepfunctions")
    def test_lambda_handler_all_services_operational(
        self, mock_stepfunctions, mock_dynamodb, mock_secrets_manager
    ):
        """Test health check with all services operational"""
        # Mock successful service checks
        mock_secrets_manager.describe_secret.return_value = {"Name": "test-secret"}
        mock_dynamodb.describe_table.return_value = {
            "Table": {"TableStatus": "ACTIVE"}
        }
        mock_stepfunctions.describe_state_machine.return_value = {
            "stateMachineArn": "arn:aws:states:us-east-1:123456789012:stateMachine:test"
        }

        # Mock context
        context = Mock()
        context.invoked_function_arn = (
            "arn:aws:lambda:eu-central-1:864899848062:function:test"
        )

        # Call handler
        event = {}
        response = handler.lambda_handler(event, context)

        # Verify response
        assert response["statusCode"] == 200
        assert "Content-Type" in response["headers"]

        body = json.loads(response["body"])
        assert body["status"] == "available"
        assert body["environment"] == os.environ.get("ENVIRONMENT", "dev")
        assert "services" in body
        assert body["services"]["companies_house"] == "operational"
        assert body["services"]["dynamodb"] == "operational"

    @patch("data_collection.health.handler.secrets_manager")
    @patch("data_collection.health.handler.dynamodb")
    @patch("data_collection.health.handler.stepfunctions")
    def test_lambda_handler_degraded_services(
        self, mock_stepfunctions, mock_dynamodb, mock_secrets_manager
    ):
        """Test health check with degraded services"""
        # Mock failed service checks
        from botocore.exceptions import ClientError

        mock_secrets_manager.describe_secret.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException"}}, "DescribeSecret"
        )
        mock_dynamodb.describe_table.return_value = {
            "Table": {"TableStatus": "ACTIVE"}
        }
        mock_stepfunctions.describe_state_machine.side_effect = ClientError(
            {"Error": {"Code": "StateMachineDoesNotExist"}}, "DescribeStateMachine"
        )

        # Mock context
        context = Mock()
        context.invoked_function_arn = (
            "arn:aws:lambda:eu-central-1:864899848062:function:test"
        )

        # Call handler
        event = {}
        response = handler.lambda_handler(event, context)

        # Verify response - still returns 200 but status is degraded
        assert response["statusCode"] == 200

        body = json.loads(response["body"])
        assert body["status"] == "degraded"
        assert body["services"]["companies_house"] == "unavailable"
        assert body["services"]["step_functions"] == "unavailable"


class TestCheckCompaniesHouseAPI:
    """Test Companies House API check function"""

    @patch("data_collection.health.handler.secrets_manager")
    def test_check_companies_house_api_operational(self, mock_secrets_manager):
        """Test successful Companies House API check"""
        mock_secrets_manager.describe_secret.return_value = {"Name": "test-secret"}

        result = handler.check_companies_house_api()
        assert result == "operational"

    @patch("data_collection.health.handler.secrets_manager")
    def test_check_companies_house_api_unavailable(self, mock_secrets_manager):
        """Test failed Companies House API check"""
        from botocore.exceptions import ClientError

        mock_secrets_manager.describe_secret.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException"}}, "DescribeSecret"
        )

        result = handler.check_companies_house_api()
        assert result == "unavailable"


class TestCheckStepFunctions:
    """Test Step Functions check function"""

    @patch("data_collection.health.handler.stepfunctions")
    def test_check_step_functions_available(self, mock_stepfunctions):
        """Test successful Step Functions check"""
        mock_stepfunctions.describe_state_machine.return_value = {
            "stateMachineArn": "arn:aws:states:us-east-1:123456789012:stateMachine:test"
        }

        # Mock context
        context = Mock()
        context.invoked_function_arn = (
            "arn:aws:lambda:eu-central-1:864899848062:function:test"
        )

        result = handler.check_step_functions(context)
        assert result == "available"

    @patch("data_collection.health.handler.stepfunctions")
    def test_check_step_functions_unavailable(self, mock_stepfunctions):
        """Test failed Step Functions check"""
        from botocore.exceptions import ClientError

        mock_stepfunctions.describe_state_machine.side_effect = ClientError(
            {"Error": {"Code": "StateMachineDoesNotExist"}}, "DescribeStateMachine"
        )

        # Mock context
        context = Mock()
        context.invoked_function_arn = (
            "arn:aws:lambda:eu-central-1:864899848062:function:test"
        )

        result = handler.check_step_functions(context)
        assert result == "unavailable"


class TestCheckDynamoDB:
    """Test DynamoDB check function"""

    @patch("data_collection.health.handler.dynamodb")
    def test_check_dynamodb_operational(self, mock_dynamodb):
        """Test successful DynamoDB check"""
        mock_dynamodb.describe_table.return_value = {
            "Table": {"TableStatus": "ACTIVE"}
        }

        result = handler.check_dynamodb()
        assert result == "operational"

    @patch("data_collection.health.handler.dynamodb")
    def test_check_dynamodb_degraded(self, mock_dynamodb):
        """Test degraded DynamoDB check (one table missing)"""
        from botocore.exceptions import ClientError

        # First call succeeds, second call fails
        mock_dynamodb.describe_table.side_effect = [
            {"Table": {"TableStatus": "ACTIVE"}},
            ClientError(
                {"Error": {"Code": "ResourceNotFoundException"}}, "DescribeTable"
            ),
        ]

        result = handler.check_dynamodb()
        assert result == "degraded"

    @patch("data_collection.health.handler.dynamodb")
    def test_check_dynamodb_unavailable(self, mock_dynamodb):
        """Test failed DynamoDB check"""
        from botocore.exceptions import ClientError

        mock_dynamodb.describe_table.side_effect = ClientError(
            {"Error": {"Code": "AccessDeniedException"}}, "DescribeTable"
        )

        result = handler.check_dynamodb()
        assert result == "unavailable"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
