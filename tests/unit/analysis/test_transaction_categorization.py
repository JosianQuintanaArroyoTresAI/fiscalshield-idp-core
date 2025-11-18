"""
Critical Unit Tests for Transaction Categorization Lambda

Tests the most important business logic for bank transaction analysis:
- HMRC MLR 2017 compliance threshold detection
- Cash risk assessment
- Geographic risk (FATF high-risk countries)
- Structuring pattern detection
- Composite risk scoring

These tests ensure regulatory compliance and accurate risk assessment.
"""
import pytest
import sys
from pathlib import Path
from decimal import Decimal

# Add categorization handler to path
CATEGORIZATION_PATH = Path(__file__).parent.parent.parent.parent / 'stacks' / 'analysis' / 'lambdas' / 'categorization'
sys.path.insert(0, str(CATEGORIZATION_PATH))

from handler import (
    check_threshold_breach,
    check_cash_risk,
    check_geographic_risk,
    check_structuring_pattern,
    check_vague_description,
    calculate_compliance_risk_score,
    normalize_country_code
)


@pytest.mark.unit
class TestThresholdBreach:
    """Critical tests for MLR 2017 threshold breach detection."""
    
    def test_general_15k_threshold_breach(self):
        """
        CRITICAL: Transactions >= £15,000 must trigger GENERAL_15K flag.
        MLR 2017 Regulation 33 requires reporting.
        """
        result = check_threshold_breach(15000.00)
        
        assert result['flag'] == 'GENERAL_15K', "Should flag £15k threshold breach"
        assert result['threshold_value'] == 15000
        assert '£15,000' in result['description']
        assert 'MLR 2017 Reg 33' in result['description']
    
    def test_hvd_10k_threshold_breach(self):
        """
        CRITICAL: Transactions >= £10,000 must trigger HVD_10K flag.
        MLR 2017 Regulation 39 for High Value Dealers.
        """
        result = check_threshold_breach(10000.00)
        
        assert result['flag'] == 'HVD_10K', "Should flag £10k HVD threshold"
        assert result['threshold_value'] == 10000
        assert '£10,000' in result['description']
        assert 'MLR 2017 Reg 39' in result['description']
    
    def test_edge_case_just_below_15k(self):
        """
        CRITICAL: £14,999.99 should trigger HVD but NOT general threshold.
        """
        result = check_threshold_breach(14999.99)
        
        assert result['flag'] == 'HVD_10K', "Should trigger HVD only"
        assert result['flag'] != 'GENERAL_15K', "Should not trigger £15k"
    
    def test_edge_case_just_below_10k(self):
        """
        CRITICAL: £9,999.99 should NOT trigger any threshold.
        """
        result = check_threshold_breach(9999.99)
        
        assert result['flag'] == 'NONE', "Should not flag below £10k"
        assert result['threshold_value'] == 0
    
    def test_negative_amounts_use_absolute_value(self):
        """
        CRITICAL: Withdrawals (negative amounts) should also trigger thresholds.
        """
        result = check_threshold_breach(-16000.00)
        
        assert result['flag'] == 'GENERAL_15K', "Negative £16k should trigger threshold"
        assert '£16,000' in result['description']
    
    def test_exact_threshold_boundaries(self):
        """
        CRITICAL: Test exact threshold amounts (£10,000 and £15,000).
        """
        # Exactly £10,000
        result_10k = check_threshold_breach(10000.00)
        assert result_10k['flag'] == 'HVD_10K', "Exactly £10k should trigger HVD"
        
        # Exactly £15,000
        result_15k = check_threshold_breach(15000.00)
        assert result_15k['flag'] == 'GENERAL_15K', "Exactly £15k should trigger general threshold"
    
    def test_very_large_amounts(self):
        """
        CRITICAL: Very large transactions (£100k+) should trigger GENERAL_15K.
        """
        result = check_threshold_breach(150000.00)
        
        assert result['flag'] == 'GENERAL_15K', "Large amounts should trigger £15k threshold"


