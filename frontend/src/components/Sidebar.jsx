import React from 'react';

/**
 * Reusable Sidebar Navigation Component for User & Admin Sections
 */
export default function Sidebar({
  title = 'NAVIGATION',
  items = [],
  activeItem,
  onSelect,
}) {
  return (
    <aside className="dashboard-sidebar" aria-label={title}>
      <div>
        <div className="sidebar-section-title">{title}</div>
        <nav className="sidebar-menu">
          {items.map((item) => {
            const isActive = activeItem === item.id;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => onSelect && onSelect(item.id)}
                className={`sidebar-item ${isActive ? 'active' : ''}`}
                id={`sidebar-item-${item.id}`}
              >
                <span className="sidebar-item-icon" aria-hidden="true">
                  {item.icon}
                </span>
                <span>{item.label}</span>
                {item.badge && (
                  <span className="sidebar-item-badge">{item.badge}</span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Simulated Scientific Station Telemetry Indicator */}
      <div className="sidebar-station-card">
        <div className="station-badge-row">
          <span>STATION STATUS</span>
          <span className="station-pulse-dot" />
        </div>
        <div className="station-name">ORCA Node #01</div>
        <div className="station-coords">15.000° N, 72.000° E</div>
        <div style={{ fontSize: '0.7rem', color: '#94a3b8', marginTop: '6px' }}>
          Arabian Sea Marine Corridor
        </div>
      </div>
    </aside>
  );
}
