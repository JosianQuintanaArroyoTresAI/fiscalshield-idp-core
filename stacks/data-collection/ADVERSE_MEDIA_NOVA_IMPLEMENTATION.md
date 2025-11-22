# Adverse Media Screening with Nova Micro - Implementation Summary

**Date**: November 22, 2025  
**Version**: 2.0  
**Status**: ✅ Ready for Deployment

---

## 🎯 Overview

Enhanced adverse media screening with AWS Bedrock Nova Micro AI analysis and GDPR-compliant two-table architecture.

### Key Features

- ✅ **Nova Micro AI Analysis**: 1-5 risk scoring for each article
- ✅ **Two-Table Architecture**: Separate tables for scan summaries and individual articles
- ✅ **GDPR Compliant**: 7-year retention, audit trails, lawful basis tracking
- ✅ **S3 Compliance Archive**: Immutable storage of raw responses
- ✅ **NewsAPI Compatible**: Currently uses NewsAPI, designed for Brave migration

---

## 📊 Architecture

### Data Flow

```
1. POST /media/check
   ↓
2. MediaChecker Lambda
   ↓
3. NewsAPI/Brave Search (fetch articles)
   ↓
4. Nova Micro Analysis (parallel processing)
   ├─ Article 1 → {score: 2, level: "LOW"}
   ├─ Article 2 → {score: 4, level: "HIGH"}
   └─ Article 3 → {score: 5, level: "CRITICAL"}
   ↓
5. Storage (Three-tier)
   ├─ S3: Raw + analyzed data (compliance)
   ├─ AdverseMediaArticlesTable: Individual articles
   └─ CompanyEventsTable: Scan summaries
```

### Tables

#### 1. **AdverseMediaArticlesTable** (New)
```
Primary Key:
  - company_number (HASH)
  - article_id (RANGE) = {url_hash}#{published_date}

GSI 1: scan-date-index
  - company_number + scan_date

GSI 2: risk-score-index
  - company_number + risk_score

Fields:
  - Article: title, url, source, author, published_at, description, content
  - Analysis: risk_score (1-5), risk_level, nova_summary, nova_reasoning, key_topics
  - Metadata: scan_id, scan_date, data_source, s3_location
  - Compliance: collected_at, processed_at, gdpr_purpose, retention_until
  - No TTL (7-year retention)
```

#### 2. **CompanyEventsTable** (Enhanced)
```
New Item Type: MEDIA_SCAN#{timestamp}

Fields:
  - scan_id, scan_date, company_name
  - Statistics: total_articles, high/medium/low_risk_counts
  - Risk: overall_risk_score, weighted_risk_score, risk_level
  - top_risk_articles (top 10 for quick access)
  - s3_archive references
  - TTL: 7 days (cache), retention_until: 7 years (compliance)
```

### S3 Structure

```
s3://fiscalshield-dc-dev-data-archive-{account}/
└── adverse-media/
    └── {company_number}/
        └── scans/
            └── {scan_id}/
                ├── raw-response.json         # Immutable NewsAPI response
                ├── analyzed-articles.json    # With Nova scores
                └── scan-metadata.json        # Compliance metadata
```

---

## 🔧 Implementation Details

### Files Modified

1. **stacks/data-collection/template.yaml**
   - Added `AdverseMediaArticlesTable`
   - Added Bedrock permissions (Nova Micro + Nova Lite)
   - Added environment variables to MediaChecker

2. **src/data_collection/aml/media_checker/handler.py**
   - Complete rewrite with Nova Micro integration
   - Two-table storage logic
   - GDPR compliance metadata
   - Backup saved as `handler_v1_backup.py`

### Environment Variables

```yaml
CACHE_TABLE_NAME: CompanyEventsTable
ARTICLES_TABLE_NAME: AdverseMediaArticlesTable  # NEW
SECRET_NAME: NewsAPI
DATA_ARCHIVE_BUCKET: fiscalshield-dc-dev-data-archive-{account}
BEDROCK_MODEL_ID: amazon.nova-micro-v1:0  # NEW
RISK_SCORE_SCALE: 5  # NEW (1-5 scale)
RETENTION_YEARS: 7  # NEW (compliance)
```