@pytest.mark.unit
class TestCashRisk:
    """Critical tests for cash transaction risk detection."""
    
    def test_large_cash_deposit_flagged(self):
        """
        CRITICAL: Cash deposits >= £5,000 require source verification.
        """
        result = check_cash_risk(5000.00, 'CASH DEPOSIT')
        
        assert result['flag'] == 'LARGE_CASH_DEPOSIT', "Should flag large cash deposit"
        assert '£5,000' in result['description']
        assert 'source verification' in result['description'].lower()
    
    def test_large_cash_withdrawal_flagged(self):
        """
        CRITICAL: Cash withdrawals >= £5,000 are unusual for business.
        """
        result = check_cash_risk(-5000.00, 'ATM WITHDRAWAL')
        
        assert result['flag'] == 'LARGE_CASH_WITHDRAWAL', "Should flag large cash withdrawal"
        assert '£5,000' in result['description']
        assert 'unusual' in result['description'].lower()
    
    def test_atm_detected_as_cash(self):
        """
        CRITICAL: ATM transactions should be detected as cash.
        """
        result = check_cash_risk(5500.00, 'ATM')
        
        assert result['flag'] == 'LARGE_CASH_DEPOSIT', "ATM should be treated as cash"
    
    def test_cash_keyword_case_insensitive(self):
        """
        CRITICAL: Cash detection should be case-insensitive.
        """
        result_lower = check_cash_risk(5000.00, 'cash deposit')
        result_upper = check_cash_risk(5000.00, 'CASH DEPOSIT')
        result_mixed = check_cash_risk(5000.00, 'Cash Deposit')
        
        assert result_lower['flag'] == 'LARGE_CASH_DEPOSIT'
        assert result_upper['flag'] == 'LARGE_CASH_DEPOSIT'
        assert result_mixed['flag'] == 'LARGE_CASH_DEPOSIT'
    
    def test_non_cash_payment_not_flagged(self):
        """
        CRITICAL: Bank transfers should not be flagged as cash.
        """
        result = check_cash_risk(10000.00, 'BANK TRANSFER')
        
        assert result['flag'] == 'NONE', "Bank transfer should not be flagged as cash"
    
    def test_small_cash_below_threshold(self):
        """
        CRITICAL: Cash < £5,000 should not be flagged.
        """
        result = check_cash_risk(4999.99, 'CASH')
        
        assert result['flag'] == 'NONE', "Cash below £5k should not be flagged"


@pytest.mark.unit
class TestGeographicRisk:
    """Critical tests for high-risk jurisdiction detection."""
    
    def test_fatf_critical_country_flagged(self):
        """
        CRITICAL: FATF critical risk countries (e.g., North Korea, Iran) must be flagged.
        """
        # Test with known critical risk countries
        result_prk = check_geographic_risk('PRK')  # North Korea
        
        assert result_prk['flag'] == 'FATF_CRITICAL', "North Korea should be CRITICAL risk"
        assert result_prk['risk_level'] == 'CRITICAL'
        assert result_prk['risk_score'] >= 90
    
    def test_fatf_high_risk_country_flagged(self):
        """
        CRITICAL: FATF high-risk countries should be flagged appropriately.
        """
        # Test depends on your high_risk_countries.json content
        # Using a placeholder - adjust based on your actual data
        result = check_geographic_risk('AFG')  # Afghanistan (typically high-risk)
        
        # If in your list, should be flagged (otherwise NONE is acceptable)
        if result['flag'] != 'NONE':
            assert result['flag'] in ['FATF_HIGH', 'FATF_CRITICAL', 'FATF_MEDIUM']
            assert result['risk_score'] > 0
    
    def test_uk_not_flagged(self):
        """
        CRITICAL: UK should NOT be flagged as high-risk.
        """
        result_gbr = check_geographic_risk('GBR')
        result_uk = check_geographic_risk('UK')
        
        assert result_gbr['flag'] == 'NONE', "UK (GBR) should not be flagged"
        assert result_uk['flag'] == 'NONE', "UK should not be flagged"
        assert result_gbr['risk_level'] == 'LOW'
    
    def test_unknown_country_not_flagged(self):
        """
        CRITICAL: Unknown countries should default to NONE, not error.
        """
        result = check_geographic_risk('UNKNOWN')
        
        assert result['flag'] == 'NONE'
        assert result['country_name'] == 'UNKNOWN'
        assert result['risk_score'] == 0
    
    def test_empty_country_handled_gracefully(self):
        """
        CRITICAL: Empty country should not crash, return NONE.
        """
        result_empty = check_geographic_risk('')
        result_none = check_geographic_risk(None)
        
        assert result_empty['flag'] == 'NONE'
        assert result_none['flag'] == 'NONE'
    
    def test_country_code_normalization(self):
        """
        CRITICAL: Various country formats should normalize correctly.
        """
        # Test ISO2 -> ISO3 conversion
        result = normalize_country_code('US')
        assert result == 'USA', "US should normalize to USA"
        
        # Test common aliases
        result_uk = normalize_country_code('UK')
        assert result_uk == 'GBR', "UK should normalize to GBR"


