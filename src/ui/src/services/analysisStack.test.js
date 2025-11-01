/**
 * Tests for Analysis Stack service layer.
 *
 * These tests validate the frontend service that communicates with the Analysis Stack API.
 * Tests include SSM parameter fetching, health checks, and intelligence data fetching.
 *
 * Run: npm test -- analysisStack.test.js
 */

// Mock AWS SDK before importing
jest.mock('@aws-sdk/client-ssm', () => ({
  SSMClient: jest.fn(),
  GetParameterCommand: jest.fn(),
}));

// Mock aws-amplify
jest.mock('aws-amplify', () => ({
  Auth: {
    currentUserCredentials: jest.fn(),
  },
  Logger: jest.fn().mockImplementation(() => ({
    debug: jest.fn(),
    info: jest.fn(),
    warn: jest.fn(),
    error: jest.fn(),
  })),
}));

// Mock aws-exports
jest.mock('../aws-exports', () => ({
  aws_project_region: 'eu-central-1',
}));

// Mock global fetch
global.fetch = jest.fn();

// Import after mocking
import { SSMClient, GetParameterCommand } from '@aws-sdk/client-ssm';
import { Auth } from 'aws-amplify';
import { checkAnalysisStackHealth, fetchCompanyIntelligence, generateAMLReport } from './analysisStack';

describe('Analysis Stack Service', () => {
  beforeEach(() => {
    // Clear all mocks before each test
    jest.clearAllMocks();

    // Mock Auth.currentUserCredentials to return valid credentials
    Auth.currentUserCredentials.mockResolvedValue({
      accessKeyId: 'test-access-key',
      secretAccessKey: 'test-secret-key',
      sessionToken: 'test-session-token',
    });

    // Reset cached API URL
    // Note: In real implementation, you might need to export a resetCache function
  });

  describe('SSM Parameter Store Integration', () => {
    test('should fetch API URL from SSM Parameter Store', async () => {
      // Mock SSM client
      const mockSend = jest.fn().mockResolvedValue({
        Parameter: {
          Value: 'https://test-api.execute-api.eu-central-1.amazonaws.com/dev',
        },
      });

      SSMClient.mockImplementation(() => ({
        send: mockSend,
      }));

      // Mock successful health check
      global.fetch.mockResolvedValue({
        ok: true,
        json: async () => ({ status: 'available' }),
      });

      // Call function that uses SSM
      await checkAnalysisStackHealth();

      // Verify SSM was called
      expect(mockSend).toHaveBeenCalledWith(expect.any(GetParameterCommand));
    });
  });

  describe('checkAnalysisStackHealth()', () => {
    beforeEach(() => {
      // Mock SSM for health check tests
      const mockSend = jest.fn().mockResolvedValue({
        Parameter: {
          Value: 'https://test-api.execute-api.eu-central-1.amazonaws.com/dev',
        },
      });

      SSMClient.mockImplementation(() => ({
        send: mockSend,
      }));
    });

    test('should return true when health check succeeds', async () => {
      global.fetch.mockResolvedValue({
        ok: true,
        json: async () => ({ status: 'available' }),
      });

      const result = await checkAnalysisStackHealth();

      expect(result).toBe(true);
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/health'),
        expect.objectContaining({
          method: 'GET',
        }),
      );
    });

    test('should return false when health check fails', async () => {
      global.fetch.mockResolvedValue({
        ok: false,
        status: 500,
      });

      const result = await checkAnalysisStackHealth();

      expect(result).toBe(false);
    });

    test('should return false when network error occurs', async () => {
      global.fetch.mockRejectedValue(new Error('Network error'));

      const result = await checkAnalysisStackHealth();

      expect(result).toBe(false);
    });
  });

  describe('fetchCompanyIntelligence()', () => {
    const TEST_COMPANY_NUMBER = '04409952';

    beforeEach(() => {
      // Mock SSM
      const mockSend = jest.fn().mockResolvedValue({
        Parameter: {
          Value: 'https://test-api.execute-api.eu-central-1.amazonaws.com/dev',
        },
      });

      SSMClient.mockImplementation(() => ({
        send: mockSend,
      }));
    });

    test('should fetch intelligence data for valid company', async () => {
      const mockIntelligence = {
        company_number: TEST_COMPANY_NUMBER,
        company_name: 'Test Company Ltd',
        risk_assessment: {
          risk_level: 'MEDIUM',
          overall_risk_score: 0.45,
          flags_summary: { critical: 0, high: 1, medium: 2, low: 3 },
        },
        governance: { company_status: 'active' },
        aml: { sanctions_screening: 'clear' },
      };

      global.fetch.mockResolvedValue({
        ok: true,
        json: async () => mockIntelligence,
      });

      const result = await fetchCompanyIntelligence(TEST_COMPANY_NUMBER);

      expect(result).toEqual(mockIntelligence);
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining(`/company/${TEST_COMPANY_NUMBER}/intelligence`),
        expect.any(Object),
      );
    });

    test('should include force_refresh parameter when requested', async () => {
      global.fetch.mockResolvedValue({
        ok: true,
        json: async () => ({}),
      });

      await fetchCompanyIntelligence(TEST_COMPANY_NUMBER, true);

      expect(global.fetch).toHaveBeenCalledWith(expect.stringContaining('force_refresh=true'), expect.any(Object));
    });

    test('should throw error for 404 response', async () => {
      global.fetch.mockResolvedValue({
        ok: false,
        status: 404,
        statusText: 'Not Found',
      });

      await expect(fetchCompanyIntelligence(TEST_COMPANY_NUMBER)).rejects.toThrow('No intelligence data found');
    });

    test('should throw error for other non-OK responses', async () => {
      global.fetch.mockResolvedValue({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
      });

      await expect(fetchCompanyIntelligence(TEST_COMPANY_NUMBER)).rejects.toThrow(
        'Failed to fetch company intelligence',
      );
    });
  });

  describe('generateAMLReport() - Placeholder', () => {
    const TEST_COMPANY_NUMBER = '04409952';

    beforeEach(() => {
      // Mock SSM
      const mockSend = jest.fn().mockResolvedValue({
        Parameter: {
          Value: 'https://test-api.execute-api.eu-central-1.amazonaws.com/dev',
        },
      });

      SSMClient.mockImplementation(() => ({
        send: mockSend,
      }));
    });

    test('should return placeholder message when Analysis Stack available', async () => {
      // Mock health check success
      global.fetch.mockResolvedValue({
        ok: true,
        json: async () => ({ status: 'available' }),
      });

      const result = await generateAMLReport(TEST_COMPANY_NUMBER);

      expect(result.success).toBe(false);
      expect(result.message).toContain('not yet available');
      expect(result.companyNumber).toBe(TEST_COMPANY_NUMBER);
    });

    test('should throw error when Analysis Stack unavailable', async () => {
      // Mock health check failure
      global.fetch.mockResolvedValue({
        ok: false,
        status: 500,
      });

      await expect(generateAMLReport(TEST_COMPANY_NUMBER)).rejects.toThrow('Analysis Stack is not available');
    });
  });
});
