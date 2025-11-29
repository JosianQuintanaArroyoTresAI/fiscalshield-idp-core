# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
LLM-based invoice boundary detection using Claude
Replaces regex-based semantic chunking with intelligent boundary identification
"""

import json
import logging
from typing import List, Dict, Any, Optional
from botocore.exceptions import ClientError
from idp_common.bedrock.client import BedrockClient

logger = logging.getLogger(__name__)


BOUNDARY_DETECTION_PROMPT = """You are analyzing a section of text that contains one or more invoices.

Your task: Identify the EXACT character positions where each invoice starts and ends.

## What defines invoice boundaries:

**Invoice STARTS with:**
- "Invoice Number:" or "Invoice No:" label
- Company letterhead (company name in header)
- "To:" or "Bill To:" customer details
- "Tax Invoice" heading
- Date and invoice reference at top

**Invoice ENDS with:**
- "AMOUNT DUE" or "Total GBP/USD/EUR" with amount
- "Thank you for your business"
- Payment terms or due date
- "This is not a tax invoice" disclaimer
- Clear page break before next invoice
- Footer with company registration details

## Instructions:

1. Scan the ENTIRE text from start to finish
2. For each invoice found, record:
   - Exact start character position
   - Exact end character position  
   - Confidence level (high/medium/low)
   - Page numbers it spans
   - What text marks the start
   - What text marks the end

3. Return a JSON array with this structure:

[
  {
    "id": 1,
    "start_char": 0,
    "end_char": 2847,
    "confidence": "high",
    "page_numbers": [1, 2],
    "start_indicator": "Invoice Number: INV-60778",
    "end_indicator": "AMOUNT DUE £296.74"
  },
  {
    "id": 2,
    "start_char": 2848,
    "end_char": 5690,
    "confidence": "high", 
    "page_numbers": [3],
    "start_indicator": "Invoice Number: INV-60779",
    "end_indicator": "Thank you for your business"
  }
]

## Important rules:

- Boundaries MUST NOT overlap (end_char of invoice N < start_char of invoice N+1)
- Each invoice should be COMPLETE (has header AND footer)
- If an invoice appears incomplete, set confidence to "low"
- Character positions are 0-indexed
- Return ONLY the JSON array, no markdown formatting

## Text to analyze:

{section_text}

