"""
Integration tests for Analysis Stack API endpoints.

Tests the deployed Analysis Stack API endpoints to ensure:
- Health check is accessible
- Intelligence endpoint returns valid data
- Error handling works correctly
- Response schema matches expectations

Run these tests against a deployed stack:
    pytest tests/integration/analysis/test_analysis_stack_api.py -v
"""
import os
import pytest
import requests
from typing import Dict, Any

# Get API URL from environment or use default dev URL
API_URL = os.environ.get(
    'ANALYSIS_API_URL',
    'https://qruy5j9952.execute-api.eu-central-1.amazonaws.com/dev'
)

# Known test company (used in Analysis Stack tests)
TEST_COMPANY_NUMBER = '04409952'
INVALID_COMPANY_NUMBER = '99999999'


@pytest.mark.integration
@pytest.mark.smoke
class TestAnalysisStackHealth:
    """Tests for Analysis Stack health check endpoint."""

    def test_health_endpoint_is_accessible(self):
        """Should return 200 OK from /health endpoint."""
        response = requests.get(f"{API_URL}/health", timeout=10)
        
        assert response.status_code == 200, (
            f"Health check failed with status {response.status_code}"
        )

    def test_health_endpoint_returns_valid_json(self):
        """Should return valid JSON with status field."""
        response = requests.get(f"{API_URL}/health", timeout=10)
        data = response.json()
        
        assert "status" in data, "Health check response missing 'status' field"
        assert data["status"] in ["available", "healthy"], (
            f"Unexpected health status: {data['status']}"
        )

    def test_health_endpoint_includes_metadata(self):
        """Should include version and region metadata."""
        response = requests.get(f"{API_URL}/health", timeout=10)
        data = response.json()
        
        # These fields are optional but good to check
        assert "version" in data or "region" in data, (
            "Health check should include version or region metadata"
        )


@pytest.mark.integration
class TestIntelligenceEndpoint:
    """Tests for company intelligence endpoint."""

    def test_intelligence_endpoint_valid_company(self):
        """Should return 200 OK for valid company number."""
        response = requests.get(
            f"{API_URL}/company/{TEST_COMPANY_NUMBER}/intelligence",
            timeout=30
        )
        
        assert response.status_code == 200, (
            f"Intelligence endpoint failed with status {response.status_code}"
        )

    def test_intelligence_response_schema(self):
        """Should return intelligence data with required fields."""
        response = requests.get(
            f"{API_URL}/company/{TEST_COMPANY_NUMBER}/intelligence",
            timeout=30
        )
        
        data = response.json()
        
        # Check top-level structure
        required_fields = [
            'company_number',
            'company_name',
            'risk_assessment',
            'data_age_hours'
        ]
        
        for field in required_fields:
            assert field in data, f"Response missing required field: {field}"

    def test_intelligence_risk_assessment_structure(self):
        """Should include properly structured risk assessment."""
        response = requests.get(
            f"{API_URL}/company/{TEST_COMPANY_NUMBER}/intelligence",
            timeout=30
        )
        
        data = response.json()
        risk_assessment = data.get('risk_assessment', {})
        
        # Check risk assessment fields
        expected_fields = ['risk_level', 'overall_risk_score', 'flags_summary']
        for field in expected_fields:
            assert field in risk_assessment, (
                f"Risk assessment missing field: {field}"
            )
        
        # Validate risk level
        assert risk_assessment['risk_level'] in ['HIGH', 'MEDIUM', 'LOW'], (
            f"Invalid risk level: {risk_assessment['risk_level']}"
        )
        
        # Validate risk score is a number
        assert isinstance(risk_assessment['overall_risk_score'], (int, float)), (
            "Risk score should be numeric"
        )

    def test_intelligence_includes_governance_data(self):
        """Should include governance information."""
        response = requests.get(
            f"{API_URL}/company/{TEST_COMPANY_NUMBER}/intelligence",
            timeout=30
        )
        
        data = response.json()
        
        assert 'governance' in data, "Response missing governance data"
        governance = data['governance']
        
        # Check for key governance fields
        assert 'company_status' in governance, "Missing company_status"
        assert 'total_officers' in governance, "Missing total_officers"

    def test_intelligence_includes_aml_screening(self):
        """Should include AML screening results."""
        response = requests.get(
            f"{API_URL}/company/{TEST_COMPANY_NUMBER}/intelligence",
            timeout=30
        )
        
        data = response.json()
        
        assert 'aml' in data, "Response missing AML data"
        aml = data['aml']
        
        # Check for AML screening fields
        assert 'sanctions_screening' in aml, "Missing sanctions_screening"
        assert 'pep_screening' in aml, "Missing pep_screening"
        assert 'requires_enhanced_dd' in aml, "Missing requires_enhanced_dd"

    def test_intelligence_invalid_company_returns_404(self):
        """Should return 404 for non-existent company."""
        response = requests.get(
            f"{API_URL}/company/{INVALID_COMPANY_NUMBER}/intelligence",
            timeout=30
        )
        
        assert response.status_code == 404, (
            f"Expected 404 for invalid company, got {response.status_code}"
        )

    def test_intelligence_force_refresh_parameter(self):
        """Should accept force_refresh query parameter."""
        response = requests.get(
            f"{API_URL}/company/{TEST_COMPANY_NUMBER}/intelligence?force_refresh=true",
            timeout=30
        )
        
        assert response.status_code == 200, (
            "Force refresh should return 200 OK"
        )


