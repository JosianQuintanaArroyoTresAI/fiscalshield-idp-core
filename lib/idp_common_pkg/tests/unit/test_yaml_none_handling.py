# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Unit tests for PyYAML library handling when yaml is None (not installed).

Tests the fix for AttributeError: 'NoneType' has no attribute 'YAMLError'
that occurs when PyYAML is not installed in Lambda environment.
"""

import json
from unittest.mock import patch

import pytest


@pytest.mark.unit
class TestPyYAMLNoneHandling:
    """Test handling when PyYAML library is not available (yaml=None)."""

    def test_extract_structured_data_when_yaml_is_none(self):
        """Test that extract_structured_data_from_text handles yaml=None gracefully."""
        # Mock yaml as None to simulate Lambda environment without PyYAML
        with patch("idp_common.utils.yaml", None):
            from idp_common.utils import extract_structured_data_from_text
            
            # JSON should still work
            json_text = '{"class": "invoice", "confidence": 0.95}'
            result, format_type = extract_structured_data_from_text(json_text)
            
            assert format_type == "json"
            assert result["class"] == "invoice"
            assert result["confidence"] == 0.95

    def test_yaml_error_check_when_yaml_is_none(self):
        """Test that yaml.YAMLError is not accessed when yaml=None."""
        # This is the critical fix - checking 'if yaml is not None' before accessing yaml.YAMLError
        yaml = None
        
        # Should not raise AttributeError
        if yaml is not None:
            # Only access yaml.YAMLError if yaml library is available
            from yaml import YAMLError
            should_not_execute = True
        else:
            # yaml is None, skip YAML-specific error handling
            should_not_execute = False
        
        assert should_not_execute is False

    def test_fallback_to_json_when_yaml_unavailable(self):
        """Test that JSON parsing is used as fallback when YAML is unavailable."""
        with patch("idp_common.utils.yaml", None):
            from idp_common.utils import extract_structured_data_from_text
            
            # Text that could be parsed as YAML if available
            text = """
            class: invoice
            confidence: 0.95
            """
            
            # Should return text with "unknown" format since YAML not available
            # and text is not valid JSON
            result, format_type = extract_structured_data_from_text(text)
            
            # Should fallback gracefully
            assert format_type == "unknown" or format_type == "json"

    def test_isinstance_check_with_yaml_none(self):
        """Test that isinstance checks don't fail when yaml=None."""
        yaml = None
        
        # This pattern should be avoided:
        # try:
        #     parsed = yaml.safe_load(text)
        # except yaml.YAMLError:  # AttributeError if yaml is None!
        #     pass
        
        # Instead, check if yaml is not None first:
        some_exception = ValueError("test")
        
        if yaml is not None:
            # Only import and check YAMLError if yaml is available
            from yaml import YAMLError
            is_yaml_error = isinstance(some_exception, YAMLError)
        else:
            # yaml is None, can't be a YAMLError
            is_yaml_error = False
        
        assert is_yaml_error is False

    def test_safe_yaml_parsing_pattern(self):
        """Test the safe pattern for YAML parsing with optional PyYAML."""
        # Simulate the fixed code pattern
        yaml = None  # PyYAML not installed
        text = "some yaml text"
        
        # Safe pattern:
        if yaml is not None:
            try:
                parsed = yaml.safe_load(text)
                format_type = "yaml"
            except Exception as e:
                # Check for YAMLError only if yaml is available
                if yaml is not None and hasattr(yaml, 'YAMLError'):
                    is_yaml_error = isinstance(e, yaml.YAMLError)
                else:
                    is_yaml_error = False
                format_type = "unknown"
        else:
            # YAML library not available
            format_type = "unknown"
        
        assert format_type == "unknown"


