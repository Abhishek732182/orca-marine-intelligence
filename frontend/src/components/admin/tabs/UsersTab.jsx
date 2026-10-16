import React, { useState, useEffect } from 'react';
import {
  fetchUsers,
  updateUserRole,
  updateUserStatus,
  deleteUserAccount,
  ADMIN_CONTRACTS,
} from '../../../services/adminApi';
import BackendRequiredNotice from '../BackendRequiredNotice';

export default function UsersTab({ onOpenContract }) {
  const [usersState, setUsersState] = useState({
    loading: true,
    users: [],
    total: 0,
    error: null,
    status: null,
  });

  const [roleFilter, setRoleFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedUser, setSelectedUser] = useState(null);
  const [actionFeedback, setActionFeedback] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isBackendAvailable = usersState.status === 200;

  const loadUsers = async () => {
    setUsersState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const res = await fetchUsers({
        role: roleFilter === 'all' ? undefined : roleFilter,
        search: searchTerm || undefined,
        page: currentPage,
        limit: 10,
      });
      setUsersState({
        loading: false,
        users: res.data?.users || (Array.isArray(res.data) ? res.data : []),
        total: res.data?.total || 0,
        error: null,
        status: res.status,
      });
    } catch (err) {
      setUsersState({
        loading: false,
        users: [],
        total: 0,
        error: err.message || 'Failed to fetch user accounts',
        status: err.status || 0,
      });
    }
  };

  useEffect(() => {
    loadUsers();
  }, [roleFilter, statusFilter, currentPage]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setCurrentPage(1);
    loadUsers();
  };

  const handleRoleChange = async (userId, targetRole) => {
    setIsSubmitting(true);
    setActionFeedback(null);
    try {
      await updateUserRole(userId, targetRole);
      setActionFeedback({
        type: 'success',
        message: `Successfully updated user ${userId} role to ${targetRole}.`,
      });
      loadUsers();
    } catch (err) {
      setActionFeedback({
        type: 'error',
        message: `Role update failed (${err.status ? `HTTP ${err.status}` : 'Offline'}): ${
          err.message
        }. Backend persistence required.`,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleStatusToggle = async (userId, newStatus) => {
    setIsSubmitting(true);
    setActionFeedback(null);
    try {
      await updateUserStatus(userId, newStatus, 'SUPER_ADMIN_CONSOLE_ACTION');
      setActionFeedback({
        type: 'success',
        message: `Successfully updated user ${userId} status to ${newStatus}.`,
      });
      loadUsers();
    } catch (err) {
      setActionFeedback({
        type: 'error',
        message: `Status change failed (${err.status ? `HTTP ${err.status}` : 'Offline'}): ${
          err.message
        }. Backend persistence required.`,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteUser = async (userId) => {
    if (!window.confirm(`Are you sure you want to permanently delete user ${userId}? This action cannot be undone.`)) {
      return;
    }
    setIsSubmitting(true);
    setActionFeedback(null);
    try {
      await deleteUserAccount(userId);
      setActionFeedback({
        type: 'success',
        message: `User ${userId} deleted successfully.`,
      });
      loadUsers();
    } catch (err) {
      setActionFeedback({
        type: 'error',
        message: `User deletion failed (${err.status ? `HTTP ${err.status}` : 'Offline'}): ${
          err.message
        }. Destructive operations disabled while backend is disconnected.`,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Title & Actions Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight font-sans">
            User Management & RBAC
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 font-medium mt-0.5">
            Governs authorized access for oceanographic researchers, fleet navigators, and administrators.
          </p>
        </div>

        <button
          type="button"
          onClick={() => onOpenContract(ADMIN_CONTRACTS.userManagement)}
          className="px-4 py-2 text-xs font-semibold rounded-xl bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 transition-colors flex items-center gap-2 shadow-xs shrink-0 self-start sm:self-auto cursor-pointer"
        >
          <svg className="w-4 h-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <span>User API Contract</span>
        </button>
      </div>

      {/* Action Notification Banner */}
      {actionFeedback && (
        <div
          className={`p-4 rounded-xl text-xs flex items-center justify-between border ${
            actionFeedback.type === 'success'
              ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
              : 'bg-rose-50 border-rose-200 text-rose-900'
          }`}
        >
          <div className="flex items-center gap-2">
            <span>{actionFeedback.type === 'success' ? '✓' : '⚠️'}</span>
            <span>{actionFeedback.message}</span>
          </div>
          <button
            type="button"
            onClick={() => setActionFeedback(null)}
            className="text-xs font-bold hover:opacity-70 ml-2"
          >
            ✕
          </button>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="p-4 bg-white border border-slate-200 rounded-2xl shadow-xs flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <form onSubmit={handleSearchSubmit} className="flex-1 max-w-md flex items-center gap-2">
          <div className="relative flex-1">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <input
              type="text"
              placeholder="Search by name, email, or affiliation..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-3.5 py-2 text-xs rounded-xl border border-slate-200 bg-slate-50 focus:bg-white focus:outline-hidden focus:border-blue-500 text-slate-900 transition-colors"
            />
          </div>
          <button
            type="submit"
            className="px-4 py-2 text-xs font-semibold rounded-xl bg-slate-900 hover:bg-slate-800 text-white transition-colors shrink-0 shadow-xs cursor-pointer"
          >
            Filter
          </button>
        </form>

        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-slate-600">Role:</span>
            <select
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value)}
              className="px-3 py-1.5 text-xs rounded-xl border border-slate-200 bg-white font-medium text-slate-800 focus:outline-hidden focus:border-blue-500 cursor-pointer"
            >
              <option value="all">All Roles</option>
              <option value="researcher">Researcher</option>
              <option value="oceanographer">Oceanographer</option>
              <option value="fleet_officer">Fleet Officer</option>
              <option value="admin">Administrator</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-slate-600">Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-1.5 text-xs rounded-xl border border-slate-200 bg-white font-medium text-slate-800 focus:outline-hidden focus:border-blue-500 cursor-pointer"
            >
              <option value="all">All Statuses</option>
              <option value="active">Active</option>
              <option value="suspended">Suspended</option>
              <option value="pending_review">Pending Review</option>
            </select>
          </div>
        </div>
      </div>

      {/* User Records Table or Honest Backend Required Notice */}
      {usersState.loading ? (
        <div className="p-16 bg-white border border-slate-200 rounded-2xl shadow-xs text-center space-y-3">
          <div className="w-8 h-8 rounded-full border-2 border-slate-300 border-t-blue-600 animate-spin mx-auto" />
          <p className="text-xs font-medium text-slate-600">
            Querying user accounts from <code className="font-mono text-slate-800">GET /api/admin/users</code>...
          </p>
        </div>
      ) : usersState.error ? (
        <BackendRequiredNotice
          title="User Account Repository Not Connected"
          endpoint="/api/admin/users"
          method="GET"
          status={usersState.status}
          message="The backend does not currently expose a persistent user management database endpoint. To view, search, and administer real user accounts, implement the GET /api/admin/users endpoint in FastAPI. Never populate this screen with synthetic accounts."
          onOpenContract={() => onOpenContract(ADMIN_CONTRACTS.userManagement)}
          onRetry={loadUsers}
          isRetrying={usersState.loading}
        />
      ) : usersState.users.length === 0 ? (
        <div className="p-16 bg-white border border-slate-200 rounded-2xl shadow-xs text-center space-y-3">
          <div className="w-12 h-12 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center mx-auto">
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
            </svg>
          </div>
          <h3 className="text-sm font-bold text-slate-800">No User Accounts Found</h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto leading-relaxed">
            The endpoint returned 0 registered user records matching the filter criteria.
          </p>
        </div>
      ) : (
        <div className="bg-white border border-slate-200 rounded-2xl shadow-xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-700 font-bold uppercase tracking-wider text-[11px] border-b border-slate-200">
                <tr>
                  <th className="px-5 py-3.5">User</th>
                  <th className="px-4 py-3.5">Email</th>
                  <th className="px-4 py-3.5">Role</th>
                  <th className="px-4 py-3.5">Status</th>
                  <th className="px-4 py-3.5">Affiliation</th>
                  <th className="px-4 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {usersState.users.map((u) => (
                  <tr key={u.id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-800 font-bold text-xs flex items-center justify-center shrink-0">
                          {u.avatarInitials || (u.fullName ? u.fullName.slice(0, 2).toUpperCase() : 'US')}
                        </div>
                        <div>
                          <div className="font-semibold text-slate-900 cursor-pointer hover:text-blue-600" onClick={() => setSelectedUser(u)}>
                            {u.fullName || 'Unnamed User'}
                          </div>
                          <div className="text-[10px] text-slate-400 font-mono">ID: {u.id}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3.5 font-mono text-slate-600">{u.email}</td>
                    <td className="px-4 py-3.5">
                      <select
                        value={u.role || 'researcher'}
                        disabled={isSubmitting || !isBackendAvailable}
                        onChange={(e) => handleRoleChange(u.id, e.target.value)}
                        className="px-2 py-1 rounded-lg border border-slate-200 font-medium text-slate-800 text-[11px] bg-white focus:outline-hidden disabled:opacity-50"
                      >
                        <option value="researcher">Researcher</option>
                        <option value="oceanographer">Oceanographer</option>
                        <option value="fleet_officer">Fleet Officer</option>
                        <option value="admin">Admin</option>
                      </select>
                    </td>
                    <td className="px-4 py-3.5">
                      <span
                        className={`px-2 py-0.5 rounded-full font-mono text-[10px] font-bold ${
                          u.status === 'suspended'
                            ? 'bg-rose-100 text-rose-800 border border-rose-200'
                            : 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                        }`}
                      >
                        {u.status || 'ACTIVE'}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 text-slate-500 truncate max-w-[180px]">
                      {u.affiliation || '—'}
                    </td>
                    <td className="px-4 py-3.5 text-right space-x-2">
                      <button
                        type="button"
                        onClick={() => setSelectedUser(u)}
                        className="px-2.5 py-1 rounded-lg text-[11px] font-medium bg-slate-100 hover:bg-slate-200 text-slate-700 transition-colors"
                      >
                        Details
                      </button>
                      <button
                        type="button"
                        disabled={isSubmitting || !isBackendAvailable}
                        onClick={() => handleStatusToggle(u.id, u.status === 'suspended' ? 'active' : 'suspended')}
                        className="px-2.5 py-1 rounded-lg text-[11px] font-medium border border-slate-200 hover:bg-slate-100 text-slate-700 transition-colors disabled:opacity-40"
                        title={!isBackendAvailable ? 'Destructive actions disabled while backend is disconnected' : ''}
                      >
                        {u.status === 'suspended' ? 'Activate' : 'Suspend'}
                      </button>
                      <button
                        type="button"
                        disabled={isSubmitting || !isBackendAvailable}
                        onClick={() => handleDeleteUser(u.id)}
                        className="px-2.5 py-1 rounded-lg text-[11px] font-medium text-rose-600 hover:bg-rose-50 border border-rose-200 transition-colors disabled:opacity-40"
                        title={!isBackendAvailable ? 'Destructive actions disabled while backend is disconnected' : 'Delete user'}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination Controls */}
          <div className="px-5 py-3 border-t border-slate-100 bg-slate-50/50 flex items-center justify-between text-xs text-slate-500">
            <span>Showing page {currentPage}</span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                disabled={currentPage <= 1 || isSubmitting}
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                className="px-3 py-1 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 disabled:opacity-40"
              >
                Previous
              </button>
              <button
                type="button"
                disabled={usersState.users.length < 10 || isSubmitting}
                onClick={() => setCurrentPage((p) => p + 1)}
                className="px-3 py-1 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      )}

      {/* User Details Slide-Over Drawer */}
      {selectedUser && (
        <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/50 backdrop-blur-xs">
          <div className="w-full max-w-md bg-white h-full shadow-2xl p-6 overflow-y-auto space-y-6">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200">
              <h3 className="text-base font-bold text-slate-900">User Account Inspection</h3>
              <button
                type="button"
                onClick={() => setSelectedUser(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-800 hover:bg-slate-100"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4 text-xs">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-full bg-blue-100 text-blue-800 font-bold text-base flex items-center justify-center">
                  {selectedUser.avatarInitials || 'US'}
                </div>
                <div>
                  <h4 className="text-sm font-bold text-slate-900">{selectedUser.fullName}</h4>
                  <div className="text-slate-500 font-mono">{selectedUser.email}</div>
                </div>
              </div>

              <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
                <div className="flex justify-between">
                  <span className="text-slate-500">User ID:</span>
                  <span className="font-mono text-slate-800 font-semibold">{selectedUser.id}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Assigned Role:</span>
                  <span className="font-semibold text-slate-800 uppercase">{selectedUser.role}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Account Status:</span>
                  <span className="font-bold text-emerald-600 uppercase">{selectedUser.status || 'Active'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Affiliation:</span>
                  <span className="text-slate-700">{selectedUser.affiliation || '—'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Registered:</span>
                  <span className="text-slate-700 font-mono">{selectedUser.createdAt || '—'}</span>
                </div>
              </div>

              <div className="pt-4 border-t border-slate-200 space-y-2">
                <div className="text-[11px] text-slate-400">
                  Destructive mutations are protected. Changes will be persisted only after backend FastAPI verification.
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
