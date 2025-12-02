# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Smart Batching Module for Classification Results

Creates optimally-sized sections from classified pages by grouping complete
documents (invoices, statements, etc.) into cost-efficient batches.

Key Features:
- Groups only COMPLETE invoices into batches (no splitting mid-invoice)
- Configurable batch sizes per document type
- Flexible: adds page to batch if invoice fits, otherwise starts new batch
- Different strategies for invoices vs bank statements
"""

import logging
from typing import Dict, List, Any, Optional
from idp_common.models import Section, Page

logger = logging.getLogger(__name__)


class InvoiceBoundary:
    """Represents a single invoice with its page range."""
    
    def __init__(self, invoice_id: int, start_page: str, pages: List[str]):
        self.invoice_id = invoice_id
        self.start_page = start_page
        self.pages = pages  # List of page IDs
        self.end_page = pages[-1] if pages else start_page
        self.page_count = len(pages)
    
    def __repr__(self):
        return f"Invoice({self.invoice_id}, pages={self.pages})"


class SmartBatcher:
    """
    Creates optimally-sized sections from classified pages.
    
    Core Algorithm for Invoices:
    1. Detect invoice boundaries using document_boundary='start'/'continue'
    2. Group invoices into batches ensuring ALL invoices in batch are complete
    3. Target batch size (e.g., 10 pages), but adjust to include complete invoices
    
    Example:
      - Target: 10 pages
      - Page 10 ends invoice #3 → Batch = pages 1-10 (invoices #1-3)
      - Page 10 is mid-invoice #3 → Look ahead:
        * If invoice #3 ends at page 11 → Batch = pages 1-11 (complete)
        * If invoice #3 ends at page 15 → Batch = pages 1-9 (stop before #3)
    """
    
    def __init__(
        self,
        target_pages_per_batch: int = 10,
        max_pages_per_batch: int = 30,
        max_invoices_per_batch: int = 20,
        max_statements_per_batch: int = 1
    ):
        """
        Initialize SmartBatcher with configurable batch sizes.
        
        Args:
            target_pages_per_batch: Ideal number of pages per batch (flexible)
            max_pages_per_batch: Hard limit on pages per batch
            max_invoices_per_batch: Maximum invoices per batch
            max_statements_per_batch: Max bank statements per batch (usually 1)
        """
        self.target_pages_per_batch = target_pages_per_batch
        self.max_pages_per_batch = max_pages_per_batch
        self.max_invoices_per_batch = max_invoices_per_batch
        self.max_statements_per_batch = max_statements_per_batch
    
    def create_optimized_sections(
        self,
        pages: Dict[str, Page],
        document_type: Optional[str] = None
    ) -> List[Section]:
        """
        Create optimally-sized sections from classified pages.
        
        Args:
            pages: Dictionary of page_id -> Page objects
            document_type: Optional hint about document type
        
        Returns:
            List of Section objects optimized for parallel extraction
        """
        if not pages:
            return []
        
        # Sort pages by ID (assumes numeric or sortable IDs)
        sorted_pages = sorted(
            pages.values(),
            key=lambda p: int(p.page_id) if p.page_id.isdigit() else p.page_id
        )
        
        # Group pages by classification type first
        pages_by_type = {}
        for page in sorted_pages:
            doc_type = page.classification or 'unclassified'
            if doc_type not in pages_by_type:
                pages_by_type[doc_type] = []
            pages_by_type[doc_type].append(page)
        
        # Create sections for each document type
        all_sections = []
        
        for doc_type, type_pages in pages_by_type.items():
            if doc_type.lower() == 'invoice':
                sections = self._create_invoice_sections(type_pages)
            elif doc_type.lower() in ['bank-statement', 'bank_statement']:
                sections = self._create_statement_sections(type_pages)
            else:
                # Generic: create one section per document boundary
                sections = self._create_generic_sections(type_pages)
            
            all_sections.extend(sections)
        
        # Renumber sections sequentially
        for idx, section in enumerate(all_sections, start=1):
            section.section_id = str(idx)
        
        logger.info(
            f"Smart batching complete: {len(sorted_pages)} pages → "
            f"{len(all_sections)} sections"
        )
        
        return all_sections
    
    def _create_invoice_sections(self, pages: List[Page]) -> List[Section]:
        """
        Create invoice sections with smart batching logic.
        
        Algorithm:
        1. Detect all invoice boundaries
        2. Group invoices into batches targeting N pages
        3. Ensure each batch contains ONLY complete invoices
        4. Adjust batch size up/down to include complete invoices
        """
        # Step 1: Detect invoice boundaries
        invoices = self._detect_invoice_boundaries(pages)
        
        if not invoices:
            logger.warning("No invoice boundaries detected, creating single section")
            return [self._create_section_from_pages('invoice', pages, 1)]
        
        logger.info(f"Detected {len(invoices)} invoices in {len(pages)} pages")
        
        # Step 2: Smart batching - group invoices into optimal batches
        sections = []
        current_batch_invoices = []
        current_batch_pages = 0
        
        for invoice in invoices:
            invoice_page_count = invoice.page_count
            
            # Calculate what the batch would be if we add this invoice
            potential_batch_pages = current_batch_pages + invoice_page_count
            potential_batch_invoice_count = len(current_batch_invoices) + 1
            
            # Decision logic: Should we add this invoice to current batch?
            should_add_to_current = self._should_add_invoice_to_batch(
                current_batch_pages=current_batch_pages,
                current_batch_invoice_count=len(current_batch_invoices),
                invoice_page_count=invoice_page_count,
                potential_batch_pages=potential_batch_pages,
                potential_batch_invoice_count=potential_batch_invoice_count
            )
            
            if should_add_to_current:
                # Add to current batch
                current_batch_invoices.append(invoice)
                current_batch_pages += invoice_page_count
            else:
                # Flush current batch and start new one
                if current_batch_invoices:
                    section = self._create_section_from_invoices(
                        current_batch_invoices,
                        len(sections) + 1
                    )
                    sections.append(section)
                    
                    logger.info(
                        f"Created section {section.section_id}: "
                        f"{len(current_batch_invoices)} invoices, "
                        f"{current_batch_pages} pages"
                    )
                
                # Start new batch with this invoice
                current_batch_invoices = [invoice]
                current_batch_pages = invoice_page_count
        
        # Don't forget the final batch!
        if current_batch_invoices:
            section = self._create_section_from_invoices(
                current_batch_invoices,
                len(sections) + 1
            )
            sections.append(section)
            
            logger.info(
                f"Created section {section.section_id} (final): "
                f"{len(current_batch_invoices)} invoices, "
                f"{current_batch_pages} pages"
            )
        
        return sections
    
    def _should_add_invoice_to_batch(
        self,
        current_batch_pages: int,
        current_batch_invoice_count: int,
        invoice_page_count: int,
        potential_batch_pages: int,
        potential_batch_invoice_count: int
    ) -> bool:
        """
        Decide whether to add an invoice to the current batch.
        
        Logic:
        - If batch is empty, always add (start new batch)
        - If adding would exceed hard limits, don't add
        - If batch hasn't reached target and adding doesn't exceed limits, add
        - If batch has reached target, start new batch
        
        This implements your requirement:
        - Page 10 has complete invoice → batch includes it (up to 10 pages)
        - Page 10 is mid-invoice → look at page 11:
          * If invoice ends at 11 → include up to 11
          * If invoice is huge → stop at page 9 (before incomplete invoice)
        """
        # Empty batch - always add first invoice
        if current_batch_invoice_count == 0:
            return True
        
        # Check hard limits
        if potential_batch_invoice_count > self.max_invoices_per_batch:
            return False
        
        if potential_batch_pages > self.max_pages_per_batch:
            return False
        
        # If we're under target, add the invoice
        if current_batch_pages < self.target_pages_per_batch:
            return True
        
        # We're at or above target
        # Decision: Would adding this invoice get us closer to target or farther?
        
        # If adding this invoice keeps us reasonably close to target, add it
        # Example: target=10, current=9, invoice=2 pages → total=11 (close, add it)
        # Example: target=10, current=9, invoice=10 pages → total=19 (too far, don't add)
        
        overage_if_added = potential_batch_pages - self.target_pages_per_batch
        
        # Allow up to 50% overage to include complete invoices
        max_allowed_overage = self.target_pages_per_batch * 0.5
        
        if overage_if_added <= max_allowed_overage:
            return True
        
        # Would exceed reasonable overage - start new batch
        return False
    
    def _detect_invoice_boundaries(self, pages: List[Page]) -> List[InvoiceBoundary]:
        """
        Detect invoice boundaries from page metadata.
        
        Returns list of InvoiceBoundary objects, each representing one complete invoice.
        """
        invoices = []
        current_invoice = None
        
        for page in pages:
            boundary = page.metadata.get('document_boundary', 'continue').lower()
            
            if boundary == 'start':
                # Save previous invoice if exists
                if current_invoice:
                    invoices.append(current_invoice)
                
                # Start new invoice
                current_invoice = InvoiceBoundary(
                    invoice_id=len(invoices) + 1,
                    start_page=page.page_id,
                    pages=[page.page_id]
                )
            elif current_invoice:
                # Continue current invoice
                current_invoice.pages.append(page.page_id)
            else:
                # First page but no 'start' boundary - assume it's the start
                logger.warning(
                    f"Page {page.page_id} has boundary='continue' but no "
                    f"invoice started yet. Creating new invoice."
                )
                current_invoice = InvoiceBoundary(
                    invoice_id=len(invoices) + 1,
                    start_page=page.page_id,
                    pages=[page.page_id]
                )
        
        # Don't forget final invoice!
        if current_invoice:
            invoices.append(current_invoice)
        
        return invoices
    
    def _create_statement_sections(self, pages: List[Page]) -> List[Section]:
        """
        Create bank statement sections.
        
        Strategy: Each statement gets its own section (statements can be long).
        """
        sections = []
        current_statement_pages = []
        
        for page in pages:
            boundary = page.metadata.get('document_boundary', 'continue').lower()
            
            if boundary == 'start' and current_statement_pages:
                # Save previous statement as section
                section = self._create_section_from_pages(
                    'bank-statement',
                    current_statement_pages,
                    len(sections) + 1
                )
                sections.append(section)
                current_statement_pages = [page]
            else:
                current_statement_pages.append(page)
        
        # Final statement
        if current_statement_pages:
            section = self._create_section_from_pages(
                'bank-statement',
                current_statement_pages,
                len(sections) + 1
            )
            sections.append(section)
        
        return sections
    
    def _create_generic_sections(self, pages: List[Page]) -> List[Section]:
        """
        Create sections for other document types.
        
        Strategy: One section per document (based on boundary='start').
        """
        sections = []
        current_pages = []
        doc_type = pages[0].classification if pages else 'unknown'
        
        for page in pages:
            boundary = page.metadata.get('document_boundary', 'continue').lower()
            
            if boundary == 'start' and current_pages:
                section = self._create_section_from_pages(
                    doc_type,
                    current_pages,
                    len(sections) + 1
                )
                sections.append(section)
                current_pages = [page]
            else:
                current_pages.append(page)
        
        # Final section
        if current_pages:
            section = self._create_section_from_pages(
                doc_type,
                current_pages,
                len(sections) + 1
            )
            sections.append(section)
        
        return sections
    
    def _create_section_from_invoices(
        self,
        invoices: List[InvoiceBoundary],
        section_id: int
    ) -> Section:
        """Create a Section from a list of invoices."""
        all_page_ids = []
        for invoice in invoices:
            all_page_ids.extend(invoice.pages)
        
        return Section(
            section_id=str(section_id),
            classification='invoice',
            confidence=1.0,
            page_ids=all_page_ids,
            attributes={
                'invoice_count': len(invoices),
                'invoice_ids': [inv.invoice_id for inv in invoices],
                'page_count': len(all_page_ids),
                'batching_strategy': 'smart_complete_invoice_batching',
                'batching_config': {
                    'target_pages': self.target_pages_per_batch,
                    'max_pages': self.max_pages_per_batch,
                    'max_invoices': self.max_invoices_per_batch
                }
            }
        )
    
    def _create_section_from_pages(
        self,
        classification: str,
        pages: List[Page],
        section_id: int
    ) -> Section:
        """Create a Section from a list of Page objects."""
        return Section(
            section_id=str(section_id),
            classification=classification,
            confidence=1.0,
            page_ids=[p.page_id for p in pages],
            attributes={
                'page_count': len(pages),
                'batching_strategy': 'document_boundary_based'
            }
        )
