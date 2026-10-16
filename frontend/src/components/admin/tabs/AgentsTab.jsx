import React, { useState } from 'react';
import {
  updateAgentConfiguration,
  probeSpecialistAgent,
  ADMIN_CONTRACTS,
  BASE_URL,
} from '../../../services/adminApi';

const DEFAULT_AGENTS = [
  {
    id: 'weather',
    name: 'Weather Agent',
    endpoint: '/api/agents/weather/analyze',
    method: 'POST',
    description: 'Atmospheric telemetry, wind velocity, and Beaufort scaling.',
    timeoutMs: 25000,
    modelRouting: 'deepseek-r1-marine',
    isEnabled: true,
    cacheTtlSeconds: 300,
    samplePayload: { latitude: 15.0, longitude: 72.0, location_name: 'Goa Shelf' },
  },
  {
    id: 'ocean',
    name: 'Ocean Agent',
    endpoint: '/api/agents/ocean/analyze',
    method: 'POST',
    description: 'Significant wave heights, swell direction, and WMO 3700 sea-state classification.',
    timeoutMs: 25000,
    modelRouting: 'deepseek-r1-marine',
    isEnabled: true,
    cacheTtlSeconds: 300,
    samplePayload: { latitude: 15.0, longitude: 72.0, location_name: 'Goa Shelf' },
  },
  {
    id: 'fishing_zone',
    name: 'Fishing Zone Agent',
    endpoint: '/api/agents/fishing-zone/analyze',
    method: 'POST',
    description: 'Thermal fronts, chlorophyll corridors, and artisanal vessel feasibility.',
    timeoutMs: 25000,
    modelRouting: 'llama-3.3-70b-maritime',
    isEnabled: true,
    cacheTtlSeconds: 600,
    samplePayload: { latitude: 15.0, longitude: 72.0, location_name: 'Goa Shelf' },
  },
  {
    id: 'route',
    name: 'Route Agent',
    endpoint: '/api/agents/route/analyze',
    method: 'POST',
    description: 'Great-Circle geodesic distance calculations and preliminary transit estimates.',
    timeoutMs: 25000,
    modelRouting: 'deterministic-geodesic',
    isEnabled: true,
    cacheTtlSeconds: 1800,
    samplePayload: { origin: { latitude: 15.0, longitude: 72.0 }, destination: { latitude: 18.9, longitude: 72.8 } },
  },
  {
    id: 'safety_risk',
    name: 'Safety/Risk Agent',
    endpoint: '/api/agents/safety-risk/analyze',
    method: 'POST',
    description: 'Vessel operability rules, gale force hazard evaluation, and safety bulletins.',
    timeoutMs: 25000,
    modelRouting: 'deepseek-r1-marine',
    isEnabled: true,
    cacheTtlSeconds: 120,
    samplePayload: { latitude: 15.0, longitude: 72.0, location_name: 'Goa Shelf' },
  },
  {
    id: 'orchestrator',
    name: 'Orchestrator Agent',
    endpoint: '/api/agents/orchestrator/analyze',
    method: 'POST',
    description: 'Multi-agent goal synthesis, evidence deduplication, and mission advisory.',
    timeoutMs: 40000,
    modelRouting: 'deepseek-r1-marine',
    isEnabled: true,
    cacheTtlSeconds: 0,
    samplePayload: { objective: 'all', latitude: 15.0, longitude: 72.0 },
  },
  {
    id: 'assistant',
    name: 'AI Workspace Assistant',
    endpoint: '/api/agents/assistant/chat',
    method: 'POST',
    description: 'Conversational agent execution, step-by-step planning, and tool approval workflow.',
    timeoutMs: 35000,
    modelRouting: 'gpt-4o-ocean-reasoning',
    isEnabled: true,
    cacheTtlSeconds: 0,
    samplePayload: { message: 'Verify marine conditions off Goa Shelf' },
  },
];

