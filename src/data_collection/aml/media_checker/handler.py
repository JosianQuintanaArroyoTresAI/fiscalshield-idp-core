"""
NewsAPI/Brave Media Data Collection Lambda Handler with Nova Micro Analysis

GDPR-compliant adverse media screening with AI risk scoring.
- Collects news articles from NewsAPI (or Brave Search when migrated)
- Analyzes each article with AWS Bedrock Nova Micro (1-5 risk scale)
- Stores raw data in S3 for compliance (7-year retention)
- Stores analyzed articles in AdverseMediaArticlesTable
- Stores scan summaries in CompanyEventsTable
"""

import json
import os
import logging
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
import boto3
import requests

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# AWS Clients
dynamodb = boto3.resource('dynamodb')
secrets_client = boto3.client('secretsmanager')
s3_client = boto3.client('s3')
# Bedrock client must be in us-east-1 for cross-region inference profiles
bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')

# Environment variables
CACHE_TABLE_NAME = os.environ.get('CACHE_TABLE_NAME', 'fiscalshield-dc-dev-CompanyEvents')
ARTICLES_TABLE_NAME = os.environ.get('ARTICLES_TABLE_NAME', 'fiscalshield-dc-dev-AdverseMediaArticles')
SECRET_NAME = os.environ.get('SECRET_NAME', 'fiscalshield-dc-dev-NewsAPI')
DATA_ARCHIVE_BUCKET = os.environ.get('DATA_ARCHIVE_BUCKET')
# Nova Micro requires cross-region inference profile ARN
BEDROCK_MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'us.amazon.nova-micro-v1:0')
RISK_SCORE_SCALE = int(os.environ.get('RISK_SCORE_SCALE', '5'))
RETENTION_YEARS = int(os.environ.get('RETENTION_YEARS', '7'))

# Cache configuration
CACHE_TTL_DAYS = 7  # News scan summaries refresh weekly

# GDPR compliance metadata
GDPR_PURPOSE = "aml_adverse_media_screening"
GDPR_LAWFUL_BASIS = "legitimate_interest"
PROCESSING_VERSION = "v2.0"


def create_scan_id() -> str:
    """Generate unique scan ID."""
    return str(uuid.uuid4())


def hash_url(url: str) -> str:
    """Create hash of URL for article ID."""
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def get_api_credentials() -> Dict[str, str]:
    """Retrieve NewsAPI/Brave credentials from Secrets Manager."""
    try:
        response = secrets_client.get_secret_value(SecretId=SECRET_NAME)
        secret_string = response['SecretString']
        
        try:
            credentials = json.loads(secret_string)
            if isinstance(credentials, dict):
                api_key = credentials.get('api_key') or credentials.get('apiKey', '')
                base_url = credentials.get('base_url', 'https://newsapi.org/v2')
                if not api_key:
                    api_key = secret_string
            else:
                api_key = secret_string
                base_url = 'https://newsapi.org/v2'
        except json.JSONDecodeError:
            api_key = secret_string.strip()
            base_url = 'https://newsapi.org/v2'
        
        logger.info(f"Successfully retrieved API credentials (base: {base_url})")
        return {
            'api_key': api_key,
            'base_url': base_url
        }
    
    except Exception as e:
        logger.error(f"Failed to retrieve API credentials: {e}")
        raise


