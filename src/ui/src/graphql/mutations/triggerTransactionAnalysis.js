// GraphQL mutation for triggering transaction analysis workflow
export const TRIGGER_TRANSACTION_ANALYSIS = `
  mutation TriggerTransactionAnalysis($companyNumber: String!, $userId: String!) {
    triggerTransactionAnalysis(companyNumber: $companyNumber, userId: $userId) {
      success
      message
      executionArn
      executionName
    }
  }
`;