export default function AgentsTab({ onOpenContract }) {
  const [agents, setAgents] = useState(DEFAULT_AGENTS);
  const [probeResults, setProbeResults] = useState({});
  const [activeProbing, setActiveProbing] = useState({});
  const [persistingId, setPersistingId] = useState(null);
  const [feedback, setFeedback] = useState(null);

  const handleProbe = async (agent) => {
    setActiveProbing((prev) => ({ ...prev, [agent.id]: true }));
    try {
      const res = await probeSpecialistAgent(agent.endpoint, agent.samplePayload);
      setProbeResults((prev) => ({
        ...prev,
        [agent.id]: {
          status: 'success',
          code: res.status,
          latencyMs: res.latencyMs,
          message: 'Endpoint online & operational',
          timestamp: new Date().toLocaleTimeString(),
        },
      }));
    } catch (err) {
      setProbeResults((prev) => ({
        ...prev,
        [agent.id]: {
          status: 'error',
          code: err.status || 0,
          latencyMs: err.latencyMs || null,
          message: err.message || 'Service unreachable',
          timestamp: new Date().toLocaleTimeString(),
        },
      }));
    } finally {
      setActiveProbing((prev) => ({ ...prev, [agent.id]: false }));
    }
  };

  const handleUpdateConfig = async (agent) => {
    setPersistingId(agent.id);
    setFeedback(null);
    try {
      await updateAgentConfiguration(agent.id, {
        is_enabled: agent.isEnabled,
        timeout_ms: agent.timeoutMs,
        model_routing: agent.modelRouting,
        cache_ttl_seconds: agent.cacheTtlSeconds,
      });
      setFeedback({
        type: 'success',
        message: `Agent ${agent.name} configuration persisted successfully by backend.`,
      });
    } catch (err) {
      setFeedback({
        type: 'warning',
        message: `Unpersisted Draft Configuration: Backend returned ${
          err.status ? `HTTP ${err.status}` : 'Connection Refused'
        } for PATCH /api/admin/agents/${agent.id}. Setting is held in draft state only and will NOT affect production until backend configuration persistence is implemented.`,
      });
    } finally {
      setPersistingId(null);
    }
  };

  const handleFieldChange = (agentId, field, value) => {
    setAgents((prev) =>
      prev.map((a) => (a.id === agentId ? { ...a, [field]: value } : a))
    );
  };

  return (
    <div className="space-y-6">
      {/* Title & Actions Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight font-sans">
            Specialist Agent Management & Microservices
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 font-medium mt-0.5">
            Registry, telemetry probing, model routing, and operational timeouts for all ORCA agents.
          </p>
        </div>

        <button
          type="button"
          onClick={() => onOpenContract(ADMIN_CONTRACTS.agentManagement)}
          className="px-4 py-2 text-xs font-semibold rounded-xl bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 transition-colors flex items-center gap-2 shadow-xs shrink-0 self-start sm:self-auto cursor-pointer"
        >
          <svg className="w-4 h-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <span>Agent API Contract</span>
        </button>
      </div>

      {/* Production Persistence Integrity Banner */}
      <div className="p-4 rounded-2xl bg-slate-900 text-slate-200 border border-slate-800 text-xs space-y-2">
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-cyan-400" />
          <h3 className="font-bold text-white tracking-wide">
            Real Backend Persistence Requirement
          </h3>
        </div>
        <p className="text-slate-400 text-[11.5px] leading-relaxed">
          Agent runtime controls below dispatch real requests to <code className="text-cyan-300">PATCH /api/admin/agents/&#123;id&#125;</code>.
          ORCA never simulates fake administrative success. If the backend microservice has not yet implemented the configuration endpoint, changes are explicitly flagged as <strong>Unpersisted Drafts</strong> and will not claim to alter live routing.
        </p>
      </div>

      {/* Feedback Alert */}
      {feedback && (
        <div
          className={`p-4 rounded-xl text-xs flex items-start justify-between border ${
            feedback.type === 'success'
              ? 'bg-emerald-50 border-emerald-300 text-emerald-950'
              : 'bg-amber-50 border-amber-300 text-amber-950'
          }`}
        >
          <div className="flex items-center gap-2">
            <span>{feedback.type === 'success' ? '✓' : '⚠️'}</span>
            <span>{feedback.message}</span>
          </div>
          <button
            type="button"
            onClick={() => setFeedback(null)}
            className="text-xs font-bold ml-3 hover:opacity-75"
          >
            ✕
          </button>
        </div>
      )}

      {/* Agent Microservice Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {agents.map((agent) => {
          const probe = probeResults[agent.id];
          const isProbing = activeProbing[agent.id];
          const isPersisting = persistingId === agent.id;

          return (
            <div
              key={agent.id}
              className="bg-white border border-slate-200 rounded-2xl p-5 shadow-xs flex flex-col justify-between space-y-4 transition-all hover:border-slate-300"
            >
              <div className="space-y-3">
                {/* Header row */}
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-sm font-bold text-slate-900">{agent.name}</h3>
                      <span
                        className={`text-[10px] font-mono px-2 py-0.5 rounded-full font-bold ${
                          agent.isEnabled
                            ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                            : 'bg-slate-100 text-slate-600 border border-slate-200'
                        }`}
                      >
                        {agent.isEnabled ? 'ENABLED' : 'DISABLED'}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 mt-1 font-mono text-[11px] text-slate-600">
                      <span className="font-bold px-1.5 py-0.5 rounded bg-slate-100 text-slate-700">
                        {agent.method}
                      </span>
                      <span className="truncate">{agent.endpoint}</span>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={() => handleProbe(agent)}
                    disabled={isProbing}
                    className="px-2.5 py-1 text-[11px] font-semibold rounded-lg bg-cyan-950 text-cyan-300 hover:bg-cyan-900 border border-cyan-800 transition-colors shrink-0 disabled:opacity-50"
                  >
                    {isProbing ? 'Probing...' : 'Probe Live'}
                  </button>
                </div>

                <p className="text-xs text-slate-600 leading-relaxed">{agent.description}</p>

                {/* Probe result feedback */}
                {probe && (
                  <div
                    className={`p-2.5 rounded-xl text-[11px] font-mono flex items-center justify-between border ${
                      probe.status === 'success'
                        ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
                        : 'bg-rose-50 border-rose-200 text-rose-900'
                    }`}
                  >
                    <div className="truncate">
                      <span className="font-bold">
                        {probe.status === 'success' ? '✓ HTTP 200 OK' : `✖ ${probe.code ? `HTTP ${probe.code}` : 'OFFLINE'}`}
                      </span>{' '}
                      ({probe.latencyMs ? `${probe.latencyMs}ms` : 'unreachable'})
                    </div>
                    <span className="text-[10px] opacity-75 shrink-0 ml-2">{probe.timestamp}</span>
                  </div>
                )}

                {/* Configuration form fields */}
                <div className="grid grid-cols-2 gap-3 pt-2 text-xs">
                  <div>
                    <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                      Model Routing Engine
                    </label>
                    <select
                      value={agent.modelRouting}
                      onChange={(e) => handleFieldChange(agent.id, 'modelRouting', e.target.value)}
                      className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 text-xs font-mono bg-white text-slate-800 focus:outline-hidden"
                    >
                      <option value="deepseek-r1-marine">deepseek-r1-marine</option>
                      <option value="llama-3.3-70b-maritime">llama-3.3-70b-maritime</option>
                      <option value="gpt-4o-ocean-reasoning">gpt-4o-ocean-reasoning</option>
                      <option value="deterministic-geodesic">deterministic-geodesic</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                      Timeout Threshold (ms)
                    </label>
                    <input
                      type="number"
                      step="1000"
                      value={agent.timeoutMs}
                      onChange={(e) => handleFieldChange(agent.id, 'timeoutMs', Number(e.target.value))}
                      className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 text-xs font-mono bg-white text-slate-800 focus:outline-hidden"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                      Evidence Cache TTL (s)
                    </label>
                    <input
                      type="number"
                      step="30"
                      value={agent.cacheTtlSeconds}
                      onChange={(e) =>
                        handleFieldChange(agent.id, 'cacheTtlSeconds', Number(e.target.value))
                      }
                      className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 text-xs font-mono bg-white text-slate-800 focus:outline-hidden"
                    />
                  </div>

                  <div className="flex flex-col justify-end">
                    <label className="flex items-center gap-2 cursor-pointer pb-2">
                      <input
                        type="checkbox"
                        checked={agent.isEnabled}
                        onChange={(e) => handleFieldChange(agent.id, 'isEnabled', e.target.checked)}
                        className="rounded border-slate-300 text-cyan-600 focus:ring-0"
                      />
                      <span className="text-xs font-semibold text-slate-800">Operational Flag</span>
                    </label>
                  </div>
                </div>
              </div>

              {/* Action row */}
              <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
                <span className="text-[11px] text-slate-500 font-mono">
                  Base: {BASE_URL}
                </span>

                <button
                  type="button"
                  onClick={() => handleUpdateConfig(agent)}
                  disabled={isPersisting}
                  className="px-3 py-1.5 rounded-xl text-xs font-semibold bg-slate-900 hover:bg-slate-800 text-white transition-colors disabled:opacity-50 shadow-xs"
                >
                  {isPersisting ? 'Persisting...' : 'Apply Configuration'}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
