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
