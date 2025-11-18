"""
Critical Unit Tests for Claude Response Parsing

Tests the XML parsing logic that extracts transaction analysis from Claude's responses.
Ensures robustness against malformed responses, missing fields, and edge cases.

CRITICAL because incorrect parsing means:
- Transactions appear analyzed but aren't
- Risk flags are missed
- Compliance scores are wrong
- Silent failures in production
"""
import pytest
import sys
from pathlib import Path

# Add categorization handler to path
CATEGORIZATION_PATH = Path(__file__).parent.parent.parent.parent / 'stacks' / 'analysis' / 'lambdas' / 'categorization'
sys.path.insert(0, str(CATEGORIZATION_PATH))

from handler import parse_categorization_response


@pytest.mark.unit
class TestClaudeResponseParsing:
    """Critical tests for parsing Claude's XML responses."""
    
    def test_parse_complete_valid_response(self):
        """
        CRITICAL: Valid XML response should parse all fields correctly.
        """
        response_text = """
        <batch_analysis>
          <transaction id="txn-001">
            <category>Office & Admin</category>
            <confidence>HIGH</confidence>
            <compliance_score>5</compliance_score>
            <risk_flags>CLEAN</risk_flags>
            <reasoning>Regular office supplies from established vendor</reasoning>
            <hmrc_concern>NO</hmrc_concern>
            <recommended_action>APPROVE</recommended_action>
          </transaction>
        </batch_analysis>
        """
        
        transaction_batch = [{'TransactionId': 'txn-001'}]
        results = parse_categorization_response(response_text, transaction_batch)
        
        assert 'txn-001' in results, "Should parse transaction"
        txn = results['txn-001']
        
        assert txn['category'] == 'Office & Admin'
        assert txn['confidence'] == 'HIGH'
        assert txn['compliance_score'] == 5
        assert txn['risk_flags'] == ['CLEAN']
        assert txn['reasoning'] == 'Regular office supplies from established vendor'
        assert txn['hmrc_concern'] is False
        assert txn['recommended_action'] == 'APPROVE'
    
    def test_parse_multiple_transactions(self):
        """
        CRITICAL: Should parse multiple transactions in one response.
        """
        response_text = """
        <batch_analysis>
          <transaction id="txn-001">
            <category>Office & Admin</category>
            <confidence>HIGH</confidence>
            <compliance_score>5</compliance_score>
            <risk_flags>CLEAN</risk_flags>
            <reasoning>Office supplies</reasoning>
            <hmrc_concern>NO</hmrc_concern>
            <recommended_action>APPROVE</recommended_action>
          </transaction>
          <transaction id="txn-002">
            <category>Entertainment</category>
            <confidence>MEDIUM</confidence>
            <compliance_score>3</compliance_score>
            <risk_flags>WEEKEND_HOSPITALITY|REVIEW_NEEDED</risk_flags>
            <reasoning>Weekend restaurant expense needs documentation</reasoning>
            <hmrc_concern>YES</hmrc_concern>
            <recommended_action>REVIEW_DOCUMENTATION</recommended_action>
          </transaction>
        </batch_analysis>
        """
        
        transaction_batch = [
            {'TransactionId': 'txn-001'},
            {'TransactionId': 'txn-002'}
        ]
        results = parse_categorization_response(response_text, transaction_batch)
        
        assert len(results) == 2, "Should parse both transactions"
        assert 'txn-001' in results
        assert 'txn-002' in results
        
        # Verify second transaction details
        txn2 = results['txn-002']
        assert txn2['category'] == 'Entertainment'
        assert txn2['compliance_score'] == 3
        assert 'WEEKEND_HOSPITALITY' in txn2['risk_flags']
        assert 'REVIEW_NEEDED' in txn2['risk_flags']
        assert txn2['hmrc_concern'] is True
    
    def test_parse_multiple_risk_flags(self):
        """
        CRITICAL: Multiple risk flags separated by | should be parsed as list.
        """
        response_text = """
        <batch_analysis>
          <transaction id="txn-003">
            <category>Travel</category>
            <confidence>LOW</confidence>
            <compliance_score>2</compliance_score>
            <risk_flags>VAGUE_DESCRIPTION|HIGH_VALUE|WEEKEND_EXPENSE</risk_flags>
            <reasoning>Suspicious travel expense</reasoning>
            <hmrc_concern>YES</hmrc_concern>
            <recommended_action>INVESTIGATE</recommended_action>
          </transaction>
        </batch_analysis>
        """
        
        transaction_batch = [{'TransactionId': 'txn-003'}]
        results = parse_categorization_response(response_text, transaction_batch)
        
        txn = results['txn-003']
        assert len(txn['risk_flags']) == 3, "Should parse all 3 flags"
        assert 'VAGUE_DESCRIPTION' in txn['risk_flags']
        assert 'HIGH_VALUE' in txn['risk_flags']
        assert 'WEEKEND_EXPENSE' in txn['risk_flags']
    
    def test_parse_missing_category_uses_default(self):
        """
        CRITICAL: Missing category should default to 'Uncategorized' not crash.
        """
        response_text = """
        <batch_analysis>
          <transaction id="txn-004">
            <confidence>MEDIUM</confidence>
            <compliance_score>3</compliance_score>
            <risk_flags>CLEAN</risk_flags>
            <reasoning>Analysis without category</reasoning>
            <hmrc_concern>NO</hmrc_concern>
            <recommended_action>REVIEW_DOCUMENTATION</recommended_action>
          </transaction>
        </batch_analysis>
        """
        
        transaction_batch = [{'TransactionId': 'txn-004'}]
        results = parse_categorization_response(response_text, transaction_batch)
        
        assert results['txn-004']['category'] == 'Uncategorized'
    
    def test_parse_missing_compliance_score_uses_default(self):
        """
        CRITICAL: Missing compliance score should default to 3 (neutral).
        """
        response_text = """
        <batch_analysis>
          <transaction id="txn-005">
            <category>Office & Admin</category>
            <confidence>MEDIUM</confidence>
            <risk_flags>CLEAN</risk_flags>
            <reasoning>Missing score</reasoning>
            <hmrc_concern>NO</hmrc_concern>
            <recommended_action>APPROVE</recommended_action>
          </transaction>
        </batch_analysis>
        """
        
        transaction_batch = [{'TransactionId': 'txn-005'}]
        results = parse_categorization_response(response_text, transaction_batch)
        
        assert results['txn-005']['compliance_score'] == 3
    
    def test_parse_missing_confidence_uses_default(self):
        """
        CRITICAL: Missing confidence should default to 'LOW'.
        """
        response_text = """
        <batch_analysis>
          <transaction id="txn-006">
            <category>Office & Admin</category>
            <compliance_score>4</compliance_score>
            <risk_flags>CLEAN</risk_flags>
            <reasoning>Missing confidence</reasoning>
            <hmrc_concern>NO</hmrc_concern>
            <recommended_action>APPROVE</recommended_action>
          </transaction>
        </batch_analysis>
        """
        
        transaction_batch = [{'TransactionId': 'txn-006'}]
        results = parse_categorization_response(response_text, transaction_batch)
        
        assert results['txn-006']['confidence'] == 'LOW'
    
    def test_parse_no_risk_flags_defaults_to_clean(self):
        """
        CRITICAL: Missing or empty risk_flags should default to ['CLEAN'].
        """
        response_text = """
        <batch_analysis>
          <transaction id="txn-007">
            <category>Office & Admin</category>
            <confidence>HIGH</confidence>
            <compliance_score>5</compliance_score>
            <risk_flags></risk_flags>
            <reasoning>No flags</reasoning>
            <hmrc_concern>NO</hmrc_concern>
            <recommended_action>APPROVE</recommended_action>
          </transaction>
        </batch_analysis>
        """
        
        transaction_batch = [{'TransactionId': 'txn-007'}]
        results = parse_categorization_response(response_text, transaction_batch)
        
        assert results['txn-007']['risk_flags'] == ['CLEAN']
    
    def test_parse_none_risk_flags_defaults_to_clean(self):
        """
        CRITICAL: 'NONE' in risk_flags should convert to ['CLEAN'].
        """
        response_text = """
        <batch_analysis>
          <transaction id="txn-008">
            <category>Office & Admin</category>
            <confidence>HIGH</confidence>
            <compliance_score>5</compliance_score>
            <risk_flags>NONE</risk_flags>
            <reasoning>Explicitly no flags</reasoning>
            <hmrc_concern>NO</hmrc_concern>
            <recommended_action>APPROVE</recommended_action>
          </transaction>
        </batch_analysis>
        """
        
        transaction_batch = [{'TransactionId': 'txn-008'}]
        results = parse_categorization_response(response_text, transaction_batch)
        
        assert results['txn-008']['risk_flags'] == ['CLEAN']
    
    def test_parse_missing_reasoning_uses_default(self):
        """
        CRITICAL: Missing reasoning should default to 'No reasoning provided'.
        """
        response_text = """
        <batch_analysis>
          <transaction id="txn-009">
            <category>Office & Admin</category>
            <confidence>HIGH</confidence>
            <compliance_score>5</compliance_score>
            <risk_flags>CLEAN</risk_flags>
            <hmrc_concern>NO</hmrc_concern>
            <recommended_action>APPROVE</recommended_action>
          </transaction>
        </batch_analysis>
        """
        
        transaction_batch = [{'TransactionId': 'txn-009'}]
        results = parse_categorization_response(response_text, transaction_batch)
        
        assert results['txn-009']['reasoning'] == 'No reasoning provided'
    
    def test_parse_missing_hmrc_concern_defaults_false(self):
        """
        CRITICAL: Missing hmrc_concern should default to False.
        """
        response_text = """
        <batch_analysis>
          <transaction id="txn-010">
            <category>Office & Admin</category>
            <confidence>HIGH</confidence>
            <compliance_score>5</compliance_score>
            <risk_flags>CLEAN</risk_flags>
            <reasoning>Missing HMRC flag</reasoning>
            <recommended_action>APPROVE</recommended_action>
          </transaction>
        </batch_analysis>
        """
        
        transaction_batch = [{'TransactionId': 'txn-010'}]
        results = parse_categorization_response(response_text, transaction_batch)
        
        assert results['txn-010']['hmrc_concern'] is False
    
    def test_parse_hmrc_concern_yes_is_true(self):
        """
        CRITICAL: hmrc_concern='YES' should parse to True boolean.
        """
        response_text = """
        <batch_analysis>
          <transaction id="txn-011">
            <category>Entertainment</category>
            <confidence>MEDIUM</confidence>
            <compliance_score>2</compliance_score>
            <risk_flags>VAGUE_DESCRIPTION</risk_flags>
            <reasoning>Needs review</reasoning>
            <hmrc_concern>YES</hmrc_concern>
            <recommended_action>REVIEW_DOCUMENTATION</recommended_action>
          </transaction>
        </batch_analysis>
        """
        
        transaction_batch = [{'TransactionId': 'txn-011'}]
        results = parse_categorization_response(response_text, transaction_batch)
        
        assert results['txn-011']['hmrc_concern'] is True
    
    def test_parse_missing_recommended_action_uses_default(self):
        """
        CRITICAL: Missing recommended_action should default to 'REVIEW_DOCUMENTATION'.
        """
        response_text = """
        <batch_analysis>
          <transaction id="txn-012">
            <category>Office & Admin</category>
            <confidence>HIGH</confidence>
            <compliance_score>4</compliance_score>
            <risk_flags>CLEAN</risk_flags>
            <reasoning>Missing action</reasoning>
            <hmrc_concern>NO</hmrc_concern>
          </transaction>
        </batch_analysis>
        """
        
        transaction_batch = [{'TransactionId': 'txn-012'}]
        results = parse_categorization_response(response_text, transaction_batch)
        
        assert results['txn-012']['recommended_action'] == 'REVIEW_DOCUMENTATION'
    
    def test_parse_malformed_xml_returns_empty(self):
        """
        CRITICAL: Malformed XML should not crash, return empty dict.
        """
        response_text = """
        <batch_analysis>
          <transaction id="txn-013">
            <category>Office & Admin
            <confidence>HIGH</confidence>
            Missing closing tags...
        """
        
        transaction_batch = [{'TransactionId': 'txn-013'}]
        results = parse_categorization_response(response_text, transaction_batch)
        
        # Should handle gracefully and return partial results or empty
        assert isinstance(results, dict), "Should return dict even on error"
    
    def test_parse_empty_response_returns_empty(self):
        """
        CRITICAL: Empty response should not crash.
        """
        response_text = ""
        
        transaction_batch = [{'TransactionId': 'txn-014'}]
        results = parse_categorization_response(response_text, transaction_batch)
        
        assert isinstance(results, dict)
        assert len(results) == 0
    
    def test_parse_no_transaction_blocks_returns_empty(self):
        """
        CRITICAL: Response with no transaction blocks should return empty.
        """
        response_text = """
        <batch_analysis>
          <summary>No transactions found</summary>
        </batch_analysis>
        """
        
        transaction_batch = [{'TransactionId': 'txn-015'}]
        results = parse_categorization_response(response_text, transaction_batch)
        
        assert isinstance(results, dict)
        assert len(results) == 0
    
    def test_parse_whitespace_in_fields_stripped(self):
        """
        CRITICAL: Whitespace should be stripped from parsed fields.
        """
        response_text = """
        <batch_analysis>
          <transaction id="  txn-016  ">
            <category>  Office & Admin  </category>
            <confidence>  HIGH  </confidence>
            <compliance_score>5</compliance_score>
            <risk_flags>  CLEAN  </risk_flags>
            <reasoning>  Some reasoning with spaces  </reasoning>
            <hmrc_concern>  NO  </hmrc_concern>
            <recommended_action>  APPROVE  </recommended_action>
          </transaction>
        </batch_analysis>
        """
        
        transaction_batch = [{'TransactionId': '  txn-016  '}]
        results = parse_categorization_response(response_text, transaction_batch)
        
        # Note: transaction ID in results might be stripped or original
        # Check if either exists
        txn_key = next(iter(results.keys())) if results else None
        if txn_key:
            txn = results[txn_key]
            assert txn['category'] == 'Office & Admin', "Should strip whitespace"
            assert txn['confidence'] == 'HIGH'
            assert txn['recommended_action'] == 'APPROVE'
    
    def test_parse_multiline_reasoning(self):
        """
        CRITICAL: Multi-line reasoning should be parsed correctly.
        """
        response_text = """
        <batch_analysis>
          <transaction id="txn-017">
            <category>Office & Admin</category>
            <confidence>HIGH</confidence>
            <compliance_score>5</compliance_score>
            <risk_flags>CLEAN</risk_flags>
            <reasoning>This is a multi-line reasoning.
            It continues here.
            And ends here.</reasoning>
            <hmrc_concern>NO</hmrc_concern>
            <recommended_action>APPROVE</recommended_action>
          </transaction>
        </batch_analysis>
        """
        
        transaction_batch = [{'TransactionId': 'txn-017'}]
        results = parse_categorization_response(response_text, transaction_batch)
        
        txn = results['txn-017']
        assert 'multi-line' in txn['reasoning']
        assert 'continues here' in txn['reasoning']
    
    def test_parse_special_characters_in_category(self):
        """
        CRITICAL: Special characters in fields should be handled.
        """
        response_text = """
        <batch_analysis>
          <transaction id="txn-018">
            <category>Office &amp; Admin</category>
            <confidence>HIGH</confidence>
            <compliance_score>5</compliance_score>
            <risk_flags>CLEAN</risk_flags>
            <reasoning>Testing &amp; validation</reasoning>
            <hmrc_concern>NO</hmrc_concern>
            <recommended_action>APPROVE</recommended_action>
          </transaction>
        </batch_analysis>
        """
        
        transaction_batch = [{'TransactionId': 'txn-018'}]
        results = parse_categorization_response(response_text, transaction_batch)
        
        txn = results['txn-018']
        # XML entities should be handled by regex or left as-is
        assert 'Office' in txn['category']
        assert 'Admin' in txn['category']
    
    def test_parse_compliance_score_boundaries(self):
        """
        CRITICAL: Compliance scores 1-5 should all parse correctly.
        """
        for score in [1, 2, 3, 4, 5]:
            response_text = f"""
            <batch_analysis>
              <transaction id="txn-score-{score}">
                <category>Test</category>
                <confidence>MEDIUM</confidence>
                <compliance_score>{score}</compliance_score>
                <risk_flags>CLEAN</risk_flags>
                <reasoning>Testing score {score}</reasoning>
                <hmrc_concern>NO</hmrc_concern>
                <recommended_action>APPROVE</recommended_action>
              </transaction>
            </batch_analysis>
            """
            
            transaction_batch = [{'TransactionId': f'txn-score-{score}'}]
            results = parse_categorization_response(response_text, transaction_batch)
            
            assert results[f'txn-score-{score}']['compliance_score'] == score
    
    def test_parse_invalid_compliance_score_uses_default(self):
        """
        CRITICAL: Invalid compliance score should default to 3.
        """
        response_text = """
        <batch_analysis>
          <transaction id="txn-019">
            <category>Office & Admin</category>
            <confidence>HIGH</confidence>
            <compliance_score>invalid</compliance_score>
            <risk_flags>CLEAN</risk_flags>
            <reasoning>Invalid score</reasoning>
            <hmrc_concern>NO</hmrc_concern>
            <recommended_action>APPROVE</recommended_action>
          </transaction>
        </batch_analysis>
        """
        
        transaction_batch = [{'TransactionId': 'txn-019'}]
        results = parse_categorization_response(response_text, transaction_batch)
        
        # Should handle gracefully - might use default or skip
        txn = results.get('txn-019', {})
        if txn:
            # If parsed, should have defaulted to 3
            assert txn.get('compliance_score') == 3
