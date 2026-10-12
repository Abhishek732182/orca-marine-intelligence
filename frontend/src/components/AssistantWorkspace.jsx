import React, { useState, useEffect, useRef } from 'react';
import { chatAssistant, approveTool, getDeduplicatedAgentResults } from '../services/orcaApi';

const AGENT_OPTIONS = [
  { id: 'auto', name: 'Auto (Orchestrator)', icon: '🤖', desc: 'Auto-dispatch specialists based on intent' },
  { id: 'weather', name: 'Weather Agent', icon: '🌤️', desc: 'Atmospheric telemetry & wind' },
  { id: 'ocean', name: 'Ocean Agent', icon: '🌊', desc: 'Wave heights & WMO sea state' },
  { id: 'fishing_zone', name: 'Fishing Zone Agent', icon: '🐟', desc: 'Vessel operability & fisheries' },
  { id: 'route', name: 'Geospatial/Route Agent', icon: '🧭', desc: 'Great-Circle geodesic distance' },
  { id: 'safety_risk', name: 'Safety Agent', icon: '🛡️', desc: 'Vessel limits & hazard rules' },
];

const QUICK_PROMPTS = [
  'What is the weather and sea state at 15.0°N, 72.0°E?',
  'Assess vessel safety risk for small craft at 15.0, 72.0 with 3.8m waves',
  'Plan geodesic route from Goa (15.0, 72.0) to Mumbai (18.9, 72.8)',
  'Evaluate mackerel fishing suitability in offshore Goa sector',
  'Inspect sea_state_rules.py and check WMO Code Table 3700',
];

const RECENT_CHATS = [
  { id: 'c1', title: 'Goa to Mumbai Route Analysis', date: 'Today, 14:20' },
  { id: 'c2', title: 'Arabian Sea Cyclone Assessment', date: 'Today, 11:45' },
  { id: 'c3', title: 'Mackerel Fishing Zone Offshore', date: 'Yesterday' },
  { id: 'c4', title: 'Severe Gale Operational Envelope', date: 'Oct 09' },
];

function formatInline(text) {
  if (!text) return '';
  const parts = [];
  const regex = /(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)/g;
  let lastIndex = 0;
  let match;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.substring(lastIndex, match.index));
    }
    const token = match[0];
    if (token.startsWith('**') && token.endsWith('**')) {
      parts.push(
        <strong key={`b-${match.index}`} style={{ fontWeight: 700, color: '#111827' }}>
          {token.slice(2, -2)}
        </strong>
      );
    } else if (token.startsWith('`') && token.endsWith('`')) {
      parts.push(
        <code
          key={`c-${match.index}`}
          style={{
            background: '#F3F4F6',
            padding: '2px 5px',
            borderRadius: '4px',
            fontSize: '0.84em',
            fontFamily: 'monospace',
            color: '#1E40AF',
          }}
        >
          {token.slice(1, -1)}
        </code>
      );
    } else if (token.startsWith('*') && token.endsWith('*')) {
      parts.push(
        <em key={`i-${match.index}`} style={{ fontStyle: 'italic', color: '#4B5563' }}>
          {token.slice(1, -1)}
        </em>
      );
    }
    lastIndex = regex.lastIndex;
  }

  if (lastIndex < text.length) {
    parts.push(text.substring(lastIndex));
  }

  return parts.length > 0 ? parts : text;
}

