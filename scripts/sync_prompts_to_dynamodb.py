#!/usr/bin/env python3
"""
Sync prompts from Lambda code to DynamoDB ConfigurationTable

This script ensures prompts in DynamoDB match the latest defaults from code.
Designed to run as part of CI/CD post-deployment.

Architecture Decision:
- Lambda code contains the "source of truth" default prompts
- DynamoDB stores user overrides (via frontend) with version tracking
- On deployment, update base prompts ONLY if no custom version exists
- If custom version exists, increment available_version but keep user's version

Usage:
    python sync_prompts_to_dynamodb.py --stack-name <stack> --region eu-central-1
"""

import argparse
import boto3
import sys
from datetime import datetime
from typing import Optional, Dict
import importlib.util
import os


def load_prompt_from_lambda(handler_path: str, function_name: str) -> Optional[str]:
    """
    Extract prompt from Lambda handler file by parsing the source code.
    
    Args:
        handler_path: Path to Lambda handler file (e.g., patterns/pattern-2/lambdas/.../handler.py)
        function_name: Name of the function that returns the prompt (e.g., 'get_default_invoice_prompt')
    
    Returns:
        Prompt string from Lambda code
    """
    try:
        # Read the file and extract the prompt
        with open(handler_path, 'r') as f:
            content = f.read()
        
        # Find the function definition first (handle type hints like -> str:)
        import re
        func_pattern = rf'def {re.escape(function_name)}\([^)]*\)(?:\s*->\s*\w+)?:'
        func_match = re.search(func_pattern, content)
        
        if not func_match:
            print(f"   ❌ Function {function_name} not found in file")
            return None
        
        # Get content starting from the function
        func_start = func_match.start()
        content_from_func = content[func_start:]
        
        # Extract the triple-quoted string after return statement
        prompt_pattern = r'return\s+"""(.*?)"""'
        prompt_match = re.search(prompt_pattern, content_from_func, re.DOTALL)
        
        if prompt_match:
            prompt = prompt_match.group(1)
            print(f"   ✅ Extracted prompt ({len(prompt)} characters)")
            return prompt
        else:
            print(f"   ❌ Could not find prompt return statement in {function_name}")
            return None
    except Exception as e:
        print(f"   ❌ Error loading prompt from {handler_path}: {e}")
        import traceback
        traceback.print_exc()
        return None
        return None


def get_configuration_table_name(stack_name: str, region: str) -> str:
    """Get ConfigurationTable name from CloudFormation stack"""
    cfn = boto3.client('cloudformation', region_name=region)
    
    try:
        response = cfn.describe_stacks(StackName=stack_name)
        stack = response['Stacks'][0]
        
        # Look for ConfigurationTable in outputs
        for output in stack.get('Outputs', []):
            if 'ConfigurationTable' in output['OutputKey']:
                table_ref = output['OutputValue']
                # Extract table name from URL or ARN if needed
                if 'table=' in table_ref:
                    # It's a console URL, extract table name
                    import re
                    match = re.search(r'table=([a-zA-Z0-9_.-]+)', table_ref)
                    if match:
                        return match.group(1)
                # Otherwise assume it's the table name directly
                return table_ref
        
        raise ValueError(f"ConfigurationTable not found in stack {stack_name}")
    except Exception as e:
        print(f"❌ Error getting ConfigurationTable: {e}")
        sys.exit(1)


