"""
Transaction Categorization Lambda
Analyzes bank transactions using Claude for expense categorization and risk scoring.
Adapted from PoC for IDP Core ExtractionResultsTable.
"""

import re
import json
import boto3
import time
import os
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Any, Optional
from pathlib import Path

def log_with_timestamp(message):
    """Helper function to log messages with timestamps"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    print(f"[{timestamp}] {message}")

# Load high-risk countries list at module level (cold start)
HIGH_RISK_COUNTRIES = {}
try:
    countries_file = Path(__file__).parent / 'high_risk_countries.json'
    with open(countries_file, 'r') as f:
        country_data = json.load(f)
        HIGH_RISK_COUNTRIES = country_data.get('countries', {})
        log_with_timestamp(f"✅ Loaded {len(HIGH_RISK_COUNTRIES)} high-risk countries from {country_data.get('version', 'unknown version')}")
except Exception as e:
    log_with_timestamp(f"⚠️ Could not load high-risk countries list: {e}")
    HIGH_RISK_COUNTRIES = {}


# ==============================================================================
# HMRC Compliance Risk Checking Functions
# ==============================================================================

def normalize_country_code(country: str) -> str:
    """Normalize country code to ISO3 format for lookup."""
    if not country or country == 'UNKNOWN':
        return ''
    
    country_upper = country.strip().upper()
    
    # Common aliases
    aliases = {
        'UK': 'GBR',
        'USA': 'USA',
        'US': 'USA', 
        'UNITED KINGDOM': 'GBR',
        'UNITED STATES': 'USA',
        'RUSSIA': 'RUS',
        'NORTH KOREA': 'PRK'
    }
    
    if country_upper in aliases:
        return aliases[country_upper]
    
    # If already ISO3 (3 letters), return as-is
    if len(country_upper) == 3 and country_upper.isalpha():
        return country_upper
    
    # If ISO2 (2 letters), try to find in our list
    if len(country_upper) == 2 and country_upper.isalpha():
        for code, data in HIGH_RISK_COUNTRIES.items():
            if data.get('iso2') == country_upper:
                return code
    
    return country_upper


def check_threshold_breach(amount: float) -> Dict[str, Any]:
    """
    Check if transaction breaches MLR 2017 threshold reporting requirements.
    
    Returns:
        {
            'flag': 'NONE' | 'HVD_10K' | 'GENERAL_15K',
            'threshold_value': int,
            'description': str
        }
    """
    abs_amount = abs(amount)
    
    if abs_amount >= 15000:
        return {
            'flag': 'GENERAL_15K',
            'threshold_value': 15000,
            'description': f'Transaction £{abs_amount:,.2f} exceeds £15,000 threshold (MLR 2017 Reg 33)'
        }
    elif abs_amount >= 10000:
        return {
            'flag': 'HVD_10K',
            'threshold_value': 10000,
            'description': f'Transaction £{abs_amount:,.2f} exceeds £10,000 HVD threshold (MLR 2017 Reg 39)'
        }
    else:
        return {
            'flag': 'NONE',
            'threshold_value': 0,
            'description': ''
        }


def check_cash_risk(amount: float, payment_method: str) -> Dict[str, Any]:
    """
    Check for large cash transactions requiring source verification.
    
    Returns:
        {
            'flag': 'NONE' | 'LARGE_CASH_DEPOSIT' | 'LARGE_CASH_WITHDRAWAL',
            'description': str
        }
    """
    if not payment_method:
        return {'flag': 'NONE', 'description': ''}
    
    abs_amount = abs(amount)
    payment_upper = payment_method.upper()
    
    is_cash = any(keyword in payment_upper for keyword in ['CASH', 'ATM'])
    
    if is_cash and abs_amount >= 5000:
        if amount > 0:
            return {
                'flag': 'LARGE_CASH_DEPOSIT',
                'description': f'Large cash deposit £{abs_amount:,.2f} - source verification required'
            }
        else:
            return {
                'flag': 'LARGE_CASH_WITHDRAWAL',
                'description': f'Large cash withdrawal £{abs_amount:,.2f} - unusual for business'
            }
    
    return {'flag': 'NONE', 'description': ''}


def check_geographic_risk(country: str) -> Dict[str, Any]:
    """
    Check if counterparty country is high-risk jurisdiction.
    
    Returns:
        {
            'flag': 'NONE' | 'FATF_CRITICAL' | 'FATF_HIGH' | 'FATF_MEDIUM',
            'country_name': str,
            'risk_level': str,
            'risk_score': int,
            'description': str
        }
    """
    if not country or country == 'UNKNOWN':
        return {'flag': 'NONE', 'country_name': country, 'risk_level': '', 'risk_score': 0, 'description': ''}
    
    # Normalize country code
    country_code = normalize_country_code(country)
    
    # Check against high-risk list
    if country_code in HIGH_RISK_COUNTRIES:
        country_info = HIGH_RISK_COUNTRIES[country_code]
        risk_level = country_info.get('risk_level', 'UNKNOWN')
        risk_score = country_info.get('risk_score', 0)
        
        flag_map = {
            'CRITICAL': 'FATF_CRITICAL',
            'HIGH': 'FATF_HIGH',
            'MEDIUM': 'FATF_MEDIUM'
        }
        
        return {
            'flag': flag_map.get(risk_level, 'FATF_MEDIUM'),
            'country_name': country_info.get('name', country),
            'risk_level': risk_level,
            'risk_score': risk_score,
            'description': f"{country_info.get('name', country)} - {country_info.get('category', 'High-Risk')} ({', '.join(country_info.get('sources', []))})"
        }
    
    # Not in high-risk list
    return {'flag': 'NONE', 'country_name': country, 'risk_level': 'LOW', 'risk_score': 0, 'description': ''}


def check_structuring_pattern(amount: float) -> Dict[str, Any]:
    """
    Check for suspicious round numbers just below thresholds.
    
    Returns:
        {
            'flag': 'NONE' | 'SUSPICIOUS_ROUND_NUMBER',
            'pattern': str,
            'description': str
        }
    """
    abs_amount = abs(amount)
    
    # Suspicious patterns: just below thresholds with round numbers
    suspicious_patterns = [
        (9999, 10000, '£9,999 - just below £10k threshold'),
        (9998, 10000, '£9,998 - just below £10k threshold'),
        (9995, 10000, '£9,995 - just below £10k threshold'),
        (9990, 10000, '£9,990 - just below £10k threshold'),
        (9900, 10000, '£9,900 - round number below £10k threshold'),
        (9950, 10000, '£9,950 - round number below £10k threshold'),
        (14999, 15000, '£14,999 - just below £15k threshold'),
        (14998, 15000, '£14,998 - just below £15k threshold'),
        (14995, 15000, '£14,995 - just below £15k threshold'),
        (14990, 15000, '£14,990 - just below £15k threshold'),
        (14900, 15000, '£14,900 - round number below £15k threshold'),
        (14950, 15000, '£14,950 - round number below £15k threshold'),
        (4999, 5000, '£4,999 - just below £5k cash threshold'),
        (4998, 5000, '£4,998 - just below £5k cash threshold'),
        (4995, 5000, '£4,995 - just below £5k cash threshold'),
        (4990, 5000, '£4,990 - just below £5k cash threshold'),
    ]
    
    for pattern_amount, threshold, description in suspicious_patterns:
        if abs_amount == pattern_amount:
            return {
                'flag': 'SUSPICIOUS_ROUND_NUMBER',
                'pattern': f'{pattern_amount}',
                'description': description
            }
    
    return {'flag': 'NONE', 'pattern': '', 'description': ''}


def check_vague_description(description: str, amount: float) -> Dict[str, Any]:
    """
    Check for vague descriptions on high-value transactions.
    
    Returns:
        {
            'flag': 'NONE' | 'VAGUE_HIGH_VALUE',
            'keywords_found': list,
            'description': str
        }
    """
    if not description:
        return {'flag': 'NONE', 'keywords_found': [], 'description': ''}
    
    abs_amount = abs(amount)
    
    # Only flag if amount > £1,000
    if abs_amount < 1000:
        return {'flag': 'NONE', 'keywords_found': [], 'description': ''}
    
    desc_upper = description.upper()
    
    vague_keywords = [
        'SERVICES', 'SERVICE', 'CONSULTANCY', 'CONSULTING', 'CONSULTANT',
        'MISCELLANEOUS', 'MISC', 'VARIOUS', 'PAYMENT', 'TRANSFER',
        'GENERAL', 'OTHER', 'SUNDRY', 'EXPENSES', 'EXPENSE'
    ]
    
    found_keywords = [kw for kw in vague_keywords if kw in desc_upper]
    
    # Check if description is very short (< 10 chars excluding spaces)
    cleaned_desc = re.sub(r'\s+', '', description)
    is_short = len(cleaned_desc) < 10
    
    if found_keywords or is_short:
        return {
            'flag': 'VAGUE_HIGH_VALUE',
            'keywords_found': found_keywords,
            'description': f'High-value transaction (£{abs_amount:,.2f}) with vague description'
        }
    
    return {'flag': 'NONE', 'keywords_found': [], 'description': ''}


def calculate_compliance_risk_score(
    threshold_check: Dict,
    cash_check: Dict,
    geo_check: Dict,
    structuring_check: Dict,
    vague_desc_check: Dict
) -> Dict[str, Any]:
    """
    Calculate composite compliance risk score from all checks.
    
    Returns:
        {
            'score': int (0-100),
            'tier': 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL',
            'flags': list of active flags,
            'reasons': list of risk reasons
        }
    """
    score = 0
    flags = []
    reasons = []
    
    # Threshold breach: +40 points
    if threshold_check['flag'] != 'NONE':
        if threshold_check['flag'] == 'GENERAL_15K':
            score += 40
        elif threshold_check['flag'] == 'HVD_10K':
            score += 35
        flags.append(threshold_check['flag'])
        reasons.append(threshold_check['description'])
    
    # Cash risk: +30 points
    if cash_check['flag'] != 'NONE':
        score += 30
        flags.append(cash_check['flag'])
        reasons.append(cash_check['description'])
    
    # Geographic risk: +50 (critical), +35 (high), +20 (medium)
    if geo_check['flag'] != 'NONE':
        if geo_check['flag'] == 'FATF_CRITICAL':
            score += 50
        elif geo_check['flag'] == 'FATF_HIGH':
            score += 35
        elif geo_check['flag'] == 'FATF_MEDIUM':
            score += 20
        flags.append(geo_check['flag'])
        reasons.append(geo_check['description'])
    
    # Structuring: +25 points
    if structuring_check['flag'] != 'NONE':
        score += 25
        flags.append(structuring_check['flag'])
        reasons.append(structuring_check['description'])
    
    # Vague description: +15 points
    if vague_desc_check['flag'] != 'NONE':
        score += 15
        flags.append(vague_desc_check['flag'])
        reasons.append(vague_desc_check['description'])
    
    # Cap at 100
    score = min(score, 100)
    
    # Determine tier
    if score >= 80:
        tier = 'CRITICAL'
    elif score >= 60:
        tier = 'HIGH'
    elif score >= 30:
        tier = 'MEDIUM'
    else:
        tier = 'LOW'
    
    return {
        'score': score,
        'tier': tier,
        'flags': flags,
        'reasons': reasons
    }


# AWS clients
dynamodb = boto3.resource('dynamodb')
bedrock = boto3.client('bedrock-runtime', region_name=os.environ.get('AWS_REGION', 'eu-west-1'))
sqs = boto3.client('sqs')

# Environment variables
EXTRACTION_RESULTS_TABLE = os.environ.get('EXTRACTION_RESULTS_TABLE')
CATEGORIZATION_QUEUE_URL = os.environ.get('CATEGORIZATION_QUEUE_URL')
BEDROCK_MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'eu.anthropic.claude-3-5-sonnet-20240620-v1:0')
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
COMPANY_EVENTS_TABLE = os.environ.get('COMPANY_EVENTS_TABLE', f'fiscalshield-dc-{ENVIRONMENT}-CompanyEvents')

# Categories for bank transactions
TRANSACTION_EXPENSE_CATEGORIES = """
Office Costs
Travel costs
Clothing costs
Staff costs
Things you buy to sell on
Financial costs
Costs of your business premises
Advertising or marketing
Training course
Accommodation
Bank charges
Bonuses
Business travel mileage for employees' own vehicles
Car parking charges
Cash sum payments to employees
Childcare
Christmas bonuses
Clothing
Club membership
Company cars and fuel
Company vans and fuel
Credit, debit and charge cards
Employee liabilities and indemnity insurance
Entertainment
Food and groceries
Holidays
Home phones
Homeworking
Income tax paid on directors' behalf
Items for disabled employees
Loans provided to employees
Long-service awards
Lost-time payments
Meals for employees and directors
Medical or dental treatment and insurance
Mobile phones
Office and workshop equipment and supplies
Parking spaces
Personal bills
Private use of heavy goods vehicles
Public transport
Relocation costs
Retirement benefit schemes
School fees for an employee's child
Social functions and parties
Sporting or recreational facilities
Subscriptions and professional fees
Training payments
Travel
Trivial benefits
Vouchers
Software
Computer Hardware
Cash withdrawal
Direct debit payments
Standing order payments
Transfer payments
Salary payments
Interest received
Interest paid
Loan repayments
Insurance payments
Utility payments
"""

def get_day_of_week(date_string):
    """Get day of week from date string"""
    if not date_string:
        return "Unknown"
    try:
        date_obj = datetime.strptime(date_string, '%Y-%m-%d')
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        return days[date_obj.weekday()]
    except:
        return "Unknown"

def get_counterparty_name(transaction: Dict) -> str:
    """Extract counterparty name with fallback to description"""
    counterparty = transaction.get('CounterpartyName')
    if counterparty and counterparty != 'NOT_AVAILABLE':
        return counterparty
    # Fallback to description for backward compatibility
    return transaction.get('TransactionDescription') or transaction.get('Description') or 'Unknown'

def get_direction(transaction: Dict) -> str:
    """Extract transaction direction with fallback logic"""
    # First, check for new Direction field
    direction = transaction.get('Direction')
    if direction and direction != 'UNKNOWN':
        return direction
    
    # Fallback: infer from TransactionType
    txn_type = transaction.get('TransactionType', '').upper()
    if txn_type == 'DEBIT':
        return 'OUTBOUND'
    elif txn_type == 'CREDIT':
        return 'INBOUND'
    
    # Fallback: infer from MoneyIn/MoneyOut
    if transaction.get('MoneyOut'):
        return 'OUTBOUND'
    elif transaction.get('MoneyIn'):
        return 'INBOUND'
    
    # Fallback: infer from amount sign
    amount = transaction.get('TransactionAmount')
    if amount:
        try:
            amount_val = float(amount)
            return 'INBOUND' if amount_val > 0 else 'OUTBOUND'
        except:
            pass
    
    return 'UNKNOWN'

def get_payment_method(transaction: Dict) -> str:
    """Extract payment method with fallback to description parsing"""
    # First, check for new PaymentMethod field
    method = transaction.get('PaymentMethod')
    if method and method != 'UNKNOWN':
        return method
    
    # Fallback: infer from description
    description = transaction.get('TransactionDescription') or transaction.get('Description') or ''
    description_upper = description.upper()
    
    # Common payment method keywords
    if 'CARD' in description_upper or 'VISA' in description_upper or 'MASTERCARD' in description_upper:
        return 'CARD'
    elif 'ATM' in description_upper:
        return 'ATM'
    elif 'CASH' in description_upper:
        return 'CASH'
    elif 'BACS' in description_upper:
        return 'BACS'
    elif 'CHAPS' in description_upper:
        return 'CHAPS'
    elif 'FP' in description_upper or 'FASTER PAYMENT' in description_upper:
        return 'FASTER_PAYMENT'
    elif 'DD' in description_upper or 'DIRECT DEBIT' in description_upper:
        return 'DIRECT_DEBIT'
    elif 'SO' in description_upper or 'STANDING ORDER' in description_upper:
        return 'STANDING_ORDER'
    elif 'CHQ' in description_upper or 'CHEQUE' in description_upper:
        return 'CHEQUE'
    elif 'TRANSFER' in description_upper:
        return 'TRANSFER'
    
    return 'UNKNOWN'

def get_company_industry_context(company_number: str) -> str:
    """
    Fetch company SIC codes from CompanyEvents table to provide industry context.
    
    Args:
        company_number: Company number to look up
        
    Returns:
        Formatted industry context string for inclusion in Claude prompt
    """
    try:
        company_table = dynamodb.Table(COMPANY_EVENTS_TABLE)
        
        # Query for company data
        response = company_table.get_item(
            Key={'company_number': company_number}
        )
        
        if 'Item' not in response:
            log_with_timestamp(f"No company data found for {company_number}")
            return ""
        
        # Extract SIC codes from stored company data
        company_data = response['Item'].get('data', {})
        sic_enriched = company_data.get('sic_codes_enriched', [])
        
        if not sic_enriched:
            log_with_timestamp(f"No SIC codes available for company {company_number}")
            return ""
        
        # Build industry context for prompt
        industry_descriptions = []
        for sic in sic_enriched:
            code = sic.get('code', '')
            description = sic.get('description', '')
            if code and description:
                industry_descriptions.append(f"{code}: {description}")
        
        if industry_descriptions:
            context = f"""
