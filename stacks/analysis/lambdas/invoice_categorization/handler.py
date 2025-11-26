"""
Invoice Categorization Lambda - TWO-STAGE ARCHITECTURE
Stage 1: Quick classification (all invoices) → DynamoDB update
Stage 2: Deep compliance testing (filtered subset) → DynamoDB update

Implements Priority 2A from improvement recommendations.
"""

import json
import boto3
import os
import time
from typing import Dict, List, Any, Tuple
from decimal import Decimal

# AWS clients
dynamodb = boto3.resource('dynamodb')
bedrock_runtime = boto3.client('bedrock-runtime', region_name='eu-west-1')

# Environment variables
EXTRACTION_RESULTS_TABLE = os.environ.get('EXTRACTION_RESULTS_TABLE')
COMPANY_EVENTS_TABLE = os.environ.get('COMPANY_EVENTS_TABLE', 'fiscalshield-dc-dev-CompanyEvents')
MODEL_ID = os.environ.get('MODEL_ID', 'eu.anthropic.claude-3-5-sonnet-20240620-v1:0')
MAX_BATCH_SIZE = 10
RECOMMENDED_BATCH_SIZE = 8
MAX_RETRY_ATTEMPTS = 3


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder for DynamoDB Decimal types"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


def fetch_company_context(company_number: str) -> Dict[str, Any]:
    """Fetch company context for industry-aware analysis"""
    try:
        company_events_table = dynamodb.Table(COMPANY_EVENTS_TABLE)
        response = company_events_table.query(
            KeyConditionExpression='company_number = :cn',
            ExpressionAttributeValues={':cn': company_number},
            ScanIndexForward=False,
            Limit=1
        )
        
        if not response.get('Items'):
            return {}
        
        company = response['Items'][0]
        context = {
            'company_name': company.get('company_name', 'Unknown'),
            'industry': f"SIC {company.get('sic_codes', [''])[0]}" if company.get('sic_codes') else 'Unknown'
        }
        
        print(f"[INFO] Company: {context['company_name']} ({context['industry']})")
        return context
        
    except Exception as e:
        print(f"[WARNING] Failed to fetch company context: {str(e)}")
        return {}


def create_stage1_classification_prompt(invoice_batch: List[Dict], company_context: Dict = None) -> str:
    """
    STAGE 1: Quick classification - streamlined for speed.
    Classifies all invoices and identifies which need deep testing.
    """
    
    # Minimal context
    context_line = f"Company: {company_context.get('company_name', 'Unknown')} | Industry: {company_context.get('industry', 'Unknown')}\n" if company_context else ""
    
    # Format invoices - minimal info
    invoice_list = []
    for idx, invoice in enumerate(invoice_batch, 1):
        desc = invoice.get('Description', 'None')
        if len(desc) > 80:
            desc = desc[:77] + "..."
        invoice_text = f"{idx}. ID:{invoice.get('InvoiceId')} | Type:{invoice.get('InvoiceType')} | Supplier:{invoice.get('SupplierName') or invoice.get('VendorName') or 'Unknown'} | £{invoice.get('TotalAmount', 0)} | Desc:{desc}"
        invoice_list.append(invoice_text)
    
    invoices_text = "\n".join(invoice_list)
    
    prompt = f"""UK tax accountant: Quick expense classification.

{context_line}
INVOICES:
{invoices_text}

For each invoice:
1. Basic deductibility: FULLY_DEDUCTIBLE (100%), NOT_DEDUCTIBLE (0%), or REQUIRES_REVIEW (null)
2. Needs deep testing?: true if EXPENSE_CLAIM with unclear deductibility, false otherwise

Rules:
- SUPPLIER_INVOICE for business goods/services → FULLY_DEDUCTIBLE, needs_deep_testing: false
- Obvious personal (gym, personal clothing) → NOT_DEDUCTIBLE, needs_deep_testing: false  
- EXPENSE_CLAIM or unclear → REQUIRES_REVIEW, needs_deep_testing: true

JSON (no markdown):
{{
  "classifications": [
    {{
      "invoice_id": "[ID]",
      "status": "FULLY_DEDUCTIBLE|NOT_DEDUCTIBLE|REQUIRES_REVIEW",
      "percentage": 100|0|null,
      "needs_deep_testing": true|false,
      "reason": "Brief"
    }}
  ]
}}"""
    
    return prompt


