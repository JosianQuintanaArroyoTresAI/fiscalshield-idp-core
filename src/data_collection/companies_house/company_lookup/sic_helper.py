"""
SIC Code Helper Module

Provides utilities for working with UK Standard Industrial Classification (SIC) codes.
Uses official ONS SIC 2007 mapping for authoritative descriptions.

Source: Office of National Statistics - UK SIC 2007 Summary of Structure
License: Open Government Licence v3.0
"""

import json
from pathlib import Path
from typing import List, Dict, Optional

# Load SIC codes at module level (Lambda cold start)
_SIC_CODES = {}
_sic_file = Path(__file__).parent / 'sic_codes.json'

try:
    with open(_sic_file, 'r') as f:
        _SIC_CODES = json.load(f)
    print(f"✅ Loaded {len(_SIC_CODES)} SIC codes from {_sic_file.name}")
except Exception as e:
    print(f"⚠️ Could not load SIC codes: {e}")
    _SIC_CODES = {}


def get_sic_description(sic_code: str) -> str:
    """
    Get official description for a SIC code.
    
    Args:
        sic_code: 5-digit SIC code (e.g., "62012")
    
    Returns:
        Official description from ONS, or "Unknown SIC code" if not found
    
    Example:
        >>> get_sic_description("62012")
        'Computer consultancy activities'
    """
    if not sic_code:
        return "No SIC code provided"
    
    # Clean code (remove spaces, ensure 5 digits)
    clean_code = str(sic_code).strip().zfill(5)
    
    return _SIC_CODES.get(clean_code, f"Unknown SIC code: {clean_code}")


def get_industry_context(sic_codes: List[str]) -> str:
    """
    Get industry descriptions for multiple SIC codes.
    
    Args:
        sic_codes: List of 5-digit SIC codes
    
    Returns:
        Formatted string with all SIC code descriptions
    
    Example:
        >>> get_industry_context(["62012", "62020"])
        '62012: Computer consultancy activities
         62020: Information technology consultancy activities'
    """
    if not sic_codes:
        return "No SIC codes provided"
    
    descriptions = []
    for code in sic_codes:
        clean_code = str(code).strip().zfill(5)
        desc = _SIC_CODES.get(clean_code, f"Unknown code: {clean_code}")
        descriptions.append(f"{clean_code}: {desc}")
    
    return "\n".join(descriptions)


def get_section_from_sic(sic_code: str) -> str:
    """
    Extract section letter (A-U) from 5-digit SIC code.
    
    Sections represent major industry categories:
    A=Agriculture, C=Manufacturing, F=Construction, J=IT, M=Professional, etc.
    
    Args:
        sic_code: 5-digit SIC code
    
    Returns:
        Section letter (A-U) or "UNKNOWN"
    
    Example:
        >>> get_section_from_sic("62012")
        'J'  # Information and Communication
    """
    try:
        code_int = int(str(sic_code).strip())
    except ValueError:
        return 'UNKNOWN'
    
    # Map code ranges to sections
    if 1110 <= code_int <= 3220: return 'A'    # Agriculture, Forestry and Fishing
    elif 5100 <= code_int <= 9900: return 'B'   # Mining and Quarrying
    elif 10110 <= code_int <= 33200: return 'C' # Manufacturing
    elif 35110 <= code_int <= 35300: return 'D' # Electricity, Gas, Steam
    elif 36000 <= code_int <= 39000: return 'E' # Water Supply, Sewerage, Waste
    elif 41100 <= code_int <= 43999: return 'F' # Construction
    elif 45111 <= code_int <= 47990: return 'G' # Wholesale and Retail Trade
    elif 49100 <= code_int <= 53202: return 'H' # Transportation and Storage
    elif 55100 <= code_int <= 56302: return 'I' # Accommodation and Food Service
    elif 58110 <= code_int <= 63990: return 'J' # Information and Communication
    elif 64110 <= code_int <= 66300: return 'K' # Financial and Insurance
    elif 68100 <= code_int <= 68320: return 'L' # Real Estate
    elif 69101 <= code_int <= 75000: return 'M' # Professional, Scientific, Technical
    elif 77110 <= code_int <= 82990: return 'N' # Administrative and Support Services
    elif 84110 <= code_int <= 84300: return 'O' # Public Administration and Defence
    elif 85100 <= code_int <= 85600: return 'P' # Education
    elif 86101 <= code_int <= 88990: return 'Q' # Human Health and Social Work
    elif 90010 <= code_int <= 93290: return 'R' # Arts, Entertainment and Recreation
    elif 94110 <= code_int <= 96090: return 'S' # Other Service Activities
    elif 97000 <= code_int <= 98200: return 'T' # Households as Employers
    elif code_int == 99000: return 'U'           # Extraterritorial Organisations
    elif code_int == 99999: return 'DORMANT'     # Dormant Company (special case)
    elif code_int == 74990: return 'NON_TRADING' # Non-trading (special case)
    else: return 'UNKNOWN'


