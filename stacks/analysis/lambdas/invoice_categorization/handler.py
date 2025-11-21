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
bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-east-1')

# Environment variables
EXTRACTION_RESULTS_TABLE = os.environ.get('EXTRACTION_RESULTS_TABLE')
HMRC_GUIDANCE_TABLE = os.environ.get('HMRC_GUIDANCE_TABLE', 'fiscalshield-dc-dev-HMRCGuidance')
MODEL_ID = os.environ.get('MODEL_ID', 'anthropic.claude-3-5-sonnet-20241022-v2:0')


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
        company_events_table = dynamodb.Table(f'fiscalshield-dc-{os.environ.get("ENVIRONMENT", "dev")}-CompanyEvents')
        
        response = company_events_table.get_item(
            Key={'company_number': company_number}
        )
        
        if 'Item' not in response:
            print(f"[WARNING] No company data found for {company_number}")
            return {}
        
        company = response['Item']
        
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
        
        # Flag employee expenses for stricter scrutiny
        if invoice_type == 'EMPLOYEE_EXPENSE':
            scrutiny_flag = '\n⚠️ EMPLOYEE EXPENSE - Apply stricter scrutiny for potential personal benefit'
        
        invoice_text = f"""
Invoice #{idx}
Invoice ID: {invoice.get('InvoiceId', 'Unknown')}
Type: {invoice_type}{scrutiny_flag}
Supplier: {invoice.get('SupplierName') or invoice.get('VendorName') or 'Unknown'}
Amount: £{invoice.get('TotalAmount', '0')}
Date: {invoice.get('InvoiceDate') or 'Unknown'}
Description: {invoice.get('Description', 'No description available')}
Line Items: {invoice.get('LineItems', 'Not available')}
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
   - Clear explanation of your assessment
   - Reference specific BIM rules
   - Note any red flags or documentation requirements

REQUIRED XML FORMAT:

<batch_analysis>
  <invoice id="[EXACT_INVOICE_ID]">
    <deductibility_status>FULLY_DEDUCTIBLE|PARTIALLY_DEDUCTIBLE|NOT_DEDUCTIBLE|REQUIRES_REVIEW</deductibility_status>
    <deductibility_percentage>0-100 or null</deductibility_percentage>
    <bim_sections>BIM37000, BIM37600</bim_sections>
    <hmrc_concern>YES|NO</hmrc_concern>
    <reasoning>Detailed explanation referencing BIM guidance</reasoning>
    <documentation_required>List any additional documentation needed for audit defense</documentation_required>
    <recommended_action>APPROVE|REQUEST_DOCUMENTATION|APPORTION|REJECT</recommended_action>
  </invoice>
</batch_analysis>

Be conservative but fair. If genuinely unclear, mark REQUIRES_REVIEW rather than guessing.
"""
    
    return prompt


def invoke_bedrock_for_analysis(prompt: str) -> str:
    """Invoke Claude via Bedrock to analyze invoices"""
    
    try:
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4000,
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
        print(f"[ERROR] Bedrock invocation failed: {str(e)}")
        raise


def parse_analysis_with_regex(xml_result: str, invoice_batch: List[Dict]) -> List[Dict]:
    """
    Fallback regex-based XML parsing.
    """
    import re
    
    analyzed_invoices = []
    
    # Extract each <invoice> block
    invoice_pattern = r'<invoice id="([^"]+)">(.*?)</invoice>'
    matches = re.finditer(invoice_pattern, xml_result, re.DOTALL)
    
    for match in matches:
        invoice_id = match.group(1)
        invoice_xml = match.group(2)
        
        # Find corresponding invoice in batch
        original_invoice = next((inv for inv in invoice_batch if inv.get('InvoiceId') == invoice_id), None)
        
        if not original_invoice:
            print(f"[WARNING] No matching invoice for ID {invoice_id}")
            continue
        
        # Parse fields
        def extract_field(field_name):
            pattern = f'<{field_name}>(.*?)</{field_name}>'
            match = re.search(pattern, invoice_xml, re.DOTALL)
            return match.group(1).strip() if match else None
        
        # Add analysis results to invoice
        analyzed_invoice = original_invoice.copy()
        analyzed_invoice.update({
            'DeductibilityStatus': extract_field('deductibility_status'),
            'DeductibilityPercentage': extract_field('deductibility_percentage'),
            'BIMSections': extract_field('bim_sections'),
            'HMRCConcern': extract_field('hmrc_concern') == 'YES',
            'DeductibilityReasoning': extract_field('reasoning'),
            'DocumentationRequired': extract_field('documentation_required'),
            'RecommendedAction': extract_field('recommended_action'),
            'AnalysisStatus': 'ANALYZED',
            'AnalyzedAt': int(time.time()),
            'ModelUsed': MODEL_ID
        })
        
        analyzed_invoices.append(analyzed_invoice)
    
    return analyzed_invoices


