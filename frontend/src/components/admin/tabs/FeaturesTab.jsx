import React, { useState } from 'react';
import { updateFeatureFlag, ADMIN_CONTRACTS } from '../../../services/adminApi';

const DEFAULT_FEATURE_FLAGS = [
  {
    key: 'autonomous_tool_execution',
    name: 'Autonomous Diagnostic Tool Execution',
    description: 'Allows the AI Workspace Assistant to run read-only telemetry queries without blocking for manual human confirmation.',
    isEnabled: false,
    rolloutPercentage: 0,
    environment: 'production',
    allowedRoles: ['admin', 'oceanographer'],
  },
  {
    key: 'strict_marine_bounding_box',
    name: 'Strict Marine Bounding Box Enforcement',
    description: 'Immediately flags terrestrial inland coordinates with insufficient evidence, halting synthetic data generation.',
    isEnabled: true,
    rolloutPercentage: 100,
    environment: 'production',
    allowedRoles: ['all'],
  },
  {
    key: 'great_circle_geodesic_routing',
    name: 'Great-Circle Navigational Routing Channel Estimation',
    description: 'Enables preliminary geodesic distance computations while requiring explicit straight-line hazard disclaimers.',
    isEnabled: true,
    rolloutPercentage: 100,
    environment: 'production',
    allowedRoles: ['all'],
  },
  {
    key: 'wmo_3700_deterministic_sea_state',
    name: 'WMO 3700 Deterministic Sea State Standard',
    description: 'Forces all wave and swell telemetry through the World Meteorological Organization Code Table 3700 rule engine.',
    isEnabled: true,
    rolloutPercentage: 100,
    environment: 'production',
    allowedRoles: ['all'],
  },
  {
    key: 'artisanal_fisheries_advisories',
    name: 'Artisanal Fisheries Coastal Safety Alerts',
    description: 'Generates specialized sea condition warnings tailored for traditional non-motorized and small coastal vessels.',
    isEnabled: true,
    rolloutPercentage: 100,
    environment: 'production',
    allowedRoles: ['all'],
  },
  {
    key: 'evidence_deduplication_engine',
    name: 'Multi-Agent Evidence Deduplication Engine',
    description: 'Coalesces overlapping observations from multiple agents into single authoritative evidence records.',
    isEnabled: true,
    rolloutPercentage: 100,
    environment: 'production',
    allowedRoles: ['all'],
  },
];

