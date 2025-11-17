"""
Trigger Transaction Analysis Lambda
Queries pending transactions and prepares batches for Step Functions Map state.
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
BATCH_SIZE = int(os.environ.get('BATCH_SIZE', '15'))  # Transactions per batch


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder for DynamoDB Decimal types"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


def query_pending_transactions(company_number: str, user_id: str, limit: int = 1000) -> List[Dict]:
    """
    Query pending transactions for a company/user from ExtractionResultsTable.
    Uses GSI6-ClientType index which projects ALL attributes including AnalysisStatus.
    """
    
    extraction_table = dynamodb.Table(EXTRACTION_RESULTS_TABLE)
    
    print(f"Querying pending transactions for company {company_number}, user {user_id}")
    
    try:
        # Query using GSI6 for company-level access with ALL attributes
        # Note: AnalysisStatus might not exist on older records, so we filter for:
        # - Records where AnalysisStatus = 'PENDING', OR
        # - Records where AnalysisStatus attribute doesn't exist
        response = extraction_table.query(
            IndexName='GSI6-ClientType',
            KeyConditionExpression='GSI6PK = :gsi6pk',
            FilterExpression='UserId = :user_id AND (attribute_not_exists(AnalysisStatus) OR AnalysisStatus = :status)',
            ExpressionAttributeValues={
                ':gsi6pk': f"client#{company_number}#type#BANK_STATEMENT",
                ':user_id': user_id,
                ':status': 'PENDING'
            },
            Limit=limit
        )
        
        items = response.get('Items', [])
        print(f"Found {len(items)} pending transactions for analysis")
        
        return items
        
    except Exception as e:
        print(f"Error querying pending transactions: {str(e)}")
        raise


def prepare_batches(transactions: List[Dict], company_number: str, user_id: str) -> List[Dict]:
    """
    Prepare transaction batches for Step Functions Map state.
    Returns list of batch objects ready for parallel processing.
    """
    
    batches = []
    
    # Filter out transactions without TransactionId (invalid records)
    valid_transactions = [t for t in transactions if t.get('TransactionId')]
    
    if len(valid_transactions) < len(transactions):
        print(f"Warning: Filtered out {len(transactions) - len(valid_transactions)} transactions without TransactionId")
    
    # Split into batches
    for i in range(0, len(valid_transactions), BATCH_SIZE):
        batch = valid_transactions[i:i + BATCH_SIZE]
        
        # Extract transaction IDs for this batch
        transaction_ids = [t['TransactionId'] for t in batch]
        
        batch_obj = {
            'transaction_ids': transaction_ids,
            'company_number': company_number,
            'user_id': user_id,
            'batch_index': i // BATCH_SIZE,
            'batch_size': len(transaction_ids),
            'created_at': int(time.time())
        }
        
        batches.append(batch_obj)
        print(f"Prepared batch {len(batches)} with {len(transaction_ids)} transactions")
    
    return batches


def lambda_handler(event, context):
    """
    Lambda handler for preparing transaction batches for Step Functions.
    
    Expected event from Step Functions:
    {
        "companyNumber": "12345678",
        "userId": "user-id-from-cognito"
    }
    
    Returns batches array for Map state processing.
    """
    
    print(f"Received event: {json.dumps(event, default=str)}")
    
    try:
        # Extract parameters
        company_number = event.get('companyNumber')
        user_id = event.get('userId')
        
        if not company_number or not user_id:
            raise ValueError('Missing required parameters: companyNumber and userId')
        
        print(f"Preparing batches for company {company_number}, user {user_id}")
        
        # Step 1: Query pending transactions
        pending_transactions = query_pending_transactions(company_number, user_id)
        
        if not pending_transactions:
            print("No pending transactions found")
            return {
                'success': True,
                'message': 'No pending transactions found for analysis',
                'pending_count': 0,
                'batches': [],
                'total_batches': 0
            }
        
        # Step 2: Prepare batches for Map state
        batches = prepare_batches(
            pending_transactions,
            company_number,
            user_id
        )
        
        print(f"Prepared {len(batches)} batches with {len(pending_transactions)} total transactions")
        
        return {
            'success': True,
            'message': f'Prepared {len(pending_transactions)} transactions for analysis',
            'pending_count': len(pending_transactions),
            'batches': batches,
            'total_batches': len(batches),
            'batch_size': BATCH_SIZE,
            'company_number': company_number,
            'user_id': user_id
        }
        
    except Exception as e:
        print(f"Error preparing batches: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        
        raise  # Re-raise for Step Functions error handling
