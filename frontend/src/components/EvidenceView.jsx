import React, { useState } from 'react';
import InlineMarineMap from './InlineMarineMap';
import { getDeduplicatedAgentResults } from '../services/orcaApi';

export default function EvidenceView({
  agentResults,
  evidenceSummary,
  risk,
  metrics,
  limitations,
  warnings = [],
  legalDisclaimer,
}) {
  const [showRawJson, setShowRawJson] = useState(false);

  // Deduplicate specialist agent results
  const agentList = getDeduplicatedAgentResults(agentResults);
  const coordinates = evidenceSummary?.coordinates;

  const hasAnyData =
    agentList.length > 0 ||
    evidenceSummary ||
    risk ||
    metrics ||
    (warnings && warnings.length > 0) ||
    legalDisclaimer;

  if (!hasAnyData) return null;

  return (
    <div className="mt-4 space-y-3.5">
      {/* Risk Level Badge if provided */}
      {risk && (
        <div
          className={`p-3.5 rounded-2xl border text-sm leading-relaxed flex items-start gap-3 shadow-2xs ${
            risk.type === 'coral' || risk.level?.includes('CRITICAL') || risk.level?.includes('HIGH')
              ? 'bg-rose-50 border-rose-200 text-rose-900'
              : risk.type === 'amber' || risk.level?.includes('MODERATE') || risk.level?.includes('CAUTION')
              ? 'bg-amber-50 border-amber-200 text-amber-900'
              : 'bg-emerald-50 border-emerald-200 text-emerald-900'
          }`}
        >
          <svg className="w-5 h-5 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <div>
            <div className="font-bold text-[14.5px]">{risk.level || 'Operational Risk Assessment'}</div>
            {risk.reason && <div className="mt-1 text-slate-700">{risk.reason}</div>}
          </div>
        </div>
      )}

      {/* Specialist Agent Telemetry Cards */}
      {agentList.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {agentList.map(({ agentName, agentData }) => {
            const status = (agentData?.status || 'SUCCESS').toUpperCase();
            const obs = agentData?.observations || {};
            const analysis = agentData?.analysis || {};

            const isSuccess = status === 'SUCCESS';
            const isInsufficient = status === 'INSUFFICIENT_EVIDENCE';

            return (
              <div
                key={agentName}
                className="p-4 bg-white border border-slate-200 rounded-2xl shadow-2xs text-sm space-y-2.5"
              >
                {/* Agent Header */}
                <div className="flex items-center justify-between gap-2 border-b border-slate-100 pb-2">
                  <span className="font-bold text-slate-900 text-[14px]">{agentName}</span>
                  <span
                    className={`text-xs font-mono px-2 py-0.5 rounded-full font-semibold ${
                      isSuccess
                        ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                        : isInsufficient
                        ? 'bg-amber-50 text-amber-800 border border-amber-200'
                        : 'bg-slate-100 text-slate-600 border border-slate-200'
                    }`}
                  >
                    {status}
                  </span>
                </div>

                {/* Agent Analysis Summary */}
                {analysis?.summary && (
                  <p className="text-slate-600 leading-relaxed text-[13.5px]">
                    {analysis.summary}
                  </p>
                )}

                {/* Structured Metric Highlights if present */}
                <div className="space-y-1.5 pt-1 text-[13px]">
                  {obs.temperature_c != null && (
                    <div className="flex justify-between text-slate-500">
                      <span>Air Temperature:</span>
                      <span className="font-semibold text-slate-800">{obs.temperature_c} °C</span>
                    </div>
                  )}
                  {obs.wind_speed_knots != null && (
                    <div className="flex justify-between text-slate-500">
                      <span>Wind Speed:</span>
                      <span className="font-semibold text-slate-800">
                        {obs.wind_speed_knots} kts
                        {obs.beaufort_scale?.force != null && ` (Force ${obs.beaufort_scale.force})`}
                      </span>
                    </div>
                  )}
                  {obs.avg_wave_height_m != null && (
                    <div className="flex justify-between text-slate-500">
                      <span>Wave Height:</span>
                      <span className="font-semibold text-slate-800">
                        {obs.avg_wave_height_m} m
                        {analysis.sea_state_code != null && ` (WMO Code ${analysis.sea_state_code})`}
                      </span>
                    </div>
                  )}
                  {obs.total_distance_nm != null && (
                    <div className="flex justify-between text-slate-500">
                      <span>Geodesic Distance:</span>
                      <span className="font-semibold text-slate-800">{obs.total_distance_nm} NM</span>
                    </div>
                  )}
                  {obs.estimated_transit_time_hours != null && (
                    <div className="flex justify-between text-slate-500">
                      <span>Est. Transit:</span>
                      <span className="font-semibold text-slate-800">{obs.estimated_transit_time_hours} hrs</span>
                    </div>
                  )}
                  {analysis.operational_feasibility && (
                    <div className="flex justify-between text-slate-500">
                      <span>Trawler Feasibility:</span>
                      <span className="font-semibold text-slate-800">{analysis.operational_feasibility}</span>
                    </div>
                  )}
                </div>

                {/* PFZ Verification Disclaimer Notice */}
                {analysis.verified_fish_distribution?.status === 'UNVERIFIED' && (
                  <div className="p-2 rounded-xl bg-slate-50 text-xs text-slate-600 border border-slate-200">
                    ⚠️ Fish distribution status is UNVERIFIED without in-situ satellite imagery.
                  </div>
                )}
                {analysis.vessel_safety_notice && (
                  <div className="text-xs text-amber-800 italic">
                    {analysis.vessel_safety_notice}
                  </div>
                )}
                {analysis.navigable_route_disclaimer && (
                  <div className="text-xs text-slate-500 italic">
                    {analysis.navigable_route_disclaimer}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Inline Geospatial Chart if coordinates or route are present */}
      {coordinates && <InlineMarineMap coordinates={coordinates} />}

      {/* Warnings & Notices */}
      {warnings && warnings.length > 0 && (
        <div className="p-3.5 rounded-2xl bg-amber-50/70 border border-amber-200 text-amber-900 text-xs sm:text-sm space-y-1.5 shadow-2xs">
          <div className="font-bold flex items-center gap-2">
            <svg className="w-4 h-4 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            Operational Warnings
          </div>
          <ul className="list-disc pl-5 space-y-1 text-xs sm:text-[13px] text-amber-800">
            {warnings.map((w, idx) => (
              <li key={idx}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Limitations */}
      {limitations && limitations.length > 0 && (
        <div className="text-xs text-slate-500 italic space-y-1 pt-2">
          {limitations.map((lim, idx) => (
            <p key={idx}>ℹ {lim}</p>
          ))}
        </div>
      )}

      {/* Legal & Regulatory Disclaimer */}
      {legalDisclaimer && (
        <div className="text-xs text-slate-400 italic leading-normal pt-1">
          {legalDisclaimer}
        </div>
      )}

      {/* Inspection Toggle for Evidence Verification */}
      <div className="pt-1">
        <button
          type="button"
          onClick={() => setShowRawJson(!showRawJson)}
          className="text-xs text-slate-400 hover:text-slate-600 underline transition-colors"
        >
          {showRawJson ? 'Hide raw agent response payload' : 'Inspect raw agent response payload'}
        </button>
        {showRawJson && (
          <pre className="mt-2 p-3 bg-slate-900 text-slate-200 rounded-xl text-xs font-mono overflow-x-auto max-h-56">
            {JSON.stringify({ agentResults, evidenceSummary, risk, metrics }, null, 2)}
          </pre>
        )}
      </div>
    </div>
  );
}
