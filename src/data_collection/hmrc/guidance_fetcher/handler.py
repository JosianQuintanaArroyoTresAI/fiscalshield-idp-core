"""
HMRC Guidance Fetcher Lambda Handler

Fetches HMRC BIM (Business Income Manual) compliance guidance from GOV.UK Content API.
- Public API (no authentication required)
- Rate limiting: 8.3 requests/second
- Stores in DynamoDB: fiscalshield-dc-{env}-HMRCGuidance
- Backs up to S3: fiscalshield-dc-{env}-data-archive/hmrc-guidance/

Triggered by:
- EventBridge Schedule (weekly - Monday 2 AM UTC)
- Manual invocation with {"force_refresh": true}
"""

import json
import os
import time
import boto3
import requests
from datetime import datetime
from typing import Dict, List, Optional
from botocore.exceptions import ClientError

# Environment variables
ENVIRONMENT = os.environ.get("ENVIRONMENT", "dev")
GUIDANCE_TABLE_NAME = os.environ.get("GUIDANCE_TABLE_NAME")
DATA_ARCHIVE_BUCKET = os.environ.get("DATA_ARCHIVE_BUCKET")
GOVUK_API_BASE_URL = os.environ.get("GOVUK_API_BASE_URL", "https://www.gov.uk/api/content")
RATE_LIMIT_PER_SEC = float(os.environ.get("RATE_LIMIT_PER_SEC", "8.3"))

# AWS clients
dynamodb = boto3.resource("dynamodb")
s3_client = boto3.client("s3")

# BIM Sections to fetch (15 priority sections)
BIM_SECTIONS = [
    "hmrc-internal-manuals/business-income-manual/bim37000",  # General principles
    "hmrc-internal-manuals/business-income-manual/bim37050",  # Expense basics
    "hmrc-internal-manuals/business-income-manual/bim37600",  # Travel expenses
    "hmrc-internal-manuals/business-income-manual/bim37650",  # Subsistence
    "hmrc-internal-manuals/business-income-manual/bim37700",  # Entertainment
    "hmrc-internal-manuals/business-income-manual/bim42000",  # Motor expenses introduction
    "hmrc-internal-manuals/business-income-manual/bim42050",  # Business vs private use
    "hmrc-internal-manuals/business-income-manual/bim45000",  # Accommodation
    "hmrc-internal-manuals/business-income-manual/bim45005",  # Rent and rates
    "hmrc-internal-manuals/business-income-manual/bim35000",  # Professional fees
    "hmrc-internal-manuals/business-income-manual/bim35010",  # Legal fees
    "hmrc-internal-manuals/business-income-manual/bim46800",  # Equipment and tools
    "hmrc-internal-manuals/business-income-manual/bim40450",  # Repairs vs improvements
    "hmrc-internal-manuals/business-income-manual/bim43200",  # Telephone and internet
    "hmrc-internal-manuals/business-income-manual/bim42400",  # Mileage allowance
]

# Category mapping
BIM_CATEGORIES = {
    "bim37000": "general",
    "bim37050": "general",
    "bim37600": "travel",
    "bim37650": "travel",
    "bim37700": "entertainment",
    "bim42000": "motor",
    "bim42050": "motor",
    "bim42400": "motor",
    "bim45000": "accommodation",
    "bim45005": "accommodation",
    "bim35000": "professional_fees",
    "bim35010": "professional_fees",
    "bim46800": "office",
    "bim40450": "general",
    "bim43200": "office",
}


