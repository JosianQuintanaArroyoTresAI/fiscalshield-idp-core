# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import os
import time
import boto3
import logging
import re
from datetime import datetime, timezone, timedelta
from datetime import datetime as _datetime_class
from pypdf import PdfReader
from io import BytesIO
from idp_common.models import Document, Status

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

sqs = boto3.client("sqs")

# These will be set by environment variables in Lambda, but defaulted for testing
QUEUE_URL = os.environ.get("QUEUE_URL", "")
APPSYNC_API_URL = os.environ.get("APPSYNC_API_URL", "")
DATA_RETENTION_IN_DAYS = int(os.environ.get("DATA_RETENTION_IN_DAYS", "30"))
OUTPUT_BUCKET = os.environ.get("OUTPUT_BUCKET", "")
MAX_PAGES = int(os.environ.get("MAX_PAGES", "500"))  # Maximum page limit for PDFs


def extract_user_id_from_path(object_key):
    """
    Extract user ID from S3 object key path.
    Expected format: users/<user_id>/filename.ext

    Args:
        object_key: S3 object key

    Returns:
        str: User ID extracted from path

    Raises:
        ValueError: If path format is invalid
    """
    if not object_key.startswith("users/"):
        raise ValueError(
            f"Invalid path format. Expected 'users/<user_id>/', got: {object_key}"
        )

    # Split path and extract user ID
    parts = object_key.split("/")
    if len(parts) < 3:
        raise ValueError(
            f"Invalid path structure. Expected at least 3 parts, got: {object_key}"
        )

    user_id = parts[1]

    if not user_id:
        raise ValueError(f"User ID is empty in path: {object_key}")

    logger.info(f"Extracted user_id: {user_id} from path: {object_key}")
    return user_id


def validate_user_id(user_id):
    """
    Validate that user ID looks like a Cognito UUID.
    Logs warning if format doesn't match but allows it through.

    Args:
        user_id: User ID to validate

    Returns:
        str: The user ID (unchanged)
    """
    uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    if not re.match(uuid_pattern, user_id, re.IGNORECASE):
        logger.warning(f"User ID doesn't match UUID pattern: {user_id}")
    return user_id


