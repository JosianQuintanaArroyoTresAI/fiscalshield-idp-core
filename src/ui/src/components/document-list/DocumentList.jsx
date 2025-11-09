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

import mapDocumentsAttributes from '../common/map-document-attributes';
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

  // Placeholder: Invoice Table Component
  const renderInvoicesTablePlaceholder = () => (
    <Table
      columnDefinitions={[
        {
          id: 'vendor',
          header: 'Vendor',
          cell: () => '-',
          width: 150,
        },
        {
          id: 'invoice_date',
          header: 'Invoice Date',
          cell: () => '-',
          width: 120,
        },
        {
          id: 'amount',
          header: 'Amount',
          cell: () => '-',
          width: 100,
        },
        {
          id: 'category',
          header: 'Category',
          cell: () => '-',
          width: 130,
        },
        {
          id: 'compliance_score',
          header: 'Compliance Score',
          cell: () => '-',
          width: 130,
        },
        {
          id: 'risk_factors',
          header: 'Risk Factors',
          cell: () => '-',
          width: 130,
        },
        {
          id: 'bim37000',
          header: 'BIM37000',
          cell: () => '-',
          width: 100,
        },
        {
          id: 'action',
          header: 'Action',
          cell: () => '-',
          width: 100,
        },
      ]}
      items={[]}
      loading={false}
      loadingText="Loading invoices"
      header={
        <Header
          counter="(0)"
          info={
            <Box variant="p" color="text-status-info">
              Backend integration in progress
            </Box>
          }
        >
          Invoices
        </Header>
      }
      empty={
        <Box margin={{ vertical: 'xs' }} textAlign="center" color="inherit">
          <SpaceBetween size="m">
            <Box variant="h3">Invoice Extraction - Coming Soon</Box>
            <Box variant="p" color="text-body-secondary">
              Extracted invoice records will appear here once the Analysis Stack is deployed.
              <br />
              Each invoice will show vendor, amount, category, compliance scores, and risk factors.
            </Box>
            <StatusIndicator type="info">Backend API not available yet</StatusIndicator>
          </SpaceBetween>
        </Box>
      }
      pagination={<Pagination currentPageIndex={1} pagesCount={1} disabled />}
    />
  );

  // Placeholder: Bank Statements Table Component
  const renderBankStatementsTablePlaceholder = () => (
    <Table
      columnDefinitions={[
        {
          id: 'transaction_date',
          header: 'Date',
          cell: () => '-',
          width: 120,
        },
        {
          id: 'description',
          header: 'Description',
          cell: () => '-',
          width: 200,
        },
        {
          id: 'counterparty',
          header: 'Counterparty',
          cell: () => '-',
          width: 150,
        },
        {
          id: 'amount',
          header: 'Amount',
          cell: () => '-',
          width: 100,
        },
        {
          id: 'type',
          header: 'Type',
          cell: () => '-',
          width: 80,
        },
        {
          id: 'balance',
          header: 'Balance',
          cell: () => '-',
          width: 100,
        },
        {
          id: 'category',
          header: 'Category',
          cell: () => '-',
          width: 120,
        },
        {
          id: 'compliance_score',
          header: 'Compliance Score',
          cell: () => '-',
          width: 100,
        },
      ]}
      items={[]}
      loading={false}
      loadingText="Loading bank transactions"
      header={
        <Header
          counter="(0)"
          info={
            <Box variant="p" color="text-status-info">
              Backend integration in progress
            </Box>
          }
        >
          Bank Transactions
        </Header>
      }
      empty={
        <Box margin={{ vertical: 'xs' }} textAlign="center" color="inherit">
          <SpaceBetween size="m">
            <Box variant="h3">Bank Statement Extraction - Coming Soon</Box>
            <Box variant="p" color="text-body-secondary">
              Extracted bank transaction records will appear here once the Analysis Stack is deployed.
              <br />
              Each transaction will show date, description, counterparty, amount, and compliance scores.
            </Box>
            <StatusIndicator type="info">Backend API not available yet</StatusIndicator>
          </SpaceBetween>
        </Box>
      }
      pagination={<Pagination currentPageIndex={1} pagesCount={1} disabled />}
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
          label: <Badge color="grey">Invoices (0)</Badge>,
          content: renderInvoicesTablePlaceholder(),
        },
        {
          id: 'statements',
          label: <Badge color="grey">Bank Statements (0)</Badge>,
          content: renderBankStatementsTablePlaceholder(),
        },
      ]}
    />
  );
};

export default DocumentList;
