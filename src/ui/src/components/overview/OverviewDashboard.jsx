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
  ColumnLayout,
  Spinner,
  BreadcrumbGroup,
  Grid,
  KeyValuePairs,
} from '@awsui/components-react';

import { useCompany } from '../../contexts/company';
import { COMPANY_SELECT_PATH } from '../../routes/constants';
import GenAIIDPTopNavigation from '../genai-idp-top-navigation';

import '@awsui/global-styles/index.css';

const OverviewDashboard = () => {
  const history = useHistory();
  const { activeCompany, isCompanySelected } = useCompany();

  const [loading, setLoading] = useState(true);

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
            Loading overview dashboard...
          </Box>
        </Box>
      </>
    );
  }

  if (!activeCompany) {
    return null;
  }

  return (
    <>
      <GenAIIDPTopNavigation />
      <SpaceBetween size="l">
      <BreadcrumbGroup
        items={[
          { text: 'Company Select', href: `#${COMPANY_SELECT_PATH}` },
          { text: activeCompany.companyName, href: '#' },
          { text: 'Overview', href: '#' },
        ]}
        ariaLabel="Breadcrumbs"
      />

      <Header variant="h1" description={`Company Number: ${activeCompany.companyNumber}`}>
        Overview Dashboard: {activeCompany.companyName}
      </Header>

      {/* Placeholder Alert */}
      <Alert type="info" header="Dashboard Under Construction">
        <SpaceBetween size="s">
          <Box>The overview dashboard will display key company metrics and insights.</Box>
          <Box variant="small">When implemented, you will see:</Box>
          <ul>
            <li>Document processing statistics</li>
            <li>Recent activity timeline</li>
            <li>Compliance status overview</li>
            <li>Risk indicators and alerts</li>
            <li>Quick actions and shortcuts</li>
          </ul>
        </SpaceBetween>
      </Alert>

      {/* Placeholder KPIs Section */}
      <Container header={<Header variant="h2">Key Metrics</Header>}>
        <ColumnLayout columns={4} variant="text-grid">
          <div>
            <Box variant="awsui-key-label">Total Documents</Box>
            <Box fontSize="display-l" fontWeight="bold" color="text-status-inactive">
              --
            </Box>
          </div>
          <div>
            <Box variant="awsui-key-label">Processed This Month</Box>
            <Box fontSize="display-l" fontWeight="bold" color="text-status-inactive">
              --
            </Box>
          </div>
          <div>
            <Box variant="awsui-key-label">Compliance Score</Box>
            <Box fontSize="display-l" fontWeight="bold" color="text-status-inactive">
              --
            </Box>
          </div>
          <div>
            <Box variant="awsui-key-label">Active Alerts</Box>
            <Box fontSize="display-l" fontWeight="bold" color="text-status-inactive">
              --
            </Box>
          </div>
        </ColumnLayout>
      </Container>

      {/* Company Information */}
      <Container header={<Header variant="h2">Company Information</Header>}>
        <ColumnLayout columns={2} variant="text-grid">
          <div>
            <Box variant="awsui-key-label">Company Name</Box>
            <div>{activeCompany.companyName}</div>
          </div>
          <div>
            <Box variant="awsui-key-label">Company Number</Box>
            <div>{activeCompany.companyNumber}</div>
          </div>
          {activeCompany.companyStatus && (
            <div>
              <Box variant="awsui-key-label">Status</Box>
              <div>{activeCompany.companyStatus}</div>
            </div>
          )}
          {activeCompany.dateOfCreation && (
            <div>
              <Box variant="awsui-key-label">Incorporation Date</Box>
              <div>{activeCompany.dateOfCreation}</div>
            </div>
          )}
        </ColumnLayout>
      </Container>
    </SpaceBetween>
    </>
  );
};

export default OverviewDashboard;
