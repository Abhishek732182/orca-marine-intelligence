import React, { useState } from 'react';
import Navbar from './components/Navbar';
import WeatherSection from './components/WeatherSection';
import OceanSection from './components/OceanSection';
import FishingZoneSection from './components/FishingZoneSection';
import RouteSection from './components/RouteSection';
import SafetyRiskSection from './components/SafetyRiskSection';
import AssistantWorkspace from './components/AssistantWorkspace';

const AGENTS = [
  {
    id: 'weather',
    num: 1,
    name: 'Weather Agent',
    icon: '🌤️',
    endpoint: '/api/agents/weather/analyze',
    desc: 'Atmospheric telemetry, wind, Beaufort scale, precipitation',
  },
  {
    id: 'ocean',
    num: 2,
    name: 'Ocean Agent',
    icon: '🌊',
    endpoint: '/api/agents/ocean/analyze',
    desc: 'Wave heights, WMO Code 3700 sea-state classification',
  },
  {
    id: 'fishing_zone',
    num: 3,
    name: 'Fishing Zone Agent',
    icon: '🐟',
    endpoint: '/api/agents/fishing-zone/analyze',
    desc: 'Vessel operability & fisheries criteria grounding',
  },
  {
    id: 'route',
    num: 4,
    name: 'Route Agent',
    icon: '🧭',
    endpoint: '/api/agents/route/analyze',
    desc: 'Great-Circle geodesic distance, leg bearings & waypoints',
  },
  {
    id: 'safety_risk',
    num: 5,
    name: 'Safety/Risk Agent',
    icon: '🛡️',
    endpoint: '/api/agents/safety-risk/analyze',
    desc: 'Documented hazard rules, vessel limits & decision support',
  },
];

