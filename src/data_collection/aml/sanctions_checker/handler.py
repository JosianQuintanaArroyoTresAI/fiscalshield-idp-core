"""
OpenSanctions Data Collection Lambda Handler

Collects sanctions and PEP data from OpenSanctions API.
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
SECRET_NAME = os.environ.get('SECRET_NAME', 'fiscalshield-dc-dev-OpenSanctionsAPI')
DATA_ARCHIVE_BUCKET = os.environ.get('DATA_ARCHIVE_BUCKET')

# Cache configuration
CACHE_TTL_DAYS = 30  # Sanctions data changes slowly


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
    """Retrieve OpenSanctions API credentials from Secrets Manager."""
    try:
        response = secrets_client.get_secret_value(SecretId=SECRET_NAME)
        secret_string = response['SecretString']
        
        # Try to parse as JSON first
        try:
            credentials = json.loads(secret_string)
            if isinstance(credentials, dict):
                api_key = credentials.get('api_key') or credentials.get('api-key', '')
                if not api_key:
                    api_key = secret_string
            else:
                api_key = secret_string
        except json.JSONDecodeError:
            # If it's just a plain string, use it directly as the API key
            api_key = secret_string.strip()
        
        logger.info("Successfully retrieved OpenSanctions API credentials")
        return {
            'api_key': api_key,
            'base_url': 'https://api.opensanctions.org'
        }
    
    except Exception as e:
        logger.error(f"Failed to retrieve API credentials: {e}")
        raise


def check_cache(person_name: str, dob: Optional[str] = None, company_number: Optional[str] = None) -> Optional[Dict]:
    """Check if sanctions data exists in cache."""
    try:
        # If no company number provided, can't check cache
        if not company_number:
            logger.info(f"No company number provided, skipping cache check for: {person_name}")
            return None
        
        table = dynamodb.Table(CACHE_TABLE_NAME)
        
        # Sort key: SANCTIONS#PERSON#{name}#{dob}
        cache_key = f"SANCTIONS#PERSON#{person_name.upper().replace(' ', '_')}"
        if dob:
            cache_key += f"#{dob}"
        
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
                    logger.info(f"Cache hit for: {person_name} (company: {company_number})")
                    return item
        
        logger.info(f"Cache miss for: {person_name} (company: {company_number})")
        return None
    
    except Exception as e:
        logger.warning(f"Cache check failed (non-blocking): {e}")
        return None


def save_to_cache(person_name: str, api_response: Dict, dob: Optional[str] = None, company_number: Optional[str] = None, s3_archive: Optional[Dict] = None):
    """Save raw OpenSanctions API response to DynamoDB cache."""
    try:
        # If no company number provided, can't cache
        if not company_number:
            logger.warning(f"No company number provided, skipping cache for: {person_name}")
            return
        
        table = dynamodb.Table(CACHE_TABLE_NAME)
        
        cache_key = f"SANCTIONS#PERSON#{person_name.upper().replace(' ', '_')}"
        if dob:
            cache_key += f"#{dob}"
        
        now = datetime.now()
        ttl = int((now + timedelta(days=CACHE_TTL_DAYS)).timestamp())
        
        item = {
            'company_number': company_number,  # Use actual company number as PK
            'event_type_timestamp': cache_key,
            'person_name': person_name,
            'date_of_birth': dob,
            'timestamp': now.isoformat(),
            'last_updated': now.isoformat(),
            'ttl': ttl,
            'data_source': 'opensanctions',
            'data': api_response,  # Store raw API response as 'data' to match other entries
            's3_archive': s3_archive  # Store S3 location
        }
        
        table.put_item(Item=item)
        logger.info(f"Cached sanctions data for: {person_name} under company: {company_number} (TTL: {CACHE_TTL_DAYS} days)")
    
    except Exception as e:
        logger.warning(f"Failed to cache results (non-blocking): {e}")


def save_to_s3(person_name: str, api_response: Dict, dob: Optional[str] = None, company_number: Optional[str] = None):
    """Archive full API response to S3."""
    if not DATA_ARCHIVE_BUCKET:
        logger.warning("DATA_ARCHIVE_BUCKET not configured, skipping S3 archive")
        return None
    
    try:
        # Create S3 key
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        name_safe = person_name.replace(' ', '_').replace('/', '-')
        
        if company_number:
            s3_key = f"sanctions/{company_number}/{name_safe}/{timestamp}.json"
        else:
            s3_key = f"sanctions/standalone/{name_safe}/{timestamp}.json"
        
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


def search_opensanctions(person_name: str, credentials: Dict, dob: Optional[str] = None, limit: int = 20) -> Dict:
    """
    Search OpenSanctions API for a person.
    Returns raw API response.
    """
    try:
        base_url = credentials['base_url']
        api_key = credentials['api_key']
        
        # Search endpoint
        search_url = f"{base_url}/search/default"
        
        # Build query
        params = {
            'q': person_name,
            'limit': limit
        }
        
        headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        
        logger.info(f"Searching OpenSanctions for: {person_name}")
        response = requests.get(
            search_url,
            params=params,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        
        api_data = response.json()
        logger.info(f"OpenSanctions returned {len(api_data.get('results', []))} results")
        
        return api_data
    
    except requests.exceptions.RequestException as e:
        logger.error(f"OpenSanctions API error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise


def lambda_handler(event, context):
    """
    Lambda handler for OpenSanctions data collection.
    
    Expected input:
    {
        "person_name": "John Smith",
        "date_of_birth": "1980-01-01",  # Optional
        "company_number": "12345678"     # Optional - for context
    }
    
    Returns:
    {
        "success": true,
        "person_name": "John Smith",
        "date_of_birth": "1980-01-01",
        "company_number": "12345678",
        "cached": false,
        "collection_date": "2025-10-27T12:00:00",
        "total_results": 5,
        "api_response": { ... },  # Raw OpenSanctions response
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
        
        person_name = body.get('person_name')
        dob = body.get('date_of_birth')
        company_number = body.get('company_number')
        
        if not person_name:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'success': False,
                    'error': 'Missing required parameter: person_name'
                })
            }
        
        logger.info(f"Processing sanctions check for: {person_name}")
        
        # Check cache first
        cached_data = check_cache(person_name, dob, company_number)
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
                    'person_name': person_name,
                    'date_of_birth': dob,
                    'company_number': company_number,
                    'cached': True,
                    'collection_date': cached_data.get('last_updated') or cached_data.get('screening_date'),
                    'total_results': len(api_data.get('results', [])),
                    'api_response': api_data,
                    's3_archive': cached_data.get('s3_archive')
                })
            }
        
        # Get API credentials
        credentials = get_api_credentials()
        
        # Search OpenSanctions API
        api_response = search_opensanctions(person_name, credentials, dob)
        
        # Archive to S3
        s3_archive = save_to_s3(person_name, api_response, dob, company_number)
        
        # Prepare response
        result = {
            'success': True,
            'person_name': person_name,
            'date_of_birth': dob,
            'company_number': company_number,
            'cached': False,
            'collection_date': datetime.now().isoformat(),
            'total_results': len(api_response.get('results', [])),
            'api_response': api_response,
            's3_archive': s3_archive
        }
        
        # Cache the raw response including S3 location
        save_to_cache(person_name, api_response, dob, company_number, s3_archive)
        
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
