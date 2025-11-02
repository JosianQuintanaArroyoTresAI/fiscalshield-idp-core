"""
AML Report Generator Lambda
Purpose: Generate professional AML CDD reports using Amazon Bedrock (Claude)
Adapted for FiscalShield Analysis Stack
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from decimal import Decimal
import boto3
from botocore.exceptions import ClientError

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
bedrock_runtime = boto3.client('bedrock-runtime', region_name='eu-west-2')
s3_client = boto3.client('s3')

# Environment variables
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
REPORTS_BUCKET = os.environ.get('REPORTS_BUCKET')
COMPANY_INTELLIGENCE_TABLE = f'fiscalshield-analysis-{ENVIRONMENT}-CompanyIntelligence'
DC_COMPANY_EVENTS_TABLE = f'fiscalshield-dc-{ENVIRONMENT}-CompanyEvents'


class ReportGenerator:
    """Generates professional AML CDD reports using Claude via Amazon Bedrock"""
    
    def __init__(self):
        self.intelligence_table = dynamodb.Table(COMPANY_INTELLIGENCE_TABLE)
        self.company_events_table = dynamodb.Table(DC_COMPANY_EVENTS_TABLE)
        
        # Use Claude 3.5 Sonnet v2 for best performance
        self.model_id = "anthropic.claude-3-5-sonnet-20241022-v2:0"
        
        # System prompt for UK accountant context
        self.system_prompt = """You are a senior AML compliance officer and UK chartered accountant with deep expertise in Money Laundering Regulations 2017 (MLR 2017). 

Your role is to analyze Customer Due Diligence (CDD) screening results and produce professional, actionable reports for UK accounting firms.

Key principles:
- Write in professional but clear language suitable for ICAEW/ACCA members
- Reference specific MLR 2017 requirements where relevant
- Provide practical, actionable recommendations
- Highlight genuine risks while avoiding unnecessary alarm
- Consider proportionality - standard CDD for low risk, enhanced for high risk
- Focus on what the accountant needs to know to make an informed decision
- Be concise but thorough - typically 2-3 pages

Report structure should follow UK accounting firm standards with sections for:
1. Executive Summary
2. Entity Overview
3. Screening Results Analysis
4. Risk Assessment
5. Red Flags (if any)
6. CDD Recommendations
7. Required Actions