export default function App() {
  const [workspaceMode, setWorkspaceMode] = useState('assistant'); // 'assistant' or 'specialists'
  const [activeTab, setActiveTab] = useState('weather');
  const [viewMode, setViewMode] = useState('single'); // 'single' or 'all'

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', background: '#FFFFFF' }}>
      <Navbar onToggleView={() => setWorkspaceMode(workspaceMode === 'assistant' ? 'specialists' : 'assistant')} currentView={workspaceMode} />

      {/* Top Workspace Navigation Switcher */}
      <div
        style={{
          borderBottom: '1px solid #E5E7EB',
          background: '#F9FAFB',
          padding: '8px 24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '10px',
        }}
      >
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          <button
            onClick={() => setWorkspaceMode('assistant')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '7px 16px',
              borderRadius: '6px',
              background: workspaceMode === 'assistant' ? '#EFF6FF' : '#FFFFFF',
              border: `1px solid ${workspaceMode === 'assistant' ? '#2563EB' : '#E5E7EB'}`,
              color: workspaceMode === 'assistant' ? '#2563EB' : '#4B5563',
              fontWeight: 600,
              fontSize: '0.84rem',
              cursor: 'pointer',
              boxShadow: 'var(--shadow-subtle)',
              transition: 'all 0.15s ease',
            }}
          >
            <span>💬</span> AI Workspace Assistant (Agent 6)
          </button>

          <button
            onClick={() => setWorkspaceMode('specialists')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '7px 16px',
              borderRadius: '6px',
              background: workspaceMode === 'specialists' ? '#EFF6FF' : '#FFFFFF',
              border: `1px solid ${workspaceMode === 'specialists' ? '#2563EB' : '#E5E7EB'}`,
              color: workspaceMode === 'specialists' ? '#2563EB' : '#4B5563',
              fontWeight: 600,
              fontSize: '0.84rem',
              cursor: 'pointer',
              boxShadow: 'var(--shadow-subtle)',
              transition: 'all 0.15s ease',
            }}
          >
            <span>🧭</span> Specialist Agents Dashboard (1–5)
          </button>
        </div>

        {workspaceMode === 'specialists' && (
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={() => setViewMode('single')}
              className="btn-preset"
              style={{
                background: viewMode === 'single' ? '#EFF6FF' : '#FFFFFF',
                borderColor: viewMode === 'single' ? '#2563EB' : '#E5E7EB',
                color: viewMode === 'single' ? '#2563EB' : '#4B5563',
                fontSize: '0.8rem',
                fontWeight: 600,
              }}
            >
              Tabbed View
            </button>
            <button
              onClick={() => setViewMode('all')}
              className="btn-preset"
              style={{
                background: viewMode === 'all' ? '#EFF6FF' : '#FFFFFF',
                borderColor: viewMode === 'all' ? '#2563EB' : '#E5E7EB',
                color: viewMode === 'all' ? '#2563EB' : '#4B5563',
                fontSize: '0.8rem',
                fontWeight: 600,
              }}
            >
              View All 5 Agents
            </button>
          </div>
        )}
      </div>

      {/* Main Workspace Body */}
      {workspaceMode === 'assistant' ? (
        <main style={{ width: '100%', flex: 1, display: 'flex' }}>
          <AssistantWorkspace onSwitchToSpecialists={() => setWorkspaceMode('specialists')} />
        </main>
      ) : (
        <main style={{ maxWidth: '1280px', margin: '0 auto', width: '100%', padding: '24px', flex: 1 }}>
          {/* Architecture Notice Banner */}
          <div
            style={{
              background: '#F9FAFB',
              border: '1px solid #E5E7EB',
              borderRadius: 'var(--radius-md)',
              padding: '16px 20px',
              marginBottom: '24px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '12px',
              boxShadow: 'var(--shadow-subtle)',
            }}
          >
            <div>
              <span style={{ fontSize: '0.74rem', fontWeight: 700, color: '#2563EB', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                System Specification
              </span>
              <p style={{ fontSize: '0.85rem', color: '#374151', marginTop: '2px' }}>
                Five completely independent, modular AI agents. Each possesses dedicated business logic, Pydantic schemas, and FastAPI endpoints.
                <strong> Zero master agent or orchestrator dependency.</strong>
              </p>
            </div>
          </div>

          {/* Agent Navigation Tabs */}
          {viewMode === 'single' && (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))',
                gap: '12px',
                marginBottom: '24px',
              }}
            >
              {AGENTS.map((agent) => {
                const isActive = activeTab === agent.id;
                return (
                  <button
                    key={agent.id}
                    onClick={() => setActiveTab(agent.id)}
                    style={{
                      background: isActive ? '#EFF6FF' : '#FFFFFF',
                      border: `1px solid ${isActive ? '#2563EB' : '#E5E7EB'}`,
                      borderRadius: 'var(--radius-md)',
                      padding: '14px 16px',
                      textAlign: 'left',
                      cursor: 'pointer',
                      transition: 'all 0.15s ease',
                      boxShadow: 'var(--shadow-subtle)',
                      position: 'relative',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                      <span style={{ fontSize: '1.3rem' }}>{agent.icon}</span>
                      <span
                        style={{
                          fontSize: '0.68rem',
                          fontFamily: 'var(--font-mono)',
                          color: isActive ? '#2563EB' : '#9CA3AF',
                          fontWeight: 600,
                        }}
                      >
                        Agent #{agent.num}
                      </span>
                    </div>
                    <div
                      style={{
                        fontFamily: 'var(--font-heading)',
                        fontSize: '0.94rem',
                        fontWeight: 700,
                        color: isActive ? '#2563EB' : '#202123',
                        marginBottom: '3px',
                      }}
                    >
                      {agent.name}
                    </div>
                    <div style={{ fontSize: '0.74rem', color: '#6B7280', lineHeight: '1.35' }}>
                      {agent.desc}
                    </div>
                  </button>
                );
              })}
            </div>
          )}

          {/* Agent Section Views */}
          {viewMode === 'single' ? (
            <div>
              {activeTab === 'weather' && <WeatherSection />}
              {activeTab === 'ocean' && <OceanSection />}
              {activeTab === 'fishing_zone' && <FishingZoneSection />}
              {activeTab === 'route' && <RouteSection />}
              {activeTab === 'safety_risk' && <SafetyRiskSection />}
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
              <WeatherSection />
              <OceanSection />
              <FishingZoneSection />
              <RouteSection />
              <SafetyRiskSection />
            </div>
          )}
        </main>
      )}

      {/* Footer */}
      <footer
        style={{
          borderTop: '1px solid #E5E7EB',
          padding: '18px 24px',
          background: '#F9FAFB',
          marginTop: 'auto',
          fontSize: '0.78rem',
          color: '#6B7280',
        }}
      >
        <div
          style={{
            maxWidth: '1280px',
            margin: '0 auto',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '12px',
          }}
        >
          <div>
            <strong style={{ color: '#202123' }}>ORCA Marine Intelligence</strong> • 6 AI Agents Architecture (5 Specialists + AI Workspace Assistant)
          </div>
          <div style={{ display: 'flex', gap: '16px', fontSize: '0.74rem' }}>
            <span>Providers: Open-Meteo Marine & Weather API</span>
            <span>Standards: WMO Code Table 3700 / Beaufort Scale</span>
            <span>Geodesics: Great-Circle Haversine</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
