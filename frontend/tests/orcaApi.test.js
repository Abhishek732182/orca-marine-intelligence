import { describe, it, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import {
  BASE_URL,
  checkHealth,
  analyzeWeather,
  analyzeOcean,
  analyzeFishingZone,
  analyzeRoute,
  analyzeSafetyRisk,
  analyzeOrchestrator,
  chatAssistant,
  approveTool,
  getConversationHistory,
  getAssistantTools,
  getDeduplicatedAgentResults,
} from '../src/services/orcaApi.js';

describe('orcaApi Frontend Service Tests', () => {
  let originalFetch;
  let lastFetchCall = null;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    lastFetchCall = null;
  });

  it('verifies BASE_URL is configured and defaults to port 8001 without trailing slash', () => {
    assert.ok(typeof BASE_URL === 'string');
    assert.ok(!BASE_URL.endsWith('/'));
    assert.ok(BASE_URL.includes(':8001') || BASE_URL.includes(':8000') || BASE_URL.includes(':8010'));
  });

  it('checkHealth calls GET /api/health', async () => {
    globalThis.fetch = async (url, options) => {
      lastFetchCall = { url, options };
      return {
        ok: true,
        status: 200,
        json: async () => ({ status: 'ok', service: 'orca-api' }),
      };
    };

    const res = await checkHealth();
    assert.equal(res.status, 'ok');
    assert.equal(lastFetchCall.url, `${BASE_URL}/api/health`);
  });

  it('analyzeWeather calls POST /api/agents/weather/analyze', async () => {
    const payload = { latitude: 15.0, longitude: 72.0, location_name: 'Offshore Goa' };
    globalThis.fetch = async (url, options) => {
      lastFetchCall = { url, options };
      return {
        ok: true,
        status: 200,
        json: async () => ({ agent: 'Weather Agent', status: 'success' }),
      };
    };

    const res = await analyzeWeather(payload);
    assert.equal(res.agent, 'Weather Agent');
    assert.equal(lastFetchCall.url, `${BASE_URL}/api/agents/weather/analyze`);
    assert.equal(lastFetchCall.options.method, 'POST');
    assert.deepEqual(JSON.parse(lastFetchCall.options.body), payload);
  });

  it('analyzeOcean calls POST /api/agents/ocean/analyze', async () => {
    const payload = { latitude: 15.0, longitude: 72.0, forecast_time_window_hours: 24 };
    globalThis.fetch = async (url, options) => {
      lastFetchCall = { url, options };
      return {
        ok: true,
        status: 200,
        json: async () => ({ agent: 'Ocean Agent', status: 'success' }),
      };
    };

    const res = await analyzeOcean(payload);
    assert.equal(res.agent, 'Ocean Agent');
    assert.equal(lastFetchCall.url, `${BASE_URL}/api/agents/ocean/analyze`);
    assert.deepEqual(JSON.parse(lastFetchCall.options.body), payload);
  });

  it('analyzeFishingZone calls POST /api/agents/fishing-zone/analyze', async () => {
    const payload = { latitude: 15.0, longitude: 72.0, target_species: 'Mackerel' };
    globalThis.fetch = async (url, options) => {
      lastFetchCall = { url, options };
      return {
        ok: true,
        status: 200,
        json: async () => ({ agent: 'Fishing Zone Agent', status: 'insufficient_evidence' }),
      };
    };

    const res = await analyzeFishingZone(payload);
    assert.equal(res.agent, 'Fishing Zone Agent');
    assert.equal(lastFetchCall.url, `${BASE_URL}/api/agents/fishing-zone/analyze`);
    assert.deepEqual(JSON.parse(lastFetchCall.options.body), payload);
  });

  it('analyzeRoute calls POST /api/agents/route/analyze', async () => {
    const payload = {
      origin_latitude: 18.9,
      origin_longitude: 72.8,
      destination_latitude: 15.4,
      destination_longitude: 73.8,
    };
    globalThis.fetch = async (url, options) => {
      lastFetchCall = { url, options };
      return {
        ok: true,
        status: 200,
        json: async () => ({ agent: 'Route Agent', status: 'success' }),
      };
    };

    const res = await analyzeRoute(payload);
    assert.equal(res.agent, 'Route Agent');
    assert.equal(lastFetchCall.url, `${BASE_URL}/api/agents/route/analyze`);
    assert.deepEqual(JSON.parse(lastFetchCall.options.body), payload);
  });

  it('analyzeSafetyRisk calls POST /api/agents/safety-risk/analyze', async () => {
    const payload = { latitude: 15.0, longitude: 72.0, vessel_type: 'small_craft' };
    globalThis.fetch = async (url, options) => {
      lastFetchCall = { url, options };
      return {
        ok: true,
        status: 200,
        json: async () => ({ agent: 'Safety/Risk Agent', status: 'success' }),
      };
    };

    const res = await analyzeSafetyRisk(payload);
    assert.equal(res.agent, 'Safety/Risk Agent');
    assert.equal(lastFetchCall.url, `${BASE_URL}/api/agents/safety-risk/analyze`);
    assert.deepEqual(JSON.parse(lastFetchCall.options.body), payload);
  });

  it('analyzeOrchestrator calls POST /api/agents/orchestrator/analyze', async () => {
    const payload = {
      latitude: 15.0,
      longitude: 72.0,
      user_objective: 'general_maritime',
      vessel_type: 'small_craft',
    };
    globalThis.fetch = async (url, options) => {
      lastFetchCall = { url, options };
      return {
        ok: true,
        status: 200,
        json: async () => ({ agent: 'ORCA Orchestrator Agent', status: 'success' }),
      };
    };

    const res = await analyzeOrchestrator(payload);
    assert.equal(res.agent, 'ORCA Orchestrator Agent');
    assert.equal(lastFetchCall.url, `${BASE_URL}/api/agents/orchestrator/analyze`);
    assert.deepEqual(JSON.parse(lastFetchCall.options.body), payload);
  });

  it('chatAssistant calls POST /api/agents/assistant/chat', async () => {
    const payload = { message: 'Check wave conditions' };
    globalThis.fetch = async (url, options) => {
      lastFetchCall = { url, options };
      return {
        ok: true,
        status: 200,
        json: async () => ({ conversation_id: 'sess-123', status: 'completed' }),
      };
    };

    const res = await chatAssistant(payload);
    assert.equal(res.conversation_id, 'sess-123');
    assert.equal(lastFetchCall.url, `${BASE_URL}/api/agents/assistant/chat`);
    assert.deepEqual(JSON.parse(lastFetchCall.options.body), payload);
  });

  it('approveTool calls POST /api/agents/assistant/approve', async () => {
    const payload = { conversation_id: 'sess-123', call_id: 'call-456', decision: 'approve' };
    globalThis.fetch = async (url, options) => {
      lastFetchCall = { url, options };
      return {
        ok: true,
        status: 200,
        json: async () => ({ status: 'completed', call_id: 'call-456' }),
      };
    };

    const res = await approveTool(payload);
    assert.equal(res.status, 'completed');
    assert.equal(lastFetchCall.url, `${BASE_URL}/api/agents/assistant/approve`);
  });

  it('getConversationHistory calls GET /api/agents/assistant/conversations/{id}', async () => {
    globalThis.fetch = async (url) => {
      lastFetchCall = { url };
      return {
        ok: true,
        status: 200,
        json: async () => ({ conversation_id: 'sess-123', messages: [] }),
      };
    };

    const res = await getConversationHistory('sess-123');
    assert.equal(res.conversation_id, 'sess-123');
    assert.equal(lastFetchCall.url, `${BASE_URL}/api/agents/assistant/conversations/sess-123`);
  });

  it('getAssistantTools calls GET /api/agents/assistant/tools', async () => {
    globalThis.fetch = async (url) => {
      lastFetchCall = { url };
      return {
        ok: true,
        status: 200,
        json: async () => ({ tools: [] }),
      };
    };

    const res = await getAssistantTools();
    assert.ok(Array.isArray(res.tools));
    assert.equal(lastFetchCall.url, `${BASE_URL}/api/agents/assistant/tools`);
  });



  it('formats FastAPI 422 validation error arrays cleanly', async () => {
    globalThis.fetch = async () => ({
      ok: false,
      status: 422,
      statusText: 'Unprocessable Entity',
      json: async () => ({
        detail: [
          { loc: ['body', 'latitude'], msg: 'Input should be greater than or equal to -90' },
          { loc: ['body', 'longitude'], msg: 'Field required' },
        ],
      }),
    });

    await assert.rejects(
      async () => {
        await analyzeOcean({ latitude: -999 });
      },
      (err) => {
        assert.equal(err.status, 422);
        assert.ok(err.message.includes('body.latitude: Input should be greater than'));
        assert.ok(err.message.includes('body.longitude: Field required'));
        return true;
      }
    );
  });

  it('preserves string error detail on HTTP 500 error', async () => {
    globalThis.fetch = async () => ({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      json: async () => ({
        detail: 'Marine data provider timeout after 25s',
      }),
    });

    await assert.rejects(
      async () => {
        await analyzeOcean({ latitude: 15.0, longitude: 72.0 });
      },
      (err) => {
        assert.equal(err.status, 500);
        assert.equal(err.message, 'Marine data provider timeout after 25s');
        return true;
      }
    );
  });

  describe('Bug 2 Regression: Specialist Agent Cards Deduplication', () => {
    it('verifies that one response containing five agent results produces exactly five result cards', () => {
      const responseAgentResults = {
        'Weather Agent': {
          agent: 'Weather Agent',
          status: 'success',
          analysis: { summary: 'Wind 12 kts, clear' },
        },
        'Ocean Agent': {
          agent: 'Ocean Agent',
          status: 'success',
          analysis: { summary: 'Wave height 1.2m, WMO Code 3' },
        },
        'Fishing Zone Agent': {
          agent: 'Fishing Zone Agent',
          status: 'insufficient_evidence',
          analysis: { summary: 'Physical wave operability suitable; biological evidence insufficient' },
        },
        'Route Agent': {
          agent: 'Route Agent',
          status: 'success',
          analysis: { summary: 'Great-Circle geodesic distance 442.8 km' },
        },
        'Safety/Risk Agent': {
          agent: 'Safety/Risk Agent',
          status: 'success',
          analysis: { summary: 'Risk Level: LOW' },
        },
      };

      const cards = getDeduplicatedAgentResults(responseAgentResults);
      assert.equal(cards.length, 5, 'Must produce exactly five result cards for five agent results');
      const names = cards.map((c) => c.agentName);
      assert.deepEqual(
        names.sort(),
        ['Fishing Zone Agent', 'Ocean Agent', 'Route Agent', 'Safety/Risk Agent', 'Weather Agent'].sort()
      );
    });

    it('verifies that a duplicated response with ten aliased entries produces exactly five result cards without data loss', () => {
      const duplicatedAgentResults = {
        'Weather Agent': {
          agent: 'Weather Agent',
          status: 'success',
          analysis: { summary: 'Wind 12 kts, clear' },
        },
        Weather: {
          agent: 'Weather Agent',
          status: 'success',
          analysis: { summary: 'Wind 12 kts, clear' },
        },
        'Ocean Agent': {
          agent: 'Ocean Agent',
          status: 'success',
          analysis: { summary: 'Wave height 1.2m' },
        },
        Ocean: {
          agent: 'Ocean Agent',
          status: 'success',
          analysis: { summary: 'Wave height 1.2m' },
        },
        'Fishing Zone Agent': {
          agent: 'Fishing Zone Agent',
          status: 'insufficient_evidence',
          analysis: { summary: 'Biological telemetry unavailable' },
        },
        'Fishing Zone': {
          agent: 'Fishing Zone Agent',
          status: 'insufficient_evidence',
          analysis: { summary: 'Biological telemetry unavailable' },
        },
        'Route Agent': {
          agent: 'Route Agent',
          status: 'success',
          analysis: { summary: 'Geodesic distance 442.8 km' },
        },
        Route: {
          agent: 'Route Agent',
          status: 'success',
          analysis: { summary: 'Geodesic distance 442.8 km' },
        },
        'Safety/Risk Agent': {
          agent: 'Safety/Risk Agent',
          status: 'success',
          analysis: { summary: 'Risk Level: MODERATE' },
        },
        Safety: {
          agent: 'Safety/Risk Agent',
          status: 'success',
          analysis: { summary: 'Risk Level: MODERATE' },
        },
      };

      const cards = getDeduplicatedAgentResults(duplicatedAgentResults);
      assert.equal(cards.length, 5, 'Ten aliased entries must deduplicate to exactly five result cards');
      
      // Verify Fishing Zone preserves real insufficient_evidence status
      const fzCard = cards.find((c) => c.agentName === 'Fishing Zone Agent');
      assert.ok(fzCard);
      assert.equal(fzCard.agentData.status, 'insufficient_evidence');
    });

    it('preserves real agent failures and errors when deduplicating', () => {
      const failingAgentResults = {
        'Route Agent': {
          agent: 'Route Agent',
          status: 'failed',
          error: 'Origin and destination coordinates cannot be identical',
          analysis: { summary: 'Execution failed: Identical endpoints' },
        },
        Route: {
          agent: 'Route Agent',
          status: 'failed',
          error: 'Origin and destination coordinates cannot be identical',
          analysis: { summary: 'Execution failed: Identical endpoints' },
        },
      };

      const cards = getDeduplicatedAgentResults(failingAgentResults);
      assert.equal(cards.length, 1);
      assert.equal(cards[0].agentName, 'Route Agent');
      assert.equal(cards[0].agentData.status, 'failed');
      assert.equal(cards[0].agentData.error, 'Origin and destination coordinates cannot be identical');
    });
  });
});

