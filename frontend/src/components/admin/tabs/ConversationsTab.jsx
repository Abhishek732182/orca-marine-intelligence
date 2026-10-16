import React, { useState, useEffect } from 'react';
import {
  fetchConversationAuditList,
  fetchConversationAuditDetail,
  ADMIN_CONTRACTS,
} from '../../../services/adminApi';
import BackendRequiredNotice from '../BackendRequiredNotice';

export default function ConversationsTab({ onOpenContract }) {
  const [auditState, setAuditState] = useState({
    loading: true,
    conversations: [],
    error: null,
    status: null,
  });

  const [auditReason, setAuditReason] = useState('SECURITY_COMPLIANCE_REVIEW');
  const [selectedAgent, setSelectedAgent] = useState('all');
  const [userQuery, setUserQuery] = useState('');
  const [activeTrace, setActiveTrace] = useState(null);
  const [traceLoading, setTraceLoading] = useState(false);
  const [traceError, setTraceError] = useState(null);

  const loadAuditStream = async () => {
    setAuditState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const res = await fetchConversationAuditList({
        agentId: selectedAgent === 'all' ? undefined : selectedAgent,
        search: userQuery || undefined,
        auditReason: auditReason || 'SECURITY_COMPLIANCE_REVIEW',
      });
      setAuditState({
        loading: false,
        conversations: res.data?.conversations || (Array.isArray(res.data) ? res.data : []),
        error: null,
        status: res.status,
      });
    } catch (err) {
      setAuditState({
        loading: false,
        conversations: [],
        error: err.message || 'Audit query failed',
        status: err.status || 0,
      });
    }
  };

  useEffect(() => {
    loadAuditStream();
  }, [selectedAgent]);

  const handleInspectTrace = async (conversationId) => {
    setTraceLoading(true);
    setTraceError(null);
    try {
      const res = await fetchConversationAuditDetail(conversationId);
      setActiveTrace(res.data);
    } catch (err) {
      setTraceError(
        `Failed to retrieve audited trace (${err.status ? `HTTP ${err.status}` : 'Offline'}): ${err.message}`
      );
    } finally {
      setTraceLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Title & Compliance Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight font-sans">
            Conversation Audit & Compliance
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 font-medium mt-0.5">
            Governed inspection of multi-agent execution plans, tool approvals, and maritime evidence.
          </p>
        </div>

        <button
          type="button"
          onClick={() => onOpenContract(ADMIN_CONTRACTS.conversationAudit)}
          className="px-4 py-2 text-xs font-semibold rounded-xl bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 transition-colors flex items-center gap-2 shadow-xs shrink-0 self-start sm:self-auto cursor-pointer"
        >
          <svg className="w-4 h-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <span>Audit API Contract</span>
        </button>
      </div>

      {/* Security & Privacy Governance Banner */}
      <div className="p-4 rounded-2xl bg-slate-900 text-slate-200 border border-slate-800 text-xs space-y-2">
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-cyan-400" />
          <h3 className="font-bold text-white tracking-wide">
            Strict Privacy & Audit Compliance Protocol
          </h3>
        </div>
        <p className="text-slate-400 text-[11.5px] leading-relaxed">
          ORCA does not expose user conversation histories via browser local storage to other users or administrators. All audit queries MUST be authenticated through backend endpoint <code className="text-cyan-300">GET /api/admin/conversations/audit</code> with an audited justification header (<code>X-Audit-Reason</code>). Access attempts are logged in the immutable security audit stream.
        </p>
      </div>

      {/* Filter & Justification Controls */}
      <div className="p-4 bg-white border border-slate-200 rounded-2xl shadow-xs space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex-1 max-w-md">
            <label className="block text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-1">
              Audit Reason Justification <span className="text-rose-600">*</span>
            </label>
            <input
              type="text"
              value={auditReason}
              onChange={(e) => setAuditReason(e.target.value)}
              placeholder="e.g. COMPLIANCE_Q4_REVIEW or INCIDENT_INVESTIGATION"
              className="w-full px-3 py-2 text-xs rounded-xl border border-slate-300 bg-slate-50 font-mono text-slate-800 focus:bg-white focus:outline-hidden focus:border-slate-800"
            />
          </div>

          <div className="flex items-center gap-3">
            <div>
              <label className="block text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-1">
                Agent Filter
              </label>
              <select
                value={selectedAgent}
                onChange={(e) => setSelectedAgent(e.target.value)}
                className="px-3 py-2 text-xs rounded-xl border border-slate-300 bg-white font-medium text-slate-800 focus:outline-hidden"
              >
                <option value="all">All Agents</option>
                <option value="weather">Weather Agent</option>
                <option value="ocean">Ocean Agent</option>
                <option value="fishing_zone">Fishing Zone Agent</option>
                <option value="route">Route Agent</option>
                <option value="safety_risk">Safety/Risk Agent</option>
                <option value="orchestrator">Orchestrator Agent</option>
                <option value="assistant">AI Workspace Assistant</option>
              </select>
            </div>

            <div>
              <label className="block text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-1">
                Session / User Filter
              </label>
              <input
                type="text"
                value={userQuery}
                onChange={(e) => setUserQuery(e.target.value)}
                placeholder="User ID / Session"
                className="px-3 py-2 text-xs rounded-xl border border-slate-300 bg-white font-mono text-slate-800 focus:outline-hidden max-w-[140px]"
              />
            </div>

            <div className="pt-5">
              <button
                type="button"
                onClick={loadAuditStream}
                className="px-3.5 py-2 text-xs font-semibold rounded-xl bg-slate-900 hover:bg-slate-800 text-white transition-colors"
              >
                Dispatch Query
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Trace Inspection Drawer / Error Modal */}
      {traceError && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-900 flex items-center justify-between">
          <span>{traceError}</span>
          <button type="button" onClick={() => setTraceError(null)} className="font-bold">
            ✕
          </button>
        </div>
      )}

      {activeTrace && (
        <div className="p-5 bg-white border border-slate-200 rounded-2xl shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-slate-200 pb-3">
            <div>
              <h3 className="text-sm font-bold text-slate-900">
                Audited Trace Detail: <span className="font-mono text-xs text-slate-600">{activeTrace.id || activeTrace.conversation_id}</span>
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Timestamp: {activeTrace.timestamp || activeTrace.created_at || '—'}
              </p>
            </div>
            <button
              type="button"
              onClick={() => setActiveTrace(null)}
              className="px-2.5 py-1 text-xs font-medium bg-slate-100 hover:bg-slate-200 rounded-lg text-slate-700"
            >
              Close Trace
            </button>
          </div>

          <pre className="p-4 bg-slate-900 text-slate-100 rounded-xl font-mono text-xs overflow-x-auto max-h-80">
            {JSON.stringify(activeTrace, null, 2)}
          </pre>
        </div>
      )}

      {/* Main Stream or Honest Backend Integration Required Notice */}
      {auditState.loading ? (
        <div className="p-12 bg-white border border-slate-200 rounded-2xl shadow-xs text-center space-y-3">
          <div className="w-8 h-8 rounded-full border-2 border-slate-300 border-t-cyan-700 animate-spin mx-auto" />
          <p className="text-xs font-medium text-slate-600">
            Querying compliance audit stream from <code className="font-mono text-slate-800">GET /api/admin/conversations/audit</code>...
          </p>
        </div>
      ) : auditState.error ? (
        <BackendRequiredNotice
          title="Conversation Audit Stream Not Implemented"
          endpoint="/api/admin/conversations/audit"
          method="GET"
          status={auditState.status}
          message="The backend server does not yet publish an authorized conversation audit stream. Private conversations remain strictly isolated in authenticated user sessions and cannot be accessed without the dedicated compliance audit endpoint."
          onOpenContract={() => onOpenContract(ADMIN_CONTRACTS.conversationAudit)}
          onRetry={loadAuditStream}
          isRetrying={auditState.loading}
        />
      ) : auditState.conversations.length === 0 ? (
        <div className="p-12 bg-white border border-slate-200 rounded-2xl shadow-xs text-center space-y-3">
          <div className="w-12 h-12 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center mx-auto">
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <h3 className="text-sm font-bold text-slate-800">No Audited Conversation Records</h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto leading-relaxed">
            The server returned an empty audit log. No conversational queries have been archived for compliance inspection under this filter.
          </p>
        </div>
      ) : (
        <div className="bg-white border border-slate-200 rounded-2xl shadow-xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-700 font-bold uppercase tracking-wider text-[11px] border-b border-slate-200">
                <tr>
                  <th className="px-5 py-3.5">Session ID</th>
                  <th className="px-4 py-3.5">User</th>
                  <th className="px-4 py-3.5">Agent Dispatched</th>
                  <th className="px-4 py-3.5">Timestamp</th>
                  <th className="px-4 py-3.5">Evidence Status</th>
                  <th className="px-4 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {auditState.conversations.map((c) => (
                  <tr key={c.id || c.conversation_id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="px-5 py-3.5 font-mono font-semibold text-slate-900">
                      {c.id || c.conversation_id}
                    </td>
                    <td className="px-4 py-3.5 text-slate-700">{c.user_email || c.user_id || '—'}</td>
                    <td className="px-4 py-3.5">
                      <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-slate-100 text-slate-800 font-semibold">
                        {c.agent_name || c.selected_agent || 'multi-agent'}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 text-slate-500 font-mono text-[11px]">
                      {c.timestamp || c.created_at || '—'}
                    </td>
                    <td className="px-4 py-3.5">
                      <span className="font-mono text-[10px] px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 font-bold">
                        {c.validation_status || 'VERIFIED'}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 text-right">
                      <button
                        type="button"
                        onClick={() => handleInspectTrace(c.id || c.conversation_id)}
                        disabled={traceLoading}
                        className="px-2.5 py-1 text-xs font-semibold bg-slate-900 hover:bg-slate-800 text-white rounded-lg transition-colors"
                      >
                        Inspect Trace
                      </button>
                    </td>
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
