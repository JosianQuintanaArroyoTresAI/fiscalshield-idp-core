# AML Report Caching Implementation Plan

## Overview

Since AML reports are generated from company intelligence data that is cached for 24 hours, and the reports are expensive to generate (Claude API costs + processing time), we should cache generated reports to:

1. **Save money** - Avoid regenerating identical reports (Claude API ~$0.04-0.06 per report)
2. **Improve performance** - Serve cached reports instantly instead of 30-40 seconds
3. **Reduce API usage** - Minimize Bedrock API calls
4. **Maintain consistency** - Same intelligence data = same report

## Current Flow (No Caching)

```
User clicks "Generate Report"
    ↓
Lambda retrieves intelligence data (from cache or fresh)
    ↓
Lambda calls Claude via Bedrock (~30-40 seconds, ~$0.05)
    ↓
Report stored in S3
    ↓
User downloads report
```

**Problem**: If User B requests a report for the same company that User A just generated, we waste money and time regenerating the identical report.

## Proposed Flow (With Caching)

```
User clicks "Generate Report"
    ↓
Lambda checks CompanyIntelligenceTable for cached report metadata
    ↓
Is there a recent report? (intelligence_type = 'AML_REPORT' + timestamp check)
    ├─ YES (cache hit, age < 24h) → Return existing S3 URL (instant, free)
    └─ NO (cache miss) → Generate new report with Claude
           ↓
           Store report in S3
           ↓
           Store metadata in CompanyIntelligenceTable
           ↓
           Return new S3 URL
```

## Implementation Details

### 1. DynamoDB Schema Enhancement

The `CompanyIntelligenceTable` already has the perfect structure:

```yaml
KeySchema:
  - company_number (HASH)
  - intelligence_type_timestamp (RANGE)  # e.g., "AML_REPORT#2025-11-09T18:30:00"
  
Attributes:
  - ttl: Unix timestamp for auto-deletion
  - data: Report metadata (report_id, s3_key, tokens_used, etc.)
  - analysis_timestamp: For sorting/querying
```

**New Record Type** (add to existing table):
```python
{
  "company_number": "00445790",
  "intelligence_type_timestamp": "AML_REPORT#2025-11-09T18:30:00",  # Sort key
  "ttl": 1731196800,  # 24 hours from generation
  "analysis_timestamp": 1731110400,
  "data": {
    "report_id": "report_20251109_183000",
    "s3_key": "aml-reports/00445790/report_20251109_183000.md",
    "company_name": "TESCO PLC",
    "risk_level": "LOW",
    "model_used": "anthropic.claude-3-7-sonnet-20250219-v1:0",
    "tokens_used": {
      "input": 2500,
      "output": 1800,
      "total": 4300
    },
    "generated_at": "2025-11-09T18:30:00",
    "intelligence_data_hash": "abc123...",  # Hash of input data (optional)
    "presigned_url_expiry": 1731715200  # When presigned URL expires
  },
  "last_updated": "2025-11-09T18:30:00"
}
```

### 2. Modified Lambda Handler

**File**: `src/analysis/company_intelligence/generate_report/handler.py`

**Changes**:

```python
def lambda_handler(event, context):
    """
    Main Lambda handler for AML Report Generation and Download
    
    New Flow:
    1. Check for cached report in CompanyIntelligenceTable
    2. If cached report exists and is fresh (< 24h), return it
    3. If no cache or expired, generate new report with Claude
    4. Store report metadata in DynamoDB for future cache hits
    """
    
    # ... existing OPTIONS/GET handling ...
    
    # Extract company number
    company_number = event.get('pathParameters', {}).get('company_number')
    
    if not company_number:
        return error_response(400, 'company_number is required')
    
    print(f"AML report requested for company {company_number}")
    
    generator = ReportGenerator()
    
    # STEP 1: Check for cached report
    cached_report = generator.get_cached_report(company_number)
    
    if cached_report:
        print(f"✅ Cache HIT - Returning cached report for {company_number}")
        print(f"   Report ID: {cached_report['report_id']}")
        print(f"   Age: {cached_report['age_hours']:.1f} hours")
        print(f"   Tokens saved: {cached_report.get('tokens_used', {}).get('total', 0)}")
        
        # Return cached report (instant response)
        return success_response(200, {
            'success': True,
            'cached': True,  # Important: indicates this is a cached response
            'cache_age_hours': cached_report['age_hours'],
            'company_number': company_number,
            'company_name': cached_report.get('company_name'),
            'risk_level': cached_report.get('risk_level'),
            'report_id': cached_report['report_id'],
            's3_key': cached_report['s3_key'],
            'download_url': reconstruct_download_url(event, company_number, cached_report['report_id']),
            'generated_at': cached_report['generated_at'],
            'tokens_used': cached_report.get('tokens_used', {}),
            'valid_until': cached_report.get('valid_until')
        })
    
    print(f"❌ Cache MISS - Generating new report for {company_number}")
    
    # STEP 2: Generate new report (existing code)
    data = generator.retrieve_intelligence_data(company_number)
    report_data = generator.generate_report_with_claude(data)
    storage_info = generator.store_report(company_number, report_data)
    
    # STEP 3: Cache the report metadata
    generator.cache_report_metadata(company_number, report_data, storage_info)
    
    # Return new report
    return success_response(200, {
        'success': True,
        'cached': False,
        'company_number': company_number,
        'company_name': report_data.get('company_name'),
        'risk_level': report_data.get('risk_level'),
        'report_id': storage_info['report_id'],
        's3_key': storage_info['s3_key'],
        'download_url': reconstruct_download_url(event, company_number, storage_info['report_id']),
        'model_used': report_data.get('model_id'),
        'tokens_used': {
            'input': report_data.get('input_tokens', 0),
            'output': report_data.get('output_tokens', 0),
            'total': report_data.get('input_tokens', 0) + report_data.get('output_tokens', 0)
        },
        'generated_at': datetime.now().isoformat()
    })
```

