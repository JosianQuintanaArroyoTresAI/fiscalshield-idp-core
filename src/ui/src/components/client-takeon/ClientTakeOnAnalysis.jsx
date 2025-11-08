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
  Button,
} from '@awsui/components-react';

import { useCompany } from '../../contexts/company';
import { COMPANY_SELECT_PATH } from '../../routes/constants';

import '@awsui/global-styles/index.css';

const ClientTakeOnAnalysis = () => {
  const history = useHistory();
  const { activeCompany, isCompanySelected } = useCompany();
  
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('aml');

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
          Loading client take-on analysis...
        </Box>
      </Box>
    );
  }

  if (!activeCompany) {
    return null;
  }

  const renderAMLTab = () => (
    <Container>
      <Alert type="info" header="AML Analysis Not Available">
        <SpaceBetween size="s">
          <Box>
            Anti-Money Laundering analysis will be available once integrated with the Analysis Stack.
          </Box>
          <Box variant="small">
            This will include:
          </Box>
          <ul>
            <li>Sanctions screening results</li>
            <li>PEP (Politically Exposed Persons) checks</li>
            <li>Adverse media monitoring</li>
            <li>Ultimate Beneficial Owner (UBO) identification</li>
            <li>Risk scoring and recommendations</li>
          </ul>
        </SpaceBetween>
      </Alert>
    </Container>
  );

  const renderKYCTab = () => (
    <Container>
      <Alert type="info" header="KYC Verification Not Available">
        <SpaceBetween size="s">
          <Box>
            Know Your Customer verification will be available once integrated with the Analysis Stack.
          </Box>
          <Box variant="small">
            This will include:
          </Box>
          <ul>
            <li>Identity verification status</li>
            <li>Document verification (ID, proof of address)</li>
            <li>Business verification</li>
            <li>Source of funds documentation</li>
            <li>Enhanced due diligence where required</li>
          </ul>
        </SpaceBetween>
      </Alert>
    </Container>
  );

  const renderComplianceTab = () => (
    <Container>
      <Alert type="info" header="Compliance Check Not Available">
        <SpaceBetween size="s">
          <Box>
            Compliance verification will be available once integrated with Companies House data.
          </Box>
          <Box variant="small">
            This will include:
          </Box>
          <ul>
            <li>Filing compliance history</li>
            <li>Director disqualifications check</li>
            <li>Insolvency history</li>
            <li>Charges and mortgages</li>
            <li>Company status verification</li>
          </ul>
        </SpaceBetween>
      </Alert>
    </Container>
  );

  return (
    <SpaceBetween size="l">
      <BreadcrumbGroup
        items={[
          { text: 'Company Select', href: `#${COMPANY_SELECT_PATH}` },
          { text: activeCompany.companyName, href: '#' },
          { text: 'Client Take-On Analysis', href: '#' },
        ]}
        ariaLabel="Breadcrumbs"
      />
      
      <Header
        variant="h1"
        description={`Company Number: ${activeCompany.companyNumber}`}
        actions={
          <Button variant="primary" disabled>
            Generate Report
          </Button>
        }
      >
        Client Take-On Analysis: {activeCompany.companyName}
      </Header>

      <Tabs
        activeTabId={activeTab}
        onChange={({ detail }) => setActiveTab(detail.activeTabId)}
        tabs={[
          {
            id: 'aml',
            label: 'AML Screening',
            content: renderAMLTab(),
          },
          {
            id: 'kyc',
            label: 'KYC Verification',
            content: renderKYCTab(),
          },
          {
            id: 'compliance',
            label: 'Compliance Check',
            content: renderComplianceTab(),
          },
        ]}
      />
    </SpaceBetween>
  );
};

export default ClientTakeOnAnalysis;
