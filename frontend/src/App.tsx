import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toast } from 'primereact/toast';

// PrimeReact CSS (theme will be loaded dynamically)
import 'primereact/resources/primereact.min.css';
import 'primeicons/primeicons.css';
import 'primeflex/primeflex.css';

import { AuthProvider } from './contexts/AuthContext';
import { LayoutProvider } from './contexts/LayoutContext';
import { useAuth } from './contexts/AuthContext';

// Pages
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import Profiles from './pages/Profiles';
import Infringements from './pages/Infringements';
import TakedownRequests from './pages/TakedownRequests';
import Settings from './pages/Settings';
import Billing from './pages/Billing';
import NotFound from './pages/NotFound';

// Components
import Layout from './components/common/Layout';
import ProtectedRoute from './components/common/ProtectedRoute';
import ErrorBoundary from './components/common/ErrorBoundary';

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
                <Profiles />
              </Layout>
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/protection/infringements" 
          element={
            <ProtectedRoute>
              <Layout>
                <Infringements />
              </Layout>
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/protection/takedowns" 
          element={
            <ProtectedRoute>
              <Layout>
                <TakedownRequests />
              </Layout>
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/settings" 
          element={
            <ProtectedRoute>
              <Layout>
                <Settings />
              </Layout>
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/billing" 
          element={
            <ProtectedRoute>
              <Layout>
                <Billing />
              </Layout>
            </ProtectedRoute>
          } 
        />
        
        {/* Legacy route redirects for compatibility */}
        <Route path="/profiles" element={<Navigate to="/protection/profiles" replace />} />
        <Route path="/infringements" element={<Navigate to="/protection/infringements" replace />} />
        <Route path="/takedown-requests" element={<Navigate to="/protection/takedowns" replace />} />
        
        {/* Redirect root to dashboard */}
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        
        {/* 404 Not Found */}
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Router>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <LayoutProvider>
            <AppContent />
          </LayoutProvider>
        </AuthProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;