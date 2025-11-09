// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
import React from 'react';
import PropTypes from 'prop-types';
import { Redirect } from 'react-router-dom';
import { Logger } from 'aws-amplify';

import { useCompany } from '../contexts/company';
import { COMPANY_SELECT_PATH } from '../routes/constants';

const logger = new Logger('RequireCompany');

/**
 * RequireCompany - Route guard that ensures a company is selected
 *
 * Redirects to company selection page if no active company
 * This ensures users cannot access company-specific features without context
 */
const RequireCompany = ({ children }) => {
  const { isCompanySelected } = useCompany();

  if (!isCompanySelected) {
    logger.warn('No company selected - redirecting to company select');
    return <Redirect to={COMPANY_SELECT_PATH} />;
  }

  return <>{children}</>;
};

RequireCompany.propTypes = {
  children: PropTypes.node.isRequired,
};

export default RequireCompany;
