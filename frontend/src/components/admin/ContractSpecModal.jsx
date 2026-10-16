import React, { useState } from 'react';
import { BASE_URL } from '../../services/adminApi';

/**
 * Interactive API Contract Specification Modal
 * Displays comprehensive specifications for backend engineers to implement missing admin endpoints.
 */
export default function ContractSpecModal({ contract, isOpen, onClose }) {
  const [copied, setCopied] = useState(false);

  if (!isOpen || !contract) return null;

  const endpointUrl = `${BASE_URL}${contract.endpoint || ''}`;
  const curlSample = `curl -X ${contract.method || 'GET'} "${endpointUrl}" \\
  -H "Authorization: Bearer <ADMIN_JWT_TOKEN>" \\
  -H "Content-Type: application/json"${
    contract.requestBody
      ? ` \\\n  -d '${JSON.stringify(contract.requestBody, null, 2).replace(/'/g, "'\\''")}'`
      : ''
  }`;

  const handleCopy = () => {
    navigator.clipboard?.writeText(JSON.stringify(contract, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-xs animate-in fade-in duration-150">
      <div
        className="relative w-full max-w-3xl max-h-[90vh] bg-white rounded-3xl shadow-2xl border border-slate-200 flex flex-col overflow-hidden text-slate-900"
        role="dialog"
        aria-modal="true"
      >
        {/* Modal Header */}
        <div className="px-6 py-4 bg-slate-900 text-white flex items-center justify-between border-b border-slate-800 shrink-0">
          <div className="flex items-center gap-3">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse" />
            <div>
              <h3 className="text-sm font-bold tracking-wide font-sans">
                Backend API Contract Specification
              </h3>
              <p className="text-[11px] text-slate-400">
                Authoritative requirement for backend implementation
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleCopy}
              className="px-2.5 py-1 text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors flex items-center gap-1"
            >
              {copied ? '✓ Copied JSON' : 'Copy Contract'}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
              aria-label="Close modal"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 text-xs text-slate-700">
          {/* Main Title & Method */}
          <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h4 className="text-base font-bold text-slate-900">{contract.title}</h4>
              <p className="text-xs text-slate-600 mt-1">{contract.description}</p>
            </div>
            <div className="flex items-center gap-2 font-mono shrink-0">
              <span className="px-2.5 py-1 rounded-lg bg-cyan-700 text-white font-bold text-xs">
                {contract.method}
              </span>
              <span className="px-3 py-1 rounded-lg bg-white border border-slate-300 text-slate-800 font-semibold text-xs">
                {contract.endpoint}
              </span>
            </div>
          </div>

          {/* Security & Access Controls */}
          <div className="space-y-2">
            <h5 className="font-bold text-slate-900 uppercase tracking-wider text-[11px] flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-rose-500" />
              Required Authorization & Security Claims
            </h5>
            <div className="p-3.5 bg-rose-50/60 border border-rose-200 rounded-xl space-y-1.5">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-rose-950">Required Role:</span>
                <span className="font-mono px-2 py-0.5 rounded bg-rose-200 text-rose-900 font-bold">
                  {contract.requiredRole || 'admin'}
                </span>
              </div>
              <p className="text-[11.5px] text-rose-900/80 leading-relaxed">
                The backend microservice MUST validate the incoming JSON Web Token signature and verify that the token claims include role <code>admin</code>. Frontend route guards enforce UI access, but backend enforcement is mandatory for security.
              </p>
            </div>
          </div>

          {/* Request Headers */}
          {contract.requestHeaders && (
            <div className="space-y-2">
              <h5 className="font-bold text-slate-900 uppercase tracking-wider text-[11px]">
                Expected Request Headers
              </h5>
              <div className="bg-slate-900 text-slate-100 p-3.5 rounded-xl font-mono text-[11px] space-y-1 overflow-x-auto">
                {Object.entries(contract.requestHeaders).map(([key, val]) => (
                  <div key={key} className="flex gap-2">
                    <span className="text-cyan-400">{key}:</span>
                    <span className="text-slate-300">{val}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Query Parameters */}
          {contract.queryParams && (
            <div className="space-y-2">
              <h5 className="font-bold text-slate-900 uppercase tracking-wider text-[11px]">
                Supported Query Parameters
              </h5>
              <div className="border border-slate-200 rounded-xl overflow-hidden">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-100 text-slate-700 font-semibold border-b border-slate-200">
                    <tr>
                      <th className="px-3 py-2">Parameter</th>
                      <th className="px-3 py-2">Description</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {Object.entries(contract.queryParams).map(([param, desc]) => (
                      <tr key={param} className="hover:bg-slate-50 font-mono">
                        <td className="px-3 py-2 text-cyan-800 font-bold">{param}</td>
                        <td className="px-3 py-2 text-slate-600 font-sans">{desc}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Request Body (for PATCH/POST) */}
          {(contract.requestBody || contract.updateEndpoint?.requestBody) && (
            <div className="space-y-2">
              <h5 className="font-bold text-slate-900 uppercase tracking-wider text-[11px]">
                Request Payload Schema (JSON)
              </h5>
              <pre className="bg-slate-900 text-emerald-400 p-4 rounded-xl font-mono text-[11px] overflow-x-auto">
                {JSON.stringify(contract.requestBody || contract.updateEndpoint.requestBody, null, 2)}
              </pre>
            </div>
          )}

          {/* Response Schema */}
          {contract.responseSchema && (
            <div className="space-y-2">
              <h5 className="font-bold text-slate-900 uppercase tracking-wider text-[11px]">
                Expected Successful Response Schema (HTTP 200 OK)
              </h5>
              <pre className="bg-slate-900 text-sky-300 p-4 rounded-xl font-mono text-[11px] overflow-x-auto">
                {JSON.stringify(contract.responseSchema, null, 2)}
              </pre>
            </div>
          )}

          {/* cURL Test Command */}
          <div className="space-y-2">
            <h5 className="font-bold text-slate-900 uppercase tracking-wider text-[11px]">
              Terminal Test Snippet (cURL)
            </h5>
            <pre className="bg-slate-950 text-slate-300 p-4 rounded-xl font-mono text-[11px] overflow-x-auto border border-slate-800">
              {curlSample}
            </pre>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3.5 bg-slate-50 border-t border-slate-200 flex items-center justify-between shrink-0">
          <span className="text-[11px] text-slate-500 font-medium">
            Status: Frontend Consumer Ready • Awaiting FastAPI Implementation
          </span>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-900 hover:bg-slate-800 text-white transition-colors shadow-xs"
          >
            Close Specification
          </button>
        </div>
      </div>
    </div>
  );
}
