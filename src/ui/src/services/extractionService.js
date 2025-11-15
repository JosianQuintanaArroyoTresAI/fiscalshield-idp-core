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
export const fetchExtractionResults = async (companyNumber, documentType, limit = 50, nextToken = null) => {
  try {
    logger.debug(`Fetching ${documentType} extraction results for company ${companyNumber}`);
    console.log(`[EXTRACTION SERVICE] Fetching ${documentType} for company ${companyNumber}, limit: ${limit}`);

    const response = await API.graphql(
      graphqlOperation(listExtractionResultsQuery, {
        companyNumber,
        documentType,
        limit,
        nextToken,
      }),
    );

    console.log('[EXTRACTION SERVICE] GraphQL Response:', response);
    console.log('[EXTRACTION SERVICE] Response data:', response?.data);
    console.log('[EXTRACTION SERVICE] listExtractionResults:', response?.data?.listExtractionResults);

    const result = response?.data?.listExtractionResults || { items: [] };

    logger.debug(`Fetched ${result.items.length} extraction results, hasMore: ${!!result.nextToken}`);
    console.log(`[EXTRACTION SERVICE] ✅ Fetched ${result.items.length} items`);
    console.log('[EXTRACTION SERVICE] First 2 items:', result.items.slice(0, 2));

    return {
      items: result.items || [],
      nextToken: result.nextToken || null,
    };
  } catch (error) {
    logger.error('Error fetching extraction results:', error);
    console.error('[EXTRACTION SERVICE] ❌ Full error:', error);
    console.error('[EXTRACTION SERVICE] Error message:', error.message);
    console.error('[EXTRACTION SERVICE] Error errors:', error.errors);
    console.error('[EXTRACTION SERVICE] Error stack:', error.stack);
    throw error;
  }
};

/**
 * Format invoice data for display
 * @param {Object} extractionResult - Raw extraction result from DynamoDB
 * @returns {Object} Formatted invoice data
 */
export const formatInvoiceData = (extractionResult) => {
  const compositeConf = extractionResult.CompositeConfidence || extractionResult.ConfidenceScore;

  return {
    id: extractionResult.DocumentId,
    invoiceNumber: extractionResult.InvoiceNumber || 'N/A',
    invoiceType: extractionResult.InvoiceType || 'SUPPLIER_INVOICE',
    vendor: extractionResult.VendorName || 'Unknown Vendor',
    date: formatDate(extractionResult.InvoiceDate),
    dueDate: formatDate(extractionResult.DueDate),
    amount: formatCurrency(extractionResult.TotalAmount, extractionResult.Currency),
    status: extractionResult.ExtractionStatus || 'UNKNOWN',
    confidence: compositeConf ? (compositeConf * 100).toFixed(1) + '%' : 'N/A',
    qualityTier: extractionResult.QualityTier || 'N/A',
    hitlRequired: extractionResult.HITLRequired || false,
    hitlReason: extractionResult.HITLReason || '',
    supplierAddress: extractionResult.SupplierAddress || 'N/A',
    processedAt: extractionResult.ProcessedAt,
    s3Uri: extractionResult.S3Uri,
    // Field-level confidence scores
    confidenceScores: {
      composite: compositeConf,
      invoiceType: extractionResult.InvoiceTypeConfidence,
      supplierName: extractionResult.SupplierNameConfidence,
      totalAmount: extractionResult.TotalAmountConfidence,
      invoiceNumber: extractionResult.InvoiceNumberConfidence,
      vatNumber: extractionResult.VATNumberConfidence,
      invoiceDate: extractionResult.InvoiceDateConfidence,
    },
    rawData: extractionResult,
  };
};

/**
 * Format bank statement data for display
 * @param {Object} extractionResult - Raw extraction result from DynamoDB
 * @returns {Object} Formatted bank statement data (transactions, not summaries)
 */
export const formatBankStatementData = (extractionResult) => {
  // Format processed date
  const processedDate = extractionResult.ProcessedAt
    ? new Date(extractionResult.ProcessedAt * 1000).toLocaleDateString('en-GB', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
      })
    : 'N/A';

  // Format transaction date
  const transactionDate = formatDate(extractionResult.TransactionDate);

  // Determine transaction type display
  const transactionType = extractionResult.TransactionType || 'UNKNOWN';
  const amount = extractionResult.TransactionAmount || 0;

  return {
    id: extractionResult.TransactionId || extractionResult.DocumentId,
    bankName: extractionResult.BankName || 'Unknown Bank',
    accountNumber: extractionResult.AccountNumber ? maskAccountNumber(extractionResult.AccountNumber) : 'N/A',
    sortCode: extractionResult.SortCode || 'N/A',
    transactionDate: transactionDate,
    transactionDescription: extractionResult.TransactionDescription || 'N/A',
    reference: extractionResult.Reference || 'N/A',
    transactionAmount: amount,
    formattedAmount: formatCurrency(Math.abs(amount), extractionResult.Currency || 'GBP'),
    transactionType: transactionType,
    accountBalance: formatCurrency(extractionResult.AccountBalance, extractionResult.Currency || 'GBP'),
    confidence: extractionResult.CompositeConfidence
      ? (extractionResult.CompositeConfidence * 100).toFixed(0) + '%'
      : 'N/A',
    qualityTier: extractionResult.QualityTier || 'N/A',
    analysisStatus: extractionResult.AnalysisStatus || 'PENDING',
    sourcePage: extractionResult.SourcePage || 'N/A',
    processedDate: processedDate,
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
 * Fetch individual transactions for a specific bank statement
 * @param {string} documentId - Document ID containing the transactions
 * @param {string} sectionId - Section ID for the statement
 * @returns {Promise<Array>} Array of transaction records
 */
export const fetchStatementTransactions = async (documentId, sectionId) => {
  try {
    logger.debug(`Fetching transactions for document ${documentId}, section ${sectionId}`);

    // For now, we'll query DynamoDB directly via a custom query
    // In production, you'd want to add a GraphQL query for this
    // The transactions have SK pattern: type#BANK_STATEMENT#section#{sectionId}#txn#{n}

    // TODO: Implement proper GraphQL query
    // For now, return empty array - we'll add the query in next step
    logger.warn('fetchStatementTransactions not yet implemented - need GraphQL query');
    return [];
  } catch (error) {
    logger.error('Error fetching statement transactions:', error);
    throw error;
  }
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
