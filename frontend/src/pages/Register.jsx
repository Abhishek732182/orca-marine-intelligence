import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  validateFullName,
  validateEmail,
  validatePassword,
  validateConfirmPassword,
} from '../utils/validation';
import OrcaLogo from '../components/OrcaLogo';

export default function Register() {
  const navigate = useNavigate();
  const { register } = useAuth();

  const [formData, setFormData] = useState({
    fullName: '',
    email: '',
    password: '',
    confirmPassword: '',
  });

  const [errors, setErrors] = useState({});
  const [touched, setTouched] = useState({});
  const [regError, setRegError] = useState(null);
  const [successInfo, setSuccessInfo] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Calculate live password strength rating
  const getPasswordStrength = (pass) => {
    if (!pass) return { score: 0, text: 'None', color: 'bg-slate-200 text-slate-400' };
    let score = 0;
    if (pass.length >= 8) score++;
    if (/[A-Z]/.test(pass)) score++;
    if (/[0-9]/.test(pass)) score++;
    if (/[^A-Za-z0-9]/.test(pass)) score++;

    switch (score) {
      case 1:
        return { score: 1, text: 'Weak', color: 'bg-rose-500 text-rose-600' };
      case 2:
      case 3:
        return { score: 2, text: 'Moderate', color: 'bg-amber-500 text-amber-600' };
      case 4:
        return { score: 4, text: 'Strong', color: 'bg-emerald-500 text-emerald-600' };
      default:
        return { score: 1, text: 'Weak', color: 'bg-rose-500 text-rose-600' };
    }
  };

  const strength = getPasswordStrength(formData.password);

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

  const handleChange = (e) => {
    const { name, value } = e.target;
    const updatedForm = { ...formData, [name]: value };
    setFormData(updatedForm);

    if (touched[name]) {
      const errorMsg = validateField(name, value, updatedForm);
      setErrors((prev) => ({ ...prev, [name]: errorMsg }));
    }
    if (regError) setRegError(null);
  };

  const handleBlur = (e) => {
    const { name, value } = e.target;
    setTouched((prev) => ({ ...prev, [name]: true }));
    const errorMsg = validateField(name, value, formData);
    setErrors((prev) => ({ ...prev, [name]: errorMsg }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    const nameErr = validateField('fullName', formData.fullName);
    const emailErr = validateField('email', formData.email);
    const passErr = validateField('password', formData.password);
    const confirmErr = validateField('confirmPassword', formData.confirmPassword, formData);

    const newErrors = {
      fullName: nameErr,
      email: emailErr,
      password: passErr,
      confirmPassword: confirmErr,
    };
    setErrors(newErrors);
    setTouched({ fullName: true, email: true, password: true, confirmPassword: true });

    if (nameErr || emailErr || passErr || confirmErr) return;

    setIsSubmitting(true);
    setRegError(null);

    try {
      const result = await register({
        fullName: formData.fullName,
        email: formData.email,
        _password: formData.password,
      });
      if (result.success) {
        setSuccessInfo(`Account successfully registered for ${result.user.fullName}. Redirecting...`);
        setTimeout(() => {
          navigate(result.user?.role === 'admin' ? '/admin/dashboard' : '/user/dashboard', { replace: true });
        }, 600);
      }
    } catch (err) {
      setRegError(err.message || 'Registration failed. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      {/* Brand Header */}
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <OrcaLogo variant="large" className="mb-2" />
        <h2 className="auth-form-title mt-3 text-2xl font-bold tracking-tight text-slate-900">
          Create an ORCA Account
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          Join the Evidence-Grounded Marine Intelligence Workspace
        </p>
      </div>

      {/* Main Card */}
      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md px-4 sm:px-0">
        <div className="bg-white py-8 px-6 sm:px-10 shadow-sm border border-slate-200 rounded-2xl">
          {successInfo && (
            <div className="auth-alert-box success mb-5 p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 flex items-center gap-2">
              <svg className="w-4 h-4 text-emerald-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <span>{successInfo}</span>
            </div>
          )}

          {regError && (
            <div className="auth-alert-box error mb-5 p-3 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-800 flex items-center gap-2">
              <svg className="w-4 h-4 text-rose-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <span>{regError}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="register-fullname" className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                Full Name
              </label>
              <input
                id="register-fullname"
                name="fullName"
                type="text"
                value={formData.fullName}
                onChange={handleChange}
                onBlur={handleBlur}
                placeholder="Dr. Rachel Carson"
                className={`w-full px-3.5 py-2.5 rounded-xl border text-sm text-slate-900 placeholder-slate-400 focus:outline-hidden transition-colors ${
                  errors.fullName
                    ? 'border-rose-300 focus:border-rose-500 bg-rose-50/20'
                    : 'border-slate-300 focus:border-slate-800 focus:ring-1 focus:ring-slate-800'
                }`}
              />
              {errors.fullName && (
                <p id="register-fullname-error" className="mt-1 text-xs text-rose-600">
                  {errors.fullName}
                </p>
              )}
            </div>

            <div>
              <label htmlFor="register-email" className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                Email Address
              </label>
              <input
                id="register-email"
                name="email"
                type="email"
                autoComplete="email"
                value={formData.email}
                onChange={handleChange}
                onBlur={handleBlur}
                placeholder="rachel.carson@orca-marine.org"
                className={`w-full px-3.5 py-2.5 rounded-xl border text-sm text-slate-900 placeholder-slate-400 focus:outline-hidden transition-colors ${
                  errors.email
                    ? 'border-rose-300 focus:border-rose-500 bg-rose-50/20'
                    : 'border-slate-300 focus:border-slate-800 focus:ring-1 focus:ring-slate-800'
                }`}
              />
              {errors.email && (
                <p id="register-email-error" className="mt-1 text-xs text-rose-600">
                  {errors.email}
                </p>
              )}
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label htmlFor="register-password" className="block text-xs font-semibold text-slate-700 uppercase tracking-wider">
                  Password
                </label>
                {formData.password && (
                  <span className="strength-score-text text-[11px] font-medium text-slate-500">
                    Strength: {strength.text}
                  </span>
                )}
              </div>
              <input
                id="register-password"
                name="password"
                type="password"
                autoComplete="new-password"
                value={formData.password}
                onChange={handleChange}
                onBlur={handleBlur}
                placeholder="At least 8 chars with upper, number, & special"
                className={`w-full px-3.5 py-2.5 rounded-xl border text-sm text-slate-900 placeholder-slate-400 focus:outline-hidden transition-colors ${
                  errors.password
                    ? 'border-rose-300 focus:border-rose-500 bg-rose-50/20'
                    : 'border-slate-300 focus:border-slate-800 focus:ring-1 focus:ring-slate-800'
                }`}
              />
              {errors.password && (
                <p id="register-password-error" className="mt-1 text-xs text-rose-600">
                  {errors.password}
                </p>
              )}
            </div>

            <div>
              <label htmlFor="register-confirmpassword" className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                Confirm Password
              </label>
              <input
                id="register-confirmpassword"
                name="confirmPassword"
                type="password"
                autoComplete="new-password"
                value={formData.confirmPassword}
                onChange={handleChange}
                onBlur={handleBlur}
                placeholder="Repeat password"
                className={`w-full px-3.5 py-2.5 rounded-xl border text-sm text-slate-900 placeholder-slate-400 focus:outline-hidden transition-colors ${
                  errors.confirmPassword
                    ? 'border-rose-300 focus:border-rose-500 bg-rose-50/20'
                    : 'border-slate-300 focus:border-slate-800 focus:ring-1 focus:ring-slate-800'
                }`}
              />
              {errors.confirmPassword && (
                <p id="register-confirmpassword-error" className="mt-1 text-xs text-rose-600">
                  {errors.confirmPassword}
                </p>
              )}
            </div>

            <button
              id="register-submit-btn"
              type="submit"
              disabled={isSubmitting}
              className="w-full mt-2 py-2.5 px-4 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-medium text-sm transition-colors shadow-xs disabled:opacity-50"
            >
              {isSubmitting ? 'Creating Account...' : 'Complete Registration'}
            </button>
          </form>

          <div className="mt-6 text-center text-xs text-slate-500">
            Already have an account?{' '}
            <Link
              id="nav-to-login-link"
              to="/login"
              className="font-semibold text-slate-900 hover:underline"
            >
              Sign in
            </Link>
            <Link
              id="nav-link-login"
              to="/login"
              className="sr-only"
            >
              Sign in
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
