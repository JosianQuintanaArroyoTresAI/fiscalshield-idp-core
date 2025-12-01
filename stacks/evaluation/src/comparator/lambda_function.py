"""
Comparator Lambda - Compares baseline vs evaluation extraction results
"""
import json
import logging
import os
import boto3
from typing import Dict, Any, List
from decimal import Decimal
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# Initialize AWS clients
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# Environment variables
STACK_NAME = os.environ.get('STACK_NAME')
EVALUATION_METRICS_TABLE = os.environ.get('EVALUATION_METRICS_TABLE')
EVALUATION_BUCKET = os.environ.get('EVALUATION_BUCKET')


def discover_table(pattern: str) -> str:
    """Discover DynamoDB table by pattern."""
    client = boto3.client('dynamodb')
    response = client.list_tables()
    
    for table_name in response.get('TableNames', []):
        if pattern in table_name:
            logger.info(f"Discovered table: {table_name}")
            return table_name
    
    raise ValueError(f"Table matching pattern '{pattern}' not found")


def get_baseline_results(evaluation_id: str) -> List[Dict]:
    """
    Fetch baseline extraction results from ExtractionResultsTable.
    
    Args:
        evaluation_id: Evaluation ID (contains timestamp)
    
    Returns:
        List of baseline extraction results
    """
    table_name = discover_table(f"{STACK_NAME}-ExtractionResultsTable")
    table = dynamodb.Table(table_name)
    
    # Read manifest to get document IDs
    manifest_key = f"batch-inputs/{evaluation_id}/manifest.jsonl"
    
    try:
        response = s3_client.get_object(Bucket=EVALUATION_BUCKET, Key=manifest_key)
        manifest_lines = response['Body'].read().decode('utf-8').strip().split('\n')
        
        baseline_results = []
        for line in manifest_lines:
            manifest_item = json.loads(line)
            doc_id = manifest_item.get('recordId')
            
            if doc_id:
                # Query DynamoDB for this document
                item_response = table.get_item(Key={'document_id': doc_id})
                if 'Item' in item_response:
                    baseline_results.append(json.loads(json.dumps(item_response['Item']), parse_float=Decimal))
        
        logger.info(f"Fetched {len(baseline_results)} baseline results")
        return baseline_results
        
    except Exception as e:
        logger.exception(f"Error fetching baseline results: {e}")
        return []


def get_evaluation_results(results_location: str, mode: str) -> List[Dict]:
    """
    Fetch evaluation results from S3.
    
    Args:
        results_location: S3 URI for results
        mode: 'batch' or 'direct'
    
    Returns:
        List of evaluation extraction results
    """
    # Parse S3 URI
    if not results_location or results_location.startswith('s3://bucket/'):
        logger.warning(f"Invalid results location: {results_location}")
        return []
    
    s3_uri = results_location.replace('s3://', '')
    parts = s3_uri.split('/', 1)
    bucket = parts[0]
    prefix = parts[1] if len(parts) > 1 else ''
    
    evaluation_results = []
    
    try:
        # List all result files in the output location
        response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
        
        for obj in response.get('Contents', []):
            key = obj['Key']
            if key.endswith('.jsonl') or key.endswith('.json'):
                result_response = s3_client.get_object(Bucket=bucket, Key=key)
                content = result_response['Body'].read().decode('utf-8')
                
                # Handle both JSONL and JSON formats
                if key.endswith('.jsonl'):
                    for line in content.strip().split('\n'):
                        if line:
                            evaluation_results.append(json.loads(line))
                else:
                    evaluation_results.append(json.loads(content))
        
        logger.info(f"Fetched {len(evaluation_results)} evaluation results from {results_location}")
        return evaluation_results
        
    except Exception as e:
        logger.exception(f"Error fetching evaluation results: {e}")
        return []


