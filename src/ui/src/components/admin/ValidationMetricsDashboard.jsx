// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Validation Metrics Dashboard - Admin Only
 *
 * Displays classification validation metrics including:
 * - User vs Model agreement rates
 * - Confidence calibration
 * - High-confidence mismatches requiring attention
 */

import React, { useState, useEffect } from 'react';
import {
  Container,
  Header,
  SpaceBetween,
  Box,
  ColumnLayout,
  KeyValuePairs,
  Table,
  Badge,
  ProgressBar,
  Select,
  Alert,
  Spinner,
  Button,
  StatusIndicator,
} from '@awsui/components-react';
import { API, graphqlOperation, Logger } from 'aws-amplify';
import getValidationMetrics from '../../graphql/queries/getValidationMetrics';

const logger = new Logger('ValidationMetricsDashboard');

const ValidationMetricsDashboard = () => {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [timeRange, setTimeRange] = useState({ label: 'Last 30 days', value: '30' });

  const timeRangeOptions = [
    { label: 'Last 7 days', value: '7' },
    { label: 'Last 30 days', value: '30' },
    { label: 'Last 90 days', value: '90' },
    { label: 'Last 180 days', value: '180' },
  ];

  const fetchMetrics = async () => {
    console.log('[ValidationMetrics] fetchMetrics called, timeRange:', timeRange);
    setLoading(true);
    setError(null);

    try {
      console.log('[ValidationMetrics] Calling API.graphql...');
      const response = await API.graphql(
        graphqlOperation(getValidationMetrics, {
          timeRangeDays: parseInt(timeRange.value),
        }),
      );

      console.log('[ValidationMetrics] API response:', response);
      const metricsData = response.data.getValidationMetrics;
      console.log('[ValidationMetrics] Metrics data:', metricsData);

      // Parse JSON fields
      metricsData.byDocumentType = JSON.parse(metricsData.byDocumentType);
      metricsData.byConfidenceBucket = JSON.parse(metricsData.byConfidenceBucket);

      setMetrics(metricsData);
      console.log('[ValidationMetrics] Metrics set successfully');
    } catch (err) {
      logger.error('Error fetching validation metrics:', err);
      console.error('Validation metrics error:', err);
      console.error('Error details:', JSON.stringify(err, null, 2));
      setError(err.message || err.errors?.[0]?.message || 'Failed to load validation metrics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [timeRange]);

  // Format timestamp to readable date
  const formatDate = (timestamp) => {
    return new Date(timestamp * 1000).toLocaleDateString('en-GB', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // Get status variant for match rate
  const getMatchRateVariant = (rate) => {
    if (rate >= 95) return 'success';
    if (rate >= 85) return 'warning';
    return 'error';
  };

  if (loading && !metrics) {
    return (
      <Container>
        <Box textAlign="center" padding="xxl">
          <Spinner size="large" />
          <Box variant="p" color="text-body-secondary" margin={{ top: 's' }}>
            Loading validation metrics...
          </Box>
        </Box>
      </Container>
    );
  }

  if (error) {
    return (
      <Container>
        <Alert type="error" header="Error loading metrics">
          {error}
        </Alert>
      </Container>
    );
  }

  if (!metrics) {
    return (
      <Container>
        <Alert type="info">No validation data available</Alert>
      </Container>
    );
  }

  // Prepare table data for by-type breakdown
  const byTypeTableItems = Object.entries(metrics.byDocumentType || {}).map(([type, data]) => ({
    documentType: type,
    total: data.total,
    matches: data.matches,
    mismatches: data.mismatches,
    highConfidenceMismatches: data.highConfidenceMismatches,
    accuracy: data.total > 0 ? ((data.matches / data.total) * 100).toFixed(1) : '0.0',
  }));

  // Prepare table data for confidence calibration
  const confidenceBuckets = Object.entries(metrics.byConfidenceBucket || {}).map(([bucket, data]) => ({
    bucket,
    total: data.total,
    matches: data.matches,
    accuracy: data.total > 0 ? ((data.matches / data.total) * 100).toFixed(1) : '0.0',
  }));

  return (
    <SpaceBetween size="l">
      {/* Header */}
      <Container
        header={
          <Header
            variant="h1"
            actions={
              <SpaceBetween direction="horizontal" size="xs">
                <Select
                  selectedOption={timeRange}
                  onChange={({ detail }) => setTimeRange(detail.selectedOption)}
                  options={timeRangeOptions}
                  selectedAriaLabel="Selected time range"
                />
                <Button iconName="refresh" onClick={fetchMetrics} loading={loading}>
                  Refresh
                </Button>
              </SpaceBetween>
            }
          >
            Classification Validation Metrics
          </Header>
        }
      >
        <SpaceBetween size="m">
          <Box variant="p" color="text-body-secondary">
            Track model accuracy vs user selections to determine when to enable auto-classification. High agreement
            rates (95%+) indicate the model is ready to classify documents automatically.
          </Box>

          {/* Summary Cards */}
          <ColumnLayout columns={4} variant="text-grid">
            <KeyValuePairs
              columns={1}
              items={[
                {
                  label: 'Model Accuracy',
                  value: (
                    <Box fontSize="display-l">
                      <StatusIndicator type={getMatchRateVariant(metrics.matchRatePercent)}>
                        {metrics.summary.modelAccuracy}
                      </StatusIndicator>
                    </Box>
                  ),
                },
              ]}
            />
            <KeyValuePairs
              columns={1}
              items={[
                {
                  label: 'Total Validated',
                  value: <Box fontSize="display-l">{metrics.totalValidations.toLocaleString()}</Box>,
                },
              ]}
            />
            <KeyValuePairs
              columns={1}
              items={[
                {
                  label: 'Agreements',
                  value: (
                    <Box fontSize="display-l">
                      <Badge color="green">{metrics.matches.toLocaleString()}</Badge>
                    </Box>
                  ),
                },
              ]}
            />
            <KeyValuePairs
              columns={1}
              items={[
                {
                  label: 'Requires Attention',
                  value: (
                    <Box fontSize="display-l">
                      <Badge color={metrics.summary.requiresAttention > 0 ? 'red' : 'grey'}>
                        {metrics.summary.requiresAttention}
                      </Badge>
                    </Box>
                  ),
                },
              ]}
            />
          </ColumnLayout>

          {/* Progress Bar */}
          <ProgressBar
            value={metrics.matchRatePercent}
            additionalInfo={`${metrics.mismatches} mismatches`}
            description="User/Model Agreement Rate"
            variant={getMatchRateVariant(metrics.matchRatePercent)}
            label="Agreement Rate"
          />
        </SpaceBetween>
      </Container>

      {/* By Document Type Table */}
      <Table
        columnDefinitions={[
          {
            id: 'documentType',
            header: 'Document Type',
            cell: (item) => item.documentType.toUpperCase(),
            sortingField: 'documentType',
          },
          {
            id: 'total',
            header: 'Total',
            cell: (item) => item.total.toLocaleString(),
            sortingField: 'total',
          },
          {
            id: 'matches',
            header: 'Matches',
            cell: (item) => <Badge color="green">{item.matches.toLocaleString()}</Badge>,
            sortingField: 'matches',
          },
          {
            id: 'mismatches',
            header: 'Mismatches',
            cell: (item) => <Badge color="red">{item.mismatches.toLocaleString()}</Badge>,
            sortingField: 'mismatches',
          },
          {
            id: 'highConfidenceMismatches',
            header: 'High Confidence Mismatches',
            cell: (item) => (
              <Badge color={item.highConfidenceMismatches > 0 ? 'red' : 'grey'}>{item.highConfidenceMismatches}</Badge>
            ),
            sortingField: 'highConfidenceMismatches',
          },
          {
            id: 'accuracy',
            header: 'Accuracy',
            cell: (item) => (
              <StatusIndicator type={getMatchRateVariant(parseFloat(item.accuracy))}>{item.accuracy}%</StatusIndicator>
            ),
            sortingField: 'accuracy',
          },
        ]}
        items={byTypeTableItems}
        loadingText="Loading validation data"
        sortingDisabled={false}
        variant="embedded"
        header={<Header variant="h2">Accuracy by Document Type</Header>}
        empty={
          <Box textAlign="center" color="inherit">
            <Box variant="p" color="inherit">
              No validation data available for the selected time range
            </Box>
          </Box>
        }
      />

      {/* Confidence Calibration Table */}
      <Table
        columnDefinitions={[
          {
            id: 'bucket',
            header: 'Confidence Range',
            cell: (item) => item.bucket,
            sortingField: 'bucket',
          },
          {
            id: 'total',
            header: 'Predictions',
            cell: (item) => item.total.toLocaleString(),
            sortingField: 'total',
          },
          {
            id: 'matches',
            header: 'Correct',
            cell: (item) => item.matches.toLocaleString(),
            sortingField: 'matches',
          },
          {
            id: 'accuracy',
            header: 'Actual Accuracy',
            cell: (item) => (
              <span>
                {item.accuracy}%
                {item.total > 0 && (
                  <Box variant="small" color="text-body-secondary" margin={{ left: 'xs' }}>
                    {parseFloat(item.accuracy) > parseFloat(item.bucket.split('-')[1]) * 100 ? '(Over)' : '(Under)'}
                  </Box>
                )}
              </span>
            ),
            sortingField: 'accuracy',
          },
        ]}
        items={confidenceBuckets}
        loadingText="Loading calibration data"
        sortingDisabled={false}
        variant="embedded"
        header={
          <Header
            variant="h2"
            description="Verify that model confidence scores align with actual accuracy. Well-calibrated models should have similar confidence and accuracy percentages."
          >
            Model Confidence Calibration
          </Header>
        }
        empty={
          <Box textAlign="center" color="inherit">
            <Box variant="p" color="inherit">
              No calibration data available
            </Box>
          </Box>
        }
      />

      {/* High Confidence Mismatches Table */}
      {metrics.highConfidenceMismatches && metrics.highConfidenceMismatches.length > 0 && (
        <Table
          columnDefinitions={[
            {
              id: 'createdAt',
              header: 'Date',
              cell: (item) => formatDate(item.createdAt),
              sortingField: 'createdAt',
            },
            {
              id: 'company',
              header: 'Company',
              cell: (item) => item.company || 'Unknown',
            },
            {
              id: 'userSelection',
              header: 'User Selected',
              cell: (item) => <Badge color="blue">{item.userSelection}</Badge>,
            },
            {
              id: 'modelPrediction',
              header: 'Model Predicted',
              cell: (item) => <Badge color="grey">{item.modelPrediction}</Badge>,
            },
            {
              id: 'confidence',
              header: 'Confidence',
              cell: (item) => <Badge color="red">{(item.confidence * 100).toFixed(1)}%</Badge>,
              sortingField: 'confidence',
            },
            {
              id: 'documentId',
              header: 'Document ID',
              cell: (item) => (
                <Box fontSize="body-s" color="text-body-secondary">
                  {item.documentId.split('/').pop()}
                </Box>
              ),
            },
          ]}
          items={metrics.highConfidenceMismatches}
          loadingText="Loading mismatches"
          sortingDisabled={false}
          variant="embedded"
          header={
            <Header
              variant="h2"
              counter={`(${metrics.highConfidenceMismatches.length})`}
              description="Documents where the model strongly disagreed with the user. Review these to identify model weaknesses or user errors."
            >
              High Confidence Mismatches Requiring Review
            </Header>
          }
        />
      )}

      {/* Recommendation Alert */}
      {metrics.matchRatePercent >= 95 && metrics.totalValidations >= 1000 && (
        <Alert type="success" header="Ready for Auto-Classification">
          <Box>
            Model accuracy is <strong>{metrics.summary.modelAccuracy}</strong> across{' '}
            <strong>{metrics.totalValidations.toLocaleString()}</strong> validations.
          </Box>
          <Box margin={{ top: 's' }}>
            ✅ <strong>Recommendation:</strong> Enable auto-classification for invoices and bank statements. The model
            has demonstrated sufficient accuracy to classify documents without user input.
          </Box>
        </Alert>
      )}

      {metrics.matchRatePercent < 95 && metrics.totalValidations >= 100 && (
        <Alert type="warning" header="Collect More Data">
          <Box>
            Model accuracy is <strong>{metrics.summary.modelAccuracy}</strong> with{' '}
            <strong>{metrics.totalValidations.toLocaleString()}</strong> validations.
          </Box>
          <Box margin={{ top: 's' }}>
            ⚠️ <strong>Recommendation:</strong> Continue collecting validation data. Target: 95%+ accuracy over 1000+
            documents before enabling auto-classification.
          </Box>
        </Alert>
      )}
    </SpaceBetween>
  );
};

export default ValidationMetricsDashboard;
