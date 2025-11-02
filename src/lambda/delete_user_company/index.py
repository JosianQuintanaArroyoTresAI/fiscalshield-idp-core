# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Lambda resolver for deleteUserCompany mutation.
Deletes a company association from a user's profile in the UserProfile table.
"""

import os
import json
import logging
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["USER_PROFILE_TABLE"])


def handler(event, context):
    """
    Delete a company association for a user.
    
    Args:
        event: AppSync event with identity and arguments
        context: Lambda context
        
    Returns:
        Boolean indicating success
    """
    logger.info(f"deleteUserCompany invoked: {json.dumps(event)}")
    
    try:
        # Extract user ID from Cognito identity
        identity = event.get("identity", {})
        user_id = identity.get("username") or identity.get("sub")
        
        if not user_id:
            logger.error("No user ID found in identity")
            raise ValueError("User not authenticated")
        
        # Extract company number from arguments
        arguments = event.get("arguments", {})
        company_number = arguments.get("companyNumber")
        
        if not company_number:
            raise ValueError("companyNumber is required")
        
        logger.info(f"Deleting company {company_number} for user {user_id}")
        
        # Delete from DynamoDB
        try:
            table.delete_item(
                Key={
                    "PK": user_id,
                    "SK": f"COMPANY#{company_number}"
                },
                ConditionExpression="attribute_exists(PK) AND attribute_exists(SK)"
            )
            logger.info(f"Successfully deleted company {company_number} for user {user_id}")
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                logger.warning(f"Company {company_number} not found for user {user_id}")
                # Return true anyway - idempotent operation
                return True
            else:
                raise
                
    except Exception as e:
        logger.error(f"Error deleting company: {str(e)}", exc_info=True)
        raise
