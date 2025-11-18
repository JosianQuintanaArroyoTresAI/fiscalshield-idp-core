# Transaction Detail View - Field Analysis

## Currently Displayed in Table (Summary View)
- ✅ Date
- ✅ Description  
- ✅ Category
- ✅ Amount
- ✅ Compliance Score
- ✅ Risk Flags
- ✅ Recommended Action
- ✅ Analysis Status

## Available Fields NOT Currently Shown

### **High Priority for Detail View** (Users will definitely want these)

1. **CategorizationReasoning** ⭐⭐⭐
   - **Why**: Explains WHY the AI chose this category/score
   - **User value**: Transparency, trust, ability to verify
   - **Display**: Full text paragraph in detail modal

2. **ComplianceReasons** ⭐⭐⭐
   - **Why**: Lists specific compliance concerns found
   - **User value**: Understand what triggered flags
   - **Display**: Bulleted list of reasons

3. **Reference** ⭐⭐
   - **Why**: Payment reference/invoice number
   - **User value**: Cross-reference with invoices, reconciliation
   - **Display**: Simple text field

4. **Counterparty Name** ⭐⭐⭐
   - **Why**: Who the payment was to/from
   - **User value**: Essential for understanding the transaction
   - **Display**: Prominent field, possibly linkable to counterparty analysis

5. **Direction** (Inbound/Outbound) ⭐⭐
   - **Why**: Money in vs money out
   - **User value**: Quick understanding of transaction type
   - **Display**: Badge (green for in, red for out)

6. **Payment Method** ⭐⭐
   - **Why**: How was it paid (BACS, CHAPS, Card, Cash, DD, etc.)
   - **User value**: Compliance context (cash = higher scrutiny)
   - **Display**: Badge or icon

7. **Account Balance** (after transaction) ⭐
   - **Why**: Running balance
   - **User value**: Context for transaction impact
   - **Display**: Formatted currency

8. **Source Page** ⭐
   - **Why**: Which page of the PDF this came from
   - **User value**: Ability to view original document at exact page
   - **Display**: Link "View on page X"

### **Medium Priority for Detail View**

9. **CounterpartyCountry** ⭐⭐
   - **Why**: Geographic risk assessment
   - **User value**: HMRC compliance (offshore payments flagged)
   - **Display**: Flag icon + country name

10. **HMRCConcern** (boolean) ⭐⭐
    - **Why**: AI flagged this as potentially concerning to tax inspector
    - **User value**: Prioritize manual review
    - **Display**: Warning badge if TRUE

11. **Individual Compliance Flags** ⭐⭐
    - ThresholdFlag (£10k/£15k breach)
    - CashRiskFlag (large cash transactions)
    - GeographicRiskFlag (high-risk countries)
    - StructuringFlag (suspicious patterns)
    - VagueDescriptionFlag (unclear purpose)
    - **User value**: Granular understanding of specific risks
    - **Display**: Expandable section showing each flag type

12. **Confidence Scores** (extraction quality) ⭐
    - DateConfidence
    - AmountConfidence
    - DescriptionConfidence
    - AccountInfoConfidence
    - CompositeConfidence
    - **User value**: Trust in extraction accuracy
    - **Display**: Progress bars or percentage (can be collapsed)

13. **Account Details** ⭐
    - AccountNumber (masked)
    - SortCode
    - BankName
    - StatementPeriod
    - **User value**: Context for which account
    - **Display**: Read-only metadata section

14. **ComplianceRiskTier** ⭐⭐
    - LOW / MEDIUM / HIGH / CRITICAL
    - **User value**: Overall risk classification
    - **Display**: Large badge at top of detail view

15. **Transaction Type** ⭐
    - DD (Direct Debit), SO (Standing Order), CARD, TRANSFER, etc.
    - **User value**: Understanding transaction nature
    - **Display**: Badge

### **Lower Priority (Metadata)**

16. **Timestamps**
    - AnalyzedAt
    - CreatedAt
    - UpdatedAt
    - **User value**: Audit trail
    - **Display**: Small text at bottom

17. **ModelUsed** 
    - Which AI model analyzed it
    - **User value**: Debugging/quality tracking
    - **Display**: Small metadata field

18. **QualityTier**
    - Extraction quality rating
    - **User value**: Trust in data
    - **Display**: Small badge

## Recommended Detail Modal Structure