def compare_fields(baseline: Any, evaluation: Any) -> Dict[str, Any]:
    """Compare two field values."""
    if baseline == evaluation:
        return {'match': 'exact', 'baseline': baseline, 'evaluation': evaluation}
    
    # Try fuzzy match for strings
    if isinstance(baseline, str) and isinstance(evaluation, str):
        baseline_norm = baseline.strip().lower()
        eval_norm = evaluation.strip().lower()
        if baseline_norm == eval_norm:
            return {'match': 'fuzzy', 'baseline': baseline, 'evaluation': evaluation}
    
    return {'match': 'mismatch', 'baseline': baseline, 'evaluation': evaluation}


def compare_documents(baseline_docs: List[Dict], evaluation_docs: List[Dict]) -> Dict[str, Any]:
    """
    Compare baseline and evaluation documents field-by-field.
    
    Args:
        baseline_docs: List of baseline extraction results
        evaluation_docs: List of evaluation extraction results
    
    Returns:
        Comparison metrics
    """
    total_fields = 0
    exact_matches = 0
    fuzzy_matches = 0
    mismatches = 0
    differences = []
    
    # Create lookup dict for evaluation results
    eval_dict = {doc.get('recordId') or doc.get('document_id'): doc for doc in evaluation_docs}
    
    for baseline_doc in baseline_docs:
        doc_id = baseline_doc.get('document_id')
        eval_doc = eval_dict.get(doc_id)
        
        if not eval_doc:
            logger.warning(f"No evaluation result for document {doc_id}")
            continue
        
        # Compare extracted fields
        baseline_data = baseline_doc.get('extracted_data', {})
        eval_data = eval_doc.get('modelOutput', {}) or eval_doc.get('extracted_data', {})
        
        # Get all unique field names
        all_fields = set(baseline_data.keys()) | set(eval_data.keys())
        
        for field in all_fields:
            total_fields += 1
            baseline_value = baseline_data.get(field)
            eval_value = eval_data.get(field)
            
            comparison = compare_fields(baseline_value, eval_value)
            
            if comparison['match'] == 'exact':
                exact_matches += 1
            elif comparison['match'] == 'fuzzy':
                fuzzy_matches += 1
            else:
                mismatches += 1
                differences.append({
                    'document_id': doc_id,
                    'field': field,
                    'baseline': baseline_value,
                    'evaluation': eval_value
                })
    
    accuracy = (exact_matches + fuzzy_matches) / total_fields if total_fields > 0 else 0.0
    
    return {
        'total_fields': total_fields,
        'exact_matches': exact_matches,
        'fuzzy_matches': fuzzy_matches,
        'mismatches': mismatches,
        'accuracy': round(accuracy, 4),
        'differences': differences[:50]  # Limit to first 50 differences
    }