def lambda_handler(event, context):
    """
    Main Lambda handler for HMRC guidance fetching
    
    Args:
        event: EventBridge schedule or manual invocation
               {"force_refresh": true} to re-fetch all sections
        context: Lambda context
    
    Returns:
        dict: Result summary with success/failure counts
    """
    print(f"[INFO] Starting HMRC Guidance Fetcher - Environment: {ENVIRONMENT}")
    print(f"[INFO] Event: {json.dumps(event)}")
    
    force_refresh = event.get("force_refresh", False)
    sections_to_fetch = event.get("sections", BIM_SECTIONS)
    
    results = {
        "total_sections": len(sections_to_fetch),
        "success_count": 0,
        "failure_count": 0,
        "sections_processed": [],
        "errors": []
    }
    
    # Validate environment
    if not GUIDANCE_TABLE_NAME:
        error_msg = "GUIDANCE_TABLE_NAME environment variable not set"
        print(f"[ERROR] {error_msg}")
        return {"statusCode": 500, "body": json.dumps({"error": error_msg})}
    
    table = dynamodb.Table(GUIDANCE_TABLE_NAME)
    
    # Process each BIM section
    for section_path in sections_to_fetch:
        section_id = section_path.split("/")[-1]  # Extract "bim37000" from path
        
        try:
            print(f"[INFO] Processing section: {section_id}")
            
            # Check if already exists (skip if not force_refresh)
            if not force_refresh and section_exists(table, section_id):
                print(f"[INFO] Section {section_id} already exists, skipping")
                results["sections_processed"].append({
                    "section_id": section_id,
                    "status": "skipped",
                    "reason": "already_exists"
                })
                continue
            
            # Fetch from GOV.UK API
            guidance_data = fetch_section_from_govuk(section_path)
            
            if not guidance_data:
                print(f"[WARNING] Failed to fetch section {section_id}")
                results["failure_count"] += 1
                results["errors"].append({
                    "section_id": section_id,
                    "error": "Failed to fetch from GOV.UK API"
                })
                continue
            
            # Extract compliance rules, examples, keywords
            processed_data = extract_compliance_data(section_id, guidance_data)
            
            # Store in DynamoDB
            store_in_dynamodb(table, section_id, processed_data)
            
            # Backup to S3
            backup_to_s3(section_id, guidance_data)
            
            results["success_count"] += 1
            results["sections_processed"].append({
                "section_id": section_id,
                "status": "success",
                "compliance_rules_count": len(processed_data.get("compliance_rules", []))
            })
            
            # Rate limiting (8.3 req/sec = ~120ms between requests)
            time.sleep(1 / RATE_LIMIT_PER_SEC)
            
        except Exception as e:
            print(f"[ERROR] Failed to process section {section_id}: {str(e)}")
            results["failure_count"] += 1
            results["errors"].append({
                "section_id": section_id,
                "error": str(e)
            })
    
    # Summary
    print(f"[INFO] Completed: {results['success_count']} success, {results['failure_count']} failures")
    
    return {
        "statusCode": 200,
        "body": json.dumps(results, default=str)
    }


def section_exists(table, section_id: str) -> bool:
    """Check if section already exists in DynamoDB"""
    try:
        response = table.get_item(Key={"section_id": section_id})
        return "Item" in response
    except ClientError as e:
        print(f"[WARNING] Error checking section existence: {e}")
        return False


def fetch_section_from_govuk(section_path: str) -> Optional[Dict]:
    """
    Fetch BIM section from GOV.UK Content API
    
    Args:
        section_path: Full path like "guidance/business-income-manual/bim37000"
    
    Returns:
        dict: JSON response from GOV.UK API or None
    """
    url = f"{GOVUK_API_BASE_URL}/{section_path}"
    
    headers = {
        "User-Agent": "FiscalShield-Compliance-Bot/1.0 (HMRC Guidance Sync)",
        "Accept": "application/json"
    }
    
    try:
        print(f"[INFO] Fetching from GOV.UK: {url}")
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            print(f"[INFO] Successfully fetched {section_path}")
            return response.json()
        elif response.status_code == 429:
            print(f"[WARNING] Rate limited by GOV.UK API, retrying after 5s")
            time.sleep(5)
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.json()
        else:
            print(f"[ERROR] GOV.UK API returned {response.status_code}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Request failed: {e}")
        return None


