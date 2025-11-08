// Document Service for secure document viewing via S3 presigned URLs
// Adapted for FiscalShield IDP Production Environment
import { API, Auth } from 'aws-amplify';

// API name will be dynamically configured from environment
// For production, this should match the API Gateway name from your deployment
const getApiName = () => {
  // TODO: Update this based on your actual API Gateway configuration
  // This should match the API name in your Amplify configuration
  return 'InvoiceAPI'; // Update when API is deployed
};

class DocumentService {
  /**
   * Get a secure pre-signed URL to view a document
   * @param {string} documentId - The document ID to view
   * @param {string} companyName - The company name (e.g., "TESCO PLC") - REQUIRED
   * @returns {Promise<Object>} Response with view_url and document info
   */
  async getDocumentViewUrl(documentId, companyName) {
    try {
      // Validate required parameters
      if (!documentId) {
        throw new Error('Document ID is required');
      }
      if (!companyName) {
        throw new Error('Company name is required');
      }

      // Get current user session for authorization
      const session = await Auth.currentSession();
      const token = session.getIdToken().getJwtToken();

      console.log(`Fetching view URL for document: ${documentId} for company: ${companyName}`);

      // Call API endpoint with company_name as query parameter
      const response = await API.get(getApiName(), `/documents/${documentId}/view`, {
        queryStringParameters: {
          company_name: companyName
        },
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      console.log('Document view URL response:', response);

      // Handle both direct response and wrapped response
      const data = response.body ? JSON.parse(response.body) : response;

      if (!data.success) {
        throw new Error(data.error || 'Failed to get document view URL');
      }

      return {
        success: true,
        viewUrl: data.view_url,
        documentId: data.document_id,
        filename: data.original_filename,
        expiresAt: data.expires_at
      };

    } catch (error) {
      console.error('Error getting document view URL:', error);
      
      // Handle different error types
      if (error.response?.status === 403) {
        throw new Error('Access denied: You do not have permission to view this document');
      } else if (error.response?.status === 404) {
        throw new Error('Document not found');
      } else if (error.response?.status === 410) {
        throw new Error('Document file no longer available');
      } else if (error.response?.status === 400) {
        throw new Error(error.response?.data?.error || 'Invalid request - company name may be missing');
      } else {
        throw new Error(error.message || 'Failed to access document');
      }
    }
  }

  /**
   * Get a secure pre-signed URL to view a financial record (shows correct page)
   * @param {string} financialRecordId - The financial record ID to view
   * @param {string} companyName - The company name (e.g., "TESCO PLC") - REQUIRED
   * @returns {Promise<Object>} Response with view_url and document info
   */
  async getFinancialRecordViewUrl(financialRecordId, companyName) {
    try {
      // Validate required parameters
      if (!financialRecordId) {
        throw new Error('Financial Record ID is required');
      }
      if (!companyName) {
        throw new Error('Company name is required');
      }

      // Get current user session for authorization
      const session = await Auth.currentSession();
      const token = session.getIdToken().getJwtToken();

      console.log(`Fetching view URL for financial record: ${financialRecordId} for company: ${companyName}`);

      // Call financial records API endpoint
      const response = await API.get(getApiName(), `/financial-records/${financialRecordId}/view`, {
        queryStringParameters: {
          company_name: companyName
        },
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      console.log('Financial record view URL response:', response);

      // Handle both direct response and wrapped response
      const data = response.body ? JSON.parse(response.body) : response;

      if (!data.success) {
        throw new Error(data.error || 'Failed to get financial record view URL');
      }

      return {
        success: true,
        viewUrl: data.view_url,
        documentId: data.document_id,
        pageNumber: data.page_number,
        financialRecordId: data.financial_record_id,
        filename: data.original_filename,
        expiresAt: data.expires_at
      };

    } catch (error) {
      console.error('Error getting financial record view URL:', error);
      
      // Handle different error types
      if (error.response?.status === 403) {
        throw new Error('Access denied: You do not have permission to view this financial record');
      } else if (error.response?.status === 404) {
        throw new Error('Financial record or document not found');
      } else if (error.response?.status === 410) {
        throw new Error('Document file no longer available');
      } else if (error.response?.status === 400) {
        throw new Error(error.response?.data?.error || 'Invalid request - company name may be missing');
      } else {
        throw new Error(error.message || 'Failed to access financial record');
      }
    }
  }

  /**
   * Open document in a new tab/window
   * @param {string} documentId - The document ID to view
   * @param {string} companyName - The company name (e.g., "TESCO PLC") - REQUIRED
   * @param {string} filename - Optional filename for better UX
   */
  async viewDocumentInNewTab(documentId, companyName, filename = 'document.pdf') {
    try {
      if (!companyName) {
        throw new Error('Company name is required');
      }

      const result = await this.getDocumentViewUrl(documentId, companyName);
      
      // Open in new tab with meaningful title
      const newWindow = window.open(result.viewUrl, '_blank');
      
      if (!newWindow) {
        // Popup blocked - fallback to direct download
        console.warn('Popup blocked, triggering download instead');
        this.downloadDocument(documentId, companyName, filename);
      } else {
        // Try to set a meaningful title (may not work due to CORS)
        try {
          newWindow.document.title = filename;
        } catch (e) {
          // Ignore - cross-origin restrictions
        }
      }

      return result;
    } catch (error) {
      console.error('Error opening document:', error);
      throw error;
    }
  }

  /**
   * Open financial record in a new tab/window (shows correct page)
   * @param {string} financialRecordId - The financial record ID to view
   * @param {string} companyName - The company name (e.g., "TESCO PLC") - REQUIRED
   * @param {string} filename - Optional filename for better UX
   */
  async viewFinancialRecordInNewTab(financialRecordId, companyName, filename = 'document.pdf') {
    try {
      if (!companyName) {
        throw new Error('Company name is required');
      }

      const result = await this.getFinancialRecordViewUrl(financialRecordId, companyName);
      
      console.log(`Opening financial record ${financialRecordId} at page ${result.pageNumber}`);
      
      // Open in new tab with meaningful title
      const newWindow = window.open(result.viewUrl, '_blank');
      
      if (!newWindow) {
        // Popup blocked - fallback to direct download
        console.warn('Popup blocked, triggering download instead');
        this.downloadDocument(result.documentId, companyName, filename);
      } else {
        // Try to set a meaningful title (may not work due to CORS)
        try {
          newWindow.document.title = `${filename} - Page ${result.pageNumber}`;
        } catch (e) {
          // Ignore - cross-origin restrictions
        }
      }

      return result;
    } catch (error) {
      console.error('Error opening financial record:', error);
      throw error;
    }
  }

  /**
   * Download document directly
   * @param {string} documentId - The document ID to download
   * @param {string} companyName - The company name (e.g., "TESCO PLC") - REQUIRED
   * @param {string} filename - Optional filename for download
   */
  async downloadDocument(documentId, companyName, filename = 'document.pdf') {
    try {
      if (!companyName) {
        throw new Error('Company name is required');
      }

      const result = await this.getDocumentViewUrl(documentId, companyName);
      
      // Create temporary download link
      const link = document.createElement('a');
      link.href = result.viewUrl;
      link.download = filename;
      link.style.display = 'none';
      
      // Trigger download
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      return result;
    } catch (error) {
      console.error('Error downloading document:', error);
      throw error;
    }
  }

  /**
   * Check if a document can be viewed (without actually fetching the URL)
   * @param {string} documentId - The document ID to check
   * @param {string} companyName - The company name (e.g., "TESCO PLC") - REQUIRED
   * @returns {Promise<boolean>} True if document can be viewed
   */
  async canViewDocument(documentId, companyName) {
    try {
      if (!companyName) {
        console.log(`Cannot check document ${documentId} - company name is required`);
        return false;
      }

      await this.getDocumentViewUrl(documentId, companyName);
      return true;
    } catch (error) {
      console.log(`Document ${documentId} cannot be viewed:`, error.message);
      return false;
    }
  }

  /**
   * Check if a financial record can be viewed (without actually fetching the URL)
   * @param {string} financialRecordId - The financial record ID to check
   * @param {string} companyName - The company name (e.g., "TESCO PLC") - REQUIRED
   * @returns {Promise<boolean>} True if financial record can be viewed
   */
  async canViewFinancialRecord(financialRecordId, companyName) {
    try {
      if (!companyName) {
        console.log(`Cannot check financial record ${financialRecordId} - company name is required`);
        return false;
      }

      await this.getFinancialRecordViewUrl(financialRecordId, companyName);
      return true;
    } catch (error) {
      console.log(`Financial record ${financialRecordId} cannot be viewed:`, error.message);
      return false;
    }
  }

  /**
   * Helper method to get company name from company context
   * This is a utility method that components can use with useCompany() hook
   * @param {Object} activeCompany - The active company object from useCompany() hook
   * @returns {string} The company name to use in API calls
   */
  static getCompanyNameFromContext(activeCompany) {
    if (!activeCompany) {
      throw new Error('No company selected');
    }
    
    // Return the company name for API calls
    // This should match what's stored in the system
    return activeCompany.companyName || activeCompany.company_name;
  }
}

// Export singleton instance
export const documentService = new DocumentService();
export default documentService;
