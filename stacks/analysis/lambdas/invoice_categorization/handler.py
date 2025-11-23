"""
Invoice Categorization Lambda
Analyzes invoices for tax deductibility using HMRC BIM (Business Income Manual) guidance.
Implements "wholly and exclusively" test for business expense deductibility.
"""

import json
import boto3
import os
import time
from typing import Dict, List, Any
from decimal import Decimal
from datetime import datetime

# AWS clients
dynamodb = boto3.resource('dynamodb')
bedrock_runtime = boto3.client('bedrock-runtime', region_name='eu-west-1')

# Environment variables
EXTRACTION_RESULTS_TABLE = os.environ.get('EXTRACTION_RESULTS_TABLE')
HMRC_GUIDANCE_TABLE = os.environ.get('HMRC_GUIDANCE_TABLE', 'fiscalshield-dc-dev-HMRCGuidance')
COMPANY_EVENTS_TABLE = os.environ.get('COMPANY_EVENTS_TABLE', 'fiscalshield-dc-dev-CompanyEvents')
MODEL_ID = os.environ.get('MODEL_ID', 'eu.anthropic.claude-3-5-sonnet-20240620-v1:0')
MAX_BATCH_SIZE = 10  # Maximum invoices per batch to avoid token limits
RECOMMENDED_BATCH_SIZE = 8  # Recommended batch size to reduce XML truncation risk
MAX_RETRY_ATTEMPTS = 3  # Maximum number of times to retry a failed invoice


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder for DynamoDB Decimal types"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


def fetch_bim_guidance() -> str:
    """
    Fetch HMRC BIM sections from Data Collection stack's HMRCGuidance table.
    Returns formatted guidance text for use in AI prompts.
    """
    try:
        guidance_table = dynamodb.Table(HMRC_GUIDANCE_TABLE)
        
        # Query all BIM sections (especially BIM37000 - wholly and exclusively)
        response = guidance_table.scan(
            ProjectionExpression='section_id, title, compliance_rules, examples, #cat',
            ExpressionAttributeNames={'#cat': 'category'}
        )
        
        sections = response.get('Items', [])
        
        if not sections:
            print("[WARNING] No BIM guidance found in table, using fallback rules")
            return get_fallback_guidance()
        
        # Format guidance for prompt
        guidance_text = "HMRC BUSINESS INCOME MANUAL (BIM) GUIDANCE:\n\n"
        
        for section in sections:
            section_id = section.get('section_id', 'Unknown')
            title = section.get('title', 'No title')
            rules = section.get('compliance_rules', [])
            examples = section.get('examples', [])
            
            guidance_text += f"## {section_id.upper()} - {title}\n"
            
            if rules:
                guidance_text += "Rules:\n"
                for rule in rules:
                    guidance_text += f"- {rule}\n"
            
            if examples:
                guidance_text += "Examples:\n"
                for example in examples:
                    guidance_text += f"- {example}\n"
            
            guidance_text += "\n"
        
        print(f"[INFO] Loaded {len(sections)} BIM sections from guidance table")
        return guidance_text
        
    except Exception as e:
        print(f"[ERROR] Failed to fetch BIM guidance: {str(e)}")
        return get_fallback_guidance()


def get_fallback_guidance() -> str:
    """Fallback BIM guidance if table query fails"""
    return """
HMRC BUSINESS INCOME MANUAL (BIM) GUIDANCE:

## BIM37000 - WHOLLY AND EXCLUSIVELY TEST

The fundamental principle: An expense is only deductible if incurred "wholly and exclusively" for business purposes.

Rules:
- The expense must be incurred entirely for business purposes
- No dual-purpose expenses allowed (business + personal use)
- Must have clear business justification
- Proper documentation/receipts required
- Entertainment expenses have strict limitations

FULLY DEDUCTIBLE Examples:
- Office rent and utilities (100% business use)
- Professional subscriptions directly related to business
- Business travel to client meetings (not regular commute)
- Raw materials and stock for resale
- Business insurance premiums
- Marketing and advertising costs
- Legal and professional fees for business matters
- Equipment used solely for business

NOT DEDUCTIBLE Examples:
- Gym memberships (personal benefit, even if "stress relief")
- Childcare or school fees
- Clothing that can be worn outside work
- Commuting costs to regular workplace
- Personal entertainment
- Fines and penalties
- Charitable donations (unless sponsorship with business benefit)

PARTIALLY DEDUCTIBLE (Requires Apportionment):
- Home office expenses (business % of total)
- Mobile phone with mixed business/personal use
- Vehicle used for both business and personal journeys
- Internet connection with mixed use

SPECIAL CASES - REQUIRES REVIEW:
- Client entertainment (strictly limited)
- Staff entertaining (may be allowable)
- Travel and subsistence (must not be home to regular workplace)
- Training courses (must enhance current skills, not retrain for new trade)
"""


