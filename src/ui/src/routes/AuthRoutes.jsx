// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
import React from 'react';
import PropTypes from 'prop-types';
import { Logger } from 'aws-amplify';
import { Redirect, Route, Switch } from 'react-router-dom';

import { Button, useAuthenticator } from '@aws-amplify/ui-react';

import { SettingsContext } from '../contexts/settings';
import useParameterStore from '../hooks/use-parameter-store';
import useAppContext from '../contexts/app';

import CompanySelect from '../components/company-select';
import DocumentsRoutes from './DocumentsRoutes';
import DocumentsQueryRoutes from './DocumentsQueryRoutes';
import DocumentsAnalyticsRoutes from './DocumentsAnalyticsRoutes';
import CompanyIntelligence from '../components/company-intelligence';
import { CompanyAnalysis } from '../components/company-intelligence';
import { OverviewDashboard } from '../components/overview';
import { ClientTakeOnAnalysis } from '../components/client-takeon';
import { InvoiceInsights, InvoiceAnalysisDashboard } from '../components/invoice-insights';
import { BankStatementInsights } from '../components/bank-insights';
import { CompanyHub } from '../components/company-hub';
import ValidationMetricsDashboard from '../components/admin/ValidationMetricsDashboard';
import RequireCompany from '../components/RequireCompany';

import {
  COMPANY_SELECT_PATH,
  DOCUMENTS_PATH,
  DEFAULT_PATH,
  LOGIN_PATH,
  LOGOUT_PATH,
  DOCUMENTS_KB_QUERY_PATH,
  DOCUMENTS_ANALYTICS_PATH,
  COMPANY_HUB_PATH,
  COMPANY_INTELLIGENCE_PATH,
  COMPANY_ANALYSIS_PATH,
  OVERVIEW_DASHBOARD_PATH,
  CLIENT_TAKEON_PATH,
  INVOICE_INSIGHTS_PATH,
  INVOICE_ANALYSIS_PATH,
  BANK_INSIGHTS_PATH,
  ADMIN_VALIDATION_METRICS_PATH,
} from './constants';

const logger = new Logger('AuthRoutes');

const AuthRoutes = ({ redirectParam }) => {
  const { currentCredentials, isAdmin } = useAppContext();
  const settings = useParameterStore(currentCredentials);
  const { signOut } = useAuthenticator();

  // eslint-disable-next-line react/jsx-no-constructed-context-values
  const settingsContextValue = {
    settings,
  };
  logger.debug('settingsContextValue', settingsContextValue);

  return (
    <SettingsContext.Provider value={settingsContextValue}>
      <Switch>
        <Route exact path={COMPANY_SELECT_PATH}>
          <CompanySelect />
        </Route>
        <Route exact path={COMPANY_HUB_PATH}>
          <RequireCompany>
            <CompanyHub />
          </RequireCompany>
        </Route>
        <Route exact path={OVERVIEW_DASHBOARD_PATH}>
          <RequireCompany>
            <OverviewDashboard />
          </RequireCompany>
        </Route>
        <Route exact path={CLIENT_TAKEON_PATH}>
          <RequireCompany>
            <ClientTakeOnAnalysis />
          </RequireCompany>
        </Route>
        <Route exact path={INVOICE_INSIGHTS_PATH}>
          <RequireCompany>
            <InvoiceInsights />
          </RequireCompany>
        </Route>
        <Route exact path={INVOICE_ANALYSIS_PATH}>
          <RequireCompany>
            <InvoiceAnalysisDashboard />
          </RequireCompany>
        </Route>
        <Route exact path={BANK_INSIGHTS_PATH}>
          <RequireCompany>
            <BankStatementInsights />
          </RequireCompany>
        </Route>
        <Route exact path={ADMIN_VALIDATION_METRICS_PATH}>
          {isAdmin ? <ValidationMetricsDashboard /> : <Redirect to={DEFAULT_PATH} />}
        </Route>
        <Route path={COMPANY_INTELLIGENCE_PATH}>
          <RequireCompany>
            <CompanyIntelligence />
          </RequireCompany>
        </Route>
        <Route path={COMPANY_ANALYSIS_PATH}>
          <RequireCompany>
            <CompanyAnalysis />
          </RequireCompany>
        </Route>
        <Route path={DOCUMENTS_PATH}>
          <RequireCompany>
            <DocumentsRoutes />
          </RequireCompany>
        </Route>
        <Route path={LOGIN_PATH}>
          <Redirect to={!redirectParam || redirectParam === LOGIN_PATH ? DEFAULT_PATH : `${redirectParam}`} />
        </Route>
        <Route path={LOGOUT_PATH}>
          <Button onClick={signOut}>Sign Out</Button>
        </Route>
        <Route path={DOCUMENTS_KB_QUERY_PATH}>
          <RequireCompany>
            <DocumentsQueryRoutes />
          </RequireCompany>
        </Route>
        <Route path={DOCUMENTS_ANALYTICS_PATH}>
          <RequireCompany>
            <DocumentsAnalyticsRoutes />
          </RequireCompany>
        </Route>
        <Route>
          <Redirect to={DEFAULT_PATH} />
        </Route>
      </Switch>
    </SettingsContext.Provider>
  );
};

AuthRoutes.propTypes = {
  redirectParam: PropTypes.string.isRequired,
};

export default AuthRoutes;
