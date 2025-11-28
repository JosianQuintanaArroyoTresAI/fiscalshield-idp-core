// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

// src/components/upload-document/UploadDocumentPanel.jsx
import React, { useState, useRef } from 'react';
import {
  Button,
  Container,
  Header,
  SpaceBetween,
  FormField,
  StatusIndicator,
  Alert,
  Box,
  ButtonDropdown,
} from '@awsui/components-react';
import { API, graphqlOperation } from 'aws-amplify';
import { PDFDocument } from 'pdf-lib';
import uploadDocument from '../../graphql/queries/uploadDocument';
import useSettingsContext from '../../contexts/settings';
import { useCompany } from '../../contexts/company';

const UploadDocumentPanel = () => {
  const { settings } = useSettingsContext();
  const { activeCompany, isCompanySelected } = useCompany();
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState([]);
  const [error, setError] = useState(null);
  const [documentType, setDocumentType] = useState(null); // 'invoice' or 'bank-statement'
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef(null);

  // Maximum page limit for uploaded PDFs
  const MAX_PAGES = 500;

  if (!settings.InputBucket) {
    return (
      <Container header={<Header variant="h2">Upload Documents</Header>}>
        <Alert type="error">Input bucket not configured</Alert>
      </Container>
    );
  }

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      setSelectedFiles(Array.from(e.target.files));
      setUploadStatus([]);
      setError(null);
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (!documentType) {
      setError('Please select a document type first');
      return;
    }

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setSelectedFiles(Array.from(e.dataTransfer.files));
      setUploadStatus([]);
      setError(null);
    }
  };

  const handleBrowseFiles = () => {
    if (!documentType) {
      setError('Please select a document type first');
      return;
    }
    fileInputRef.current?.click();
  };

  const validatePdfPageCount = async (file) => {
    // Only validate PDFs
    if (!file.type.includes('pdf') && !file.name.toLowerCase().endsWith('.pdf')) {
      return { valid: true };
    }

    try {
      const arrayBuffer = await file.arrayBuffer();
      const pdfDoc = await PDFDocument.load(arrayBuffer);
      const pageCount = pdfDoc.getPageCount();

      if (pageCount > MAX_PAGES) {
        return {
          valid: false,
          error: `File "${file.name}" has ${pageCount} pages, which exceeds the maximum limit of ${MAX_PAGES} pages. Please split the file or reduce the number of pages.`,
        };
      }

      console.log(`✓ ${file.name}: ${pageCount} pages (within ${MAX_PAGES} page limit)`);
      return { valid: true, pageCount };
    } catch (err) {
      console.error(`Failed to validate page count for ${file.name}:`, err);
      // If we can't read the PDF, let backend validation catch it
      return { valid: true };
    }
  };

  const uploadFiles = async () => {
    if (selectedFiles.length === 0) {
      setError('Please select at least one file to upload');
      return;
    }

    setIsUploading(true);
    setUploadStatus([]);
    setError(null);

    // Validate page counts before uploading
    for (const file of selectedFiles) {
      const validation = await validatePdfPageCount(file);
      if (!validation.valid) {
        setError(validation.error);
        setIsUploading(false);
        return;
      }
    }

    // Check if company is selected using the context
    if (!isCompanySelected || !activeCompany?.companyNumber) {
      setError('No company selected. Please select a company from the landing page first.');
      setIsUploading(false);
      return;
    }

    console.log('Uploading documents for company:', activeCompany.companyName, activeCompany.companyNumber);

    const newUploadStatus = [];

    try {
      await selectedFiles.reduce(async (previousPromise, file) => {
        // Wait for the previous file to finish
        await previousPromise;

        try {
          // Step 1: Get presigned URL data
          console.log(`Getting upload credentials for ${file.name}...`);
          console.log(`Document type: ${documentType}`);
          console.log(`Company: ${activeCompany.companyName} (${activeCompany.companyNumber})`);

          const response = await API.graphql(
            graphqlOperation(uploadDocument, {
              fileName: file.name,
              contentType: file.type,
              bucket: settings.InputBucket, // Explicitly pass the input bucket
              companyNumber: activeCompany.companyNumber, // Pass company number for isolation
              companyName: activeCompany.companyName, // Pass company name for metadata
              documentType: documentType, // NEW: Pass the selected document type
            }),
          );
          const { presignedUrl, objectKey, usePostMethod } = response.data.uploadDocument;

          if (!usePostMethod) {
            throw new Error('Server returned PUT method which is not supported. Please update your backend code.');
          }

          console.log('Received presigned POST data for:', objectKey);

          // Parse the presigned post data
          const presignedPostData = JSON.parse(presignedUrl);
          console.log('Parsed presigned POST data:', presignedPostData);

          // Step 2: Upload file using FormData and POST
          console.log(`Uploading ${file.name} to S3 using POST method...`);

          const formData = new FormData();

          // Add all the fields from the presigned POST data to the form
          Object.entries(presignedPostData.fields).forEach(([key, value]) => {
            formData.append(key, value);
          });

          // Append the file last
          formData.append('file', file);

          // Post the form to S3
          const uploadResponse = await fetch(presignedPostData.url, {
            method: 'POST',
            body: formData,
          });

          console.log(`Upload response status: ${uploadResponse.status}`);

          if (!uploadResponse.ok) {
            console.error(`Upload failed with status: ${uploadResponse.status}`);
            // Try to get more error details
            const errorText = await uploadResponse.text().catch(() => 'Could not read error response');
            console.error(`Error details: ${errorText}`);
            throw new Error(`HTTP error! status: ${uploadResponse.status}`);
          }

          console.log(`Successfully uploaded ${file.name}`);
          newUploadStatus.push({
            file: file.name,
            status: 'success',
            objectKey,
          });
        } catch (err) {
          console.error(`Error uploading ${file.name}:`, err);
          newUploadStatus.push({
            file: file.name,
            status: 'error',
            error: err.message,
          });
        }

        // Update status after each file
        setUploadStatus([...newUploadStatus]);
      }, Promise.resolve());
    } catch (err) {
      console.error('Error in overall upload process:', err);
      setError(`Upload process failed: ${err.message}`);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <Container header={<Header variant="h2">Upload Documents</Header>}>
      {error && (
        <Alert type="error" dismissible onDismiss={() => setError(null)}>
          {error}
        </Alert>
      )}

      <SpaceBetween size="l">
        {/* Document Type Selection Buttons */}
        <Box>
          <FormField label="Select Document Type" description="Choose the type of documents you want to upload">
            <SpaceBetween direction="horizontal" size="m">
              <Button
                variant={documentType === 'invoice' ? 'primary' : 'normal'}
                onClick={() => {
                  setDocumentType('invoice');
                  setSelectedFiles([]);
                  setUploadStatus([]);
                  setError(null);
                }}
                disabled={isUploading}
                iconName={documentType === 'invoice' ? 'check' : undefined}
              >
                📄 Invoices
              </Button>

              <Button
                variant={documentType === 'bank-statement' ? 'primary' : 'normal'}
                onClick={() => {
                  setDocumentType('bank-statement');
                  setSelectedFiles([]);
                  setUploadStatus([]);
                  setError(null);
                }}
                disabled={isUploading}
                iconName={documentType === 'bank-statement' ? 'check' : undefined}
              >
                🏦 Bank Statements
              </Button>

              {/* More document types dropdown */}
              <ButtonDropdown
                items={[
                  { id: 'payslip', text: '💰 Payslip' },
                  { id: 'drivers-license', text: "🪪 Driver's License" },
                  { id: 'w2', text: '📋 W2 Tax Form' },
                  { id: 'check', text: '✅ Check' },
                  { id: 'homeowners-insurance', text: '🏠 Homeowners Insurance' },
                ]}
                onItemClick={({ detail }) => {
                  setDocumentType(detail.id);
                  setSelectedFiles([]);
                  setUploadStatus([]);
                  setError(null);
                }}
                disabled={isUploading}
                variant={documentType && !['invoice', 'bank-statement'].includes(documentType) ? 'primary' : 'normal'}
              >
                {documentType && !['invoice', 'bank-statement'].includes(documentType)
                  ? `✓ ${documentType.replace(/-/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}`
                  : 'Other Document Types'}
              </ButtonDropdown>
            </SpaceBetween>
          </FormField>
        </Box>

        {/* Drag and Drop Upload Area */}
        <Box>
          <div
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            style={{
              border: documentType ? (dragActive ? '3px dashed #0972d3' : '2px dashed #aab7b8') : '2px dashed #d5dbdb',
              borderRadius: '8px',
              padding: '60px 20px',
              textAlign: 'center',
              backgroundColor: documentType ? (dragActive ? '#f0f8ff' : '#fafafa') : '#f5f5f5',
              cursor: documentType ? 'pointer' : 'not-allowed',
              transition: 'all 0.3s ease',
              opacity: documentType ? 1 : 0.5,
            }}
            onClick={handleBrowseFiles}
          >
            <SpaceBetween size="m" alignItems="center">
              <Box fontSize="heading-xl" color={documentType ? 'text-label' : 'text-status-inactive'}>
                📁
              </Box>
              <Box fontSize="heading-m" color={documentType ? 'text-label' : 'text-status-inactive'}>
                {documentType
                  ? dragActive
                    ? 'Drop files here'
                    : 'Drag and drop files here'
                  : 'Select a document type to enable upload'}
              </Box>
              {documentType && (
                <>
                  <Box fontSize="body-s" color="text-body-secondary">
                    or
                  </Box>
                  <Button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleBrowseFiles();
                    }}
                    disabled={!documentType || isUploading}
                  >
                    Browse Files
                  </Button>
                  <Box fontSize="body-s" color="text-body-secondary">
                    Supports: PDF, PNG, JPG (Max 100MB per file, 500 pages for PDFs)
                  </Box>
                </>
              )}
            </SpaceBetween>
          </div>

          {/* Hidden file input */}
          <input
            ref={fileInputRef}
            type="file"
            multiple
            onChange={handleFileChange}
            disabled={!documentType || isUploading}
            style={{ display: 'none' }}
            accept=".pdf,.png,.jpg,.jpeg"
          />
        </Box>

        {/* Selected Files Display */}
        {selectedFiles.length > 0 && (
          <Box>
            <FormField label={`Selected Files (${selectedFiles.length})`}>
              <SpaceBetween size="xs">
                {selectedFiles.map((file, index) => (
                  <Box key={index} fontSize="body-s">
                    📎 {file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)
                  </Box>
                ))}
              </SpaceBetween>
            </FormField>
          </Box>
        )}

        {/* Upload Button */}
        <Button
          variant="primary"
          onClick={uploadFiles}
          loading={isUploading}
          disabled={selectedFiles.length === 0 || isUploading || !documentType}
          iconName="upload"
        >
          {isUploading
            ? `Uploading... (${uploadStatus.length}/${selectedFiles.length})`
            : `Upload ${
                selectedFiles.length > 0 ? `${selectedFiles.length} ${documentType?.replace(/-/g, ' ')}(s)` : 'Files'
              }`}
        </Button>

        {/* Upload Results */}
        {uploadStatus.length > 0 && (
          <Box>
            <Header variant="h3">Upload Results</Header>
            <SpaceBetween size="s">
              {uploadStatus.map((item, index) => (
                // eslint-disable-next-line react/no-array-index-key
                <div key={index}>
                  <StatusIndicator type={item.status === 'success' ? 'success' : 'error'}>
                    {item.file}: {item.status === 'success' ? 'Uploaded successfully' : `Failed - ${item.error}`}
                    {item.status === 'success' && (
                      <Box fontSize="body-s" color="text-body-secondary">
                        Object Key: {item.objectKey}
                      </Box>
                    )}
                  </StatusIndicator>
                </div>
              ))}
            </SpaceBetween>
          </Box>
        )}
      </SpaceBetween>
    </Container>
  );
};

export default UploadDocumentPanel;