### 3. New ReportGenerator Methods

```python
class ReportGenerator:
    """Generates professional AML CDD reports using Claude via Amazon Bedrock"""
    
    def __init__(self):
        self.intelligence_table = dynamodb.Table(COMPANY_INTELLIGENCE_TABLE)
        self.company_events_table = dynamodb.Table(DC_COMPANY_EVENTS_TABLE)
        self.model_id = "eu.anthropic.claude-3-7-sonnet-20250219-v1:0"
        self.system_prompt = """..."""  # existing
        self.cache_ttl_seconds = 24 * 60 * 60  # 24 hours
    
    def get_cached_report(self, company_number: str) -> Optional[Dict]:
        """
        Check if a recent AML report exists in cache
        
        Returns:
            Dict with report metadata if found and fresh (< 24h)
            None if no cache or expired
        """
        try:
            # Query for most recent AML_REPORT entry
            response = self.intelligence_table.query(
                KeyConditionExpression="company_number = :num AND begins_with(intelligence_type_timestamp, :type)",
                ExpressionAttributeValues={
                    ":num": company_number,
                    ":type": "AML_REPORT"
                },
                ScanIndexForward=False,  # Most recent first
                Limit=1
            )
            
            if not response.get('Items'):
                print(f"No cached report found for {company_number}")
                return None
            
            item = response['Items'][0]
            
            # Check if cache is still fresh
            generated_at = datetime.fromisoformat(item.get('generated_at', '2000-01-01'))
            age_seconds = (datetime.utcnow() - generated_at).total_seconds()
            age_hours = age_seconds / 3600
            
            if age_seconds > self.cache_ttl_seconds:
                print(f"Cached report expired (age: {age_hours:.1f}h > 24h)")
                return None
            
            print(f"Found fresh cached report (age: {age_hours:.1f}h)")
            
            # Return cached report metadata
            data = item.get('data', {})
            return {
                'report_id': data.get('report_id'),
                's3_key': data.get('s3_key'),
                'company_name': data.get('company_name'),
                'risk_level': data.get('risk_level'),
                'generated_at': item.get('generated_at'),
                'tokens_used': data.get('tokens_used', {}),
                'valid_until': item.get('ttl'),
                'age_hours': age_hours
            }
            
        except Exception as e:
            print(f"Error checking report cache: {e}")
            return None
    
    def cache_report_metadata(self, company_number: str, report_data: Dict, storage_info: Dict):
        """
        Store report metadata in CompanyIntelligenceTable for caching
        
        This enables future requests to return the same report without regenerating
        """
        try:
            now = datetime.utcnow()
            ttl = int(now.timestamp()) + self.cache_ttl_seconds
            
            item = {
                'company_number': company_number,
                'intelligence_type_timestamp': f"AML_REPORT#{now.isoformat()}",
                'ttl': ttl,
                'analysis_timestamp': int(now.timestamp()),
                'generated_at': now.isoformat(),
                'last_updated': now.isoformat(),
                'data': {
                    'report_id': storage_info['report_id'],
                    's3_key': storage_info['s3_key'],
                    'company_name': report_data.get('company_name'),
                    'risk_level': report_data.get('risk_level'),
                    'model_used': report_data.get('model_id'),
                    'tokens_used': {
                        'input': report_data.get('input_tokens', 0),
                        'output': report_data.get('output_tokens', 0),
                        'total': report_data.get('input_tokens', 0) + report_data.get('output_tokens', 0)
                    }
                }
            }
            
            self.intelligence_table.put_item(Item=item)
            print(f"✅ Cached report metadata for {company_number} (TTL: 24h)")
            
        except Exception as e:
            print(f"⚠️  Failed to cache report metadata (non-blocking): {e}")
            # Don't fail the request if caching fails
```