COMPANY INDUSTRY CONTEXT:
The company being analyzed operates in the following industry sectors (UK SIC codes):
{chr(10).join(['- ' + desc for desc in industry_descriptions])}

Consider this industry context when categorizing expenses. For example:
- Retail companies (SIC 47xxx) commonly have supplier payments, inventory purchases, and POS system costs
- IT/Software companies (SIC 62xxx) commonly have cloud services, software licenses, and contractor payments
- Construction companies (SIC 41xxx-43xxx) commonly have materials, subcontractor payments, and equipment rental
- Professional services (SIC 69xxx-75xxx) commonly have office costs, professional indemnity insurance, and client entertainment
"""
            log_with_timestamp(f"Added industry context for company {company_number}: {', '.join([s.get('code', '') for s in sic_enriched])}")
            return context
        
        return ""
        
    except Exception as e:
        log_with_timestamp(f"Could not fetch company industry context: {str(e)}")
        return ""

def create_batch_categorization_prompt(transaction_batch, categories: str, company_number: str = None):
    """Create sophisticated prompt for Claude to categorize bank transactions"""
    
    # Convert transactions to formatted text with context
    transaction_list = []
    for transaction in transaction_batch:
        counterparty = get_counterparty_name(transaction)
        direction = get_direction(transaction)
        payment_method = get_payment_method(transaction)
        country = transaction.get('CounterpartyCountry', 'NOT_AVAILABLE')
        
        transaction_text = f"""