def calculate_classification_metrics(evaluation_docs: List[Dict]) -> Dict[str, Any]:
    """
    Calculate classification accuracy metrics.
    
    Compares:
    1. User classification vs Model classification (from production)
    2. User classification vs Evaluation model classification
    3. Production model vs Evaluation model classification
    
    Args:
        evaluation_docs: Evaluation result documents with classification data
        
    Returns:
        Classification metrics
    """
    total_docs = 0
    user_model_matches = 0
    user_eval_matches = 0
    model_eval_matches = 0
    
    user_model_available = 0
    model_eval_available = 0
    user_eval_available = 0
    
    classification_details = []
    
    for doc in evaluation_docs:
        total_docs += 1
        
        # Get metadata with classification information
        metadata = doc.get('metadata', {})
        classification_validation = metadata.get('classificationValidation', {})
        
        user_classification = classification_validation.get('userClassification')
        model_classification = classification_validation.get('modelClassification')
        
        # Get evaluation model classification
        eval_classification = doc.get('evaluationClassification', {}).get('document_type')
        
        # Normalize to uppercase for comparison
        user_norm = user_classification.upper() if user_classification else None
        model_norm = model_classification.upper() if model_classification else None
        eval_norm = eval_classification.upper() if eval_classification else None
        
        # Compare user vs production model
        if user_norm and model_norm:
            user_model_available += 1
            if user_norm == model_norm:
                user_model_matches += 1
        
        # Compare user vs evaluation model
        if user_norm and eval_norm:
            user_eval_available += 1
            if user_norm == eval_norm:
                user_eval_matches += 1
        
        # Compare production model vs evaluation model
        if model_norm and eval_norm:
            model_eval_available += 1
            if model_norm == eval_norm:
                model_eval_matches += 1
        
        # Track disagreements for analysis
        if user_norm or model_norm or eval_norm:
            all_match = (
                (not user_norm or not model_norm or user_norm == model_norm) and
                (not user_norm or not eval_norm or user_norm == eval_norm) and
                (not model_norm or not eval_norm or model_norm == eval_norm)
            )
            
            if not all_match:
                classification_details.append({
                    'document_id': doc.get('documentId'),
                    'user_classification': user_classification,
                    'model_classification': model_classification,
                    'evaluation_classification': eval_classification,
                    'user_model_match': user_norm == model_norm if (user_norm and model_norm) else None,
                    'user_eval_match': user_norm == eval_norm if (user_norm and eval_norm) else None,
                    'model_eval_match': model_norm == eval_norm if (model_norm and eval_norm) else None
                })
    
    # Calculate accuracy percentages
    user_model_accuracy = (user_model_matches / user_model_available) if user_model_available > 0 else None
    user_eval_accuracy = (user_eval_matches / user_eval_available) if user_eval_available > 0 else None
    model_eval_accuracy = (model_eval_matches / model_eval_available) if model_eval_available > 0 else None
    
    return {
        'total_documents': total_docs,
        'user_vs_production_model': {
            'available': user_model_available,
            'matches': user_model_matches,
            'accuracy': round(user_model_accuracy, 4) if user_model_accuracy is not None else None
        },
        'user_vs_evaluation_model': {
            'available': user_eval_available,
            'matches': user_eval_matches,
            'accuracy': round(user_eval_accuracy, 4) if user_eval_accuracy is not None else None
        },
        'production_vs_evaluation_model': {
            'available': model_eval_available,
            'matches': model_eval_matches,
            'accuracy': round(model_eval_accuracy, 4) if model_eval_accuracy is not None else None
        },
        'disagreements': classification_details[:20]  # Limit to first 20 disagreements
    }


def save_metrics(evaluation_id: str, metrics: Dict[str, Any], classification_metrics: Dict[str, Any], mode: str):
    """Save comparison metrics to DynamoDB."""
    if not EVALUATION_METRICS_TABLE:
        logger.warning("EVALUATION_METRICS_TABLE not set, skipping save")
        return
    
    table = dynamodb.Table(EVALUATION_METRICS_TABLE)
    
    timestamp = int(datetime.now().timestamp())
    
    # Save extraction metrics
    extraction_item = {
        'PK': f'EVALUATION#{evaluation_id}',
        'SK': f'EXTRACTION_METRICS#{timestamp}',
        'GSI1PK': 'EVALUATION',
        'GSI1SK': f'MODEL#{mode}',
        'EvaluationDate': timestamp,
        'EvaluationId': evaluation_id,
        'MetricType': 'EXTRACTION',
        'Mode': mode,
        'TotalFields': metrics['total_fields'],
        'ExactMatches': metrics['exact_matches'],
        'FuzzyMatches': metrics['fuzzy_matches'],
        'Mismatches': metrics['mismatches'],
        'Accuracy': Decimal(str(metrics['accuracy'])),
        'DifferenceCount': len(metrics['differences']),
        'CreatedAt': timestamp
    }
    
    table.put_item(Item=extraction_item)
    logger.info(f"Saved extraction metrics for evaluation {evaluation_id}")
    
    # Save classification metrics if available
    if classification_metrics.get('total_documents', 0) > 0:
        classification_item = {
            'PK': f'EVALUATION#{evaluation_id}',
            'SK': f'CLASSIFICATION_METRICS#{timestamp}',
            'GSI1PK': 'EVALUATION',
            'GSI1SK': f'CLASSIFICATION#{mode}',
            'EvaluationDate': timestamp,
            'EvaluationId': evaluation_id,
            'MetricType': 'CLASSIFICATION',
            'Mode': mode,
            'TotalDocuments': classification_metrics['total_documents'],
            'CreatedAt': timestamp
        }
        
        # Add user vs production model metrics
        if classification_metrics['user_vs_production_model']['accuracy'] is not None:
            classification_item['UserVsProductionAvailable'] = classification_metrics['user_vs_production_model']['available']
            classification_item['UserVsProductionMatches'] = classification_metrics['user_vs_production_model']['matches']
            classification_item['UserVsProductionAccuracy'] = Decimal(str(classification_metrics['user_vs_production_model']['accuracy']))
        
        # Add user vs evaluation model metrics
        if classification_metrics['user_vs_evaluation_model']['accuracy'] is not None:
            classification_item['UserVsEvaluationAvailable'] = classification_metrics['user_vs_evaluation_model']['available']
            classification_item['UserVsEvaluationMatches'] = classification_metrics['user_vs_evaluation_model']['matches']
            classification_item['UserVsEvaluationAccuracy'] = Decimal(str(classification_metrics['user_vs_evaluation_model']['accuracy']))
        
        # Add production vs evaluation model metrics
        if classification_metrics['production_vs_evaluation_model']['accuracy'] is not None:
            classification_item['ProductionVsEvaluationAvailable'] = classification_metrics['production_vs_evaluation_model']['available']
            classification_item['ProductionVsEvaluationMatches'] = classification_metrics['production_vs_evaluation_model']['matches']
            classification_item['ProductionVsEvaluationAccuracy'] = Decimal(str(classification_metrics['production_vs_evaluation_model']['accuracy']))
        
        classification_item['DisagreementCount'] = len(classification_metrics['disagreements'])
        
        table.put_item(Item=classification_item)
        logger.info(f"Saved classification metrics for evaluation {evaluation_id}")


