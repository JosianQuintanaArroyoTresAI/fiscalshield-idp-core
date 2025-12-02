#!/usr/bin/env python3
"""
Test LLM-based boundary detection

This test validates that the LLM boundary detector can:
1. Detect invoice boundaries in section text
2. Validate boundaries correctly
3. Handle edge cases (no boundaries, invalid responses, etc.)
"""

import sys
import os
import json
import pytest
from unittest.mock import Mock, patch, MagicMock

# Add lib to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib', 'idp_common_pkg'))

from idp_common.classification.llm_boundary_detection import (
    LLMBoundaryDetector,
    get_section_text,
    DEFAULT_BOUNDARY_MODEL_ID,
)


# Sample test data
SAMPLE_INVOICE_TEXT = """[PAGE:1]
ACME Corporation
123 Business Street
London, UK

Invoice Number: INV-001
Date: 15/01/2024

Bill To:
Customer Ltd
456 Customer Road

Description         Qty    Price    Amount
Product A           10     £50.00   £500.00
Product B           5      £30.00   £150.00

Subtotal:                           £650.00
VAT (20%):                          £130.00
AMOUNT DUE:                         £780.00

[PAGE:2]
XYZ Services
789 Service Ave
Manchester, UK

Invoice Number: INV-002
Date: 16/01/2024

Bill To:
Another Client Inc
321 Client Street

Description         Qty    Price    Amount
Service A           1      £1000.00 £1000.00

Subtotal:                           £1000.00
VAT (20%):                          £200.00
AMOUNT DUE:                         £1200.00

Thank you for your business
"""


