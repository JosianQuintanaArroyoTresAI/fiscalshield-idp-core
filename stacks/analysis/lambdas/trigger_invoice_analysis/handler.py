"""
Trigger Invoice Analysis Lambda
Queries pending invoices and prepares batches for Step Functions Map state.
Invoked via Step Functions workflow from GraphQL mutation.
"""

import json
import boto3
import os
import time
from typing import Dict, List, Any
from decimal import Decimal

# AWS clients
dynamodb = boto3.resource('dynamodb')

# Environment variables
EXTRACTION_RESULTS_TABLE = os.environ.get('EXTRACTION_RESULTS_TABLE')
BATCH_SIZE = int(os.environ.get('BATCH_SIZE', '10'))  # Invoices per batch (smaller than transactions due to longer content)


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder for DynamoDB Decimal types"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


def query_pending_invoices(company_number: str, user_id: str, max_items: int = 1000) -> List[Dict]:
    """
    Query pending invoices for a company/user from ExtractionResultsTable.
    Uses GSI7-ClientTypeDate index to fetch invoices that haven't been analyzed yet.
    
    Args:
        company_number: Company number to filter invoices
        user_id: User ID to filter invoices
        max_items: Maximum number of items to fetch (default 1000)
    
    Returns:
        List of pending invoices (AnalysisStatus is None or 'PENDING')
    """
    
    extraction_table = dynamodb.Table(EXTRACTION_RESULTS_TABLE)
    
    print(f"Querying pending invoices for company {company_number}, user {user_id}")
    
    try:
        all_items = []
        last_evaluated_key = None
        
        # Paginate through results
        while True:
            query_params = {
                'IndexName': 'GSI7-ClientTypeDate',
                'KeyConditionExpression': 'GSI6PK = :gsi6pk',
                'FilterExpression': '(attribute_not_exists(AnalysisStatus) OR AnalysisStatus = :status)',
                'ExpressionAttributeValues': {
                    ':gsi6pk': f"client#{company_number}#type#INVOICE",
                    ':status': 'PENDING'
                }
            }
            
            if last_evaluated_key:
                query_params['ExclusiveStartKey'] = last_evaluated_key
            
            response = extraction_table.query(**query_params)
            all_items.extend(response.get('Items', []))
            
            # Check if we have more pages
            last_evaluated_key = response.get('LastEvaluatedKey')
            
            # Stop if no more pages or we've hit max_items limit
            if not last_evaluated_key or len(all_items) >= max_items:
                break
        
        print(f"Found {len(all_items)} pending invoices for analysis")
        return all_items[:max_items]
        
    except Exception as e:
        print(f"Error querying pending invoices: {str(e)}")
        raise


def prepare_batches(invoices: List[Dict], company_number: str, user_id: str) -> List[Dict]:
    """
    Prepare invoice batches for Step Functions Map state.
    Returns list of batch objects ready for parallel processing.
    """
    
    batches = []
    
    # Filter out invoices without InvoiceId (invalid records)
    valid_invoices = [inv for inv in invoices if inv.get('InvoiceId')]
    
    if len(valid_invoices) < len(invoices):
        print(f"Warning: Filtered out {len(invoices) - len(valid_invoices)} invoices without InvoiceId")
    
    # Split into batches
    for i in range(0, len(valid_invoices), BATCH_SIZE):
        batch = valid_invoices[i:i + BATCH_SIZE]
        
        batch_obj = {
            'batch_index': len(batches),
            'batch_size': len(batch),
            'company_number': company_number,
            'user_id': user_id,
            'invoices': batch
        }
        
        batches.append(batch_obj)
    
    print(f"Prepared {len(batches)} batches (batch size: {BATCH_SIZE})")
    
    return batches


def lambda_handler(event, context):
    """
    Main handler for triggering invoice analysis.
    
    Event format (from GraphQL mutation via Step Functions):
    {
        "company_number": "12345678",
        "user_id": "user@example.com"
    }
    
    Returns:
    {
        "batches": [<batch objects for Map state>],
        "total_invoices": 156,
        "batch_count": 16
    }
    """
    
    print(f"Trigger Invoice Analysis Lambda invoked")
    print(f"Event: {json.dumps(event, default=str)}")
    
    try:
        # Extract parameters
        company_number = event.get('company_number')
        user_id = event.get('user_id')
        
        if not company_number or not user_id:
            raise ValueError("Missing required parameters: company_number, user_id")
        
        # Query pending invoices
        pending_invoices = query_pending_invoices(company_number, user_id)
        
        if not pending_invoices:
            print("No pending invoices found for analysis")
            return {
                'statusCode': 200,
                'batches': [],
                'total_invoices': 0,
                'batch_count': 0,
                'message': 'No pending invoices to analyze'
            }
        
        # Prepare batches for Map state
        batches = prepare_batches(pending_invoices, company_number, user_id)
        
        result = {
            'statusCode': 200,
            'batches': batches,
            'total_invoices': len(pending_invoices),
            'batch_count': len(batches),
            'message': f'Prepared {len(batches)} batches for processing ({len(pending_invoices)} invoices)'
        }
        
        print(f"Successfully prepared batches: {result['message']}")
        
        return result
        
    except Exception as e:
        print(f"Error in trigger_invoice_analysis: {str(e)}")
        raise
