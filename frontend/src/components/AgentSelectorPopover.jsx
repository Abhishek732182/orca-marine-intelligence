import React, { useEffect, useRef } from 'react';

export const AGENT_OPTIONS = [
  {
    id: 'auto',
    name: 'Auto / ORCA Orchestrator',
    shortName: 'Auto',
    badge: 'Orchestrator',
    desc: 'Dispatches specialists dynamically based on question intent',
    icon: (
      <svg className="w-5 h-5 text-sky-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M13 10V3L4 14h7v7l9-11h-7z" />
      </svg>
    ),
  },
  {
    id: 'weather',
    name: 'Weather & Forecast',
    shortName: 'Weather',
    badge: 'Agent 1',
    desc: 'Atmospheric telemetry, surface wind speed, and Beaufort scale',
    icon: (
      <svg className="w-5 h-5 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 00-9.78 2.096A4.001 4.001 0 003 15z" />
      </svg>
    ),
  },
  {
    id: 'ocean',
    name: 'Ocean Conditions',
    shortName: 'Ocean',
    badge: 'Agent 2',
    desc: 'Wave heights, swell period, and WMO 3700 sea-state codes',
    icon: (
      <svg className="w-5 h-5 text-teal-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M14 10l-2 1m0 0l-2-1m2 1v2.5M20 7l-2 1m2-1l-2-1m2 1v2.5M14 4l-2-1-2 1M4 7l2-1M4 7l2 1M4 7v2.5M12 21l-2-1m2 1l2-1m-2 1v-2.5M6 18l-2-1v-2.5M18 18l2-1v-2.5" />
      </svg>
    ),
  },
  {
    id: 'fishing_zone',
    name: 'Potential Fishing Zones (PFZ)',
    shortName: 'PFZ',
    badge: 'Agent 3',
    desc: 'Habitat viability, operational feasibility, and thermal gradients',
    icon: (
      <svg className="w-5 h-5 text-cyan-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
      </svg>
    ),
  },
  {
    id: 'route',
    name: 'Route Planning',
    shortName: 'Route',
    badge: 'Agent 4',
    desc: 'Great-Circle geodesic distance and estimated transit time',
    icon: (
      <svg className="w-5 h-5 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
      </svg>
    ),
  },
  {
    id: 'safety_risk',
    name: 'Marine Safety',
    shortName: 'Safety',
    badge: 'Agent 5',
    desc: 'Vessel limits, wind/wave hazard thresholds, and advisory status',
    icon: (
      <svg className="w-5 h-5 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
    ),
  },
];

export default function AgentSelectorPopover({
  selectedAgent,
  onSelectAgent,
  isOpen,
  onClose,
}) {
  const popoverRef = useRef(null);

  useEffect(() => {
    function handleClickOutside(e) {
      if (popoverRef.current && !popoverRef.current.contains(e.target)) {
        onClose();
      }
    }
    function handleKeyDown(e) {
      if (e.key === 'Escape') {
        onClose();
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      ref={popoverRef}
      className="absolute bottom-full left-0 mb-2 w-80 sm:w-96 bg-white rounded-xl shadow-xl border border-slate-200 py-2 z-50 animate-in fade-in zoom-in-95 duration-150"
      role="menu"
      aria-label="Select Specialist Agent"
    >
      <div className="px-3.5 py-1.5 border-b border-slate-100 flex items-center justify-between">
        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
          Specialist Agents
        </span>
        <span className="text-[11px] text-slate-400">
          Select target agent
        </span>
      </div>

      <div className="max-h-80 overflow-y-auto p-1.5 space-y-1">
        {AGENT_OPTIONS.map((agent) => {
          const isSelected = selectedAgent === agent.id;
          return (
            <button
              key={agent.id}
              type="button"
              onClick={() => {
                onSelectAgent(agent.id);
                onClose();
              }}
              className={`w-full text-left px-3 py-2.5 rounded-lg flex items-start gap-3 transition-colors ${
                isSelected
                  ? 'bg-sky-50 border border-sky-200'
                  : 'hover:bg-slate-50 border border-transparent'
              }`}
              role="menuitem"
            >
              <div className="p-1.5 rounded-md bg-white border border-slate-100 shadow-xs shrink-0 mt-0.5">
                {agent.icon}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-1">
                  <span
                    className={`text-sm font-medium truncate ${
                      isSelected ? 'text-sky-950 font-semibold' : 'text-slate-800'
                    }`}
                  >
                    {agent.name}
                  </span>
                  <span
                    className={`text-[10px] px-1.5 py-0.5 rounded font-mono ${
                      isSelected
                        ? 'bg-sky-200 text-sky-800'
                        : 'bg-slate-100 text-slate-600'
                    }`}
                  >
                    {agent.badge}
                  </span>
                </div>
                <p className="text-xs text-slate-500 leading-relaxed mt-0.5 line-clamp-2">
                  {agent.desc}
                </p>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