def analyze_article_with_nova(article: Dict, company_name: str) -> Dict:
    """
    Analyze article with Nova Micro for risk scoring.
    
    Returns:
    {
        "risk_score": 1-5,
        "risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
        "summary": "Brief explanation",
        "reasoning": "Detailed reasoning",
        "key_topics": ["topic1", "topic2"]
    }
    """
    try:
        title = article.get('title', '')
        description = article.get('description', '')
        content = article.get('content', '')[:500]  # Limit content to 500 chars
        
        # Build prompt for Nova Micro
        prompt = f"""Analyze this news article about {company_name} for adverse business impact.

Article Title: {title}
Description: {description}
Content Snippet: {content}

Rate the article on a scale of 1-{RISK_SCORE_SCALE}:
1 = Positive/neutral news
2 = Slightly negative
3 = Moderately negative
4 = Significantly negative (regulatory issues, investigations)
5 = Critically negative (fraud, major scandals, legal action)

Respond ONLY with valid JSON in this exact format:
{{
  "risk_score": <number 1-{RISK_SCORE_SCALE}>,
  "risk_level": "<LOW|MEDIUM|HIGH|CRITICAL>",
  "summary": "<one sentence explanation>",
  "reasoning": "<brief explanation of score>",
  "key_topics": ["<topic1>", "<topic2>"]
}}"""

        # Call Nova Micro via Bedrock
        body = json.dumps({
            "messages": [
                {
                    "role": "user",
                    "content": [{"text": prompt}]
                }
            ],
            "inferenceConfig": {
                "temperature": 0.1,  # Low temperature for consistency
                "maxTokens": 300
            }
        })
        
        response = bedrock_client.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            contentType='application/json',
            accept='application/json',
            body=body
        )
        
        response_body = json.loads(response['body'].read())
        nova_output = response_body['output']['message']['content'][0]['text']
        
        # Parse Nova's JSON response
        try:
            # Try to extract JSON from response (in case Nova adds text around it)
            json_start = nova_output.find('{')
            json_end = nova_output.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = nova_output[json_start:json_end]
                analysis = json.loads(json_str)
            else:
                analysis = json.loads(nova_output)
            
            # Validate and normalize
            risk_score = max(1, min(RISK_SCORE_SCALE, int(analysis.get('risk_score', 3))))
            
            # Map score to risk level if not provided
            if 'risk_level' not in analysis or not analysis['risk_level']:
                if risk_score >= 5:
                    risk_level = 'CRITICAL'
                elif risk_score >= 4:
                    risk_level = 'HIGH'
                elif risk_score >= 3:
                    risk_level = 'MEDIUM'
                else:
                    risk_level = 'LOW'
            else:
                risk_level = analysis.get('risk_level', 'MEDIUM')
            
            return {
                'risk_score': risk_score,
                'risk_level': risk_level,
                'summary': analysis.get('summary', 'Analysis completed'),
                'reasoning': analysis.get('reasoning', 'Automated risk assessment'),
                'key_topics': analysis.get('key_topics', [])
            }
            
        except json.JSONDecodeError as e:
            logger.warning(f"Nova returned non-JSON response: {nova_output[:200]}")
            # Fallback: neutral score
            return {
                'risk_score': 3,
                'risk_level': 'MEDIUM',
                'summary': 'Analysis failed - defaulted to neutral',
                'reasoning': f'JSON parse error: {str(e)}',
                'key_topics': []
            }
    
    except Exception as e:
        logger.error(f"Nova analysis failed: {e}")
        # Fallback: neutral score
        return {
            'risk_score': 3,
            'risk_level': 'MEDIUM',
            'summary': 'Analysis error - defaulted to neutral',
            'reasoning': f'Error: {str(e)}',
            'key_topics': []
        }