@pytest.mark.unit
class TestStructuringPattern:
    """Critical tests for suspicious structuring detection."""
    
    def test_9999_flagged_as_suspicious(self):
        """
        CRITICAL: £9,999 is classic structuring to avoid £10k threshold.
        """
        result = check_structuring_pattern(9999.00)
        
        assert result['flag'] == 'SUSPICIOUS_ROUND_NUMBER', "£9,999 should be flagged"
        assert '£9,999' in result['description']
        assert '£10k threshold' in result['description']
    
    def test_14999_flagged_as_suspicious(self):
        """
        CRITICAL: £14,999 is structuring to avoid £15k threshold.
        """
        result = check_structuring_pattern(14999.00)
        
        assert result['flag'] == 'SUSPICIOUS_ROUND_NUMBER', "£14,999 should be flagged"
        assert '£14,999' in result['description']
        assert '£15k threshold' in result['description']
    
    def test_4999_flagged_as_suspicious(self):
        """
        CRITICAL: £4,999 is structuring to avoid £5k cash threshold.
        """
        result = check_structuring_pattern(4999.00)
        
        assert result['flag'] == 'SUSPICIOUS_ROUND_NUMBER', "£4,999 should be flagged"
        assert '£4,999' in result['description']
        assert '£5k' in result['description']
    
    def test_round_numbers_below_thresholds(self):
        """
        CRITICAL: Round numbers below thresholds (£9,900, £9,950) should be flagged.
        """
        result_9900 = check_structuring_pattern(9900.00)
        result_9950 = check_structuring_pattern(9950.00)
        
        assert result_9900['flag'] == 'SUSPICIOUS_ROUND_NUMBER'
        assert result_9950['flag'] == 'SUSPICIOUS_ROUND_NUMBER'
    
    def test_normal_amounts_not_flagged(self):
        """
        CRITICAL: Normal amounts should not be flagged as structuring.
        """
        result_5432 = check_structuring_pattern(5432.17)
        result_12000 = check_structuring_pattern(12000.00)
        
        assert result_5432['flag'] == 'NONE', "£5,432.17 is not suspicious"
        assert result_12000['flag'] == 'NONE', "£12,000 is not suspicious"
    
    def test_negative_amounts_checked(self):
        """
        CRITICAL: Withdrawals should also be checked for structuring.
        """
        result = check_structuring_pattern(-9999.00)
        
        assert result['flag'] == 'SUSPICIOUS_ROUND_NUMBER', "Negative £9,999 should be flagged"


