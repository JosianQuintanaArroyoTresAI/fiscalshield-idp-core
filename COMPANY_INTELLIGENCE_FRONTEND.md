# Company Intelligence Frontend Implementation

## Overview
Implemented a comprehensive Company Intelligence page in the FiscalShield frontend to display risk assessments, AML analysis, and company insights for UK accountants. The page integrates with the Analysis Stack backend and provides a professional interface for compliance review.

## Implementation Date
2025-01-XX

## Features Implemented

### 1. Company Intelligence Page (`/company/:companyNumber/intelligence`)

**Key Features:**
- **Traffic Light Risk System**: Visual risk indicators (RED/AMBER/GREEN badges)
- **Risk Summary Dashboard**: Displays critical, high, medium, and low flag counts
- **Company Insights Grid**:
  - Governance metrics (directors, PSCs, appointments)
  - Financial health (accounts status, filing history)
  - AML risk indicators (PEP connections, sanctions, watchlists)
- **Reputational Analysis**: Adverse media tracking
- **Flags & Alerts**: Expandable section showing detailed risk flags
- **AML Report Generation**: Placeholder button for future LLM-powered report generation
- **Data Sources**: Shows collection status and data freshness

**UI Components Used:**
- AWS Cloudscape Design System (@awsui/components-react)
- BreadcrumbGroup for navigation
- Container, Header, SpaceBetween for layout
- Badge, StatusIndicator for status display
- Alert, ExpandableSection for progressive disclosure
- Button with loading states
- Grid/ColumnLayout for responsive design

### 2. Analysis Stack Service Integration

**Service File**: `/src/ui/src/services/analysisStack.js`

**Key Functions:**
- `getAnalysisApiUrl()`: Fetches API URL from SSM Parameter Store (`/fiscalshield/analysis/dev/api-url`)
- `checkAnalysisStackHealth()`: Validates Analysis Stack availability
- `fetchCompanyIntelligence(companyNumber, forceRefresh)`: Retrieves company intelligence data
- `generateAMLReport(companyNumber)`: **Placeholder** - Returns "not yet available" message

**SSM Integration:**
- Parameter: `/fiscalshield/analysis/dev/api-url`
- Region: `eu-central-1`
- Caching: API URL cached after first fetch to minimize SSM calls

### 3. Navigation Integration

**CompanyCard Updates** (`/src/ui/src/components/company-card/CompanyCard.jsx`):
- Added "View Intelligence" button alongside "View Documents"
- Button uses `status-info` icon for visual distinction
- New prop: `onViewIntelligence` callback

**CompanySelect Updates** (`/src/ui/src/components/company-select/CompanySelect.jsx`):
- Added import: `COMPANY_INTELLIGENCE_PATH` from route constants
- New handler: `handleViewCompanyIntelligence(company)`
- Stores company context in localStorage
- Navigates to `/company/{companyNumber}/intelligence`
- Passes handler to CompanyCard components

**Route Configuration** (`/src/ui/src/routes/AuthRoutes.jsx`):
- Added route: `<Route path={COMPANY_INTELLIGENCE_PATH}><CompanyIntelligence /></Route>`
- Route placed before `DOCUMENTS_PATH` for proper URL matching

## User Flow

1. User logs in → Company Select page
2. User's registered companies displayed in cards
3. Each card shows:
   - "View Intelligence" button (new) → Company Intelligence page
   - "View Documents" button → Documents page
4. On Intelligence page, user can:
   - View comprehensive risk assessment
   - Refresh intelligence data
   - Generate AML report (placeholder for now)
   - Navigate back to Company Select

## Technical Architecture

### Data Flow
```
Frontend (React) 
  → SSM Parameter Store (get API URL)
  → Analysis Stack API
  → GET /company/{companyNumber}/intelligence
  → Display in CompanyIntelligence component
```

### Component Hierarchy
```
CompanySelect
  └── CompanyCard (with onViewIntelligence)
        └── Navigates to CompanyIntelligence

CompanyIntelligence
  ├── BreadcrumbGroup
  ├── Hero Banner (Risk Assessment)
  ├── Risk Summary Card
  ├── Insights Grid
  │   ├── Governance Card
  │   ├── Financial Card
  │   └── AML Card
  ├── Reputational Section
  ├── Flags & Alerts Section
  ├── AML Report Section (placeholder)
  └── Data Sources Footer
```

### State Management
- `intelligence`: Company intelligence data from API
- `isLoading`: Initial page load state
- `isRefreshing`: Refresh button loading state
- `isGeneratingReport`: Report generation button loading state
- `error`: Error message display
- `reportMessage`: Placeholder message for AML report
- `isAnalysisStackAvailable`: Health check result

## API Endpoints Used