### 4. Helper Functions

```python
def reconstruct_download_url(event: Dict, company_number: str, report_id: str) -> str:
    """
    Reconstruct API Gateway download URL from event context
    Avoids presigned URL signature issues
    """
    headers = event.get('headers', {})
    host = headers.get('Host') or headers.get('host', '')
    stage = event.get('requestContext', {}).get('stage', 'Prod')
    
    if host:
        return f"https://{host}/{stage}/company/{company_number}/report/{report_id}"
    else:
        # Fallback to S3 key
        return f"s3://reports-bucket/aml-reports/{company_number}/{report_id}.md"

def success_response(status_code: int, data: Dict) -> Dict:
    """Create successful API response with CORS"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
        },
        'body': json.dumps(data, default=decimal_to_float)
    }

def error_response(status_code: int, error_message: str) -> Dict:
    """Create error API response with CORS"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'success': False,
            'error': error_message
        })
    }

def decimal_to_float(obj):
    """JSON serializer for Decimal objects"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
```

## Cost Savings Analysis

### Current Scenario (No Caching)
- 100 users each generate 1 report per month for the same popular company
- **Cost**: 100 × $0.05 = **$5.00**
- **Time**: 100 × 35 seconds = **58 minutes of total generation time**

### With Caching (24h TTL)
- User 1 generates report (cache miss): $0.05, 35 seconds
- Users 2-100 get cached report (cache hits): $0.00, <1 second each
- **Cost**: 1 × $0.05 = **$0.05** 
- **Savings**: **99%** ($4.95 saved)
- **Time saved**: 57.5 minutes

### Real-World Impact
If 50 companies are analyzed by multiple users:
- **Without cache**: 50 companies × 10 users × $0.05 = **$25/month**
- **With cache**: 50 companies × 1 generation × $0.05 = **$2.50/month**
- **Monthly savings**: **$22.50** (90% reduction)

## Cache Invalidation Strategy

Reports are automatically invalidated when:

1. **TTL expires** (24 hours) - DynamoDB auto-deletes the cached metadata
2. **Intelligence data is refreshed** - User clicks "Refresh Intelligence" → invalidates report cache
3. **Manual force refresh** - Add optional `?force_refresh=true` parameter

### Force Refresh Implementation

```python
def lambda_handler(event, context):
    # Check for force refresh parameter
    query_params = event.get('queryStringParameters') or {}
    force_refresh = query_params.get('force_refresh', 'false').lower() == 'true'
    
    if force_refresh:
        print(f"Force refresh requested - bypassing cache")
        cached_report = None
    else:
        cached_report = generator.get_cached_report(company_number)
```

## Testing Plan

### Unit Tests

```python
# test_report_caching.py

def test_cache_miss_generates_new_report():
    """First request should generate new report"""
    response = invoke_lambda(company_number="00445790")
    assert response['cached'] == False
    assert 'report_id' in response

def test_cache_hit_returns_existing_report():
    """Second request within 24h should return cached report"""
    # First call
    response1 = invoke_lambda(company_number="00445790")
    report_id_1 = response1['report_id']
    
    # Second call (within 24h)
    response2 = invoke_lambda(company_number="00445790")
    
    assert response2['cached'] == True
    assert response2['report_id'] == report_id_1  # Same report
    assert response2['cache_age_hours'] < 24

def test_expired_cache_regenerates_report():
    """Request after 24h should generate new report"""
    # Mock TTL as expired
    # Assert new report generated

def test_force_refresh_bypasses_cache():
    """force_refresh=true should ignore cache"""
    response1 = invoke_lambda(company_number="00445790")
    response2 = invoke_lambda(company_number="00445790", force_refresh=True)
    
    assert response2['cached'] == False
    assert response2['report_id'] != response1['report_id']
```

### Integration Tests

```bash
# Test cache behavior end-to-end

# First call - cache miss
time curl -X POST "$API_URL/company/00445790/report"
# Expected: ~35 seconds, cached=false

# Second call - cache hit
time curl -X POST "$API_URL/company/00445790/report"
# Expected: <1 second, cached=true

# Force refresh
curl -X POST "$API_URL/company/00445790/report?force_refresh=true"
# Expected: ~35 seconds, cached=false, new report_id
```

## Frontend Changes

Update the UI to show cache status:

