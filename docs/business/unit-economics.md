UNIT ECONOMICS - TAXRADAR IDP PLATFORM

═══════════════════════════════════════════════════════════════════════

COST PER DOCUMENT (Typical Invoice Processing)

AWS Service                         Usage                                   Cost per Document
─────────────────────────────────────────────────────────────────────────────────────────────
AWS Textract                        ~5 pages OCR @ $0.0015/page            $0.0075
Claude 3.5 Sonnet (Bedrock)         ~15k tokens (classification +          $0.06
                                    extraction)
Lambda Compute                      ~15 seconds total execution            $0.003
Step Functions                      1 workflow execution, ~8 transitions   $0.0002
DynamoDB                            ~10 read/write operations              $0.0001
S3 Storage & Transfer               Document storage + transfer            $0.0002
AppSync GraphQL                     API calls for status updates           $0.0001
─────────────────────────────────────────────────────────────────────────────────────────────
TOTAL INFRASTRUCTURE COST                                                  ~$0.08 per document


═══════════════════════════════════════════════════════════════════════

REVENUE MODEL & MARGINS

Pricing Tier        Target Customer                    Price per Document    Gross Margin
──────────────────────────────────────────────────────────────────────────────────────────
Pay-as-you-go       Small practices                    £0.50                84%
                    (<50 docs/month)

Standard            Mid-size firms                      £0.35                77%
                    (50-500 docs/month)

Enterprise          Large firms                         £0.25                68%
                    (500+ docs/month)


═══════════════════════════════════════════════════════════════════════

SCALE ECONOMICS

The serverless architecture delivers compound cost advantages as volume increases:

• Zero Idle Costs
  No servers to maintain during off-peak hours (60-70% of the day for most firms)

• Volume Efficiency
  AWS discounts (Bedrock commit, Textract volume pricing) kick in at 10,000+ docs/month,
  reducing per-document costs by 20-30%

• Optimization Gains
  Platform improvements (prompt caching, chunking optimizations) have already reduced
  costs by 79% from initial implementation ($0.39 → $0.08 per doc)

• Marginal Cost Scaling
  Each additional document costs £0.08 while revenue starts at £0.25, maintaining
  68%+ margins even at enterprise pricing


═══════════════════════════════════════════════════════════════════════

BREAK-EVEN ANALYSIS

• Development costs amortized across 1,000 documents = break-even
• Current pilot approaching break-even threshold
• Each subsequent document contributes 68-84% gross profit


═══════════════════════════════════════════════════════════════════════

VOLUME EXAMPLES

Processing 1,000 invoices per month:

Infrastructure Cost:     £80  (1,000 × £0.08)

Revenue by Tier:
  • Pay-as-you-go:      £500  →  Profit: £420  (84% margin)
  • Standard:           £350  →  Profit: £270  (77% margin)
  • Enterprise:         £250  →  Profit: £170  (68% margin)


Processing 10,000 invoices per month (with volume discounts):

Infrastructure Cost:     £640  (10,000 × £0.064 after 20% volume discount)

Revenue by Tier:
  • Pay-as-you-go:      £5,000  →  Profit: £4,360  (87% margin)
  • Standard:           £3,500  →  Profit: £2,860  (82% margin)
  • Enterprise:         £2,500  →  Profit: £1,860  (74% margin)


═══════════════════════════════════════════════════════════════════════

KEY TAKEAWAYS

✓ Infrastructure cost: ~£0.08 per document
✓ Gross margins: 68-84% depending on pricing tier
✓ Zero idle costs due to serverless architecture
✓ Costs decrease 20-30% with volume (AWS discounts)
✓ Already achieved 79% cost reduction through optimization
✓ Break-even at 1,000 documents processed