def fetch_company_context(company_number: str) -> Dict[str, Any]:
    """
    Fetch company context from Data Collection stack's CompanyEvents table.
    Returns company name, industry, SIC codes for context-aware analysis.
    """
    try:
        company_events_table = dynamodb.Table(COMPANY_EVENTS_TABLE)
        
        # Query by company_number (partition key) to get latest event
        response = company_events_table.query(
            KeyConditionExpression='company_number = :cn',
            ExpressionAttributeValues={':cn': company_number},
            ScanIndexForward=False,  # Get most recent first
            Limit=1
        )
        
        if not response.get('Items'):
            print(f"[WARNING] No company data found for {company_number}")
            return {}
        
        company = response['Items'][0]
        
        context = {
            'company_name': company.get('company_name', 'Unknown'),
            'company_type': company.get('company_type', 'Unknown'),
            'sic_codes': company.get('sic_codes', []),
            'company_status': company.get('company_status', 'Unknown')
        }
        
        # Get industry from first SIC code if available
        if context['sic_codes']:
            # SIC codes are 5-digit codes like "62012" (Business and domestic software development)
            first_sic = context['sic_codes'][0]
            context['industry'] = f"SIC {first_sic}"
        else:
            context['industry'] = 'Unknown'
        
        print(f"[INFO] Company context: {context['company_name']} ({context['industry']})")
        return context
        
    except Exception as e:
        print(f"[WARNING] Failed to fetch company context: {str(e)}")
        return {}


