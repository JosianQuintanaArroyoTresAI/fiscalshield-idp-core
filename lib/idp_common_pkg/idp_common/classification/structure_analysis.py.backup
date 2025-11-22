# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Structure Analysis Module

Enhances document classification with intelligent boundary detection for invoices.
Analyzes document structure to identify invoice boundaries and provides
risk-aware chunking metadata for extraction optimization.
"""

import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from decimal import Decimal

logger = logging.getLogger(__name__)


class InvoiceBoundaryDetector:
    """
    Detects invoice boundaries within a section of text.
    
    Key Features:
    - LLM-based boundary detection (learns document-specific patterns)
    - Overlap zone risk analysis
    - Multi-page invoice support
    - Fallback chunking intelligence
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

2. **Boundary Patterns**: What pattern identifies invoice starts/ends?
   - Common start: "To:", "Invoice Number:", company name, "INVOICE" header
   - Common end: "AMOUNT DUE", "Payment terms:", "This is not a tax invoice"
   - Report the MOST RELIABLE pattern you observe

3. **Multi-Page Detection**: Are any invoices split across multiple pages?
   - Look for [PAGE:N] markers
   - Check if invoice spans multiple page markers

RESPOND IN THIS FORMAT (at the end of your classification response):

<structure_analysis>
  <invoice_count>{estimated_invoices}</invoice_count>
  <boundary_start_pattern>Invoice Number:</boundary_start_pattern>
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
    
    def detect_boundaries_with_pattern(
        self,
        section_text: str,
        start_pattern: str,
        end_pattern: str
    ) -> List[Dict[str, int]]:
        """
        Detect invoice boundaries using learned patterns.
        
        Args:
            section_text: Full section text
            start_pattern: Pattern that marks invoice start
            end_pattern: Pattern that marks invoice end
            
        Returns:
            List of boundary dicts with start/end positions and page numbers
        """
        boundaries = []
        
        if not start_pattern:
            logger.warning("No start pattern provided, cannot detect boundaries")
            return boundaries
        
        try:
            # Find all invoice starts
            starts = []
            for match in re.finditer(re.escape(start_pattern), section_text, re.IGNORECASE):
                page_num = self._get_page_number_at_position(section_text, match.start())
                starts.append({
                    'pos': match.start(),
                    'page': page_num
                })
            
            if not starts:
                logger.warning(f"No matches found for start pattern: '{start_pattern}'")
                return boundaries
            
            # Find all invoice ends
            ends = []
            if end_pattern:
                for match in re.finditer(re.escape(end_pattern), section_text, re.IGNORECASE):
                    page_num = self._get_page_number_at_position(section_text, match.end())
                    ends.append({
                        'pos': match.end(),
                        'page': page_num
                    })
            
            # Match starts to ends
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
                    if start_pos < end_pos < next_start_pos:
                        best_end_pos = end_pos
                        end_page = end_info['page']
                        break
                
                # If no end found, use next start position
                if best_end_pos is None:
                    best_end_pos = next_start_pos - 10  # Leave small gap
                    end_page = self._get_page_number_at_position(section_text, best_end_pos)
                
                # Determine pages for this invoice
                pages = list(range(start_page, end_page + 1)) if start_page <= end_page else [start_page]
                
                boundaries.append({
                    'id': i + 1,
                    'start': start_pos,
                    'end': best_end_pos,
                    'size': best_end_pos - start_pos,
                    'pages': pages,
                    'pattern_match': start_pattern
                })
            
            logger.info(f"✅ Detected {len(boundaries)} invoice boundaries using pattern matching")
            return boundaries
            
        except Exception as e:
            logger.error(f"Failed to detect boundaries with pattern: {e}")
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
    
    def calculate_overlap_risk_zones(
        self,
        boundaries: List[Dict[str, int]],
        total_text_length: int
    ) -> Dict[str, Any]:
        """
        Calculate which invoices are at risk of duplication in overlap zones.
        
        This is your key insight: instead of deduplicating the entire 60k chunk,
        we only need to check the 5k overlap zones!
        
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
        
        # Calculate how many chunks we'd need
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
                'method': 'classification_with_llm_analysis',
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
    
    # Parse structure analysis from LLM response
    structure_analysis = detector.parse_structure_analysis_from_llm_response(
        llm_response, section_text
    )
    
    if not structure_analysis:
        logger.warning("Structure analysis failed, extraction will use fallback chunking")
        return None
    
    # Detect boundaries using learned patterns
    boundaries = detector.detect_boundaries_with_pattern(
        section_text,
        structure_analysis.get('boundary_start_pattern', ''),
        structure_analysis.get('boundary_end_pattern', '')
    )
    
    if not boundaries:
        logger.warning(
            f"No boundaries detected with patterns, extraction will use fallback chunking. "
            f"Expected {structure_analysis.get('invoice_count', 0)} invoices."
        )
        return None
    
    # Create comprehensive metadata
    metadata = detector.create_boundary_metadata(boundaries, structure_analysis, section_text)
    
    logger.info(
        f"✅ Structure analysis complete: {len(boundaries)} boundaries detected, "
        f"{metadata['fallback_chunking']['estimated_chunks']} estimated chunks, "
        f"{len(metadata['fallback_chunking']['at_risk_invoices'])} at-risk invoices"
    )
    
    return metadata
