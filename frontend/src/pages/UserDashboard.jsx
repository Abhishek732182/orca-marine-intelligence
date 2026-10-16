import React, { useState, useEffect, useRef, useCallback } from 'react';
import ChatSidebar from '../components/ChatSidebar';
import ChatMessage from '../components/ChatMessage';
import AgentSelectorPopover, { AGENT_OPTIONS } from '../components/AgentSelectorPopover';
import OrcaLogo from '../components/OrcaLogo';
import { useAuth } from '../context/AuthContext';
import {
  chatAssistant,
  approveTool,
  checkHealth,
  listUserConversations,
  saveUserConversation,
  deleteServerConversation,
  renameServerConversation,
} from '../services/orcaApi';

// The 5 Suggestion Cards matching the design reference image
const SUGGESTED_PROMPTS = [
  {
    title: 'Check marine weather and forecast',
    prompt: 'Check marine weather, surface wind velocity, and Beaufort scale at 15.0°N, 72.0°E (Offshore Goa)',
    agent: 'weather',
    icon: (
      <svg className="w-6 h-6 text-cyan-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 00-9.78 2.096A4.001 4.001 0 003 15z" />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M12 3v2m0 14v2M3.5 10.5h2m13 0h2" />
      </svg>
    ),
  },
  {
    title: 'Find available PFZ advisories',
    prompt: 'Find available PFZ advisories, chlorophyll-a thermal fronts, and trawler operability for Mackerel at 15.0°N, 72.0°E',
    agent: 'fishing_zone',
    icon: (
      <svg className="w-6 h-6 text-cyan-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M2 12c3-4 6-4 9 0s6 4 9 0 6-4 9 0" />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M2 16c3-4 6-4 9 0s6 4 9 0 6-4 9 0" />
      </svg>
    ),
  },
  {
    title: 'Analyze ocean conditions',
    prompt: 'Analyze wave heights, swell period, and WMO 3700 sea-state code for coordinates 15.0, 72.0',
    agent: 'ocean',
    icon: (
      <svg className="w-6 h-6 text-cyan-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M3 15c2.5-3 5-3 7.5 0s5 3 7.5 0 5-3 7.5 0" />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M3 9c2.5-3 5-3 7.5 0s5 3 7.5 0 5-3 7.5 0" />
      </svg>
    ),
  },
  {
    title: 'Plan a marine route',
    prompt: 'Help plan a marine route from Mumbai Port (18.9°N, 72.8°E) to Goa (15.0°N, 72.0°E)',
    agent: 'route',
    icon: (
      <svg className="w-6 h-6 text-cyan-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <circle cx="6" cy="18" r="3" strokeWidth={1.8} />
        <circle cx="18" cy="6" r="3" strokeWidth={1.8} />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M8.5 16.5C11 14 13 14 15.5 8.5" />
      </svg>
    ),
  },
  {
    title: 'Check marine safety risks',
    prompt: 'Check potential marine safety risks for a small craft vessel in 3.5m waves and 28 kts wind',
    agent: 'safety_risk',
    icon: (
      <svg className="w-6 h-6 text-cyan-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
      </svg>
    ),
  },
];

