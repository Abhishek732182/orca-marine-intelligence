import React, { useState } from 'react';
import Card from '../components/Card';
import Sidebar from '../components/Sidebar';

const ADMIN_SIDEBAR_ITEMS = [
  { id: 'cluster', label: 'Agent Cluster Health', icon: '🤖', badge: '5/5' },
  { id: 'users', label: 'Researcher Accounts', icon: '👥', badge: '42' },
  { id: 'thresholds', label: 'Hazard Thresholds', icon: '🎛️' },
  { id: 'audit', label: 'Audit Log Stream', icon: '📋' },
  { id: 'telemetry', label: 'Node Hardware', icon: '🖥️' },
];

const INITIAL_USERS = [
  {
    id: 1,
    name: 'Dr. Rachel Carson',
    email: 'rachel.carson@orca-marine.org',
    role: 'Lead Oceanographer',
    status: 'Active',
    lastActive: 'Just now',
  },
  {
    id: 2,
    name: 'Jacques-Yves Cousteau',
    email: 'j.cousteau@subsea-expeditions.org',
    role: 'Senior Marine Biologist',
    status: 'Active',
    lastActive: '14 mins ago',
  },
  {
    id: 3,
    name: 'Capt. Robert Ballard',
    email: 'r.ballard@marine-survey.gov',
    role: 'Fleet Safety Officer',
    status: 'Active',
    lastActive: '1 hour ago',
  },
  {
    id: 4,
    name: 'Dr. Sylvia Earle',
    email: 'sylvia.earle@deepsearch.org',
    role: 'Ecosystem Investigator',
    status: 'Pending Verification',
    statusClass: 'badge-amber',
    lastActive: '2 hours ago',
  },
];

const AGENT_CLUSTER = [
  {
    id: 1,
    name: 'Weather Agent',
    icon: '🌤️',
    endpoint: '/api/agents/weather/analyze',
    latency: '118 ms',
    memory: '142 MB',
    status: 'HEALTHY',
    version: 'v2.4.0',
  },
  {
    id: 2,
    name: 'Ocean Agent',
    icon: '🌊',
    endpoint: '/api/agents/ocean/analyze',
    latency: '135 ms',
    memory: '188 MB',
    status: 'HEALTHY',
    version: 'v2.4.0',
  },
  {
    id: 3,
    name: 'Fishing Zone Agent',
    icon: '🐟',
    endpoint: '/api/agents/fishing-zone/analyze',
    latency: '162 ms',
    memory: '210 MB',
    status: 'HEALTHY',
    version: 'v2.1.2',
  },
  {
    id: 4,
    name: 'Route Agent',
    icon: '🧭',
    endpoint: '/api/agents/route/analyze',
    latency: '94 ms',
    memory: '96 MB',
    status: 'HEALTHY',
    version: 'v2.3.1',
  },
  {
    id: 5,
    name: 'Safety/Risk Agent',
    icon: '🛡️',
    endpoint: '/api/agents/safety-risk/analyze',
    latency: '148 ms',
    memory: '154 MB',
    status: 'HEALTHY',
    version: 'v2.5.0',
  },
];

