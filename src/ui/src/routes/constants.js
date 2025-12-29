// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
export const LOGIN_PATH = '/login';
export const LOGOUT_PATH = '/logout';
export const COMPANY_SELECT_PATH = '/company-select';
export const DOCUMENTS_PATH = '/documents';
export const DEFAULT_PATH = COMPANY_SELECT_PATH; // Changed: Company selection first
export const REDIRECT_URL_PARAM = 'redirect';
export const DOCUMENTS_KB_QUERY_PATH = `${DOCUMENTS_PATH}/query`;
export const DOCUMENTS_ANALYTICS_PATH = `${DOCUMENTS_PATH}/agents`;
export const CONFIGURATION_PATH = `${DOCUMENTS_PATH}/config`;
export const UPLOAD_DOCUMENT_PATH = `${DOCUMENTS_PATH}/upload`;
export const DISCOVERY_PATH = `${DOCUMENTS_PATH}/discovery`;
export const COMPANY_HUB_PATH = '/company/:companyNumber/hub';
export const COMPANY_INTELLIGENCE_PATH = '/company/:companyNumber/intelligence';
export const COMPANY_ANALYSIS_PATH = '/company/:companyNumber/analysis';
export const OVERVIEW_DASHBOARD_PATH = '/overview';
export const CLIENT_TAKEON_PATH = '/client-takeon';
export const INVOICE_INSIGHTS_PATH = '/invoice-insights';
export const INVOICE_ANALYSIS_PATH = '/invoice-analysis';
export const BANK_INSIGHTS_PATH = '/bank-insights';
export const ADMIN_VALIDATION_METRICS_PATH = '/admin/validation-metrics';