def sync_prompt(
    table_name: str,
    region: str,
    config_key: str,
    new_prompt: str,
    force_update: bool = False
) -> bool:
    """
    Sync a single prompt to DynamoDB with version tracking.
    
    Strategy:
    - If no prompt exists → create with version 1
    - If prompt exists and is DEFAULT (not customized) → update
    - If prompt exists and is CUSTOM → increment available_version, don't overwrite
    - If force_update=True → always update (use with caution)
    
    Args:
        table_name: DynamoDB table name
        region: AWS region
        config_key: Configuration key (e.g., 'INVOICE_EXTRACTION_PROMPT')
        new_prompt: New prompt text from Lambda code
        force_update: Force update even if custom version exists
    
    Returns:
        True if updated, False if skipped
    """
    dynamodb = boto3.resource('dynamodb', region_name=region)
    table = dynamodb.Table(table_name)
    
    try:
        # Check if prompt already exists
        response = table.get_item(Key={'Configuration': config_key})
        
        if 'Item' in response:
            existing_item = response['Item']
            is_custom = existing_item.get('IsCustom', False)
            current_version = existing_item.get('Version', 1)
            
            if is_custom and not force_update:
                # User has customized this prompt - don't overwrite
                print(f"⚠️  {config_key}: Custom version detected (v{current_version})")
                print(f"   → Keeping user's custom version")
                print(f"   → Incrementing available_version for reference")
                
                # Update metadata to show new version is available
                table.update_item(
                    Key={'Configuration': config_key},
                    UpdateExpression='SET AvailableVersion = :new_ver, LastCodeUpdate = :updated',
                    ExpressionAttributeValues={
                        ':new_ver': current_version + 1,
                        ':updated': datetime.now().isoformat()
                    }
                )
                return False
            else:
                # Default prompt - safe to update
                print(f"✅ {config_key}: Updating default prompt (v{current_version} → v{current_version + 1})")
                
                table.put_item(Item={
                    'Configuration': config_key,
                    'PromptTemplate': new_prompt,
                    'Version': current_version + 1,
                    'IsCustom': False,
                    'LastUpdated': datetime.now().isoformat(),
                    'LastCodeUpdate': datetime.now().isoformat(),
                    'UpdatedBy': 'cicd-deployment',
                    'Source': 'lambda-code-sync'
                })
                return True
        else:
            # No existing prompt - create new
            print(f"🆕 {config_key}: Creating initial prompt (v1)")
            
            table.put_item(Item={
                'Configuration': config_key,
                'PromptTemplate': new_prompt,
                'Version': 1,
                'IsCustom': False,
                'LastUpdated': datetime.now().isoformat(),
                'LastCodeUpdate': datetime.now().isoformat(),
                'CreatedAt': datetime.now().isoformat(),
                'UpdatedBy': 'cicd-deployment',
                'Source': 'lambda-code-sync'
            })
            return True
            
    except Exception as e:
        print(f"❌ Error syncing {config_key}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Sync prompts from Lambda code to DynamoDB')
    parser.add_argument('--stack-name', required=True, help='CloudFormation stack name')
    parser.add_argument('--region', default='eu-central-1', help='AWS region')
    parser.add_argument('--force', action='store_true', 
                       help='Force update even if custom versions exist (DANGEROUS)')
    
    args = parser.parse_args()
    
    print(f"🔄 Syncing prompts to DynamoDB...")
    print(f"   Stack: {args.stack_name}")
    print(f"   Region: {args.region}")
    
    # Get ConfigurationTable name
    table_name = get_configuration_table_name(args.stack_name, args.region)
    print(f"   Table: {table_name}")
    
    # Define prompts to sync (Lambda path, function name, DynamoDB key)
    prompts_to_sync = [
        {
            'path': 'patterns/pattern-2/lambdas/invoice_extraction/invoice_extraction_handler.py',
            'function': 'get_default_invoice_prompt',
            'key': 'INVOICE_EXTRACTION_PROMPT',
            'name': 'Invoice Extraction'
        },
        # Add more prompts here as needed:
        # {
        #     'path': 'patterns/pattern-2/lambdas/bank_statement_extraction/handler.py',
        #     'function': 'get_default_bank_statement_prompt',
        #     'key': 'BANK_STATEMENT_EXTRACTION_PROMPT',
        #     'name': 'Bank Statement Extraction'
        # },
    ]
    
    updated_count = 0
    skipped_count = 0
    
    for prompt_config in prompts_to_sync:
        print(f"\n📋 Processing: {prompt_config['name']}")
        
        # Load prompt from Lambda code
        prompt_text = load_prompt_from_lambda(prompt_config['path'], prompt_config['function'])
        
        if not prompt_text:
            print(f"   ⚠️  Could not load prompt from {prompt_config['path']}")
            skipped_count += 1
            continue
        
        # Sync to DynamoDB
        updated = sync_prompt(
            table_name=table_name,
            region=args.region,
            config_key=prompt_config['key'],
            new_prompt=prompt_text,
            force_update=args.force
        )
        
        if updated:
            updated_count += 1
        else:
            skipped_count += 1
    
    print(f"\n{'='*60}")
    print(f"✅ Sync complete!")
    print(f"   Updated: {updated_count}")
    print(f"   Skipped: {skipped_count} (custom versions preserved)")
    print(f"{'='*60}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
