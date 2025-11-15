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
  Spinner,
  BreadcrumbGroup,
  Button,
  ExpandableSection,
} from '@awsui/components-react';

import { useCompany } from '../../contexts/company';
import { COMPANY_SELECT_PATH } from '../../routes/constants';
import { fetchCompanyIntelligence, generateAMLReport } from '../../services/analysisStack';
import MarkdownViewer from '../document-viewer/MarkdownViewer';

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
 *
 * @param {boolean} embedded - If true, hides breadcrumbs and header (for use within tabs)
 */
const ClientTakeOnAnalysis = ({ embedded = false }) => {
  const history = useHistory();
  const { activeCompany, isCompanySelected } = useCompany();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [generatingReport, setGeneratingReport] = useState(false);
  const [reportSuccess, setReportSuccess] = useState(null);
  const [intelligence, setIntelligence] = useState(null);
  const [reportMarkdown, setReportMarkdown] = useState(null);
  const [isLoadingMarkdown, setIsLoadingMarkdown] = useState(false);

  // Fetch markdown content when reportSuccess changes
  useEffect(() => {
    const fetchMarkdown = async () => {
      if (!reportSuccess?.downloadUrl) {
        setReportMarkdown(null);
        return;
      }

      try {
        setIsLoadingMarkdown(true);
        console.log('Fetching report markdown from:', reportSuccess.downloadUrl);

        const response = await fetch(reportSuccess.downloadUrl);
        if (!response.ok) {
          throw new Error(`Failed to fetch report: ${response.statusText}`);
        }

        const markdown = await response.text();
        setReportMarkdown(markdown);
        console.log('Report markdown loaded successfully');
      } catch (err) {
        console.error('Error fetching report markdown:', err);
        setError(`Failed to load report content: ${err.message}`);
      } finally {
        setIsLoadingMarkdown(false);
      }
    };

    fetchMarkdown();
  }, [reportSuccess]);

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
    setReportMarkdown(null);
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
      {!embedded && (
        <>
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
        </>
      )}

      {embedded && (
        <Header
          variant="h2"
          description="Risks identified in client take on process"
          actions={
            <Button onClick={() => fetchIntelligence(true)} disabled={loading} iconName="refresh">
              Refresh Analysis
            </Button>
          }
        >
          Client Take-On Analysis
        </Header>
      )}

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
                {/* Top Section: Overall Risk - Full Width */}
                <RiskCard
                  title="Overall Risk Assessment"
                  value={intelligence.risk_assessment?.risk_level || 'Unknown'}
                  subtitle={`Risk Score: ${intelligence.risk_assessment?.overall_risk_score || 'N/A'}`}
                  status={intelligence.risk_assessment?.risk_level || 'Unknown'}
                  statusColor={getRiskColor(intelligence.risk_assessment?.risk_level)}
                  large={true}
                />

                {/* Screening Cards - 3 Column Grid */}
                <Container header={<Header variant="h2">Screening Results</Header>}>
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
                        intelligence.aml?.sanctioned_directors?.length > 0 ||
                          intelligence.aml?.pep_directors?.length > 0,
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
                </Container>

                {/* Key Metrics Summary Cards */}
                {intelligence.insights && (
                  <Container header={<Header variant="h2">Analysis Summary</Header>}>
                    <div
                      style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
                        gap: '20px',
                      }}
                    >
                      {/* Red Flags Count */}
                      <RiskCard
                        title="Red Flags"
                        value={intelligence.insights.red_flags?.length || 0}
                        subtitle="Critical Issues"
                        status={
                          intelligence.insights.red_flags?.length > 0
                            ? `${intelligence.insights.red_flags.length} FOUND`
                            : 'NONE'
                        }
                        statusColor={intelligence.insights.red_flags?.length > 0 ? '#dc3545' : '#28a745'}
                      />

                      {/* Recommendations Count */}
                      <RiskCard
                        title="Recommendations"
                        value={intelligence.insights.recommendations?.length || 0}
                        subtitle="Action Items"
                        status={intelligence.insights.recommendations?.length > 0 ? 'REVIEW' : 'NONE'}
                        statusColor={intelligence.insights.recommendations?.length > 0 ? '#0972d3' : '#6c757d'}
                      />

                      {/* Mitigating Factors */}
                      <RiskCard
                        title="Mitigating Factors"
                        value={intelligence.insights.mitigating_factors?.length || 0}
                        subtitle="Positive Indicators"
                        status={intelligence.insights.mitigating_factors?.length > 0 ? 'PRESENT' : 'NONE'}
                        statusColor={intelligence.insights.mitigating_factors?.length > 0 ? '#037f0c' : '#6c757d'}
                      />

                      {/* Enhanced DD Required */}
                      <RiskCard
                        title="Enhanced Due Diligence"
                        value={intelligence.aml?.requires_enhanced_dd ? 'REQUIRED' : 'NOT REQUIRED'}
                        subtitle="AML Compliance"
                        status={intelligence.aml?.requires_enhanced_dd ? 'ACTION NEEDED' : 'STANDARD'}
                        statusColor={intelligence.aml?.requires_enhanced_dd ? '#fd7e14' : '#28a745'}
                      />
                    </div>
                  </Container>
                )}

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
                      documentName={`AML_Report_${activeCompany.companyNumber}`}
                      title={`AML Report - ${reportSuccess?.companyName || activeCompany.companyName}`}
                    />
                  </Box>
                )}

                {/* Detailed Intelligence Insights - Expandable Sections */}
                {intelligence.insights && (
                  <Container header={<Header variant="h2">Detailed Analysis</Header>}>
                    <SpaceBetween size="m">
                      {/* Overall Summary */}
                      {intelligence.insights.overall_summary && (
                        <ExpandableSection headerText="Overall Summary" variant="container">
                          <Box variant="p">{intelligence.insights.overall_summary}</Box>
                        </ExpandableSection>
                      )}

                      {/* Red Flags - Expandable */}
                      {intelligence.insights.red_flags && intelligence.insights.red_flags.length > 0 && (
                        <ExpandableSection
                          headerText={`Red Flags (${intelligence.insights.red_flags.length})`}
                          variant="container"
                        >
                          <ul style={{ margin: 0, paddingLeft: '20px' }}>
                            {intelligence.insights.red_flags.map((flag, index) => (
                              <li key={index} style={{ marginBottom: '8px', color: '#d13212' }}>
                                {flag}
                              </li>
                            ))}
                          </ul>
                        </ExpandableSection>
                      )}

                      {/* Recommendations - Expandable */}
                      {intelligence.insights.recommendations && intelligence.insights.recommendations.length > 0 && (
                        <ExpandableSection
                          headerText={`Recommendations (${intelligence.insights.recommendations.length})`}
                          variant="container"
                        >
                          <ul style={{ margin: 0, paddingLeft: '20px' }}>
                            {intelligence.insights.recommendations.map((rec, index) => (
                              <li key={index} style={{ marginBottom: '8px', color: '#0972d3' }}>
                                {rec}
                              </li>
                            ))}
                          </ul>
                        </ExpandableSection>
                      )}

                      {/* Mitigating Factors - Expandable */}
                      {intelligence.insights.mitigating_factors &&
                        intelligence.insights.mitigating_factors.length > 0 && (
                          <ExpandableSection
                            headerText={`Mitigating Factors (${intelligence.insights.mitigating_factors.length})`}
                            variant="container"
                          >
                            <ul style={{ margin: 0, paddingLeft: '20px' }}>
                              {intelligence.insights.mitigating_factors.map((factor, index) => (
                                <li key={index} style={{ marginBottom: '8px', color: '#037f0c' }}>
                                  {factor}
                                </li>
                              ))}
                            </ul>
                          </ExpandableSection>
                        )}

                      {/* Governance Insight */}
                      {intelligence.insights.governance_insight && (
                        <ExpandableSection headerText="Governance Analysis" variant="container">
                          <Box variant="p">{intelligence.insights.governance_insight}</Box>
                        </ExpandableSection>
                      )}

                      {/* AML Insight */}
                      {intelligence.insights.aml_insight && (
                        <ExpandableSection headerText="AML/Sanctions Analysis" variant="container">
                          <Box variant="p">{intelligence.insights.aml_insight}</Box>
                        </ExpandableSection>
                      )}

                      {/* Reputational Insight */}
                      {intelligence.insights.reputational_insight && (
                        <ExpandableSection headerText="Reputational Analysis" variant="container">
                          <Box variant="p">{intelligence.insights.reputational_insight}</Box>
                        </ExpandableSection>
                      )}

                      {/* Financial Insight */}
                      {intelligence.insights.financial_insight && (
                        <ExpandableSection headerText="Financial Analysis" variant="container">
                          <Box variant="p">{intelligence.insights.financial_insight}</Box>
                        </ExpandableSection>
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
