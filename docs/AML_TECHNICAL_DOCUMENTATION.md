## AML Customer Due Diligence — Technical Documentation

Last updated: 2025-10-27

This document describes the technical design, components, APIs, deployment, and operational details for the AML Customer Due Diligence (CDD) system contained in this repository.

## 1. High-level overview

The system is a serverless, event-driven AML CDD pipeline implemented on AWS. Key goals:
- Automatically retrieve company and officer data (Companies House)
- Screen people and entities against sanctions and PEP lists (OpenSanctions)
- Aggregate findings and calculate an overall risk score
- Optionally enrich with adverse media analysis (NewsAPI + LLM)
- Generate professional CDD reports using Amazon Bedrock (Claude)

Primary hosting and services used:
- AWS Lambda (Python 3.12) — business logic
- DynamoDB — persistent screening and report metadata
- S3 — raw responses, reports and artifacts
- AWS Secrets Manager — API keys (Companies House, OpenSanctions, NewsAPI)
- AWS Step Functions / API Gateway (CloudFormation template included)
- Amazon Bedrock (Claude models) for LLM tasks (report generation, media analysis)

The repository includes a CloudFormation template at `infrastructure/aml-cdd-infrastructure.yaml` and Lambda source in `src/lambdas/`.

## 2. Core components and responsibilities

- Companies House Checker (src/lambdas/companies_house_checker.py)
  - Queries Companies House API for profile, officers, PSCs and filing history.
  - Implements AML heuristics: officer turnover, rapid churn (phoenixing), multiple directors at same non-company address, offshore indicators, overdue filings, no PSCs, etc.
  - Stores raw API responses to S3 and processed screening results in DynamoDB.

- Sanctions & PEP Checker (src/lambdas/sanctions_checker.py)
  - Uses OpenSanctions commercial API (bearer token) to search and fetch entity details.
  - Performs fuzzy name matching (SequenceMatcher) and dataset-aware detection (OFAC, HMT, EU, UN, etc.).
  - Distinguishes current vs former PEP, produces flags and risk contribution values, stores raw data in S3 and results in DynamoDB.

- Adverse Media / Media Checker (src/lambdas/media_checker.py)
  - Phase 1: NewsAPI keyword filtering for negative keywords.
  - Phase 2: (optional) LLM analysis using Bedrock/Claude to validate whether articles constitute AML red flags.
  - Stores raw article lists in S3 and results in DynamoDB.

- Risk Aggregator (src/lambdas/risk_aggregator.py)
  - Pulls Companies House results and sanctions results from DynamoDB.
  - Extracts active directors and triggers sanctions screening for each director (Lambda-to-Lambda invocation).
  - Aggregates flags and computes a weighted overall risk score and risk level (LOW / MEDIUM / HIGH).
  - Stores aggregated results in DynamoDB.

- Report Generator (src/lambdas/report_generator.py)
  - Collects screening data and constructs a structured prompt for the LLM.
  - Calls Amazon Bedrock (Claude 3.7 Sonnet by default) to generate a professional AML CDD report (Markdown).
  - Stores reports (Markdown) in S3 and metadata in DynamoDB.

- API / Frontend
  - The repo contains a simple static frontend in `frontend/` that calls Lambda Function URLs directly.
  - The CloudFormation template also defines an API Gateway / Step Functions integration for a screening endpoint.

## 3. Infrastructure (CloudFormation summary)

Location: `infrastructure/aml-cdd-infrastructure.yaml`

Notable resources defined:
- S3 bucket `AMLDataBucket` with versioning and lifecycle rules.
- DynamoDB tables: `EntitiesTable`, `ScreeningResultsTable`, `ReportsTable` (PAY_PER_REQUEST + PointInTimeRecovery).
- IAM roles: `LambdaExecutionRole` (allows S3, DynamoDB, SecretsManager, StepFunctions, Lambda invoke and Bedrock access for specified model ARNs), `StepFunctionRole` and `ApiGatewayStepFunctionRole`.
- Lambda functions (placeholders in the YAML; real code is deployed separately): CompaniesHouse, Sanctions, Media, RiskAggregator, ReportGenerator.
- Step Functions state machine `AMLStepFunction` which runs Companies House, Sanctions and Media checks in parallel, then RiskAggregation, then GenerateReport.
- API Gateway REST API `AMLRestApi` and a `/screening` POST method which can start a Step Functions execution.

The template exports the S3 bucket name, DynamoDB table names, API URL and Step Function ARN.

## 4. Environment variables & secrets