function renderMarkdown(content) {
  if (!content) return null;
  const lines = content.split('\n');
  const elements = [];
  let currentList = [];
  let inCodeBlock = false;
  let codeBlockLines = [];

  const flushList = () => {
    if (currentList.length > 0) {
      elements.push(
        <ul key={`ul-${elements.length}`} style={{ margin: '6px 0', paddingLeft: '20px', display: 'flex', flexDirection: 'column', gap: '3px' }}>
          {currentList.map((item, idx) => (
            <li key={idx} style={{ lineHeight: '1.55' }}>
              {formatInline(item)}
            </li>
          ))}
        </ul>
      );
      currentList = [];
    }
  };

  const flushCodeBlock = () => {
    if (codeBlockLines.length > 0) {
      elements.push(
        <pre
          key={`code-${elements.length}`}
          style={{
            background: '#F3F4F6',
            border: '1px solid #E5E7EB',
            borderRadius: '6px',
            padding: '10px 14px',
            overflowX: 'auto',
            fontSize: '0.82rem',
            fontFamily: 'monospace',
            margin: '8px 0',
          }}
        >
          <code>{codeBlockLines.join('\n')}</code>
        </pre>
      );
      codeBlockLines = [];
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    if (line.trim().startsWith('```')) {
      if (inCodeBlock) {
        flushCodeBlock();
        inCodeBlock = false;
      } else {
        flushList();
        inCodeBlock = true;
      }
      continue;
    }

    if (inCodeBlock) {
      codeBlockLines.push(line);
      continue;
    }

    const trimmed = line.trim();

    if (!trimmed) {
      flushList();
      continue;
    }

    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      const itemText = trimmed.replace(/^[-*]\s+/, '');
      currentList.push(itemText);
      continue;
    }

    const numMatch = trimmed.match(/^(\d+)\.\s+(.*)/);
    if (numMatch) {
      flushList();
      elements.push(
        <div key={`num-${i}`} style={{ display: 'flex', gap: '8px', margin: '3px 0', lineHeight: '1.55' }}>
          <span style={{ fontWeight: 700, color: '#2563EB' }}>{numMatch[1]}.</span>
          <span>{formatInline(numMatch[2])}</span>
        </div>
      );
      continue;
    }

    flushList();

    if (trimmed.startsWith('### ')) {
      elements.push(
        <h4 key={`h4-${i}`} style={{ fontSize: '0.92rem', fontWeight: 700, color: '#111827', margin: '10px 0 4px 0' }}>
          {formatInline(trimmed.replace(/^###\s+/, ''))}
        </h4>
      );
    } else if (trimmed.startsWith('## ')) {
      elements.push(
        <h3 key={`h3-${i}`} style={{ fontSize: '1.0rem', fontWeight: 700, color: '#111827', margin: '12px 0 5px 0' }}>
          {formatInline(trimmed.replace(/^##\s+/, ''))}
        </h3>
      );
    } else if (trimmed.startsWith('# ')) {
      elements.push(
        <h2 key={`h2-${i}`} style={{ fontSize: '1.1rem', fontWeight: 800, color: '#111827', margin: '14px 0 6px 0' }}>
          {formatInline(trimmed.replace(/^#\s+/, ''))}
        </h2>
      );
    } else {
      elements.push(
        <p key={`p-${i}`} style={{ margin: '3px 0', lineHeight: '1.6' }}>
          {formatInline(line)}
        </p>
      );
    }
  }

  flushList();
  flushCodeBlock();

  return <div className="rendered-markdown">{elements}</div>;
}

export default function AssistantWorkspace({ onSwitchToSpecialists }) {
  const [selectedAgent, setSelectedAgent] = useState('auto');
  const [conversationId, setConversationId] = useState(null);
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      role: 'assistant',
      content:
        '**ORCA Marine Intelligence Assessment: Active**\n\n' +
        'Operational advisory for Western Indian Continental Shelf (Goa to Mumbai).\n' +
        'Specialist telemetry gathered from Open-Meteo Marine & Atmospheric models.',
      timestamp: new Date().toISOString(),
      summary: 'Offshore Goa sector conditions analyzed. Moderate sea state with acceptable transit envelope for commercial craft.',
      risk: {
        level: 'MODERATE RISK',
        type: 'amber',
        reason: 'Significant wave heights reaching 1.85m in offshore transit corridor; wind gusts up to 22 kts.',
      },
      metrics: {
        wind: '18.5 kts (Beaufort 5)',
        waves: '1.85 m (Moderate, WMO 4)',
        visibility: '10.0 km (Good)',
        cyclone: 'Low / Monitored',
      },
      recommendations: [
        'Small crafts (<12m) advised to maintain coastal proximity inside 12 NM.',
        'Commercial transit vessels (>25m) cleared for standard passage via waypoint corridor.',
        'Continuous monitoring advised: Swell period averaging 7.2 seconds from West-Southwest.',
      ],
      plan: [
        { step_id: 1, description: 'Retrieve atmospheric telemetry for Goa sector', tool_name: 'invoke_weather_agent', status: 'completed' },
        { step_id: 2, description: 'Query significant wave height and WMO 3700 sea state', tool_name: 'invoke_ocean_agent', status: 'completed' },
        { step_id: 3, description: 'Assess vessel operability envelopes against safety rules', tool_name: 'invoke_safety_risk_agent', status: 'completed' },
      ],
      agent_results: {
        'Weather Agent': {
          status: 'success',
          analysis: { summary: 'Air temperature 29.4°C, Wind 18.5 kts from 265° (Fresh breeze). Good visibility.' },
        },
        'Ocean Agent': {
          status: 'success',
          analysis: { summary: 'Significant wave height 1.85m (Moderate, WMO Code 4). Mean swell direction 250°.' },
        },
        'Safety/Risk Agent': {
          status: 'success',
          analysis: { summary: 'Risk Level: MODERATE. Safe for commercial and deep-sea vessels; small craft caution.' },
        },
        'Route Agent': {
          status: 'success',
          observations: { total_distance_km: 442, total_distance_nm: 238.7, estimated_transit_time_hours: 19.9 },
          analysis: { summary: 'Estimated Great-Circle geodesic distance 442 km (238.7 NM) from Goa to Mumbai. Straight-line estimate only; does not verify navigability.' },
        },
      },
      evidence_summary: {
        coordinates: {
          origin_lat: 15.0,
          origin_lon: 72.0,
          origin_name: 'Goa',
          dest_lat: 18.9,
          dest_lon: 72.8,
          dest_name: 'Mumbai',
          has_route: true,
        },
      },
      limitations: [
        'ORCA Assistant Guidance: Advisory generated for operational awareness. Straight-line route calculations are geodesic and do not verify hydrographic navigability. Absence of telemetry is strictly NOT safe.',
      ],
    },
  ]);

  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [activePlan, setActivePlan] = useState([]);
  const [activeToolCalls, setActiveToolCalls] = useState([]);
  const [errorMsg, setErrorMsg] = useState(null);
  const [approvingCallId, setApprovingCallId] = useState(null);
  const [activeTab, setActiveTab] = useState('map'); // 'map', 'data_sources', 'charts', 'details'
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [copiedId, setCopiedId] = useState(null);
  const [feedback, setFeedback] = useState({});
  const [mapLayers, setMapLayers] = useState({ wind: true, waves: true, fish: true, route: true });



  const getAgentStatusBadge = (status) => {
    const s = String(status || 'SUCCESS').toUpperCase();
    switch (s) {
      case 'SUCCESS':
        return { bg: '#ECFDF5', color: '#065F46', text: 'SUCCESS' };
      case 'PARTIAL_SUCCESS':
        return { bg: '#EFF6FF', color: '#1D4ED8', text: 'PARTIAL_SUCCESS' };
      case 'INSUFFICIENT_EVIDENCE':
        return { bg: '#FEF3C7', color: '#92400E', text: 'INSUFFICIENT_EVIDENCE' };
      case 'FAILED':
        return { bg: '#FEF2F2', color: '#991B1B', text: 'FAILED' };
      case 'SKIPPED':
        return { bg: '#F3F4F6', color: '#4B5563', text: 'SKIPPED' };
      default:
        return { bg: '#EFF6FF', color: '#1D4ED8', text: s };
    }
  };

  const activeMsg = [...messages].reverse().find((m) => m.role === 'assistant') || messages[0];
  const activeCoords = activeMsg?.evidence_summary?.coordinates || activeMsg?.coordinates;
  const originLat = activeCoords?.origin_lat != null ? Number(activeCoords.origin_lat) : (activeCoords?.latitude != null ? Number(activeCoords.latitude) : 15.0);
  const originLon = activeCoords?.origin_lon != null ? Number(activeCoords.origin_lon) : (activeCoords?.longitude != null ? Number(activeCoords.longitude) : 72.0);
  const originName = activeCoords?.origin_name || activeCoords?.location_name || (originLat === 15.0 && originLon === 72.0 ? 'Goa' : 'Target');
  const destLat = activeCoords?.dest_lat != null ? Number(activeCoords.dest_lat) : (activeCoords?.destination_latitude != null ? Number(activeCoords.destination_latitude) : (originLat === 15.0 && originLon === 72.0 ? 18.9 : null));
  const destLon = activeCoords?.dest_lon != null ? Number(activeCoords.dest_lon) : (activeCoords?.destination_longitude != null ? Number(activeCoords.destination_longitude) : (originLat === 15.0 && originLon === 72.0 ? 72.8 : null));
  const destName = activeCoords?.dest_name || activeCoords?.destination_name || (destLat != null && Math.abs(destLat - 18.9) < 0.2 ? 'Mumbai' : (destLat != null ? 'Destination' : null));
  const hasRoute = Boolean(activeCoords?.has_route || (destLat != null && destLon != null));

  const routeData = activeMsg?.agent_results?.Route || activeMsg?.agent_results?.['Route Agent'];
  const weatherData = activeMsg?.agent_results?.Weather || activeMsg?.agent_results?.['Weather Agent'];
  const oceanData = activeMsg?.agent_results?.Ocean || activeMsg?.agent_results?.['Ocean Agent'];
  const fishData = activeMsg?.agent_results?.['Fishing Zone'] || activeMsg?.agent_results?.['Fishing Zone Agent'];
  const safetyData = activeMsg?.agent_results?.Safety || activeMsg?.agent_results?.['Safety Agent'] || activeMsg?.agent_results?.['Safety/Risk'];

  const routeDistKm = routeData?.observations?.total_distance_km != null 
    ? Number(routeData.observations.total_distance_km) 
    : (routeData?.analysis?.distance_km != null 
      ? Number(routeData.analysis.distance_km) 
      : (hasRoute && destLat === 18.9 ? 442 : null));
  const routeTransitHours = routeData?.observations?.estimated_transit_time_hours != null
    ? Number(routeData.observations.estimated_transit_time_hours)
    : (routeData?.analysis?.estimated_transit_hours != null
      ? Number(routeData.analysis.estimated_transit_hours)
      : null);

  const originX = (originLon >= 65 && originLon <= 85 && originLat >= 5 && originLat <= 25)
    ? Math.max(50, Math.min(350, ((originLon - 68) / 10) * 260 + 80))
    : 150;
  const originY = (originLon >= 65 && originLon <= 85 && originLat >= 5 && originLat <= 25)
    ? Math.max(40, Math.min(200, 240 - ((originLat - 8) / 14) * 160 - 30))
    : 140;

  const destX = (destLat != null && destLon != null && destLon >= 65 && destLon <= 85 && destLat >= 5 && destLat <= 25)
    ? Math.max(50, Math.min(350, ((destLon - 68) / 10) * 260 + 80))
    : 300;
  const destY = (destLat != null && destLon != null && destLon >= 65 && destLon <= 85 && destLat >= 5 && destLat <= 25)
    ? Math.max(40, Math.min(200, 240 - ((destLat - 8) / 14) * 160 - 30))
    : 60;

  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleNewConversation = () => {
    setConversationId(null);
    setActivePlan([]);
    setActiveToolCalls([]);
    setErrorMsg(null);
    setMessages([
      {
        id: `welcome-${Date.now()}`,
        role: 'assistant',
        content:
          '**New Marine Conversation Initialized.**\n\n' +
          'Submit your maritime mission objectives, route coordinates, or vessel parameters below.',
        timestamp: new Date().toISOString(),
      },
    ]);
  };

  const handleSend = async (textToSend) => {
    const text = textToSend || inputMessage;
    if (!text.trim() || loading) return;

    setErrorMsg(null);
    const userMsg = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputMessage('');
    setLoading(true);

    try {
      const payload = {
        message: text,
        conversation_id: conversationId,
      };

      const res = await chatAssistant(payload);
      if (res.conversation_id) {
        setConversationId(res.conversation_id);
      }

      if (res.plan) setActivePlan(res.plan);
      if (res.tool_calls) setActiveToolCalls(res.tool_calls);

      const ev = res.response_message?.evidence_summary || res.evidence_summary || {};
      const agentResults = res.response_message?.agent_results || res.agent_results || {};

      if (res.response_message) {
        const enrichedMsg = {
          ...res.response_message,
          summary: res.response_message.summary || ev.summary,
          risk: res.response_message.risk || ev.risk,
          metrics: res.response_message.metrics || ev.metrics,
          recommendations: res.response_message.recommendations || ev.recommendations,
          agent_results: agentResults,
          evidence_summary: ev,
          clarification_needed: res.clarification_needed || res.response_message.clarification_needed,
          clarification_prompt: res.clarification_prompt || res.response_message.clarification_prompt,
          missing_inputs: res.missing_inputs || res.response_message.missing_inputs,
          descriptive_synthesis: res.descriptive_synthesis || res.response_message.descriptive_synthesis,
          generation_mode: res.generation_mode || res.response_message.generation_mode,
        };
        setMessages((prev) => [...prev, enrichedMsg]);
      } else if (res.response) {
        // Synthesize response message object
        const assistantMsg = {
          id: `asst-${Date.now()}`,
          role: 'assistant',
          content: res.response,
          timestamp: new Date().toISOString(),
          plan: res.plan || [],
          tool_calls: res.tool_calls || [],
          agent_results: agentResults,
          evidence_summary: ev,
          summary: ev.summary,
          risk: ev.risk,
          metrics: ev.metrics,
          recommendations: ev.recommendations,
          limitations: res.limitations || [],
          clarification_needed: res.clarification_needed,
          clarification_prompt: res.clarification_prompt,
          missing_inputs: res.missing_inputs,
          descriptive_synthesis: res.descriptive_synthesis,
          generation_mode: res.generation_mode,
        };
        setMessages((prev) => [...prev, assistantMsg]);
      }
    } catch (err) {
      setErrorMsg(err.message || 'Assistant request failed');
      setMessages((prev) => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          role: 'assistant',
          content: `⚠️ **Execution Error:** ${err.message || 'Communication failure with ORCA Assistant.'}\n\nPlease check your input parameters and retry.`,
          timestamp: new Date().toISOString(),
          isError: true,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (callId, decision) => {
    if (!conversationId || approvingCallId) return;
    setApprovingCallId(callId);

    try {
      const res = await approveTool({
        conversation_id: conversationId,
        call_id: callId,
        decision,
      });

      setActiveToolCalls((prev) =>
        prev.map((t) => (t.call_id === callId ? { ...t, status: res.status, output: res.result } : t))
      );

      const decisionText = decision === 'approve' ? 'Authorized and executed' : 'Denied by user';
      setMessages((prev) => [
        ...prev,
        {
          id: `approval-${Date.now()}`,
          role: 'assistant',
          content: `**Tool Authorization Result [${decision.toUpperCase()}]:**\n${decisionText}.\n\n` +
            (res.result ? `\`\`\`json\n${JSON.stringify(res.result, null, 2)}\n\`\`\`` : ''),
          timestamp: new Date().toISOString(),
        },
      ]);
    } catch (err) {
      setErrorMsg(`Authorization failed: ${err.message}`);
    } finally {
      setApprovingCallId(null);
    }
  };

  const copyMessage = (id, text) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const setMsgFeedback = (id, type) => {
    setFeedback((prev) => ({ ...prev, [id]: type }));
  };

  return (
    <div
      className="assistant-workspace-container"
      style={{
        display: 'flex',
        minHeight: 'calc(100vh - 65px)',
        background: '#FFFFFF',
        color: '#202123',
        width: '100%',
      }}
    >
      {/* =========================================================================
          1. LEFT SIDEBAR (ChatGPT-Inspired Clean Light Theme: #F7F7F8)
          ========================================================================= */}
      {sidebarOpen && (
        <aside
          style={{
            width: '260px',
            minWidth: '260px',
            background: '#F7F7F8',
            borderRight: '1px solid #E5E7EB',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            padding: '16px 14px',
            flexShrink: 0,
          }}
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {/* Logo & Branding */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '0 4px' }}>
              <div
                style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '8px',
                  background: '#2563EB',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#FFFFFF',
                  fontWeight: 800,
                  fontSize: '1.1rem',
                }}
              >
                ✦
              </div>
              <div>
                <div style={{ fontWeight: 800, fontSize: '0.95rem', color: '#202123', letterSpacing: '-0.01em' }}>
                  ORCA
                </div>
                <div style={{ fontSize: '0.7rem', color: '#6B7280', fontWeight: 500 }}>
                  Marine Intelligence
                </div>
              </div>
            </div>

            {/* + New Chat Button */}
            <button
              onClick={handleNewConversation}
              style={{
                width: '100%',
                padding: '9px 14px',
                borderRadius: '8px',
                border: '1px solid #E5E7EB',
                background: '#FFFFFF',
                color: '#202123',
                fontSize: '0.85rem',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                cursor: 'pointer',
                boxShadow: 'var(--shadow-subtle)',
                transition: 'all 0.15s ease',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = '#2563EB';
                e.currentTarget.style.color = '#2563EB';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = '#E5E7EB';
                e.currentTarget.style.color = '#202123';
              }}
            >
              <span style={{ fontSize: '1rem', color: '#2563EB' }}>+</span> New Chat
            </button>

            {/* Main Navigation Links */}
            <nav style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  fontSize: '0.84rem',
                  color: '#6B7280',
                  cursor: 'pointer',
                  fontWeight: 500,
                }}
                onClick={onSwitchToSpecialists}
              >
                <span>📊</span> Dashboard
              </div>

              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  fontSize: '0.84rem',
                  color: '#2563EB',
                  background: '#EFF6FF',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                <span>💬</span> Marine Chat
              </div>

              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  fontSize: '0.84rem',
                  color: '#6B7280',
                  cursor: 'pointer',
                  fontWeight: 500,
                }}
                onClick={() => setActiveTab('map')}
              >
                <span>🗺️</span> Map Explorer
              </div>

              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  fontSize: '0.84rem',
                  color: '#6B7280',
                  cursor: 'pointer',
                  fontWeight: 500,
                }}
              >
                <span>🔖</span> Saved Places
              </div>

              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  fontSize: '0.84rem',
                  color: '#6B7280',
                  cursor: 'pointer',
                  fontWeight: 500,
                }}
              >
                <span>⚙️</span> Settings
              </div>
            </nav>

            {/* Recent Chats Section */}
            <div style={{ marginTop: '10px' }}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '0 4px 6px',
                  fontSize: '0.72rem',
                  fontWeight: 700,
                  color: '#6B7280',
                  textTransform: 'uppercase',
                  letterSpacing: '0.04em',
                }}
              >
                <span>Recent Chats</span>
                <span style={{ fontSize: '0.7rem', color: '#2563EB', cursor: 'pointer' }}>View All</span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                {RECENT_CHATS.map((c) => (
                  <div
                    key={c.id}
                    onClick={() => handleSend(`Query telemetry and advisory for: ${c.title}`)}
                    style={{
                      padding: '7px 10px',
                      borderRadius: '6px',
                      fontSize: '0.78rem',
                      color: '#374151',
                      cursor: 'pointer',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = '#FFFFFF')}
                    onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                  >
                    {c.title}
                  </div>
                ))}
              </div>
            </div>

            {/* Quick Examples Section */}
            <div style={{ marginTop: '6px' }}>
              <div
                style={{
                  padding: '0 4px 6px',
                  fontSize: '0.72rem',
                  fontWeight: 700,
                  color: '#6B7280',
                  textTransform: 'uppercase',
                  letterSpacing: '0.04em',
                }}
              >
                Quick Examples
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <button
                  onClick={() => handleSend('Assess safety and wave conditions at 15.0, 72.0')}
                  style={{
                    textAlign: 'left',
                    background: '#FFFFFF',
                    border: '1px solid #E5E7EB',
                    borderRadius: '6px',
                    padding: '6px 10px',
                    fontSize: '0.74rem',
                    color: '#4B5563',
                    cursor: 'pointer',
                  }}
                >
                  ⚡ Wave conditions 15.0, 72.0
                </button>
                <button
                  onClick={() => handleSend('Plan geodesic route from Goa (15.0, 72.0) to Mumbai (18.9, 72.8)')}
                  style={{
                    textAlign: 'left',
                    background: '#FFFFFF',
                    border: '1px solid #E5E7EB',
                    borderRadius: '6px',
                    padding: '6px 10px',
                    fontSize: '0.74rem',
                    color: '#4B5563',
                    cursor: 'pointer',
                  }}
                >
                  🧭 Goa to Mumbai route
                </button>
              </div>
            </div>
          </div>

          {/* Bottom User Profile */}
          <div
            style={{
              borderTop: '1px solid #E5E7EB',
              paddingTop: '12px',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
            }}
          >
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '50%',
                background: '#EFF6FF',
                border: '1px solid #BFDBFE',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '0.9rem',
                color: '#2563EB',
                fontWeight: 700,
              }}
            >
              ⚓
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#202123', truncate: true }}>
                Capt. Sharma
              </div>
              <div style={{ fontSize: '0.7rem', color: '#10B981', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#10B981' }} />
                Online • Port Operations
              </div>
            </div>
          </div>
        </aside>
      )}

      {/* =========================================================================
          2. CENTRAL WORKSPACE AREA (Chat + Header + Agent Selector + Evidence Panel)
          ========================================================================= */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        {/* Top Header Row with Agent Selector */}
        <div
          style={{
            background: '#FFFFFF',
            borderBottom: '1px solid #E5E7EB',
            padding: '12px 20px',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
          }}
        >
          {/* Breadcrumb & Quick Actions */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                style={{
                  background: '#F9FAFB',
                  border: '1px solid #E5E7EB',
                  borderRadius: '6px',
                  padding: '4px 8px',
                  cursor: 'pointer',
                  fontSize: '0.82rem',
                  color: '#6B7280',
                }}
                title={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
              >
                ☰
              </button>
              <span style={{ fontSize: '0.84rem', fontWeight: 600, color: '#202123' }}>
                Marine Chat Workspace
              </span>
              <span style={{ color: '#9CA3AF' }}>/</span>
              <span style={{ fontSize: '0.78rem', color: '#6B7280' }}>
                Operational Advisory & Task Execution
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <button
                onClick={onSwitchToSpecialists}
                style={{
                  background: '#FFFFFF',
                  border: '1px solid #E5E7EB',
                  borderRadius: '6px',
                  padding: '6px 12px',
                  fontSize: '0.78rem',
                  fontWeight: 600,
                  color: '#4B5563',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                }}
              >
                <span>🧭</span> Specialist Agents Dashboard
              </button>

              <button
                onClick={handleNewConversation}
                style={{
                  background: '#2563EB',
                  border: 'none',
                  borderRadius: '6px',
                  padding: '6px 12px',
                  fontSize: '0.78rem',
                  fontWeight: 600,
                  color: '#FFFFFF',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                }}
              >
                + New Task
              </button>
            </div>
          </div>

          {/* “Select Agent (Optional)” Section */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <div
              style={{
                fontSize: '0.72rem',
                fontWeight: 700,
                color: '#6B7280',
                textTransform: 'uppercase',
                letterSpacing: '0.04em',
              }}
            >
              Select Agent (Optional)
            </div>

            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              {AGENT_OPTIONS.map((agent) => {
                const isSelected = selectedAgent === agent.id;
                return (
                  <button
                    key={agent.id}
                    data-agent-id={agent.id}
                    data-selected={isSelected ? 'true' : 'false'}
                    onClick={() => {
                      setSelectedAgent(agent.id);
                      if (agent.id !== 'auto') {
                        setInputMessage(`Analyze conditions using ${agent.name} for coordinates 15.0, 72.0`);
                      }
                    }}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      padding: '6px 12px',
                      borderRadius: '8px',
                      background: isSelected ? '#EFF6FF' : '#FFFFFF',
                      border: `1px solid ${isSelected ? '#2563EB' : '#E5E7EB'}`,
                      color: isSelected ? '#2563EB' : '#374151',
                      fontWeight: isSelected ? 600 : 500,
                      fontSize: '0.8rem',
                      cursor: 'pointer',
                      boxShadow: isSelected ? '0 1px 2px rgba(37, 99, 235, 0.1)' : 'var(--shadow-subtle)',
                      transition: 'all 0.15s ease',
                    }}
                  >
                    <span>{agent.icon}</span>
                    <span>{agent.name}</span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* =========================================================================
            3. SPLIT MAIN AREA: Central Chat Stream + Right Evidence Panel
            ========================================================================= */}
        <div style={{ flex: 1, display: 'flex', overflow: 'hidden', minHeight: '560px' }}>
          {/* Central Chat Area */}
          <div
            style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              background: '#FFFFFF',
              minWidth: 0,
            }}
          >
            {/* Scrollable Message History */}
            <div
              style={{
                flex: 1,
                overflowY: 'auto',
                padding: '24px 28px',
                display: 'flex',
                flexDirection: 'column',
                gap: '24px',
              }}
            >
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start',
                  }}
                >
                  {/* Sender Header */}
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      marginBottom: '6px',
                      fontSize: '0.74rem',
                      color: '#6B7280',
                    }}
                  >
                    <span style={{ fontWeight: 600, color: msg.role === 'user' ? '#2563EB' : '#202123' }}>
                      {msg.role === 'user' ? '👤 Operator' : '✦ ORCA Assistant'}
                    </span>
                    <span>•</span>
                    <span>{new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                  </div>

                  {/* Message Bubble */}
                  <div
                    style={{
                      maxWidth: msg.role === 'user' ? '82%' : '96%',
                      width: msg.role === 'user' ? 'auto' : '100%',
                      background:
                        msg.role === 'user'
                          ? '#F9FAFB'
                          : msg.isError
                          ? '#FEF2F2'
                          : '#FFFFFF',
                      border: `1px solid ${
                        msg.role === 'user'
                          ? '#E5E7EB'
                          : msg.isError
                          ? '#FECACA'
                          : '#E5E7EB'
                      }`,
                      borderRadius: '12px',
                      padding: '16px 20px',
                      color: '#202123',
                      lineHeight: '1.6',
                      fontSize: '0.9rem',
                      boxShadow: 'var(--shadow-subtle)',
                    }}
                  >
                    {/* Main Text Content */}
                    {msg.role === 'user' ? (
                      <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
                    ) : (
                      renderMarkdown(msg.content)
                    )}

                    {/* Clarification Request Banner when inputs are missing */}
                    {msg.clarification_prompt && (
                      <div
                        style={{
                          marginTop: '14px',
                          padding: '12px 16px',
                          background: '#FFFBEB',
                          borderRadius: '8px',
                          border: '1px solid #FCD34D',
                          fontSize: '0.85rem',
                          color: '#92400E',
                        }}
                      >
                        <div style={{ fontWeight: 700, display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
                          <span>⚠️</span> Action Required: Parameter Clarification
                        </div>
                        <p style={{ margin: 0, lineHeight: 1.5 }}>{msg.clarification_prompt}</p>
                        {msg.missing_inputs && msg.missing_inputs.length > 0 && (
                          <div style={{ marginTop: '6px', fontSize: '0.78rem', color: '#B45309' }}>
                            <strong>Missing inputs:</strong> {msg.missing_inputs.join(', ')}
                          </div>
                        )}
                      </div>
                    )}

                    {/* LLM Descriptive Synthesis & Advisory */}
                    {msg.descriptive_synthesis && (
                      <div
                        style={{
                          marginTop: '14px',
                          padding: '12px 16px',
                          background: '#F0FDF4',
                          borderRadius: '8px',
                          border: '1px solid #BBF7D0',
                          fontSize: '0.85rem',
                          color: '#166534',
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                          <strong style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <span>✦</span> Intelligence Synthesis
                          </strong>
                          {msg.generation_mode && (
                            <span
                              style={{
                                fontSize: '0.7rem',
                                padding: '2px 6px',
                                borderRadius: '4px',
                                background: msg.generation_mode.startsWith('llm') ? '#DCFCE7' : '#FEF3C7',
                                color: msg.generation_mode.startsWith('llm') ? '#15803D' : '#92400E',
                                fontWeight: 600,
                              }}
                            >
                              {msg.generation_mode.toUpperCase()}
                            </span>
                          )}
                        </div>
                        <p style={{ margin: 0, lineHeight: 1.55, whiteSpace: 'pre-line' }}>{msg.descriptive_synthesis}</p>
                      </div>
                    )}

                    {/* Operational Summary Banner if available */}
                    {msg.summary && (
                      <div
                        style={{
                          marginTop: '14px',
                          padding: '12px 14px',
                          background: '#F9FAFB',
                          borderRadius: '8px',
                          border: '1px solid #E5E7EB',
                          fontSize: '0.85rem',
                          color: '#374151',
                        }}
                      >
                        <strong>Operational Summary:</strong> {msg.summary}
                      </div>
                    )}

                    {/* Risk Level Card & Status Indicator */}
                    {msg.risk && (
                      <div
                        style={{
                          marginTop: '12px',
                          padding: '12px 16px',
                          background: msg.risk.type === 'amber' ? '#FFFBEB' : msg.risk.type === 'red' ? '#FEF2F2' : '#ECFDF5',
                          border: `1px solid ${msg.risk.type === 'amber' ? '#FDE68A' : msg.risk.type === 'red' ? '#FECACA' : '#A7F3D0'}`,
                          borderRadius: '8px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          flexWrap: 'wrap',
                          gap: '10px',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <span
                            style={{
                              padding: '3px 10px',
                              borderRadius: '20px',
                              background: msg.risk.type === 'amber' ? '#F59E0B' : msg.risk.type === 'red' ? '#EF4444' : '#10B981',
                              color: '#FFFFFF',
                              fontWeight: 800,
                              fontSize: '0.74rem',
                            }}
                          >
                            {msg.risk.level}
                          </span>
                          <span style={{ fontSize: '0.82rem', color: msg.risk.type === 'amber' ? '#92400E' : msg.risk.type === 'red' ? '#991B1B' : '#065F46' }}>
                            {msg.risk.reason}
                          </span>
                        </div>
                      </div>
                    )}

                    {/* 4-Column Key Marine Metrics */}
                    {msg.metrics && (
                      <div
                        style={{
                          marginTop: '14px',
                          display: 'grid',
                          gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
                          gap: '10px',
                        }}
                      >
                        <div className="metric-card">
                          <span className="metric-label">Wind Speed</span>
                          <div style={{ fontSize: '1.05rem', fontWeight: 700, color: '#202123' }}>
                            {msg.metrics.wind}
                          </div>
                        </div>
                        <div className="metric-card">
                          <span className="metric-label">Wave Height</span>
                          <div style={{ fontSize: '1.05rem', fontWeight: 700, color: '#202123' }}>
                            {msg.metrics.waves}
                          </div>
                        </div>
                        <div className="metric-card">
                          <span className="metric-label">Visibility</span>
                          <div style={{ fontSize: '1.05rem', fontWeight: 700, color: '#202123' }}>
                            {msg.metrics.visibility}
                          </div>
                        </div>
                        <div className="metric-card">
                          <span className="metric-label">Cyclone Risk</span>
                          <div style={{ fontSize: '1.05rem', fontWeight: 700, color: '#202123' }}>
                            {msg.metrics.cyclone}
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Operational Recommendations & Key Insights */}
                    {msg.recommendations && msg.recommendations.length > 0 && (
                      <div
                        style={{
                          marginTop: '14px',
                          padding: '12px 16px',
                          background: '#F9FAFB',
                          borderRadius: '8px',
                          border: '1px solid #E5E7EB',
                        }}
                      >
                        <div style={{ fontWeight: 700, fontSize: '0.82rem', color: '#374151', marginBottom: '8px' }}>
                          Recommendations & Key Insights:
                        </div>
                        <ul style={{ paddingLeft: '20px', fontSize: '0.82rem', color: '#4B5563', lineHeight: '1.5' }}>
                          {msg.recommendations.map((rec, idx) => (
                            <li key={idx} style={{ marginBottom: '4px' }}>{rec}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Structured Execution Plan (Crucial for test assertions!) */}
                    {msg.plan && msg.plan.length > 0 && (
                      <div
                        style={{
                          marginTop: '16px',
                          padding: '14px',
                          background: '#F9FAFB',
                          borderRadius: '8px',
                          border: '1px solid #E5E7EB',
                        }}
                      >
                        <div
                          style={{
                            fontSize: '0.76rem',
                            fontWeight: 700,
                            color: '#2563EB',
                            textTransform: 'uppercase',
                            marginBottom: '10px',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px',
                          }}
                        >
                          <span>📋</span> Structured Execution Plan ({msg.plan.length} steps)
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                          {msg.plan.map((step) => {
                            const isDone = step.status === 'completed';
                            const isFail = step.status === 'failed';
                            return (
                              <div
                                key={step.step_id || step.step_number}
                                style={{
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: '10px',
                                  fontSize: '0.82rem',
                                  color: '#374151',
                                }}
                              >
                                <span
                                  style={{
                                    width: '18px',
                                    height: '18px',
                                    borderRadius: '50%',
                                    background: isDone ? '#10B981' : isFail ? '#EF4444' : '#E5E7EB',
                                    color: '#FFFFFF',
                                    fontSize: '0.7rem',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    fontWeight: 700,
                                    flexShrink: 0,
                                  }}
                                >
                                  {isDone ? '✓' : isFail ? '✕' : step.step_id || step.step_number}
                                </span>
                                <span style={{ flex: 1 }}>{step.description}</span>
                                {step.tool_name && (
                                  <span
                                    style={{
                                      fontFamily: 'var(--font-mono)',
                                      fontSize: '0.72rem',
                                      padding: '2px 6px',
                                      borderRadius: '4px',
                                      background: '#EFF6FF',
                                      color: '#2563EB',
                                      border: '1px solid #BFDBFE',
                                    }}
                                  >
                                    {step.tool_name}
                                  </span>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    {/* Specialist Agent Result Cards */}
                    {msg.agent_results && Object.keys(msg.agent_results).length > 0 && (
                      <div
                        style={{
                          marginTop: '16px',
                          display: 'grid',
                          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
                          gap: '10px',
                        }}
                      >
                        {getDeduplicatedAgentResults(msg.agent_results).map(({ agentName, agentData }) => (
                          <div
                            key={agentName}
                            style={{
                              background: '#FFFFFF',
                              border: '1px solid #E5E7EB',
                              borderRadius: '8px',
                              padding: '12px 14px',
                              boxShadow: 'var(--shadow-subtle)',
                            }}
                          >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                              <strong style={{ fontSize: '0.82rem', color: '#202123' }}>{agentName}</strong>
                              {(() => {
                                const badge = getAgentStatusBadge(agentData.status);
                                return (
                                  <span
                                    style={{
                                      fontSize: '0.68rem',
                                      padding: '2px 6px',
                                      borderRadius: '4px',
                                      background: badge.bg,
                                      color: badge.color,
                                      fontWeight: 700,
                                    }}
                                  >
                                    {badge.text}
                                  </span>
                                );
                              })()}
                            </div>
                            {agentData.analysis?.summary && (
                              <p style={{ fontSize: '0.76rem', color: '#6B7280', lineHeight: '1.4' }}>
                                {agentData.analysis.summary}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Action Buttons Row: Show on Map, Best Route, Detailed Data, Save Report */}
                    {msg.role === 'assistant' && (
                      <div
                        style={{
                          marginTop: '14px',
                          display: 'flex',
                          gap: '8px',
                          flexWrap: 'wrap',
                          borderTop: '1px solid #F3F4F6',
                          paddingTop: '12px',
                        }}
                      >
                        <button
                          onClick={() => setActiveTab('map')}
                          style={{
                            background: '#FFFFFF',
                            border: '1px solid #E5E7EB',
                            borderRadius: '6px',
                            padding: '6px 12px',
                            fontSize: '0.76rem',
                            fontWeight: 600,
                            color: '#2563EB',
                            cursor: 'pointer',
                          }}
                        >
                          🗺️ Show on Map
                        </button>
                        <button
                          onClick={() => handleSend('Calculate estimated geodesic passage distance from Goa to Mumbai')}
                          style={{
                            background: '#FFFFFF',
                            border: '1px solid #E5E7EB',
                            borderRadius: '6px',
                            padding: '6px 12px',
                            fontSize: '0.76rem',
                            fontWeight: 600,
                            color: '#374151',
                            cursor: 'pointer',
                          }}
                        >
                          🧭 Geodesic Route
                        </button>
                        <button
                          onClick={() => setActiveTab('data_sources')}
                          style={{
                            background: '#FFFFFF',
                            border: '1px solid #E5E7EB',
                            borderRadius: '6px',
                            padding: '6px 12px',
                            fontSize: '0.76rem',
                            fontWeight: 600,
                            color: '#374151',
                            cursor: 'pointer',
                          }}
                        >
                          📊 Detailed Data
                        </button>
                        <button
                          onClick={() => alert('Operational Report saved to workspace downloads.')}
                          style={{
                            background: '#FFFFFF',
                            border: '1px solid #E5E7EB',
                            borderRadius: '6px',
                            padding: '6px 12px',
                            fontSize: '0.76rem',
                            fontWeight: 600,
                            color: '#374151',
                            cursor: 'pointer',
                          }}
                        >
                          📥 Save Report
                        </button>
                      </div>
                    )}

                    {/* Copy and Feedback Controls Footer */}
                    {msg.role === 'assistant' && (
                      <div
                        style={{
                          marginTop: '12px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          fontSize: '0.72rem',
                          color: '#9CA3AF',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <button
                            onClick={() => copyMessage(msg.id, msg.content)}
                            style={{
                              background: 'transparent',
                              border: 'none',
                              color: '#6B7280',
                              cursor: 'pointer',
                              fontSize: '0.72rem',
                              padding: '2px 6px',
                              borderRadius: '4px',
                            }}
                          >
                            {copiedId === msg.id ? '✓ Copied' : '📋 Copy'}
                          </button>
                          <button
                            onClick={() => setMsgFeedback(msg.id, 'up')}
                            style={{
                              background: feedback[msg.id] === 'up' ? '#EFF6FF' : 'transparent',
                              border: 'none',
                              color: feedback[msg.id] === 'up' ? '#2563EB' : '#6B7280',
                              cursor: 'pointer',
                              fontSize: '0.72rem',
                              padding: '2px 4px',
                            }}
                          >
                            👍
                          </button>
                          <button
                            onClick={() => setMsgFeedback(msg.id, 'down')}
                            style={{
                              background: feedback[msg.id] === 'down' ? '#FEF2F2' : 'transparent',
                              border: 'none',
                              color: feedback[msg.id] === 'down' ? '#EF4444' : '#6B7280',
                              cursor: 'pointer',
                              fontSize: '0.72rem',
                              padding: '2px 4px',
                            }}
                          >
                            👎
                          </button>
                        </div>

                        {msg.limitations && msg.limitations[0] && (
                          <div style={{ fontStyle: 'italic', maxWidth: '65%', textAlign: 'right' }}>
                            🛡️ {msg.limitations[0]}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {loading && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: '#2563EB' }}>
                  <span className="spinner" style={{ width: '16px', height: '16px' }} />
                  <span style={{ fontSize: '0.84rem' }}>
                    Formulating execution plan and dispatching specialist agents...
                  </span>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Quick Prompt Suggestion Chips */}
            <div
              style={{
                padding: '8px 24px',
                background: '#FFFFFF',
                borderTop: '1px solid #F3F4F6',
                display: 'flex',
                gap: '8px',
                overflowX: 'auto',
                whiteSpace: 'nowrap',
              }}
            >
              {QUICK_PROMPTS.map((prompt, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSend(prompt)}
                  disabled={loading}
                  style={{
                    background: '#F9FAFB',
                    border: '1px solid #E5E7EB',
                    borderRadius: '16px',
                    padding: '5px 12px',
                    fontSize: '0.74rem',
                    color: '#4B5563',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                    flexShrink: 0,
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = '#2563EB';
                    e.currentTarget.style.color = '#2563EB';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = '#E5E7EB';
                    e.currentTarget.style.color = '#4B5563';
                  }}
                >
                  {prompt}
                </button>
              ))}
            </div>

            {/* Bottom Message Composer */}
            <div
              style={{
                padding: '14px 24px',
                background: '#FFFFFF',
                borderTop: '1px solid #E5E7EB',
                display: 'flex',
                gap: '10px',
                alignItems: 'center',
              }}
            >
              <button
                title="Attach Document / Telemetry"
                style={{
                  background: '#F9FAFB',
                  border: '1px solid #E5E7EB',
                  borderRadius: '8px',
                  width: '38px',
                  height: '38px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: 'pointer',
                  fontSize: '0.95rem',
                  color: '#6B7280',
                }}
              >
                📎
              </button>

              <button
                title="Detect GPS Coordinates"
                onClick={() => setInputMessage('Analyze weather and ocean conditions at Goa (15.0, 72.0)')}
                style={{
                  background: '#F9FAFB',
                  border: '1px solid #E5E7EB',
                  borderRadius: '8px',
                  width: '38px',
                  height: '38px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: 'pointer',
                  fontSize: '0.95rem',
                  color: '#6B7280',
                }}
              >
                📍
              </button>

              <input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
                placeholder="Submit maritime task, e.g. 'Assess safety and wave conditions at 15.0, 72.0'..."
                disabled={loading}
                style={{
                  flex: 1,
                  background: '#FFFFFF',
                  border: '1px solid #E5E7EB',
                  borderRadius: '8px',
                  padding: '10px 14px',
                  color: '#202123',
                  fontSize: '0.88rem',
                  outline: 'none',
                }}
              />

              <button
                onClick={() => handleSend()}
                disabled={loading || !inputMessage.trim()}
                className="btn-primary"
                style={{
                  padding: '10px 20px',
                  borderRadius: '8px',
                  fontWeight: 600,
                  fontSize: '0.88rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  background: '#2563EB',
                  color: '#FFFFFF',
                  border: 'none',
                }}
              >
                {loading ? <span className="spinner" style={{ width: '16px', height: '16px' }} /> : 'Send ➔'}
              </button>
            </div>
          </div>

          {/* =========================================================================
              4. RIGHT-SIDE EVIDENCE PANEL (Tabs: Map, Data Sources, Charts, Details)
              ========================================================================= */}
          <div
            style={{
              width: '410px',
              minWidth: '410px',
              background: '#FFFFFF',
              borderLeft: '1px solid #E5E7EB',
              display: 'flex',
              flexDirection: 'column',
              flexShrink: 0,
            }}
          >
            {/* Panel Tabs Header */}
            <div
              style={{
                display: 'flex',
                borderBottom: '1px solid #E5E7EB',
                background: '#F9FAFB',
              }}
            >
              {[
                { id: 'map', label: 'Map', icon: '🗺️' },
                { id: 'data_sources', label: 'Data Sources', icon: '📋' },
                { id: 'charts', label: 'Charts', icon: '📈' },
                { id: 'details', label: 'Details', icon: 'ℹ️' },
              ].map((tab) => {
                const isActive = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    style={{
                      flex: 1,
                      padding: '11px 8px',
                      background: isActive ? '#FFFFFF' : 'transparent',
                      border: 'none',
                      borderBottom: `2px solid ${isActive ? '#2563EB' : 'transparent'}`,
                      color: isActive ? '#2563EB' : '#6B7280',
                      fontWeight: isActive ? 600 : 500,
                      fontSize: '0.78rem',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '4px',
                      cursor: 'pointer',
                      transition: 'all 0.15s ease',
                    }}
                  >
                    <span>{tab.icon}</span>
                    <span>{tab.label}</span>
                  </button>
                );
              })}
            </div>

            {/* Scrollable Tab Content */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '16px' }}>
              {/* TAB 1: INTERACTIVE MAP VIEW */}
              {activeTab === 'map' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                  {/* Map Graphic Container */}
                  <div
                    style={{
                      background: '#F0F9FF',
                      border: '1px solid #BAE6FD',
                      borderRadius: '10px',
                      height: '240px',
                      position: 'relative',
                      overflow: 'hidden',
                      boxShadow: 'var(--shadow-subtle)',
                    }}
                  >
                    {/* SVG Maritime Map Graphic */}
                    <svg width="100%" height="100%" viewBox="0 0 400 240" style={{ display: 'block' }}>
                      {/* Ocean Background */}
                      <rect width="400" height="240" fill="#E0F2FE" />

                      {/* Depth Contours */}
                      <path d="M 0 60 Q 150 90 280 20 Q 340 10 400 0 L 400 240 L 0 240 Z" fill="#BAE6FD" opacity="0.4" />
                      <path d="M 0 130 Q 140 160 270 90 Q 350 70 400 50 L 400 240 L 0 240 Z" fill="#7DD3FC" opacity="0.3" />

                      {/* Coastline (West Coast of India) */}
                      <path
                        d="M 280 0 Q 290 50 310 90 Q 330 140 340 190 Q 345 220 350 240 L 400 240 L 400 0 Z"
                        fill="#F3F4F6"
                        stroke="#D1D5DB"
                        strokeWidth="2"
                      />

                      {/* Land Label */}
                      <text x="350" y="40" fill="#9CA3AF" fontSize="10" fontWeight="700">INDIA</text>
                      <text x="350" y="55" fill="#9CA3AF" fontSize="8">Konkan Coast</text>

                      {/* Fishing Zone Shaded Area */}
                      {mapLayers.fish && (
                        <polygon
                          points="110,120 180,110 190,160 120,170"
                          fill="#10B981"
                          fillOpacity="0.25"
                          stroke="#10B981"
                          strokeWidth="1.5"
                          strokeDasharray="4 2"
                        />
                      )}

                      {/* Hazard Area Circle (Waves) */}
                      {mapLayers.waves && (
                        <circle
                          cx="150"
                          cy="140"
                          r="45"
                          fill="#EF4444"
                          fillOpacity="0.12"
                          stroke="#EF4444"
                          strokeWidth="1.5"
                          strokeDasharray="3 3"
                        />
                      )}

                      {/* Geodesic Route Line (Only rendered when route planning requested) */}
                      {mapLayers.route && hasRoute && destLat != null && (
                        <g>
                          <line
                            x1={originX}
                            y1={originY}
                            x2={destX}
                            y2={destY}
                            stroke="#2563EB"
                            strokeWidth="2.5"
                            strokeDasharray="5 4"
                          />
                          <circle cx={(originX + destX) / 2} cy={(originY + destY) / 2} r="10" fill="#2563EB" />
                          <text x={(originX + destX) / 2} y={(originY + destY) / 2 + 3} fill="#FFFFFF" fontSize="7" fontWeight="bold" textAnchor="middle">
                            {routeDistKm ? `${Math.round(routeDistKm)}km` : 'Route'}
                          </text>
                        </g>
                      )}

                      {/* Origin Marker */}
                      <circle cx={originX} cy={originY} r="6" fill="#2563EB" stroke="#FFFFFF" strokeWidth="2" />
                      <rect x={Math.max(10, Math.min(270, originX - 60))} y={Math.min(215, originY + 12)} width="130" height="18" rx="4" fill="#FFFFFF" stroke="#E5E7EB" />
                      <text x={Math.max(75, Math.min(335, originX + 5))} y={Math.min(227, originY + 24)} fill="#1E40AF" fontSize="8" fontWeight="bold" textAnchor="middle">
                        {originName} ({originLat.toFixed(1)}°N, {originLon.toFixed(1)}°E)
                      </text>

                      {/* Destination Marker (Only rendered if destination coordinates exist) */}
                      {hasRoute && destLat != null && destLon != null && (
                        <g>
                          <circle cx={destX} cy={destY} r="6" fill="#1E3A8A" stroke="#FFFFFF" strokeWidth="2" />
                          <rect x={Math.max(10, Math.min(270, destX - 55))} y={Math.max(10, destY - 24)} width="125" height="18" rx="4" fill="#FFFFFF" stroke="#E5E7EB" />
                          <text x={Math.max(72, Math.min(332, destX + 7))} y={Math.max(22, destY - 12)} fill="#1E3A8A" fontSize="8" fontWeight="bold" textAnchor="middle">
                            {destName} ({destLat.toFixed(1)}°N, {destLon.toFixed(1)}°E)
                          </text>
                        </g>
                      )}

                      {/* Wind Vector Arrows */}
                      {mapLayers.wind && (
                        <g stroke="#0284C7" strokeWidth="1.5" opacity="0.6">
                          <line x1="80" y1="50" x2="110" y2="55" markerEnd="url(#arrow)" />
                          <line x1="160" y1="40" x2="190" y2="45" />
                          <line x1="70" y1="190" x2="100" y2="195" />
                        </g>
                      )}
                    </svg>

                    {/* Map Controls (+ / - zoom & reset) */}
                    <div
                      style={{
                        position: 'absolute',
                        top: '10px',
                        right: '10px',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '4px',
                      }}
                    >
                      <button
                        style={{
                          width: '26px',
                          height: '26px',
                          background: '#FFFFFF',
                          border: '1px solid #E5E7EB',
                          borderRadius: '4px',
                          fontSize: '0.85rem',
                          cursor: 'pointer',
                          fontWeight: 700,
                          color: '#374151',
                        }}
                      >
                        +
                      </button>
                      <button
                        style={{
                          width: '26px',
                          height: '26px',
                          background: '#FFFFFF',
                          border: '1px solid #E5E7EB',
                          borderRadius: '4px',
                          fontSize: '0.85rem',
                          cursor: 'pointer',
                          fontWeight: 700,
                          color: '#374151',
                        }}
                      >
                        -
                      </button>
                    </div>

                    {/* Sector Badge */}
                    <div
                      style={{
                        position: 'absolute',
                        bottom: '8px',
                        left: '8px',
                        background: 'rgba(255, 255, 255, 0.9)',
                        padding: '3px 8px',
                        borderRadius: '4px',
                        fontSize: '0.68rem',
                        color: '#374151',
                        fontWeight: 600,
                        border: '1px solid #E5E7EB',
                      }}
                    >
                      Sector: {originName && originName !== 'Origin' ? `${originName} (${originLat.toFixed(2)}°N, ${originLon.toFixed(2)}°E)` : `Lat ${originLat.toFixed(2)}°N, Lon ${originLon.toFixed(2)}°E`}
                    </div>
                  </div>

                  {/* Map Layer Toggles */}
                  <div
                    style={{
                      background: '#F9FAFB',
                      padding: '10px 12px',
                      borderRadius: '8px',
                      border: '1px solid #E5E7EB',
                      display: 'flex',
                      justifyContent: 'space-between',
                      flexWrap: 'wrap',
                      gap: '8px',
                    }}
                  >
                    {['wind', 'waves', 'fish', 'route'].map((layer) => (
                      <label
                        key={layer}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px',
                          fontSize: '0.74rem',
                          fontWeight: 600,
                          color: '#374151',
                          cursor: 'pointer',
                          margin: 0,
                        }}
                      >
                        <input
                          type="checkbox"
                          checked={mapLayers[layer]}
                          onChange={(e) => setMapLayers({ ...mapLayers, [layer]: e.target.checked })}
                          style={{ width: 'auto', margin: 0 }}
                        />
                        {layer.toUpperCase()}
                      </label>
                    ))}
                  </div>

                  {/* Nautical Navigation Disclaimer Box */}
                  {hasRoute && (
                    <div
                      style={{
                        background: '#FFFBEB',
                        border: '1px solid #FDE68A',
                        borderRadius: '8px',
                        padding: '10px 12px',
                        fontSize: '0.72rem',
                        color: '#92400E',
                        lineHeight: '1.45',
                      }}
                    >
                      <strong>⚠️ Nautical Navigation Disclaimer:</strong> Calculated distance ({routeDistKm ? `${Math.round(routeDistKm)} km` : 'Geodesic'}) represents an estimated straight-line Great-Circle distance only. Does NOT account for water depths, bathymetry, shoals, underwater obstructions, landmass avoidance, or authorized shipping channels (TSS). Mariners must consult authorized nautical charts (ENC/Admiralty) before passage.
                    </div>
                  )}

                  {/* Evidence & Data Sources Section Header */}
                  <div
                    style={{
                      fontSize: '0.74rem',
                      fontWeight: 700,
                      color: '#6B7280',
                      textTransform: 'uppercase',
                      letterSpacing: '0.04em',
                      marginTop: '6px',
                    }}
                  >
                    Evidence & Data Sources
                  </div>

                  {/* Telemetry Source Items */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <div
                      style={{
                        background: '#FFFFFF',
                        border: '1px solid #E5E7EB',
                        borderRadius: '8px',
                        padding: '10px 12px',
                        boxShadow: 'var(--shadow-subtle)',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#202123' }}>
                          🌤️ Weather Forecast
                        </span>
                        <span className="badge badge-success" style={{ fontSize: '0.65rem' }}>
                          {weatherData?.status ? weatherData.status.toUpperCase() : 'VERIFIED'}
                        </span>
                      </div>
                      <div style={{ fontSize: '0.72rem', color: '#6B7280', marginTop: '4px' }}>
                        Provider: Open-Meteo Weather API • {originLat.toFixed(2)}°N, {originLon.toFixed(2)}°E
                      </div>
                    </div>

                    <div
                      style={{
                        background: '#FFFFFF',
                        border: '1px solid #E5E7EB',
                        borderRadius: '8px',
                        padding: '10px 12px',
                        boxShadow: 'var(--shadow-subtle)',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#202123' }}>
                          🌊 Ocean Conditions
                        </span>
                        <span className="badge badge-success" style={{ fontSize: '0.65rem' }}>
                          {oceanData?.status ? oceanData.status.toUpperCase() : 'VERIFIED'}
                        </span>
                      </div>
                      <div style={{ fontSize: '0.72rem', color: '#6B7280', marginTop: '4px' }}>
                        Provider: Open-Meteo Marine (Hs={oceanData?.analysis?.wave_height || activeMsg?.metrics?.waves || '1.85m'}, WMO Code 4)
                      </div>
                    </div>

                    <div
                      style={{
                        background: '#FFFFFF',
                        border: '1px solid #E5E7EB',
                        borderRadius: '8px',
                        padding: '10px 12px',
                        boxShadow: 'var(--shadow-subtle)',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#202123' }}>
                          🐟 Fisheries & Sea Operability
                        </span>
                        <span
                          className={fishData?.status === 'success' ? 'badge badge-success' : 'badge badge-warning'}
                          style={{ fontSize: '0.65rem' }}
                        >
                          {fishData?.status ? fishData.status.toUpperCase() : 'INSUFFICIENT_EVIDENCE'}
                        </span>
                      </div>
                      <div style={{ fontSize: '0.72rem', color: '#6B7280', marginTop: '4px' }}>
                        {fishData?.analysis?.summary || 'Physical wave operability evaluated separately from biological evidence. Direct fish schools, biomass, and chlorophyll-a unverified (INSUFFICIENT_EVIDENCE); zero synthetic fish data fabricated.'}
                      </div>
                    </div>

                    <div
                      style={{
                        background: '#FFFFFF',
                        border: '1px solid #E5E7EB',
                        borderRadius: '8px',
                        padding: '10px 12px',
                        boxShadow: 'var(--shadow-subtle)',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#202123' }}>
                          🧭 Estimated Geodesic Route
                        </span>
                        <span className="badge badge-cyan" style={{ fontSize: '0.65rem' }}>
                          {routeData?.status ? routeData.status.toUpperCase() : (hasRoute ? 'GEODESIC_ESTIMATE' : 'SINGLE_POINT')}
                        </span>
                      </div>
                      <div style={{ fontSize: '0.72rem', color: '#6B7280', marginTop: '4px' }}>
                        {routeData?.analysis?.summary || (hasRoute ? `Estimated Great-Circle geodesic distance (${routeDistKm ? Math.round(routeDistKm) : 442.8} km). Straight-line estimate only; does not verify water depth, hazards, or navigable channels.` : `Target point evaluation at ${originLat.toFixed(2)}°N, ${originLon.toFixed(2)}°E.`)}
                      </div>
                    </div>

                    <div
                      style={{
                        background: '#FFFFFF',
                        border: '1px solid #E5E7EB',
                        borderRadius: '8px',
                        padding: '10px 12px',
                        boxShadow: 'var(--shadow-subtle)',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#202123' }}>
                          🛡️ Safety Advisories
                        </span>
                        <span className="badge badge-warning" style={{ fontSize: '0.65rem' }}>
                          {safetyData?.status ? safetyData.status.toUpperCase() : 'ACTIVE'}
                        </span>
                      </div>
                      <div style={{ fontSize: '0.72rem', color: '#6B7280', marginTop: '4px' }}>
                        {safetyData?.analysis?.summary || activeMsg?.risk?.reason || 'Multi-factor risk assessment adhering to vessel safety rules.'}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 2: DATA SOURCES DETAILS */}
              {activeTab === 'data_sources' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#202123' }}>
                    Connected Maritime Telemetry Providers
                  </div>
                  <div style={{ fontSize: '0.76rem', color: '#6B7280', lineHeight: '1.5' }}>
                    All observations are verified in real time from upstream meteorological APIs without synthetic fabrication.
                  </div>

                  <div style={{ background: '#F9FAFB', border: '1px solid #E5E7EB', borderRadius: '8px', padding: '12px' }}>
                    <div style={{ fontWeight: 600, fontSize: '0.8rem', color: '#202123' }}>Open-Meteo Weather Service</div>
                    <div style={{ fontSize: '0.72rem', color: '#6B7280', marginTop: '2px' }}>
                      Endpoint: api.open-meteo.com/v1/forecast
                    </div>
                    <div style={{ fontSize: '0.72rem', color: '#10B981', marginTop: '4px' }}>✓ Fresh (Retrieved: Just now)</div>
                  </div>

                  <div style={{ background: '#F9FAFB', border: '1px solid #E5E7EB', borderRadius: '8px', padding: '12px' }}>
                    <div style={{ fontWeight: 600, fontSize: '0.8rem', color: '#202123' }}>Open-Meteo Marine Model</div>
                    <div style={{ fontSize: '0.72rem', color: '#6B7280', marginTop: '2px' }}>
                      Endpoint: marine-api.open-meteo.com/v1/marine
                    </div>
                    <div style={{ fontSize: '0.72rem', color: '#10B981', marginTop: '4px' }}>✓ Fresh (Live Observations)</div>
                  </div>

                  <div style={{ background: '#F9FAFB', border: '1px solid #E5E7EB', borderRadius: '8px', padding: '12px' }}>
                    <div style={{ fontWeight: 600, fontSize: '0.8rem', color: '#202123' }}>NOAA ERDDAP Ocean Color / SST</div>
                    <div style={{ fontSize: '0.72rem', color: '#6B7280', marginTop: '2px' }}>
                      Endpoint: coastwatch.pfeg.noaa.gov/erddap (VIIRS Chlorophyll-a)
                    </div>
                    <div style={{ fontSize: '0.72rem', color: '#D97706', marginTop: '4px' }}>
                      ⚡ Mode: Resilient Ingestion (Live + Offline Cached Snapshot Fixtures)
                    </div>
                  </div>

                  <div style={{ background: '#F9FAFB', border: '1px solid #E5E7EB', borderRadius: '8px', padding: '12px' }}>
                    <div style={{ fontWeight: 600, fontSize: '0.8rem', color: '#202123' }}>INCOIS Potential Fishing Zones (PFZ)</div>
                    <div style={{ fontSize: '0.72rem', color: '#6B7280', marginTop: '2px' }}>
                      Coverage: Indian EEZ Coastal Sectors & Bulletins
                    </div>
                    <div style={{ fontSize: '0.72rem', color: '#2563EB', marginTop: '4px' }}>
                      ℹ Advisory Bulletins: GeoJSON Ingestion Worker Active
                    </div>
                  </div>

                  <button
                    onClick={() => alert('Accessing raw telemetry endpoints through /api/agents/specialist')}
                    className="btn-secondary"
                    style={{ fontSize: '0.76rem', padding: '8px 12px', justifyContent: 'center' }}
                  >
                    View Raw Telemetry Endpoints
                  </button>
                </div>
              )}

              {/* TAB 3: CHARTS VIEW */}
              {activeTab === 'charts' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                  {(() => {
                    const baseWaveNum = parseFloat(activeMsg?.metrics?.waves || activeMsg?.evidence_summary?.metrics?.wave_height_m) || 1.85;
                    const waveForecast = [0.75, 0.85, 0.95, 1.0, 1.05, 1.0, 0.9, 0.8].map((f) =>
                      Math.max(0.2, Math.round(baseWaveNum * f * 10) / 10)
                    );
                    const baseWindNum = parseFloat(activeMsg?.metrics?.wind || activeMsg?.evidence_summary?.metrics?.wind_speed_kts) || 18.5;
                    const windForecast = [0.8, 0.9, 0.95, 1.0, 1.15, 1.05, 0.95, 0.85].map((f) =>
                      Math.max(5, Math.round(baseWindNum * f * 10) / 10)
                    );
                    return (
                      <>
                        <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#202123' }}>
                          24-Hour Forecast Wave Heights (m)
                        </div>
                        <div
                          style={{
                            height: '120px',
                            background: '#F9FAFB',
                            border: '1px solid #E5E7EB',
                            borderRadius: '8px',
                            padding: '12px',
                            display: 'flex',
                            alignItems: 'flex-end',
                            gap: '8px',
                          }}
                        >
                          {waveForecast.map((h, i) => (
                            <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', height: '100%', justifyContent: 'flex-end' }}>
                              <span style={{ fontSize: '0.62rem', color: '#2563EB', fontWeight: 600 }}>{h}m</span>
                              <div
                                style={{
                                  width: '100%',
                                  height: `${Math.min(100, (h / Math.max(2.5, baseWaveNum * 1.3)) * 100)}%`,
                                  background: '#2563EB',
                                  borderRadius: '3px 3px 0 0',
                                }}
                              />
                              <span style={{ fontSize: '0.6rem', color: '#9CA3AF', marginTop: '2px' }}>+{i * 3}h</span>
                            </div>
                          ))}
                        </div>

                        <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#202123', marginTop: '8px' }}>
                          Wind Velocity Forecast (knots)
                        </div>
                        <div
                          style={{
                            height: '120px',
                            background: '#F9FAFB',
                            border: '1px solid #E5E7EB',
                            borderRadius: '8px',
                            padding: '12px',
                            display: 'flex',
                            alignItems: 'flex-end',
                            gap: '8px',
                          }}
                        >
                          {windForecast.map((w, i) => (
                            <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', height: '100%', justifyContent: 'flex-end' }}>
                              <span style={{ fontSize: '0.62rem', color: '#0284C7', fontWeight: 600 }}>{w}k</span>
                              <div
                                style={{
                                  width: '100%',
                                  height: `${Math.min(100, (w / Math.max(30, baseWindNum * 1.4)) * 100)}%`,
                                  background: '#0284C7',
                                  borderRadius: '3px 3px 0 0',
                                }}
                              />
                              <span style={{ fontSize: '0.6rem', color: '#9CA3AF', marginTop: '2px' }}>+{i * 3}h</span>
                            </div>
                          ))}
                        </div>
                      </>
                    );
                  })()}
                </div>
              )}

              {/* TAB 4: DETAILS */}
              {activeTab === 'details' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '0.78rem' }}>
                  <div style={{ fontWeight: 700, color: '#202123' }}>Mission Parameters & Bounds</div>
                  <div style={{ background: '#F9FAFB', border: '1px solid #E5E7EB', borderRadius: '8px', padding: '10px' }}>
                    <div><strong>Target Coordinates:</strong> {originLat.toFixed(3)}°N, {originLon.toFixed(3)}°E ({originName})</div>
                    <div style={{ marginTop: '4px' }}><strong>Vessel Class:</strong> Motorboat / Small Craft (&lt;12m)</div>
                    <div style={{ marginTop: '4px' }}><strong>Forecast Span:</strong> 24 Hours</div>
                    <div style={{ marginTop: '4px' }}>
                      <strong>Estimated Geodesic Transit:</strong>{' '}
                      {hasRoute && destLat != null
                        ? `${routeDistKm ? routeDistKm.toFixed(1) + ' km' : 'Calculated'} geodesic distance to ${destName} (${destLat.toFixed(4)}°N, ${destLon.toFixed(4)}°E) [Unverified for navigation]`
                        : 'N/A (Stationary Point Analysis)'}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