### Nova Micro Configuration

**Risk Scoring Scale**: 1-5
- **1**: Positive/neutral news
- **2**: Slightly negative
- **3**: Moderately negative
- **4**: Significantly negative (regulatory issues, investigations)
- **5**: Critically negative (fraud, major scandals, legal action)

**Risk Levels**:
- Score 5 → CRITICAL
- Score 4 → HIGH
- Score 3 → MEDIUM
- Score 1-2 → LOW

**Model Settings**:
- Temperature: 0.1 (for consistency)
- Max tokens: 300
- Output format: Strict JSON

---

## 📋 Deployment Steps

### 1. Deploy Infrastructure

```bash
cd /home/josian/git/fiscalshield-idp-core/stacks/data-collection

# Validate template
sam validate

# Deploy
sam build
sam deploy --config-env dev
```

### 2. Verify Resources

```bash
# Check new table exists
aws dynamodb describe-table \
  --table-name fiscalshield-dc-dev-AdverseMediaArticles \
  --region eu-central-1

# Verify Bedrock permissions
aws iam get-role-policy \
  --role-name fiscalshield-dc-dev-LambdaExecutionRole \
  --policy-name BedrockAccess \
  --region eu-central-1
```

### 3. Test MediaChecker

```bash
# Test endpoint
aws lambda invoke \
  --function-name fiscalshield-dc-dev-MediaChecker \
  --payload '{
    "company_name": "Tesco PLC",
    "company_number": "00445790",
    "days_back": 30
  }' \
  --region eu-central-1 \
  response.json

cat response.json | jq
```

---

## 🔄 Migration to Brave Search API

When you get Brave API key with storage rights:

### Step 1: Update Secret

```bash
# Update NewsAPI secret with Brave credentials
aws secretsmanager update-secret \
  --secret-id fiscalshield-dc-dev-NewsAPI \
  --secret-string '{
    "api_key": "YOUR_BRAVE_API_KEY",
    "base_url": "https://api.search.brave.com/res/v1"
  }' \
  --region eu-central-1
```

### Step 2: Update Handler (Only 1 Function)

In `handler.py`, modify `search_news()`:

```python
def search_news(company_name: str, credentials: Dict, days_back: int = 30) -> Dict:
    """Search Brave News API for company articles."""
    base_url = credentials['base_url']
    api_key = credentials['api_key']
    
    # Brave News Search endpoint
    search_url = f"{base_url}/news/search"
    
    params = {
        'q': company_name,
        'count': 100,  # Results per page
        'search_lang': 'en'
    }
    
    headers = {
        'Accept': 'application/json',
        'Accept-Encoding': 'gzip',
        'X-Subscription-Token': api_key
    }
    
    response = requests.get(search_url, params=params, headers=headers, timeout=30)
    response.raise_for_status()
    
    brave_data = response.json()
    
    # Transform Brave response to match NewsAPI structure
    articles = []
    for result in brave_data.get('results', []):
        articles.append({
            'title': result.get('title'),
            'url': result.get('url'),
            'description': result.get('description'),
            'publishedAt': result.get('page_fetched'),
            'source': {'name': result.get('meta_url', {}).get('hostname')},
            'author': None,
            'content': result.get('description')
        })
    
    return {
        'status': 'ok',
        'totalResults': len(articles),
        'articles': articles
    }
```

**That's it!** Everything else stays the same.

---

## 📊 Response Format

### Success Response

