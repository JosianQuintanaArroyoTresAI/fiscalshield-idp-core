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
        Description
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
        # Transaction Analysis Fields
        ExpenseCategory
        CategorizationConfidence
        ComplianceScore
        RiskFlags
        CategorizationReasoning
        RecommendedAction
        HMRCConcern
        AnalyzedAt
        ComplianceRiskScore
        ComplianceRiskTier
        ComplianceFlags
        ComplianceReasons
        ThresholdFlag
        CashRiskFlag
        GeographicRiskFlag
        StructuringFlag
        VagueDescriptionFlag
        # HMRC Compliance Fields
        CounterpartyName
        Direction
        PaymentMethod
        CounterpartyCountry
        # Extraction Confidence Scores
        DateConfidence
        AmountConfidence
        DescriptionConfidence
        AccountInfoConfidence
        # Invoice Tax Deductibility Analysis
        DeductibilityStatus
        DeductibilityPercentage
        DeductibilityConfidence
        BIMSections
        DeductibilityReasoning
        DocumentationRequired
        RecommendedAction
        AddbackAmount
        AddbackReason
        Test1_WhollyExclusively
        Test1_Reasoning
        Test1_Confidence
        Test2_Entertainment
        Test2_Reasoning
        Test2_Confidence
        Test3_Travel
        Test3_Reasoning
        Test3_Confidence
        Test4_Training
        Test4_Reasoning
        Test4_Confidence
        Test5_StatutoryBan
        Test5_Reasoning
        Test5_Confidence
        Test6_MixedUse
        Test6_BusinessPercentage
        Test6_Reasoning
        Test6_Confidence
        Test6_DocumentationNeeded
        Test7_Duality
        Test7_Reasoning
        Test7_Confidence
      }
      nextToken
    }
  }
`;

export default listExtractionResults;
