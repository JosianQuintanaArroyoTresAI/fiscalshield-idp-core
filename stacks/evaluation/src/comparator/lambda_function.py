"""
Comparator Lambda - Compares baseline vs evaluation extraction results
"""
import json
import logging
import os
from typing import Dict, Any, List

logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

def lambda_handler(event, context):
    """
    Compares baseline extraction results with evaluation results.
    
    Args:
        event: Contains baseline_results and evaluation_results
        context: Lambda context
        
    Returns:
        Comparison metrics and detailed differences
    """
    logger.info("Starting comparison...")
    
    baseline = event.get('baseline_results', {})
    evaluation = event.get('evaluation_results', {})
    
    # TODO: Implement field-by-field comparison
    # For now, return placeholder metrics
    
    metrics = {
        'total_fields': 0,
        'exact_matches': 0,
        'fuzzy_matches': 0,
        'mismatches': 0,
        'accuracy': 0.0,
        'differences': []
    }
    
    logger.info(f"Comparison complete: {metrics}")
    
    return {
        'statusCode': 200,
        'metrics': metrics
    }
