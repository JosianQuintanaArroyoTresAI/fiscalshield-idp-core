# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Lambda function for aggregating validation metrics from ValidationRequestsTable.
Provides metrics for admin dashboard to track classification accuracy and drift.
"""

import json
import os
from typing import Dict, List, Any, Optional
from decimal import Decimal
from datetime import datetime, timedelta
from collections import defaultdict

import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

# Environment variables
VALIDATION_REQUESTS_TABLE = os.environ.get("VALIDATION_REQUESTS_TABLE")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

# AWS clients
dynamodb = boto3.resource("dynamodb")


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder for DynamoDB Decimal types"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


def get_validation_metrics(
    time_range_days: int = 30,
    company_number: Optional[str] = None,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Aggregate validation metrics from ValidationRequestsTable.
    
    Args:
        time_range_days: Number of days to look back (default 30)
        company_number: Optional filter by company
        user_id: Optional filter by user
        
    Returns:
        dict: Aggregated metrics
    """
    
    if not VALIDATION_REQUESTS_TABLE:
        raise ValueError("VALIDATION_REQUESTS_TABLE environment variable not set")
    
    table = dynamodb.Table(VALIDATION_REQUESTS_TABLE)
    
    # Calculate timestamp for time range
    cutoff_timestamp = int((datetime.now() - timedelta(days=time_range_days)).timestamp())
    
    # Scan table (for POC - in production, use GSI2-StatusDate for better performance)
    scan_kwargs = {
        "FilterExpression": Key("CreatedAt").gte(cutoff_timestamp)
    }
    
    if company_number:
        scan_kwargs["FilterExpression"] &= Attr("CompanyNumber").eq(company_number)
    
    if user_id:
        scan_kwargs["FilterExpression"] &= Attr("UserId").eq(user_id)
    
    items = []
    try:
        response = table.scan(**scan_kwargs)
        items.extend(response.get("Items", []))
        
        # Handle pagination
        while "LastEvaluatedKey" in response:
            scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
            response = table.scan(**scan_kwargs)
            items.extend(response.get("Items", []))
            
    except ClientError as e:
        print(f"Error scanning ValidationRequestsTable: {e}")
        raise
    
    # Aggregate metrics
    total_validations = len(items)
    matches = sum(1 for item in items if item.get("ValidationMatch", False))
    mismatches = total_validations - matches
    
    # By document type
    by_type = defaultdict(lambda: {"total": 0, "matches": 0, "mismatches": 0, "highConfidenceMismatches": 0})
    
    # By confidence bucket
    confidence_buckets = {
        "0.0-0.5": {"total": 0, "matches": 0},
        "0.5-0.7": {"total": 0, "matches": 0},
        "0.7-0.85": {"total": 0, "matches": 0},
        "0.85-0.95": {"total": 0, "matches": 0},
        "0.95-1.0": {"total": 0, "matches": 0},
    }
    
    # Recent mismatches for review
    high_confidence_mismatches = []
    
    for item in items:
        user_selection = item.get("UserSelection", "unknown")
        model_prediction = item.get("ModelPrediction", "unknown")
        confidence = float(item.get("ModelConfidence", 0))
        is_match = item.get("ValidationMatch", False)
        
        # By type
        by_type[user_selection]["total"] += 1
        if is_match:
            by_type[user_selection]["matches"] += 1
        else:
            by_type[user_selection]["mismatches"] += 1
            if confidence > 0.90:
                by_type[user_selection]["highConfidenceMismatches"] += 1
                
                # Collect recent high-confidence mismatches for review
                high_confidence_mismatches.append({
                    "documentId": item.get("DocumentId"),
                    "userSelection": user_selection,
                    "modelPrediction": model_prediction,
                    "confidence": confidence,
                    "createdAt": item.get("CreatedAt"),
                    "validationId": item.get("ValidationId"),
                    "company": item.get("CompanyName", "Unknown")
                })
        
        # By confidence bucket
        if confidence < 0.5:
            bucket = "0.0-0.5"
        elif confidence < 0.7:
            bucket = "0.5-0.7"
        elif confidence < 0.85:
            bucket = "0.7-0.85"
        elif confidence < 0.95:
            bucket = "0.85-0.95"
        else:
            bucket = "0.95-1.0"
        
        confidence_buckets[bucket]["total"] += 1
        if is_match:
            confidence_buckets[bucket]["matches"] += 1
    
    # Calculate percentages
    match_rate = (matches / total_validations * 100) if total_validations > 0 else 0
    mismatch_rate = (mismatches / total_validations * 100) if total_validations > 0 else 0
    
    # Sort high-confidence mismatches by date (most recent first)
    high_confidence_mismatches.sort(key=lambda x: x["createdAt"], reverse=True)
    
    # Build response
    metrics = {
        "timeRangeDays": time_range_days,
        "totalValidations": total_validations,
        "matches": matches,
        "mismatches": mismatches,
        "matchRatePercent": round(match_rate, 2),
        "mismatchRatePercent": round(mismatch_rate, 2),
        "byDocumentType": json.dumps(dict(by_type)),  # GraphQL AWSJSON expects string
        "byConfidenceBucket": json.dumps(confidence_buckets),  # GraphQL AWSJSON expects string
        "highConfidenceMismatches": high_confidence_mismatches[:50],  # Limit to 50 most recent
        "summary": {
            "modelAccuracy": f"{match_rate:.1f}%",
            "totalDocumentsValidated": total_validations,
            "requiresAttention": sum(1 for item in items if not item.get("ValidationMatch") and float(item.get("ModelConfidence", 0)) > 0.90),
        }
    }
    
    return metrics


def lambda_handler(event, context):
    """
    Lambda handler for validation metrics aggregation.
    
    Expected event:
    {
        "timeRangeDays": 30,
        "companyNumber": "12345678",  // optional
        "userId": "abc-123-def"       // optional
    }
    """
    
    print(f"Event: {json.dumps(event)}")
    
    try:
        # Parse arguments
        arguments = event.get("arguments", {})
        time_range_days = int(arguments.get("timeRangeDays", 30))
        company_number = arguments.get("companyNumber")
        user_id = arguments.get("userId")
        
        # Get metrics
        metrics = get_validation_metrics(
            time_range_days=time_range_days,
            company_number=company_number,
            user_id=user_id
        )
        
        # Return response
        return {
            "statusCode": 200,
            "body": json.dumps(metrics, cls=DecimalEncoder),
            "metrics": metrics  # For GraphQL resolver
        }
        
    except Exception as e:
        print(f"Error getting validation metrics: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
            "metrics": None
        }
