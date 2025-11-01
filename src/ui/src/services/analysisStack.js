// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
import { Logger } from 'aws-amplify';
import { SSMClient, GetParameterCommand } from '@aws-sdk/client-ssm';

const logger = new Logger('AnalysisStackService');

const SSM_PARAM_NAME = '/fiscalshield/analysis/dev/api-url';
const REGION = 'eu-central-1';

let cachedApiUrl = null;

/**
 * Get Analysis Stack API URL from SSM Parameter Store
 */
const getAnalysisApiUrl = async () => {
  if (cachedApiUrl) {
    return cachedApiUrl;
  }

  try {
    const ssmClient = new SSMClient({ region: REGION });
    const command = new GetParameterCommand({ Name: SSM_PARAM_NAME });
    const response = await ssmClient.send(command);
    
    cachedApiUrl = response.Parameter.Value;
    logger.debug('Analysis Stack API URL retrieved:', cachedApiUrl);
    
    return cachedApiUrl;
  } catch (error) {
    logger.error('Failed to get Analysis Stack API URL:', error);
    throw error;
  }
};

/**
 * Check if Analysis Stack is available
 */
export const checkAnalysisStackHealth = async () => {
  try {
    const apiUrl = await getAnalysisApiUrl();
    const response = await fetch(`${apiUrl}/health`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      logger.warn('Analysis Stack health check failed:', response.status);
      return false;
    }

    const data = await response.json();
    logger.debug('Analysis Stack health check response:', data);
    
    return data.status === 'available';
  } catch (error) {
    logger.error('Analysis Stack health check error:', error);
    return false;
  }
};

/**
 * Fetch company intelligence data
 * @param {string} companyNumber - UK company number
 * @param {boolean} forceRefresh - Force fresh data calculation
 */
export const fetchCompanyIntelligence = async (companyNumber, forceRefresh = false) => {
  try {
    const apiUrl = await getAnalysisApiUrl();
    const url = `${apiUrl}/company/${companyNumber}/intelligence${forceRefresh ? '?force_refresh=true' : ''}`;
    
    logger.debug(`Fetching company intelligence for ${companyNumber}, force_refresh=${forceRefresh}`);
    
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      if (response.status === 404) {
        throw new Error('No intelligence data found for this company. Please gather company data first.');
      }
      throw new Error(`Failed to fetch company intelligence: ${response.statusText}`);
    }

    const data = await response.json();
    logger.debug('Company intelligence data received:', data);
    
    return data;
  } catch (error) {
    logger.error('Error fetching company intelligence:', error);
    throw error;
  }
};

/**
 * Generate AML report for a company (placeholder for future implementation)
 * @param {string} companyNumber - UK company number
 */
export const generateAMLReport = async (companyNumber) => {
  logger.debug(`AML report generation requested for ${companyNumber}`);
  
  // Placeholder: Check if Analysis Stack has report generation capability
  try {
    const available = await checkAnalysisStackHealth();
    if (!available) {
      throw new Error('Analysis Stack is not available');
    }
    
    // TODO: Implement actual report generation endpoint
    // For now, return a placeholder response
    return {
      success: false,
      message: 'AML report generation is not yet available. This feature requires the Analysis Stack to be fully deployed with AI report generation capability.',
      companyNumber,
      timestamp: new Date().toISOString(),
    };
  } catch (error) {
    logger.error('Error generating AML report:', error);
    throw error;
  }
};
