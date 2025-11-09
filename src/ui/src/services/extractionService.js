// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Service for fetching extraction results (invoices, bank statements)
 */

import { API, graphqlOperation, Logger } from 'aws-amplify';
import listExtractionResultsQuery from '../graphql/queries/listExtractionResults';

const logger = new Logger('ExtractionService');

/**
 * Document types for extraction results
 */
export const DOCUMENT_TYPES = {
  INVOICE: 'INVOICE',
  BANK_STATEMENT: 'BANK_STATEMENT',
};

/**
 * Fetch extraction results for a company by document type
 * @param {string} companyNumber - Company number to filter by
 * @param {string} documentType - Type of document (INVOICE or BANK_STATEMENT)
 * @param {number} limit - Maximum number of results (default: 50)
 * @param {string} nextToken - Pagination token for next page
 * @returns {Promise<{items: Array, nextToken: string|null}>} Extraction results
 */
export const fetchExtractionResults = async (
  companyNumber,
  documentType,
  limit = 50,
  nextToken = null,
) => {
  try {
    logger.debug(
      `Fetching ${documentType} extraction results for company ${companyNumber}`,
    );

    const response = await API.graphql(
      graphqlOperation(listExtractionResultsQuery, {
        companyNumber,
        documentType,
        limit,
        nextToken,
      }),
    );

    const result = response?.data?.listExtractionResults || { items: [] };

    logger.debug(
      `Fetched ${result.items.length} extraction results, hasMore: ${!!result.nextToken}`,
    );

    return {
      items: result.items || [],
      nextToken: result.nextToken || null,
    };
  } catch (error) {
    logger.error('Error fetching extraction results:', error);
    throw error;
  }
};

/**
 * Format invoice data for display
 * @param {Object} extractionResult - Raw extraction result from DynamoDB
 * @returns {Object} Formatted invoice data
 */
export const formatInvoiceData = (extractionResult) => {
  return {
    id: extractionResult.DocumentId,
    invoiceNumber: extractionResult.InvoiceNumber || 'N/A',
    vendor: extractionResult.VendorName || 'Unknown Vendor',
    date: formatDate(extractionResult.InvoiceDate),
    dueDate: formatDate(extractionResult.DueDate),
    amount: formatCurrency(
      extractionResult.TotalAmount,
      extractionResult.Currency,
    ),
    status: extractionResult.ExtractionStatus || 'UNKNOWN',
    confidence: extractionResult.ConfidenceScore
      ? (extractionResult.ConfidenceScore * 100).toFixed(1) + '%'
      : 'N/A',
    supplierAddress: extractionResult.SupplierAddress || 'N/A',
    processedAt: extractionResult.ProcessedAt,
    s3Uri: extractionResult.S3Uri,
    rawData: extractionResult,
  };
};

/**
 * Format bank statement data for display
 * @param {Object} extractionResult - Raw extraction result from DynamoDB
 * @returns {Object} Formatted bank statement data
 */
export const formatBankStatementData = (extractionResult) => {
  return {
    id: extractionResult.DocumentId,
    bankName: extractionResult.BankName || 'Unknown Bank',
    accountNumber: extractionResult.AccountNumber
      ? maskAccountNumber(extractionResult.AccountNumber)
      : 'N/A',
    statementDate: formatDate(extractionResult.StatementDate),
    statementPeriod: extractionResult.StatementPeriod || 'N/A',
    openingBalance: formatCurrency(
      extractionResult.OpeningBalance,
      extractionResult.Currency,
    ),
    closingBalance: formatCurrency(
      extractionResult.ClosingBalance,
      extractionResult.Currency,
    ),
    status: extractionResult.ExtractionStatus || 'UNKNOWN',
    confidence: extractionResult.ConfidenceScore
      ? (extractionResult.ConfidenceScore * 100).toFixed(1) + '%'
      : 'N/A',
    processedAt: extractionResult.ProcessedAt,
    s3Uri: extractionResult.S3Uri,
    rawData: extractionResult,
  };
};

/**
 * Format date string to readable format
 * @param {string} dateString - ISO date string (YYYY-MM-DD)
 * @returns {string} Formatted date
 */
export const formatDate = (dateString) => {
  if (!dateString) return 'N/A';

  try {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-GB', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  } catch {
    return dateString;
  }
};

/**
 * Format currency amount
 * @param {number} amount - Amount value
 * @param {string} currency - Currency code (default: GBP)
 * @returns {string} Formatted currency string
 */
export const formatCurrency = (amount, currency = 'GBP') => {
  if (amount === null || amount === undefined) return 'N/A';

  try {
    return new Intl.NumberFormat('en-GB', {
      style: 'currency',
      currency: currency || 'GBP',
    }).format(amount);
  } catch {
    return `${currency} ${amount.toFixed(2)}`;
  }
};

/**
 * Mask account number for security (show last 4 digits)
 * @param {string} accountNumber - Full account number
 * @returns {string} Masked account number
 */
export const maskAccountNumber = (accountNumber) => {
  if (!accountNumber || accountNumber.length < 4) return accountNumber;

  const lastFour = accountNumber.slice(-4);
  const masked = '*'.repeat(Math.max(accountNumber.length - 4, 4));
  return `${masked}${lastFour}`;
};

/**
 * Get extraction status badge variant
 * @param {string} status - Extraction status
 * @returns {string} Cloudscape badge variant
 */
export const getStatusVariant = (status) => {
  const statusMap = {
    COMPLETED: 'success',
    PROCESSING: 'in-progress',
    FAILED: 'error',
    PENDING: 'warning',
  };

  return statusMap[status] || 'info';
};

/**
 * Sort extraction results by date (newest first)
 * @param {Array} results - Array of extraction results
 * @returns {Array} Sorted results
 */
export const sortByDateDescending = (results) => {
  return [...results].sort((a, b) => {
    const dateA = a.ProcessedAt || 0;
    const dateB = b.ProcessedAt || 0;
    return dateB - dateA;
  });
};
