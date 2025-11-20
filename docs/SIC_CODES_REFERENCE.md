# UK SIC Codes - Reference Guide

## Overview

**SIC (Standard Industrial Classification) codes** are used by Companies House to classify the nature of a company's business activities. These codes are essential for invoice categorization and expense compliance analysis.

## Key Facts

### What Are SIC Codes?

- **Purpose**: Classify economic activities of businesses
- **Maintained by**: Office of National Statistics (ONS)
- **Used by**: Companies House for UK company registration
- **Format**: 5-digit numerical codes (e.g., `62012`, `47110`)
- **Stability**: **Rarely change** - companies typically keep the same SIC codes for years
- **Multiple codes**: Companies can register with **up to 4 SIC codes**

### How Many SIC Codes Are There?

Based on the Companies House condensed list:
- **~730 distinct codes** in the condensed version used by Companies House
- Organized into **21 sections** (A-U)
- Full ONS version has more granular subcategories

### Sections (Main Categories)

| Section | Description | Example Codes |
|---------|-------------|---------------|
| **A** | Agriculture, Forestry and Fishing | 01110-03220 |
| **B** | Mining and Quarrying | 05101-09900 |
| **C** | Manufacturing | 10110-33200 |
| **D** | Electricity, Gas, Steam and Air | 35110-35300 |
| **E** | Water Supply, Sewerage, Waste | 36000-39000 |
| **F** | Construction | 41100-43999 |
| **G** | Wholesale and Retail Trade | 45111-47990 |
| **H** | Transportation and Storage | 49100-53202 |
| **I** | Accommodation and Food Services | 55100-56302 |
| **J** | Information and Communication | 58110-63990 |
| **K** | Financial and Insurance | 64110-66300 |
| **L** | Real Estate Activities | 68100-68320 |
| **M** | Professional, Scientific and Technical | 69101-75000 |
| **N** | Administrative and Support Services | 77110-82990 |
| **O** | Public Administration and Defence | 84110-84300 |
| **P** | Education | 85100-85600 |
| **Q** | Human Health and Social Work | 86101-88990 |
| **R** | Arts, Entertainment and Recreation | 90010-93290 |
| **S** | Other Service Activities | 94110-96090 |
| **T** | Households as Employers | 97000-98200 |
| **U** | Extraterritorial Organisations | 99000 |

### Special Codes

- **74990** - Non-trading company
- **99999** - Dormant company

## Current Implementation Status

### ✅ Already Retrieved and Stored

SIC codes are **already being fetched** from Companies House API:

**Location**: `src/data_collection/companies_house/company_lookup/handler.py`

```python
formatted = {
    "company_name": company_data.get("company_name", ""),
    "company_number": company_data.get("company_number", ""),
    # ... other fields ...
    "sic_codes": company_data.get("sic_codes", []),  # ✅ Already retrieved
}
```

**Storage**:
- Stored in DynamoDB: `fiscalshield-dc-{env}-CompanyEvents` table
- Cache key: `COMPANY_INFO#{date}`
- TTL: 24 hours
- Field format: Array of strings (e.g., `["62012", "62020"]`)

**Display**:
- Already shown in UI: `src/ui/src/components/company-intelligence/CompanyAnalysis.jsx`
- Displays as comma-separated list

### ❌ Not Yet Used For

- **Invoice categorization** - Could use SIC codes to improve AI categorization
- **Expense compliance** - Could use to determine industry-specific allowances
- **Risk scoring** - Could flag unusual expenses for the industry

## How to Use SIC Codes for Invoice Categorization

### Use Case: Context-Aware Expense Categorization

**Problem**: Generic invoice categorization doesn't account for industry differences.

**Example**:
- **Construction company** (SIC: 41201):
  - "Materials" → Likely building materials (allowable)
  - Heavy vehicle expenses → Normal business expense
  
