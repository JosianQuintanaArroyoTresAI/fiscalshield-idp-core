# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Lambda function to list all companies registered under a user.
Queries TrackingTable to find unique company registrations for a user.
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
TRACKING_TABLE = os.environ.get("TRACKING_TABLE")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

# AWS clients
dynamodb = boto3.resource("dynamodb")


def get_user_companies(user_id: str) -> List[Dict[str, Any]]:
    """
    Query DynamoDB to get all unique companies for a user.
    
    This function queries the TrackingTable using GSI1
    to find all documents for a user, then extracts unique companies.
    
    Args:
        user_id: The Cognito user ID
        
    Returns:
        List of company dictionaries with company details
    """
    print(f"Querying companies for user: {user_id}")
    
    table = dynamodb.Table(TRACKING_TABLE)
    
    # Query GSI1 to get all user's documents
    response = table.query(
        IndexName="GSI1",
        KeyConditionExpression=Key("UserId").eq(user_id),
        ProjectionExpression=(
            "PK, SK, UserId, CompanyNumber, CompanyName, "
            "QueuedTime, ObjectKey, WorkflowStatus"
        ),
    )
    
    items = response.get("Items", [])
    
    # Handle pagination if there are more results
    while "LastEvaluatedKey" in response:
        response = table.query(
            IndexName="GSI1",
            KeyConditionExpression=Key("UserId").eq(user_id),
            ProjectionExpression=(
                "PK, SK, UserId, CompanyNumber, CompanyName, "
                "QueuedTime, ObjectKey, WorkflowStatus"
            ),
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        items.extend(response.get("Items", []))
    
    print(f"Found {len(items)} documents for user {user_id}")
    
    # Group by company number and aggregate data
    companies_map: Dict[str, Dict[str, Any]] = {}
    
    for item in items:
        company_number = item.get("CompanyNumber")
        if not company_number:
            continue
            
        if company_number not in companies_map:
            companies_map[company_number] = {
                "company_number": company_number,
                "company_name": item.get("CompanyName", "Unknown Company"),
                "user_id": user_id,
                "document_count": 0,
                "first_registered": item.get("QueuedTime"),
                "last_activity": item.get("QueuedTime"),
                "document_types": set(),
            }
        
        # Update company data
        company = companies_map[company_number]
        company["document_count"] += 1
        
        # Update timestamps
        queued_time = item.get("QueuedTime")
        if queued_time:
            if queued_time < company["first_registered"]:
                company["first_registered"] = queued_time
            if queued_time > company["last_activity"]:
                company["last_activity"] = queued_time
        
        # Track document types (from filename extension)
        object_key = item.get("ObjectKey", "")
        if object_key:
            ext = object_key.split(".")[-1].lower() if "." in object_key else "unknown"
            company["document_types"].add(ext)
    
    # Convert to list and format for response
    companies = []
    for company_number, company_data in companies_map.items():
        companies.append({
            "company_number": company_data["company_number"],
            "company_name": company_data["company_name"],
            "user_id": company_data["user_id"],
            "document_count": company_data["document_count"],
            "first_registered": company_data["first_registered"],
            "last_activity": company_data["last_activity"],
            "document_types": sorted(list(company_data["document_types"])),
        })
    
    # Sort by last activity (most recent first)
    companies.sort(key=lambda x: x["last_activity"], reverse=True)
    
    print(f"Returning {len(companies)} unique companies")
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