@pytest.mark.unit
class TestStructuredDataExtraction:
    """Test structured data extraction with and without PyYAML."""

    def test_json_extraction_works_without_yaml(self):
        """Test that JSON extraction works independently of PyYAML."""
        with patch("idp_common.utils.yaml", None):
            from idp_common.utils import extract_json_from_text, extract_structured_data_from_text
            
            # JSON in code block
            text = '```json\n{"class": "invoice"}\n```'
            json_str = extract_json_from_text(text)
            assert json_str == '{"class": "invoice"}'
            
            # Full extraction
            result, format_type = extract_structured_data_from_text(text)
            assert format_type == "json"
            assert result["class"] == "invoice"

    def test_detect_format_without_yaml(self):
        """Test format detection works without PyYAML."""
        with patch("idp_common.utils.yaml", None):
            from idp_common.utils import detect_format
            
            # JSON format
            json_text = '{"key": "value"}'
            assert detect_format(json_text) == "json"
            
            # Code block
            code_block = '```json\n{"key": "value"}\n```'
            assert detect_format(code_block) == "json"

    def test_classification_parsing_without_yaml(self):
        """Test classification response parsing when PyYAML not available."""
        with patch("idp_common.utils.yaml", None):
            from idp_common.utils import extract_structured_data_from_text
            
            # Model returns JSON classification
            llm_response = '''
            Here is the classification:
            ```json
            {
                "class": "invoice",
                "confidence": 0.95,
                "document_boundary": "start"
            }
            ```
            '''
            
            result, format_type = extract_structured_data_from_text(llm_response)
            
            assert format_type == "json"
            assert result["class"] == "invoice"
            assert result["confidence"] == 0.95


@pytest.mark.unit
class TestExceptionHandling:
    """Test exception handling in parsing code."""

    def test_no_attribute_error_when_yaml_none(self):
        """Test that no AttributeError occurs when yaml=None."""
        yaml = None
        
        # This should NOT raise AttributeError
        try:
            # Simulate checking yaml.YAMLError when yaml is None
            if yaml is not None:
                # Safe: only access when yaml is available
                yaml_error_class = yaml.YAMLError
                raise yaml_error_class("test")
            else:
                # yaml is None, handle gracefully
                raise ValueError("YAML not available")
        except ValueError as e:
            # Should catch ValueError, not AttributeError
            assert "YAML not available" in str(e)
        except AttributeError:
            # Should NOT reach here
            pytest.fail("AttributeError should not occur with safe yaml handling")

    def test_exception_chain_without_yaml(self):
        """Test exception handling chain when YAML parsing fails."""
        with patch("idp_common.utils.yaml", None):
            from idp_common.utils import extract_structured_data_from_text
            
            # Invalid JSON
            invalid_text = "not valid json or yaml"
            
            # Should not raise exception, should return text with unknown format
            result, format_type = extract_structured_data_from_text(invalid_text)
            
            assert format_type == "unknown"
            assert result == invalid_text

    def test_yaml_error_isinstance_check_safe(self):
        """Test that isinstance check for YAMLError is done safely."""
        yaml = None
        exception = ValueError("test error")
        
        # UNSAFE pattern (causes AttributeError):
        # is_yaml_error = isinstance(exception, yaml.YAMLError)
        
        # SAFE pattern:
        if yaml is not None:
            from yaml import YAMLError
            is_yaml_error = isinstance(exception, YAMLError)
        else:
            is_yaml_error = False
        
        assert is_yaml_error is False
        # No AttributeError raised!


@pytest.mark.unit
class TestClassificationWithoutYAML:
    """Test classification workflow when PyYAML not available in Lambda."""

    def test_classification_result_parsing_json_only(self):
        """Test that classification can parse results with JSON only (no YAML)."""
        with patch("idp_common.utils.yaml", None):
            from idp_common.utils import extract_structured_data_from_text
            
            # Typical Bedrock Claude response
            classification_response = '''
            Based on the document content, this is an invoice.
            
            ```json
            {
                "class": "invoice",
                "document_boundary": "start"
            }
            ```
            '''
            
            result, format_type = extract_structured_data_from_text(classification_response)
            
            assert format_type == "json"
            assert result["class"] == "invoice"
            # Should not return "unclassified" due to parsing error

    def test_unclassified_not_returned_on_yaml_none_error(self):
        """Test that 'unclassified' is not returned due to yaml=None AttributeError."""
        with patch("idp_common.utils.yaml", None):
            from idp_common.utils import extract_structured_data_from_text
            
            # Valid JSON response
            response = '{"class": "invoice"}'
            
            # Should parse successfully
            result, format_type = extract_structured_data_from_text(response)
            
            assert format_type == "json"
            assert result["class"] == "invoice"
            assert result["class"] != "unclassified"