Transaction ID: {transaction.get('TransactionId', 'Unknown')}
Date: {transaction.get('TransactionDate') or 'Unknown'}
Day of Week: {get_day_of_week(transaction.get('TransactionDate'))}
Counterparty: {counterparty}
Description: {transaction.get('TransactionDescription') or transaction.get('Description') or 'No description'}
Amount: £{transaction.get('TransactionAmount') or transaction.get('MoneyOut') or transaction.get('MoneyIn') or '0'}
Direction: {direction}
Payment Method: {payment_method}
Country: {country if country and country != 'NOT_AVAILABLE' else 'Not stated'}
Reference: {transaction.get('Reference') or 'N/A'}
"""
        transaction_list.append(transaction_text)
    
    transactions_text = "\n".join(transaction_list)
    
    # Get industry context from SIC codes if company number provided
    industry_context = ""
    if company_number:
        industry_context = get_company_industry_context(company_number)
    
    prompt = f"""You are an experienced forensic accountant reviewing bank transactions for potential tax and compliance issues.
{industry_context} 
Analyze these transactions with professional skepticism while avoiding false positives for legitimate business expenses.

AVAILABLE EXPENSE CATEGORIES:
{categories}

BANK TRANSACTIONS TO ANALYZE:
{transactions_text}

ANALYSIS FRAMEWORK:

