"""
Trigger Transaction Analysis GraphQL Resolver
Starts Step Functions execution for transaction categorization workflow.
"""

import json
import boto3
import os
import time
import traceback
import logging
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
stepfunctions = boto3.client('stepfunctions')

# Environment variables
STATE_MACHINE_ARN = os.environ.get('STATE_MACHINE_ARN')


def lambda_handler(event, context):
    """
    GraphQL resolver to trigger transaction categorization Step Functions workflow.
    """
    logger.info("triggerTransactionAnalysis resolver invoked")
    logger.info(f"Event: {json.dumps(event)}")

    # Extract arguments from the GraphQL event
    arguments = event.get('arguments', {})
    company_number = arguments.get('companyNumber')

    if not company_number:
        logger.error("Missing required parameter: companyNumber")
        return {
            'success': False,
            'message': 'Missing required parameter: companyNumber',
            'executionArn': None,
            'executionName': None,
        }

    try:
        state_machine_arn = os.environ['STATE_MACHINE_ARN']
        logger.info(f"State Machine ARN: {state_machine_arn}")

        # Check for running executions for this company
        logger.info(f"Checking for running executions for company {company_number}")
        running_executions = stepfunctions.list_executions(
            stateMachineArn=state_machine_arn,
            statusFilter='RUNNING',
            maxResults=10,
        )

        # Check if any running execution is for this company
        for execution in running_executions.get('executions', []):
            execution_name = execution['name']
            # Execution name format: categorization-{companyNumber}-{timestamp}
            if execution_name.startswith(f"categorization-{company_number}-"):
                logger.info(f"Found running execution: {execution_name}")
                return {
                    'success': False,
                    'message': f'Analysis already in progress for company {company_number}. Please wait for the current analysis to complete.',
                    'executionArn': execution['executionArn'],
                    'executionName': execution_name,
                }

        # Generate unique execution name with timestamp
        timestamp = int(time.time())
        execution_name = f"categorization-{company_number}-{timestamp}"

        # Start Step Functions execution
        logger.info(f"Starting execution: {execution_name}")
        response = stepfunctions.start_execution(
            stateMachineArn=state_machine_arn,
            name=execution_name,
            input=json.dumps({
                'companyNumber': company_number,
            }),
        )

        execution_arn = response['executionArn']
        logger.info(f"Execution started successfully: {execution_arn}")

        return {
            'success': True,
            'message': f'Transaction analysis workflow started for company {company_number}',
            'executionArn': execution_arn,
            'executionName': execution_name,
        }

    except Exception as e:
        logger.error(f"Error starting Step Functions execution: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            'success': False,
            'message': f'Error starting analysis workflow: {str(e)}',
            'executionArn': None,
            'executionName': None,
        }
