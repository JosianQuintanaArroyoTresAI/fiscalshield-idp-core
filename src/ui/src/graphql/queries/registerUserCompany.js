// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

const registerUserCompany = /* GraphQL */ `
  mutation RegisterUserCompany($companyNumber: String!, $companyName: String!) {
    registerUserCompany(companyNumber: $companyNumber, companyName: $companyName)
  }
`;

export default registerUserCompany;
