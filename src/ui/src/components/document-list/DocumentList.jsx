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
  Box,
  SpaceBetween,
  Header,
  StatusIndicator,
  Button,
} from '@awsui/components-react';
import { useCollection } from '@awsui/collection-hooks';
import { Logger, API, graphqlOperation } from 'aws-amplify';

import useDocumentsContext from '../../contexts/documents';
import useSettingsContext from '../../contexts/settings';
import { useCompany } from '../../contexts/company';

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
  const [invoicesNextToken, setInvoicesNextToken] = useState(null);
  const [bankStatementsNextToken, setBankStatementsNextToken] = useState(null);

  // Bank statement transactions state
  const [selectedStatement, setSelectedStatement] = useState(null);
  const [statementTransactions, setStatementTransactions] = useState([]);
  const [isLoadingTransactions, setIsLoadingTransactions] = useState(false);
  const [showTransactionsPanel, setShowTransactionsPanel] = useState(false);
  const [bankStatementView, setBankStatementView] = useState('summary'); // 'summary' or 'transactions'

  const { activeCompany, isCompanySelected } = useCompany();
  const { settings } = useSettingsContext();

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

        const result = await fetchExtractionResults(activeCompany.companyNumber, DOCUMENT_TYPES.INVOICE, 50);

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
        const result = await fetchExtractionResults(activeCompany.companyNumber, DOCUMENT_TYPES.BANK_STATEMENT, 50);

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

  // Invoices Table Component
  const renderInvoicesTable = () => (
    <Table
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
      ]}
      items={invoices}
      loading={isLoadingInvoices}
      loadingText="Loading invoices"
      sortingDisabled={false}
      header={
        <Header
          counter={`(${invoices.length})`}
          description={
            isCompanySelected
              ? `Extracted invoices for ${activeCompany?.companyName || 'selected company'}`
              : 'Select a company to view invoices'
          }
          actions={
            <Button onClick={handleDownloadInvoices} disabled={invoices.length === 0} iconName="download">
              Download CSV
            </Button>
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
      pagination={<Pagination currentPageIndex={1} pagesCount={1} disabled={!invoicesNextToken} />}
    />
  );

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

  // Bank Statements Table Component (Transaction-level view)
  const renderBankStatementsTable = () => (
    <Table
      columnDefinitions={[
        {
          id: 'transactionDate',
          header: 'Date',
          cell: (item) => item.transactionDate,
          width: 100,
          sortingField: 'transactionDate',
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
            <span title={item.transactionDescription}>
              {item.transactionDescription.length > 60
                ? item.transactionDescription.substring(0, 60) + '...'
                : item.transactionDescription}
            </span>
          ),
          width: 300,
          sortingField: 'transactionDescription',
        },
        {
          id: 'transactionAmount',
          header: 'Amount',
          cell: (item) => (
            <span
              style={{
                color: item.transactionAmount >= 0 ? '#037f0c' : '#d13212',
                fontWeight: 'bold',
              }}
            >
              {item.transactionAmount >= 0 ? '+' : ''}
              {item.formattedAmount}
            </span>
          ),
          width: 120,
          sortingField: 'transactionAmount',
        },
        {
          id: 'accountBalance',
          header: 'Balance',
          cell: (item) => item.accountBalance,
          width: 120,
          sortingField: 'accountBalance',
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
          id: 'confidence',
          header: 'Confidence',
          cell: (item) => (
            <Badge
              color={parseInt(item.confidence) >= 90 ? 'green' : parseInt(item.confidence) >= 75 ? 'blue' : 'grey'}
            >
              {item.confidence}
            </Badge>
          ),
          width: 90,
          sortingField: 'confidence',
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
      items={bankStatements}
      loading={isLoadingBankStatements}
      loadingText="Loading bank statements"
      sortingDisabled={false}
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

                  const pendingCount = bankStatements.filter(
                    (item) => (item.analysisStatus || 'PENDING') === 'PENDING',
                  ).length;

                  try {
                    console.log(
                      `Starting analysis for ${activeCompany.companyNumber} - ${pendingCount} pending transactions`,
                    );

                    const response = await API.graphql(
                      graphqlOperation(TRIGGER_TRANSACTION_ANALYSIS, {
                        companyNumber: activeCompany.companyNumber,
                      }),
                    );

                    const result = response.data.triggerTransactionAnalysis;

                    if (result.success) {
                      console.log('Analysis started:', result.executionArn);
                      alert(
                        `✓ Analysis started successfully!\n${result.message}\n\nExecution: ${result.executionName}`,
                      );

                      // Refresh bank statements to show IN_PROGRESS status
                      setTimeout(() => {
                        loadBankStatements();
                      }, 2000);
                    } else {
                      console.error('Analysis failed:', result.message);
                      alert(`✗ Analysis failed: ${result.message}`);
                    }
                  } catch (error) {
                    console.error('Error triggering analysis:', error);
                    alert(`✗ Error starting analysis: ${error.message || 'Unknown error'}`);
                  }
                }}
                disabled={
                  bankStatements.length === 0 ||
                  !bankStatements.some((item) => (item.analysisStatus || 'PENDING') === 'PENDING')
                }
                variant="primary"
              >
                Analyse Transactions
                {bankStatements.filter((item) => (item.analysisStatus || 'PENDING') === 'PENDING').length > 0 &&
                  ` (${bankStatements.filter((item) => (item.analysisStatus || 'PENDING') === 'PENDING').length})`}
              </Button>
              <Button onClick={handleDownloadBankStatements} disabled={bankStatements.length === 0} iconName="download">
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
      pagination={<Pagination currentPageIndex={1} pagesCount={1} disabled={!bankStatementsNextToken} />}
    />
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
            <Badge color={bankStatements.length > 0 ? 'blue' : 'grey'}>Bank Statements ({bankStatements.length})</Badge>
          ),
          content: renderBankStatementsTable(),
        },
      ]}
    />
  );
};

export default DocumentList;
