import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import { waitForBackend, shouldRetry, retryDelay } from './api/backendReady';
import './styles/globals.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: shouldRetry,
      retryDelay,
    },
  },
});

// The app's first requests wait for the backend's health check: while it is starting, the screens say so instead of
// showing 500s from /api/datasets and /api/dashboard/overview.
function Root() {
  const [ready, setReady] = React.useState<boolean | null>(null);
  React.useEffect(() => {
    let alive = true;
    waitForBackend().then((ok) => {
      if (alive) setReady(ok);
    });
    return () => {
      alive = false;
    };
  }, []);

  if (ready === null) {
    return <div className="p-6 text-sm">Starting the ForgeRunner backend…</div>;
  }
  if (!ready) {
    return <div className="p-6 text-sm">The backend is not answering on /api. Start it, then reload this page.</div>;
  }
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  );
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>,
);
