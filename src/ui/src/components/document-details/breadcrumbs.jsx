// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
import React from 'react';
import { useParams } from 'react-router-dom';

import { BreadcrumbGroup } from '@awsui/components-react';

import { DOCUMENTS_PATH, COMPANY_SELECT_PATH } from '../../routes/constants';
import { useCompany } from '../../contexts/company';

const Breadcrumbs = () => {
  const { objectKey } = useParams();
  const { activeCompany, isCompanySelected } = useCompany();

  const decodedDocumentId = decodeURIComponent(objectKey);
  // Always ensure the objectKey in the URL is properly encoded to handle slashes correctly
  const encodedObjectKey = encodeURIComponent(decodedDocumentId);

  const items = [{ text: 'Company Selection', href: `#${COMPANY_SELECT_PATH}` }];

  if (isCompanySelected && activeCompany) {
    items.push({
      text: `${activeCompany.companyName} (${activeCompany.companyNumber})`,
      href: `#${DOCUMENTS_PATH}`,
    });
  } else {
    items.push({ text: 'Documents', href: `#${DOCUMENTS_PATH}` });
  }

  items.push({ text: decodedDocumentId, href: `#${DOCUMENTS_PATH}/${encodedObjectKey}` });

  return <BreadcrumbGroup ariaLabel="Breadcrumbs" items={items} />;
};

export default Breadcrumbs;