### Analysis Stack Endpoints
- **Health Check**: `GET /health`
  - Returns: `{ status: "healthy", version: "1.0.0", region: "eu-central-1" }`

- **Fetch Intelligence**: `GET /company/{companyNumber}/intelligence?force_refresh=true`
  - Returns: Comprehensive intelligence data including:
    - Risk level (HIGH/MEDIUM/LOW)
    - Risk score (0-100)
    - Flag counts (critical, high, medium, low)
    - Governance metrics
    - Financial metrics
    - AML risk indicators
    - Reputational data
    - Flags and alerts
    - Data sources status

- **Generate AML Report** (Placeholder): Currently returns error message
  - Future: Will call LLM Lambda to generate comprehensive AML compliance report

## Configuration

### SSM Parameters Required
```
Parameter Name: /fiscalshield/analysis/dev/api-url
Parameter Type: String
Value: https://qruy5j9952.execute-api.eu-central-1.amazonaws.com/dev
Region: eu-central-1
```

### Environment Requirements
- AWS Amplify configured for auth
- IAM permissions to read SSM parameters
- CORS enabled on Analysis Stack API

## Future Enhancements

### Phase 1: Real AML Report Generation
**Goal**: Replace placeholder with actual LLM-powered report generation

**Implementation Steps**:
1. Create Lambda function in Analysis Stack
2. Integrate with Amazon Bedrock / Claude
3. Implement prompt engineering for AML report generation
4. Generate structured report (PDF or HTML)
5. Store report in S3
6. Update `generateAMLReport()` service to call real endpoint
7. Display report in modal or new page

**Prompt Template** (example):
```
You are an AML compliance expert. Based on the following company intelligence data, 
generate a comprehensive AML risk assessment report suitable for UK accountants 
following Money Laundering Regulations 2017 (MLR 2017).

Company Data:
{intelligence_data}

Report Structure:
1. Executive Summary
2. Risk Assessment (HIGH/MEDIUM/LOW with justification)
3. Red Flags Analysis
4. Governance Review
5. Financial Health Assessment
6. PEP and Sanctions Screening Results
7. Reputational Risk Review
8. Recommendations for Enhanced Due Diligence
9. Regulatory Compliance Notes (MLR 2017)

Format: Professional, clear, actionable. Highlight critical issues first.
```

### Phase 2: Historical Tracking
- Track risk level changes over time
- Display trend graphs (risk score over 30/60/90 days)
- Alert notifications when risk increases

### Phase 3: Enhanced Features
- Export intelligence data (CSV/JSON/PDF)
- Email scheduled reports
- Comparison with industry benchmarks
- Integration with document analysis (cross-reference with invoices/receipts)
- Automated alerts for new flags

### Phase 4: Collaboration
- Share intelligence reports with team members
- Add notes/annotations to flags
- Create remediation tasks
- Audit trail of intelligence views

## Design Principles

### Professional UK Accountant Focus
- Clean, professional aesthetic using Cloudscape Design System
- Traffic light system for quick risk assessment
- Progressive disclosure (expandable sections for details)
- Data freshness indicators
- Clear regulatory context (MLR 2017)

### User Experience
- Fast loading with intelligent caching
- Graceful error handling
- Loading states for all async operations
- Breadcrumb navigation for easy back navigation
- Refresh button for data updates
- Responsive layout (desktop/tablet optimized)

### Compliance Focus
- Emphasis on AML risk indicators
- PEP and sanctions screening prominent
- Governance and ownership transparency
- Adverse media tracking
- Regulatory filing status

## Testing Checklist

### Frontend Testing
- [ ] Page loads correctly at `/company/:companyNumber/intelligence`
- [ ] SSM parameter fetch successful
- [ ] Analysis Stack health check works
- [ ] Intelligence data displays correctly
- [ ] Traffic light badges show correct colors
- [ ] Refresh button triggers data reload
- [ ] Generate AML Report button shows placeholder message
- [ ] Breadcrumb navigation works
- [ ] Error states display correctly
- [ ] Loading states show during async operations

### Integration Testing
- [ ] Navigation from CompanySelect → Intelligence works
- [ ] Company context stored in localStorage
- [ ] Back navigation to CompanySelect works
- [ ] Multiple company switches work correctly

### Browser Testing
- [ ] Chrome/Chromium
- [ ] Firefox
- [ ] Safari
- [ ] Edge

### Responsive Testing
- [ ] Desktop (1920x1080)
- [ ] Laptop (1366x768)
- [ ] Tablet (768x1024)

## Files Modified/Created

### New Files
1. `/src/ui/src/components/company-intelligence/CompanyIntelligence.jsx` (554 lines)
2. `/src/ui/src/components/company-intelligence/index.js` (3 lines)
3. `/src/ui/src/services/analysisStack.js` (124 lines)

