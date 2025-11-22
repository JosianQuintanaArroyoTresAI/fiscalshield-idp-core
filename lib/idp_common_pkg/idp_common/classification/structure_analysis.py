# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
IMPROVED Structure Analysis Module

Key improvements over original:
1. PAGE markers as PRIMARY chunking strategy (most reliable)
2. Pattern matching as SECONDARY (more flexible regex)
3. Hybrid fallback approach
4. Better overlap risk calculation
"""

import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from decimal import Decimal

logger = logging.getLogger(__name__)


class InvoiceBoundaryDetector:
    """
    Detects invoice boundaries within a section of text.
    
    STRATEGY HIERARCHY (from most to least reliable):
    1. PAGE-marker-based chunking (invoices = 1-3 pages typically)
    2. LLM-identified patterns (flexible regex, not exact match)
    3. Fallback to overlap chunking
    """
    
    def __init__(self, chunk_size: int = 60000, overlap_size: int = 5000):
        """
        Initialize boundary detector.
        
        Args:
            chunk_size: Maximum chunk size for fallback chunking
            overlap_size: Overlap size for chunk boundaries
        """
        self.chunk_size = chunk_size
        self.overlap_size = overlap_size
        self.min_invoice_size = 500  # Min chars for valid invoice
        self.max_invoice_size = 50000  # Max single invoice size
        
    def detect_boundaries_page_based(self, section_text: str) -> Optional[List[Dict[str, Any]]]:
        """
        PRIMARY STRATEGY: Use PAGE markers to detect invoice boundaries.
        
        Most invoices are 1-2 pages. Page breaks are natural boundaries.
        This is OCR-proof and doesn't rely on text pattern matching.
        
        Args:
            section_text: Full section OCR text with [PAGE:X] markers
            
        Returns:
            List of boundary dicts, or None if strategy fails
        """
        try:
            # Find all PAGE markers
            page_pattern = r'\[PAGE:(\d+)\]'
            page_markers = list(re.finditer(page_pattern, section_text))
            
            if not page_markers:
                logger.warning("⚠️ No PAGE markers found - cannot use page-based strategy")
                return None
            
            logger.info(f"📄 Found {len(page_markers)} PAGE markers")
            
            boundaries = []
            
            # Process each page
            for i in range(len(page_markers)):
                start_pos = page_markers[i].start()
                end_pos = page_markers[i + 1].start() if i + 1 < len(page_markers) else len(section_text)
                page_num = int(page_markers[i].group(1))
                
                page_text = section_text[start_pos:end_pos]
                page_size = len(page_text)
                
                # Skip tiny pages (likely blank or noise)
                if page_size < 200:
                    logger.debug(f"⏭️  Skipping tiny page {page_num} ({page_size} chars)")
                    continue
                
                # Check if page contains invoice content
                has_invoice_markers = bool(re.search(
                    r'(?:invoice|total|amount|due|date|supplier|vendor|reference|number)',
                    page_text,
                    re.IGNORECASE
                ))
                
                if not has_invoice_markers:
                    logger.debug(f"⏭️  Skipping non-invoice page {page_num}")
                    continue
                
                # Check if page has invoice ENDING indicators (total, amount due)
                has_invoice_end = bool(re.search(
                    r'(?:total|amount\s*due|balance\s*due|payment\s*terms)',
                    page_text,
                    re.IGNORECASE
                ))
                
                boundaries.append({
                    'id': len(boundaries) + 1,
                    'start': start_pos,
                    'end': end_pos,
                    'size': page_size,
                    'pages': [page_num],
                    'has_end_marker': has_invoice_end,
                    'confidence': 'high' if has_invoice_end else 'medium'
                })
            
            if not boundaries:
                logger.warning("⚠️ No invoice pages found")
                return None
            
            # SMART MERGING: Combine pages that look like multi-page invoices
            merged_boundaries = self._merge_multi_page_invoices(boundaries, section_text)
            
            logger.info(
                f"✅ Page-based strategy: {len(page_markers)} pages → "
                f"{len(merged_boundaries)} invoice boundaries"
            )
            
            return merged_boundaries
            
        except Exception as e:
            logger.error(f"❌ Page-based detection failed: {e}")
            return None
    
    def _merge_multi_page_invoices(
        self, 
        page_boundaries: List[Dict[str, Any]], 
        section_text: str
    ) -> List[Dict[str, Any]]:
        """
        Merge consecutive pages that belong to the same invoice.
        
        Heuristics:
        - If page N has NO end marker AND page N+1 has invoice header → Merge
        - If pages are consecutive AND total size < max_invoice_size → Consider merging
        
        Args:
            page_boundaries: Single-page boundaries
            section_text: Full text for content analysis
            
        Returns:
            Merged multi-page boundaries
        """
        if len(page_boundaries) <= 1:
            return page_boundaries
        
        merged = []
        i = 0
        
        while i < len(page_boundaries):
            current = page_boundaries[i]
            
            # Look ahead - should we merge with next page?
            if i + 1 < len(page_boundaries):
                next_bound = page_boundaries[i + 1]
                
                # Get text from both pages
                current_text = section_text[current['start']:current['end']]
                next_text = section_text[next_bound['start']:next_bound['end']]
                
                # Heuristic 1: Current page has NO total/end marker
                current_has_end = current.get('has_end_marker', False)
                
                # Heuristic 2: Next page has invoice START indicators
                next_has_header = bool(re.search(
                    r'(?:^|\n)\s*(?:to:|bill\s*to|invoice|from)',
                    next_text[:500],  # Check first 500 chars
                    re.IGNORECASE
                ))
                
                # Heuristic 3: Combined size is reasonable
                combined_size = current['size'] + next_bound['size']
                size_ok = combined_size <= self.max_invoice_size
                
                # Decision: Merge if current page incomplete AND next looks like continuation
                should_merge = not current_has_end and size_ok
                
                if should_merge:
                    # Merge into multi-page invoice
                    logger.info(
                        f"🔗 Merging pages {current['pages'][0]} + {next_bound['pages'][0]} "
                        f"({combined_size} chars)"
                    )
                    
                    merged_invoice = {
                        'id': len(merged) + 1,
                        'start': current['start'],
                        'end': next_bound['end'],
                        'size': combined_size,
                        'pages': current['pages'] + next_bound['pages'],
                        'has_end_marker': next_bound.get('has_end_marker', False),
                        'confidence': 'medium'  # Multi-page = slightly less confident
                    }
                    merged.append(merged_invoice)
                    i += 2  # Skip both pages
                    continue
            
            # No merge - add current page as-is
            merged.append(current)
            i += 1
        
        return merged
    
    def detect_boundaries_with_flexible_patterns(
        self,
        section_text: str,
        start_hint: str,
        end_hint: str
    ) -> Optional[List[Dict[str, Any]]]:
        """
        SECONDARY STRATEGY: Use LLM-suggested patterns with FLEXIBLE matching.
        
        Unlike original implementation, this uses FLEXIBLE regex patterns
        instead of exact string matching (re.escape).
        
        Args:
            section_text: Full section text
            start_hint: LLM-suggested start pattern (e.g., "Invoice Number:")
            end_hint: LLM-suggested end pattern (e.g., "AMOUNT DUE")
            
        Returns:
            List of boundary dicts, or None if strategy fails
        """
        try:
            if not start_hint:
                logger.warning("No start pattern hint provided")
                return None
            
            # Convert hints to FLEXIBLE regex patterns
            start_pattern = self._create_flexible_pattern(start_hint)
            end_pattern = self._create_flexible_pattern(end_hint) if end_hint else None
            
            logger.info(f"🔍 Using flexible patterns: start='{start_pattern}', end='{end_pattern}'")
            
            # Find all invoice starts
            starts = []
            for match in re.finditer(start_pattern, section_text, re.IGNORECASE):
                page_num = self._get_page_number_at_position(section_text, match.start())
                starts.append({
                    'pos': match.start(),
                    'page': page_num
                })
            
            if not starts:
                logger.warning(f"No matches found for start pattern: '{start_hint}'")
                return None
            
            logger.info(f"📊 Found {len(starts)} potential invoice starts")
            
            # Find all invoice ends
            ends = []
            if end_pattern:
                for match in re.finditer(end_pattern, section_text, re.IGNORECASE):
                    page_num = self._get_page_number_at_position(section_text, match.end())
                    ends.append({
                        'pos': match.end(),
                        'page': page_num
                    })
                
                logger.info(f"📊 Found {len(ends)} potential invoice ends")
            
            # Match starts to ends
            boundaries = self._match_starts_to_ends(starts, ends, section_text)
            
            if not boundaries:
                logger.warning("Failed to create valid boundaries from patterns")
                return None
            
            logger.info(f"✅ Pattern-based strategy: {len(boundaries)} boundaries detected")
            return boundaries
            
        except Exception as e:
            logger.error(f"❌ Pattern-based detection failed: {e}")
            return None
    
    def _create_flexible_pattern(self, hint: str) -> str:
        r"""
        Convert LLM hint into flexible regex pattern.
        
        Examples:
        - "Invoice Number:" → r'invoice\s*number[\s:]*'
        - "AMOUNT DUE" → r'amount\s*due'
        - "To:" → r'to[\s:]*'
        
        Args:
            hint: LLM-suggested pattern hint
            
        Returns:
            Flexible regex pattern string
        """
        # Normalize hint
        hint_clean = hint.strip().lower()
        
        # Replace spaces with flexible whitespace
        pattern = re.sub(r'\s+', r'\\s*', hint_clean)
        
        # Add optional colon/punctuation at end
        if not pattern.endswith(r'[\s:]*'):
            pattern += r'[\s:]*'
        
        return pattern
    
    def _match_starts_to_ends(
        self,
        starts: List[Dict[str, int]],
        ends: List[Dict[str, int]],
        section_text: str
    ) -> List[Dict[str, Any]]:
        """
        Match invoice starts to appropriate ends.
        
        Strategy:
        - For each start, find the CLOSEST end that comes after it
        - If no end found, use next start position
        - Validate size constraints
        """
        boundaries = []
        
        for i, start_info in enumerate(starts):
            start_pos = start_info['pos']
            start_page = start_info['page']
            
            # Find next start (if exists)
            next_start_pos = starts[i + 1]['pos'] if i + 1 < len(starts) else len(section_text)
            
            # Find best matching end
            best_end_pos = None
            end_page = start_page
            
            for end_info in ends:
                end_pos = end_info['pos']
                # End must be after start and before next start
                if start_pos < end_pos < next_start_pos:
                    best_end_pos = end_pos
                    end_page = end_info['page']
                    break  # Take first valid end
            
            # If no end found, use position before next start
            if best_end_pos is None:
                best_end_pos = max(start_pos + self.min_invoice_size, next_start_pos - 10)
                end_page = self._get_page_number_at_position(section_text, best_end_pos)
            
            # Validate size
            invoice_size = best_end_pos - start_pos
            if invoice_size < self.min_invoice_size:
                logger.debug(f"⏭️  Skipping small boundary at {start_pos} ({invoice_size} chars)")
                continue
            
            if invoice_size > self.max_invoice_size:
                logger.warning(f"⚠️  Truncating large invoice at {start_pos} ({invoice_size} chars)")
                best_end_pos = start_pos + self.max_invoice_size
                end_page = self._get_page_number_at_position(section_text, best_end_pos)
            
            # Determine pages for this invoice
            pages = list(range(start_page, end_page + 1)) if start_page <= end_page else [start_page]
            
            boundaries.append({
                'id': i + 1,
                'start': start_pos,
                'end': best_end_pos,
                'size': best_end_pos - start_pos,
                'pages': pages,
                'confidence': 'high' if best_end_pos in [e['pos'] for e in ends] else 'medium'
            })
        
        return boundaries
    
    def _get_page_number_at_position(self, text: str, pos: int) -> int:
        """
        Get page number at a specific character position in text.
        
        Looks for [PAGE:N] markers before the position.
        """
        # Find all page markers before this position
        page_pattern = r'\[PAGE:(\d+)\]'
        page_markers = list(re.finditer(page_pattern, text[:pos]))
        
        if page_markers:
            # Return the last page number found before this position
            return int(page_markers[-1].group(1))
        
        # Default to page 1 if no markers found
        return 1
    
    def detect_boundaries_hybrid(
        self,
        section_text: str,
        start_hint: str = None,
        end_hint: str = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        HYBRID STRATEGY: Try strategies in order of reliability.
        
        1. PAGE-marker-based (most reliable)
        2. Pattern-based with hints (if provided)
        3. Return None (triggers overlap chunking fallback)
        
        Args:
            section_text: Full section text
            start_hint: Optional LLM-suggested start pattern
            end_hint: Optional LLM-suggested end pattern
            
        Returns:
            List of boundaries, or None if all strategies fail
        """
        # Strategy 1: PAGE-marker-based
        logger.info("🔍 Attempting PAGE-marker-based boundary detection...")
        boundaries = self.detect_boundaries_page_based(section_text)
        
        if boundaries and len(boundaries) >= 1:
            logger.info(f"✅ PAGE-marker strategy succeeded: {len(boundaries)} boundaries")
            return boundaries
        
        # Strategy 2: Pattern-based (if hints provided)
        if start_hint:
            logger.info("🔍 PAGE strategy failed, trying pattern-based detection...")
            boundaries = self.detect_boundaries_with_flexible_patterns(
                section_text, start_hint, end_hint
            )
            
            if boundaries and len(boundaries) >= 1:
                logger.info(f"✅ Pattern-based strategy succeeded: {len(boundaries)} boundaries")
                return boundaries
        
        # All strategies failed
        logger.warning("⚠️ All boundary detection strategies failed")
        return None
    
    def calculate_overlap_risk_zones(
        self,
        boundaries: List[Dict[str, int]],
        total_text_length: int
    ) -> Dict[str, Any]:
        """
        Calculate which invoices are at risk of duplication in overlap zones.
        
        IMPORTANT: This analysis assumes OVERLAP chunking will be used.
        If using pre-computed boundaries (1 invoice per chunk), overlap risk is ZERO.
        
        Args:
            boundaries: List of invoice boundaries
            total_text_length: Total length of section text
            
        Returns:
            Dictionary with overlap analysis
        """
        if not boundaries:
            return {
                'has_overlap_risk': False,
                'estimated_chunks': 1,
                'at_risk_invoices': [],
                'overlap_zones': []
            }
        
        # Calculate how many chunks we'd need IF using overlap strategy
        estimated_chunks = max(1, (total_text_length + self.chunk_size - 1) // self.chunk_size)
        
        if estimated_chunks == 1:
            return {
                'has_overlap_risk': False,
                'estimated_chunks': 1,
                'at_risk_invoices': [],
                'overlap_zones': []
            }
        
        # Identify overlap zones
        overlap_zones = []
        at_risk_invoice_ids = []
        
        for chunk_idx in range(estimated_chunks - 1):
            # Overlap zone is the last `overlap_size` chars of chunk N
            # and first `overlap_size` chars of chunk N+1
            chunk_end = (chunk_idx + 1) * self.chunk_size
            overlap_start = chunk_end - self.overlap_size
            overlap_end = chunk_end + self.overlap_size
            
            # Find invoices that fall in this overlap zone
            invoices_in_zone = []
            for boundary in boundaries:
                # Check if invoice overlaps with this zone
                invoice_start = boundary['start']
                invoice_end = boundary['end']
                
                if (overlap_start <= invoice_start <= overlap_end) or \
                   (overlap_start <= invoice_end <= overlap_end) or \
                   (invoice_start <= overlap_start and invoice_end >= overlap_end):
                    invoices_in_zone.append(boundary['id'])
                    if boundary['id'] not in at_risk_invoice_ids:
                        at_risk_invoice_ids.append(boundary['id'])
            
            if invoices_in_zone:
                overlap_zones.append({
                    'chunks': f"{chunk_idx}-{chunk_idx+1}",
                    'start': overlap_start,
                    'end': overlap_end,
                    'size': overlap_end - overlap_start,
                    'invoice_ids': invoices_in_zone
                })
        
        logger.info(
            f"📊 Overlap Risk Analysis: {len(overlap_zones)} overlap zones, "
            f"{len(at_risk_invoice_ids)} at-risk invoices out of {len(boundaries)} total"
        )
        
        return {
            'has_overlap_risk': len(at_risk_invoice_ids) > 0,
            'estimated_chunks': estimated_chunks,
            'at_risk_invoices': at_risk_invoice_ids,
            'overlap_zones': overlap_zones,
            'chunk_size': self.chunk_size,
            'overlap_size': self.overlap_size
        }
    
    def get_structure_analysis_prompt(self, section_text: str, document_type: str) -> str:
        """
        Generate prompt for LLM-based structure analysis.
        
        This prompt is designed to be ADDED to existing classification prompts,
        requiring minimal additional tokens but providing critical structure metadata.
        
        Args:
            section_text: OCR text from the section
            document_type: Classification type (e.g., "invoice")
            
        Returns:
            Prompt text for structure analysis
        """
        text_length = len(section_text)
        estimated_invoices = max(1, text_length // 2500)  # Rough estimate: 2500 chars per invoice
        
        prompt = f"""
ADDITIONAL TASK: Document Structure Analysis

You've classified this section as "{document_type}". Now analyze its internal structure:

1. **Invoice Count**: How many separate invoices are in this text?
   - Look for repeating patterns (headers, footers, invoice numbers)
   - Count distinct "Invoice Number:" or "Reference Number:" occurrences
   - Each invoice may span 1-3 pages

2. **Boundary Patterns**: What pattern RELIABLY identifies invoice starts/ends?
   - START patterns: "To:", "Invoice Number:", company name at top, "INVOICE" header, [PAGE:X] marker
   - END patterns: "AMOUNT DUE", "Payment terms:", "This is not a tax invoice", "VAT TOTAL"
   - Report the MOST COMMON and CONSISTENT pattern you observe
   - Be GENERAL not SPECIFIC (e.g., "Invoice Number" not "Invoice Number: INV-12345")

3. **Multi-Page Detection**: Are any invoices split across multiple pages?
   - Look for [PAGE:N] markers
   - Check if invoice spans multiple page markers

IMPORTANT: Provide GENERAL patterns that will work across ALL invoices in this batch.
Example: "Invoice Number:" not "Invoice Number: INV-60778"
Example: "AMOUNT DUE" not "AMOUNT DUE 296.74"

RESPOND IN THIS FORMAT (at the end of your classification response):

<structure_analysis>
  <invoice_count>{estimated_invoices}</invoice_count>
  <boundary_start_pattern>Invoice Number</boundary_start_pattern>
  <boundary_end_pattern>AMOUNT DUE</boundary_end_pattern>
  <multi_page_invoices>false</multi_page_invoices>
  <average_invoice_size>2500</average_invoice_size>
  <confidence>high</confidence>
</structure_analysis>

Text length: {text_length} chars (~{text_length/1000:.0f}kb)
Estimated invoices: ~{estimated_invoices}
"""
        return prompt
    
    def parse_structure_analysis_from_llm_response(
        self, llm_response: str, section_text: str
    ) -> Optional[Dict[str, Any]]:
        """
        Parse structure analysis from LLM response.
        
        Args:
            llm_response: Full LLM response including structure analysis
            section_text: Original section text (for validation)
            
        Returns:
            Dictionary with structure metadata, or None if parsing failed
        """
        try:
            # Extract structure_analysis block
            match = re.search(
                r'<structure_analysis>(.*?)</structure_analysis>',
                llm_response,
                re.DOTALL | re.IGNORECASE
            )
            
            if not match:
                logger.warning("No structure_analysis block found in LLM response")
                return None
            
            analysis_xml = match.group(1)
            
            # Parse fields
            invoice_count = self._extract_xml_field(analysis_xml, 'invoice_count', int, 1)
            boundary_start = self._extract_xml_field(analysis_xml, 'boundary_start_pattern', str, '')
            boundary_end = self._extract_xml_field(analysis_xml, 'boundary_end_pattern', str, '')
            multi_page = self._extract_xml_field(analysis_xml, 'multi_page_invoices', str, 'false').lower() == 'true'
            avg_size = self._extract_xml_field(analysis_xml, 'average_invoice_size', int, 2500)
            confidence = self._extract_xml_field(analysis_xml, 'confidence', str, 'medium')
            
            # Validate invoice count against text length
            text_length = len(section_text)
            expected_min_invoices = max(1, text_length // 10000)  # At least 1 invoice per 10kb
            expected_max_invoices = text_length // 500  # At most 1 invoice per 500 chars
            
            if invoice_count < expected_min_invoices or invoice_count > expected_max_invoices:
                logger.warning(
                    f"Invoice count {invoice_count} seems unrealistic for {text_length} chars "
                    f"(expected {expected_min_invoices}-{expected_max_invoices}). Using conservative estimate."
                )
                invoice_count = max(1, text_length // 2500)
            
            logger.info(
                f"📊 Structure Analysis: {invoice_count} invoices, "
                f"pattern: '{boundary_start}' → '{boundary_end}', "
                f"multi_page: {multi_page}, confidence: {confidence}"
            )
            
            return {
                'invoice_count': invoice_count,
                'boundary_start_pattern': boundary_start,
                'boundary_end_pattern': boundary_end,
                'multi_page_invoices': multi_page,
                'average_invoice_size': avg_size,
                'confidence': confidence,
                'analysis_method': 'llm'
            }
            
        except Exception as e:
            logger.error(f"Failed to parse structure analysis: {e}")
            return None
    
    def _extract_xml_field(
        self, xml_text: str, field_name: str, field_type: type, default: Any
    ) -> Any:
        """Extract and convert XML field value."""
        try:
            pattern = f'<{field_name}>(.*?)</{field_name}>'
            match = re.search(pattern, xml_text, re.DOTALL | re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                if field_type == int:
                    return int(value)
                elif field_type == float:
                    return float(value)
                else:
                    return value
            return default
        except Exception:
            return default
    
    def create_boundary_metadata(
        self,
        boundaries: List[Dict[str, int]],
        structure_analysis: Dict[str, Any],
        section_text: str
    ) -> Dict[str, Any]:
        """
        Create comprehensive boundary metadata for extraction function.
        
        This is the key output that extraction function will use to:
        1. Skip expensive regex-based chunking
        2. Process exact invoice boundaries
        3. Focus deduplication on overlap zones only
        
        Args:
            boundaries: Detected invoice boundaries
            structure_analysis: LLM structure analysis results
            section_text: Original section text
            
        Returns:
            Complete metadata dictionary for section.attributes
        """
        total_length = len(section_text)
        overlap_analysis = self.calculate_overlap_risk_zones(boundaries, total_length)
        
        return {
            'structure_detection': {
                'method': 'classification_with_hybrid_detection',
                'detected_at': 'classification_function',
                'invoice_count': len(boundaries),
                'confidence': structure_analysis.get('confidence', 'medium'),
                'boundary_pattern_start': structure_analysis.get('boundary_start_pattern', ''),
                'boundary_pattern_end': structure_analysis.get('boundary_end_pattern', ''),
                'multi_page_invoices': structure_analysis.get('multi_page_invoices', False),
                'average_invoice_size': structure_analysis.get('average_invoice_size', 2500)
            },
            'boundaries': boundaries,
            'fallback_chunking': {
                'chunk_size': self.chunk_size,
                'overlap_size': self.overlap_size,
                'estimated_chunks': overlap_analysis['estimated_chunks'],
                'has_overlap_risk': overlap_analysis['has_overlap_risk'],
                'at_risk_invoices': overlap_analysis['at_risk_invoices'],
                'overlap_zones': overlap_analysis['overlap_zones']
            },
            'extraction_guidance': {
                'use_detected_boundaries': len(boundaries) > 0,
                'focus_deduplication_on_overlap': overlap_analysis['has_overlap_risk'],
                'expected_invoices': len(boundaries),
                'deduplication_strategy': 'overlap_zones_only' if overlap_analysis['has_overlap_risk'] else 'none'
            }
        }


def enhance_classification_with_structure_analysis(
    section_text: str,
    document_type: str,
    llm_response: str,
    chunk_size: int = 60000,
    overlap_size: int = 5000
) -> Optional[Dict[str, Any]]:
    """
    Main entry point for structure analysis enhancement.
    
    Call this AFTER classification to add structure metadata to the section.
    
    Uses HYBRID detection strategy:
    1. PAGE-marker-based (primary)
    2. Pattern-based with LLM hints (secondary)
    3. Returns None if both fail (triggers overlap chunking fallback)
    
    Args:
        section_text: Full section OCR text
        document_type: Classification result (e.g., "invoice")
        llm_response: Full LLM response from classification
        chunk_size: Chunk size for fallback (from env var)
        overlap_size: Overlap size for fallback (from env var)
        
    Returns:
        Metadata dictionary to add to section.attributes, or None if analysis failed
    """
    # Only analyze invoice sections
    if document_type.lower() != 'invoice':
        logger.info(f"Skipping structure analysis for non-invoice type: {document_type}")
        return None
    
    detector = InvoiceBoundaryDetector(chunk_size, overlap_size)
    
    # Parse structure analysis from LLM response (for pattern hints)
    structure_analysis = detector.parse_structure_analysis_from_llm_response(
        llm_response, section_text
    )
    
    if not structure_analysis:
        logger.warning("Structure analysis parsing failed, will try boundary detection without hints")
        structure_analysis = {
            'invoice_count': max(1, len(section_text) // 2500),
            'boundary_start_pattern': '',
            'boundary_end_pattern': '',
            'multi_page_invoices': False,
            'average_invoice_size': 2500,
            'confidence': 'low',
            'analysis_method': 'fallback'
        }
    
    # Detect boundaries using HYBRID strategy
    boundaries = detector.detect_boundaries_hybrid(
        section_text,
        start_hint=structure_analysis.get('boundary_start_pattern', ''),
        end_hint=structure_analysis.get('boundary_end_pattern', '')
    )
    
    if not boundaries:
        logger.warning(
            f"No boundaries detected with hybrid strategy, extraction will use overlap chunking. "
            f"Expected {structure_analysis.get('invoice_count', 0)} invoices."
        )
        return None
    
    # Create comprehensive metadata
    metadata = detector.create_boundary_metadata(boundaries, structure_analysis, section_text)
    
    logger.info(
        f"✅ Structure analysis complete: {len(boundaries)} boundaries detected, "
        f"{metadata['fallback_chunking']['estimated_chunks']} estimated fallback chunks, "
        f"{len(metadata['fallback_chunking']['at_risk_invoices'])} at-risk invoices"
    )
    
    return metadata