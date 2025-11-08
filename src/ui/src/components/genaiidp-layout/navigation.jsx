// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
import { React } from 'react';
import { Route, Switch, useLocation } from 'react-router-dom';
import { SideNavigation } from '@awsui/components-react';
import useSettingsContext from '../../contexts/settings';
import useAppContext from '../../contexts/app';
import { useCompany } from '../../contexts/company';

import {
  DOCUMENTS_PATH,
  DOCUMENTS_KB_QUERY_PATH,
  DOCUMENTS_ANALYTICS_PATH,
  DEFAULT_PATH,
  UPLOAD_DOCUMENT_PATH,
  CONFIGURATION_PATH,
  DISCOVERY_PATH,
  COMPANY_SELECT_PATH,
  COMPANY_ANALYSIS_PATH,
  OVERVIEW_DASHBOARD_PATH,
  CLIENT_TAKEON_PATH,
  INVOICE_INSIGHTS_PATH,
  BANK_INSIGHTS_PATH,
} from '../../routes/constants';

export const documentsNavHeader = { text: 'Tools', href: `#${DEFAULT_PATH}` };

// Function to generate navigation items based on user role
export const getDocumentsNavItems = (isAdmin = false, hasActiveCompany = false) => {
  const baseItems = [
    {
      type: 'link',
      text: '← Change Company',
      href: `#${COMPANY_SELECT_PATH}`,
      info: 'Return to company selection',
    },
    { type: 'divider' },
  ];

  // Company-specific menu items (only show when company is selected)
  const companyItems = hasActiveCompany
    ? [
        {
          type: 'section',
          text: 'Company',
          items: [
            { type: 'link', text: 'Overview Dashboard', href: `#${OVERVIEW_DASHBOARD_PATH}` },
            { type: 'link', text: 'Client Take-On', href: `#${CLIENT_TAKEON_PATH}` },
            { type: 'link', text: 'Invoice Insights', href: `#${INVOICE_INSIGHTS_PATH}` },
            { type: 'link', text: 'Bank Insights', href: `#${BANK_INSIGHTS_PATH}` },
          ],
        },
        { type: 'divider' },
      ]
    : [];

  const documentItems = [
    { type: 'link', text: 'Document List', href: `#${DOCUMENTS_PATH}` },
    { type: 'link', text: 'Upload Document(s)', href: `#${UPLOAD_DOCUMENT_PATH}` },
  ];

  // Items only visible to administrators
  const adminItems = [
    { type: 'link', text: 'Document KB', href: `#${DOCUMENTS_KB_QUERY_PATH}` },
    { type: 'link', text: 'Agent Analysis', href: `#${DOCUMENTS_ANALYTICS_PATH}` },
    { type: 'link', text: 'Discovery', href: `#${DISCOVERY_PATH}` },
    { type: 'link', text: 'View/Edit Configuration', href: `#${CONFIGURATION_PATH}` },
  ];

  const items = [...baseItems, ...companyItems, ...documentItems];

  if (isAdmin) {
    items.push(...adminItems);

    items.push({
      type: 'section',
      text: 'Resources',
      items: [
        {
          type: 'link',
          text: 'README',
          href: 'https://github.com/aws-solutions-library-samples/accelerated-intelligent-document-processing-on-aws/blob/main/README.md',
          external: true,
        },
        {
          type: 'link',
          text: 'Source Code',
          href: 'https://github.com/aws-solutions-library-samples/accelerated-intelligent-document-processing-on-aws',
          external: true,
        },
      ],
    });
  }

  return items;
};

// Default items (for backwards compatibility)
export const documentsNavItems = getDocumentsNavItems(true);

const defaultOnFollowHandler = (ev) => {
  // Prevent navigation for deployment info items (make them non-clickable)
  if (ev.detail.href === '#deployment-info') {
    ev.preventDefault();
    return;
  }
  // XXX keep the locked href for our demo pages
  // ev.preventDefault();
  console.log(ev);
};

/* eslint-disable react/prop-types */
const Navigation = ({ header = documentsNavHeader, items = null, onFollowHandler = defaultOnFollowHandler }) => {
  const location = useLocation();
  const path = location.pathname;
  const { isAdmin } = useAppContext();
  const { isCompanySelected } = useCompany();
  const { settings } = useSettingsContext() || {};

  let activeHref = `#${DEFAULT_PATH}`;

  // Determine active link based on current path, most specific routes first
  if (path.includes(CONFIGURATION_PATH)) {
    activeHref = `#${CONFIGURATION_PATH}`;
  } else if (path.includes(DOCUMENTS_KB_QUERY_PATH)) {
    activeHref = `#${DOCUMENTS_KB_QUERY_PATH}`;
  } else if (path.includes(DOCUMENTS_ANALYTICS_PATH)) {
    activeHref = `#${DOCUMENTS_ANALYTICS_PATH}`;
  } else if (path.includes(UPLOAD_DOCUMENT_PATH)) {
    activeHref = `#${UPLOAD_DOCUMENT_PATH}`;
  } else if (path.includes(DISCOVERY_PATH)) {
    activeHref = `#${DISCOVERY_PATH}`;
  } else if (path.includes(OVERVIEW_DASHBOARD_PATH)) {
    activeHref = `#${OVERVIEW_DASHBOARD_PATH}`;
  } else if (path.includes(CLIENT_TAKEON_PATH)) {
    activeHref = `#${CLIENT_TAKEON_PATH}`;
  } else if (path.includes(INVOICE_INSIGHTS_PATH)) {
    activeHref = `#${INVOICE_INSIGHTS_PATH}`;
  } else if (path.includes(BANK_INSIGHTS_PATH)) {
    activeHref = `#${BANK_INSIGHTS_PATH}`;
  } else if (path.includes(DOCUMENTS_PATH)) {
    activeHref = `#${DOCUMENTS_PATH}`;
  }

  // Get navigation items based on role and company selection (or use provided items)
  const navigationItems = [...(items || getDocumentsNavItems(isAdmin, isCompanySelected))];

  // Show deployment info only to administrators
  if (isAdmin && (settings?.Version || settings?.StackName || settings?.BuildDateTime || settings?.IDPPattern)) {
    const deploymentInfoItems = [];

    if (settings?.StackName) {
      deploymentInfoItems.push({
        type: 'link',
        text: `Stack Name: ${settings.StackName}`,
        href: '#stackname',
      });
    }

    if (settings?.Version) {
      deploymentInfoItems.push({
        type: 'link',
        text: `Version: ${settings.Version}`,
        href: '#version',
      });
    }

    if (settings?.BuildDateTime) {
      deploymentInfoItems.push({
        type: 'link',
        text: `Build: ${settings.BuildDateTime}`,
        href: '#builddatetime',
      });
    }

    if (settings?.IDPPattern) {
      const pattern = settings.IDPPattern.split(' ')[0];
      deploymentInfoItems.push({
        type: 'link',
        text: `Pattern: ${pattern}`,
        href: '#idppattern',
      });
    }

    navigationItems.push({
      type: 'section',
      text: 'Deployment Info',
      items: deploymentInfoItems,
    });
  }

  return (
    <Switch>
      <Route path={DOCUMENTS_PATH}>
        <SideNavigation
          items={navigationItems}
          header={header || documentsNavHeader}
          activeHref={activeHref}
          onFollow={onFollowHandler}
        />
      </Route>
    </Switch>
  );
};

export default Navigation;
