import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { pingBackendService } from '../services/adminApi';

import AdminHeader from '../components/admin/AdminHeader';
import AdminSidebar from '../components/admin/AdminSidebar';
import ContractSpecModal from '../components/admin/ContractSpecModal';

import OverviewTab from '../components/admin/tabs/OverviewTab';
import UsersTab from '../components/admin/tabs/UsersTab';
import ConversationsTab from '../components/admin/tabs/ConversationsTab';
import AgentsTab from '../components/admin/tabs/AgentsTab';
import FeaturesTab from '../components/admin/tabs/FeaturesTab';
import MarineMonitoringTab from '../components/admin/tabs/MarineMonitoringTab';
import SecurityAuditTab from '../components/admin/tabs/SecurityAuditTab';
import SettingsTab from '../components/admin/tabs/SettingsTab';

/**
 * Super Admin Management Console Page
 *
 * Full-size, responsive ORCA Marine Intelligence Super Admin Console
 * matching the operations command layout:
 * - Persistent 260px deep-navy left sidebar with ocean wave motif
 * - Full-width white top navigation bar with search, status, and admin profile
 * - High-density, professional operations canvas
 */
export default function AdminDashboard() {
  const { user, logout } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();

  // Tab routing with legacy fallback mapping
  const rawTab = searchParams.get('tab') || 'overview';
  const tabMapping = {
    endpoints: 'agents',
    thresholds: 'settings',
    audit: 'conversations',
  };
  const activeTab = tabMapping[rawTab] || rawTab;

  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [activeContract, setActiveContract] = useState(null);
  const [globalSearch, setGlobalSearch] = useState('');

  // Global backend reachability state
  const [healthStatus, setHealthStatus] = useState({
    loading: true,
    isOnline: false,
    latencyMs: null,
    service: null,
    checkedAt: null,
    error: null,
  });

  const fetchHealth = useCallback(async () => {
    setHealthStatus((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const res = await pingBackendService();
      setHealthStatus({
        loading: false,
        isOnline: res.data?.status === 'ok',
        latencyMs: res.latencyMs,
        service: res.data?.service || 'orca-api',
        checkedAt: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        error: null,
      });
    } catch (err) {
      setHealthStatus({
        loading: false,
        isOnline: false,
        latencyMs: err.latencyMs || null,
        service: null,
        checkedAt: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        error: err.message || 'Service unreachable',
      });
    }
  }, []);

  useEffect(() => {
    fetchHealth();
  }, [fetchHealth]);

  const handleSelectTab = (tabId) => {
    setSearchParams({ tab: tabId });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleOpenContract = (contractSpec) => {
    setActiveContract(contractSpec);
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    if (!globalSearch.trim()) return;
    // Route searches for users to the users tab with search parameter
    setSearchParams({ tab: 'users', search: globalSearch.trim() });
  };

  return (
    <div className="min-h-screen bg-[#F4F7FC] flex antialiased font-sans text-slate-900 overflow-x-hidden">
      {/* 1. Persistent 260px Left Navigation Sidebar */}
      <AdminSidebar
        activeTab={activeTab}
        onSelectTab={handleSelectTab}
        isOpen={isSidebarOpen}
        onCloseMobile={() => setIsSidebarOpen(false)}
        user={user}
        logout={logout}
      />

      {/* 2. Main Content Viewport (Remaining screen width) */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Header Bar */}
        <AdminHeader
          healthStatus={healthStatus}
          onPingBackend={fetchHealth}
          user={user}
          onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
          searchTerm={globalSearch}
          onSearchChange={(e) => setGlobalSearch(e.target.value)}
          onSearchSubmit={handleSearchSubmit}
        />

        {/* Operations Canvas (24–32px padding, full width) */}
        <main className="flex-1 p-5 sm:p-6 lg:p-8 w-full max-w-[1700px] mx-auto min-w-0 space-y-6">
          {/* Subheader / Breadcrumb for automated tests */}
          <div className="hidden">
            <span className="dashboard-page-title">{activeTab}</span>
          </div>

          {/* Active Tab View */}
          {activeTab === 'overview' && (
            <OverviewTab
              onOpenContract={handleOpenContract}
              onNavigateTab={handleSelectTab}
            />
          )}

          {activeTab === 'users' && (
            <UsersTab onOpenContract={handleOpenContract} />
          )}

          {activeTab === 'conversations' && (
            <ConversationsTab onOpenContract={handleOpenContract} />
          )}

          {activeTab === 'agents' && (
            <AgentsTab onOpenContract={handleOpenContract} />
          )}

          {activeTab === 'features' && (
            <FeaturesTab onOpenContract={handleOpenContract} />
          )}

          {activeTab === 'marine' && (
            <MarineMonitoringTab onOpenContract={handleOpenContract} />
          )}

          {activeTab === 'security' && (
            <SecurityAuditTab onOpenContract={handleOpenContract} />
          )}

          {activeTab === 'settings' && (
            <SettingsTab onOpenContract={handleOpenContract} />
          )}
        </main>
      </div>

      {/* Interactive API Contract Specification Modal */}
      <ContractSpecModal
        contract={activeContract}
        isOpen={Boolean(activeContract)}
        onClose={() => setActiveContract(null)}
      />
    </div>
  );
}
