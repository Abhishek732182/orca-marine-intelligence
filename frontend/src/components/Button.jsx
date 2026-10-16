import React from 'react';

/**
 * Reusable Button Component for ORCA Marine Intelligence
 * Includes loading spinner and interactive hover/focus states.
 */
export default function Button({
  id,
  type = 'button',
  variant = 'primary',
  disabled = false,
  loading = false,
  children,
  onClick,
  className = '',
  icon,
}) {
  const isActionDisabled = disabled || loading;

  return (
    <button
      id={id}
      type={type}
      disabled={isActionDisabled}
      onClick={onClick}
      className={`orca-btn-${variant} ${className}`}
      aria-busy={loading}
    >
      {loading ? (
        <>
          <span className="orca-spinner" aria-hidden="true" />
          <span>Verifying Inputs...</span>
        </>
      ) : (
        <>
          {icon && <span className="btn-icon" aria-hidden="true">{icon}</span>}
          <span>{children}</span>
        </>
      )}
    </button>
  );
}