@pytest.mark.integration
class TestAPIResponseTime:
    """Tests for API performance (basic smoke tests)."""

    def test_health_endpoint_responds_quickly(self):
        """Health check should respond in under 2 seconds."""
        import time
        
        start = time.time()
        response = requests.get(f"{API_URL}/health", timeout=10)
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 2.0, (
            f"Health check took {elapsed:.2f}s (should be < 2s)"
        )

    @pytest.mark.slow
    def test_intelligence_endpoint_responds_in_reasonable_time(self):
        """Intelligence endpoint should respond in under 30 seconds."""
        import time
        
        start = time.time()
        response = requests.get(
            f"{API_URL}/company/{TEST_COMPANY_NUMBER}/intelligence",
            timeout=30
        )
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 30.0, (
            f"Intelligence request took {elapsed:.2f}s (should be < 30s)"
        )


@pytest.mark.integration
class TestCORSHeaders:
    """Tests for CORS configuration."""

    def test_health_endpoint_has_cors_headers(self):
        """Should include CORS headers in response."""
        response = requests.get(f"{API_URL}/health", timeout=10)
        
        # Check for CORS headers (may be present)
        # This is important for frontend integration
        headers = response.headers
        
        # At minimum, the request should succeed
        assert response.status_code == 200
        
        # If CORS is configured, check the header
        if 'Access-Control-Allow-Origin' in headers:
            # Either wildcard or specific origin
            origin = headers['Access-Control-Allow-Origin']
            assert origin in ['*', 'https://fiscalshield.example.com'], (
                f"Unexpected CORS origin: {origin}"
            )


# Helper function for manual testing
def print_sample_response():
    """
    Print a sample intelligence response for documentation.
    Run with: pytest tests/integration/analysis/test_analysis_stack_api.py::print_sample_response -v -s
    """
    response = requests.get(
        f"{API_URL}/company/{TEST_COMPANY_NUMBER}/intelligence",
        timeout=30
    )
    
    import json
    print("\n" + "="*80)
    print("Sample Intelligence Response:")
    print("="*80)
    print(json.dumps(response.json(), indent=2))
    print("="*80 + "\n")


if __name__ == "__main__":
    # Quick manual test
    print(f"Testing Analysis Stack API at: {API_URL}")
    print_sample_response()
