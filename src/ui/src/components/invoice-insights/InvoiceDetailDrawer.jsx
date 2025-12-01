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
import useDocumentsContext from '../../contexts/documents';
import generateS3PresignedUrl from '../common/generate-s3-presigned-url';
import {
  resolveDocumentKey,
  buildPageImageUri,
  getPageImageFromDocuments,
} from '../../utils/sourceDocumentUtils';
import { resolveDocumentKey, buildPageImageUri } from '../../utils/sourceDocumentUtils';

const logger = new Logger('InvoiceDetailDrawer');

const InvoiceDetailDrawer = ({ invoice, visible, onDismiss }) => {
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
  }, [invoice?.id]);

  if (!invoice) return null;

  const rawData = invoice.rawData || {};
  const isAnalyzed = invoice.analysisStatus === 'ANALYZED';
  const documentKey = resolveDocumentKey({
    s3Path: invoice.s3Path,
    s3Uri: invoice.s3Uri || rawData.S3Uri,
    documentId: invoice.id || rawData.DocumentId,
  });

  // Debug logging for troubleshooting
  console.log('[INVOICE DRAWER DEBUG] Invoice data:', {
    invoiceType: invoice.invoiceType,
    analysisStatus: invoice.analysisStatus,
    isAnalyzed,
    hasBIMSections: !!rawData.BIMSections,
    hasTest1: !!rawData.Test1_WhollyExclusively,
    hasAddbackAmount: !!rawData.AddbackAmount,
    BIMSections: rawData.BIMSections,
    Test1_WhollyExclusively: rawData.Test1_WhollyExclusively,
    AddbackAmount: rawData.AddbackAmount,
    DeductibilityStatus: rawData.DeductibilityStatus,
    allTestFields: {
      Test1: rawData.Test1_WhollyExclusively,
      Test2: rawData.Test2_Entertainment,
      Test3: rawData.Test3_Travel,
      Test4: rawData.Test4_Training,
      Test5: rawData.Test5_StatutoryBan,
      Test6: rawData.Test6_MixedUse,
      Test7: rawData.Test7_Duality,
    },
  });
  console.log('[INVOICE DRAWER DEBUG] Full rawData keys:', Object.keys(rawData));

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

  // Construct page image URI from document URI (for snapshot view)
  // Invoices may span multiple pages, so we'll use the first page if available
  const pageNumber = rawData.SourcePage || rawData.PageNumber || 1;
  const pageImageFromDocuments = getPageImageFromDocuments({
    documents,
    documentKeyCandidates: [documentKey, rawData.DocumentId, invoice?.s3Path],
    pageNumber,
  });
  const computedPageImageUri = buildPageImageUri({
    outputBucket: settings?.OutputBucket,
    documentKey,
    pageNumber,
  });
  const pageImageUri = pageImageFromDocuments || computedPageImageUri;

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

    if (!pageImageUri && !sourceDocumentTarget) {
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

      // Prefer page image, fall back to full document
      const targetUri = pageImageUri || sourceDocumentTarget;
      logger.info(`[SOURCE DOC] Loading URI: ${targetUri}`);
      logger.info(`[SOURCE DOC] Using page image: ${!!pageImageUri}`);

      const url = await generateS3PresignedUrl(targetUri, currentCredentials, {
        forceInline: true,
      });

      logger.info(`[SOURCE DOC] Generated presigned URL (first 100 chars): ${url.substring(0, 100)}...`);
      setSourceDocumentUrl(url);
      setIsSourceVisible(true);
    } catch (error) {
      logger.error(`[SOURCE DOC] Failed to load document:`, error);
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

  const handleDownloadDocument = async () => {
    if (!sourceDocumentTarget) {
      logger.warn('[SOURCE DOC] No source document target available');
      return;
    }

    try {
      if (!currentCredentials) {
        throw new Error('Missing AWS credentials');
      }

      logger.info(`[SOURCE DOC] Downloading PDF: ${sourceDocumentTarget}`);

      // Generate URL without forceInline to trigger download
      const url = await generateS3PresignedUrl(sourceDocumentTarget, currentCredentials, {
        forceInline: false,
      });

      // Extract filename from S3 URI
      const filename = sourceDocumentTarget.split('/').pop() || 'invoice.pdf';

      // Create temporary link and trigger download
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      logger.info(`[SOURCE DOC] Download triggered: ${filename}`);
    } catch (error) {
      logger.error('[SOURCE DOC] Failed to download document:', error);
      setSourceError(error.message || 'Failed to download document.');
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
                  <Box variant="awsui-key-label">Confidence Level</Box>
                  <Badge
                    color={
                      rawData.DeductibilityConfidence === 'HIGH'
                        ? 'green'
                        : rawData.DeductibilityConfidence === 'MEDIUM'
                        ? 'blue'
                        : 'grey'
                    }
                  >
                    {rawData.DeductibilityConfidence || 'N/A'}
                  </Badge>
                </div>
                <div>
                  <Box variant="awsui-key-label">Tax Savings (19% CT)</Box>
                  <Box fontSize="heading-m" fontWeight="bold" color="text-status-success">
                    {calculateTaxSavings(invoice.amount, rawData.DeductibilityPercentage)}
                  </Box>
                </div>
              </ColumnLayout>

              <ColumnLayout columns={2} variant="text-grid">
                <div>
                  <Box variant="awsui-key-label">HMRC Risk</Box>
                  <Badge color={rawData.HMRCConcern ? 'red' : 'green'}>
                    {rawData.HMRCConcern ? 'High Risk' : 'Low Risk'}
                  </Badge>
                </div>
                <div>
                  <Box variant="awsui-key-label">Recommended Action</Box>
                  <Badge color={getRecommendedActionColor(rawData.RecommendedAction)}>
                    {rawData.RecommendedAction?.replace(/_/g, ' ') || 'N/A'}
                  </Badge>
                </div>
              </ColumnLayout>

              {rawData.DeductibilityReasoning && (
                <div>
                  <Box variant="awsui-key-label">Tax Analysis</Box>
                  <Box variant="p" padding={{ top: 'xs' }}>
                    {rawData.DeductibilityReasoning}
                  </Box>
                </div>
              )}

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

        {/* Compliance Tests - For EXPENSE_CLAIM only */}
        {isAnalyzed && invoice.invoiceType === 'EXPENSE_CLAIM' && rawData.Test1_WhollyExclusively && (
          <Container header={<Header variant="h3">Statutory Compliance Tests</Header>}>
            <SpaceBetween size="m">
              <Alert type="info" header="Multi-Test Framework Applied">
                This expense claim has been assessed using the full UK statutory compliance framework with 7 specific
                tests.
              </Alert>

              <ColumnLayout columns={2} variant="text-grid">
                <div>
                  <Box variant="awsui-key-label">TEST 1: Wholly & Exclusively (S54 CTA 2009)</Box>
                  <SpaceBetween direction="horizontal" size="xs">
                    <Badge
                      color={
                        rawData.Test1_WhollyExclusively === 'PASS'
                          ? 'green'
                          : rawData.Test1_WhollyExclusively === 'FAIL'
                          ? 'red'
                          : 'grey'
                      }
                    >
                      {rawData.Test1_WhollyExclusively || 'N/A'}
                    </Badge>
                    {rawData.Test1_Confidence && (
                      <Badge
                        color={
                          rawData.Test1_Confidence === 'HIGH'
                            ? 'green'
                            : rawData.Test1_Confidence === 'MEDIUM'
                            ? 'blue'
                            : 'grey'
                        }
                      >
                        {rawData.Test1_Confidence}
                      </Badge>
                    )}
                  </SpaceBetween>
                  {rawData.Test1_Reasoning && (
                    <Box variant="small" color="text-body-secondary" padding={{ top: 'xxs' }}>
                      {rawData.Test1_Reasoning}
                    </Box>
                  )}
                </div>

                <div>
                  <Box variant="awsui-key-label">TEST 2: Entertainment (S45-47 CTA 2009)</Box>
                  <SpaceBetween direction="horizontal" size="xs">
                    <Badge
                      color={
                        rawData.Test2_Entertainment === 'STAFF_ENTERTAINMENT'
                          ? 'green'
                          : rawData.Test2_Entertainment === 'CLIENT_ENTERTAINMENT'
                          ? 'red'
                          : 'grey'
                      }
                    >
                      {rawData.Test2_Entertainment?.replace(/_/g, ' ') || 'NOT APPLICABLE'}
                    </Badge>
                    {rawData.Test2_Confidence && (
                      <Badge
                        color={
                          rawData.Test2_Confidence === 'HIGH'
                            ? 'green'
                            : rawData.Test2_Confidence === 'MEDIUM'
                            ? 'blue'
                            : 'grey'
                        }
                      >
                        {rawData.Test2_Confidence}
                      </Badge>
                    )}
                  </SpaceBetween>
                  {rawData.Test2_Reasoning && (
                    <Box variant="small" color="text-body-secondary" padding={{ top: 'xxs' }}>
                      {rawData.Test2_Reasoning}
                    </Box>
                  )}
                </div>

                <div>
                  <Box variant="awsui-key-label">TEST 3: Travel (S54 CTA + S38 ITEPA)</Box>
                  <SpaceBetween direction="horizontal" size="xs">
                    <Badge
                      color={
                        rawData.Test3_Travel === 'BUSINESS_TRAVEL'
                          ? 'green'
                          : rawData.Test3_Travel === 'COMMUTING'
                          ? 'red'
                          : 'grey'
                      }
                    >
                      {rawData.Test3_Travel?.replace(/_/g, ' ') || 'NOT APPLICABLE'}
                    </Badge>
                    {rawData.Test3_Confidence && (
                      <Badge
                        color={
                          rawData.Test3_Confidence === 'HIGH'
                            ? 'green'
                            : rawData.Test3_Confidence === 'MEDIUM'
                            ? 'blue'
                            : 'grey'
                        }
                      >
                        {rawData.Test3_Confidence}
                      </Badge>
                    )}
                  </SpaceBetween>
                  {rawData.Test3_Reasoning && (
                    <Box variant="small" color="text-body-secondary" padding={{ top: 'xxs' }}>
                      {rawData.Test3_Reasoning}
                    </Box>
                  )}
                </div>

                <div>
                  <Box variant="awsui-key-label">TEST 4: Training (S74 CTA)</Box>
                  <SpaceBetween direction="horizontal" size="xs">
                    <Badge
                      color={
                        rawData.Test4_Training === 'WORK_RELATED'
                          ? 'green'
                          : rawData.Test4_Training === 'PERSONAL_DEVELOPMENT'
                          ? 'blue'
                          : 'grey'
                      }
                    >
                      {rawData.Test4_Training?.replace(/_/g, ' ') || 'NOT APPLICABLE'}
                    </Badge>
                    {rawData.Test4_Confidence && (
                      <Badge
                        color={
                          rawData.Test4_Confidence === 'HIGH'
                            ? 'green'
                            : rawData.Test4_Confidence === 'MEDIUM'
                            ? 'blue'
                            : 'grey'
                        }
                      >
                        {rawData.Test4_Confidence}
                      </Badge>
                    )}
                  </SpaceBetween>
                  {rawData.Test4_Reasoning && (
                    <Box variant="small" color="text-body-secondary" padding={{ top: 'xxs' }}>
                      {rawData.Test4_Reasoning}
                    </Box>
                  )}
                </div>

                <div>
                  <Box variant="awsui-key-label">TEST 5: Statutory Ban</Box>
                  <SpaceBetween direction="horizontal" size="xs">
                    <Badge
                      color={
                        rawData.Test5_StatutoryBan === 'NOT_APPLICABLE'
                          ? 'green'
                          : rawData.Test5_StatutoryBan === 'PENALTIES' || rawData.Test5_StatutoryBan === 'DEPRECIATION'
                          ? 'red'
                          : 'grey'
                      }
                    >
                      {rawData.Test5_StatutoryBan?.replace(/_/g, ' ') || 'NOT APPLICABLE'}
                    </Badge>
                    {rawData.Test5_Confidence && (
                      <Badge
                        color={
                          rawData.Test5_Confidence === 'HIGH'
                            ? 'green'
                            : rawData.Test5_Confidence === 'MEDIUM'
                            ? 'blue'
                            : 'grey'
                        }
                      >
                        {rawData.Test5_Confidence}
                      </Badge>
                    )}
                  </SpaceBetween>
                  {rawData.Test5_Reasoning && (
                    <Box variant="small" color="text-body-secondary" padding={{ top: 'xxs' }}>
                      {rawData.Test5_Reasoning}
                    </Box>
                  )}
                </div>
              </ColumnLayout>

              {/* Test 6: Mixed Use */}
              {rawData.Test6_MixedUse && rawData.Test6_MixedUse !== 'NOT_APPLICABLE' && (
                <Container>
                  <SpaceBetween size="s">
                    <div>
                      <Box variant="awsui-key-label">TEST 6: Mixed Use / Apportionable (S54(2))</Box>
                      <SpaceBetween direction="horizontal" size="xs">
                        <Badge color={rawData.Test6_MixedUse === 'APPORTIONABLE' ? 'blue' : 'green'}>
                          {rawData.Test6_MixedUse?.replace(/_/g, ' ')}
                        </Badge>
                        {rawData.Test6_Confidence && (
                          <Badge
                            color={
                              rawData.Test6_Confidence === 'HIGH'
                                ? 'green'
                                : rawData.Test6_Confidence === 'MEDIUM'
                                ? 'blue'
                                : 'grey'
                            }
                          >
                            Confidence: {rawData.Test6_Confidence}
                          </Badge>
                        )}
                      </SpaceBetween>
                    </div>

                    {rawData.Test6_BusinessPercentage && (
                      <div>
                        <Box variant="awsui-key-label">Business Use Percentage</Box>
                        <Box fontSize="heading-m" fontWeight="bold">
                          {rawData.Test6_BusinessPercentage}%
                        </Box>
                      </div>
                    )}

                    {rawData.Test6_Reasoning && (
                      <div>
                        <Box variant="awsui-key-label">Apportionment Basis</Box>
                        <Box variant="p" color="text-body-secondary">
                          {rawData.Test6_Reasoning}
                        </Box>
                      </div>
                    )}

                    {rawData.Test6_DocumentationNeeded && (
                      <Alert type="warning" header="Verification Required">
                        {rawData.Test6_DocumentationNeeded}
                      </Alert>
                    )}
                  </SpaceBetween>
                </Container>
              )}

              {/* Test 7: Duality */}
              <div>
                <Box variant="awsui-key-label">TEST 7: Duality of Purpose (S54(2))</Box>
                <SpaceBetween direction="horizontal" size="xs">
                  <Badge
                    color={
                      rawData.Test7_Duality === 'PASS' ? 'green' : rawData.Test7_Duality === 'FAIL' ? 'red' : 'grey'
                    }
                  >
                    {rawData.Test7_Duality || 'N/A'}
                  </Badge>
                  {rawData.Test7_Confidence && (
                    <Badge
                      color={
                        rawData.Test7_Confidence === 'HIGH'
                          ? 'green'
                          : rawData.Test7_Confidence === 'MEDIUM'
                          ? 'blue'
                          : 'grey'
                      }
                    >
                      {rawData.Test7_Confidence}
                    </Badge>
                  )}
                </SpaceBetween>
                {rawData.Test7_Reasoning && (
                  <Box variant="small" color="text-body-secondary" padding={{ top: 'xxs' }}>
                    {rawData.Test7_Reasoning}
                  </Box>
                )}
              </div>

              {rawData.AddbackAmount && parseFloat(rawData.AddbackAmount) > 0 && (
                <Alert type="warning" header={`Tax Addback Required: £${rawData.AddbackAmount}`}>
                  <SpaceBetween size="xs">
                    <Box variant="p">{rawData.AddbackReason}</Box>
                    <Box variant="small" color="text-status-error">
                      This amount must be added back to taxable profits.
                    </Box>
                  </SpaceBetween>
                </Alert>
              )}
            </SpaceBetween>
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
                    value={invoice.confidenceScores?.composite ? invoice.confidenceScores.composite * 100 : 0}
                    hideLabel
                  />
                </SpaceBetween>
              </div>
              <div>
                <Box variant="awsui-key-label">Quality Tier</Box>
                <Badge
                  color={
                    invoice.qualityTier === 'EXCELLENT' ? 'green' : invoice.qualityTier === 'GOOD' ? 'blue' : 'grey'
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
                  {invoice.processedAt ? new Date(invoice.processedAt * 1000).toLocaleDateString('en-GB') : 'N/A'}
                </Box>
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
                <StatusIndicator type="info">No source document stored for this invoice.</StatusIndicator>
              )}
              {isSourceVisible && (
                <Box textAlign="center" padding={{ top: 's' }}>
                  {isSourceLoading && <Spinner />}
                  {!isSourceLoading && sourceError && <StatusIndicator type="error">{sourceError}</StatusIndicator>}
                  {!isSourceLoading && !sourceError && sourceDocumentUrl && (
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
                          <img
                            src={sourceDocumentUrl}
                            alt={`Invoice page ${pageNumber || ''}`}
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

                      {isFullScreen && (
                        <Box>
                          <SpaceBetween size="s">
                            <Button iconName="close" onClick={() => setIsFullScreen(false)} variant="primary">
                              Close
                            </Button>
                            <img
                              src={sourceDocumentUrl}
                              alt={`Invoice page ${pageNumber || ''}`}
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
