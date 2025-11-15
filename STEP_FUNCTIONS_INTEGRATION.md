# Step Functions Integration - Next Steps

## Overview
We've successfully refactored the transaction categorization system from SQS-based to Step Functions orchestration for better visibility, error handling, and production-grade workflow management.

## ✅ Completed Steps

### 1. Analysis Stack Refactoring
- **Trigger Lambda** (`stacks/analysis/lambdas/trigger_analysis/handler.py`):
  - ✅ Removed SQS dependency
  - ✅ Returns batches array instead of queuing to SQS
  - ✅ Simplified for Step Functions invocation

- **Categorization Lambda** (`stacks/analysis/lambdas/categorization/handler.py`):
  - ✅ Removed SQS event source mapping
  - ✅ Updated to receive batch data directly from Step Functions
  - ✅ Returns structured result for workflow tracking

- **Step Functions State Machine** (`stacks/analysis/statemachines/transaction-categorization.asl.json`):
  - ✅ Created workflow with Map state for parallel batch processing
  - ✅ Added retry logic with exponential backoff for Bedrock throttling
  - ✅ Configured MaxConcurrency=5 to prevent overwhelming Bedrock
  - ✅ Added error handling with Catch clauses
  - ✅ Structured for progress visibility

- **Template Updates** (`stacks/analysis/template.yaml`):
  - ✅ Added `AWS::Serverless::StateMachine` resource
  - ✅ Created `StepFunctionsExecutionRole` with Lambda invoke permissions
  - ✅ Added CloudWatch Logs group for execution logging
  - ✅ Removed SQS event source from Categorization Lambda
  - ✅ Removed SQS IAM policies (no longer needed)
  - ✅ Added State Machine ARN to outputs

- **Deployment Script** (`stacks/analysis/deploy-analysis-dev.sh`):
  - ✅ Updated to display State Machine ARN
  - ✅ Added Step Functions testing commands

### 2. GraphQL Resolver Created
- **Resolver Lambda** (`src/resolvers/triggerTransactionAnalysis/index.py`):
  - ✅ Created Lambda to start Step Functions execution
  - ✅ Extracts `companyNumber` and `userId` from GraphQL mutation
  - ✅ Returns `executionArn` for status polling
  - ✅ Handles duplicate execution attempts

## 🔄 Next Steps

### Step 1: Deploy Analysis Stack
```bash
cd stacks/analysis
chmod +x deploy-analysis-dev.sh
./deploy-analysis-dev.sh
```

**Expected Outputs:**
- State Machine ARN: `arn:aws:states:eu-central-1:...:stateMachine:fiscalshield-analysis-dev-TransactionCategorization`
- API Gateway URL
- SSM Parameter name

**Copy the State Machine ARN** - you'll need it for the next step.

---

### Step 2: Add GraphQL Resolver to IDP Core Stack

Add the following resources to `/home/josian/git/fiscalshield-idp-core/template.yaml`:

#### 2a. Add Lambda Function (around line 4150, after other resolver functions)

```yaml
  TriggerTransactionAnalysisFunction:
    Type: AWS::Serverless::Function
    Properties:
      PermissionsBoundary:
        !If [
          HasPermissionsBoundary,
          !Ref PermissionsBoundaryArn,
          !Ref AWS::NoValue,
        ]
      CodeUri: src/resolvers/triggerTransactionAnalysis/
      Handler: index.lambda_handler
      Runtime: python3.12
      Timeout: 30
      Environment:
        Variables:
          STATE_MACHINE_ARN: <PASTE_STATE_MACHINE_ARN_HERE>
          LOG_LEVEL: !Ref LogLevel
      Policies:
        - Version: "2012-10-17"
          Statement:
            - Effect: Allow
              Action:
                - states:StartExecution
                - states:ListExecutions
              Resource:
                - <PASTE_STATE_MACHINE_ARN_HERE>
      LoggingConfig:
        LogGroup: !Ref TriggerTransactionAnalysisLogGroup

  TriggerTransactionAnalysisLogGroup:
    Type: AWS::Logs::LogGroup
    Properties:
      KmsKeyId: !GetAtt CustomerManagedEncryptionKey.Arn
      RetentionInDays: !Ref LogRetentionDays
```

#### 2b. Add AppSync Data Source (around line 4420, after other data sources)

```yaml
  TriggerTransactionAnalysisDataSource:
    Type: AWS::AppSync::DataSource
    Properties:
      ApiId: !GetAtt GraphQLApi.ApiId
      Name: TriggerTransactionAnalysisDataSource
      Type: AWS_LAMBDA
      ServiceRoleArn: !GetAtt AppSyncServiceRole.Arn
      LambdaConfig:
        LambdaFunctionArn: !GetAtt TriggerTransactionAnalysisFunction.Arn
```

