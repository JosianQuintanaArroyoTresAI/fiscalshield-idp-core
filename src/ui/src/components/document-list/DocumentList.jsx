// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
import React, { useEffect, useState } from 'react';
import {
  Table,
  Pagination,
  TextFilter,
  Tabs,
  Badge,
  Container,
  Alert,
  Box,
  SpaceBetween,
  Header,
  StatusIndicator,
  Button,
  ProgressBar,
  Popover,
  ColumnLayout,
} from '@awsui/components-react';
import { useCollection } from '@awsui/collection-hooks';
import { Logger, API, graphqlOperation } from 'aws-amplify';

import useDocumentsContext from '../../contexts/documents';
import useSettingsContext from '../../contexts/settings';
import { useCompany } from '../../contexts/company';
import useUserAuthState from '../../hooks/use-user-auth-state';

import mapDocumentsAttributes from '../common/map-document-attributes';
import {
  fetchExtractionResults,
  formatInvoiceData,
  formatBankStatementData,
  getStatusVariant,
  DOCUMENT_TYPES,
} from '../../services/extractionService';
import { paginationLabels } from '../common/labels';
import useLocalStorage from '../common/local-storage';
import { exportToExcel, exportToCSV } from '../common/download-func';
import DeleteDocumentModal from '../common/DeleteDocumentModal';
import ReprocessDocumentModal from '../common/ReprocessDocumentModal';
import { TRIGGER_TRANSACTION_ANALYSIS } from '../../graphql/mutations/triggerTransactionAnalysis';
import { TRIGGER_INVOICE_ANALYSIS } from '../../graphql/mutations/triggerInvoiceAnalysis';

import {
  DocumentsPreferences,
  DocumentsCommonHeader,
  COLUMN_DEFINITIONS_MAIN,
  KEY_COLUMN_ID,
  SELECTION_LABELS,
  DEFAULT_PREFERENCES,
  DEFAULT_SORT_COLUMN,
} from './documents-table-config';

import { getFilterCounterText, TableEmptyState, TableNoMatchState } from '../common/table';

import TransactionDetailDrawer from '../bank-insights/TransactionDetailDrawer';
import InvoiceDetailDrawer from '../invoice-insights/InvoiceDetailDrawer';

import '@awsui/global-styles/index.css';

const logger = new Logger('DocumentList');

