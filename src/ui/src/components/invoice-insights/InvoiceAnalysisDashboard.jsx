// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
import React, { useState, useEffect, useMemo } from 'react';
import { useHistory } from 'react-router-dom';
import {
  Container,
  Header,
  SpaceBetween,
  Box,
  Tabs,
  Spinner,
  BreadcrumbGroup,
  ColumnLayout,
  Table,
  Button,
  StatusIndicator,
  Badge,
  PieChart,
  BarChart,
  Link,
  Alert,
  ProgressBar,
  Grid,
  Icon,
  Flashbar,
  Select,
  TextFilter,
  Pagination,
} from '@awsui/components-react';

import { useCompany } from '../../contexts/company';
import { COMPANY_SELECT_PATH, INVOICE_INSIGHTS_PATH } from '../../routes/constants';
import GenAIIDPTopNavigation from '../genai-idp-top-navigation';
import {
  fetchExtractionResults,
  formatInvoiceData,
  DOCUMENT_TYPES,
  formatCurrency,
} from '../../services/extractionService';

import '@awsui/global-styles/index.css';

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

const calculateAnalytics = (invoices) => {
  const analytics = {
    // Totals
    totalInvoices: invoices.length,
    totalSpend: 0,
    totalVAT: 0,
    totalNet: 0,
    averageInvoice: 0,

    // Deductibility
    fullyDeductible: { count: 0, amount: 0 },
    partiallyDeductible: { count: 0, amount: 0 },
    notDeductible: { count: 0, amount: 0 },
    requiresReview: { count: 0, amount: 0 },
    pendingAnalysis: { count: 0, amount: 0 },

    // Risk levels
    highRisk: { count: 0, amount: 0 },
    mediumRisk: { count: 0, amount: 0 },
    lowRisk: { count: 0, amount: 0 },

    // Actions
    actionApprove: 0,
    actionReject: 0,
    actionDocumentation: 0,
    actionApportion: 0,
    hitlRequired: 0,

    // Financial
    addbackAmount: 0,
    deductibleAmount: 0,

    // Suppliers
    supplierSpend: {},
    supplierCount: new Set(),

    // Invoice types
    byType: {},

    // Quality
    excellentQuality: 0,
    goodQuality: 0,
    acceptableQuality: 0,
    poorQuality: 0,

    // Monthly breakdown
    monthlySpend: {},
  };

  invoices.forEach((inv) => {
    const rawData = inv.rawData || {};
    const amount = parseFloat(rawData.TotalAmount) || 0;
    const vat = parseFloat(rawData.VATAmount) || 0;
    const net = parseFloat(rawData.NetAmount) || amount - vat;
    const addback = parseFloat(rawData.AddbackAmount) || 0;
    const deductPct = parseFloat(rawData.DeductibilityPercentage) || 0;

    // Totals
    analytics.totalSpend += amount;
    analytics.totalVAT += vat;
    analytics.totalNet += net;
    analytics.addbackAmount += addback;

    // Deductibility status
    const deductStatus = rawData.DeductibilityStatus;
    const analysisStatus = rawData.AnalysisStatus;

    if (!analysisStatus || analysisStatus === 'PENDING') {
      analytics.pendingAnalysis.count++;
      analytics.pendingAnalysis.amount += amount;
    } else if (deductStatus === 'FULLY_DEDUCTIBLE') {
      analytics.fullyDeductible.count++;
      analytics.fullyDeductible.amount += amount;
      analytics.deductibleAmount += amount;
    } else if (deductStatus === 'PARTIALLY_DEDUCTIBLE') {
      analytics.partiallyDeductible.count++;
      analytics.partiallyDeductible.amount += amount;
      analytics.deductibleAmount += (amount * deductPct) / 100;
    } else if (deductStatus === 'NOT_DEDUCTIBLE') {
      analytics.notDeductible.count++;
      analytics.notDeductible.amount += amount;
    } else if (deductStatus === 'REQUIRES_REVIEW') {
      analytics.requiresReview.count++;
      analytics.requiresReview.amount += amount;
    }

    // Risk levels
    const hmrcRisk = rawData.HMRCRisk;
    if (hmrcRisk === 'HIGH') {
      analytics.highRisk.count++;
      analytics.highRisk.amount += amount;
    } else if (hmrcRisk === 'MEDIUM') {
      analytics.mediumRisk.count++;
      analytics.mediumRisk.amount += amount;
    } else if (hmrcRisk === 'LOW') {
      analytics.lowRisk.count++;
      analytics.lowRisk.amount += amount;
    }

    // Recommended actions
    const action = rawData.RecommendedAction;
    if (action === 'APPROVE') analytics.actionApprove++;
    else if (action === 'REJECT') analytics.actionReject++;
    else if (action === 'REQUEST_DOCUMENTATION') analytics.actionDocumentation++;
    else if (action === 'APPORTION') analytics.actionApportion++;

    if (rawData.HITLRequired) analytics.hitlRequired++;

    // Supplier breakdown
    const supplier = rawData.SupplierName || rawData.VendorName || 'Unknown';
    if (!analytics.supplierSpend[supplier]) {
      analytics.supplierSpend[supplier] = { amount: 0, count: 0, deductible: 0, notDeductible: 0 };
    }
    analytics.supplierSpend[supplier].amount += amount;
    analytics.supplierSpend[supplier].count++;
    if (deductStatus === 'FULLY_DEDUCTIBLE' || deductStatus === 'PARTIALLY_DEDUCTIBLE') {
      analytics.supplierSpend[supplier].deductible += amount;
    } else if (deductStatus === 'NOT_DEDUCTIBLE') {
      analytics.supplierSpend[supplier].notDeductible += amount;
    }
    analytics.supplierCount.add(supplier);

    // Invoice type breakdown
    const invType = rawData.InvoiceType || 'UNKNOWN';
    if (!analytics.byType[invType]) {
      analytics.byType[invType] = { count: 0, amount: 0 };
    }
    analytics.byType[invType].count++;
    analytics.byType[invType].amount += amount;

    // Quality tier
    const quality = rawData.QualityTier;
    if (quality === 'EXCELLENT') analytics.excellentQuality++;
    else if (quality === 'GOOD') analytics.goodQuality++;
    else if (quality === 'ACCEPTABLE') analytics.acceptableQuality++;
    else analytics.poorQuality++;

    // Monthly breakdown
    const invoiceDate = rawData.InvoiceDate;
    if (invoiceDate) {
      const month = invoiceDate.substring(0, 7); // YYYY-MM
      if (!analytics.monthlySpend[month]) {
        analytics.monthlySpend[month] = { amount: 0, count: 0, deductible: 0 };
      }
      analytics.monthlySpend[month].amount += amount;
      analytics.monthlySpend[month].count++;
      if (deductStatus === 'FULLY_DEDUCTIBLE') {
        analytics.monthlySpend[month].deductible += amount;
      }
    }
  });

  // Averages
  analytics.averageInvoice = analytics.totalInvoices > 0 ? analytics.totalSpend / analytics.totalInvoices : 0;

  return analytics;
};