#### 2c. Add AppSync Resolver (around line 4440, after other resolvers)

```yaml
  TriggerTransactionAnalysisResolver:
    Type: AWS::AppSync::Resolver
    Properties:
      ApiId: !GetAtt GraphQLApi.ApiId
      TypeName: Mutation
      FieldName: triggerTransactionAnalysis
      DataSourceName: !GetAtt TriggerTransactionAnalysisDataSource.Name
```

---

### Step 3: Update Frontend Button Implementation

Update `/home/josian/git/fiscalshield-idp-core/src/ui/src/components/document-list/DocumentList.jsx`:

#### 3a. Add mutation import at top of file:
```javascript
import { TRIGGER_TRANSACTION_ANALYSIS } from '../../graphql/mutations/triggerTransactionAnalysis';
```

#### 3b. Create mutation file:
Create `/home/josian/git/fiscalshield-idp-core/src/ui/src/graphql/mutations/triggerTransactionAnalysis.js`:

```javascript
import { gql } from '@apollo/client';

export const TRIGGER_TRANSACTION_ANALYSIS = gql`
  mutation TriggerTransactionAnalysis($companyNumber: String!) {
    triggerTransactionAnalysis(companyNumber: $companyNumber) {
      success
      message
      executionArn
      executionName
    }
  }
`;
```

#### 3c. Wire button to mutation:

Replace the `handleAnalyseClick` function in `DocumentList.jsx`:

```javascript
const [triggerAnalysis, { loading: analysisLoading }] = useMutation(
  TRIGGER_TRANSACTION_ANALYSIS,
  {
    onCompleted: (data) => {
      if (data.triggerTransactionAnalysis.success) {
        setSnackbarMessage(data.triggerTransactionAnalysis.message);
        setSnackbarSeverity('success');
        setSnackbarOpen(true);
        
        // Optional: Poll for execution status
        console.log('Execution ARN:', data.triggerTransactionAnalysis.executionArn);
        
        // Refresh list to show IN_PROGRESS status
        setTimeout(() => {
          onRefresh?.();
        }, 2000);
      } else {
        setSnackbarMessage(data.triggerTransactionAnalysis.message);
        setSnackbarSeverity('error');
        setSnackbarOpen(true);
      }
    },
    onError: (error) => {
      setSnackbarMessage(`Failed to start analysis: ${error.message}`);
      setSnackbarSeverity('error');
      setSnackbarOpen(true);
    },
  }
);

const handleAnalyseClick = () => {
  if (selectedCompany) {
    triggerAnalysis({
      variables: {
        companyNumber: selectedCompany.companyNumber,
      },
    });
  }
};
```

Update the button to show loading state:
```javascript
<Button
  variant="primary"
  onClick={handleAnalyseClick}
  disabled={pendingCount === 0 || analysisLoading}
  loading={analysisLoading}
>
  {analysisLoading ? 'Starting Analysis...' : `Analyse Transactions (${pendingCount})`}
</Button>
```

---

### Step 4: Deploy IDP Core Stack

```bash
cd /home/josian/git/fiscalshield-idp-core
sam build
sam deploy \
  --stack-name genaiic-dev \
  --region eu-central-1 \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --no-confirm-changeset \
  --resolve-s3
```

---

### Step 5: Test End-to-End Workflow

#### 5a. Upload a bank statement
Use the frontend to upload a bank statement with transactions.

#### 5b. Verify transactions marked as PENDING
Check DynamoDB table or frontend to confirm `AnalysisStatus='PENDING'`.

#### 5c. Click "Analyse Transactions" button
- Should start Step Functions execution
- Button should show loading state
- Success message should appear

#### 5d. Monitor Step Functions execution
```bash
# Get execution ARN from frontend console or:
STATE_MACHINE_ARN="<paste-arn-here>"

# List recent executions
aws stepfunctions list-executions \
  --state-machine-arn "$STATE_MACHINE_ARN" \
  --max-results 5

# Describe specific execution
EXECUTION_ARN="<paste-execution-arn-here>"
aws stepfunctions describe-execution \
  --execution-arn "$EXECUTION_ARN"

# View execution history
aws stepfunctions get-execution-history \
  --execution-arn "$EXECUTION_ARN" \
  --max-results 50
```

#### 5e. Check CloudWatch Logs
```bash
# Trigger Lambda logs
aws logs tail /aws/lambda/fiscalshield-analysis-dev-TriggerAnalysis --follow

# Categorization Lambda logs
aws logs tail /aws/lambda/fiscalshield-analysis-dev-Categorization --follow

# Step Functions execution logs
aws logs tail /aws/stepfunctions/fiscalshield-analysis-dev-TransactionCategorization --follow
```

