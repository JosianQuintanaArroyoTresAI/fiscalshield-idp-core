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
} from '@awsui/components-react';
import { Logger } from 'aws-amplify';
import useAppContext from '../../contexts/app';
import useSettingsContext from '../../contexts/settings';
import useDocumentsContext from '../../contexts/documents';
import generateS3PresignedUrl from '../common/generate-s3-presigned-url';
import {
  resolveDocumentKey,
  buildPageImageUri,
  getPageImageFromDocuments,
} from '../../utils/sourceDocumentUtils';
import { resolveDocumentKey, buildPageImageUri } from '../../utils/sourceDocumentUtils';

const logger = new Logger('TransactionDetailDrawer');

const TransactionDetailDrawer = ({ transaction, visible, onDismiss }) => {
  const { currentCredentials } = useAppContext();
  const { settings } = useSettingsContext();
  const { documents } = useDocumentsContext();
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
  }, [transaction?.id]);

  if (!transaction) return null;

  const rawData = transaction.rawData || {};
  const isAnalyzed = transaction.analysisStatus === 'ANALYZED';
  const documentKey = resolveDocumentKey({
    s3Path: transaction.s3Path,
    s3Uri: transaction.s3Uri || rawData.S3Uri,
    documentId: transaction.id || rawData.DocumentId,
  });

  // Construct proper S3 URI from the transaction data
  let sourceDocumentTarget = transaction.s3Uri || rawData.S3Uri;

  // If s3Uri has the NEEDS_BUCKET prefix, construct the full S3 URI
  if (sourceDocumentTarget && sourceDocumentTarget.startsWith('NEEDS_BUCKET:')) {
    const s3Path = sourceDocumentTarget.replace('NEEDS_BUCKET:', '');
    if (settings.InputBucket && s3Path) {
      sourceDocumentTarget = `s3://${settings.InputBucket}/${s3Path}`;
      logger.debug(`Constructed S3 URI from PK: ${sourceDocumentTarget}`);
    } else {
      logger.warn('Missing InputBucket setting or s3Path for document preview');
      sourceDocumentTarget = null;
    }
  } else if (transaction.s3Path && settings.InputBucket) {
    // Fallback: use s3Path if available
    sourceDocumentTarget = `s3://${settings.InputBucket}/${transaction.s3Path}`;
    logger.debug(`Constructed S3 URI from s3Path: ${sourceDocumentTarget}`);
  }

  // Construct page image URI from document URI (for snapshot view)
  const pageNumber = rawData.SourcePage || transaction.sourcePage;
  
  // Debug: Log what we're searching for
  console.log('[TRANSACTION DRAWER PAGE DEBUG] Looking for page image:', {
    pageNumber,
    documentKey,
    documentKeyCandidates: [documentKey, rawData.DocumentId, transaction?.s3Path],
    documentsCount: documents?.length,
    OutputBucket: settings?.OutputBucket,
  });
  
  // Debug: Log what documents we have
  if (documents?.length > 0) {
    console.log('[TRANSACTION DRAWER PAGE DEBUG] Available documents:', documents.map(doc => ({
      objectKey: doc?.objectKey,
      pagesCount: doc?.pages?.length,
      firstPageId: doc?.pages?.[0]?.Id,
      firstPageImageUri: doc?.pages?.[0]?.ImageUri,
    })));
  }
  
  const pageImageFromDocuments = getPageImageFromDocuments({
    documents,
    documentKeyCandidates: [documentKey, rawData.DocumentId, transaction?.s3Path],
    pageNumber,
  });
  const computedPageImageUri = buildPageImageUri({
    outputBucket: settings?.OutputBucket,
    documentKey,
    pageNumber,
  });
  const pageImageUri = pageImageFromDocuments || computedPageImageUri;
  
  console.log('[TRANSACTION DRAWER PAGE DEBUG] Resolution result:', {
    pageImageFromDocuments,
    computedPageImageUri,
    finalPageImageUri: pageImageUri,
  });

  if (pageImageUri) {
    logger.info(`[SOURCE DOC] Page image URI resolved (${pageImageFromDocuments ? 'document cache' : 'computed'}).`);
    logger.info(`[SOURCE DOC] Source document: ${sourceDocumentTarget}`);
    logger.info(`[SOURCE DOC] Page number: ${pageNumber}`);
  } else if (pageNumber && documentKey && !settings?.OutputBucket) {
    logger.warn('[SOURCE DOC] Missing OutputBucket setting. Cannot build page image preview URI.');
  } else if (pageNumber && documentKey) {
    logger.warn('[SOURCE DOC] Unable to construct page image URI despite having key and page number.');
  } else {
    logger.warn(
      `[SOURCE DOC] Cannot construct page image - documentKey: ${documentKey}, pageNumber: ${pageNumber}, outputBucket: ${settings?.OutputBucket}`,
    );
  }

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

  const handleToggleSourceDocument = async () => {
    if (isSourceVisible) {
      setIsSourceVisible(false);
      return;
    }

    if (!pageImageUri && !sourceDocumentTarget) {
      setSourceError('No source document available for this transaction.');
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

      // Prefer page image, fall back to full document
      const targetUri = pageImageUri || sourceDocumentTarget;
      const url = await generateS3PresignedUrl(targetUri, currentCredentials, {
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

  const handleOpenFullDocument = async () => {
    if (!sourceDocumentTarget) {
      logger.warn('[SOURCE DOC] No source document target available');
      return;
    }

    try {
      if (!currentCredentials) {
        throw new Error('Missing AWS credentials');
      }

      logger.info(`[SOURCE DOC] Opening full PDF: ${sourceDocumentTarget}`);

      const url = await generateS3PresignedUrl(sourceDocumentTarget, currentCredentials, {
        forceInline: true,
      });

      logger.info(`[SOURCE DOC] Opening PDF in new tab`);
      const newWindow = window.open(url, '_blank');

      if (!newWindow) {
        logger.warn('[SOURCE DOC] Popup blocked by browser');
        setSourceError('Popup blocked. Please allow popups for this site.');
      }
    } catch (error) {
      logger.error('[SOURCE DOC] Failed to open full document:', error);
      setSourceError(error.message || 'Failed to open document.');
    }
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
                  <Badge color={getTierColor(rawData.ComplianceRiskTier)}>{rawData.ComplianceRiskTier || 'N/A'}</Badge>
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
                  <ProgressBar value={rawData.CompositeConfidence ? rawData.CompositeConfidence * 100 : 0} hideLabel />
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

          <SpaceBetween size="s" direction="vertical">
            <SpaceBetween size="xs" direction="horizontal">
              <Button
                iconName={isSourceVisible ? 'close' : 'search'}
                onClick={handleToggleSourceDocument}
                disabled={!pageImageUri && !sourceDocumentTarget && !sourceDocumentUrl}
                loading={isSourceLoading}
              >
                {isSourceVisible ? 'Hide Page Image' : pageNumber ? `View Page ${pageNumber}` : 'View Source Page'}
              </Button>
              {sourceDocumentTarget && sourceDocumentType === 'pdf' && (
                <>
                  <Button iconName="external" onClick={handleOpenFullDocument} variant="normal">
                    View PDF in Browser
                  </Button>
                  <Button iconName="download" onClick={handleDownloadDocument} variant="normal">
                    Download PDF
                  </Button>
                </>
              )}
            </SpaceBetween>
            {!pageImageUri && !sourceDocumentTarget && !sourceDocumentUrl && (
              <StatusIndicator type="info">No source document stored for this transaction.</StatusIndicator>
            )}
            {isSourceVisible && (
              <Box textAlign="center" padding={{ top: 's' }}>
                {isSourceLoading && <Spinner />}
                {!isSourceLoading && sourceError && <StatusIndicator type="error">{sourceError}</StatusIndicator>}
                {!isSourceLoading && !sourceError && sourceDocumentUrl && (
                  <Box>
                    {/* Thumbnail/Preview */}
                    {!isFullScreen && (
                      <Box
                        onClick={() => setIsFullScreen(true)}
                        style={{
                          cursor: 'pointer',
                          position: 'relative',
                          display: 'inline-block',
                        }}
                      >
                        <img
                          src={sourceDocumentUrl}
                          alt={`Bank statement page ${pageNumber || ''}`}
                          crossOrigin="anonymous"
                          onError={(e) => {
                            logger.error(`[SOURCE DOC] Image failed to load: ${sourceDocumentUrl}`);
                            setSourceError('Failed to load page image. The file may not exist or is inaccessible.');
                          }}
                          onLoad={() => logger.info(`[SOURCE DOC] Image loaded successfully`)}
                          style={{
                            maxWidth: '100%',
                            maxHeight: '400px',
                            borderRadius: '8px',
                            boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
                            transition: 'transform 0.2s',
                          }}
                          onMouseOver={(e) => (e.currentTarget.style.transform = 'scale(1.02)')}
                          onMouseOut={(e) => (e.currentTarget.style.transform = 'scale(1)')}
                        />
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
                          🔍 Click to enlarge
                        </Box>
                      </Box>
                    )}

                    {/* Full Screen View */}
                    {isFullScreen && (
                      <Box>
                        <SpaceBetween size="s">
                          <Button iconName="close" onClick={() => setIsFullScreen(false)} variant="primary">
                            Close
                          </Button>
                          <img
                            src={sourceDocumentUrl}
                            alt={`Bank statement page ${pageNumber || ''}`}
                            style={{
                              maxWidth: '100%',
                              height: 'auto',
                              borderRadius: '8px',
                              boxShadow: '0 4px 12px rgba(0,0,0,0.2)',
                            }}
                          />
                        </SpaceBetween>
                      </Box>
                    )}

                    <Box padding={{ top: 's' }} textAlign="center">
                      <Box variant="small" color="text-body-secondary">
                        {isFullScreen
                          ? 'Full size view'
                          : pageNumber
                          ? `Page ${pageNumber} snapshot • Click to enlarge`
                          : 'Click to enlarge'}
                      </Box>
                    </Box>
                  </Box>
                )}
                {!isSourceLoading && !sourceError && !sourceDocumentUrl && (
                  <StatusIndicator type="info">No preview available.</StatusIndicator>
                )}
              </Box>
            )}
          </SpaceBetween>
          {rawData.SourcePage && (
            <Box padding={{ top: 's' }} textAlign="center">
              <Box variant="small">Page {rawData.SourcePage}</Box>
            </Box>
          )}
        </ExpandableSection>

        {/* Metadata */}
        {isAnalyzed && (
          <ExpandableSection headerText="Metadata" defaultExpanded={false}>
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
          <Button variant="normal">Edit Category</Button>
          <Button variant="normal">Flag for Review</Button>
          <Button variant="normal">Add Note</Button>
        </SpaceBetween>
      </SpaceBetween>
    </Drawer>
  );
};

export default TransactionDetailDrawer;
