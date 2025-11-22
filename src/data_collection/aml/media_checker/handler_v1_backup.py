"""
NewsAPI Media Data Collection Lambda Handler

Collects news articles about companies from NewsAPI.
Stores raw API responses for later analysis.

This is the DATA COLLECTION layer - no analysis/scoring here.
Analysis happens in the Analysis Stack.
"""

import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
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

# Environment variables
CACHE_TABLE_NAME = os.environ.get('CACHE_TABLE_NAME', 'fiscalshield-dc-dev-CompanyEvents')
SECRET_NAME = os.environ.get('SECRET_NAME', 'fiscalshield-dc-dev-NewsAPI')
DATA_ARCHIVE_BUCKET = os.environ.get('DATA_ARCHIVE_BUCKET')

# Cache configuration
CACHE_TTL_DAYS = 7  # News data refreshes weekly


class DecimalEncoder(json.JSONEncoder):
    """Helper class to convert Decimal objects to float for JSON serialization.
    
    DynamoDB returns numeric values as Decimal objects, which can't be directly
    serialized to JSON. This encoder converts them to float.
    """
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


def convert_decimals(obj):
    """Recursively convert Decimal objects to float in nested structures."""
    if isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_decimals(value) for key, value in obj.items()}
    elif isinstance(obj, Decimal):
        return float(obj)
    else:
        return obj


def get_api_credentials() -> Dict[str, str]:
    """Retrieve NewsAPI credentials from Secrets Manager."""
    try:
        response = secrets_client.get_secret_value(SecretId=SECRET_NAME)
        secret_string = response['SecretString']
        
        # Try to parse as JSON first
        try:
            credentials = json.loads(secret_string)
            if isinstance(credentials, dict):
                api_key = credentials.get('api_key') or credentials.get('apiKey', '')
                if not api_key:
                    api_key = secret_string
            else:
                api_key = secret_string
        except json.JSONDecodeError:
            # If it's just a plain string, use it directly as the API key
            api_key = secret_string.strip()
        
        logger.info("Successfully retrieved NewsAPI credentials")
        return {
            'api_key': api_key,
            'base_url': 'https://newsapi.org/v2'
        }
    
    except Exception as e:
        logger.error(f"Failed to retrieve API credentials: {e}")
        raise


def check_cache(company_name: str, days_back: int = 30, company_number: Optional[str] = None) -> Optional[Dict]:
    """Check if media data exists in cache."""
    try:
        # If no company number provided, can't check cache
        if not company_number:
            logger.info(f"No company number provided, skipping cache check for: {company_name}")
            return None
        
        table = dynamodb.Table(CACHE_TABLE_NAME)
        
        # Sort key: MEDIA#COMPANY#{name}#DAYS_{days}
        cache_key = f"MEDIA#COMPANY#{company_name.upper().replace(' ', '_')}#DAYS_{days_back}"
        
        response = table.get_item(
            Key={
                'company_number': company_number,
                'event_type_timestamp': cache_key
            }
        )
        
        if 'Item' in response:
            # Check if cache is still valid (TTL not expired)
            item = response['Item']
            if 'ttl' in item:
                if datetime.now().timestamp() < item['ttl']:
                    logger.info(f"Cache hit for: {company_name} (company: {company_number})")
                    return item
        
        logger.info(f"Cache miss for: {company_name} (company: {company_number})")
        return None
    
    except Exception as e:
        logger.warning(f"Cache check failed (non-blocking): {e}")
        return None


def save_to_cache(company_name: str, api_response: Dict, days_back: int = 30, company_number: Optional[str] = None, s3_archive: Optional[Dict] = None):
    """Save raw NewsAPI response to DynamoDB cache."""
    try:
        # If no company number provided, can't cache
        if not company_number:
            logger.warning(f"No company number provided, skipping cache for: {company_name}")
            return
        
        table = dynamodb.Table(CACHE_TABLE_NAME)
        
        cache_key = f"MEDIA#COMPANY#{company_name.upper().replace(' ', '_')}#DAYS_{days_back}"
        
        now = datetime.now()
        ttl = int((now + timedelta(days=CACHE_TTL_DAYS)).timestamp())
        
        item = {
            'company_number': company_number,  # Use actual company number as PK
            'event_type_timestamp': cache_key,
            'company_name': company_name,
            'days_searched': days_back,
            'timestamp': now.isoformat(),
            'last_updated': now.isoformat(),
            'ttl': ttl,
            'data_source': 'newsapi',
            'data': api_response,  # Store raw API response as 'data' to match other entries
            's3_archive': s3_archive  # Store S3 location
        }
        
        table.put_item(Item=item)
        logger.info(f"Cached media data for: {company_name} under company: {company_number} (TTL: {CACHE_TTL_DAYS} days)")
    
    except Exception as e:
        logger.warning(f"Failed to cache results (non-blocking): {e}")


