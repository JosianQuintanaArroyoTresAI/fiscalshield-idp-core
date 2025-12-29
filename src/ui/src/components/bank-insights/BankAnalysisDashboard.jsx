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
  Alert,
  ProgressBar,
  Grid,
  Flashbar,
  Select,
  TextFilter,
  Pagination,
} from '@awsui/components-react';

import { useCompany } from '../../contexts/company';
import { COMPANY_SELECT_PATH, BANK_INSIGHTS_PATH } from '../../routes/constants';
import GenAIIDPTopNavigation from '../genai-idp-top-navigation';
import {
  fetchExtractionResults,
  formatBankStatementData,
  DOCUMENT_TYPES,
  formatCurrency,
} from '../../services/extractionService';

import '@awsui/global-styles/index.css';

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

const calculateBankAnalytics = (transactions) => {
  const analytics = {
    // Totals
    totalTransactions: 0,
    totalDebits: 0,
    totalCredits: 0,
    netCashFlow: 0,
    averageTransaction: 0,

    // Categories
    categorySpend: {},

    // Counterparties
    counterpartySpend: {},
    counterpartyCount: new Set(),

    // Transaction types
    byType: {},
    byPaymentMethod: {},

    // Actions & Compliance
    actionApprove: 0,
    actionReview: 0,
    actionInvestigate: 0,
    actionReject: 0,

    // Risk analysis
    complianceRiskTiers: { LOW: 0, MEDIUM: 0, HIGH: 0 },
    riskFlags: {
      cash: 0,
      threshold: 0,
      structuring: 0,
      geographic: 0,
      vagueDescription: 0,
    },

    // Direction
    inbound: { count: 0, amount: 0 },
    outbound: { count: 0, amount: 0 },

    // Banks & Accounts
    banks: new Set(),
    accounts: new Set(),

    // Monthly breakdown
    monthlyFlow: {},

    // Quality
    excellentQuality: 0,
    goodQuality: 0,
    acceptableQuality: 0,

    // HMRC concerns
    hmrcConcerns: [],
  };

  // Filter out statement summaries (only process transactions)
  const txnRecords = transactions.filter((t) => t.rawData?.TransactionId || t.rawData?.TransactionAmount);
  analytics.totalTransactions = txnRecords.length;

  txnRecords.forEach((txn) => {
    const rawData = txn.rawData || {};
    const amount = parseFloat(rawData.TransactionAmount) || 0;
    const absAmount = Math.abs(amount);

    // Debits vs Credits
    if (amount < 0) {
      analytics.totalDebits += absAmount;
      analytics.outbound.count++;
      analytics.outbound.amount += absAmount;
    } else if (amount > 0) {
      analytics.totalCredits += amount;
      analytics.inbound.count++;
      analytics.inbound.amount += amount;
    }

    // Category breakdown
    const category = rawData.ExpenseCategory || 'Uncategorized';
    if (!analytics.categorySpend[category]) {
      analytics.categorySpend[category] = { amount: 0, count: 0 };
    }
    if (amount < 0) {
      analytics.categorySpend[category].amount += absAmount;
      analytics.categorySpend[category].count++;
    }

    // Counterparty breakdown
    const counterparty = rawData.CounterpartyName || 'Unknown';
    if (!analytics.counterpartySpend[counterparty]) {
      analytics.counterpartySpend[counterparty] = { amount: 0, count: 0, category: category };
    }
    if (amount < 0) {
      analytics.counterpartySpend[counterparty].amount += absAmount;
      analytics.counterpartySpend[counterparty].count++;
    }
    analytics.counterpartyCount.add(counterparty);

    // Transaction type
    const txnType = rawData.TransactionType || 'OTHER';
    if (!analytics.byType[txnType]) {
      analytics.byType[txnType] = { count: 0, amount: 0 };
    }
    analytics.byType[txnType].count++;
    analytics.byType[txnType].amount += absAmount;

    // Payment method
    const paymentMethod = rawData.PaymentMethod || 'OTHER';
    if (!analytics.byPaymentMethod[paymentMethod]) {
      analytics.byPaymentMethod[paymentMethod] = { count: 0, amount: 0 };
    }
    analytics.byPaymentMethod[paymentMethod].count++;
    analytics.byPaymentMethod[paymentMethod].amount += absAmount;

    // Recommended actions
    const action = rawData.RecommendedAction;
    if (action === 'APPROVE') analytics.actionApprove++;
    else if (action === 'REVIEW_DOCUMENTATION') analytics.actionReview++;
    else if (action === 'INVESTIGATE') analytics.actionInvestigate++;
    else if (action === 'REJECT') analytics.actionReject++;

    // Compliance risk tiers
    const riskTier = rawData.ComplianceRiskTier || 'LOW';
    analytics.complianceRiskTiers[riskTier] = (analytics.complianceRiskTiers[riskTier] || 0) + 1;

    // Risk flags
    if (rawData.CashRiskFlag && rawData.CashRiskFlag !== 'NONE') analytics.riskFlags.cash++;
    if (rawData.ThresholdFlag && rawData.ThresholdFlag !== 'NONE') analytics.riskFlags.threshold++;
    if (rawData.StructuringFlag && rawData.StructuringFlag !== 'NONE') analytics.riskFlags.structuring++;
    if (rawData.GeographicRiskFlag && rawData.GeographicRiskFlag !== 'NONE') analytics.riskFlags.geographic++;
    if (rawData.VagueDescriptionFlag && rawData.VagueDescriptionFlag !== 'NONE') analytics.riskFlags.vagueDescription++;

    // Banks & accounts
    if (rawData.BankName) analytics.banks.add(rawData.BankName);
    if (rawData.AccountNumber) analytics.accounts.add(rawData.AccountNumber);

    // Monthly breakdown
    const txnDate = rawData.TransactionDate;
    if (txnDate) {
      const month = txnDate.substring(0, 7); // YYYY-MM
      if (!analytics.monthlyFlow[month]) {
        analytics.monthlyFlow[month] = { debits: 0, credits: 0, count: 0 };
      }
      analytics.monthlyFlow[month].count++;
      if (amount < 0) {
        analytics.monthlyFlow[month].debits += absAmount;
      } else {
        analytics.monthlyFlow[month].credits += amount;
      }
    }

    // Quality
    const quality = rawData.QualityTier;
    if (quality === 'EXCELLENT') analytics.excellentQuality++;
    else if (quality === 'GOOD') analytics.goodQuality++;
    else if (quality === 'ACCEPTABLE') analytics.acceptableQuality++;

    // HMRC concerns
    if (rawData.HMRCConcern && rawData.HMRCConcern !== 'false' && rawData.HMRCConcern !== false) {
      analytics.hmrcConcerns.push({
        counterparty,
        amount,
        description: rawData.TransactionDescription,
        concern: rawData.HMRCConcern,
        category,
      });
    }
  });

  // Net cash flow
  analytics.netCashFlow = analytics.totalCredits - analytics.totalDebits;

  // Average
  if (analytics.totalTransactions > 0) {
    analytics.averageTransaction = (analytics.totalDebits + analytics.totalCredits) / analytics.totalTransactions;
  }

  return analytics;
};

