"""
Health check endpoint for Analysis Stack
"""

import json
import os


def lambda_handler(event, context):
    """
    Health check endpoint
    
    Returns stack availability status for Core Stack integration
    """
    environment = os.environ.get('ENVIRONMENT', 'unknown')
    
    health_status = {
        'status': 'available',
        'stack': 'fiscalshield-analysis',
        'version': '1.0.0',
        'environment': environment,
        'region': os.environ.get('AWS_REGION', 'unknown'),
        'services': {
            'company_intelligence': 'operational',
            'risk_assessment': 'operational',
            'dynamodb': 'operational'
        },
        'message': 'Analysis Stack is operational'
    }
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'GET,OPTIONS'
        },
        'body': json.dumps(health_status)
    }