Environment variables used by Lambdas (examples seen in code and template):
- S3_DATA_BUCKET — S3 bucket for raw data and reports
- DYNAMODB_SCREENING_TABLE, DYNAMODB_ENTITIES_TABLE, DYNAMODB_REPORTS_TABLE — DynamoDB tables
- SANCTIONS_LAMBDA_NAME — name used when the Risk Aggregator invokes the sanctions lambda
- STATE_MACHINE_ARN — Step Functions ARN used by API handler
- POWERTOOLS_SERVICE_NAME / POWERTOOLS_METRICS_NAMESPACE — AWS Lambda Powertools settings

Secrets stored in Secrets Manager (expected keys):
- taxguard/companies-house/api-key — Companies House API key (Basic auth)
- taxguard/opensanctions/api-key — OpenSanctions API key (Bearer)
- taxguard/newsapi/api-key — NewsAPI key (for media checker)

Access pattern: code retrieves secrets via boto3 Secrets Manager client. A fallback to environment variables is implemented for local dev.

## 5. APIs, inputs and outputs (contract)

All Lambdas accept and return JSON. Below are the primary inputs and outputs (canonical shapes found in the code):

- Companies House Lambda (handler: companies_house_checker.lambda_handler)
  - Input (required): { entity_id, company_name?, company_number? }
  - Behavior: if company_number absent, performs search; fetches profile, officers, PSCs, filing history; runs AML heuristics
  - Output: statusCode 200, body JSON with { entity_id, source: 'companies_house', company_data, flags, risk_contribution, raw_data }
  - Stores processed result to ScreeningResultsTable and raw data to S3

- Sanctions Lambda (handler: sanctions_checker.lambda_handler)
  - Input: { entity_id, entity_name, entity_type, date_of_birth? }
  - Output: statusCode 200, body JSON with fields: entity_id, source: 'sanctions_pep', matches, sanctions_matches, pep_matches, flags, risk_contribution
  - Persists raw + processed results (S3 + DynamoDB)

- Media Lambda (handler: media_checker.lambda_handler)
  - Input: { entity_id, entity_name, entity_type, directors? }
  - Phases: keyword filter with NewsAPI, optional LLM analysis
  - Output: statusCode 200, body JSON with adverse_media assessment, flags and risk_contribution

- Risk Aggregator Lambda (handler: risk_aggregator.lambda_handler)
  - Input: { entity_id, screen_directors?: true }
  - Behavior: collects CH results, extracts directors, invokes sanctions checker for each director, retrieves media results, computes aggregate risk score and risk_level
  - Output: statusCode 200, body JSON with { entity_id, overall_risk_score, risk_level, flags_summary, summary, directors_screened }
  - Stores aggregated result to DynamoDB

- Report Generator Lambda (handler: report_generator.lambda_handler)
  - Input: { entity_id }
  - Behavior: retrieves all screening records for entity_id, prepares context, calls Bedrock (Claude) to produce Markdown report, stores it in S3 + metadata table
  - Output: statusCode 200, body JSON with { entity_id, report_id, company_name, risk_level, report_markdown, tokens_used }

## 6. Data flow (end-to-end)

1. User triggers screening via frontend or API.
2. Companies House Lambda runs and writes a `companies_house` record to `ScreeningResultsTable` and raw data to S3.
3. Step Functions (or orchestrator) triggers Sanctions and Media checks in parallel for the same entity_id; each writes `sanctions_pep` and `adverse_media` records to the same table.
4. Risk Aggregator reads those records, extracts directors, invokes Sanctions Lambda for each director (isolated screening), computes an aggregated weighted score and risk level and writes a `risk_aggregation` record.
5. Report Generator assembles all data and calls Bedrock to create a final professional report saved in S3 and referenced in `ReportsTable`.

## 7. Scoring and risk model

Implemented weights (see `risk_aggregator.py` and `sanctions_checker.py`):
- sanctions_match: 0.95 (critical)
- current_pep: 0.70 (high)
- former_pep: 0.40 (medium)
- adverse_media: 0.60
- companies_house high severity: 0.50
- companies_house medium severity: 0.30
- companies_house low severity: 0.10

Risk level rules (simplified):
- Any critical flag -> HIGH
- score >= 0.7 or >=2 high flags -> HIGH
- score >= 0.4 -> MEDIUM
- otherwise -> LOW

These are implemented in `RiskAggregator._determine_risk_level`.

## 8. LLM usage (Bedrock / Claude)

- Models: code uses `anthropic.claude-3-7-sonnet-20250219-v1:0` by default for report generation and media analysis. Region is set to `eu-west-2` in code examples.
- Prompts: `report_generator.py` builds a long structured prompt including executive summary instructions tuned for UK accountants and MLR 2017 context.
- Safety & cost: ReportGenerator uses low temperature (0.3) to produce consistent professional text; token usage is recorded in metrics.

