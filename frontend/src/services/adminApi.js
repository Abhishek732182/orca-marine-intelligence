/**
 * Centralized ORCA Super Admin API Service
 *
 * Provides standardized communication with ORCA backend administrative endpoints.
 * Operates with strict fidelity:
 *  - Dispatches authenticated requests with Bearer JWT tokens.
 *  - Does NOT invent mock success or fabricate fake database entities.
 *  - Accurately captures 404/501/connection failure states and couples them
 *    with authoritative API contracts for backend engineering implementation.
 */

import { BASE_URL } from './orcaApi.js';

export { BASE_URL };

const STORAGE_KEY_TOKEN = 'orca_auth_token';

/**
 * Retrieve current bearer token from client storage
 */
export function getAuthToken() {
  try {
    return localStorage.getItem(STORAGE_KEY_TOKEN) || null;
  } catch {
    return null;
  }
}

/**
 * Authoritative Backend Admin Integration Contracts
 * Defines required endpoints, payload schemas, and access controls for backend engineers.
 */
export const ADMIN_CONTRACTS = {
  overviewMetrics: {
    title: 'Super Admin Overview & Telemetry Metrics',
    method: 'GET',
    endpoint: '/api/admin/metrics',
    requiredRole: 'admin',
    description: 'Returns real-time server telemetry, active agent workloads, registered users tally, and system uptime.',
    requestHeaders: {
      Authorization: 'Bearer <admin_jwt_token>',
      Accept: 'application/json',
    },
    responseSchema: {
      status: 'ok',
      timestamp: '2026-10-15T12:00:00Z',
      server_uptime_seconds: 86400,
      total_registered_users: 142,
      active_sessions_count: 9,
      total_agent_dispatches_24h: 3840,
      average_latency_ms: 145.2,
      active_feature_flags_count: 6,
      system_load: {
        cpu_usage_pct: 18.4,
        memory_usage_mb: 512.8,
      },
    },
  },
  userManagement: {
    title: 'User Management & Role-Based Access Control',
    method: 'GET',
    endpoint: '/api/admin/users',
    requiredRole: 'admin',
    description: 'Lists paginated registered user accounts with roles, affiliations, and account status.',
    requestHeaders: {
      Authorization: 'Bearer <admin_jwt_token>',
      Accept: 'application/json',
    },
    queryParams: {
      role: 'Optional filter: researcher | oceanographer | fleet_officer | admin',
      search: 'Optional string to search by name or email',
      page: 'Page integer (default: 1)',
      limit: 'Page size integer (default: 20)',
    },
    updateRoleEndpoint: {
      method: 'PATCH',
      endpoint: '/api/admin/users/{userId}/role',
      requestBody: {
        role: 'researcher | oceanographer | fleet_officer | admin',
      },
    },
    updateStatusEndpoint: {
      method: 'PATCH',
      endpoint: '/api/admin/users/{userId}/status',
      requestBody: {
        status: 'active | suspended | pending_review',
        reason: 'Optional audit justification string',
      },
    },
  },
  conversationAudit: {
    title: 'Compliance & Conversation Audit Stream',
    method: 'GET',
    endpoint: '/api/admin/conversations/audit',
    requiredRole: 'admin',
    description: 'Allows authorized compliance officers to audit agent conversations, tool invocations, and marine evidence traces.',
    requestHeaders: {
      Authorization: 'Bearer <admin_jwt_token>',
      'X-Audit-Reason': 'Required justification for security log (e.g., COMPLIANCE_REVIEW_Q4)',
    },
    queryParams: {
      agent_id: 'Specialist agent filter',
      user_id: 'User ID filter',
      start_date: 'ISO 8601 timestamp',
      end_date: 'ISO 8601 timestamp',
      has_errors_only: 'boolean flag',
    },
    detailEndpoint: {
      method: 'GET',
      endpoint: '/api/admin/conversations/{conversationId}/audit',
      description: 'Fetches complete audited conversation trace including execution plans and raw agent telemetry.',
    },
  },
  agentManagement: {
    title: 'Specialist Agent Configuration & Registry',
    method: 'GET',
    endpoint: '/api/admin/agents',
    requiredRole: 'admin',
    description: 'Retrieves runtime operational settings for all five specialist agents and the orchestrator.',
    updateEndpoint: {
      method: 'PATCH',
      endpoint: '/api/admin/agents/{agentId}',
      requestBody: {
        is_enabled: true,
        timeout_ms: 30000,
        model_routing: 'deepseek-r1-marine | llama-3.3-70b | gpt-4o-ocean',
        cache_ttl_seconds: 300,
        max_batch_points: 100,
        rate_limit_per_minute: 120,
      },
    },
  },
  featureManagement: {
    title: 'Platform Feature Flags & Capabilities',
    method: 'GET',
    endpoint: '/api/admin/features',
    requiredRole: 'admin',
    description: 'Returns operational feature flags governing autonomous tool approvals, bathymetric modeling, and geospatial boundaries.',
    updateEndpoint: {
      method: 'PATCH',
      endpoint: '/api/admin/features/{flagKey}',
      requestBody: {
        is_enabled: true,
        rollout_percentage: 100,
        allowed_roles: ['admin', 'oceanographer'],
        environment: 'production',
      },
    },
  },
  marineDataMonitoring: {
    title: 'External Marine Telemetry & API Providers',
    method: 'GET',
    endpoint: '/api/admin/marine-sources',
    requiredRole: 'admin',
    description: 'Provides live connection health, rate-limiting budgets, and quota metrics for Open-Meteo, ECMWF, and NOAA sources.',
  },
  securityAuditLogs: {
    title: 'Security Events & Administrative Audit Log',
    method: 'GET',
    endpoint: '/api/admin/audit-logs',
    requiredRole: 'admin',
    description: 'Streams immutable security event logs including login events, role elevations, and parameter alterations.',
    queryParams: {
      event_type: 'AUTH_LOGIN | ROLE_ELEVATION | AGENT_DISPATCH | CONFIG_CHANGE',
      severity: 'INFO | WARNING | CRITICAL | AUDIT',
      limit: 50,
    },
  },
  platformSettings: {
    title: 'Platform Operational Settings & Maritime Thresholds',
    method: 'GET',
    endpoint: '/api/admin/settings',
    requiredRole: 'admin',
    description: 'Fetches persistent platform configurations including maritime hazard limits and global timeout parameters.',
    updateEndpoint: {
      method: 'PATCH',
      endpoint: '/api/admin/settings',
      requestBody: {
        safety_thresholds: {
          max_wind_knots: 25,
          max_wave_height_meters: 2.8,
          reef_buffer_nm: 2.0,
          monsoon_margin_pct: 15,
        },
        system_defaults: {
          request_timeout_ms: 25000,
          default_coordinate_precision: 4,
          enforce_strict_marine_bounds: true,
          operational_mode: 'standard',
        },
      },
    },
  },
};

