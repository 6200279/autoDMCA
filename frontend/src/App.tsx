import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { lazy, Suspense, useEffect } from 'react';

// PrimeReact CSS (theme will be loaded dynamically)
import 'primereact/resources/primereact.min.css';
import 'primeicons/primeicons.css';
import 'primeflex/primeflex.css';

import { AuthProvider } from './contexts/AuthContext';
import { LayoutProvider } from './contexts/LayoutContext';
import { WebSocketProvider } from './contexts/WebSocketContext';
import { useAuth } from './contexts/AuthContext';

// Components (imported immediately as they're critical)
import Layout from './components/common/Layout';
import ProtectedRoute from './components/common/ProtectedRoute';
import ErrorBoundary from './components/common/ErrorBoundary';

// Loading component for route transitions
import LoadingSpinner from './components/common/LoadingSpinner';

// Performance monitoring
import { reportBundleSize, monitorMemoryUsage } from './utils/performance';

// Route preloading
import { routePreloader } from './utils/preloader';

// Critical pages (loaded immediately)
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import NotFound from './pages/NotFound';

// Lazy-loaded pages (split into chunks)
const Profiles = lazy(() => import('./pages/Profiles'));
const Infringements = lazy(() => import('./pages/Infringements'));
const TakedownRequests = lazy(() => import('./pages/TakedownRequests'));
const Submissions = lazy(() => import('./pages/Submissions'));
const Reports = lazy(() => import('./pages/Reports'));
const SocialMediaProtection = lazy(() => import('./pages/SocialMediaProtection'));
const AIContentMatching = lazy(() => import('./pages/AIContentMatching'));
const Settings = lazy(() => import('./pages/Settings'));
const Billing = lazy(() => import('./pages/Billing'));
const AdminPanel = lazy(() => import('./pages/AdminPanel'));
const DMCATemplates = lazy(() => import('./pages/DMCATemplates'));
const SearchEngineDelisting = lazy(() => import('./pages/SearchEngineDelisting'));
const ContentWatermarking = lazy(() => import('./pages/ContentWatermarking'));
const BrowserExtension = lazy(() => import('./pages/BrowserExtension'));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

// Configure PrimeReact globally
const configurePrimeReact = () => {
  // You can add global PrimeReact configuration here if needed
};

configurePrimeReact();

// Higher-order component to wrap lazy-loaded components with Suspense
const LazyRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <Suspense fallback={<LoadingSpinner message="Loading page..." size="medium" />}>
    {children}
  </Suspense>
);

function AppContent() {
  const { user } = useAuth();

  return (
    <Router>
      <Routes>
        {/* Public routes */}
        <Route 
          path="/login" 
          element={user ? <Navigate to="/dashboard" replace /> : <Login />} 
        />
        <Route 
          path="/register" 
          element={user ? <Navigate to="/dashboard" replace /> : <Register />} 
        />
        
        {/* Protected routes */}
        <Route 
          path="/dashboard" 
          element={
            <ProtectedRoute>
              <Layout>
                <Dashboard />
              </Layout>
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/protection/profiles" 
          element={
            <ProtectedRoute>
              <Layout>
                <LazyRoute>
                  <Profiles />
                </LazyRoute>
              </Layout>
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/protection/infringements" 
          element={
            <ProtectedRoute>
              <Layout>
                <LazyRoute>
                  <Infringements />
                </LazyRoute>
              </Layout>
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/protection/takedowns" 
          element={
            <ProtectedRoute>
              <Layout>
                <LazyRoute>
                  <TakedownRequests />
                </LazyRoute>
              </Layout>
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/protection/submissions" 
          element={
            <ProtectedRoute>
              <Layout>
                <LazyRoute>
                  <Submissions />
                </LazyRoute>
              </Layout>
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/protection/social-media" 
          element={
            <ProtectedRoute>
              <Layout>
                <LazyRoute>
                  <SocialMediaProtection />
                </LazyRoute>
              </Layout>
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/protection/ai-matching" 
          element={
            <ProtectedRoute>
              <Layout>
                <LazyRoute>
                  <AIContentMatching />
                </LazyRoute>
              </Layout>
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/protection/templates" 
          element={
            <ProtectedRoute>
              <Layout>
                <LazyRoute>
                  <DMCATemplates />
                </LazyRoute>
              </Layout>
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/protection/search-delisting" 
          element={
            <ProtectedRoute>
              <Layout>
                <LazyRoute>
                  <SearchEngineDelisting />
                </LazyRoute>
              </Layout>
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/protection/browser-extension" 
          element={
            <ProtectedRoute>
              <Layout>
                <LazyRoute>
                  <BrowserExtension />
                </LazyRoute>
              </Layout>
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/protection/watermarking" 
          element={
            <ProtectedRoute>
              <Layout>
                <LazyRoute>
                  <ContentWatermarking />
                </LazyRoute>
              </Layout>
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/settings" 
          element={
            <ProtectedRoute>
              <Layout>
                <LazyRoute>
                  <Settings />
                </LazyRoute>
              </Layout>
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/billing" 
          element={
            <ProtectedRoute>
              <Layout>
                <LazyRoute>
                  <Billing />
                </LazyRoute>
              </Layout>
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/reports" 
          element={
            <ProtectedRoute>
              <Layout>
                <LazyRoute>
                  <Reports />
                </LazyRoute>
              </Layout>
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/admin" 
          element={
            <ProtectedRoute roles={['admin']}>
              <Layout>
                <LazyRoute>
                  <AdminPanel />
                </LazyRoute>
              </Layout>
            </ProtectedRoute>
          } 
        />
        
        {/* Legacy route redirects for compatibility */}
        <Route path="/profiles" element={<Navigate to="/protection/profiles" replace />} />
        <Route path="/infringements" element={<Navigate to="/protection/infringements" replace />} />
        <Route path="/takedown-requests" element={<Navigate to="/protection/takedowns" replace />} />
        <Route path="/templates" element={<Navigate to="/protection/templates" replace />} />
        <Route path="/dmca-templates" element={<Navigate to="/protection/templates" replace />} />
        <Route path="/submissions" element={<Navigate to="/protection/submissions" replace />} />
        <Route path="/social-media" element={<Navigate to="/protection/social-media" replace />} />
        <Route path="/ai-matching" element={<Navigate to="/protection/ai-matching" replace />} />
        <Route path="/content-matching" element={<Navigate to="/protection/ai-matching" replace />} />
        <Route path="/search-delisting" element={<Navigate to="/protection/search-delisting" replace />} />
        <Route path="/watermarking" element={<Navigate to="/protection/watermarking" replace />} />
        <Route path="/browser-extension" element={<Navigate to="/protection/browser-extension" replace />} />
        
        {/* Redirect root to dashboard */}
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        
        {/* 404 Not Found */}
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Router>
  );
}

function App() {
  useEffect(() => {
    // Initialize performance monitoring
    setTimeout(() => {
      reportBundleSize();
      monitorMemoryUsage();
    }, 2000); // Give time for bundles to load

    // Preload critical routes
    routePreloader.preloadCriticalRoutes();

    // Monitor memory usage every 30 seconds in development
    if (process.env.NODE_ENV === 'development') {
      const memoryInterval = setInterval(monitorMemoryUsage, 30000);
      return () => clearInterval(memoryInterval);
    }
  }, []);

  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <WebSocketProvider
            autoConnect={true}
            reconnectOnError={true}
            maxReconnectAttempts={10}
            debug={process.env.NODE_ENV === 'development'}
          >
            <LayoutProvider>
              <AppContent />
            </LayoutProvider>
          </WebSocketProvider>
        </AuthProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;