Consider these patterns and examples, but use your judgment based on the full context:

LEGITIMATE BUSINESS PATTERNS (typically score 4-5):
• Regular vendors with clear business purpose (utilities, rent, insurance, software subscriptions)
• Business travel with supporting context (client meetings, conferences)
• Professional services with proper references
• ATM withdrawals with business justification (e.g., "petty cash for market stall")
• Round amounts from ATMs are NORMAL and expected
• Weekend hospitality expenses for client entertainment
• Direct debits and standing orders to established vendors

CONTEXT-DEPENDENT PATTERNS (typically score 3):
• Weekend transactions - consider the business type:
  - Restaurant on Saturday might be client entertainment (legitimate)
  - Office supplies on Sunday might be unusual (investigate)
• Round number transfers - consider the context:
  - £500 to "John Smith" with no reference (suspicious)
  - £500 to "ABC Ltd - Monthly retainer" (legitimate)
• Foreign transactions - consider the business:
  - Tech company paying for US cloud services (legitimate)
  - Local bakery paying Panama company (suspicious)

RED FLAGS TO IDENTIFY (typically score 1-2):
• Structuring patterns:
  - Multiple £9,999 payments (just below £10k threshold)
  - Series of £4,999 transactions (below £5k threshold)
  - Split payments to same vendor on same day
