// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
import React from 'react';
import PropTypes from 'prop-types';
import {
  Container,
  Header,
  SpaceBetween,
  ColumnLayout,
  Box,
  StatusIndicator,
  Alert,
} from '@awsui/components-react';

/**
 * CompanyOverview Component
 * 
 * Displays basic company information from Companies House
 * Placeholder for future filing history and officers data
 */
const CompanyOverview = ({ companyData, loading }) => {
  if (loading) {
    return (
      <Container>
        <Box textAlign="center" padding="l">
          Loading company overview...
        </Box>
      </Container>
    );
  }

  if (!companyData) {
    return (
      <Container>
        <Alert type="info" header="No Company Data">
          Company information is not available.
        </Alert>
      </Container>
    );
  }

  return (
    <SpaceBetween size="l">
      {/* Basic Company Information */}
      <Container header={<Header variant="h2">Company Information</Header>}>
        <ColumnLayout columns={2} variant="text-grid">
          <div>
            <Box variant="awsui-key-label">Company Name</Box>
            <Box>{companyData.companyName || 'N/A'}</Box>
          </div>
          <div>
            <Box variant="awsui-key-label">Company Number</Box>
            <Box>{companyData.companyNumber || 'N/A'}</Box>
          </div>
          <div>
            <Box variant="awsui-key-label">Status</Box>
            <div>
              <StatusIndicator type={companyData.companyStatus === 'active' ? 'success' : 'warning'}>
                {companyData.companyStatus?.toUpperCase() || 'UNKNOWN'}
              </StatusIndicator>
            </div>
          </div>
          <div>
            <Box variant="awsui-key-label">Date of Creation</Box>
            <Box>{companyData.dateOfCreation || 'N/A'}</Box>
          </div>
        </ColumnLayout>

        {companyData.registeredOfficeAddress && (
          <div style={{ marginTop: '16px' }}>
            <Box variant="awsui-key-label">Registered Office Address</Box>
            <Box variant="p">
              {[
                companyData.registeredOfficeAddress.address_line_1,
                companyData.registeredOfficeAddress.address_line_2,
                companyData.registeredOfficeAddress.locality,
                companyData.registeredOfficeAddress.region,
                companyData.registeredOfficeAddress.postal_code,
              ]
                .filter(Boolean)
                .join(', ')}
            </Box>
          </div>
        )}
      </Container>

      {/* Placeholder sections for future data */}
      <Container header={<Header variant="h2">Filing History</Header>}>
        <Alert type="info" header="Coming Soon">
          Filing history information will be displayed here once the data collection stack is fully integrated.
        </Alert>
      </Container>

      <Container header={<Header variant="h2">Officers & Directors</Header>}>
        <Alert type="info" header="Coming Soon">
          Officers and directors information will be displayed here once the data collection stack is fully integrated.
        </Alert>
      </Container>
    </SpaceBetween>
  );
};

CompanyOverview.propTypes = {
  companyData: PropTypes.shape({
    companyNumber: PropTypes.string,
    companyName: PropTypes.string,
    companyStatus: PropTypes.string,
    dateOfCreation: PropTypes.string,
    registeredOfficeAddress: PropTypes.object,
  }),
  loading: PropTypes.bool,
};

CompanyOverview.defaultProps = {
  companyData: null,
  loading: false,
};

export default CompanyOverview;
