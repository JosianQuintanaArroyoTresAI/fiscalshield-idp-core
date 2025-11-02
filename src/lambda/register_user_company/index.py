# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Lambda resolver for registerUserCompany mutation.
Registers a company as a client for a user in the UserProfile table.
"""

import os
import json
import time
import logging
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["USER_PROFILE_TABLE"])


def handler(event, context):
    """
    Register a company for a user.
    
    Args:
        event: AppSync event with identity and arguments
        context: Lambda context
        
    Returns:
        Boolean indicating success
    """
    logger.info(f"registerUserCompany invoked: {json.dumps(event)}")
    
    try:
        # Extract user ID from Cognito identity
        identity = event.get("identity", {})
        user_id = identity.get("username") or identity.get("sub")
        
        if not user_id:
            logger.error("No user ID found in identity")
            raise ValueError("User not authenticated")
        
        # Extract company details from arguments
        arguments = event.get("arguments", {})
        company_number = arguments.get("companyNumber")
        company_name = arguments.get("companyName")
        
        if not company_number or not company_name:
            raise ValueError("companyNumber and companyName are required")
        
        logger.info(f"Registering company {company_name} ({company_number}) for user {user_id}")
        
        # Prepare item for UserProfile table
        current_timestamp = int(time.time())
        item = {
            "PK": user_id,
            "SK": f"COMPANY#{company_number}",
            "DataType": "COMPANY",
            "CompanyNumber": company_number,
            "CompanyName": company_name,
            "CreatedAt": current_timestamp,
            "UpdatedAt": current_timestamp,
        }
        
        # Write to DynamoDB with condition to prevent duplicates
        try:
            table.put_item(
                Item=item,
                ConditionExpression="attribute_not_exists(PK) AND attribute_not_exists(SK)"
            )
            logger.info(f"Successfully registered company {company_number} for user {user_id}")
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                # Company already registered - update timestamp
                logger.info(f"Company {company_number} already registered, updating timestamp")
                table.update_item(
                    Key={"PK": user_id, "SK": f"COMPANY#{company_number}"},
                    UpdateExpression="SET UpdatedAt = :timestamp, CompanyName = :name",
                    ExpressionAttributeValues={
                        ":timestamp": current_timestamp,
                        ":name": company_name
                    }
                )
            else:
                raise
        
        return True
        
    except Exception as e:
        logger.error(f"Error registering company: {str(e)}", exc_info=True)
        raise