def create_invoice_analysis_prompt(invoice_batch: List[Dict], bim_guidance: str, company_context: Dict = None) -> str:
    """
    Create prompt for Claude to analyze invoice deductibility.
    Uses BIM guidance to assess "wholly and exclusively" compliance.
    """
    
    # Add company context to prompt
    context_section = ""
    if company_context:
        sic_codes_str = ", ".join(company_context.get('sic_codes', [])) if company_context.get('sic_codes') else 'Unknown'
        context_section = f"""
BUSINESS CONTEXT:
Company Name: {company_context.get('company_name', 'Unknown')}
Industry: {company_context.get('industry', 'Unknown')}
SIC Codes: {sic_codes_str}
Company Type: {company_context.get('company_type', 'Unknown')}

IMPORTANT: Consider whether expenses are relevant to this specific industry when assessing the "wholly and exclusively" test.
For example, gym equipment for a fitness business is clearly deductible, but for an accountancy firm it would be personal.
"""
    
    # Format invoices for analysis
    invoice_list = []
    for idx, invoice in enumerate(invoice_batch, 1):
        invoice_type = invoice.get('InvoiceType', 'UNKNOWN')
        scrutiny_flag = ''
        analysis_framework = ''
        
        # Flag employee expenses for stricter scrutiny
        if invoice_type == 'EMPLOYEE_EXPENSE':
            scrutiny_flag = '\n⚠️ EMPLOYEE EXPENSE - Apply stricter scrutiny for potential personal benefit'
        
        # Test 1 applies to ALL invoices
        base_analysis = """

TEST 1: S54 CTA 2009 - Wholly and Exclusively?
  - Is the sole purpose of this expense for the trade?
  - This test applies to ALL invoice types (SUPPLIER_INVOICE and EXPENSE_CLAIM)
  - Add confidence if uncertain (e.g., limited invoice description)
"""
        
        # Type-specific analysis instructions
        if invoice_type == 'EXPENSE_CLAIM':
            analysis_framework = base_analysis + """

🔍 EXPENSE CLAIM - APPLY ADDITIONAL COMPLIANCE TESTS (2-7):

TEST 2: Entertainment? (S45-47 CTA 2009)
  - IF Staff Entertainment → DEDUCTIBLE (S45(2))
  - IF Client Entertainment → DISALLOWED (S45) - ADDBACK = 100%
  - Add confidence if unclear from invoice description

TEST 3: Travel Expense? (S54 CTA + S38 ITEPA)
  - IF Business Travel → DEDUCTIBLE (S54)
  - IF Commuting (home to regular workplace) → DISALLOWED (S38 ITEPA) - ADDBACK = 100%
  - Add confidence if destination/purpose unclear

TEST 4: Training? (S74 CTA)
  - IF Work-Related (enhances current skills) → DEDUCTIBLE (S74)
  - IF Personal Development (new career/retraining) → Assess case-by-case

TEST 5: Statutory Bans?
  - IF Penalties/Fines (S1304) → DISALLOWED - ADDBACK = 100%
  - IF Depreciation (S53) → Use Capital Allowances instead - ADDBACK = 100%

TEST 6: Mixed Use / Apportionable? (S54(2))
  - Does this expense have BOTH business and personal use?
  - Examples: Home office, car, mobile phone, internet
  - IF YES → Estimate business use % based on available information
  - ALWAYS mark as LOW confidence unless invoice provides usage data
  - Calculate: ADDBACK = Total × (1 - Business_Use_%)
  - Specify what documentation is needed to verify the %

TEST 7: Duality of Purpose? (S54(2))
  - Does the expense have inherently DUAL objectives (business AND personal benefit)?
  - Key case: Mallalieu v Drummond - expense must be for business ONLY
  - Examples of duality: Business suit (professional + personal clothing), Gym membership (health + stress relief)
  - IF Dual Purpose = TRUE → ADDBACK = 100% (entire expense disallowed)
  - IF Passes duality test → Continue to deduction

CONFIDENCE LEVELS:
  - HIGH: Clear evidence in invoice (e.g., "Staff Christmas Party", "Train to client meeting with receipt")
  - MEDIUM: Reasonable inference from description (e.g., "Fuel" for business vehicle)
  - LOW: Insufficient information, requires verification (e.g., "Mobile phone" without usage breakdown)

For this invoice, identify which test(s) apply and provide detailed outcomes with confidence levels where appropriate.
"""
        else:
            # SUPPLIER_INVOICE - Test 1 only
            analysis_framework = base_analysis + """

📋 SUPPLIER INVOICE - TEST 1 ONLY:
  - Apply the wholly & exclusively test
  - No need for additional tests (2-7) unless expense claim characteristics detected
"""
        
        invoice_text = f"""
Invoice #{idx}
Invoice ID: {invoice.get('InvoiceId', 'Unknown')}
Type: {invoice_type}{scrutiny_flag}
Supplier: {invoice.get('SupplierName') or invoice.get('VendorName') or 'Unknown'}
Amount: £{invoice.get('TotalAmount', '0')}
Date: {invoice.get('InvoiceDate') or 'Unknown'}
Description: {invoice.get('Description', 'No description available')}
Line Items: {invoice.get('LineItems', 'Not available')}{analysis_framework}
"""
        invoice_list.append(invoice_text)
    
    invoices_text = "\n---\n".join(invoice_list)
    
    prompt = f"""You are an experienced UK tax accountant analyzing business expenses for HMRC compliance.
Apply the "wholly and exclusively" test to determine tax deductibility of each invoice.

{context_section}

{bim_guidance}

INVOICES TO ANALYZE:
{invoices_text}

ANALYSIS FRAMEWORK:

For each invoice, determine:

1. DEDUCTIBILITY STATUS - Choose ONE:
   - FULLY_DEDUCTIBLE: Expense incurred wholly and exclusively for business (100% allowable)
   - PARTIALLY_DEDUCTIBLE: Has business and personal elements (requires apportionment %)
   - NOT_DEDUCTIBLE: Personal expense or fails wholly/exclusively test
   - REQUIRES_REVIEW: Unclear from invoice alone, needs additional documentation

2. DEDUCTIBILITY PERCENTAGE:
   - FULLY_DEDUCTIBLE: 100
   - PARTIALLY_DEDUCTIBLE: Reasonable business use % (e.g., 60 for home office)
   - NOT_DEDUCTIBLE: 0
   - REQUIRES_REVIEW: null (cannot determine)

3. BIM SECTION REFERENCE:
   - Which BIM section(s) apply to this expense type?
   - Example: "BIM37000 - Wholly and exclusively", "BIM37600 - Travel expenses"

4. HMRC CONCERNS:
   - Would an HMRC inspector likely challenge this expense?
   - YES if suspicious/personal, NO if clearly business

5. REASONING:
   - KEEP IT CONCISE (1-2 sentences maximum)
   - Reference specific BIM rules
   - Note any red flags or documentation requirements

IMPORTANT: Be concise in ALL text fields to ensure complete response for all invoices.

REQUIRED JSON FORMAT (respond with valid JSON only, no markdown):

{{
  "analyses": [
    {{
      "invoice_id": "[EXACT_INVOICE_ID]",
      "type": "EXPENSE_CLAIM|SUPPLIER_INVOICE",
      "status": "FULLY_DEDUCTIBLE|PARTIALLY_DEDUCTIBLE|NOT_DEDUCTIBLE|REQUIRES_REVIEW",
      "percentage": 0-100 or null,
      "confidence": "HIGH|MEDIUM|LOW",
      "bim_sections": "BIM37000, BIM37600",
      "hmrc_concern": true|false,
      "reasoning": "Concise 1-2 sentence explanation",
      "documentation": "Brief list of needed docs",
      "action": "APPROVE|REQUEST_DOCUMENTATION|APPORTION|REJECT",
      "tests": {{
        "test_1": {{"result": "PASS|FAIL|DUALITY", "confidence": "HIGH|MEDIUM|LOW", "reasoning": "..."}},
        "test_2": {{"result": "NOT_APPLICABLE|STAFF_ENTERTAINMENT|CLIENT_ENTERTAINMENT", "confidence": "...", "reasoning": "..."}},
        "test_3": {{"result": "NOT_APPLICABLE|BUSINESS_TRAVEL|COMMUTING", "confidence": "...", "reasoning": "..."}},
        "test_4": {{"result": "NOT_APPLICABLE|WORK_RELATED|PERSONAL_DEVELOPMENT", "confidence": "...", "reasoning": "..."}},
        "test_5": {{"result": "NOT_APPLICABLE|PENALTIES|DEPRECIATION"}},
        "test_6": {{"result": "NOT_APPLICABLE|APPORTIONABLE|NO_MIXED_USE", "business_pct": 0-100, "confidence": "...", "reasoning": "...", "docs_needed": "..."}},
        "test_7": {{"result": "PASS|FAIL", "confidence": "...", "reasoning": "..."}},
        "addback_amount": "0.00",
        "addback_reason": "..."
      }}
    }}
  ]
}}

NOTES:
- Respond with JSON only (no markdown code blocks)
- For SUPPLIER_INVOICE: Include only test_1 in tests object, omit tests 2-7
- For EXPENSE_CLAIM: Include all 7 tests
- Omit optional fields (confidence, reasoning) when not needed to save tokens
"""
    
    return prompt