• Vague descriptions hiding true purpose:
  - "Invoice" or "Services" with no detail
  - "Consultancy" to individuals without company designation
  - "Miscellaneous" for significant amounts
• Personal expenses without business justification:
  - Streaming services (Netflix, Spotify) not for business use
  - School fees, childcare without employee benefit documentation
  - Personal retail (jewelry, clothing) without business purpose
• Director/shareholder concerns:
  - Round number "loans" without documentation
  - Excessive drawings disguised as expenses
  - Personal bills paid by company
• Geographic/vendor risks:
  - Payments to tax havens without clear purpose
  - New vendors with immediately high values
  - Personal names for professional services

IMPORTANT CONTEXTUAL FACTORS:
• Business type matters - retail has different patterns than consultancy
• Timing patterns - month-end clustering might indicate manipulation
• Historical patterns - sudden changes need investigation
• Amount reasonableness - £50 lunch vs £500 lunch
• Documentation quality - proper references vs vague descriptions

For each transaction, assess:
1. Does the expense align with the business nature?
2. Is the amount reasonable for the described purpose?
3. Is there sufficient documentation/reference?
4. Are there any patterns suggesting tax avoidance or personal use?
5. Would this transaction concern an HMRC inspector?

REQUIRED XML FORMAT:
<batch_analysis>
  <transaction id="[EXACT_TRANSACTION_ID]">
    <category>Category name from list above</category>
    <confidence>HIGH|MEDIUM|LOW</confidence>
    <compliance_score>4</compliance_score>
    <risk_flags>ATM_ROUND_NORMAL|WEEKEND_HOSPITALITY|VAGUE_DESCRIPTION|STRUCTURING|PERSONAL_EXPENSE|DIRECTOR_LOAN|HIGH_VALUE|etc</risk_flags>
    <reasoning>Detailed explanation of your assessment including why you chose specific flags</reasoning>
    <hmrc_concern>YES|NO - Would this likely concern a tax inspector?</hmrc_concern>
    <recommended_action>APPROVE|REVIEW_DOCUMENTATION|INVESTIGATE|REJECT</recommended_action>
  </transaction>
</batch_analysis>

