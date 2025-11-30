# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
LLM-based invoice boundary detection using Claude
Replaces regex-based semantic chunking with intelligent boundary identification
"""

import json
import logging
import re
from typing import List, Dict, Any, Optional
from botocore.exceptions import ClientError
from idp_common.bedrock.client import BedrockClient

logger = logging.getLogger(__name__)

# Default inference profile for boundary detection (EU cross-region)
DEFAULT_BOUNDARY_MODEL_ID = (
    "arn:aws:bedrock:eu-central-1:864899848062:inference-profile/"
    "eu.anthropic.claude-3-5-sonnet-20240620-v1:0"
)


BOUNDARY_DETECTION_PROMPT = """You are reviewing OCR text that may include multiple invoices separated by [PAGE:x] markers.

<<CACHEPOINT>>
Your mission: deliver precise, gap-free boundaries so downstream extraction can process each invoice independently.

<<CACHEPOINT>>
### What counts as an invoice boundary
**Reliable START signals**
- Company header, logo, or registered address block
- Labels such as "Invoice", "Tax Invoice", "Invoice No", "Invoice Number"
- Customer section ("Bill To", "Sold To", "Ship To")
- Early metadata (issue date, PO, account number)

**Reliable END signals**
- Summary tables ("Amount Due", "Balance", "Total" with currency)
- Payment instructions, bank details, remittance info
- Terms/disclaimers ("Thank you", "Payment due", "This is not a tax invoice")
- Footers with registration or VAT info
- A clear blank gap or new header before the next invoice

When start/end cues conflict, prefer the option that maximizes total coverage without overlapping ranges.

<<CACHEPOINT>>
### Required workflow
1. Skim every page marker sequentially; note where context switches.
2. Propose provisional boundaries using the cues above and any strong separators (blank lines, page headers, separator characters).
3. Validate coverage: combined length of all boundaries must be ≥92% of the provided text unless you confidently return an empty list.
4. Reject partial or low-signal fragments (set confidence "low" only when unavoidable and explain via indicators).
5. Ensure `end_char` of invoice *i* is strictly less than `start_char` of invoice *i+1*.

<<CACHEPOINT>>
### Output contract (JSON ONLY)
Return a JSON array ordered by document flow. Each object MUST include:
- `id`: sequential integer starting at 1.
- `start_char` and `end_char`: 0-indexed offsets referencing the provided text.
- `page_numbers`: list of page integers covered.
- `confidence`: `high`, `medium`, or `low`.
- `start_indicator` / `end_indicator`: short snippets (≤120 chars) explaining what anchored the decision.

Example:
[
    {
        "id": 1,
        "start_char": 0,
        "end_char": 2847,
        "confidence": "high",
        "page_numbers": [1, 2],
        "start_indicator": "Invoice Number: INV-60778",
        "end_indicator": "AMOUNT DUE £296.74"
    }
]

Rules:
- Return `[]` when no valid invoice is present; otherwise cover the document with <250 character gaps when feasible.
- Do not emit markdown, prose, backticks, or comments—JSON only.
- Bounds must lie within `[0, len(text))`.

<<CACHEPOINT>>
### Text to analyze
{section_text}