def invoke_bedrock_for_analysis(prompt: str, max_retries: int = 3) -> str:
    """Invoke Claude via Bedrock with retry logic for throttling"""
    
    # Estimate token count (1 token ≈ 4 characters)
    estimated_tokens = len(prompt) // 4
    print(f"[INFO] Estimated input tokens: {estimated_tokens}")
    
    for attempt in range(max_retries):
        try:
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 8000,
                "temperature": 0,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            response = bedrock_runtime.invoke_model(
                modelId=MODEL_ID,
                body=json.dumps(request_body)
            )
            
            response_body = json.loads(response['body'].read())
            result_text = response_body['content'][0]['text']
            
            # Log full response to CloudWatch for audit trail
            print("[DEBUG] Claude Response (first 1000 chars):")
            print(result_text[:1000])
            
            return result_text
            
        except Exception as e:
            error_msg = str(e)
            is_throttle = 'ThrottlingException' in error_msg or 'TooManyRequestsException' in error_msg
            
            print(f"[WARNING] Bedrock invocation attempt {attempt + 1}/{max_retries} failed: {error_msg}")
            
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                print(f"[INFO] Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print(f"[ERROR] All Bedrock invocation attempts failed after {max_retries} retries")
                if is_throttle:
                    # Re-raise with clear throttling indicator
                    raise Exception(f"BEDROCK_THROTTLED: {error_msg}")
                raise


def parse_analysis_from_json(json_result: str, invoice_batch: List[Dict]) -> List[Dict]:
    """
    Parse JSON analysis results.
    Returns list of invoices with analysis fields added.
    """
    analyzed_invoices = []
    
    try:
        # Clean up potential markdown code blocks
        json_text = json_result.strip()
        if json_text.startswith('```json'):
            json_text = json_text.split('```json')[1]
        if json_text.startswith('```'):
            json_text = json_text.split('```')[1]
        if json_text.endswith('```'):
            json_text = json_text.rsplit('```', 1)[0]
        json_text = json_text.strip()
        
        # Parse JSON
        data = json.loads(json_text)
        analyses = data.get('analyses', [])
        
        for analysis in analyses:
            invoice_id = analysis.get('invoice_id')
            
            # Find corresponding invoice in batch
            original_invoice = next((inv for inv in invoice_batch if inv.get('InvoiceId') == invoice_id), None)
            
            if not original_invoice:
                print(f"[WARNING] No matching invoice for ID {invoice_id}")
                continue
            
            analyzed_invoice = original_invoice.copy()
            analyzed_invoice.update({
                'DeductibilityStatus': analysis.get('status'),
                'DeductibilityPercentage': analysis.get('percentage'),
                'DeductibilityConfidence': analysis.get('confidence'),
                'BIMSections': analysis.get('bim_sections'),
                'HMRCConcern': analysis.get('hmrc_concern', False),
                'DeductibilityReasoning': analysis.get('reasoning'),
                'DocumentationRequired': analysis.get('documentation'),
                'RecommendedAction': analysis.get('action'),
                'AnalysisStatus': 'ANALYZED',
                'AnalyzedAt': int(time.time()),
                'ModelUsed': MODEL_ID
            })
            
            # Parse compliance tests
            tests = analysis.get('tests', {})
            if tests:
                test1 = tests.get('test_1', {})
                analyzed_invoice.update({
                    # Test 1
                    'Test1_WhollyExclusively': test1.get('result'),
                    'Test1_Confidence': test1.get('confidence'),
                    'Test1_Reasoning': test1.get('reasoning'),
                })
                
                # Tests 2-7 (only for EXPENSE_CLAIM)
                test2 = tests.get('test_2', {})
                if test2:
                    analyzed_invoice['Test2_Entertainment'] = test2.get('result')
                    analyzed_invoice['Test2_Confidence'] = test2.get('confidence')
                    analyzed_invoice['Test2_Reasoning'] = test2.get('reasoning')
                
                test3 = tests.get('test_3', {})
                if test3:
                    analyzed_invoice['Test3_Travel'] = test3.get('result')
                    analyzed_invoice['Test3_Confidence'] = test3.get('confidence')
                    analyzed_invoice['Test3_Reasoning'] = test3.get('reasoning')
                
                test4 = tests.get('test_4', {})
                if test4:
                    analyzed_invoice['Test4_Training'] = test4.get('result')
                    analyzed_invoice['Test4_Confidence'] = test4.get('confidence')
                    analyzed_invoice['Test4_Reasoning'] = test4.get('reasoning')
                
                test5 = tests.get('test_5', {})
                if test5:
                    analyzed_invoice['Test5_StatutoryBan'] = test5.get('result')
                
                test6 = tests.get('test_6', {})
                if test6:
                    analyzed_invoice['Test6_MixedUse'] = test6.get('result')
                    analyzed_invoice['Test6_BusinessPercentage'] = test6.get('business_pct')
                    analyzed_invoice['Test6_Confidence'] = test6.get('confidence')
                    analyzed_invoice['Test6_Reasoning'] = test6.get('reasoning')
                    analyzed_invoice['Test6_DocumentationNeeded'] = test6.get('docs_needed')
                
                test7 = tests.get('test_7', {})
                if test7:
                    analyzed_invoice['Test7_Duality'] = test7.get('result')
                    analyzed_invoice['Test7_Confidence'] = test7.get('confidence')
                    analyzed_invoice['Test7_Reasoning'] = test7.get('reasoning')
                
                # Addback
                analyzed_invoice['AddbackAmount'] = tests.get('addback_amount')
                analyzed_invoice['AddbackReason'] = tests.get('addback_reason')
            
            analyzed_invoices.append(analyzed_invoice)
        
        print(f"[INFO] Successfully parsed {len(analyzed_invoices)} invoice analyses from JSON")
        return analyzed_invoices
        
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON parsing failed: {str(e)}")
        print(f"[ERROR] Response text: {json_result[:500]}...")
        return []
    except Exception as e:
        print(f"[ERROR] Unexpected error parsing JSON: {str(e)}")
        return []


def validate_analysis(analyzed_invoice: Dict) -> bool:
    """
    Validate that analysis results are complete and sensible.
    Returns True if valid, False otherwise.
    """
    invoice_id = analyzed_invoice.get('InvoiceId', 'Unknown')
    status = analyzed_invoice.get('DeductibilityStatus')
    percentage = analyzed_invoice.get('DeductibilityPercentage')
    
    # Check required fields
    if not status or status not in ['FULLY_DEDUCTIBLE', 'PARTIALLY_DEDUCTIBLE', 'NOT_DEDUCTIBLE', 'REQUIRES_REVIEW']:
        print(f"[ERROR] Invoice {invoice_id}: Invalid deductibility status: {status}")
        return False
    
    # Validate percentage matches status
    if status == 'FULLY_DEDUCTIBLE' and percentage not in ['100', 100]:
        print(f"[WARNING] Invoice {invoice_id}: FULLY_DEDUCTIBLE should have 100% - got {percentage}")
    
    if status == 'NOT_DEDUCTIBLE' and percentage not in ['0', 0]:
        print(f"[WARNING] Invoice {invoice_id}: NOT_DEDUCTIBLE should have 0% - got {percentage}")
    
    if status == 'REQUIRES_REVIEW' and percentage not in [None, 'null', '']:
        print(f"[WARNING] Invoice {invoice_id}: REQUIRES_REVIEW should have null percentage - got {percentage}")
    
    if status == 'PARTIALLY_DEDUCTIBLE':
        try:
            pct = int(percentage) if percentage else 0
            if pct <= 0 or pct >= 100:
                print(f"[WARNING] Invoice {invoice_id}: PARTIALLY_DEDUCTIBLE with {pct}% - should be between 1-99%")
        except (ValueError, TypeError):
            print(f"[WARNING] Invoice {invoice_id}: PARTIALLY_DEDUCTIBLE has invalid percentage: {percentage}")
    
    return True


def update_invoices_in_dynamodb(analyzed_invoices: List[Dict]):
    """Update invoices in ExtractionResultsTable with analysis results"""
    
    extraction_table = dynamodb.Table(EXTRACTION_RESULTS_TABLE)
    
    for invoice in analyzed_invoices:
        try:
            pk = invoice.get('PK')
            sk = invoice.get('SK')
            
            if not pk or not sk:
                print(f"[WARNING] Invoice missing PK/SK: {invoice.get('InvoiceId')}")
                continue
            
            # Check if this is a failed invoice (parsing error)
            if invoice.get('AnalysisStatus') in ['FAILED', 'FAILED_PERMANENT']:
                # Minimal update for failed invoices
                extraction_table.update_item(
                    Key={'PK': pk, 'SK': sk},
                    UpdateExpression='SET AnalysisStatus = :status, AnalyzedAt = :analyzed_at, DeductibilityReasoning = :reasoning, AnalysisRetryCount = :retry_count',
                    ExpressionAttributeValues={
                        ':status': invoice.get('AnalysisStatus'),
                        ':analyzed_at': invoice.get('AnalyzedAt'),
                        ':reasoning': invoice.get('DeductibilityReasoning', 'Analysis failed'),
                        ':retry_count': invoice.get('AnalysisRetryCount', 0)
                    }
                )
                status_label = 'PERMANENTLY FAILED' if invoice.get('AnalysisStatus') == 'FAILED_PERMANENT' else 'FAILED'
                print(f"[INFO] Marked invoice as {status_label}: {invoice.get('InvoiceId')} (retry count: {invoice.get('AnalysisRetryCount', 0)})")
                continue
            
            # Validate analysis results for successful invoices
            if not validate_analysis(invoice):
                print(f"[WARNING] Skipping invalid analysis for invoice {invoice.get('InvoiceId')}")
                continue
            
            # Handle null percentage properly
            percentage = invoice.get('DeductibilityPercentage')
            if percentage and percentage not in ['null', '']:
                try:
                    percentage = int(percentage)
                except (ValueError, TypeError):
                    print(f"[WARNING] Invalid percentage value: {percentage}, setting to None")
                    percentage = None
            else:
                percentage = None
            
            # Build dynamic update expression
            update_expr = 'SET DeductibilityStatus = :status'
            expr_values = {':status': invoice.get('DeductibilityStatus')}
            
            if percentage is not None:
                update_expr += ', DeductibilityPercentage = :percentage'
                expr_values[':percentage'] = percentage
            
            # Add other fields
            update_expr += ''', 
                BIMSections = :sections,
                HMRCConcern = :concern,
                DeductibilityReasoning = :reasoning,
                DocumentationRequired = :docs,
                RecommendedAction = :action,
                AnalysisStatus = :analysis_status,
                AnalyzedAt = :analyzed_at,
                ModelUsed = :model
            '''
            
            expr_values.update({
                ':sections': invoice.get('BIMSections'),
                ':concern': invoice.get('HMRCConcern', False),
                ':reasoning': invoice.get('DeductibilityReasoning'),
                ':docs': invoice.get('DocumentationRequired'),
                ':action': invoice.get('RecommendedAction'),
                ':analysis_status': 'ANALYZED',
                ':analyzed_at': invoice.get('AnalyzedAt'),
                ':model': invoice.get('ModelUsed')
            })
            
            # Add deductibility confidence if present
            if invoice.get('DeductibilityConfidence'):
                update_expr += ', DeductibilityConfidence = :deduct_conf'
                expr_values[':deduct_conf'] = invoice.get('DeductibilityConfidence')
            
            # Add compliance test results if present (EXPENSE_CLAIM invoices)
            if invoice.get('Test1_WhollyExclusively'):
                # Build dynamic expression for optional confidence/reasoning fields
                test_fields = []
                
                # Test 1
                test_fields.append('Test1_WhollyExclusively = :test1')
                expr_values[':test1'] = invoice.get('Test1_WhollyExclusively')
                if invoice.get('Test1_Confidence'):
                    test_fields.append('Test1_Confidence = :test1_conf')
                    expr_values[':test1_conf'] = invoice.get('Test1_Confidence')
                if invoice.get('Test1_Reasoning'):
                    test_fields.append('Test1_Reasoning = :test1_reason')
                    expr_values[':test1_reason'] = invoice.get('Test1_Reasoning')
                
                # Test 2
                test_fields.append('Test2_Entertainment = :test2')
                expr_values[':test2'] = invoice.get('Test2_Entertainment')
                if invoice.get('Test2_Confidence'):
                    test_fields.append('Test2_Confidence = :test2_conf')
                    expr_values[':test2_conf'] = invoice.get('Test2_Confidence')
                if invoice.get('Test2_Reasoning'):
                    test_fields.append('Test2_Reasoning = :test2_reason')
                    expr_values[':test2_reason'] = invoice.get('Test2_Reasoning')
                
                # Test 3
                test_fields.append('Test3_Travel = :test3')
                expr_values[':test3'] = invoice.get('Test3_Travel')
                if invoice.get('Test3_Confidence'):
                    test_fields.append('Test3_Confidence = :test3_conf')
                    expr_values[':test3_conf'] = invoice.get('Test3_Confidence')
                if invoice.get('Test3_Reasoning'):
                    test_fields.append('Test3_Reasoning = :test3_reason')
                    expr_values[':test3_reason'] = invoice.get('Test3_Reasoning')
                
                # Test 4
                test_fields.append('Test4_Training = :test4')
                expr_values[':test4'] = invoice.get('Test4_Training')
                if invoice.get('Test4_Confidence'):
                    test_fields.append('Test4_Confidence = :test4_conf')
                    expr_values[':test4_conf'] = invoice.get('Test4_Confidence')
                if invoice.get('Test4_Reasoning'):
                    test_fields.append('Test4_Reasoning = :test4_reason')
                    expr_values[':test4_reason'] = invoice.get('Test4_Reasoning')
                
                # Test 5
                test_fields.append('Test5_StatutoryBan = :test5')
                expr_values[':test5'] = invoice.get('Test5_StatutoryBan')
                
                # Test 6
                test_fields.append('Test6_MixedUse = :test6')
                expr_values[':test6'] = invoice.get('Test6_MixedUse')
                if invoice.get('Test6_BusinessPercentage'):
                    test_fields.append('Test6_BusinessPercentage = :test6_pct')
                    expr_values[':test6_pct'] = invoice.get('Test6_BusinessPercentage')
                if invoice.get('Test6_Confidence'):
                    test_fields.append('Test6_Confidence = :test6_conf')
                    expr_values[':test6_conf'] = invoice.get('Test6_Confidence')
                if invoice.get('Test6_Reasoning'):
                    test_fields.append('Test6_Reasoning = :test6_reason')
                    expr_values[':test6_reason'] = invoice.get('Test6_Reasoning')
                if invoice.get('Test6_DocumentationNeeded'):
                    test_fields.append('Test6_DocumentationNeeded = :test6_docs')
                    expr_values[':test6_docs'] = invoice.get('Test6_DocumentationNeeded')
                
                # Test 7
                test_fields.append('Test7_Duality = :test7')
                expr_values[':test7'] = invoice.get('Test7_Duality')
                if invoice.get('Test7_Confidence'):
                    test_fields.append('Test7_Confidence = :test7_conf')
                    expr_values[':test7_conf'] = invoice.get('Test7_Confidence')
                if invoice.get('Test7_Reasoning'):
                    test_fields.append('Test7_Reasoning = :test7_reason')
                    expr_values[':test7_reason'] = invoice.get('Test7_Reasoning')
                
                # Addback
                test_fields.append('AddbackAmount = :addback_amt')
                test_fields.append('AddbackReason = :addback_reason')
                expr_values[':addback_amt'] = invoice.get('AddbackAmount')
                expr_values[':addback_reason'] = invoice.get('AddbackReason')
                
                # Add all test fields to update expression
                update_expr += ', ' + ', '.join(test_fields)
            
            # Update with analysis fields
            extraction_table.update_item(
                Key={'PK': pk, 'SK': sk},
                UpdateExpression=update_expr,
                ExpressionAttributeValues=expr_values
            )
            
            print(f"[INFO] Updated invoice {invoice.get('InvoiceId')} - {invoice.get('DeductibilityStatus')} ({percentage}%)")
            
        except Exception as e:
            print(f"[ERROR] Failed to update invoice {invoice.get('InvoiceId')}: {str(e)}")
            # Continue with other invoices


def lambda_handler(event, context):
    """
    Main Lambda handler for invoice categorization.
    Receives batch of invoices from Step Functions, analyzes deductibility.
    Returns status and breakdown, or raises exception for Step Functions retry.
    """
    
    print(f"[INFO] Invoice Categorization Lambda invoked")
    print(f"[INFO] Event: {json.dumps(event, default=str)[:500]}...")
    
    try:
        # Extract invoice batch from event
        invoice_batch = event.get('invoices', [])
        
        if not invoice_batch:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'No invoices in batch'})
            }
        
        print(f"[INFO] Processing batch of {len(invoice_batch)} invoices")
        
        # Validate batch size
        if len(invoice_batch) > MAX_BATCH_SIZE:
            print(f"[WARNING] Batch size {len(invoice_batch)} exceeds recommended max {MAX_BATCH_SIZE}")
            print(f"[WARNING] This may cause token limit issues or timeouts")
        
        # Fetch company context for industry-aware analysis
        company_number = event.get('company_number')
        company_context = fetch_company_context(company_number) if company_number else None
        
        # Fetch BIM guidance from Data Collection stack
        bim_guidance = fetch_bim_guidance()
        
        # Create analysis prompt with company context
        prompt = create_invoice_analysis_prompt(invoice_batch, bim_guidance, company_context)
        
        # Invoke Claude for analysis (with retry logic)
        print("[INFO] Invoking Claude for invoice analysis...")
        json_result = invoke_bedrock_for_analysis(prompt)
        
        # Parse results
        analyzed_invoices = parse_analysis_from_json(json_result, invoice_batch)
        
        # Identify invoices that failed to parse (lost in truncation)
        analyzed_ids = {inv.get('InvoiceId') for inv in analyzed_invoices}
        failed_invoices = [inv for inv in invoice_batch if inv.get('InvoiceId') not in analyzed_ids]
        
        if failed_invoices:
            print(f"[WARNING] {len(failed_invoices)} invoices failed to parse from JSON response")
            for failed_inv in failed_invoices:
                invoice_id = failed_inv.get('InvoiceId')
                print(f"[WARNING] Failed invoice: {invoice_id}")
                
                # Check retry count
                retry_count = failed_inv.get('AnalysisRetryCount', 0)
                new_retry_count = retry_count + 1
                
                if new_retry_count >= MAX_RETRY_ATTEMPTS:
                    # Max retries reached - mark as permanently failed
                    print(f"[ERROR] Invoice {invoice_id} reached max retry attempts ({MAX_RETRY_ATTEMPTS})")
                    failed_inv.update({
                        'AnalysisStatus': 'FAILED_PERMANENT',
                        'AnalyzedAt': int(time.time()),
                        'AnalysisRetryCount': new_retry_count,
                        'DeductibilityReasoning': f'Analysis failed after {MAX_RETRY_ATTEMPTS} attempts. Manual review required.',
                    })
                else:
                    # Mark as failed for retry
                    print(f"[INFO] Invoice {invoice_id} will be retried (attempt {new_retry_count}/{MAX_RETRY_ATTEMPTS})")
                    failed_inv.update({
                        'AnalysisStatus': 'FAILED',
                        'AnalyzedAt': int(time.time()),
                        'AnalysisRetryCount': new_retry_count,
                        'DeductibilityReasoning': f'JSON parsing failed - attempt {new_retry_count}/{MAX_RETRY_ATTEMPTS}. Will retry automatically.',
                    })
            # Add failed invoices to the list so they get status updated in DynamoDB
            analyzed_invoices.extend(failed_invoices)
        
        # Update DynamoDB
        update_invoices_in_dynamodb(analyzed_invoices)
        
        # Calculate summary statistics
        status_counts = {}
        for inv in analyzed_invoices:
            status = inv.get('DeductibilityStatus', 'UNKNOWN')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print(f"[SUMMARY] Analysis breakdown: {status_counts}")
        print(f"[SUMMARY] Successfully processed {len(analyzed_invoices)}/{len(invoice_batch)} invoices")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'invoices_analyzed': len(analyzed_invoices),
                'batch_size': len(invoice_batch),
                'breakdown': status_counts
            }, cls=DecimalEncoder)
        }
        
    except Exception as e:
        error_msg = str(e)
        print(f"[ERROR] Invoice categorization failed: {error_msg}")
        
        # If throttled, raise specific error for Step Functions to retry
        if 'BEDROCK_THROTTLED' in error_msg or 'ThrottlingException' in error_msg:
            print(f"[ERROR] Bedrock throttling detected - Step Functions should retry this batch")
            raise Exception(f"THROTTLED: {error_msg}")
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': error_msg
            })
        }
