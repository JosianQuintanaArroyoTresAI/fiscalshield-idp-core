"""
OpenSanctions Sanctions & PEP Checker Lambda

Screens individuals against sanctions lists and PEP databases using OpenSanctions API.
Results are cached in DynamoDB with 30-day TTL.
"""
