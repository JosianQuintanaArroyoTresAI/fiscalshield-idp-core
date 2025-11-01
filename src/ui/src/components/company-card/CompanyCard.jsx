// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import React from 'react';
import PropTypes from 'prop-types';
import { Container, Box, Badge, Button, ColumnLayout, SpaceBetween } from '@awsui/components-react';
import { formatCompanyDate, formatRelativeTime } from '../../services/userCompanies';

/**
 * CompanyCard component to display company information in a card format
 * @param {Object} props
 * @param {Object} props.company - Company data object
 * @param {Function} props.onViewDocuments - Callback when "View Documents" is clicked
 * @param {Function} props.onViewIntelligence - Callback when "View Intelligence" is clicked
 */
const CompanyCard = ({ company, onViewDocuments, onViewIntelligence }) => {
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

  return (
    <Container
      footer={
        <Box float="right">
          <SpaceBetween direction="horizontal" size="xs">
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
};

CompanyCard.defaultProps = {
  onViewDocuments: null,
};

export default CompanyCard;
