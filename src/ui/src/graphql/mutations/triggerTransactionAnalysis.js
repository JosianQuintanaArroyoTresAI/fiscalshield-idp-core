// GraphQL mutation for triggering transaction analysis workflow
export const TRIGGER_TRANSACTION_ANALYSIS = `
  mutation TriggerTransactionAnalysis($companyNumber: String!) {
    triggerTransactionAnalysis(companyNumber: $companyNumber) {
      success
      message
      executionArn
      executionName
    }
  }
`;