export default function FeaturesTab({ onOpenContract }) {
  const [flags, setFlags] = useState(DEFAULT_FEATURE_FLAGS);
  const [dirtyKeys, setDirtyKeys] = useState(new Set());
  const [confirmModal, setConfirmModal] = useState(null);
  const [savingKey, setSavingKey] = useState(null);
  const [feedback, setFeedback] = useState(null);

  const handleToggle = (key) => {
    setFlags((prev) =>
      prev.map((f) => (f.key === key ? { ...f, isEnabled: !f.isEnabled } : f))
    );
    setDirtyKeys((prev) => new Set(prev).add(key));
  };

  const handleRolloutChange = (key, value) => {
    setFlags((prev) =>
      prev.map((f) => (f.key === key ? { ...f, rolloutPercentage: Number(value) } : f))
    );
    setDirtyKeys((prev) => new Set(prev).add(key));
  };

  const promptSync = (flag) => {
    setConfirmModal(flag);
  };

  const executePersistFlag = async (flag) => {
    setConfirmModal(null);
    setSavingKey(flag.key);
    setFeedback(null);
    try {
      await updateFeatureFlag(flag.key, {
        is_enabled: flag.isEnabled,
        rollout_percentage: flag.rolloutPercentage,
        environment: flag.environment,
      });
      setFeedback({
        type: 'success',
        message: `Feature flag '${flag.name}' persisted successfully by backend.`,
      });
      setDirtyKeys((prev) => {
        const next = new Set(prev);
        next.delete(flag.key);
        return next;
      });
    } catch (err) {
      setFeedback({
        type: 'warning',
        message: `Unpersisted Draft State: Backend returned ${
          err.status ? `HTTP ${err.status}` : 'Connection Refused'
        } for PATCH /api/admin/features/${flag.key}. This flag is held in client draft memory only and will NOT change live production behavior until enforced by backend feature flag storage.`,
      });
    } finally {
      setSavingKey(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Title & Actions Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight font-sans">
            Platform Feature Management & Flags
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 font-medium mt-0.5">
            Control progressive rollouts, experimental AI capabilities, and maritime safety gates.
          </p>
        </div>

        <button
          type="button"
          onClick={() => onOpenContract(ADMIN_CONTRACTS.featureManagement)}
          className="px-4 py-2 text-xs font-semibold rounded-xl bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 transition-colors flex items-center gap-2 shadow-xs shrink-0 self-start sm:self-auto cursor-pointer"
        >
          <svg className="w-4 h-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <span>Feature Flags Contract</span>
        </button>
      </div>

      {/* Production Persistence Integrity Banner */}
      <div className="p-4 rounded-2xl bg-slate-900 text-slate-200 border border-slate-800 text-xs space-y-2">
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-cyan-400" />
          <h3 className="font-bold text-white tracking-wide">
            Feature Flag Enforcement Integrity
          </h3>
        </div>
        <p className="text-slate-400 text-[11.5px] leading-relaxed">
          Toggling a feature flag here dispatches a real mutation to <code className="text-cyan-300">PATCH /api/admin/features/&#123;key&#125;</code>.
          If the backend returns HTTP 404 or fails to respond, ORCA explicitly marks the setting as an <strong>Unpersisted Draft</strong>, preventing false claims that production capabilities have shifted.
        </p>
      </div>

      {/* Feedback Banner */}
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

      {/* Feature Flags Cards */}
      <div className="space-y-4">
        {flags.map((flag) => {
          const isSaving = savingKey === flag.key;
          const isDirty = dirtyKeys.has(flag.key);

          return (
            <div
              key={flag.key}
              className={`bg-white border rounded-2xl p-5 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4 transition-all hover:border-slate-300 ${
                isDirty ? 'border-amber-300 bg-amber-50/20' : 'border-slate-200'
              }`}
            >
              <div className="space-y-1.5 max-w-xl">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-sm font-bold text-slate-900">{flag.name}</h3>
                  <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-semibold">
                    {flag.key}
                  </span>
                  <span
                    className={`font-mono text-[10px] px-2 py-0.5 rounded-full font-bold ${
                      flag.isEnabled
                        ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                        : 'bg-slate-100 text-slate-600 border border-slate-200'
                    }`}
                  >
                    {flag.isEnabled ? 'ENABLED' : 'DISABLED'}
                  </span>
                  {isDirty && (
                    <span className="font-mono text-[10px] px-2 py-0.5 rounded-full font-bold bg-amber-100 text-amber-800 border border-amber-300 animate-pulse">
                      UNSAVED DRAFT
                    </span>
                  )}
                </div>
                <p className="text-xs text-slate-600 leading-relaxed">{flag.description}</p>
                <div className="flex items-center gap-3 text-[11px] text-slate-500 pt-1">
                  <span>Env: <strong className="text-slate-700 uppercase">{flag.environment}</strong></span>
                  <span>•</span>
                  <span>Rollout: <strong className="text-slate-700">{flag.rolloutPercentage}%</strong></span>
                </div>
              </div>

              {/* Controls */}
              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4 shrink-0">
                <div className="w-32">
                  <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1">
                    Rollout ({flag.rolloutPercentage}%)
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    step="10"
                    value={flag.rolloutPercentage}
                    onChange={(e) => handleRolloutChange(flag.key, e.target.value)}
                    className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
                  />
                </div>

                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={() => handleToggle(flag.key)}
                    className={`w-12 h-6 flex items-center rounded-full p-1 transition-colors cursor-pointer ${
                      flag.isEnabled ? 'bg-blue-600' : 'bg-slate-300'
                    }`}
                    aria-label={`Toggle ${flag.name}`}
                  >
                    <div
                      className={`bg-white w-4 h-4 rounded-full shadow-md transform transition-transform ${
                        flag.isEnabled ? 'translate-x-6' : 'translate-x-0'
                      }`}
                    />
                  </button>

                  <button
                    type="button"
                    onClick={() => promptSync(flag)}
                    disabled={isSaving}
                    className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-colors disabled:opacity-50 shadow-xs cursor-pointer ${
                      isDirty
                        ? 'bg-amber-600 hover:bg-amber-700 text-white'
                        : 'bg-slate-900 hover:bg-slate-800 text-white'
                    }`}
                  >
                    {isSaving ? 'Syncing...' : isDirty ? 'Persist Draft' : 'Sync Flag'}
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Confirmation Dialog Modal */}
      {confirmModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-xs">
          <div className="w-full max-w-md bg-white rounded-2xl p-6 shadow-2xl space-y-4">
            <h4 className="text-base font-bold text-slate-900">Confirm Feature Flag Mutation</h4>
            <p className="text-xs text-slate-600 leading-relaxed">
              Are you sure you want to dispatch a mutation for feature flag <strong>{confirmModal.name}</strong>?
              Setting: <span className="font-mono font-bold">{confirmModal.isEnabled ? 'ENABLED' : 'DISABLED'}</span> with rollout <span className="font-mono font-bold">{confirmModal.rolloutPercentage}%</span> in environment <span className="font-mono font-bold uppercase">{confirmModal.environment}</span>.
            </p>
            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setConfirmModal(null)}
                className="px-3.5 py-1.5 rounded-xl text-xs font-semibold border border-slate-200 text-slate-700 hover:bg-slate-50 cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => executePersistFlag(confirmModal)}
                className="px-4 py-1.5 rounded-xl text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white shadow-xs cursor-pointer"
              >
                Confirm & Dispatch
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
