import React from 'react';

/**
 * Honest Backend Integration Required Component
 * Clearly surfaces missing backend endpoints, actual status codes, and links to the contract.
 */
export default function BackendRequiredNotice({
  title = 'Backend Integration Required',
  endpoint,
  method = 'GET',
  status,
  message,
  onOpenContract,
  onRetry,
  isRetrying = false,
  className = '',
}) {
  const isConnectionRefused = status === 0 || status === 'OFFLINE';

  return (
    <div
      className={`p-5 rounded-2xl border border-amber-300/80 bg-linear-to-br from-amber-50/90 to-orange-50/60 text-slate-800 shadow-xs ${className}`}
    >
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
        <div className="flex items-start gap-3.5">
          <div className="w-9 h-9 rounded-xl bg-amber-500/15 border border-amber-500/30 text-amber-800 flex items-center justify-center shrink-0 mt-0.5">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </div>

          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <h4 className="text-sm font-bold text-amber-950">{title}</h4>
              <span className="font-mono text-[11px] font-bold px-2 py-0.5 rounded bg-amber-200/70 text-amber-900 border border-amber-300">
                {isConnectionRefused ? 'SERVER OFFLINE' : `HTTP ${status || '404'}`}
              </span>
            </div>

            <p className="text-xs text-amber-900/80 leading-relaxed max-w-2xl">
              {message ||
                `The ORCA backend microservice does not currently expose or persist this administrative capability. The frontend contract is implemented and ready to consume responses once deployed.`}
            </p>

            {endpoint && (
              <div className="flex items-center gap-2 pt-1 font-mono text-[11px] text-slate-700">
                <span className="font-semibold px-1.5 py-0.5 rounded bg-slate-200/80 text-slate-800">
                  {method}
                </span>
                <span className="text-slate-600 truncate">{endpoint}</span>
              </div>
            )}
          </div>
        </div>

        <div className="flex sm:flex-col items-center sm:items-end gap-2 shrink-0">
          {onOpenContract && (
            <button
              type="button"
              onClick={onOpenContract}
              className="px-3 py-1.5 rounded-xl text-xs font-semibold bg-amber-900 text-white hover:bg-amber-800 transition-colors shadow-xs flex items-center gap-1.5"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
              <span>View API Contract</span>
            </button>
          )}

          {onRetry && (
            <button
              type="button"
              onClick={onRetry}
              disabled={isRetrying}
              className="px-3 py-1.5 rounded-xl text-xs font-semibold bg-white border border-amber-300 text-amber-900 hover:bg-amber-100/60 transition-colors disabled:opacity-50"
            >
              {isRetrying ? 'Checking...' : 'Re-check Endpoint'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