/**
 * Core authenticated fetch dispatcher
 */
async function adminRequest(endpoint, options = {}, timeoutMs = 12000) {
  const url = `${BASE_URL}${endpoint}`;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  const token = getAuthToken();
  const headers = {
    'Content-Type': 'application/json',
    Accept: 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const startTime = Date.now();

  try {
    const response = await fetch(url, {
      ...options,
      headers,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    const latencyMs = Date.now() - startTime;

    const json = await response.json().catch(() => null);

    if (!response.ok) {
      const err = new Error(
        json?.detail || `Admin request failed with HTTP ${response.status}: ${response.statusText}`
      );
      err.status = response.status;
      err.data = json;
      err.latencyMs = latencyMs;
      err.endpoint = endpoint;
      err.isBackendMissing = response.status === 404 || response.status === 501;
      throw err;
    }

    return {
      success: true,
      status: response.status,
      data: json,
      latencyMs,
      endpoint,
    };
  } catch (error) {
    clearTimeout(timeoutId);
    const latencyMs = Date.now() - startTime;
    if (error.name === 'AbortError') {
      const timeoutErr = new Error(`Admin request to ${endpoint} timed out after ${timeoutMs}ms`);
      timeoutErr.status = 504;
      timeoutErr.latencyMs = latencyMs;
      timeoutErr.endpoint = endpoint;
      timeoutErr.isTimeout = true;
      throw timeoutErr;
    }
    // Flag network connection failures
    if (!error.status) {
      error.isConnectionRefused = true;
      error.status = 0;
      error.latencyMs = latencyMs;
      error.endpoint = endpoint;
    }
    throw error;
  }
}

// ------------------------------------------------------------------------------
// 1. Overview & Health
// ------------------------------------------------------------------------------

export async function fetchAdminOverviewMetrics() {
  return adminRequest('/api/admin/metrics', { method: 'GET' });
}

export async function pingBackendService() {
  return adminRequest('/api/health', { method: 'GET' }, 8000);
}

// ------------------------------------------------------------------------------
// 2. User Management
// ------------------------------------------------------------------------------

export async function fetchUsers(params = {}) {
  const query = new URLSearchParams();
  if (params.role) query.append('role', params.role);
  if (params.search) query.append('search', params.search);
  if (params.page) query.append('page', String(params.page));
  if (params.limit) query.append('limit', String(params.limit));

  const qs = query.toString() ? `?${query.toString()}` : '';
  return adminRequest(`/api/admin/users${qs}`, { method: 'GET' });
}

export async function updateUserRole(userId, newRole) {
  return adminRequest(`/api/admin/users/${encodeURIComponent(userId)}/role`, {
    method: 'PATCH',
    body: JSON.stringify({ role: newRole }),
  });
}

export async function updateUserStatus(userId, status, reason = '') {
  return adminRequest(`/api/admin/users/${encodeURIComponent(userId)}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status, reason }),
  });
}

export async function deleteUserAccount(userId) {
  return adminRequest(`/api/admin/users/${encodeURIComponent(userId)}`, {
    method: 'DELETE',
  });
}

// ------------------------------------------------------------------------------
// 3. Conversation Audit
// ------------------------------------------------------------------------------

export async function fetchConversationAuditList(params = {}) {
  const query = new URLSearchParams();
  if (params.agentId) query.append('agent_id', params.agentId);
  if (params.userId) query.append('user_id', params.userId);
  if (params.search) query.append('search', params.search);
  if (params.limit) query.append('limit', String(params.limit));

  const qs = query.toString() ? `?${query.toString()}` : '';
  return adminRequest(`/api/admin/conversations/audit${qs}`, {
    method: 'GET',
    headers: {
      'X-Audit-Reason': params.auditReason || 'ORCA_SUPER_ADMIN_AUDIT_CONSOLE',
    },
  });
}

export async function fetchConversationAuditDetail(conversationId) {
  return adminRequest(`/api/admin/conversations/${encodeURIComponent(conversationId)}/audit`, {
    method: 'GET',
    headers: {
      'X-Audit-Reason': 'ORCA_CONVERSATION_INSPECTION',
    },
  });
}

// ------------------------------------------------------------------------------
// 4. Agent Management
// ------------------------------------------------------------------------------

export async function fetchAgentsRegistry() {
  return adminRequest('/api/admin/agents', { method: 'GET' });
}

export async function updateAgentConfiguration(agentId, configPayload) {
  return adminRequest(`/api/admin/agents/${encodeURIComponent(agentId)}`, {
    method: 'PATCH',
    body: JSON.stringify(configPayload),
  });
}

export async function probeSpecialistAgent(endpointPath, samplePayload = {}) {
  return adminRequest(endpointPath, {
    method: 'POST',
    body: JSON.stringify(samplePayload),
  }, 15000);
}

// ------------------------------------------------------------------------------
// 5. Feature Management
// ------------------------------------------------------------------------------

export async function fetchFeatureFlags() {
  return adminRequest('/api/admin/features', { method: 'GET' });
}

export async function updateFeatureFlag(flagKey, updatePayload) {
  return adminRequest(`/api/admin/features/${encodeURIComponent(flagKey)}`, {
    method: 'PATCH',
    body: JSON.stringify(updatePayload),
  });
}

// ------------------------------------------------------------------------------
// 6. Marine Data & API Monitoring
// ------------------------------------------------------------------------------

export async function fetchMarineSourcesStatus() {
  return adminRequest('/api/admin/marine-sources', { method: 'GET' });
}

export async function probeMarineProvider(providerKey) {
  return adminRequest(`/api/admin/marine-sources/${encodeURIComponent(providerKey)}/probe`, {
    method: 'POST',
  }, 15000);
}

// ------------------------------------------------------------------------------
// 7. Security & Audit Logs
// ------------------------------------------------------------------------------

export async function fetchSecurityAuditLogs(params = {}) {
  const query = new URLSearchParams();
  if (params.eventType) query.append('event_type', params.eventType);
  if (params.severity) query.append('severity', params.severity);
  if (params.limit) query.append('limit', String(params.limit || 50));

  const qs = query.toString() ? `?${query.toString()}` : '';
  return adminRequest(`/api/admin/audit-logs${qs}`, { method: 'GET' });
}

// ------------------------------------------------------------------------------
// 8. Platform Settings
// ------------------------------------------------------------------------------

export async function fetchPlatformSettings() {
  return adminRequest('/api/admin/settings', { method: 'GET' });
}

export async function updatePlatformSettings(settingsPayload) {
  return adminRequest('/api/admin/settings', {
    method: 'PATCH',
    body: JSON.stringify(settingsPayload),
  });
}