Remember:
- Use the examples as guidance, not rigid rules
- Consider the full context of each transaction
- Round ATM amounts are NORMAL - don't flag without other concerns
- Be specific about WHY something is suspicious
- Provide actionable recommendations"""

    return prompt

def invoke_bedrock(prompt, max_retries=3):
    """Invoke Claude via Bedrock for text processing with retry logic"""
    
    # Estimate token count (1 token ≈ 4 characters)
    estimated_tokens = len(prompt) // 4
    log_with_timestamp(f"Estimated input tokens: {estimated_tokens}")
    
    for attempt in range(max_retries):
        try:
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4000,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            })
            
            response = bedrock.invoke_model(
                body=body,
                modelId=BEDROCK_MODEL_ID,
                accept='application/json',
                contentType='application/json'
            )
            
            response_body = json.loads(response.get('body').read())
            return response_body['content'][0]['text']
            
        except Exception as e:
            error_msg = str(e)
            is_throttle = 'ThrottlingException' in error_msg or 'TooManyRequestsException' in error_msg
            
            log_with_timestamp(f"Bedrock invocation attempt {attempt + 1}/{max_retries} failed: {error_msg}")
            
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                log_with_timestamp(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                log_with_timestamp(f"All Bedrock invocation attempts failed after {max_retries} retries")
                if is_throttle:
                    # Re-raise with clear throttling indicator for Step Functions retry
                    raise Exception(f"BEDROCK_THROTTLED: {error_msg}")
                raise

def parse_categorization_response(response_text, transaction_batch):
    """Parse Claude's enhanced XML response into structured results"""
    
    results = {}
    
    try:
        # Extract each transaction analysis
        transaction_blocks = re.findall(r'<transaction id="([^"]+)">(.*?)</transaction>', response_text, re.DOTALL)
        
        for transaction_id, transaction_content in transaction_blocks:
            # Extract all fields from Claude's analysis
            category_match = re.search(r'<category>(.*?)</category>', transaction_content, re.DOTALL)
            confidence_match = re.search(r'<confidence>(.*?)</confidence>', transaction_content, re.DOTALL)
            score_match = re.search(r'<compliance_score>(\d+)</compliance_score>', transaction_content, re.DOTALL)
            flags_match = re.search(r'<risk_flags>(.*?)</risk_flags>', transaction_content, re.DOTALL)
            reasoning_match = re.search(r'<reasoning>(.*?)</reasoning>', transaction_content, re.DOTALL)
            hmrc_match = re.search(r'<hmrc_concern>(.*?)</hmrc_concern>', transaction_content, re.DOTALL)
            action_match = re.search(r'<recommended_action>(.*?)</recommended_action>', transaction_content, re.DOTALL)
            
            # Parse risk flags from Claude's response
            risk_flags = []
            if flags_match and flags_match.group(1).strip():
                flags_text = flags_match.group(1).strip()
                if flags_text and flags_text.upper() != 'NONE':
                    risk_flags = [flag.strip() for flag in flags_text.split('|')]
            
            if not risk_flags:
                risk_flags = ['CLEAN']
            
            results[transaction_id] = {
                'category': category_match.group(1).strip() if category_match else 'Uncategorized',
                'confidence': confidence_match.group(1).strip() if confidence_match else 'LOW',
                'compliance_score': int(score_match.group(1)) if score_match else 3,
                'risk_flags': risk_flags,
                'reasoning': reasoning_match.group(1).strip() if reasoning_match else 'No reasoning provided',
                'hmrc_concern': hmrc_match.group(1).strip() == 'YES' if hmrc_match else False,
                'recommended_action': action_match.group(1).strip() if action_match else 'REVIEW_DOCUMENTATION'
            }
            
    except Exception as e:
        log_with_timestamp(f"Error parsing categorization response: {str(e)}")
    
    return results

def categorize_transaction_batch(transaction_batch, company_number: str = None):
    """
    Categorize a batch of bank transactions using Claude with industry context from SIC codes
    
    Args:
        transaction_batch: List of transaction dictionaries
        company_number: Optional company number to fetch SIC codes for industry context
    """
    
    log_with_timestamp(f"Starting batch categorization for {len(transaction_batch)} transactions")
    
    # Create batch categorization prompt with industry context
    prompt = create_batch_categorization_prompt(transaction_batch, TRANSACTION_EXPENSE_CATEGORIES, company_number)
    
    # Call Claude for categorization
    response = invoke_bedrock(prompt)
    
    if not response:
        log_with_timestamp("Failed to get categorization response from Claude")
        return {}
    
    # Parse the response
    analysis_results = parse_categorization_response(response, transaction_batch)
    log_with_timestamp(f"Parsed categorization results for {len(analysis_results)} transactions")
    
    return analysis_results

def get_transactions_by_ids(transaction_ids: List[str], company_number: str, user_id: str) -> List[Dict]:
    """Get specific transactions by their IDs for a company/user"""
    
    extraction_table = dynamodb.Table(EXTRACTION_RESULTS_TABLE)
    transactions = []
    
    for transaction_id in transaction_ids:
        try:
            # TransactionId format: users/{userId}/{document}.pdf-bank-{section}-{txn}-{hash}
            # Need to extract document path and transaction number to build PK/SK
            
            # Extract document path (everything before -bank-)
            parts = transaction_id.split('-bank-')
            if len(parts) < 2:
                log_with_timestamp(f"Invalid transaction ID format: {transaction_id}")
                continue
                
            document_path = parts[0]  # Already includes .pdf extension
            bank_parts = parts[1].split('-')  # e.g., ['1', '3', 'd4cf0ecb']
            
            if len(bank_parts) < 2:
                log_with_timestamp(f"Invalid transaction ID format: {transaction_id}")
                continue
                
            section_num = bank_parts[0]
            txn_num = bank_parts[1]
            
            # Build PK and SK based on actual table structure
            pk = f"user#{user_id}#doc#{document_path}"
            sk = f"type#BANK_STATEMENT#section#{section_num}#txn#{txn_num}"
            
            # Get item by primary key
            response = extraction_table.get_item(
                Key={'PK': pk, 'SK': sk}
            )
            
            if 'Item' in response:
                transactions.append(response['Item'])
                log_with_timestamp(f"Found transaction {transaction_id}")
            else:
                log_with_timestamp(f"Transaction {transaction_id} not found (PK: {pk}, SK: {sk})")
                
        except Exception as e:
            log_with_timestamp(f"Error retrieving transaction {transaction_id}: {str(e)}")
    
    return transactions

