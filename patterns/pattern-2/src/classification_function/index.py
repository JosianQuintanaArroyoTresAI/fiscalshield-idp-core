# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Classification function that processes documents and classifies them using LLMs.
Uses the idp_common.classification package for classification functionality.
"""

import json
import logging
import os
import time

from idp_common import classification, metrics, get_config
from idp_common.models import Document, Status
from idp_common.docs_service import create_document_service
from idp_common.utils import calculate_lambda_metering, merge_metering_data
from idp_common.classification.structure_analysis import enhance_classification_with_structure_analysis
from idp_common.classification.smart_batcher import SmartBatcher
from idp_common.classification.llm_boundary_detection import DEFAULT_BOUNDARY_MODEL_ID

# Configuration will be loaded in handler function
region = os.environ["AWS_REGION"]
MAX_WORKERS = int(os.environ.get("MAX_WORKERS", 20))

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))
logging.getLogger("idp_common.bedrock.client").setLevel(
    os.environ.get("BEDROCK_LOG_LEVEL", "INFO")
)


def handler(event, context):
    """
    Lambda handler for document classification.
    """
    start_time = time.time()  # Capture start time for Lambda metering
    logger.info(f"Event: {json.dumps(event)}")

    # Load configuration
    config = get_config()
    # Use default=str to handle Decimal and other non-serializable types
    logger.info(f"Config: {json.dumps(config, default=str)}")

    # Extract document from the OCR result - handle both compressed and uncompressed
    working_bucket = os.environ.get("WORKING_BUCKET")
    document = Document.load_document(
        event["OCRResult"]["document"], working_bucket, logger
    )

    # Log loaded document for troubleshooting
    logger.info(f"Loaded document - ID: {document.id}, input_key: {document.input_key}")
    logger.info(
        f"Document buckets - input_bucket: {document.input_bucket}, output_bucket: {document.output_bucket}"
    )
    logger.info(f"Document status: {document.status}, num_pages: {document.num_pages}")
    logger.info(
        f"Document pages count: {len(document.pages)}, sections count: {len(document.sections)}"
    )
    logger.info(f"Full document content: {json.dumps(document.to_dict(), default=str)}")

    # NEW: Check if user provided document type hint
    user_hint = document.user_document_type
    trust_user_hint = config.get("classification", {}).get("trust_user_hint", False)

    # Intelligent Classification detection: Skip if pages already have classifications
    # NOTE: Exclude "unclassified" - it means classification failed previously, so we should retry
    pages_with_classification = 0
    for page in document.pages.values():
        if page.classification and page.classification.strip() and page.classification.lower() != "unclassified":
            pages_with_classification += 1

    if pages_with_classification == len(document.pages) and len(document.pages) > 0:
        logger.info(
            f"Skipping classification for document {document.id} - all {len(document.pages)} pages already classified"
        )

        # Ensure document has the expected execution ARN
        document.workflow_execution_arn = event.get("execution_arn")

        # Update document execution ARN for tracking
        document_service = create_document_service()
        logger.info("Updating document execution ARN for classification skip")
        document_service.update_document(document)

        # Add Lambda metering for classification skip execution
        try:
            lambda_metering = calculate_lambda_metering(
                "Classification", context, start_time
            )
            document.metering = merge_metering_data(document.metering, lambda_metering)
        except Exception as e:
            logger.warning(
                f"Failed to add Lambda metering for classification skip: {str(e)}"
            )

        # Prepare output with existing document data
        response = {
            "document": document.serialize_document(
                working_bucket, "classification_skip", logger
            )
        }

        logger.info(
            f"Classification skipped - Response: {json.dumps(response, default=str)}"
        )
        return response

    # Normal classification processing
    # Update document status to CLASSIFYING
    document.status = Status.CLASSIFYING
    document.workflow_execution_arn = event.get("execution_arn")
    document_service = create_document_service()
    logger.info(f"Updating document status to {document.status}")
    document_service.update_document(document)

    if not document.pages:
        error_message = "Document has no pages to classify"
        logger.error(error_message)
        document.status = Status.FAILED
        document.errors.append(error_message)

    t0 = time.time()

    # Track pages processed for metrics
    total_pages = len(document.pages)
    metrics.put_metric("BedrockRequestsTotal", total_pages)

    # Initialize classification service with DynamoDB caching
    cache_table = os.environ.get("TRACKING_TABLE")
    service = classification.ClassificationService(
        region=region, max_workers=MAX_WORKERS, config=config, cache_table=cache_table
    )

    # Classify the document - the service will update the Document directly
    document = service.classify_document(document)
    
    # NEW: Apply smart batching to create optimally-sized sections
    # This groups pages into cost-efficient batches for parallel extraction
    enable_smart_batching = config.get("classification", {}).get("enable_smart_batching", True)
    
    if enable_smart_batching:
        logger.info("🔧 Smart batching enabled - creating optimized sections")
        
        # Get batch size configuration
        target_pages = int(os.environ.get('BATCH_TARGET_PAGES', 
                                          config.get("classification", {}).get("target_pages_per_batch", 10)))
        max_pages = int(os.environ.get('BATCH_MAX_PAGES',
                                       config.get("classification", {}).get("max_pages_per_batch", 30)))
        max_invoices = int(os.environ.get('BATCH_MAX_INVOICES',
                                          config.get("classification", {}).get("max_invoices_per_batch", 20)))
        
        # Initialize smart batcher
        batcher = SmartBatcher(
            target_pages_per_batch=target_pages,
            max_pages_per_batch=max_pages,
            max_invoices_per_batch=max_invoices,
            max_statements_per_batch=1  # Bank statements: 1 per section
        )
        
        # Replace sections with optimized batches
        original_section_count = len(document.sections)
        document.sections = batcher.create_optimized_sections(
            pages=document.pages,
            document_type=user_hint
        )
        
        logger.info(
            f"✅ Smart batching complete: {original_section_count} original sections → "
            f"{len(document.sections)} optimized sections"
        )
        
        # Calculate total expected invoice count for validation
        total_expected_invoices = sum(
            section.attributes.get('invoice_count', 0) if section.attributes else 0
            for section in document.sections
            if section.classification == 'invoice'
        )
        
        # Calculate total page count for validation
        total_page_count = sum(
            len(section.page_ids)
            for section in document.sections
        )
        
        # Store in document metadata
        # PAGE COUNT = VALIDATION (robust, can't be wrong)
        # INVOICE COUNT = METRIC (for refinement, continuation detection can be imperfect)
        if not document.metadata:
            document.metadata = {}
        document.metadata['expected_page_count'] = total_page_count  # CRITICAL: Must match extraction
        document.metadata['expected_invoice_count'] = total_expected_invoices  # INFORMATIONAL: Helps refine process
        document.metadata['batching_strategy'] = 'smart'
        
        logger.info("="*80)
        logger.info(
            f"📊 Classification complete: {total_page_count} pages, ~{total_expected_invoices} invoices across "
            f"{len([s for s in document.sections if s.classification == 'invoice'])} sections"
        )
        logger.info(f"   (Page count = VALIDATION, Invoice count = METRIC)")
        
        # Log batch details
        for section in document.sections:
            invoice_count = section.attributes.get('invoice_count', 0) if section.attributes else 0
            page_count = section.attributes.get('page_count', len(section.page_ids)) if section.attributes else len(section.page_ids)
            logger.info(
                f"  Section {section.section_id}: {section.classification}, "
                f"{page_count} pages, ~{invoice_count} invoices"
            )
        logger.info("="*80)
    else:
        logger.info("ℹ️  Smart batching disabled - using default section grouping")
    
    # Store classification metadata for drift detection
    if not document.metadata:
        document.metadata = {}
    
    # Check if we should use user hint for routing
    # Two modes:
    # 1. trust_user_hint=True: Run boundary detection but use user's classification type for all sections
    # 2. validate_hint_on_mismatch=True: Run LLM classification, compare with user hint, use hint if mismatch
    validate_on_mismatch = config.get("classification", {}).get("validate_hint_on_mismatch", False)
    use_user_hint_for_routing = (user_hint and (trust_user_hint or validate_on_mismatch))
    
    # Check if we should use user hint for routing
    # Two modes:
    # 1. trust_user_hint=True: Run boundary detection but use user's classification type for all sections
    # 2. validate_hint_on_mismatch=True: Run LLM classification, compare with user hint, use hint if mismatch
    validate_on_mismatch = config.get("classification", {}).get("validate_hint_on_mismatch", False)
    use_user_hint_for_routing = (user_hint and (trust_user_hint or validate_on_mismatch))
    
    if use_user_hint_for_routing:
        if trust_user_hint:
            document.metadata["classification_method"] = "boundary_detection_with_user_hint"
            logger.info(
                f"🔄 Using user hint '{user_hint}' for all {len(document.sections)} sections "
                f"(boundary detection ran, classification type overridden)"
            )
        else:
            document.metadata["classification_method"] = "user_hint_validated"
            logger.info(f"🔄 Using user hint '{user_hint}' for routing (validation mode)")
        
        document.metadata["user_provided_type"] = user_hint
    else:
        document.metadata["classification_method"] = "llm"
    
    if user_hint:
        # Store user hint even when we ran LLM (for comparison/drift detection)
        if not use_user_hint_for_routing:
            document.metadata["user_provided_type"] = user_hint
            logger.info(f"Stored user hint '{user_hint}' for drift detection (LLM classification was run)")
        
        # NEW: Validate user hint against model prediction
        if document.sections and len(document.sections) > 0:
            model_classification = document.sections[0].classification
            model_confidence = document.sections[0].confidence
            
            validation_match = (model_classification.lower() == user_hint.lower())
            
            # If validate_on_mismatch=true, override model classification with user hint
            if use_user_hint_for_routing:
                original_classification = model_classification
                # Override the section classification with user hint
                for section in document.sections:
                    section.classification = user_hint
                # document.pages is a dict, iterate over values
                for page_id, page in document.pages.items():
                    page.classification = user_hint
                
                logger.info(
                    f"📝 Overrode classification: model='{original_classification}' → user='{user_hint}' "
                    f"(confidence={model_confidence:.2f}) for routing"
                )
            
            # Log validation result
            logger.info(
                f"🔍 VALIDATION: user='{user_hint}', model='{model_classification}' "
                f"(confidence={model_confidence:.2f}), match={validation_match}"
            )
            
            # Store validation data in DynamoDB for metrics
            try:
                import boto3
                import uuid
                from datetime import datetime
                from decimal import Decimal
                
                validation_table_name = os.environ.get("VALIDATION_REQUESTS_TABLE")
                if validation_table_name:
                    dynamodb = boto3.resource("dynamodb")
                    validation_table = dynamodb.Table(validation_table_name)
                    
                    validation_id = str(uuid.uuid4())
                    timestamp = int(datetime.now().timestamp())
                    
                    # Create validation record
                    validation_item = {
                        "PK": f"validation#{validation_id}",
                        "SK": f"doc#{document.id}",
                        "ValidationId": validation_id,
                        "DocumentId": document.id,
                        "UserId": document.user_id if hasattr(document, 'user_id') and document.user_id else "unknown",
                        "CompanyNumber": document.company_number if hasattr(document, 'company_number') and document.company_number else None,
                        "CompanyName": document.company_name if hasattr(document, 'company_name') and document.company_name else None,
                        "UserSelection": user_hint,
                        "ModelPrediction": model_classification,
                        "ModelConfidence": Decimal(str(model_confidence)),  # Convert float to Decimal for DynamoDB
                        "ValidationMatch": validation_match,
                        "ValidationStatus": "auto_logged",  # vs "pending_user_confirmation" for future
                        "CreatedAt": timestamp,
                        "TTL": timestamp + (90 * 24 * 60 * 60),  # 90 days retention
                    }
                    
                    validation_table.put_item(Item=validation_item)
                    
                    if not validation_match and model_confidence > 0.90:
                        logger.warning(
                            f"⚠️  HIGH CONFIDENCE MISMATCH: user='{user_hint}', "
                            f"model='{model_classification}' (confidence={model_confidence:.2f}). "
                            f"Validation ID: {validation_id}"
                        )
                    elif not validation_match:
                        logger.info(
                            f"📊 Mismatch logged (low confidence): user='{user_hint}', "
                            f"model='{model_classification}' (confidence={model_confidence:.2f}). "
                            f"Validation ID: {validation_id}"
                        )
                    else:
                        logger.info(f"✅ User and model agree on '{user_hint}'. Validation ID: {validation_id}")
                        
                else:
                    logger.warning("VALIDATION_REQUESTS_TABLE not configured - skipping validation logging")
                    
            except Exception as e:
                logger.error(f"Failed to log validation data: {str(e)}")
                # Don't fail the workflow if validation logging fails

    # Check if document processing failed or has pages that failed to classify
    failed_page_exceptions = None
    primary_exception = None

    # Check for failed page exceptions in metadata
    if document.metadata and "failed_page_exceptions" in document.metadata:
        failed_page_exceptions = document.metadata["failed_page_exceptions"]
        primary_exception = document.metadata.get("primary_exception")

        # Log details about failed pages
        logger.error(
            f"Document {document.id} has {len(failed_page_exceptions)} pages that failed to classify:"
        )
        for page_id, exc_info in failed_page_exceptions.items():
            logger.error(
                f"  Page {page_id}: {exc_info['exception_type']} - {exc_info['exception_message']}"
            )

    # Check if document processing completely failed or has critical page failures
    if document.status == Status.FAILED or failed_page_exceptions:
        error_message = f"Classification failed for document {document.id}"
        if failed_page_exceptions:
            error_message += (
                f" - {len(failed_page_exceptions)} pages failed to classify"
            )

        logger.error(error_message)
        # Update document status in AppSync before raising exception
        document_service.update_document(document)

        # Raise the original exception type if available, otherwise raise generic exception
        if primary_exception:
            logger.error(
                f"Re-raising original exception: {type(primary_exception).__name__}"
            )
            raise primary_exception
        else:
            raise Exception(error_message)

    t1 = time.time()
    logger.info(f"Time taken for classification: {t1-t0:.2f} seconds")

    # NEW: LLM-based boundary detection for invoice sections
    # Uses Claude Sonnet 3.5 to intelligently detect invoice boundaries
    try:
        # Get configuration for boundary detection
        classification_cfg = config.get("classification", {})

        def _safe_float(value, default):
            try:
                return float(value)
            except (TypeError, ValueError):
                return default

        def _safe_int(value, default):
            try:
                return int(value)
            except (TypeError, ValueError):
                return default

        enable_llm_boundaries = classification_cfg.get("enable_llm_boundary_detection", True)
        boundary_model_id = classification_cfg.get(
            "boundary_detection_model", DEFAULT_BOUNDARY_MODEL_ID
        )
        use_caching = classification_cfg.get("use_prompt_caching", True)
        boundary_min_coverage = _safe_float(classification_cfg.get("boundary_min_coverage", 0.92), 0.92)
        boundary_max_gap_ratio = _safe_float(classification_cfg.get("boundary_max_gap_ratio", 0.12), 0.12)
        fallback_pages_per_boundary = _safe_int(classification_cfg.get("fallback_pages_per_boundary", 2), 2)
        
        if not enable_llm_boundaries:
            logger.info("⏭️  LLM boundary detection disabled in config")
        else:
            logger.info(f"🔍 LLM boundary detection enabled (model: {boundary_model_id})")
            
            # Import LLM boundary detector
            from idp_common.classification.llm_boundary_detection import (
                LLMBoundaryDetector,
                get_section_text
            )
            
            # Initialize detector
            detector = LLMBoundaryDetector(
                region=region,
                model_id=boundary_model_id,
                use_caching=use_caching,
                min_coverage=boundary_min_coverage,
                max_gap_ratio=boundary_max_gap_ratio,
                fallback_pages_per_boundary=fallback_pages_per_boundary
            )
            
            # Process each invoice section
            for section in document.sections:
                if section.classification.lower() == 'invoice':
                    logger.info(f"🔍 Detecting boundaries for invoice section {section.section_id}")
                    
                    # Get section text (combine all pages with PAGE markers)
                    section_text = get_section_text(section, document.pages)
                    
                    if section_text:
                        logger.info(f"📄 Section text length: {len(section_text)} chars")
                        
                        # Initialize attributes dict if not exists
                        if not section.attributes:
                            section.attributes = {}
                        
                        # Run LLM boundary detection
                        try:
                            boundaries = detector.detect_invoice_boundaries(
                                section_text=section_text,
                                section_pages=section.page_ids
                            )

                            validation_passed = False
                            validation_reason = None
                            if boundaries:
                                validation_passed = detector.validate_boundaries(boundaries, section_text)
                                if not validation_passed:
                                    validation_reason = detector.last_validation_error or "validation_failed"
                            else:
                                validation_reason = "llm_returned_no_boundaries"

                            if validation_passed:
                                section.attributes['boundaries'] = boundaries
                                section.attributes['boundary_strategy'] = 'llm_detected'
                                section.attributes['invoice_count'] = len(boundaries)
                                section.attributes['boundary_model'] = boundary_model_id
                                metrics.put_metric("LLMBoundaryValidationPassed", len(boundaries))
                                logger.info(
                                    f"✅ Detected {len(boundaries)} invoices in section {section.section_id}"
                                )
                            else:
                                metrics.put_metric("LLMBoundaryValidationFailed", 1)
                                logger.warning(
                                    f"⚠️ Boundary detection/validation failed for section {section.section_id}"
                                )
                                section.attributes['boundary_strategy'] = 'validation_failed'
                                section.attributes['invoice_count'] = 0
                                if validation_reason:
                                    section.attributes['boundary_failure_reason'] = validation_reason

                                fallback_boundaries = detector.generate_page_chunk_fallback(
                                    section_text=section_text,
                                    section_pages=section.page_ids,
                                    max_pages_per_boundary=fallback_pages_per_boundary
                                )

                                if fallback_boundaries:
                                    section.attributes['boundaries'] = fallback_boundaries
                                    section.attributes['boundary_strategy'] = 'fallback_page_chunks'
                                    section.attributes['invoice_count'] = len(fallback_boundaries)
                                    section.attributes['boundary_model'] = boundary_model_id
                                    section.attributes['boundary_failure_reason'] = validation_reason or 'llm_unavailable'
                                    metrics.put_metric("LLMBoundaryFallbackUsed", len(fallback_boundaries))
                                    logger.info(
                                        f"🛟 Applied fallback boundaries for section {section.section_id}"
                                    )
                                else:
                                    logger.error(
                                        f"❌ Fallback boundary generation failed for section {section.section_id}"
                                    )
                                    section.attributes['boundary_strategy'] = 'fallback_failed'
                                    section.attributes['boundary_failure_reason'] = validation_reason or 'fallback_failed'
                                
                        except Exception as e:
                            logger.error(f"❌ Error in LLM boundary detection: {str(e)}")
                            section.attributes['boundary_strategy'] = 'error'
                            section.attributes['error'] = str(e)
                    else:
                        logger.warning(f"No text found for invoice section {section.section_id}")
                        section.attributes['boundary_strategy'] = 'no_text'
    
    except Exception as e:
        logger.warning(f"Structure analysis enhancement failed (non-critical): {e}")
        # Don't fail the workflow if structure analysis fails

    # Add Lambda metering for successful classification execution
    try:
        lambda_metering = calculate_lambda_metering(
            "Classification", context, start_time
        )
        document.metering = merge_metering_data(document.metering, lambda_metering)
    except Exception as e:
        logger.warning(f"Failed to add Lambda metering for classification: {str(e)}")

    # Prepare output with automatic compression if needed
    response = {
        "document": document.serialize_document(
            working_bucket, "classification", logger
        )
    }

    logger.info(f"Response: {json.dumps(response, default=str)}")
    return response