def calculate_hmrc_risk(invoice: Dict) -> str:
    """
    Programmatic HMRC risk calculation based on deductibility and test results.
    Returns: HIGH, MEDIUM, or LOW
    """
    deductibility_status = invoice.get('DeductibilityStatus', '')
    deductibility_pct = invoice.get('DeductibilityPercentage')
    
    # HIGH RISK triggers
    high_risk_triggers = [
        deductibility_status == 'NOT_DEDUCTIBLE',
        invoice.get('Test7_Duality') == 'FAIL',  # Dual purpose - personal element
        invoice.get('Test2_Entertainment') == 'CLIENT_ENTERTAINMENT',  # Banned
        invoice.get('Test5_StatutoryBan') in ['PENALTIES', 'FINES'],  # Statutory ban
    ]
    
    if any(high_risk_triggers):
        return 'HIGH'
    
    # MEDIUM RISK triggers
    medium_risk_triggers = [
        deductibility_status == 'PARTIALLY_DEDUCTIBLE',
        deductibility_status == 'REQUIRES_REVIEW',
        invoice.get('Test1_WhollyExclusively') == 'FAIL',
        invoice.get('Test3_Travel') == 'COMMUTING',  # Not allowed
        invoice.get('Test6_MixedUse') == 'APPORTIONABLE',  # Needs careful split
        deductibility_pct and deductibility_pct < 100 and deductibility_pct > 0,
    ]
    
    if any(medium_risk_triggers):
        return 'MEDIUM'
    
    # LOW RISK - fully deductible with clean tests
    return 'LOW'


def create_stage2_deep_testing_prompt(invoice_batch: List[Dict], company_context: Dict = None) -> str:
    """
    STAGE 2: Deep compliance testing - only for invoices needing detailed analysis.
    Condensed BIM guidance, full 7-test framework.
    """
    
    # Condensed BIM guidance (key rules only - ~300 tokens vs 800)
    condensed_bim = """BIM37000 - Wholly & Exclusively:
- Expense must be solely for business
- Entertainment: Staff OK (S45(2)), Client banned (S45)
- Travel: Business trips OK (S54), commuting banned (S38 ITEPA)
- Training: Work-related OK (S74), retraining not OK
- Penalties/fines: Banned (S1304)
- Mixed use: Apportion by business % (S54(2))
- Dual purpose (Mallalieu): Business suit, gym = personal (100% disallowed)"""
    
    context_line = f"Company: {company_context.get('company_name')} | Industry: {company_context.get('industry')}\n" if company_context else ""
    
    # Format invoices
    invoice_list = []
    for idx, invoice in enumerate(invoice_batch, 1):
        invoice_type = invoice.get('InvoiceType', 'UNKNOWN')
        tests_note = "Apply 7 tests" if invoice_type == 'EXPENSE_CLAIM' else "Test 1 only"
        
        invoice_text = f"""{idx}. ID:{invoice.get('InvoiceId')}
Type: {invoice_type} | Supplier: {invoice.get('SupplierName') or invoice.get('VendorName')}
Amount: £{invoice.get('TotalAmount')} | Desc: {invoice.get('Description', 'None')[:150]}
{tests_note}: Wholly/exclusively? Entertainment? Travel? Training? Penalties? Mixed use? Dual purpose?"""
        invoice_list.append(invoice_text)
    
    invoices_text = "\n---\n".join(invoice_list)
    
    prompt = f"""UK tax accountant: Deep compliance testing.

{context_line}
{condensed_bim}

INVOICES:
{invoices_text}

For each invoice, apply compliance tests and determine:
- Final deductibility status
- Percentage (0-100 or null)
- Test results (PASS/FAIL, specific outcomes)
- Addback amount if any

JSON (no markdown):
{{
  "analyses": [
    {{
      "invoice_id": "[ID]",
      "status": "FULLY_DEDUCTIBLE|PARTIALLY_DEDUCTIBLE|NOT_DEDUCTIBLE|REQUIRES_REVIEW",
      "percentage": 0-100|null,
      "reasoning": "Brief",
      "bim_sections": "BIM37000",
      "tests": {{
        "test_1": {{"result": "PASS|FAIL", "reasoning": "..."}},
        "test_2": {{"result": "NOT_APPLICABLE|STAFF_ENTERTAINMENT|CLIENT_ENTERTAINMENT"}},
        "test_3": {{"result": "NOT_APPLICABLE|BUSINESS_TRAVEL|COMMUTING"}},
        "test_4": {{"result": "NOT_APPLICABLE|WORK_RELATED|PERSONAL_DEVELOPMENT"}},
        "test_5": {{"result": "NOT_APPLICABLE|PENALTIES|DEPRECIATION"}},
        "test_6": {{"result": "NOT_APPLICABLE|APPORTIONABLE|NO_MIXED_USE", "business_pct": 0-100}},
        "test_7": {{"result": "PASS|FAIL"}},
        "addback_amount": "0.00"
      }}
    }}
  ]
}}"""
    
    return prompt


