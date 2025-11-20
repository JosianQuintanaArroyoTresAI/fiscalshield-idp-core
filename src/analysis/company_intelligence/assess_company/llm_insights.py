"""
LLM-Powered Insights Generator for Company Risk Assessment

Uses Amazon Bedrock (Claude) to generate natural language explanations
for risk scores and provide actionable compliance recommendations.

Features:
- Prompt caching for cost optimization
- Structured output (JSON)
- Context-aware risk explanations
- Actionable recommendations
"""

import json
import logging
import os
from typing import Dict, List, Any, Optional
import boto3

logger = logging.getLogger()

# Initialize Bedrock client - use eu-central-1 for cross-region inference
bedrock_runtime = boto3.client('bedrock-runtime', region_name='eu-central-1')


class LLMInsightsGenerator:
    """
    Generate natural language insights for company risk assessments using Claude
    
    Uses prompt caching to reduce costs for repeated analysis patterns.
    Uses EU cross-region inference for optimal availability and performance.
    """
    
    def __init__(self):
        # Use EU cross-region inference profile for Claude 3.7 Sonnet
        # Supports prompt caching and provides optimal EU region routing
        self.model_id = "eu.anthropic.claude-3-7-sonnet-20250219-v1:0"
        self.max_tokens = 1500
        self.temperature = 0.3  # Low temperature for consistent, factual output
        
        # System prompt (cacheable - reused across all companies)
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """
        Build the system prompt that defines the LLM's role and output format.
        This prompt is cached to save costs across multiple company analyses.
        """
        return """You are an expert AML/KYC compliance analyst specializing in company due diligence and risk assessment. Your role is to analyze company intelligence data and provide clear, actionable insights for compliance officers.

Your analysis should:
1. Be factual and evidence-based
2. Identify both risks AND positive indicators
3. Explain the "why" behind risk scores
4. Provide specific, actionable recommendations
5. Use clear, professional language suitable for compliance reports
6. NEVER use emojis, icons, or informal symbols - your audience is highly educated UK accountants and compliance professionals

**OUTPUT FORMAT:**
Return a JSON object with the following structure:
{
  "governance_insight": "Brief explanation of director/governance risk (2-3 sentences)",
  "financial_insight": "Analysis of filing compliance and financial indicators (2-3 sentences)",
  "aml_insight": "Summary of sanctions/PEP screening results and implications (2-3 sentences)",
  "reputational_insight": "Assessment of media risk and public profile (2-3 sentences)",
  "overall_summary": "High-level risk summary and key takeaways (3-4 sentences)",
  "recommendations": [
    "Specific action item 1",
    "Specific action item 2"
  ],
  "red_flags": [
    "Any concerning patterns identified"
  ],
  "mitigating_factors": [
    "Any positive indicators that reduce risk"
  ]
}

**RISK CONTEXT:**
- LOW risk (0.0-0.39): Standard CDD sufficient, minimal concerns
- MEDIUM risk (0.4-0.69): Enhanced monitoring recommended, some risk factors present
- HIGH risk (0.7-1.0): Enhanced due diligence required, significant risk factors

Focus on patterns, context, and practical implications rather than just restating numbers."""
    
    def generate_insights(self, company_data: Dict, risk_results: Dict) -> Dict[str, Any]:
        """
        Generate LLM-powered insights for a company's risk assessment
        
        Args:
            company_data: Raw company data from Data Collection Stack
            risk_results: Calculated risk scores and flags from RiskCalculator
            
        Returns:
            Dictionary containing natural language insights for each category
        """
        try:
            # Prepare the user prompt with company-specific data
            user_prompt = self._build_user_prompt(company_data, risk_results)
            
            # Call Claude via Bedrock with prompt caching
            insights = self._call_bedrock(user_prompt)
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating LLM insights: {str(e)}")
            # Return fallback insights if LLM fails
            return self._generate_fallback_insights(risk_results)
    
    def _build_user_prompt(self, company_data: Dict, risk_results: Dict) -> str:
        """Build company-specific analysis prompt"""
        
        # Extract key data points
        company_number = company_data.get('company_number', 'Unknown')
        companies_house = company_data.get('companies_house', {})
        company_profile = companies_house.get('company_profile', {})
        officers_data = companies_house.get('officers', {})
        sanctions = company_data.get('sanctions', [])
        media = company_data.get('adverse_media', {})
        
        # Extract officer counts
        active_officers = len(officers_data.get('active_officers', []))
        resigned_officers = len(officers_data.get('resigned_officers', []))
        
        # Extract sanctions/PEP info
        sanctions_hits = [s for s in sanctions if s.get('data', {}).get('sanctions_matches', [])]
        pep_hits = [s for s in sanctions if s.get('data', {}).get('pep_matches', [])]
        
        # Extract filing data
        filing_data = companies_house.get('filing_history', {})
        filing_count = len(filing_data.get('items', []))
        
        # Build the prompt
        prompt = f"""Analyze the following company intelligence data and provide insights:

**COMPANY DETAILS:**
- Number: {company_number}
- Name: {company_profile.get('company_name', 'Unknown')}
- Status: {company_profile.get('company_status', 'Unknown')}
- Type: {company_profile.get('type', 'Unknown')}
- Incorporated: {company_profile.get('date_of_creation', 'Unknown')}
- Industry (SIC Codes): {self._format_sic_codes(company_profile.get('sic_codes_enriched', []))}

**GOVERNANCE DATA:**
- Active Officers: {active_officers}
- Resigned Officers: {resigned_officers}
- Director Turnover: {resigned_officers} historical resignations
- Recent Appointments: {self._get_recent_appointments(officers_data)}

**FINANCIAL INDICATORS:**
- Total Filings: {filing_count}
- Accounts Overdue: {company_profile.get('accounts', {}).get('overdue', False)}
- Confirmation Statement Overdue: {company_profile.get('confirmation_statement', {}).get('overdue', False)}
- Last Accounts Date: {company_profile.get('accounts', {}).get('last_accounts', {}).get('made_up_to', 'Unknown')}

**AML SCREENING:**
- Sanctions Screening Results: {len(sanctions_hits)} director(s) with sanctions matches
- PEP Screening Results: {len(pep_hits)} director(s) with PEP connections
- Sanctioned Directors: {self._format_sanctions_summary(sanctions_hits)}
- PEP Directors: {self._format_pep_summary(pep_hits)}

**REPUTATIONAL DATA:**
- Adverse Media Articles: {media.get('total_articles', 0)}
- Media Risk Score: {media.get('risk_score', 0.0)}
- Media Summary: {media.get('summary', 'No adverse media found')}

**CALCULATED RISK SCORES:**
- Overall Risk Level: {risk_results.get('risk_level', 'UNKNOWN')}
- Overall Risk Score: {risk_results.get('overall_risk_score', 0.0):.2f} / 1.00
- Critical Flags: {len(risk_results.get('critical_flags', []))}
- High Risk Flags: {len(risk_results.get('high_flags', []))}
- Medium Risk Flags: {len(risk_results.get('medium_flags', []))}
- Low Risk Flags: {len(risk_results.get('low_flags', []))}

**SPECIFIC FLAGS:**
{self._format_flags(risk_results)}

Based on this data, provide your analysis in the specified JSON format. Focus on:
1. What the numbers mean in practical compliance terms
2. Patterns or trends that increase/decrease risk
3. Context that explains the risk scores
4. Specific next steps for the compliance team"""
        
        return prompt
    
    def _format_sic_codes(self, sic_codes_enriched: list) -> str:
        """Format enriched SIC codes for prompt"""
        if not sic_codes_enriched:
            return "No SIC codes available"
        
        # Format as "CODE: Description"
        formatted = []
        for sic in sic_codes_enriched:
            code = sic.get('code', 'Unknown')
            description = sic.get('description', 'No description')
            formatted.append(f"{code}: {description}")
        
        return ", ".join(formatted)
    
    def _get_recent_appointments(self, officers_data: Dict) -> str:
        """Summarize recent officer appointments"""
        active_officers = officers_data.get('active_officers', [])
        if not active_officers:
            return "None"
        
        # Sort by appointment date (most recent first)
        sorted_officers = sorted(
            active_officers,
            key=lambda x: x.get('appointed_on', ''),
            reverse=True
        )
        
        recent_count = len([o for o in sorted_officers[:5] if o.get('appointed_on', '').startswith('2024') or o.get('appointed_on', '').startswith('2025')])
        return f"{recent_count} in past 12 months" if recent_count > 0 else "None recent"
    
    def _format_sanctions_summary(self, sanctions_hits: List[Dict]) -> str:
        """Format sanctions matches for prompt"""
        if not sanctions_hits:
            return "None"
        
        summaries = []
        for hit in sanctions_hits[:3]:  # Limit to first 3
            officer_name = hit.get('person_name', 'Unknown')
            matches = hit.get('data', {}).get('sanctions_matches', [])
            if matches:
                match_count = len(matches)
                summaries.append(f"{officer_name} ({match_count} match(es))")
        
        return ", ".join(summaries) if summaries else "None"
    
    def _format_pep_summary(self, pep_hits: List[Dict]) -> str:
        """Format PEP matches for prompt"""
        if not pep_hits:
            return "None"
        
        summaries = []
        for hit in pep_hits[:3]:  # Limit to first 3
            officer_name = hit.get('person_name', 'Unknown')
            matches = hit.get('data', {}).get('pep_matches', [])
            if matches:
                summaries.append(f"{officer_name}")
        
        return ", ".join(summaries) if summaries else "None"
    
    def _format_flags(self, risk_results: Dict) -> str:
        """Format risk flags for the prompt"""
        lines = []
        
        # Critical flags
        for flag in risk_results.get('critical_flags', [])[:3]:
            lines.append(f"  🚨 CRITICAL: {flag.get('description', 'Unknown')}")
        
        # High flags
        for flag in risk_results.get('high_flags', [])[:3]:
            lines.append(f"  ⚠️  HIGH: {flag.get('description', 'Unknown')}")
        
        # Medium flags
        for flag in risk_results.get('medium_flags', [])[:2]:
            lines.append(f"  ⚡ MEDIUM: {flag.get('description', 'Unknown')}")
        
        return "\n".join(lines) if lines else "  No significant flags"
    
    def _call_bedrock(self, user_prompt: str) -> Dict[str, Any]:
        """
        Call Claude via Bedrock with prompt caching enabled
        
        Uses Converse API with cache points for cost optimization
        """
        try:
            # Build messages with cache point after system prompt
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"text": user_prompt}
                    ]
                }
            ]
            
            # System configuration with cache point
            # The system prompt is static and can be cached
            system = [
                {
                    "text": self.system_prompt
                },
                {
                    "cachePoint": {
                        "type": "default"
                    }
                }
            ]
            
            # Call Converse API
            response = bedrock_runtime.converse(
                modelId=self.model_id,
                messages=messages,
                system=system,
                inferenceConfig={
                    "maxTokens": self.max_tokens,
                    "temperature": self.temperature
                }
            )
            
            # Extract response
            output_text = response['output']['message']['content'][0]['text']
            
            # Log cache performance
            usage = response.get('usage', {})
            logger.info(f"LLM insights generated - Cache read: {usage.get('cacheReadInputTokens', 0)}, Cache write: {usage.get('cacheWriteInputTokens', 0)}")
            
            # Parse JSON response
            try:
                # Extract JSON from response (might be wrapped in markdown)
                if '```json' in output_text:
                    json_start = output_text.find('```json') + 7
                    json_end = output_text.find('```', json_start)
                    output_text = output_text[json_start:json_end].strip()
                elif '```' in output_text:
                    json_start = output_text.find('```') + 3
                    json_end = output_text.find('```', json_start)
                    output_text = output_text[json_start:json_end].strip()
                
                insights = json.loads(output_text)
                return insights
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM JSON response: {e}")
                logger.debug(f"Raw response: {output_text}")
                # Return the text as-is in a structured format
                return {
                    "overall_summary": output_text,
                    "governance_insight": "Unable to generate structured insights",
                    "financial_insight": "",
                    "aml_insight": "",
                    "reputational_insight": "",
                    "recommendations": [],
                    "red_flags": [],
                    "mitigating_factors": []
                }
        
        except Exception as e:
            logger.error(f"Bedrock API error: {str(e)}")
            raise
    
    def _generate_fallback_insights(self, risk_results: Dict) -> Dict[str, Any]:
        """Generate basic rule-based insights if LLM fails"""
        risk_level = risk_results.get('risk_level', 'UNKNOWN')
        risk_score = risk_results.get('overall_risk_score', 0.0)
        
        fallback = {
            "governance_insight": "Unable to generate detailed governance insights at this time.",
            "financial_insight": "Unable to generate detailed financial insights at this time.",
            "aml_insight": "Unable to generate detailed AML insights at this time.",
            "reputational_insight": "Unable to generate detailed reputational insights at this time.",
            "overall_summary": f"Risk Level: {risk_level} (Score: {risk_score:.2f}). Please review the raw data for detailed assessment.",
            "recommendations": [
                "Review company profile and officer details",
                "Verify all sanctions and PEP screening results",
                "Monitor for any changes in company status"
            ],
            "red_flags": [flag.get('description', '') for flag in risk_results.get('critical_flags', [])[:3]],
            "mitigating_factors": []
        }
        
        return fallback
