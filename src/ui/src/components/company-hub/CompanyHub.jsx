// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
import React, { useState, useEffect } from 'react';
import { useParams, useHistory } from 'react-router-dom';
import {
  AppLayout,
  Tabs,
  SpaceBetween,
  BreadcrumbGroup,
  Header,
  Box,
  Spinner,
  Flashbar,
} from '@awsui/components-react';
import { Logger } from 'aws-amplify';

import { useCompany } from '../../contexts/company';
import useAppContext from '../../contexts/app';
import useNotifications from '../../hooks/use-notifications';
import { COMPANY_SELECT_PATH, DOCUMENTS_PATH } from '../../routes/constants';
import { appLayoutLabels } from '../common/labels';

import GenAIIDPTopNavigation from '../genai-idp-top-navigation';
import Navigation from '../genaiidp-layout/navigation';
import CompanyOverview from './CompanyOverview';
import ClientTakeOnAnalysis from '../client-takeon/ClientTakeOnAnalysis';

const logger = new Logger('CompanyHub');

/**
 * CompanyHub Component
 * 
 * Central hub for all company-related information with tabbed interface:
 * - Overview: Basic company info, filing history, officers
 * - Intelligence: Risk analysis, AML screening, compliance checks
 * - Documents: Document management (redirects to existing documents route)
 */
const CompanyHub = () => {
  const { companyNumber } = useParams();
  const history = useHistory();
  const { activeCompany, isCompanySelected } = useCompany();
  const { navigationOpen, setNavigationOpen } = useAppContext();
  const notifications = useNotifications();

  const [loading, setLoading] = useState(true);
  const [activeTabId, setActiveTabId] = useState('overview');

  useEffect(() => {
    // Redirect to company select if no company is selected
    if (!isCompanySelected) {
      logger.warn('No company selected, redirecting to company select');
      history.push(COMPANY_SELECT_PATH);
      return;
    }

    // Verify the URL company number matches the active company
    if (activeCompany?.companyNumber !== companyNumber) {
      logger.warn('Company number mismatch, redirecting to company select');
      history.push(COMPANY_SELECT_PATH);
      return;
    }

    setLoading(false);
  }, [isCompanySelected, activeCompany, companyNumber, history]);

  const handleTabChange = ({ detail }) => {
    const newTabId = detail.activeTabId;
    
    // For documents tab, navigate to the documents route
    if (newTabId === 'documents') {
      history.push(DOCUMENTS_PATH);
    } else {
      setActiveTabId(newTabId);
    }
  };

  if (loading) {
    return (
      <>
        <GenAIIDPTopNavigation />
        <Box textAlign="center" padding="xxl">
          <Spinner size="large" />
          <Box variant="p" padding={{ top: 's' }}>
            Loading company hub...
          </Box>
        </Box>
      </>
    );
  }

  const breadcrumbItems = [
    { text: 'Company Select', href: `#${COMPANY_SELECT_PATH}` },
    { text: activeCompany?.companyName || companyNumber, href: '#' },
  ];

  const tabs = [
    {
      id: 'overview',
      label: 'Overview',
      content: (
        <Box padding={{ top: 'l' }}>
          <CompanyOverview companyData={activeCompany} loading={loading} />
        </Box>
      ),
    },
    {
      id: 'intelligence',
      label: 'Intelligence',
      content: (
        <Box padding={{ top: 'l' }}>
          <ClientTakeOnAnalysis embedded={true} />
        </Box>
      ),
    },
    {
      id: 'documents',
      label: 'Documents',
      content: null, // Will redirect, so content not needed
    },
  ];

  return (
    <>
      <GenAIIDPTopNavigation />
      <AppLayout
        headerSelector="#top-navigation"
        navigation={<Navigation />}
        navigationOpen={navigationOpen}
        onNavigationChange={({ detail }) => setNavigationOpen(detail.open)}
        breadcrumbs={
          <BreadcrumbGroup items={breadcrumbItems} ariaLabel="Breadcrumbs" />
        }
        notifications={<Flashbar items={notifications} />}
        content={
          <SpaceBetween size="l">
            <Header
              variant="h1"
              description={`Company Number: ${companyNumber}`}
            >
              {activeCompany?.companyName || 'Company Hub'}
            </Header>

            <Tabs
              activeTabId={activeTabId}
              onChange={handleTabChange}
              tabs={tabs}
            />
          </SpaceBetween>
        }
        ariaLabels={appLayoutLabels}
      />
    </>
  );
};

export default CompanyHub;