// ============================================================================
// METRIC CARD COMPONENT
// ============================================================================

const MetricCard = ({ title, value, description, variant = 'default' }) => {
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
          {title}
        </Box>
        <Box fontSize="display-l" fontWeight="bold">
          {value}
        </Box>
        {description && (
          <Box variant="small" color={getVariantColor()}>
            {description}
          </Box>
        )}
      </SpaceBetween>
    </Container>
  );
};

// ============================================================================
// MAIN COMPONENT
// ============================================================================

const BankAnalysisDashboard = () => {
  const history = useHistory();
  const { activeCompany, isCompanySelected } = useCompany();

  const [loading, setLoading] = useState(true);
  const [transactions, setTransactions] = useState([]);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');

  // Table state
  const [filterText, setFilterText] = useState('');
  const [selectedActionFilter, setSelectedActionFilter] = useState(null);
  const [selectedCategoryFilter, setSelectedCategoryFilter] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 20;

  useEffect(() => {
    if (!isCompanySelected) {
      history.push(COMPANY_SELECT_PATH);
      return;
    }

    loadTransactions();
  }, [isCompanySelected, activeCompany]);

  const loadTransactions = async () => {
    if (!activeCompany?.companyNumber) return;

    setLoading(true);
    setError(null);

    try {
      console.log('[BANK ANALYSIS] Loading transactions for:', activeCompany.companyNumber);
      const result = await fetchExtractionResults(activeCompany.companyNumber, DOCUMENT_TYPES.BANK_STATEMENT, 500);

      const formattedTransactions = result.items.map(formatBankStatementData);
      console.log('[BANK ANALYSIS] Loaded transactions:', formattedTransactions.length);
      setTransactions(formattedTransactions);
    } catch (err) {
      console.error('[BANK ANALYSIS] Error loading transactions:', err);
      setError(err.message || 'Failed to load transactions');
    } finally {
      setLoading(false);
    }
  };

  // Calculate analytics
  const analytics = useMemo(() => calculateBankAnalytics(transactions), [transactions]);

  // Filter transactions for review queue
  const reviewItems = useMemo(() => {
    return transactions.filter((txn) => {
      const rawData = txn.rawData || {};
      // Only include actual transactions, not summaries
      if (!rawData.TransactionId) return false;

      const action = rawData.RecommendedAction;

      // Apply filters
      if (selectedActionFilter && action !== selectedActionFilter.value) return false;
      if (selectedCategoryFilter && rawData.ExpenseCategory !== selectedCategoryFilter.value) return false;
      if (filterText) {
        const searchLower = filterText.toLowerCase();
        const counterparty = (rawData.CounterpartyName || '').toLowerCase();
        const desc = (rawData.TransactionDescription || '').toLowerCase();
        if (!counterparty.includes(searchLower) && !desc.includes(searchLower)) return false;
      }

      return action === 'REVIEW_DOCUMENTATION' || action === 'INVESTIGATE' || action === 'REJECT';
    });
  }, [transactions, filterText, selectedActionFilter, selectedCategoryFilter]);

  // Paginated review items
  const paginatedReviewItems = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return reviewItems.slice(start, start + pageSize);
  }, [reviewItems, currentPage, pageSize]);

  // Top categories sorted by spend
  const topCategories = useMemo(() => {
    return Object.entries(analytics.categorySpend)
      .map(([name, data]) => ({ name, ...data }))
      .sort((a, b) => b.amount - a.amount)
      .slice(0, 15);
  }, [analytics]);

  // Top counterparties sorted by spend
  const topCounterparties = useMemo(() => {
    return Object.entries(analytics.counterpartySpend)
      .map(([name, data]) => ({ name, ...data }))
      .sort((a, b) => b.amount - a.amount)
      .slice(0, 15);
  }, [analytics]);

  // Monthly data for chart
  const monthlyChartData = useMemo(() => {
    return Object.entries(analytics.monthlyFlow)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([month, data]) => ({
        x: month,
        debits: data.debits,
        credits: data.credits,
        net: data.credits - data.debits,
      }));
  }, [analytics]);

  // Category options for filter
  const categoryOptions = useMemo(() => {
    const cats = Object.keys(analytics.categorySpend);
    return [{ label: 'All Categories', value: null }, ...cats.map((c) => ({ label: c, value: c }))];
  }, [analytics]);

  if (loading) {
    return (
      <>
        <GenAIIDPTopNavigation />
        <Box textAlign="center" padding="xxl">
          <Spinner size="large" />
          <Box variant="p" color="text-body-secondary">
            Loading bank statement analysis dashboard...
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
    const totalRiskFlags = Object.values(analytics.riskFlags).reduce((a, b) => a + b, 0);

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
            title="Total Outflow"
            value={formatCurrency(analytics.totalDebits, 'GBP')}
            description={`${analytics.outbound.count} outbound transactions`}
            variant="error"
          />
          <MetricCard
            title="Total Inflow"
            value={formatCurrency(analytics.totalCredits, 'GBP')}
            description={`${analytics.inbound.count} inbound transactions`}
            variant="success"
          />
          <MetricCard
            title="Net Cash Flow"
            value={formatCurrency(analytics.netCashFlow, 'GBP')}
            description={analytics.netCashFlow >= 0 ? 'Positive flow' : 'Negative flow'}
            variant={analytics.netCashFlow >= 0 ? 'success' : 'warning'}
          />
          <MetricCard
            title="Transactions"
            value={analytics.totalTransactions.toString()}
            description={`${analytics.counterpartyCount.size} unique counterparties`}
          />
        </Grid>

        {/* Bank Account Info */}
        <Container header={<Header variant="h3">Account Overview</Header>}>
          <ColumnLayout columns={4} variant="text-grid">
            <div>
              <Box variant="awsui-key-label">Banks</Box>
              <Box fontSize="heading-xl" fontWeight="bold">
                {analytics.banks.size}
              </Box>
              <Box variant="small">{Array.from(analytics.banks).join(', ') || 'N/A'}</Box>
            </div>
            <div>
              <Box variant="awsui-key-label">Accounts</Box>
              <Box fontSize="heading-xl" fontWeight="bold">
                {analytics.accounts.size}
              </Box>
            </div>
            <div>
              <Box variant="awsui-key-label">Avg Transaction</Box>
              <Box fontSize="heading-xl" fontWeight="bold">
                {formatCurrency(analytics.averageTransaction, 'GBP')}
              </Box>
            </div>
            <div>
              <Box variant="awsui-key-label">Unique Counterparties</Box>
              <Box fontSize="heading-xl" fontWeight="bold">
                {analytics.counterpartyCount.size}
              </Box>
            </div>
          </ColumnLayout>
        </Container>

        {/* Spending by Category & Actions */}
        <ColumnLayout columns={2} variant="text-grid">
          <Container header={<Header variant="h3">Spending by Category</Header>}>
            <PieChart
              data={topCategories.slice(0, 8).map((cat, idx) => ({
                title: cat.name,
                value: cat.amount,
              }))}
              detailPopoverContent={(datum, sum) => [
                { key: 'Amount', value: formatCurrency(datum.value, 'GBP') },
                { key: 'Percentage', value: `${((datum.value / sum) * 100).toFixed(1)}%` },
              ]}
              segmentDescription={(datum, sum) =>
                `${formatCurrency(datum.value, 'GBP')} (${((datum.value / sum) * 100).toFixed(0)}%)`
              }
              size="medium"
              hideFilter
              hideLegend={false}
              legendTitle="Category"
              empty={<Box textAlign="center">No data</Box>}
            />
          </Container>

          <Container header={<Header variant="h3">Review Actions Required</Header>}>
            <SpaceBetween size="m">
              <Box>
                <Box variant="awsui-key-label">✓ Approve</Box>
                <ProgressBar
                  value={analytics.actionApprove}
                  additionalInfo={`${analytics.actionApprove} transactions`}
                  status="success"
                />
              </Box>
              <Box>
                <Box variant="awsui-key-label">📄 Review Documentation</Box>
                <ProgressBar
                  value={analytics.actionReview}
                  additionalInfo={`${analytics.actionReview} transactions`}
                  status="in-progress"
                />
              </Box>
              <Box>
                <Box variant="awsui-key-label">🔍 Investigate</Box>
                <ProgressBar
                  value={analytics.actionInvestigate}
                  additionalInfo={`${analytics.actionInvestigate} transactions`}
                  status="error"
                />
              </Box>
              <Box>
                <Box variant="awsui-key-label">✗ Reject</Box>
                <ProgressBar
                  value={analytics.actionReject}
                  additionalInfo={`${analytics.actionReject} transactions`}
                  status="error"
                />
              </Box>
            </SpaceBetween>
          </Container>
        </ColumnLayout>

        {/* Risk Flags Summary */}
        <Container header={<Header variant="h3">Compliance & Risk Flags</Header>}>
          <ColumnLayout columns={5} variant="text-grid">
            <div>
              <Box variant="awsui-key-label">💵 Cash Risk</Box>
              <Box
                fontSize="heading-xl"
                fontWeight="bold"
                color={analytics.riskFlags.cash > 0 ? 'text-status-error' : 'text-status-success'}
              >
                {analytics.riskFlags.cash}
              </Box>
            </div>
            <div>
              <Box variant="awsui-key-label">📊 Threshold</Box>
              <Box
                fontSize="heading-xl"
                fontWeight="bold"
                color={analytics.riskFlags.threshold > 0 ? 'text-status-error' : 'text-status-success'}
              >
                {analytics.riskFlags.threshold}
              </Box>
            </div>
            <div>
              <Box variant="awsui-key-label">🔄 Structuring</Box>
              <Box
                fontSize="heading-xl"
                fontWeight="bold"
                color={analytics.riskFlags.structuring > 0 ? 'text-status-error' : 'text-status-success'}
              >
                {analytics.riskFlags.structuring}
              </Box>
            </div>
            <div>
              <Box variant="awsui-key-label">🌍 Geographic</Box>
              <Box
                fontSize="heading-xl"
                fontWeight="bold"
                color={analytics.riskFlags.geographic > 0 ? 'text-status-error' : 'text-status-success'}
              >
                {analytics.riskFlags.geographic}
              </Box>
            </div>
            <div>
              <Box variant="awsui-key-label">❓ Vague Description</Box>
              <Box
                fontSize="heading-xl"
                fontWeight="bold"
                color={analytics.riskFlags.vagueDescription > 0 ? 'text-status-warning' : 'text-status-success'}
              >
                {analytics.riskFlags.vagueDescription}
              </Box>
            </div>
          </ColumnLayout>
          {totalRiskFlags === 0 && (
            <Box padding={{ top: 'm' }}>
              <StatusIndicator type="success">No risk flags detected across all transactions</StatusIndicator>
            </Box>
          )}
        </Container>

        {/* Extraction Quality */}
        <Container header={<Header variant="h3">Extraction Quality</Header>}>
          <ColumnLayout columns={3} variant="text-grid">
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
          </ColumnLayout>
        </Container>
      </SpaceBetween>
    );
  };

  // ============================================================================
  // TAB: REVIEW QUEUE
  // ============================================================================

  const renderReviewQueueTab = () => {
    const actionOptions = [
      { label: 'All Actions', value: null },
      { label: 'Review Documentation', value: 'REVIEW_DOCUMENTATION' },
      { label: 'Investigate', value: 'INVESTIGATE' },
      { label: 'Reject', value: 'REJECT' },
    ];

    return (
      <SpaceBetween size="l">
        {reviewItems.length === 0 ? (
          <Alert type="success" header="No Items Require Review">
            All transactions have been approved or are awaiting initial review.
          </Alert>
        ) : (
          <Alert type="warning" header={`${reviewItems.length} Transactions Require Attention`}>
            These transactions have been flagged for documentation review, investigation, or rejection.
          </Alert>
        )}

        <Table
          columnDefinitions={[
            {
              id: 'date',
              header: 'Date',
              cell: (item) => item.rawData?.TransactionDate || 'N/A',
              width: 100,
              sortingField: 'date',
            },
            {
              id: 'counterparty',
              header: 'Counterparty',
              cell: (item) => item.rawData?.CounterpartyName || 'Unknown',
              width: 180,
              sortingField: 'counterparty',
            },
            {
              id: 'amount',
              header: 'Amount',
              cell: (item) => {
                const amt = parseFloat(item.rawData?.TransactionAmount) || 0;
                const color = amt < 0 ? 'text-status-error' : 'text-status-success';
                return <Box color={color}>{formatCurrency(amt, 'GBP')}</Box>;
              },
              width: 110,
              sortingField: 'amount',
            },
            {
              id: 'category',
              header: 'Category',
              cell: (item) => <Badge>{item.rawData?.ExpenseCategory || 'Uncategorized'}</Badge>,
              width: 180,
            },
            {
              id: 'description',
              header: 'Description',
              cell: (item) => (
                <Box variant="small">
                  {(item.rawData?.TransactionDescription || 'N/A').substring(0, 50)}
                  {(item.rawData?.TransactionDescription || '').length > 50 ? '...' : ''}
                </Box>
              ),
              width: 200,
            },
            {
              id: 'action',
              header: 'Action',
              cell: (item) => {
                const action = item.rawData?.RecommendedAction;
                const icons = {
                  APPROVE: <StatusIndicator type="success">Approve</StatusIndicator>,
                  REVIEW_DOCUMENTATION: <StatusIndicator type="warning">Review Docs</StatusIndicator>,
                  INVESTIGATE: <StatusIndicator type="error">Investigate</StatusIndicator>,
                  REJECT: <StatusIndicator type="error">Reject</StatusIndicator>,
                };
                return icons[action] || <StatusIndicator type="pending">Pending</StatusIndicator>;
              },
              width: 130,
            },
            {
              id: 'reasoning',
              header: 'Reasoning',
              cell: (item) => (
                <Box variant="small" color="text-body-secondary">
                  {(item.rawData?.CategorizationReasoning || 'N/A').substring(0, 80)}
                  {(item.rawData?.CategorizationReasoning || '').length > 80 ? '...' : ''}
                </Box>
              ),
              minWidth: 200,
            },
          ]}
          items={paginatedReviewItems}
          loadingText="Loading review items"
          sortingDisabled={false}
          variant="container"
          stickyHeader
          filter={
            <SpaceBetween direction="horizontal" size="s">
              <TextFilter
                filteringText={filterText}
                filteringPlaceholder="Search counterparty or description"
                onChange={({ detail }) => {
                  setFilterText(detail.filteringText);
                  setCurrentPage(1);
                }}
              />
              <Select
                selectedOption={selectedActionFilter || actionOptions[0]}
                onChange={({ detail }) => {
                  setSelectedActionFilter(detail.selectedOption.value ? detail.selectedOption : null);
                  setCurrentPage(1);
                }}
                options={actionOptions}
                placeholder="Filter by action"
              />
              <Select
                selectedOption={selectedCategoryFilter || categoryOptions[0]}
                onChange={({ detail }) => {
                  setSelectedCategoryFilter(detail.selectedOption.value ? detail.selectedOption : null);
                  setCurrentPage(1);
                }}
                options={categoryOptions}
                placeholder="Filter by category"
              />
            </SpaceBetween>
          }
          pagination={
            <Pagination
              currentPageIndex={currentPage}
              pagesCount={Math.ceil(reviewItems.length / pageSize)}
              onChange={({ detail }) => setCurrentPage(detail.currentPageIndex)}
            />
          }
          empty={
            <Box textAlign="center" color="inherit">
              <b>No review items</b>
              <Box padding={{ bottom: 's' }} variant="p" color="inherit">
                No transactions match the current filters.
              </Box>
            </Box>
          }
          header={
            <Header
              counter={`(${reviewItems.length})`}
              description="Transactions requiring documentation review or investigation"
              actions={
                <Button iconName="refresh" onClick={loadTransactions}>
                  Refresh
                </Button>
              }
            >
              Review Queue
            </Header>
          }
        />
      </SpaceBetween>
    );
  };

  // ============================================================================
  // TAB: CATEGORY ANALYSIS
  // ============================================================================

  const renderCategoryTab = () => {
    return (
      <SpaceBetween size="l">
        <Container header={<Header variant="h3">Category Summary</Header>}>
          <ColumnLayout columns={3} variant="text-grid">
            <div>
              <Box variant="awsui-key-label">Unique Categories</Box>
              <Box fontSize="display-l" fontWeight="bold">
                {Object.keys(analytics.categorySpend).length}
              </Box>
            </div>
            <div>
              <Box variant="awsui-key-label">Top Category</Box>
              <Box fontSize="display-l" fontWeight="bold">
                {topCategories[0]?.name || 'N/A'}
              </Box>
              <Box variant="small">{formatCurrency(topCategories[0]?.amount || 0, 'GBP')}</Box>
            </div>
            <div>
              <Box variant="awsui-key-label">Total Categorized Spend</Box>
              <Box fontSize="display-l" fontWeight="bold">
                {formatCurrency(analytics.totalDebits, 'GBP')}
              </Box>
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
              id: 'category',
              header: 'Category',
              cell: (item) => <Badge>{item.name}</Badge>,
              width: 280,
              sortingField: 'name',
            },
            {
              id: 'transactions',
              header: 'Transactions',
              cell: (item) => item.count,
              width: 120,
              sortingField: 'count',
            },
            {
              id: 'totalSpend',
              header: 'Total Spend',
              cell: (item) => formatCurrency(item.amount, 'GBP'),
              width: 140,
              sortingField: 'amount',
            },
            {
              id: 'avgTxn',
              header: 'Avg Transaction',
              cell: (item) => formatCurrency(item.count > 0 ? item.amount / item.count : 0, 'GBP'),
              width: 140,
            },
            {
              id: 'pctOfTotal',
              header: '% of Total',
              cell: (item) => {
                const pct = analytics.totalDebits > 0 ? (item.amount / analytics.totalDebits) * 100 : 0;
                return `${pct.toFixed(1)}%`;
              },
              width: 100,
            },
          ]}
          items={topCategories}
          sortingDisabled={false}
          variant="container"
          header={
            <Header counter={`(${topCategories.length})`} description="Spending breakdown by expense category">
              Category Breakdown
            </Header>
          }
          empty={
            <Box textAlign="center" color="inherit">
              <b>No category data</b>
            </Box>
          }
        />
      </SpaceBetween>
    );
  };

  // ============================================================================
  // TAB: COUNTERPARTY ANALYSIS
  // ============================================================================

  const renderCounterpartyTab = () => {
    return (
      <SpaceBetween size="l">
        <Container header={<Header variant="h3">Counterparty Summary</Header>}>
          <ColumnLayout columns={3} variant="text-grid">
            <div>
              <Box variant="awsui-key-label">Unique Counterparties</Box>
              <Box fontSize="display-l" fontWeight="bold">
                {analytics.counterpartyCount.size}
              </Box>
            </div>
            <div>
              <Box variant="awsui-key-label">Top Counterparty</Box>
              <Box fontSize="display-l" fontWeight="bold">
                {topCounterparties[0]?.name || 'N/A'}
              </Box>
              <Box variant="small">{formatCurrency(topCounterparties[0]?.amount || 0, 'GBP')}</Box>
            </div>
            <div>
              <Box variant="awsui-key-label">Avg per Counterparty</Box>
              <Box fontSize="display-l" fontWeight="bold">
                {formatCurrency(analytics.totalDebits / Math.max(analytics.counterpartyCount.size, 1), 'GBP')}
              </Box>
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
              id: 'counterparty',
              header: 'Counterparty',
              cell: (item) => item.name,
              width: 250,
              sortingField: 'name',
            },
            {
              id: 'transactions',
              header: 'Transactions',
              cell: (item) => item.count,
              width: 120,
              sortingField: 'count',
            },
            {
              id: 'totalSpend',
              header: 'Total Spend',
              cell: (item) => formatCurrency(item.amount, 'GBP'),
              width: 140,
              sortingField: 'amount',
            },
            {
              id: 'category',
              header: 'Category',
              cell: (item) => <Badge color="grey">{item.category}</Badge>,
              width: 180,
            },
            {
              id: 'avgTxn',
              header: 'Avg Transaction',
              cell: (item) => formatCurrency(item.count > 0 ? item.amount / item.count : 0, 'GBP'),
              width: 140,
            },
          ]}
          items={topCounterparties}
          sortingDisabled={false}
          variant="container"
          header={
            <Header counter={`(${topCounterparties.length})`} description="Top counterparties by total spend">
              Counterparty Breakdown
            </Header>
          }
          empty={
            <Box textAlign="center" color="inherit">
              <b>No counterparty data</b>
            </Box>
          }
        />
      </SpaceBetween>
    );
  };

  // ============================================================================
  // TAB: CASH FLOW TRENDS
  // ============================================================================

  const renderTrendsTab = () => {
    return (
      <SpaceBetween size="l">
        <Container header={<Header variant="h3">Monthly Cash Flow Trend</Header>}>
          {monthlyChartData.length > 0 ? (
            <BarChart
              series={[
                {
                  title: 'Outflow (Debits)',
                  type: 'bar',
                  data: monthlyChartData.map((d) => ({ x: d.x, y: d.debits })),
                  color: '#d91515',
                },
                {
                  title: 'Inflow (Credits)',
                  type: 'bar',
                  data: monthlyChartData.map((d) => ({ x: d.x, y: d.credits })),
                  color: '#1d8102',
                },
              ]}
              xDomain={monthlyChartData.map((d) => d.x)}
              yDomain={[0, Math.max(...monthlyChartData.map((d) => Math.max(d.debits, d.credits))) * 1.1]}
              xTitle="Month"
              yTitle="Amount (£)"
              hideFilter
              height={300}
              empty={<Box textAlign="center">No trend data available</Box>}
            />
          ) : (
            <Alert type="info">
              Not enough data to display monthly trends. Process more bank statements to see patterns.
            </Alert>
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
              header: 'Transactions',
              cell: (item) => analytics.monthlyFlow[item.x]?.count || 0,
              width: 120,
            },
            {
              id: 'debits',
              header: 'Outflow',
              cell: (item) => <Box color="text-status-error">{formatCurrency(item.debits, 'GBP')}</Box>,
              width: 140,
            },
            {
              id: 'credits',
              header: 'Inflow',
              cell: (item) => <Box color="text-status-success">{formatCurrency(item.credits, 'GBP')}</Box>,
              width: 140,
            },
            {
              id: 'net',
              header: 'Net Flow',
              cell: (item) => {
                const color = item.net >= 0 ? 'text-status-success' : 'text-status-error';
                return <Box color={color}>{formatCurrency(item.net, 'GBP')}</Box>;
              },
              width: 140,
            },
          ]}
          items={monthlyChartData}
          variant="container"
          header={<Header variant="h3">Monthly Breakdown</Header>}
          empty={<Box textAlign="center">No monthly data</Box>}
        />

        {/* Payment Methods */}
        <Container header={<Header variant="h3">Payment Methods</Header>}>
          <Table
            columnDefinitions={[
              {
                id: 'method',
                header: 'Payment Method',
                cell: (item) => <Badge>{item.method}</Badge>,
                width: 180,
              },
              {
                id: 'count',
                header: 'Transactions',
                cell: (item) => item.count,
                width: 120,
              },
              {
                id: 'amount',
                header: 'Total Amount',
                cell: (item) => formatCurrency(item.amount, 'GBP'),
                width: 150,
              },
              {
                id: 'pct',
                header: '% of Transactions',
                cell: (item) => {
                  const pct = analytics.totalTransactions > 0 ? (item.count / analytics.totalTransactions) * 100 : 0;
                  return `${pct.toFixed(1)}%`;
                },
                width: 140,
              },
            ]}
            items={Object.entries(analytics.byPaymentMethod).map(([method, data]) => ({ method, ...data }))}
            variant="embedded"
            empty={<Box textAlign="center">No data</Box>}
          />
        </Container>
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
              { text: 'Bank Insights', href: `#${BANK_INSIGHTS_PATH}` },
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
            description={`Transaction analysis for ${activeCompany.companyNumber}`}
            actions={
              <SpaceBetween direction="horizontal" size="s">
                <Button onClick={() => history.push(BANK_INSIGHTS_PATH)}>View All Transactions</Button>
                <Button iconName="refresh" onClick={loadTransactions}>
                  Refresh Data
                </Button>
              </SpaceBetween>
            }
          >
            Bank Statement Analysis: {activeCompany.companyName}
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
                id: 'review',
                label: `Review Queue ${reviewItems.length > 0 ? `(${reviewItems.length})` : ''}`,
                content: renderReviewQueueTab(),
              },
              {
                id: 'categories',
                label: 'Categories',
                content: renderCategoryTab(),
              },
              {
                id: 'counterparties',
                label: 'Counterparties',
                content: renderCounterpartyTab(),
              },
              {
                id: 'trends',
                label: 'Cash Flow',
                content: renderTrendsTab(),
              },
            ]}
          />
        </SpaceBetween>
      </Box>
    </>
  );
};

export default BankAnalysisDashboard;
