import React, { useState, useEffect } from 'react';
import {
  fetchAdminOverviewMetrics,
  pingBackendService,
  ADMIN_CONTRACTS,
} from '../../../services/adminApi';
import { OrcaCircularEmblem } from '../../OrcaLogo';

export default function OverviewTab({ onOpenContract, onNavigateTab }) {
  const [metricsState, setMetricsState] = useState({
    loading: true,
    data: null,
    error: null,
    status: null,
  });

  const [healthState, setHealthState] = useState({
    loading: true,
    isOnline: false,
    latencyMs: null,
    details: null,
    error: null,
    checkedAt: null,
  });

  const [activeTrendRange, setActiveTrendRange] = useState('7D');
  const [showContractBanner, setShowContractBanner] = useState(true);

  const loadHealth = async () => {
    setHealthState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const res = await pingBackendService();
      setHealthState({
        loading: false,
        isOnline: res.data?.status === 'ok',
        latencyMs: res.latencyMs,
        details: res.data,
        error: null,
        checkedAt: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      });
    } catch (err) {
      setHealthState({
        loading: false,
        isOnline: false,
        latencyMs: err.latencyMs || null,
        details: null,
        error: err.message || 'Service unreachable',
        checkedAt: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      });
    }
  };

  const loadMetrics = async () => {
    setMetricsState({ loading: true, data: null, error: null, status: null });
    try {
      const res = await fetchAdminOverviewMetrics();
      setMetricsState({
        loading: false,
        data: res.data,
        error: null,
        status: res.status,
      });
    } catch (err) {
      setMetricsState({
        loading: false,
        data: null,
        error: err.message || 'Failed to fetch admin metrics',
        status: err.status || 0,
      });
    }
  };

  useEffect(() => {
    loadHealth();
    loadMetrics();
  }, []);

  const handleRefresh = () => {
    loadHealth();
    loadMetrics();
  };

  const isBackendReady = Boolean(metricsState.data);

  return (
    <div className="space-y-6 max-w-full">
      {/* 1. Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 sm:w-14 sm:h-14 shrink-0 drop-shadow-md">
            <OrcaCircularEmblem className="w-full h-full" />
          </div>
          <div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight font-sans">
              ORCA Admin Console
            </h1>
            <p className="text-xs sm:text-sm text-slate-500 font-medium mt-0.5">
              Platform overview and system management
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 self-start sm:self-auto">
          {healthState.checkedAt && (
            <span className="text-xs text-slate-500 font-medium">
              Last checked: {healthState.checkedAt}
            </span>
          )}

          <button
            type="button"
            onClick={handleRefresh}
            disabled={healthState.loading || metricsState.loading}
            className="px-3.5 py-2 rounded-xl bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 font-semibold text-xs transition-all shadow-xs flex items-center gap-2 cursor-pointer disabled:opacity-50"
          >
            <svg
              className={`w-4 h-4 text-slate-600 ${healthState.loading ? 'animate-spin' : ''}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            <span>Refresh Diagnostics</span>
          </button>
        </div>
      </div>

      {/* Backend Integration Contract Callout (Honest State) */}
      {!isBackendReady && showContractBanner && (
        <div className="p-4 bg-linear-to-r from-blue-50/80 to-cyan-50/60 border border-blue-200 rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-slate-700 shadow-xs">
          <div className="flex items-center gap-3">
            <span className="w-2.5 h-2.5 rounded-full bg-blue-500 animate-pulse shrink-0" />
            <div>
              <span className="font-bold text-slate-900">
                Backend Telemetry Endpoint Missing:
              </span>{' '}
              <code className="font-mono text-blue-700 font-semibold">GET /api/admin/metrics</code> is not yet connected in FastAPI. The overview panels below display honest indicators and required schemas rather than fabricating production numbers.
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={() => onOpenContract(ADMIN_CONTRACTS.overviewMetrics)}
              className="px-3 py-1.5 rounded-xl bg-blue-700 hover:bg-blue-800 text-white font-semibold text-xs transition-colors shadow-xs cursor-pointer"
            >
              View API Contract
            </button>
            <button
              type="button"
              onClick={() => setShowContractBanner(false)}
              className="text-slate-400 hover:text-slate-600 p-1 cursor-pointer"
              title="Dismiss banner"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* 2. Top KPI Cards (5 Cards Grid with ZERO fabricated numbers) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* KPI Card 1: Total Users */}
        <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-xs flex flex-col justify-between hover:border-slate-300 transition-all">
          <div className="flex items-center justify-between">
            <div className="w-10 h-10 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center shrink-0">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
            </div>
            <svg className="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
            </svg>
          </div>
          <div className="mt-4">
            <div className="text-xs font-semibold text-slate-500">Total Users</div>
            <div className="text-2xl font-black text-slate-900 mt-1">
              {metricsState.data?.total_registered_users ?? '—'}
            </div>
            <div className="text-[11px] font-medium text-slate-400 mt-1">
              {metricsState.data ? 'Live registered accounts' : 'Awaiting backend integration'}
            </div>
          </div>
        </div>

        {/* KPI Card 2: Total Conversations */}
        <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-xs flex flex-col justify-between hover:border-slate-300 transition-all">
          <div className="flex items-center justify-between">
            <div className="w-10 h-10 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center shrink-0">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            </div>
            <svg className="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z" />
            </svg>
          </div>
          <div className="mt-4">
            <div className="text-xs font-semibold text-slate-500">Total Conversations</div>
            <div className="text-2xl font-black text-slate-900 mt-1">
              {metricsState.data?.total_agent_dispatches_24h ?? '—'}
            </div>
            <div className="text-[11px] font-medium text-slate-400 mt-1">
              {metricsState.data ? 'Live 24h dispatches' : 'Awaiting backend integration'}
            </div>
          </div>
        </div>

        {/* KPI Card 3: Agent Health */}
        <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-xs flex flex-col justify-between hover:border-slate-300 transition-all">
          <div className="flex items-center justify-between">
            <div className="w-10 h-10 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center shrink-0">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </div>
            <svg className="w-4 h-4 text-cyan-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <div className="mt-4">
            <div className="text-xs font-semibold text-slate-500">Agent Health</div>
            <div className="text-2xl font-black text-slate-900 mt-1">
              {metricsState.data?.active_agents_count != null
                ? `${metricsState.data.active_agents_count} / 6`
                : '—'}
            </div>
            <div className="text-[11px] font-medium text-slate-400 mt-1">
              {metricsState.data ? 'Active microservices' : 'Awaiting backend telemetry'}
            </div>
          </div>
        </div>

        {/* KPI Card 4: API Status */}
        <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-xs flex flex-col justify-between hover:border-slate-300 transition-all">
          <div className="flex items-center justify-between">
            <div className="w-10 h-10 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center shrink-0">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" />
              </svg>
            </div>
            <svg className="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
          </div>
          <div className="mt-4">
            <div className="text-xs font-semibold text-slate-500">API Status</div>
            <div className="text-2xl font-black text-slate-900 mt-1">
              {healthState.isOnline ? 'Online' : 'Unavailable'}
            </div>
            <div className="text-[11px] font-medium text-slate-400 mt-1">
              {healthState.isOnline ? 'Liveness verified (200 OK)' : 'Awaiting backend connection'}
            </div>
          </div>
        </div>

        {/* KPI Card 5: System Uptime */}
        <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-xs flex flex-col justify-between hover:border-slate-300 transition-all">
          <div className="flex items-center justify-between">
            <div className="w-10 h-10 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center shrink-0">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>
            <svg className="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div className="mt-4">
            <div className="text-xs font-semibold text-slate-500">System Uptime</div>
            <div className="text-2xl font-black text-slate-900 mt-1">
              {metricsState.data?.server_uptime_seconds
                ? `${Math.floor(metricsState.data.server_uptime_seconds / 3600)}h`
                : '—'}
            </div>
            <div className="text-[11px] font-medium text-slate-400 mt-1">
              {metricsState.data ? 'Aggregated server runtime' : 'Awaiting backend telemetry'}
            </div>
          </div>
        </div>
      </div>

      {/* 3. Analytics Panels Row (Honest states with zero fabricated charts) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Panel 1: User & Conversation Trends */}
        <div className="lg:col-span-5 bg-white border border-slate-200/90 rounded-2xl p-5 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between gap-2 pb-4">
              <h3 className="text-sm font-bold text-slate-900 font-sans">
                User & Conversation Trends
              </h3>
              <div className="flex items-center gap-3">
                <div className="flex items-center bg-slate-100 rounded-lg p-0.5 text-[11px] font-semibold">
                  {['7D', '30D', '90D'].map((range) => (
                    <button
                      key={range}
                      type="button"
                      onClick={() => setActiveTrendRange(range)}
                      className={`px-2 py-0.5 rounded-md transition-colors ${
                        activeTrendRange === range
                          ? 'bg-[#1E88E5] text-white shadow-xs'
                          : 'text-slate-600 hover:text-slate-900'
                      }`}
                    >
                      {range}
                    </button>
                  ))}
                </div>

                <div className="hidden sm:flex items-center gap-3 text-[11px] font-medium">
                  <span className="flex items-center gap-1.5 text-slate-600">
                    <span className="w-2 h-2 rounded-full bg-[#1E88E5]" />
                    Users
                  </span>
                  <span className="flex items-center gap-1.5 text-slate-600">
                    <span className="w-2 h-2 rounded-full bg-[#06B6D4]" />
                    Conversations
                  </span>
                </div>
              </div>
            </div>

            {/* Honest Empty Chart Container */}
            <div className="h-56 flex flex-col items-center justify-center text-center p-6 bg-slate-50/70 border border-dashed border-slate-200 rounded-xl my-2 space-y-2">
              <div className="w-10 h-10 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
                </svg>
              </div>
              <div className="text-xs font-bold text-slate-800">Historical Trend Telemetry Awaiting Backend</div>
              <p className="text-[11px] text-slate-500 max-w-sm leading-relaxed">
                Time-series aggregations for users and conversations are not published by the current backend. Connect <code className="font-mono text-slate-700">GET /api/admin/metrics</code> to render live trends without data fabrication.
              </p>
            </div>
          </div>

          <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
            <span>Awaiting telemetry aggregation</span>
            <button
              type="button"
              onClick={() => onOpenContract(ADMIN_CONTRACTS.overviewMetrics)}
              className="text-blue-600 font-semibold hover:underline cursor-pointer"
            >
              Contract Spec
            </button>
          </div>
        </div>

        {/* Panel 2: Agent Usage */}
        <div className="lg:col-span-4 bg-white border border-slate-200/90 rounded-2xl p-5 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-2">
              <h3 className="text-sm font-bold text-slate-900 font-sans">
                Agent Usage
              </h3>
              <span className="text-[11px] font-semibold text-slate-500 bg-slate-100 px-2 py-0.5 rounded-md">
                7D
              </span>
            </div>

            {/* Honest Empty Donut Container */}
            <div className="h-56 flex flex-col items-center justify-center text-center p-6 bg-slate-50/70 border border-dashed border-slate-200 rounded-xl my-2 space-y-2">
              <div className="w-10 h-10 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M11 3.055A9.001 9.001 0 1020.945 13H11V3.055z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20.488 9H15V3.512A9.025 9.025 0 0120.488 9z" />
                </svg>
              </div>
              <div className="text-xs font-bold text-slate-800">Agent Usage Distribution Unavailable</div>
              <p className="text-[11px] text-slate-500 max-w-xs leading-relaxed">
                Per-agent dispatch telemetry requires endpoint <code className="font-mono text-slate-700">GET /api/admin/metrics</code>. No mock proportions or synthetic requests are rendered.
              </p>
            </div>
          </div>

          <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
            <span>Specialist Microservices Distribution</span>
            <button
              type="button"
              onClick={() => onNavigateTab('agents')}
              className="text-blue-600 font-semibold hover:underline cursor-pointer"
            >
              Manage Agents
            </button>
          </div>
        </div>

        {/* Panel 3: System & API Health (Real health checks only) */}
        <div className="lg:col-span-3 bg-white border border-slate-200/90 rounded-2xl p-5 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3">
              <h3 className="text-sm font-bold text-slate-900 font-sans">
                System & API Health
              </h3>
              <button
                type="button"
                onClick={() => onNavigateTab('marine')}
                className="text-xs font-semibold text-blue-600 hover:text-blue-700 transition-colors cursor-pointer"
              >
                View All
              </button>
            </div>

            {/* Real Status Entries */}
            <div className="space-y-3 pt-1">
              {/* Service 1: Backend API (Real /api/health) */}
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2.5">
                  <div className="w-6 h-6 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center shrink-0">
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2" />
                    </svg>
                  </div>
                  <span className="font-semibold text-slate-800">FastAPI Backend</span>
                </div>
                <span
                  className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                    healthState.loading
                      ? 'bg-amber-100 text-amber-800 border border-amber-200'
                      : healthState.isOnline
                      ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                      : 'bg-rose-100 text-rose-800 border border-rose-200'
                  }`}
                >
                  {healthState.loading ? 'Probing...' : healthState.isOnline ? 'Healthy' : 'Offline'}
                </span>
              </div>

              {/* Service 2: Database */}
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2.5">
                  <div className="w-6 h-6 rounded-lg bg-slate-100 text-slate-600 flex items-center justify-center shrink-0">
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
                    </svg>
                  </div>
                  <span className="font-semibold text-slate-700">Database</span>
                </div>
                <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                  metricsState.data?.database_status === 'connected'
                    ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                    : 'bg-slate-100 text-slate-600 border border-slate-200'
                }`}>
                  {metricsState.data?.database_status || 'Awaiting Probe'}
                </span>
              </div>

              {/* Service 3: Open-Meteo Marine */}
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2.5">
                  <div className="w-6 h-6 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center shrink-0">
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" />
                    </svg>
                  </div>
                  <span className="font-semibold text-slate-800">Open-Meteo API</span>
                </div>
                <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                  metricsState.data?.open_meteo_status === 'healthy'
                    ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                    : 'bg-slate-100 text-slate-600 border border-slate-200'
                }`}>
                  {metricsState.data?.open_meteo_status || 'Awaiting Probe'}
                </span>
              </div>

              {/* Service 4: ECMWF API */}
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2.5">
                  <div className="w-6 h-6 rounded-lg bg-slate-100 text-slate-600 flex items-center justify-center shrink-0">
                    <span className="text-[10px] font-bold">EC</span>
                  </div>
                  <span className="font-semibold text-slate-700">ECMWF Wave Model</span>
                </div>
                <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                  metricsState.data?.ecmwf_status === 'healthy'
                    ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                    : 'bg-slate-100 text-slate-600 border border-slate-200'
                }`}>
                  {metricsState.data?.ecmwf_status || 'Awaiting Probe'}
                </span>
              </div>

              {/* Service 5: CMEMS API */}
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2.5">
                  <div className="w-6 h-6 rounded-lg bg-slate-100 text-slate-600 flex items-center justify-center shrink-0">
                    <span className="text-[10px] font-bold">CM</span>
                  </div>
                  <span className="font-semibold text-slate-700">CMEMS Satellite</span>
                </div>
                <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                  metricsState.data?.cmems_status === 'healthy'
                    ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                    : 'bg-slate-100 text-slate-600 border border-slate-200'
                }`}>
                  {metricsState.data?.cmems_status || 'Awaiting Probe'}
                </span>
              </div>

              {/* Service 6: GEBCO Data */}
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2.5">
                  <div className="w-6 h-6 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center shrink-0">
                    <span className="text-[10px] font-bold">GE</span>
                  </div>
                  <span className="font-semibold text-slate-800">GEBCO Bathymetry</span>
                </div>
                <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                  metricsState.data?.gebco_status === 'healthy'
                    ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                    : 'bg-slate-100 text-slate-600 border border-slate-200'
                }`}>
                  {metricsState.data?.gebco_status || 'Awaiting Probe'}
                </span>
              </div>
            </div>
          </div>

          <div className="pt-3 border-t border-slate-100 text-[11px] text-slate-500 flex items-center justify-between">
            <span>Provider Reachability</span>
            <span className="font-mono text-slate-600 font-bold">
              {healthState.isOnline ? 'Backend 200 OK' : 'Backend Offline'}
            </span>
          </div>
        </div>
      </div>

      {/* 4. Recent Activity Row (Honest states with zero fabricated event rows) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Panel 1: Recent System Events */}
        <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-900 font-sans">
              Recent System Events
            </h3>
            <button
              type="button"
              onClick={() => onNavigateTab('security')}
              className="text-xs font-semibold text-blue-600 hover:text-blue-700 transition-colors cursor-pointer"
            >
              View All
            </button>
          </div>

          {/* Honest Empty State */}
          <div className="py-12 text-center space-y-2 bg-slate-50/50 rounded-xl border border-slate-100">
            <div className="w-10 h-10 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center mx-auto">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div className="text-xs font-bold text-slate-800">No System Events Available</div>
            <p className="text-[11px] text-slate-500 max-w-sm mx-auto leading-relaxed">
              Live telemetry audit streaming is not currently published by the backend server. Connect <code className="font-mono text-slate-700">GET /api/admin/audit-logs</code> to stream verified events without fabrication.
            </p>
          </div>
        </div>

        {/* Panel 2: Recent Admin Actions */}
        <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-900 font-sans">
              Recent Admin Actions
            </h3>
            <button
              type="button"
              onClick={() => onNavigateTab('security')}
              className="text-xs font-semibold text-blue-600 hover:text-blue-700 transition-colors cursor-pointer"
            >
              View All
            </button>
          </div>

          {/* Honest Empty State */}
          <div className="py-12 text-center space-y-2 bg-slate-50/50 rounded-xl border border-slate-100">
            <div className="w-10 h-10 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center mx-auto">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
            </div>
            <div className="text-xs font-bold text-slate-800">No Administrative Actions Logged</div>
            <p className="text-[11px] text-slate-500 max-w-sm mx-auto leading-relaxed">
              No administrative action records have been returned from persistent audit storage. Connect <code className="font-mono text-slate-700">GET /api/admin/audit-logs</code> to record administrative audit traces.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
