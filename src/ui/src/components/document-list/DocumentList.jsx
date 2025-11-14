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
import { Logger } from 'aws-amplify';

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
import { exportToExcel } from '../common/download-func';
import DeleteDocumentModal from '../common/DeleteDocumentModal';
import ReprocessDocumentModal from '../common/ReprocessDocumentModal';

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

  // Bank Statements Table Component
  const renderBankStatementsTable = () => (
    <Table
      columnDefinitions={[
        {
          id: 'bankName',
          header: 'Bank',
          cell: (item) => item.bankName,
          width: 120,
          sortingField: 'bankName',
        },
        {
          id: 'accountNumber',
          header: 'Account',
          cell: (item) => item.accountNumber,
          width: 110,
          sortingField: 'accountNumber',
        },
        {
          id: 'statementPeriod',
          header: 'Statement Period',
          cell: (item) => item.statementPeriod,
          width: 180,
          sortingField: 'statementPeriod',
        },
        {
          id: 'transactionCount',
          header: 'Transactions',
          cell: (item) => item.transactionCount,
          width: 100,
          sortingField: 'transactionCount',
        },
        {
          id: 'totalCredits',
          header: 'Total In',
          cell: (item) => (
            <span style={{ color: '#037f0c', fontWeight: 'bold' }}>{item.totalCredits}</span>
          ),
          width: 120,
          sortingField: 'totalCredits',
        },
        {
          id: 'totalDebits',
          header: 'Total Out',
          cell: (item) => (
            <span style={{ color: '#d13212', fontWeight: 'bold' }}>{item.totalDebits}</span>
          ),
          width: 120,
          sortingField: 'totalDebits',
        },
        {
          id: 'netMovement',
          header: 'Net Movement',
          cell: (item) => (
            <span style={{ color: item.netMovement >= 0 ? '#037f0c' : '#d13212', fontWeight: 'bold' }}>
              {item.netMovement}
            </span>
          ),
          width: 120,
          sortingField: 'netMovement',
        },
        {
          id: 'closingBalance',
          header: 'Closing Balance',
          cell: (item) => item.closingBalance,
          width: 130,
          sortingField: 'closingBalance',
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
          width: 100,
          sortingField: 'qualityTier',
        },
        {
          id: 'processedDate',
          header: 'Processed',
          cell: (item) => item.processedDate,
          width: 110,
          sortingField: 'processedDate',
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
              ? `Extracted bank statements for ${activeCompany?.companyName || 'selected company'}`
              : 'Select a company to view bank statements'
          }
        >
          Bank Statements
        </Header>
      }
      empty={
        <Box margin={{ vertical: 'xs' }} textAlign="center" color="inherit">
          <SpaceBetween size="m">
            <Box variant="h3">{isCompanySelected ? 'No bank statements found' : 'No company selected'}</Box>
            <Box variant="p" color="text-body-secondary">
              {isCompanySelected
                ? 'No extracted bank statements available for this company yet.'
                : 'Please select a company from the dropdown to view bank statements.'}
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
