"""Fixtures for ListExtractionResults Lambda tests."""
import pytest
import sys
from pathlib import Path
from decimal import Decimal

# Add lambda to path
LAMBDA_DIR = Path(__file__).parent.parent.parent.parent.parent / 'src' / 'lambda' / 'list_extraction_results'
sys.path.insert(0, str(LAMBDA_DIR))


@pytest.fixture
def valid_appsync_event():
    """Valid AppSync event for listExtractionResults query."""
    return {
        "arguments": {
            "companyNumber": "15944206",
            "documentType": "INVOICE",
            "limit": 50,
            "nextToken": None
        },
        "identity": {
            "sub": "23b4b872-20a1-709e-ffef-d20a604f60b5",
            "username": "josian@protonmail.com",
            "claims": {
                "sub": "23b4b872-20a1-709e-ffef-d20a604f60b5",
                "cognito:groups": ["Admin"]
            }
        },
        "info": {
            "fieldName": "listExtractionResults",
            "parentTypeName": "Query"
        }
    }


@pytest.fixture
def mock_gsi_response():
    """Mock DynamoDB GSI query response with limited projection."""
    return {
        "Items": [
            {
                "PK": "user#23b4b872-20a1-709e-ffef-d20a604f60b5#doc#users/23b4b872-20a1-709e-ffef-d20a604f60b5/invoice28.pdf",
                "SK": "type#INVOICE#section#1#invoice#1",
                "GSI6PK": "client#15944206#type#INVOICE",
                "UserId": "23b4b872-20a1-709e-ffef-d20a604f60b5",
                "DocumentId": "users/23b4b872-20a1-709e-ffef-d20a604f60b5/invoice28.pdf",
                "CompanyName": "TRESAI LIMITED",
                "TotalAmount": Decimal("18"),
                "ProcessedAt": Decimal("1762966408"),
                "ExtractionStatus": "COMPLETED"
                # Note: DocumentType missing due to GSI projection limitation
            },
            {
                "PK": "user#23b4b872-20a1-709e-ffef-d20a604f60b5#doc#users/23b4b872-20a1-709e-ffef-d20a604f60b5/invoice27.pdf",
                "SK": "type#INVOICE#section#1#invoice#1",
                "GSI6PK": "client#15944206#type#INVOICE",
                "UserId": "23b4b872-20a1-709e-ffef-d20a604f60b5",
                "DocumentId": "users/23b4b872-20a1-709e-ffef-d20a604f60b5/invoice27.pdf",
                "CompanyName": "TRESAI LIMITED",
                "TotalAmount": Decimal("18"),
                "ProcessedAt": Decimal("1762966408"),
                "ExtractionStatus": "COMPLETED"
            }
        ],
        "Count": 2,
        "ScannedCount": 2
    }


@pytest.fixture
def mock_batch_get_response():
    """Mock DynamoDB batch_get_item response with full items."""
    return {
        "Responses": {
            "ExtractionResultsTable": [
                {
                    "PK": "user#23b4b872-20a1-709e-ffef-d20a604f60b5#doc#users/23b4b872-20a1-709e-ffef-d20a604f60b5/invoice28.pdf",
                    "SK": "type#INVOICE#section#1#invoice#1",
                    "GSI6PK": "client#15944206#type#INVOICE",
                    "UserId": "23b4b872-20a1-709e-ffef-d20a604f60b5",
                    "DocumentId": "users/23b4b872-20a1-709e-ffef-d20a604f60b5/invoice28.pdf",
                    "DocumentType": "INVOICE",  # ← This field is now present
                    "CompanyNumber": "15944206",
                    "CompanyName": "TRESAI LIMITED",
                    "VendorName": "Anthropic, PBC",
                    "SupplierAddress": "548 Market Street PMB 90375, San Francisco, California 94104, United States",
                    "InvoiceNumber": "BBE642FB-0011",
                    "InvoiceDate": "2025-09-29",
                    "DueDate": "2025-09-29",
                    "TotalAmount": Decimal("18"),
                    "Currency": "GBP",
                    "ProcessedAt": Decimal("1762966408"),
                    "ExtractionStatus": "COMPLETED",
                    "ConfidenceScore": Decimal("0.975"),
                    "CompositeConfidence": Decimal("0.975"),
                    "QualityTier": "EXCELLENT",
                    "HITLRequired": False,
                    "HITLReason": ""
                },
                {
                    "PK": "user#23b4b872-20a1-709e-ffef-d20a604f60b5#doc#users/23b4b872-20a1-709e-ffef-d20a604f60b5/invoice27.pdf",
                    "SK": "type#INVOICE#section#1#invoice#1",
                    "GSI6PK": "client#15944206#type#INVOICE",
                    "UserId": "23b4b872-20a1-709e-ffef-d20a604f60b5",
                    "DocumentId": "users/23b4b872-20a1-709e-ffef-d20a604f60b5/invoice27.pdf",
                    "DocumentType": "INVOICE",
                    "CompanyNumber": "15944206",
                    "CompanyName": "TRESAI LIMITED",
                    "VendorName": "Anthropic, PBC",
                    "SupplierAddress": "548 Market Street PMB 90375, San Francisco, California 94104, United States",
                    "InvoiceNumber": "BBE642FB-0011",
                    "InvoiceDate": "2025-09-29",
                    "DueDate": "2025-09-29",
                    "TotalAmount": Decimal("18"),
                    "Currency": "GBP",
                    "ProcessedAt": Decimal("1762966408"),
                    "ExtractionStatus": "COMPLETED",
                    "ConfidenceScore": Decimal("0.975"),
                    "CompositeConfidence": Decimal("0.975"),
                    "QualityTier": "EXCELLENT",
                    "HITLRequired": False,
                    "HITLReason": ""
                }
            ]
        }
    }
