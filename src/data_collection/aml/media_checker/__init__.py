"""
NewsAPI Adverse Media Checker Lambda

Searches for negative news articles about companies and individuals.
Results are stored in S3 (full articles) and DynamoDB (summary) with 7-day TTL.
"""
