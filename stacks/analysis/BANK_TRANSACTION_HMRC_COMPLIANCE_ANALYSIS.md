Bank Transaction HMRC Compliance Enhancement Analysis - REVISED
Date: 2025-11-16
Status: Analysis Phase - No Implementation Yet
Purpose: Identify UK HMRC compliance patterns detectable from bank transaction data alone and architectural constraints

Executive Summary
Current implementation uses Claude AI to analyze batches of 15 transactions at a time. This architecture is excellent for transaction-level analysis but creates challenges for cross-transaction pattern detection that requires viewing all transactions together.
Key Finding: MLR 2017 explicitly requires detection of "linked transactions" - this is a legal mandate, not optional, and cannot be achieved with batch-only processing.
This document identifies:

What patterns we can detect from bank transaction data alone (not invoices, VAT returns, or payroll)
Which patterns work in a single Lambda pass (batch processing)
Which patterns require full-dataset analysis (post-collection)
Architectural solutions to meet MLR 2017 requirements


Critical Data Audit Required BEFORE Implementation
You must verify what data is actually in your extracted bank statement transactions:
Essential Fields (Must Have):

✅ Transaction date (ideally with timestamp, minimum date-only)
✅ Transaction description/narrative
✅ Amount (positive/negative or separate debit/credit flag)
✅ Counterparty name (payee/payer)
✅ Payment method code (BACS, CHAPS, FASTER_PAYMENT, CASH, ATM, DD, SO, CARD)

Critical Fields (Needed for Advanced Detection):

❓ Inbound vs Outbound flag - CRITICAL for circular transaction detection
❓ Counterparty bank details (IBAN, Sort Code, country) - needed for geographic risk
❓ Transaction timestamp (hour/minute) - needed for same-day linked detection
❓ Reference/invoice numbers - helps with pattern matching
❓ Transaction type codes (salary, dividend, loan, etc.)

Impact of Missing Fields:

No inbound/outbound flag → Cannot detect circular transactions at all
No counterparty country → Cannot detect geographic risk (FATF compliance)
No timestamps → Can only detect linked transactions by date, not same-day patterns
No payment method → Cannot distinguish cash from electronic (affects structuring detection)

ACTION REQUIRED: Run this audit first, then update this document with confirmed available fields.

UK HMRC & MLR 2017 Compliance Requirements - Bank Transaction Data Only
SINGLE LAMBDA PASS PATTERNS (✅ Batch Processing Compatible)
These patterns can be detected by analyzing individual transactions within a 15-transaction batch:

1. Threshold-Based Reporting
Regulatory Requirement:

High-value dealers: Flag transactions ≥£10,000 (MLR 2017 Regulation 39)
General businesses: Flag transactions ≥£15,000 (MLR 2017 Regulation 33)
Triggers Enhanced Customer Due Diligence requirements

What to Detect:

Single transaction ≥£10,000
Single transaction ≥£15,000

Processing Architecture: ✅ SINGLE LAMBDA PASS

Each transaction evaluated independently
Flag raised immediately within batch
No cross-batch coordination needed

Current Status: ✅ Already implemented in your Claude prompt
Enhancement Suggestion:

Add business type context flag (if company is HVD, use £10k threshold, otherwise £15k)
Consider soft warnings at 80% of thresholds (£8k for HVD, £12k for general)


2. Geographic Risk - High-Risk Jurisdictions
Regulatory Requirement:

MLR 2017 Enhanced Due Diligence for high-risk third countries
FATF maintains list of high-risk jurisdictions requiring enhanced scrutiny

What to Detect:

Payments to FATF high-risk countries (Iran, North Korea, Myanmar, Syria)
Payments to non-cooperative tax jurisdictions
Payments to sanctioned countries (OFAC/HMT lists)

Processing Architecture: ✅ SINGLE LAMBDA PASS

Each transaction evaluated independently
Requires maintaining static reference lists (update quarterly)
Match counterparty country against lists

Data Dependency: ⚠️ Requires counterparty country in transaction data