def update_transaction_analysis(pk: str, sk: str, analysis_result: Dict, compliance_result: Dict) -> bool:
    """Update transaction record in DynamoDB with Claude's analysis and compliance risk scores"""
    
    try:
        extraction_table = dynamodb.Table(EXTRACTION_RESULTS_TABLE)
        
        current_time = int(time.time())
        
        # Build update expression with Claude's complete analysis + compliance risk scores
        update_expression = """
            SET ExpenseCategory = :category,
                CategorizationConfidence = :confidence,
                ComplianceScore = :score,
                RiskFlags = :flags,
                CategorizationReasoning = :reasoning,
                RecommendedAction = :action,
                HMRCConcern = :hmrc,
                AnalysisStatus = :status,
                AnalyzedAt = :timestamp,
                UpdatedAt = :timestamp,
                ComplianceRiskScore = :compliance_score,
                ComplianceRiskTier = :compliance_tier,
                ComplianceFlags = :compliance_flags,
                ComplianceReasons = :compliance_reasons,
                ThresholdFlag = :threshold_flag,
                CashRiskFlag = :cash_flag,
                GeographicRiskFlag = :geo_flag,
                StructuringFlag = :structuring_flag,
                VagueDescriptionFlag = :vague_flag
        """
        
        expression_values = {
            ':category': analysis_result['category'],
            ':confidence': analysis_result['confidence'],
            ':score': Decimal(str(analysis_result['compliance_score'])),
            ':flags': analysis_result['risk_flags'],
            ':reasoning': analysis_result['reasoning'],
            ':action': analysis_result['recommended_action'],
            ':hmrc': analysis_result['hmrc_concern'],
            ':status': 'ANALYZED',
            ':timestamp': current_time,
            ':compliance_score': Decimal(str(compliance_result['score'])),
            ':compliance_tier': compliance_result['tier'],
            ':compliance_flags': compliance_result['flags'],
            ':compliance_reasons': compliance_result['reasons'],
            ':threshold_flag': compliance_result.get('threshold_flag', 'NONE'),
            ':cash_flag': compliance_result.get('cash_flag', 'NONE'),
            ':geo_flag': compliance_result.get('geo_flag', 'NONE'),
            ':structuring_flag': compliance_result.get('structuring_flag', 'NONE'),
            ':vague_flag': compliance_result.get('vague_flag', 'NONE')
        }
        
        # Perform the update
        extraction_table.update_item(
            Key={
                'PK': pk,
                'SK': sk
            },
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values
        )
        
        log_with_timestamp(
            f"Updated transaction: {analysis_result['category']} "
            f"(compliance: {analysis_result['compliance_score']}, risk: {compliance_result['score']}/{compliance_result['tier']}, "
            f"action: {analysis_result['recommended_action']})"
        )
        
        return True
        
    except Exception as e:
        log_with_timestamp(f"Error updating transaction: {str(e)}")
        return False

