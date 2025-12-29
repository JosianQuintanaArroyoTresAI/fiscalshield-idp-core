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
  ColumnLayout,
  Table,
  Badge,
  StatusIndicator,
  Button,
  ProgressBar,
  Popover,
  ExpandableSection,
  Link,
} from '@awsui/components-react';

import { useCompany } from '../../contexts/company';
import { COMPANY_SELECT_PATH, BANK_ANALYSIS_PATH } from '../../routes/constants';
import GenAIIDPTopNavigation from '../genai-idp-top-navigation';
import { fetchExtractionResults, formatBankStatementData, DOCUMENT_TYPES } from '../../services/extractionService';
import TransactionDetailDrawer from './TransactionDetailDrawer';

import '@awsui/global-styles/index.css';

const BankStatementInsights = () => {
  const history = useHistory();
  const { activeCompany, isCompanySelected } = useCompany();

  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('transactions');
  const [transactions, setTransactions] = useState([]);
  const [loadingTransactions, setLoadingTransactions] = useState(false);
  const [error, setError] = useState(null);
  const [expandedItems, setExpandedItems] = useState(new Set());
  const [selectedTransaction, setSelectedTransaction] = useState(null);

  useEffect(() => {
    // Redirect if no company selected
    if (!isCompanySelected) {
      history.push(COMPANY_SELECT_PATH);
      return;
    }

    setLoading(false);
    loadTransactions();
  }, [isCompanySelected, history, activeCompany]);

  const loadTransactions = async () => {
    if (!activeCompany?.companyNumber) return;

    setLoadingTransactions(true);
    setError(null);

    try {
      console.log('[BANK INSIGHTS] Loading transactions for:', activeCompany.companyNumber);
      const result = await fetchExtractionResults(activeCompany.companyNumber, DOCUMENT_TYPES.BANK_STATEMENT, 100);

      const formattedTransactions = result.items.map(formatBankStatementData);
      console.log('[BANK INSIGHTS] Loaded transactions:', formattedTransactions.length);
      console.log('[BANK INSIGHTS] First formatted transaction:', formattedTransactions[0]);
      console.log('[BANK INSIGHTS] First transaction rawData:', formattedTransactions[0]?.rawData);
      console.log('[BANK INSIGHTS] First transaction expenseCategory:', formattedTransactions[0]?.expenseCategory);
      console.log('[BANK INSIGHTS] First transaction complianceScore:', formattedTransactions[0]?.complianceScore);
      console.log('[BANK INSIGHTS] First transaction analysisStatus:', formattedTransactions[0]?.analysisStatus);
      setTransactions(formattedTransactions);
    } catch (err) {
      console.error('[BANK INSIGHTS] Error loading transactions:', err);
      setError(err.message || 'Failed to load transactions');
    } finally {
      setLoadingTransactions(false);
    }
  };

  if (loading) {
    return (
      <>
        <GenAIIDPTopNavigation />
        <Box textAlign="center" padding="xxl">
          <Spinner size="large" />
          <Box variant="p" color="text-body-secondary">
            Loading bank statement insights...
          </Box>
        </Box>
      </>
    );
  }

  if (!activeCompany) {
    return null;
  }

  const renderCashFlowTab = () => (
    <Container>
      <Alert type="info" header="Cash Flow Analysis Not Available">
        <SpaceBetween size="s">
          <Box>Cash flow analysis will be available once bank statement data is processed.</Box>
          <Box variant="small">This will include:</Box>
          <ul>
            <li>Monthly cash flow trends and patterns</li>
            <li>Income vs expenses breakdown</li>
            <li>Cash flow forecasting</li>
            <li>Seasonal variations and anomalies</li>
            <li>Working capital analysis</li>
          </ul>
        </SpaceBetween>
      </Alert>

      {/* Placeholder metrics */}
      <Box padding={{ top: 'l' }}>
        <ColumnLayout columns={3} variant="text-grid">
          <div>
            <Box variant="awsui-key-label">Average Monthly Inflow</Box>
            <Box fontSize="display-l" fontWeight="bold" color="text-status-inactive">
              --
            </Box>
          </div>
          <div>
            <Box variant="awsui-key-label">Average Monthly Outflow</Box>
            <Box fontSize="display-l" fontWeight="bold" color="text-status-inactive">
              --
            </Box>
          </div>
          <div>
            <Box variant="awsui-key-label">Net Cash Flow</Box>
            <Box fontSize="display-l" fontWeight="bold" color="text-status-inactive">
              --
            </Box>
          </div>
        </ColumnLayout>
      </Box>
    </Container>
  );

  const toggleExpanded = (itemId) => {
    const newExpanded = new Set(expandedItems);
    if (newExpanded.has(itemId)) {
      newExpanded.delete(itemId);
    } else {
      newExpanded.add(itemId);
    }
    setExpandedItems(newExpanded);
  };

  const renderExpandedContent = (item) => {
    if (item.analysisStatus !== 'ANALYZED') {
      return (
        <Box padding="l" color="text-body-secondary">
          <SpaceBetween size="s">
            <Box>This transaction has not been analyzed yet.</Box>
            <Box variant="small">
              Run transaction analysis to see detailed compliance information, categorization reasoning, and risk
              assessment.
            </Box>
          </SpaceBetween>
        </Box>
      );
    }

    const rawData = item.rawData || {};

    return (
      <Box padding="l" variant="div">
        <SpaceBetween size="m">
          {/* Transaction Summary */}
          <ColumnLayout columns={3} variant="text-grid">
            <div>
              <Box variant="awsui-key-label">Counterparty</Box>
              <Box>{rawData.CounterpartyName || 'N/A'}</Box>
            </div>
            <div>
              <Box variant="awsui-key-label">Payment Method</Box>
              <Badge>{rawData.PaymentMethod || 'N/A'}</Badge>
            </div>
            <div>
              <Box variant="awsui-key-label">Direction</Box>
              <Badge color={rawData.Direction === 'INBOUND' ? 'green' : 'blue'}>{rawData.Direction || 'N/A'}</Badge>
            </div>
          </ColumnLayout>

          {/* Categorization Reasoning */}
          {rawData.CategorizationReasoning && (
            <div>
              <Box variant="h4" padding={{ bottom: 'xs' }}>
                Categorization Reasoning
              </Box>
              <Box variant="p" color="text-body-secondary">
                {rawData.CategorizationReasoning}
              </Box>
            </div>
          )}

          {/* Risk Flags Detail */}
          {rawData.RiskFlags && rawData.RiskFlags.length > 0 && rawData.RiskFlags[0] !== 'CLEAN' && (
            <div>
              <Box variant="h4" padding={{ bottom: 'xs' }}>
                Risk Flags
              </Box>
              <SpaceBetween direction="horizontal" size="xs">
                {rawData.RiskFlags.map((flag, idx) => (
                  <Badge key={idx} color="red">
                    {flag.replace(/_/g, ' ')}
                  </Badge>
                ))}
              </SpaceBetween>
            </div>
          )}

          {/* Compliance Reasons */}
          {rawData.ComplianceReasons && rawData.ComplianceReasons.length > 0 && (
            <div>
              <Box variant="h4" padding={{ bottom: 'xs' }}>
                Compliance Notes
              </Box>
              <ul style={{ margin: 0, paddingLeft: '20px' }}>
                {rawData.ComplianceReasons.map((reason, idx) => (
                  <li key={idx}>
                    <Box variant="small">{reason}</Box>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Actions */}
          <SpaceBetween direction="horizontal" size="xs">
            <Button variant="primary" onClick={() => setSelectedTransaction(item)}>
              View Full Details
            </Button>
            {rawData.SourcePage && (
              <Button iconName="external">View Source Document (Page {rawData.SourcePage})</Button>
            )}
          </SpaceBetween>
        </SpaceBetween>
      </Box>
    );
  };

  const getComplianceScoreColor = (score) => {
    if (!score) return 'grey';
    if (score >= 4) return 'green';
    if (score >= 3) return 'blue';
    if (score >= 2) return 'grey';
    return 'red';
  };

  const getRecommendedActionVariant = (action) => {
    const actionMap = {
      APPROVE: 'success',
      REVIEW_DOCUMENTATION: 'warning',
      INVESTIGATE: 'warning',
      REJECT: 'error',
    };
    return actionMap[action] || 'info';
  };

  const renderRiskFlags = (flags) => {
    if (!flags || flags.length === 0 || (flags.length === 1 && flags[0] === 'CLEAN')) {
      return <Badge color="green">Clean</Badge>;
    }

    // Show first 2 flags, rest in popover
    const visibleFlags = flags.slice(0, 2);
    const hiddenFlags = flags.slice(2);

    return (
      <SpaceBetween direction="horizontal" size="xs">
        {visibleFlags.map((flag, idx) => (
          <Badge key={idx} color="red">
            {flag.replace(/_/g, ' ')}
          </Badge>
        ))}
        {hiddenFlags.length > 0 && (
          <Popover
            dismissButton={false}
            position="top"
            size="small"
            triggerType="custom"
            content={
              <SpaceBetween size="xs">
                {hiddenFlags.map((flag, idx) => (
                  <Badge key={idx} color="red">
                    {flag.replace(/_/g, ' ')}
                  </Badge>
                ))}
              </SpaceBetween>
            }
          >
            <Badge color="grey">+{hiddenFlags.length} more</Badge>
          </Popover>
        )}
      </SpaceBetween>
    );
  };

  const renderTransactionsTab = () => {
    if (loadingTransactions) {
      return (
        <Container>
          <Box textAlign="center" padding="l">
            <Spinner size="large" />
            <Box variant="p" color="text-body-secondary">
              Loading transactions...
            </Box>
          </Box>
        </Container>
      );
    }

    if (error) {
      return (
        <Container>
          <Alert type="error" header="Error Loading Transactions">
            {error}
          </Alert>
        </Container>
      );
    }

    if (transactions.length === 0) {
      return (
        <Container>
          <Alert type="info" header="No Transactions Found">
            <SpaceBetween size="s">
              <Box>No bank statement transactions found for this company.</Box>
              <Box variant="small">
                Upload bank statements to see transaction analysis, categorization, and compliance scoring.
              </Box>
            </SpaceBetween>
          </Alert>
        </Container>
      );
    }

    // Check if any transactions are pending analysis
    const pendingCount = transactions.filter((t) => t.analysisStatus !== 'ANALYZED').length;
    const analyzedCount = transactions.length - pendingCount;

    return (
      <SpaceBetween size="l">
        {pendingCount > 0 && (
          <Alert type="info" header={`${pendingCount} transaction${pendingCount > 1 ? 's' : ''} pending analysis`}>
            {analyzedCount > 0 ? (
              <Box>
                {analyzedCount} of {transactions.length} transactions have been analyzed. The remaining {pendingCount}{' '}
                will show compliance scores once analysis completes.
              </Box>
            ) : (
              <Box>
                Transactions are extracted but not yet analyzed for compliance. Run transaction analysis to see
                categories, compliance scores, and risk flags.
              </Box>
            )}
          </Alert>
        )}

        <Table
          columnDefinitions={[
            {
              id: 'expander',
              header: '',
              cell: (item) => (
                <Button
                  variant="icon"
                  iconName={expandedItems.has(item.id) ? 'angle-down' : 'angle-right'}
                  onClick={(e) => {
                    e.stopPropagation();
                    toggleExpanded(item.id);
                  }}
                />
              ),
              width: 50,
            },
            {
              id: 'date',
              header: 'Date',
              cell: (item) => item.transactionDate,
              sortingField: 'transactionDate',
              width: 100,
            },
            {
              id: 'description',
              header: 'Description',
              cell: (item) => item.transactionDescription || 'N/A',
              width: 250,
            },
            {
              id: 'category',
              header: 'Category',
              cell: (item) => {
                if (item.analysisStatus !== 'ANALYZED') {
                  return <Badge color="grey">Pending</Badge>;
                }
                return (
                  item.expenseCategory || (
                    <Box color="text-status-inactive" variant="small">
                      Uncategorized
                    </Box>
                  )
                );
              },
              width: 140,
            },
            {
              id: 'amount',
              header: 'Amount',
              cell: (item) => (
                <Box
                  color={item.transactionAmount >= 0 ? 'text-status-success' : 'text-status-error'}
                  fontWeight="bold"
                >
                  {item.formattedAmount}
                </Box>
              ),
              sortingField: 'transactionAmount',
              width: 110,
            },
            {
              id: 'complianceScore',
              header: 'Compliance',
              cell: (item) => {
                if (item.analysisStatus !== 'ANALYZED') {
                  return <Badge color="grey">Pending</Badge>;
                }

                const score = item.complianceScore;
                if (!score)
                  return (
                    <Box color="text-status-inactive" variant="small">
                      —
                    </Box>
                  );

                return (
                  <SpaceBetween direction="horizontal" size="xs">
                    <Box fontSize="body-m" fontWeight="bold" color={`text-status-${getComplianceScoreColor(score)}`}>
                      {score}/5
                    </Box>
                    <ProgressBar
                      value={(score / 5) * 100}
                      variant={getComplianceScoreColor(score) === 'red' ? 'error' : undefined}
                      additionalInfo=""
                      description=""
                      hideLabel
                    />
                  </SpaceBetween>
                );
              },
              width: 120,
            },
            {
              id: 'riskFlags',
              header: 'Risk Flags',
              cell: (item) => {
                if (item.analysisStatus !== 'ANALYZED') {
                  return <Badge color="grey">Pending</Badge>;
                }

                const flags = item.riskFlags;
                if (!flags) return <Badge color="green">Clean</Badge>;
                return renderRiskFlags(flags);
              },
              width: 200,
            },
            {
              id: 'recommendedAction',
              header: 'Recommended Action',
              cell: (item) => {
                if (item.analysisStatus !== 'ANALYZED') {
                  return <Badge color="grey">Pending</Badge>;
                }

                const action = item.recommendedAction;
                if (!action)
                  return (
                    <Box color="text-status-inactive" variant="small">
                      —
                    </Box>
                  );

                return <Badge color={getRecommendedActionVariant(action)}>{action.replace(/_/g, ' ')}</Badge>;
              },
              width: 150,
            },
            {
              id: 'analysisStatus',
              header: 'Status',
              cell: (item) => {
                const status = item.analysisStatus;
                if (status === 'ANALYZED') {
                  return <StatusIndicator type="success">Analyzed</StatusIndicator>;
                }
                return <StatusIndicator type="pending">Pending Analysis</StatusIndicator>;
              },
              width: 120,
            },
          ]}
          items={transactions}
          loadingText="Loading transactions"
          sortingDisabled={false}
          variant="container"
          expandableRows={{
            getItemChildren: (item) => {
              if (!expandedItems.has(item.id)) return [];
              return [{ content: renderExpandedContent(item) }];
            },
            isItemExpandable: () => true,
            expandedItems: Array.from(expandedItems).map((id) => transactions.find((t) => t.id === id)),
            onExpandableItemToggle: ({ detail }) => toggleExpanded(detail.item.id),
          }}
          empty={
            <Box textAlign="center" color="inherit">
              <b>No transactions</b>
              <Box padding={{ bottom: 's' }} variant="p" color="inherit">
                No transactions to display.
              </Box>
            </Box>
          }
          header={
            <Header
              counter={`(${transactions.length})`}
              description={analyzedCount > 0 ? `${analyzedCount} analyzed, ${pendingCount} pending` : undefined}
              actions={
                <Button iconName="refresh" onClick={loadTransactions}>
                  Refresh
                </Button>
              }
            >
              Bank Statement Transactions
            </Header>
          }
        />
      </SpaceBetween>
    );
  };

  const renderExpensesTab = () => (
    <Container>
      <Alert type="info" header="Expense Analysis Not Available">
        <SpaceBetween size="s">
          <Box>Expense breakdown and categorization will be available once bank statement data is processed.</Box>
          <Box variant="small">This will include:</Box>
          <ul>
            <li>Expense categories and trends</li>
            <li>Fixed vs variable costs</li>
            <li>Expense ratios and benchmarks</li>
            <li>Cost reduction opportunities</li>
            <li>Budget compliance monitoring</li>
          </ul>
        </SpaceBetween>
      </Alert>
    </Container>
  );

  return (
    <>
      <GenAIIDPTopNavigation />
      <SpaceBetween size="l">
        <BreadcrumbGroup
          items={[
            { text: 'Company Select', href: `#${COMPANY_SELECT_PATH}` },
            { text: activeCompany.companyName, href: '#' },
            { text: 'Bank Insights', href: '#' },
          ]}
          ariaLabel="Breadcrumbs"
        />

        <Header 
          variant="h1" 
          description={`Company Number: ${activeCompany.companyNumber}`}
          actions={
            <Button 
              variant="primary" 
              onClick={() => history.push(BANK_ANALYSIS_PATH)}
              iconName="status-positive"
            >
              Analysis Dashboard
            </Button>
          }
        >
          Bank Statement Insights: {activeCompany.companyName}
        </Header>

        <Tabs
          activeTabId={activeTab}
          onChange={({ detail }) => setActiveTab(detail.activeTabId)}
          tabs={[
            {
              id: 'transactions',
              label: 'Transactions',
              content: renderTransactionsTab(),
            },
            {
              id: 'cashflow',
              label: 'Cash Flow',
              content: renderCashFlowTab(),
            },
            {
              id: 'expenses',
              label: 'Expenses',
              content: renderExpensesTab(),
            },
          ]}
        />
      </SpaceBetween>

      {/* Transaction Detail Drawer */}
      <TransactionDetailDrawer
        transaction={selectedTransaction}
        visible={!!selectedTransaction}
        onDismiss={() => setSelectedTransaction(null)}
      />
    </>
  );
};

export default BankStatementInsights;
