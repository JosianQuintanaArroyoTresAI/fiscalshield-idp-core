// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

const getUserCompanies = /* GraphQL */ `
  query GetUserCompanies {
    getUserCompanies {
      company_number
      company_name
      user_id
      document_count
      first_registered
      last_activity
      document_types
    }
  }
`;

export default getUserCompanies;
