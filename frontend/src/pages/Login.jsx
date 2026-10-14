import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import FormInput from '../components/FormInput';
import Button from '../components/Button';
import MarineBrandingPanel from '../components/MarineBrandingPanel';
import { useAuth } from '../context/AuthContext';
import { validateEmail, validateLoginPassword } from '../utils/validation';

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();

  // Form input state
  const [formData, setFormData] = useState({
    email: '',
    password: '',
  });

  // Errors state
  const [errors, setErrors] = useState({});
  // Touched state
  const [touched, setTouched] = useState({});
  // Feedback states
  const [successInfo, setSuccessInfo] = useState(null);
  const [authError, setAuthError] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Field validation logic using shared validation utilities
  const validateField = (name, value) => {
    switch (name) {
      case 'email':
        return validateEmail(value);
      case 'password':
        return validateLoginPassword(value);
      default:
        return '';
    }
  };

  // Handle live input change with real-time validation if touched
  const handleChange = (e) => {
    const { name, value } = e.target;
    const updatedForm = { ...formData, [name]: value };
    setFormData(updatedForm);

    if (touched[name]) {
      const errorMsg = validateField(name, value);
      setErrors((prev) => ({ ...prev, [name]: errorMsg }));
    }

    if (successInfo) setSuccessInfo(null);
    if (authError) setAuthError(null);
  };

  // Handle onBlur for real-time validation
  const handleBlur = (e) => {
    const { name, value } = e.target;
    setTouched((prev) => ({ ...prev, [name]: true }));
    const errorMsg = validateField(name, value);
    setErrors((prev) => ({ ...prev, [name]: errorMsg }));
  };

  // Handle quick login demo account autofill
  const handleAutofillDemo = (email, pass = 'Oceanic@2026!') => {
    setFormData({ email, password: pass });
    setErrors({});
    setTouched({});
    setAuthError(null);
  };

  // Handle submit
  const handleSubmit = async (e) => {
    e.preventDefault();

    setTouched({
      email: true,
      password: true,
    });

    const newErrors = {
      email: validateField('email', formData.email),
      password: validateField('password', formData.password),
    };

    setErrors(newErrors);

    const hasError = Object.values(newErrors).some((err) => Boolean(err));
    if (hasError) {
      setSuccessInfo(null);
      return;
    }

    setIsSubmitting(true);
    setAuthError(null);

    try {
      const result = await login(formData.email, formData.password);
      setSuccessInfo({
        email: result.user.email,
        fullName: result.user.fullName,
        role: result.user.role,
        timestamp: new Date().toLocaleTimeString(),
      });

      // Redirect after brief visual feedback or immediately
      const destination = location.state?.from?.pathname || '/user/dashboard';
      setTimeout(() => {
        navigate(destination, { replace: true });
      }, 500);
    } catch (err) {
      setAuthError(err.message || 'Login failed. Please check credentials.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReset = () => {
    setFormData({
      email: '',
      password: '',
    });
    setErrors({});
    setTouched({});
    setSuccessInfo(null);
    setAuthError(null);
  };

  return (
    <div className="auth-card-split" id="orca-login-card">
      {/* Left: Scientific Marine Mission & Agents Showcase */}
      <MarineBrandingPanel />

      {/* Right: Login Form Panel */}
      <div className="auth-form-panel">
        <div className="auth-form-header">
          <span className="auth-form-badge">Researcher Portal</span>
          <h1 className="auth-form-title">Marine Portal Sign In</h1>
          <p className="auth-form-subtitle">
            Sign in to access your marine intelligence telemetry workspace and multi-agent reasoning tools.
          </p>
        </div>

        {/* Quick Testing Demo Accounts Banner */}
        <div
          style={{
            background: 'var(--orca-bg-subtle)',
            border: '1px solid var(--orca-border-subtle)',
            borderRadius: 'var(--radius-md)',
            padding: '10px 14px',
            marginBottom: '16px',
            fontSize: '0.78rem',
          }}
        >
          <div style={{ fontWeight: 600, color: 'var(--orca-navy-950)', marginBottom: '6px' }}>
            ⚡ Quick Evaluator Demo Logins:
          </div>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            <button
              type="button"
              className="orca-btn orca-btn-sm orca-btn-secondary"
              style={{ fontSize: '0.72rem', padding: '3px 8px' }}
              onClick={() => handleAutofillDemo('rachel.carson@orca-marine.org')}
            >
              🌊 Dr. Carson (Oceanographer)
            </button>
            <button
              type="button"
              className="orca-btn orca-btn-sm orca-btn-secondary"
              style={{ fontSize: '0.72rem', padding: '3px 8px' }}
              onClick={() => handleAutofillDemo('admin@orca.io')}
            >
              ⚙️ Admin Operator
            </button>
          </div>
        </div>

        {/* Auth Error Box */}
        {authError && (
          <div className="auth-alert-box error" role="alert" style={{ marginBottom: '16px' }}>
            <span className="alert-icon" aria-hidden="true">⚠️</span>
            <div className="alert-content">
              <strong>Authentication Notice</strong>
              <div>{authError}</div>
            </div>
          </div>
        )}

        {/* Frontend Success Feedback Notice */}
        {successInfo && (
          <div className="auth-alert-box success" role="status" aria-live="polite" style={{ marginBottom: '16px' }}>
            <span className="alert-icon" aria-hidden="true">🌊</span>
            <div className="alert-content">
              <strong>Session Authenticated!</strong>
              <div>
                Welcome back, <strong>{successInfo.fullName}</strong> ({successInfo.email}). Navigating to Researcher Workspace...
              </div>
            </div>
          </div>
        )}

        <form className="auth-form" onSubmit={handleSubmit} noValidate>
          {/* 1. Email Address */}
          <FormInput
            id="login-email"
            name="email"
            label="Email Address"
            type="email"
            required
            value={formData.email}
            onChange={handleChange}
            onBlur={handleBlur}
            placeholder="researcher@marine.org"
            autoComplete="email"
            error={touched.email ? errors.email : ''}
            isValid={touched.email && !errors.email && formData.email.trim().length > 0}
            icon={
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path>
                <polyline points="22,6 12,13 2,6"></polyline>
              </svg>
            }
          />

          {/* 2. Password */}
          <FormInput
            id="login-password"
            name="password"
            label="Password"
            type="password"
            required
            value={formData.password}
            onChange={handleChange}
            onBlur={handleBlur}
            placeholder="Enter your account password"
            autoComplete="current-password"
            error={touched.password ? errors.password : ''}
            isValid={touched.password && !errors.password && formData.password.length > 0}
            icon={
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
              </svg>
            }
          />

          {/* 3. Login Button */}
          <Button
            id="login-submit-btn"
            type="submit"
            variant="primary"
            loading={isSubmitting}
            icon={
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"></path>
                <polyline points="10 17 15 12 10 7"></polyline>
                <line x1="15" y1="12" x2="3" y2="12"></line>
              </svg>
            }
          >
            Sign In to ORCA
          </Button>

          {successInfo && (
            <button
              type="button"
              onClick={handleReset}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--orca-text-muted)',
                fontSize: '0.8rem',
                cursor: 'pointer',
                textAlign: 'center',
                textDecoration: 'underline',
              }}
            >
              Clear form to test again
            </button>
          )}
        </form>

        {/* Client-side SPA navigation link to Register */}
        <div className="auth-switch-footer">
          <span>New researcher to the ORCA platform? </span>
          <Link
            to="/register"
            className="auth-switch-link"
            id="nav-to-register-link"
          >
            Create an account here →
          </Link>
        </div>

        {/* Scope disclaimer */}
        <div className="auth-scope-disclaimer">
          <span aria-hidden="true">ℹ️</span>
          <span>
            <strong>Production State:</strong> Authenticated token is persisted to browser session and injects into all multi-agent API calls.
          </span>
        </div>
      </div>
    </div>
  );
}