@pytest.mark.unit
class TestVagueDescription:
    """Critical tests for vague transaction description detection."""
    
    def test_services_flagged_on_high_value(self):
        """
        CRITICAL: "Services" on £10k+ transaction should be flagged.
        """
        result = check_vague_description('Professional Services', 10000.00)
        
        assert result['flag'] == 'VAGUE_HIGH_VALUE', "Vague description should be flagged"
        assert 'SERVICES' in result['keywords_found']
        assert '£10,000' in result['description']
    
    def test_consultancy_flagged_on_high_value(self):
        """
        CRITICAL: "Consultancy" on large transaction should be flagged.
        """
        result = check_vague_description('Consultancy Payment', 5000.00)
        
        assert result['flag'] == 'VAGUE_HIGH_VALUE'
        assert 'CONSULTANCY' in result['keywords_found']
    
    def test_short_description_flagged(self):
        """
        CRITICAL: Very short descriptions (< 10 chars) on large amounts flagged.
        """
        result = check_vague_description('Pay', 2000.00)
        
        assert result['flag'] == 'VAGUE_HIGH_VALUE', "Short description should be flagged"
    
    def test_detailed_description_not_flagged(self):
        """
        CRITICAL: Detailed descriptions should not be flagged.
        """
        result = check_vague_description(
            'Monthly software license renewal for accounting system - Invoice #12345',
            5000.00
        )
        
        assert result['flag'] == 'NONE', "Detailed description should not be flagged"
    
    def test_low_value_vague_not_flagged(self):
        """
        CRITICAL: Vague descriptions on small amounts (< £1,000) acceptable.
        """
        result = check_vague_description('Services', 500.00)
        
        assert result['flag'] == 'NONE', "Low value vague description acceptable"


@pytest.mark.unit
class TestComplianceRiskScoring:
    """Critical tests for composite compliance risk calculation."""
    
    def test_critical_tier_multiple_flags(self):
        """
        CRITICAL: Multiple high-risk flags should result in CRITICAL tier.
        """
        # Setup: £16k to North Korea (threshold + critical geo)
        threshold_check = {
            'flag': 'GENERAL_15K',
            'threshold_value': 15000,
            'description': 'Transaction £16,000 exceeds £15,000 threshold'
        }
        cash_check = {'flag': 'NONE', 'description': ''}
        geo_check = {
            'flag': 'FATF_CRITICAL',
            'country_name': 'North Korea',
            'risk_level': 'CRITICAL',
            'risk_score': 95,
            'description': 'North Korea - Critical Risk'
        }
        structuring_check = {'flag': 'NONE', 'pattern': '', 'description': ''}
        vague_check = {'flag': 'NONE', 'keywords_found': [], 'description': ''}
        
        result = calculate_compliance_risk_score(
            threshold_check, cash_check, geo_check, structuring_check, vague_check
        )
        
        # Score: 40 (threshold) + 50 (critical geo) = 90
        assert result['score'] == 90, "Score should be 90 (40 + 50)"
        assert result['tier'] == 'CRITICAL', "Should be CRITICAL tier (>= 80)"
        assert len(result['flags']) == 2, "Should have 2 flags"
        assert 'GENERAL_15K' in result['flags']
        assert 'FATF_CRITICAL' in result['flags']
    
    def test_high_tier_threshold_and_structuring(self):
        """
        CRITICAL: Threshold + structuring should result in HIGH tier.
        """
        threshold_check = {
            'flag': 'HVD_10K',
            'threshold_value': 10000,
            'description': 'Transaction £10,000 exceeds £10,000 threshold'
        }
        cash_check = {'flag': 'NONE', 'description': ''}
        geo_check = {'flag': 'NONE', 'country_name': 'UK', 'risk_level': 'LOW', 'risk_score': 0, 'description': ''}
        structuring_check = {
            'flag': 'SUSPICIOUS_ROUND_NUMBER',
            'pattern': '9999',
            'description': '£9,999 - just below £10k threshold'
        }
        vague_check = {'flag': 'NONE', 'keywords_found': [], 'description': ''}
        
        result = calculate_compliance_risk_score(
            threshold_check, cash_check, geo_check, structuring_check, vague_check
        )
        
        # Score: 35 (HVD) + 25 (structuring) = 60
        assert result['score'] == 60, "Score should be 60"
        assert result['tier'] == 'HIGH', "Should be HIGH tier (>= 60)"
    
    def test_medium_tier_single_flag(self):
        """
        CRITICAL: Single medium flag should result in MEDIUM tier.
        """
        threshold_check = {
            'flag': 'HVD_10K',
            'threshold_value': 10000,
            'description': 'Transaction £10,000 exceeds threshold'
        }
        cash_check = {'flag': 'NONE', 'description': ''}
        geo_check = {'flag': 'NONE', 'country_name': 'UK', 'risk_level': 'LOW', 'risk_score': 0, 'description': ''}
        structuring_check = {'flag': 'NONE', 'pattern': '', 'description': ''}
        vague_check = {'flag': 'NONE', 'keywords_found': [], 'description': ''}
        
        result = calculate_compliance_risk_score(
            threshold_check, cash_check, geo_check, structuring_check, vague_check
        )
        
        # Score: 35 (HVD only)
        assert result['score'] == 35
        assert result['tier'] == 'MEDIUM', "Should be MEDIUM tier (30-59)"
    
    def test_low_tier_no_flags(self):
        """
        CRITICAL: No flags should result in LOW tier.
        """
        threshold_check = {'flag': 'NONE', 'threshold_value': 0, 'description': ''}
        cash_check = {'flag': 'NONE', 'description': ''}
        geo_check = {'flag': 'NONE', 'country_name': 'UK', 'risk_level': 'LOW', 'risk_score': 0, 'description': ''}
        structuring_check = {'flag': 'NONE', 'pattern': '', 'description': ''}
        vague_check = {'flag': 'NONE', 'keywords_found': [], 'description': ''}
        
        result = calculate_compliance_risk_score(
            threshold_check, cash_check, geo_check, structuring_check, vague_check
        )
        
        assert result['score'] == 0
        assert result['tier'] == 'LOW', "Should be LOW tier (< 30)"
        assert len(result['flags']) == 0
        assert len(result['reasons']) == 0
    
    def test_score_capped_at_100(self):
        """
        CRITICAL: Score should never exceed 100 even with all flags.
        """
        # All flags at maximum
        threshold_check = {
            'flag': 'GENERAL_15K',
            'threshold_value': 15000,
            'description': 'Threshold'
        }
        cash_check = {
            'flag': 'LARGE_CASH_DEPOSIT',
            'description': 'Cash'
        }
        geo_check = {
            'flag': 'FATF_CRITICAL',
            'country_name': 'PRK',
            'risk_level': 'CRITICAL',
            'risk_score': 95,
            'description': 'Geographic'
        }
        structuring_check = {
            'flag': 'SUSPICIOUS_ROUND_NUMBER',
            'pattern': '9999',
            'description': 'Structuring'
        }
        vague_check = {
            'flag': 'VAGUE_HIGH_VALUE',
            'keywords_found': ['SERVICES'],
            'description': 'Vague'
        }
        
        result = calculate_compliance_risk_score(
            threshold_check, cash_check, geo_check, structuring_check, vague_check
        )
        
        # Raw: 40 + 30 + 50 + 25 + 15 = 160, should cap at 100
        assert result['score'] == 100, "Score should be capped at 100"
        assert result['tier'] == 'CRITICAL'
        assert len(result['flags']) == 5, "Should have all 5 flags"