- **Software company** (SIC: 62012):
  - "Materials" → Unusual, might be equipment (needs review)
  - Heavy vehicle expenses → Suspicious (software companies don't need trucks)

### Implementation Strategy

#### Option 1: Pass SIC Codes to Categorization Lambda

**Update**: `stacks/analysis/lambdas/categorization/handler.py`

```python
def categorize_invoices_batch(invoices: List[Dict], company_sic_codes: List[str]) -> List[Dict]:
    """
    Categorize invoices with industry context from SIC codes.
    
    Args:
        invoices: List of invoice records
        company_sic_codes: SIC codes for the company (e.g., ["62012", "62020"])
    """
    
    # Get industry description
    industry_context = get_industry_context(company_sic_codes)
    
    # Enhanced prompt with industry context
    prompt = f"""
You are analyzing invoices for a company in the following industry:
Industry Codes: {', '.join(company_sic_codes)}
Industry Description: {industry_context}

Categorize these invoices considering typical expenses for this industry:
- Construction companies: materials, subcontractors, equipment hire
- Software companies: licenses, hosting, development tools
- Retail companies: stock, POS systems, shop fitting
- Professional services: insurance, training, software

{invoice_data}
"""
```

#### Option 2: Create SIC Code to Industry Mapping

**File**: `stacks/analysis/lambdas/categorization/sic_industry_mapping.json`

```json
{
  "62012": {
    "section": "J",
    "division": "62",
    "group": "620",
    "class": "6201",
    "description": "Business and domestic software development",
    "typical_expenses": [
      "Cloud hosting (AWS, Azure)",
      "Software licenses",
      "Development tools",
      "API subscriptions",
      "Domain registrations",
      "Code repositories"
    ],
    "unusual_expenses": [
      "Heavy machinery",
      "Construction materials",
      "Wholesale inventory",
      "Agricultural supplies"
    ],
    "compliance_notes": "R&D tax relief may apply to development costs"
  },
  "41201": {
    "section": "F",
    "division": "41",
    "group": "412",
    "class": "4120",
    "description": "Construction of commercial buildings",
    "typical_expenses": [
      "Building materials",
      "Subcontractor payments",
      "Equipment hire",
      "Site safety equipment",
      "Scaffolding",
      "CIS deductions"
    ],
    "unusual_expenses": [
      "Software licenses (unless construction management software)",
      "Retail inventory",
      "Hospitality expenses (unless client entertainment)"
    ],
    "compliance_notes": "CIS scheme applies - check tax deductions"
  }
}
```

#### Option 3: Lightweight Mapping (Recommended for MVP)

Create a simple section-level mapping:

**File**: `stacks/analysis/lambdas/categorization/sic_sections.py`

```python
SIC_SECTIONS = {
    'A': {
        'name': 'Agriculture, Forestry and Fishing',
        'keywords': ['farming', 'crops', 'livestock', 'fishing', 'forestry'],
        'typical_expense_categories': ['Equipment', 'Feed', 'Seeds', 'Fuel']
    },
    'C': {
        'name': 'Manufacturing',
        'keywords': ['raw materials', 'production', 'machinery', 'factory'],
        'typical_expense_categories': ['Materials', 'Equipment', 'Machinery', 'Factory Rent']
    },
    'F': {
        'name': 'Construction',
        'keywords': ['building', 'construction', 'materials', 'subcontractor'],
        'typical_expense_categories': ['Materials', 'Subcontractors', 'Equipment Hire', 'CIS']
    },
    'G': {
        'name': 'Wholesale and Retail Trade',
        'keywords': ['stock', 'inventory', 'wholesale', 'shop'],
        'typical_expense_categories': ['Stock', 'Retail Premises', 'POS Systems']
    },
    'J': {
        'name': 'Information and Communication',
        'keywords': ['software', 'IT', 'hosting', 'licenses'],
        'typical_expense_categories': ['Software', 'Cloud Services', 'Domains', 'APIs']
    },
    'M': {
        'name': 'Professional, Scientific and Technical',
        'keywords': ['consultancy', 'professional fees', 'insurance'],
        'typical_expense_categories': ['Professional Indemnity', 'Training', 'Memberships']
    }
}

def get_section_from_sic(sic_code: str) -> str:
    """Extract section letter from 5-digit SIC code."""
    # SIC codes are organized by numeric ranges
    code_int = int(sic_code)
    
    if 1110 <= code_int <= 3220: return 'A'  # Agriculture
    elif 5101 <= code_int <= 9900: return 'B'  # Mining
    elif 10110 <= code_int <= 33200: return 'C'  # Manufacturing
    elif 35110 <= code_int <= 35300: return 'D'  # Electricity/Gas
    elif 36000 <= code_int <= 39000: return 'E'  # Water/Waste
    elif 41100 <= code_int <= 43999: return 'F'  # Construction
    elif 45111 <= code_int <= 47990: return 'G'  # Retail/Wholesale
    elif 49100 <= code_int <= 53202: return 'H'  # Transportation
    elif 55100 <= code_int <= 56302: return 'I'  # Accommodation/Food
    elif 58110 <= code_int <= 63990: return 'J'  # Information/Comm
    elif 64110 <= code_int <= 66300: return 'K'  # Financial
    elif 68100 <= code_int <= 68320: return 'L'  # Real Estate
    elif 69101 <= code_int <= 75000: return 'M'  # Professional/Scientific
    elif 77110 <= code_int <= 82990: return 'N'  # Admin/Support
    elif 84110 <= code_int <= 84300: return 'O'  # Public Admin
    elif 85100 <= code_int <= 85600: return 'P'  # Education
    elif 86101 <= code_int <= 88990: return 'Q'  # Health/Social
    elif 90010 <= code_int <= 93290: return 'R'  # Arts/Entertainment
    elif 94110 <= code_int <= 96090: return 'S'  # Other Services
    elif 97000 <= code_int <= 98200: return 'T'  # Households
    elif code_int == 99000: return 'U'  # Extraterritorial
    else: return 'UNKNOWN'
```

## Recommendations

### For Invoice Categorization Enhancement

1. **Retrieve SIC codes** from existing Companies House data (already available!)
2. **Pass to categorization Lambda** as context
3. **Use section-level mapping** (lightweight, low maintenance)
4. **Enhance Claude prompt** with industry context

**Example Enhanced Prompt**:
```
Company Industry: Information and Communication (Software Development)
SIC Codes: 62012

This company typically has expenses for:
- Cloud hosting (AWS, Azure, etc.)
- Software licenses and subscriptions
- Domain registrations
- API services

Unusual expenses for this industry:
- Heavy machinery
- Construction materials
- Wholesale inventory

Categorize the following invoice with this industry context...
```

### Benefits

✅ **Better categorization accuracy** - Industry-specific context
✅ **Fraud detection** - Flag expenses unusual for the industry
✅ **Compliance guidance** - Industry-specific tax rules (CIS, R&D relief)
✅ **No API calls needed** - SIC codes already retrieved and cached
✅ **Stable data** - Codes rarely change, minimal maintenance

### Implementation Priority

**Phase 1: Quick Win (2-3 hours)**
- Add SIC section mapping (simple Python dict)
- Pass company SIC codes to categorization Lambda
- Update Claude prompt with industry context
- Test with 3-4 different industries

**Phase 2: Enhanced Mapping (1-2 days)**
- Create detailed SIC code descriptions JSON
- Add typical/unusual expense lists per industry
- Implement compliance notes (CIS, R&D relief, etc.)
- Add to compliance scoring logic

**Phase 3: ML Enhancement (Future)**
- Train industry-specific expense models
- Build anomaly detection based on industry norms
- Cross-company benchmarking by SIC code

## Reference Links

- **Companies House SIC Codes**: https://resources.companieshouse.gov.uk/sic/
- **ONS Full SIC List**: https://www.ons.gov.uk/methodology/classificationsandstandards/ukstandardindustrialclassificationofeconomicactivities
- **Companies House API**: Returns `sic_codes` array in company profile response

## Authoritative SIC Code Mapping

### ✅ Official Mapping File Created

**Location**: `stacks/analysis/lambdas/categorization/sic_codes.json`

**Source**: Office of National Statistics (ONS) - UK SIC 2007 Summary of Structure  
**Download URL**: https://www.ons.gov.uk/file?uri=/methodology/classificationsandstandards/ukstandardindustrialclassificationofeconomicactivities/uksic2007/publisheduksicsummaryofstructureworksheet.xlsx

**File Details**:
- **Total codes**: 806 distinct SIC codes
- **Format**: JSON (code → description mapping)
- **File size**: ~48KB (small enough for Lambda layer or direct inclusion)
- **License**: Open Government Licence v3.0 (free to use)

**Example Structure**:
```json
{
  "01110": "Growing of rice",
  "41201": "Construction of domestic buildings",
  "62012": "Computer consultancy activities",
  "69201": "Bookkeeping activities",
  "74990": "Non-trading company",
  "99999": "Dormant Company"
}
```

**Special Codes Included**:
- `74990` - Non-trading company (Companies House specific)
- `99999` - Dormant company (Companies House specific)
- All standard ONS SIC 2007 codes
- All Companies House condensed list codes

### Usage in Code

```python
import json
from pathlib import Path

# Load at module level (Lambda cold start)
SIC_CODES = {}
sic_file = Path(__file__).parent / 'sic_codes.json'
with open(sic_file, 'r') as f:
    SIC_CODES = json.load(f)

def get_sic_description(sic_code: str) -> str:
    """Get official description for SIC code."""
    return SIC_CODES.get(sic_code, f"Unknown SIC code: {sic_code}")

def get_industry_context(sic_codes: list) -> str:
    """Get industry descriptions for multiple SIC codes."""
    descriptions = [
        f"{code}: {SIC_CODES.get(code, 'Unknown')}"
        for code in sic_codes
    ]
    return "\n".join(descriptions)
```

### Data Freshness

- **Last ONS Update**: SIC 2007 (published 2008, minor amendments 2022)
- **Next Major Revision**: Not scheduled (typically every 10-15 years)
- **Stability**: Very stable - codes change infrequently
- **Maintenance**: Check ONS website annually for addendums

## Notes

- SIC codes are **already in your database** - no new API integration needed
- Companies House API returns codes as array (companies can have multiple)
- Codes are **free and publicly available** under Open Government Licence
- Updates are infrequent (major revision every ~10 years)
- Current version: **SIC 2007** (updated from SIC 2003)
- **Official mapping file now available** - no need to rely on LLM knowledge
- File is small enough to bundle with Lambda code (no S3 needed)

---

**Last Updated**: November 20, 2025  
**Status**: ✅ **IMPLEMENTED** - SIC codes enriched at Data Collection stack level  
**Location**: `src/data_collection/companies_house/company_lookup/`
