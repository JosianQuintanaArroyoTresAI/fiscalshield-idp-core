"""
FiscalShield Analysis Stack - Placeholder Lambda Handler

This is a PLACEHOLDER implementation that returns mock data.
Replace with real risk assessment logic in Phase 2.
"""

import json
import os
from datetime import datetime

# Environment variables
INTELLIGENCE_TABLE_NAME = os.environ.get('INTELLIGENCE_TABLE_NAME')
COMPANY_EVENTS_TABLE = os.environ.get('COMPANY_EVENTS_TABLE')
FILING_EVENTS_TABLE = os.environ.get('FILING_EVENTS_TABLE')


def create_response(status_code, body):
    """Create API Gateway response"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'GET,OPTIONS'
        },
        'body': json.dumps(body)
    }


def lambda_handler(event, context):
    """
Lambda handler for Assess Company Intelligence endpoint

Calculates company risk based on data from Data Collection Stack
"""

import json
import logging
import os
import boto3
from datetime import datetime, timedelta
from decimal import Decimal

from risk_calculator import RiskCalculator

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')

# Get environment variables
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
COMPANY_INTELLIGENCE_TABLE = os.environ.get('COMPANY_INTELLIGENCE_TABLE')
DATA_COLLECTION_PREFIX = os.environ.get('DATA_COLLECTION_PREFIX', f'fiscalshield-dc-{ENVIRONMENT}')

# Data Collection Stack table names (convention-based)
COMPANY_EVENTS_TABLE = f"{DATA_COLLECTION_PREFIX}-CompanyEvents"
FILING_EVENTS_TABLE = f"{DATA_COLLECTION_PREFIX}-FilingEvents"

# Cache TTL in seconds (24 hours)
CACHE_TTL_SECONDS = 24 * 60 * 60


def lambda_handler(event, context):
    """
    Assess company intelligence based on collected data
    
    Process:
    1. Check if cached intelligence exists (age < 24h)
    2. If cached, return immediately
    3. If not cached, fetch data from Data Collection Stack
    4. Calculate risk using RiskCalculator
    5. Store results in CompanyIntelligenceTable
    6. Return intelligence data
    """
    try:
        # Extract company number from path
        company_number = event.get('pathParameters', {}).get('company_number')
        
        if not company_number:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'success': False,
                    'error': 'company_number is required'
                })
            }
        
        logger.info(f"Assessing company intelligence for: {company_number}")
        
        # Check for force refresh parameter
        query_params = event.get('queryStringParameters') or {}
        force_refresh = query_params.get('force_refresh', 'false').lower() == 'true'
        
        # Check cache first (unless force refresh)
        if not force_refresh:
            cached_intelligence = get_cached_intelligence(company_number)
            if cached_intelligence:
                logger.info(f"Returning cached intelligence for {company_number}")
                return {
                    'statusCode': 200,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps(cached_intelligence, default=decimal_default)
                }
        
        # Fetch data from Data Collection Stack
        logger.info(f"Fetching fresh data for {company_number}")
        company_data = fetch_company_data(company_number)
        
        if not company_data:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'success': False,
                    'error': 'No data found for company. Please gather company data first.'
                })
            }
        
        # Calculate risk
        calculator = RiskCalculator()
        risk_assessment = calculator.calculate_company_risk(company_data)
        
        # Build intelligence report
        intelligence = build_intelligence_report(company_number, company_data, risk_assessment)
        
        # Cache results in DynamoDB
        cache_intelligence(company_number, intelligence)
        
        logger.info(f"Successfully assessed {company_number}: Risk Level = {risk_assessment['risk_level']}")
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(intelligence, default=decimal_default)
        }
        
    except Exception as e:
        logger.error(f"Error assessing company intelligence: {str(e)}", exc_info=True)
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


def get_cached_intelligence(company_number: str):
    """Check if valid cached intelligence exists"""
    try:
        table = dynamodb.Table(COMPANY_INTELLIGENCE_TABLE)
        # Query for the most recent ASSESSMENT record
        response = table.query(
            KeyConditionExpression='company_number = :cn AND begins_with(intelligence_type_timestamp, :type)',
            ExpressionAttributeValues={
                ':cn': company_number,
                ':type': 'ASSESSMENT#'
            },
            ScanIndexForward=False,  # Most recent first
            Limit=1
        )
        
        if not response.get('Items'):
            return None
        
        item = response['Items'][0]
        
        # Check if cache is still valid
        cached_time = datetime.fromisoformat(item.get('calculation_timestamp', ''))
        age = datetime.now() - cached_time
        
        if age.total_seconds() < CACHE_TTL_SECONDS:
            logger.info(f"Cache hit for {company_number} (age: {age.total_seconds():.0f}s)")
            return item
        else:
            logger.info(f"Cache expired for {company_number} (age: {age.total_seconds():.0f}s)")
            return None
            
    except Exception as e:
        logger.warning(f"Error checking cache: {str(e)}")
        return None


def fetch_company_data(company_number: str) -> dict:
    """
    Fetch all collected data for a company from Data Collection Stack
    
    The Data Collection Stack stores data as separate records with event_type_timestamp as sort key:
    - COMPANY_INFO#YYYY-MM-DD
    - OFFICERS#YYYY-MM-DD
    - PSC#YYYY-MM-DD
    - CHARGES#YYYY-MM-DD
    - FILING_HISTORY#YYYY-MM-DD
    - INSOLVENCY#YYYY-MM-DD
    
    Returns:
        Dictionary with aggregated companies_house, sanctions, adverse_media data
    """
    try:
        # Fetch all events for this company
        company_events_table = dynamodb.Table(COMPANY_EVENTS_TABLE)
        response = company_events_table.query(
            KeyConditionExpression='company_number = :cn',
            ExpressionAttributeValues={':cn': company_number}
        )
        
        if not response.get('Items'):
            logger.warning(f"No data found in {COMPANY_EVENTS_TABLE} for {company_number}")
            return None
        
        items = response['Items']
        logger.info(f"Found {len(items)} data records for company {company_number}")
        
        # Aggregate data by event type
        company_info = None
        officers_data = None
        psc_data = None
        charges_data = None
        filing_history_data = None
        insolvency_data = None
        collection_timestamp = None
        
        for item in items:
            event_type = item.get('event_type_timestamp', '')
            data = item.get('data', {})
            timestamp = item.get('last_updated', '')
            
            if event_type.startswith('COMPANY_INFO'):
                company_info = data
                collection_timestamp = timestamp
            elif event_type.startswith('OFFICERS'):
                officers_data = data
            elif event_type.startswith('PSC'):
                psc_data = data
            elif event_type.startswith('CHARGES'):
                charges_data = data
            elif event_type.startswith('FILING_HISTORY'):
                filing_history_data = data
            elif event_type.startswith('INSOLVENCY'):
                insolvency_data = data
        
        if not company_info:
            logger.warning(f"No COMPANY_INFO found for {company_number}")
            return None
        
        # Build Companies House data structure
        companies_house_data = {
            'company_profile': company_info,
            'officers': officers_data or {},
            'psc': psc_data or {},
            'charges': charges_data or {},
            'filing_history': filing_history_data or {},
            'insolvency': insolvency_data or {}
        }
        
        # Extract flags from Companies House data
        companies_house_data['flags'] = extract_companies_house_flags(companies_house_data)
        
        # Build aggregated company data
        company_data = {
            'company_number': company_number,
            'companies_house': companies_house_data,
            'sanctions': [],  # TODO: Extract from officers screening
            'adverse_media': {},  # TODO: Extract from media screening
            'collection_timestamp': collection_timestamp or ''
        }
        
        return company_data
        
    except Exception as e:
        logger.error(f"Error fetching company data: {str(e)}", exc_info=True)
        return None


def extract_companies_house_flags(ch_data: dict) -> list:
    """
    Extract compliance flags from Companies House data
    
    Analyzes company profile, officers, charges, filings for risk indicators
    """
    flags = []
    
    company_profile = ch_data.get('company_profile', {})
    officers = ch_data.get('officers', {})
    charges = ch_data.get('charges', {})
    insolvency = ch_data.get('insolvency', {})
    
    # Check company status
    company_status = company_profile.get('company_status', '')
    if company_status in ['dissolved', 'liquidation', 'receivership', 'administration']:
        flags.append({
            'flag_type': 'company_status',
            'severity': 'high',
            'description': f'Company status: {company_status}',
            'source': 'company_profile'
        })
    elif company_status == 'voluntary-arrangement':
        flags.append({
            'flag_type': 'company_status',
            'severity': 'medium',
            'description': 'Company in voluntary arrangement',
            'source': 'company_profile'
        })
    
    # Check accounts overdue
    accounts = company_profile.get('accounts', {})
    if accounts.get('accounts_overdue'):
        flags.append({
            'flag_type': 'accounts_overdue',
            'severity': 'medium',
            'description': 'Accounts are overdue',
            'source': 'company_profile'
        })
    
    # Check confirmation statement overdue
    if company_profile.get('confirmation_statement_overdue'):
        flags.append({
            'flag_type': 'confirmation_statement_overdue',
            'severity': 'low',
            'description': 'Confirmation statement is overdue',
            'source': 'company_profile'
        })
    
    # Check insolvency
    if insolvency and insolvency.get('cases'):
        cases = insolvency.get('cases', [])
        for case in cases:
            flags.append({
                'flag_type': 'insolvency',
                'severity': 'critical',
                'description': f'Insolvency case found: {case.get("type", "unknown")}',
                'source': 'insolvency',
                'details': case
            })
    
    # Check outstanding charges
    outstanding_count = charges.get('outstanding_count', 0)
    if isinstance(outstanding_count, (int, float)) and outstanding_count > 5:
        flags.append({
            'flag_type': 'high_charge_count',
            'severity': 'low',
            'description': f'{outstanding_count} outstanding charges registered',
            'source': 'charges'
        })
    
    # Check for disqualified directors
    if officers.get('items'):
        for officer in officers.get('items', []):
            if officer.get('disqualifications'):
                flags.append({
                    'flag_type': 'disqualified_director',
                    'severity': 'high',
                    'description': f'Director {officer.get("name", "unknown")} has disqualifications',
                    'source': 'officers',
                    'details': officer
                })
    
    return flags


def build_intelligence_report(company_number: str, company_data: dict, risk_assessment: dict) -> dict:
    """Build comprehensive intelligence report"""
    
    ch_data = company_data.get('companies_house', {})
    sanctions_data = company_data.get('sanctions', [])
    media_data = company_data.get('adverse_media', {})
    
    # Extract key metrics
    company_profile = ch_data.get('company_profile', {})
    officers = ch_data.get('officers', {}).get('items', [])
    
    intelligence = {
        'success': True,
        'company_number': company_number,
        'company_name': company_profile.get('company_name', 'Unknown'),
        'calculation_timestamp': risk_assessment['calculation_timestamp'],
        'cache_expires_at': (datetime.now() + timedelta(seconds=CACHE_TTL_SECONDS)).isoformat(),
        
        # Risk Assessment (from RiskCalculator)
        'risk_assessment': {
            'overall_risk_score': risk_assessment['overall_risk_score'],
            'risk_level': risk_assessment['risk_level'],
            'summary': risk_assessment['summary'],
            'flags_summary': risk_assessment['flags_summary'],
            'critical_flags': risk_assessment['critical_flags'][:5],  # Top 5 critical
            'high_flags': risk_assessment['high_flags'][:5],  # Top 5 high
            'risk_factors_count': len(risk_assessment['risk_factors'])
        },
        
        # Governance
        'governance': {
            'total_officers': len(officers),
            'active_officers': len([o for o in officers if o.get('resigned_on') is None]),
            'director_stability': 'good' if len(officers) > 0 else 'unknown',
            'company_status': company_profile.get('company_status', 'unknown'),
            'company_type': company_profile.get('type', 'unknown')
        },
        
        # Financial
        'financial': {
            'filing_compliance': 'up_to_date',  # Could calculate from filing history
            'accounts_overdue': company_profile.get('accounts_overdue', False),
            'confirmation_statement_overdue': company_profile.get('confirmation_statement_overdue', False)
        },
        
        # Reputational
        'reputational': {
            'adverse_media_count': media_data.get('suspicious_articles_count', 0),
            'adverse_media_risk': media_data.get('risk_contribution', 0.0),
            'has_adverse_media': media_data.get('suspicious_articles_count', 0) > 0
        },
        
        # AML
        'aml': {
            'sanctions_screening': 'clear' if not risk_assessment['sanctioned_directors'] else 'matches_found',
            'sanctioned_directors': risk_assessment['sanctioned_directors'],
            'pep_screening': 'clear' if not risk_assessment['pep_directors'] else 'matches_found',
            'pep_directors': risk_assessment['pep_directors'],
            'requires_enhanced_dd': risk_assessment['risk_level'] == 'HIGH'
        },
        
        # Data freshness
        'data_collection_timestamp': company_data.get('collection_timestamp', ''),
        'data_age_hours': calculate_data_age_hours(company_data.get('collection_timestamp', ''))
    }
    
    return intelligence


def cache_intelligence(company_number: str, intelligence: dict):
    """Store intelligence data in DynamoDB with TTL"""
    try:
        table = dynamodb.Table(COMPANY_INTELLIGENCE_TABLE)
        
        # Convert floats to Decimal for DynamoDB
        intelligence_decimal = RiskCalculator.convert_to_dynamodb_format(intelligence)
        
        # Add composite key attributes
        intelligence_decimal['company_number'] = company_number
        intelligence_decimal['intelligence_type_timestamp'] = f"ASSESSMENT#{datetime.now().strftime('%Y-%m-%d')}"
        
        # Add TTL for automatic cleanup
        ttl = int((datetime.now() + timedelta(seconds=CACHE_TTL_SECONDS)).timestamp())
        intelligence_decimal['ttl'] = ttl
        
        # Add analysis_timestamp for GSI
        intelligence_decimal['analysis_timestamp'] = int(datetime.now().timestamp())
        
        table.put_item(Item=intelligence_decimal)
        logger.info(f"Cached intelligence for {company_number} (expires in 24h)")
        
    except Exception as e:
        logger.error(f"Error caching intelligence: {str(e)}", exc_info=True)


def calculate_data_age_hours(timestamp_str: str) -> float:
    """Calculate age of data in hours"""
    try:
        if not timestamp_str:
            return 999.0  # Unknown age
        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        age = datetime.now() - timestamp
        return age.total_seconds() / 3600
    except Exception:
        return 999.0


def decimal_default(obj):
    """JSON serializer for Decimal objects"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError
    print(f"Event: {json.dumps(event)}")
    
    # Extract company number from path parameters
    try:
        company_number = event['pathParameters']['company_number']
        if not company_number:
            return create_response(400, {'error': 'Company number is required'})
    except (KeyError, TypeError):
        return create_response(400, {'error': 'Company number is required in path'})
    
    print(f"Assessing company: {company_number}")
    
    # PLACEHOLDER: Return mock intelligence data
    # In real implementation, this will:
    # 1. Read from Data Collection DynamoDB tables
    # 2. Calculate risk scores
    # 3. Generate intelligence report
    # 4. Cache results in CompanyIntelligenceTable
    
    mock_intelligence = {
        'success': True,
        'company_number': company_number,
        'intelligence_type': 'OVERALL_RISK',
        'timestamp': datetime.now().isoformat(),
        'status': 'placeholder',
        'message': 'Analysis Stack deployed successfully. Real risk assessment coming in Phase 2.',
        
        # Mock risk assessment
        'risk_assessment': {
            'risk_score': 0.25,
            'risk_level': 'LOW',
            'risk_factors': {
                'sanctions_matches': 0,
                'pep_matches': 0,
                'director_turnover': 0,
                'filing_issues': 0,
                'adverse_media': 0
            },
            'recommendations': 'Standard CDD procedures sufficient (mock data)',
            'action_required': False
        },
        
        # Mock governance intelligence
        'governance': {
            'director_stability': 'good',
            'officer_turnover_rate': 0.0,
            'sanctioned_individuals': 0,
            'geographic_risk': 'low'
        },
        
        # Mock financial intelligence
        'financial': {
            'filing_compliance': 'up_to_date',
            'late_filings': 0,
            'accounts_status': 'current'
        },
        
        # Mock reputational intelligence
        'reputational': {
            'adverse_media_count': 0,
            'controversies': 0,
            'media_sentiment': 'neutral'
        },
        
        # Mock AML intelligence
        'aml': {
            'sanctions_screening': 'clear',
            'pep_connections': 'none',
            'high_risk_jurisdictions': 0
        },
        
        # Data sources
        'data_sources': {
            'companies_house': 'available (via Data Collection Stack)',
            'sanctions': 'available (via Data Collection Stack)',
            'media': 'available (via Data Collection Stack)'
        },
        
        # Configuration
        'config': {
            'intelligence_table': INTELLIGENCE_TABLE_NAME,
            'company_events_table': COMPANY_EVENTS_TABLE,
            'filing_events_table': FILING_EVENTS_TABLE
        }
    }
    
    return create_response(200, mock_intelligence)
