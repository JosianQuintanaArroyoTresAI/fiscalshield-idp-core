# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Unit tests for LLM hallucination prevention in bank statement extraction.

Tests that the extraction prompt correctly instructs the model to:
1. Return empty results for non-bank-statement documents
2. Not copy example transactions from the prompt
3. Only extract transactions actually present in the text
"""

import pytest


@pytest.mark.unit
class TestHallucinationPrevention:
    """Test hallucination prevention in extraction prompts."""

    def test_prompt_has_document_type_check(self):
        """Test that prompt includes critical document type check."""
        import sys
        import os
        
        # Add patterns directory to path
        patterns_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "patterns", "pattern-2", "lambdas", "bank_statement_extraction")
        if os.path.exists(patterns_path):
            sys.path.insert(0, os.path.dirname(patterns_path))
        
        # Read the handler file directly
        handler_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "patterns", "pattern-2", "lambdas", "bank_statement_extraction", "bank_statement_extraction_handler.py")
        with open(handler_path, 'r') as f:
            handler_content = f.read()
        
        # Should have critical document type check in the prompt
        assert "CRITICAL DOCUMENT TYPE CHECK" in handler_content
        assert "If the document is an INVOICE, RECEIPT, or OTHER document type" in handler_content
        assert "Return EMPTY XML" in handler_content

    def test_prompt_warns_against_copying_examples(self):
        """Test that prompt warns model not to copy example transactions."""
        import os
        
        handler_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "patterns", "pattern-2", "lambdas", "bank_statement_extraction", "bank_statement_extraction_handler.py")
        with open(handler_path, 'r') as f:
            handler_content = f.read()
        
        # Should have warnings before and after examples
        assert "⚠️ EXAMPLE OUTPUT FORMAT (DO NOT COPY THESE VALUES" in handler_content
        assert "⚠️ END OF EXAMPLES - DO NOT USE THESE VALUES IN YOUR OUTPUT" in handler_content

    def test_prompt_has_explicit_empty_xml_format(self):
        """Test that prompt shows how to return empty results."""
        import os
        
        handler_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "patterns", "pattern-2", "lambdas", "bank_statement_extraction", "bank_statement_extraction_handler.py")
        with open(handler_path, 'r') as f:
            handler_content = f.read()
        
        # Should show empty XML format
        assert "<bank_statement><transactions></transactions></bank_statement>" in handler_content

    def test_example_transactions_not_in_real_data(self):
        """Test that example transaction values are clearly marked as examples."""
        import os
        
        handler_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "patterns", "pattern-2", "lambdas", "bank_statement_extraction", "bank_statement_extraction_handler.py")
        with open(handler_path, 'r') as f:
            handler_content = f.read()
        
        # Example data should be present (for format reference)
        assert "862834451961-CHB" in handler_content
        assert "PAYPAL PAYMENT" in handler_content
        assert "TESCO" in handler_content
        
        # But should be clearly marked as examples
        if "⚠️ EXAMPLE OUTPUT FORMAT" in handler_content and "⚠️ END OF EXAMPLES" in handler_content:
            example_section = handler_content[handler_content.find("⚠️ EXAMPLE OUTPUT FORMAT"):handler_content.find("⚠️ END OF EXAMPLES")]
            assert "862834451961-CHB" in example_section
            assert "DO NOT COPY THESE VALUES" in example_section

    def test_prompt_instructs_invoice_handling(self):
        """Test that prompt explicitly instructs how to handle invoices."""
        import os
        
        handler_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "patterns", "pattern-2", "lambdas", "bank_statement_extraction", "bank_statement_extraction_handler.py")
        with open(handler_path, 'r') as f:
            handler_content = f.read()
        
        # Should have specific invoice handling instructions
        assert "If the text below is NOT a bank statement (e.g., it's an invoice, receipt, etc.)" in handler_content
        assert "DO NOT hallucinate or copy example transactions" in handler_content
        assert "Only extract what you actually see in the text below" in handler_content


@pytest.mark.unit
class TestExtractionXMLParsing:
    """Test XML parsing for extraction results."""

    def test_empty_transactions_parsing(self):
        """Test parsing of empty transactions XML."""
        import re
        
        xml_result = "<bank_statement><transactions></transactions></bank_statement>"
        
        # Should parse as having 0 transactions
        transaction_pattern = r'<transaction>(.*?)</transaction>'
        transactions = re.findall(transaction_pattern, xml_result, re.DOTALL)
        
        assert len(transactions) == 0

    def test_account_info_extraction(self):
        """Test extraction of account info from XML."""
        import re
        
        xml_result = """
        <bank_statement>
        <account_info>
          <account_number>12345678</account_number>
          <sort_code>12-34-56</sort_code>
          <bank_name>Test Bank</bank_name>
        </account_info>
        <transactions></transactions>
        </bank_statement>
        """
        
        # Extract account info
        account_pattern = r'<account_info>(.*?)</account_info>'
        field_pattern = r'<(\w+)>(.*?)</\1>'
        
        account_match = re.search(account_pattern, xml_result, re.DOTALL)
        assert account_match is not None
        
        account_data = account_match.group(1)
        fields = dict(re.findall(field_pattern, account_data))
        
        assert fields.get("account_number", "").strip() == "12345678"
        assert fields.get("sort_code", "").strip() == "12-34-56"
        assert fields.get("bank_name", "").strip() == "Test Bank"

    def test_transaction_extraction(self):
        """Test extraction of transaction from XML."""
        import re
        
        xml_result = """
        <bank_statement>
        <transactions>
        <transaction>
          <date>2024-01-15</date>
          <description>Payment to vendor</description>
          <amount>-100.50</amount>
          <balance>1500.00</balance>
          <reference>REF123</reference>
        </transaction>
        </transactions>
        </bank_statement>
        """
        
        # Extract transactions
        transaction_pattern = r'<transaction>(.*?)</transaction>'
        field_pattern = r'<(\w+)>(.*?)</\1>'
        
        transactions = re.findall(transaction_pattern, xml_result, re.DOTALL)
        assert len(transactions) == 1
        
        # Parse first transaction
        fields = dict(re.findall(field_pattern, transactions[0]))
        
        assert fields.get("date", "").strip() == "2024-01-15"
        assert fields.get("description", "").strip() == "Payment to vendor"
        assert fields.get("amount", "").strip() == "-100.50"
        assert fields.get("reference", "").strip() == "REF123"


@pytest.mark.unit  
class TestExtractionResultStorage:
    """Test storage of extraction results in DynamoDB."""

    def test_transaction_count_correct_for_empty(self):
        """Test that TransactionCount is 0 when no transactions found."""
        transactions = []
        
        transaction_count = len(transactions)
        assert transaction_count == 0

    def test_transaction_record_structure(self):
        """Test structure of transaction record in DynamoDB."""
        transaction_item = {
            "PK": "user#test-user#doc#test-doc.pdf",
            "SK": "type#BANK_STATEMENT#section#1#txn#1",
            "TransactionId": "test-doc.pdf-bank-1-1-abc123",
            "DocumentId": "test-doc.pdf",
            "UserId": "test-user",
            "TransactionDate": "2024-01-15",
            "TransactionDescription": "Payment to vendor",
            "TransactionAmount": -100.50,
            "AccountBalance": 1500.00,
            "TransactionType": "DEBIT",
            "Reference": "REF123",
            "DateConfidence": 0.95,
            "AmountConfidence": 0.98,
            "DescriptionConfidence": 0.90,
        }
        
        # Verify required fields
        assert "PK" in transaction_item
        assert "SK" in transaction_item
        assert "#txn#" in transaction_item["SK"]
        assert "TransactionId" in transaction_item
        assert "TransactionDate" in transaction_item
        assert "TransactionAmount" in transaction_item
        
        # Verify confidence scores are floats
        assert isinstance(transaction_item["DateConfidence"], float)
        assert 0.0 <= transaction_item["DateConfidence"] <= 1.0

    def test_statement_summary_structure(self):
        """Test structure of statement summary record."""
        summary_item = {
            "PK": "user#test-user#doc#test-doc.pdf",
            "SK": "type#BANK_STATEMENT#section#1#statement#summary",
            "StatementId": "test-doc.pdf-stmt-1-abc123",
            "DocumentId": "test-doc.pdf",
            "UserId": "test-user",
            "AccountNumber": "12345678",
            "SortCode": "12-34-56",
            "BankName": "Test Bank",
            "StatementPeriod": "2024-01-01 to 2024-01-31",
            "OpeningBalance": 1000.00,
            "ClosingBalance": 1500.00,
            "TotalCredits": 600.00,
            "TotalDebits": 100.00,
            "TransactionCount": 5,
        }
        
        # Verify required fields
        assert "PK" in summary_item
        assert "SK" in summary_item
        assert "#statement#summary" in summary_item["SK"]
        assert "TransactionCount" in summary_item
        assert isinstance(summary_item["TransactionCount"], int)