```javascript
// src/ui/src/services/analysisStack.js

export const generateAMLReport = async (companyNumber, forceRefresh = false) => {
  const url = `${apiUrl}/company/${companyNumber}/report${forceRefresh ? '?force_refresh=true' : ''}`;
  
  const data = await response.json();
  
  return {
    ...data,
    cacheStatus: data.cached ? `Cached (${data.cache_age_hours?.toFixed(1)}h old)` : 'Newly generated'
  };
};
```

```jsx
// Display cache status in UI
{reportData.cached && (
  <div className="cache-notice" style={{
    padding: '8px 12px',
    backgroundColor: '#e8f5e9',
    borderRadius: '4px',
    fontSize: '14px',
    color: '#2e7d32',
    marginBottom: '12px'
  }}>
    ⚡ This report was retrieved from cache ({reportData.cache_age_hours?.toFixed(1)}h old)
    <button onClick={() => generateReport(true)} style={{marginLeft: '12px'}}>
      Force Refresh
    </button>
  </div>
)}
```

## Monitoring & Metrics

### CloudWatch Custom Metrics

```python
import boto3

cloudwatch = boto3.client('cloudwatch')

def emit_cache_metric(cache_hit: bool, company_number: str):
    """Emit custom metric for cache performance tracking"""
    cloudwatch.put_metric_data(
        Namespace='FiscalShield/Analysis',
        MetricData=[
            {
                'MetricName': 'ReportCacheHit' if cache_hit else 'ReportCacheMiss',
                'Value': 1,
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'Environment', 'Value': ENVIRONMENT}
                ]
            }
        ]
    )
```

### Dashboard Queries

```bash
# Cache hit rate over last 24 hours
aws cloudwatch get-metric-statistics \
  --namespace FiscalShield/Analysis \
  --metric-name ReportCacheHit \
  --start-time $(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum \
  --region eu-central-1

# Cost savings estimate
# (Cache Hits × $0.05) = Money saved
```

## Deployment Steps

1. **Update Lambda code** with caching logic (no infrastructure changes needed!)
2. **Deploy updated Lambda**:
   ```bash
   cd stacks/analysis
   sam build
   sam deploy --config-env prod --region eu-central-1
   ```
3. **Test caching** with production company
4. **Monitor CloudWatch** for cache hit rates
5. **Update frontend** to show cache status (optional)

## Benefits Summary

✅ **Cost Reduction**: 90%+ savings on repeated reports  
✅ **Performance**: <1 second vs 35 seconds for cached reports  
✅ **API Efficiency**: Reduces Bedrock API usage  
✅ **User Experience**: Instant report delivery  
✅ **Data Consistency**: Same input data = same report  
✅ **No Infrastructure Changes**: Uses existing DynamoDB table  
✅ **Automatic Cleanup**: TTL handles cache expiration  

## Edge Cases & Considerations

### 1. Intelligence Data Changes
If intelligence data is refreshed between report generations, we might serve stale reports.

**Solution**: Delete cached report when intelligence is refreshed:

```python
# In assess_company/handler.py (intelligence refresh Lambda)
def invalidate_report_cache(company_number: str):
    """Delete cached reports when intelligence is refreshed"""
    table = dynamodb.Table(COMPANY_INTELLIGENCE_TABLE)
    
    # Query all AML_REPORT entries
    response = table.query(
        KeyConditionExpression="company_number = :num AND begins_with(intelligence_type_timestamp, :type)",
        ExpressionAttributeValues={
            ":num": company_number,
            ":type": "AML_REPORT"
        }
    )
    
    # Delete them
    for item in response.get('Items', []):
        table.delete_item(
            Key={
                'company_number': company_number,
                'intelligence_type_timestamp': item['intelligence_type_timestamp']
            }
        )
    
    print(f"Invalidated {len(response.get('Items', []))} cached reports for {company_number}")
```

### 2. Multiple Report Versions
What if we want to keep history of old reports?

**Current behavior**: S3 keeps reports for 90 days (lifecycle policy), but cache only references latest

**Enhancement**: Add version number to cache key:
```python
"intelligence_type_timestamp": f"AML_REPORT#v1#{now.isoformat()}"
```

### 3. Presigned URL Expiry
Presigned URLs expire after 7 days, but cached metadata might reference expired URL.

**Solution**: Already implemented - use API Gateway download endpoint instead of presigned URLs

## Conclusion

This caching strategy provides significant cost and performance benefits with minimal code changes. The existing `CompanyIntelligenceTable` structure is perfect for this use case, and DynamoDB's TTL feature handles automatic cleanup.

**Next Steps**:
1. Review and approve this implementation plan
2. Implement the code changes in `generate_report/handler.py`
3. Add unit tests for caching logic
4. Deploy to dev environment and test
5. Monitor cache hit rates
6. Deploy to production
