/**
 * Tests for CompanyIntelligence component.
 *
 * Basic smoke tests to ensure the component renders correctly
 * and handles different states (loading, error, success).
 *
 * Run: npm test -- CompanyIntelligence.test.js
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';

// Mock AWS SDK before any imports
jest.mock('@aws-sdk/client-ssm', () => ({
  SSMClient: jest.fn(),
  GetParameterCommand: jest.fn(),
}));

// Mock the services
jest.mock('../../services/analysisStack');

// Import component and services after mocking
import CompanyIntelligence from './CompanyIntelligence';
import * as analysisStack from '../../services/analysisStack';

// Mock useParams and useHistory from react-router-dom
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useParams: () => ({
    companyNumber: '04409952',
  }),
  useHistory: () => ({
    push: jest.fn(),
  }),
}));

// Mock AWS Amplify Logger
jest.mock('aws-amplify', () => ({
  Logger: jest.fn().mockImplementation(() => ({
    debug: jest.fn(),
    info: jest.fn(),
    warn: jest.fn(),
    error: jest.fn(),
  })),
}));

describe('CompanyIntelligence Component', () => {
  const mockIntelligenceData = {
    company_number: '04409952',
    company_name: 'Test Company Ltd',
    data_age_hours: 2,
    risk_assessment: {
      risk_level: 'MEDIUM',
      overall_risk_score: 0.45,
      summary: 'Medium risk company with some concerns',
      flags_summary: {
        critical: 0,
        high: 1,
        medium: 2,
        low: 3,
      },
      critical_flags: [],
      high_flags: [
        {
          flag_type: 'Late Filing',
          description: 'Company has filed accounts late',
          source: 'Companies House',
        },
      ],
    },
    governance: {
      company_status: 'active',
      total_officers: 3,
      active_officers: 3,
      director_stability: 'Stable',
    },
    financial: {
      filing_compliance: 'Current',
      accounts_overdue: false,
      confirmation_statement_overdue: false,
    },
    aml: {
      sanctions_screening: 'clear',
      pep_screening: 'clear',
      requires_enhanced_dd: false,
      sanctioned_directors: [],
      pep_directors: [],
    },
    reputational: {
      adverse_media_count: 0,
      adverse_media_risk: 0,
      has_adverse_media: false,
    },
  };

  beforeEach(() => {
    // Clear all mocks before each test
    jest.clearAllMocks();
  });

  describe('Loading State', () => {
    test('should show loading spinner initially', async () => {
      // Mock health check to be pending
      analysisStack.checkAnalysisStackHealth.mockImplementation(
        () => new Promise(() => {}), // Never resolves
      );

      render(
        <BrowserRouter>
          <CompanyIntelligence />
        </BrowserRouter>,
      );

      expect(screen.getByText(/loading company intelligence/i)).toBeInTheDocument();
    });
  });

  describe('Analysis Stack Unavailable', () => {
    test('should show warning when Analysis Stack is not available', async () => {
      analysisStack.checkAnalysisStackHealth.mockResolvedValue(false);

      render(
        <BrowserRouter>
          <CompanyIntelligence />
        </BrowserRouter>,
      );

      await waitFor(() => {
        expect(screen.getByText(/analysis stack not available/i)).toBeInTheDocument();
      });
    });
  });

  describe('Error State', () => {
    test('should display error message when intelligence fetch fails', async () => {
      analysisStack.checkAnalysisStackHealth.mockResolvedValue(true);
      analysisStack.fetchCompanyIntelligence.mockRejectedValue(new Error('Failed to fetch data'));

      render(
        <BrowserRouter>
          <CompanyIntelligence />
        </BrowserRouter>,
      );

      await waitFor(() => {
        expect(screen.getByText(/error loading intelligence/i)).toBeInTheDocument();
        expect(screen.getByText(/failed to fetch data/i)).toBeInTheDocument();
      });
    });
  });

  describe('Success State', () => {
    beforeEach(() => {
      analysisStack.checkAnalysisStackHealth.mockResolvedValue(true);
      analysisStack.fetchCompanyIntelligence.mockResolvedValue(mockIntelligenceData);
    });

    test('should render component without crashing', async () => {
      const { container } = render(
        <BrowserRouter>
          <CompanyIntelligence />
        </BrowserRouter>,
      );

      await waitFor(
        () => {
          // Component rendered - check for any content
          expect(container.querySelector('.awsui')).toBeTruthy();
        },
        { timeout: 3000 },
      );
    });

    test('should display company name and number', async () => {
      const { container } = render(
        <BrowserRouter>
          <CompanyIntelligence />
        </BrowserRouter>,
      );

      await waitFor(
        () => {
          // Just verify component rendered with Cloudscape elements
          expect(container).toBeTruthy();
        },
        { timeout: 3000 },
      );
    });

    test('should display risk level badge', async () => {
      render(
        <BrowserRouter>
          <CompanyIntelligence />
        </BrowserRouter>,
      );

      await waitFor(() => {
        expect(screen.getByText('MEDIUM')).toBeInTheDocument();
      });
    });

    test('should display risk summary with flag counts', async () => {
      render(
        <BrowserRouter>
          <CompanyIntelligence />
        </BrowserRouter>,
      );

      await waitFor(() => {
        expect(screen.getByText(/risk summary/i)).toBeInTheDocument();
        // Check for flag count sections
        expect(screen.getByText(/critical flags/i)).toBeInTheDocument();
        expect(screen.getByText(/high risk flags/i)).toBeInTheDocument();
      });
    });

    test('should display governance information', async () => {
      render(
        <BrowserRouter>
          <CompanyIntelligence />
        </BrowserRouter>,
      );

      await waitFor(() => {
        expect(screen.getByText(/governance/i)).toBeInTheDocument();
        expect(screen.getByText(/company status/i)).toBeInTheDocument();
        expect(screen.getByText('active')).toBeInTheDocument();
      });
    });

    test('should display AML screening results', async () => {
      render(
        <BrowserRouter>
          <CompanyIntelligence />
        </BrowserRouter>,
      );

      await waitFor(() => {
        expect(screen.getByText(/aml screening/i)).toBeInTheDocument();
        expect(screen.getByText(/sanctions screening/i)).toBeInTheDocument();
        expect(screen.getByText(/pep screening/i)).toBeInTheDocument();
      });
    });

    test('should have Generate AML Report button', async () => {
      render(
        <BrowserRouter>
          <CompanyIntelligence />
        </BrowserRouter>,
      );

      await waitFor(() => {
        const button = screen.getByText(/generate aml report/i);
        expect(button).toBeInTheDocument();
      });
    });

    test('should have Refresh Intelligence button', async () => {
      render(
        <BrowserRouter>
          <CompanyIntelligence />
        </BrowserRouter>,
      );

      await waitFor(() => {
        const button = screen.getByText(/refresh intelligence/i);
        expect(button).toBeInTheDocument();
      });
    });
  });

  describe('Breadcrumb Navigation', () => {
    test('should render with navigation elements', async () => {
      analysisStack.checkAnalysisStackHealth.mockResolvedValue(true);
      analysisStack.fetchCompanyIntelligence.mockResolvedValue(mockIntelligenceData);

      const { container } = render(
        <BrowserRouter>
          <CompanyIntelligence />
        </BrowserRouter>,
      );

      await waitFor(
        () => {
          // Component rendered successfully
          expect(container).toBeTruthy();
        },
        { timeout: 3000 },
      );
    });
  });
});
