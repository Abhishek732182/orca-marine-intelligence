import React, { useState } from 'react';

export default function AdminHeader({
  healthStatus,
  onPingBackend,
  user,
  onToggleSidebar,
  searchTerm,
  onSearchChange,
  onSearchSubmit,
}) {
  const [showNotifications, setShowNotifications] = useState(false);
  const [showProfileMenu, setShowProfileMenu] = useState(false);

  return (
    <header className="h-16 px-4 sm:px-6 lg:px-8 bg-white border-b border-slate-200/90 flex items-center justify-between shrink-0 sticky top-0 z-30 shadow-xs">
      {/* Left: Hamburger & Global Search */}
      <div className="flex items-center gap-3 sm:gap-4 flex-1 max-w-xl">
        <button
          type="button"
          onClick={onToggleSidebar}
          className="p-2 rounded-xl text-slate-500 hover:text-slate-800 hover:bg-slate-100 lg:hidden transition-colors"
          aria-label="Toggle navigation sidebar"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>

        {/* Global Search Input Field matching reference image */}
        <form onSubmit={onSearchSubmit || ((e) => e.preventDefault())} className="relative w-full max-w-md">
          <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
          </div>
          <input
            type="text"
            placeholder="Search users, conversations, or system..."
            value={searchTerm || ''}
            onChange={onSearchChange || (() => {})}
            className="w-full pl-10 pr-4 py-2 text-xs rounded-xl border border-slate-200 bg-slate-50/70 text-slate-800 placeholder-slate-400 focus:bg-white focus:outline-hidden focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-all font-sans"
          />
        </form>
      </div>

      {/* Right Controls: Status, Notifications, Admin Profile */}
      <div className="flex items-center gap-4 sm:gap-6">
        {/* Real Backend Service Health Status */}
        <div
          onClick={onPingBackend}
          title="Click to probe backend /api/health"
          className="hidden md:flex items-center gap-2.5 cursor-pointer p-1.5 rounded-xl hover:bg-slate-50 transition-colors"
        >
          <div
            className={`w-2.5 h-2.5 rounded-full ${
              healthStatus.loading
                ? 'bg-amber-400 animate-ping'
                : healthStatus.isOnline
                ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.6)]'
                : 'bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.6)]'
            }`}
          />
          <div className="flex flex-col text-left">
            <span className="text-xs font-bold text-slate-800 leading-tight">
              {healthStatus.loading
                ? 'Probing Status...'
                : healthStatus.isOnline
                ? 'System Online'
                : 'Service Offline'}
            </span>
            <span className="text-[11px] text-slate-500 leading-tight">
              {healthStatus.loading
                ? 'Verifying reachability'
                : healthStatus.isOnline
                ? `FastAPI 200 OK (${healthStatus.latencyMs ? `${healthStatus.latencyMs}ms` : 'ok'})`
                : 'Awaiting backend connection'}
            </span>
          </div>
        </div>

        {/* Notifications Icon with Badge */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setShowNotifications(!showNotifications)}
            className="relative p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-xl transition-colors cursor-pointer"
            aria-label="View system notifications"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.75}
                d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
              />
            </svg>
            {!healthStatus.isOnline && (
              <span className="absolute top-1 right-1 w-2.5 h-2.5 bg-amber-500 rounded-full ring-2 ring-white" />
            )}
          </button>

          {/* Notifications Dropdown */}
          {showNotifications && (
            <div className="absolute right-0 mt-2 w-80 bg-white border border-slate-200 rounded-2xl shadow-xl p-4 z-50 animate-in fade-in space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                <span className="text-xs font-bold text-slate-900">System Notifications</span>
                <span className="text-[11px] text-slate-400">Live Status</span>
              </div>
              <div className="space-y-2 text-xs">
                <div
                  className={`p-2.5 rounded-xl border space-y-0.5 ${
                    healthStatus.isOnline
                      ? 'bg-emerald-50 border-emerald-200 text-emerald-950'
                      : 'bg-amber-50 border-amber-200 text-amber-950'
                  }`}
                >
                  <div className="font-semibold flex items-center justify-between">
                    <span>FastAPI Backend Status</span>
                    <span className="font-mono text-[10px] font-bold">
                      {healthStatus.isOnline ? 'ONLINE' : 'DISCONNECTED'}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-600">
                    {healthStatus.isOnline
                      ? `Liveness verified (HTTP 200 OK • ${healthStatus.latencyMs || 0}ms).`
                      : 'Backend server is not running on port 8001. Awaiting service connection.'}
                  </div>
                </div>
                <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100 space-y-0.5 text-slate-700">
                  <div className="font-semibold text-slate-800">Security Posture Guard</div>
                  <div className="text-[11px] text-slate-500">
                    Client-side route guard active. Backend JWT verification required on all API endpoints.
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Authenticated Administrator Profile Pill */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setShowProfileMenu(!showProfileMenu)}
            className="flex items-center gap-3 p-1.5 pr-2.5 rounded-xl hover:bg-slate-100 transition-colors"
          >
            <div className="w-8 h-8 rounded-full bg-[#1E88E5] text-white flex items-center justify-center shrink-0 shadow-xs">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
                />
              </svg>
            </div>
            <div className="hidden sm:flex flex-col text-left">
              <span className="text-xs font-bold text-slate-900 leading-tight">
                {user?.fullName || 'Super Admin'}
              </span>
              <span className="text-[11px] text-slate-500 leading-tight">Administrator</span>
            </div>
            <svg
              className="w-4 h-4 text-slate-400 hidden sm:block shrink-0"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
        </div>
      </div>
    </header>
  );
}
