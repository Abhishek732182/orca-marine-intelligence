import React from 'react';

/**
 * Real-time Password Strength Meter & Regex Criteria Checklist
 */
export default function PasswordStrengthMeter({ password = '' }) {
  if (!password) {
    return null;
  }

  const checks = [
    { label: 'At least 8 characters', met: password.length >= 8 },
    { label: 'One uppercase letter (A-Z)', met: /[A-Z]/.test(password) },
    { label: 'One lowercase letter (a-z)', met: /[a-z]/.test(password) },
    { label: 'One numeric digit (0-9)', met: /\d/.test(password) },
    {
      label: 'One special character (@$!%*?&...)',
      met: /[@$!%*?&#^()_+\-=[\]{}|;:,.<>]/.test(password),
    },
  ];

  const metCount = checks.filter((c) => c.met).length;

  let strengthLabel = 'Weak';
  let strengthClass = 'weak';

  if (metCount >= 5) {
    strengthLabel = 'Strong';
    strengthClass = 'strong';
  } else if (metCount >= 4) {
    strengthLabel = 'Good';
    strengthClass = 'good';
  } else if (metCount >= 2) {
    strengthLabel = 'Fair';
    strengthClass = 'fair';
  }

  return (
    <div className="password-strength-container" aria-live="polite">
      <div className="strength-header">
        <span className="strength-label">Password Strength:</span>
        <span className={`strength-score-text ${strengthClass}`}>{strengthLabel}</span>
      </div>

      <div className="strength-meter-bar" role="progressbar" aria-valuenow={metCount} aria-valuemin={0} aria-valuemax={5}>
        <div className={`strength-bar-segment ${metCount >= 1 ? `filled-${strengthClass}` : ''}`} />
        <div className={`strength-bar-segment ${metCount >= 2 ? `filled-${strengthClass}` : ''}`} />
        <div className={`strength-bar-segment ${metCount >= 4 ? `filled-${strengthClass}` : ''}`} />
        <div className={`strength-bar-segment ${metCount === 5 ? `filled-${strengthClass}` : ''}`} />
      </div>

      <div className="strength-checklist">
        {checks.map((item, idx) => (
          <div key={idx} className={`requirement-item ${item.met ? 'met' : ''}`}>
            <span className="req-icon" aria-hidden="true">
              {item.met ? '✓' : '•'}
            </span>
            <span>{item.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
