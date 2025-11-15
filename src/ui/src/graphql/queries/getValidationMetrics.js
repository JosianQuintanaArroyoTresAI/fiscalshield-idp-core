// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

const getValidationMetrics = /* GraphQL */ `
  query GetValidationMetrics($timeRangeDays: Int, $companyNumber: String, $userId: String) {
    getValidationMetrics(timeRangeDays: $timeRangeDays, companyNumber: $companyNumber, userId: $userId) {
      timeRangeDays
      totalValidations
      matches
      mismatches
      matchRatePercent
      mismatchRatePercent
      byDocumentType
      byConfidenceBucket
      highConfidenceMismatches {
        documentId
        userSelection
        modelPrediction
        confidence
        createdAt
        validationId
        company
      }
      summary {
        modelAccuracy
        totalDocumentsValidated
        requiresAttention
      }
    }
  }
`;

export default getValidationMetrics;
