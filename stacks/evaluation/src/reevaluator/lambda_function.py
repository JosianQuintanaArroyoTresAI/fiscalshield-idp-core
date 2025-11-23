# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Re-Evaluator Lambda

Fetches original document images and re-runs FULL extraction pipeline
using evaluation models for comparison with baseline extractions.

Flow:
1. Read batch manifest (from sampler)
2. For each document:
   a. Fetch original image from S3
   b. Run OCR with evaluation model
   c. Run extraction with same schema as production
   d. Store results for comparison
"""

import os
import json
import logging
import boto3
import base64
from typing import Dict, List, Any, Optional
from decimal import Decimal

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# Initialize AWS clients
s3_client = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")

# Environment variables
STACK_NAME = os.environ["STACK_NAME"]
EVALUATION_MODEL_ID = os.environ["EVALUATION_MODEL_ID"]
EVALUATION_REGION = os.environ["EVALUATION_REGION"]
EVALUATION_BUCKET = os.environ["EVALUATION_BUCKET"]
BATCH_INFERENCE_ENABLED = os.environ.get("BATCH_INFERENCE_ENABLED", "false") == "true"
BEDROCK_BATCH_ROLE_ARN = os.environ.get("BEDROCK_BATCH_ROLE_ARN", "")

# Lazy-load Bedrock client for evaluation region
_bedrock_client = None


def get_bedrock_client():
    """Get or create Bedrock client in evaluation region."""
    global _bedrock_client
    if _bedrock_client is None:
        _bedrock_client = boto3.client(
            "bedrock-runtime",
            region_name=EVALUATION_REGION
        )
    return _bedrock_client


def get_extraction_config(document_type: str) -> Dict[str, Any]:
    """
    Get extraction configuration (prompts, schema) for document type.
    
    This should match EXACTLY what production uses.
    You can either:
    1. Import from idp_common (if available)
    2. Fetch from ConfigurationTable
    3. Hardcode for common types
    
    Args:
        document_type: INVOICE, BANK_STATEMENT, etc.
        
    Returns:
        Extraction config with prompts and schema
    """
    # Option 1: Try to import from idp_common (best)
    try:
        from idp_common import get_config
        config = get_config()
        
        # Find class config for this document type
        for class_config in config.get("classes", []):
            if class_config["name"].upper() == document_type.upper():
                return {
                    "attributes": class_config.get("attributes", []),
                    "extraction_prompt": config.get("extraction", {}).get("task_prompt", ""),
                    "system_prompt": config.get("extraction", {}).get("system_prompt", "")
                }
    except Exception as e:
        logger.warning(f"Could not import idp_common config: {e}")
    
    # Option 2: Fallback to basic config for common types
    if document_type.upper() == "INVOICE":
        return {
            "attributes": [
                {"name": "InvoiceNumber", "description": "Unique invoice identifier"},
                {"name": "InvoiceDate", "description": "Invoice issue date"},
                {"name": "TotalAmount", "description": "Total amount including tax"},
                {"name": "VATAmount", "description": "VAT/tax amount"},
                {"name": "VendorName", "description": "Supplier/vendor name"},
            ],
            "extraction_prompt": "Extract the invoice details from this document.",
            "system_prompt": "You are an expert at extracting structured data from invoices."
        }
    elif document_type.upper() == "BANK_STATEMENT":
        return {
            "attributes": [
                {"name": "BankName", "description": "Financial institution name"},
                {"name": "AccountNumber", "description": "Account number"},
                {"name": "StatementPeriodStart", "description": "Start date"},
                {"name": "StatementPeriodEnd", "description": "End date"},
                {"name": "OpeningBalance", "description": "Starting balance"},
                {"name": "ClosingBalance", "description": "Ending balance"},
            ],
            "extraction_prompt": "Extract the bank statement details from this document.",
            "system_prompt": "You are an expert at extracting structured data from bank statements."
        }
    else:
        raise ValueError(f"Unknown document type: {document_type}")


def fetch_document_image(s3_uri: str) -> bytes:
    """
    Fetch original document image from S3.
    
    Args:
        s3_uri: S3 URI like s3://bucket/key/to/image.pdf
        
    Returns:
        Document bytes
    """
    # Parse S3 URI
    if not s3_uri.startswith("s3://"):
        raise ValueError(f"Invalid S3 URI: {s3_uri}")
    
    parts = s3_uri.replace("s3://", "").split("/", 1)
    bucket = parts[0]
    key = parts[1] if len(parts) > 1 else ""
    
    logger.info(f"Fetching document from s3://{bucket}/{key}")
    
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        document_bytes = response["Body"].read()
        logger.info(f"Fetched {len(document_bytes)} bytes")
        return document_bytes
    except Exception as e:
        logger.error(f"Failed to fetch document: {e}")
        raise


def run_extraction_with_evaluation_model(
    document_bytes: bytes,
    document_type: str,
    evaluation_model_id: str
) -> Dict[str, Any]:
    """
    Run FULL extraction using evaluation model (OCR + Extraction).
    
    This mimics the production extraction pipeline but with a different model.
    
    Args:
        document_bytes: Document image bytes
        document_type: INVOICE, BANK_STATEMENT, etc.
        evaluation_model_id: Model to use for evaluation
        
    Returns:
        Extraction result matching production schema
    """
    bedrock = get_bedrock_client()
    
    # Get extraction config (same as production)
    config = get_extraction_config(document_type)
    
    # Encode image to base64
    image_base64 = base64.b64encode(document_bytes).decode("utf-8")
    
    # Determine content type
    content_type = "image/png"
    if document_bytes.startswith(b"%PDF"):
        content_type = "application/pdf"
    elif document_bytes.startswith(b"\xff\xd8\xff"):
        content_type = "image/jpeg"
    
    # Build extraction prompt (same as production)
    attribute_descriptions = "\n".join([
        f"- {attr['name']}: {attr['description']}"
        for attr in config["attributes"]
    ])
    
    extraction_prompt = f"""
{config['extraction_prompt']}

