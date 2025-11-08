// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { Box, Modal, SpaceBetween, Button, Select, FormField } from '@awsui/components-react';
import { Logger } from 'aws-amplify';

const logger = new Logger('ReprocessDocumentModal');

const ReprocessDocumentModal = ({ visible, onDismiss, onConfirm, selectedItems = [] }) => {
  const [selectedDocumentType, setSelectedDocumentType] = useState(null);

  let title = 'Reprocess document';
  let message = 'Are you sure you want to reprocess this document?';

  if (selectedItems.length > 1) {
    title = `Reprocess ${selectedItems.length} documents`;
    message = `Are you sure you want to reprocess ${selectedItems.length} documents?`;
  }

  const documentTypeOptions = [
    { label: 'Auto-detect (use AI)', value: '' },
    { label: 'Invoice', value: 'invoice' },
    { label: 'Bank Statement', value: 'bank-statement' },
    { label: 'Payslip', value: 'payslip' },
    { label: 'Receipt', value: 'receipt' },
    { label: 'Contract', value: 'contract' },
    { label: 'Other', value: 'other' },
  ];

  const handleConfirm = () => {
    const documentType = selectedDocumentType?.value || null;
    logger.debug('Reprocessing documents', { selectedItems, documentType });
    onConfirm(documentType);
  };

  return (
    <Modal
      visible={visible}
      onDismiss={onDismiss}
      header={title}
      footer={
        <Box float="right">
          <SpaceBetween direction="horizontal" size="xs">
            <Button variant="link" onClick={onDismiss}>
              Cancel
            </Button>
            <Button variant="primary" onClick={handleConfirm}>
              Reprocess
            </Button>
          </SpaceBetween>
        </Box>
      }
    >
      <SpaceBetween size="m">
        <p>{message}</p>

        <FormField
          label="Document Type"
          description="Select the document type to skip AI classification and improve accuracy. Choose 'Auto-detect' to let AI classify the document."
        >
          <Select
            selectedOption={selectedDocumentType}
            onChange={({ detail }) => setSelectedDocumentType(detail.selectedOption)}
            options={documentTypeOptions}
            placeholder="Choose document type"
            selectedAriaLabel="Selected"
          />
        </FormField>

        <div>
          <p>
            This will trigger workflow reprocessing for the following{' '}
            {selectedItems.length > 1 ? 'documents' : 'document'}:
          </p>
          <ul>
            {selectedItems.map((item) => (
              <li key={item.objectKey}>{item.objectKey}</li>
            ))}
          </ul>
        </div>
      </SpaceBetween>
    </Modal>
  );
};

ReprocessDocumentModal.propTypes = {
  visible: PropTypes.bool.isRequired,
  onDismiss: PropTypes.func.isRequired,
  onConfirm: PropTypes.func.isRequired,
  selectedItems: PropTypes.arrayOf(
    PropTypes.shape({
      objectKey: PropTypes.string.isRequired,
    }),
  ),
};

ReprocessDocumentModal.defaultProps = {
  selectedItems: [],
};

export default ReprocessDocumentModal;