def invoke_bedrock(prompt: str, stage: str, max_retries: int = 3) -> str:
    """Invoke Claude via Bedrock with retry logic"""
    
    estimated_tokens = len(prompt) // 4
    print(f"[{stage}] Input tokens: ~{estimated_tokens}")
    
    for attempt in range(max_retries):
        try:
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4000 if stage == "STAGE1" else 8000,  # Stage 1 needs less output tokens
                "temperature": 0,
                "messages": [{"role": "user", "content": prompt}]
            }
            
            response = bedrock_runtime.invoke_model(
                modelId=MODEL_ID,
                body=json.dumps(request_body)
            )
            
            response_body = json.loads(response['body'].read())
            result_text = response_body['content'][0]['text']
            
            print(f"[{stage}] Response preview: {result_text[:200]}...")
            return result_text
            
        except Exception as e:
            error_msg = str(e)
            is_throttle = 'ThrottlingException' in error_msg or 'TooManyRequestsException' in error_msg
            
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"[{stage}] Retry {attempt + 1}/{max_retries} in {wait_time}s...")
                time.sleep(wait_time)
            else:
                if is_throttle:
                    raise Exception(f"BEDROCK_THROTTLED: {error_msg}")
                raise


def parse_stage1_classification(json_result: str, invoice_batch: List[Dict]) -> List[Dict]:
    """Parse Stage 1 classification results with per-invoice error handling"""
    classified_invoices = []
    failed_invoices = []
    
    try:
        json_text = json_result.strip()
        if '```' in json_text:
            json_text = json_text.split('```json')[-1].split('```')[0]
        json_text = json_text.strip()
        
        data = json.loads(json_text)
        classifications = data.get('classifications', [])
        
        for classification in classifications:
            try:
                invoice_id = classification.get('invoice_id')
                original_invoice = next((inv for inv in invoice_batch if inv.get('InvoiceId') == invoice_id), None)
                
                if not original_invoice:
                    print(f"[STAGE1] No match for {invoice_id}")
                    continue
                
                classified_invoice = original_invoice.copy()
                classified_invoice.update({
                    'DeductibilityStatus': classification.get('status'),
                    'DeductibilityPercentage': classification.get('percentage'),
                    'DeductibilityReasoning': classification.get('reason'),
                    'NeedsDeepTesting': classification.get('needs_deep_testing', False),
                    'AnalysisStatus': 'ANALYZED',
                    'AnalyzedAt': int(time.time()),
                    'ModelUsed': MODEL_ID,
                    'AnalysisStage': 'STAGE1_CLASSIFICATION'
                })
                
                classified_invoices.append(classified_invoice)
                
            except Exception as invoice_error:
                print(f"[STAGE1] Failed to process invoice {classification.get('invoice_id', 'unknown')}: {str(invoice_error)}")
                # Mark invoice as failed but continue processing others
                if original_invoice:
                    failed_invoice = original_invoice.copy()
                    failed_invoice.update({
                        'AnalysisStatus': 'FAILED',
                        'AnalysisError': f"Stage 1 parsing error: {str(invoice_error)}",
                        'AnalyzedAt': int(time.time()),
                        'AnalysisStage': 'STAGE1_CLASSIFICATION'
                    })
                    failed_invoices.append(failed_invoice)
        
        print(f"[STAGE1] Classified {len(classified_invoices)}/{len(invoice_batch)} invoices, {len(failed_invoices)} failed")
        return classified_invoices + failed_invoices  # Return both successful and failed
        
    except Exception as e:
        print(f"[ERROR] Stage 1 parsing completely failed: {str(e)}")
        # Mark all invoices as failed if JSON parsing fails completely
        for invoice in invoice_batch:
            failed_invoice = invoice.copy()
            failed_invoice.update({
                'AnalysisStatus': 'FAILED',
                'AnalysisError': f"Stage 1 JSON parsing failed: {str(e)}",
                'AnalyzedAt': int(time.time()),
                'AnalysisStage': 'STAGE1_CLASSIFICATION'
            })
            failed_invoices.append(failed_invoice)
        return failed_invoices


