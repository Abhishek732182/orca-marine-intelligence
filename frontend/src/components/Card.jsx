import React from 'react';

/**
 * Reusable Card Component adhering to ORCA Design System
 */
export default function Card({
  title,
  subtitle,
  icon,
  action,
  children,
  footer,
  className = '',
  id,
}) {
  return (
    <div className={`orca-card ${className}`} id={id}>
      {(title || action) && (
        <div className="orca-card-header">
          <div>
            <h3 className="orca-card-title">
              {icon && <span aria-hidden="true">{icon}</span>}
              <span>{title}</span>
            </h3>
            {subtitle && <p className="orca-card-subtitle">{subtitle}</p>}
          </div>
          {action && <div className="orca-card-action">{action}</div>}
        </div>
      )}

      <div className="orca-card-body">{children}</div>

      {footer && <div className="orca-card-footer">{footer}</div>}
    </div>
  );
}