const DocumentList = () => {
  const [documentList, setDocumentList] = useState([]);
  const [isDeleteModalVisible, setIsDeleteModalVisible] = useState(false);
  const [isReprocessModalVisible, setIsReprocessModalVisible] = useState(false);
  const [activeTabId, setActiveTabId] = useState('documents');

  // Extraction results state
  const [invoices, setInvoices] = useState([]);
  const [bankStatements, setBankStatements] = useState([]);
  const [isLoadingInvoices, setIsLoadingInvoices] = useState(false);
  const [isLoadingBankStatements, setIsLoadingBankStatements] = useState(false);
  const [isAnalysisRunning, setIsAnalysisRunning] = useState(false);
  const [isInvoiceAnalysisRunning, setIsInvoiceAnalysisRunning] = useState(false);
  const [invoicesNextToken, setInvoicesNextToken] = useState(null);
  const [bankStatementsNextToken, setBankStatementsNextToken] = useState(null);

  const [selectedTransaction, setSelectedTransaction] = useState(null);
  const [selectedInvoice, setSelectedInvoice] = useState(null);

  const { activeCompany, isCompanySelected } = useCompany();
  const { settings } = useSettingsContext();
  const { user } = useUserAuthState();

  const {
    documents,
    isDocumentsListLoading,
    setIsDocumentsListLoading,
    setPeriodsToLoad,
    setSelectedItems,
    setToolsOpen,
    periodsToLoad,
    getDocumentDetailsFromIds,
    deleteDocuments,
    reprocessDocuments,
  } = useDocumentsContext();

  const [preferences, setPreferences] = useLocalStorage('documents-list-preferences', DEFAULT_PREFERENCES);

  // prettier-ignore
  const {
    items, actions, filteredItemsCount, collectionProps, filterProps, paginationProps,
  } = useCollection(documentList, {
    filtering: {
      empty: <TableEmptyState resourceName="Document" />,
      noMatch: <TableNoMatchState onClearFilter={() => actions.setFiltering('')} />,
    },
    pagination: { pageSize: preferences.pageSize },
    sorting: { defaultState: { sortingColumn: DEFAULT_SORT_COLUMN, isDescending: true } },
    selection: {
      keepSelection: false,
      trackBy: KEY_COLUMN_ID,
    },
  });

  const {
    items: invoiceItems,
    collectionProps: invoiceCollectionProps,
    paginationProps: invoicePaginationProps,
  } = useCollection(invoices, {
    sorting: {
      defaultState: {
        sortingColumn: { sortingField: 'date' },
        isDescending: true,
      },
    },
    pagination: { pageSize: 10 },
  });

  const {
    items: bankStatementItems,
    collectionProps: bankStatementCollectionProps,
    paginationProps: bankStatementPaginationProps,
  } = useCollection(bankStatements, {
    sorting: {
      defaultState: {
        sortingColumn: { sortingField: 'transactionDate' },
        isDescending: true,
      },
    },
    pagination: { pageSize: 10 },
  });

  useEffect(() => {
    if (!isDocumentsListLoading) {
      logger.debug('setting documents list', documents);
      setDocumentList(mapDocumentsAttributes(documents, settings));
    } else {
      logger.debug('documents list is loading');
    }
  }, [isDocumentsListLoading, documents]);

  useEffect(() => {
    logger.debug('setting selected items', collectionProps.selectedItems);
    setSelectedItems(collectionProps.selectedItems);
  }, [collectionProps.selectedItems]);

  useEffect(() => {
    setSelectedTransaction(null);
  }, [activeTabId, activeCompany?.companyNumber]);

  // Load invoices when company is selected and tab is active
  useEffect(() => {
    console.log('[INVOICES DEBUG] useEffect triggered', {
      isCompanySelected,
      companyNumber: activeCompany?.companyNumber,
      activeTabId,
    });

    const loadInvoices = async () => {
      if (!isCompanySelected || !activeCompany?.companyNumber) {
        console.log('[INVOICES DEBUG] No company selected, skipping invoice load');
        logger.debug('No company selected, skipping invoice load');
        setInvoices([]);
        return;
      }

      if (activeTabId !== 'invoices') {
        console.log('[INVOICES DEBUG] Tab not active, current tab:', activeTabId);
        return; // Only load when tab is active
      }

      console.log('[INVOICES DEBUG] Loading invoices...');
      setIsLoadingInvoices(true);
      try {
        logger.debug(`Loading invoices for company ${activeCompany.companyNumber}`);
        console.log('[INVOICES DEBUG] Calling fetchExtractionResults with:', {
          companyNumber: activeCompany.companyNumber,
          documentType: DOCUMENT_TYPES.INVOICE,
        });

        const result = await fetchExtractionResults(activeCompany.companyNumber, DOCUMENT_TYPES.INVOICE, 1000);

        console.log('[INVOICES DEBUG] Received result:', result);

        const formattedInvoices = result.items.map(formatInvoiceData);
        setInvoices(formattedInvoices);
        setInvoicesNextToken(result.nextToken);
        logger.debug(`Loaded ${formattedInvoices.length} invoices`);
        console.log('[INVOICES DEBUG] Loaded invoices:', formattedInvoices);
      } catch (error) {
        logger.error('Error loading invoices:', error);
        console.error('[INVOICES DEBUG] Error loading invoices:', error);
        setInvoices([]);
      } finally {
        setIsLoadingInvoices(false);
      }
    };

    loadInvoices();
  }, [isCompanySelected, activeCompany?.companyNumber, activeTabId]);

  // Load bank statements when company is selected and tab is active
  useEffect(() => {
    const loadBankStatements = async () => {
      if (!isCompanySelected || !activeCompany?.companyNumber) {
        logger.debug('No company selected, skipping bank statements load');
        setBankStatements([]);
        return;
      }

      if (activeTabId !== 'statements') {
        return; // Only load when tab is active
      }

      setIsLoadingBankStatements(true);
      try {
        logger.debug(`Loading bank statements for company ${activeCompany.companyNumber}`);
        const result = await fetchExtractionResults(activeCompany.companyNumber, DOCUMENT_TYPES.BANK_STATEMENT, 1000);

        const formattedStatements = result.items.map(formatBankStatementData);
        setBankStatements(formattedStatements);
        setBankStatementsNextToken(result.nextToken);
        logger.debug(`Loaded ${formattedStatements.length} bank statements`);
      } catch (error) {
        logger.error('Error loading bank statements:', error);
        setBankStatements([]);
      } finally {
        setIsLoadingBankStatements(false);
      }
    };

    loadBankStatements();
  }, [isCompanySelected, activeCompany?.companyNumber, activeTabId]);

  const handleDeleteConfirm = async () => {
    const objectKeys = collectionProps.selectedItems.map((item) => item.objectKey);
    logger.debug('Deleting documents', objectKeys);

    const result = await deleteDocuments(objectKeys);
    logger.debug('Delete result', result);

    // Close the modal
    setIsDeleteModalVisible(false);

    // Clear selection after deletion
    actions.setSelectedItems([]);
  };

  const handleReprocessConfirm = async (documentType) => {
    const objectKeys = collectionProps.selectedItems.map((item) => item.objectKey);
    logger.debug('Reprocessing documents', { objectKeys, documentType });

    const result = await reprocessDocuments(objectKeys, documentType);
    logger.debug('Reprocess result', result);

    // Close the modal
    setIsReprocessModalVisible(false);

    // Clear selection after reprocessing
    actions.setSelectedItems([]);
  };

  // Download invoices to CSV
  const handleDownloadInvoices = () => {
    const csvData = invoices.map((item) => ({
      Type: item.invoiceType === 'SUPPLIER_INVOICE' ? 'Invoice' : 'Expense',
      'Invoice Number': item.invoiceNumber,
      Vendor: item.vendor,
      'Invoice Date': item.date,
      Amount: item.amount,
      Status: item.status,
      Confidence: item.confidence,
      Quality: item.qualityTier,
      Review: item.hitlRequired ? 'HITL Required' : 'Auto-approved',
    }));

    const timestamp = new Date().toISOString().split('T')[0];
    const companyName = activeCompany?.companyName || 'Company';
    exportToCSV(csvData, `${companyName}_Invoices_${timestamp}`);
  };

  // Helper functions for invoice tax deductibility display
  const getDeductibilityColor = (status) => {
    const colorMap = {
      FULLY_DEDUCTIBLE: 'green',
      PARTIALLY_DEDUCTIBLE: 'blue',
      NOT_DEDUCTIBLE: 'red',
      REQUIRES_REVIEW: 'grey',
    };
    return colorMap[status] || 'grey';
  };

  const getRecommendedActionColor = (action) => {
    const colorMap = {
      APPROVE: 'green',
      APPORTION: 'blue',
      REQUEST_DOCUMENTATION: 'grey',
      REJECT: 'red',
    };
    return colorMap[action] || 'grey';
  };

  const calculateTaxSavings = (totalAmount, deductibilityPercentage) => {
    if (!totalAmount || !deductibilityPercentage) return '£0.00';

    const amount = parseFloat(totalAmount.toString().replace(/[^0-9.-]+/g, ''));
    const deductibleAmount = (amount * deductibilityPercentage) / 100;
    const taxSavings = deductibleAmount * 0.19; // Corporation tax at 19%

    return `£${taxSavings.toFixed(2)}`;
  };

  // Invoices Table Component
  const renderInvoicesTable = () => (
    <Table
      {...invoiceCollectionProps}
      columnDefinitions={[
        {
          id: 'invoiceType',
          header: 'Type',
          cell: (item) => (
            <Badge color={item.invoiceType === 'SUPPLIER_INVOICE' ? 'blue' : 'green'}>
              {item.invoiceType === 'SUPPLIER_INVOICE' ? 'Invoice' : 'Expense'}
            </Badge>
          ),
          width: 100,
          sortingField: 'invoiceType',
        },
        {
          id: 'invoiceNumber',
          header: 'Invoice #',
          cell: (item) => item.invoiceNumber,
          width: 120,
          sortingField: 'invoiceNumber',
        },
        {
          id: 'vendor',
          header: 'Vendor',
          cell: (item) => item.vendor,
          width: 180,
          sortingField: 'vendor',
        },
        {
          id: 'description',
          header: 'Description',
          cell: (item) => (
            <span title={item.description || ''}>
              {item.description && item.description.length > 40
                ? item.description.substring(0, 40) + '...'
                : item.description || 'N/A'}
            </span>
          ),
          width: 200,
          sortingField: 'description',
        },
        {
          id: 'date',
          header: 'Invoice Date',
          cell: (item) => item.date,
          width: 120,
          sortingField: 'date',
        },
        {
          id: 'amount',
          header: 'Amount',
          cell: (item) => item.amount,
          width: 120,
          sortingField: 'amount',
          sortingComparator: (a, b) => {
            const amountA = parseFloat(a.rawData?.TotalAmount || a.rawData?.Amount || 0);
            const amountB = parseFloat(b.rawData?.TotalAmount || b.rawData?.Amount || 0);
            return amountA - amountB;
          },
        },
        {
          id: 'status',
          header: 'Status',
          cell: (item) => <Badge color={getStatusVariant(item.status)}>{item.status}</Badge>,
          width: 120,
          sortingField: 'status',
        },
        {
          id: 'confidence',
          header: 'Confidence',
          cell: (item) => (
            <Badge
              color={
                item.qualityTier === 'EXCELLENT'
                  ? 'green'
                  : item.qualityTier === 'GOOD'
                  ? 'blue'
                  : item.qualityTier === 'ACCEPTABLE'
                  ? 'grey'
                  : 'red'
              }
            >
              {item.confidence}
            </Badge>
          ),
          width: 120,
          sortingField: 'confidence',
        },
        {
          id: 'quality',
          header: 'Quality',
          cell: (item) => (
            <Badge
              color={
                item.qualityTier === 'EXCELLENT'
                  ? 'green'
                  : item.qualityTier === 'GOOD'
                  ? 'blue'
                  : item.qualityTier === 'ACCEPTABLE'
                  ? 'grey'
                  : 'red'
              }
            >
              {item.qualityTier}
            </Badge>
          ),
          width: 120,
          sortingField: 'qualityTier',
        },
        {
          id: 'hitl',
          header: 'Review',
          cell: (item) =>
            item.hitlRequired ? <Badge color="red">HITL Required</Badge> : <Badge color="green">Auto-approved</Badge>,
          width: 130,
          sortingField: 'hitlRequired',
        },
        {
          id: 'deductibilityStatus',
          header: 'Tax Status',
          cell: (item) => {
            if (!item.analysisStatus || item.analysisStatus === 'PENDING') {
              return <Badge color="grey">Pending Analysis</Badge>;
            }

            const status = item.deductibilityStatus;
            const percentage = item.deductibilityPercentage;

            if (!status) {
              return (
                <Box color="text-status-inactive" variant="small">
                  —
                </Box>
              );
            }

            const colorMap = {
              FULLY_DEDUCTIBLE: 'green',
              PARTIALLY_DEDUCTIBLE: 'blue',
              NOT_DEDUCTIBLE: 'red',
              REQUIRES_REVIEW: 'grey',
            };

            const labelMap = {
              FULLY_DEDUCTIBLE: '100% Deductible',
              PARTIALLY_DEDUCTIBLE: `${percentage}% Deductible`,
              NOT_DEDUCTIBLE: 'Not Deductible',
              REQUIRES_REVIEW: 'Needs Review',
            };

            return <Badge color={colorMap[status] || 'grey'}>{labelMap[status] || status}</Badge>;
          },
          width: 150,
          sortingField: 'deductibilityStatus',
        },
        {
          id: 'hmrcConcern',
          header: 'HMRC Risk',
          cell: (item) => {
            if (!item.analysisStatus || item.analysisStatus === 'PENDING') {
              return <Badge color="grey">Pending</Badge>;
            }

            return item.hmrcConcern ? <Badge color="red">High Risk</Badge> : <Badge color="green">Low Risk</Badge>;
          },
          width: 120,
          sortingField: 'hmrcConcern',
        },
        {
          id: 'addback',
          header: 'Tax Addback',
          cell: (item) => {
            // Only show for EXPENSE_CLAIM invoices with analyzed status
            if (item.invoiceType !== 'EXPENSE_CLAIM' || !item.analysisStatus || item.analysisStatus === 'PENDING') {
              return (
                <Box color="text-status-inactive" variant="small">
                  —
                </Box>
              );
            }

            const addbackAmount = item.rawData?.AddbackAmount;
            if (addbackAmount && parseFloat(addbackAmount) > 0) {
              return (
                <Badge color="red">
                  £{parseFloat(addbackAmount).toFixed(2)}
                </Badge>
              );
            }

            return <Badge color="green">None</Badge>;
          },
          width: 110,
        },
      ]}
      items={invoiceItems}
      loading={isLoadingInvoices}
      loadingText="Loading invoices"
      sortingDisabled={false}
      onRowClick={({ detail }) => setSelectedInvoice(detail.item)}
      selectedItems={selectedInvoice ? [selectedInvoice] : []}
      selectionType="single"
      header={
        <Header
          counter={`(${invoices.length})`}
          description={
            isCompanySelected
              ? `Extracted invoices for ${activeCompany?.companyName || 'selected company'}`
              : 'Select a company to view invoices'
          }
          actions={
            <SpaceBetween direction="horizontal" size="xs">
              <Button
                onClick={handleAnalyseInvoices}
                loading={isInvoiceAnalysisRunning}
                disabled={
                  isInvoiceAnalysisRunning ||
                  invoices.length === 0 ||
                  !invoices.some((item) => (item.analysisStatus || 'PENDING') === 'PENDING')
                }
                variant="primary"
              >
                Analyse Invoices
                {invoices.filter((item) => (item.analysisStatus || 'PENDING') === 'PENDING').length > 0 &&
                  ` (${invoices.filter((item) => (item.analysisStatus || 'PENDING') === 'PENDING').length})`}
              </Button>
              <Button onClick={handleDownloadInvoices} disabled={invoices.length === 0} iconName="download">
                Download CSV
              </Button>
            </SpaceBetween>
          }
        >
          Invoices
        </Header>
      }
      empty={
        <Box margin={{ vertical: 'xs' }} textAlign="center" color="inherit">
          <SpaceBetween size="m">
            <Box variant="h3">{isCompanySelected ? 'No invoices found' : 'No company selected'}</Box>
            <Box variant="p" color="text-body-secondary">
              {isCompanySelected
                ? 'No extracted invoices available for this company yet.'
                : 'Please select a company from the dropdown to view invoices.'}
            </Box>
          </SpaceBetween>
        </Box>
      }
      pagination={<Pagination {...invoicePaginationProps} ariaLabels={paginationLabels} />}
    />
  );

  // Trigger invoice analysis
  const handleAnalyseInvoices = async () => {
    if (!activeCompany?.companyNumber || !user?.username) {
      alert('Missing company or user information');
      return;
    }

    setIsInvoiceAnalysisRunning(true);

    try {
      console.log('[INVOICE ANALYSIS] Triggering analysis for company:', activeCompany.companyNumber);

      const response = await API.graphql(
        graphqlOperation(TRIGGER_INVOICE_ANALYSIS, {
          companyNumber: activeCompany.companyNumber,
          userId: user.username,
        }),
      );

      const result = response.data.triggerInvoiceAnalysis;

      if (result.success) {
        console.log('Invoice analysis started:', result.executionArn);
        alert(
          `✓ Invoice analysis started successfully!\n${result.message}\n\nExecution: ${result.executionName}\n\nRefresh the page in 60 seconds to see analysis results.`,
        );
      } else {
        console.error('Invoice analysis failed:', result.message);
        alert(`✗ Invoice analysis failed: ${result.message}`);
      }
    } catch (error) {
      console.error('[INVOICE ANALYSIS] Error:', error);
      alert(`Error starting invoice analysis: ${error.message || 'Unknown error'}`);
    } finally {
      setIsInvoiceAnalysisRunning(false);
    }
  };

  // Download bank statements to CSV
  const handleDownloadBankStatements = () => {
    const csvData = bankStatements.map((item) => ({
      Date: item.transactionDate,
      Reference: item.reference,
      Description: item.transactionDescription,
      Amount: item.formattedAmount,
      Balance: item.accountBalance,
      Bank: item.bankName,
      Account: item.accountNumber,
      Confidence: item.confidence,
    }));

    const timestamp = new Date().toISOString().split('T')[0];
    const companyName = activeCompany?.companyName || 'Company';
    exportToCSV(csvData, `${companyName}_BankStatements_${timestamp}`);
  };

  const getComplianceScoreColor = (score) => {
    if (!score) return 'grey';
    if (score >= 4) return 'green';
    if (score >= 3) return 'blue';
    if (score >= 2) return 'grey';
    return 'red';
  };

  const getRecommendedActionVariant = (action) => {
    const actionMap = {
      APPROVE: 'success',
      REVIEW_DOCUMENTATION: 'warning',
      INVESTIGATE: 'warning',
      REJECT: 'error',
    };

    return actionMap[action] || 'info';
  };

  const renderRiskFlags = (flags) => {
    if (!flags || flags.length === 0 || (flags.length === 1 && flags[0] === 'CLEAN')) {
      return <Badge color="green">Clean</Badge>;
    }

    const visibleFlags = flags.slice(0, 2);
    const hiddenFlags = flags.slice(2);

    return (
      <SpaceBetween direction="horizontal" size="xs">
        {visibleFlags.map((flag, idx) => (
          <Badge key={`${flag}-${idx}`} color="red">
            {flag.replace(/_/g, ' ')}
          </Badge>
        ))}
        {hiddenFlags.length > 0 && (
          <Popover
            dismissButton={false}
            position="top"
            size="small"
            triggerType="custom"
            content={
              <SpaceBetween size="xs">
                {hiddenFlags.map((flag, idx) => (
                  <Badge key={`${flag}-${idx}`} color="red">
                    {flag.replace(/_/g, ' ')}
                  </Badge>
                ))}
              </SpaceBetween>
            }
          >
            <Badge color="grey">+{hiddenFlags.length} more</Badge>
          </Popover>
        )}
      </SpaceBetween>
    );
  };

  // Bank Statements Table Component (Transaction-level view)
  const renderBankStatementsTable = () => (
    <>
      <Table
        {...bankStatementCollectionProps}
        columnDefinitions={[
          {
            id: 'transactionDate',
            header: 'Date',
            cell: (item) => item.transactionDate,
            width: 100,
            sortingField: 'transactionDate',
            sortingComparator: (a, b) => {
              const dateA = new Date(a.rawData?.TransactionDate || 0).getTime();
              const dateB = new Date(b.rawData?.TransactionDate || 0).getTime();
              return dateA - dateB;
            },
          },
          {
            id: 'reference',
            header: 'Reference',
            cell: (item) => item.reference,
            width: 200,
            sortingField: 'reference',
          },
          {
            id: 'transactionDescription',
            header: 'Description',
            cell: (item) => (
              <span title={item.transactionDescription || ''}>
                {item.transactionDescription && item.transactionDescription.length > 60
                  ? item.transactionDescription.substring(0, 60) + '...'
                  : item.transactionDescription || ''}
              </span>
            ),
            width: 300,
            sortingField: 'transactionDescription',
          },
          {
            id: 'expenseCategory',
            header: 'Category',
            cell: (item) => {
              if (!item.analysisStatus || item.analysisStatus !== 'ANALYZED') {
                return <Badge color="grey">Pending</Badge>;
              }

              return (
                item.expenseCategory || (
                  <Box color="text-status-inactive" variant="small">
                    Uncategorized
                  </Box>
                )
              );
            },
            width: 140,
            sortingField: 'expenseCategory',
          },
          {
            id: 'transactionAmount',
            header: 'Amount',
            cell: (item) => (
              <span
                style={{
                  color: (item.transactionAmount || 0) >= 0 ? '#037f0c' : '#d13212',
                  fontWeight: 'bold',
                }}
              >
                {(item.transactionAmount || 0) >= 0 ? '+' : ''}
                {item.formattedAmount || ''}
              </span>
            ),
            width: 120,
            sortingField: 'transactionAmount',
            sortingComparator: (a, b) => (a.transactionAmount || 0) - (b.transactionAmount || 0),
          },
          {
            id: 'accountBalance',
            header: 'Balance',
            cell: (item) => item.accountBalance,
            width: 120,
            sortingField: 'accountBalance',
            sortingComparator: (a, b) => (a.rawData?.AccountBalance || 0) - (b.rawData?.AccountBalance || 0),
          },
          {
            id: 'bankName',
            header: 'Bank',
            cell: (item) => item.bankName,
            width: 110,
            sortingField: 'bankName',
          },
          {
            id: 'accountNumber',
            header: 'Account',
            cell: (item) => item.accountNumber,
            width: 100,
            sortingField: 'accountNumber',
          },
          {
            id: 'complianceScore',
            header: 'Compliance',
            cell: (item) => {
              if (!item.analysisStatus || item.analysisStatus !== 'ANALYZED') {
                return <Badge color="grey">Pending</Badge>;
              }

              const score = item.complianceScore;
              if (!score) {
                return (
                  <Box color="text-status-inactive" variant="small">
                    —
                  </Box>
                );
              }

              return (
                <SpaceBetween direction="horizontal" size="xs">
                  <Box fontSize="body-m" fontWeight="bold" color={`text-status-${getComplianceScoreColor(score)}`}>
                    {score}/5
                  </Box>
                  <ProgressBar
                    value={(score / 5) * 100}
                    variant={getComplianceScoreColor(score) === 'red' ? 'error' : undefined}
                    hideLabel
                  />
                </SpaceBetween>
              );
            },
            width: 140,
            sortingField: 'complianceScore',
            sortingComparator: (a, b) => (a.complianceScore || 0) - (b.complianceScore || 0),
          },
          {
            id: 'riskFlags',
            header: 'Risk Flags',
            cell: (item) => {
              if (!item.analysisStatus || item.analysisStatus !== 'ANALYZED') {
                return <Badge color="grey">Pending</Badge>;
              }

              return renderRiskFlags(item.riskFlags);
            },
            width: 200,
            sortingDisabled: true,
          },
          {
            id: 'recommendedAction',
            header: 'Recommended Action',
            cell: (item) => {
              if (!item.analysisStatus || item.analysisStatus !== 'ANALYZED') {
                return <Badge color="grey">Pending</Badge>;
              }

              if (!item.recommendedAction) {
                return (
                  <Box color="text-status-inactive" variant="small">
                    —
                  </Box>
                );
              }

              return (
                <Badge color={getRecommendedActionVariant(item.recommendedAction)}>
                  {item.recommendedAction.replace(/_/g, ' ')}
                </Badge>
              );
            },
            width: 180,
            sortingField: 'recommendedAction',
          },
          {
            id: 'confidence',
            header: 'Confidence',
            cell: (item) => (
              <Badge
                color={
                  item.confidence && parseInt(item.confidence) >= 90
                    ? 'green'
                    : item.confidence && parseInt(item.confidence) >= 75
                    ? 'blue'
                    : 'grey'
                }
              >
                {item.confidence || 'N/A'}
              </Badge>
            ),
            width: 90,
            sortingField: 'confidence',
            sortingComparator: (a, b) =>
              (Number.parseInt(a.confidence, 10) || 0) - (Number.parseInt(b.confidence, 10) || 0),
          },
          {
            id: 'analysisStatus',
            header: 'Analysis',
            cell: (item) => {
              const status = item.analysisStatus || 'PENDING';
              const colorMap = {
                PENDING: 'grey',
                IN_PROGRESS: 'blue',
                ANALYZED: 'green',
                FAILED: 'red',
              };
              return <Badge color={colorMap[status] || 'grey'}>{status}</Badge>;
            },
            width: 100,
            sortingField: 'analysisStatus',
          },
        ]}
        items={bankStatementItems}
        loading={isLoadingBankStatements}
        loadingText="Loading bank statements"
        onRowClick={({ detail }) => setSelectedTransaction(detail.item)}
        selectedItems={selectedTransaction ? [selectedTransaction] : []}
        selectionType="single"
        header={
          <Header
            counter={`(${bankStatements.length})`}
            description={
              isCompanySelected
                ? `Bank statement transactions for ${activeCompany?.companyName || 'selected company'}`
                : 'Select a company to view bank statement transactions'
            }
            actions={
              <SpaceBetween direction="horizontal" size="xs">
                <Button
                  onClick={async () => {
                    if (!activeCompany?.companyNumber) {
                      console.error('No active company selected');
                      return;
                    }

                    if (!user?.attributes?.sub) {
                      console.error('No authenticated user found');
                      alert('✗ Error: User not authenticated');
                      return;
                    }

                    const pendingCount = bankStatements.filter(
                      (item) => (item.analysisStatus || 'PENDING') === 'PENDING',
                    ).length;

                    setIsAnalysisRunning(true);
                    try {
                      console.log(
                        `Starting analysis for company ${activeCompany.companyNumber}, user ${user.attributes.sub} - ${pendingCount} pending transactions`,
                      );

                      const response = await API.graphql(
                        graphqlOperation(TRIGGER_TRANSACTION_ANALYSIS, {
                          companyNumber: activeCompany.companyNumber,
                          userId: user.attributes.sub,
                        }),
                      );

                      const result = response.data.triggerTransactionAnalysis;

                      if (result.success) {
                        console.log('Analysis started:', result.executionArn);
                        alert(
                          `✓ Analysis started successfully!\n${result.message}\n\nExecution: ${result.executionName}\n\nRefresh the page in 30 seconds to see categorization results.`,
                        );
                      } else {
                        console.error('Analysis failed:', result.message);
                        alert(`✗ Analysis failed: ${result.message}`);
                      }
                    } catch (error) {
                      console.error('Error triggering analysis:', error);
                      alert(`✗ Error starting analysis: ${error.message || 'Unknown error'}`);
                    } finally {
                      setIsAnalysisRunning(false);
                    }
                  }}
                  loading={isAnalysisRunning}
                  disabled={
                    isAnalysisRunning ||
                    bankStatements.length === 0 ||
                    !bankStatements.some((item) => (item.analysisStatus || 'PENDING') === 'PENDING')
                  }
                  variant="primary"
                >
                  Analyse Transactions
                  {bankStatements.filter((item) => (item.analysisStatus || 'PENDING') === 'PENDING').length > 0 &&
                    ` (${bankStatements.filter((item) => (item.analysisStatus || 'PENDING') === 'PENDING').length})`}
                </Button>
                <Button
                  onClick={handleDownloadBankStatements}
                  disabled={bankStatements.length === 0}
                  iconName="download"
                >
                  Download CSV
                </Button>
              </SpaceBetween>
            }
          >
            Bank Statement Transactions
          </Header>
        }
        empty={
          <Box margin={{ vertical: 'xs' }} textAlign="center" color="inherit">
            <SpaceBetween size="m">
              <Box variant="h3">{isCompanySelected ? 'No transactions found' : 'No company selected'}</Box>
              <Box variant="p" color="text-body-secondary">
                {isCompanySelected
                  ? 'No bank statement transactions available for this company yet.'
                  : 'Please select a company from the dropdown to view bank statement transactions.'}
              </Box>
            </SpaceBetween>
          </Box>
        }
        pagination={<Pagination {...bankStatementPaginationProps} ariaLabels={paginationLabels} />}
      />

      {selectedTransaction && (
        <Alert type="info" header="Transaction Selected" dismissible onDismiss={() => setSelectedTransaction(null)}>
          Viewing details for <b>{selectedTransaction.reference || selectedTransaction.transactionDescription}</b>{' '}
          below. The selected row is highlighted in blue.
        </Alert>
      )}

      <TransactionDetailDrawer
        transaction={selectedTransaction}
        visible={!!selectedTransaction}
        onDismiss={() => setSelectedTransaction(null)}
      />
    </>
  );

  // Documents Table (existing implementation)
  const renderDocumentsTable = () => (
    <>
      <Table
        {...collectionProps}
        header={
          <DocumentsCommonHeader
            resourceName="Documents"
            documents={documents}
            selectedItems={collectionProps.selectedItems}
            totalItems={documentList}
            updateTools={() => setToolsOpen(true)}
            loading={isDocumentsListLoading}
            setIsLoading={setIsDocumentsListLoading}
            periodsToLoad={periodsToLoad}
            setPeriodsToLoad={setPeriodsToLoad}
            getDocumentDetailsFromIds={getDocumentDetailsFromIds}
            downloadToExcel={() => exportToExcel(documentList, 'Document-List')}
            onReprocess={() => setIsReprocessModalVisible(true)}
            onDelete={() => setIsDeleteModalVisible(true)}
            // eslint-disable-next-line max-len, prettier/prettier
          />
        }
        columnDefinitions={COLUMN_DEFINITIONS_MAIN}
        items={items}
        loading={isDocumentsListLoading}
        loadingText="Loading documents"
        selectionType="multi"
        ariaLabels={SELECTION_LABELS}
        filter={
          <TextFilter
            {...filterProps}
            filteringAriaLabel="Filter documents"
            filteringPlaceholder="Find documents"
            countText={getFilterCounterText(filteredItemsCount)}
          />
        }
        wrapLines={preferences.wrapLines}
        pagination={<Pagination {...paginationProps} ariaLabels={paginationLabels} />}
        preferences={<DocumentsPreferences preferences={preferences} setPreferences={setPreferences} />}
        trackBy={items.objectKey}
        visibleColumns={[KEY_COLUMN_ID, ...preferences.visibleContent]}
        resizableColumns
      />

      <DeleteDocumentModal
        visible={isDeleteModalVisible}
        onDismiss={() => setIsDeleteModalVisible(false)}
        onConfirm={handleDeleteConfirm}
        selectedItems={collectionProps.selectedItems}
      />

      <ReprocessDocumentModal
        visible={isReprocessModalVisible}
        onDismiss={() => setIsReprocessModalVisible(false)}
        onConfirm={handleReprocessConfirm}
        selectedItems={collectionProps.selectedItems}
      />
    </>
  );

  /* eslint-disable react/jsx-props-no-spreading */
  return (
    <>
      <Tabs
        activeTabId={activeTabId}
        onChange={({ detail }) => setActiveTabId(detail.activeTabId)}
        tabs={[
          {
            id: 'documents',
            label: 'Documents',
            content: renderDocumentsTable(),
          },
          {
            id: 'invoices',
            label: <Badge color={invoices.length > 0 ? 'blue' : 'grey'}>Invoices ({invoices.length})</Badge>,
            content: renderInvoicesTable(),
          },
          {
            id: 'statements',
            label: (
              <Badge color={bankStatements.length > 0 ? 'blue' : 'grey'}>
                Bank Statements ({bankStatements.length})
              </Badge>
            ),
            content: renderBankStatementsTable(),
          },
        ]}
      />
      <InvoiceDetailDrawer
        invoice={selectedInvoice}
        visible={!!selectedInvoice}
        onDismiss={() => setSelectedInvoice(null)}
      />
    </>
  );
};

export default DocumentList;
