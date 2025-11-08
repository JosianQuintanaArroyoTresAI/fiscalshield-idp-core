// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
import React, { useState, useEffect } from 'react';
import { useHistory } from 'react-router-dom';
import {
  Container,
  Header,
  SpaceBetween,
  FormField,
  Input,
  Button,
  Box,
  Alert,
  Spinner,
  ColumnLayout,
  StatusIndicator,
  ExpandableSection,
  Badge,
  Table,
  Grid,
} from '@awsui/components-react';
import { Logger } from 'aws-amplify';

import { checkDataCollectionHealth, lookupCompany, triggerBackgroundResearch } from '../../services/dataCollection';
import { fetchUserCompanies, registerCompany, deleteCompany } from '../../services/userCompanies';
import CompanyCard from '../company-card/CompanyCard';
import useAppContext from '../../contexts/app';
import { DOCUMENTS_PATH, COMPANY_INTELLIGENCE_PATH, COMPANY_ANALYSIS_PATH } from '../../routes/constants';

import '@awsui/global-styles/index.css';

const logger = new Logger('CompanySelect');

const CompanySelect = () => {
  const history = useHistory();
  const { user } = useAppContext();

  const [companyNumber, setCompanyNumber] = useState('');
  const [companyData, setCompanyData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isResearching, setIsResearching] = useState(false);
  const [error, setError] = useState('');
  const [isDataCollectionAvailable, setIsDataCollectionAvailable] = useState(null);
  const [healthCheckComplete, setHealthCheckComplete] = useState(false);

  // User companies state
  const [userCompanies, setUserCompanies] = useState([]);
  const [loadingCompanies, setLoadingCompanies] = useState(true);
  const [companiesError, setCompaniesError] = useState(null);

  // Officers state
  // Research status message state
  const [researchStatusMessage, setResearchStatusMessage] = useState('');

  // Check if Data Collection Stack is available on mount
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const available = await checkDataCollectionHealth();
        setIsDataCollectionAvailable(available);
        logger.debug('Data Collection availability:', available);
      } catch (err) {
        logger.warn('Health check failed:', err);
        setIsDataCollectionAvailable(false);
      } finally {
        setHealthCheckComplete(true);
      }
    };

    checkHealth();
  }, []);

  // Load user's registered companies on mount
  useEffect(() => {
    const loadUserCompanies = async () => {
      try {
        setLoadingCompanies(true);
        setCompaniesError(null);
        const companies = await fetchUserCompanies();
        setUserCompanies(companies);
        logger.debug(`Loaded ${companies.length} companies for user`);
      } catch (err) {
        logger.error('Error loading user companies:', err);
        setCompaniesError('Failed to load your registered companies');
      } finally {
        setLoadingCompanies(false);
      }
    };

    loadUserCompanies();
  }, []);

  const handleCompanyNumberChange = (event) => {
    const { value } = event.detail;
    // Clean the input (remove spaces, ensure uppercase)
    const cleanValue = value.replace(/\s+/g, '').toUpperCase();
    // Remove any non-alphanumeric characters and limit to 8 characters
    const sanitized = cleanValue.replace(/[^A-Z0-9]/g, '').slice(0, 8);
    setCompanyNumber(sanitized);
    setCompanyData(null);
    setError('');
  };

  const handleSearch = async () => {
    if (!companyNumber || companyNumber.length < 6) {
      setError('Please enter a valid company number (6-8 characters)');
      return;
    }

    setIsLoading(true);
    setError('');
    setCompanyData(null);

    try {
      const data = await lookupCompany(companyNumber);
      logger.debug('Company data received:', data);
      setCompanyData(data);
    } catch (err) {
      logger.error('Error looking up company:', err);
      if (err.message.includes('404')) {
        setError('Company not found. Please check the company number and try again.');
      } else {
        setError('Failed to lookup company. Please try again later.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleConfirmAndResearch = async () => {
    if (!companyData) return;

    setIsResearching(true);

    // Cycling status messages for elegant loading experience
    const statusMessages = [
      'Verifying company information...',
      'Analyzing corporate structure...',
      'Running compliance checks...',
      'Preparing your workspace...',
    ];

    let messageIndex = 0;
    setResearchStatusMessage(statusMessages[0]);

    // Cycle through messages every 700ms
    const messageInterval = setInterval(() => {
      messageIndex = (messageIndex + 1) % statusMessages.length;
      setResearchStatusMessage(statusMessages[messageIndex]);
    }, 700);

    // Store company selection
    const companyContext = {
      company_number: companyData.company_number,
      company_name: companyData.company_name,
      selected_at: new Date().toISOString(),
      user_id: user?.username || 'unknown',
    };

    localStorage.setItem('active_company', JSON.stringify(companyContext));
    logger.debug('Company context saved:', companyContext);

    // Register company in UserProfileTable for persistent storage
    try {
      await registerCompany(companyData.company_number, companyData.company_name);
      logger.debug('Company registered in user profile');
    } catch (err) {
      logger.error('Failed to register company:', err);
      // Non-blocking error - still proceed with localStorage fallback
    }

    // If Data Collection Stack is available, trigger background research
    if (isDataCollectionAvailable) {
      try {
        await triggerBackgroundResearch({
          company_number: companyData.company_number,
          company_name: companyData.company_name,
          user_id: user?.username || 'unknown',
          client_id: user?.username || 'unknown',
        });
        logger.debug('Background research initiated');
      } catch (err) {
        logger.warn('Failed to trigger background research:', err);
        // Non-blocking error - still proceed to documents
      }
    }

    // Redirect after 2.5 seconds of elegant loading
    setTimeout(() => {
      clearInterval(messageInterval);
      history.push(DOCUMENTS_PATH);
    }, 2500);
  };

  const handleKeyPress = (event) => {
    if (event.detail.key === 'Enter') {
      handleSearch();
    }
  };

  const getRiskColor = (level) => {
    switch (level) {
      case 'HIGH':
        return 'red';
      case 'MEDIUM':
        return 'grey';
      case 'LOW':
        return 'green';
      default:
        return 'blue';
    }
  };

  const getScoreType = (score) => {
    if (score >= 8) return 'success';
    if (score >= 6) return 'warning';
    return 'error';
  };

  const renderRiskAnalysis = () => {
    if (!companyData?.risk_analysis) return null;

    const { risk_analysis: riskAnalysis } = companyData;

    return (
      <div style={{ borderTop: '1px solid #eee', paddingTop: '16px' }}>
        <Header variant="h3" description="Automated risk assessment based on Companies House data">
          🔍 Risk Analysis
        </Header>

        <SpaceBetween size="s">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <Badge color={getRiskColor(riskAnalysis.risk_level)}>{riskAnalysis.risk_level} RISK</Badge>
            <Box>
              <Box variant="awsui-key-label">Risk Score</Box>
              <Box>{riskAnalysis.risk_score}/100</Box>
            </Box>
          </div>

          {riskAnalysis.risk_indicators && riskAnalysis.risk_indicators.length > 0 && (
            <Alert type="warning" header={`${riskAnalysis.risk_indicators.length} Risk Indicators Found`}>
              <ul style={{ margin: '0', paddingLeft: '20px' }}>
                {riskAnalysis.risk_indicators.map((indicator) => (
                  <li key={indicator}>{indicator}</li>
                ))}
              </ul>
            </Alert>
          )}

          {(!riskAnalysis.risk_indicators || riskAnalysis.risk_indicators.length === 0) && (
            <Alert type="success">No immediate risk factors detected from Companies House data.</Alert>
          )}

          {/* Enhanced Business Health Info */}
          {companyData.business_health && (
            <Box>
              <Box variant="awsui-key-label">Business Health Check</Box>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '14px' }}>
                <div>
                  <StatusIndicator type={companyData.business_health.has_insolvency_history ? 'error' : 'success'}>
                    {companyData.business_health.has_insolvency_history ? 'Has' : 'No'} insolvency history
                  </StatusIndicator>
                </div>
                <div>
                  <StatusIndicator type={companyData.business_health.has_charges ? 'warning' : 'success'}>
                    {companyData.business_health.has_charges ? 'Has' : 'No'} registered charges
                  </StatusIndicator>
                </div>
                <div>
                  <StatusIndicator type={companyData.business_health.has_been_liquidated ? 'error' : 'success'}>
                    {companyData.business_health.has_been_liquidated ? 'Has been' : 'Never'} liquidated
                  </StatusIndicator>
                </div>
                <div>
                  <StatusIndicator type={companyData.business_health.can_file ? 'success' : 'error'}>
                    {companyData.business_health.can_file ? 'Can' : 'Cannot'} file returns
                  </StatusIndicator>
                </div>
              </div>
            </Box>
          )}

          {/* Compliance Status */}
          {companyData.accounts && (
            <Box>
              <Box variant="awsui-key-label">Compliance Status</Box>
              <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
                {companyData.accounts.overdue ? (
                  <Badge color="red">Accounts Overdue</Badge>
                ) : (
                  <Badge color="green">Accounts Up to Date</Badge>
                )}

                {companyData.confirmation_statement?.overdue ? (
                  <Badge color="red">Confirmation Overdue</Badge>
                ) : (
                  <Badge color="green">Confirmation Up to Date</Badge>
                )}
              </div>

              {companyData.accounts.next_due && (
                <div style={{ fontSize: '13px', color: '#666', marginTop: '4px' }}>
                  Next accounts due: {new Date(companyData.accounts.next_due).toLocaleDateString('en-GB')}
                </div>
              )}
            </Box>
          )}
        </SpaceBetween>
      </div>
    );
  };

  // Handle viewing documents for a registered company
  const handleViewCompanyDocuments = (company) => {
    logger.info(`Viewing documents for company: ${company.company_number}`);

    // Store company context
    const companyContext = {
      company_number: company.company_number,
      company_name: company.company_name,
      selected_at: new Date().toISOString(),
      user_id: user?.username || 'unknown',
      from_registered: true,
    };

    localStorage.setItem('active_company', JSON.stringify(companyContext));
    logger.debug('Company context saved:', companyContext);

    // Navigate to documents page
    history.push(DOCUMENTS_PATH);
  };

  // Handle viewing company intelligence
  const handleViewCompanyIntelligence = (company) => {
    logger.debug('Viewing intelligence for company:', company.company_number);

    // Set company context in localStorage
    const companyContext = {
      company_number: company.company_number,
      company_name: company.company_name,
      selected_at: new Date().toISOString(),
      user_id: user?.username || 'unknown',
      from_registered: true,
    };

    localStorage.setItem('active_company', JSON.stringify(companyContext));
    logger.debug('Company context saved:', companyContext);

    // Navigate to intelligence page
    const intelligencePath = COMPANY_INTELLIGENCE_PATH.replace(':companyNumber', company.company_number);
    history.push(intelligencePath);
  };

  // Handle viewing company analysis
  const handleViewCompanyAnalysis = (company) => {
    logger.debug('Viewing analysis for company:', company.company_number);

    // Set company context in localStorage
    const companyContext = {
      company_number: company.company_number,
      company_name: company.company_name,
      selected_at: new Date().toISOString(),
      user_id: user?.username || 'unknown',
      from_registered: true,
    };

    localStorage.setItem('active_company', JSON.stringify(companyContext));
    logger.debug('Company context saved:', companyContext);

    // Navigate to analysis page
    const analysisPath = COMPANY_ANALYSIS_PATH.replace(':companyNumber', company.company_number);
    history.push(analysisPath);
  };  // Handle deleting a company
  const handleDeleteCompany = async (company) => {
    logger.info(`Deleting company: ${company.company_number}`);

    try {
      setLoadingCompanies(true);
      await deleteCompany(company.company_number);

      // Refresh companies list
      const companies = await fetchUserCompanies();
      setUserCompanies(companies);

      logger.debug('Company deleted and list refreshed');
    } catch (error) {
      logger.error('Error deleting company:', error);
      setCompaniesError(`Failed to delete company: ${error.message}`);
    } finally {
      setLoadingCompanies(false);
    }
  };

  return (
    <Box padding={{ top: 'xxxl' }}>
      <SpaceBetween size="l">
        {/* Registered Companies Section */}
        {userCompanies && userCompanies.length > 0 && (
          <Container
            header={
              <Header variant="h2" description="Companies you have registered documents for">
                Your Registered Companies
              </Header>
            }
          >
            {loadingCompanies && (
              <Box textAlign="center" padding={{ vertical: 'l' }}>
                <Spinner size="large" />
                <Box variant="p" padding={{ top: 's' }}>
                  Loading your companies...
                </Box>
              </Box>
            )}
            {!loadingCompanies && companiesError && (
              <Alert type="error" header="Failed to load companies">
                {companiesError}
              </Alert>
            )}
            {!loadingCompanies && !companiesError && (
              <Grid gridDefinition={[{ colspan: 4 }, { colspan: 4 }, { colspan: 4 }]}>
                {userCompanies.map((company) => (
                  <CompanyCard
                    key={company.company_number}
                    company={company}
                    onViewDocuments={handleViewCompanyDocuments}
                    onViewIntelligence={handleViewCompanyIntelligence}
                    onViewAnalysis={handleViewCompanyAnalysis}
                    onDelete={handleDeleteCompany}
                  />
                ))}
              </Grid>
            )}
          </Container>
        )}

        <Container
          header={
            <Header variant="h1" description="Enter a UK Companies House number to get started">
              {userCompanies && userCompanies.length > 0 ? 'Register Another Company' : 'Select Your Company'}
            </Header>
          }
        >
          <SpaceBetween size="l">
            {/* Health Check Status */}
            {healthCheckComplete && (
              <Alert
                type={isDataCollectionAvailable ? 'success' : 'info'}
                statusIconAriaLabel={isDataCollectionAvailable ? 'Success' : 'Info'}
                header={isDataCollectionAvailable ? 'Deep research available' : 'Basic search available'}
              >
                {isDataCollectionAvailable
                  ? 'Background company research is enabled. You will receive a notification when complete.'
                  : 'Background research is unavailable. You can still select your company and access documents.'}
              </Alert>
            )}

            {/* Search Form */}
            <FormField
              label="Company Number"
              description="Enter the 8-digit UK Companies House registration number"
              errorText={error}
            >
              <SpaceBetween size="xs" direction="horizontal">
                <Input
                  value={companyNumber}
                  onChange={handleCompanyNumberChange}
                  onKeyDown={handleKeyPress}
                  placeholder="12345678"
                  disabled={isLoading}
                  inputMode="text"
                  maxLength={8}
                />
                <Button
                  onClick={handleSearch}
                  loading={isLoading}
                  disabled={!companyNumber || companyNumber.length < 6}
                  variant="primary"
                >
                  Search
                </Button>
              </SpaceBetween>
            </FormField>

            {/* Company Details */}
            {companyData && (
              <Container header={<Header variant="h2">Company Details</Header>}>
                <SpaceBetween size="m">
                  <ColumnLayout columns={2} variant="text-grid">
                    <div>
                      <Box variant="awsui-key-label">Company Name</Box>
                      <div>{companyData.company_name}</div>
                    </div>
                    <div>
                      <Box variant="awsui-key-label">Company Number</Box>
                      <div>{companyData.company_number}</div>
                    </div>
                    <div>
                      <Box variant="awsui-key-label">Status</Box>
                      <div>
                        <StatusIndicator type={companyData.company_status === 'active' ? 'success' : 'warning'}>
                          {companyData.company_status?.toUpperCase() || 'UNKNOWN'}
                        </StatusIndicator>
                      </div>
                    </div>
                    <div>
                      <Box variant="awsui-key-label">Incorporation Date</Box>
                      <div>{companyData.date_of_creation || 'N/A'}</div>
                    </div>
                  </ColumnLayout>

                  {companyData.registered_office_address && (
                    <div>
                      <Box variant="awsui-key-label">Registered Office</Box>
                      <Box variant="p">
                        {[
                          companyData.registered_office_address.address_line_1,
                          companyData.registered_office_address.address_line_2,
                          companyData.registered_office_address.locality,
                          companyData.registered_office_address.region,
                          companyData.registered_office_address.postal_code,
                        ]
                          .filter(Boolean)
                          .join(', ')}
                      </Box>
                    </div>
                  )}

                  {/* Risk Analysis Section */}
                  {renderRiskAnalysis()}

                  <Box textAlign="center" padding={{ top: 'l' }}>
                    <SpaceBetween size="m" direction="vertical">
                      {isResearching ? (
                        <Box>
                          <Spinner size="large" />
                          <Box variant="p" padding={{ top: 's' }} fontSize="body-m" fontWeight="normal">
                            {researchStatusMessage}
                          </Box>
                        </Box>
                      ) : (
                        <>
                          <Button
                            onClick={handleConfirmAndResearch}
                            variant="primary"
                            iconAlign="right"
                            iconName="arrow-right"
                          >
                            Begin Background Research
                          </Button>
                          {isDataCollectionAvailable && (
                            <Box variant="small" color="text-status-inactive">
                              Our comprehensive verification includes: Corporate structure · Compliance screening ·
                              Officer verification · Risk assessment
                            </Box>
                          )}
                          {!isDataCollectionAvailable && (
                            <Box variant="small" color="text-status-warning">
                              Background research currently unavailable - you can still proceed
                            </Box>
                          )}
                        </>
                      )}
                    </SpaceBetween>
                  </Box>
                </SpaceBetween>
              </Container>
            )}
          </SpaceBetween>
        </Container>

        {/* Help Section */}
        <Container header={<Header variant="h3">Need help finding your company number?</Header>}>
          <SpaceBetween size="xs">
            <Box variant="p">You can find your company number on:</Box>
            <ul>
              <li>Your certificate of incorporation</li>
              <li>Official company documents and correspondence</li>
              <li>
                The{' '}
                <a
                  href="https://find-and-update.company-information.service.gov.uk/"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Companies House website
                </a>
              </li>
            </ul>
          </SpaceBetween>
        </Container>
      </SpaceBetween>
    </Box>
  );
};

export default CompanySelect;
