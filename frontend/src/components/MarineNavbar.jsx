import React from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

/**
 * Global Marine Navigation Bar for ORCA SPA
 * Uses React Router for client-side navigation without page reloads.
 * Synchronized with AuthContext for live user session display and logout.
 */
export default function MarineNavbar() {
  const { user, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <header className="dashboard-navbar" role="banner">
      <div className="dashboard-nav-left">
        <Link to="/user/dashboard" className="dashboard-brand-link" title="ORCA Marine Ecosystem Reasoning">
          <div className="auth-logo-badge" style={{ width: 36, height: 36, fontSize: '1.1rem' }}>
            ✦
          </div>
          <div>
            <span className="dashboard-brand-title">ORCA Marine Intelligence</span>
            <span className="dashboard-brand-subtitle" style={{ display: 'block' }}>
              Multi-Agent Ocean Ecosystem SPA
            </span>
          </div>
        </Link>
      </div>

      {/* Main SPA Navigation Bar */}
      <nav className="dashboard-nav-center" aria-label="Primary Application Navigation">
        {isAuthenticated ? (
          <>
            <NavLink
              to="/user/dashboard"
              className={({ isActive }) =>
                `dashboard-nav-link ${isActive ? 'active' : ''}`
              }
              id="nav-link-user"
            >
              <span>📊</span>
              <span>Researcher Workspace</span>
            </NavLink>

            <NavLink
              to="/admin/dashboard"
              className={({ isActive }) =>
                `dashboard-nav-link ${isActive ? 'active' : ''}`
              }
              id="nav-link-admin"
            >
              <span>⚙️</span>
              <span>Admin Cluster</span>
            </NavLink>
          </>
        ) : (
          <>
            <NavLink
              to="/register"
              className={({ isActive }) =>
                `dashboard-nav-link ${isActive ? 'active' : ''}`
              }
              id="nav-link-register"
            >
              <span>📝</span>
              <span>Register</span>
            </NavLink>

            <NavLink
              to="/login"
              className={({ isActive }) =>
                `dashboard-nav-link ${isActive ? 'active' : ''}`
              }
              id="nav-link-login"
            >
              <span>🔐</span>
              <span>Login</span>
            </NavLink>
          </>
        )}
      </nav>

      {/* Right User & Live Status Section */}
      <div className="dashboard-nav-right">
        {isAuthenticated && user ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div className="user-profile-pill" title={`Role: ${user.role} • ${user.email}`}>
              <span className="user-avatar-badge">{user.avatarInitials || 'RC'}</span>
              <span>{user.fullName}</span>
              <span
                className={`orca-badge ${user.role === 'admin' ? 'badge-amber' : 'badge-emerald'}`}
                style={{ fontSize: '0.65rem', padding: '1px 6px', textTransform: 'uppercase' }}
              >
                {user.role}
              </span>
            </div>

            <button
              type="button"
              onClick={handleLogout}
              className="orca-btn orca-btn-sm orca-btn-secondary"
              style={{ fontSize: '0.74rem', padding: '4px 10px' }}
              title="Sign out of ORCA session"
            >
              Sign Out
            </button>
          </div>
        ) : (
          <Link
            to="/login"
            className="orca-btn orca-btn-sm orca-btn-primary"
            style={{ fontSize: '0.78rem' }}
          >
            Sign In ➜
          </Link>
        )}
      </div>
    </header>
  );
}
