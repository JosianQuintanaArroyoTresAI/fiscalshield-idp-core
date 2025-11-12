# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Lambda function to list extraction results (invoices, bank statements) for a company.
Queries ExtractionResultsTable using GSI6-ClientTypeDate index.
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
    next_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Query DynamoDB ExtractionResultsTable for extraction results.
    
    Uses GSI6-ClientTypeDate index to efficiently query by company and document type.
    Results are filtered by user_id for security.
    
    Args:
        user_id: Cognito user ID (for security filtering)
        company_number: Company number to filter by
        document_type: Document type (INVOICE or BANK_STATEMENT)
        limit: Maximum number of results to return
        next_token: Pagination token from previous query
        
    Returns:
        Dict with items list and optional nextToken
    """
    print(f"Querying extraction results - Company: {company_number}, Type: {document_type}, User: {user_id}")
    
    extraction_table = dynamodb.Table(EXTRACTION_RESULTS_TABLE)
    
    # Build GSI6 query: client#{CompanyNumber}#type#{DocumentType}
    gsi6_pk = f"client#{company_number}#type#{document_type}"
    
    print(f"🔍 DEBUG: Querying GSI6PK = '{gsi6_pk}'")
    
    query_params = {
        "IndexName": "GSI6-ClientTypeDate",
        "KeyConditionExpression": Key("GSI6PK").eq(gsi6_pk),
        "ScanIndexForward": False,  # Sort by ProcessedAt descending (newest first)
        "Limit": limit
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
    print(f"🔍 DEBUG: Query response - Count: {response.get('Count', 0)}, ScannedCount: {response.get('ScannedCount', 0)}")
    
    items = response.get("Items", [])
    
    # Log first item for debugging (if any)
    if items:
        first_item = items[0]
        print(f"🔍 DEBUG: First item GSI6PK = '{first_item.get('GSI6PK')}', UserId = '{first_item.get('UserId')}'")
    
    # Security filter: only return items for the authenticated user
    filtered_items = [
        item for item in items
        if item.get("UserId") == user_id
    ]
    
    print(f"Found {len(items)} items, {len(filtered_items)} belong to user {user_id}")
    
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
        
        # Validate required arguments
        if not company_number:
            raise ValueError("companyNumber is required")
        
        if not document_type:
            raise ValueError("documentType is required")
        
        # Validate document type
        valid_types = ["INVOICE", "BANK_STATEMENT"]
        if document_type not in valid_types:
            raise ValueError(f"documentType must be one of: {', '.join(valid_types)}")
        
        print(f"Processing request - User: {user_id}, Company: {company_number}, Type: {document_type}")
        
        # Query extraction results
        result = list_extraction_results(
            user_id=user_id,
            company_number=company_number,
            document_type=document_type,
            limit=limit,
            next_token=next_token
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
