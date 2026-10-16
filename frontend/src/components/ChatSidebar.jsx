import React, { useState, useMemo } from 'react';
import { useAuth } from '../context/AuthContext';
import OrcaLogo from './OrcaLogo';

export default function ChatSidebar({
  conversations = [],
  activeConversationId,
  onSelectConversation,
  onNewChat,
  onDeleteConversation,
  onRenameConversation,
  isCollapsed,
  onToggleCollapse,
  isMobileOpen,
  onCloseMobile,
}) {
  const { user, logout } = useAuth();
  const [searchQuery, setSearchQuery] = useState('');
  const [editingId, setEditingId] = useState(null);
  const [editTitle, setEditTitle] = useState('');
  const [activeMenuId, setActiveMenuId] = useState(null);

  // Filter conversations by search query
  const filteredConversations = useMemo(() => {
    if (!searchQuery.trim()) return conversations;
    const q = searchQuery.toLowerCase();
    return conversations.filter((c) => (c.title || '').toLowerCase().includes(q));
  }, [conversations, searchQuery]);

  // Format relative timestamp like the reference image: "Today, 10:24 AM", "Yesterday, 4:32 PM", "2 days ago"
  const formatTimestamp = (dateString) => {
    if (!dateString) return 'Recent';
    try {
      const date = new Date(dateString);
      const now = new Date();
      const diffMs = now - date;
      const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

      const timeStr = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

      if (diffDays === 0 && date.getDate() === now.getDate()) {
        return `Today, ${timeStr}`;
      }
      if (diffDays <= 1) {
        return `Yesterday, ${timeStr}`;
      }
      if (diffDays < 7) {
        return `${diffDays} days ago`;
      }
      return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
    } catch {
      return 'Recent';
    }
  };

  const handleStartRename = (e, conv) => {
    e.stopPropagation();
    setActiveMenuId(null);
    setEditingId(conv.id);
    setEditTitle(conv.title);
  };

  const handleSaveRename = (e, id) => {
    e.stopPropagation();
    if (editTitle.trim() && onRenameConversation) {
      onRenameConversation(id, editTitle.trim());
    }
    setEditingId(null);
  };

  const handleCancelRename = (e) => {
    e.stopPropagation();
    setEditingId(null);
  };

  // User initials for bottom avatar
  const userInitials = useMemo(() => {
    if (!user) return 'OR';
    const name = user.name || user.email || 'Researcher';
    const parts = name.trim().split(/\s+/);
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return name.slice(0, 2).toUpperCase();
  }, [user]);

  const userName = user?.name || user?.email?.split('@')[0] || 'Shyam';

  return (
    <>
      {/* Mobile Backdrop Overlay */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 bg-slate-950/70 backdrop-blur-xs z-40 lg:hidden"
          onClick={onCloseMobile}
          aria-hidden="true"
        />
      )}

      {/* Sidebar Container: Deep Midnight Navy matching reference image */}
      <aside
        className={`fixed inset-y-0 left-0 z-40 lg:static bg-gradient-to-b from-[#06152b] via-[#091b35] to-[#07162c] text-slate-200 border-r border-[#142845] flex flex-col h-full transition-all duration-200 ease-in-out shrink-0 select-none shadow-2xl lg:shadow-none ${
          isMobileOpen ? 'translate-x-0 w-[290px]' : '-translate-x-full lg:translate-x-0'
        } ${isCollapsed ? 'lg:w-[72px]' : 'lg:w-[290px]'}`}
        aria-label="ORCA Navigation Sidebar"
      >
        {/* Brand Header */}
        <div className="h-16 px-4 border-b border-[#142a4a] flex items-center justify-between shrink-0">
          {!isCollapsed ? (
            <div className="flex items-center justify-between w-full">
              <OrcaLogo variant="sidebar" />
              {/* Collapse Button << */}
              <button
                type="button"
                onClick={onToggleCollapse}
                className="hidden lg:flex p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-[#132c4f] transition-colors"
                title="Collapse sidebar"
                aria-label="Collapse sidebar"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
                </svg>
              </button>
            </div>
          ) : (
            <div className="mx-auto flex flex-col items-center">
              <OrcaLogo variant="icon" className="w-8 h-8" />
              <button
                type="button"
                onClick={onToggleCollapse}
                className="mt-2 p-1 text-slate-400 hover:text-white hover:bg-[#132c4f] rounded"
                title="Expand sidebar"
              >
                <svg className="w-3.5 h-3.5 rotate-180" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
                </svg>
              </button>
            </div>
          )}

          {/* Mobile Close Button */}
          <button
            type="button"
            onClick={onCloseMobile}
            className="lg:hidden p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-[#132c4f]"
            aria-label="Close sidebar"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Action Bar: New Chat & Search */}
        <div className="p-3 space-y-2 shrink-0">
          {/* "+ New Chat" Button (Pill Blue) */}
          <button
            type="button"
            onClick={() => {
              onNewChat();
              if (onCloseMobile) onCloseMobile();
            }}
            className={`w-full py-2.5 px-4 rounded-xl font-medium text-sm text-white bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 active:scale-[0.99] transition-all shadow-md shadow-blue-900/30 flex items-center justify-center gap-2 group ${
              isCollapsed ? 'px-2' : ''
            }`}
            title="Start new marine conversation"
          >
            <svg className="w-4 h-4 stroke-[2.5]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
            </svg>
            {!isCollapsed && <span>New Chat</span>}
          </button>

          {/* Search Conversations Input */}
          {!isCollapsed && (
            <div className="relative">
              <svg
                className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search conversations..."
                className="w-full pl-9 pr-3 py-2 text-xs rounded-xl bg-[#0e223f] border border-[#1b355c] text-slate-200 placeholder-slate-400 focus:outline-hidden focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400/40 transition-all"
              />
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => setSearchQuery('')}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white text-xs"
                >
                  ✕
                </button>
              )}
            </div>
          )}
        </div>

        {/* Scrollable Conversation History */}
        <div className="flex-1 overflow-y-auto px-2 space-y-1 scrollbar-thin scrollbar-thumb-slate-700">
          {!isCollapsed && (
            <div className="px-2 pt-2 pb-1 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
              Recent Conversations
            </div>
          )}

          {filteredConversations.length === 0 ? (
            !isCollapsed && (
              <div className="px-3 py-6 text-center text-xs text-slate-400">
                {searchQuery ? 'No matching conversations' : 'No conversations yet'}
              </div>
            )
          ) : (
            filteredConversations.map((c) => {
              const isActive = c.id === activeConversationId;
              const isEditing = editingId === c.id;
              const isMenuOpen = activeMenuId === c.id;

              if (isEditing) {
                return (
                  <div key={c.id} className="p-1.5 flex items-center gap-1.5 bg-[#0e223f] rounded-xl border border-cyan-500/50">
                    <input
                      type="text"
                      value={editTitle}
                      onChange={(e) => setEditTitle(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleSaveRename(e, c.id);
                        if (e.key === 'Escape') handleCancelRename(e);
                      }}
                      className="flex-1 px-2 py-1 text-xs bg-[#09182d] border border-slate-600 rounded text-white focus:outline-hidden focus:border-cyan-400"
                      autoFocus
                    />
                    <button
                      type="button"
                      onClick={(e) => handleSaveRename(e, c.id)}
                      className="p-1 text-emerald-400 hover:text-emerald-300 text-xs font-bold"
                    >
                      ✓
                    </button>
                    <button
                      type="button"
                      onClick={handleCancelRename}
                      className="p-1 text-slate-400 hover:text-white text-xs"
                    >
                      ✕
                    </button>
                  </div>
                );
              }

              return (
                <div
                  key={c.id}
                  className={`group relative rounded-xl transition-all duration-150 ${
                    isActive
                      ? 'bg-[#163156] text-white shadow-inner border-l-2 border-cyan-400'
                      : 'text-slate-300 hover:bg-[#0e223f] hover:text-white'
                  }`}
                >
                  <div className="flex items-center">
                    <button
                      type="button"
                      onClick={() => {
                        onSelectConversation(c.id);
                        if (onCloseMobile) onCloseMobile();
                      }}
                      className={`flex-1 text-left px-3 py-2.5 text-xs truncate flex items-start gap-2.5 ${
                        isCollapsed ? 'justify-center px-1' : ''
                      }`}
                      title={c.title}
                    >
                      {/* Chat Bubble Icon */}
                      <div className={`mt-0.5 p-1 rounded-md shrink-0 ${isActive ? 'text-cyan-400' : 'text-slate-400 group-hover:text-cyan-300'}`}>
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                          />
                        </svg>
                      </div>

                      {!isCollapsed && (
                        <div className="min-w-0 flex-1">
                          <div className="font-medium truncate text-[13px] leading-tight">
                            {c.title || 'Marine Conversation'}
                          </div>
                          <div className="text-[11px] text-slate-400 mt-0.5">
                            {formatTimestamp(c.updatedAt || c.createdAt)}
                          </div>
                        </div>
                      )}
                    </button>

                    {/* Three-dots Menu on Right */}
                    {!isCollapsed && (
                      <div className="relative pr-2 shrink-0">
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            setActiveMenuId(isMenuOpen ? null : c.id);
                          }}
                          className={`p-1 rounded-md transition-opacity ${
                            isMenuOpen ? 'opacity-100 text-white bg-[#1a3863]' : 'opacity-0 group-hover:opacity-100 text-slate-400 hover:text-white'
                          }`}
                          title="Conversation actions"
                        >
                          <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
                            <circle cx="12" cy="5" r="2" />
                            <circle cx="12" cy="12" r="2" />
                            <circle cx="12" cy="19" r="2" />
                          </svg>
                        </button>

                        {/* Dropdown Popover */}
                        {isMenuOpen && (
                          <div
                            className="absolute right-0 top-full mt-1 w-32 bg-[#091b35] border border-[#19365c] rounded-xl shadow-xl py-1 z-30"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <button
                              type="button"
                              onClick={(e) => handleStartRename(e, c)}
                              className="w-full text-left px-3 py-1.5 text-xs text-slate-200 hover:bg-[#132c4f] hover:text-white flex items-center gap-2"
                            >
                              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                              </svg>
                              Rename
                            </button>
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                setActiveMenuId(null);
                                if (onDeleteConversation) onDeleteConversation(c.id);
                              }}
                              className="w-full text-left px-3 py-1.5 text-xs text-rose-400 hover:bg-rose-950/40 flex items-center gap-2"
                            >
                              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                              </svg>
                              Delete
                            </button>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>


        {/* User Profile Card & Actions at Bottom */}
        <div className="p-3 border-t border-[#142845] bg-[#051122]/60 shrink-0 space-y-2">
          {/* User Profile Info */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="w-9 h-9 rounded-full bg-blue-600 text-white font-bold text-xs flex items-center justify-center shrink-0 shadow-md">
                {userInitials}
              </div>
              {!isCollapsed && (
                <div className="min-w-0">
                  <div className="text-xs font-bold text-white truncate">
                    {userName}
                  </div>
                  <div className="text-[11px] text-slate-400 truncate">
                    {user?.role === 'admin' ? 'Admin Plan' : 'Free Plan'}
                  </div>
                </div>
              )}
            </div>

            {!isCollapsed && (
              <span className="text-slate-400 text-xs font-mono">
                &gt;&gt;
              </span>
            )}
          </div>


          {/* Logout Action */}
          <button
            type="button"
            onClick={logout}
            className={`w-full flex items-center gap-2 px-2 py-1.5 text-xs text-slate-400 hover:text-rose-400 hover:bg-slate-800/40 rounded-lg transition-colors ${
              isCollapsed ? 'justify-center' : ''
            }`}
            title="Sign out of ORCA Marine Intelligence"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            {!isCollapsed && <span>Logout</span>}
          </button>
        </div>
      </aside>
    </>
  );
}
