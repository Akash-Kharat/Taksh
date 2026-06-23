import React from 'react';
import { HashRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import { getBackendUrl, ConnectionState } from './services/backend';
import { systemApi } from './services/api/systemApi';
import { StartupGuard } from './components/StartupGuard';
import { ShellLayout } from './layouts/ShellLayout';
import { ErrorBoundary } from './components/ErrorBoundary';

// Pages
import { Dashboard } from './pages/Dashboard';
import { Diagnostics } from './pages/Diagnostics';
import { Providers } from './pages/Providers';
import { Settings } from './pages/Settings';

import { GlobalHealthStatus } from './components/GlobalStatusBanner';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      refetchOnWindowFocus: false,
    },
  },
});

const AppContent: React.FC = () => {
  // Poll readiness endpoint every 15s to check connectivity and readiness score
  const {
    data: readiness,
    isError,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ['startupReadiness'],
    queryFn: systemApi.getReadiness,
    refetchInterval: 15000,
  });

  // Determine Connection State
  let connectionState: ConnectionState = 'CONNECTING';
  if (isError) {
    connectionState = 'DISCONNECTED';
  } else if (readiness) {
    connectionState = 'CONNECTED';
  }

  // Determine Global Health status
  let healthStatus: GlobalHealthStatus = 'Healthy';
  if (connectionState === 'DISCONNECTED') {
    healthStatus = 'Disconnected';
  } else if (readiness) {
    if (readiness.score < 70) {
      healthStatus = 'Not Ready';
    } else if (readiness.score < 90) {
      healthStatus = 'Degraded';
    }
  }

  const backendUrl = getBackendUrl();

  const handleReconnect = () => {
    refetch();
  };

  return (
    <Router>
      <StartupGuard
        connectionState={connectionState}
        readiness={readiness || null}
        isLoading={isLoading}
        onRetry={handleReconnect}
      >
        <ShellLayout
          status={healthStatus}
          score={readiness?.score}
          backendUrl={backendUrl}
        >
          <ErrorBoundary>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/diagnostics" element={<Diagnostics />} />
              <Route path="/providers" element={<Providers />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
          </ErrorBoundary>
        </ShellLayout>
      </StartupGuard>
    </Router>
  );
};

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppContent />
    </QueryClientProvider>
  );
}

export default App;