def lambda_handler(event, context):
    """
    Compares baseline extraction results with evaluation results.
    
    Args:
        event: Contains evaluationId, mode, and resultsLocation
        context: Lambda context
        
    Returns:
        Comparison metrics and detailed differences
    """
    logger.info(f"Comparator event: {json.dumps(event)}")
    
    evaluation_id = event.get('evaluationId')
    mode = event.get('mode', 'batch')
    results_location = event.get('resultsLocation')
    
    if not evaluation_id:
        return {
            'statusCode': 400,
            'error': 'Missing evaluationId'
        }
    
    try:
        # Fetch baseline and evaluation results
        baseline_docs = get_baseline_results(evaluation_id)
        evaluation_docs = get_evaluation_results(results_location, mode)
        
        if not baseline_docs:
            logger.warning(f"No baseline results found for {evaluation_id}")
            return {
                'statusCode': 200,
                'metrics': {
                    'total_fields': 0,
                    'exact_matches': 0,
                    'fuzzy_matches': 0,
                    'mismatches': 0,
                    'accuracy': 0.0,
                    'message': 'No baseline results found'
                }
            }
        
        if not evaluation_docs:
            logger.warning(f"No evaluation results found at {results_location}")
            return {
                'statusCode': 200,
                'metrics': {
                    'total_fields': 0,
                    'exact_matches': 0,
                    'fuzzy_matches': 0,
                    'mismatches': 0,
                    'accuracy': 0.0,
                    'message': 'No evaluation results found'
                }
            }
        
        # Compare documents
        metrics = compare_documents(baseline_docs, evaluation_docs)
        
        # Calculate classification metrics
        classification_metrics = calculate_classification_metrics(evaluation_docs)
        
        # Save metrics to DynamoDB
        save_metrics(evaluation_id, metrics, classification_metrics, mode)
        
        logger.info(f"Comparison complete: {metrics['accuracy']*100:.2f}% extraction accuracy")
        logger.info(f"Classification metrics: {classification_metrics}")
        
        return {
            'statusCode': 200,
            'metrics': metrics,
            'classificationMetrics': classification_metrics
        }
        
    except Exception as e:
        logger.exception(f"Error in comparator: {e}")
        return {
            'statusCode': 500,
            'error': str(e)
        }
