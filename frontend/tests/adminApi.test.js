import { describe, it, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import {
  BASE_URL,
  ADMIN_CONTRACTS,
  getAuthToken,
  fetchAdminOverviewMetrics,
  pingBackendService,
  fetchUsers,
  updateUserRole,
  updateUserStatus,
  fetchConversationAuditList,
  fetchConversationAuditDetail,
  fetchAgentsRegistry,
  updateAgentConfiguration,
  probeSpecialistAgent,
  fetchFeatureFlags,
  updateFeatureFlag,
  fetchMarineSourcesStatus,
  fetchSecurityAuditLogs,
  fetchPlatformSettings,
  updatePlatformSettings,
} from '../src/services/adminApi.js';

describe('ORCA Super Admin API Service Tests', () => {
  let originalFetch;
  let lastFetchCall = null;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
    // Mock localStorage if in node environment
    if (!globalThis.localStorage) {
      globalThis.localStorage = {
        _store: {},
        getItem(key) {
          return this._store[key] || null;
        },
        setItem(key, value) {
          this._store[key] = String(value);
        },
        removeItem(key) {
          delete this._store[key];
        },
      };
    }
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    lastFetchCall = null;
  });

  it('1. verifies BASE_URL defaults correctly without trailing slash', () => {
    assert.ok(typeof BASE_URL === 'string');
    assert.ok(!BASE_URL.endsWith('/'));
    assert.ok(BASE_URL.includes('http'));
  });

  it('2. verifies ADMIN_CONTRACTS contains authoritative definitions for all 8 modules', () => {
    const expectedKeys = [
      'overviewMetrics',
      'userManagement',
      'conversationAudit',
      'agentManagement',
      'featureManagement',
      'marineDataMonitoring',
      'securityAuditLogs',
      'platformSettings',
    ];

    for (const key of expectedKeys) {
      assert.ok(ADMIN_CONTRACTS[key], `Contract missing for ${key}`);
      assert.ok(ADMIN_CONTRACTS[key].method, `Missing method in ${key}`);
      assert.ok(ADMIN_CONTRACTS[key].endpoint, `Missing endpoint in ${key}`);
      assert.equal(ADMIN_CONTRACTS[key].requiredRole, 'admin');
    }
  });

  it('3. pingBackendService calls GET /api/health with timeout control', async () => {
    globalThis.fetch = async (url, options) => {
      lastFetchCall = { url, options };
      return {
        ok: true,
        status: 200,
        json: async () => ({ status: 'ok', service: 'orca-api' }),
      };
    };

    const res = await pingBackendService();
    assert.equal(res.success, true);
    assert.equal(res.data.status, 'ok');
    assert.equal(lastFetchCall.url, `${BASE_URL}/api/health`);
    assert.equal(lastFetchCall.options.method, 'GET');
  });

  it('4. fetchAdminOverviewMetrics sends Bearer token to GET /api/admin/metrics', async () => {
    localStorage.setItem('orca_auth_token', 'test_admin_jwt_123');
    assert.equal(getAuthToken(), 'test_admin_jwt_123');

    globalThis.fetch = async (url, options) => {
      lastFetchCall = { url, options };
      return {
        ok: true,
        status: 200,
        json: async () => ({
          status: 'ok',
          total_registered_users: 42,
          total_agent_dispatches_24h: 120,
        }),
      };
    };

    const res = await fetchAdminOverviewMetrics();
    assert.equal(res.success, true);
    assert.equal(res.data.total_registered_users, 42);
    assert.equal(lastFetchCall.url, `${BASE_URL}/api/admin/metrics`);
    assert.equal(lastFetchCall.options.headers.Authorization, 'Bearer test_admin_jwt_123');
  });

  it('5. fetchUsers constructs paginated query string properly', async () => {
    globalThis.fetch = async (url, options) => {
      lastFetchCall = { url, options };
      return {
        ok: true,
        status: 200,
        json: async () => ({ users: [], total: 0 }),
      };
    };

    await fetchUsers({ role: 'oceanographer', search: 'Rachel', page: 2, limit: 10 });
    assert.equal(
      lastFetchCall.url,
      `${BASE_URL}/api/admin/users?role=oceanographer&search=Rachel&page=2&limit=10`
    );
  });

  it('6. updateUserRole calls PATCH /api/admin/users/{id}/role with payload', async () => {
    globalThis.fetch = async (url, options) => {
      lastFetchCall = { url, options };
      return {
        ok: true,
        status: 200,
        json: async () => ({ success: true, updated_role: 'admin' }),
      };
    };

    await updateUserRole('usr_007', 'admin');
    assert.equal(lastFetchCall.url, `${BASE_URL}/api/admin/users/usr_007/role`);
    assert.equal(lastFetchCall.options.method, 'PATCH');
    assert.deepEqual(JSON.parse(lastFetchCall.options.body), { role: 'admin' });
  });

  it('7. updateUserStatus calls PATCH /api/admin/users/{id}/status with justification', async () => {
    globalThis.fetch = async (url, options) => {
      lastFetchCall = { url, options };
      return {
        ok: true,
        status: 200,
        json: async () => ({ success: true, status: 'suspended' }),
      };
    };

    await updateUserStatus('usr_007', 'suspended', 'SECURITY_POLICY_VIOLATION');
    assert.equal(lastFetchCall.url, `${BASE_URL}/api/admin/users/usr_007/status`);
    assert.deepEqual(JSON.parse(lastFetchCall.options.body), {
      status: 'suspended',
      reason: 'SECURITY_POLICY_VIOLATION',
    });
  });

  it('8. fetchConversationAuditList sends X-Audit-Reason header for compliance', async () => {
    globalThis.fetch = async (url, options) => {
      lastFetchCall = { url, options };
      return {
        ok: true,
        status: 200,
        json: async () => ({ conversations: [] }),
      };
    };

    await fetchConversationAuditList({
      agentId: 'safety_risk',
      auditReason: 'COMPLIANCE_AUDIT_2026',
    });

    assert.equal(lastFetchCall.url, `${BASE_URL}/api/admin/conversations/audit?agent_id=safety_risk`);
    assert.equal(lastFetchCall.options.headers['X-Audit-Reason'], 'COMPLIANCE_AUDIT_2026');
  });

  it('9. fetchConversationAuditDetail calls GET /api/admin/conversations/{id}/audit', async () => {
    globalThis.fetch = async (url, options) => {
      lastFetchCall = { url, options };
      return {
        ok: true,
        status: 200,
        json: async () => ({ id: 'conv_123', tool_calls: [] }),
      };
    };

    await fetchConversationAuditDetail('conv_123');
    assert.equal(lastFetchCall.url, `${BASE_URL}/api/admin/conversations/conv_123/audit`);
  });

  it('10. updateAgentConfiguration calls PATCH /api/admin/agents/{id}', async () => {
    globalThis.fetch = async (url, options) => {
      lastFetchCall = { url, options };
      return {
        ok: true,
        status: 200,
        json: async () => ({ success: true }),
      };
    };

    const config = { is_enabled: false, timeout_ms: 15000, model_routing: 'llama-3.3-70b-maritime' };
    await updateAgentConfiguration('weather', config);
    assert.equal(lastFetchCall.url, `${BASE_URL}/api/admin/agents/weather`);
    assert.equal(lastFetchCall.options.method, 'PATCH');
    assert.deepEqual(JSON.parse(lastFetchCall.options.body), config);
  });

  it('11. probeSpecialistAgent dispatches POST request with test payload to specialist microservice', async () => {
    globalThis.fetch = async (url, options) => {
      lastFetchCall = { url, options };
      return {
        ok: true,
        status: 200,
        json: async () => ({ agent: 'Ocean Agent', status: 'success' }),
      };
    };

    const payload = { latitude: 15.0, longitude: 72.0 };
    await probeSpecialistAgent('/api/agents/ocean/analyze', payload);
    assert.equal(lastFetchCall.url, `${BASE_URL}/api/agents/ocean/analyze`);
    assert.equal(lastFetchCall.options.method, 'POST');
    assert.deepEqual(JSON.parse(lastFetchCall.options.body), payload);
  });

  it('12. updateFeatureFlag calls PATCH /api/admin/features/{flagKey}', async () => {
    globalThis.fetch = async (url, options) => {
      lastFetchCall = { url, options };
      return {
        ok: true,
        status: 200,
        json: async () => ({ key: 'strict_marine_bounds', is_enabled: true }),
      };
    };

    await updateFeatureFlag('strict_marine_bounds', { is_enabled: true, rollout_percentage: 100 });
    assert.equal(lastFetchCall.url, `${BASE_URL}/api/admin/features/strict_marine_bounds`);
    assert.equal(lastFetchCall.options.method, 'PATCH');
  });

  it('13. fetchMarineSourcesStatus calls GET /api/admin/marine-sources', async () => {
    globalThis.fetch = async (url, options) => {
      lastFetchCall = { url, options };
      return {
        ok: true,
        status: 200,
        json: async () => ({ sources: [] }),
      };
    };

    await fetchMarineSourcesStatus();
    assert.equal(lastFetchCall.url, `${BASE_URL}/api/admin/marine-sources`);
  });

  it('14. fetchSecurityAuditLogs passes severity and event filters', async () => {
    globalThis.fetch = async (url, options) => {
      lastFetchCall = { url, options };
      return {
        ok: true,
        status: 200,
        json: async () => ({ logs: [] }),
      };
    };

    await fetchSecurityAuditLogs({ eventType: 'ROLE_ELEVATION', severity: 'CRITICAL', limit: 25 });
    assert.equal(
      lastFetchCall.url,
      `${BASE_URL}/api/admin/audit-logs?event_type=ROLE_ELEVATION&severity=CRITICAL&limit=25`
    );
  });

  it('15. updatePlatformSettings calls PATCH /api/admin/settings with hazard calibration', async () => {
    globalThis.fetch = async (url, options) => {
      lastFetchCall = { url, options };
      return {
        ok: true,
        status: 200,
        json: async () => ({ success: true }),
      };
    };

    const payload = {
      safety_thresholds: { max_wind_knots: 30, max_wave_height_meters: 3.5 },
    };
    await updatePlatformSettings(payload);
    assert.equal(lastFetchCall.url, `${BASE_URL}/api/admin/settings`);
    assert.equal(lastFetchCall.options.method, 'PATCH');
    assert.deepEqual(JSON.parse(lastFetchCall.options.body), payload);
  });

  it('16. correctly captures 404 / 501 missing backend errors with isBackendMissing flag', async () => {
    globalThis.fetch = async () => ({
      ok: false,
      status: 404,
      statusText: 'Not Found',
      json: async () => ({ detail: 'Endpoint /api/admin/metrics not implemented' }),
    });

    await assert.rejects(
      async () => {
        await fetchAdminOverviewMetrics();
      },
      (err) => {
        assert.equal(err.status, 404);
        assert.equal(err.isBackendMissing, true);
        assert.equal(err.message, 'Endpoint /api/admin/metrics not implemented');
        return true;
      }
    );
  });

  it('17. correctly flags network connection refusal without crashing', async () => {
    globalThis.fetch = async () => {
      const err = new TypeError('fetch failed');
      err.cause = { code: 'ECONNREFUSED' };
      throw err;
    };

    await assert.rejects(
      async () => {
        await pingBackendService();
      },
      (err) => {
        assert.equal(err.isConnectionRefused, true);
        assert.equal(err.status, 0);
        return true;
      }
    );
  });
});