export default function UserDashboard() {
  const { user } = useAuth();

  // Storage key scoped strictly to the authenticated user identity
  const userStorageKey = `orca_convs_${user?.id || user?.email || 'default'}`;

  // Layout & Sidebar State
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);

  // User-Specific Persistent Conversation History State
  const [conversations, setConversations] = useState(() => {
    try {
      const stored = localStorage.getItem(userStorageKey);
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  });

  const [activeConversationId, setActiveConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  // Specialist Agent Selection State
  const [selectedAgent, setSelectedAgent] = useState('auto');
  const [isAgentPopoverOpen, setIsAgentPopoverOpen] = useState(false);

  // Theme State (for the Sun/Moon toggle in the top right)
  const [isDarkMode, setIsDarkMode] = useState(false);

  // System Health Status State
  const [systemHealth, setSystemHealth] = useState({ checked: false, isOnline: false });

  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  // Synchronize conversations when authenticated user changes
  useEffect(() => {
    try {
      const stored = localStorage.getItem(userStorageKey);
      const userConvs = stored ? JSON.parse(stored) : [];
      setConversations(userConvs);
      setActiveConversationId(null);
      setMessages([]);
    } catch (err) {
      console.warn('Failed to load user-scoped conversation history:', err);
    }
  }, [userStorageKey]);

  // Check backend server health
  useEffect(() => {
    let isMounted = true;
    checkHealth()
      .then(() => {
        if (isMounted) setSystemHealth({ checked: true, isOnline: true });
      })
      .catch(() => {
        if (isMounted) setSystemHealth({ checked: true, isOnline: false });
      });
    return () => {
      isMounted = false;
    };
  }, []);

  // Fetch conversations from backend if available
  useEffect(() => {
    let isMounted = true;
    listUserConversations()
      .then((serverConvs) => {
        if (isMounted && Array.isArray(serverConvs) && serverConvs.length > 0) {
          setConversations(serverConvs);
          localStorage.setItem(userStorageKey, JSON.stringify(serverConvs));
        }
      })
      .catch(() => {
        // Fallback to user-scoped localStorage
      });
    return () => {
      isMounted = false;
    };
  }, [userStorageKey]);

  // Persist conversations locally whenever they change
  const persistConversations = useCallback(
    (newConversations) => {
      setConversations(newConversations);
      try {
        localStorage.setItem(userStorageKey, JSON.stringify(newConversations));
      } catch (err) {
        console.warn('LocalStorage save failed:', err);
      }
    },
    [userStorageKey]
  );

  // Scroll to latest message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  // Switch Active Conversation
  const handleSelectConversation = (convId) => {
    const target = conversations.find((c) => c.id === convId);
    if (target) {
      setActiveConversationId(target.id);
      setMessages(target.messages || []);
      if (target.selectedAgent) {
        setSelectedAgent(target.selectedAgent);
      }
      setErrorMsg(null);
    }
  };

  // Start New Chat
  const handleNewChat = () => {
    setActiveConversationId(null);
    setMessages([]);
    setInputMessage('');
    setErrorMsg(null);
    setSelectedAgent('auto');
  };

  // Delete Conversation
  const handleDeleteConversation = async (convId) => {
    const updated = conversations.filter((c) => c.id !== convId);
    persistConversations(updated);

    if (activeConversationId === convId) {
      handleNewChat();
    }

    try {
      await deleteServerConversation(convId);
    } catch {
      // Offline fallback succeeded locally
    }
  };

  // Rename Conversation
  const handleRenameConversation = async (convId, newTitle) => {
    const updated = conversations.map((c) => (c.id === convId ? { ...c, title: newTitle } : c));
    persistConversations(updated);

    try {
      await renameServerConversation(convId, newTitle);
    } catch {
      // Offline fallback succeeded locally
    }
  };

  // Send Message
  const handleSend = async (customPrompt, overrideAgent) => {
    const text = (customPrompt !== undefined ? customPrompt : inputMessage).trim();
    if (!text || loading) return;

    const agentToUse = overrideAgent || selectedAgent;
    if (overrideAgent) {
      setSelectedAgent(overrideAgent);
    }

    setInputMessage('');
    setErrorMsg(null);

    const userMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    };

    const newMessages = [...messages, userMessage];
    setMessages(newMessages);

    let currentConvId = activeConversationId;
    let isBrandNewConv = false;

    if (!currentConvId) {
      currentConvId = `conv-${Date.now()}`;
      setActiveConversationId(currentConvId);
      isBrandNewConv = true;
    }

    setLoading(true);

    try {
      const response = await chatAssistant({
        message: text,
        agent: agentToUse !== 'auto' ? agentToUse : undefined,
        conversation_id: currentConvId,
      });

      const assistantMsg = {
        id: `asst-${Date.now()}`,
        role: 'assistant',
        content:
          response.response_message?.content ||
          response.summary ||
          response.message ||
          'Analysis completed. Please review the verified telemetry data below.',
        timestamp: new Date().toISOString(),
        selectedAgent: agentToUse,
        evidence: response.evidence_summary || response.agent_results || null,
        plan: response.plan || [],
        toolCalls: response.tool_calls || [],
        pendingApproval: response.pending_approval || null,
      };

      const finalMessages = [...newMessages, assistantMsg];
      setMessages(finalMessages);

      const convTitle = isBrandNewConv
        ? text.length > 36
          ? `${text.substring(0, 36)}...`
          : text
        : conversations.find((c) => c.id === currentConvId)?.title || text;

      const updatedConv = {
        id: currentConvId,
        title: convTitle,
        messages: finalMessages,
        selectedAgent: agentToUse,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };

      const updatedConversations = isBrandNewConv
        ? [updatedConv, ...conversations]
        : conversations.map((c) => (c.id === currentConvId ? updatedConv : c));

      persistConversations(updatedConversations);

      saveUserConversation(updatedConv).catch(() => {
        // Offline server persistence fallback
      });
    } catch (err) {
      console.error('Chat error:', err);
      const errorText = err.message || 'Service unreachable. Verify backend server is active on port 8001.';
      setErrorMsg(errorText);

      const errorAssistantMsg = {
        id: `err-${Date.now()}`,
        role: 'assistant',
        content: `**Request Error:** ${errorText}\n\nPlease check network connectivity or verify if the backend is running.`,
        timestamp: new Date().toISOString(),
        isError: true,
      };

      const finalMessages = [...newMessages, errorAssistantMsg];
      setMessages(finalMessages);
    } finally {
      setLoading(false);
    }
  };

  // Tool Approval Handler
  const handleApproveTool = async (callId, decision) => {
    try {
      await approveTool({
        call_id: callId,
        decision,
      });
      handleSend(`Authorized tool execution: ${callId}`);
    } catch (err) {
      setErrorMsg(`Authorization failed: ${err.message}`);
    }
  };

  const currentAgentInfo = AGENT_OPTIONS.find((a) => a.id === selectedAgent) || AGENT_OPTIONS[0];

  // Reusable Message Composer Bar
  const renderComposer = () => (
    <div className="relative rounded-full bg-white shadow-xl shadow-slate-200/70 border border-slate-200/90 px-3 sm:px-4 py-2 flex items-center gap-2.5 focus-within:border-cyan-500 focus-within:ring-2 focus-within:ring-cyan-100 transition-all">
      {/* Left Plus (+) Button */}
      <div className="relative shrink-0">
        <button
          type="button"
          onClick={() => setIsAgentPopoverOpen(!isAgentPopoverOpen)}
          className="w-8 h-8 rounded-full flex items-center justify-center text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
          title="Select specialist agent"
          aria-label="Select specialist agent"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
        </button>

        {/* Popover Menu */}
        <AgentSelectorPopover
          selectedAgent={selectedAgent}
          onSelectAgent={(id) => setSelectedAgent(id)}
          isOpen={isAgentPopoverOpen}
          onClose={() => setIsAgentPopoverOpen(false)}
        />
      </div>

      {/* Input Field with Placeholder */}
      <input
        ref={textareaRef}
        type="text"
        value={inputMessage}
        onChange={(e) => setInputMessage(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') {
            e.preventDefault();
            handleSend();
          }
        }}
        placeholder="Ask ORCA anything about the ocean..."
        className="flex-1 bg-transparent text-[14.5px] sm:text-[15px] text-slate-800 placeholder-slate-400 border-none outline-hidden focus:ring-0 px-1 py-1"
        disabled={loading}
      />

      {/* Embedded Specialist Agent Selector Pill */}
      <button
        type="button"
        onClick={() => setIsAgentPopoverOpen(!isAgentPopoverOpen)}
        className="shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold text-slate-600 hover:text-slate-900 bg-slate-50 hover:bg-slate-100 border border-slate-200/80 transition-colors"
        title="Change active specialist agent"
      >
        <span className="text-amber-500">⭐</span>
        <span className="hidden sm:inline">{currentAgentInfo.name}</span>
        <span className="sm:hidden">{currentAgentInfo.shortName}</span>
        <svg className="w-3.5 h-3.5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Send Button: Solid Vibrant Blue Pill Circle with Paper Airplane */}
      <button
        type="button"
        onClick={() => handleSend()}
        disabled={!inputMessage.trim() || loading}
        className={`w-9 h-9 rounded-full flex items-center justify-center shrink-0 transition-all ${
          inputMessage.trim() && !loading
            ? 'bg-[#1a73e8] hover:bg-blue-600 text-white shadow-md active:scale-95'
            : 'bg-[#1a73e8]/70 text-white/80 cursor-not-allowed'
        }`}
        title="Send message"
        aria-label="Send message"
      >
        <svg className="w-4 h-4 translate-x-0.5 -translate-y-0.5" viewBox="0 0 24 24" fill="currentColor">
          <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
        </svg>
      </button>
    </div>
  );

  return (
    <div className={`flex h-screen w-screen overflow-hidden font-sans antialiased ${isDarkMode ? 'bg-[#0a192f] text-white' : 'bg-white text-slate-900'}`}>
      {/* Left Collapsible Navigation Sidebar (290px) */}
      <ChatSidebar
        conversations={conversations}
        activeConversationId={activeConversationId}
        onSelectConversation={handleSelectConversation}
        onNewChat={handleNewChat}
        onDeleteConversation={handleDeleteConversation}
        onRenameConversation={handleRenameConversation}
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
        isMobileOpen={isMobileSidebarOpen}
        onCloseMobile={() => setIsMobileSidebarOpen(false)}
      />

      {/* Main Conversation Canvas: Full Available Screen Space */}
      <main className="flex-1 flex flex-col h-full min-w-0 relative overflow-hidden bg-gradient-to-b from-white via-[#f7fbfe] to-[#e8f4fc]">
        {/* Soft Background Ocean Waves Vector Illustration */}
        <div className="absolute inset-0 pointer-events-none overflow-hidden opacity-35 z-0" aria-hidden="true">
          <svg className="absolute -bottom-10 -right-20 w-[800px] h-[400px]" viewBox="0 0 800 400" fill="none">
            <path
              d="M0 280 C200 240 400 360 800 260 L800 400 L0 400 Z"
              fill="#bae6fd"
              opacity="0.35"
            />
            <path
              d="M0 310 C300 280 500 370 800 300 L800 400 L0 400 Z"
              fill="#7dd3fc"
              opacity="0.25"
            />
          </svg>
        </div>

        {/* Top Minimal Navigation Bar */}
        <header className="h-16 px-4 sm:px-6 flex items-center justify-between shrink-0 z-10">
          <div className="flex items-center gap-3 min-w-0">
            {/* Mobile Hamburger Button */}
            <button
              type="button"
              onClick={() => setIsMobileSidebarOpen(true)}
              className="lg:hidden p-2 rounded-xl text-slate-600 hover:bg-slate-100 transition-colors"
              aria-label="Open sidebar"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
          </div>

          {/* Top Right Controls: Theme Toggle Sun/Moon Pill & Status */}
          <div className="flex items-center gap-3">
            {/* Theme Toggle Pill matching Reference Image */}
            <div className="flex items-center bg-white/90 backdrop-blur-xs border border-slate-200/90 rounded-full p-1 shadow-xs">
              <button
                type="button"
                onClick={() => setIsDarkMode(false)}
                className={`p-1.5 rounded-full transition-all ${!isDarkMode ? 'bg-sky-100 text-sky-700 shadow-2xs' : 'text-slate-400 hover:text-slate-600'}`}
                title="Light mode"
                aria-label="Light mode"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                </svg>
              </button>
              <button
                type="button"
                onClick={() => setIsDarkMode(true)}
                className={`p-1.5 rounded-full transition-all ${isDarkMode ? 'bg-slate-800 text-sky-400 shadow-2xs' : 'text-slate-400 hover:text-slate-600'}`}
                title="Dark mode"
                aria-label="Dark mode"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                </svg>
              </button>
            </div>

            {/* Backend Health Status Dot */}
            {systemHealth.checked && (
              <span
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium backdrop-blur-xs transition-colors ${
                  systemHealth.isOnline
                    ? 'bg-emerald-50/90 text-emerald-800 border border-emerald-200'
                    : 'bg-slate-100/90 text-slate-600 border border-slate-200'
                }`}
                title={systemHealth.isOnline ? 'FastAPI Agent Backend Online' : 'Backend offline or standalone'}
              >
                <span
                  className={`w-2 h-2 rounded-full ${
                    systemHealth.isOnline ? 'bg-emerald-500 animate-pulse' : 'bg-slate-400'
                  }`}
                />
                <span className="hidden sm:inline">
                  {systemHealth.isOnline ? 'Online' : 'Standalone'}
                </span>
              </span>
            )}
          </div>
        </header>

        {/* Scrollable Main Conversation Area */}
        <div className="flex-1 overflow-y-auto overflow-x-hidden flex flex-col z-10">
          {messages.length === 0 ? (
            /* Centered New-Chat Composition in the middle of the screen */
            <div className="flex-1 flex flex-col justify-center items-center px-4 sm:px-6 py-6 max-w-4xl mx-auto w-full my-auto">
              {/* Large Centered Circular Emblem & Spaced Typography */}
              <OrcaLogo variant="hero" />

              {/* Main Headline */}
              <h1 className="text-2xl sm:text-3xl font-bold text-[#091b33] tracking-tight text-center mt-5 mb-2 font-sans">
                What would you like to know about the ocean?
              </h1>

              {/* Refined Subheading */}
              <p className="text-sm sm:text-base text-slate-500 text-center max-w-xl mx-auto mb-7 sm:mb-8 leading-relaxed">
                Ask about marine weather, ocean conditions, fishing-zone advisories, routes, and marine safety.
              </p>

              {/* Five Suggestion Cards in a Row on Desktop */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5 w-full mb-6 sm:mb-7">
                {SUGGESTED_PROMPTS.map((item, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => handleSend(item.prompt, item.agent)}
                    className="p-4 rounded-2xl border border-slate-200/90 bg-white/95 backdrop-blur-xs hover:border-cyan-400 hover:shadow-md hover:-translate-y-0.5 active:scale-[0.98] transition-all text-center shadow-xs group flex flex-col items-center justify-center min-h-[110px]"
                  >
                    <div className="mb-2.5 p-2 rounded-xl bg-sky-50/80 group-hover:bg-cyan-50 transition-colors">
                      {item.icon}
                    </div>
                    <div className="text-xs font-semibold text-slate-800 leading-snug group-hover:text-cyan-900 transition-colors">
                      {item.title}
                    </div>
                  </button>
                ))}
              </div>

              {/* Error Banner if any */}
              {errorMsg && (
                <div className="w-full mb-3 p-3 rounded-2xl bg-rose-50 border border-rose-200 text-xs sm:text-sm text-rose-800 flex items-center justify-between shadow-xs">
                  <span>{errorMsg}</span>
                  <button
                    type="button"
                    onClick={() => setErrorMsg(null)}
                    className="text-rose-500 hover:text-rose-800 font-bold ml-2"
                  >
                    ✕
                  </button>
                </div>
              )}

              {/* Prominent Composer in the Middle of Screen directly below cards */}
              <div className="w-full">
                {renderComposer()}
              </div>
            </div>
          ) : (
            /* Active Chronological Conversation Stream */
            <div className="max-w-4xl mx-auto px-4 sm:px-6 w-full py-6 flex-1">
              {messages.map((msg) => (
                <ChatMessage
                  key={msg.id}
                  message={msg}
                  onApproveTool={handleApproveTool}
                />
              ))}

              {/* Loading State */}
              {loading && (
                <div className="flex items-start gap-4 my-6 px-2 sm:px-4">
                  <div className="w-9 h-9 rounded-full bg-[#0a1e38] p-1 flex items-center justify-center shrink-0 shadow-md mt-0.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-ping" />
                  </div>
                  <div className="text-[15px] text-slate-600 font-medium flex items-center gap-2 mt-1.5">
                    <span>ORCA Agent reasoning in progress</span>
                    <span className="flex gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce" />
                      <span className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce [animation-delay:0.2s]" />
                      <span className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce [animation-delay:0.4s]" />
                    </span>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Docked Message Composer at Bottom (Active Chat) */}
        {messages.length > 0 && (
          <div className="w-full shrink-0 z-20 pb-6 pt-2 px-4 sm:px-6">
            <div className="max-w-4xl mx-auto">
              {errorMsg && (
                <div className="mb-3 p-3 rounded-2xl bg-rose-50 border border-rose-200 text-xs sm:text-sm text-rose-800 flex items-center justify-between shadow-xs">
                  <span>{errorMsg}</span>
                  <button
                    type="button"
                    onClick={() => setErrorMsg(null)}
                    className="text-rose-500 hover:text-rose-800 font-bold ml-2"
                  >
                    ✕
                  </button>
                </div>
              )}
              {renderComposer()}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
