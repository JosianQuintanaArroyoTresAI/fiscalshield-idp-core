// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
import React from 'react';
import {
  Drawer,
  SpaceBetween,
  Box,
  Header,
  ColumnLayout,
  Badge,
  ProgressBar,
  Container,
  ExpandableSection,
  Button,
  StatusIndicator,
} from '@awsui/components-react';

const TransactionDetailDrawer = ({ transaction, visible, onDismiss }) => {
  if (!transaction) return null;

  const rawData = transaction.rawData || {};
  const isAnalyzed = transaction.analysisStatus === 'ANALYZED';

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

  const getTierColor = (tier) => {
    const tierMap = {
      LOW: 'green',
      MEDIUM: 'blue',
      HIGH: 'red',
      CRITICAL: 'red',
    };
    return tierMap[tier] || 'grey';
  };

  return (
    <Drawer header={<Header variant="h2">Transaction Details</Header>} visible={visible} onDismiss={onDismiss}>
      <SpaceBetween size="l">
        {!isAnalyzed && (
          <Box color="text-status-inactive">
            <SpaceBetween size="s">
              <Box variant="p">This transaction has not been analyzed yet.</Box>
              <Box variant="small">
                Run transaction analysis to see detailed compliance information, categorization reasoning, and risk
                assessment.
              </Box>
            </SpaceBetween>
          </Box>
        )}

        {/* Transaction Overview */}
        <Container header={<Header variant="h3">Transaction Details</Header>}>
          <ColumnLayout columns={2} variant="text-grid">
            <div>
              <Box variant="awsui-key-label">Date</Box>
              <Box>{transaction.transactionDate}</Box>
            </div>
            <div>
              <Box variant="awsui-key-label">Amount</Box>
              <Box
                fontSize="heading-m"
                fontWeight="bold"
                color={transaction.transactionAmount >= 0 ? 'text-status-success' : 'text-status-error'}
              >
                {transaction.formattedAmount}
              </Box>
            </div>
            <div>
              <Box variant="awsui-key-label">Description</Box>
              <Box>{transaction.transactionDescription || 'N/A'}</Box>
            </div>
            <div>
              <Box variant="awsui-key-label">Reference</Box>
              <Box>{rawData.Reference || 'N/A'}</Box>
            </div>
            <div>
              <Box variant="awsui-key-label">Counterparty</Box>
              <Box>{rawData.CounterpartyName || 'N/A'}</Box>
            </div>
            <div>
              <Box variant="awsui-key-label">Country</Box>
              <Box>{rawData.CounterpartyCountry || 'N/A'}</Box>
            </div>
            <div>
              <Box variant="awsui-key-label">Payment Method</Box>
              <Badge>{rawData.PaymentMethod || 'N/A'}</Badge>
            </div>
            <div>
              <Box variant="awsui-key-label">Direction</Box>
              <Badge color={rawData.Direction === 'INBOUND' ? 'green' : 'blue'}>{rawData.Direction || 'N/A'}</Badge>
            </div>
            <div>
              <Box variant="awsui-key-label">Balance After</Box>
              <Box>{transaction.accountBalance}</Box>
            </div>
            <div>
              <Box variant="awsui-key-label">Transaction Type</Box>
              <Badge>{rawData.TransactionType || transaction.transactionType || 'N/A'}</Badge>
            </div>
          </ColumnLayout>
        </Container>

        {/* Compliance Assessment */}
        {isAnalyzed && (
          <Container header={<Header variant="h3">Compliance Assessment</Header>}>
            <SpaceBetween size="m">
              <ColumnLayout columns={3} variant="text-grid">
                <div>
                  <Box variant="awsui-key-label">Compliance Score</Box>
                  <SpaceBetween direction="horizontal" size="xs">
                    <Box
                      fontSize="heading-l"
                      fontWeight="bold"
                      color={`text-status-${getComplianceScoreColor(rawData.ComplianceScore)}`}
                    >
                      {rawData.ComplianceScore || '—'}/5
                    </Box>
                    {rawData.ComplianceScore && (
                      <ProgressBar
                        value={(rawData.ComplianceScore / 5) * 100}
                        variant={getComplianceScoreColor(rawData.ComplianceScore) === 'red' ? 'error' : undefined}
                        hideLabel
                      />
                    )}
                  </SpaceBetween>
                </div>
                <div>
                  <Box variant="awsui-key-label">Risk Tier</Box>
                  <Badge color={getTierColor(rawData.ComplianceRiskTier)}>
                    {rawData.ComplianceRiskTier || 'N/A'}
                  </Badge>
                </div>
                <div>
                  <Box variant="awsui-key-label">Risk Score</Box>
                  <Box fontSize="heading-m">{rawData.ComplianceRiskScore || '—'}/100</Box>
                </div>
              </ColumnLayout>

              <div>
                <Box variant="awsui-key-label">Recommended Action</Box>
                <Badge color={getRecommendedActionVariant(rawData.RecommendedAction)}>
                  {rawData.RecommendedAction?.replace(/_/g, ' ') || 'N/A'}
                </Badge>
              </div>

              <div>
                <Box variant="awsui-key-label">HMRC Concern</Box>
                <StatusIndicator type={rawData.HMRCConcern ? 'warning' : 'success'}>
                  {rawData.HMRCConcern ? 'Yes - Requires attention' : 'No concerns'}
                </StatusIndicator>
              </div>
            </SpaceBetween>
          </Container>
        )}

        {/* Categorization */}
        {isAnalyzed && rawData.ExpenseCategory && (
          <Container header={<Header variant="h3">Categorization</Header>}>
            <SpaceBetween size="m">
              <div>
                <Box variant="awsui-key-label">Category</Box>
                <Box fontSize="heading-s">{rawData.ExpenseCategory}</Box>
              </div>
              <div>
                <Box variant="awsui-key-label">Confidence</Box>
                <Badge color={rawData.CategorizationConfidence === 'HIGH' ? 'green' : 'blue'}>
                  {rawData.CategorizationConfidence || 'N/A'}
                </Badge>
              </div>
              {rawData.CategorizationReasoning && (
                <div>
                  <Box variant="awsui-key-label">AI Reasoning</Box>
                  <Box variant="p" color="text-body-secondary">
                    {rawData.CategorizationReasoning}
                  </Box>
                </div>
              )}
            </SpaceBetween>
          </Container>
        )}

        {/* Risk Flags */}
        {isAnalyzed && rawData.RiskFlags && rawData.RiskFlags.length > 0 && rawData.RiskFlags[0] !== 'CLEAN' && (
          <Container header={<Header variant="h3">Risk Flags</Header>}>
            <SpaceBetween size="s">
              <SpaceBetween direction="horizontal" size="xs">
                {rawData.RiskFlags.map((flag, idx) => (
                  <Badge key={idx} color="red">
                    {flag.replace(/_/g, ' ')}
                  </Badge>
                ))}
              </SpaceBetween>
            </SpaceBetween>
          </Container>
        )}

        {/* Compliance Details */}
        {isAnalyzed && (
          <ExpandableSection headerText="Compliance Details" defaultExpanded={false}>
            <SpaceBetween size="m">
              {rawData.ComplianceReasons && rawData.ComplianceReasons.length > 0 && (
                <div>
                  <Box variant="awsui-key-label">Compliance Notes</Box>
                  <ul style={{ margin: 0, paddingLeft: '20px' }}>
                    {rawData.ComplianceReasons.map((reason, idx) => (
                      <li key={idx}>
                        <Box variant="small">{reason}</Box>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <ColumnLayout columns={2} variant="text-grid">
                <div>
                  <Box variant="awsui-key-label">Threshold Flag</Box>
                  <Box>{rawData.ThresholdFlag || 'NONE'}</Box>
                </div>
                <div>
                  <Box variant="awsui-key-label">Cash Risk Flag</Box>
                  <Box>{rawData.CashRiskFlag || 'NONE'}</Box>
                </div>
                <div>
                  <Box variant="awsui-key-label">Geographic Risk Flag</Box>
                  <Box>{rawData.GeographicRiskFlag || 'NONE'}</Box>
                </div>
                <div>
                  <Box variant="awsui-key-label">Structuring Flag</Box>
                  <Box>{rawData.StructuringFlag || 'NONE'}</Box>
                </div>
                <div>
                  <Box variant="awsui-key-label">Vague Description Flag</Box>
                  <Box>{rawData.VagueDescriptionFlag || 'NONE'}</Box>
                </div>
              </ColumnLayout>
            </SpaceBetween>
          </ExpandableSection>
        )}

        {/* Extraction Quality */}
        {isAnalyzed && (
          <ExpandableSection headerText="Extraction Quality" defaultExpanded={false}>
            <SpaceBetween size="m">
              <div>
                <Box variant="awsui-key-label">Composite Confidence</Box>
                <SpaceBetween direction="horizontal" size="xs">
                  <Box fontSize="heading-m">{transaction.confidence}</Box>
                  <ProgressBar
                    value={rawData.CompositeConfidence ? rawData.CompositeConfidence * 100 : 0}
                    hideLabel
                  />
                </SpaceBetween>
              </div>
              <div>
                <Box variant="awsui-key-label">Quality Tier</Box>
                <Badge>{transaction.qualityTier}</Badge>
              </div>

              <ColumnLayout columns={2} variant="text-grid">
                <div>
                  <Box variant="awsui-key-label">Date Confidence</Box>
                  <ProgressBar value={(rawData.DateConfidence || 0) * 100} hideLabel />
                </div>
                <div>
                  <Box variant="awsui-key-label">Amount Confidence</Box>
                  <ProgressBar value={(rawData.AmountConfidence || 0) * 100} hideLabel />
                </div>
                <div>
                  <Box variant="awsui-key-label">Description Confidence</Box>
                  <ProgressBar value={(rawData.DescriptionConfidence || 0) * 100} hideLabel />
                </div>
                <div>
                  <Box variant="awsui-key-label">Account Info Confidence</Box>
                  <ProgressBar value={(rawData.AccountInfoConfidence || 0) * 100} hideLabel />
                </div>
              </ColumnLayout>
            </SpaceBetween>
          </ExpandableSection>
        )}

        {/* Source Document */}
        <ExpandableSection headerText="Source Document" defaultExpanded={false}>
          <ColumnLayout columns={2} variant="text-grid">
            <div>
              <Box variant="awsui-key-label">Bank</Box>
              <Box>{transaction.bankName}</Box>
            </div>
            <div>
              <Box variant="awsui-key-label">Account</Box>
              <Box>{transaction.accountNumber}</Box>
            </div>
            <div>
              <Box variant="awsui-key-label">Sort Code</Box>
              <Box>{transaction.sortCode}</Box>
            </div>
            <div>
              <Box variant="awsui-key-label">Source Page</Box>
              <Box>{rawData.SourcePage || transaction.sourcePage || 'N/A'}</Box>
            </div>
            <div>
              <Box variant="awsui-key-label">Processed Date</Box>
              <Box>{transaction.processedDate}</Box>
            </div>
          </ColumnLayout>

          {rawData.SourcePage && (
            <Box padding={{ top: 'm' }}>
              <Button iconName="external" variant="primary">
                View Source Document (Page {rawData.SourcePage})
              </Button>
            </Box>
          )}
        </ExpandableSection>

        {/* Metadata */}
        {isAnalyzed && (
          <ExpandableSection headerText="Metadata" defaultExpanded={false}>
            <ColumnLayout columns={2} variant="text-grid">
              <div>
                <Box variant="awsui-key-label">Analyzed At</Box>
                <Box>
                  {rawData.AnalyzedAt
                    ? new Date(rawData.AnalyzedAt * 1000).toLocaleString('en-GB')
                    : 'N/A'}
                </Box>
              </div>
              <div>
                <Box variant="awsui-key-label">Model Used</Box>
                <Box>{rawData.ModelUsed || 'N/A'}</Box>
              </div>
            </ColumnLayout>
          </ExpandableSection>
        )}

        {/* Action Buttons */}
        <SpaceBetween direction="horizontal" size="xs">
          <Button variant="normal">Edit Category</Button>
          <Button variant="normal">Flag for Review</Button>
          <Button variant="normal">Add Note</Button>
        </SpaceBetween>
      </SpaceBetween>
    </Drawer>
  );
};

export default TransactionDetailDrawer;
