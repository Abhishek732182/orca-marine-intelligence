import React, { useState } from 'react';
import Card from '../components/Card';
import Sidebar from '../components/Sidebar';
import AssistantWorkspace from '../components/AssistantWorkspace';
import MarineMap from '../components/MarineMap';
import WeatherSection from '../components/WeatherSection';
import OceanSection from '../components/OceanSection';
import FishingZoneSection from '../components/FishingZoneSection';
import RouteSection from '../components/RouteSection';
import SafetyRiskSection from '../components/SafetyRiskSection';

const USER_SIDEBAR_ITEMS = [
  { id: 'assistant', label: 'AI Chat Assistant', icon: '🤖', badge: 'Agent 6' },
  { id: 'map', label: 'Geospatial Radar Map', icon: '🧭', badge: 'Live Chart' },
  { id: 'overview', label: 'Ecosystem Telemetry', icon: '🌊', badge: '5 Agents' },
  { id: 'weather', label: 'Atmospheric & Wind', icon: '🌤️' },
  { id: 'ocean', label: 'Sea State & Waves', icon: '🌀' },
  { id: 'fisheries', label: 'Fishing Habitats', icon: '🐟' },
  { id: 'routes', label: 'Geodesic Navigation', icon: '🧭' },
  { id: 'safety', label: 'Vessel Risk Matrix', icon: '🛡️' },
];

