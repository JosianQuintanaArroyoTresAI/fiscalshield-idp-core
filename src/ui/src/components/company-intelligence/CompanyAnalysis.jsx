// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
import React, { useState, useEffect } from 'react';
import { useParams, useHistory } from 'react-router-dom';
import {
  Container,
  Header,
  SpaceBetween,
  Button,
  Alert,
  Box,
  Tabs,
  Spinner,
  BreadcrumbGroup,
} from '@awsui/components-react';

import { COMPANY_SELECT_PATH } from '../../routes/constants';

import '@awsui/global-styles/index.css';

const CompanyAnalysis = () => {
  const { companyNumber } = useParams();
  const history = useHistory();

  const [loading, setLoading] = useState(true);
  const [companyData, setCompanyData] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    loadCompanyData();
  }, [companyNumber]);

  const loadCompanyData = async () => {
    try {
      setLoading(true);

      const storedCompany = localStorage.getItem('active_company');

      if (storedCompany) {
        const companyContext = JSON.parse(storedCompany);
        setCompanyData(companyContext);
      } else {
        setCompanyData({
          company_number: companyNumber,
          company_name: 'Unknown Company',
        });
      }
    } catch (err) {
      console.error('Failed to load company data:', err);
    } finally {
      setLoading(false);
    }
  };

  const renderOverview = () => (
    <Container>
      <Alert type="info" header="Data Collection Not Available">
        <SpaceBetween size="s">
          <Box>Companies House data enrichment is not currently enabled.</Box>
          <Box variant="small">
            This feature requires the Data Collection stack to be deployed. When available, you will see:
          </Box>
          <ul>
            <li>Company compliance scoring</li>
            <li>Filing history analysis</li>
            <li>Officers and directors information</li>
            <li>Business health indicators</li>
          </ul>
        </SpaceBetween>
      </Alert>
    </Container>
  );

  const renderFilingHistory = () => (
    <Container>
      <Alert type="info" header="Filing History Not Available">
        <Box>Filing history data will be available once the Data Collection stack is deployed.</Box>
      </Alert>
    </Container>
  );

  const renderOfficers = () => (
    <Container>
      <Alert type="info" header="Officers Data Not Available">
        <Box>Officers and directors information will be available once the Data Collection stack is deployed.</Box>
      </Alert>
    </Container>
  );

  if (loading) {
    return (
      <Box textAlign="center" padding="xxl">
        <Spinner size="large" />
        <Box variant="p" color="text-body-secondary">
          Loading company analysis...
        </Box>
      </Box>
    );
  }

  return (
    <SpaceBetween size="l">
      <BreadcrumbGroup
        items={[
          { text: 'Company Select', href: `#${COMPANY_SELECT_PATH}` },
          { text: companyData?.company_name || companyNumber, href: '#' },
        ]}
        ariaLabel="Breadcrumbs"
      />

      <Header variant="h1" description={`Company Number: ${companyNumber}`}>
        Company Analysis: {companyData?.company_name || 'Loading...'}
      </Header>

      <Tabs
        activeTabId={activeTab}
        onChange={({ detail }) => setActiveTab(detail.activeTabId)}
        tabs={[
          {
            id: 'overview',
            label: 'Overview',
            content: renderOverview(),
          },
          {
            id: 'filing_history',
            label: 'Filing History',
            content: renderFilingHistory(),
          },
          {
            id: 'officers',
            label: 'Officers',
            content: renderOfficers(),
          },
        ]}
      />
    </SpaceBetween>
  );
};

export default CompanyAnalysis;