Extract the following attributes:
{attribute_descriptions}

Return valid JSON with these exact field names.
"""
    
    # Prepare request body
    request_body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 4096,
        "temperature": 0.0,
        "system": config["system_prompt"],
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": content_type,
                            "data": image_base64
                        }
                    },
                    {
                        "type": "text",
                        "text": extraction_prompt
                    }
                ]
            }
        ]
    }
    
    logger.info(f"Invoking {evaluation_model_id} for extraction")
    
    try:
        # Invoke Bedrock model
        response = bedrock.invoke_model(
            modelId=evaluation_model_id,
            body=json.dumps(request_body),
            contentType="application/json",
            accept="application/json"
        )
        
        # Parse response
        response_body = json.loads(response["body"].read())
        
        # Extract text from response
        content_blocks = response_body.get("content", [])
        extracted_text = ""
        for block in content_blocks:
            if block.get("type") == "text":
                extracted_text += block.get("text", "")
        
        # Parse JSON from extracted text
        # Try to find JSON object in response
        start_idx = extracted_text.find("{")
        end_idx = extracted_text.rfind("}") + 1
        
        if start_idx != -1 and end_idx > start_idx:
            json_str = extracted_text[start_idx:end_idx]
            extraction_result = json.loads(json_str)
        else:
            logger.warning("No JSON found in response, using raw text")
            extraction_result = {"raw_response": extracted_text}
        
        logger.info(f"Extraction successful: {len(extraction_result)} fields")
        
        return {
            "inference_result": extraction_result,
            "model_id": evaluation_model_id,
            "document_type": document_type,
            "token_usage": {
                "input_tokens": response_body.get("usage", {}).get("input_tokens", 0),
                "output_tokens": response_body.get("usage", {}).get("output_tokens", 0)
            }
        }
    
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        raise


def store_evaluation_result(
    evaluation_id: str,
    document_id: str,
    section_id: str,
    baseline_extraction_uri: str,
    evaluation_extraction: Dict[str, Any],
    metadata: Dict[str, Any]
) -> None:
    """
    Store evaluation extraction result for later comparison.
    
    Args:
        evaluation_id: Unique evaluation run ID
        document_id: Document identifier
        section_id: Section identifier
        baseline_extraction_uri: S3 URI of original extraction
        evaluation_extraction: New extraction result
        metadata: Additional metadata (confidence tier, etc.)
    """
    # Store in S3 for comparator to use
    result_key = f"evaluation-results/{evaluation_id}/{document_id}_{section_id}.json"
    
    result_data = {
        "evaluationId": evaluation_id,
        "documentId": document_id,
        "sectionId": section_id,
        "baselineUri": baseline_extraction_uri,
        "evaluationExtraction": evaluation_extraction,
        "metadata": metadata
    }
    
    s3_client.put_object(
        Bucket=EVALUATION_BUCKET,
        Key=result_key,
        Body=json.dumps(result_data, default=str).encode("utf-8"),
        ContentType="application/json"
    )
    
    logger.info(f"Stored evaluation result: s3://{EVALUATION_BUCKET}/{result_key}")


def get_original_document_from_tracking_table(document_id: str) -> Optional[str]:
    """
    Fetch original document S3 URI from TrackingTable.
    
    TrackingTable schema:
      PK: user#<userId>#doc#<objectKey>  OR  doc#<objectKey> (old format)
      SK: none
      ObjectKey: users/<userId>/filename.pdf (original S3 key)
      InputBucket: <bucket-name> (optional)
    
    Args:
        document_id: Document identifier
        
    Returns:
        S3 URI of original document (s3://bucket/key) or None
    """
    # Discover TrackingTable (same pattern as ExtractionResultsTable)
    try:
        tracking_table_name = None
        
        # Try environment variable first
        tracking_table_env = os.environ.get("TRACKING_TABLE")
        if tracking_table_env:
            tracking_table_name = tracking_table_env
        else:
            # Discover by pattern
            client = boto3.client("dynamodb")
            response = client.list_tables()
            prefix = f"{STACK_NAME}-TrackingTable"
            
            matching = [t for t in response.get("TableNames", []) if t.startswith(prefix)]
            if matching:
                tracking_table_name = matching[0]
        
        if not tracking_table_name:
            logger.error("Could not discover TrackingTable")
            return None
        
        logger.info(f"Using TrackingTable: {tracking_table_name}")
        tracking_table = dynamodb.Table(tracking_table_name)
        
        # Try both key formats (user-scoped and legacy)
        # First, try doc#<documentId> (legacy format)
        pk = f"doc#{document_id}"
        
        response = tracking_table.get_item(Key={"PK": pk, "SK": "none"})
        
        if "Item" not in response:
            # Try user-scoped format: user#<userId>#doc#<objectKey>
            # We need to scan since we don't know the userId
            logger.info(f"Legacy key not found, scanning for user-scoped key containing {document_id}")
            
            response = tracking_table.scan(
                FilterExpression="contains(PK, :doc_id)",
                ExpressionAttributeValues={":doc_id": f"doc#{document_id}"}
            )
            
            if not response.get("Items"):
                logger.warning(f"Document {document_id} not found in TrackingTable")
                return None
            
            item = response["Items"][0]
        else:
            item = response["Item"]
        
        # Extract ObjectKey (original S3 key)
        object_key = item.get("ObjectKey")
        if not object_key:
            logger.error(f"No ObjectKey found for document {document_id}")
            return None
        
        # Get InputBucket (may be in item or from environment)
        input_bucket = item.get("InputBucket") or os.environ.get("INPUT_BUCKET")
        
        if not input_bucket:
            # Try to extract from STACK_NAME
            # Pattern: fiscalshield-idp-dev-input-bucket-...
            client = boto3.client("s3")
            buckets = client.list_buckets()
            prefix = f"{STACK_NAME}-input"
            
            matching = [
                b["Name"] for b in buckets.get("Buckets", [])
                if b["Name"].startswith(prefix)
            ]
            
            if matching:
                input_bucket = matching[0]
        
        if not input_bucket:
            logger.error("Could not determine InputBucket")
            return None
        
        original_uri = f"s3://{input_bucket}/{object_key}"
        logger.info(f"Found original document: {original_uri}")
        return original_uri
    
    except Exception as e:
        logger.error(f"Error fetching from TrackingTable: {e}")
        return None


def process_batch_direct(
    batch_metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Process batch using direct inference (synchronous, one-by-one).
    
    Faster but more expensive than batch API.
    
    Args:
        batch_metadata: Metadata from sampler including manifest URI
        
    Returns:
        Processing summary
    """
    evaluation_id = batch_metadata["evaluationId"]
    manifest_uri = batch_metadata["manifestUri"]
    
    # Fetch manifest from S3
    manifest_parts = manifest_uri.replace("s3://", "").split("/", 1)
    manifest_bucket = manifest_parts[0]
    manifest_key = manifest_parts[1]
    
    logger.info(f"Fetching manifest: {manifest_uri}")
    manifest_obj = s3_client.get_object(Bucket=manifest_bucket, Key=manifest_key)
    manifest_content = manifest_obj["Body"].read().decode("utf-8")
    
    # Parse JSONL manifest
    manifest_items = [json.loads(line) for line in manifest_content.strip().split("\n")]
    
    logger.info(f"Processing {len(manifest_items)} documents directly")
    
    processed = 0
    failed = 0
    
    for item in manifest_items:
        try:
            document_id = item["documentId"]
            section_id = item["sectionId"]
            document_type = item["documentType"]
            s3_object = item["s3Object"]
            
            logger.info(f"Processing document: {document_id}")
            
            # Step 1: Get original document location from TrackingTable
            original_doc_uri = get_original_document_from_tracking_table(document_id)
            
            if not original_doc_uri:
                logger.warning(f"Could not find original document for {document_id}, skipping")
                failed += 1
                continue
            
            # Step 2: Fetch original image
            document_bytes = fetch_document_image(original_doc_uri)
            
            # Step 3: Run extraction with evaluation model
            evaluation_extraction = run_extraction_with_evaluation_model(
                document_bytes,
                document_type,
                EVALUATION_MODEL_ID
            )
            
            # Step 4: Store result
            store_evaluation_result(
                evaluation_id=evaluation_id,
                document_id=document_id,
                section_id=section_id,
                baseline_extraction_uri=s3_object,
                evaluation_extraction=evaluation_extraction,
                metadata={
                    "confidenceTier": item.get("confidenceTier"),
                    "originalConfidence": item.get("originalConfidence"),
                    "documentType": document_type
                }
            )
            
            processed += 1
            logger.info(f"Successfully processed {document_id} ({processed}/{len(manifest_items)})")
        
        except Exception as e:
            logger.error(f"Failed to process document {item.get('documentId')}: {e}")
            failed += 1
    
    return {
        "evaluationId": evaluation_id,
        "totalDocuments": len(manifest_items),
        "processed": processed,
        "failed": failed,
        "mode": "direct"
    }


def process_batch_api(
    batch_metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Process batch using Bedrock Batch Inference API.
    
    50% cheaper but takes 6-24 hours to complete.
    
    Args:
        batch_metadata: Metadata from sampler
        
    Returns:
        Batch job information
    """
    evaluation_id = batch_metadata["evaluationId"]
    
    # Create batch inference job
    bedrock = boto3.client("bedrock", region_name=EVALUATION_REGION)
    
    # Prepare batch input manifest (convert to Bedrock format)
    # This is a simplified version - you'd need to create proper JSONL with model requests
    
    input_uri = batch_metadata["manifestUri"]
    output_uri = f"s3://{EVALUATION_BUCKET}/batch-outputs/{evaluation_id}/"
    
    try:
        response = bedrock.create_model_invocation_job(
            modelId=EVALUATION_MODEL_ID,
            jobName=f"evaluation-{evaluation_id}",
            roleArn=BEDROCK_BATCH_ROLE_ARN,
            inputDataConfig={
                "s3InputDataConfig": {
                    "s3Uri": input_uri
                }
            },
            outputDataConfig={
                "s3OutputDataConfig": {
                    "s3Uri": output_uri
                }
            }
        )
        
        job_arn = response["jobArn"]
        logger.info(f"Created batch job: {job_arn}")
        
        # Update batch jobs table
        batch_table = dynamodb.Table(os.environ.get("BATCH_JOBS_TABLE"))
        batch_table.update_item(
            Key={"JobId": evaluation_id},
            UpdateExpression="SET #status = :status, BedrockJobArn = :arn, OutputUri = :output",
            ExpressionAttributeNames={"#status": "Status"},
            ExpressionAttributeValues={
                ":status": "RUNNING",
                ":arn": job_arn,
                ":output": output_uri
            }
        )
        
        return {
            "evaluationId": evaluation_id,
            "jobArn": job_arn,
            "outputUri": output_uri,
            "mode": "batch",
            "status": "RUNNING"
        }
    
    except Exception as e:
        logger.error(f"Failed to create batch job: {e}")
        raise


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for re-evaluation.
    
    Args:
        event: Contains mode ('batch' or 'direct') and batchMetadata
        context: Lambda context
        
    Returns:
        Processing results
    """
    try:
        mode = event.get("mode", "direct")
        batch_metadata = event.get("batchMetadata")
        
        if not batch_metadata:
            raise ValueError("batchMetadata is required")
        
        logger.info(f"Starting re-evaluation in {mode} mode")
        
        if mode == "batch" and BATCH_INFERENCE_ENABLED:
            result = process_batch_api(batch_metadata)
        else:
            result = process_batch_direct(batch_metadata)
        
        logger.info(f"Re-evaluation complete: {result}")
        
        return {
            "statusCode": 200,
            "result": result
        }
    
    except Exception as e:
        logger.exception("Error in re-evaluator function")
        raise
