import React from 'react';

const AGENTS_LIST = [
  {
    icon: '🌤️',
    name: 'Weather Agent',
    desc: 'Atmospheric telemetry, wind velocity & Beaufort scale analysis',
  },
  {
    icon: '🌊',
    name: 'Ocean Agent',
    desc: 'Wave heights & WMO Code 3700 sea-state classification',
  },
  {
    icon: '🐟',
    name: 'Fishing Zone Agent',
    desc: 'Vessel operability & marine habitat criteria grounding',
  },
  {
    icon: '🧭',
    name: 'Route Agent',
    desc: 'Great-Circle geodesic distance & waypoint optimization',
  },
  {
    icon: '🛡️',
    name: 'Safety & Risk Agent',
    desc: 'Maritime hazard assessment & vessel risk envelope evaluation',
  },
];

export default function MarineBrandingPanel() {
  return (
    <div className="auth-branding-panel">
      <div className="branding-content">
        <div className="branding-tagline">
          <span className="branding-tagline-pulse" aria-hidden="true" />
          <span>Marine Ecosystem Research Portal</span>
        </div>

        <h2 className="branding-title">
          Evidence-Grounded <span>Ocean Intelligence</span>
        </h2>

        <p className="branding-description">
          Collaborative multi-agent reasoning architecture designed for maritime safety,
          fisheries management, and high-fidelity oceanographic telemetry analysis.
        </p>

        <div className="branding-agents-grid">
          {AGENTS_LIST.map((agent, index) => (
            <div key={index} className="agent-mini-badge">
              <div className="agent-mini-icon">{agent.icon}</div>
              <div className="agent-mini-info">
                <span className="agent-mini-name">{agent.name}</span>
                <span className="agent-mini-desc">{agent.desc}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="branding-telemetry-footer">
        <div className="telemetry-node">
          <span className="telemetry-status-dot" />
          <span>STATION // ORCA-NETWORK-PRIMARY</span>
        </div>
        <span>TELEMETRY: ACTIVE</span>
      </div>
    </div>
  );
}
