// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
import React, { useEffect, useState } from 'react';
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
  Spinner,
  Alert,
} from '@awsui/components-react';
import { Logger } from 'aws-amplify';
import useAppContext from '../../contexts/app';
import useSettingsContext from '../../contexts/settings';
import generateS3PresignedUrl from '../common/generate-s3-presigned-url';

const logger = new Logger('InvoiceDetailDrawer');

const InvoiceDetailDrawer = ({ invoice, visible, onDismiss }) => {
  const { currentCredentials } = useAppContext();
  const { settings } = useSettingsContext();
  const [isSourceVisible, setIsSourceVisible] = useState(false);
  const [sourceDocumentUrl, setSourceDocumentUrl] = useState(null);
  const [isSourceLoading, setIsSourceLoading] = useState(false);
  const [sourceError, setSourceError] = useState(null);
  const [isFullScreen, setIsFullScreen] = useState(false);

  useEffect(() => {
    setIsSourceVisible(false);
    setSourceDocumentUrl(null);
    setSourceError(null);
    setIsSourceLoading(false);
    setIsFullScreen(false);
  }, [invoice?.id]);

  if (!invoice) return null;

  const rawData = invoice.rawData || {};
  const isAnalyzed = invoice.analysisStatus === 'ANALYZED';

  // Construct proper S3 URI from the invoice data
  const getSourceDocumentTarget = () => {
    let target = invoice.s3Uri || rawData.S3Uri;

    if (target && target.startsWith('NEEDS_BUCKET:')) {
      const s3Path = target.replace('NEEDS_BUCKET:', '');
      if (settings.InputBucket && s3Path) {
        target = `s3://${settings.InputBucket}/${s3Path}`;
        logger.debug(`Constructed S3 URI from PK: ${target}`);
      } else {
        logger.warn('Missing InputBucket setting or s3Path for document preview');
        return null;
      }
    } else if (invoice.s3Path && settings.InputBucket) {
      target = `s3://${settings.InputBucket}/${invoice.s3Path}`;
      logger.debug(`Constructed S3 URI from s3Path: ${target}`);
    }

    return target;
  };

  const sourceDocumentTarget = getSourceDocumentTarget();

  const getSourceDocumentType = () => {
    if (!sourceDocumentTarget) return 'unknown';
    const sanitized = sourceDocumentTarget.split('?')[0];
    const extension = sanitized.split('.').pop()?.toLowerCase();
    if (!extension) return 'unknown';
    if (extension === 'pdf') return 'pdf';
    if (['jpg', 'jpeg', 'png', 'gif', 'svg', 'webp'].includes(extension)) return 'image';
    return 'file';
  };

  const sourceDocumentType = getSourceDocumentType();

  const getDeductibilityColor = (status) => {
    const colorMap = {
      FULLY_DEDUCTIBLE: 'green',
      PARTIALLY_DEDUCTIBLE: 'blue',
      NOT_DEDUCTIBLE: 'red',
      REQUIRES_REVIEW: 'grey',
    };
    return colorMap[status] || 'grey';
  };

  const getRecommendedActionColor = (action) => {
    const colorMap = {
      APPROVE: 'green',
      APPORTION: 'blue',
      REQUEST_DOCUMENTATION: 'grey',
      REJECT: 'red',
    };
    return colorMap[action] || 'grey';
  };

  const calculateTaxSavings = (totalAmount, deductibilityPercentage) => {
    if (!totalAmount || !deductibilityPercentage) return '£0.00';

    const amount = parseFloat(totalAmount.toString().replace(/[^0-9.-]+/g, ''));
    const deductibleAmount = (amount * deductibilityPercentage) / 100;
    const taxSavings = deductibleAmount * 0.19; // Corporation tax at 19%

    return `£${taxSavings.toFixed(2)}`;
  };

  const handleToggleSourceDocument = async () => {
    if (isSourceVisible) {
      setIsSourceVisible(false);
      return;
    }

    if (!sourceDocumentTarget) {
      setSourceError('No source document available for this invoice.');
      setIsSourceVisible(true);
      return;
    }

    if (sourceDocumentUrl) {
      setIsSourceVisible(true);
      return;
    }

    try {
      setIsSourceLoading(true);
      setSourceError(null);

      if (!currentCredentials) {
        throw new Error('Missing AWS credentials for document preview.');
      }

      const url = await generateS3PresignedUrl(sourceDocumentTarget, currentCredentials, {
        forceInline: true,
      });
      setSourceDocumentUrl(url);
      setIsSourceVisible(true);
    } catch (error) {
      setSourceError(error.message || 'Failed to load source document.');
      setIsSourceVisible(true);
    } finally {
      setIsSourceLoading(false);
    }
  };

  return (
    <Drawer header={<Header variant="h2">Invoice Details</Header>} visible={visible} onDismiss={onDismiss}>
      <SpaceBetween size="l">
        {!isAnalyzed && (
          <Box color="text-status-inactive">
            <SpaceBetween size="s">
              <Box variant="p">This invoice has not been analyzed for tax deductibility yet.</Box>
              <Box variant="small">
                Run invoice analysis to see detailed tax compliance information, BIM guidance references, and HMRC risk
                assessment.
              </Box>
            </SpaceBetween>
          </Box>
        )}

        {/* Invoice Overview */}
        <Container header={<Header variant="h3">Invoice Details</Header>}>
          <ColumnLayout columns={2} variant="text-grid">
            <div>
              <Box variant="awsui-key-label">Invoice Type</Box>
              <Badge color={invoice.invoiceType === 'SUPPLIER_INVOICE' ? 'blue' : 'green'}>
                {invoice.invoiceType === 'SUPPLIER_INVOICE' ? 'Supplier Invoice' : 'Expense Claim'}
              </Badge>
            </div>
            <div>
              <Box variant="awsui-key-label">Amount</Box>
              <Box fontSize="heading-m" fontWeight="bold" color="text-status-info">
                {invoice.amount}
              </Box>
            </div>
            <div>
              <Box variant="awsui-key-label">Invoice Number</Box>
              <Box>{invoice.invoiceNumber || 'N/A'}</Box>
            </div>
            <div>
              <Box variant="awsui-key-label">Invoice Date</Box>
              <Box>{invoice.date}</Box>
            </div>
            <div>
              <Box variant="awsui-key-label">Vendor/Supplier</Box>
              <Box>{invoice.vendor}</Box>
            </div>
            <div>
              <Box variant="awsui-key-label">Due Date</Box>
              <Box>{invoice.dueDate || 'N/A'}</Box>
            </div>
            <div>
              <Box variant="awsui-key-label">VAT Number</Box>
              <Box>{rawData.VATNumber || 'N/A'}</Box>
            </div>
            <div>
              <Box variant="awsui-key-label">Currency</Box>
              <Box>{rawData.Currency || 'GBP'}</Box>
            </div>
          </ColumnLayout>

          {invoice.supplierAddress && (
            <div style={{ marginTop: '16px' }}>
              <Box variant="awsui-key-label">Supplier Address</Box>
              <Box variant="p">{invoice.supplierAddress}</Box>
            </div>
          )}
        </Container>

        {/* Tax Deductibility Assessment */}
        {isAnalyzed && (
          <Container header={<Header variant="h3">Tax Deductibility Assessment</Header>}>
            <SpaceBetween size="m">
              <ColumnLayout columns={3} variant="text-grid">
                <div>
                  <Box variant="awsui-key-label">Deductibility Status</Box>
                  <Badge color={getDeductibilityColor(rawData.DeductibilityStatus)}>
                    {rawData.DeductibilityPercentage
                      ? `${rawData.DeductibilityPercentage}% Deductible`
                      : rawData.DeductibilityStatus?.replace(/_/g, ' ') || 'N/A'}
                  </Badge>
                </div>
                <div>
                  <Box variant="awsui-key-label">Tax Savings (19% CT)</Box>
                  <Box fontSize="heading-m" fontWeight="bold" color="text-status-success">
                    {calculateTaxSavings(invoice.amount, rawData.DeductibilityPercentage)}
                  </Box>
                </div>
                <div>
                  <Box variant="awsui-key-label">HMRC Risk</Box>
                  <Badge color={rawData.HMRCConcern ? 'red' : 'green'}>
                    {rawData.HMRCConcern ? 'High Risk' : 'Low Risk'}
                  </Badge>
                </div>
              </ColumnLayout>

              <div>
                <Box variant="awsui-key-label">Recommended Action</Box>
                <Badge color={getRecommendedActionColor(rawData.RecommendedAction)}>
                  {rawData.RecommendedAction?.replace(/_/g, ' ') || 'N/A'}
                </Badge>
              </div>

              {rawData.HMRCConcern && (
                <Alert type="error" header="HMRC Compliance Risk">
                  This expense may attract HMRC scrutiny. Ensure proper documentation is maintained.
                </Alert>
              )}
            </SpaceBetween>
          </Container>
        )}

        {/* HMRC Guidance (BIM Sections) */}
        {isAnalyzed && rawData.BIMSections && (
          <Container header={<Header variant="h3">HMRC Guidance Applied</Header>}>
            <SpaceBetween size="m">
              <div>
                <Box variant="awsui-key-label">Business Income Manual (BIM) Sections</Box>
                <SpaceBetween direction="horizontal" size="xs">
                  {rawData.BIMSections.split(',').map((section, idx) => (
                    <Badge key={idx} color="blue">
                      {section.trim()}
                    </Badge>
                  ))}
                </SpaceBetween>
              </div>
              {rawData.DeductibilityReasoning && (
                <div>
                  <Box variant="awsui-key-label">AI Tax Analysis</Box>
                  <Box variant="p" color="text-body-secondary">
                    {rawData.DeductibilityReasoning}
                  </Box>
                </div>
              )}
            </SpaceBetween>
          </Container>
        )}

        {/* Documentation Requirements */}
        {isAnalyzed && rawData.DocumentationRequired && (
          <Container header={<Header variant="h3">Audit Defense</Header>}>
            <Alert type="warning" header="Additional Documentation Required">
              {rawData.DocumentationRequired}
            </Alert>
          </Container>
        )}

        {/* Extraction Quality */}
        <ExpandableSection headerText="Extraction Quality" defaultExpanded={false}>
          <SpaceBetween size="m">
            <ColumnLayout columns={2} variant="text-grid">
              <div>
                <Box variant="awsui-key-label">Composite Confidence</Box>
                <SpaceBetween direction="horizontal" size="xs">
                  <Box fontSize="heading-m">{invoice.confidence}</Box>
                  <ProgressBar
                    value={
                      invoice.confidenceScores?.composite ? invoice.confidenceScores.composite * 100 : 0
                    }
                    hideLabel
                  />
                </SpaceBetween>
              </div>
              <div>
                <Box variant="awsui-key-label">Quality Tier</Box>
                <Badge
                  color={
                    invoice.qualityTier === 'EXCELLENT'
                      ? 'green'
                      : invoice.qualityTier === 'GOOD'
                      ? 'blue'
                      : 'grey'
                  }
                >
                  {invoice.qualityTier}
                </Badge>
              </div>
            </ColumnLayout>

            <div>
              <Box variant="awsui-key-label">HITL Review Status</Box>
              <StatusIndicator type={invoice.hitlRequired ? 'warning' : 'success'}>
                {invoice.hitlRequired ? `Review Required: ${invoice.hitlReason}` : 'Auto-approved'}
              </StatusIndicator>
            </div>

            <Box variant="h4">Field-Level Confidence Scores</Box>
            <ColumnLayout columns={3} variant="text-grid">
              <div>
                <Box variant="awsui-key-label">Invoice Type</Box>
                <ProgressBar value={(invoice.confidenceScores?.invoiceType || 0) * 100} hideLabel />
              </div>
              <div>
                <Box variant="awsui-key-label">Supplier Name</Box>
                <ProgressBar value={(invoice.confidenceScores?.supplierName || 0) * 100} hideLabel />
              </div>
              <div>
                <Box variant="awsui-key-label">Total Amount</Box>
                <ProgressBar value={(invoice.confidenceScores?.totalAmount || 0) * 100} hideLabel />
              </div>
              <div>
                <Box variant="awsui-key-label">Invoice Number</Box>
                <ProgressBar value={(invoice.confidenceScores?.invoiceNumber || 0) * 100} hideLabel />
              </div>
              <div>
                <Box variant="awsui-key-label">VAT Number</Box>
                <ProgressBar value={(invoice.confidenceScores?.vatNumber || 0) * 100} hideLabel />
              </div>
              <div>
                <Box variant="awsui-key-label">Invoice Date</Box>
                <ProgressBar value={(invoice.confidenceScores?.invoiceDate || 0) * 100} hideLabel />
              </div>
            </ColumnLayout>
          </SpaceBetween>
        </ExpandableSection>

        {/* Source Document */}
        <ExpandableSection headerText="Source Document" defaultExpanded={false}>
          <SpaceBetween size="m">
            <ColumnLayout columns={2} variant="text-grid">
              <div>
                <Box variant="awsui-key-label">Extraction Status</Box>
                <Badge color={invoice.status === 'COMPLETED' ? 'green' : 'grey'}>{invoice.status}</Badge>
              </div>
              <div>
                <Box variant="awsui-key-label">Processed Date</Box>
                <Box>
                  {invoice.processedAt
                    ? new Date(invoice.processedAt * 1000).toLocaleDateString('en-GB')
                    : 'N/A'}
                </Box>
              </div>
            </ColumnLayout>

            <SpaceBetween size="s" direction="vertical">
              <Button
                iconName={isSourceVisible ? 'close' : 'search'}
                onClick={handleToggleSourceDocument}
                disabled={!sourceDocumentTarget && !sourceDocumentUrl}
                loading={isSourceLoading}
              >
                {isSourceVisible ? 'Hide Source Document' : 'Show Source Document'}
              </Button>
              {!sourceDocumentTarget && !sourceDocumentUrl && (
                <StatusIndicator type="info">No source document stored for this invoice.</StatusIndicator>
              )}
              {isSourceVisible && (
                <Box textAlign="center" padding={{ top: 's' }}>
                  {isSourceLoading && <Spinner />}
                  {!isSourceLoading && sourceError && <StatusIndicator type="error">{sourceError}</StatusIndicator>}
                  {!isSourceLoading &&
                    !sourceError &&
                    sourceDocumentUrl &&
                    (sourceDocumentType === 'image' || sourceDocumentType === 'pdf') && (
                      <Box>
                        {!isFullScreen && (
                          <Box
                            onClick={() => setIsFullScreen(true)}
                            style={{
                              cursor: 'pointer',
                              position: 'relative',
                              display: 'inline-block',
                            }}
                          >
                            {sourceDocumentType === 'image' ? (
                              <img
                                src={sourceDocumentUrl}
                                alt="Invoice thumbnail"
                                style={{
                                  maxWidth: '300px',
                                  maxHeight: '200px',
                                  borderRadius: '8px',
                                  boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
                                  transition: 'transform 0.2s',
                                }}
                                onMouseOver={(e) => (e.currentTarget.style.transform = 'scale(1.02)')}
                                onMouseOut={(e) => (e.currentTarget.style.transform = 'scale(1)')}
                              />
                            ) : (
                              <object
                                data={sourceDocumentUrl}
                                type="application/pdf"
                                width="300px"
                                height="200px"
                                style={{
                                  border: 'none',
                                  borderRadius: '8px',
                                  boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
                                  pointerEvents: 'none',
                                }}
                              >
                                <Box padding="m" textAlign="center" color="text-body-secondary">
                                  PDF Preview
                                </Box>
                              </object>
                            )}
                            <Box
                              position="absolute"
                              bottom="8px"
                              right="8px"
                              padding="xs"
                              style={{
                                background: 'rgba(0,0,0,0.7)',
                                color: 'white',
                                borderRadius: '4px',
                                fontSize: '12px',
                                padding: '4px 8px',
                              }}
                            >
                              🔍 Click to expand
                            </Box>
                          </Box>
                        )}

                        {isFullScreen && (
                          <Box>
                            <SpaceBetween size="s">
                              <Button iconName="close" onClick={() => setIsFullScreen(false)} variant="primary">
                                Close Full View
                              </Button>
                              {sourceDocumentType === 'image' ? (
                                <img
                                  src={sourceDocumentUrl}
                                  alt="Invoice source"
                                  style={{
                                    maxWidth: '100%',
                                    maxHeight: '800px',
                                    borderRadius: '8px',
                                    boxShadow: '0 4px 12px rgba(0,0,0,0.2)',
                                  }}
                                />
                              ) : (
                                <object
                                  data={sourceDocumentUrl}
                                  type="application/pdf"
                                  width="100%"
                                  height="800px"
                                  style={{
                                    border: 'none',
                                    borderRadius: '8px',
                                    boxShadow: '0 4px 12px rgba(0,0,0,0.2)',
                                  }}
                                >
                                  <p>
                                    This browser cannot display the PDF inline.{' '}
                                    <a href={sourceDocumentUrl} target="_blank" rel="noreferrer">
                                      Download the file
                                    </a>{' '}
                                    instead.
                                  </p>
                                </object>
                              )}
                            </SpaceBetween>
                          </Box>
                        )}

                        <Box padding={{ top: 's' }} textAlign="center">
                          <Box variant="small" color="text-body-secondary">
                            {isFullScreen ? 'Full size view' : 'Click thumbnail to view full size'}
                          </Box>
                        </Box>
                      </Box>
                    )}
                  {!isSourceLoading &&
                    !sourceError &&
                    sourceDocumentUrl &&
                    sourceDocumentType !== 'image' &&
                    sourceDocumentType !== 'pdf' && (
                      <Button iconName="external" href={sourceDocumentUrl} target="_blank" rel="noreferrer">
                        Download source document
                      </Button>
                    )}
                </Box>
              )}
            </SpaceBetween>
          </SpaceBetween>
        </ExpandableSection>

        {/* Metadata */}
        {isAnalyzed && (
          <ExpandableSection headerText="Analysis Metadata" defaultExpanded={false}>
            <ColumnLayout columns={2} variant="text-grid">
              <div>
                <Box variant="awsui-key-label">Analyzed At</Box>
                <Box>{rawData.AnalyzedAt ? new Date(rawData.AnalyzedAt * 1000).toLocaleString('en-GB') : 'N/A'}</Box>
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
          <Button variant="normal">Edit Details</Button>
          <Button variant="normal">Flag for Review</Button>
          <Button variant="normal">Add Note</Button>
        </SpaceBetween>
      </SpaceBetween>
    </Drawer>
  );
};

export default InvoiceDetailDrawer;