def parse_analysis_from_xml(xml_result: str, invoice_batch: List[Dict]) -> List[Dict]:
    """
    Parse XML analysis results with proper XML parsing and regex fallback.
    Returns list of invoices with analysis fields added.
    """
    import xml.etree.ElementTree as ET
    
    analyzed_invoices = []
    
    try:
        # Try to parse as proper XML first
        root = ET.fromstring(f"<root>{xml_result}</root>")
        
        for invoice_elem in root.findall('.//invoice'):
            invoice_id = invoice_elem.get('id')
            
            # Find corresponding invoice in batch
            original_invoice = next((inv for inv in invoice_batch if inv.get('InvoiceId') == invoice_id), None)
            
            if not original_invoice:
                print(f"[WARNING] No matching invoice for ID {invoice_id}")
                continue
            
            # Parse fields safely
            def get_text(elem, tag, default=None):
                child = elem.find(tag)
                return child.text.strip() if child is not None and child.text else default
            
            analyzed_invoice = original_invoice.copy()
            analyzed_invoice.update({
                'DeductibilityStatus': get_text(invoice_elem, 'deductibility_status'),
                'DeductibilityPercentage': get_text(invoice_elem, 'deductibility_percentage'),
                'BIMSections': get_text(invoice_elem, 'bim_sections'),
                'HMRCConcern': get_text(invoice_elem, 'hmrc_concern') == 'YES',
                'DeductibilityReasoning': get_text(invoice_elem, 'reasoning'),
                'DocumentationRequired': get_text(invoice_elem, 'documentation_required'),
                'RecommendedAction': get_text(invoice_elem, 'recommended_action'),
                'AnalysisStatus': 'ANALYZED',
                'AnalyzedAt': int(time.time()),
                'ModelUsed': MODEL_ID
            })
            
            analyzed_invoices.append(analyzed_invoice)
        
        print(f"[INFO] Successfully parsed {len(analyzed_invoices)} invoice analyses using XML parser")
        
    except ET.ParseError as e:
        print(f"[WARNING] XML parsing failed: {str(e)}, falling back to regex")
        analyzed_invoices = parse_analysis_with_regex(xml_result, invoice_batch)
        print(f"[INFO] Successfully parsed {len(analyzed_invoices)} invoice analyses using regex fallback")
    
    return analyzed_invoices


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
    
    return True


def update_invoices_in_dynamodb(analyzed_invoices: List[Dict]):
    """Update invoices in ExtractionResultsTable with analysis results"""
    
    extraction_table = dynamodb.Table(EXTRACTION_RESULTS_TABLE)
    
    for invoice in analyzed_invoices:
        try:
            # Validate analysis results
            if not validate_analysis(invoice):
                print(f"[WARNING] Skipping invalid analysis for invoice {invoice.get('InvoiceId')}")
                continue
            
            pk = invoice.get('PK')
            sk = invoice.get('SK')
            
            if not pk or not sk:
                print(f"[WARNING] Invoice missing PK/SK: {invoice.get('InvoiceId')}")
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
        
        # Fetch company context for industry-aware analysis
        company_number = event.get('company_number')
        company_context = fetch_company_context(company_number) if company_number else None
        
        # Fetch BIM guidance from Data Collection stack
        bim_guidance = fetch_bim_guidance()
        
        # Create analysis prompt with company context
        prompt = create_invoice_analysis_prompt(invoice_batch, bim_guidance, company_context)
        
        # Invoke Claude for analysis
        print("[INFO] Invoking Claude for invoice analysis...")
        xml_result = invoke_bedrock_for_analysis(prompt)
        
        # Parse results
        analyzed_invoices = parse_analysis_from_xml(xml_result, invoice_batch)
        
        # Update DynamoDB
        update_invoices_in_dynamodb(analyzed_invoices)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'invoices_analyzed': len(analyzed_invoices),
                'batch_size': len(invoice_batch)
            }, cls=DecimalEncoder)
        }
        
    except Exception as e:
        print(f"[ERROR] Invoice categorization failed: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': str(e)
            })
        }