If available in IBAN prefix → Easy detection
If available in SWIFT/BIC code → Easy detection
If only counterparty name → Fuzzy/unreliable (don't implement)

Implementation Suggestions:

Store FATF/sanctions lists in S3 as JSON, load into Lambda memory at cold start
Cache lists for 24 hours to reduce S3 reads
Separate "High Risk" (FATF) from "Tax Haven" (informational only) flags
Consider integration with existing sanctions checker Lambda


3. Cash Transaction Flags
Regulatory Requirement:

Large cash deposits (>£5,000) trigger source of funds verification under UK AML procedures
Frequent cash transactions inconsistent with business type may indicate structuring

What to Detect:

Single cash deposit ≥£5,000
Single ATM withdrawal ≥£5,000 (unusual for business)
Cash transaction with vague description

Processing Architecture: ✅ SINGLE LAMBDA PASS

Identify transaction type (CASH, ATM, CASH_DEPOSIT)
Flag if amount exceeds threshold
Current prompt already notes "ATM round numbers are normal" (good!)

Enhancement Suggestions:

Flag cash deposits >£5k as "SOURCE_VERIFICATION_REQUIRED"
Don't over-flag legitimate cash businesses (retail, hospitality)
Context matters: £8k cash for "Restaurant Ltd" might be normal, £8k cash for "IT Consultancy Ltd" suspicious


4. Vague Description Analysis
Regulatory Requirement:

HMRC guidance requires businesses to scrutinize transactions that "don't make commercial sense"
Vague descriptions may hide true transaction purpose

What to Detect:

Generic descriptions: "Services", "Consultancy", "Miscellaneous", "Payment", "Transfer"
High-value transactions (>£1,000) with no meaningful description
Descriptions inconsistent with counterparty business type

Processing Architecture: ✅ SINGLE LAMBDA PASS

Text analysis of transaction description field
Current Claude prompt already handles this well

Current Status: ✅ Already implemented and working
Enhancement Suggestions:

Maintain list of "red flag words" that trigger scrutiny: "Consultancy", "Services", "Misc", "Various"
Weight by amount: £50 "miscellaneous" = low priority, £5,000 "miscellaneous" = high priority
Consider counterparty analysis: payments to individuals (not companies) with vague descriptions


5. Round Number Detection (Within Batch)
Regulatory Requirement:

Structuring indicator: transactions deliberately set at round numbers just below thresholds
Example: £9,999, £9,900, £4,999 to avoid £10k or £5k reporting

What to Detect (Single Transaction):

Round amounts just below thresholds: £9,999, £9,900, £9,500, £4,999
Multiple round-number transactions within same batch to same recipient

Processing Architecture: ✅ SINGLE LAMBDA PASS (LIMITED)

Can detect suspicious round numbers in individual transactions
Can flag if 2-3 instances appear in same 15-transaction batch
LIMITATION: Cannot detect pattern if spread across batches (see Section 6)

Current Status: ✅ Partially implemented in Claude prompt
Enhancement Suggestions:

Don't over-flag: £1,000, £5,000, £10,000 are common legitimate business amounts
Focus on "deliberately under" patterns: £9,999, £14,999, £24,999
Consider context: salary payments often round (normal), ad-hoc payments rarely round (suspicious if under threshold)


6. Individual PEP/Sanctions Screening
Regulatory Requirement:

MLR 2017 requires Enhanced Due Diligence for Politically Exposed Persons
Sanctions lists must be checked for all payments

What to Detect:

Transaction counterparty matches PEP database
Transaction counterparty on sanctions list (OFAC, HMT, EU)

Processing Architecture: ✅ SINGLE LAMBDA PASS (IF INTEGRATED)

Each transaction's counterparty checked independently
Requires API call to PEP/sanctions database per unique counterparty

Current Status: ⚠️ System has separate sanctions checker Lambda - not integrated into transaction analysis
Architectural Options:
Option A: Real-time API calls in categorization Lambda

Pro: Immediate flagging
Con: Adds latency (200ms+ per API call)
Con: API costs per transaction
Best for: Small transaction volumes (<1000/month)

Option B: Pre-screen all counterparties before categorization

Separate Lambda scans all unique counterparties from uploaded statement
Stores results in DynamoDB (counterparty_name → PEP_status → true/false)
Categorization Lambda does DynamoDB lookup (fast, cheap)
Best for: Large transaction volumes

Option C: Post-categorization screening

Run after all transactions categorized
Generate "counterparty risk report" separately
Pro: Doesn't slow down categorization
Con: Not in initial analysis results

Recommendation: Option B for production (pre-screen), Option C for MVP (separate report)

FULL DATASET PATTERNS (❌ Require Post-Collection Analysis)
These patterns cannot be detected in 15-transaction batches and require viewing all transactions together:

7. Linked Transaction Detection ⚠️ LEGALLY REQUIRED BY MLR 2017
Regulatory Requirement:

MLR 2017 Regulation 27: "Several operations which appear to be linked"
HMRC guidance: "Multiple cash payments against a single invoice exceeding €10,000, for example, instalments in cash of £2,000 until goods have been paid in full"
This is not optional - it is a legal requirement

What to Detect:

Multiple payments to same recipient within time window (24-48 hours, or 30 days conservative)
Total aggregate exceeds £10,000 (HVD) or £15,000 (general)
Each individual payment below threshold

Why Batch Processing Fails:
Example:
- Batch 1 (transactions 1-15): Contains 2× £4,999 to "ABC Consulting"
- Batch 2 (transactions 16-30): Contains 1× £4,999 to "ABC Consulting"
- Result: Neither batch sees the pattern (3× £4,999 = £14,997 total)
Processing Architecture: ❌ REQUIRES FULL DATASET ANALYSIS
When to Run: After all transactions for period extracted and categorized
Architectural Solutions:
Solution A: Monthly Full-Dataset Lambda (Recommended)
Trigger: End of month or after final batch completes
Process: 
1. Query ALL transactions for client for period (DynamoDB query by client_id + date range)
2. Group by counterparty_name
3. For each counterparty, check for aggregation within time windows
4. Flag if total exceeds threshold

Challenges:
- Large datasets (5000+ transactions/month) may approach Lambda timeout (15 min max)
- Solution: Process in chunks of 1000 transactions, or use Step Functions for pagination

Trigger mechanism:
- Option 1: CloudWatch EventBridge scheduled rule (1st of month)
- Option 2: Final categorization batch sends "completion" event to EventBridge
- Option 3: Document status update (COMPLETED) triggers analysis Lambda
Solution B: Incremental Aggregation (More Complex)
Maintain running totals in DynamoDB:
- Key: client_id#counterparty_name#date
- Value: cumulative_amount, transaction_count, transaction_ids[]

Each categorization Lambda:
1. Updates aggregation table for each counterparty
2. Checks if aggregate exceeds threshold
3. Flags if threshold breached

Challenges:
- Race conditions if parallel batches update same counterparty
- DynamoDB transaction costs
- More complex to implement
- Best suited for real-time detection (not your current architecture)
Solution C: Two-Pass with Aggregation Pre-Processing
Before categorization batches:
1. Scan all transactions, extract counterparty names
2. Pre-compute aggregates (counterparty → total amount in period)
3. Store in DynamoDB
4. Pass aggregation context into each categorization batch

Categorization Lambda receives:
- 15 transactions to analyze
- Context: "ABC Consulting has £25k total in 5 transactions this period"

Challenges:
- Requires modifying Step Functions workflow
- Pre-processing adds time before categorization starts
Recommendation: Solution A - Monthly Full-Dataset Lambda

Simplest to implement
Aligns with retrospective analysis approach
MLR 2017 doesn't require real-time detection, just detection
Run as separate compliance report after categorization complete


8. Structuring Pattern Detection (Cross-Batch)
Regulatory Requirement:

Linked to MLR 2017 linked transactions
Pattern: Series of transactions deliberately structured just below reporting thresholds

What to Detect:

Multiple transactions to different recipients, all just below thresholds
Pattern of £9,999, £9,998, £9,997 (not just coincidental round numbers)
Frequency analysis: unusual clustering of near-threshold amounts

Why Batch Processing Fails:

Batch 1 might have 1× £9,999
Batch 2 might have 1× £9,998
Batch 3 might have 1× £9,997
Each batch sees one round number (could be coincidence)
All together: clear deliberate pattern

Processing Architecture: ❌ REQUIRES FULL DATASET ANALYSIS
When to Run: After all transactions categorized, in same Lambda as linked transaction detection
Detection Algorithm (conceptual):
1. Filter all transactions between £9,000-£9,999 or £14,000-£14,999
2. Count frequency within period
3. If >3 transactions in this range AND varied recipients → flag as structuring
4. Weight by precision: £9,999.00 more suspicious than £9,900
5. Check temporal clustering: all on same day = more suspicious
Architectural Suggestion:

Combine with linked transaction detection Lambda (Solution A above)
Run as second analysis step on full dataset
Share same data query (efficient)


9. Circular Transaction Detection
Regulatory Requirement:

HMRC guidance on "complex transactions" that don't make commercial sense
Round-tripping is classic money laundering technique

What to Detect:

Money leaves account and returns within short period
Direct: £10k to "ABC Ltd", £10k from "ABC Ltd" within 7 days
Indirect: £10k to "Company A", £10k from "Company B" (related entities)
Triangle: £10k to A, receive £10k from B, £10k to C, receive £10k from A

Data Dependency: ⚠️ REQUIRES INBOUND/OUTBOUND TRANSACTION FLAG

If not available in bank statement data, this pattern is undetectable
Alternative: Use amount sign (positive = inbound, negative = outbound)

Why Batch Processing Fails:

Outbound transaction might be in Batch 1
Inbound transaction might be in Batch 5
Cannot correlate without seeing both

Processing Architecture: ❌ REQUIRES FULL DATASET ANALYSIS
When to Run: After categorization complete, monthly analysis
Detection Algorithm (conceptual):
1. Separate transactions into OUTBOUND and INBOUND
2. For each OUTBOUND transaction:
   - Look for INBOUND transaction with:
     - Similar amount (±5%)
     - Within time window (7-90 days)
     - Related counterparty (exact match or fuzzy match)
3. Flag as circular if found

Complexity levels:
- Level 1: Exact counterparty match (easy)
- Level 2: Related parties (requires Companies House data)
- Level 3: Multi-hop (A→B→C→A) - very complex
Architectural Suggestion:

Implement Level 1 (exact match) first - catches most obvious cases
Level 2 requires Companies House integration (officer overlap detection)
Level 3 requires graph analysis - use dedicated graph database or defer to manual review

Critical Data Check: Verify you have inbound/outbound flag before attempting this pattern

10. Velocity & Volume Anomaly Detection
Regulatory Requirement:

HMRC guidance: Businesses should monitor "increases above 20% in total monthly spending"
Sudden changes in transaction patterns may indicate fraud or money laundering

What to Detect:

Transaction volume spike: >200% increase month-over-month
Dormant account activation: No transactions for 3+ months, then sudden activity
Amount anomalies: Sudden high-value transactions inconsistent with history
Frequency changes: Daily transactions when normally monthly

Data Dependency: ⚠️ REQUIRES HISTORICAL BASELINE

Need previous months' transaction data for comparison
Cannot detect without knowing "normal" for this client

Why Batch Processing Fails:

Cannot compare current month to previous months
No context on what's "normal" vs "anomalous"

Processing Architecture: ❌ REQUIRES FULL DATASET + HISTORICAL CONTEXT
Architectural Solutions:
Solution A: Monthly Baseline Storage
After each month's analysis:
1. Compute aggregates:
   - Total transaction count
   - Total transaction volume
   - Unique counterparty count
   - Average transaction amount
   - Transaction frequency (daily/weekly/monthly pattern)
2. Store in DynamoDB:
   Key: client_id#month (e.g., "CLIENT123#2025-10")
   Value: {count: 450, volume: 125000, unique_recipients: 87, avg: 278}

Next month's analysis:
1. Query previous 3 months' baselines
2. Compare current month to baseline
3. Flag if >200% increase in any metric
Solution B: Rolling Window in Transaction Table
Query last 90 days of transactions from DynamoDB
Compute on-the-fly baseline
Compare current month to previous 3 months

Challenge: More expensive (scan more data each time)
Benefit: No separate baseline table to maintain
Recommendation: Solution A (separate baseline table)

Cheaper at scale
Faster queries
Can pre-compute complex metrics
Easy to visualize trends over time

When to Run: As part of monthly full-dataset analysis Lambda
Enhancement Suggestion:

Start simple: just flag volume/count increases >200%
Later: Add ML anomaly detection (AWS services like SageMaker, or simpler z-score analysis)
Consider business growth context: new clients expected to grow, mature clients stable


PATTERNS NOT DETECTABLE FROM BANK DATA ALONE (❌ Removed)
These patterns require external data sources not present in bank transaction statements:
Trade-Based Money Laundering - REMOVED
Why: Requires invoice details (what goods/services, market prices, quantities) - not in bank data
What bank data shows: "Payment to ABC Ltd - £50,000 - Invoice 123"
What we can't know: Was £50k reasonable for the goods/services?
Possible partial detection: Flag round high-value amounts to companies with "consultancy" or "services" descriptions for manual review
CIS Compliance - REMOVED
Why: Requires CIS registration database, tax deduction amounts, subcontractor status - not in bank data
Note: Only relevant for construction industry clients
Recommendation: Flag as low priority, address only if serving construction sector clients
VAT Fraud - REMOVED
Why: Requires VAT return data, supplier VAT registration status, carousel timing - not in bank data
Recommendation: Defer to HMRC VAT compliance tools, outside scope of bank transaction analysis
Payroll Fraud (Full Detection) - REMOVED
Why: Requires employee list, payroll records, salary amounts - not in bank data
Partial detection: Can flag round-number "bonus" payments to directors, payments to individuals with "consultancy" descriptions
Recommendation: Flag suspicious payroll-like patterns for manual review, but cannot fully validate

Revised Architectural Recommendation
Two-Pass Architecture (Recommended Solution)
┌─────────────────────────────────────────────────────────────┐
│ PASS 1: BATCH CATEGORIZATION (Current - Keep as-is)        │
│ Trigger: After bank statement extraction                    │
│                                                              │
│ Step Functions Map State:                                   │
│   → Split transactions into batches of 15                   │
│   → Each batch → Categorization Lambda                      │
│                                                              │
│ Categorization Lambda (per batch):                          │
│   ✅ Transaction-level analysis via Claude                  │
│   ✅ Category assignment                                    │
│   ✅ Single transaction thresholds (£10k/£15k)             │
│   ✅ Geographic risk (if country data available)            │
│   ✅ Cash deposit flags                                     │
│   ✅ Vague description detection                            │
│   ✅ Round number flagging (within batch)                   │
│   ✅ Individual PEP screening (if integrated)               │
│                                                              │
│ Output: Categorized transactions in DynamoDB                │
└─────────────────────────────────────────────────────────────┘
                            ↓
                  All batches complete?
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ PASS 2: FULL-DATASET COMPLIANCE ANALYSIS (New)             │
│ Trigger: After final categorization batch completes         │
│         OR monthly scheduled (EventBridge)                   │
│                                                              │
│ Compliance Analysis Lambda:                                 │
│   1. Query ALL transactions for client for period           │
│   2. Run pattern detection algorithms:                      │
│      ✅ Linked transactions (MLR 2017 required)            │
│      ✅ Structuring patterns (cross-batch)                  │
│      ✅ Circular transactions (if inbound/outbound data)    │
│      ✅ Velocity anomalies (vs historical baseline)         │
│   3. Generate compliance alerts                             │
│   4. Store in separate alerts table                         │
│                                                              │
│ Output: Compliance report with high-risk pattern alerts     │
└─────────────────────────────────────────────────────────────┘
Why This Architecture Works:

Preserves Current Investment: Keep working batch categorization system
Meets MLR 2017 Requirements: Enables legally-required linked transaction detection
Cost-Effective: Batch processing cheap for high volume, full analysis runs less frequently
Scalable: Can handle large datasets without Lambda timeout issues (use Step Functions for very large datasets)
Testable: Each pass validates independently
Phased Implementation: Can deploy Pass 1 enhancements while building Pass 2


Implementation Priority Matrix
TIER 1: Legal Requirements - Implement Immediately
PatternSingle LambdaFull DatasetData RequiredEffortThreshold reporting (£10k/£15k)✅Amount✅ LowLinked transactions✅Counterparty, date, amount🟡 MediumGeographic risk✅Counterparty country🟡 Medium
Rationale: These are explicitly required by MLR 2017. Linked transaction detection is non-negotiable.

TIER 2: High Compliance Value - Implement Soon
PatternSingle LambdaFull DatasetData RequiredEffortStructuring patterns✅ (partial)✅ (full)Amount, date✅ LowCircular transactions✅Inbound/outbound flag🔴 HighVelocity anomalies✅Historical baseline🟡 MediumCash deposit flags✅Payment method, amount✅ Low
Rationale: Common money laundering techniques, high regulatory risk if missed.

TIER 3: Nice to Have - Future Enhancement
PatternSingle LambdaFull DatasetData RequiredEffortPEP screening✅PEP database API🟡 MediumEnhanced description analysis✅Better NLP🟡 MediumMulti-company patterns✅Cross-client data🔴 High
Rationale: Valuable but not legally mandated. Can be added incrementally.

Trigger Mechanism Options for Pass 2 Analysis
Option A: Event-Driven (Recommended for Real-Time Systems)
Mechanism:
- Last categorization batch completes
- Sends SNS notification or EventBridge event
- Triggers Pass 2 Lambda

Pros:
- Immediate analysis after upload complete
- Users see compliance report quickly
- Best for real-time requirements

Cons:
- Must track "last batch" completion
- More complex orchestration

Implementation:
- Document status update (COMPLETED) → EventBridge rule → Pass 2 Lambda
- OR: Step Functions state machine tracks batch count, triggers when count == total
Option B: Scheduled Monthly (Recommended for Batch Systems)
Mechanism:
- CloudWatch EventBridge scheduled rule
- Runs 1st of each month (or end of month)
- Analyzes all transactions from previous month

Pros:
- Simple implementation
- Consistent timing
- Suitable for retrospective compliance analysis

Cons:
- Delay between upload and analysis
- Month-boundary edge cases

Implementation:
- EventBridge rule: cron(0 2 1 * ? *) # 2am on 1st of month
- Lambda queries: WHERE transaction_date BETWEEN last_month_start AND last_month_end
Option C: Hybrid - Immediate + Monthly
Mechanism:
- Run basic checks immediately after upload (linked transactions only)
- Run comprehensive analysis monthly (all patterns + historical comparison)

Pros:
- Catches critical patterns quickly
- Deep analysis when full context available
- Best of both worlds

Cons:
- More complex
- Potential duplicate alerts

Recommendation: Start with Option B (simplest), migrate to Option C if real-time requirements emerge

Data Storage Architecture Suggestions
Current: Transactions in tag-financial-data-{env}-{region}

Keep as-is for categorized transaction storage

New: Compliance Alerts Table
Table: tag-compliance-alerts-{env}-{region}

Schema:
PK: client_id#alert_date (e.g., "CLIENT123#2025-11-01")
SK: alert_type#alert_id (e.g., "LINKED_TRANSACTIONS#uuid")

Attributes:
- alert_type: "LINKED_TRANSACTIONS" | "STRUCTURING" | "CIRCULAR" | "VELOCITY_ANOMALY"
- severity: "HIGH" | "MEDIUM" | "LOW"
- transaction_ids: [array of related transaction IDs]
- details: {
    counterparty: "ABC Consulting",
    total_amount: 14997,
    transaction_count: 3,
    time_span_days: 2
  }
- status: "NEW" | "REVIEWING" | "RESOLVED" | "FALSE_POSITIVE"
- created_at: timestamp
- reviewed_by: username (if reviewed)
- reviewer_notes: text

GSI-1: alert_type + status (for querying all open "LINKED_TRANSACTIONS" alerts)
GSI-2: severity + created_at (for dashboard of high-severity recent alerts)
New: Monthly Baseline Table (for velocity detection)
Table: tag-client-baselines-{env}-{region}

Schema:
PK: client_id
SK: month (e.g., "2025-10")

Attributes:
- transaction_count: 450
- transaction_volume: 125000.50
- unique_counterparties: 87
- avg_transaction_amount: 277.78
- payment_method_distribution: {BACS: 300, CARD: 100, CASH: 50}
- top_counterparties: [list of top 10 by volume]
- calculated_at: timestamp

Testing Strategy Suggestions
Unit Test Data Sets (Create These)
Test Set 1: Linked Transactions
Client: TEST_CLIENT_001
Transactions:
- 2025-11-01, ABC Consulting, £4,999, "Services"
- 2025-11-01, ABC Consulting, £4,999, "Consultancy"
- 2025-11-02, ABC Consulting, £4,999, "Advisory"
Total: £14,997 in 2 days

Expected: Alert triggered (LINKED_TRANSACTIONS, HIGH severity)
Test Set 2: Structuring Pattern
Client: TEST_CLIENT_002
Transactions:
- 2025-11-05, Company A, £9,999, "Payment"
- 2025-11-06, Company B, £9,998, "Invoice"
- 2025-11-07, Company C, £9,997, "Services"

Expected: Alert triggered (STRUCTURING, MEDIUM severity)
Test Set 3: Circular Transaction
Client: TEST_CLIENT_003
Transactions:
- 2025-11-10, OUTBOUND, XYZ Ltd, £25,000, "Loan"
- 2025-11-15, INBOUND, XYZ Ltd, £25,000, "Repayment"

Expected: Alert triggered (CIRCULAR, HIGH severity)
Test Set 4: Velocity Anomaly
Client: TEST_CLIENT_004
Baseline (Oct 2025): 50 transactions, £10,000 volume
Current (Nov 2025): 180 transactions, £45,000 volume
Increase: 260% transactions, 350% volume

Expected: Alert triggered (VELOCITY_ANOMALY, MEDIUM severity)
Test Set 5: False Positive - Legitimate Business
Client: TEST_CLIENT_005 (Restaurant)
Transactions:
- Multiple £5k-8k cash deposits (daily takings)
- Weekend transactions (Saturday/Sunday business hours)
- Round amounts (£1,000, £2,000 - till floats)

Expected: NO alerts (context: legitimate cash business)
Validation Criteria
For each pattern, define:

Precision: Of flagged alerts, what % are true positives?
Recall: Of actual violations in test set, what % did we catch?
Target: 80%+ precision (minimize false positives), 95%+ recall (don't miss real violations)


Open Questions - ANSWERS REQUIRED
Q1: Data Availability ⚠️ CRITICAL
Run this audit immediately:
SELECT 
  COUNT(*) as total_transactions,
  COUNT(DISTINCT counterparty_name) as unique_counterparties,
  COUNT(CASE WHEN inbound_outbound_flag IS NOT NULL THEN 1 END) as has_direction_flag,
  COUNT(CASE WHEN counterparty_country IS NOT NULL THEN 1 END) as has_country,
  COUNT(CASE WHEN transaction_timestamp IS NOT NULL THEN 1 END) as has_timestamp,
  COUNT(CASE WHEN payment_method IS NOT NULL THEN 1 END) as has_payment_method
FROM tag-financial-data-{env}
WHERE client_id = 'TEST_CLIENT'
LIMIT 100;
Then update this document with confirmed available fields.
Q2: Business Type Context
Does your system know if a client is:

High Value Dealer (£10k threshold)
General business (£15k threshold)
Cash-intensive business (retail, hospitality) - affects cash deposit flagging

Impact: Determines which thresholds to apply
Q3: False Positive Tolerance
What's acceptable false positive rate?

Conservative (80% precision): Flag more, review manually
Balanced (90% precision): Flag only high-confidence
Aggressive (95% precision): Flag only very high confidence, risk missing some violations

Recommendation: Start conservative (better to over-flag for compliance), tune based on manual review feedback
Q4: Historical Data Retention
How far back do you store transactions?

3 months? (Minimum for velocity detection)
6 months? (Better baseline)
12 months? (Ideal for trend analysis)

Impact: Determines velocity anomaly detection accuracy
Q5: Real-Time Requirements
When must compliance analysis complete?

Immediate (<1 hour after upload): Event-driven Pass 2
End of day (overnight acceptable): Scheduled Pass 2
Monthly (retrospective only): Scheduled monthly Pass 2

Current architecture suggests: Batch/retrospective (monthly) is acceptable

Phased Implementation Roadmap
Phase 1: Single Lambda Enhancements (2-3 weeks)
Goal: Improve current batch categorization without architecture changes

✅ Add threshold flagging (£10k/£15k) to Claude prompt
✅ Enhance cash deposit detection
✅ Improve vague description analysis
🟡 Add geographic risk lists (FATF countries) - if country data available
🟡 Integrate PEP screening - if budget approved

Deliverable: Enhanced categorization with better single-transaction compliance flags

Phase 2: Full Dataset Analysis (4-6 weeks)
Goal: Implement legally-required linked transaction detection

🔴 Design compliance alerts table schema
🔴 Build Pass 2 Lambda:

Linked transaction detection (MLR 2017 requirement)
Structuring pattern detection (cross-batch)


🔴 Implement trigger mechanism (EventBridge scheduled or event-driven)
🔴 Create compliance dashboard/report format
🔴 Testing with known violation patterns

Deliverable: MLR 2017 compliant system with linked transaction detection

Phase 3: Advanced Patterns (6-8 weeks)
Goal: Add high-value compliance patterns

🟡 Circular transaction detection (if inbound/outbound data available)
🟡 Velocity anomaly detection:

Create baseline table
Implement baseline calculation
Implement anomaly detection


🟡 Historical trend reporting
🟡 Alert review workflow (status updates, false positive marking)

Deliverable: Comprehensive compliance analysis with trend detection

Phase 4: Optimization & ML (Future)
Goal: Reduce false positives, improve accuracy

🔵 Collect false positive feedback
🔵 Tune detection thresholds based on real data
🔵 Consider ML models for anomaly detection (AWS SageMaker or simpler statistical models)
🔵 Automated risk scoring
🔵 Cross-client pattern detection (if privacy allows)

Deliverable: Mature, tuned system with low false positive rate

Summary & Critical Path Forward
Key Insights:

MLR 2017 explicitly requires linked transaction detection - this is not optional
Current batch architecture cannot detect linked transactions - requires full dataset
Two-pass architecture is the optimal solution - preserves current system, adds compliance layer
Most patterns are detectable from bank transaction data alone - don't need invoices, VAT returns, payroll

Critical Path:

IMMEDIATE: Run data availability audit - confirms what fields are actually in bank statements
WEEK 1-2: Enhance current batch categorization with easy wins (thresholds, cash flags)
WEEK 3-6: Build Pass 2 Lambda for linked transaction detection (legal requirement)
MONTH 2+: Add velocity, circular, and advanced patterns

Success Criteria:

✅ Detect 95%+ of linked transactions (MLR 2017 compliance)
✅ Threshold violations flagged 100% (simple rule-based)
✅ False positive rate <20% (acceptable manual review burden)
✅ Processing completes within acceptable timeframe (overnight for monthly is fine)

Next Action:
Schedule 30-minute data audit session - run queries against actual bank statement extraction output to confirm available fields. Update this document with results before proceeding to implementation.

Document Status: ✅ Analysis Complete - Ready for Data Audit & Implementation Planning