// ============================================================================
// METRIC CARD COMPONENT
// ============================================================================

const MetricCard = ({ title, value, description, trend, trendDirection, variant = 'default', icon }) => {
  const getVariantColor = () => {
    switch (variant) {
      case 'success':
        return 'text-status-success';
      case 'warning':
        return 'text-status-warning';
      case 'error':
        return 'text-status-error';
      case 'info':
        return 'text-status-info';
      default:
        return 'text-body-secondary';
    }
  };

  return (
    <Container>
      <SpaceBetween size="xxs">
        <Box variant="awsui-key-label" color="text-label">
          {icon && <Icon name={icon} />} {title}
        </Box>
        <Box fontSize="display-l" fontWeight="bold">
          {value}
        </Box>
        {description && (
          <Box variant="small" color={getVariantColor()}>
            {description}
          </Box>
        )}
        {trend && (
          <Box variant="small" color={trendDirection === 'up' ? 'text-status-success' : 'text-status-error'}>
            {trendDirection === 'up' ? '↑' : '↓'} {trend}
          </Box>
        )}
      </SpaceBetween>
    </Container>
  );
};

// ============================================================================
// MAIN COMPONENT
// ============================================================================

const InvoiceAnalysisDashboard = () => {
  const history = useHistory();
  const { activeCompany, isCompanySelected } = useCompany();

  const [loading, setLoading] = useState(true);
  const [invoices, setInvoices] = useState([]);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');

  // Table state
  const [filterText, setFilterText] = useState('');
  const [selectedRiskFilter, setSelectedRiskFilter] = useState(null);
  const [selectedStatusFilter, setSelectedStatusFilter] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 20;

  useEffect(() => {
    if (!isCompanySelected) {
      history.push(COMPANY_SELECT_PATH);
      return;
    }

    loadInvoices();
  }, [isCompanySelected, activeCompany]);

  const loadInvoices = async () => {
    if (!activeCompany?.companyNumber) return;

    setLoading(true);
    setError(null);

    try {
      console.log('[INVOICE ANALYSIS] Loading invoices for:', activeCompany.companyNumber);
      const result = await fetchExtractionResults(activeCompany.companyNumber, DOCUMENT_TYPES.INVOICE, 500);

      const formattedInvoices = result.items.map(formatInvoiceData);
      console.log('[INVOICE ANALYSIS] Loaded invoices:', formattedInvoices.length);
      setInvoices(formattedInvoices);
    } catch (err) {
      console.error('[INVOICE ANALYSIS] Error loading invoices:', err);
      setError(err.message || 'Failed to load invoices');
    } finally {
      setLoading(false);
    }
  };

  // Calculate analytics from loaded invoices
  const analytics = useMemo(() => calculateAnalytics(invoices), [invoices]);

  // Filter invoices for action queue
  const actionItems = useMemo(() => {
    return invoices.filter((inv) => {
      const rawData = inv.rawData || {};
      const action = rawData.RecommendedAction;
      const hmrcRisk = rawData.HMRCRisk;
      const hitl = rawData.HITLRequired;

      // Apply filters
      if (selectedRiskFilter && hmrcRisk !== selectedRiskFilter.value) return false;
      if (selectedStatusFilter && rawData.DeductibilityStatus !== selectedStatusFilter.value) return false;
      if (filterText) {
        const searchLower = filterText.toLowerCase();
        const supplier = (rawData.SupplierName || '').toLowerCase();
        const desc = (rawData.Description || '').toLowerCase();
        if (!supplier.includes(searchLower) && !desc.includes(searchLower)) return false;
      }

      return (
        action === 'REJECT' ||
        action === 'REQUEST_DOCUMENTATION' ||
        action === 'APPORTION' ||
        hitl ||
        hmrcRisk === 'HIGH'
      );
    });
  }, [invoices, filterText, selectedRiskFilter, selectedStatusFilter]);

  // Paginated action items
  const paginatedActionItems = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return actionItems.slice(start, start + pageSize);
  }, [actionItems, currentPage, pageSize]);

  // Top suppliers sorted by spend
  const topSuppliers = useMemo(() => {
    return Object.entries(analytics.supplierSpend)
      .map(([name, data]) => ({ name, ...data }))
      .sort((a, b) => b.amount - a.amount)
      .slice(0, 15);
  }, [analytics]);

  // Monthly data for chart
  const monthlyChartData = useMemo(() => {
    return Object.entries(analytics.monthlySpend)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([month, data]) => ({
        x: month,
        y: data.amount,
        deductible: data.deductible,
      }));
  }, [analytics]);

  if (loading) {
    return (
      <>
        <GenAIIDPTopNavigation />
        <Box textAlign="center" padding="xxl">
          <Spinner size="large" />
          <Box variant="p" color="text-body-secondary">
            Loading invoice analysis dashboard...
          </Box>
        </Box>
      </>
    );
  }

  if (!activeCompany) {
    return null;
  }

  // ============================================================================
  // TAB: EXECUTIVE OVERVIEW
  // ============================================================================

  const renderOverviewTab = () => {
    const analyzedPct =
      analytics.totalInvoices > 0
        ? (((analytics.totalInvoices - analytics.pendingAnalysis.count) / analytics.totalInvoices) * 100).toFixed(0)
        : 0;

    const deductiblePct =
      analytics.totalSpend > 0 ? ((analytics.deductibleAmount / analytics.totalSpend) * 100).toFixed(1) : 0;

    const taxAtRisk = analytics.addbackAmount * 0.25; // Assuming 25% corp tax rate

    return (
      <SpaceBetween size="l">
        {/* Key Metrics Row */}
        <Grid
          gridDefinition={[
            { colspan: { default: 12, xs: 6, s: 3 } },
            { colspan: { default: 12, xs: 6, s: 3 } },
            { colspan: { default: 12, xs: 6, s: 3 } },
            { colspan: { default: 12, xs: 6, s: 3 } },
          ]}
        >
          <MetricCard
            title="Total Spend"
            value={formatCurrency(analytics.totalSpend, 'GBP')}
            description={`${analytics.totalInvoices} invoices from ${analytics.supplierCount.size} suppliers`}
          />
          <MetricCard
            title="VAT Recoverable"
            value={formatCurrency(analytics.totalVAT, 'GBP')}
            description="Total VAT from all invoices"
            variant="info"
          />
          <MetricCard
            title="Tax Deductible"
            value={formatCurrency(analytics.deductibleAmount, 'GBP')}
            description={`${deductiblePct}% of total spend`}
            variant="success"
          />
          <MetricCard
            title="Tax Savings at Risk"
            value={formatCurrency(taxAtRisk, 'GBP')}
            description={`From £${analytics.addbackAmount.toLocaleString()} addback`}
            variant="error"
          />
        </Grid>

        {/* Analysis Progress */}
        {analytics.pendingAnalysis.count > 0 && (
          <Alert type="info" header={`Analysis Progress: ${analyzedPct}% Complete`}>
            <Box>
              {analytics.totalInvoices - analytics.pendingAnalysis.count} of {analytics.totalInvoices} invoices have
              been analyzed for tax compliance. {analytics.pendingAnalysis.count} invoices (£
              {analytics.pendingAnalysis.amount.toLocaleString()}) are pending analysis.
            </Box>
            <Box padding={{ top: 's' }}>
              <ProgressBar value={parseInt(analyzedPct)} />
            </Box>
          </Alert>
        )}

        {/* Deductibility & Risk Charts */}
        <ColumnLayout columns={2} variant="text-grid">
          <Container header={<Header variant="h3">Tax Deductibility Breakdown</Header>}>
            <PieChart
              data={[
                { title: 'Fully Deductible', value: analytics.fullyDeductible.count, color: '#1d8102' },
                { title: 'Partially Deductible', value: analytics.partiallyDeductible.count, color: '#0972d3' },
                { title: 'Not Deductible', value: analytics.notDeductible.count, color: '#d91515' },
                { title: 'Requires Review', value: analytics.requiresReview.count, color: '#8d6605' },
                { title: 'Pending Analysis', value: analytics.pendingAnalysis.count, color: '#879596' },
              ].filter((d) => d.value > 0)}
              detailPopoverContent={(datum, sum) => [
                { key: 'Count', value: datum.value },
                { key: 'Percentage', value: `${((datum.value / sum) * 100).toFixed(1)}%` },
              ]}
              segmentDescription={(datum, sum) =>
                `${datum.value} invoices (${((datum.value / sum) * 100).toFixed(0)}%)`
              }
              size="medium"
              hideFilter
              hideLegend={false}
              legendTitle="Status"
              empty={<Box textAlign="center">No data</Box>}
            />
          </Container>

          <Container header={<Header variant="h3">HMRC Risk Assessment</Header>}>
            <SpaceBetween size="m">
              <Box>
                <Box variant="awsui-key-label">High Risk</Box>
                <ProgressBar
                  value={analytics.highRisk.count}
                  additionalInfo={`${analytics.highRisk.count} invoices • ${formatCurrency(
                    analytics.highRisk.amount,
                    'GBP',
                  )}`}
                  status="error"
                />
              </Box>
              <Box>
                <Box variant="awsui-key-label">Medium Risk</Box>
                <ProgressBar
                  value={analytics.mediumRisk.count}
                  additionalInfo={`${analytics.mediumRisk.count} invoices • ${formatCurrency(
                    analytics.mediumRisk.amount,
                    'GBP',
                  )}`}
                  status="in-progress"
                />
              </Box>
              <Box>
                <Box variant="awsui-key-label">Low Risk</Box>
                <ProgressBar
                  value={analytics.lowRisk.count}
                  additionalInfo={`${analytics.lowRisk.count} invoices • ${formatCurrency(
                    analytics.lowRisk.amount,
                    'GBP',
                  )}`}
                  status="success"
                />
              </Box>
            </SpaceBetween>
          </Container>
        </ColumnLayout>

        {/* Action Summary */}
        <Container header={<Header variant="h3">Actions Required</Header>}>
          <ColumnLayout columns={4} variant="text-grid">
            <div>
              <Box variant="awsui-key-label">✓ Approve</Box>
              <Box fontSize="heading-xl" fontWeight="bold" color="text-status-success">
                {analytics.actionApprove}
              </Box>
            </div>
            <div>
              <Box variant="awsui-key-label">📄 Need Documentation</Box>
              <Box fontSize="heading-xl" fontWeight="bold" color="text-status-warning">
                {analytics.actionDocumentation}
              </Box>
            </div>
            <div>
              <Box variant="awsui-key-label">✗ Reject</Box>
              <Box fontSize="heading-xl" fontWeight="bold" color="text-status-error">
                {analytics.actionReject}
              </Box>
            </div>
            <div>
              <Box variant="awsui-key-label">⚖️ Apportion</Box>
              <Box fontSize="heading-xl" fontWeight="bold" color="text-status-info">
                {analytics.actionApportion}
              </Box>
            </div>
          </ColumnLayout>
        </Container>

        {/* Quality Summary */}
        <Container header={<Header variant="h3">Extraction Quality</Header>}>
          <ColumnLayout columns={4} variant="text-grid">
            <div>
              <Box variant="awsui-key-label">Excellent</Box>
              <Box fontSize="heading-xl" fontWeight="bold">
                {analytics.excellentQuality}
              </Box>
              <Box variant="small" color="text-status-success">
                High confidence
              </Box>
            </div>
            <div>
              <Box variant="awsui-key-label">Good</Box>
              <Box fontSize="heading-xl" fontWeight="bold">
                {analytics.goodQuality}
              </Box>
            </div>
            <div>
              <Box variant="awsui-key-label">Acceptable</Box>
              <Box fontSize="heading-xl" fontWeight="bold">
                {analytics.acceptableQuality}
              </Box>
            </div>
            <div>
              <Box variant="awsui-key-label">Needs Review</Box>
              <Box fontSize="heading-xl" fontWeight="bold" color="text-status-warning">
                {analytics.hitlRequired}
              </Box>
              <Box variant="small" color="text-status-warning">
                Human review required
              </Box>
            </div>
          </ColumnLayout>
        </Container>
      </SpaceBetween>
    );
  };

  // ============================================================================
  // TAB: ACTION QUEUE
  // ============================================================================

  const renderActionQueueTab = () => {
    const riskOptions = [
      { label: 'All Risks', value: null },
      { label: 'High Risk', value: 'HIGH' },
      { label: 'Medium Risk', value: 'MEDIUM' },
      { label: 'Low Risk', value: 'LOW' },
    ];

    const statusOptions = [
      { label: 'All Statuses', value: null },
      { label: 'Not Deductible', value: 'NOT_DEDUCTIBLE' },
      { label: 'Requires Review', value: 'REQUIRES_REVIEW' },
      { label: 'Partially Deductible', value: 'PARTIALLY_DEDUCTIBLE' },
    ];

    return (
      <SpaceBetween size="l">
        {actionItems.length === 0 ? (
          <Alert type="success" header="No Actions Required">
            All invoices have been reviewed and no items require immediate attention.
          </Alert>
        ) : (
          <Alert type="warning" header={`${actionItems.length} Items Require Attention`}>
            These invoices have been flagged for review, rejection, documentation, or have high HMRC risk.
          </Alert>
        )}

        <Table
          columnDefinitions={[
            {
              id: 'supplier',
              header: 'Supplier',
              cell: (item) => item.rawData?.SupplierName || 'Unknown',
              width: 180,
              sortingField: 'supplier',
            },
            {
              id: 'amount',
              header: 'Amount',
              cell: (item) => formatCurrency(item.rawData?.TotalAmount, item.rawData?.Currency || 'GBP'),
              width: 110,
              sortingField: 'amount',
            },
            {
              id: 'description',
              header: 'Description',
              cell: (item) => (
                <Box variant="small">
                  {(item.rawData?.Description || 'N/A').substring(0, 60)}
                  {(item.rawData?.Description || '').length > 60 ? '...' : ''}
                </Box>
              ),
              width: 250,
            },
            {
              id: 'risk',
              header: 'HMRC Risk',
              cell: (item) => {
                const risk = item.rawData?.HMRCRisk;
                const colors = { HIGH: 'red', MEDIUM: 'blue', LOW: 'green' };
                return risk ? <Badge color={colors[risk]}>{risk}</Badge> : <Badge color="grey">N/A</Badge>;
              },
              width: 100,
            },
            {
              id: 'deductibility',
              header: 'Deductibility',
              cell: (item) => {
                const status = item.rawData?.DeductibilityStatus;
                const colors = {
                  FULLY_DEDUCTIBLE: 'green',
                  PARTIALLY_DEDUCTIBLE: 'blue',
                  NOT_DEDUCTIBLE: 'red',
                  REQUIRES_REVIEW: 'grey',
                };
                return status ? (
                  <Badge color={colors[status]}>{status.replace(/_/g, ' ')}</Badge>
                ) : (
                  <Badge color="grey">PENDING</Badge>
                );
              },
              width: 150,
            },
            {
              id: 'action',
              header: 'Action',
              cell: (item) => {
                const action = item.rawData?.RecommendedAction;
                const icons = {
                  APPROVE: <StatusIndicator type="success">Approve</StatusIndicator>,
                  REJECT: <StatusIndicator type="error">Reject</StatusIndicator>,
                  REQUEST_DOCUMENTATION: <StatusIndicator type="warning">Documentation</StatusIndicator>,
                  APPORTION: <StatusIndicator type="info">Apportion</StatusIndicator>,
                };
                return icons[action] || <StatusIndicator type="pending">Pending</StatusIndicator>;
              },
              width: 140,
            },
            {
              id: 'reasoning',
              header: 'Reason',
              cell: (item) => (
                <Box variant="small" color="text-body-secondary">
                  {(item.rawData?.DeductibilityReasoning || item.rawData?.HMRCConcern || 'N/A').substring(0, 80)}
                  {(item.rawData?.DeductibilityReasoning || item.rawData?.HMRCConcern || '').length > 80 ? '...' : ''}
                </Box>
              ),
              minWidth: 200,
            },
          ]}
          items={paginatedActionItems}
          loadingText="Loading action items"
          sortingDisabled={false}
          variant="container"
          stickyHeader
          filter={
            <SpaceBetween direction="horizontal" size="s">
              <TextFilter
                filteringText={filterText}
                filteringPlaceholder="Search supplier or description"
                onChange={({ detail }) => {
                  setFilterText(detail.filteringText);
                  setCurrentPage(1);
                }}
              />
              <Select
                selectedOption={selectedRiskFilter || riskOptions[0]}
                onChange={({ detail }) => {
                  setSelectedRiskFilter(detail.selectedOption.value ? detail.selectedOption : null);
                  setCurrentPage(1);
                }}
                options={riskOptions}
                placeholder="Filter by risk"
              />
              <Select
                selectedOption={selectedStatusFilter || statusOptions[0]}
                onChange={({ detail }) => {
                  setSelectedStatusFilter(detail.selectedOption.value ? detail.selectedOption : null);
                  setCurrentPage(1);
                }}
                options={statusOptions}
                placeholder="Filter by status"
              />
            </SpaceBetween>
          }
          pagination={
            <Pagination
              currentPageIndex={currentPage}
              pagesCount={Math.ceil(actionItems.length / pageSize)}
              onChange={({ detail }) => setCurrentPage(detail.currentPageIndex)}
            />
          }
          empty={
            <Box textAlign="center" color="inherit">
              <b>No action items</b>
              <Box padding={{ bottom: 's' }} variant="p" color="inherit">
                No invoices match the current filters.
              </Box>
            </Box>
          }
          header={
            <Header
              counter={`(${actionItems.length})`}
              description="Invoices flagged for review, rejection, or documentation"
              actions={
                <Button iconName="refresh" onClick={loadInvoices}>
                  Refresh
                </Button>
              }
            >
              Action Queue
            </Header>
          }
        />
      </SpaceBetween>
    );
  };

  // ============================================================================
  // TAB: SUPPLIER ANALYSIS
  // ============================================================================

  const renderSupplierTab = () => {
    return (
      <SpaceBetween size="l">
        <Container header={<Header variant="h3">Supplier Summary</Header>}>
          <ColumnLayout columns={3} variant="text-grid">
            <div>
              <Box variant="awsui-key-label">Unique Suppliers</Box>
              <Box fontSize="display-l" fontWeight="bold">
                {analytics.supplierCount.size}
              </Box>
            </div>
            <div>
              <Box variant="awsui-key-label">Average per Supplier</Box>
              <Box fontSize="display-l" fontWeight="bold">
                {formatCurrency(analytics.totalSpend / Math.max(analytics.supplierCount.size, 1), 'GBP')}
              </Box>
            </div>
            <div>
              <Box variant="awsui-key-label">Top Supplier</Box>
              <Box fontSize="display-l" fontWeight="bold">
                {topSuppliers[0]?.name || 'N/A'}
              </Box>
              <Box variant="small">{formatCurrency(topSuppliers[0]?.amount || 0, 'GBP')}</Box>
            </div>
          </ColumnLayout>
        </Container>

        <Table
          columnDefinitions={[
            {
              id: 'rank',
              header: '#',
              cell: (item, index) => index + 1,
              width: 50,
            },
            {
              id: 'supplier',
              header: 'Supplier',
              cell: (item) => item.name,
              width: 250,
              sortingField: 'name',
            },
            {
              id: 'invoices',
              header: 'Invoices',
              cell: (item) => item.count,
              width: 100,
              sortingField: 'count',
            },
            {
              id: 'totalSpend',
              header: 'Total Spend',
              cell: (item) => formatCurrency(item.amount, 'GBP'),
              width: 130,
              sortingField: 'amount',
            },
            {
              id: 'deductible',
              header: 'Deductible',
              cell: (item) => formatCurrency(item.deductible, 'GBP'),
              width: 130,
            },
            {
              id: 'notDeductible',
              header: 'Not Deductible',
              cell: (item) => formatCurrency(item.notDeductible, 'GBP'),
              width: 130,
            },
            {
              id: 'deductiblePct',
              header: 'Deductible %',
              cell: (item) => {
                const pct = item.amount > 0 ? (item.deductible / item.amount) * 100 : 0;
                const color = pct >= 80 ? 'green' : pct >= 50 ? 'blue' : pct > 0 ? 'grey' : 'red';
                return <Badge color={color}>{pct.toFixed(0)}%</Badge>;
              },
              width: 120,
            },
          ]}
          items={topSuppliers}
          sortingDisabled={false}
          variant="container"
          header={
            <Header counter={`(${topSuppliers.length})`} description="Top suppliers by total spend">
              Supplier Breakdown
            </Header>
          }
          empty={
            <Box textAlign="center" color="inherit">
              <b>No supplier data</b>
            </Box>
          }
        />
      </SpaceBetween>
    );
  };

  // ============================================================================
  // TAB: VAT ANALYSIS
  // ============================================================================

  const renderVATTab = () => {
    const vatPct = analytics.totalSpend > 0 ? ((analytics.totalVAT / analytics.totalSpend) * 100).toFixed(1) : 0;

    return (
      <SpaceBetween size="l">
        <Grid
          gridDefinition={[
            { colspan: { default: 12, s: 4 } },
            { colspan: { default: 12, s: 4 } },
            { colspan: { default: 12, s: 4 } },
          ]}
        >
          <MetricCard
            title="Total VAT"
            value={formatCurrency(analytics.totalVAT, 'GBP')}
            description={`${vatPct}% of total spend`}
          />
          <MetricCard
            title="Net Amount"
            value={formatCurrency(analytics.totalNet, 'GBP')}
            description="Excluding VAT"
          />
          <MetricCard
            title="Gross Amount"
            value={formatCurrency(analytics.totalSpend, 'GBP')}
            description="Including VAT"
          />
        </Grid>

        <Container header={<Header variant="h3">Invoice Type Breakdown</Header>}>
          <Table
            columnDefinitions={[
              {
                id: 'type',
                header: 'Invoice Type',
                cell: (item) => <Badge>{item.type.replace(/_/g, ' ')}</Badge>,
                width: 200,
              },
              {
                id: 'count',
                header: 'Count',
                cell: (item) => item.count,
                width: 100,
              },
              {
                id: 'amount',
                header: 'Total Amount',
                cell: (item) => formatCurrency(item.amount, 'GBP'),
                width: 150,
              },
              {
                id: 'pct',
                header: '% of Total',
                cell: (item) => {
                  const pct = analytics.totalSpend > 0 ? (item.amount / analytics.totalSpend) * 100 : 0;
                  return `${pct.toFixed(1)}%`;
                },
                width: 100,
              },
              {
                id: 'avgAmount',
                header: 'Avg. Invoice',
                cell: (item) => formatCurrency(item.count > 0 ? item.amount / item.count : 0, 'GBP'),
                width: 130,
              },
            ]}
            items={Object.entries(analytics.byType).map(([type, data]) => ({ type, ...data }))}
            variant="container"
            empty={<Box textAlign="center">No data</Box>}
          />
        </Container>
      </SpaceBetween>
    );
  };

  // ============================================================================
  // TAB: MONTHLY TRENDS
  // ============================================================================

  const renderTrendsTab = () => {
    return (
      <SpaceBetween size="l">
        <Container header={<Header variant="h3">Monthly Spend Trend</Header>}>
          {monthlyChartData.length > 0 ? (
            <BarChart
              series={[
                {
                  title: 'Total Spend',
                  type: 'bar',
                  data: monthlyChartData.map((d) => ({ x: d.x, y: d.y })),
                },
                {
                  title: 'Deductible',
                  type: 'bar',
                  data: monthlyChartData.map((d) => ({ x: d.x, y: d.deductible })),
                },
              ]}
              xDomain={monthlyChartData.map((d) => d.x)}
              yDomain={[0, Math.max(...monthlyChartData.map((d) => d.y)) * 1.1]}
              xTitle="Month"
              yTitle="Amount (£)"
              hideFilter
              height={300}
              empty={<Box textAlign="center">No trend data available</Box>}
            />
          ) : (
            <Alert type="info">Not enough data to display monthly trends. Process more invoices to see patterns.</Alert>
          )}
        </Container>

        <Table
          columnDefinitions={[
            {
              id: 'month',
              header: 'Month',
              cell: (item) => item.x,
              width: 120,
            },
            {
              id: 'count',
              header: 'Invoices',
              cell: (item) => analytics.monthlySpend[item.x]?.count || 0,
              width: 100,
            },
            {
              id: 'spend',
              header: 'Total Spend',
              cell: (item) => formatCurrency(item.y, 'GBP'),
              width: 150,
            },
            {
              id: 'deductible',
              header: 'Deductible',
              cell: (item) => formatCurrency(item.deductible, 'GBP'),
              width: 150,
            },
            {
              id: 'deductPct',
              header: 'Deductible %',
              cell: (item) => {
                const pct = item.y > 0 ? (item.deductible / item.y) * 100 : 0;
                return `${pct.toFixed(1)}%`;
              },
              width: 120,
            },
          ]}
          items={monthlyChartData}
          variant="container"
          header={<Header variant="h3">Monthly Breakdown</Header>}
          empty={<Box textAlign="center">No monthly data</Box>}
        />
      </SpaceBetween>
    );
  };

  // ============================================================================
  // RENDER MAIN COMPONENT
  // ============================================================================

  return (
    <>
      <GenAIIDPTopNavigation />
      <Box padding={{ horizontal: 'l', vertical: 'm' }}>
        <SpaceBetween size="l">
          <BreadcrumbGroup
            items={[
              { text: 'Company Select', href: `#${COMPANY_SELECT_PATH}` },
              { text: activeCompany.companyName, href: '#' },
              { text: 'Invoice Insights', href: `#${INVOICE_INSIGHTS_PATH}` },
              { text: 'Analysis Dashboard', href: '#' },
            ]}
            ariaLabel="Breadcrumbs"
          />

          {error && (
            <Flashbar
              items={[
                {
                  type: 'error',
                  content: error,
                  dismissible: true,
                  onDismiss: () => setError(null),
                },
              ]}
            />
          )}

          <Header
            variant="h1"
            description={`Tax compliance analysis for ${activeCompany.companyNumber}`}
            actions={
              <SpaceBetween direction="horizontal" size="s">
                <Button onClick={() => history.push(INVOICE_INSIGHTS_PATH)}>View All Invoices</Button>
                <Button iconName="refresh" onClick={loadInvoices}>
                  Refresh Data
                </Button>
              </SpaceBetween>
            }
          >
            Invoice Analysis: {activeCompany.companyName}
          </Header>

          <Tabs
            activeTabId={activeTab}
            onChange={({ detail }) => setActiveTab(detail.activeTabId)}
            tabs={[
              {
                id: 'overview',
                label: 'Executive Summary',
                content: renderOverviewTab(),
              },
              {
                id: 'actions',
                label: `Action Queue ${actionItems.length > 0 ? `(${actionItems.length})` : ''}`,
                content: renderActionQueueTab(),
              },
              {
                id: 'suppliers',
                label: 'Suppliers',
                content: renderSupplierTab(),
              },
              {
                id: 'vat',
                label: 'VAT & Types',
                content: renderVATTab(),
              },
              {
                id: 'trends',
                label: 'Trends',
                content: renderTrendsTab(),
              },
            ]}
          />
        </SpaceBetween>
      </Box>
    </>
  );
};

export default InvoiceAnalysisDashboard;
