import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

const CompanyContext = createContext(null);

/**
 * CompanyProvider - Manages active company state across the application
 * 
 * This context provides:
 * - activeCompany: Currently selected company object with companyNumber, companyName, etc.
 * - selectCompany: Function to set the active company and persist to localStorage
 * - clearCompany: Function to clear the active company
 * - isCompanySelected: Boolean flag for conditional rendering
 * 
 * Data persists in localStorage as 'active_company' for session continuity.
 */
export const CompanyProvider = ({ children }) => {
  const [activeCompany, setActiveCompany] = useState(null);
  const [loading, setLoading] = useState(true);

  // Load company from localStorage on mount
  useEffect(() => {
    try {
      const storedCompany = localStorage.getItem('active_company');
      if (storedCompany) {
        const company = JSON.parse(storedCompany);
        setActiveCompany(company);
      }
    } catch (error) {
      console.error('Error loading active company from localStorage:', error);
      localStorage.removeItem('active_company');
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Select a company and persist to localStorage
   * @param {Object} company - Company object with at minimum { companyNumber, companyName }
   */
  const selectCompany = useCallback((company) => {
    if (!company || !company.companyNumber) {
      console.error('Invalid company object - must have companyNumber');
      return;
    }

    setActiveCompany(company);
    try {
      localStorage.setItem('active_company', JSON.stringify(company));
    } catch (error) {
      console.error('Error saving company to localStorage:', error);
    }
  }, []);

  /**
   * Clear the active company from state and localStorage
   */
  const clearCompany = useCallback(() => {
    setActiveCompany(null);
    try {
      localStorage.removeItem('active_company');
    } catch (error) {
      console.error('Error clearing company from localStorage:', error);
    }
  }, []);

  /**
   * Refresh company data (placeholder for future API integration)
   * When DataCollection stack is available, this can fetch updated company details
   */
  const refreshCompany = useCallback(async () => {
    if (!activeCompany) return;

    // TODO: Phase 3 - Add API call to refresh company data
    // const response = await API.get('DataCollectionAPI', `/companies/${activeCompany.companyNumber}`);
    // selectCompany(response);
    
    console.log('refreshCompany - API integration pending');
  }, [activeCompany]);

  const value = {
    activeCompany,
    selectCompany,
    clearCompany,
    refreshCompany,
    isCompanySelected: !!activeCompany,
    loading
  };

  return (
    <CompanyContext.Provider value={value}>
      {children}
    </CompanyContext.Provider>
  );
};

/**
 * Custom hook to access CompanyContext
 * @returns {Object} Company context value
 * @throws {Error} If used outside CompanyProvider
 */
export const useCompany = () => {
  const context = useContext(CompanyContext);
  if (!context) {
    throw new Error('useCompany must be used within a CompanyProvider');
  }
  return context;
};

export default CompanyContext;