def parse_stage2_deep_testing(json_result: str, invoice_batch: List[Dict]) -> List[Dict]:
    """Parse Stage 2 deep testing results with per-invoice error handling"""
    analyzed_invoices = []
    failed_invoices = []
    
    try:
        json_text = json_result.strip()
        if '```' in json_text:
            json_text = json_text.split('```json')[-1].split('```')[0]
        json_text = json_text.strip()
        
        data = json.loads(json_text)
        analyses = data.get('analyses', [])
        
        for analysis in analyses:
            try:
                invoice_id = analysis.get('invoice_id')
                original_invoice = next((inv for inv in invoice_batch if inv.get('InvoiceId') == invoice_id), None)
                
                if not original_invoice:
                    print(f"[STAGE2] No match for {invoice_id}")
                    continue
                
                analyzed_invoice = original_invoice.copy()
                analyzed_invoice.update({
                    'DeductibilityStatus': analysis.get('status'),
                    'DeductibilityPercentage': analysis.get('percentage'),
                    'DeductibilityReasoning': analysis.get('reasoning'),
                    'BIMSections': analysis.get('bim_sections'),
                    'AnalysisStatus': 'ANALYZED',
                    'AnalyzedAt': int(time.time()),
                    'ModelUsed': MODEL_ID,
                    'AnalysisStage': 'STAGE2_DEEP_TESTING'
                })
                
                # Parse compliance tests
                tests = analysis.get('tests', {})
                if tests:
                    test1 = tests.get('test_1', {})
                    analyzed_invoice.update({
                        'Test1_WhollyExclusively': test1.get('result'),
                        'Test1_Reasoning': test1.get('reasoning'),
                    })
                    
                    # Tests 2-7 (for EXPENSE_CLAIM)
                    for test_num in range(2, 8):
                        test_key = f'test_{test_num}'
                        test_data = tests.get(test_key, {})
                        if test_data:
                            if test_num == 2:
                                analyzed_invoice['Test2_Entertainment'] = test_data.get('result')
                            elif test_num == 3:
                                analyzed_invoice['Test3_Travel'] = test_data.get('result')
                            elif test_num == 4:
                                analyzed_invoice['Test4_Training'] = test_data.get('result')
                            elif test_num == 5:
                                analyzed_invoice['Test5_StatutoryBan'] = test_data.get('result')
                            elif test_num == 6:
                                analyzed_invoice['Test6_MixedUse'] = test_data.get('result')
                                analyzed_invoice['Test6_BusinessPercentage'] = test_data.get('business_pct')
                            elif test_num == 7:
                                analyzed_invoice['Test7_Duality'] = test_data.get('result')
                    
                    # Addback
                    analyzed_invoice['AddbackAmount'] = tests.get('addback_amount')
                
                # Calculate HMRC risk programmatically based on test results
                analyzed_invoice['HMRCRisk'] = calculate_hmrc_risk(analyzed_invoice)
                
                analyzed_invoices.append(analyzed_invoice)
                
            except Exception as invoice_error:
                print(f"[STAGE2] Failed to process invoice {analysis.get('invoice_id', 'unknown')}: {str(invoice_error)}")
                # Keep Stage 1 results but mark Stage 2 as failed
                if original_invoice:
                    failed_invoice = original_invoice.copy()
                    failed_invoice.update({
                        'AnalysisError': f"Stage 2 parsing error: {str(invoice_error)}",
                        'AnalyzedAt': int(time.time()),
                        'AnalysisStage': 'STAGE2_DEEP_TESTING_FAILED'
                    })
                    failed_invoices.append(failed_invoice)
        
        print(f"[STAGE2] Deep tested {len(analyzed_invoices)}/{len(invoice_batch)} invoices, {len(failed_invoices)} failed")
        return analyzed_invoices + failed_invoices  # Return both successful and failed
        
    except Exception as e:
        print(f"[ERROR] Stage 2 parsing completely failed: {str(e)}")
        # Keep Stage 1 results for all invoices but log Stage 2 failure
        for invoice in invoice_batch:
            failed_invoice = invoice.copy()
            failed_invoice.update({
                'AnalysisError': f"Stage 2 JSON parsing failed: {str(e)}",
                'AnalyzedAt': int(time.time()),
                'AnalysisStage': 'STAGE2_DEEP_TESTING_FAILED'
            })
            failed_invoices.append(failed_invoice)
        return failed_invoices


