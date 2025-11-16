"""
Trigger Transaction Analysis GraphQL Resolver
Starts Step Functions execution for transaction categorization workflow.
"""

import json
import boto3
import os
from datetime import datetime

# AWS clients
stepfunctions = boto3.client('stepfunctions')

# Environment variables
STATE_MACHINE_ARN = os.environ.get('STATE_MACHINE_ARN')


def lambda_handler(event, context):
    """
    Lambda handler for triggerTransactionAnalysis GraphQL mutation.
    
    Expected event from AppSync:
    {
        "arguments": {
            "companyNumber": "12345678"
        },
        "identity": {
            "sub": "user-id-from-cognito",
            "username": "user@example.com"
        }
    }
    
    Returns:
    {
        "success": true,
        "message": "Analysis workflow started",
        "executionArn": "arn:aws:states:...",
        "executionName": "categorization-12345678-1234567890"
    }
    """
    
    print(f"Received event: {json.dumps(event, default=str)}")
    
    try:
        # Extract parameters
        arguments = event.get('arguments', {})
        company_number = arguments.get('companyNumber')
        
        # Get user ID from Cognito identity
        identity = event.get('identity', {})
        user_id = identity.get('sub') or identity.get('username')
        
        if not company_number:
            return {
                'success': False,
                'message': 'Missing required parameter: companyNumber',
                'executionArn': None,
                'executionName': None
            }
        
        if not user_id:
            return {
                'success': False,
                'message': 'User authentication required',
                'executionArn': None,
                'executionName': None
            }
        
        # Create execution name with timestamp
        timestamp = int(datetime.now().timestamp())
        execution_name = f"categorization-{company_number}-{timestamp}"
        
        # Prepare Step Functions input
        execution_input = {
            'companyNumber': company_number,
            'userId': user_id,
            'triggeredAt': timestamp,
            'triggeredBy': identity.get('username', user_id)
        }
        
        print(f"Starting Step Functions execution: {execution_name}")
        print(f"Input: {json.dumps(execution_input)}")
        
        # Start Step Functions execution
    execution = stepfunctions.start_execution(
        stateMachineArn=STATE_MACHINE_ARN,
        name=execution_name,
        input=json.dumps({
            'companyNumber': company_number
        })
    )
    
    logger.info(f"Started Step Functions execution: {execution['executionArn']}")
    
    # Extract execution name from ARN
    execution_name_from_arn = execution['executionArn'].split(':')[-1]
    
    return {
        'success': True,
        'message': f'Transaction analysis workflow started successfully',
        'executionArn': execution['executionArn'],
        'executionName': execution_name_from_arn
    }
        
    except stepfunctions.exceptions.ExecutionAlreadyExists:
        # Handle duplicate execution (e.g., user clicked button twice)
        print(f"Execution already exists: {execution_name}")
        return {
            'success': False,
            'message': 'Analysis workflow already in progress for this company',
            'executionArn': None,
            'executionName': execution_name
        }
        
    except Exception as e:
        print(f"Error starting execution: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        
        return {
            'success': False,
            'message': f'Failed to start analysis workflow: {str(e)}',
            'executionArn': None,
            'executionName': None
        }
