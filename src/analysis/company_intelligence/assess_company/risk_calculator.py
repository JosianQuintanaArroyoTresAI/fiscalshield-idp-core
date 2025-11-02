"""
Risk Calculator for Company Intelligence

Analyzes data from Data Collection Stack and calculates aggregate risk scores.
Based on AML risk aggregation logic with weighted scoring algorithm.
"""

import logging
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime

logger = logging.getLogger()


class RiskCalculator:
    """
    Calculate company risk scores based on multiple data sources
    
    Uses weighted scoring algorithm to aggregate:
    - Sanctions matches (critical)
    - PEP connections (high)
    - Adverse media (high-medium)
    - Companies House flags (high/medium/low severity)
    """
    
    def __init__(self):
        # Risk scoring weights (from AML README)
        self.risk_weights = {
            'sanctions_match': 0.95,      # Critical - automatic high risk
            'current_pep': 0.70,          # High
            'adverse_media': 0.60,        # High-Medium
            'ch_high_severity': 0.50,     # High severity Companies House flags
            'former_pep': 0.40,           # Medium
            'ch_medium_severity': 0.30,   # Medium severity
            'ch_low_severity': 0.10       # Low severity
        }
        
        # Risk level thresholds
        self.RISK_THRESHOLD_LOW = 0.4
        self.RISK_THRESHOLD_MEDIUM = 0.7
    
    def calculate_company_risk(self, company_data: Dict) -> Dict[str, Any]:
        """
        Calculate aggregate risk score for a company
        
        Args:
            company_data: Dictionary containing all collected data from Data Collection Stack
            
        Returns:
            Dictionary with risk assessment results
        """
        logger.info(f"Calculating risk for company: {company_data.get('company_number', 'unknown')}")
        
        risk_factors = []
        total_score = 0.0
        critical_flags = []
        high_flags = []
        medium_flags = []
        low_flags = []
        
        # Extract data sources
        companies_house_data = company_data.get('companies_house', {})
        sanctions_data = company_data.get('sanctions', [])
        media_data = company_data.get('adverse_media', {})
        
        # Process Companies House flags
        ch_contribution = self._process_companies_house_flags(
            companies_house_data, 
            risk_factors,
            critical_flags,
            high_flags,
            medium_flags,
            low_flags
        )
        total_score += ch_contribution
        
        # Process Sanctions screening results
        sanctions_contribution, sanctioned_directors = self._process_sanctions_data(
            sanctions_data,
            risk_factors,
            critical_flags,
            high_flags
        )
        total_score += sanctions_contribution
        
        # Process PEP screening results
        pep_contribution, pep_directors = self._process_pep_data(
            sanctions_data,
            risk_factors,
            high_flags,
            medium_flags
        )
        total_score += pep_contribution
        
        # Process Adverse Media
        media_contribution = self._process_media_data(
            media_data,
            risk_factors,
            high_flags,
            medium_flags,
            low_flags
        )
        total_score += media_contribution
        
        # Cap score at 1.0
        total_score = min(total_score, 1.0)
        
        # Determine overall risk level
        risk_level = self._determine_risk_level(
            total_score,
            len(critical_flags),
            len(high_flags)
        )
        
        # Generate human-readable summary
        summary = self._generate_risk_summary(
            total_score,
            risk_level,
            len(critical_flags),
            len(high_flags),
            len(medium_flags),
            len(low_flags),
            sanctioned_directors,
            pep_directors
        )
        
        # Return risk assessment
        return {
            'overall_risk_score': total_score,
            'risk_level': risk_level,
            'risk_factors': risk_factors,
            'flags_summary': {
                'critical': len(critical_flags),
                'high': len(high_flags),
                'medium': len(medium_flags),
                'low': len(low_flags),
                'total': len(critical_flags) + len(high_flags) + len(medium_flags) + len(low_flags)
            },
            'critical_flags': critical_flags,
            'high_flags': high_flags,
            'medium_flags': medium_flags,
            'low_flags': low_flags,
            'sanctioned_directors': sanctioned_directors,
            'pep_directors': pep_directors,
            'summary': summary,
            'calculation_timestamp': datetime.now().isoformat()
        }
    
    def _analyze_governance_risk(self, ch_data: Dict) -> tuple[float, List[Dict]]:
        """
        Analyze governance risk factors with nuanced scoring
        
        Considers:
        - Officer turnover rates
        - Director tenure stability
        - Resignation patterns (mass exits)
        - Company age vs officer tenure
        - Board composition
        
        Returns: (risk_contribution, governance_flags)
        """
        contribution = 0.0
        flags = []
        
        officers_data = ch_data.get('officers', {})
        active_officers = officers_data.get('active_officers', [])
        resigned_officers = officers_data.get('resigned_officers', [])
        company_profile = ch_data.get('company_profile', {})
        
        # Calculate turnover rate
        total_officers = len(active_officers) + len(resigned_officers)
        if total_officers > 0:
            turnover_rate = len(resigned_officers) / total_officers
            
            # High turnover is concerning
            if turnover_rate > 0.75:  # >75% historical turnover
                contribution += 0.15
                flags.append({
                    'severity': 'medium',
                    'category': 'governance',
                    'description': f'High officer turnover rate ({turnover_rate:.0%})'
                })
            elif turnover_rate > 0.5:  # >50% turnover
                contribution += 0.08
                flags.append({
                    'severity': 'low',
                    'category': 'governance',
                    'description': f'Elevated officer turnover ({turnover_rate:.0%})'
                })
        
        # Check for recent mass resignations (multiple in short period)
        recent_resignations = [
            r for r in resigned_officers 
            if r.get('resigned_on', '').startswith(('2024', '2025'))
        ]
        if len(recent_resignations) >= 3:
            contribution += 0.20
            flags.append({
                'severity': 'high',
                'category': 'governance',
                'description': f'{len(recent_resignations)} director resignations in past 12 months'
            })
        
        # Very small board size (single director companies are higher risk)
        if len(active_officers) == 1:
            contribution += 0.10
            flags.append({
                'severity': 'low',
                'category': 'governance',
                'description': 'Single director company - limited oversight'
            })
        elif len(active_officers) == 0:
            contribution += 0.30
            flags.append({
                'severity': 'high',
                'category': 'governance',
                'description': 'No active directors on record'
            })
        
        # Inactive/dissolved company status
        company_status = company_profile.get('company_status', '').lower()
        if company_status in ['dissolved', 'liquidation', 'receivership', 'administration']:
            contribution += 0.40
            flags.append({
                'severity': 'high',
                'category': 'governance',
                'description': f'Company status: {company_status}'
            })
        elif company_status == 'dormant':
            contribution += 0.05
            flags.append({
                'severity': 'low',
                'category': 'governance',
                'description': 'Company is dormant'
            })
        
        return contribution, flags
    
    def _process_companies_house_flags(
        self,
        ch_data: Dict,
        risk_factors: List[Dict],
        critical_flags: List[Dict],
        high_flags: List[Dict],
        medium_flags: List[Dict],
        low_flags: List[Dict]
    ) -> float:
        """Process Companies House compliance flags and calculate contribution"""
        contribution = 0.0
        
        # First, analyze governance risk with nuanced scoring
        gov_contribution, gov_flags = self._analyze_governance_risk(ch_data)
        contribution += gov_contribution
        
        # Categorize governance flags
        for flag in gov_flags:
            if flag['severity'] == 'critical':
                critical_flags.append(flag)
            elif flag['severity'] == 'high':
                high_flags.append(flag)
            elif flag['severity'] == 'medium':
                medium_flags.append(flag)
            else:
                low_flags.append(flag)
        
        # Extract flags from various CH data sources
        flags = []
        
        # Company profile flags
        if 'company_profile' in ch_data:
            profile_flags = ch_data['company_profile'].get('flags', [])
            flags.extend(profile_flags)
        
        # Officer flags
        if 'officers' in ch_data:
            officer_flags = ch_data['officers'].get('flags', [])
            flags.extend(officer_flags)
        
        # Filing history flags
        if 'filing_history' in ch_data:
            filing_flags = ch_data['filing_history'].get('flags', [])
            flags.extend(filing_flags)
        
        # PSC flags
        if 'psc' in ch_data:
            psc_flags = ch_data['psc'].get('flags', [])
            flags.extend(psc_flags)
        
        # Process each flag
        for flag in flags:
            severity = flag.get('severity', 'low')
            flag_type = flag.get('flag_type', 'unknown')
            description = flag.get('description', 'No description')
            
            # Determine weight based on severity
            if severity == 'critical':
                weight = self.risk_weights['sanctions_match']
                critical_flags.append(flag)
            elif severity == 'high':
                weight = self.risk_weights['ch_high_severity']
                high_flags.append(flag)
            elif severity == 'medium':
                weight = self.risk_weights['ch_medium_severity']
                medium_flags.append(flag)
            else:
                weight = self.risk_weights['ch_low_severity']
                low_flags.append(flag)
            
            contribution += weight
            
            risk_factors.append({
                'source': 'companies_house',
                'type': flag_type,
                'severity': severity,
                'description': description,
                'score_contribution': weight
            })
        
        if flags:
            logger.info(f"Companies House: {len(flags)} flags, contribution: {contribution:.3f}")
        
        return contribution
    
    def _process_sanctions_data(
        self,
        sanctions_data: List[Dict],
        risk_factors: List[Dict],
        critical_flags: List[Dict],
        high_flags: List[Dict]
    ) -> tuple[float, List[str]]:
        """Process sanctions screening results"""
        contribution = 0.0
        sanctioned_directors = []
        
        for screening in sanctions_data:
            director_name = screening.get('person_name', 'Unknown')
            matches = screening.get('sanctions_matches', [])
            
            if matches:
                # Each sanctions match is critical
                contribution += self.risk_weights['sanctions_match']
                sanctioned_directors.append(director_name)
                
                for match in matches:
                    flag = {
                        'flag_type': 'sanctions_match',
                        'severity': 'critical',
                        'description': f"Director {director_name} on sanctions list",
                        'details': match
                    }
                    critical_flags.append(flag)
                    
                    risk_factors.append({
                        'source': 'sanctions',
                        'type': 'sanctions_match',
                        'severity': 'critical',
                        'description': f"Director {director_name} matches sanctions list",
                        'score_contribution': self.risk_weights['sanctions_match'],
                        'details': match
                    })
        
        if sanctioned_directors:
            logger.warning(f"Sanctions: {len(sanctioned_directors)} directors matched, contribution: {contribution:.3f}")
        
        return contribution, sanctioned_directors
    
    def _process_pep_data(
        self,
        sanctions_data: List[Dict],
        risk_factors: List[Dict],
        high_flags: List[Dict],
        medium_flags: List[Dict]
    ) -> tuple[float, List[str]]:
        """Process PEP (Politically Exposed Person) screening results"""
        contribution = 0.0
        pep_directors = []
        
        for screening in sanctions_data:
            director_name = screening.get('person_name', 'Unknown')
            pep_matches = screening.get('pep_matches', [])
            
            if pep_matches:
                # Check if current or former PEP
                is_current_pep = any(
                    match.get('is_current_pep', False)
                    for match in pep_matches
                )
                
                if is_current_pep:
                    weight = self.risk_weights['current_pep']
                    severity = 'high'
                    flag_list = high_flags
                else:
                    weight = self.risk_weights['former_pep']
                    severity = 'medium'
                    flag_list = medium_flags
                
                contribution += weight
                pep_directors.append(director_name)
                
                flag = {
                    'flag_type': 'pep_match',
                    'severity': severity,
                    'description': f"Director {director_name} is a {'current' if is_current_pep else 'former'} PEP",
                    'details': pep_matches
                }
                flag_list.append(flag)
                
                risk_factors.append({
                    'source': 'pep',
                    'type': 'pep_match',
                    'severity': severity,
                    'description': f"Director {director_name} is a {'current' if is_current_pep else 'former'} PEP",
                    'score_contribution': weight,
                    'details': pep_matches
                })
        
        if pep_directors:
            logger.info(f"PEP: {len(pep_directors)} directors matched, contribution: {contribution:.3f}")
        
        return contribution, pep_directors
    
    def _process_media_data(
        self,
        media_data: Dict,
        risk_factors: List[Dict],
        high_flags: List[Dict],
        medium_flags: List[Dict],
        low_flags: List[Dict]
    ) -> float:
        """Process adverse media screening results"""
        contribution = 0.0
        
        if not media_data:
            return contribution
        
        # Extract media risk and articles
        media_risk = media_data.get('risk_contribution', 0.0)
        suspicious_articles = media_data.get('suspicious_articles_count', 0)
        articles = media_data.get('articles', [])
        
        if media_risk > 0 and suspicious_articles > 0:
            # Weight media contribution
            contribution = float(media_risk) * self.risk_weights['adverse_media']
            
            # Categorize by severity
            for article in articles:
                severity = article.get('severity', 'medium')
                
                flag = {
                    'flag_type': 'adverse_media',
                    'severity': severity,
                    'description': article.get('title', 'Adverse media found'),
                    'details': article
                }
                
                if severity == 'high':
                    high_flags.append(flag)
                elif severity == 'medium':
                    medium_flags.append(flag)
                else:
                    low_flags.append(flag)
                
                risk_factors.append({
                    'source': 'adverse_media',
                    'type': 'adverse_media',
                    'severity': severity,
                    'description': article.get('title', 'Adverse media found'),
                    'score_contribution': contribution / len(articles) if articles else 0,
                    'details': article
                })
            
            logger.info(f"Adverse Media: {suspicious_articles} articles, contribution: {contribution:.3f}")
        
        return contribution
    
    def _determine_risk_level(
        self,
        score: float,
        critical_count: int,
        high_count: int
    ) -> str:
        """
        Determine risk level based on score and flag counts
        
        Logic:
        - Any critical flag → HIGH
        - Score ≥ 0.7 or ≥2 high flags → HIGH
        - Score ≥ 0.4 or ≥1 high flag → MEDIUM
        - Score > 0 → LOW
        - Score = 0 → LOW (clean)
        """
        # Any critical flag = automatic HIGH
        if critical_count > 0:
            return 'HIGH'
        
        # High score or multiple high flags
        if score >= self.RISK_THRESHOLD_MEDIUM or high_count >= 2:
            return 'HIGH'
        
        # Medium score or some high flags
        if score >= self.RISK_THRESHOLD_LOW or high_count >= 1:
            return 'MEDIUM'
        
        # Any risk factors detected
        return 'LOW'
    
    def _generate_risk_summary(
        self,
        score: float,
        level: str,
        critical: int,
        high: int,
        medium: int,
        low: int,
        sanctioned: List[str],
        peps: List[str]
    ) -> str:
        """Generate human-readable risk summary"""
        summary_parts = []
        
        # Overall assessment
        summary_parts.append(f"Overall Risk Level: {level} (Score: {score:.2f})")
        
        # Critical issues
        if critical > 0:
            summary_parts.append(f"⚠️ CRITICAL: {critical} critical risk factor(s) identified")
        
        # Sanctioned directors
        if sanctioned:
            summary_parts.append(
                f"🚨 SANCTIONS: {len(sanctioned)} director(s) on sanctions lists: {', '.join(sanctioned)}"
            )
        
        # PEP directors
        if peps:
            summary_parts.append(
                f"👤 PEP: {len(peps)} director(s) identified as Politically Exposed Persons: {', '.join(peps)}"
            )
        
        # Flag summary
        if high > 0 or medium > 0 or low > 0:
            summary_parts.append(f"📋 Flags: {high} high, {medium} medium, {low} low severity")
        
        # Recommendation
        if level == 'HIGH':
            summary_parts.append(
                "⛔ Recommendation: ENHANCED DUE DILIGENCE REQUIRED - Senior management approval needed"
            )
        elif level == 'MEDIUM':
            summary_parts.append(
                "⚠️ Recommendation: Additional documentation and verification required"
            )
        else:
            summary_parts.append(
                "✅ Recommendation: Standard CDD procedures sufficient"
            )
        
        return "\n".join(summary_parts)
    
    @staticmethod
    def convert_to_dynamodb_format(data: Any) -> Any:
        """
        Convert Python objects to DynamoDB-compatible format
        (floats to Decimal, recursive)
        """
        if isinstance(data, float):
            return Decimal(str(data))
        elif isinstance(data, dict):
            return {k: RiskCalculator.convert_to_dynamodb_format(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [RiskCalculator.convert_to_dynamodb_format(item) for item in data]
        return data
