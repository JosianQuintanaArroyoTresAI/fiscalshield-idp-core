// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
import React from 'react';
import PropTypes from 'prop-types';
import { useHistory, useLocation } from 'react-router-dom';
import { SideNavigation, Box, StatusIndicator } from '@awsui/components-react';
import { Logger } from 'aws-amplify';

import { useCompany } from '../../contexts/company';
import useAppContext from '../../contexts/app';
import {
  COMPANY_SELECT_PATH,
  COMPANY_ANALYSIS_PATH,
  UPLOAD_DOCUMENT_PATH,
  DOCUMENTS_PATH,
  DOCUMENTS_KB_QUERY_PATH,
  DOCUMENTS_ANALYTICS_PATH,
  CONFIGURATION_PATH,
  DISCOVERY_PATH,
  ADMIN_VALIDATION_METRICS_PATH,
} from '../../routes/constants';

const logger = new Logger('AppSidebar');

const AppSidebar = () => {
  const history = useHistory();
  const location = useLocation();
  const { activeCompany, clearCompany } = useCompany();
  const { isAdmin } = useAppContext();

  if (!activeCompany) {
    return null; // Don't show sidebar if no company selected
  }

  const companyNumber = activeCompany.companyNumber;
  const companyName = activeCompany.companyName || 'Unknown Company';

  // Build navigation items based on role
  const navigationItems = [
    {
      type: 'section',
      text: 'Company Context',
      items: [
        {
          type: 'link',
          text: (
            <Box>
              <Box variant="awsui-key-label" fontSize="body-s">
                Active Company
              </Box>
              <Box fontWeight="bold">{companyName}</Box>
              <Box fontSize="body-s" color="text-body-secondary">
                {companyNumber}
              </Box>
            </Box>
          ),
          href: '#',
          info: <StatusIndicator type="success">Active</StatusIndicator>,
        },
      ],
    },
    { type: 'divider' },
    {
      type: 'section',
      text: 'Analysis',
      items: [
        {
          type: 'link',
          text: 'Company Intelligence',
          href: COMPANY_ANALYSIS_PATH.replace(':companyNumber', companyNumber),
          info: '🔍',
        },
      ],
    },
    { type: 'divider' },
    {
      type: 'section',
      text: 'Documents',
      items: [
        {
          type: 'link',
          text: 'Upload Documents',
          href: UPLOAD_DOCUMENT_PATH,
          info: '📤',
        },
        {
          type: 'link',
          text: 'Documents',
          href: DOCUMENTS_PATH,
          info: '📄',
        },
      ],
    },
  ];

  // Add admin-only items
  if (isAdmin) {
    navigationItems.push(
      { type: 'divider' },
      {
        type: 'section',
        text: 'Advanced',
        items: [
          {
            type: 'link',
            text: 'Validation Metrics',
            href: ADMIN_VALIDATION_METRICS_PATH,
            info: '📊',
          },
          {
            type: 'link',
            text: 'Query Knowledge Base',
            href: DOCUMENTS_KB_QUERY_PATH,
            info: '💬',
          },
          {
            type: 'link',
            text: 'Analytics & Agents',
            href: DOCUMENTS_ANALYTICS_PATH,
            info: '🤖',
          },
          {
            type: 'link',
            text: 'Configuration',
            href: CONFIGURATION_PATH,
            info: '⚙️',
          },
          {
            type: 'link',
            text: 'Discovery',
            href: DISCOVERY_PATH,
            info: '🔍',
          },
        ],
      },
    );
  }

  // Add footer with company switch option
  navigationItems.push(
    { type: 'divider' },
    {
      type: 'link',
      text: 'Switch Company',
      href: COMPANY_SELECT_PATH,
      info: '🔄',
    },
  );

  const handleFollow = (event) => {
    event.preventDefault();
    const href = event.detail.href;

    // If switching company, clear the active company
    if (href === COMPANY_SELECT_PATH) {
      logger.debug('Switching company - clearing active company');
      clearCompany();
    }

    history.push(href);
  };

  return (
    <SideNavigation
      activeHref={location.pathname}
      header={{
        text: 'FiscalShield',
        href: COMPANY_SELECT_PATH,
      }}
      items={navigationItems}
      onFollow={handleFollow}
    />
  );
};

AppSidebar.propTypes = {};

export default AppSidebar;
