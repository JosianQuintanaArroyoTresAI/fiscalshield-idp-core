# Analysis Stack Testing

Minimal test suite for Analysis Stack backend API and frontend integration.

## 📁 Test Structure

```
tests/integration/analysis/
├── __init__.py
└── test_analysis_stack_api.py          # Backend API integration tests

src/ui/src/
├── services/
│   └── analysisStack.test.js           # Service layer unit tests
└── components/company-intelligence/
    └── CompanyIntelligence.test.js     # Component rendering tests
```

## 🚀 Quick Start

### Backend Tests (Python/pytest)

```bash
# From project root
pytest tests/integration/analysis/ -v

# Run with specific test
pytest tests/integration/analysis/test_analysis_stack_api.py::TestAnalysisStackHealth::test_health_endpoint_is_accessible -v

# Run smoke tests only
pytest tests/integration/analysis/ -m smoke -v

# Skip slow tests
pytest tests/integration/analysis/ -m "not slow" -v
```

### Frontend Tests (JavaScript/Jest)

```bash
# From src/ui directory
cd src/ui

# Run all tests
npm test

# Run specific test file
npm test -- analysisStack.test.js

# Run with coverage
npm test -- --coverage

# Run in watch mode
npm test -- --watch
```

## 📊 Test Coverage

### Backend API Tests (Integration)

**Purpose**: Verify deployed Analysis Stack API endpoints work correctly

✅ **Health Check Endpoint**
- Accessible and returns 200 OK
- Returns valid JSON with status field
- Includes version/region metadata

✅ **Intelligence Endpoint**
- Returns 200 for valid company
- Response includes all required fields
- Risk assessment structure is correct
- Governance data is present
- AML screening data is present
- Returns 404 for invalid company
- Accepts force_refresh parameter

✅ **Performance**
- Health check responds in < 2 seconds
- Intelligence endpoint responds in < 30 seconds

✅ **CORS Configuration**
- CORS headers present for frontend integration

**Run Location**: Against deployed stack (dev/staging/prod)

```bash
# Test against dev
ANALYSIS_API_URL=https://qruy5j9952.execute-api.eu-central-1.amazonaws.com/dev \
pytest tests/integration/analysis/ -v

# Test against different environment
ANALYSIS_API_URL=https://your-api-url.amazonaws.com/prod \
pytest tests/integration/analysis/ -v
```

### Frontend Service Tests (Unit)

**Purpose**: Verify frontend service layer logic without external dependencies

✅ **SSM Parameter Store Integration**
- Fetches API URL from SSM Parameter Store
- Handles SSM errors gracefully

✅ **Health Check Function**
- Returns true on success
- Returns false on failure
- Handles network errors

✅ **Intelligence Fetching**
- Fetches data for valid company
- Includes force_refresh parameter when requested
- Throws appropriate errors for 404
- Throws appropriate errors for other failures

✅ **AML Report (Placeholder)**
- Returns placeholder message when stack available
- Throws error when stack unavailable

**Run Location**: Local, mocked (no external dependencies)

### Frontend Component Tests (Unit)

**Purpose**: Ensure React component renders correctly in different states

✅ **Rendering States**
- Shows loading spinner initially
- Shows warning when Analysis Stack unavailable
- Displays error message on fetch failure
- Renders successfully with valid data

✅ **Content Display**
- Company name and number displayed
- Risk level badge shown
- Risk summary with flag counts
- Governance information rendered
- AML screening results shown
- Generate AML Report button present
- Refresh Intelligence button present

✅ **Navigation**
- Breadcrumb navigation displayed
- Links to Company Select page

**Run Location**: Local, mocked (JSDOM test environment)

## 🎯 Test Markers (Backend)

```bash
# Smoke tests (fast, critical path)
pytest tests/integration/analysis/ -m smoke

# Integration tests (may hit real API)
pytest tests/integration/analysis/ -m integration

# Slow tests (> 5 seconds)
pytest tests/integration/analysis/ -m slow

# Exclude slow tests
pytest tests/integration/analysis/ -m "not slow"
```

## 🔧 Configuration

### Backend Test Configuration

Tests use environment variable for API URL:

