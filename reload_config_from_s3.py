#!/usr/bin/env python3
"""Reload the Pattern 2 configuration from the configuration bucket into DynamoDB.

This helper discovers the active configuration bucket and table from the
CloudFormation stack (by default ``fiscalshield-idp-dev``) so it keeps working
after deployments that create new physical resource IDs.  The script also
ensures the ``classification.trust_user_hint`` flag is present (defaulting to
``true``) so that user-provided document types can bypass LLM classification
without requiring manual edits to the stored configuration.
"""

from __future__ import annotations

import os
from decimal import Decimal

import boto3
import yaml

# Default settings can be overridden via environment variables
REGION = os.environ.get("REGION", "eu-central-1")
STACK_NAME = os.environ.get("STACK_NAME", "fiscalshield-idp-dev")
S3_KEY = os.environ.get(
    "CONFIG_S3_KEY", "config_library/pattern-2/rvl-cdip-package-sample/config.yaml"
)

def convert_floats_to_decimal(obj):
    """Recursively convert float values to Decimal for DynamoDB compatibility"""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: convert_floats_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats_to_decimal(item) for item in obj]
    return obj

def discover_stack_resource(logical_id: str) -> str:
    """Look up a physical resource ID by logical ID from the target stack."""

    cf = boto3.client("cloudformation", region_name=REGION)
    paginator = cf.get_paginator("list_stack_resources")

    for page in paginator.paginate(StackName=STACK_NAME):
        for resource in page.get("StackResourceSummaries", []):
            if resource.get("LogicalResourceId") == logical_id:
                return resource.get("PhysicalResourceId")

    raise RuntimeError(
        f"Unable to find resource with logical ID '{logical_id}' in stack {STACK_NAME}"
    )


def ensure_user_hint_defaults(config: dict) -> None:
    """Add user-hint defaults to the classification block when missing."""

    classification_cfg = config.setdefault("classification", {})

    classification_cfg.setdefault("trust_user_hint", True)
    classification_cfg.setdefault("validate_hint_on_mismatch", True)


def main():
    # Discover dynamic resource names
    print(f"🔍 Discovering resources for stack: {STACK_NAME} (region: {REGION})")
    dynamodb_table = os.environ.get(
        "DYNAMODB_TABLE",
        discover_stack_resource("ConfigurationTable"),
    )
    s3_bucket = os.environ.get(
        "CONFIG_BUCKET",
        discover_stack_resource("ConfigurationBucket"),
    )

    print(f"   • Configuration table : {dynamodb_table}")
    print(f"   • Configuration bucket: {s3_bucket}")
    print(f"   • Config key          : {S3_KEY}")

    # Initialize AWS clients
    s3_client = boto3.client("s3", region_name=REGION)
    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(dynamodb_table)

    print("\n📥 Fetching configuration from S3…")
    response = s3_client.get_object(Bucket=s3_bucket, Key=S3_KEY)
    config_content = response["Body"].read().decode("utf-8")
    config_data = yaml.safe_load(config_content)

    # Ensure user hint behaviour is enabled by default
    ensure_user_hint_defaults(config_data)

    # Show some model info for quick verification
    print("\n✅ Configuration loaded from S3")
    print("\n🔍 Model IDs found in configuration:")
    if config_data.get("classification", {}).get("model"):
        print(f"   - Classification: {config_data['classification']['model']}")
    if config_data.get("extraction", {}).get("model"):
        print(f"   - Extraction: {config_data['extraction']['model']}")
    if config_data.get("summarization", {}).get("model"):
        print(f"   - Summarization: {config_data['summarization']['model']}")
    if config_data.get("assessment", {}).get("model"):
        print(f"   - Assessment: {config_data['assessment']['model']}")

    # Convert floats to Decimal for DynamoDB
    converted_data = convert_floats_to_decimal(config_data)

    print("\n💾 Writing Default configuration to DynamoDB…")
    table.put_item(Item={"Configuration": "Default", **converted_data})

    print("\n✅ Configuration successfully reloaded!")
    print("\n🎯 Next steps:")
    print("   1. Refresh the frontend configuration view (if open)")
    print("   2. Re-run a document to confirm user-hinted classification is used")
    print(
        "   3. If custom configs exist, repeat for the appropriate configuration keys"
    )

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