def update_invoices_in_dynamodb(invoices: List[Dict], stage: str):
    """Update invoices in DynamoDB after analysis stage with per-invoice error handling"""
    
    extraction_table = dynamodb.Table(EXTRACTION_RESULTS_TABLE)
    success_count = 0
    failure_count = 0
    
    for invoice in invoices:
        try:
            pk = invoice.get('PK')
            sk = invoice.get('SK')
            
            if not pk or not sk:
                print(f"[{stage}] Missing PK/SK for {invoice.get('InvoiceId')}")
                failure_count += 1
                continue
            
            # Handle null percentage
            percentage = invoice.get('DeductibilityPercentage')
            if percentage and percentage not in ['null', '']:
                try:
                    percentage = int(percentage)
                except (ValueError, TypeError):
                    percentage = None
            else:
                percentage = None
            
            # Build update expression
            update_expr = 'SET AnalysisStatus = :status, AnalyzedAt = :analyzed_at, ModelUsed = :model, AnalysisStage = :stage'
            expr_values = {
                ':status': 'ANALYZED',
                ':analyzed_at': invoice.get('AnalyzedAt'),
                ':model': MODEL_ID,
                ':stage': stage
            }
            
            # Add deductibility fields
            if invoice.get('DeductibilityStatus'):
                update_expr += ', DeductibilityStatus = :deduct_status'
                expr_values[':deduct_status'] = invoice.get('DeductibilityStatus')
            
            if percentage is not None:
                update_expr += ', DeductibilityPercentage = :percentage'
                expr_values[':percentage'] = percentage
            
            if invoice.get('DeductibilityReasoning'):
                update_expr += ', DeductibilityReasoning = :reasoning'
                expr_values[':reasoning'] = invoice.get('DeductibilityReasoning')
            
            if invoice.get('BIMSections'):
                update_expr += ', BIMSections = :bim'
                expr_values[':bim'] = invoice.get('BIMSections')
            
            # Add HMRC risk (both Stage 1 and Stage 2)
            if invoice.get('HMRCRisk'):
                update_expr += ', HMRCRisk = :hmrc_risk'
                expr_values[':hmrc_risk'] = invoice.get('HMRCRisk')
            
            # Add test results if present (Stage 2 only)
            if invoice.get('Test1_WhollyExclusively'):
                test_fields = []
                
                for field_name in ['Test1_WhollyExclusively', 'Test1_Reasoning',
                                   'Test2_Entertainment', 'Test3_Travel', 'Test4_Training',
                                   'Test5_StatutoryBan', 'Test6_MixedUse', 'Test6_BusinessPercentage',
                                   'Test7_Duality', 'AddbackAmount', 'HMRCRisk']:
                    if invoice.get(field_name) is not None:
                        test_fields.append(f'{field_name} = :{field_name}')
                        expr_values[f':{field_name}'] = invoice.get(field_name)
                
                if test_fields:
                    update_expr += ', ' + ', '.join(test_fields)
            
            # Update DynamoDB
            extraction_table.update_item(
                Key={'PK': pk, 'SK': sk},
                UpdateExpression=update_expr,
                ExpressionAttributeValues=expr_values
            )
            
            success_count += 1
            print(f"[{stage}] Updated {invoice.get('InvoiceId')} - {invoice.get('DeductibilityStatus')}")
            
        except Exception as e:
            failure_count += 1
            print(f"[ERROR] Failed to update {invoice.get('InvoiceId')}: {str(e)}")
            # Continue processing other invoices
    
    print(f"[{stage}] DynamoDB updates: {success_count} succeeded, {failure_count} failed")


