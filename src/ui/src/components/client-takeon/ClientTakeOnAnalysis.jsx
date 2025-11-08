// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
import React, { useState, useEffect } from 'react';
import { useHistory } from 'react-router-dom';
import { Container, Header, SpaceBetween, Alert, Box, Spinner, BreadcrumbGroup, Button } from '@awsui/components-react';

import { useCompany } from '../../contexts/company';
import { COMPANY_SELECT_PATH } from '../../routes/constants';
import { fetchCompanyIntelligence, generateAMLReport } from '../../services/analysisStack';

import '@awsui/global-styles/index.css';

/**
 * Client Take-On Analysis Component
 *
 * Provides comprehensive analysis for new client onboarding including:
 * - Overall risk assessment
 * - Company adverse media screening
 * - Director sanctions and PEP screening
 * - Company status and governance checks
 * - AML report generation
 */
const ClientTakeOnAnalysis = () => {
  const history = useHistory();
  const { activeCompany, isCompanySelected } = useCompany();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [generatingReport, setGeneratingReport] = useState(false);
  const [reportSuccess, setReportSuccess] = useState(null);
  const [intelligence, setIntelligence] = useState(null);

  useEffect(() => {
    // Redirect if no company selected
    if (!isCompanySelected) {
      history.push(COMPANY_SELECT_PATH);
      return;
    }

    // Fetch intelligence data
    if (activeCompany?.companyNumber) {
      fetchIntelligence();
    }
  }, [isCompanySelected, activeCompany?.companyNumber, history]);

  const fetchIntelligence = async (forceRefresh = false) => {
    setLoading(true);
    setError(null);

    try {
      const data = await fetchCompanyIntelligence(activeCompany.companyNumber, forceRefresh);
      setIntelligence(data);
    } catch (err) {
      console.error('Error fetching company intelligence:', err);
      setError(err.message || 'Failed to load company intelligence');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateReport = async () => {
    setGeneratingReport(true);
    setReportSuccess(null);
    setError(null);

    try {
      const result = await generateAMLReport(activeCompany.companyNumber);
      setReportSuccess(result);
    } catch (err) {
      console.error('Error generating AML report:', err);
      setError(err.message || 'Failed to generate AML report');
    } finally {
      setGeneratingReport(false);
    }
  };

  // Risk Assessment Card Component
  const RiskCard = ({ title, value, subtitle, status, statusColor, large = false }) => {
    return (
      <div
        style={{
          backgroundColor: 'white',
          border: '1px solid #e5e7eb',
          borderRadius: '12px',
          padding: large ? '32px 24px' : '24px 20px',
          height: large ? '220px' : '180px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
          textAlign: 'center',
        }}
      >
        {/* Title */}
        <div
          style={{
            fontSize: '18px',
            fontWeight: '600',
            color: '#374151',
            marginBottom: '16px',
          }}
        >
          {title}
        </div>

        {/* Main Value */}
        <div
          style={{
            fontSize: large ? '32px' : '28px',
            fontWeight: 'bold',
            color: '#2c7873',
            marginBottom: '12px',
            lineHeight: '1.1',
          }}
        >
          {value}
        </div>

        {/* Subtitle */}
        {subtitle && (
          <div
            style={{
              fontSize: '14px',
              color: '#6b7280',
              marginBottom: '12px',
            }}
          >
            {subtitle}
          </div>
        )}

        {/* Status Badge */}
        <div
          style={{
            padding: '6px 16px',
            borderRadius: '20px',
            fontSize: '12px',
            fontWeight: '600',
            color: 'white',
            backgroundColor: statusColor,
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
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
      return '#fd7e14'; // Orange for review required
    }
    return '#28a745'; // Green for clean
  };

  if (!activeCompany) {
    return null;
  }

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
        description="Risks identified in client take on process"
        actions={
          <Button onClick={() => fetchIntelligence(true)} disabled={loading} iconName="refresh">
            Refresh Analysis
          </Button>
        }
      >
        Client Take-On Analysis
      </Header>

      <Container>
        <SpaceBetween size="l">
          {error && (
            <Alert type="error" dismissible onDismiss={() => setError(null)}>
              {error}
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

          {/* Company Name Section with Accent Bar */}
          {activeCompany && !loading && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                marginBottom: '24px',
              }}
            >
              <div
                style={{
                  width: '4px',
                  height: '40px',
                  backgroundColor: '#2c7873',
                  marginRight: '16px',
                }}
              />
              <div
                style={{
                  fontSize: '24px',
                  fontWeight: '600',
                  color: '#2c7873',
                }}
              >
                {activeCompany.companyName}
              </div>
            </div>
          )}

          {loading ? (
            <Box textAlign="center" padding={{ top: 'xl', bottom: 'xl' }}>
              <Spinner size="large" />
              <Box variant="p" padding={{ top: 's' }}>
                Loading client take-on analysis...
              </Box>
            </Box>
          ) : intelligence ? (
            <>
              {/* Risk Assessment Cards */}
              <SpaceBetween size="l">
                {/* Overall Risk Card - Full Width */}
                <Container>
                  <RiskCard
                    title="Overall Risk Assessment"
                    value={intelligence.risk_assessment?.risk_level || 'Unknown'}
                    subtitle={`Risk Score: ${intelligence.risk_assessment?.overall_risk_score || 'N/A'}`}
                    status={intelligence.risk_assessment?.risk_level || 'Unknown'}
                    statusColor={getRiskColor(intelligence.risk_assessment?.risk_level)}
                    large={true}
                  />
                </Container>

                {/* Screening Cards - 3 Column Grid */}
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
                    gap: '24px',
                  }}
                >
                  {/* Company Adverse Media */}
                  <RiskCard
                    title="Company Adverse Media"
                    value={intelligence.reputational?.adverse_media_count || 0}
                    subtitle="Adverse Findings"
                    status={intelligence.reputational?.has_adverse_media ? 'REVIEW REQUIRED' : 'CLEAN'}
                    statusColor={getStatusColor(
                      intelligence.reputational?.has_adverse_media,
                      intelligence.reputational?.adverse_media_risk === 'high',
                    )}
                  />

                  {/* Director Sanctions/PEP */}
                  <RiskCard
                    title="Director Screening"
                    value={
                      (intelligence.aml?.sanctioned_directors?.length || 0) +
                      (intelligence.aml?.pep_directors?.length || 0)
                    }
                    subtitle="Sanctions & PEP Findings"
                    status={intelligence.aml?.requires_enhanced_dd ? 'ENHANCED DD REQUIRED' : 'CLEAN'}
                    statusColor={getStatusColor(
                      intelligence.aml?.sanctioned_directors?.length > 0 || intelligence.aml?.pep_directors?.length > 0,
                      intelligence.aml?.requires_enhanced_dd,
                    )}
                  />

                  {/* Company Status/Governance */}
                  <RiskCard
                    title="Company Status"
                    value={intelligence.governance?.company_status || 'Unknown'}
                    subtitle={`${intelligence.governance?.active_officers || 0} Active Officers`}
                    status={
                      intelligence.governance?.company_status === 'active'
                        ? 'ACTIVE'
                        : intelligence.governance?.company_status?.toUpperCase() || 'UNKNOWN'
                    }
                    statusColor={intelligence.governance?.company_status === 'active' ? '#28a745' : '#fd7e14'}
                  />
                </div>

                {/* Generate AML Report Button */}
                <Box textAlign="center" margin={{ top: 'xl' }}>
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

                {/* Additional Intelligence Insights */}
                {intelligence.insights && (
                  <Container header={<Header variant="h2">AI-Generated Insights</Header>}>
                    <SpaceBetween size="m">
                      {/* Overall Summary */}
                      {intelligence.insights.overall_summary && (
                        <Box>
                          <Box variant="h3" padding={{ bottom: 'xs' }}>Overall Summary</Box>
                          <Box variant="p">{intelligence.insights.overall_summary}</Box>
                        </Box>
                      )}

                      {/* Governance Insight */}
                      {intelligence.insights.governance_insight && (
                        <Box>
                          <Box variant="h3" padding={{ bottom: 'xs' }}>Governance Analysis</Box>
                          <Box variant="p">{intelligence.insights.governance_insight}</Box>
                        </Box>
                      )}

                      {/* AML Insight */}
                      {intelligence.insights.aml_insight && (
                        <Box>
                          <Box variant="h3" padding={{ bottom: 'xs' }}>AML/Sanctions Analysis</Box>
                          <Box variant="p">{intelligence.insights.aml_insight}</Box>
                        </Box>
                      )}

                      {/* Reputational Insight */}
                      {intelligence.insights.reputational_insight && (
                        <Box>
                          <Box variant="h3" padding={{ bottom: 'xs' }}>Reputational Analysis</Box>
                          <Box variant="p">{intelligence.insights.reputational_insight}</Box>
                        </Box>
                      )}

                      {/* Financial Insight */}
                      {intelligence.insights.financial_insight && (
                        <Box>
                          <Box variant="h3" padding={{ bottom: 'xs' }}>Financial Analysis</Box>
                          <Box variant="p">{intelligence.insights.financial_insight}</Box>
                        </Box>
                      )}

                      {/* Red Flags */}
                      {intelligence.insights.red_flags && intelligence.insights.red_flags.length > 0 && (
                        <Box>
                          <Box variant="h3" padding={{ bottom: 'xs' }}>Red Flags</Box>
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
                          <Box variant="h3" padding={{ bottom: 'xs' }}>Recommendations</Box>
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
                          <Box variant="h3" padding={{ bottom: 'xs' }}>Mitigating Factors</Box>
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
                )}
              </SpaceBetween>
            </>
          ) : (
            <Box textAlign="center" padding={{ vertical: 'xl' }}>
              <Box variant="p" color="text-body-secondary">
                No intelligence data available for this company. Please ensure company data has been collected first.
              </Box>
            </Box>
          )}
        </SpaceBetween>
      </Container>
    </SpaceBetween>
  );
};

export default ClientTakeOnAnalysis;
