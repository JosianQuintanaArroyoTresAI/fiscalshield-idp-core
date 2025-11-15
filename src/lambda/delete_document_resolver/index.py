# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os
import boto3
import json
import logging
from typing import List
from robust_list_deletion import delete_list_entries_robust

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))
logging.getLogger("idp_common.bedrock.client").setLevel(
    os.environ.get("BEDROCK_LOG_LEVEL", "INFO")
)
# Get LOG_LEVEL from environment variable with INFO as default

dynamodb = boto3.resource("dynamodb")
s3 = boto3.client("s3")


def delete_extraction_results(object_key: str) -> int:
    """
    Delete all extraction results for a document from ExtractionResultsTable.
    
    Uses GSI4-DocumentSections index to query by DocumentId and delete all related records
    (invoices, bank statement transactions, etc.).
    
    Args:
        object_key: Document object key (used as DocumentId)
        
    Returns:
        int: Number of extraction result records deleted
    """
    deleted_count = 0
    
    extraction_table_name = os.environ.get("EXTRACTION_RESULTS_TABLE")
    if not extraction_table_name:
        logger.info("EXTRACTION_RESULTS_TABLE not configured - skipping extraction results deletion")
        return 0
    
    try:
        extraction_table = dynamodb.Table(extraction_table_name)
        
        # Use DocumentId as the query key (object_key is the document ID)
        logger.info(f"Querying extraction results for DocumentId: {object_key}")
        
        # Query GSI4-DocumentSections to find all extraction records for this document
        response = extraction_table.query(
            IndexName="GSI4-DocumentSections",
            KeyConditionExpression="DocumentId = :doc_id",
            ExpressionAttributeValues={
                ":doc_id": object_key
            }
        )
        
        items = response.get('Items', [])
        logger.info(f"Found {len(items)} extraction result records to delete")
        
        # Delete each extraction result record
        for item in items:
            try:
                extraction_table.delete_item(
                    Key={
                        "PK": item["PK"],
                        "SK": item["SK"]
                    }
                )
                deleted_count += 1
                logger.debug(f"Deleted extraction record: PK={item['PK']}, SK={item['SK']}")
            except Exception as e:
                logger.error(f"Error deleting extraction record {item['PK']}/{item['SK']}: {str(e)}")
        
        # Handle pagination if there are more items
        while 'LastEvaluatedKey' in response:
            response = extraction_table.query(
                IndexName="GSI4-DocumentSections",
                KeyConditionExpression="DocumentId = :doc_id",
                ExpressionAttributeValues={
                    ":doc_id": object_key
                },
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            
            items = response.get('Items', [])
            for item in items:
                try:
                    extraction_table.delete_item(
                        Key={
                            "PK": item["PK"],
                            "SK": item["SK"]
                        }
                    )
                    deleted_count += 1
                    logger.debug(f"Deleted extraction record: PK={item['PK']}, SK={item['SK']}")
                except Exception as e:
                    logger.error(f"Error deleting extraction record {item['PK']}/{item['SK']}: {str(e)}")
        
        logger.info(f"Successfully deleted {deleted_count} extraction result records for {object_key}")
        
    except Exception as e:
        logger.error(f"Error deleting extraction results for {object_key}: {str(e)}")
    
    return deleted_count


def delete_chunk_tracking_records(tracking_table, object_key: str) -> int:
    """
    Delete all chunk tracking records for a document.
    
    Chunk records have PK pattern: document#{object_key}#section#{section_id}
    and SK pattern: chunk#{idx}
    
    Args:
        tracking_table: DynamoDB table resource
        object_key: Document object key
        
    Returns:
        int: Number of chunk records deleted
    """
    deleted_count = 0
    
    try:
        # Query for all sections of this document
        # We need to scan with a filter since we don't know section IDs in advance
        logger.info(f"Scanning for chunk tracking records for document: {object_key}")
        
        # Use begins_with filter on PK to find all section chunks
        pk_prefix = f"document#{object_key}#section#"
        
        response = tracking_table.scan(
            FilterExpression="begins_with(PK, :pk_prefix) AND begins_with(SK, :sk_prefix)",
            ExpressionAttributeValues={
                ":pk_prefix": pk_prefix,
                ":sk_prefix": "chunk#"
            }
        )
        
        items = response.get('Items', [])
        logger.info(f"Found {len(items)} chunk tracking records to delete")
        
        # Delete each chunk record
        for item in items:
            try:
                tracking_table.delete_item(
                    Key={
                        "PK": item["PK"],
                        "SK": item["SK"]
                    }
                )
                deleted_count += 1
                logger.debug(f"Deleted chunk record: PK={item['PK']}, SK={item['SK']}")
            except Exception as e:
                logger.error(f"Error deleting chunk record {item['PK']}/{item['SK']}: {str(e)}")
        
        # Handle pagination if there are more items
        while 'LastEvaluatedKey' in response:
            response = tracking_table.scan(
                FilterExpression="begins_with(PK, :pk_prefix) AND begins_with(SK, :sk_prefix)",
                ExpressionAttributeValues={
                    ":pk_prefix": pk_prefix,
                    ":sk_prefix": "chunk#"
                },
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            
            items = response.get('Items', [])
            for item in items:
                try:
                    tracking_table.delete_item(
                        Key={
                            "PK": item["PK"],
                            "SK": item["SK"]
                        }
                    )
                    deleted_count += 1
                    logger.debug(f"Deleted chunk record: PK={item['PK']}, SK={item['SK']}")
                except Exception as e:
                    logger.error(f"Error deleting chunk record {item['PK']}/{item['SK']}: {str(e)}")
        
        logger.info(f"Successfully deleted {deleted_count} chunk tracking records for {object_key}")
        
    except Exception as e:
        logger.error(f"Error deleting chunk tracking records for {object_key}: {str(e)}")
    
    return deleted_count


def handler(event, context):
    logger.info(f"Delete document resolver invoked with event: {json.dumps(event)}")

    try:
        object_keys: List[str] = event["arguments"]["objectKeys"]

        # Validate input
        if not object_keys or not isinstance(object_keys, list):
            raise ValueError("objectKeys must be a non-empty list")

        tracking_table = dynamodb.Table(os.environ["TRACKING_TABLE_NAME"])
        input_bucket = os.environ["INPUT_BUCKET"]
        output_bucket = os.environ["OUTPUT_BUCKET"]

        logger.info(f"Preparing to delete {len(object_keys)} documents: {object_keys}")
        logger.debug(f"Using tracking table: {os.environ['TRACKING_TABLE_NAME']}")
        logger.debug(f"Input bucket: {input_bucket}, Output bucket: {output_bucket}")

        deleted_count = 0
        # Delete each document and its associated data
        for object_key in object_keys:
            logger.info(f"Processing deletion for document: {object_key}")

            # First get the document metadata to extract the queued time
            doc_pk = f"doc#{object_key}"
            logger.info(
                f"Getting document metadata with PK={doc_pk}, SK=none from tracking table"
            )
            document_metadata = None
            try:
                response = tracking_table.get_item(Key={"PK": doc_pk, "SK": "none"})
                if "Item" in response:
                    document_metadata = response["Item"]
                    logger.info(
                        f"Successfully got document metadata: {document_metadata}"
                    )
                else:
                    logger.warning(f"Document metadata not found for {object_key}")
            except Exception as e:
                logger.error(f"Error getting document metadata: {str(e)}")
                # Continue with deletion process even if this part fails

            # Delete from input bucket
            try:
                logger.info(
                    f"Deleting document from input bucket: {input_bucket}/{object_key}"
                )
                s3.delete_object(Bucket=input_bucket, Key=object_key)
                logger.info("Successfully deleted document from input bucket")
            except Exception as e:
                logger.error(f"Error deleting from input bucket: {str(e)}")

            # Delete from output bucket
            try:
                # List and delete all objects with the prefix
                logger.info(
                    f"Deleting document outputs from output bucket with prefix: {object_key}"
                )
                paginator = s3.get_paginator("list_objects_v2")
                deleted_output_count = 0

                for page in paginator.paginate(Bucket=output_bucket, Prefix=object_key):
                    if "Contents" in page:
                        for obj in page["Contents"]:
                            logger.debug(f"Deleting output file: {obj['Key']}")
                            s3.delete_object(Bucket=output_bucket, Key=obj["Key"])
                            deleted_output_count += 1

                logger.info(
                    f"Successfully deleted {deleted_output_count} output files from output bucket"
                )
            except Exception as e:
                logger.error(f"Error deleting from output bucket: {str(e)}")

            # Delete from list entries using robust deletion strategy
            try:
                logger.info(f"Attempting robust list entry deletion for {object_key}")
                deletion_success = delete_list_entries_robust(
                    tracking_table, object_key, document_metadata
                )

                if deletion_success:
                    logger.info(f"Successfully deleted list entries for {object_key}")
                else:
                    logger.warning(
                        f"No list entries were found/deleted for {object_key}"
                    )
                    # Fallback: Scan for list entries by ObjectKey if robust deletion failed
                    logger.info(f"Attempting fallback: scanning for list entries by ObjectKey")
                    try:
                        scan_response = tracking_table.scan(
                            FilterExpression="ObjectKey = :obj_key",
                            ExpressionAttributeValues={":obj_key": object_key}
                        )
                        
                        list_items = scan_response.get('Items', [])
                        logger.info(f"Found {len(list_items)} list entries via scan for {object_key}")
                        
                        for item in list_items:
                            try:
                                tracking_table.delete_item(
                                    Key={"PK": item["PK"], "SK": item["SK"]}
                                )
                                logger.info(f"Deleted list entry: PK={item['PK']}, SK={item['SK']}")
                                deletion_success = True
                            except Exception as del_err:
                                logger.error(f"Error deleting scanned list entry: {str(del_err)}")
                        
                        # Handle pagination
                        while 'LastEvaluatedKey' in scan_response:
                            scan_response = tracking_table.scan(
                                FilterExpression="ObjectKey = :obj_key",
                                ExpressionAttributeValues={":obj_key": object_key},
                                ExclusiveStartKey=scan_response['LastEvaluatedKey']
                            )
                            list_items = scan_response.get('Items', [])
                            for item in list_items:
                                try:
                                    tracking_table.delete_item(
                                        Key={"PK": item["PK"], "SK": item["SK"]}
                                    )
                                    logger.info(f"Deleted list entry (paginated): PK={item['PK']}, SK={item['SK']}")
                                    deletion_success = True
                                except Exception as del_err:
                                    logger.error(f"Error deleting paginated list entry: {str(del_err)}")
                    except Exception as scan_err:
                        logger.error(f"Error in fallback scan deletion: {str(scan_err)}")
            except Exception as e:
                logger.error(f"Error in robust list entry deletion: {str(e)}")

            # Delete extraction results (invoices, bank statements, etc.)
            try:
                logger.info(f"Deleting extraction results for {object_key}")
                extraction_count = delete_extraction_results(object_key)
                logger.info(f"Deleted {extraction_count} extraction result records")
            except Exception as e:
                logger.error(f"Error deleting extraction results: {str(e)}")

            # Delete chunk tracking records (for chunked extraction feature)
            try:
                logger.info(f"Deleting chunk tracking records for {object_key}")
                chunk_count = delete_chunk_tracking_records(tracking_table, object_key)
                logger.info(f"Deleted {chunk_count} chunk tracking records")
            except Exception as e:
                logger.error(f"Error deleting chunk tracking records: {str(e)}")

            # Note: In this architecture, documents exist ONLY as list entries.
            # There is no separate doc#{object_key} record to delete.
            # The document_metadata query above is only used to get timestamp for list deletion.

            deleted_count += 1
            logger.info(f"Completed deletion process for document: {object_key}")

        logger.info(
            f"Successfully deleted {deleted_count} of {len(object_keys)} documents"
        )
        return True
    except Exception as e:
        logger.error(f"Error in delete_document resolver: {str(e)}", exc_info=True)
        raise e