## 9. Deployment and runbook

Prerequisites:
- AWS CLI configured with a user that can deploy CloudFormation, manage Lambda, S3, DynamoDB and Secrets Manager
- Python 3.12 for local tests
- Required secrets stored in Secrets Manager (Companies House, OpenSanctions, NewsAPI keys)

Recommended quick flow (from repo root):
1. Create secrets in Secrets Manager (see README examples).
2. Deploy CloudFormation stack:
   - `./infrastructure/deploy-yaml.sh` (wraps aws cloudformation create/update)
3. Deploy Lambda code (scripts provided):
   - `./infrastructure/deploy-single-lambda.sh companies-house-checker`
   - `./infrastructure/deploy-single-lambda.sh sanctions-checker`
   - `./infrastructure/deploy-single-lambda.sh risk-aggregator`
   - `./infrastructure/deploy-single-lambda.sh report-generator`
4. Test functions via AWS CLI or the frontend (function URLs are used by the frontend; API Gateway + Step Functions are also wired in the template).

Quick CLI test examples (from README):
```
# Start Companies House check
aws lambda invoke --function-name aml-companies-house-checker-dev --payload '{"entity_id":"demo_001","company_name":"Tesco PLC"}' response.json

# Run risk aggregation (screens directors)
aws lambda invoke --function-name aml-risk-aggregator-dev --payload '{"entity_id":"demo_001","screen_directors":true}' response.json
```

## 10. Observability and operational notes

- Logging: Lambdas use AWS Lambda Powertools logger; logs appear in CloudWatch.
- Metrics: Powertools metrics are emitted: function counts, matches, tokens, risk score.
- Tracing: AWS X-Ray is used via Powertools Tracer decorators.
- Data retention: S3 lifecycle rules in the CloudFormation template move objects to STANDARD_IA and GLACIER after 30/90 days.

## 11. Security considerations

- Secrets are stored in AWS Secrets Manager; code retrieves them at runtime.
- IAM roles are scoped for each Lambda (see template). LambdaExecutionRole grants access to S3 prefix, DynamoDB tables, Secrets Manager, Step Functions, Lambda invoke and Bedrock model ARNs.
- DynamoDB and S3 are used with encryption at rest.
- No API keys in source code.

## 12. Testing and verification

Unit / local tests: repository contains test scripts (e.g., `test_companies_house.py`, `test_sanctions.py`). These are small integration checks and example payloads.

Integration test suggestions:
- Deploy to a `dev` environment, populate secrets, run a Companies House check for a well-known company (e.g., Tesco) and verify: companies_house record stored, directors extracted, sanctions checks for each director, aggregated risk stored.
- Test sanctions with a known sanctioned individual (e.g., a public sanctions name used during testing) to verify critical flags.
- Test Report Generator with an entity that has companies_house + risk aggregation records to verify Bedrock invocation and report storage.

## 13. Known gaps & next steps

- Adverse media module (media_checker.py) is implemented but may require API quota and production tuning.
- PDF generation and automated emailing of reports are not implemented (future enhancements).
- API authentication for the frontend / API Gateway is not configured (Cognito or other auth to be added before production usage).
- Bedrock model access must be requested and Bedrock IAM tightened for production.

## 14. Files of interest (repository)

- `infrastructure/aml-cdd-infrastructure.yaml` — CloudFormation template that provisions S3, DynamoDB, Lambdas placeholders, Step Functions, API Gateway and IAM roles.
- `src/lambdas/companies_house_checker.py` — Companies House integration and AML heuristics.
- `src/lambdas/sanctions_checker.py` — OpenSanctions integration and PEP detection.
- `src/lambdas/risk_aggregator.py` — Director screening orchestration and risk scoring.
- `src/lambdas/media_checker.py` — NewsAPI + LLM adverse media analysis.
- `src/lambdas/report_generator.py` — Report assembly and Bedrock invocation.
- `frontend/index.html` — Static frontend that invokes Lambda Function URLs.

## 15. Contact / Ownership

Repository owner (git remote): see repo metadata. For questions about production deployment and security, contact the repository maintainer and the cloud infra owner.

---

If you want, I can:
- add an architecture diagram image file in the repo,
- expand the API Gateway / Step Functions details into a dedicated section, or
- produce a short operational runbook script that runs a full demo end-to-end and validates outputs.

Done: initial technical documentation added as `TECHNICAL_DOCUMENTATION.md`.
