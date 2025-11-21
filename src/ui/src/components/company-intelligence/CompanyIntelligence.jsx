// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
import React, { useState, useEffect } from 'react';
import { useParams, useHistory } from 'react-router-dom';
import {
  Container,
  Header,
  SpaceBetween,
  Button,
  Box,
  Alert,
  Spinner,
  StatusIndicator,
  ColumnLayout,
  Badge,
  ExpandableSection,
  BreadcrumbGroup,
  Grid,
} from '@awsui/components-react';
import { Logger } from 'aws-amplify';

import { checkAnalysisStackHealth, fetchCompanyIntelligence, generateAMLReport } from '../../services/analysisStack';
import { COMPANY_SELECT_PATH } from '../../routes/constants';
import AppLayoutWrapper from '../app-layout-wrapper';
import MarkdownViewer from '../document-viewer/MarkdownViewer';

import '@awsui/global-styles/index.css';

const logger = new Logger('CompanyIntelligence');

const getReportAlertType = (message) => {
  if (!message) {
    return 'info';
  }

  if (message.includes('successfully')) {
    return 'success';
  }

  if (message.includes('Failed')) {
    return 'error';
  }

  return 'info';
};

const CompanyIntelligence = () => {
  const { companyNumber } = useParams();
  const history = useHistory();

  const [intelligence, setIntelligence] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isGeneratingReport, setIsGeneratingReport] = useState(false);
  const [error, setError] = useState('');
  const [reportMessage, setReportMessage] = useState('');
  const [isAnalysisStackAvailable, setIsAnalysisStackAvailable] = useState(null);

  // Check if Analysis Stack is available on mount
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const available = await checkAnalysisStackHealth();
        setIsAnalysisStackAvailable(available);
        logger.debug('Analysis Stack availability:', available);
      } catch (err) {
        logger.warn('Analysis Stack health check failed:', err);
        setIsAnalysisStackAvailable(false);
      }
    };

    checkHealth();
  }, []);

  // Fetch company intelligence on mount
  useEffect(() => {
    const loadIntelligence = async () => {
      if (!companyNumber) {
        setError('No company number provided');
        setIsLoading(false);
        return;
      }

      try {
        setIsLoading(true);
        setError('');
        const data = await fetchCompanyIntelligence(companyNumber);
        setIntelligence(data);
        logger.debug('Intelligence loaded:', data);
      } catch (err) {
        logger.error('Error loading intelligence:', err);
        setError(err.message || 'Failed to load company intelligence');
      } finally {
        setIsLoading(false);
      }
    };

    if (isAnalysisStackAvailable) {
      loadIntelligence();
    }
  }, [companyNumber, isAnalysisStackAvailable]);

  const handleRefresh = async () => {
    try {
      setIsRefreshing(true);
      setError('');
      const data = await fetchCompanyIntelligence(companyNumber, true);
      setIntelligence(data);
      logger.debug('Intelligence refreshed:', data);
    } catch (err) {
      logger.error('Error refreshing intelligence:', err);
      setError(err.message || 'Failed to refresh company intelligence');
    } finally {
      setIsRefreshing(false);
    }
  };

  const [reportData, setReportData] = useState(null);
  const [reportMarkdown, setReportMarkdown] = useState(null);
  const [isLoadingMarkdown, setIsLoadingMarkdown] = useState(false);

  // Fetch markdown content when reportData changes
  useEffect(() => {
    const fetchMarkdown = async () => {
      if (!reportData?.downloadUrl) {
        setReportMarkdown(null);
        return;
      }

      try {
        setIsLoadingMarkdown(true);
        logger.debug('Fetching report markdown from:', reportData.downloadUrl);

        const response = await fetch(reportData.downloadUrl);
        if (!response.ok) {
          throw new Error(`Failed to fetch report: ${response.statusText}`);
        }

        const markdown = await response.text();
        setReportMarkdown(markdown);
        logger.debug('Report markdown loaded successfully');
      } catch (err) {
        logger.error('Error fetching report markdown:', err);
        setReportMessage(`Failed to load report content: ${err.message}`);
      } finally {
        setIsLoadingMarkdown(false);
      }
    };

    fetchMarkdown();
  }, [reportData]);

  const handleGenerateReport = async () => {
    try {
      setIsGeneratingReport(true);
      setReportMessage('');
      setReportData(null);
      setReportMarkdown(null);
      const result = await generateAMLReport(companyNumber);

      if (result.success) {
        setReportMessage(`Report generated successfully for ${result.companyName}!`);
        setReportData(result);
      } else {
        setReportMessage(result.message);
      }

      logger.debug('AML report generation result:', result);
    } catch (err) {
      logger.error('Error generating AML report:', err);
      setReportMessage(err.message || 'Failed to generate AML report');
    } finally {
      setIsGeneratingReport(false);
    }
  };

  const getRiskBadgeType = (riskLevel) => {
    switch (riskLevel?.toUpperCase()) {
      case 'HIGH':
        return 'red';
      case 'MEDIUM':
        return 'blue';
      case 'LOW':
        return 'green';
      default:
        return 'grey';
    }
  };

  const formatDataAge = (hours) => {
    if (hours < 1) return 'Just now';
    if (hours < 2) return '1 hour ago';
    if (hours < 24) return `${Math.floor(hours)} hours ago`;
    const days = Math.floor(hours / 24);
    return days === 1 ? '1 day ago' : `${days} days ago`;
  };

  const breadcrumbs = (
    <BreadcrumbGroup
      items={[
        { text: 'Company Select', href: COMPANY_SELECT_PATH },
        { text: intelligence?.company_name || companyNumber, href: '#' },
      ]}
      onFollow={(event) => {
        event.preventDefault();
        history.push(event.detail.href);
      }}
    />
  );

  if (isAnalysisStackAvailable === false) {
    return (
      <AppLayoutWrapper breadcrumbs={breadcrumbs}>
        <Alert type="warning" header="Analysis Stack Not Available">
          The Analysis Stack is not deployed or not accessible. Company intelligence features are currently unavailable.
        </Alert>
      </AppLayoutWrapper>
    );
  }

  if (isLoading) {
    return (
      <AppLayoutWrapper breadcrumbs={breadcrumbs}>
        <Box textAlign="center" padding="xxl">
          <Spinner size="large" />
          <Box variant="p">Loading company intelligence...</Box>
        </Box>
      </AppLayoutWrapper>
    );
  }

  if (error && !intelligence) {
    return (
      <AppLayoutWrapper breadcrumbs={breadcrumbs}>
        <SpaceBetween size="l">
          <Alert type="error" header="Error Loading Intelligence">
            {error}
          </Alert>
          <Button onClick={() => history.push(COMPANY_SELECT_PATH)}>Back to Company Select</Button>
        </SpaceBetween>
      </AppLayoutWrapper>
    );
  }

  if (!intelligence) {
    return null;
  }

  const riskAssessment = intelligence.risk_assessment || {};
  const governance = intelligence.governance || {};
  const financial = intelligence.financial || {};
  const aml = intelligence.aml || {};
  const reputational = intelligence.reputational || {};
  const flagsSummary = riskAssessment.flags_summary || {};
  const insights = intelligence.insights || null;

  return (
    <AppLayoutWrapper breadcrumbs={breadcrumbs}>
      <SpaceBetween size="l">
        {/* Hero Banner - Risk Assessment */}
        <Container
          header={
            <Header
              variant="h1"
              description={`Company Number: ${intelligence.company_number}`}
              actions={
                <SpaceBetween direction="horizontal" size="xs">
                  <Button onClick={handleRefresh} loading={isRefreshing} iconName="refresh">
                    Refresh Intelligence
                  </Button>
                </SpaceBetween>
              }
            >
              {intelligence.company_name}
            </Header>
          }
        >
          <ColumnLayout columns={3} variant="text-grid">
            <div>
              <Box variant="awsui-key-label">Risk Level</Box>
              <Badge color={getRiskBadgeType(riskAssessment.risk_level)}>{riskAssessment.risk_level}</Badge>
            </div>
            <div>
              <Box variant="awsui-key-label">Risk Score</Box>
              <Box variant="p">{(riskAssessment.overall_risk_score || 0).toFixed(2)} / 1.00</Box>
            </div>
            <div>
              <Box variant="awsui-key-label">Last Updated</Box>
              <StatusIndicator type="success">{formatDataAge(intelligence.data_age_hours || 0)}</StatusIndicator>
            </div>
          </ColumnLayout>

          <Box padding={{ top: 'm' }}>
            <Box variant="p" color="text-body-secondary">
              {riskAssessment.summary?.split('\n')[0] || 'No summary available'}
            </Box>
          </Box>
        </Container>

        {/* Error Alert */}
        {error && (
          <Alert type="error" dismissible onDismiss={() => setError('')}>
            {error}
          </Alert>
        )}

        {/* Risk Summary Card */}
        <Container header={<Header variant="h2">Risk Summary</Header>}>
          <ColumnLayout columns={4} variant="text-grid">
            <div>
              <Box variant="awsui-key-label">Critical Flags</Box>
              <Box variant="h3" color={flagsSummary.critical > 0 ? 'text-status-error' : 'text-body-secondary'}>
                {flagsSummary.critical || 0}
              </Box>
            </div>
            <div>
              <Box variant="awsui-key-label">High Risk Flags</Box>
              <Box variant="h3" color={flagsSummary.high > 0 ? 'text-status-warning' : 'text-body-secondary'}>
                {flagsSummary.high || 0}
              </Box>
            </div>
            <div>
              <Box variant="awsui-key-label">Medium Risk Flags</Box>
              <Box variant="h3" color={flagsSummary.medium > 0 ? 'text-status-info' : 'text-body-secondary'}>
                {flagsSummary.medium || 0}
              </Box>
            </div>
            <div>
              <Box variant="awsui-key-label">Low Risk Flags</Box>
              <Box variant="h3">{flagsSummary.low || 0}</Box>
            </div>
          </ColumnLayout>
        </Container>

        {/* Insights Grid */}
        <Grid gridDefinition={[{ colspan: 4 }, { colspan: 4 }, { colspan: 4 }]}>
          {/* Governance Card */}
          <Container header={<Header variant="h2">🏛️ Governance</Header>}>
            <ColumnLayout columns={1} variant="text-grid">
              <div>
                <Box variant="awsui-key-label">Company Status</Box>
                <Badge color={governance.company_status === 'active' ? 'green' : 'grey'}>
                  {governance.company_status || 'Unknown'}
                </Badge>
              </div>
              <div>
                <Box variant="awsui-key-label">Total Directors</Box>
                <Box>{governance.total_officers || 0}</Box>
              </div>
              <div>
                <Box variant="awsui-key-label">Active Directors</Box>
                <Box>{governance.active_officers || 0}</Box>
              </div>
              <div>
                <Box variant="awsui-key-label">Director Stability</Box>
                <Box>{governance.director_stability || 'Unknown'}</Box>
              </div>
            </ColumnLayout>
          </Container>

          {/* Financial Card */}
          <Container header={<Header variant="h2">💰 Financial</Header>}>
            <ColumnLayout columns={1} variant="text-grid">
              <div>
                <Box variant="awsui-key-label">Filing Compliance</Box>
                <StatusIndicator type="success">{financial.filing_compliance || 'Unknown'}</StatusIndicator>
              </div>
              <div>
                <Box variant="awsui-key-label">Accounts Status</Box>
                <StatusIndicator type={financial.accounts_overdue ? 'warning' : 'success'}>
                  {financial.accounts_overdue ? 'Overdue' : 'Current'}
                </StatusIndicator>
              </div>
              <div>
                <Box variant="awsui-key-label">Confirmation Statement</Box>
                <StatusIndicator type={financial.confirmation_statement_overdue ? 'warning' : 'success'}>
                  {financial.confirmation_statement_overdue ? 'Overdue' : 'Current'}
                </StatusIndicator>
              </div>
            </ColumnLayout>
          </Container>

          {/* AML Card */}
          <Container header={<Header variant="h2">AML Screening</Header>}>
            <ColumnLayout columns={1} variant="text-grid">
              <div>
                <Box variant="awsui-key-label">Sanctions Screening</Box>
                <StatusIndicator type={aml.sanctions_screening === 'clear' ? 'success' : 'error'}>
                  {aml.sanctions_screening === 'clear' ? 'Clear' : 'Matches Found'}
                </StatusIndicator>
              </div>
              <div>
                <Box variant="awsui-key-label">PEP Screening</Box>
                <StatusIndicator type={aml.pep_screening === 'clear' ? 'success' : 'warning'}>
                  {aml.pep_screening === 'clear' ? 'Clear' : 'Matches Found'}
                </StatusIndicator>
              </div>
              <div>
                <Box variant="awsui-key-label">Enhanced Due Diligence</Box>
                <Badge color={aml.requires_enhanced_dd ? 'red' : 'green'}>
                  {aml.requires_enhanced_dd ? 'Required' : 'Not Required'}
                </Badge>
              </div>
              {(aml.sanctioned_directors?.length > 0 || aml.pep_directors?.length > 0) && (
                <div>
                  <Box variant="awsui-key-label">Flagged Individuals</Box>
                  <Box variant="p" fontSize="body-s" color="text-status-error">
                    {aml.sanctioned_directors?.length > 0 && (
                      <div>Sanctioned: {aml.sanctioned_directors.join(', ')}</div>
                    )}
                    {aml.pep_directors?.length > 0 && <div>PEP: {aml.pep_directors.join(', ')}</div>}
                  </Box>
                </div>
              )}
            </ColumnLayout>
          </Container>
        </Grid>

        {/* Reputational Section */}
        <Container header={<Header variant="h2">📰 Reputational</Header>}>
          <ColumnLayout columns={3} variant="text-grid">
            <div>
              <Box variant="awsui-key-label">Adverse Media Count</Box>
              <Box variant="p">{reputational.adverse_media_count || 0}</Box>
            </div>
            <div>
              <Box variant="awsui-key-label">Media Risk Contribution</Box>
              <Box variant="p">{(reputational.adverse_media_risk || 0).toFixed(2)}</Box>
            </div>
            <div>
              <Box variant="awsui-key-label">Status</Box>
              <StatusIndicator type={reputational.has_adverse_media ? 'warning' : 'success'}>
                {reputational.has_adverse_media ? 'Adverse Media Found' : 'No Issues Found'}
              </StatusIndicator>
            </div>
          </ColumnLayout>
        </Container>

        {/* LLM Insights Section */}
        {insights && (
          <Container
            header={
              <Header variant="h2" description="AI-powered risk analysis and compliance recommendations">
                Intelligence Insights
              </Header>
            }
          >
            <SpaceBetween size="l">
              {/* Overall Summary */}
              {insights.overall_summary && (
                <Box>
                  <Box variant="awsui-key-label" margin={{ bottom: 'xs' }}>
                    Overall Assessment
                  </Box>
                  <Box variant="p" color="text-body-secondary">
                    {insights.overall_summary}
                  </Box>
                </Box>
              )}

              {/* Category Insights Grid */}
              <Grid gridDefinition={[{ colspan: 6 }, { colspan: 6 }]}>
                {/* Governance Insight */}
                {insights.governance_insight && (
                  <Box>
                    <Box variant="awsui-key-label" margin={{ bottom: 'xs' }}>
                      Governance Analysis
                    </Box>
                    <Box variant="p" fontSize="body-s">
                      {insights.governance_insight}
                    </Box>
                  </Box>
                )}

                {/* Financial Insight */}
                {insights.financial_insight && (
                  <Box>
                    <Box variant="awsui-key-label" margin={{ bottom: 'xs' }}>
                      Financial Analysis
                    </Box>
                    <Box variant="p" fontSize="body-s">
                      {insights.financial_insight}
                    </Box>
                  </Box>
                )}

                {/* AML Insight */}
                {insights.aml_insight && (
                  <Box>
                    <Box variant="awsui-key-label" margin={{ bottom: 'xs' }}>
                      AML Screening Analysis
                    </Box>
                    <Box variant="p" fontSize="body-s">
                      {insights.aml_insight}
                    </Box>
                  </Box>
                )}

                {/* Reputational Insight */}
                {insights.reputational_insight && (
                  <Box>
                    <Box variant="awsui-key-label" margin={{ bottom: 'xs' }}>
                      Reputational Analysis
                    </Box>
                    <Box variant="p" fontSize="body-s">
                      {insights.reputational_insight}
                    </Box>
                  </Box>
                )}
              </Grid>

              {/* Recommendations */}
              {insights.recommendations && insights.recommendations.length > 0 && (
                <Box>
                  <Box variant="awsui-key-label" margin={{ bottom: 'xs' }}>
                    💡 Recommended Actions
                  </Box>
                  <Box variant="ul">
                    {insights.recommendations.map((rec, index) => (
                      <li key={index}>
                        <Box variant="p" fontSize="body-s">
                          {rec}
                        </Box>
                      </li>
                    ))}
                  </Box>
                </Box>
              )}

              {/* Red Flags */}
              {insights.red_flags && insights.red_flags.length > 0 && (
                <Alert type="warning" header="Areas of Concern">
                  <Box variant="ul">
                    {insights.red_flags.map((flag, index) => (
                      <li key={index}>{flag}</li>
                    ))}
                  </Box>
                </Alert>
              )}

              {/* Mitigating Factors */}
              {insights.mitigating_factors && insights.mitigating_factors.length > 0 && (
                <Box>
                  <Box variant="awsui-key-label" margin={{ bottom: 'xs' }}>
                    Positive Indicators
                  </Box>
                  <Box variant="ul">
                    {insights.mitigating_factors.map((factor, index) => (
                      <li key={index}>
                        <Box variant="p" fontSize="body-s" color="text-status-success">
                          {factor}
                        </Box>
                      </li>
                    ))}
                  </Box>
                </Box>
              )}
            </SpaceBetween>
          </Container>
        )}

        {/* Flags & Alerts */}
        {(riskAssessment.critical_flags?.length > 0 || riskAssessment.high_flags?.length > 0) && (
          <ExpandableSection headerText="Flags & Alerts" defaultExpanded={flagsSummary.critical > 0}>
            <SpaceBetween size="m">
              {riskAssessment.critical_flags?.map((flag, index) => (
                <Alert key={`critical-${index}`} type="error" header={flag.flag_type}>
                  {flag.description}
                  {flag.source && (
                    <Box variant="small" color="text-body-secondary">
                      Source: {flag.source}
                    </Box>
                  )}
                </Alert>
              ))}
              {riskAssessment.high_flags?.map((flag, index) => (
                <Alert key={`high-${index}`} type="warning" header={flag.flag_type}>
                  {flag.description}
                  {flag.source && (
                    <Box variant="small" color="text-body-secondary">
                      Source: {flag.source}
                    </Box>
                  )}
                </Alert>
              ))}
            </SpaceBetween>
          </ExpandableSection>
        )}

        {/* Generate AML Report Section - At Bottom */}
        <Container
          header={
            <Header variant="h2" description="Generate a comprehensive AML compliance report for this company">
              AML Compliance Report
            </Header>
          }
        >
          <SpaceBetween size="m">
            <Box variant="p">
              Generate a detailed Anti-Money Laundering (AML) compliance report including risk assessment, due diligence
              findings, and regulatory compliance summary for client files.
            </Box>

            {/* Show warning if intelligence data is not available */}
            {!intelligence && !isLoading && (
              <Alert type="warning" header="Intelligence Data Required">
                Company intelligence data must be gathered before generating an AML report. Please refresh the page or
                click "Refresh Intelligence" to load the required data.
              </Alert>
            )}

            {!reportData ? (
              <Button 
                variant="primary" 
                onClick={handleGenerateReport} 
                loading={isGeneratingReport}
                disabled={!intelligence || isLoading || isRefreshing}
              >
                Generate AML Report
              </Button>
            ) : (
              <SpaceBetween direction="horizontal" size="xs">
                <Button
                  variant="primary"
                  iconName="download"
                  onClick={() => window.open(reportData.downloadUrl, '_blank')}
                >
                  Download Report
                </Button>
                <Button 
                  variant="normal" 
                  onClick={handleGenerateReport} 
                  loading={isGeneratingReport}
                  disabled={!intelligence || isLoading || isRefreshing}
                >
                  Regenerate Report
                </Button>
              </SpaceBetween>
            )}

            {reportMessage && (
              <Alert
                type={getReportAlertType(reportMessage)}
                dismissible
                onDismiss={() => {
                  setReportMessage('');
                }}
              >
                {reportMessage}
              </Alert>
            )}

            {/* Display the markdown report content inline */}
            {isLoadingMarkdown && (
              <Box textAlign="center" padding="l">
                <Spinner size="large" />
                <Box variant="p" padding={{ top: 's' }}>
                  Loading report content...
                </Box>
              </Box>
            )}

            {reportMarkdown && !isLoadingMarkdown && (
              <Box margin={{ top: 'l' }}>
                <MarkdownViewer
                  content={reportMarkdown}
                  documentName={`AML_Report_${companyNumber}`}
                  title={`AML Report - ${reportData?.companyName || companyNumber}`}
                />
              </Box>
            )}
          </SpaceBetween>
        </Container>

        {/* Data Sources Footer */}
        <ExpandableSection headerText="📋 Data Sources" variant="footer">
          <ColumnLayout columns={2} variant="text-grid">
            <div>
              <Box variant="awsui-key-label">Companies House</Box>
              <StatusIndicator type="success">
                Collected {formatDataAge(intelligence.data_age_hours || 0)}
              </StatusIndicator>
            </div>
            <div>
              <Box variant="awsui-key-label">Data Collection Stack</Box>
              <StatusIndicator type="success">Active</StatusIndicator>
            </div>
          </ColumnLayout>
        </ExpandableSection>
      </SpaceBetween>
    </AppLayoutWrapper>
  );
};

export default CompanyIntelligence;
