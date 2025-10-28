// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Service for managing user companies
 */

import { API, graphqlOperation, Logger } from 'aws-amplify';
import getUserCompaniesQuery from '../graphql/queries/getUserCompanies';
import registerUserCompanyMutation from '../graphql/queries/registerUserCompany';

const logger = new Logger('UserCompaniesService');

/**
 * Register a company for the current user
 * @param {string} companyNumber - UK Companies House number
 * @param {string} companyName - Company name
 * @returns {Promise<boolean>} Registration success
 */
export const registerCompany = async (companyNumber, companyName) => {
  try {
    logger.debug(`Registering company ${companyNumber} (${companyName})`);

    const response = await API.graphql(
      graphqlOperation(registerUserCompanyMutation, {
        companyNumber,
        companyName,
      })
    );

    const success = response?.data?.registerUserCompany;

    if (success) {
      logger.debug('Company registered successfully');
    }

    return success;
  } catch (error) {
    logger.error('Error registering company:', error);
    throw error;
  }
};

/**
 * Fetch all companies registered under the current user
 * @returns {Promise<Array>} List of user companies with details
 */
export const fetchUserCompanies = async () => {
  try {
    logger.debug('Fetching user companies from GraphQL');

    const response = await API.graphql(graphqlOperation(getUserCompaniesQuery));

    const companies = response?.data?.getUserCompanies || [];

    logger.debug(`Fetched ${companies.length} companies for user`);

    return companies;
  } catch (error) {
    logger.error('Error fetching user companies:', error);
    throw error;
  }
};

/**
 * Format timestamp to readable date
 * @param {number} timestamp - Unix timestamp
 * @returns {string} Formatted date string
 */
export const formatCompanyDate = (timestamp) => {
  if (!timestamp) return 'N/A';

  const date = new Date(timestamp * 1000);
  return date.toLocaleDateString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
};

/**
 * Format timestamp to relative time (e.g., "2 days ago")
 * @param {number} timestamp - Unix timestamp
 * @returns {string} Relative time string
 */
export const formatRelativeTime = (timestamp) => {
  if (!timestamp) return 'N/A';

  const now = Date.now();
  const date = new Date(timestamp * 1000);
  const diffMs = now - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
  if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`;
  return `${Math.floor(diffDays / 365)} years ago`;
};
