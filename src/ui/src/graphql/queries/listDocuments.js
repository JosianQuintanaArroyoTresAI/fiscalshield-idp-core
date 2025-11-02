// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
import gql from 'graphql-tag';

export default gql`
  query Query($endDateTime: AWSDateTime, $startDateTime: AWSDateTime, $companyNumber: String) {
    listDocuments(endDateTime: $endDateTime, startDateTime: $startDateTime, companyNumber: $companyNumber) {
      Calls {
        ObjectKey
        PK
        SK
      }
      nextToken
    }
  }
`;
