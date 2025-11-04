// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

const reprocessDocument = /* GraphQL */ `
  mutation ReprocessDocument($objectKeys: [String!]!, $documentType: String) {
    reprocessDocument(objectKeys: $objectKeys, documentType: $documentType)
  }
`;

export default reprocessDocument;
