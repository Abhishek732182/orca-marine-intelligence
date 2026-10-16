import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Register from './pages/Register';
import Login from './pages/Login';
import UserDashboard from './pages/UserDashboard';
import AdminDashboard from './pages/AdminDashboard';
import NotFound from './pages/NotFound';

import { evaluateRootRedirect } from './utils/routeGuards.js';

export { evaluateRootRedirect };

/**
 * Root landing redirect based on authentication state
 */
export function RootRedirect() {
  const auth = useAuth();
  const target = evaluateRootRedirect(auth);
  if (!target) return null;
  return <Navigate to={target} replace />;
}

/**
 * ORCA — Marine Ecosystem Reasoning with Collaborative Agents
 * Single Page Application (SPA) Root Router
 */
export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <div className="min-h-screen w-full flex flex-col bg-white text-slate-900 font-sans antialiased">
          <Routes>
            {/* Root Landing Route */}
            <Route path="/" element={<RootRedirect />} />

            {/* Public Authentication Pages */}
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />

            {/* Protected User Workspace (Chat-First Experience) */}
            <Route
              path="/user/dashboard"
              element={
                <ProtectedRoute>
                  <UserDashboard />
                </ProtectedRoute>
              }
            />

            {/* Protected Admin Console */}
            <Route
              path="/admin/dashboard"
              element={
                <ProtectedRoute requiredRole="admin">
                  <AdminDashboard />
                </ProtectedRoute>
              }
            />

            {/* Catch-all 404 Fallback */}
            <Route path="*" element={<NotFound />} />
          </Routes>
        </div>
      </BrowserRouter>
    </AuthProvider>
  );
}
