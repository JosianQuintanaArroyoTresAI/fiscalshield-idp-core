// GraphQL mutation for triggering invoice analysis workflow
export const TRIGGER_INVOICE_ANALYSIS = `
  mutation TriggerInvoiceAnalysis($companyNumber: String!, $userId: String!) {
    triggerInvoiceAnalysis(companyNumber: $companyNumber, userId: $userId) {
      success
      message
      executionArn
      executionName
    }
  }
`;