Remember: Return ONLY valid JSON, no explanation or markdown.
"""


class LLMBoundaryDetector:
    """
    LLM-based boundary detection for invoices and other documents.
    Uses Claude models via Bedrock for intelligent structure analysis.
    """
    
    def __init__(
        self,
        region: str = "us-east-1",
        model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0",
        use_caching: bool = True
    ):
        """
        Initialize LLM boundary detector.
        
        Args:
            region: AWS region for Bedrock
            model_id: Bedrock model ID (default: Sonnet 3.5 for best accuracy)
            use_caching: Enable prompt caching to reduce costs (not supported with inference profiles)
        """
        self.region = region
        self.model_id = model_id
        self.use_caching = use_caching
        self.bedrock_client = BedrockClient(region=region)
        
    def detect_invoice_boundaries(
        self,
        section_text: str,
        section_pages: List[str],
        max_tokens: int = 4000
    ) -> List[Dict[str, Any]]:
        """
        Use Claude to detect invoice boundaries in section text.
        
        Args:
            section_text: Full OCR text from section (with PAGE markers)
            section_pages: List of page IDs in this section
            max_tokens: Maximum tokens for response
        
        Returns:
            List of boundary dictionaries with start/end positions
        """
        try:
            # Truncate text if too long (Claude Sonnet: 200K tokens ≈ 800K chars)
            max_input_chars = 500000  # Conservative limit
            if len(section_text) > max_input_chars:
                logger.warning(
                    f"Section text too long ({len(section_text)} chars), "
                    f"truncating to {max_input_chars}"
                )
                section_text = section_text[:max_input_chars]
            
            # Build prompt with section text
            prompt = BOUNDARY_DETECTION_PROMPT.format(section_text=section_text)
            
            logger.info(f"📄 Section text length: {len(section_text)} chars")
            
            # Prepare content for bedrock client
            content = [{"text": prompt}]
            
            # System prompt
            system_prompt = "You are an expert at analyzing document structure and identifying precise boundaries between invoices in a multi-invoice document."
            
            # Invoke Bedrock using the shared client
            logger.info(f"🔍 Invoking {self.model_id} for boundary detection...")
            response_with_metering = self.bedrock_client.invoke_model(
                model_id=self.model_id,
                system_prompt=system_prompt,
                content=content,
                temperature=0.0,
                max_tokens=max_tokens,
                context="BoundaryDetection"
            )
            
            # Extract response text from converse API format
            response = response_with_metering["response"]
            
            # Debug: Log the response structure
            logger.info(f"🔍 DEBUG: Response keys: {response.keys()}")
            logger.info(f"🔍 DEBUG: Full response structure: {json.dumps(response, default=str)[:1000]}")
            
            response_text = response["output"]["message"]["content"][0]["text"]
            
            # Log token usage
            if 'usage' in response:
                usage = response['usage']
                input_tokens = usage.get('inputTokens', 0)
                output_tokens = usage.get('outputTokens', 0)
                
                logger.info(
                    f"📊 Token usage: {input_tokens} input, {output_tokens} output"
                )
            
            # Parse JSON response (handle potential markdown wrapping)
            boundaries = self._parse_json_response(response_text)
            
            logger.info(f"✅ LLM detected {len(boundaries)} invoice boundaries")
            
            return boundaries
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"❌ Bedrock API error ({error_code}): {str(e)}")
            return []
            
        except Exception as e:
            logger.error(f"❌ Error in LLM boundary detection: {str(e)}")
            return []
    
    def _parse_json_response(self, response_text: str) -> List[Dict[str, Any]]:
        """
        Parse JSON from LLM response, handling markdown wrapping.
        
        Args:
            response_text: Raw response from LLM
            
        Returns:
            Parsed boundary list
        """
        try:
            cleaned_response = response_text.strip()
            
            # Remove markdown code blocks if present
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response.split('```json', 1)[1]
                cleaned_response = cleaned_response.rsplit('```', 1)[0].strip()
            elif cleaned_response.startswith('```'):
                cleaned_response = cleaned_response.split('```', 1)[1]
                cleaned_response = cleaned_response.rsplit('```', 1)[0].strip()
            
            # Additional cleanup - remove any leading/trailing whitespace and control characters
            cleaned_response = cleaned_response.strip()
            
            # Parse JSON
            boundaries = json.loads(cleaned_response)
            
            if not isinstance(boundaries, list):
                logger.error(f"❌ Response is not a list: {type(boundaries)}")
                return []
            
            return boundaries
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse LLM response as JSON: {str(e)}")
            logger.error(f"Response preview (first 500 chars): {response_text[:500]}")
            logger.error(f"Response preview (last 500 chars): {response_text[-500:]}")
            
            # Try to extract JSON array from response if it's embedded in text
            try:
                # Look for JSON array pattern
                import re
                json_match = re.search(r'\[\s*\{.*\}\s*\]', response_text, re.DOTALL)
                if json_match:
                    logger.info("Attempting to extract JSON array from response text")
                    extracted_json = json_match.group(0)
                    boundaries = json.loads(extracted_json)
                    if isinstance(boundaries, list):
                        logger.info("✅ Successfully extracted JSON array from response")
                        return boundaries
            except Exception as extraction_error:
                logger.error(f"Failed to extract JSON from response: {str(extraction_error)}")
            
            return []
            
        except Exception as e:
            logger.error(f"❌ Error parsing response: {str(e)}")
            logger.error(f"Response text type: {type(response_text)}")
            return []
    
    def validate_boundaries(
        self,
        boundaries: List[Dict[str, Any]],
        section_text: str,
        min_coverage: float = 0.80,
        max_boundaries: int = 100
    ) -> bool:
        """
        Validate that detected boundaries are reasonable.
        
        Checks:
        1. No overlapping boundaries
        2. Boundaries cover most of the text (>80%)
        3. Reasonable count (1-100 invoices per section)
        4. Each boundary has required fields
        
        Args:
            boundaries: List of boundary dictionaries from LLM
            section_text: Original section text
            min_coverage: Minimum text coverage ratio (default 0.80)
            max_boundaries: Maximum number of boundaries allowed
        
        Returns:
            True if boundaries pass validation, False otherwise
        """
        if not boundaries:
            logger.warning("⚠️ No boundaries detected")
            return False
        
        try:
            # Check 1: Required fields present
            for idx, boundary in enumerate(boundaries):
                required_fields = ['id', 'start_char', 'end_char', 'confidence']
                missing = [f for f in required_fields if f not in boundary]
                if missing:
                    logger.error(f"❌ Boundary {idx} missing fields: {missing}")
                    return False
            
            # Check 2: No overlapping boundaries
            sorted_boundaries = sorted(boundaries, key=lambda b: b['start_char'])
            for i in range(len(sorted_boundaries) - 1):
                current = sorted_boundaries[i]
                next_boundary = sorted_boundaries[i + 1]
                
                if current['end_char'] > next_boundary['start_char']:
                    logger.error(
                        f"❌ Overlapping boundaries detected: "
                        f"Invoice {current['id']} ends at {current['end_char']}, "
                        f"Invoice {next_boundary['id']} starts at {next_boundary['start_char']}"
                    )
                    return False
            
            # Check 3: Boundaries cover most of text
            total_coverage = sum(b['end_char'] - b['start_char'] for b in boundaries)
            coverage_ratio = total_coverage / len(section_text) if len(section_text) > 0 else 0
            
            if coverage_ratio < min_coverage:
                logger.warning(
                    f"⚠️ Low text coverage: {coverage_ratio:.1%} "
                    f"(expected >{min_coverage:.0%})"
                )
                return False
            
            # Check 4: Reasonable boundary count
            if len(boundaries) > max_boundaries:
                logger.error(f"❌ Too many boundaries: {len(boundaries)} (max {max_boundaries})")
                return False
            
            # Check 5: Boundaries within text bounds
            for boundary in boundaries:
                if boundary['start_char'] < 0 or boundary['end_char'] > len(section_text):
                    logger.error(
                        f"❌ Boundary out of range: "
                        f"start={boundary['start_char']}, end={boundary['end_char']}, "
                        f"text_length={len(section_text)}"
                    )
                    return False
            
            # All checks passed
            logger.info(
                f"✅ Boundary validation passed: {len(boundaries)} invoices, "
                f"{coverage_ratio:.1%} coverage"
            )
            return True
            
        except Exception as e:
            logger.error(f"❌ Error during boundary validation: {str(e)}")
            return False


def get_section_text(section, pages: Dict) -> str:
    """
    Extract full text for a section by combining page texts with PAGE markers.
    
    Args:
        section: Section object with page_ids
        pages: Dictionary of page objects (document.pages)
    
    Returns:
        Combined section text with [PAGE:N] markers
    """
    section_text = ""
    
    for page_id in section.page_ids:
        if page_id not in pages:
            logger.warning(f"Page {page_id} not found in document.pages")
            continue
        
        page = pages[page_id]
        
        # Extract page number from page_id (e.g., "page-5" -> 5)
        try:
            if page_id.startswith('page-'):
                page_number = int(page_id.split('-')[1])
            elif page_id.isdigit():
                page_number = int(page_id)
            else:
                page_number = section.page_ids.index(page_id) + 1
        except (ValueError, IndexError):
            page_number = section.page_ids.index(page_id) + 1
        
        # Add page marker
        page_marker = f"\n[PAGE:{page_number}]\n"
        
        # Get page text
        page_text = None
        
        # Try inline ocr_text first
        if hasattr(page, 'ocr_text') and page.ocr_text:
            page_text = page.ocr_text
        # Try parsed_text_uri (Nova OCR)
        elif hasattr(page, 'parsed_text_uri') and page.parsed_text_uri:
            from idp_common import s3
            page_text = s3.get_text_content(page.parsed_text_uri)
        # Try raw_text_uri (Textract)
        elif hasattr(page, 'raw_text_uri') and page.raw_text_uri:
            from idp_common import s3
            page_text = s3.get_text_content(page.raw_text_uri)
        
        if page_text:
            section_text += page_marker + page_text + "\n"
    
    return section_text