def get_section_name(section_letter: str) -> str:
    """
    Get full name for a section letter.
    
    Args:
        section_letter: Section letter A-U
    
    Returns:
        Full section name
    
    Example:
        >>> get_section_name('J')
        'Information and Communication'
    """
    sections = {
        'A': 'Agriculture, Forestry and Fishing',
        'B': 'Mining and Quarrying',
        'C': 'Manufacturing',
        'D': 'Electricity, Gas, Steam and Air Conditioning Supply',
        'E': 'Water Supply, Sewerage, Waste Management',
        'F': 'Construction',
        'G': 'Wholesale and Retail Trade',
        'H': 'Transportation and Storage',
        'I': 'Accommodation and Food Service Activities',
        'J': 'Information and Communication',
        'K': 'Financial and Insurance Activities',
        'L': 'Real Estate Activities',
        'M': 'Professional, Scientific and Technical Activities',
        'N': 'Administrative and Support Service Activities',
        'O': 'Public Administration and Defence',
        'P': 'Education',
        'Q': 'Human Health and Social Work Activities',
        'R': 'Arts, Entertainment and Recreation',
        'S': 'Other Service Activities',
        'T': 'Activities of Households as Employers',
        'U': 'Activities of Extraterritorial Organisations',
        'DORMANT': 'Dormant Company',
        'NON_TRADING': 'Non-Trading Company'
    }
    return sections.get(section_letter, 'Unknown Section')


def get_industry_summary(sic_codes: List[str]) -> Dict[str, any]:
    """
    Get comprehensive industry summary for a company's SIC codes.
    
    Args:
        sic_codes: List of SIC codes (companies can have up to 4)
    
    Returns:
        Dictionary with industry analysis
    
    Example:
        >>> get_industry_summary(["62012", "62020"])
        {
            'primary_code': '62012',
            'primary_description': 'Computer consultancy activities',
            'section': 'J',
            'section_name': 'Information and Communication',
            'all_codes': [
                {'code': '62012', 'description': 'Computer consultancy activities'},
                {'code': '62020', 'description': 'Information technology consultancy activities'}
            ],
            'context': 'This company operates in the Information and Communication sector...'
        }
    """
    if not sic_codes or len(sic_codes) == 0:
        return {
            'primary_code': None,
            'primary_description': 'No SIC codes available',
            'section': 'UNKNOWN',
            'section_name': 'Unknown',
            'all_codes': [],
            'context': 'No industry information available'
        }
    
    # Primary code is typically the first one
    primary_code = str(sic_codes[0]).strip().zfill(5)
    primary_desc = get_sic_description(primary_code)
    section = get_section_from_sic(primary_code)
    section_name = get_section_name(section)
    
    # Get all codes
    all_codes = []
    for code in sic_codes:
        clean_code = str(code).strip().zfill(5)
        all_codes.append({
            'code': clean_code,
            'description': get_sic_description(clean_code)
        })
    
    # Generate context
    if len(sic_codes) == 1:
        context = f"This company operates in the {section_name} sector, specifically: {primary_desc}."
    else:
        context = f"This company operates primarily in the {section_name} sector ({primary_desc}), with additional activities in: "
        context += ", ".join([c['description'] for c in all_codes[1:]])
    
    return {
        'primary_code': primary_code,
        'primary_description': primary_desc,
        'section': section,
        'section_name': section_name,
        'all_codes': all_codes,
        'context': context
    }


# For testing/debugging
if __name__ == '__main__':
    # Test cases
    test_codes = ['62012', '41201', '47110', '69201', '74990', '99999']
    
    print("SIC Code Tests")
    print("=" * 80)
    
    for code in test_codes:
        desc = get_sic_description(code)
        section = get_section_from_sic(code)
        section_name = get_section_name(section)
        print(f"\n{code}:")
        print(f"  Description: {desc}")
        print(f"  Section: {section} - {section_name}")
    
    print("\n" + "=" * 80)
    print("\nMultiple SIC Codes Test:")
    summary = get_industry_summary(['62012', '62020'])
    print(f"Primary: {summary['primary_code']} - {summary['primary_description']}")
    print(f"Section: {summary['section']} - {summary['section_name']}")
    print(f"Context: {summary['context']}")
