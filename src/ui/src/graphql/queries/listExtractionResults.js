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
        AnalysisStatus
        ProcessedAt
        SectionId
        ConfidenceScore
        InvoiceType
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
        TransactionCount
        TotalCredits
        TotalDebits
        TransactionId
        TransactionDate
        TransactionDescription
        TransactionAmount
        TransactionType
        AccountBalance
        Reference
        SourcePage
        SortCode
        S3Uri
        ModelUsed
        ExtractedData
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