def process_transaction_batch(message_body: Dict) -> Dict:
    """Process a batch of transactions from SQS message"""
    
    transaction_ids = message_body.get('transaction_ids', [])
    company_number = message_body.get('company_number')
    user_id = message_body.get('user_id')
    
    log_with_timestamp(f"Processing batch of {len(transaction_ids)} transactions for company {company_number}")
    
    # Step 1: Get the transactions
    transaction_batch = get_transactions_by_ids(transaction_ids, company_number, user_id)
    
    if not transaction_batch:
        log_with_timestamp(f"No transactions found for IDs: {transaction_ids}")
        return {
            'successful_count': 0,
            'failed_count': len(transaction_ids),
            'failed_transaction_ids': transaction_ids
        }
    
    log_with_timestamp(f"Retrieved {len(transaction_batch)} transactions for processing")
    
    # Step 2: Categorize with Claude (with industry context from SIC codes)
    try:
        analysis_results = categorize_transaction_batch(transaction_batch, company_number)
        log_with_timestamp(f"Completed categorization for {len(analysis_results)} transactions")
    except Exception as e:
        log_with_timestamp(f"Categorization failed: {str(e)}")
        return {
            'successful_count': 0,
            'failed_count': len(transaction_ids),
            'failed_transaction_ids': transaction_ids
        }
    
    # Step 3: Update each transaction with analysis and compliance checks
    successful_count = 0
    failed_transaction_ids = []
    
    for transaction in transaction_batch:
        transaction_id = transaction.get('TransactionId')
        pk = transaction.get('PK')
        sk = transaction.get('SK')
        
        if transaction_id in analysis_results:
            analysis = analysis_results[transaction_id]
            
            try:
                # Run compliance risk checks
                amount = float(transaction.get('TransactionAmount', 0))
                description = transaction.get('TransactionDescription') or transaction.get('Description') or ''
                payment_method = get_payment_method(transaction)
                country = transaction.get('CounterpartyCountry', '')
                
                # Execute all compliance checks
                threshold_check = check_threshold_breach(amount)
                cash_check = check_cash_risk(amount, payment_method)
                geo_check = check_geographic_risk(country)
                structuring_check = check_structuring_pattern(amount)
                vague_check = check_vague_description(description, amount)
                
                # Calculate composite risk score
                compliance_risk = calculate_compliance_risk_score(
                    threshold_check,
                    cash_check,
                    geo_check,
                    structuring_check,
                    vague_check
                )
                
                # Add individual flags to compliance result for DynamoDB storage
                compliance_risk['threshold_flag'] = threshold_check['flag']
                compliance_risk['cash_flag'] = cash_check['flag']
                compliance_risk['geo_flag'] = geo_check['flag']
                compliance_risk['structuring_flag'] = structuring_check['flag']
                compliance_risk['vague_flag'] = vague_check['flag']
                
                # Update DynamoDB with both analysis and compliance results
                if update_transaction_analysis(pk, sk, analysis, compliance_risk):
                    successful_count += 1
                    flags_summary = ', '.join(analysis['risk_flags'][:2])
                    compliance_summary = f"{compliance_risk['score']}/{compliance_risk['tier']}"
                    log_with_timestamp(
                        f"✅ {transaction_id}: {analysis['category']} "
                        f"(compliance: {analysis['compliance_score']}, risk: {compliance_summary}, "
                        f"flags: {flags_summary})"
                    )
                else:
                    failed_transaction_ids.append(transaction_id)
                    
            except Exception as e:
                log_with_timestamp(f"Error processing transaction {transaction_id}: {str(e)}")
                failed_transaction_ids.append(transaction_id)
        else:
            log_with_timestamp(f"No analysis result for transaction {transaction_id}")
            failed_transaction_ids.append(transaction_id)
    
    log_with_timestamp(
        f"Batch processing complete: {successful_count} successful, {len(failed_transaction_ids)} failed"
    )
    
    return {
        'successful_count': successful_count,
        'failed_count': len(failed_transaction_ids),
        'failed_transaction_ids': failed_transaction_ids
    }

def lambda_handler(event, context):
    """
    Lambda handler for categorizing bank transactions using Claude.
    Invoked by Step Functions Map state for each batch.
    
    Expected event from Step Functions:
    {
        "transaction_ids": ["txn-123", "txn-456", ...],
        "company_number": "12345678",
        "user_id": "user-id",
        "batch_index": 0,
        "batch_size": 15
    }
    
    Returns batch processing result for Step Functions.
    """
    
    log_with_timestamp("Starting batch bank transaction categorization")
    log_with_timestamp(f"Received event: {json.dumps(event, default=str)}")
    
    try:
        # Extract batch parameters directly from event (not from SQS Records)
        transaction_ids = event.get('transaction_ids', [])
        company_number = event.get('company_number')
        user_id = event.get('user_id')
        batch_index = event.get('batch_index', 0)
        
        if not transaction_ids:
            raise ValueError('No transaction IDs provided in batch')
        
        log_with_timestamp(f"Processing batch {batch_index} with {len(transaction_ids)} transactions")
        
        # Process the batch using existing helper function
        message_body = {
            'transaction_ids': transaction_ids,
            'company_number': company_number,
            'user_id': user_id
        }
        
        batch_result = process_transaction_batch(message_body)
        
        log_with_timestamp(
            f"Batch {batch_index} complete: {batch_result['successful_count']} succeeded, "
            f"{batch_result['failed_count']} failed"
        )
        
        # Return result for Step Functions
        return {
            'success': batch_result['successful_count'] > 0,
            'batch_index': batch_index,
            'processed': batch_result['successful_count'],
            'failed': batch_result['failed_count'],
            'failed_transaction_ids': batch_result.get('failed_transaction_ids', []),
            'total': len(transaction_ids)
        }
        
    except Exception as e:
        error_msg = str(e)
        log_with_timestamp(f"Error in lambda handler: {error_msg}")
        import traceback
        log_with_timestamp(f"Full traceback: {traceback.format_exc()}")
        
        # If throttled, raise specific error for Step Functions to retry
        if 'BEDROCK_THROTTLED' in error_msg or 'ThrottlingException' in error_msg:
            log_with_timestamp("Bedrock throttling detected - Step Functions should retry this batch")
            raise Exception(f"THROTTLED: {error_msg}")
        
        # Return error result for Step Functions retry logic
        raise  # Re-raise to trigger Step Functions retry

