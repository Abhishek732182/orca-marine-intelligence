import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import MarineNavbar from './components/MarineNavbar';
import Register from './pages/Register';
import Login from './pages/Login';
import UserDashboard from './pages/UserDashboard';
import AdminDashboard from './pages/AdminDashboard';
import NotFound from './pages/NotFound';

/**
 * Authentication-aware root redirect.
 * Redirects authenticated researchers to /user/dashboard,
 * authenticated admins to /admin/dashboard,
 * and unauthenticated visitors to /login.
 */
function RootRedirect() {
  const { isAuthenticated, user } = useAuth();
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  if (user?.role === 'admin') {
    return <Navigate to="/admin/dashboard" replace />;
  }
  return <Navigate to="/user/dashboard" replace />;
}

/**
 * ORCA — Marine Ecosystem Reasoning with Collaborative Agents
 * Single Page Application (SPA) Root with React Router & AuthProvider
 */
export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <div className="app-spa-layout">
          {/* Global Marine Navbar with Client-Side Active NavLinks & Session Controls */}
          <MarineNavbar />

          {/* Client-Side Routes Container */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
            <Routes>
              {/* Authentication-aware root redirect */}
              <Route path="/" element={<RootRedirect />} />

              {/* Public Authentication Pages */}
              <Route
                path="/register"
                element={
                  <main className="auth-main-container">
                    <Register />
                  </main>
                }
              />
              <Route
                path="/login"
                element={
                  <main className="auth-main-container">
                    <Login />
                  </main>
                }
              />

              {/* Protected User Section (Integrated Researcher & Specialist Workspace) */}
              <Route
                path="/user/dashboard"
                element={
                  <ProtectedRoute>
                    <UserDashboard />
                  </ProtectedRoute>
                }
              />

              {/* Protected Admin Section (Agent Cluster & System Administration) */}
              <Route
                path="/admin/dashboard"
                element={
                  <ProtectedRoute requiredRole="admin">
                    <AdminDashboard />
                  </ProtectedRoute>
                }
              />

              {/* Catch-all Fallback */}
              <Route path="*" element={<NotFound />} />
            </Routes>
          </div>

          {/* Unified Marine Platform Footer */}
          <footer className="auth-global-footer">
            <div>
              <strong>ORCA — Marine Ecosystem Reasoning with Collaborative Agents</strong> • Evidence-Grounded Ocean Intelligence & Maritime Safety
            </div>
            <div style={{ marginTop: '4px', color: 'var(--orca-text-muted)' }}>
              Single Page Application (SPA) Architecture • Decentralized Multi-Agent Telemetry • Open-Meteo & FastAPI Integrated
            </div>
          </footer>
        </div>
      </BrowserRouter>
    </AuthProvider>
  );
}
