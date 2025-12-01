"""
Batch Job Monitor - Polls Bedrock batch job status
"""
import json
import logging
import os
import boto3
from typing import Dict, Any

logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
BATCH_JOBS_TABLE = os.environ.get('BATCH_JOBS_TABLE')

def lambda_handler(event, context):
    """
    Monitors Bedrock batch inference job status.
    
    Args:
        event: Contains batchJob with result containing jobArn
        context: Lambda context
        
    Returns:
        Job status and results location
    """
    logger.info(f"Checking batch job status: {json.dumps(event)}")
    
    # Extract job ARN from the event structure
    batch_job = event.get('batchJob', {})
    result = batch_job.get('result', {})
    job_arn = result.get('jobArn')
    evaluation_id = result.get('evaluationId')
    
    if not job_arn:
        logger.error(f"No jobArn found in event: {event}")
        return {
            'statusCode': 400,
            'status': 'FAILED',
            'error': 'Missing jobArn in event'
        }
    
    region = os.environ.get('EVALUATION_REGION', 'us-east-1')
    bedrock = boto3.client('bedrock', region_name=region)
    
    try:
        # Get job status from Bedrock
        response = bedrock.get_model_invocation_job(jobIdentifier=job_arn)
        
        job_status = response.get('status')
        output_config = response.get('outputDataConfig', {})
        output_uri = output_config.get('s3Uri', '')
        
        logger.info(f"Bedrock job {job_arn} status: {job_status}")
        logger.info(f"Output URI: {output_uri}")
        
        # Map Bedrock statuses to our expected statuses
        status_mapping = {
            'Submitted': 'RUNNING',
            'InProgress': 'RUNNING',
            'Completed': 'COMPLETED',
            'Failed': 'FAILED',
            'Stopping': 'RUNNING',
            'Stopped': 'FAILED',
            'PartiallyCompleted': 'COMPLETED'  # Treat partial as complete
        }
        
        mapped_status = status_mapping.get(job_status, 'RUNNING')
        
        # Update DynamoDB with current status
        if BATCH_JOBS_TABLE and evaluation_id:
            table = dynamodb.Table(BATCH_JOBS_TABLE)
            table.update_item(
                Key={'JobId': evaluation_id},
                UpdateExpression='SET #status = :status, LastChecked = :timestamp',
                ExpressionAttributeNames={'#status': 'Status'},
                ExpressionAttributeValues={
                    ':status': mapped_status,
                    ':timestamp': int(context.aws_request_id[:8], 16)
                }
            )
        
        return {
            'statusCode': 200,
            'job_id': evaluation_id,
            'status': mapped_status,
            'results_location': output_uri,
            'bedrock_status': job_status
        }
        
    except bedrock.exceptions.ResourceNotFoundException:
        logger.error(f"Job not found: {job_arn}")
        return {
            'statusCode': 404,
            'status': 'FAILED',
            'error': f'Job not found: {job_arn}'
        }
    except Exception as e:
        logger.exception(f"Error checking batch job status: {e}")
        return {
            'statusCode': 500,
            'status': 'FAILED',
            'error': str(e)
        }