class TestLLMBoundaryDetector:
    """Test LLM boundary detection functionality"""
    
    def test_initialization(self):
        """Test detector initialization with different configurations"""
        # Default initialization
        detector = LLMBoundaryDetector()
        assert detector.model_id == DEFAULT_BOUNDARY_MODEL_ID
        assert detector.use_caching is True
        
        # Custom initialization
        detector = LLMBoundaryDetector(
            region="eu-central-1",
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            use_caching=False
        )
        assert detector.region == "eu-central-1"
        assert detector.model_id == "anthropic.claude-3-haiku-20240307-v1:0"
        assert detector.use_caching is False
    
    def test_parse_json_response_valid(self):
        """Test parsing valid JSON responses"""
        detector = LLMBoundaryDetector()
        
        # Plain JSON
        response = '[{"id": 1, "start_char": 0, "end_char": 100, "confidence": "high"}]'
        result = detector._parse_json_response(response)
        assert len(result) == 1
        assert result[0]['id'] == 1
        
        # JSON with markdown
        response = '```json\n[{"id": 1, "start_char": 0, "end_char": 100, "confidence": "high"}]\n```'
        result = detector._parse_json_response(response)
        assert len(result) == 1
        
        # JSON with markdown (alternate format)
        response = '```\n[{"id": 1, "start_char": 0, "end_char": 100, "confidence": "high"}]\n```'
        result = detector._parse_json_response(response)
        assert len(result) == 1
    
    def test_parse_json_response_invalid(self):
        """Test parsing invalid JSON responses"""
        detector = LLMBoundaryDetector()
        
        # Invalid JSON
        response = "This is not JSON"
        result = detector._parse_json_response(response)
        assert result == []
        
        # Empty response
        response = ""
        result = detector._parse_json_response(response)
        assert result == []
        
        # JSON object instead of array
        response = '{"id": 1, "start_char": 0}'
        result = detector._parse_json_response(response)
        assert result == []
    
    def test_validate_boundaries_success(self):
        """Test boundary validation with valid boundaries"""
        detector = LLMBoundaryDetector()
        
        section_text = "x" * 10000
        boundaries = [
            {'id': 1, 'start_char': 0, 'end_char': 5000, 'confidence': 'high'},
            {'id': 2, 'start_char': 5000, 'end_char': 10000, 'confidence': 'high'}
        ]
        
        result = detector.validate_boundaries(boundaries, section_text)
        assert result is True
    
    def test_validate_boundaries_overlapping(self):
        """Test boundary validation rejects overlapping boundaries"""
        detector = LLMBoundaryDetector()
        
        section_text = "x" * 2000
        boundaries = [
            {'id': 1, 'start_char': 0, 'end_char': 1000, 'confidence': 'high'},
            {'id': 2, 'start_char': 900, 'end_char': 2000, 'confidence': 'high'}  # Overlap!
        ]
        
        result = detector.validate_boundaries(boundaries, section_text)
        assert result is False
    
    def test_validate_boundaries_low_coverage(self):
        """Test boundary validation rejects low text coverage"""
        detector = LLMBoundaryDetector()
        
        section_text = "x" * 10000
        boundaries = [
            {'id': 1, 'start_char': 0, 'end_char': 500, 'confidence': 'high'}  # Only 5% coverage
        ]
        
        result = detector.validate_boundaries(boundaries, section_text, min_coverage=0.80)
        assert result is False
    
    def test_validate_boundaries_large_gap(self):
        """Test boundary validation rejects large uncovered regions"""
        detector = LLMBoundaryDetector(min_coverage=0.50, max_gap_ratio=0.05)
        section_text = "x" * 1000
        boundaries = [
            {'id': 1, 'start_char': 0, 'end_char': 450, 'confidence': 'high'},
            {'id': 2, 'start_char': 750, 'end_char': 1000, 'confidence': 'high'}
        ]

        result = detector.validate_boundaries(boundaries, section_text)
        assert result is False
        assert detector.last_validation_error == "gap_threshold_exceeded"

    def test_validate_boundaries_missing_fields(self):
        """Test boundary validation rejects boundaries with missing fields"""
        detector = LLMBoundaryDetector()
        
        section_text = "x" * 1000
        boundaries = [
            {'id': 1, 'start_char': 0}  # Missing end_char and confidence
        ]
        
        result = detector.validate_boundaries(boundaries, section_text)
        assert result is False
    
    def test_validate_boundaries_out_of_range(self):
        """Test boundary validation rejects out-of-range boundaries"""
        detector = LLMBoundaryDetector()
        
        section_text = "x" * 1000
        boundaries = [
            {'id': 1, 'start_char': 0, 'end_char': 2000, 'confidence': 'high'}  # end_char > text length
        ]
        
        result = detector.validate_boundaries(boundaries, section_text)
        assert result is False
    
    @patch('idp_common.classification.llm_boundary_detection.BedrockClient')
    def test_detect_invoice_boundaries_success(self, mock_bedrock_client_cls):
        """Test successful boundary detection with mocked Bedrock response"""
        mock_bedrock_client = MagicMock()
        mock_bedrock_client_cls.return_value = mock_bedrock_client
        
        llm_payload = json.dumps([
            {
                'id': 1,
                'start_char': 0,
                'end_char': 500,
                'confidence': 'high',
                'page_numbers': [1],
                'start_indicator': 'Invoice Number: INV-001',
                'end_indicator': 'AMOUNT DUE: £780.00'
            },
            {
                'id': 2,
                'start_char': 501,
                'end_char': 1000,
                'confidence': 'high',
                'page_numbers': [2],
                'start_indicator': 'Invoice Number: INV-002',
                'end_indicator': 'AMOUNT DUE: £1200.00'
            }
        ])
        
        mock_response = {
            'response': {
                'output': {
                    'message': {
                        'content': [{'text': llm_payload}]
                    }
                },
                'usage': {
                    'inputTokens': 1000,
                    'outputTokens': 100
                }
            }
        }
        
        mock_bedrock_client.invoke_model.return_value = mock_response
        
        detector = LLMBoundaryDetector()
        boundaries = detector.detect_invoice_boundaries(
            section_text=SAMPLE_INVOICE_TEXT,
            section_pages=['page-1', 'page-2']
        )
        
        assert len(boundaries) == 2
        assert boundaries[0]['id'] == 1
        assert boundaries[1]['id'] == 2
        assert mock_bedrock_client.invoke_model.called
    
    @patch('idp_common.classification.llm_boundary_detection.BedrockClient')
    def test_detect_invoice_boundaries_error_handling(self, mock_bedrock_client_cls):
        """Test boundary detection handles Bedrock errors gracefully"""
        mock_bedrock = MagicMock()
        mock_bedrock_client_cls.return_value = mock_bedrock
        
        from botocore.exceptions import ClientError
        mock_bedrock.invoke_model.side_effect = ClientError(
            {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            'InvokeModel'
        )
        
        detector = LLMBoundaryDetector()
        boundaries = detector.detect_invoice_boundaries(
            section_text=SAMPLE_INVOICE_TEXT,
            section_pages=['page-1']
        )
        
        assert boundaries == []

    def test_generate_page_chunk_fallback(self):
        """Test fallback boundary generation using PAGE markers"""
        detector = LLMBoundaryDetector(fallback_pages_per_boundary=1)
        fallback = detector.generate_page_chunk_fallback(SAMPLE_INVOICE_TEXT)
        assert len(fallback) == 2
        assert fallback[0]['page_numbers'] == [1]
        assert fallback[0]['id'] == 1

    def test_generate_page_chunk_fallback_without_markers(self):
        """Test fallback boundary generation when no markers exist"""
        detector = LLMBoundaryDetector()
        text = "Invoice Number: 1\nTotal 10"
        fallback = detector.generate_page_chunk_fallback(text, [])
        assert len(fallback) == 1
        assert fallback[0]['start_char'] == 0
        assert fallback[0]['end_char'] == len(text)


class TestGetSectionText:
    """Test section text extraction"""
    
    def test_get_section_text_basic(self):
        """Test basic section text extraction"""
        # Create mock section
        section = Mock()
        section.page_ids = ['page-1', 'page-2']
        
        # Create mock pages
        page1 = Mock()
        page1.ocr_text = "Page 1 text"
        
        page2 = Mock()
        page2.ocr_text = "Page 2 text"
        
        pages = {
            'page-1': page1,
            'page-2': page2
        }
        
        # Extract section text
        section_text = get_section_text(section, pages)
        
        assert "[PAGE:1]" in section_text
        assert "Page 1 text" in section_text
        assert "[PAGE:2]" in section_text
        assert "Page 2 text" in section_text
    
    def test_get_section_text_missing_page(self):
        """Test section text extraction with missing page"""
        section = Mock()
        section.page_ids = ['page-1', 'page-2', 'page-3']
        
        page1 = Mock()
        page1.ocr_text = "Page 1 text"
        
        pages = {
            'page-1': page1
            # page-2 and page-3 missing
        }
        
        section_text = get_section_text(section, pages)
        
        assert "[PAGE:1]" in section_text
        assert "Page 1 text" in section_text
        # Should handle missing pages gracefully


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
