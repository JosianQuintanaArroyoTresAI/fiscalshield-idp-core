"""
Constants for Analysis Stack

Convention-based naming ensures predictable cross-stack access.
All resources follow: fiscalshield-analysis-{environment}-{ResourceName}
"""

import os

# Environment
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')

# DynamoDB Table Names (convention-based)
COMPANY_INTELLIGENCE_TABLE = f'fiscalshield-analysis-{ENVIRONMENT}-CompanyIntelligence'

# Data Collection Stack Tables (read-only access)
DC_COMPANY_EVENTS_TABLE = f'fiscalshield-dc-{ENVIRONMENT}-CompanyEvents'
DC_FILING_EVENTS_TABLE = f'fiscalshield-dc-{ENVIRONMENT}-FilingEvents'
DC_HMRC_GUIDANCE_TABLE = f'fiscalshield-dc-{ENVIRONMENT}-HMRCGuidance'

# Cache TTL
ANALYSIS_CACHE_TTL_HOURS = int(os.environ.get('ANALYSIS_CACHE_TTL_HOURS', '24'))

# Intelligence Types
INTELLIGENCE_TYPE_OVERALL = 'OVERALL_RISK'
INTELLIGENCE_TYPE_GOVERNANCE = 'GOVERNANCE'
INTELLIGENCE_TYPE_AML = 'AML'
INTELLIGENCE_TYPE_FINANCIAL = 'FINANCIAL'
INTELLIGENCE_TYPE_MEDIA = 'MEDIA'

# Risk Levels
RISK_LEVEL_LOW = 'LOW'
RISK_LEVEL_MEDIUM = 'MEDIUM'
RISK_LEVEL_HIGH = 'HIGH'

# Risk Score Thresholds
RISK_THRESHOLD_LOW = 0.4
RISK_THRESHOLD_MEDIUM = 0.7

# Risk Weights (from AML README)
WEIGHT_SANCTIONS = 0.95
WEIGHT_CURRENT_PEP = 0.70
WEIGHT_FORMER_PEP = 0.40
WEIGHT_CH_HIGH_FLAG = 0.50
WEIGHT_CH_MEDIUM_FLAG = 0.30
WEIGHT_CH_LOW_FLAG = 0.10
