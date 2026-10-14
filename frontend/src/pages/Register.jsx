import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import FormInput from '../components/FormInput';
import Button from '../components/Button';
import PasswordStrengthMeter from '../components/PasswordStrengthMeter';
import MarineBrandingPanel from '../components/MarineBrandingPanel';
import { useAuth } from '../context/AuthContext';
import {
  validateFullName,
  validateEmail,
  validatePassword,
  validateConfirmPassword,
} from '../utils/validation';

export default function Register() {
  const navigate = useNavigate();
  const { register } = useAuth();

  // Form input state
  const [formData, setFormData] = useState({
    fullName: '',
    email: '',
    password: '',
    confirmPassword: '',
  });

  // Errors state
  const [errors, setErrors] = useState({});
  // Touched state for touched fields
  const [touched, setTouched] = useState({});
  // Submission feedback state
  const [successInfo, setSuccessInfo] = useState(null);
  const [regError, setRegError] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Field validator helper using shared validation utilities
  const validateField = (name, value, allValues = formData) => {
    switch (name) {
      case 'fullName':
        return validateFullName(value);
      case 'email':
        return validateEmail(value);
      case 'password':
        return validatePassword(value);
      case 'confirmPassword':
        return validateConfirmPassword(value, allValues.password);
      default:
        return '';
    }
  };

  // Handle live input change with real-time validation if field was touched
  const handleChange = (e) => {
    const { name, value } = e.target;
    const updatedForm = { ...formData, [name]: value };
    setFormData(updatedForm);

    if (touched[name]) {
      const errorMsg = validateField(name, value, updatedForm);
      setErrors((prev) => ({ ...prev, [name]: errorMsg }));
    }

    if (name === 'password' && touched.confirmPassword) {
      const confirmError = validateField('confirmPassword', updatedForm.confirmPassword, updatedForm);
      setErrors((prev) => ({ ...prev, confirmPassword: confirmError }));
    }

    if (successInfo) setSuccessInfo(null);
    if (regError) setRegError(null);
  };

  // Handle onBlur for real-time validation when leaving the field
  const handleBlur = (e) => {
    const { name, value } = e.target;
    setTouched((prev) => ({ ...prev, [name]: true }));
    const errorMsg = validateField(name, value, formData);
    setErrors((prev) => ({ ...prev, [name]: errorMsg }));
  };

  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();

    setTouched({
      fullName: true,
      email: true,
      password: true,
      confirmPassword: true,
    });

    const newErrors = {
      fullName: validateField('fullName', formData.fullName, formData),
      email: validateField('email', formData.email, formData),
      password: validateField('password', formData.password, formData),
      confirmPassword: validateField('confirmPassword', formData.confirmPassword, formData),
    };

    setErrors(newErrors);

    const hasError = Object.values(newErrors).some((err) => Boolean(err));
    if (hasError) {
      setSuccessInfo(null);
      return;
    }

    setIsSubmitting(true);
    setRegError(null);

    try {
      const result = await register({
        fullName: formData.fullName,
        email: formData.email,
        password: formData.password,
      });

      setSuccessInfo({
        fullName: result.user.fullName,
        email: result.user.email,
        timestamp: new Date().toLocaleTimeString(),
      });

      setTimeout(() => {
        navigate('/user/dashboard');
      }, 700);
    } catch (err) {
      setRegError(err.message || 'Registration failed.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReset = () => {
    setFormData({
      fullName: '',
      email: '',
      password: '',
      confirmPassword: '',
    });
    setErrors({});
    setTouched({});
    setSuccessInfo(null);
    setRegError(null);
  };

  return (
    <div className="auth-card-split" id="orca-registration-card">
      {/* Left: Scientific Marine Mission & Agents Showcase */}
      <MarineBrandingPanel />

      {/* Right: Registration Form Panel */}
      <div className="auth-form-panel">
        <div className="auth-form-header">
          <span className="auth-form-badge">Researcher Onboarding</span>
          <h1 className="auth-form-title">Create ORCA Account</h1>
          <p className="auth-form-subtitle">
            Register to access multi-agent oceanographic telemetry, sea state analyses, and route safety assessments.
          </p>
        </div>

        {/* Error notification */}
        {regError && (
          <div className="auth-alert-box error" role="alert" style={{ marginBottom: '16px' }}>
            <span className="alert-icon" aria-hidden="true">⚠️</span>
            <div className="alert-content">
              <strong>Registration Notice</strong>
              <div>{regError}</div>
            </div>
          </div>
        )}

        {/* Frontend Success Feedback Notice */}
        {successInfo && (
          <div className="auth-alert-box success" role="status" aria-live="polite">
            <span className="alert-icon" aria-hidden="true">🛡️</span>
            <div className="alert-content">
              <strong>Registration Successful!</strong>
              <div>
                Welcome, <strong>{successInfo.fullName}</strong> ({successInfo.email}). Your session is active. Redirecting to workspace...
              </div>
              <div style={{ marginTop: '8px', display: 'flex', gap: '8px' }}>
                <button
                  type="button"
                  className="orca-btn orca-btn-sm orca-btn-primary"
                  onClick={() => navigate('/user/dashboard')}
                >
                  Enter Workspace Immediately →
                </button>
              </div>
            </div>
          </div>
        )}

        <form className="auth-form" onSubmit={handleSubmit} noValidate>
          {/* 1. Full Name */}
          <FormInput
            id="register-fullname"
            name="fullName"
            label="Full Legal Name"
            type="text"
            required
            value={formData.fullName}
            onChange={handleChange}
            onBlur={handleBlur}
            placeholder="Dr. Sylvia Earle"
            autoComplete="name"
            hint="Scientific and maritime communications will use this identifier."
            error={touched.fullName ? errors.fullName : ''}
            isValid={touched.fullName && !errors.fullName && formData.fullName.trim().length > 0}
            icon={
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                <circle cx="12" cy="7" r="4"></circle>
              </svg>
            }
          />

          {/* 2. Email Address */}
          <FormInput
            id="register-email"
            name="email"
            label="Scientific / Institutional Email"
            type="email"
            required
            value={formData.email}
            onChange={handleChange}
            onBlur={handleBlur}
            placeholder="sylvia.earle@deepsea.org"
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

          {/* 3. Password */}
          <FormInput
            id="register-password"
            name="password"
            label="Password"
            type="password"
            required
            value={formData.password}
            onChange={handleChange}
            onBlur={handleBlur}
            placeholder="Create a high-entropy password"
            autoComplete="new-password"
            error={touched.password ? errors.password : ''}
            isValid={touched.password && !errors.password && formData.password.length > 0}
            icon={
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
              </svg>
            }
          />

          {/* Password Strength Meter & Real-time Requirements */}
          <PasswordStrengthMeter password={formData.password} />

          {/* 4. Confirm Password */}
          <FormInput
            id="register-confirm-password"
            name="confirmPassword"
            label="Confirm Password"
            type="password"
            required
            value={formData.confirmPassword}
            onChange={handleChange}
            onBlur={handleBlur}
            placeholder="Re-enter password to confirm"
            autoComplete="new-password"
            error={touched.confirmPassword ? errors.confirmPassword : ''}
            isValid={
              touched.confirmPassword &&
              !errors.confirmPassword &&
              formData.confirmPassword.length > 0 &&
              formData.confirmPassword === formData.password
            }
            icon={
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
              </svg>
            }
          />

          {/* 5. Submit Button */}
          <Button
            id="register-submit-btn"
            type="submit"
            variant="primary"
            loading={isSubmitting}
            icon={
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                <circle cx="8.5" cy="7" r="4"></circle>
                <line x1="20" y1="8" x2="20" y2="14"></line>
                <line x1="23" y1="11" x2="17" y2="11"></line>
              </svg>
            }
          >
            Create Researcher Account
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

        {/* Client-side SPA navigation link to Login */}
        <div className="auth-switch-footer">
          <span>Already registered in the ORCA registry? </span>
          <Link
            to="/login"
            className="auth-switch-link"
            id="nav-to-login-link"
          >
            Sign in here →
          </Link>
        </div>

        {/* Scope disclaimer */}
        <div className="auth-scope-disclaimer">
          <span aria-hidden="true">ℹ️</span>
          <span>
            <strong>Production State:</strong> Registered credentials immediately initialize session token and establish WebSocket/REST connectivity to specialist agents.
          </span>
        </div>
      </div>
    </div>
  );
}