def validate_pdf_page_count(bucket_name, object_key):
    """
    Validate PDF page count to prevent processing oversized documents.
    
    Args:
        bucket_name: S3 bucket name
        object_key: S3 object key
    
    Raises:
        ValueError: If PDF exceeds MAX_PAGES limit
    """
    # Only validate PDFs
    if not object_key.lower().endswith('.pdf'):
        return
    
    try:
        s3_client = boto3.client('s3')
        
        # Download PDF file to memory
        logger.info(f"Downloading PDF to validate page count: {object_key}")
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        pdf_bytes = response['Body'].read()
        
        # Count pages using pypdf
        pdf_reader = PdfReader(BytesIO(pdf_bytes))
        page_count = len(pdf_reader.pages)
        
        logger.info(f"PDF page count: {page_count} (limit: {MAX_PAGES})")
        
        if page_count > MAX_PAGES:
            error_msg = (
                f"PDF exceeds maximum page limit: {page_count} pages found, "
                f"but maximum allowed is {MAX_PAGES} pages. "
                f"Please split the file or reduce the number of pages."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        logger.info(f"✓ PDF validation passed: {page_count} pages within {MAX_PAGES} page limit")
        
    except ValueError:
        # Re-raise validation errors
        raise
    except Exception as e:
        # Log other errors but don't block processing
        logger.warning(f"Failed to validate PDF page count: {str(e)}")
        # Continue processing - classification will handle invalid PDFs


def handler(event, context):
    """
    Handles S3 Object Created events from EventBridge.
    Extracts user context from S3 path and sends to SQS with UserId.

    Args:
        event: EventBridge event for S3 Object Created
        context: Lambda context

    Returns:
        dict: Response with status
    """
    logger.info(f"QueueSender invoked with event: {json.dumps(event)}")

    try:
        # Extract S3 event details
        detail = event.get("detail", {})
        bucket_name = detail.get("bucket", {}).get("name")
        object_key = detail.get("object", {}).get("key")

        if not bucket_name or not object_key:
            raise ValueError("Missing bucket name or object key in event")

        logger.info(f"Processing S3 event: bucket={bucket_name}, key={object_key}")

        # Extract company metadata from S3 object if available
        company_number = None
        company_name = None
        user_document_type = None  # NEW: User's document type hint
        try:
            # Get object metadata to extract company information
            head_response = boto3.client("s3").head_object(
                Bucket=bucket_name, Key=object_key
            )
            metadata = head_response.get("Metadata", {})
            company_number = metadata.get("company-number")
            company_name = metadata.get("company-name")
            user_document_type = metadata.get("user-document-type")  # NEW
            
            if company_number:
                logger.info(
                    f"Extracted company metadata: {company_name} ({company_number})"
                )
            if user_document_type:
                logger.info(f"User indicated document type: {user_document_type}")
        except Exception as e:
            logger.warning(f"Could not retrieve object metadata: {str(e)}")
            # Continue without company metadata

        # Extract user ID from path
        try:
            user_id = extract_user_id_from_path(object_key)
            user_id = validate_user_id(user_id)
        except ValueError as e:
            logger.error(f"Path validation error: {str(e)}")
            # This will go to DLQ for investigation
            raise

        # Validate PDF page count (safety net - frontend should catch this too)
        try:
            validate_pdf_page_count(bucket_name, object_key)
        except ValueError as e:
            logger.error(f"PDF page count validation failed: {str(e)}")
            # This will go to DLQ - user needs to split the file
            raise

        # Create a Document object (same pattern as reprocess_document_resolver)
        current_dt = datetime.now(timezone.utc)
        current_time = current_dt.isoformat()
        event_time = (
            detail.get("object", {}).get("last-modified")
            or event.get("time")
            or current_time
        )

        document = Document(
            id=object_key,
            input_bucket=bucket_name,
            input_key=object_key,
            output_bucket=OUTPUT_BUCKET,
            status=Status.QUEUED,
            queued_time=event_time,
            initial_event_time=event_time,
            user_id=user_id,
            company_number=company_number,
            company_name=company_name,
            user_document_type=user_document_type,  # NEW: Pass user's hint
            pages={},
            sections=[],
        )

        logger.info(
            f"Created document object for user {user_id}, company {company_number}: {object_key}"
        )

        # Calculate expiry timestamp; fall back to epoch math if datetime is mocked
        if isinstance(current_dt, _datetime_class):
            expires_after_dt = current_dt + timedelta(days=DATA_RETENTION_IN_DAYS)
            expires_after = int(expires_after_dt.timestamp())
        else:
            expires_after = int(time.time() + DATA_RETENTION_IN_DAYS * 86400)

        # Prepare SQS message payload with document details and quick-access metadata
        message_payload = document.to_dict()
        message_payload.update(
            {
                "Bucket": bucket_name,
                "ObjectKey": object_key,
                "UserId": user_id,
                "EventTime": event_time,
                "ExpiresAfter": expires_after,
            }
        )

        message_body = json.dumps(message_payload, default=str)

        logger.info(
            f"Sending message to SQS with UserId: {user_id}, CompanyNumber: {company_number}"
        )

        # Build message attributes
        message_attributes = {
            "UserId": {"StringValue": user_id, "DataType": "String"},
            "ObjectKey": {"StringValue": object_key, "DataType": "String"},
            "ExpiresAfter": {
                "StringValue": str(expires_after),
                "DataType": "Number",
            },
        }

        # Add company metadata if available
        if company_number:
            message_attributes["CompanyNumber"] = {
                "StringValue": company_number,
                "DataType": "String",
            }
        if company_name:
            message_attributes["CompanyName"] = {
                "StringValue": company_name,
                "DataType": "String",
            }

        # Send to SQS
        queue_url = os.environ.get(
            "QUEUE_URL", QUEUE_URL
        )  # Use runtime env var if available
        response = sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=message_body,
            MessageAttributes=message_attributes,
        )

        logger.info(
            f"Successfully sent message to SQS. MessageId: {response['MessageId']}"
        )

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "Successfully queued document",
                    "messageId": response["MessageId"],
                    "userId": user_id,
                    "objectKey": object_key,
                }
            ),
        }

    except Exception as e:
        logger.error(f"Error in QueueSender: {str(e)}", exc_info=True)
        raise