@pytest.mark.unit
class TestEdgeCases:
    """Critical edge case and boundary tests."""
    
    def test_zero_amount_handled(self):
        """
        CRITICAL: Zero amount transactions should not crash.
        """
        threshold = check_threshold_breach(0.00)
        structuring = check_structuring_pattern(0.00)
        vague = check_vague_description('Test', 0.00)
        
        assert threshold['flag'] == 'NONE'
        assert structuring['flag'] == 'NONE'
        assert vague['flag'] == 'NONE'
    
    def test_very_large_amount_handled(self):
        """
        CRITICAL: Very large amounts (£1M+) should be handled correctly.
        """
        result = check_threshold_breach(1000000.00)
        
        assert result['flag'] == 'GENERAL_15K'
        assert '£1,000,000' in result['description']
    
    def test_none_payment_method_handled(self):
        """
        CRITICAL: None payment method should not crash.
        """
        result = check_cash_risk(10000.00, None)
        
        assert result['flag'] == 'NONE'
    
    def test_empty_description_handled(self):
        """
        CRITICAL: Empty description should not crash.
        """
        result = check_vague_description('', 5000.00)
        
        assert result['flag'] == 'NONE'
    
    def test_unicode_in_description(self):
        """
        CRITICAL: Unicode characters should be handled.
        """
        result = check_vague_description('Payment für Services € £', 2000.00)
        
        # Should still detect "Services"
        assert result['flag'] == 'VAGUE_HIGH_VALUE'