def search_news(company_name: str, credentials: Dict, days_back: int = 30) -> Dict:
    """
    Search NewsAPI for company articles.
    Returns raw API response.
    
    Note: When migrating to Brave, only this function needs to change.
    """
    try:
        base_url = credentials['base_url']
        api_key = credentials['api_key']
        
        # Calculate date range
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days_back)
        
        # NewsAPI endpoint
        search_url = f"{base_url}/everything"
        
        params = {
            'q': company_name,
            'from': from_date.strftime('%Y-%m-%d'),
            'to': to_date.strftime('%Y-%m-%d'),
            'sortBy': 'publishedAt',
            'language': 'en',
            'pageSize': 100,  # Max allowed by NewsAPI
            'apiKey': api_key
        }
        
        logger.info(f"Searching NewsAPI for: {company_name} ({days_back} days)")
        response = requests.get(
            search_url,
            params=params,
            timeout=30
        )
        response.raise_for_status()
        
        api_data = response.json()
        
        if api_data.get('status') != 'ok':
            raise Exception(f"NewsAPI error: {api_data.get('message', 'Unknown error')}")
        
        total_results = api_data.get('totalResults', 0)
        articles_count = len(api_data.get('articles', []))
        
        logger.info(f"NewsAPI found {total_results} total results, returned {articles_count} articles")
        
        return api_data
    
    except requests.exceptions.RequestException as e:
        logger.error(f"NewsAPI request error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise


def save_scan_to_s3(scan_id: str, company_number: str, company_name: str, 
                    raw_response: Dict, analyzed_articles: List[Dict]) -> Dict:
    """
    Save scan data to S3 for compliance.
    
    Returns S3 locations dictionary.
    """
    if not DATA_ARCHIVE_BUCKET:
        logger.warning("DATA_ARCHIVE_BUCKET not configured, skipping S3 archive")
        return {}
    
    try:
        date_str = datetime.now().strftime('%Y-%m-%d')
        scan_folder = f"adverse-media/{company_number}/scans/{scan_id}/"
        
        s3_locations = {}
        
        # 1. Save raw API response (immutable compliance record)
        raw_key = f"{scan_folder}raw-response.json"
        s3_client.put_object(
            Bucket=DATA_ARCHIVE_BUCKET,
            Key=raw_key,
            Body=json.dumps(raw_response, indent=2),
            ContentType='application/json',
            Metadata={
                'scan_id': scan_id,
                'company_number': company_number,
                'company_name': company_name,
                'scan_date': datetime.now().isoformat(),
                'gdpr_purpose': GDPR_PURPOSE
            }
        )
        s3_locations['raw_response'] = raw_key
        logger.info(f"Saved raw response: s3://{DATA_ARCHIVE_BUCKET}/{raw_key}")
        
        # 2. Save analyzed articles (with Nova scores)
        analyzed_key = f"{scan_folder}analyzed-articles.json"
        s3_client.put_object(
            Bucket=DATA_ARCHIVE_BUCKET,
            Key=analyzed_key,
            Body=json.dumps(analyzed_articles, indent=2),
            ContentType='application/json',
            Metadata={
                'scan_id': scan_id,
                'articles_count': str(len(analyzed_articles)),
                'processing_version': PROCESSING_VERSION
            }
        )
        s3_locations['analyzed_articles'] = analyzed_key
        logger.info(f"Saved analyzed articles: s3://{DATA_ARCHIVE_BUCKET}/{analyzed_key}")
        
        # 3. Save scan metadata
        metadata = {
            'scan_id': scan_id,
            'company_number': company_number,
            'company_name': company_name,
            'scan_date': datetime.now().isoformat(),
            'articles_count': len(analyzed_articles),
            'data_source': 'newsapi',
            'processing_version': PROCESSING_VERSION,
            'bedrock_model': BEDROCK_MODEL_ID,
            'gdpr_purpose': GDPR_PURPOSE,
            'lawful_basis': GDPR_LAWFUL_BASIS,
            'retention_until': (datetime.now() + timedelta(days=RETENTION_YEARS*365)).isoformat()
        }
        
        metadata_key = f"{scan_folder}scan-metadata.json"
        s3_client.put_object(
            Bucket=DATA_ARCHIVE_BUCKET,
            Key=metadata_key,
            Body=json.dumps(metadata, indent=2),
            ContentType='application/json'
        )
        s3_locations['metadata'] = metadata_key
        
        return {
            'bucket': DATA_ARCHIVE_BUCKET,
            'scan_folder': scan_folder,
            **s3_locations
        }
    
    except Exception as e:
        logger.error(f"Failed to save to S3: {e}")
        return {}


def save_article_to_dynamodb(company_number: str, article: Dict, 
                              analysis: Dict, scan_id: str, s3_location: str):
    """Save individual article to AdverseMediaArticlesTable."""
    try:
        table = dynamodb.Table(ARTICLES_TABLE_NAME)
        
        # Create article ID from URL hash + published date
        url_hash = hash_url(article.get('url', ''))
        published_at = article.get('publishedAt', datetime.now().isoformat())
        published_date = published_at[:10] if published_at else datetime.now().strftime('%Y-%m-%d')
        article_id = f"{url_hash}#{published_date}"
        
        # Calculate retention date (7 years from now)
        retention_date = datetime.now() + timedelta(days=RETENTION_YEARS*365)
        
        item = {
            'company_number': company_number,
            'article_id': article_id,
            
            # Article data
            'title': article.get('title', ''),
            'url': article.get('url', ''),
            'source': article.get('source', {}),
            'author': article.get('author', ''),
            'published_at': published_at,
            'description': article.get('description', ''),
            'content': article.get('content', ''),
            
            # Nova Micro analysis
            'risk_score': Decimal(str(analysis['risk_score'])),
            'risk_level': analysis['risk_level'],
            'nova_summary': analysis['summary'],
            'nova_reasoning': analysis['reasoning'],
            'key_topics': analysis.get('key_topics', []),
            
            # Scan context
            'scan_id': scan_id,
            'scan_date': datetime.now().isoformat(),
            'data_source': 'newsapi',
            
            # S3 reference
            's3_location': s3_location,
            
            # Compliance metadata
            'collected_at': datetime.now().isoformat(),
            'processed_at': datetime.now().isoformat(),
            'processing_version': PROCESSING_VERSION,
            'nova_model': BEDROCK_MODEL_ID,
            'gdpr_purpose': GDPR_PURPOSE,
            'gdpr_lawful_basis': GDPR_LAWFUL_BASIS,
            'retention_until': retention_date.isoformat(),
            
            # No TTL - keep for 7 years per compliance
            # 'ttl': null
            
            'version': 1,
            'last_updated': datetime.now().isoformat()
        }
        
        table.put_item(Item=item)
        logger.info(f"Saved article {article_id} to AdverseMediaArticlesTable")
    
    except Exception as e:
        logger.error(f"Failed to save article to DynamoDB: {e}")


def save_scan_summary_to_dynamodb(company_number: str, company_name: str,
                                   scan_id: str, analyzed_articles: List[Dict],
                                   s3_archive: Dict, days_searched: int):
    """Save scan summary to CompanyEventsTable."""
    try:
        table = dynamodb.Table(CACHE_TABLE_NAME)
        
        # Calculate risk statistics
        risk_scores = [a['analysis']['risk_score'] for a in analyzed_articles]
        high_risk = sum(1 for s in risk_scores if s >= 4)
        medium_risk = sum(1 for s in risk_scores if s == 3)
        low_risk = sum(1 for s in risk_scores if s <= 2)
        
        overall_risk_score = max(risk_scores) if risk_scores else 0
        weighted_risk_score = sum(risk_scores) / len(risk_scores) if risk_scores else 0
        
        # Determine overall risk level
        if overall_risk_score >= 5:
            risk_level = 'CRITICAL'
        elif overall_risk_score >= 4:
            risk_level = 'HIGH'
        elif overall_risk_score >= 3:
            risk_level = 'MEDIUM'
        else:
            risk_level = 'LOW'
        
        # Get top risk articles for quick access
        top_articles = sorted(
            analyzed_articles,
            key=lambda x: x['analysis']['risk_score'],
            reverse=True
        )[:10]
        
        top_risk_articles = [
            {
                'article_id': f"{hash_url(a['article'].get('url', ''))}#{a['article'].get('publishedAt', '')[:10]}",
                'title': a['article'].get('title', ''),
                'url': a['article'].get('url', ''),
                'risk_score': a['analysis']['risk_score'],
                'risk_level': a['analysis']['risk_level'],
                'summary': a['analysis']['summary']
            }
            for a in top_articles
        ]
        
        # Calculate cache TTL (7 days)
        now = datetime.now()
        ttl = int((now + timedelta(days=CACHE_TTL_DAYS)).timestamp())
        retention_date = now + timedelta(days=RETENTION_YEARS*365)
        
        item = {
            'company_number': company_number,
            'event_type_timestamp': f"MEDIA_SCAN#{now.isoformat()}",
            
            # Scan metadata
            'scan_id': scan_id,
            'scan_date': now.isoformat(),
            'scan_type': 'manual',
            'company_name': company_name,
            
            # Summary statistics
            'total_articles_found': len(analyzed_articles),
            'articles_analyzed': len(analyzed_articles),
            'high_risk_count': high_risk,
            'medium_risk_count': medium_risk,
            'low_risk_count': low_risk,
            
            # Risk assessment
            'overall_risk_score': Decimal(str(overall_risk_score)),
            'weighted_risk_score': Decimal(str(round(weighted_risk_score, 2))),
            'risk_level': risk_level,
            
            # Data lineage
            'data_source': 'newsapi',
            'processing_version': PROCESSING_VERSION,
            'nova_model': BEDROCK_MODEL_ID,
            'days_searched': days_searched,
            
            # Storage references
            's3_archive': s3_archive,
            'top_risk_articles': top_risk_articles,
            
            # Compliance fields
            'ttl': ttl,
            'retention_until': retention_date.isoformat(),
            'gdpr_purpose': GDPR_PURPOSE,
            'gdpr_lawful_basis': GDPR_LAWFUL_BASIS,
            'gdpr_consent_version': 'v1.0',
            
            'last_updated': now.isoformat(),
            'version': 1
        }
        
        table.put_item(Item=item)
        logger.info(f"Saved scan summary to CompanyEventsTable (scan_id: {scan_id})")
    
    except Exception as e:
        logger.error(f"Failed to save scan summary: {e}")


def lambda_handler(event, context):
    """
    Enhanced Lambda handler with Nova Micro analysis and two-table storage.
    
    Expected input:
    {
        "company_name": "Example Corp",
        "company_number": "12345678",
        "days_back": 30
    }
    
    Returns:
    {
        "success": true,
        "scan_id": "uuid-...",
        "company_number": "12345678",
        "scan_date": "2025-11-22T10:00:00Z",
        "total_articles": 15,
        "high_risk_count": 2,
        "medium_risk_count": 5,
        "low_risk_count": 8,
        "overall_risk_score": 4,
        "risk_level": "HIGH",
        "top_risk_articles": [...],
        "s3_archive": {...}
    }
    """
    try:
        # Parse input
        if isinstance(event, str):
            event = json.loads(event)
        
        if 'body' in event:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            body = event
        
        company_name = body.get('company_name')
        company_number = body.get('company_number')
        days_back = int(body.get('days_back') or body.get('days', 30))
        
        # Validation
        if not company_name or not company_number:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'success': False,
                    'error': 'Missing required parameters: company_name and company_number'
                })
            }
        
        if days_back < 1 or days_back > 365:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'success': False,
                    'error': 'days_back must be between 1 and 365'
                })
            }
        
        logger.info(f"Starting adverse media scan for {company_name} ({company_number})")
        
        # Generate scan ID
        scan_id = create_scan_id()
        
        # Get API credentials
        credentials = get_api_credentials()
        
        # Search for news articles
        raw_response = search_news(company_name, credentials, days_back)
        articles = raw_response.get('articles', [])
        
        if not articles:
            logger.info(f"No articles found for {company_name}")
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'success': True,
                    'scan_id': scan_id,
                    'company_number': company_number,
                    'total_articles': 0,
                    'message': 'No news articles found'
                })
            }
        
        # Analyze each article with Nova Micro
        logger.info(f"Analyzing {len(articles)} articles with Nova Micro...")
        analyzed_articles = []
        
        for idx, article in enumerate(articles):
            logger.info(f"Analyzing article {idx+1}/{len(articles)}")
            analysis = analyze_article_with_nova(article, company_name)
            analyzed_articles.append({
                'article': article,
                'analysis': analysis
            })
        
        # Save everything to S3 (compliance archive)
        s3_archive = save_scan_to_s3(
            scan_id, company_number, company_name,
            raw_response, analyzed_articles
        )
        
        # Save each article to AdverseMediaArticlesTable
        for analyzed in analyzed_articles:
            save_article_to_dynamodb(
                company_number,
                analyzed['article'],
                analyzed['analysis'],
                scan_id,
                s3_archive.get('scan_folder', '')
            )
        
        # Save scan summary to CompanyEventsTable
        save_scan_summary_to_dynamodb(
            company_number, company_name, scan_id,
            analyzed_articles, s3_archive, days_back
        )
        
        # Calculate response statistics
        risk_scores = [a['analysis']['risk_score'] for a in analyzed_articles]
        high_risk_count = sum(1 for s in risk_scores if s >= 4)
        medium_risk_count = sum(1 for s in risk_scores if s == 3)
        low_risk_count = sum(1 for s in risk_scores if s <= 2)
        overall_risk_score = max(risk_scores)
        
        if overall_risk_score >= 5:
            risk_level = 'CRITICAL'
        elif overall_risk_score >= 4:
            risk_level = 'HIGH'
        elif overall_risk_score >= 3:
            risk_level = 'MEDIUM'
        else:
            risk_level = 'LOW'
        
        # Get top risk articles for response
        top_articles = sorted(
            analyzed_articles,
            key=lambda x: x['analysis']['risk_score'],
            reverse=True
        )[:5]
        
        result = {
            'success': True,
            'scan_id': scan_id,
            'company_number': company_number,
            'company_name': company_name,
            'scan_date': datetime.now().isoformat(),
            'total_articles': len(analyzed_articles),
            'high_risk_count': high_risk_count,
            'medium_risk_count': medium_risk_count,
            'low_risk_count': low_risk_count,
            'overall_risk_score': overall_risk_score,
            'risk_level': risk_level,
            'top_risk_articles': [
                {
                    'title': a['article'].get('title'),
                    'url': a['article'].get('url'),
                    'source': a['article'].get('source', {}).get('name'),
                    'published_at': a['article'].get('publishedAt'),
                    'risk_score': a['analysis']['risk_score'],
                    'risk_level': a['analysis']['risk_level'],
                    'summary': a['analysis']['summary']
                }
                for a in top_articles
            ],
            's3_archive': s3_archive
        }
        
        logger.info(f"Scan complete: {high_risk_count} high risk, {medium_risk_count} medium risk, {low_risk_count} low risk")
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps(result)
        }
    
    except Exception as e:
        logger.error(f"Lambda execution failed: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'success': False,
                'error': str(e)
            })
        }
