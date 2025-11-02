// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import React, { useState } from 'react';
import PropTypes from 'prop-types';
import {
  Container,
  Box,
  Badge,
  Button,
  ColumnLayout,
  SpaceBetween,
  Modal,
  ButtonDropdown,
} from '@awsui/components-react';
import { formatCompanyDate, formatRelativeTime } from '../../services/userCompanies';

/**
 * CompanyCard component to display company information in a card format
 * @param {Object} props
 * @param {Object} props.company - Company data object
 * @param {Function} props.onViewDocuments - Callback when "View Documents" is clicked
 * @param {Function} props.onViewIntelligence - Callback when "View Intelligence" is clicked
 * @param {Function} props.onDelete - Callback when "Delete" is clicked
 */
const CompanyCard = ({ company, onViewDocuments, onViewIntelligence, onDelete }) => {
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const {
    company_number: companyNumber,
    company_name: companyName,
    document_count: documentCount,
    first_registered: firstRegistered,
    last_activity: lastActivity,
    document_types: documentTypes = [],
  } = company;

  const handleViewDocuments = () => {
    if (onViewDocuments) {
      onViewDocuments(company);
    }
  };

  const handleViewIntelligence = () => {
    if (onViewIntelligence) {
      onViewIntelligence(company);
    }
  };

  const handleDeleteClick = () => {
    setShowDeleteModal(true);
  };

  const handleDeleteConfirm = () => {
    setShowDeleteModal(false);
    if (onDelete) {
      onDelete(company);
    }
  };

  const handleDeleteCancel = () => {
    setShowDeleteModal(false);
  };

  return (
    <>
      <Container
        footer={
          <Box float="right">
            <SpaceBetween direction="horizontal" size="xs">
              <ButtonDropdown
                items={[
                  {
                    id: 'delete',
                    text: 'Delete Company',
                    iconName: 'remove',
                    disabled: !onDelete,
                  },
                ]}
                onItemClick={({ detail }) => {
                  if (detail.id === 'delete') {
                    handleDeleteClick();
                  }
                }}
                variant="icon"
                ariaLabel="Company actions"
              />
              <Button onClick={handleViewIntelligence} iconAlign="right" iconName="status-info">
                View Intelligence
              </Button>
              <Button variant="primary" onClick={handleViewDocuments} iconAlign="right" iconName="arrow-right">
                View Documents
              </Button>
            </SpaceBetween>
          </Box>
        }
      >
        <SpaceBetween size="m">
          <div>
            <Box variant="h3" margin={{ bottom: 'xxs' }}>
              {companyName || 'Unknown Company'}
            </Box>
            <Box variant="small" color="text-status-inactive">
              Company #{companyNumber}
            </Box>
          </div>

          <ColumnLayout columns={3} variant="text-grid">
            <div>
              <Box variant="awsui-key-label">Documents</Box>
              <Box fontSize="heading-l" fontWeight="bold">
                {documentCount || 0}
              </Box>
            </div>

            <div>
              <Box variant="awsui-key-label">Last Activity</Box>
              <Box>{formatRelativeTime(lastActivity)}</Box>
              <Box variant="small" color="text-status-inactive">
                {formatCompanyDate(lastActivity)}
              </Box>
            </div>

            <div>
              <Box variant="awsui-key-label">First Registered</Box>
              <Box>{formatCompanyDate(firstRegistered)}</Box>
            </div>
          </ColumnLayout>

          {documentTypes && documentTypes.length > 0 && (
            <div>
              <Box variant="awsui-key-label" margin={{ bottom: 'xxs' }}>
                Document Types
              </Box>
              <SpaceBetween size="xs" direction="horizontal">
                {documentTypes.map((type) => (
                  <Badge key={type} color="blue">
                    {type}
                  </Badge>
                ))}
              </SpaceBetween>
            </div>
          )}
        </SpaceBetween>
      </Container>

      {/* Delete Confirmation Modal */}
      <Modal
        visible={showDeleteModal}
        onDismiss={handleDeleteCancel}
        header="Delete Company"
        closeAriaLabel="Close"
        footer={
          <Box float="right">
            <SpaceBetween direction="horizontal" size="xs">
              <Button variant="link" onClick={handleDeleteCancel}>
                Cancel
              </Button>
              <Button variant="primary" onClick={handleDeleteConfirm}>
                Delete
              </Button>
            </SpaceBetween>
          </Box>
        }
      >
        <SpaceBetween size="m">
          <Box variant="p">
            Are you sure you want to delete <strong>{companyName}</strong> (#{companyNumber}) from your registered
            companies?
          </Box>
          <Box variant="p" color="text-status-warning">
            This will remove the company from your list, but any cached data and documents will remain in the system.
          </Box>
        </SpaceBetween>
      </Modal>
    </>
  );
};

CompanyCard.propTypes = {
  company: PropTypes.shape({
    company_number: PropTypes.string.isRequired,
    company_name: PropTypes.string.isRequired,
    document_count: PropTypes.number,
    first_registered: PropTypes.number,
    last_activity: PropTypes.number,
    document_types: PropTypes.arrayOf(PropTypes.string),
  }).isRequired,
  onViewDocuments: PropTypes.func,
  onViewIntelligence: PropTypes.func,
  onDelete: PropTypes.func,
};

CompanyCard.defaultProps = {
  onViewDocuments: null,
};

export default CompanyCard;
