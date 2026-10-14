import React from 'react';
import { Navigate, useLocation, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

/**
 * Route Guard Component for ORCA Single Page Application
 * Protects Researcher and Admin views, enforces role authorization.
 */
export default function ProtectedRoute({ children, requiredRole }) {
  const { user, isAuthenticated, isLoading, switchRole } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div
        style={{
          minHeight: '60vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '1rem',
        }}
      >
        <span className="orca-spinner" style={{ width: 36, height: 36 }} />
        <span style={{ fontSize: '0.9rem', color: 'var(--orca-text-muted)' }}>
          Verifying maritime cryptographic session...
        </span>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Check role-based access if specified
  if (requiredRole && user?.role !== requiredRole) {
    return (
      <main className="dashboard-content-canvas" style={{ maxWidth: 800, margin: '40px auto', padding: '24px' }}>
        <div className="auth-alert-box error" style={{ padding: '24px' }}>
          <div style={{ fontSize: '2rem', marginBottom: '8px' }}>🛡️</div>
          <div>
            <h2 style={{ fontSize: '1.25rem', color: 'var(--orca-error-text)', marginBottom: '6px' }}>
              Restricted Operations Area ({requiredRole.toUpperCase()} Required)
            </h2>
            <p style={{ fontSize: '0.88rem', color: 'var(--orca-text-secondary)', marginBottom: '16px' }}>
              Your current profile (<strong>{user?.fullName}</strong>) is assigned role{' '}
              <span className="orca-badge badge-amber" style={{ textTransform: 'uppercase' }}>
                {user?.role}
              </span>
              . Administrative cluster telemetry and audit access require Administrator credentials.
            </p>

            <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
              <button
                type="button"
                className="orca-btn orca-btn-primary"
                onClick={() => switchRole('admin')}
              >
                Elevate to Admin Role (Demo Mode) ⚡
              </button>
              <Link to="/user/dashboard" className="orca-btn orca-btn-secondary">
                Return to Researcher Workspace
              </Link>
            </div>
          </div>
        </div>
      </main>
    );
  }

  return children;
}