#### 5f. Verify DynamoDB updates
After execution completes, check transactions have:
- `AnalysisStatus='ANALYZED'`
- `Category` field populated
- `LegitimacyScore` (1-5)
- `RiskFlags` array
- `CategoryRationale`
- `UpdatedAt` timestamp

---

## Architecture Benefits

### Before (SQS-based):
- ❌ Limited visibility into batch processing progress
- ❌ Difficult to track individual transaction failures
- ❌ No built-in retry logic
- ❌ Hard to show progress to users

### After (Step Functions):
- ✅ Full execution history and traceability
- ✅ Visual workflow in AWS Console
- ✅ Built-in retry with exponential backoff
- ✅ Throttling control via MaxConcurrency
- ✅ Can poll execution status for progress bars
- ✅ CloudWatch Logs integration
- ✅ Error handling with Catch clauses
- ✅ Production-ready orchestration

---

## Workflow Flow

1. **User clicks "Analyse Transactions" button**
   - Frontend calls GraphQL mutation `triggerTransactionAnalysis`
   - Passes `companyNumber` (automatically gets `userId` from Cognito)

2. **GraphQL resolver Lambda starts execution**
   - Calls `stepfunctions.start_execution()`
   - Returns `executionArn` to frontend

3. **Step Functions workflow begins**
   - **State: TriggerAnalysis** - Query pending transactions, prepare batches
   - **State: CheckBatchesExist** - Verify batches were created
   - **State: ProcessBatches (Map)** - Process batches in parallel (MaxConcurrency=5)
     - For each batch: **CategorizeBatch** - Call Claude via Bedrock
     - Retries on throttling with exponential backoff
   - **State: AggregateResults** - Combine batch results
   - **State: AnalysisComplete** - Success

4. **Transactions updated in DynamoDB**
   - Status: PENDING → IN_PROGRESS → ANALYZED
   - Analysis fields populated
   - Frontend refreshes to show results

---

## Troubleshooting

### Issue: State Machine ARN not found
**Solution:** Deploy Analysis stack first (`./deploy-analysis-dev.sh`)

### Issue: Execution fails immediately
**Solution:** Check CloudWatch Logs for Trigger Lambda errors

### Issue: Batches fail with ThrottlingException
**Solution:** Reduce `MaxConcurrency` in state machine definition (currently 5)

### Issue: Frontend button doesn't respond
**Solution:** 
- Check browser console for GraphQL errors
- Verify mutation is defined in schema
- Ensure resolver is attached to mutation

### Issue: Transactions stuck in IN_PROGRESS
**Solution:**
- Check Step Functions execution status in AWS Console
- Review Categorization Lambda logs
- Verify Bedrock permissions and model availability

---

## Cost Optimization

- **Step Functions**: ~$0.025 per 1,000 state transitions
  - Example: 100 transactions = 7 batches = ~15 transitions = $0.0004
- **Lambda**: Pay per invocation + duration
- **Bedrock**: Pay per token (existing cost, unchanged)
- **CloudWatch Logs**: Standard pricing

**Total additional cost:** ~$0.01 per 1,000 transactions

---

## Future Enhancements

1. **Progress Polling**: Frontend polls execution status for real-time progress bar
2. **Execution History UI**: Show past analysis runs with results
3. **Partial Failure Handling**: Re-run only failed batches
4. **Batch Size Tuning**: Adjust based on Bedrock performance
5. **Execution Notifications**: SNS alerts on completion/failure
6. **Metrics Dashboard**: CloudWatch dashboard for workflow metrics

---

## File Locations

### Analysis Stack (Already Updated)
- `/stacks/analysis/lambdas/trigger_analysis/handler.py`
- `/stacks/analysis/lambdas/categorization/handler.py`
- `/stacks/analysis/statemachines/transaction-categorization.asl.json`
- `/stacks/analysis/template.yaml`
- `/stacks/analysis/deploy-analysis-dev.sh`

### IDP Core Stack (Need Updates - Step 2)
- `/template.yaml` - Add Lambda function, data source, resolver
- `/src/resolvers/triggerTransactionAnalysis/index.py` - Already created ✅

### Frontend (Need Updates - Step 3)
- `/src/ui/src/graphql/mutations/triggerTransactionAnalysis.js` - Need to create
- `/src/ui/src/components/document-list/DocumentList.jsx` - Need to update

---

## Summary

The Step Functions refactoring is **complete on the Analysis stack side**. The next immediate action is:

**⏭️ Deploy the Analysis stack to get the State Machine ARN, then wire the GraphQL mutation in the IDP Core stack.**

This gives you production-grade orchestration with full visibility, retry logic, and throttling control - essential for LLM workflows at scale.
