import React, { useState } from 'react';

export default function JsonViewer({ data, title = "Raw Agent Response" }) {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  if (!data) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(JSON.stringify(data, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div style={{ marginTop: '16px', borderTop: '1px solid var(--border-light)', paddingTop: '14px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
        <button
          onClick={() => setExpanded(!expanded)}
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--primary-blue)',
            cursor: 'pointer',
            fontSize: '0.82rem',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontFamily: 'var(--font-heading)',
          }}
        >
          <span>{expanded ? '▼' : '►'}</span>
          <span>{title} ({data.agent} • {data.status})</span>
        </button>

        {expanded && (
          <button
            onClick={handleCopy}
            className="btn-preset"
            style={{ fontSize: '0.72rem', padding: '3px 8px' }}
          >
            {copied ? '✓ Copied' : 'Copy JSON'}
          </button>
        )}
      </div>

      {expanded && (
        <pre style={{
          background: '#F9FAFB',
          border: '1px solid var(--border-light)',
          borderRadius: 'var(--radius-sm)',
          padding: '12px 14px',
          fontSize: '0.76rem',
          fontFamily: 'var(--font-mono)',
          color: '#374151',
          overflowX: 'auto',
          maxHeight: '340px',
          lineHeight: '1.45',
        }}>
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </div>
  );
}