export default function UserDashboard() {
  const [activeTab, setActiveTab] = useState('assistant');
  const [selectedFilter, setSelectedFilter] = useState('all');
  const [queryCoordinates, setQueryCoordinates] = useState({ lat: 15.00, lon: 72.00, sector: 'Goa Coastal Shelf' });
  const [queryFeedback, setQueryFeedback] = useState(null);

  const handleSimulateQuery = (e) => {
    e.preventDefault();
    setQueryFeedback({
      message: `Simulated observations retrieved for Sector ${queryCoordinates.sector} (${queryCoordinates.lat}° N, ${queryCoordinates.lon}° E). Open-Meteo ECMWF wave models synced.`,
      timestamp: new Date().toLocaleTimeString(),
    });
  };

  const handleMapCoordSelect = (coords) => {
    setQueryCoordinates(coords);
    setQueryFeedback({
      message: `Selected coordinates updated from Nautical Map: ${coords.lat}°N, ${coords.lon}°E (${coords.sector || 'Custom Vector'}).`,
      timestamp: new Date().toLocaleTimeString(),
    });
  };

  const handleMapQueryAction = (coords) => {
    setQueryCoordinates(coords);
    setActiveTab('assistant');
  };

  const activeStreamCount = selectedFilter === 'all' ? 5 : 1;

  return (
    <div className="dashboard-workspace-body">
      {/* Sidebar Navigation */}
      <Sidebar
        title="RESEARCH PORTAL"
        items={USER_SIDEBAR_ITEMS}
        activeItem={activeTab}
        onSelect={(id) => {
          setActiveTab(id);
          if (id === 'overview') setSelectedFilter('all');
          else if (['weather', 'ocean', 'fisheries', 'routes', 'safety'].includes(id)) {
            setSelectedFilter(id);
          }
        }}
      />

      {/* Main Content Area */}
      <main className="dashboard-content-canvas" id="user-dashboard-main">
        {/* Header Bar */}
        <div className="dashboard-page-header">
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
              <span className="orca-badge badge-teal">RESEARCHER WORKSPACE</span>
              <span className="orca-badge badge-cyan">FASTAPI & OPEN-METEO BACKED</span>
            </div>
            <h1 className="dashboard-page-title">ORCA Marine Intelligence Console</h1>
            <p className="dashboard-page-desc">
              Conversational reasoning agent, geospatial nautical radar chart, and multi-agent oceanographic telemetry.
            </p>
          </div>

          {/* Primary View Switcher Tabs */}
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            <button
              type="button"
              className={`orca-btn ${activeTab === 'assistant' ? 'orca-btn-primary' : 'orca-btn-secondary'}`}
              style={{ fontSize: '0.82rem' }}
              onClick={() => setActiveTab('assistant')}
            >
              💬 AI Chat & Agents
            </button>
            <button
              type="button"
              className={`orca-btn ${activeTab === 'map' ? 'orca-btn-primary' : 'orca-btn-secondary'}`}
              style={{ fontSize: '0.82rem' }}
              onClick={() => setActiveTab('map')}
            >
              🧭 Nautical Radar Map
            </button>
            <button
              type="button"
              className={`orca-btn ${['overview', 'weather', 'ocean', 'fisheries', 'routes', 'safety'].includes(activeTab) ? 'orca-btn-primary' : 'orca-btn-secondary'}`}
              style={{ fontSize: '0.82rem' }}
              onClick={() => {
                setActiveTab('overview');
                setSelectedFilter('all');
              }}
            >
              📊 Specialist Grid
            </button>
          </div>
        </div>

        {/* Top Metric Cards */}
        <div className="orca-stat-grid">
          <div className="orca-stat-card">
            <div className="orca-stat-info">
              <span className="orca-stat-label">Sea State (WMO 3700)</span>
              <span className="orca-stat-value">Code 3</span>
              <span className="orca-stat-subtext text-marine-teal">
                Wave Ht: 1.4m • Moderate
              </span>
            </div>
            <div className="orca-stat-icon">🌊</div>
          </div>

          <div className="orca-stat-card">
            <div className="orca-stat-info">
              <span className="orca-stat-label">Wind Velocity</span>
              <span className="orca-stat-value">14.8 kts</span>
              <span className="orca-stat-subtext text-marine-teal">
                Beaufort Force 4 • Steady
              </span>
            </div>
            <div className="orca-stat-icon">🌤️</div>
          </div>

          <div className="orca-stat-card">
            <div className="orca-stat-info">
              <span className="orca-stat-label">Geodesic Transit</span>
              <span className="orca-stat-value">282.4 NM</span>
              <span className="orca-stat-subtext text-marine-teal">
                Bearing 163.5° • Goa Shelf
              </span>
            </div>
            <div className="orca-stat-icon">🧭</div>
          </div>

          <div className="orca-stat-card">
            <div className="orca-stat-info">
              <span className="orca-stat-label">Vessel Risk Index</span>
              <span className="orca-stat-value" style={{ color: 'var(--orca-success)' }}>
                0.18
              </span>
              <span className="orca-stat-subtext" style={{ color: 'var(--orca-success-text)' }}>
                ✓ Safe Operational Envelope
              </span>
            </div>
            <div className="orca-stat-icon">🛡️</div>
          </div>
        </div>

        {/* Tab View 1: Conversational AI Assistant & Agent Selector */}
        {activeTab === 'assistant' && (
          <div style={{ marginBottom: '24px' }}>
            <AssistantWorkspace
              onSwitchToSpecialists={() => {
                setActiveTab('overview');
                setSelectedFilter('all');
              }}
            />
          </div>
        )}

        {/* Tab View 2: Geospatial Nautical Radar Map */}
        {activeTab === 'map' && (
          <div style={{ marginBottom: '24px' }}>
            <MarineMap
              selectedCoords={queryCoordinates}
              onSelectCoords={handleMapCoordSelect}
              onQueryAgent={handleMapQueryAction}
            />
          </div>
        )}

        {/* Tab View 3: Specialist Telemetry Grid & Coordinate Simulator */}
        {(['overview', 'weather', 'ocean', 'fisheries', 'routes', 'safety'].includes(activeTab) || activeTab === 'map') && (
          <>
            {/* Filter Bar */}
            <div className="dashboard-filter-bar">
              <div className="filter-pills-group">
                <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--orca-text-muted)' }}>
                  Filter Specialists:
                </span>
                {[
                  { id: 'all', label: 'All 5 Specialists' },
                  { id: 'weather', label: '🌤️ Weather' },
                  { id: 'ocean', label: '🌊 Ocean' },
                  { id: 'fisheries', label: '🐟 Fisheries' },
                  { id: 'routes', label: '🧭 Routes' },
                  { id: 'safety', label: '🛡️ Safety/Risk' },
                ].map((f) => (
                  <button
                    key={f.id}
                    type="button"
                    className={`filter-pill-btn ${selectedFilter === f.id ? 'active' : ''}`}
                    onClick={() => {
                      setSelectedFilter(f.id);
                      if (f.id !== 'all') setActiveTab(f.id);
                      else setActiveTab('overview');
                    }}
                  >
                    {f.label}
                  </button>
                ))}
              </div>

              <div style={{ fontSize: '0.78rem', color: 'var(--orca-text-muted)' }}>
                Showing <strong>{activeStreamCount}</strong> active telemetry stream{activeStreamCount > 1 ? 's' : ''}
              </div>
            </div>

            {/* Live Specialist Telemetry Components */}
            <div className="live-specialists-container" style={{ display: 'flex', flexDirection: 'column', gap: '24px', marginBottom: '24px' }}>
              {(selectedFilter === 'all' || selectedFilter === 'weather') && <WeatherSection />}
              {(selectedFilter === 'all' || selectedFilter === 'ocean') && <OceanSection />}
              {(selectedFilter === 'all' || selectedFilter === 'fisheries') && <FishingZoneSection />}
              {(selectedFilter === 'all' || selectedFilter === 'routes') && <RouteSection />}
              {(selectedFilter === 'all' || selectedFilter === 'safety') && <SafetyRiskSection />}
            </div>

            {/* 2-Column Section: Coordinates Query & Live Observation Logs */}
            <div className="dashboard-grid-2col">
              {/* Query Coordinates Card */}
              <Card
                title="Coordinate-Grounded Telemetry Query"
                subtitle="Simulate real-time evidence generation for coastal maritime sectors"
                icon="📍"
              >
                {queryFeedback && (
                  <div className="auth-alert-box info" style={{ marginBottom: '1rem' }}>
                    <span className="alert-icon">ℹ️</span>
                    <div className="alert-content">
                      <strong>Observation Synchronized ({queryFeedback.timestamp})</strong>
                      <div>{queryFeedback.message}</div>
                    </div>
                  </div>
                )}

                <form onSubmit={handleSimulateQuery} style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                    <div className="form-group">
                      <label className="form-label" htmlFor="user-query-lat">Latitude (°N)</label>
                      <input
                        id="user-query-lat"
                        className="form-input"
                        style={{ paddingLeft: '0.85rem' }}
                        value={queryCoordinates.lat}
                        onChange={(e) => setQueryCoordinates({ ...queryCoordinates, lat: parseFloat(e.target.value) || 0 })}
                      />
                    </div>
                    <div className="form-group">
                      <label className="form-label" htmlFor="user-query-lon">Longitude (°E)</label>
                      <input
                        id="user-query-lon"
                        className="form-input"
                        style={{ paddingLeft: '0.85rem' }}
                        value={queryCoordinates.lon}
                        onChange={(e) => setQueryCoordinates({ ...queryCoordinates, lon: parseFloat(e.target.value) || 0 })}
                      />
                    </div>
                  </div>

                  <div className="form-group">
                    <label className="form-label" htmlFor="user-query-sector">Coastal Sector Identifier</label>
                    <input
                      id="user-query-sector"
                      className="form-input"
                      style={{ paddingLeft: '0.85rem' }}
                      value={queryCoordinates.sector}
                      onChange={(e) => setQueryCoordinates({ ...queryCoordinates, sector: e.target.value })}
                    />
                  </div>

                  <button type="submit" className="orca-btn orca-btn-primary" style={{ marginTop: '0.5rem' }}>
                    Query Evidence Grounding ➜
                  </button>
                </form>
              </Card>

              {/* Recent Agent Reasoning Stream */}
              <Card
                title="Evidence Grounding Activity"
                subtitle="Recent multi-agent reasoning iterations & hazard checks"
                icon="📡"
              >
                <div className="event-stream-list">
                  <div className="event-stream-item">
                    <span className="event-icon-dot" style={{ background: 'var(--orca-success)' }} />
                    <div className="event-content">
                      <div className="event-content-header">
                        <span className="event-title">Route Leg Bearing Verified</span>
                        <span className="event-time">10:04:12 AM</span>
                      </div>
                      <div style={{ color: 'var(--orca-text-secondary)', fontSize: '0.76rem' }}>
                        Great-circle path clearance verified against shallow reef hazard limits.
                      </div>
                    </div>
                  </div>

                  <div className="event-stream-item">
                    <span className="event-icon-dot" style={{ background: 'var(--orca-teal-500)' }} />
                    <div className="event-content">
                      <div className="event-content-header">
                        <span className="event-title">Wave Spectral Model Synced</span>
                        <span className="event-time">09:58:30 AM</span>
                      </div>
                      <div style={{ color: 'var(--orca-text-secondary)', fontSize: '0.76rem' }}>
                        WMO Code 3700 state 3 confirmed. Average wave height: 1.4m.
                      </div>
                    </div>
                  </div>

                  <div className="event-stream-item">
                    <span className="event-icon-dot" style={{ background: 'var(--orca-warning)' }} />
                    <div className="event-content">
                      <div className="event-content-header">
                        <span className="event-title">Artisanal Vessel Advisory</span>
                        <span className="event-time">09:42:15 AM</span>
                      </div>
                      <div style={{ color: 'var(--orca-text-secondary)', fontSize: '0.76rem' }}>
                        Wind gusts approaching 16 knots near headlands; cautionary advisory posted.
                      </div>
                    </div>
                  </div>
                </div>
              </Card>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
