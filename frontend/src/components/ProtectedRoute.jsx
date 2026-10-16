import React from 'react';
import { Navigate, useLocation, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

import { evaluateProtectedRoute } from '../utils/routeGuards.js';

export { evaluateProtectedRoute };

/**
 * Route Guard Component for ORCA Single Page Application.
 * Protects User Workspace and Admin Console, enforcing real role authorization.
 */
export default function ProtectedRoute({ children, requiredRole }) {
  const { user, isAuthenticated, isLoading, switchRole } = useAuth();
  const location = useLocation();

  const decision = evaluateProtectedRoute({ isAuthenticated, isLoading, user, requiredRole });

  if (decision.status === 'loading') {
    return (
      <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center gap-3">
        <div className="w-8 h-8 rounded-full border-2 border-slate-300 border-t-slate-900 animate-spin" />
        <span className="text-xs text-slate-500">
          Verifying maritime session...
        </span>
      </div>
    );
  }

  if (decision.status === 'redirect_login') {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Check role-based access if specified
  if (decision.status === 'restricted') {
    return (
      <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-4 sm:p-6">
        <div className="max-w-md w-full bg-white p-6 sm:p-8 rounded-2xl border border-slate-200 shadow-sm text-center">
          <div className="w-12 h-12 rounded-2xl bg-amber-50 text-amber-600 flex items-center justify-center mx-auto mb-4 border border-amber-200">
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>

          <h2 className="text-lg font-bold text-slate-900">
            Restricted Operations Area
          </h2>
          <p className="mt-2 text-xs text-slate-500 leading-relaxed">
            Your current account (<strong>{user?.fullName || 'User'}</strong>) has role{' '}
            <span className="font-mono uppercase font-semibold text-slate-700 bg-slate-100 px-1.5 py-0.5 rounded">
              {user?.role || 'unassigned'}
            </span>
            . Access to the Admin Management Console requires <strong>Administrator</strong> privileges.
          </p>

          <div className="mt-6 flex flex-col gap-2">
            <button
              type="button"
              onClick={() => switchRole('admin')}
              className="w-full py-2 px-4 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-medium text-xs transition-colors shadow-xs"
            >
              Switch Role to Admin (Demo Mode)
            </button>
            <Link
              to="/user/dashboard"
              className="w-full py-2 px-4 rounded-xl bg-white hover:bg-slate-50 text-slate-700 font-medium text-xs border border-slate-200 transition-colors"
            >
              Return to Chat Workspace
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return children;
}