```
┌──────────────────────────────────────────────────────────┐
│  Transaction Details                              [X]     │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  📊 COMPLIANCE ASSESSMENT                                │
│  ┌────────────────────────────────────────────────────┐ │
│  │ Compliance Score: 4/5 ████████░░                   │ │
│  │ Risk Tier: MEDIUM                                  │ │
│  │ Recommended Action: REVIEW DOCUMENTATION           │ │
│  └────────────────────────────────────────────────────┘ │
│                                                           │
│  💰 TRANSACTION DETAILS                                  │
│  Date:           15 Jan 2024                             │
│  Description:    AMAZON MARKETPLACE LONDON               │
│  Amount:         £125.50 (Outbound)                      │
│  Balance After:  £5,234.12                               │
│  Reference:      INV-2024-001                            │
│  Payment Method: CARD                                    │
│  Counterparty:   Amazon EU S.a.r.L                       │
│  Country:        🇬🇧 United Kingdom                      │
│                                                           │
│  📁 CATEGORIZATION                                       │
│  Category:     Office Supplies                           │
│  Confidence:   HIGH                                      │
│  Reasoning:                                              │
│  "Purchase from Amazon Marketplace. Description         │
│   indicates office supplies. Amount reasonable for      │
│   business expense. No red flags detected."             │
│                                                           │
│  🚨 RISK FLAGS (2)                                       │
│  • VAGUE_DESCRIPTION - Description lacks detail         │
│  • WEEKEND_PURCHASE - Transaction on Saturday           │
│                                                           │
│  ⚖️ COMPLIANCE DETAILS                                   │
│  HMRC Concern:      No                                   │
│  Threshold Flag:    None (under £10k)                    │
│  Cash Risk:         None                                 │
│  Geographic Risk:   None (UK domestic)                   │
│  Structuring:       None                                 │
│                                                           │
│  Compliance Reasons:                                     │
│  • Weekend purchase may indicate personal use           │
│  • Generic description from marketplace seller          │
│  • Recommend retaining purchase receipt for audit       │
│                                                           │
│  📄 DOCUMENT SOURCE                                      │
│  Bank:           Barclays                                │
│  Account:        ****1234                                │
│  Statement:      Jan 2024                                │
│  Source Page:    [View on page 3] →                     │
│                                                           │
│  🔍 EXTRACTION QUALITY                                   │
│  Composite Confidence: 92%                               │
│  Date:        95%  ████████████████████░                 │
│  Amount:      98%  ███████████████████░                  │
│  Description: 85%  █████████████████░░░                  │
│                                                           │
│  ℹ️ METADATA                                             │
│  Analyzed: 17 Nov 2024, 14:23                           │
│  Model: Claude 3.5 Sonnet                               │
│  Quality Tier: EXCELLENT                                │
│                                                           │
│  [Edit Category]  [Override Action]  [Add Note]         │
└──────────────────────────────────────────────────────────┘
```

## Implementation Recommendations

### 1. **Add Row Click Handler**
```jsx
<Table
  onRowClick={({ detail }) => setSelectedTransaction(detail.item)}
  // ... existing props
/>
```

### 2. **Create Detail Modal Component**
```jsx
<Modal
  visible={!!selectedTransaction}
  onDismiss={() => setSelectedTransaction(null)}
  size="large"
  header="Transaction Details"
>
  <TransactionDetailView transaction={selectedTransaction} />
</Modal>
```

### 3. **Pagination/Infinite Scroll**
Since bank statements can have 500+ transactions:
```jsx
<Table
  variant="container"
  loading={loadingTransactions}
  loadingText="Loading transactions..."
  pagination={
    <Pagination
      currentPageIndex={currentPage}
      pagesCount={Math.ceil(transactions.length / 50)}
      onChange={({ detail }) => setCurrentPage(detail.currentPageIndex)}
    />
  }
/>
```

### 4. **Quick Actions in Table**
Add an actions column for common tasks:
```jsx
{
  id: 'actions',
  header: 'Actions',
  cell: (item) => (
    <ButtonDropdown
      items={[
        { id: 'view', text: 'View Details' },
        { id: 'viewDoc', text: 'View Source Document' },
        { id: 'edit', text: 'Edit Category' },
        { id: 'flag', text: 'Flag for Review' },
      ]}
      onItemClick={({ detail }) => handleAction(detail.id, item)}
    >
      Actions
    </ButtonDropdown>
  )
}
```

### 5. **Filtering & Sorting**
Users will want to filter by:
- Compliance Score (1-5)
- Risk Flags (Clean, High Risk, etc.)
- Category
- Date Range
- Amount Range
- Analysis Status

## Fields Priority Summary

**Must Have in Detail View:**
1. CategorizationReasoning
2. ComplianceReasons  
3. CounterpartyName
4. Direction
5. PaymentMethod
6. Reference

**Should Have:**
7. CounterpartyCountry
8. HMRCConcern
9. Individual compliance flags breakdown
10. Source page link
11. Account balance

**Nice to Have:**
12. Confidence scores breakdown
13. Metadata (timestamps, model, quality)
