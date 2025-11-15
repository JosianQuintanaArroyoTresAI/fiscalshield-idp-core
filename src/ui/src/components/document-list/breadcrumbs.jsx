// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
import React from 'react';

import { BreadcrumbGroup } from '@awsui/components-react';

import { DOCUMENTS_PATH, COMPANY_SELECT_PATH } from '../../routes/constants';
import { useCompany } from '../../contexts/company';

const Breadcrumbs = () => {
  const { activeCompany, isCompanySelected } = useCompany();

  const items = [{ text: 'Company Selection', href: `#${COMPANY_SELECT_PATH}` }];

  if (isCompanySelected && activeCompany) {
    items.push({
      text: `${activeCompany.companyName} (${activeCompany.companyNumber})`,
      href: `#${DOCUMENTS_PATH}`,
    });
  } else {
    items.push({ text: 'Documents', href: `#${DOCUMENTS_PATH}` });
  }

  return <BreadcrumbGroup ariaLabel="Breadcrumbs" items={items} />;
};

export default Breadcrumbs;