```json
{
  "success": true,
  "scan_id": "a7f3b2c9-1234-5678-90ab-cdef12345678",
  "company_number": "00445790",
  "company_name": "Tesco PLC",
  "scan_date": "2025-11-22T10:30:00Z",
  "total_articles": 15,
  "high_risk_count": 2,
  "medium_risk_count": 5,
  "low_risk_count": 8,
  "overall_risk_score": 4,
  "risk_level": "HIGH",
  "top_risk_articles": [
    {
      "title": "Tesco faces investigation over...",
      "url": "https://...",
      "source": "Financial Times",
      "published_at": "2025-11-20T14:30:00Z",
      "risk_score": 4,
      "risk_level": "HIGH",
      "summary": "Regulatory investigation mentioned"
    }
  ],
  "s3_archive": {
    "bucket": "fiscalshield-dc-dev-data-archive-xxx",
    "scan_folder": "adverse-media/00445790/scans/{scan_id}/"
  }
}
```

---

## 🛡️ GDPR Compliance

### Data Retained

1. **S3 Archives**: 7 years (regulatory requirement)
2. **AdverseMediaArticlesTable**: 7 years (no TTL)
3. **CompanyEventsTable**: Summaries cached 7 days, retained 7 years

### Metadata Tracked

- `gdpr_purpose`: "aml_adverse_media_screening"
- `gdpr_lawful_basis`: "legitimate_interest"
- `retention_until`: 7 years from collection
- `collected_at`, `processed_at`: Audit trail
- `processing_version`: Code version tracking
- `nova_model`: AI model used

### Rights Supported

- **Right to Access**: Query AdverseMediaArticlesTable by company_number
- **Right to Erasure**: Delete items (after retention period)
- **Right to Data Portability**: Export from DynamoDB + S3
- **Right to Object**: TTL allows automatic deletion after cache period

---

## 💰 Cost Estimate

### Nova Micro

- Input: $0.035 per 1M tokens (~$0.04 per 1,000 articles)
- Output: $0.14 per 1M tokens

**Example**: 500 companies/month, 20 articles each = 10,000 articles
- Cost: ~$0.40/month for AI analysis

### DynamoDB

- AdverseMediaArticlesTable: Pay-per-request
- Estimated: <$5/month for 500 companies

### S3

- Storage: $0.023/GB/month
- Estimated: <$2/month for compliance archives

**Total**: ~$7-10/month for 500 companies

---

## 🧪 Testing

### Manual Test

```bash
curl -X POST https://{api-gateway-url}/media/check \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Tesco PLC",
    "company_number": "00445790",
    "days_back": 30
  }'
```

### Check DynamoDB

```bash
# Check articles table
aws dynamodb query \
  --table-name fiscalshield-dc-dev-AdverseMediaArticles \
  --key-condition-expression "company_number = :cn" \
  --expression-attribute-values '{":cn":{"S":"00445790"}}' \
  --region eu-central-1

# Check scan summaries
aws dynamodb query \
  --table-name fiscalshield-dc-dev-CompanyEvents \
  --key-condition-expression "company_number = :cn AND begins_with(event_type_timestamp, :et)" \
  --expression-attribute-values '{":cn":{"S":"00445790"},":et":{"S":"MEDIA_SCAN"}}' \
  --region eu-central-1
```

### Check S3

```bash
aws s3 ls s3://fiscalshield-dc-dev-data-archive-{account}/adverse-media/00445790/scans/ --recursive
```

---

## 📚 References

- **Nova Micro Docs**: AWS Bedrock Nova family
- **GDPR Compliance**: 7-year AML retention requirement
- **NewsAPI**: https://newsapi.org/docs
- **Brave Search API**: https://brave.com/search/api/

---

## ✅ Checklist

- [x] AdverseMediaArticlesTable created
- [x] Bedrock permissions added
- [x] MediaChecker Lambda updated
- [x] GDPR metadata implemented
- [x] S3 archive structure defined
- [x] Brave migration path documented
- [ ] Deploy to dev environment
- [ ] Test with real company
- [ ] Verify S3 archival
- [ ] Verify DynamoDB storage
- [ ] Test Nova Micro analysis
- [ ] Update Brave API when available

---

**Implementation Complete!** Ready for deployment and testing.
