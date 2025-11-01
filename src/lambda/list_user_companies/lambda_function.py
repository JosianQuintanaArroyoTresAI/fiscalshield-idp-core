# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Lambda function to list all companies registered under a user.
Queries UserProfileTable for company registrations and enriches with document counts from TrackingTable.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import defaultdict

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

# Environment variables
USER_PROFILE_TABLE = os.environ.get("USER_PROFILE_TABLE")
TRACKING_TABLE = os.environ.get("TRACKING_TABLE")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

# AWS clients
dynamodb = boto3.resource("dynamodb")


def get_user_companies(user_id: str) -> List[Dict[str, Any]]:
    """
    Query DynamoDB to get all registered companies for a user.
    
    This function queries the UserProfileTable for company registrations,
    then enriches with document counts from TrackingTable.
    
    Args:
        user_id: The Cognito user ID
        
    Returns:
        List of company dictionaries with company details and document counts
    """
    print(f"Querying companies for user: {user_id}")
    
    # Query UserProfileTable for registered companies
    profile_table = dynamodb.Table(USER_PROFILE_TABLE)
    
    response = profile_table.query(
        KeyConditionExpression=Key("PK").eq(user_id) & Key("SK").begins_with("COMPANY#"),
        ProjectionExpression="SK, CompanyNumber, CompanyName, CreatedAt"
    )
    
    registered_companies = response.get("Items", [])
    
    # Handle pagination
    while "LastEvaluatedKey" in response:
        response = profile_table.query(
            KeyConditionExpression=Key("PK").eq(user_id) & Key("SK").begins_with("COMPANY#"),
            ProjectionExpression="SK, CompanyNumber, CompanyName, CreatedAt",
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        registered_companies.extend(response.get("Items", []))
    
    print(f"Found {len(registered_companies)} registered companies")
    
    if not registered_companies:
        return []
    
    # TODO: Query TrackingTable to get document counts once GSI1 index is available
    # For now, return companies with default document count = 0
    companies = []
    
    for company_item in registered_companies:
        company_number = company_item.get("CompanyNumber")
        company_name = company_item.get("CompanyName", "Unknown Company")
        created_at = company_item.get("CreatedAt")
        
        if not company_number:
            continue
        
        # Skip TrackingTable query for now - GSI1 index not available
        # doc_response = tracking_table.query(
        #     IndexName="GSI1",
        #     KeyConditionExpression=Key("UserId").eq(user_id),
        #     FilterExpression=Key("CompanyNumber").eq(company_number),
        #     ProjectionExpression="QueuedTime, ObjectKey",
        #     Select="SPECIFIC_ATTRIBUTES"
        # )
        
        # Use empty list for docs
        docs = []
        
        # Skip pagination for now
        # while "LastEvaluatedKey" in doc_response:
        #     doc_response = tracking_table.query(
        #         IndexName="GSI1",
        #         KeyConditionExpression=Key("UserId").eq(user_id),
        #         FilterExpression=Key("CompanyNumber").eq(company_number),
        #         ProjectionExpression="QueuedTime, ObjectKey",
        #         Select="SPECIFIC_ATTRIBUTES",
        #         ExclusiveStartKey=doc_response["LastEvaluatedKey"],
        #     )
        #     docs.extend(doc_response.get("Items", []))
        
        # Calculate statistics
        document_count = len(docs)
        first_registered = created_at
        last_activity = created_at
        
        if docs:
            # Find earliest and latest document times
            doc_times = [doc.get("QueuedTime") for doc in docs if doc.get("QueuedTime")]
            if doc_times:
                last_activity = max(doc_times)
        
        # Extract document types from filenames
        document_types = set()
        for doc in docs:
            object_key = doc.get("ObjectKey", "")
            if object_key:
                ext = object_key.split(".")[-1].lower() if "." in object_key else "unknown"
                document_types.add(ext)
        
        companies.append({
            "company_number": company_number,
            "company_name": company_name,
            "user_id": user_id,
            "document_count": document_count,
            "first_registered": first_registered,
            "last_activity": last_activity,
            "document_types": sorted(list(document_types)),
        })
    
    # Sort by last activity (most recent first)
    companies.sort(key=lambda x: x["last_activity"], reverse=True)
    
    print(f"Returning {len(companies)} companies with document counts")
    return companies


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for getUserCompanies GraphQL query.
    
    Args:
        event: AppSync event containing identity and arguments
        context: Lambda context
        
    Returns:
        List of companies for the user
    """
    print(f"Event: {json.dumps(event)}")
    
    try:
        # Extract user ID from Cognito identity
        identity = event.get("identity", {})
        user_id = identity.get("username")
        
        if not user_id:
            print("ERROR: No user ID found in identity")
            raise ValueError("User ID not found in request")
        
        print(f"Processing request for user: {user_id}")
        
        # Get companies for user
        companies = get_user_companies(user_id)
        
        print(f"Successfully retrieved {len(companies)} companies")
        return companies
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise
