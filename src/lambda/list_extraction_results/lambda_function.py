# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Lambda function for listing extraction results from DynamoDB.
Queries ExtractionResultsTable using GSI7-ClientTypeDate index.
Supports filtering by company number and document type (INVOICE or BANK_STATEMENT).
"""

import json
import os
from typing import Dict, List, Any, Optional
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

# Environment variables
EXTRACTION_RESULTS_TABLE = os.environ.get("EXTRACTION_RESULTS_TABLE")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

# AWS clients
dynamodb = boto3.resource("dynamodb")
dynamodb_client = boto3.client("dynamodb")


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder for DynamoDB Decimal types"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            # Convert to int if it's a whole number (e.g., timestamps)
            if obj % 1 == 0:
                return int(obj)
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


def list_extraction_results(
    user_id: str,
    company_number: str,
    document_type: str,
    limit: int = 50,
    next_token: Optional[str] = None,
    view_type: Optional[str] = "transactions"  # NEW: "transactions" or "summary"
) -> Dict[str, Any]:
    """
    List extraction results for a given company and document type.
    
    Uses GSI7-ClientTypeDate index to efficiently query by company and document type.
    GSI7 has ProjectionType: ALL, so we get full items without needing batch_get_item.
    
    Args:
        user_id: Authenticated user ID
        company_number: UK Companies House number (e.g., "12345678")
        document_type: "INVOICE" or "BANK_STATEMENT"
        limit: Maximum number of results to return (default: 50)
        next_token: Pagination token for fetching next page
        view_type: For BANK_STATEMENT: "transactions" returns individual transactions,
                   "summary" returns statement summaries
    
    Returns:
        Dictionary with items list and optional nextToken
    """
    print(f"Querying extraction results - Company: {company_number}, Type: {document_type}, User: {user_id}, View: {view_type}")
    
    extraction_table = dynamodb.Table(EXTRACTION_RESULTS_TABLE)
    
    # Build GSI7 query: client#{CompanyNumber}#type#{DocumentType}
    gsi6_pk = f"client#{company_number}#type#{document_type}"
    
    print(f"🔍 DEBUG: Querying GSI6PK = '{gsi6_pk}'")
    
    query_params = {
        "IndexName": "GSI7-ClientTypeDate",
        "KeyConditionExpression": Key("GSI6PK").eq(gsi6_pk),
        "ScanIndexForward": False,  # Sort by ProcessedAt descending (newest first)
        "Limit": limit * 10  # Get more to allow for filtering
    }
    
    # Handle pagination
    if next_token:
        try:
            query_params["ExclusiveStartKey"] = json.loads(next_token)
        except Exception as e:
            print(f"WARNING: Invalid pagination token: {e}")
    
    print(f"🔍 DEBUG: Query params: {json.dumps(query_params, default=str)}")
    
    response = extraction_table.query(**query_params)
    
    print(f"🔍 DEBUG: Query response - Count: {response.get('Count', 0)}, ScannedCount: {response.get('ScannedCount', 0)}")
    
    items = response.get("Items", [])
    
    # Security filter: only return items for the authenticated user
    user_items = [
        item for item in items
        if item.get("UserId") == user_id
    ]
    
    print(f"Found {len(items)} items, {len(user_items)} belong to user {user_id}")
    
    # Filter by SK pattern based on view_type
    if document_type == "BANK_STATEMENT":
        if view_type == "transactions":
            # Return individual transaction records (SK contains '#txn#')
            filtered_items = [
                item for item in user_items
                if '#txn#' in item.get('SK', '')
            ]
            print(f"Filtered to {len(filtered_items)} transaction records")
        else:
            # Return statement summary records (SK contains '#statement#summary')
            filtered_items = [
                item for item in user_items
                if '#statement#summary' in item.get('SK', '')
            ]
            print(f"Filtered to {len(filtered_items)} statement summary records")
    elif document_type == "INVOICE":
        # For invoices, return invoice records (SK contains '#invoice#')
        filtered_items = [
            item for item in user_items
            if '#invoice#' in item.get('SK', '')
        ]
        print(f"Filtered to {len(filtered_items)} invoice records")
    else:
        filtered_items = user_items
    
    # Limit to requested number
    filtered_items = filtered_items[:limit]
    
    # Convert Decimal to float for JSON serialization
    serialized_items = json.loads(json.dumps(filtered_items, cls=DecimalEncoder))
    
    result = {
        "items": serialized_items
    }
    
    # Add pagination token if more results available
    if "LastEvaluatedKey" in response:
        result["nextToken"] = json.dumps(response["LastEvaluatedKey"], cls=DecimalEncoder)
    
    return result


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for listExtractionResults GraphQL query.
    
    Args:
        event: AppSync event containing identity and arguments
        context: Lambda context
        
    Returns:
        Dict with items and nextToken
    """
    print(f"Event: {json.dumps(event, default=str)}")
    
    try:
        # Extract user ID from Cognito identity
        identity = event.get("identity", {})
        # Use Cognito sub (UUID) not username for consistency with invoice storage
        user_id = identity.get("sub") or identity.get("username")
        
        if not user_id:
            print("ERROR: No user ID found in identity")
            raise ValueError("User ID not found in request")
        
        # Extract arguments
        arguments = event.get("arguments", {})
        company_number = arguments.get("companyNumber")
        document_type = arguments.get("documentType")
        limit = arguments.get("limit", 50)
        next_token = arguments.get("nextToken")
        view_type = arguments.get("viewType", "transactions")  # NEW: Default to transactions for BANK_STATEMENT
        
        # Validate required arguments
        if not company_number:
            raise ValueError("companyNumber is required")
        
        if not document_type:
            raise ValueError("documentType is required")
        
        # Validate document type
        valid_types = ["INVOICE", "BANK_STATEMENT"]
        if document_type not in valid_types:
            raise ValueError(f"documentType must be one of: {', '.join(valid_types)}")
        
        print(f"Processing request - User: {user_id}, Company: {company_number}, Type: {document_type}, View: {view_type}")
        
        # Query extraction results
        result = list_extraction_results(
            user_id=user_id,
            company_number=company_number,
            document_type=document_type,
            limit=limit,
            next_token=next_token,
            view_type=view_type  # Pass view_type parameter
        )
        
        print(f"Successfully retrieved {len(result['items'])} extraction results")
        
        # Debug: Log first item to see what's being returned
        if result['items']:
            first_item = result['items'][0]
            print(f"🔍 DEBUG: First item keys: {list(first_item.keys())}")
            print(f"🔍 DEBUG: DocumentType value: {first_item.get('DocumentType')} (type: {type(first_item.get('DocumentType'))})")
            print(f"🔍 DEBUG: Full first item: {json.dumps(first_item, default=str)[:500]}")
        
        return result
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise
