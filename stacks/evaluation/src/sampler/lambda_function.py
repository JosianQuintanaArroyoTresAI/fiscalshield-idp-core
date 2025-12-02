# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Evaluation Sampler Lambda

Queries ExtractionResultsTable and samples documents for evaluation
based on confidence scores using weighted sampling strategy.

Sampling Strategy:
- Low confidence (<0.7): 100% sampling
- Medium confidence (0.7-0.9): 20% sampling
- High confidence (>0.9): 5% sampling
"""

import os
import json
import logging
import random
import boto3
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Any, Optional
from boto3.dynamodb.conditions import Key, Attr


def decimal_default(obj):
    """JSON serializer for Decimal objects."""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# Initialize AWS clients
dynamodb = boto3.resource("dynamodb")
s3_client = boto3.client("s3")

# Environment variables
STACK_NAME = os.environ["STACK_NAME"]
EXTRACTION_RESULTS_TABLE = os.environ["EXTRACTION_RESULTS_TABLE"]
EVALUATION_METRICS_TABLE = os.environ["EVALUATION_METRICS_TABLE"]
BATCH_JOBS_TABLE = os.environ["BATCH_JOBS_TABLE"]
EVALUATION_BUCKET = os.environ["EVALUATION_BUCKET"]
LOW_CONFIDENCE_THRESHOLD = float(os.environ.get("LOW_CONFIDENCE_THRESHOLD", "0.7"))
MEDIUM_SAMPLING_RATE = float(os.environ.get("MEDIUM_SAMPLING_RATE", "20")) / 100
HIGH_SAMPLING_RATE = float(os.environ.get("HIGH_SAMPLING_RATE", "5")) / 100


def discover_extraction_table() -> str:
    """
    Discover the actual ExtractionResultsTable name by looking for pattern.
    
    Handles CloudFormation-generated suffixes like:
    fiscalshield-idp-dev-ExtractionResultsTable-ODNDYL7KUECH
    
    Returns:
        Full table name with suffix
    """
    try:
        # Try exact name first (from parameter)
        table_name = EXTRACTION_RESULTS_TABLE
        table = dynamodb.Table(table_name)
        table.load()  # Verify table exists
        logger.info(f"Found extraction results table: {table_name}")
        return table_name
    except Exception as e:
        logger.warning(f"Exact table name not found: {e}")
    
    # Fallback: List all tables and find matching pattern
    client = boto3.client("dynamodb")
    try:
        response = client.list_tables()
        prefix = f"{STACK_NAME}-ExtractionResultsTable"
        
        matching_tables = [
            name for name in response.get("TableNames", [])
            if name.startswith(prefix)
        ]
        
        if matching_tables:
            table_name = matching_tables[0]
            logger.info(f"Discovered extraction results table: {table_name}")
            return table_name
        else:
            raise ValueError(f"No table found matching pattern: {prefix}*")
    
    except Exception as e:
        logger.error(f"Failed to discover extraction table: {e}")
        raise


def discover_table(pattern: str) -> str:
    """
    Discover a DynamoDB table by pattern.
    
    Args:
        pattern: Pattern to match in table name (e.g., 'fiscalshield-idp-dev-ValidationRequestsTable')
        
    Returns:
        Full table name with CloudFormation suffix
        
    Raises:
        ValueError: If table not found
    """
    client = boto3.client("dynamodb")
    try:
        response = client.list_tables()
        
        matching_tables = [
            name for name in response.get("TableNames", [])
            if pattern in name
        ]
        
        if matching_tables:
            table_name = matching_tables[0]
            logger.info(f"Discovered table matching '{pattern}': {table_name}")
            return table_name
        else:
            raise ValueError(f"No table found matching pattern: {pattern}")
    
    except Exception as e:
        logger.error(f"Failed to discover table '{pattern}': {e}")
        raise


def query_recent_extractions(
    table_name: str,
    lookback_days: int = 1
) -> List[Dict[str, Any]]:
    """
    Query extraction results from the last N days.
    
    Uses GSI1-UserTypeDate index to efficiently query recent documents.
    
    Args:
        table_name: Name of ExtractionResultsTable
        lookback_days: Number of days to look back
        
    Returns:
        List of extraction result items
    """
    table = dynamodb.Table(table_name)
    
    # Calculate timestamp for lookback
    cutoff_timestamp = int((datetime.utcnow() - timedelta(days=lookback_days)).timestamp())
    
    logger.info(f"Querying extractions since timestamp: {cutoff_timestamp}")
    
    # Query all document types (INVOICE, BANK_STATEMENT, etc.)
    # Note: This is a full scan since we need all users and types
    # For production, consider using GSI1 with specific user/type patterns
    
    results = []
    try:
        # Scan with filter for recent documents
        response = table.scan(
            FilterExpression=Attr("ProcessedAt").gte(cutoff_timestamp)
        )
        
        results.extend(response.get("Items", []))
        
        # Handle pagination
        while "LastEvaluatedKey" in response:
            response = table.scan(
                FilterExpression=Attr("ProcessedAt").gte(cutoff_timestamp),
                ExclusiveStartKey=response["LastEvaluatedKey"]
            )
            results.extend(response.get("Items", []))
        
        logger.info(f"Found {len(results)} extraction results from last {lookback_days} days")
        return results
    
    except Exception as e:
        logger.error(f"Error querying extraction results: {e}")
        raise


def sample_by_confidence(
    items: List[Dict[str, Any]]
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Apply weighted sampling based on confidence scores.
    
    Args:
        items: List of extraction result items
        
    Returns:
        Dictionary with keys: low_confidence, medium_confidence, high_confidence
    """
    sampled = {
        "low_confidence": [],
        "medium_confidence": [],
        "high_confidence": [],
        "skipped": []
    }
    
    for item in items:
        # Get confidence score (default to 1.0 if not present)
        confidence = float(item.get("ConfidenceScore", Decimal("1.0")))
        
        if confidence < LOW_CONFIDENCE_THRESHOLD:
            # Always sample low confidence
            sampled["low_confidence"].append(item)
        
        elif confidence < 0.9:
            # Sample medium confidence at configured rate
            if random.random() < MEDIUM_SAMPLING_RATE:
                sampled["medium_confidence"].append(item)
            else:
                sampled["skipped"].append(item)
        
        else:
            # Sample high confidence at configured rate
            if random.random() < HIGH_SAMPLING_RATE:
                sampled["high_confidence"].append(item)
            else:
                sampled["skipped"].append(item)
    
    total_sampled = (
        len(sampled["low_confidence"]) +
        len(sampled["medium_confidence"]) +
        len(sampled["high_confidence"])
    )
    
    logger.info(
        f"Sampling results: "
        f"{len(sampled['low_confidence'])} low-conf, "
        f"{len(sampled['medium_confidence'])} medium-conf, "
        f"{len(sampled['high_confidence'])} high-conf, "
        f"{len(sampled['skipped'])} skipped. "
        f"Total sampled: {total_sampled}/{len(items)}"
    )
    
    return sampled


def prepare_evaluation_batch(
    sampled_items: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, Any]:
    """
    Prepare batch of documents for re-evaluation.
    
    Creates manifest file for batch inference or direct processing.
    
    Args:
        sampled_items: Dictionary of sampled items by confidence tier
        
    Returns:
        Batch job metadata
    """
    evaluation_id = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    
    # Flatten all sampled items
    all_samples = (
        sampled_items["low_confidence"] +
        sampled_items["medium_confidence"] +
        sampled_items["high_confidence"]
    )
    
    # Discover validation table for classification data
    validation_table_name = None
    try:
        validation_table_name = discover_table(f"{STACK_NAME}-ValidationRequestsTable")
        logger.info(f"Found validation table: {validation_table_name}")
    except Exception as e:
        logger.warning(f"Validation table not found (classification metrics will be skipped): {e}")
    
    # Create batch manifest
    batch_manifest = []
    for item in all_samples:
        manifest_item = {
            "documentId": item["DocumentId"],
            "sectionId": item.get("SectionId", "1"),
            "documentType": item.get("DocumentType", "INVOICE"),
            "s3Uri": item["DocumentId"],  # DocumentId is the S3 key (e.g., users/xxx/file.pdf)
            "originalConfidence": float(item.get("ConfidenceScore", 1.0)),
            "originalExtraction": item,  # Include full extraction result for comparison
            "confidenceTier": (
                "low" if item in sampled_items["low_confidence"]
                else "medium" if item in sampled_items["medium_confidence"]
                else "high"
            )
        }
        
        # Fetch classification validation data if available
        if validation_table_name:
            try:
                validation_table = dynamodb.Table(validation_table_name)
                doc_id = item.get("DocumentId", "")
                
                # Query validation table for this document using GSI1-DocumentValidations
                response = validation_table.query(
                    IndexName="GSI1-DocumentValidations",
                    KeyConditionExpression=Key("DocumentId").eq(doc_id),
                    Limit=1,  # Get most recent validation
                    ScanIndexForward=False  # Sort descending by CreatedAt
                )
                
                if response.get("Items"):
                    validation_item = response["Items"][0]  # Get most recent
                    manifest_item["classificationValidation"] = {
                        "userClassification": validation_item.get("UserSelection"),
                        "modelClassification": validation_item.get("ModelPrediction"),
                        "modelConfidence": float(validation_item.get("ModelConfidence", 0)),
                        "validationMatch": validation_item.get("ValidationMatch", False)
                    }
                    logger.info(f"Found classification validation for {doc_id}: user={validation_item.get('UserSelection')}, model={validation_item.get('ModelPrediction')}")
            except Exception as e:
                logger.warning(f"Could not fetch validation data for {item.get('DocumentId')}: {e}")
        
        batch_manifest.append(manifest_item)
    
    # Upload manifest to S3
    manifest_key = f"batch-inputs/{evaluation_id}/manifest.jsonl"
    
    # Convert to JSONL format (one JSON object per line)
    manifest_content = "\n".join([json.dumps(item, default=decimal_default) for item in batch_manifest])
    
    s3_client.put_object(
        Bucket=EVALUATION_BUCKET,
        Key=manifest_key,
        Body=manifest_content.encode("utf-8"),
        ContentType="application/jsonlines"
    )
    
    logger.info(f"Uploaded batch manifest: s3://{EVALUATION_BUCKET}/{manifest_key}")
    
    # Create batch job metadata
    batch_metadata = {
        "evaluationId": evaluation_id,
        "manifestUri": f"s3://{EVALUATION_BUCKET}/{manifest_key}",
        "totalDocuments": len(all_samples),
        "lowConfidenceCount": len(sampled_items["low_confidence"]),
        "mediumConfidenceCount": len(sampled_items["medium_confidence"]),
        "highConfidenceCount": len(sampled_items["high_confidence"]),
        "createdAt": int(datetime.utcnow().timestamp()),
        "status": "PENDING"
    }
    
    # Store in BatchJobsTable
    batch_table = dynamodb.Table(BATCH_JOBS_TABLE)
    batch_table.put_item(Item={
        "JobId": evaluation_id,
        "Status": "PENDING",
        "CreatedAt": batch_metadata["createdAt"],
        "ManifestUri": batch_metadata["manifestUri"],
        "TotalDocuments": batch_metadata["totalDocuments"],
        "Metadata": batch_metadata
    })
    
    return batch_metadata


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for sampling documents for evaluation.
    
    Args:
        event: Contains optional 'lookbackDays' parameter
        context: Lambda context
        
    Returns:
        Batch job metadata for downstream processing
    """
    try:
        lookback_days = event.get("lookbackDays", 1)
        
        logger.info(f"Starting evaluation sampling for last {lookback_days} days")
        
        # Step 1: Discover extraction results table
        table_name = discover_extraction_table()
        
        # Step 2: Query recent extractions
        recent_extractions = query_recent_extractions(table_name, lookback_days)
        
        if not recent_extractions:
            logger.warning("No recent extractions found - skipping evaluation")
            return {
                "statusCode": 200,
                "message": "No documents to evaluate",
                "totalDocuments": 0
            }
        
        # Step 3: Sample by confidence
        sampled_items = sample_by_confidence(recent_extractions)
        
        # Step 4: Prepare evaluation batch
        batch_metadata = prepare_evaluation_batch(sampled_items)
        
        logger.info(f"Evaluation batch prepared: {batch_metadata['evaluationId']}")
        
        # Check if batch inference is enabled from environment
        use_batch = os.environ.get("BATCH_INFERENCE_ENABLED", "true").lower() == "true"
        
        return {
            "statusCode": 200,
            "batchMetadata": batch_metadata,
            "totalDocuments": batch_metadata["totalDocuments"],
            "useBatchInference": use_batch
        }
    
    except Exception as e:
        logger.exception("Error in sampler function")
        raise
