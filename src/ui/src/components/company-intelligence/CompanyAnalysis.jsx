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
  ColumnLayout,
} from '@awsui/components-react';

import { COMPANY_SELECT_PATH } from '../../routes/constants';
import { useCompany } from '../../contexts/company';
import { fetchCompanyIntelligence, generateAMLReport } from '../../services/analysisStack';

import '@awsui/global-styles/index.css';

const CompanyAnalysis = () => {
  const { companyNumber } = useParams();
  const history = useHistory();
  const { activeCompany } = useCompany();

  const [loading, setLoading] = useState(true);
  const [companyData, setCompanyData] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [intelligence, setIntelligence] = useState(null);
  const [intelligenceLoading, setIntelligenceLoading] = useState(false);
  const [intelligenceError, setIntelligenceError] = useState(null);
  const [generatingReport, setGeneratingReport] = useState(false);
  const [reportSuccess, setReportSuccess] = useState(null);

  useEffect(() => {
    loadCompanyData();
    loadIntelligence();
  }, [companyNumber, activeCompany]);

  const loadCompanyData = async () => {
    try {
      setLoading(true);

      // Use CompanyProvider context first, fallback to URL param
      if (activeCompany && activeCompany.companyNumber === companyNumber) {
        setCompanyData(activeCompany);
      } else if (activeCompany) {
        // Active company exists but doesn't match URL - use active company
        setCompanyData(activeCompany);
      } else {
        // No active company - show minimal data
        setCompanyData({
          companyNumber: companyNumber,
          companyName: 'Unknown Company',
        });
      }
    } catch (err) {
      console.error('Failed to load company data:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadIntelligence = async (forceRefresh = false) => {
    setIntelligenceLoading(true);
    setIntelligenceError(null);

    try {
      const data = await fetchCompanyIntelligence(companyNumber, forceRefresh);
      setIntelligence(data);
    } catch (err) {
      console.error('Error fetching company intelligence:', err);
      setIntelligenceError(err.message || 'Failed to load company intelligence');
    } finally {
      setIntelligenceLoading(false);
    }
  };

  const handleGenerateReport = async () => {
    setGeneratingReport(true);
    setReportSuccess(null);
    setIntelligenceError(null);

    try {
      const result = await generateAMLReport(companyNumber);
      setReportSuccess(result);
    } catch (err) {
      console.error('Error generating AML report:', err);
      setIntelligenceError(err.message || 'Failed to generate AML report');
    } finally {
      setGeneratingReport(false);
    }
  };

  // Compact Risk Card Component (smaller, denser)
  const CompactRiskCard = ({ title, value, status, statusColor }) => {
    return (
      <div
        style={{
          backgroundColor: 'white',
          border: '1px solid #e5e7eb',
          borderRadius: '8px',
          padding: '16px',
          height: '120px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          boxShadow: '0 1px 2px rgba(0, 0, 0, 0.05)',
        }}
      >
        <div style={{ fontSize: '13px', fontWeight: '600', color: '#6b7280', marginBottom: '8px' }}>{title}</div>
        <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#2c7873', marginBottom: '8px' }}>{value}</div>
        <div
          style={{
            padding: '4px 12px',
            borderRadius: '12px',
            fontSize: '11px',
            fontWeight: '600',
            color: 'white',
            backgroundColor: statusColor,
            textTransform: 'uppercase',
            letterSpacing: '0.3px',
            textAlign: 'center',
          }}
        >
          {status}
        </div>
      </div>
    );
  };

  // Get status color based on risk level or findings
  const getRiskColor = (riskLevel) => {
    switch (riskLevel?.toUpperCase()) {
      case 'HIGH':
      case 'CRITICAL':
        return '#dc3545';
      case 'MEDIUM':
      case 'ELEVATED':
        return '#fd7e14';
      case 'LOW':
      case 'MINIMAL':
        return '#28a745';
      default:
        return '#6c757d';
    }
  };

  const getStatusColor = (hasFindings, requiresReview) => {
    if (requiresReview || hasFindings) {
      return '#fd7e14';
    }
    return '#28a745';
  };

  const renderOverview = () => (
    <SpaceBetween size="l">
      {/* Risk Summary Cards - Compact */}
      {intelligenceLoading ? (
        <Box textAlign="center" padding="l">
          <Spinner size="normal" />
          <Box variant="small" padding={{ top: 's' }}>
            Loading risk assessment...
          </Box>
        </Box>
      ) : intelligence ? (
        <Container header={<Header variant="h3">Risk Assessment Summary</Header>}>
          <ColumnLayout columns={4} variant="text-grid">
            <CompactRiskCard
              title="Overall Risk"
              value={intelligence.risk_assessment?.risk_level || 'Unknown'}
              status={intelligence.risk_assessment?.risk_level || 'Unknown'}
              statusColor={getRiskColor(intelligence.risk_assessment?.risk_level)}
            />
            <CompactRiskCard
              title="Adverse Media"
              value={intelligence.reputational?.adverse_media_count || 0}
              status={intelligence.reputational?.has_adverse_media ? 'REVIEW' : 'CLEAN'}
              statusColor={getStatusColor(
                intelligence.reputational?.has_adverse_media,
                intelligence.reputational?.adverse_media_risk === 'high',
              )}
            />
            <CompactRiskCard
              title="Director Screening"
              value={
                (intelligence.aml?.sanctioned_directors?.length || 0) + (intelligence.aml?.pep_directors?.length || 0)
              }
              status={intelligence.aml?.requires_enhanced_dd ? 'ENHANCED DD' : 'CLEAN'}
              statusColor={getStatusColor(
                intelligence.aml?.sanctioned_directors?.length > 0 || intelligence.aml?.pep_directors?.length > 0,
                intelligence.aml?.requires_enhanced_dd,
              )}
            />
            <CompactRiskCard
              title="Company Status"
              value={intelligence.governance?.company_status || 'Unknown'}
              status={intelligence.governance?.company_status === 'active' ? 'ACTIVE' : 'INACTIVE'}
              statusColor={intelligence.governance?.company_status === 'active' ? '#28a745' : '#fd7e14'}
            />
          </ColumnLayout>
        </Container>
      ) : intelligenceError ? (
        <Alert type="warning" header="Risk Assessment Unavailable">
          {intelligenceError}
        </Alert>
      ) : null}

      {/* Existing Company Data Section */}
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
    </SpaceBetween>
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

  const renderAMLReport = () => (
    <SpaceBetween size="l">
      {/* Alert Messages */}
      {intelligenceError && (
        <Alert type="error" dismissible onDismiss={() => setIntelligenceError(null)}>
          {intelligenceError}
        </Alert>
      )}

      {reportSuccess && (
        <Alert
          type="success"
          dismissible
          onDismiss={() => setReportSuccess(null)}
          action={
            reportSuccess.downloadUrl && (
              <Button href={reportSuccess.downloadUrl} iconAlign="right" iconName="external" target="_blank">
                Download Report
              </Button>
            )
          }
        >
          {reportSuccess.message || 'AML report generated successfully'}
        </Alert>
      )}

      {intelligenceLoading ? (
        <Box textAlign="center" padding="xxl">
          <Spinner size="large" />
          <Box variant="p" padding={{ top: 's' }}>
            Loading AML intelligence...
          </Box>
        </Box>
      ) : intelligence?.insights ? (
        <>
          {/* Key Metrics Summary */}
          <Container header={<Header variant="h3">Analysis Summary</Header>}>
            <ColumnLayout columns={4} variant="text-grid">
              <CompactRiskCard
                title="Red Flags"
                value={intelligence.insights.red_flags?.length || 0}
                status={
                  intelligence.insights.red_flags?.length > 0
                    ? `${intelligence.insights.red_flags.length} FOUND`
                    : 'NONE'
                }
                statusColor={intelligence.insights.red_flags?.length > 0 ? '#dc3545' : '#28a745'}
              />
              <CompactRiskCard
                title="Recommendations"
                value={intelligence.insights.recommendations?.length || 0}
                status={intelligence.insights.recommendations?.length > 0 ? 'REVIEW' : 'NONE'}
                statusColor={intelligence.insights.recommendations?.length > 0 ? '#0972d3' : '#6c757d'}
              />
              <CompactRiskCard
                title="Mitigating Factors"
                value={intelligence.insights.mitigating_factors?.length || 0}
                status={intelligence.insights.mitigating_factors?.length > 0 ? 'PRESENT' : 'NONE'}
                statusColor={intelligence.insights.mitigating_factors?.length > 0 ? '#037f0c' : '#6c757d'}
              />
              <CompactRiskCard
                title="Enhanced DD"
                value={intelligence.aml?.requires_enhanced_dd ? 'REQUIRED' : 'NOT REQUIRED'}
                status={intelligence.aml?.requires_enhanced_dd ? 'ACTION' : 'STANDARD'}
                statusColor={intelligence.aml?.requires_enhanced_dd ? '#fd7e14' : '#28a745'}
              />
            </ColumnLayout>
          </Container>

          {/* Detailed Insights */}
          <Container header={<Header variant="h3">Detailed Intelligence</Header>}>
            <SpaceBetween size="m">
              {/* Overall Summary */}
              {intelligence.insights.overall_summary && (
                <Box>
                  <Box variant="h4" padding={{ bottom: 'xs' }}>
                    Overall Summary
                  </Box>
                  <Box variant="p">{intelligence.insights.overall_summary}</Box>
                </Box>
              )}

              {/* Red Flags */}
              {intelligence.insights.red_flags && intelligence.insights.red_flags.length > 0 && (
                <Box>
                  <Box variant="h4" padding={{ bottom: 'xs' }}>
                    Red Flags ({intelligence.insights.red_flags.length})
                  </Box>
                  <ul style={{ margin: 0, paddingLeft: '20px' }}>
                    {intelligence.insights.red_flags.map((flag, index) => (
                      <li key={index} style={{ marginBottom: '8px', color: '#d13212' }}>
                        {flag}
                      </li>
                    ))}
                  </ul>
                </Box>
              )}

              {/* Recommendations */}
              {intelligence.insights.recommendations && intelligence.insights.recommendations.length > 0 && (
                <Box>
                  <Box variant="h4" padding={{ bottom: 'xs' }}>
                    Recommendations ({intelligence.insights.recommendations.length})
                  </Box>
                  <ul style={{ margin: 0, paddingLeft: '20px' }}>
                    {intelligence.insights.recommendations.map((rec, index) => (
                      <li key={index} style={{ marginBottom: '8px', color: '#0972d3' }}>
                        {rec}
                      </li>
                    ))}
                  </ul>
                </Box>
              )}

              {/* Mitigating Factors */}
              {intelligence.insights.mitigating_factors && intelligence.insights.mitigating_factors.length > 0 && (
                <Box>
                  <Box variant="h4" padding={{ bottom: 'xs' }}>
                    Mitigating Factors ({intelligence.insights.mitigating_factors.length})
                  </Box>
                  <ul style={{ margin: 0, paddingLeft: '20px' }}>
                    {intelligence.insights.mitigating_factors.map((factor, index) => (
                      <li key={index} style={{ marginBottom: '8px', color: '#037f0c' }}>
                        {factor}
                      </li>
                    ))}
                  </ul>
                </Box>
              )}
            </SpaceBetween>
          </Container>

          {/* Category Insights */}
          <Container header={<Header variant="h3">Category Analysis</Header>}>
            <SpaceBetween size="m">
              {intelligence.insights.governance_insight && (
                <Box>
                  <Box variant="h4" padding={{ bottom: 'xs' }}>
                    Governance
                  </Box>
                  <Box variant="p">{intelligence.insights.governance_insight}</Box>
                </Box>
              )}

              {intelligence.insights.aml_insight && (
                <Box>
                  <Box variant="h4" padding={{ bottom: 'xs' }}>
                    AML/Sanctions
                  </Box>
                  <Box variant="p">{intelligence.insights.aml_insight}</Box>
                </Box>
              )}

              {intelligence.insights.reputational_insight && (
                <Box>
                  <Box variant="h4" padding={{ bottom: 'xs' }}>
                    Reputational
                  </Box>
                  <Box variant="p">{intelligence.insights.reputational_insight}</Box>
                </Box>
              )}

              {intelligence.insights.financial_insight && (
                <Box>
                  <Box variant="h4" padding={{ bottom: 'xs' }}>
                    Financial
                  </Box>
                  <Box variant="p">{intelligence.insights.financial_insight}</Box>
                </Box>
              )}
            </SpaceBetween>
          </Container>

          {/* Generate Report Button */}
          <Box textAlign="center">
            <Button
              variant="primary"
              onClick={handleGenerateReport}
              disabled={generatingReport}
              loading={generatingReport}
              iconName="download"
            >
              {generatingReport ? 'Generating Report...' : 'Generate Full AML Report'}
            </Button>
          </Box>
        </>
      ) : (
        <Alert type="info" header="AML Intelligence Not Available">
          <Box>
            No AML intelligence data available for this company. Please ensure company data has been collected and
            analyzed first.
          </Box>
        </Alert>
      )}
    </SpaceBetween>
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
          { text: companyData?.companyName || companyNumber, href: '#' },
        ]}
        ariaLabel="Breadcrumbs"
      />

      <Header variant="h1" description={`Company Number: ${companyNumber}`}>
        Company Analysis: {companyData?.companyName || 'Loading...'}
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
          {
            id: 'aml_report',
            label: 'AML Report',
            content: renderAMLReport(),
          },
        ]}
      />
    </SpaceBetween>
  );
};

export default CompanyAnalysis;
