# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Unit tests for SmartBatcher class
Tests invoice batching algorithm with various edge cases
"""

import pytest
from idp_common.classification.smart_batcher import SmartBatcher, InvoiceBoundary
from idp_common.models import Page


class TestInvoiceBoundary:
    """Test InvoiceBoundary helper class"""
    
    def test_invoice_boundary_creation(self):
        """Test creating an invoice boundary"""
        boundary = InvoiceBoundary(start_page=1, end_page=3)
        assert boundary.start_page == 1
        assert boundary.end_page == 3
        assert boundary.page_count == 3
    
    def test_single_page_invoice(self):
        """Test single-page invoice"""
        boundary = InvoiceBoundary(start_page=5, end_page=5)
        assert boundary.page_count == 1


class TestSmartBatcher:
    """Test SmartBatcher class"""
    
    def create_test_pages(self, page_configs):
        """
        Helper to create test pages with boundary metadata
        
        Args:
            page_configs: List of tuples (page_num, boundary, classification)
        """
        pages = {}
        for page_num, boundary, classification in page_configs:
            page_id = f"page-{page_num}"
            pages[page_id] = Page(
                page_id=page_id,
                page_number=page_num,
                classification=classification,
                confidence=0.95,
                metadata={'document_boundary': boundary}
            )
        return pages
    
    def test_single_invoice_batch(self):
        """Test batching with single invoice (1 page)"""
        pages = self.create_test_pages([
            (1, 'start', 'invoice'),
        ])
        
        batcher = SmartBatcher(target_pages_per_batch=10)
        sections = batcher.create_optimized_sections(pages, document_type='invoice')
        
        assert len(sections) == 1
        assert len(sections[0].page_ids) == 1
        assert sections[0].attributes['invoice_count'] == 1
    
    def test_exact_target_batch(self):
        """Test batching with exactly 10 single-page invoices"""
        page_configs = [(i, 'start', 'invoice') for i in range(1, 11)]
        pages = self.create_test_pages(page_configs)
        
        batcher = SmartBatcher(target_pages_per_batch=10)
        sections = batcher.create_optimized_sections(pages, document_type='invoice')
        
        assert len(sections) == 1
        assert len(sections[0].page_ids) == 10
        assert sections[0].attributes['invoice_count'] == 10
    
    def test_multiple_batches(self):
        """Test batching with 50 single-page invoices (should create 5 batches)"""
        page_configs = [(i, 'start', 'invoice') for i in range(1, 51)]
        pages = self.create_test_pages(page_configs)
        
        batcher = SmartBatcher(target_pages_per_batch=10)
        sections = batcher.create_optimized_sections(pages, document_type='invoice')
        
        assert len(sections) == 5
        for section in sections:
            assert len(section.page_ids) == 10
            assert section.attributes['invoice_count'] == 10
    
    def test_overage_allowed(self):
        """Test that 50% overage is allowed to include complete invoice"""
        # 9 single-page invoices + 1 two-page invoice = 11 pages total
        page_configs = [
            (1, 'start', 'invoice'),
            (2, 'start', 'invoice'),
            (3, 'start', 'invoice'),
            (4, 'start', 'invoice'),
            (5, 'start', 'invoice'),
            (6, 'start', 'invoice'),
            (7, 'start', 'invoice'),
            (8, 'start', 'invoice'),
            (9, 'start', 'invoice'),
            (10, 'start', 'invoice'),  # 2-page invoice starts
            (11, 'continue', 'invoice'),  # 2-page invoice continues
        ]
        pages = self.create_test_pages(page_configs)
        
        batcher = SmartBatcher(target_pages_per_batch=10)
        sections = batcher.create_optimized_sections(pages, document_type='invoice')
        
        # Should create 1 section with 11 pages (allows overage to include complete invoice)
        assert len(sections) == 1
        assert len(sections[0].page_ids) == 11
        assert sections[0].attributes['invoice_count'] == 10
    
    def test_new_batch_when_overage_too_large(self):
        """Test that new batch starts when overage exceeds 50%"""
        # 9 single-page invoices + 1 seven-page invoice = 16 pages (60% overage)
        page_configs = [
            (1, 'start', 'invoice'),
            (2, 'start', 'invoice'),
            (3, 'start', 'invoice'),
            (4, 'start', 'invoice'),
            (5, 'start', 'invoice'),
            (6, 'start', 'invoice'),
            (7, 'start', 'invoice'),
            (8, 'start', 'invoice'),
            (9, 'start', 'invoice'),
            (10, 'start', 'invoice'),  # 7-page invoice starts
            (11, 'continue', 'invoice'),
            (12, 'continue', 'invoice'),
            (13, 'continue', 'invoice'),
            (14, 'continue', 'invoice'),
            (15, 'continue', 'invoice'),
            (16, 'continue', 'invoice'),
        ]
        pages = self.create_test_pages(page_configs)
        
        batcher = SmartBatcher(target_pages_per_batch=10)
        sections = batcher.create_optimized_sections(pages, document_type='invoice')
        
        # Should create 2 sections: [9 pages] + [7 pages]
        assert len(sections) == 2
        assert len(sections[0].page_ids) == 9
        assert sections[0].attributes['invoice_count'] == 9
        assert len(sections[1].page_ids) == 7
        assert sections[1].attributes['invoice_count'] == 1
    
    def test_max_pages_enforced(self):
        """Test that max_pages_per_batch is enforced"""
        # Create 20 single-page invoices
        page_configs = [(i, 'start', 'invoice') for i in range(1, 21)]
        pages = self.create_test_pages(page_configs)
        
        batcher = SmartBatcher(target_pages_per_batch=10, max_pages_per_batch=15)
        sections = batcher.create_optimized_sections(pages, document_type='invoice')
        
        # Should create at least 2 sections
        assert len(sections) >= 2
        for section in sections:
            assert len(section.page_ids) <= 15
    
    def test_bank_statement_single_per_section(self):
        """Test that bank statements get 1 per section"""
        # Create 3 multi-page bank statements
        page_configs = [
            (1, 'start', 'bank-statement'),
            (2, 'continue', 'bank-statement'),
            (3, 'continue', 'bank-statement'),
            (4, 'start', 'bank-statement'),
            (5, 'continue', 'bank-statement'),
            (6, 'start', 'bank-statement'),
            (7, 'continue', 'bank-statement'),
            (8, 'continue', 'bank-statement'),
        ]
        pages = self.create_test_pages(page_configs)
        
        batcher = SmartBatcher(target_pages_per_batch=10)
        sections = batcher.create_optimized_sections(pages, document_type='bank-statement')
        
        # Should create 3 sections (1 per statement)
        assert len(sections) == 3
        assert len(sections[0].page_ids) == 3  # First statement: 3 pages
        assert len(sections[1].page_ids) == 2  # Second statement: 2 pages
        assert len(sections[2].page_ids) == 3  # Third statement: 3 pages
    
    def test_mixed_classifications(self):
        """Test with mixed document classifications"""
        page_configs = [
            (1, 'start', 'invoice'),
            (2, 'start', 'invoice'),
            (3, 'start', 'bank-statement'),
            (4, 'continue', 'bank-statement'),
            (5, 'start', 'invoice'),
        ]
        pages = self.create_test_pages(page_configs)
        
        batcher = SmartBatcher(target_pages_per_batch=10)
        sections = batcher.create_optimized_sections(pages, document_type='mixed')
        
        # Should handle gracefully (mixed documents typically classified separately)
        assert len(sections) >= 1
    
    def test_empty_pages(self):
        """Test with no pages"""
        pages = {}
        
        batcher = SmartBatcher(target_pages_per_batch=10)
        sections = batcher.create_optimized_sections(pages, document_type='invoice')
        
        assert len(sections) == 0
    
    def test_section_metadata(self):
        """Test that section metadata is correctly populated"""
        page_configs = [(i, 'start', 'invoice') for i in range(1, 6)]
        pages = self.create_test_pages(page_configs)
        
        batcher = SmartBatcher(target_pages_per_batch=10)
        sections = batcher.create_optimized_sections(pages, document_type='invoice')
        
        assert len(sections) == 1
        section = sections[0]
        
        # Verify metadata
        assert section.section_id == 'section-0'
        assert section.classification == 'invoice'
        assert section.confidence >= 0.95
        assert section.attributes is not None
        assert section.attributes['page_count'] == 5
        assert section.attributes['invoice_count'] == 5
        assert section.attributes['batching_strategy'] == 'smart'
        assert section.attributes['target_pages'] == 10


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
