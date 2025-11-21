// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
import React, { useState, useEffect } from 'react';
import { useHistory } from 'react-router-dom';
import {
  Container,
  Header,
  SpaceBetween,
  Alert,
  Box,
  Tabs,
  Spinner,
  BreadcrumbGroup,
  ColumnLayout,
  Table,
  Button,
  StatusIndicator,
  Badge,
} from '@awsui/components-react';
import { API, graphqlOperation } from 'aws-amplify';

import { useCompany } from '../../contexts/company';
import { COMPANY_SELECT_PATH } from '../../routes/constants';
import GenAIIDPTopNavigation from '../genai-idp-top-navigation';
import { fetchExtractionResults, formatInvoiceData, DOCUMENT_TYPES } from '../../services/extractionService';
import { TRIGGER_INVOICE_ANALYSIS } from '../../graphql/mutations/triggerInvoiceAnalysis';
import useUserAuthState from '../../hooks/use-user-auth-state';

import '@awsui/global-styles/index.css';

const InvoiceInsights = () => {
  const history = useHistory();
  const { activeCompany, isCompanySelected } = useCompany();
  const { user } = useUserAuthState();

  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('invoices');
  const [invoices, setInvoices] = useState([]);
  const [loadingInvoices, setLoadingInvoices] = useState(false);
  const [isAnalysisRunning, setIsAnalysisRunning] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Redirect if no company selected
    if (!isCompanySelected) {
      history.push(COMPANY_SELECT_PATH);
      return;
    }

    setLoading(false);
    loadInvoices();
  }, [isCompanySelected, history, activeCompany]);

  const loadInvoices = async () => {
    if (!activeCompany?.companyNumber) return;

    setLoadingInvoices(true);
    setError(null);

    try {
      console.log('[INVOICE INSIGHTS] Loading invoices for:', activeCompany.companyNumber);
      const result = await fetchExtractionResults(activeCompany.companyNumber, DOCUMENT_TYPES.INVOICE, 100);

      const formattedInvoices = result.items.map(formatInvoiceData);
      console.log('[INVOICE INSIGHTS] Loaded invoices:', formattedInvoices.length);
      setInvoices(formattedInvoices);
    } catch (err) {
      console.error('[INVOICE INSIGHTS] Error loading invoices:', err);
      setError(err.message || 'Failed to load invoices');
    } finally {
      setLoadingInvoices(false);
    }
  };

  const handleAnalyseInvoices = async () => {
    if (!activeCompany?.companyNumber || !user?.username) {
      alert('Missing company or user information');
      return;
    }

    setIsAnalysisRunning(true);

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
      console.error('Error triggering invoice analysis:', error);
      alert(`✗ Error starting invoice analysis: ${error.message || 'Unknown error'}`);
    } finally {
      setIsAnalysisRunning(false);
    }
  };

  if (loading) {
    return (
      <>
        <GenAIIDPTopNavigation />
        <Box textAlign="center" padding="xxl">
          <Spinner size="large" />
          <Box variant="p" color="text-body-secondary">
            Loading invoice insights...
          </Box>
        </Box>
      </>
    );
  }

  if (!activeCompany) {
    return null;
  }

  const pendingCount = invoices.filter((inv) => !inv.analysisStatus || inv.analysisStatus === 'PENDING').length;
  const analyzedCount = invoices.length - pendingCount;

  const renderInvoicesTab = () => (
    <SpaceBetween size="l">
      {pendingCount > 0 && (
        <Alert type="info" header={`${pendingCount} invoice${pendingCount > 1 ? 's' : ''} pending analysis`}>
          {analyzedCount > 0 ? (
            <Box>
              {analyzedCount} of {invoices.length} invoices have been analyzed. The remaining {pendingCount} will show
              tax deductibility assessment once analysis completes.
            </Box>
          ) : (
            <Box>
              Invoices are extracted but not yet analyzed for tax compliance. Run invoice analysis to assess "wholly and
              exclusively" deductibility using HMRC BIM guidance.
            </Box>
          )}
        </Alert>
      )}

      <Table
        columnDefinitions={[
          {
            id: 'invoiceNumber',
            header: 'Invoice Number',
            cell: (item) => item.invoiceNumber || 'N/A',
            width: 150,
          },
          {
            id: 'invoiceDate',
            header: 'Date',
            cell: (item) => item.invoiceDate,
            sortingField: 'invoiceDate',
            width: 120,
          },
          {
            id: 'supplierName',
            header: 'Supplier',
            cell: (item) => item.supplierName || 'N/A',
            width: 200,
          },
          {
            id: 'totalAmount',
            header: 'Amount',
            cell: (item) => item.formattedAmount || 'N/A',
            width: 120,
          },
          {
            id: 'invoiceType',
            header: 'Type',
            cell: (item) => <Badge>{item.invoiceType || 'UNKNOWN'}</Badge>,
            width: 150,
          },
          {
            id: 'deductibilityStatus',
            header: 'Tax Deductibility',
            cell: (item) => {
              if (!item.analysisStatus || item.analysisStatus !== 'ANALYZED') {
                return <Badge color="grey">Pending Analysis</Badge>;
              }
              const status = item.deductibilityStatus;
              const statusColors = {
                FULLY_DEDUCTIBLE: 'green',
                PARTIALLY_DEDUCTIBLE: 'blue',
                NOT_DEDUCTIBLE: 'red',
                REQUIRES_REVIEW: 'grey',
              };
              return <Badge color={statusColors[status] || 'grey'}>{status?.replace(/_/g, ' ') || 'Unknown'}</Badge>;
            },
            width: 160,
          },
          {
            id: 'analysisStatus',
            header: 'Status',
            cell: (item) => {
              const status = item.analysisStatus;
              if (status === 'ANALYZED') {
                return <StatusIndicator type="success">Analyzed</StatusIndicator>;
              }
              return <StatusIndicator type="pending">Pending Analysis</StatusIndicator>;
            },
            width: 120,
          },
        ]}
        items={invoices}
        loadingText="Loading invoices"
        loading={loadingInvoices}
        sortingDisabled={false}
        variant="container"
        empty={
          <Box textAlign="center" color="inherit">
            <b>No invoices</b>
            <Box padding={{ bottom: 's' }} variant="p" color="inherit">
              No invoices to display.
            </Box>
          </Box>
        }
        header={
          <Header
            counter={`(${invoices.length})`}
            description={analyzedCount > 0 ? `${analyzedCount} analyzed, ${pendingCount} pending` : undefined}
            actions={
              <SpaceBetween direction="horizontal" size="xs">
                <Button
                  onClick={handleAnalyseInvoices}
                  loading={isAnalysisRunning}
                  disabled={isAnalysisRunning || invoices.length === 0 || pendingCount === 0}
                  variant="primary"
                >
                  Analyse Invoices
                  {pendingCount > 0 && ` (${pendingCount})`}
                </Button>
                <Button iconName="refresh" onClick={loadInvoices}>
                  Refresh
                </Button>
              </SpaceBetween>
            }
          >
            Invoices - Tax Compliance Analysis
          </Header>
        }
      />
    </SpaceBetween>
  );

  const renderOverviewTab = () => (
    <Container>
      <Alert type="info" header="Invoice Analytics Not Available">
        <SpaceBetween size="s">
          <Box>Invoice analytics will be available once invoice data is processed and aggregated.</Box>
          <Box variant="small">This dashboard will show:</Box>
          <ul>
            <li>Total invoice volume and trends</li>
            <li>Average invoice value and payment terms</li>
            <li>Top suppliers and spending patterns</li>
            <li>VAT analysis and compliance</li>
            <li>Payment behavior and aging analysis</li>
          </ul>
        </SpaceBetween>
      </Alert>

      {/* Placeholder metrics */}
      <Box padding={{ top: 'l' }}>
        <ColumnLayout columns={3} variant="text-grid">
          <div>
            <Box variant="awsui-key-label">Total Invoices</Box>
            <Box fontSize="display-l" fontWeight="bold" color="text-status-inactive">
              --
            </Box>
          </div>
          <div>
            <Box variant="awsui-key-label">Total Value</Box>
            <Box fontSize="display-l" fontWeight="bold" color="text-status-inactive">
              --
            </Box>
          </div>
          <div>
            <Box variant="awsui-key-label">Average Invoice</Box>
            <Box fontSize="display-l" fontWeight="bold" color="text-status-inactive">
              --
            </Box>
          </div>
        </ColumnLayout>
      </Box>
    </Container>
  );

  const renderSuppliersTab = () => (
    <Container>
      <Alert type="info" header="Supplier Analysis Not Available">
        <Box>Supplier breakdown and spending analysis will be available once invoice data is processed.</Box>
      </Alert>
    </Container>
  );

  const renderVATTab = () => (
    <Container>
      <Alert type="info" header="VAT Analysis Not Available">
        <Box>
          VAT breakdown, rates analysis, and compliance checking will be available once invoice data is processed.
        </Box>
      </Alert>
    </Container>
  );

  return (
    <>
      <GenAIIDPTopNavigation />
      <SpaceBetween size="l">
        <BreadcrumbGroup
          items={[
            { text: 'Company Select', href: `#${COMPANY_SELECT_PATH}` },
            { text: activeCompany.companyName, href: '#' },
            { text: 'Invoice Insights', href: '#' },
          ]}
          ariaLabel="Breadcrumbs"
        />

        <Header variant="h1" description={`Company Number: ${activeCompany.companyNumber}`}>
          Invoice Insights: {activeCompany.companyName}
        </Header>

        <Tabs
          activeTabId={activeTab}
          onChange={({ detail }) => setActiveTab(detail.activeTabId)}
          tabs={[
            {
              id: 'invoices',
              label: 'Tax Compliance',
              content: renderInvoicesTab(),
            },
            {
              id: 'overview',
              label: 'Overview',
              content: renderOverviewTab(),
            },
            {
              id: 'suppliers',
              label: 'Suppliers',
              content: renderSuppliersTab(),
            },
            {
              id: 'vat',
              label: 'VAT Analysis',
              content: renderVATTab(),
            },
          ]}
        />
      </SpaceBetween>
    </>
  );
};

export default InvoiceInsights;
