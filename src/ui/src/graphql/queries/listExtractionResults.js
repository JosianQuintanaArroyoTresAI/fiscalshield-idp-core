// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

const listExtractionResults = /* GraphQL */ `
  query ListExtractionResults($companyNumber: String!, $documentType: String!, $limit: Int, $nextToken: String) {
    listExtractionResults(
      companyNumber: $companyNumber
      documentType: $documentType
      limit: $limit
      nextToken: $nextToken
    ) {
      items {
        PK
        SK
        DocumentId
        DocumentType
        CompanyNumber
        CompanyName
        UserId
        ExtractionStatus
        ProcessedAt
        SectionId
        ConfidenceScore
        InvoiceNumber
        InvoiceDate
        DueDate
        VendorName
        SupplierAddress
        TotalAmount
        Currency
        BankName
        AccountNumber
        StatementDate
        StatementPeriod
        OpeningBalance
        ClosingBalance
        S3Uri
        ModelUsed
        ExtractedData
        InvoiceType
        InvoiceTypeConfidence
        SupplierNameConfidence
        TotalAmountConfidence
        InvoiceNumberConfidence
        VATNumberConfidence
        InvoiceDateConfidence
        CompositeConfidence
        QualityTier
        HITLRequired
        HITLReason
      }
      nextToken
    }
  }
`;

export default listExtractionResults;