def save_to_s3(company_name: str, api_response: Dict, company_number: Optional[str] = None):
    """Archive full API response to S3."""
    if not DATA_ARCHIVE_BUCKET:
        logger.warning("DATA_ARCHIVE_BUCKET not configured, skipping S3 archive")
        return None
    
    try:
        # Create S3 key
        date_str = datetime.now().strftime('%Y-%m-%d')
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        name_safe = company_name.replace(' ', '_').replace('/', '-')
        
        if company_number:
            s3_key = f"adverse-media/{company_number}/{name_safe}/{timestamp}.json"
        else:
            s3_key = f"adverse-media/standalone/{name_safe}/{timestamp}.json"
        
        # Upload to S3
        s3_client.put_object(
            Bucket=DATA_ARCHIVE_BUCKET,
            Key=s3_key,
            Body=json.dumps(api_response, indent=2),
            ContentType='application/json'
        )
        
        logger.info(f"Archived to S3: s3://{DATA_ARCHIVE_BUCKET}/{s3_key}")
        return {
            'bucket': DATA_ARCHIVE_BUCKET,
            'key': s3_key,
            'timestamp': timestamp
        }
    
    except Exception as e:
        logger.error(f"Failed to archive to S3: {e}")
        return None


def search_news(company_name: str, credentials: Dict, days_back: int = 30) -> Dict:
    """
    Search NewsAPI for company articles.
    Returns raw API response.
    """
    try:
        base_url = credentials['base_url']
        api_key = credentials['api_key']
        
        # Calculate date range
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days_back)
        
        # Everything endpoint
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


def lambda_handler(event, context):
    """
    Lambda handler for NewsAPI media data collection.
    
    Expected input:
    {
        "company_name": "Example Corp",
        "company_number": "12345678",  # Optional - for context
        "days_back": 30                # Optional, default 30
    }
    
    Returns:
    {
        "success": true,
        "company_name": "Example Corp",
        "company_number": "12345678",
        "cached": false,
        "collection_date": "2025-10-27T12:00:00",
        "days_searched": 30,
        "total_results": 150,
        "articles_returned": 100,
        "api_response": { ... },  # Raw NewsAPI response
        "s3_archive": {
            "bucket": "...",
            "key": "...",
            "timestamp": "..."
        }
    }
    """
    try:
        # Parse input
        if isinstance(event, str):
            event = json.loads(event)
        
        # Handle API Gateway event
        if 'body' in event:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            body = event
        
        company_name = body.get('company_name')
        company_number = body.get('company_number')
        # Accept both 'days_back' and 'days' for backwards compatibility
        days_back = int(body.get('days_back') or body.get('days', 30))
        
        # Log the company_number to help debug
        logger.info(f"Received company_number: {company_number}")
        
        if not company_name:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'success': False,
                    'error': 'Missing required parameter: company_name'
                })
            }
        
        if not company_number:
            logger.warning(f"No company_number provided for media search of: {company_name}")
            logger.warning("This will prevent caching. Please ensure company_number is passed in the payload.")
        
        # Validate days_back
        if days_back < 1 or days_back > 365:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'success': False,
                    'error': 'days_back must be between 1 and 365'
                })
            }
        
        logger.info(f"Processing media search for: {company_name} ({days_back} days)")
        
        # Check cache first
        cached_data = check_cache(company_name, days_back, company_number)
        if cached_data:
            # Convert Decimals before serialization
            cached_data = convert_decimals(cached_data)
            
            # Support both old 'api_response' and new 'data' fields
            api_data = cached_data.get('data') or cached_data.get('api_response', {})
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'success': True,
                    'company_name': company_name,
                    'company_number': company_number,
                    'cached': True,
                    'collection_date': cached_data.get('last_updated') or cached_data.get('collection_date'),
                    'days_searched': days_back,
                    'total_results': api_data.get('totalResults', 0),
                    'articles_returned': len(api_data.get('articles', [])),
                    'api_response': api_data,
                    's3_archive': cached_data.get('s3_archive')
                })
            }
        
        # Get API credentials
        credentials = get_api_credentials()
        
        # Search NewsAPI
        api_response = search_news(company_name, credentials, days_back)
        
        # Archive to S3
        s3_archive = save_to_s3(company_name, api_response, company_number)
        
        # Prepare response
        result = {
            'success': True,
            'company_name': company_name,
            'company_number': company_number,
            'cached': False,
            'collection_date': datetime.now().isoformat(),
            'days_searched': days_back,
            'total_results': api_response.get('totalResults', 0),
            'articles_returned': len(api_response.get('articles', [])),
            'api_response': api_response,
            's3_archive': s3_archive
        }
        
        # Cache the raw response including S3 location
        save_to_cache(company_name, api_response, days_back, company_number, s3_archive)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(result)
        }
    
    except Exception as e:
        logger.error(f"Lambda execution failed: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': False,
                'error': str(e)
            })
        }
