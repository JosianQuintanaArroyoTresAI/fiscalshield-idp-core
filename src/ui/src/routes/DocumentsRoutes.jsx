// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
import React from 'react';
import { Route, Switch, useRouteMatch } from 'react-router-dom';
import { Logger } from 'aws-amplify';

import GenAIIDPLayout from '../components/genaiidp-layout';

const logger = new Logger('DocumentsRoutes');

const DocumentsRoutes = () => {
  const { path } = useRouteMatch();
  logger.info('path ', path);

  return (
    <Switch>
      <Route path={path}>
        <GenAIIDPLayout />
      </Route>
    </Switch>
  );
};

export default DocumentsRoutes;
