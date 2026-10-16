import React, { useState, useEffect } from 'react';
import { fetchSecurityAuditLogs, ADMIN_CONTRACTS, getAuthToken } from '../../../services/adminApi';
import { useAuth } from '../../../context/AuthContext';
import BackendRequiredNotice from '../BackendRequiredNotice';

export default function SecurityAuditTab({ onOpenContract }) {
  const { user } = useAuth();
  const token = getAuthToken();

  const [logsState, setLogsState] = useState({
    loading: true,
    logs: [],
    error: null,
    status: null,
  });

  const [selectedEventType, setSelectedEventType] = useState('all');
  const [selectedSeverity, setSelectedSeverity] = useState('all');

  const loadAuditLogs = async () => {
    setLogsState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const res = await fetchSecurityAuditLogs({
        eventType: selectedEventType === 'all' ? undefined : selectedEventType,
        severity: selectedSeverity === 'all' ? undefined : selectedSeverity,
      });
      setLogsState({
        loading: false,
        logs: res.data?.logs || (Array.isArray(res.data) ? res.data : []),
        error: null,
        status: res.status,
      });
    } catch (err) {
      setLogsState({
        loading: false,
        logs: [],
        error: err.message || 'Failed to retrieve security audit logs',
        status: err.status || 0,
      });
    }
  };

  useEffect(() => {
    loadAuditLogs();
  }, [selectedEventType, selectedSeverity]);

  return (
    <div className="space-y-6">
      {/* Title & Actions Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight font-sans">
            Security Architecture & Audit Logs
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 font-medium mt-0.5">
            Immutable authentication trails, role elevation records, and cryptographic authorization posture.
          </p>
        </div>

        <button
          type="button"
          onClick={() => onOpenContract(ADMIN_CONTRACTS.securityAuditLogs)}
          className="px-4 py-2 text-xs font-semibold rounded-xl bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 transition-colors flex items-center gap-2 shadow-xs shrink-0 self-start sm:self-auto cursor-pointer"
        >
          <svg className="w-4 h-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <span>Security API Contract</span>
        </button>
      </div>

      {/* Security Posture Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Frontend Route Guard Posture */}
        <div className="p-5 bg-white border border-slate-200 rounded-2xl shadow-xs space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
              Frontend Route Guard
            </span>
            <span className="px-2 py-0.5 rounded-full font-mono text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
              ENFORCED
            </span>
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            Routes under <code className="bg-slate-100 px-1 py-0.5 rounded text-slate-800">/admin/*</code> verify active session role is strictly <strong>admin</strong>.
          </p>
          <div className="pt-1 text-[11px] text-slate-500 font-mono">
            Active User: {user?.fullName || 'Admin'} ({user?.role})
          </div>
        </div>

        {/* Backend Authorization Requirement */}
        <div className="p-5 bg-white border border-slate-200 rounded-2xl shadow-xs space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
              Backend Authorization
            </span>
            <span className="px-2 py-0.5 rounded-full font-mono text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-200">
              PENDING ENDPOINTS
            </span>
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            FastAPI must independently validate incoming Bearer tokens and verify cryptographic signatures.
          </p>
          <div className="pt-1 text-[11px] text-slate-500 font-mono">
            Authorization: {token ? 'Bearer Session Active (Protected)' : 'No Session Token'}
          </div>
        </div>

        {/* Audit Trail Policy */}
        <div className="p-5 bg-white border border-slate-200 rounded-2xl shadow-xs space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
              Compliance Retention
            </span>
            <span className="px-2 py-0.5 rounded-full font-mono text-[10px] font-bold bg-cyan-100 text-cyan-800 border border-cyan-200">
              365 DAYS
            </span>
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            Administrative mutations, parameter overrides, and agent dispatch traces must be immutably recorded.
          </p>
          <div className="pt-1 text-[11px] text-slate-500 font-mono">
            Auditing Standard: ISO 27001 / SOC 2
          </div>
        </div>
      </div>

      {/* Filter Controls */}
      <div className="p-4 bg-white border border-slate-200 rounded-2xl shadow-xs flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <div>
            <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1">
              Event Type
            </label>
            <select
              value={selectedEventType}
              onChange={(e) => setSelectedEventType(e.target.value)}
              className="px-3 py-1.5 text-xs rounded-xl border border-slate-300 bg-white font-medium text-slate-800 focus:outline-hidden"
            >
              <option value="all">All Events</option>
              <option value="AUTH_LOGIN">Authentication Logins</option>
              <option value="ROLE_ELEVATION">Role Changes</option>
              <option value="AGENT_DISPATCH">Agent Dispatches</option>
              <option value="CONFIG_CHANGE">Configuration Overrides</option>
            </select>
          </div>

          <div>
            <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1">
              Severity Level
            </label>
            <select
              value={selectedSeverity}
              onChange={(e) => setSelectedSeverity(e.target.value)}
              className="px-3 py-1.5 text-xs rounded-xl border border-slate-300 bg-white font-medium text-slate-800 focus:outline-hidden"
            >
              <option value="all">All Severities</option>
              <option value="INFO">INFO</option>
              <option value="WARNING">WARNING</option>
              <option value="CRITICAL">CRITICAL</option>
              <option value="AUDIT">AUDIT</option>
            </select>
          </div>
        </div>

        <button
          type="button"
          onClick={loadAuditLogs}
          disabled={logsState.loading}
          className="px-3 py-1.5 text-xs font-semibold rounded-xl bg-slate-900 hover:bg-slate-800 text-white transition-colors disabled:opacity-50"
        >
          {logsState.loading ? 'Fetching...' : 'Refresh Logs'}
        </button>
      </div>

      {/* Audit Log Stream or Honest Backend Integration Required Notice */}
      {logsState.loading ? (
        <div className="p-12 bg-white border border-slate-200 rounded-2xl shadow-xs text-center space-y-3">
          <div className="w-8 h-8 rounded-full border-2 border-slate-300 border-t-cyan-700 animate-spin mx-auto" />
          <p className="text-xs font-medium text-slate-600">
            Querying security event stream from <code className="font-mono text-slate-800">GET /api/admin/audit-logs</code>...
          </p>
        </div>
      ) : logsState.error ? (
        <BackendRequiredNotice
          title="Security Event Log Stream Inactive"
          endpoint="/api/admin/audit-logs"
          method="GET"
          status={logsState.status}
          message="No live security event stream is currently published by the backend server. To view verified login attempts, privilege elevations, and system configuration modifications, connect the GET /api/admin/audit-logs endpoint."
          onOpenContract={() => onOpenContract(ADMIN_CONTRACTS.securityAuditLogs)}
          onRetry={loadAuditLogs}
          isRetrying={logsState.loading}
        />
      ) : logsState.logs.length === 0 ? (
        <div className="p-12 bg-white border border-slate-200 rounded-2xl shadow-xs text-center space-y-3">
          <div className="w-12 h-12 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center mx-auto">
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <h3 className="text-sm font-bold text-slate-800">No Security Events Recorded</h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto leading-relaxed">
            The security log stream returned 0 events matching the selected criteria.
          </p>
        </div>
      ) : (
        <div className="bg-white border border-slate-200 rounded-2xl shadow-xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-700 font-bold uppercase tracking-wider text-[11px] border-b border-slate-200">
                <tr>
                  <th className="px-5 py-3.5">Timestamp</th>
                  <th className="px-4 py-3.5">Severity</th>
                  <th className="px-4 py-3.5">Event Type</th>
                  <th className="px-4 py-3.5">Actor / User</th>
                  <th className="px-4 py-3.5">Details</th>
                  <th className="px-4 py-3.5 text-right">IP / Origin</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono text-[11px]">
                {logsState.logs.map((log, idx) => (
                  <tr key={idx} className="hover:bg-slate-50/70 transition-colors">
                    <td className="px-5 py-3 text-slate-500">{log.timestamp || '—'}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`px-2 py-0.5 rounded font-bold text-[10px] ${
                          log.severity === 'CRITICAL'
                            ? 'bg-rose-100 text-rose-800'
                            : log.severity === 'WARNING'
                            ? 'bg-amber-100 text-amber-800'
                            : 'bg-slate-100 text-slate-700'
                        }`}
                      >
                        {log.severity || 'INFO'}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-bold text-slate-800">{log.event_type}</td>
                    <td className="px-4 py-3 text-slate-600">{log.user_id || log.actor || 'system'}</td>
                    <td className="px-4 py-3 font-sans text-slate-700">{log.message || log.details}</td>
                    <td className="px-4 py-3 text-right text-slate-500">{log.ip_address || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
