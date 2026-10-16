/**
 * Reusable ORCA API Client.
 *
 * Calls each of the five independent AI agent endpoints directly.
 * Does NOT call any central AI orchestrator.
 */

const getBaseUrl = () => {
  if (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_ORCA_API_URL) {
    return import.meta.env.VITE_ORCA_API_URL;
  }
  if (typeof process !== 'undefined' && process.env && process.env.VITE_ORCA_API_URL) {
    return process.env.VITE_ORCA_API_URL;
  }
  return 'http://127.0.0.1:8001';
};

const BASE_URL = getBaseUrl().replace(/\/$/, '');

async function postJson(endpoint, data, timeoutMs = 25000) {
  const url = `${BASE_URL}${endpoint}`;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    const json = await response.json().catch(() => null);

    if (!response.ok) {
      let detailMsg = `HTTP ${response.status} ${response.statusText}`;
      if (json && json.detail) {
        detailMsg = Array.isArray(json.detail)
          ? json.detail.map(d => `${d.loc ? d.loc.join('.') + ': ' : ''}${d.msg}`).join('; ')
          : json.detail;
      }
      const err = new Error(detailMsg);
      err.status = response.status;
      err.data = json;
      throw err;
    }

    return json;
  } catch (error) {
    clearTimeout(timeoutId);
    if (error.name === 'AbortError') {
      const timeoutErr = new Error(`Request timed out after ${timeoutMs / 1000} seconds`);
      timeoutErr.status = 504;
      throw timeoutErr;
    }
    throw error;
  }
}

async function getJson(endpoint, timeoutMs = 15000) {
  const url = `${BASE_URL}${endpoint}`;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, { signal: controller.signal });
    clearTimeout(timeoutId);
    const json = await response.json().catch(() => null);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${json?.detail || response.statusText}`);
    }
    return json;
  } catch (err) {
    clearTimeout(timeoutId);
    throw err;
  }
}

async function deleteJson(endpoint, timeoutMs = 15000) {
  const url = `${BASE_URL}${endpoint}`;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, { method: 'DELETE', signal: controller.signal });
    clearTimeout(timeoutId);
    const json = await response.json().catch(() => null);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${json?.detail || response.statusText}`);
    }
    return json;
  } catch (err) {
    clearTimeout(timeoutId);
    throw err;
  }
}

async function patchJson(endpoint, data, timeoutMs = 15000) {
  const url = `${BASE_URL}${endpoint}`;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    const json = await response.json().catch(() => null);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${json?.detail || response.statusText}`);
    }
    return json;
  } catch (err) {
    clearTimeout(timeoutId);
    throw err;
  }
}

/**
 * 1. Weather Agent: POST /api/agents/weather/analyze
 */
export async function analyzeWeather(payload) {
  return postJson('/api/agents/weather/analyze', payload);
}

/**
 * 2. Ocean Agent: POST /api/agents/ocean/analyze
 */
export async function analyzeOcean(payload) {
  return postJson('/api/agents/ocean/analyze', payload);
}

/**
 * 3. Fishing Zone Agent: POST /api/agents/fishing-zone/analyze
 */
export async function analyzeFishingZone(payload) {
  return postJson('/api/agents/fishing-zone/analyze', payload);
}

/**
 * 4. Route Agent: POST /api/agents/route/analyze
 */
export async function analyzeRoute(payload) {
  return postJson('/api/agents/route/analyze', payload);
}

/**
 * 5. Safety/Risk Agent: POST /api/agents/safety-risk/analyze
 */
export async function analyzeSafetyRisk(payload) {
  return postJson('/api/agents/safety-risk/analyze', payload);
}

/**
 * 6. Orchestrator Agent: POST /api/agents/orchestrator/analyze
 */
export async function analyzeOrchestrator(payload) {
  return postJson('/api/agents/orchestrator/analyze', payload);
}

/**
 * 7. AI Workspace Assistant (Agent 6): POST /api/agents/assistant/chat
 */
export async function chatAssistant(payload) {
  return postJson('/api/agents/assistant/chat', payload);
}

/**
 * AI Workspace Assistant Approve: POST /api/agents/assistant/approve
 */
export async function approveTool(payload) {
  return postJson('/api/agents/assistant/approve', payload);
}

/**
 * AI Workspace Assistant History: GET /api/agents/assistant/conversations/{id}
 */
export async function getConversationHistory(conversationId) {
  return getJson(`/api/agents/assistant/conversations/${conversationId}`);
}

/**
 * List all saved conversations for current user: GET /api/agents/assistant/conversations
 */
export async function listUserConversations() {
  return getJson('/api/agents/assistant/conversations');
}

/**
 * Persist or update conversation to server: POST /api/agents/assistant/conversations
 */
export async function saveUserConversation(conversation) {
  return postJson('/api/agents/assistant/conversations', conversation);
}

/**
 * Delete conversation on server: DELETE /api/agents/assistant/conversations/{id}
 */
export async function deleteServerConversation(conversationId) {
  return deleteJson(`/api/agents/assistant/conversations/${conversationId}`);
}

/**
 * Rename conversation on server: PATCH /api/agents/assistant/conversations/{id}
 */
export async function renameServerConversation(conversationId, title) {
  return patchJson(`/api/agents/assistant/conversations/${conversationId}`, { title });
}

/**
 * AI Workspace Assistant Tools: GET /api/agents/assistant/tools
 */
export async function getAssistantTools() {
  return getJson('/api/agents/assistant/tools');
}

/**
 * Health check: GET /api/health
 */
export async function checkHealth() {
  return getJson('/api/health');
}
export { BASE_URL };

/**
 * Deduplicate agent results to ensure each specialist agent result renders at most once.
 * Preserves real agent status, output, evidence, and error details.
 */
export function getDeduplicatedAgentResults(agentResults) {
  if (!agentResults || typeof agentResults !== 'object') return [];
  const canonicalMap = {
    'weather': 'Weather Agent',
    'weather agent': 'Weather Agent',
    'ocean': 'Ocean Agent',
    'ocean agent': 'Ocean Agent',
    'fishing zone': 'Fishing Zone Agent',
    'fishing zone agent': 'Fishing Zone Agent',
    'fishing': 'Fishing Zone Agent',
    'route': 'Route Agent',
    'route agent': 'Route Agent',
    'safety': 'Safety/Risk Agent',
    'safety agent': 'Safety/Risk Agent',
    'safety/risk': 'Safety/Risk Agent',
    'safety/risk agent': 'Safety/Risk Agent',
  };

  const seen = new Map();
  for (const [key, val] of Object.entries(agentResults)) {
    if (!val || typeof val !== 'object') continue;
    const lowerKey = key.trim().toLowerCase();
    const canonicalKey = canonicalMap[lowerKey] || key;
    if (!seen.has(canonicalKey)) {
      seen.set(canonicalKey, { agentName: canonicalKey, agentData: val });
    } else {
      const existing = seen.get(canonicalKey);
      if (key === canonicalKey || (!existing.agentData.analysis && val.analysis) || (val.error && !existing.agentData.error)) {
        seen.set(canonicalKey, { agentName: canonicalKey, agentData: val });
      }
    }
  }
  return Array.from(seen.values());
}
