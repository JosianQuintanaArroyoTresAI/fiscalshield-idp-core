# ⚠️ DO NOT USE FOR FISCALSHIELD

This configuration is for **academic research and general office documents** only.

## Why Not Use This?

- **Wrong classification method**: Uses holistic document analysis instead of page-level boundary detection
- **Wrong use case**: Designed for letters, forms, emails, memos - NOT for financial documents
- **Missing features**: Does not detect invoice boundaries in multi-invoice PDFs
- **Higher cost**: Uses Nova Pro instead of more cost-effective Claude Haiku

## What To Use Instead

✅ **Use `lending-package-sample`** for:
- Invoices (including multi-invoice packages)
- Bank statements
- Payslips
- W2 forms
- All financial documents

## History

This config was accidentally deployed to production on 2025-11-22, causing issues with multi-invoice document processing. It has been renamed and removed from allowed CloudFormation values to prevent future confusion.

**Last incident**: 101-page invoice only created 1 section instead of 6 invoices (resolved by switching to lending-package-sample)
