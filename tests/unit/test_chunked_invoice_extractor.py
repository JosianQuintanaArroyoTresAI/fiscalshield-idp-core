# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Unit tests for ChunkedInvoiceExtractor
"""

import pytest
from decimal import Decimal
from idp_common.extraction.chunked_invoice_extractor import ChunkedInvoiceExtractor


class TestChunkCreation:
    """Tests for chunk creation with overlap"""
    
    def test_create_chunks_basic(self):
        """Test that chunks are created with proper overlap"""
        extractor = ChunkedInvoiceExtractor(chunk_size=100, overlap_size=20)
        text = "A" * 250
        
        chunks = extractor.create_chunks_with_overlap(text)
        
        assert len(chunks) == 3  # 250 chars with 100 char chunks and 20 overlap
        assert chunks[0]['start'] == 0
        assert chunks[0]['end'] == 100
        assert chunks[1]['start'] == 80  # 100 - 20 overlap
        assert len(chunks[0]['chunk']) == 100
    
    def test_default_chunk_sizes(self):
        """Test that default chunk sizes are optimized (60k/5k)"""
        extractor = ChunkedInvoiceExtractor()
        
        assert extractor.chunk_size == 60000  # Optimized for Claude context
        assert extractor.overlap_size == 5000  # Covers 3-page invoices
    
    def test_extract_page_numbers(self):
        """Test page number extraction from markers"""
        extractor = ChunkedInvoiceExtractor()
        text = "[PAGE:1] Some text [PAGE:2] More text [PAGE:3] Even more"
        
        pages = extractor.extract_page_numbers(text)
        
        assert pages == [1, 2, 3]
    
    def test_extract_page_numbers_no_markers(self):
        """Test page extraction defaults to [1] when no markers"""
        extractor = ChunkedInvoiceExtractor()
        text = "No page markers here"
        
        pages = extractor.extract_page_numbers(text)
        
        assert pages == [1]


class TestDeduplication:
    """Tests for invoice deduplication logic"""
    
    def test_deduplicate_same_vendor_different_people(self):
        """Test that invoices from different people are NOT deduplicated"""
        extractor = ChunkedInvoiceExtractor()
        
        invoices = [
            {
                'supplier_name': 'Tesco',
                'total_amount': Decimal('15.50'),
                'invoice_date': '2025-01-01',
                'description': 'Employee: John Smith john@example.com',
                'pages': [1, 2]
            },
            {
                'supplier_name': 'Tesco',
                'total_amount': Decimal('15.50'),
                'invoice_date': '2025-01-01',
                'description': 'Employee: Jane Doe jane@example.com',
                'pages': [2, 3]
            }
        ]
        
        result = extractor.deduplicate_invoices(invoices)
        
        # Should keep both (different people)
        assert len(result) == 2
    
    def test_deduplicate_chunk_overlap(self):
        """Test that chunk overlap duplicates ARE removed"""
        extractor = ChunkedInvoiceExtractor()
        
        invoices = [
            {
                'supplier_name': 'Microsoft',
                'total_amount': Decimal('5.88'),
                'invoice_date': '2025-03-07',
                'invoice_number': 'GB-TI2500887574',
                'description': 'Microsoft 365 Business Basic',
                'pages': [2],
                'chunk_index': 0
            },
            {
                'supplier_name': 'Microsoft',
                'total_amount': Decimal('5.88'),
                'invoice_date': '2025-03-07',
                'invoice_number': 'GB-TI2500887574',
                'description': 'Microsoft 365 Business Basic',
                'pages': [2],
                'chunk_index': 1
            }
        ]
        
        result = extractor.deduplicate_invoices(invoices)
        
        # Should keep only one (duplicate from overlap)
        assert len(result) == 1
    
    def test_contains_different_people_with_emails(self):
        """Test people detection with different emails"""
        extractor = ChunkedInvoiceExtractor()
        
        desc1 = "Expense claim for John Smith (john@company.com)"
        desc2 = "Expense claim for Jane Doe (jane@company.com)"
        
        assert extractor.contains_different_people(desc1, desc2) is True
    
    def test_contains_different_people_with_names(self):
        """Test people detection with different names"""
        extractor = ChunkedInvoiceExtractor()
        
        desc1 = "Expense claim for John Smith"
        desc2 = "Expense claim for Jane Doe"
        
        assert extractor.contains_different_people(desc1, desc2) is True
    
    def test_no_different_people_same_person(self):
        """Test that same person is not flagged as different"""
        extractor = ChunkedInvoiceExtractor()
        
        desc1 = "Expense claim for John Smith (john@company.com)"
        desc2 = "Another expense for John Smith (john@company.com)"
        
        assert extractor.contains_different_people(desc1, desc2) is False
    
    def test_keep_more_complete_invoice(self):
        """Test that more complete invoice is kept during deduplication"""
        extractor = ChunkedInvoiceExtractor()
        
        # Invoice with all fields
        complete_invoice = {
            'supplier_name': 'Microsoft',
            'total_amount': Decimal('5.88'),
            'invoice_date': '2025-03-07',
            'invoice_number': 'GB-TI2500887574',
            'reference_number': 'REF-123',
            'description': 'Microsoft 365 Business Basic',
            'supplier_address': '123 Main St',
            'pages': [2]
        }
        
        # Invoice with fewer fields
        incomplete_invoice = {
            'supplier_name': 'Microsoft',
            'total_amount': Decimal('5.88'),
            'invoice_date': '2025-03-07',
            'pages': [2]
        }
        
        invoices = [incomplete_invoice, complete_invoice]
        result = extractor.deduplicate_invoices(invoices)
        
        # Should keep the complete one
        assert len(result) == 1
        assert result[0]['invoice_number'] == 'GB-TI2500887574'


class TestContentSimilarity:
    """Tests for content similarity detection"""
    
    def test_similar_content_match(self):
        """Test that matching content is detected"""
        extractor = ChunkedInvoiceExtractor()
        
        invoice1 = {
            'supplier_name': 'Microsoft',
            'total_amount': 5.88,
            'invoice_date': '2025-03-07',
            'description': 'Microsoft 365'
        }
        
        invoice2 = {
            'supplier_name': 'Microsoft',
            'total_amount': 5.88,
            'invoice_date': '2025-03-07',
            'description': 'Microsoft 365'
        }
        
        assert extractor.are_invoices_similar_content(invoice1, invoice2) is True
    
    def test_different_amounts_not_similar(self):
        """Test that different amounts are not similar"""
        extractor = ChunkedInvoiceExtractor()
        
        invoice1 = {
            'supplier_name': 'Microsoft',
            'total_amount': 5.88,
            'invoice_date': '2025-03-07'
        }
        
        invoice2 = {
            'supplier_name': 'Microsoft',
            'total_amount': 10.00,
            'invoice_date': '2025-03-07'
        }
        
        assert extractor.are_invoices_similar_content(invoice1, invoice2) is False
    
    def test_completeness_scoring(self):
        """Test invoice completeness scoring"""
        extractor = ChunkedInvoiceExtractor()
        
        complete = {
            'supplier_name': 'Microsoft',
            'invoice_number': 'INV-123',
            'reference_number': 'REF-456',
            'description': 'Some description',
            'supplier_address': '123 Main St'
        }
        
        incomplete = {
            'supplier_name': 'Microsoft',
            'invoice_number': 'INV-123'
        }
        
        assert extractor.is_more_complete_invoice(complete, incomplete) is True
        assert extractor.is_more_complete_invoice(incomplete, complete) is False