def extract_compliance_data(section_id: str, govuk_data: Dict) -> Dict:
    """
    Extract compliance rules, examples, and keywords from GOV.UK response
    
    Args:
        section_id: BIM section ID (e.g., "bim37000")
        govuk_data: Raw JSON from GOV.UK API
    
    Returns:
        dict: Processed compliance data
    """
    details = govuk_data.get("details", {})
    
    # Extract main content
    body = details.get("body", "")
    title = govuk_data.get("title", "")
    description = govuk_data.get("description", "")
    
    # Extract compliance rules (look for lists, bullet points)
    compliance_rules = extract_rules_from_html(body)
    
    # Extract examples
    examples = extract_examples_from_html(body)
    
    # Extract keywords
    keywords = extract_keywords(title, description, body)
    
    # Category
    category = BIM_CATEGORIES.get(section_id, "general")
    
    return {
        "section_id": section_id,
        "title": title,
        "description": description,
        "category": category,
        "compliance_rules": compliance_rules,
        "examples": examples,
        "keywords": keywords,
        "body_html": body,  # Store full HTML for future reference
        "last_updated": int(time.time()),
        "source_url": govuk_data.get("base_path", "")
    }


def extract_rules_from_html(html_body: str) -> List[str]:
    """Extract compliance rules from HTML (simplified)"""
    # Simple extraction - look for list items and paragraphs
    # In production, you'd use BeautifulSoup for proper HTML parsing
    rules = []
    
    # Basic pattern: Look for sentences with "must", "should", "cannot", "allowed"
    keywords = ["must", "should", "cannot", "not allowed", "permitted", "deductible", "non-deductible"]
    
    for line in html_body.split("."):
        line_lower = line.lower()
        if any(keyword in line_lower for keyword in keywords):
            rule = line.strip()
            if len(rule) > 20:  # Ignore very short sentences
                rules.append(rule[:500])  # Limit rule length
    
    return rules[:50]  # Max 50 rules per section


def extract_examples_from_html(html_body: str) -> List[str]:
    """Extract examples from HTML"""
    examples = []
    
    # Look for "Example:", "For example", "Such as"
    for line in html_body.split("\n"):
        if any(marker in line.lower() for marker in ["example:", "for example", "such as"]):
            example = line.strip()
            if len(example) > 20:
                examples.append(example[:300])
    
    return examples[:20]  # Max 20 examples


def extract_keywords(title: str, description: str, body: str) -> List[str]:
    """Extract relevant keywords for search"""
    # Combine all text
    combined_text = f"{title} {description} {body}".lower()
    
    # Common keywords to extract
    keyword_patterns = [
        "travel", "subsistence", "entertainment", "motor", "vehicle",
        "accommodation", "hotel", "meal", "client", "business",
        "private", "expense", "deductible", "allowable", "vat",
        "invoice", "receipt", "claim", "mileage", "fuel",
        "professional fees", "legal", "accountancy", "tax"
    ]
    
    found_keywords = []
    for keyword in keyword_patterns:
        if keyword in combined_text:
            found_keywords.append(keyword)
    
    return list(set(found_keywords))  # Remove duplicates


def store_in_dynamodb(table, section_id: str, data: Dict):
    """Store processed guidance data in DynamoDB"""
    try:
        item = {
            "section_id": section_id,
            "category": data["category"],
            "title": data["title"],
            "description": data["description"],
            "compliance_rules": data["compliance_rules"],
            "examples": data["examples"],
            "keywords": data["keywords"],
            "body_html": data["body_html"],
            "last_updated": data["last_updated"],
            "source_url": data["source_url"]
        }
        
        table.put_item(Item=item)
        print(f"[INFO] Stored {section_id} in DynamoDB")
        
    except ClientError as e:
        print(f"[ERROR] Failed to store in DynamoDB: {e}")
        raise


def backup_to_s3(section_id: str, raw_data: Dict):
    """Backup raw GOV.UK response to S3"""
    if not DATA_ARCHIVE_BUCKET:
        print("[WARNING] DATA_ARCHIVE_BUCKET not set, skipping S3 backup")
        return
    
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d")
        s3_key = f"hmrc-guidance/{section_id}/{timestamp}.json"
        
        s3_client.put_object(
            Bucket=DATA_ARCHIVE_BUCKET,
            Key=s3_key,
            Body=json.dumps(raw_data, indent=2),
            ContentType="application/json"
        )
        
        print(f"[INFO] Backed up {section_id} to S3: {s3_key}")
        
    except ClientError as e:
        print(f"[WARNING] Failed to backup to S3 (non-fatal): {e}")
        # Don't raise - S3 backup is optional