export default function AdminDashboard() {
  const [activeTab, setActiveTab] = useState('cluster');
  const [thresholds, setThresholds] = useState({
    maxWindKnots: 25,
    maxWaveHeightMeters: 2.8,
    reefBufferNm: 2.0,
  });
  const [adminFeedback, setAdminFeedback] = useState(null);

  const handleSaveThresholds = (e) => {
    e.preventDefault();
    setAdminFeedback({
      message: `Safety thresholds calibrated: Wind Limit=${thresholds.maxWindKnots} kts, Wave Limit=${thresholds.maxWaveHeightMeters}m, Reef Clearance=${thresholds.reefBufferNm} NM. Updated in frontend state.`,
      timestamp: new Date().toLocaleTimeString(),
    });
  };

  return (
    <div className="dashboard-workspace-body">
      {/* Sidebar */}
      <Sidebar
        title="ADMIN CONTROLS"
        items={ADMIN_SIDEBAR_ITEMS}
        activeItem={activeTab}
        onSelect={(id) => setActiveTab(id)}
      />

      {/* Main Canvas */}
      <main className="dashboard-content-canvas" id="admin-dashboard-main">
        {/* Header */}
        <div className="dashboard-page-header">
          <div>
            <span className="orca-badge badge-navy" style={{ marginBottom: '6px' }}>
              ADMINISTRATION & CLUSTER CONTROL
            </span>
            <h1 className="dashboard-page-title">Agent Network Management</h1>
            <p className="dashboard-page-desc">
              Manage multi-agent reasoning cluster services, user permissions, and maritime safety rule thresholds.
            </p>
          </div>

          <div className="dashboard-header-actions">
            <span className="orca-badge badge-emerald">
              All 5 Nodes Online (100% SLA)
            </span>
          </div>
        </div>

        {/* Feedback Alert */}
        {adminFeedback && (
          <div className="auth-alert-box success" style={{ marginBottom: '1.5rem' }}>
            <span className="alert-icon">⚙️</span>
            <div className="alert-content">
              <strong>Admin Configuration Applied ({adminFeedback.timestamp})</strong>
              <div>{adminFeedback.message}</div>
            </div>
          </div>
        )}

        {/* Top Metric Cards */}
        <div className="orca-stat-grid">
          <div className="orca-stat-card">
            <div className="orca-stat-info">
              <span className="orca-stat-label">Multi-Agent Cluster</span>
              <span className="orca-stat-value" style={{ color: 'var(--orca-teal-600)' }}>
                5 / 5
              </span>
              <span className="orca-stat-subtext text-marine-teal">
                Decentralized & Operational
              </span>
            </div>
            <div className="orca-stat-icon">🤖</div>
          </div>

          <div className="orca-stat-card">
            <div className="orca-stat-info">
              <span className="orca-stat-label">Avg Inference Latency</span>
              <span className="orca-stat-value">131 ms</span>
              <span className="orca-stat-subtext" style={{ color: 'var(--orca-success-text)' }}>
                ⚡ Optimal P95 response time
              </span>
            </div>
            <div className="orca-stat-icon">⚡</div>
          </div>

          <div className="orca-stat-card">
            <div className="orca-stat-info">
              <span className="orca-stat-label">Active Researchers</span>
              <span className="orca-stat-value">42</span>
              <span className="orca-stat-subtext text-marine-teal">
                Marine institutes & fleets
              </span>
            </div>
            <div className="orca-stat-icon">👥</div>
          </div>

          <div className="orca-stat-card">
            <div className="orca-stat-info">
              <span className="orca-stat-label">Evidence Grounding SLA</span>
              <span className="orca-stat-value">99.98%</span>
              <span className="orca-stat-subtext" style={{ color: 'var(--orca-success-text)' }}>
                Zero ungrounded hallucinations
              </span>
            </div>
            <div className="orca-stat-icon">🛡️</div>
          </div>
        </div>

        {/* Section 1: Specialist Agents Cluster Matrix */}
        <div style={{ marginBottom: '2rem' }}>
          <Card
            title="Collaborative Agent Infrastructure Status"
            subtitle="Real-time telemetry performance and memory utilization across the 5 independent agents"
            icon="🖥️"
          >
            <div className="orca-table-wrapper">
              <table className="orca-table">
                <thead>
                  <tr>
                    <th>Agent Name</th>
                    <th>API Endpoint</th>
                    <th>Version</th>
                    <th>Avg Latency</th>
                    <th>RAM Usage</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {AGENT_CLUSTER.map((agent) => (
                    <tr key={agent.id}>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 600 }}>
                          <span>{agent.icon}</span>
                          <span>{agent.name}</span>
                        </div>
                      </td>
                      <td>
                        <code style={{ fontSize: '0.78rem', background: 'var(--orca-bg-subtle)', padding: '2px 6px', borderRadius: 4, fontFamily: 'var(--font-telemetry)' }}>
                          {agent.endpoint}
                        </code>
                      </td>
                      <td style={{ fontFamily: 'var(--font-telemetry)', fontSize: '0.8rem' }}>
                        {agent.version}
                      </td>
                      <td style={{ fontFamily: 'var(--font-telemetry)', fontSize: '0.82rem', fontWeight: 600 }}>
                        {agent.latency}
                      </td>
                      <td style={{ fontFamily: 'var(--font-telemetry)', fontSize: '0.82rem' }}>
                        {agent.memory}
                      </td>
                      <td>
                        <span className="orca-badge badge-emerald">
                          {agent.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>

        {/* Section 2: Researcher User Accounts Table */}
        <div style={{ marginBottom: '2rem' }}>
          <Card
            title="Researcher Access & Fleet Credentials"
            subtitle="Registered oceanographers, marine biologists, and safety officers"
            icon="👥"
          >
            <div className="orca-table-wrapper">
              <table className="orca-table">
                <thead>
                  <tr>
                    <th>Researcher</th>
                    <th>Email Address</th>
                    <th>System Role</th>
                    <th>Status</th>
                    <th>Last Active</th>
                  </tr>
                </thead>
                <tbody>
                  {INITIAL_USERS.map((user) => (
                    <tr key={user.id}>
                      <td style={{ fontWeight: 600 }}>{user.name}</td>
                      <td style={{ color: 'var(--orca-text-secondary)', fontSize: '0.82rem' }}>
                        {user.email}
                      </td>
                      <td>
                        <span className="orca-badge badge-teal" style={{ fontSize: '0.72rem' }}>
                          {user.role}
                        </span>
                      </td>
                      <td>
                        <span
                          className={`orca-badge ${user.statusClass || 'badge-emerald'}`}
                          style={{ fontSize: '0.72rem' }}
                        >
                          {user.status}
                        </span>
                      </td>
                      <td style={{ fontSize: '0.78rem', color: 'var(--orca-text-muted)' }}>
                        {user.lastActive}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>

        {/* Section 3: Safety Rule & Threshold Calibrator */}
        <div className="dashboard-grid-2col">
          <Card
            title="Maritime Hazard Threshold Calibration"
            subtitle="Adjust operational bounds for the Safety & Risk Agent"
            icon="🎛️"
          >
            <form onSubmit={handleSaveThresholds} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              <div className="admin-control-grid">
                <div className="control-item-card">
                  <div className="control-item-title">
                    Wind Hazard Limit: <strong>{thresholds.maxWindKnots} kts</strong>
                  </div>
                  <div className="control-item-desc">
                    Triggers Beaufort scale advisory warnings when exceeded.
                  </div>
                  <input
                    type="range"
                    min="15"
                    max="45"
                    className="control-input-slider"
                    value={thresholds.maxWindKnots}
                    onChange={(e) =>
                      setThresholds({ ...thresholds, maxWindKnots: Number(e.target.value) })
                    }
                  />
                </div>

                <div className="control-item-card">
                  <div className="control-item-title">
                    Wave Height Cutoff: <strong>{thresholds.maxWaveHeightMeters} m</strong>
                  </div>
                  <div className="control-item-desc">
                    Vessel operative boundary limit for artisanal craft.
                  </div>
                  <input
                    type="range"
                    min="1.0"
                    max="5.0"
                    step="0.1"
                    className="control-input-slider"
                    value={thresholds.maxWaveHeightMeters}
                    onChange={(e) =>
                      setThresholds({ ...thresholds, maxWaveHeightMeters: Number(e.target.value) })
                    }
                  />
                </div>

                <div className="control-item-card">
                  <div className="control-item-title">
                    Shallow Reef Clearance: <strong>{thresholds.reefBufferNm} NM</strong>
                  </div>
                  <div className="control-item-desc">
                    Buffer distance for Great-Circle route waypoints.
                  </div>
                  <input
                    type="range"
                    min="0.5"
                    max="5.0"
                    step="0.5"
                    className="control-input-slider"
                    value={thresholds.reefBufferNm}
                    onChange={(e) =>
                      setThresholds({ ...thresholds, reefBufferNm: Number(e.target.value) })
                    }
                  />
                </div>
              </div>

              <button type="submit" className="orca-btn orca-btn-primary" style={{ alignSelf: 'flex-start' }}>
                Save Operational Thresholds (Frontend Preview)
              </button>
            </form>
          </Card>

          {/* Audit Trail */}
          <Card
            title="Cluster Audit Trail & Rule Triggers"
            subtitle="Immutable operational telemetry log"
            icon="📋"
          >
            <div className="event-stream-list">
              <div className="event-stream-item">
                <span className="event-icon-dot" style={{ background: 'var(--orca-teal-500)' }} />
                <div className="event-content">
                  <div className="event-content-header">
                    <span className="event-title">Weather Model Weight Sync</span>
                    <span className="event-time">10:02:11 AM</span>
                  </div>
                  <div style={{ color: 'var(--orca-text-secondary)', fontSize: '0.76rem' }}>
                    GFS and ECMWF assimilation blend completed successfully for Sector 15N 72E.
                  </div>
                </div>
              </div>

              <div className="event-stream-item">
                <span className="event-icon-dot" style={{ background: 'var(--orca-success)' }} />
                <div className="event-content">
                  <div className="event-content-header">
                    <span className="event-title">Role Granted: Lead Oceanographer</span>
                    <span className="event-time">09:15:00 AM</span>
                  </div>
                  <div style={{ color: 'var(--orca-text-secondary)', fontSize: '0.76rem' }}>
                    Dr. Rachel Carson verified for Arabian Sea observation node.
                  </div>
                </div>
              </div>

              <div className="event-stream-item">
                <span className="event-icon-dot" style={{ background: 'var(--orca-info)' }} />
                <div className="event-content">
                  <div className="event-content-header">
                    <span className="event-title">Geodesic Waypoint Re-calculation</span>
                    <span className="event-time">08:44:20 AM</span>
                  </div>
                  <div style={{ color: 'var(--orca-text-secondary)', fontSize: '0.76rem' }}>
                    Great-circle route leg updated to bypass high-traffic shipping lane.
                  </div>
                </div>
              </div>
            </div>
          </Card>
        </div>
      </main>
    </div>
  );
}
