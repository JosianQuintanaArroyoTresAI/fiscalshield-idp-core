# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Lambda function to list all companies registered under a user.
Queries ExtractionResultsTable to find unique company registrations for a user.
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
EXTRACTION_RESULTS_TABLE = os.environ.get("EXTRACTION_RESULTS_TABLE")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

# AWS clients
dynamodb = boto3.resource("dynamodb")


def get_user_companies(user_id: str) -> List[Dict[str, Any]]:
    """
    Query DynamoDB to get all unique companies for a user.
    
    This function queries the ExtractionResultsTable using GSI2-UserAllDocs
    to find all documents for a user, then extracts unique companies.
    
    Args:
        user_id: The Cognito user ID
        
    Returns:
        List of company dictionaries with company details
    """
    print(f"Querying companies for user: {user_id}")
    
    table = dynamodb.Table(EXTRACTION_RESULTS_TABLE)
    
    # Query GSI2-UserAllDocs to get all user's documents
    response = table.query(
        IndexName="GSI2-UserAllDocs",
        KeyConditionExpression=Key("UserId").eq(user_id),
        ProjectionExpression=(
            "PK, SK, UserId, CompanyNumber, CompanyName, "
            "ProcessedAt, DocumentType, DocumentId, TotalAmount"
        ),
    )
    
    items = response.get("Items", [])
    
    # Handle pagination if there are more results
    while "LastEvaluatedKey" in response:
        response = table.query(
            IndexName="GSI2-UserAllDocs",
            KeyConditionExpression=Key("UserId").eq(user_id),
            ProjectionExpression=(
                "PK, SK, UserId, CompanyNumber, CompanyName, "
                "ProcessedAt, DocumentType, DocumentId, TotalAmount"
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
                "first_registered": item.get("ProcessedAt"),
                "last_activity": item.get("ProcessedAt"),
                "document_types": set(),
            }
        
        # Update company data
        company = companies_map[company_number]
        company["document_count"] += 1
        
        # Update timestamps
        processed_at = item.get("ProcessedAt")
        if processed_at:
            if processed_at < company["first_registered"]:
                company["first_registered"] = processed_at
            if processed_at > company["last_activity"]:
                company["last_activity"] = processed_at
        
        # Track document types
        doc_type = item.get("DocumentType")
        if doc_type:
            company["document_types"].add(doc_type)
    
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
