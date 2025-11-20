# SIC Code Mapping - Implementation Summary

## Problem Solved ✅

**Question**: Where can we get authoritative SIC code to description mapping?  
**Answer**: Official ONS (Office of National Statistics) data - now extracted and ready to use!

## What We Have Now

### 1. Official SIC Code Mapping File
**Location**: `stacks/analysis/lambdas/categorization/sic_codes.json`

- ✅ **806 SIC codes** with official descriptions
- ✅ **Source**: ONS UK SIC 2007 Summary of Structure
- ✅ **License**: Open Government Licence v3.0 (free to use)
- ✅ **Size**: ~48KB (small enough to bundle with Lambda)
- ✅ **Format**: JSON for easy loading

**Example entries**:
```json
{
  "62012": "Computer consultancy activities",
  "41201": "Construction of domestic buildings",
  "69201": "Bookkeeping activities",
  "74990": "Non-trading company",
  "99999": "Dormant Company"
}
```

### 2. Helper Module
**Location**: `stacks/analysis/lambdas/categorization/sic_helper.py`

Provides easy-to-use functions:
- `get_sic_description(code)` - Get official description
- `get_industry_context(codes)` - Format multiple codes
- `get_section_from_sic(code)` - Get industry section (A-U)
- `get_section_name(letter)` - Get section full name
- `get_industry_summary(codes)` - Complete industry analysis

**Example usage**:
```python
from sic_helper import get_industry_summary

# Get company SIC codes (already available in your DB)
company_sic_codes = ["62012", "62020"]

# Get industry context
summary = get_industry_summary(company_sic_codes)

print(summary['context'])
# Output: "This company operates primarily in the Information and 
#          Communication sector (Computer consultancy activities), 
#          with additional activities in: Information technology 
#          consultancy activities"
```

### 3. Updated Documentation
**Location**: `docs/SIC_CODES_REFERENCE.md`

Complete reference guide with:
- SIC code structure explanation
- All 21 sections (A-U) defined
- Implementation examples
- Data sources and licensing

## Why This Matters

### Before
❌ Would need to rely on LLM knowledge of SIC codes (potentially inaccurate)  
❌ No way to verify if descriptions are correct  
❌ Codes might be outdated or wrong

### After
✅ **Authoritative source** - Official ONS data  
✅ **Verifiable** - Can trace back to government source  
✅ **Accurate** - Exact descriptions used by Companies House  
✅ **Stable** - Only needs updating when ONS publishes changes (rare)  
✅ **Free** - Open Government Licence  

## How to Use for Invoice Categorization

### Step 1: Retrieve Company SIC Codes
(Already available in your database!)

```python
# From DynamoDB CompanyEvents table
company_data = get_company_info(company_number)
sic_codes = company_data.get('sic_codes', [])
# Example: ["62012", "62020"]
```

### Step 2: Get Industry Context
```python
from sic_helper import get_industry_summary

industry = get_industry_summary(sic_codes)
# Returns: {
#   'primary_code': '62012',
#   'primary_description': 'Computer consultancy activities',
#   'section': 'J',
#   'section_name': 'Information and Communication',
#   'context': 'This company operates primarily in...'
# }
```

### Step 3: Pass to Invoice Categorization
```python
# Enhanced prompt with industry context
prompt = f"""
You are analyzing an invoice for a company with the following business activities:

Industry: {industry['section_name']}
Primary Activity: {industry['primary_description']}
Additional Activities: {', '.join([c['description'] for c in industry['all_codes'][1:]])}

This means the company typically has expenses related to:
{get_typical_expenses_for_section(industry['section'])}

Unusual expenses for this industry would include:
{get_unusual_expenses_for_section(industry['section'])}

Now categorize this invoice...
"""
```

## Data Freshness

- **Current version**: UK SIC 2007 (published 2008)
- **Last minor update**: December 2022
- **Next major revision**: Not scheduled (typically every 10-15 years)
- **Maintenance needed**: Check ONS website annually for addendums
- **Download URL**: https://www.ons.gov.uk/methodology/classificationsandstandards/ukstandardindustrialclassificationofeconomicactivities/uksic2007

## Benefits for Your System

1. **Better Invoice Categorization**
   - AI knows what's normal for each industry
   - Can flag unusual expenses (e.g., heavy machinery for software company)

2. **Industry-Specific Compliance**
   - Construction (CIS scheme)
   - R&D tax relief (tech companies)
   - Sector-specific allowances

3. **Fraud Detection**
   - Flag expenses that don't match business type
   - Identify suspicious patterns

4. **No LLM Hallucination Risk**
   - Using official government data
   - No risk of invented SIC code descriptions
   - Can verify every code against source

## Next Steps

Ready to integrate! The files are in place:
1. ✅ `sic_codes.json` - Official mapping
2. ✅ `sic_helper.py` - Helper functions
3. ✅ Documentation updated

**To implement**:
- Import `sic_helper` in your categorization Lambda
- Retrieve company SIC codes from existing data
- Add industry context to categorization prompts
- Test with different industries (construction, IT, retail, etc.)

---

**Created**: November 20, 2025  
**Source**: Office of National Statistics  
**Status**: ✅ Ready for Implementation