### Modified Files
1. `/src/ui/src/routes/constants.js`
   - Added: `COMPANY_INTELLIGENCE_PATH = '/company/:companyNumber/intelligence'`

2. `/src/ui/src/routes/AuthRoutes.jsx`
   - Added import: `COMPANY_INTELLIGENCE_PATH`
   - Added import: `CompanyIntelligence` component
   - Added route: `<Route path={COMPANY_INTELLIGENCE_PATH}>...</Route>`

3. `/src/ui/src/components/company-card/CompanyCard.jsx`
   - Added prop: `onViewIntelligence`
   - Added handler: `handleViewIntelligence()`
   - Updated footer: Added "View Intelligence" button with SpaceBetween layout

4. `/src/ui/src/components/company-select/CompanySelect.jsx`
   - Added import: `COMPANY_INTELLIGENCE_PATH`
   - Added handler: `handleViewCompanyIntelligence(company)`
   - Updated CompanyCard: Added `onViewIntelligence={handleViewCompanyIntelligence}` prop

## Dependencies

### Required NPM Packages (Already Installed)
- `@awsui/components-react`: ^3.0.1487
- `@aws-sdk/client-ssm`: ^3.777.0
- `react`: ^17.0.2
- `react-router-dom`: ^5.3.4
- `aws-amplify`: ^5.3.11

### AWS Resources Required
- SSM Parameter: `/fiscalshield/analysis/dev/api-url`
- Analysis Stack API (deployed)
- IAM role with `ssm:GetParameter` permission

## Deployment Notes

### Pre-Deployment Checklist
1. Ensure Analysis Stack is deployed
2. Verify SSM parameter exists: `/fiscalshield/analysis/dev/api-url`
3. Verify API Gateway CORS configuration
4. Test health check endpoint: `GET /health`
5. Test intelligence endpoint with known company number

### Deployment Steps
1. Build frontend: `npm run build` (from `/src/ui`)
2. Deploy to S3/CloudFront (if using static hosting)
3. Verify Amplify configuration
4. Test login → Company Select → Intelligence flow
5. Verify SSM parameter access works in production

### Post-Deployment Verification
1. Open frontend URL
2. Login as test user
3. Navigate to Company Select
4. Click "View Intelligence" on a registered company
5. Verify intelligence data loads
6. Click "Refresh Intelligence"
7. Click "Generate AML Report" → Should show placeholder message
8. Check browser console for errors
9. Verify breadcrumb navigation works

## Known Limitations

### Current Implementation
- AML report generation is placeholder (returns "not yet available" message)
- No historical tracking (only current snapshot)
- No export functionality
- No email notifications
- Single user view (no team collaboration)

### Browser Compatibility
- Requires modern browser with ES6+ support
- JavaScript must be enabled
- Cookies/localStorage must be enabled

### Performance Considerations
- SSM calls cached but add latency on first load
- Intelligence data fetched on page load (not prefetched)
- Large flag lists may impact render performance
- No pagination for flags (all loaded at once)

## Support and Troubleshooting

### Common Issues

**Issue**: "Analysis Stack is not available"
- **Cause**: Health check failed or SSM parameter not found
- **Solution**: Verify Analysis Stack deployment and SSM parameter

**Issue**: "Failed to load intelligence data"
- **Cause**: API error or network issue
- **Solution**: Check browser console, verify API endpoint, check CORS

**Issue**: Navigation doesn't work
- **Cause**: React Router not configured correctly
- **Solution**: Verify route paths in constants.js and AuthRoutes.jsx

**Issue**: SSM permission denied
- **Cause**: IAM role missing `ssm:GetParameter` permission
- **Solution**: Update IAM role attached to Cognito identity pool

### Debug Mode
Enable debug logging in browser console:
```javascript
localStorage.setItem('aws-amplify-log-level', 'DEBUG');
```

View Analysis Stack service logs:
```javascript
// In browser console
window.localStorage.getItem('analysisApiUrl'); // Should show cached API URL
```

## Security Considerations

### Data Protection
- Intelligence data contains sensitive company information
- Must be protected with authentication (AWS Amplify)
- Company context stored in localStorage (cleared on logout)
- API calls use AWS Signature V4 authentication

### Access Control
- Only authenticated users can access intelligence pages
- User can only view intelligence for registered companies
- API enforces user-company relationship

### Best Practices
- Never log sensitive intelligence data
- Clear localStorage on logout
- Use HTTPS for all API calls
- Implement rate limiting on API
- Regular security audits

## Contact

For questions or issues related to Company Intelligence frontend:
- Review this documentation first
- Check browser console for errors
- Verify Analysis Stack deployment
- Contact development team

---

**Document Version**: 1.0  
**Last Updated**: 2025-01-XX  
**Author**: Development Team  
**Status**: Implementation Complete (Placeholder AML Report)