Always maintain professional skepticism while being fair and objective."""

    def retrieve_intelligence_data(self, company_number: str) -> Dict[str, Any]:
        """Retrieve intelligence data from Analysis Stack"""
        
        try:
            # Get intelligence assessment
            response = self.intelligence_table.get_item(
                Key={'company_number': company_number}
            )
            
            if 'Item' not in response:
                raise ValueError(f"No intelligence data found for company {company_number}")
            
            intelligence = response['Item']
            print(f"Retrieved intelligence data for {company_number}")
            
            # Also get raw company data from Data Collection Stack
            try:
                dc_response = self.company_events_table.get_item(
                    Key={'company_number': company_number}
                )
                raw_data = dc_response.get('Item', {})
            except Exception as e:
                print(f"Could not retrieve raw data from Data Collection: {str(e)}")
                raw_data = {}
            
            return {
                'intelligence': intelligence,
                'raw_data': raw_data,
                'company_number': company_number
            }
            
        except Exception as e:
            print(f"Failed to retrieve intelligence data: {str(e)}")
            raise
    
    def prepare_data_for_llm(self, data: Dict) -> str:
        """Format intelligence data into a structured prompt for the LLM"""
        
        def decimal_to_float(obj):
            """Convert Decimal objects to float for JSON serialization"""
            if isinstance(obj, Decimal):
                return float(obj)
            elif isinstance(obj, dict):
                return {k: decimal_to_float(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [decimal_to_float(item) for item in obj]
            return obj
        
        intelligence = decimal_to_float(data.get('intelligence', {}))
        raw_data = decimal_to_float(data.get('raw_data', {}))
        
        context_parts = []
        context_parts.append("=== COMPANY INTELLIGENCE DATA FOR AML REPORT ===\n")
        
        # Basic Company Info
        company_name = intelligence.get('company_name', 'Unknown')
        company_number = intelligence.get('company_number', 'Unknown')
        
        context_parts.append("--- COMPANY OVERVIEW ---")
        context_parts.append(f"Company Name: {company_name}")
        context_parts.append(f"Company Number: {company_number}")
        context_parts.append(f"Assessment Date: {intelligence.get('assessment_date', 'Unknown')}")
        context_parts.append(f"Data Age: {intelligence.get('data_age_hours', 0):.1f} hours")
        context_parts.append("")
        
        # Risk Assessment
        risk_assessment = intelligence.get('risk_assessment', {})
        context_parts.append("--- OVERALL RISK ASSESSMENT ---")
        context_parts.append(f"Risk Level: {risk_assessment.get('risk_level', 'LOW')}")
        context_parts.append(f"Risk Score: {risk_assessment.get('overall_risk_score', 0):.3f}")
        context_parts.append(f"\n{risk_assessment.get('summary', 'No summary available')}\n")
        
        flags_summary = risk_assessment.get('flags_summary', {})
        if flags_summary:
            context_parts.append(f"Total Flags: {flags_summary.get('total', 0)}")
            context_parts.append(f"  - Critical: {flags_summary.get('critical', 0)}")
            context_parts.append(f"  - High: {flags_summary.get('high', 0)}")
            context_parts.append(f"  - Medium: {flags_summary.get('medium', 0)}")
            context_parts.append(f"  - Low: {flags_summary.get('low', 0)}")
        
        if risk_assessment.get('sanctioned_directors'):
            context_parts.append(f"\n⚠️ SANCTIONED DIRECTORS: {', '.join(risk_assessment['sanctioned_directors'])}")
        
        if risk_assessment.get('pep_directors'):
            context_parts.append(f"⚠️ PEP DIRECTORS: {', '.join(risk_assessment['pep_directors'])}")
        
        context_parts.append("")
        
        # Governance
        governance = intelligence.get('governance', {})
        context_parts.append("--- GOVERNANCE STRUCTURE ---")
        context_parts.append(f"Company Status: {governance.get('company_status', 'Unknown')}")
        context_parts.append(f"Company Type: {governance.get('company_type', 'Unknown')}")
        context_parts.append(f"Total Officers: {governance.get('total_officers', 0)}")
        context_parts.append(f"Active Officers: {governance.get('active_officers', 0)}")
        context_parts.append(f"Director Stability: {governance.get('director_stability', 'Unknown')}")
        context_parts.append("")
        
        # Financial Compliance
        financial = intelligence.get('financial', {})
        context_parts.append("--- FINANCIAL COMPLIANCE ---")
        context_parts.append(f"Filing Compliance: {financial.get('filing_compliance', 'Unknown')}")
        context_parts.append(f"Accounts Overdue: {'Yes' if financial.get('accounts_overdue') else 'No'}")
        context_parts.append(f"Confirmation Statement Overdue: {'Yes' if financial.get('confirmation_statement_overdue') else 'No'}")
        context_parts.append("")
        
        # AML Screening Results
        aml = intelligence.get('aml', {})
        context_parts.append("--- AML SCREENING RESULTS ---")
        context_parts.append(f"Sanctions Screening: {aml.get('sanctions_screening', 'Not performed')}")
        
        if aml.get('sanctioned_directors'):
            context_parts.append("\nSANCTIONED INDIVIDUALS:")
            for director in aml.get('sanctioned_directors', []):
                context_parts.append(f"  - {director}")
        
        context_parts.append(f"\nPEP Screening: {aml.get('pep_screening', 'Not performed')}")
        
        if aml.get('pep_directors'):
            context_parts.append("\nPOLITICALLY EXPOSED PERSONS:")
            for director in aml.get('pep_directors', []):
                context_parts.append(f"  - {director}")
        
        context_parts.append(f"\nEnhanced Due Diligence Required: {'Yes' if aml.get('requires_enhanced_dd') else 'No'}")
        context_parts.append("")
        
        # Reputational
        reputational = intelligence.get('reputational', {})
        context_parts.append("--- REPUTATIONAL ANALYSIS ---")
        context_parts.append(f"Adverse Media Count: {reputational.get('adverse_media_count', 0)}")
        context_parts.append(f"Adverse Media Risk: {reputational.get('adverse_media_risk', 0):.3f}")
        context_parts.append(f"Has Adverse Media: {'Yes' if reputational.get('has_adverse_media') else 'No'}")
        context_parts.append("")
        
        # Critical and High Flags Detail
        critical_flags = risk_assessment.get('critical_flags', [])
        high_flags = risk_assessment.get('high_flags', [])
        
        if critical_flags:
            context_parts.append("--- CRITICAL FLAGS ---")
            for flag in critical_flags:
                context_parts.append(f"[CRITICAL] {flag.get('flag_type', 'Unknown')}")
                context_parts.append(f"  Description: {flag.get('description', 'No description')}")
                context_parts.append(f"  Source: {flag.get('source', 'Unknown')}")
                context_parts.append(f"  Score Impact: {flag.get('score_contribution', 0):.3f}")
                context_parts.append("")
        
        if high_flags:
            context_parts.append("--- HIGH RISK FLAGS ---")
            for flag in high_flags:
                context_parts.append(f"[HIGH] {flag.get('flag_type', 'Unknown')}")
                context_parts.append(f"  Description: {flag.get('description', 'No description')}")
                context_parts.append(f"  Source: {flag.get('source', 'Unknown')}")
                context_parts.append(f"  Score Impact: {flag.get('score_contribution', 0):.3f}")
                context_parts.append("")
        
        # Medium and Low flags summary
        medium_flags = risk_assessment.get('medium_flags', [])
        low_flags = risk_assessment.get('low_flags', [])
        
        if medium_flags:
            context_parts.append(f"--- MEDIUM RISK FLAGS ({len(medium_flags)} total) ---")
            for flag in medium_flags[:5]:  # Show first 5
                context_parts.append(f"  - {flag.get('flag_type', 'Unknown')}: {flag.get('description', 'No description')}")
            if len(medium_flags) > 5:
                context_parts.append(f"  ... and {len(medium_flags) - 5} more")
            context_parts.append("")
        
        if low_flags:
            context_parts.append(f"--- LOW RISK FLAGS ({len(low_flags)} total) ---")
            for flag in low_flags[:3]:  # Show first 3
                context_parts.append(f"  - {flag.get('flag_type', 'Unknown')}")
            if len(low_flags) > 3:
                context_parts.append(f"  ... and {len(low_flags) - 3} more")
            context_parts.append("")
        
        context_parts.append("=== END OF INTELLIGENCE DATA ===")
        
        return "\n".join(context_parts)
    
    def generate_report_with_claude(self, data: Dict) -> Dict[str, str]:
        """Generate report using Claude via Amazon Bedrock"""
        
        try:
            # Prepare data context
            data_context = self.prepare_data_for_llm(data)
            
            intelligence = data.get('intelligence', {})
            risk_assessment = intelligence.get('risk_assessment', {})
            
            company_name = intelligence.get('company_name', 'Unknown Company')
            company_number = intelligence.get('company_number', 'Unknown')
            risk_level = risk_assessment.get('risk_level', 'LOW')
            
            # Construct the prompt
            user_prompt = f"""Please analyze the following AML screening results and generate a comprehensive Customer Due Diligence (CDD) report for {company_name} (Company Number: {company_number}).

