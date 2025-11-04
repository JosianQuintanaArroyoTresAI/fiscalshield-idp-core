// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
import gql from 'graphql-tag';

export default gql`
  mutation UploadDocument(
    $fileName: String!
    $contentType: String
    $bucket: String
    $companyNumber: String
    $companyName: String
    $documentType: String
  ) {
    uploadDocument(
      fileName: $fileName
      contentType: $contentType
      bucket: $bucket
      companyNumber: $companyNumber
      companyName: $companyName
      documentType: $documentType
    ) {
      presignedUrl
      objectKey
      usePostMethod
    }
  }
`;