Return ONLY the JSON array—no explanation.
"""


class LLMBoundaryDetector:
    """
    LLM-based boundary detection for invoices and other documents.
    Uses Claude models via Bedrock for intelligent structure analysis.
    """
    
    def __init__(
        self,
        region: str = "us-east-1",
        model_id: str = DEFAULT_BOUNDARY_MODEL_ID,
        use_caching: bool = True,
        min_coverage: float = 0.92,
        max_gap_ratio: float = 0.12,
        fallback_pages_per_boundary: int = 2
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
        self.min_coverage = min_coverage
        self.max_gap_ratio = max_gap_ratio
        self.fallback_pages_per_boundary = max(1, fallback_pages_per_boundary)
        self.last_validation_details: Dict[str, Any] = {}
        self.last_validation_error: Optional[str] = None
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
            
            # Build prompt with section text without triggering str.format brace parsing
            prompt = BOUNDARY_DETECTION_PROMPT.replace("{section_text}", section_text)
            
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
            
            # Remove newline / carriage-return / tab characters that break JSON parsing
            cleaned_response = (
                cleaned_response.replace('\r', ' ')
                .replace('\n', ' ')
                .replace('\t', ' ')
            )
            
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
        min_coverage: Optional[float] = None,
        max_boundaries: int = 100,
        max_gap_ratio: Optional[float] = None
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
        self.last_validation_details = {}
        min_coverage = self.min_coverage if min_coverage is None else min_coverage
        max_gap_ratio = self.max_gap_ratio if max_gap_ratio is None else max_gap_ratio

        if not boundaries:
            logger.warning("⚠️ No boundaries detected")
            self.last_validation_error = "no_boundaries"
            return False
        
        try:
            # Check 1: Required fields present
            for idx, boundary in enumerate(boundaries):
                required_fields = ['id', 'start_char', 'end_char', 'confidence']
                missing = [f for f in required_fields if f not in boundary]
                if missing:
                    logger.error(f"❌ Boundary {idx} missing fields: {missing}")
                    self.last_validation_error = f"missing_fields:{missing}"
                    return False

                if boundary['start_char'] >= boundary['end_char']:
                    logger.error(
                        f"❌ Invalid boundary {boundary.get('id')}: start_char >= end_char"
                    )
                    self.last_validation_error = "start_greater_than_end"
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
                    self.last_validation_error = "overlap_detected"
                    return False
            
            # Check 3: Boundaries cover most of text
            total_coverage = 0
            largest_gap = 0
            previous_end = 0
            text_length = len(section_text)

            for boundary in sorted_boundaries:
                start = boundary['start_char']
                end = boundary['end_char']
                gap = max(0, start - previous_end)
                if gap > largest_gap:
                    largest_gap = gap
                total_coverage += max(0, end - start)
                previous_end = end

            tail_gap = max(0, text_length - previous_end)
            if tail_gap > largest_gap:
                largest_gap = tail_gap

            coverage_ratio = total_coverage / text_length if text_length > 0 else 0
            largest_gap_ratio = largest_gap / text_length if text_length > 0 else 0

            logger.info(
                f"📏 Coverage stats: {coverage_ratio:.1%} coverage, "
                f"max gap {largest_gap_ratio:.1%}"
            )
            
            if coverage_ratio < min_coverage:
                logger.warning(
                    f"⚠️ Low text coverage: {coverage_ratio:.1%} "
                    f"(expected >{min_coverage:.0%})"
                )
                self.last_validation_error = "low_coverage"
                return False

            if max_gap_ratio is not None and largest_gap_ratio > max_gap_ratio:
                logger.warning(
                    f"⚠️ Large uncovered region detected: {largest_gap_ratio:.1%} gap "
                    f"(allowed <{max_gap_ratio:.1%})"
                )
                self.last_validation_error = "gap_threshold_exceeded"
                return False
            
            # Check 4: Reasonable boundary count
            if len(boundaries) > max_boundaries:
                logger.error(f"❌ Too many boundaries: {len(boundaries)} (max {max_boundaries})")
                self.last_validation_error = "too_many_boundaries"
                return False
            
            # Check 5: Boundaries within text bounds
            for boundary in boundaries:
                if boundary['start_char'] < 0 or boundary['end_char'] > len(section_text):
                    logger.error(
                        f"❌ Boundary out of range: "
                        f"start={boundary['start_char']}, end={boundary['end_char']}, "
                        f"text_length={len(section_text)}"
                    )
                    self.last_validation_error = "boundary_out_of_range"
                    return False
            
            # All checks passed
            logger.info(
                f"✅ Boundary validation passed: {len(boundaries)} invoices, "
                f"{coverage_ratio:.1%} coverage"
            )
            self.last_validation_details = {
                "coverage_ratio": coverage_ratio,
                "largest_gap_ratio": largest_gap_ratio,
                "boundary_count": len(boundaries)
            }
            self.last_validation_error = None
            return True
            
        except Exception as e:
            logger.error(f"❌ Error during boundary validation: {str(e)}")
            self.last_validation_error = str(e)
            return False

    def generate_page_chunk_fallback(
        self,
        section_text: str,
        section_pages: Optional[List[str]] = None,
        max_pages_per_boundary: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Generate deterministic fallback boundaries using PAGE markers."""

        if not section_text:
            logger.warning("Cannot generate fallback boundaries without section text")
            return []

        pages_per_boundary = max_pages_per_boundary or self.fallback_pages_per_boundary
        page_blocks = self._extract_page_blocks(section_text)

        if section_pages and len(page_blocks) != len(section_pages):
            logger.debug(
                "Fallback page block count mismatch: text has %s markers, section has %s pages",
                len(page_blocks),
                len(section_pages)
            )

        if not page_blocks:
            logger.info("Fallback using single boundary covering entire section")
            return [
                {
                    "id": 1,
                    "start_char": 0,
                    "end_char": len(section_text),
                    "confidence": "low",
                    "page_numbers": [],
                    "start_indicator": self._extract_indicator_snippet(section_text, 0, forward=True),
                    "end_indicator": self._extract_indicator_snippet(section_text, len(section_text), forward=False)
                }
            ]

        boundaries: List[Dict[str, Any]] = []
        current_chunk: List[Dict[str, Any]] = []

        for block in page_blocks:
            current_chunk.append(block)
            if len(current_chunk) >= pages_per_boundary:
                boundaries.append(self._build_fallback_boundary(current_chunk, section_text))
                current_chunk = []

        if current_chunk:
            boundaries.append(self._build_fallback_boundary(current_chunk, section_text))

        for idx, boundary in enumerate(boundaries, start=1):
            boundary["id"] = idx

        logger.info(
            f"🛟 Generated {len(boundaries)} fallback boundaries using {pages_per_boundary} page(s) per chunk"
        )
        return boundaries

    def _extract_page_blocks(self, section_text: str) -> List[Dict[str, Any]]:
        """Build page spans using PAGE markers in the section text."""
        matches = list(re.finditer(r"\[PAGE:(\d+)\]", section_text))
        page_blocks: List[Dict[str, Any]] = []

        for idx, match in enumerate(matches):
            start = match.end()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(section_text)
            page_blocks.append(
                {
                    "page_number": int(match.group(1)),
                    "start": start,
                    "end": end,
                }
            )

        return page_blocks

    def _build_fallback_boundary(
        self,
        page_blocks: List[Dict[str, Any]],
        section_text: str
    ) -> Dict[str, Any]:
        start_char = page_blocks[0]["start"]
        end_char = page_blocks[-1]["end"]
        return {
            "id": 0,  # placeholder, set later
            "start_char": start_char,
            "end_char": end_char,
            "confidence": "low",
            "page_numbers": [block["page_number"] for block in page_blocks],
            "start_indicator": self._extract_indicator_snippet(section_text, start_char, forward=True),
            "end_indicator": self._extract_indicator_snippet(section_text, end_char, forward=False)
        }

    def _extract_indicator_snippet(
        self,
        text: str,
        pivot: int,
        forward: bool,
        window: int = 120
    ) -> str:
        if forward:
            snippet = text[pivot: min(len(text), pivot + window)]
        else:
            start = max(0, pivot - window)
            snippet = text[start:pivot]

        cleaned = snippet.strip()
        if not cleaned:
            return "fallback-boundary"
        return cleaned

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