```bash
export ANALYSIS_API_URL="https://your-api-url.amazonaws.com/dev"
```

Default if not set: `https://qruy5j9952.execute-api.eu-central-1.amazonaws.com/dev`

Test company number: `04409952` (known test company from Analysis Stack)

### Frontend Test Configuration

Tests automatically mock:
- AWS SDK SSM Client
- Fetch API calls
- React Router hooks (useParams, useHistory)
- AWS Amplify Logger

## 📈 Coverage Goals

| Component | Current Coverage | Target | Notes |
|-----------|------------------|--------|-------|
| Backend API | ~80% | 80%+ | Integration tests cover main paths |
| Frontend Service | ~85% | 80%+ | Unit tests with mocks |
| Frontend Component | ~70% | 70%+ | Basic rendering tests |

**Philosophy**: Test critical paths thoroughly, not 100% coverage.

## 🚦 CI/CD Integration

### GitHub Actions Example

```yaml
name: Analysis Stack Tests

on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -r requirements-dev.txt
      
      - name: Run backend tests
        run: pytest tests/integration/analysis/ -v -m "not slow"
        env:
          ANALYSIS_API_URL: ${{ secrets.ANALYSIS_API_URL }}

  frontend-tests:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: src/ui
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '16'
      
      - name: Install dependencies
        run: npm ci
      
      - name: Run frontend tests
        run: npm test -- --coverage --watchAll=false
```

## 🆘 Troubleshooting

### Backend Tests Failing

**Issue**: `ConnectionError: Failed to establish connection`
- **Cause**: API not deployed or incorrect URL
- **Fix**: Verify `ANALYSIS_API_URL` and stack deployment

**Issue**: `Test timeout after 30s`
- **Cause**: Lambda cold start or large dataset
- **Fix**: Increase timeout or skip slow tests with `-m "not slow"`

**Issue**: `404 on intelligence endpoint`
- **Cause**: Test company data not collected yet
- **Fix**: Run data collection for company `04409952` first

### Frontend Tests Failing

**Issue**: `Cannot find module '@aws-sdk/client-ssm'`
- **Cause**: Dependencies not installed
- **Fix**: Run `npm install` in `src/ui` directory

**Issue**: `Test suite failed to run: ReferenceError: fetch is not defined`
- **Cause**: Test environment missing fetch mock
- **Fix**: Ensure `global.fetch = jest.fn()` is in test file

**Issue**: `Warning: ReactDOM.render is no longer supported`
- **Cause**: Using newer testing library with React 17
- **Fix**: This is a warning, tests still work. Upgrade React if needed.

## 📚 Best Practices

### ✅ Do's

- ✅ **Test critical paths**: Focus on features that break the app
- ✅ **Mock external services**: Never hit real AWS in unit tests
- ✅ **Use descriptive test names**: `test_intelligence_endpoint_valid_company`
- ✅ **Test error paths**: Don't just test happy paths
- ✅ **Keep tests fast**: Unit tests < 1s, integration tests < 30s
- ✅ **Run tests before commits**: Catch issues early

### ❌ Don'ts

- ❌ **Don't aim for 100% coverage**: Diminishing returns
- ❌ **Don't test framework code**: Trust React/AWS SDK works
- ❌ **Don't over-mock**: Some integration is good
- ❌ **Don't skip slow tests in CI**: Run them on deployment
- ❌ **Don't commit broken tests**: Fix or skip them

## 🎯 Future Improvements

### Phase 1 (Optional)
- [ ] Add E2E tests with Playwright/Cypress
- [ ] Add visual regression tests for UI
- [ ] Add load testing for API endpoints

### Phase 2 (When needed)
- [ ] Add mutation testing to verify test quality
- [ ] Add contract tests between frontend/backend
- [ ] Add chaos engineering tests

### Phase 3 (Production)
- [ ] Add synthetic monitoring in production
- [ ] Add real user monitoring (RUM)
- [ ] Add A/B testing framework

## 📖 Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Jest Documentation](https://jestjs.io/)
- [React Testing Library](https://testing-library.com/react)
- [Testing Best Practices](https://testingjavascript.com/)

---

**Created**: 2025-11-01  
**Last Updated**: 2025-11-01  
**Maintainer**: Development Team
