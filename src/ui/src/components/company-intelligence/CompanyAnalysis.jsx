// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
import React, { useState, useEffect, useCallback, useMemo } from 'react';
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
  ProgressBar,
  StatusIndicator,
  Table,
  TextContent,
} from '@awsui/components-react';

import { COMPANY_SELECT_PATH } from '../../routes/constants';
import { useCompany } from '../../contexts/company';
import { fetchCompanyIntelligence, generateAMLReport } from '../../services/analysisStack';
import { lookupCompany, checkFilingHistory, lookupOfficers } from '../../services/dataCollection';
import AppLayoutWrapper from '../app-layout-wrapper';
import MarkdownViewer from '../document-viewer/MarkdownViewer';

import '@awsui/global-styles/index.css';

const formatDate = (value) => {
  if (!value) {
    return 'N/A';
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toLocaleDateString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
};

const formatDateTime = (value) => {
  if (!value) {
    return 'N/A';
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toLocaleString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

const formatAddress = (address = {}) => {
  const parts = [
    address.address_line_1,
    address.address_line_2,
    address.locality,
    address.region,
    address.postal_code,
    address.country,
  ].filter(Boolean);

  return parts.length ? parts.join(', ') : 'N/A';
};

const CompanyAnalysis = () => {
  const { companyNumber } = useParams();
  const history = useHistory();
  const { activeCompany } = useCompany();

  const [loading, setLoading] = useState(true);
  const [companyData, setCompanyData] = useState(null);
  const [companyProfile, setCompanyProfile] = useState(null);
  const [companyProfileLoading, setCompanyProfileLoading] = useState(false);
  const [companyProfileError, setCompanyProfileError] = useState(null);
  const [filingHistory, setFilingHistory] = useState(null);
  const [filingLoading, setFilingLoading] = useState(false);
  const [filingError, setFilingError] = useState(null);
  const [officersData, setOfficersData] = useState(null);
  const [officersLoading, setOfficersLoading] = useState(false);
  const [officersError, setOfficersError] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [intelligence, setIntelligence] = useState(null);
  const [intelligenceLoading, setIntelligenceLoading] = useState(false);
  const [intelligenceError, setIntelligenceError] = useState(null);
  const [generatingReport, setGeneratingReport] = useState(false);
  const [reportSuccess, setReportSuccess] = useState(null);
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
        setIntelligenceError(`Failed to load report content: ${err.message}`);
      } finally {
        setIsLoadingMarkdown(false);
      }
    };

    fetchMarkdown();
  }, [reportSuccess]);

  const loadCompanyData = useCallback(async () => {
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
  }, [activeCompany, companyNumber]);

  const loadCompanyProfile = useCallback(
    async (forceRefresh = false) => {
      if (!companyNumber) {
        return;
      }

      setCompanyProfileLoading(true);
      setCompanyProfileError(null);

      try {
        const profile = await lookupCompany(companyNumber, { refresh: forceRefresh });
        setCompanyProfile(profile);
      } catch (err) {
        console.error('Failed to load company profile:', err);
        setCompanyProfile(null);
        setCompanyProfileError(err.message || 'Failed to load company profile.');
      } finally {
        setCompanyProfileLoading(false);
      }
    },
    [companyNumber],
  );

  const loadFilingHistory = useCallback(
    async (forceRefresh = false) => {
      if (!companyNumber) {
        return;
      }

      setFilingLoading(true);
      setFilingError(null);

      try {
        const historyResponse = await checkFilingHistory(companyNumber, {
          refresh: forceRefresh,
          summary: false,
        });
        setFilingHistory(historyResponse);
      } catch (err) {
        console.error('Failed to load filing history:', err);
        setFilingHistory(null);
        setFilingError(err.message || 'Failed to load filing history.');
      } finally {
        setFilingLoading(false);
      }
    },
    [companyNumber],
  );

  const loadOfficers = useCallback(
    async (forceRefresh = false) => {
      if (!companyNumber) {
        return;
      }

      setOfficersLoading(true);
      setOfficersError(null);

      try {
        const officersResponse = await lookupOfficers(companyNumber, { refresh: forceRefresh });
        setOfficersData(officersResponse);
      } catch (err) {
        console.error('Failed to load officers data:', err);
        setOfficersData(null);
        setOfficersError(err.message || 'Failed to load officers data.');
      } finally {
        setOfficersLoading(false);
      }
    },
    [companyNumber],
  );

  const loadIntelligence = useCallback(
    async (forceRefresh = false) => {
      if (!companyNumber) {
        return;
      }

      setIntelligenceLoading(true);
      setIntelligenceError(null);

      try {
        const data = await fetchCompanyIntelligence(companyNumber, forceRefresh);
        setIntelligence(data);
      } catch (err) {
        console.error('Error fetching company intelligence:', err);
        setIntelligence(null);
        setIntelligenceError(err.message || 'Failed to load company intelligence.');
      } finally {
        setIntelligenceLoading(false);
      }
    },
    [companyNumber],
  );

  useEffect(() => {
    loadCompanyData();
  }, [loadCompanyData]);

  useEffect(() => {
    if (!companyNumber) {
      return;
    }

    loadCompanyProfile();
    loadFilingHistory();
    loadOfficers();
    loadIntelligence();
  }, [companyNumber, loadCompanyProfile, loadFilingHistory, loadOfficers, loadIntelligence]);

  const handleRefreshAll = async () => {
    await Promise.allSettled([
      loadCompanyProfile(true),
      loadFilingHistory(true),
      loadOfficers(true),
      loadIntelligence(true),
    ]);
  };

  const handleGenerateReport = async () => {
    setGeneratingReport(true);
    setReportSuccess(null);
    setReportMarkdown(null);
    setIntelligenceError(null);

    try {
      const result = await generateAMLReport(companyNumber);
      setReportSuccess(result);
      await loadIntelligence(true);
    } catch (err) {
      console.error('Error generating AML report:', err);
      setIntelligenceError(err.message || 'Failed to generate AML report');
    } finally {
      setGeneratingReport(false);
    }
  };

  const officerRows = useMemo(() => {
    if (!officersData) {
      return [];
    }

    const active = (officersData.active_officers || []).map((officer) => ({
      ...officer,
      status: 'active',
    }));
    const resigned = (officersData.resigned_officers || []).map((officer) => ({
      ...officer,
      status: 'resigned',
    }));

    return [...active, ...resigned];
  }, [officersData]);

  const sanitizedSanctionedNames = useMemo(() => {
    const names = intelligence?.aml?.sanctioned_directors || [];
    return new Set(names.map((name) => name?.toLowerCase?.() || ''));
  }, [intelligence]);

  const sanitizedPepNames = useMemo(() => {
    const names = intelligence?.aml?.pep_directors || [];
    return new Set(names.map((name) => name?.toLowerCase?.() || ''));
  }, [intelligence]);

  const companyDisplayName =
    companyProfile?.company_name || companyData?.companyName || companyData?.company_name || companyNumber;

  const isRefreshing =
    companyProfileLoading || filingLoading || officersLoading || intelligenceLoading || generatingReport;

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

  const renderRiskSummary = () => {
    if (intelligenceLoading) {
      return (
        <Box textAlign="center" padding="l">
          <Spinner size="normal" />
          <Box variant="small" padding={{ top: 's' }}>
            Loading risk assessment...
          </Box>
        </Box>
      );
    }

    if (intelligence) {
      return (
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
              statusColor={intelligence.reputational?.has_adverse_media ? '#fd7e14' : '#28a745'}
            />
            <CompactRiskCard
              title="Director Screening"
              value={
                (intelligence.aml?.sanctioned_directors?.length || 0) + (intelligence.aml?.pep_directors?.length || 0)
              }
              status={intelligence.aml?.requires_enhanced_dd ? 'ENHANCED DD' : 'CLEAN'}
              statusColor={intelligence.aml?.requires_enhanced_dd ? '#fd7e14' : '#28a745'}
            />
            <CompactRiskCard
              title="Company Status"
              value={intelligence.governance?.company_status || 'Unknown'}
              status={intelligence.governance?.company_status === 'active' ? 'ACTIVE' : 'INACTIVE'}
              statusColor={intelligence.governance?.company_status === 'active' ? '#28a745' : '#fd7e14'}
            />
          </ColumnLayout>
        </Container>
      );
    }

    if (intelligenceError) {
      return (
        <Alert type="warning" header="Risk Assessment Unavailable">
          {intelligenceError}
        </Alert>
      );
    }

    return null;
  };

  const renderDataCompleteness = () => {
    const hasProfile = Boolean(companyProfile?.company_number);
    const hasFiling = Boolean(filingHistory?.total_count || (filingHistory?.recent_filings || []).length);
    const hasOfficers = Boolean(
      (officersData?.active_officers || []).length + (officersData?.resigned_officers || []).length,
    );

    const sources = [hasProfile, hasFiling, hasOfficers];
    const completenessScore = Math.round((sources.filter((value) => value).length / sources.length) * 100);

    return (
      <Container header={<Header variant="h3">Companies House Data Coverage</Header>}>
        <SpaceBetween size="m">
          <ProgressBar
            value={completenessScore}
            label="Data completeness"
            status={completenessScore >= 80 ? 'success' : 'in-progress'}
            description="Availability of Companies House data sources"
          />

          <SpaceBetween size="xs" direction="horizontal">
            <StatusIndicator type={hasProfile ? 'success' : 'in-progress'}>Company profile</StatusIndicator>
            <StatusIndicator type={hasFiling ? 'success' : 'in-progress'}>Filing history</StatusIndicator>
            <StatusIndicator type={hasOfficers ? 'success' : 'in-progress'}>Officers</StatusIndicator>
          </SpaceBetween>

          <Box variant="small" color="text-body-secondary">
            {companyProfile?.last_updated && `Profile updated ${formatDateTime(companyProfile.last_updated)}`}
          </Box>
        </SpaceBetween>
      </Container>
    );
  };

  const renderCompanySnapshot = () => {
    if (companyProfileLoading && !companyProfile) {
      return (
        <Container header={<Header variant="h3">Company Snapshot</Header>}>
          <Box textAlign="center" padding="l">
            <Spinner size="normal" />
          </Box>
        </Container>
      );
    }

    if (companyProfileError && !companyProfile) {
      return (
        <Alert type="warning" header="Company profile unavailable">
          {companyProfileError}
        </Alert>
      );
    }

    if (!companyProfile) {
      return null;
    }

    const sicCodes = (companyProfile.sic_codes || []).join(', ') || 'N/A';

    return (
      <Container header={<Header variant="h3">Company Snapshot</Header>}>
        <ColumnLayout columns={2} variant="text-grid">
          <Box>
            <Box variant="awsui-key-label">Company Number</Box>
            <Box>{companyProfile.company_number}</Box>
          </Box>
          <Box>
            <Box variant="awsui-key-label">Status</Box>
            <StatusIndicator type={companyProfile.company_status === 'active' ? 'success' : 'warning'}>
              {companyProfile.company_status || 'Unknown'}
            </StatusIndicator>
          </Box>
          <Box>
            <Box variant="awsui-key-label">Company Type</Box>
            <Box>{companyProfile.company_type || 'Unknown'}</Box>
          </Box>
          <Box>
            <Box variant="awsui-key-label">Incorporated</Box>
            <Box>{formatDate(companyProfile.date_of_creation)}</Box>
          </Box>
          <Box>
            <Box variant="awsui-key-label">Jurisdiction</Box>
            <Box>{companyProfile.jurisdiction || 'N/A'}</Box>
          </Box>
          <Box>
            <Box variant="awsui-key-label">SIC Codes</Box>
            <Box>{sicCodes}</Box>
          </Box>
        </ColumnLayout>
      </Container>
    );
  };

  const renderBusinessHealth = () => {
    if (!companyProfile && !filingHistory && !intelligence) {
      return null;
    }

    const accountsOverdue =
      intelligence?.financial?.accounts_overdue ?? companyProfile?.accounts?.accounts_overdue ?? false;
    const confirmationOverdue =
      intelligence?.financial?.confirmation_statement_overdue ??
      companyProfile?.confirmation_statement_overdue ??
      false;
    const recentFilings = filingHistory?.recent_filings || [];
    const latestFiling = recentFilings.length ? recentFilings[0] : null;

    return (
      <Container header={<Header variant="h3">Business Health & Compliance</Header>}>
        <SpaceBetween size="m">
          <ColumnLayout columns={2} variant="text-grid">
            <Box>
              <Box variant="awsui-key-label">Accounts status</Box>
              <StatusIndicator type={accountsOverdue ? 'error' : 'success'}>
                {accountsOverdue ? 'Accounts overdue' : 'Accounts current'}
              </StatusIndicator>
            </Box>
            <Box>
              <Box variant="awsui-key-label">Confirmation statement</Box>
              <StatusIndicator type={confirmationOverdue ? 'error' : 'success'}>
                {confirmationOverdue ? 'Statement overdue' : 'Statement current'}
              </StatusIndicator>
            </Box>
            <Box>
              <Box variant="awsui-key-label">Total filings captured</Box>
              <Box>{filingHistory?.total_count ?? 'N/A'}</Box>
            </Box>
            <Box>
              <Box variant="awsui-key-label">Latest filing date</Box>
              <Box>{latestFiling ? formatDate(latestFiling.date || latestFiling.action_date) : 'N/A'}</Box>
            </Box>
          </ColumnLayout>

          {intelligence?.risk_assessment?.critical_flags?.length > 0 && (
            <Alert type="warning" header="Critical risk indicators">
              <ul style={{ margin: 0, paddingLeft: 20 }}>
                {intelligence.risk_assessment.critical_flags.map((flag, index) => (
                  <li key={index}>{flag.description || 'Critical flag detected'}</li>
                ))}
              </ul>
            </Alert>
          )}
        </SpaceBetween>
      </Container>
    );
  };

  const renderAddress = () => {
    if (!companyProfile?.registered_office_address) {
      return null;
    }

    return (
      <Container header={<Header variant="h3">Registered Address</Header>}>
        <Box>{formatAddress(companyProfile.registered_office_address)}</Box>
      </Container>
    );
  };

  const renderOverview = () => (
    <SpaceBetween size="l">
      {renderRiskSummary()}

      {companyProfileError && companyProfile && (
        <Alert type="warning" header="Company profile warning">
          {companyProfileError}
        </Alert>
      )}

      {filingError && filingHistory && (
        <Alert type="warning" header="Filing data warning">
          {filingError}
        </Alert>
      )}

      {officersError && officersData && (
        <Alert type="warning" header="Officers data warning">
          {officersError}
        </Alert>
      )}

      {renderDataCompleteness()}
      {renderCompanySnapshot()}
      {renderBusinessHealth()}
      {renderAddress()}
    </SpaceBetween>
  );

  const renderFilingHistory = () => (
    <Container
      header={
        <Header
          variant="h3"
          actions={
            <Button iconName="refresh" loading={filingLoading} onClick={() => loadFilingHistory(true)}>
              Refresh filing history
            </Button>
          }
        >
          Filing History Analysis
        </Header>
      }
    >
      <SpaceBetween size="m">
        {filingError && (
          <Alert type="error" header="Unable to load filing history" dismissible onDismiss={() => setFilingError(null)}>
            {filingError}
          </Alert>
        )}

        {filingLoading && !filingHistory ? (
          <Box textAlign="center" padding="xxl">
            <Spinner size="large" />
            <Box variant="p" color="text-body-secondary">
              Loading filing history...
            </Box>
          </Box>
        ) : null}

        {!filingLoading && !filingHistory && !filingError ? (
          <Box textAlign="center" padding="xxl">
            <TextContent>
              <p>
                No filing history data available yet. Trigger background research from the landing page to populate this
                view.
              </p>
            </TextContent>
          </Box>
        ) : null}

        {filingHistory && (
          <SpaceBetween size="l">
            <ColumnLayout columns={3} variant="text-grid">
              <Box>
                <Box variant="awsui-key-label">Total filings captured</Box>
                <Box>{filingHistory.total_count ?? 'N/A'}</Box>
              </Box>
              <Box>
                <Box variant="awsui-key-label">Distinct filing types</Box>
                <Box>{Object.keys(filingHistory.filing_types || {}).length}</Box>
              </Box>
              <Box>
                <Box variant="awsui-key-label">Last updated</Box>
                <Box>{formatDateTime(filingHistory.last_updated)}</Box>
              </Box>
            </ColumnLayout>

            {Object.keys(filingHistory.filing_types || {}).length > 0 && (
              <Alert type="info" header="Filing type distribution">
                <ul style={{ margin: 0, paddingLeft: 20 }}>
                  {Object.entries(filingHistory.filing_types || {}).map(([type, count]) => (
                    <li key={type}>
                      {type}: {count}
                    </li>
                  ))}
                </ul>
              </Alert>
            )}

            {(filingHistory.recent_filings || []).length > 0 && (
              <Table
                columnDefinitions={[
                  {
                    id: 'type',
                    header: 'Filing type',
                    cell: (item) => item.type || 'N/A',
                  },
                  {
                    id: 'description',
                    header: 'Description',
                    cell: (item) => item.description || 'N/A',
                  },
                  {
                    id: 'made_up_date',
                    header: 'Made up to',
                    cell: (item) => formatDate(item.made_up_date),
                  },
                  {
                    id: 'date',
                    header: 'Filed',
                    cell: (item) => formatDate(item.date || item.action_date),
                  },
                ]}
                items={filingHistory.recent_filings}
                loadingText="Loading recent filings..."
                trackBy={(item) => `${item.type}-${item.date}-${item.made_up_date}`}
                empty={<TextContent>No recent filings recorded.</TextContent>}
              />
            )}
          </SpaceBetween>
        )}
      </SpaceBetween>
    </Container>
  );

  const renderOfficers = () => (
    <Container
      header={
        <Header
          variant="h3"
          actions={
            <Button iconName="refresh" loading={officersLoading} onClick={() => loadOfficers(true)}>
              Refresh officers
            </Button>
          }
        >
          Officers Analysis
        </Header>
      }
    >
      <SpaceBetween size="m">
        {officersError && (
          <Alert type="error" header="Unable to load officers" dismissible onDismiss={() => setOfficersError(null)}>
            {officersError}
          </Alert>
        )}

        {officersLoading && !officersData ? (
          <Box textAlign="center" padding="xxl">
            <Spinner size="large" />
            <Box variant="p" color="text-body-secondary">
              Loading officers data...
            </Box>
          </Box>
        ) : null}

        {!officersLoading && !officersData && !officersError ? (
          <Box textAlign="center" padding="xxl">
            <TextContent>
              <p>No officers data available yet. Trigger background research to populate this view.</p>
            </TextContent>
          </Box>
        ) : null}

        {officersData && (
          <SpaceBetween size="l">
            <Alert
              type={intelligence?.governance?.director_stability === 'good' ? 'info' : 'warning'}
              header={`Directors risk level: ${intelligence?.risk_assessment?.risk_level || 'Unknown'}`}
            >
              <div>
                <strong>Total officers:</strong> {officersData.total_results || officerRows.length} (
                {officersData.active_count || (officersData.active_officers || []).length} active)
              </div>
              {intelligence?.risk_assessment?.summary && (
                <div style={{ marginTop: '8px' }}>{intelligence.risk_assessment.summary}</div>
              )}
            </Alert>

            <Table
              columnDefinitions={[
                {
                  id: 'name',
                  header: 'Name',
                  cell: (item) => item.name || 'N/A',
                },
                {
                  id: 'role',
                  header: 'Role',
                  cell: (item) => item.officer_role || item.role || 'N/A',
                },
                {
                  id: 'appointed',
                  header: 'Appointed',
                  cell: (item) => formatDate(item.appointed_on),
                },
                {
                  id: 'status',
                  header: 'Status',
                  cell: (item) => (
                    <StatusIndicator type={item.status === 'active' ? 'success' : 'stopped'}>
                      {item.status === 'active' ? 'Active' : 'Resigned'}
                    </StatusIndicator>
                  ),
                },
                {
                  id: 'risk',
                  header: 'Screening flags',
                  cell: (item) => {
                    const normalizedName = (item.name || '').toLowerCase();
                    const isSanctioned = sanitizedSanctionedNames.has(normalizedName);
                    const isPep = sanitizedPepNames.has(normalizedName);

                    if (isSanctioned) {
                      return <StatusIndicator type="error">Sanctions match</StatusIndicator>;
                    }

                    if (isPep) {
                      return <StatusIndicator type="warning">PEP match</StatusIndicator>;
                    }

                    return <StatusIndicator type="success">Clear</StatusIndicator>;
                  },
                },
              ]}
              items={officerRows}
              trackBy={(item) => `${item.name}-${item.appointed_on}-${item.resigned_on || 'active'}`}
              loadingText="Loading officers..."
              empty={<TextContent>No officers data available.</TextContent>}
            />
          </SpaceBetween>
        )}
      </SpaceBetween>
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
            <SpaceBetween size="s">
              {!intelligence && !intelligenceLoading && (
                <Alert type="warning" header="Intelligence Data Required">
                  Company intelligence data must be gathered before generating an AML report. Please refresh intelligence to load the required data.
                </Alert>
              )}
              <Button
                variant="primary"
                onClick={handleGenerateReport}
                disabled={generatingReport || !intelligence || intelligenceLoading}
                loading={generatingReport}
                iconName="download"
              >
                {generatingReport ? 'Generating Report...' : 'Generate Full AML Report'}
              </Button>
            </SpaceBetween>
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
                documentName={`AML_Report_${companyNumber}`}
                title={`AML Report - ${reportSuccess?.companyName || companyDisplayName}`}
              />
            </Box>
          )}
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

  const breadcrumbs = (
    <BreadcrumbGroup
      items={[
        { text: 'Company select', href: `#${COMPANY_SELECT_PATH}` },
        { text: companyDisplayName, href: '#' },
      ]}
      ariaLabel="Breadcrumbs"
    />
  );

  if (loading) {
    return (
      <AppLayoutWrapper breadcrumbs={breadcrumbs}>
        <Box textAlign="center" padding="xxl">
          <Spinner size="large" />
          <Box variant="p" color="text-body-secondary">
            Loading company analysis...
          </Box>
        </Box>
      </AppLayoutWrapper>
    );
  }

  return (
    <AppLayoutWrapper breadcrumbs={breadcrumbs}>
      <SpaceBetween size="l">
        <Header
          variant="h1"
          description={`Company number: ${companyProfile?.company_number || companyNumber}`}
          actions={
            <SpaceBetween direction="horizontal" size="s">
              <Button iconName="external" onClick={() => history.push(COMPANY_SELECT_PATH)}>
                Choose another company
              </Button>
              <Button onClick={handleRefreshAll} loading={isRefreshing} iconName="refresh">
                Refresh all data
              </Button>
            </SpaceBetween>
          }
        >
          Company analysis: {companyDisplayName}
        </Header>

        {reportSuccess && activeTab !== 'aml_report' && (
          <Alert
            type="success"
            dismissible
            onDismiss={() => setReportSuccess(null)}
            action={
              reportSuccess.downloadUrl && (
                <Button href={reportSuccess.downloadUrl} iconAlign="right" iconName="external" target="_blank">
                  Download report
                </Button>
              )
            }
          >
            {reportSuccess.message || 'AML report generated successfully'}
          </Alert>
        )}

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
    </AppLayoutWrapper>
  );
};

export default CompanyAnalysis;
