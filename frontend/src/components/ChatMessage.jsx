import React from 'react';
import EvidenceView from './EvidenceView';
import OrcaLogo from './OrcaLogo';

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
        <strong key={`b-${match.index}`} className="font-semibold text-slate-900">
          {token.slice(2, -2)}
        </strong>
      );
    } else if (token.startsWith('`') && token.endsWith('`')) {
      parts.push(
        <code
          key={`c-${match.index}`}
          className="bg-slate-100 text-sky-800 px-1.5 py-0.5 rounded-md text-[13px] font-mono border border-slate-200/60"
        >
          {token.slice(1, -1)}
        </code>
      );
    } else if (token.startsWith('*') && token.endsWith('*')) {
      parts.push(
        <em key={`i-${match.index}`} className="italic text-slate-700">
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

function RenderMarkdown({ content }) {
  if (!content) return null;
  const lines = content.split('\n');
  const elements = [];
  let currentList = [];
  let inCodeBlock = false;
  let codeBlockLines = [];

  const flushList = () => {
    if (currentList.length > 0) {
      elements.push(
        <ul key={`ul-${elements.length}`} className="my-2 pl-6 list-disc space-y-1">
          {currentList.map((item, idx) => (
            <li key={idx} className="leading-relaxed">
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
          className="my-3 p-4 bg-slate-900 text-slate-100 rounded-xl text-xs sm:text-sm font-mono overflow-x-auto border border-slate-800"
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
      currentList.push(trimmed.replace(/^[-*]\s+/, ''));
      continue;
    }

    flushList();

    if (trimmed.startsWith('### ')) {
      elements.push(
        <h4 key={`h4-${i}`} className="font-bold text-slate-900 text-base mt-4 mb-1.5">
          {formatInline(trimmed.replace(/^###\s+/, ''))}
        </h4>
      );
    } else if (trimmed.startsWith('## ')) {
      elements.push(
        <h3 key={`h3-${i}`} className="font-bold text-slate-900 text-lg mt-5 mb-2">
          {formatInline(trimmed.replace(/^##\s+/, ''))}
        </h3>
      );
    } else if (trimmed.startsWith('# ')) {
      elements.push(
        <h2 key={`h2-${i}`} className="font-extrabold text-slate-900 text-xl mt-6 mb-2.5">
          {formatInline(trimmed.replace(/^#\s+/, ''))}
        </h2>
      );
    } else {
      elements.push(
        <p key={`p-${i}`} className="my-2 leading-relaxed">
          {formatInline(trimmed)}
        </p>
      );
    }
  }

  flushList();
  flushCodeBlock();

  return <div className="space-y-1">{elements}</div>;
}

export default function ChatMessage({ message, onApproveTool }) {
  const isUser = message.role === 'user';
  const isError = Boolean(message.isError);

  // User Message: Aligned to the right in a modern bubble
  if (isUser) {
    return (
      <div className="flex justify-end my-4 px-2 sm:px-4">
        <div className="max-w-2xl bg-slate-100 hover:bg-slate-200/70 text-slate-900 rounded-3xl px-5 py-3.5 text-[15px] leading-relaxed shadow-2xs transition-colors">
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
      </div>
    );
  }

  // Assistant Response: Aligned to the left with custom ORCA logo avatar
  return (
    <div className="flex items-start gap-4 my-6 px-2 sm:px-4">
      {/* Avatar Badge */}
      <div
        className={`w-9 h-9 rounded-full flex items-center justify-center shrink-0 shadow-xs mt-0.5 ${
          isError ? 'bg-rose-600 text-white p-2' : 'p-0.5 drop-shadow-sm'
        }`}
      >
        {isError ? (
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        ) : (
          <OrcaLogo variant="icon" className="w-8 h-8" />
        )}
      </div>

      {/* Message Body */}
      <div className="flex-1 min-w-0 text-[15px] text-slate-800 leading-relaxed">
        {/* Header Metadata */}
        <div className="flex items-center gap-2 mb-2">
          <span className="font-bold text-xs uppercase tracking-wider text-slate-900">
            ORCA Assistant
          </span>
          {message.selectedAgent && message.selectedAgent !== 'auto' && (
            <span className="text-[11px] uppercase font-mono px-2 py-0.5 rounded-full bg-sky-100 text-sky-800 font-semibold border border-sky-200">
              {message.selectedAgent}
            </span>
          )}
          {message.timestamp && (
            <span className="text-xs text-slate-400">
              {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
          )}
        </div>

        {/* Reasoning Execution Plan */}
        {message.plan && message.plan.length > 0 && (
          <div className="my-3 p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs space-y-1.5">
            <span className="font-bold text-slate-700 block text-[11px] uppercase tracking-wider">
              Reasoning & Dispatch Plan
            </span>
            <div className="space-y-1">
              {message.plan.map((step, idx) => (
                <div key={idx} className="flex items-center gap-2.5 text-slate-700 text-xs">
                  <span className="w-4 h-4 rounded-full bg-sky-100 text-sky-800 font-mono text-[10px] flex items-center justify-center shrink-0 font-bold">
                    {step.step_id || idx + 1}
                  </span>
                  <span className="flex-1 truncate">{step.description}</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-200/80 text-slate-600 font-medium">
                    {step.status || 'dispatched'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Tool Calls requiring approval */}
        {message.tool_calls && message.tool_calls.length > 0 && onApproveTool && (
          <div className="my-3 space-y-2">
            {message.tool_calls.map((call, idx) => (
              <div
                key={idx}
                className="p-3 rounded-xl border border-amber-200 bg-amber-50/70 text-xs flex items-center justify-between gap-3 shadow-2xs"
              >
                <div>
                  <span className="font-bold text-amber-900">Action: </span>
                  <code className="text-amber-800 font-mono font-semibold">{call.tool_name}</code>
                </div>
                {call.status === 'pending_approval' && (
                  <button
                    type="button"
                    onClick={() => onApproveTool(call.call_id, 'approve')}
                    className="px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-700 text-white font-semibold text-xs shadow-xs transition-colors shrink-0"
                  >
                    Authorize Tool
                  </button>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Markdown Content */}
        <div className="prose prose-slate max-w-none text-slate-800 text-[15px] leading-relaxed">
          <RenderMarkdown content={message.content} />
        </div>

        {/* Structured Evidence View */}
        <EvidenceView
          agentResults={message.agent_results}
          evidenceSummary={message.evidence_summary}
          risk={message.risk}
          metrics={message.metrics}
          limitations={message.limitations}
          warnings={message.warnings}
          legalDisclaimer={message.legal_disclaimer}
        />
      </div>
    </div>
  );
}