The overall risk assessment is: {risk_level}

{data_context}

Please generate a professional report following this structure:

# AML Customer Due Diligence Report

## Executive Summary
[Provide a concise 2-3 paragraph summary suitable for senior partners. Include the overall risk rating, key findings, and primary recommendation (Accept/Enhanced DD/Reject)]

## Entity Overview
[Summarize the company's basic information, structure, and business activities]

## Screening Results

### Companies House Analysis
[Analyze the corporate structure, compliance history, and any red flags from the official registry]

### Sanctions and PEP Screening
[Detail any sanctions or PEP matches, or confirm clean results]

### Adverse Media Analysis
[Discuss any adverse media findings or confirm none found]

## Risk Assessment

### Overall Risk Classification
[Explain the {risk_level} risk rating and its implications under MLR 2017]

### Contributing Risk Factors
[Analyze each significant risk factor and its weight in the overall assessment]

### Mitigating Factors
[Identify any factors that reduce risk or provide context]

## Red Flags and Concerns
[List and explain any critical or high-severity flags requiring attention. If none, state clearly that no significant red flags were identified]

## CDD Recommendations

### Required Level of Due Diligence
[Specify whether Standard CDD, Simplified DD, or Enhanced DD is required]

### Specific Measures Required
[List concrete actions the accountant must take, such as:
- Documents to request
- Information to verify
- Ongoing monitoring requirements
- Approval levels required]

### Questions for Client
[Provide 3-5 specific questions the accountant should ask during onboarding to address any concerns or gaps]

## Compliance Notes

### MLR 2017 Considerations
[Reference specific MLR 2017 requirements relevant to this case]

### Record Keeping
[Note what documentation must be retained and for how long]

### Next Review Date
[Recommend when this screening should be refreshed based on risk level]

## Conclusion
[Final paragraph with clear accept/reject/enhanced DD recommendation and rationale]

---

**Report Generated:** {datetime.now().strftime('%d %B %Y at %H:%M UTC')}
**Screening Reference:** {company_number}
**Valid Until:** [Recommend validity period based on risk level - typically 12 months for LOW, 6 months for MEDIUM, immediate review for HIGH]

Please write in a professional but accessible style suitable for UK chartered accountants. Be thorough but concise. Focus on actionable insights."""

            # Call Claude via Bedrock
            print(f"Calling Claude {self.model_id} to generate report")
            
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4096,
                "temperature": 0.3,  # Lower temperature for more consistent, professional output
                "system": self.system_prompt,
                "messages": [
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ]
            }
            
            response = bedrock_runtime.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )
            
            response_body = json.loads(response['body'].read())
            
            # Extract the generated report
            report_markdown = response_body['content'][0]['text']
            
            # Get token usage for metrics
            usage = response_body.get('usage', {})
            input_tokens = usage.get('input_tokens', 0)
            output_tokens = usage.get('output_tokens', 0)
            
            print(f"Report generated successfully. Tokens: {input_tokens} input, {output_tokens} output")
            
            return {
                'markdown': report_markdown,
                'model_used': self.model_id,
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'company_name': company_name,
                'company_number': company_number,
                'risk_level': risk_level
            }
            
        except Exception as e:
            print(f"Failed to generate report with Claude: {str(e)}")
            raise
    
    def store_report(self, company_number: str, report_data: Dict) -> str:
        """Store generated report in S3"""
        
        try:
            report_id = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            timestamp = datetime.now().isoformat()
            
            if not REPORTS_BUCKET:
                raise ValueError("REPORTS_BUCKET environment variable not set")
            
            # Store markdown report in S3
            s3_key = f"aml-reports/{company_number}/{report_id}.md"
            s3_client.put_object(
                Bucket=REPORTS_BUCKET,
                Key=s3_key,
                Body=report_data['markdown'].encode('utf-8'),
                ContentType='text/markdown',
                Metadata={
                    'company_number': company_number,
                    'report_id': report_id,
                    'generated_at': timestamp,
                    'risk_level': report_data.get('risk_level', 'LOW'),
                    'company_name': report_data.get('company_name', 'Unknown')
                }
            )
            
            s3_url = f"s3://{REPORTS_BUCKET}/{s3_key}"
            print(f"Report stored in S3: {s3_url}")
            
            # Generate presigned URL (valid for 7 days)
            presigned_url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': REPORTS_BUCKET, 'Key': s3_key},
                ExpiresIn=604800  # 7 days
            )
            
            return {
                'report_id': report_id,
                's3_url': s3_url,
                's3_key': s3_key,
                'presigned_url': presigned_url
            }
            
        except Exception as e:
            print(f"Failed to store report: {str(e)}")
            raise


def lambda_handler(event, context):
    """
    Main Lambda handler for AML Report Generation
    
    Expected input from API Gateway:
    {
        "pathParameters": {
            "company_number": "12345678"
        }
    }
    """
    
    try:
        print(f"Event: {json.dumps(event)}")
        
        # Extract company number from path parameters
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
        
        print(f"Starting AML report generation for company {company_number}")
        
        generator = ReportGenerator()
        
        # Step 1: Retrieve intelligence data
        data = generator.retrieve_intelligence_data(company_number)
        
        # Step 2: Generate report with Claude
        report_data = generator.generate_report_with_claude(data)
        
        # Step 3: Store report in S3
        storage_info = generator.store_report(company_number, report_data)
        
        # Prepare response
        response_data = {
            'success': True,
            'company_number': company_number,
            'company_name': report_data.get('company_name', 'Unknown'),
            'risk_level': report_data.get('risk_level', 'LOW'),
            'report_id': storage_info['report_id'],
            's3_key': storage_info['s3_key'],
            'download_url': storage_info['presigned_url'],
            'model_used': report_data.get('model_id'),
            'tokens_used': {
                'input': report_data.get('input_tokens', 0),
                'output': report_data.get('output_tokens', 0),
                'total': report_data.get('input_tokens', 0) + report_data.get('output_tokens', 0)
            },
            'generated_at': datetime.now().isoformat(),
            'valid_until': (datetime.now().timestamp() + 604800) * 1000  # 7 days in milliseconds
        }
        
        print(f"Report generation completed for {company_number}: {storage_info['report_id']}")
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'POST,OPTIONS'
            },
            'body': json.dumps(response_data)
        }
        
    except ValueError as e:
        print(f"Validation error: {str(e)}")
        return {
            'statusCode': 404,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': False,
                'error': str(e)
            })
        }
    
    except Exception as e:
        print(f"Report generation failed: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': False,
                'error': f'Failed to generate report: {str(e)}'
            })
        }
