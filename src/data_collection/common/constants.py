"""
Constants for Data Collection Stack

Convention-based naming ensures predictable cross-stack access.
All resources follow: fiscalshield-dc-{environment}-{ResourceName}
"""

import os

# Environment
ENVIRONMENT = os.environ.get("ENVIRONMENT", "dev")

# DynamoDB Table Names (convention-based)
FILING_EVENTS_TABLE = f"fiscalshield-dc-{ENVIRONMENT}-FilingEvents"
COMPANY_EVENTS_TABLE = f"fiscalshield-dc-{ENVIRONMENT}-CompanyEvents"
HMRC_DATA_TABLE = f"fiscalshield-dc-{ENVIRONMENT}-HMRCData"
HMRC_GUIDANCE_TABLE = f"fiscalshield-dc-{ENVIRONMENT}-HMRCGuidance"
RATE_LIMITS_TABLE = f"fiscalshield-dc-{ENVIRONMENT}-RateLimits"

# Secrets Manager Secret Names
COMPANIES_HOUSE_SECRET = f"fiscalshield-dc-{ENVIRONMENT}-CompaniesHouseAPI"
HMRC_SECRET = f"fiscalshield-dc-{ENVIRONMENT}-HMRCAPI"
BANKING_SECRET = f"fiscalshield-dc-{ENVIRONMENT}-BankingAPI"

# Lambda Function Names
COMPANY_LOOKUP_FUNCTION = f"fiscalshield-dc-{ENVIRONMENT}-CompanyLookup"
FILING_HISTORY_FUNCTION = f"fiscalshield-dc-{ENVIRONMENT}-FilingHistory"
OFFICERS_FUNCTION = f"fiscalshield-dc-{ENVIRONMENT}-Officers"
PSC_LOOKUP_FUNCTION = f"fiscalshield-dc-{ENVIRONMENT}-PSCLookup"
VAT_OBLIGATIONS_FUNCTION = f"fiscalshield-dc-{ENVIRONMENT}-VATObligations"
CACHE_MAINTENANCE_FUNCTION = f"fiscalshield-dc-{ENVIRONMENT}-CacheMaintenance"

# Cache TTL (in hours)
CACHE_TTL_COMPANY_PROFILE = 24
CACHE_TTL_FILING_HISTORY = 24
CACHE_TTL_OFFICERS = 24
CACHE_TTL_PSC = 168  # 7 days
CACHE_TTL_VAT_OBLIGATIONS = 1
CACHE_TTL_VAT_RETURNS = 720  # 30 days

# API Rate Limits
COMPANIES_HOUSE_RATE_LIMIT = 600  # requests per 5 minutes
COMPANIES_HOUSE_RATE_WINDOW = 300  # seconds

# Risk Levels
RISK_LOW = "LOW"
RISK_MEDIUM = "MEDIUM"
RISK_HIGH = "HIGH"
RISK_CRITICAL = "CRITICAL"

# Compliance Score Range
MIN_COMPLIANCE_SCORE = 1
MAX_COMPLIANCE_SCORE = 10

# HMRC BIM (Business Income Manual) Sections
# These are the priority sections for VAT/expense compliance
BIM_SECTIONS = [
    "hmrc-internal-manuals/business-income-manual/bim37000",  # General principles
    "hmrc-internal-manuals/business-income-manual/bim37050",  # Expense basics
    "hmrc-internal-manuals/business-income-manual/bim37600",  # Travel expenses
    "hmrc-internal-manuals/business-income-manual/bim37650",  # Subsistence
    "hmrc-internal-manuals/business-income-manual/bim37700",  # Entertainment
    "hmrc-internal-manuals/business-income-manual/bim42000",  # Motor expenses introduction
    "hmrc-internal-manuals/business-income-manual/bim42050",  # Business vs private use
    "hmrc-internal-manuals/business-income-manual/bim45000",  # Accommodation
    "hmrc-internal-manuals/business-income-manual/bim45005",  # Rent and rates
    "hmrc-internal-manuals/business-income-manual/bim35000",  # Professional fees
    "hmrc-internal-manuals/business-income-manual/bim35010",  # Legal fees
    "hmrc-internal-manuals/business-income-manual/bim46800",  # Equipment and tools
    "hmrc-internal-manuals/business-income-manual/bim40450",  # Repairs vs improvements
    "hmrc-internal-manuals/business-income-manual/bim43200",  # Telephone and internet
    "hmrc-internal-manuals/business-income-manual/bim42400",  # Mileage allowance
]

# GOV.UK Content API
GOVUK_API_BASE_URL = "https://www.gov.uk/api/content"
GOVUK_RATE_LIMIT_PER_SEC = 8.3  # Public API rate limit

# BIM Section Categories (for GSI queries)
BIM_CATEGORY_TRAVEL = "travel"
BIM_CATEGORY_MOTOR = "motor"
BIM_CATEGORY_ENTERTAINMENT = "entertainment"
BIM_CATEGORY_OFFICE = "office"
BIM_CATEGORY_ACCOMMODATION = "accommodation"
BIM_CATEGORY_PROFESSIONAL_FEES = "professional_fees"
BIM_CATEGORY_GENERAL = "general"

# Map BIM sections to categories
BIM_SECTION_CATEGORIES = {
    "bim37000": BIM_CATEGORY_GENERAL,
    "bim37050": BIM_CATEGORY_GENERAL,
    "bim37600": BIM_CATEGORY_TRAVEL,
    "bim37650": BIM_CATEGORY_TRAVEL,
    "bim37700": BIM_CATEGORY_ENTERTAINMENT,
    "bim42000": BIM_CATEGORY_MOTOR,
    "bim42050": BIM_CATEGORY_MOTOR,
    "bim42400": BIM_CATEGORY_MOTOR,
    "bim45000": BIM_CATEGORY_ACCOMMODATION,
    "bim45005": BIM_CATEGORY_ACCOMMODATION,
    "bim35000": BIM_CATEGORY_PROFESSIONAL_FEES,
    "bim35010": BIM_CATEGORY_PROFESSIONAL_FEES,
    "bim46800": BIM_CATEGORY_OFFICE,
    "bim40450": BIM_CATEGORY_GENERAL,
    "bim43200": BIM_CATEGORY_OFFICE,
}
