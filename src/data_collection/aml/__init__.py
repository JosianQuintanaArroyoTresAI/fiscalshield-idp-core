"""
AML (Anti-Money Laundering) Data Collection Module

This module contains Lambda functions for collecting AML-related data:
- Sanctions/PEP screening (OpenSanctions API)
- Adverse media screening (NewsAPI)

Data is cached in DynamoDB and S3 for compliance and audit purposes.
"""

__version__ = "1.0.0"
