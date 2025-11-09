// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { AppLayout, Flashbar } from '@awsui/components-react';
import { Logger } from 'aws-amplify';

import GenAIIDPTopNavigation from '../genai-idp-top-navigation';
import AppSidebar from '../app-sidebar';
import { appLayoutLabels } from '../common/labels';
import { useCompany } from '../../contexts/company';
import useAppContext from '../../contexts/app';

const logger = new Logger('AppLayoutWrapper');

/**
 * AppLayoutWrapper - Provides consistent layout with top navigation and sidebar
 *
 * Features:
 * - Persistent top navigation with user menu and logout
 * - Role-based sidebar navigation (only shown when company is selected)
 * - Responsive layout with collapsible sidebar
 * - Flash notifications support
 */
const AppLayoutWrapper = ({ children, notifications = [], breadcrumbs = null, headerSelector = '#top-navigation' }) => {
  const { navigationOpen, setNavigationOpen } = useAppContext();
  const { isCompanySelected } = useCompany();

  logger.debug('AppLayoutWrapper - Company selected:', isCompanySelected);

  return (
    <>
      <GenAIIDPTopNavigation />
      <AppLayout
        headerSelector={headerSelector}
        navigation={isCompanySelected ? <AppSidebar /> : null}
        navigationOpen={navigationOpen}
        navigationHide={!isCompanySelected}
        onNavigationChange={({ detail }) => setNavigationOpen(detail.open)}
        breadcrumbs={breadcrumbs}
        notifications={notifications && notifications.length > 0 ? <Flashbar items={notifications} /> : null}
        content={children}
        ariaLabels={appLayoutLabels}
        toolsHide
      />
    </>
  );
};

AppLayoutWrapper.propTypes = {
  children: PropTypes.node.isRequired,
  notifications: PropTypes.arrayOf(
    PropTypes.shape({
      type: PropTypes.string,
      content: PropTypes.node,
      dismissible: PropTypes.bool,
      onDismiss: PropTypes.func,
    }),
  ),
  breadcrumbs: PropTypes.node,
  headerSelector: PropTypes.string,
};

export default AppLayoutWrapper;