def lambda_handler(event, context):
    """
    TWO-STAGE Lambda handler:
    Stage 1: Quick classification (all invoices) → DynamoDB update
    Stage 2: Deep compliance testing (filtered subset) → DynamoDB update
    """
    
    print(f"[INFO] Two-Stage Invoice Categorization Lambda invoked")
    print(f"[INFO] Event: {json.dumps(event, default=str)[:500]}...")
    
    try:
        invoice_batch = event.get('invoices', [])
        
        if not invoice_batch:
            return {'statusCode': 400, 'body': json.dumps({'error': 'No invoices in batch'})}
        
        print(f"[INFO] Processing batch of {len(invoice_batch)} invoices")
        
        # Fetch company context
        company_number = event.get('company_number')
        company_context = fetch_company_context(company_number) if company_number else None
        
        # ======================
        # STAGE 1: CLASSIFICATION
        # ======================
        print("\n[STAGE1] Starting quick classification...")
        stage1_prompt = create_stage1_classification_prompt(invoice_batch, company_context)
        stage1_result = invoke_bedrock(stage1_prompt, "STAGE1")
        classified_invoices = parse_stage1_classification(stage1_result, invoice_batch)
        
        if not classified_invoices:
            print("[ERROR] Stage 1 failed - no invoices classified")
            return {'statusCode': 500, 'body': json.dumps({'error': 'Stage 1 classification failed'})}
        
        # Calculate basic HMRC risk for Stage 1 invoices (before deep testing)
        for invoice in classified_invoices:
            if not invoice.get('NeedsDeepTesting', False):
                # Simple risk for supplier invoices that skip deep testing
                if invoice.get('DeductibilityStatus') == 'NOT_DEDUCTIBLE':
                    invoice['HMRCRisk'] = 'HIGH'
                elif invoice.get('DeductibilityStatus') == 'REQUIRES_REVIEW':
                    invoice['HMRCRisk'] = 'MEDIUM'
                else:
                    invoice['HMRCRisk'] = 'LOW'
        
        # Update DynamoDB after Stage 1
        print(f"[STAGE1] Updating DynamoDB with {len(classified_invoices)} classified invoices...")
        update_invoices_in_dynamodb(classified_invoices, "STAGE1_CLASSIFICATION")
        
        stage1_counts = {}
        for inv in classified_invoices:
            status = inv.get('DeductibilityStatus', 'UNKNOWN')
            stage1_counts[status] = stage1_counts.get(status, 0) + 1
        print(f"[STAGE1] Results: {stage1_counts}")
        
        # ======================
        # STAGE 2: DEEP TESTING
        # ======================
        # Filter invoices needing deep testing
        deep_testing_invoices = [inv for inv in classified_invoices if inv.get('NeedsDeepTesting', False)]
        
        if not deep_testing_invoices:
            print("[STAGE2] No invoices need deep testing - all done!")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'success': True,
                    'invoices_analyzed': len(classified_invoices),
                    'stage1_breakdown': stage1_counts,
                    'deep_tested': 0,
                    'message': 'All invoices classified in Stage 1'
                }, cls=DecimalEncoder)
            }
        
        print(f"\n[STAGE2] Starting deep testing for {len(deep_testing_invoices)} invoices...")
        stage2_prompt = create_stage2_deep_testing_prompt(deep_testing_invoices, company_context)
        stage2_result = invoke_bedrock(stage2_prompt, "STAGE2")
        deep_tested_invoices = parse_stage2_deep_testing(stage2_result, deep_testing_invoices)
        
        if not deep_tested_invoices:
            print("[WARNING] Stage 2 failed - keeping Stage 1 results")
        else:
            # Update DynamoDB with Stage 2 results (merges with Stage 1)
            print(f"[STAGE2] Updating DynamoDB with {len(deep_tested_invoices)} deep tested invoices...")
            update_invoices_in_dynamodb(deep_tested_invoices, "STAGE2_DEEP_TESTING")
            
            stage2_counts = {}
            for inv in deep_tested_invoices:
                status = inv.get('DeductibilityStatus', 'UNKNOWN')
                stage2_counts[status] = stage2_counts.get(status, 0) + 1
            print(f"[STAGE2] Results: {stage2_counts}")
        
        # ======================
        # SUMMARY
        # ======================
        total_analyzed = len(classified_invoices)
        deep_tested_count = len(deep_tested_invoices) if deep_tested_invoices else 0
        
        print(f"\n[SUMMARY] Total: {total_analyzed} | Stage 1 only: {total_analyzed - len(deep_testing_invoices)} | Stage 2: {deep_tested_count}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'invoices_analyzed': total_analyzed,
                'stage1_breakdown': stage1_counts,
                'deep_tested': deep_tested_count,
                'message': f'Two-stage analysis complete'
            }, cls=DecimalEncoder)
        }
        
    except Exception as e:
        error_msg = str(e)
        print(f"[ERROR] Two-stage categorization failed: {error_msg}")
        
        if 'BEDROCK_THROTTLED' in error_msg or 'ThrottlingException' in error_msg:
            raise Exception(f"THROTTLED: {error_msg}")
        
        return {
            'statusCode': 500,
            'body': json.dumps({'success': False, 'error': error_msg})
        }
