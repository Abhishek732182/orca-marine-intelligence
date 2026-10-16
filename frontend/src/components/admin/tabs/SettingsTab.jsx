import React, { useState } from 'react';
import { updatePlatformSettings, ADMIN_CONTRACTS, BASE_URL } from '../../../services/adminApi';

export default function SettingsTab({ onOpenContract }) {
  const [settings, setSettings] = useState({
    maxWindKnots: 25,
    maxWaveHeightMeters: 2.8,
    reefBufferNm: 2.0,
    monsoonMarginPct: 15,
    requestTimeoutMs: 25000,
    coordinatePrecision: 4,
    operationalMode: 'standard',
    enforceStrictMarineBounds: true,
  });

  const [isSaving, setIsSaving] = useState(false);
  const [notice, setNotice] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSaving(true);
    setNotice(null);

    try {
      await updatePlatformSettings({
        safety_thresholds: {
          max_wind_knots: settings.maxWindKnots,
          max_wave_height_meters: settings.maxWaveHeightMeters,
          reef_buffer_nm: settings.reefBufferNm,
          monsoon_margin_pct: settings.monsoonMarginPct,
        },
        system_defaults: {
          request_timeout_ms: settings.requestTimeoutMs,
          default_coordinate_precision: settings.coordinatePrecision,
          enforce_strict_marine_bounds: settings.enforceStrictMarineBounds,
          operational_mode: settings.operationalMode,
        },
      });

      setNotice({
        type: 'success',
        message: `Platform calibration verified and persisted by backend at ${new Date().toLocaleTimeString()}.`,
      });
    } catch (err) {
      setNotice({
        type: 'warning',
        message: `Unpersisted Calibration Draft: Backend returned ${
          err.status ? `HTTP ${err.status}` : 'Connection Refused'
        } for PATCH /api/admin/settings. Changes are held only in local client state and will NOT affect production until backend persistence is implemented.`,
      });
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Title & Actions Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight font-sans">
            Platform Settings & Maritime Safety Thresholds
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 font-medium mt-0.5">
            Global hazard triggers, timeout defaults, coordinate precision, and operational modes.
          </p>
        </div>

        <button
          type="button"
          onClick={() => onOpenContract(ADMIN_CONTRACTS.platformSettings)}
          className="px-4 py-2 text-xs font-semibold rounded-xl bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 transition-colors flex items-center gap-2 shadow-xs shrink-0 self-start sm:self-auto cursor-pointer"
        >
          <svg className="w-4 h-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <span>Settings API Contract</span>
        </button>
      </div>

      {/* Production Persistence Integrity Banner */}
      <div className="p-4 rounded-2xl bg-slate-900 text-slate-200 border border-slate-800 text-xs space-y-2">
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-cyan-400" />
          <h3 className="font-bold text-white tracking-wide">
            Backend Persistence & Production Authority
          </h3>
        </div>
        <p className="text-slate-400 text-[11.5px] leading-relaxed">
          Calibrating threshold values dispatches to <code className="text-cyan-300">PATCH /api/admin/settings</code>.
          The Safety/Risk Agent evaluates these thresholds during analysis. If the backend is offline or missing the endpoint, calibrations are flagged as <strong>Unpersisted Drafts</strong> to ensure operational transparency.
        </p>
      </div>

      {/* Notice Banner */}
      {notice && (
        <div
          className={`p-4 rounded-xl text-xs flex items-start justify-between border ${
            notice.type === 'success'
              ? 'bg-emerald-50 border-emerald-300 text-emerald-950'
              : 'bg-amber-50 border-amber-300 text-amber-950'
          }`}
        >
          <div className="flex items-center gap-2">
            <span>{notice.type === 'success' ? '✓' : '⚠️'}</span>
            <span>{notice.message}</span>
          </div>
          <button
            type="button"
            onClick={() => setNotice(null)}
            className="text-xs font-bold ml-3 hover:opacity-75"
          >
            ✕
          </button>
        </div>
      )}

      {/* Settings Form */}
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Maritime Hazard Thresholds Card */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs space-y-4">
          <div>
            <h2 className="text-sm font-bold text-slate-900">
              Maritime Hazard Thresholds (Safety/Risk Agent)
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Defines physical parameters beyond which the Safety/Risk Agent triggers HIGH or CRITICAL risk advisories.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Maximum Allowable Surface Wind Speed (knots)
              </label>
              <input
                type="number"
                value={settings.maxWindKnots}
                onChange={(e) => setSettings({ ...settings, maxWindKnots: Number(e.target.value) })}
                className="w-full px-3.5 py-2 rounded-xl border border-slate-300 text-slate-900 text-sm focus:outline-hidden focus:border-slate-800"
              />
              <span className="text-[11px] text-slate-500 mt-1 block">
                Standard gale threshold: 25-34 knots
              </span>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Maximum Significant Wave Height (meters)
              </label>
              <input
                type="number"
                step="0.1"
                value={settings.maxWaveHeightMeters}
                onChange={(e) =>
                  setSettings({ ...settings, maxWaveHeightMeters: Number(e.target.value) })
                }
                className="w-full px-3.5 py-2 rounded-xl border border-slate-300 text-slate-900 text-sm focus:outline-hidden focus:border-slate-800"
              />
              <span className="text-[11px] text-slate-500 mt-1 block">
                WMO 3700 Moderate/Rough transition: 2.50 - 4.00 m
              </span>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Reef & Shoal Clearance Buffer (Nautical Miles)
              </label>
              <input
                type="number"
                step="0.5"
                value={settings.reefBufferNm}
                onChange={(e) => setSettings({ ...settings, reefBufferNm: Number(e.target.value) })}
                className="w-full px-3.5 py-2 rounded-xl border border-slate-300 text-slate-900 text-sm focus:outline-hidden focus:border-slate-800"
              />
              <span className="text-[11px] text-slate-500 mt-1 block">
                Minimum distance required from submerged navigation hazards
              </span>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Monsoon Seasonal Hazard Margin (%)
              </label>
              <input
                type="number"
                value={settings.monsoonMarginPct}
                onChange={(e) =>
                  setSettings({ ...settings, monsoonMarginPct: Number(e.target.value) })
                }
                className="w-full px-3.5 py-2 rounded-xl border border-slate-300 text-slate-900 text-sm focus:outline-hidden focus:border-slate-800"
              />
              <span className="text-[11px] text-slate-500 mt-1 block">
                Safety score inflation during active southwest/northeast monsoon
              </span>
            </div>
          </div>
        </div>

        {/* Global System & Runtime Parameters */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs space-y-4">
          <div>
            <h2 className="text-sm font-bold text-slate-900">
              System Runtime Parameters
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Client request timeouts, coordinate precision, and operational routing profiles.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Connected Backend Endpoint
              </label>
              <input
                type="text"
                disabled
                value={BASE_URL}
                className="w-full px-3.5 py-2 rounded-xl border border-slate-200 bg-slate-50 text-slate-500 font-mono text-xs"
              />
              <span className="text-[11px] text-slate-500 mt-1 block">
                Configured via VITE_ORCA_API_URL environment variable
              </span>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Operational Mode Profile
              </label>
              <select
                value={settings.operationalMode}
                onChange={(e) => setSettings({ ...settings, operationalMode: e.target.value })}
                className="w-full px-3.5 py-2 rounded-xl border border-slate-300 text-slate-900 text-sm bg-white focus:outline-hidden"
              >
                <option value="standard">Standard Marine Research Mode</option>
                <option value="high_risk_monsoon">High-Risk Monsoon Advisory Mode</option>
                <option value="port_operations">Coastal Defense & Port Operations Mode</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Default API Timeout Limit (ms)
              </label>
              <input
                type="number"
                step="1000"
                value={settings.requestTimeoutMs}
                onChange={(e) =>
                  setSettings({ ...settings, requestTimeoutMs: Number(e.target.value) })
                }
                className="w-full px-3.5 py-2 rounded-xl border border-slate-300 text-slate-900 text-sm focus:outline-hidden focus:border-slate-800"
              />
            </div>

            <div className="flex flex-col justify-center pt-2">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.enforceStrictMarineBounds}
                  onChange={(e) =>
                    setSettings({ ...settings, enforceStrictMarineBounds: e.target.checked })
                  }
                  className="rounded border-slate-300 text-cyan-600 focus:ring-0"
                />
                <span className="text-xs font-semibold text-slate-800">
                  Enforce strict marine coordinates bounding box
                </span>
              </label>
            </div>
          </div>
        </div>

        {/* Form Action Button */}
        <div className="flex items-center justify-end">
          <button
            type="submit"
            disabled={isSaving}
            className="py-2.5 px-6 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-semibold text-xs transition-colors shadow-xs disabled:opacity-50"
          >
            {isSaving ? 'Saving Calibration...' : 'Apply & Persist Platform Settings'}
          </button>
        </div>
      </form>
    </div>
  );
}
