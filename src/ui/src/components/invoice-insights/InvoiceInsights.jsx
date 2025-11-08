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
} from '@awsui/components-react';

import { useCompany } from '../../contexts/company';
import { COMPANY_SELECT_PATH } from '../../routes/constants';

import '@awsui/global-styles/index.css';

const InvoiceInsights = () => {
  const history = useHistory();
  const { activeCompany, isCompanySelected } = useCompany();
  
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    // Redirect if no company selected
    if (!isCompanySelected) {
      history.push(COMPANY_SELECT_PATH);
      return;
    }

    // Simulate loading
    const timer = setTimeout(() => setLoading(false), 500);
    return () => clearTimeout(timer);
  }, [isCompanySelected, history]);

  if (loading) {
    return (
      <Box textAlign="center" padding="xxl">
        <Spinner size="large" />
        <Box variant="p" color="text-body-secondary">
          Loading invoice insights...
        </Box>
      </Box>
    );
  }

  if (!activeCompany) {
    return null;
  }

  const renderOverviewTab = () => (
    <Container>
      <Alert type="info" header="Invoice Analytics Not Available">
        <SpaceBetween size="s">
          <Box>
            Invoice analytics will be available once invoice data is processed and aggregated.
          </Box>
          <Box variant="small">
            This dashboard will show:
          </Box>
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
        <Box>
          Supplier breakdown and spending analysis will be available once invoice data is processed.
        </Box>
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
    <SpaceBetween size="l">
      <BreadcrumbGroup
        items={[
          { text: 'Company Select', href: `#${COMPANY_SELECT_PATH}` },
          { text: activeCompany.companyName, href: '#' },
          { text: 'Invoice Insights', href: '#' },
        ]}
        ariaLabel="Breadcrumbs"
      />
      
      <Header
        variant="h1"
        description={`Company Number: ${activeCompany.companyNumber}`}
      >
        Invoice Insights: {activeCompany.companyName}
      </Header>

      <Tabs
        activeTabId={activeTab}
        onChange={({ detail }) => setActiveTab(detail.activeTabId)}
        tabs={[
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
  );
};

export default InvoiceInsights;
