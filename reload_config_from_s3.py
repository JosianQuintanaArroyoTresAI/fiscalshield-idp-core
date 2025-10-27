#!/usr/bin/env python3
"""
Script to reload configuration from S3 into DynamoDB
This ensures EU models are used instead of US cross-region inference
"""

import boto3
import yaml
from decimal import Decimal

# Configuration
REGION = 'eu-central-1'
DYNAMODB_TABLE = 'fiscalshield-idp-dev-ConfigurationTable-6UMRLKUMM1UL'
S3_BUCKET = 'fiscalshield-idp-dev-configurationbucket-6plnyx2e6czr'
S3_KEY = 'config_library/pattern-2/rvl-cdip-package-sample/config.yaml'

def convert_floats_to_decimal(obj):
    """Recursively convert float values to Decimal for DynamoDB compatibility"""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: convert_floats_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats_to_decimal(item) for item in obj]
    return obj

def main():
    # Initialize AWS clients
    s3_client = boto3.client('s3', region_name=REGION)
    dynamodb = boto3.resource('dynamodb', region_name=REGION)
    table = dynamodb.Table(DYNAMODB_TABLE)
    
    print(f"📥 Fetching configuration from S3...")
    print(f"   Bucket: {S3_BUCKET}")
    print(f"   Key: {S3_KEY}")
    
    # Fetch config from S3
    response = s3_client.get_object(Bucket=S3_BUCKET, Key=S3_KEY)
    config_content = response['Body'].read().decode('utf-8')
    config_data = yaml.safe_load(config_content)
    
    # Show some model info
    print(f"\n✅ Configuration loaded from S3")
    print(f"\n🔍 Model IDs found in configuration:")
    if 'classification' in config_data and 'model' in config_data['classification']:
        print(f"   - Classification: {config_data['classification']['model']}")
    if 'extraction' in config_data and 'model' in config_data['extraction']:
        print(f"   - Extraction: {config_data['extraction']['model']}")
    if 'summarization' in config_data and 'model' in config_data['summarization']:
        print(f"   - Summarization: {config_data['summarization']['model']}")
    if 'assessment' in config_data and 'model' in config_data['assessment']:
        print(f"   - Assessment: {config_data['assessment']['model']}")
    
    # Convert floats to Decimal for DynamoDB
    converted_data = convert_floats_to_decimal(config_data)
    
    print(f"\n💾 Writing Default configuration to DynamoDB...")
    print(f"   Table: {DYNAMODB_TABLE}")
    
    # Write to DynamoDB
    table.put_item(Item={'Configuration': 'Default', **converted_data})
    
    print(f"\n✅ Configuration successfully reloaded!")
    print(f"\n🎯 Next steps:")
    print(f"   1. Refresh your frontend UI")
    print(f"   2. Check View/Edit Configuration - models should now be EU-based")
    print(f"   3. Test document processing to verify EU models are being used")
    print(f"\n⚠️  Note: This fix will persist across redeployments as long as the")
    print(f"   S3 config files continue to have EU models.")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
