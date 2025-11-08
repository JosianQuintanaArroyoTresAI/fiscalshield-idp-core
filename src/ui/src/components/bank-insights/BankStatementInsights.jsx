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
import GenAIIDPTopNavigation from '../genai-idp-top-navigation';

import '@awsui/global-styles/index.css';

const BankStatementInsights = () => {
  const history = useHistory();
  const { activeCompany, isCompanySelected } = useCompany();

  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('cashflow');

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
      <>
        <GenAIIDPTopNavigation />
        <Box textAlign="center" padding="xxl">
          <Spinner size="large" />
          <Box variant="p" color="text-body-secondary">
            Loading bank statement insights...
          </Box>
        </Box>
      </>
    );
  }

  if (!activeCompany) {
    return null;
  }

  const renderCashFlowTab = () => (
    <Container>
      <Alert type="info" header="Cash Flow Analysis Not Available">
        <SpaceBetween size="s">
          <Box>Cash flow analysis will be available once bank statement data is processed.</Box>
          <Box variant="small">This will include:</Box>
          <ul>
            <li>Monthly cash flow trends and patterns</li>
            <li>Income vs expenses breakdown</li>
            <li>Cash flow forecasting</li>
            <li>Seasonal variations and anomalies</li>
            <li>Working capital analysis</li>
          </ul>
        </SpaceBetween>
      </Alert>

      {/* Placeholder metrics */}
      <Box padding={{ top: 'l' }}>
        <ColumnLayout columns={3} variant="text-grid">
          <div>
            <Box variant="awsui-key-label">Average Monthly Inflow</Box>
            <Box fontSize="display-l" fontWeight="bold" color="text-status-inactive">
              --
            </Box>
          </div>
          <div>
            <Box variant="awsui-key-label">Average Monthly Outflow</Box>
            <Box fontSize="display-l" fontWeight="bold" color="text-status-inactive">
              --
            </Box>
          </div>
          <div>
            <Box variant="awsui-key-label">Net Cash Flow</Box>
            <Box fontSize="display-l" fontWeight="bold" color="text-status-inactive">
              --
            </Box>
          </div>
        </ColumnLayout>
      </Box>
    </Container>
  );

  const renderTransactionsTab = () => (
    <Container>
      <Alert type="info" header="Transaction Analysis Not Available">
        <SpaceBetween size="s">
          <Box>Transaction categorization and analysis will be available once bank statement data is processed.</Box>
          <Box variant="small">This will include:</Box>
          <ul>
            <li>Automatic transaction categorization</li>
            <li>Top payees and payment patterns</li>
            <li>Recurring payments identification</li>
            <li>Unusual transaction detection</li>
            <li>Merchant category analysis</li>
          </ul>
        </SpaceBetween>
      </Alert>
    </Container>
  );

  const renderExpensesTab = () => (
    <Container>
      <Alert type="info" header="Expense Analysis Not Available">
        <SpaceBetween size="s">
          <Box>Expense breakdown and categorization will be available once bank statement data is processed.</Box>
          <Box variant="small">This will include:</Box>
          <ul>
            <li>Expense categories and trends</li>
            <li>Fixed vs variable costs</li>
            <li>Expense ratios and benchmarks</li>
            <li>Cost reduction opportunities</li>
            <li>Budget compliance monitoring</li>
          </ul>
        </SpaceBetween>
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
          { text: 'Bank Insights', href: '#' },
        ]}
        ariaLabel="Breadcrumbs"
      />

      <Header variant="h1" description={`Company Number: ${activeCompany.companyNumber}`}>
        Bank Statement Insights: {activeCompany.companyName}
      </Header>

      <Tabs
        activeTabId={activeTab}
        onChange={({ detail }) => setActiveTab(detail.activeTabId)}
        tabs={[
          {
            id: 'cashflow',
            label: 'Cash Flow',
            content: renderCashFlowTab(),
          },
          {
            id: 'transactions',
            label: 'Transactions',
            content: renderTransactionsTab(),
          },
          {
            id: 'expenses',
            label: 'Expenses',
            content: renderExpensesTab(),
          },
        ]}
      />
    </SpaceBetween>
    </>
  );
};

export default BankStatementInsights;
