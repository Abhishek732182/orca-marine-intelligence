import React, { useState, useEffect } from 'react';
import { checkHealth, BASE_URL } from '../services/orcaApi';

export default function Navbar({ onToggleView, currentView }) {
  const [healthStatus, setHealthStatus] = useState('checking');
  const [apiInfo, setApiInfo] = useState(null);

  useEffect(() => {
    let isMounted = true;
    checkHealth()
      .then(res => {
        if (isMounted) {
          setHealthStatus('online');
          setApiInfo(res);
        }
      })
      .catch(() => {
        if (isMounted) setHealthStatus('offline');
      });

    const interval = setInterval(() => {
      checkHealth()
        .then(() => isMounted && setHealthStatus('online'))
        .catch(() => isMounted && setHealthStatus('offline'));
    }, 15000);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <header style={{
      borderBottom: '1px solid var(--border-light)',
      background: '#FFFFFF',
      position: 'sticky',
      top: 0,
      zIndex: 100,
      padding: '12px 24px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      boxShadow: 'var(--shadow-subtle)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div style={{
          width: '36px',
          height: '36px',
          borderRadius: '8px',
          background: 'var(--primary-blue)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 1px 3px rgba(37, 99, 235, 0.2)',
        }}>
          <span style={{ fontSize: '1.2rem', fontWeight: 800, color: '#FFFFFF' }}>✦</span>
        </div>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h1 style={{ fontSize: '1.15rem', fontWeight: 700, letterSpacing: '-0.01em', color: 'var(--text-main)' }}>
              ORCA Marine Intelligence
            </h1>
            <span className="badge badge-cyan" style={{ fontSize: '0.68rem', background: '#EFF6FF', color: '#2563EB', borderColor: '#BFDBFE' }}>
              6 AI AGENTS
            </span>
          </div>
          <p style={{ fontSize: '0.74rem', color: 'var(--text-secondary)' }}>
            Decentralized Architecture • Evidence-Grounded Maritime Operations
          </p>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        {/* API Health Pill */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '5px 12px',
          borderRadius: '20px',
          background: '#F9FAFB',
          border: '1px solid var(--border-light)',
          fontSize: '0.76rem',
        }}>
          <span style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            background: healthStatus === 'online' ? 'var(--emerald)' : healthStatus === 'checking' ? 'var(--amber)' : 'var(--coral)',
            display: 'inline-block',
          }} />
          <span style={{ color: 'var(--text-secondary)' }}>
            API: <strong style={{ color: healthStatus === 'online' ? '#065F46' : 'var(--coral-text)' }}>
              {healthStatus.toUpperCase()}
            </strong>
            {apiInfo?.service && <span style={{ marginLeft: '4px', color: 'var(--text-dim)' }}>[{apiInfo.service}]</span>}
          </span>
          <span style={{ color: 'var(--text-dim)', fontSize: '0.72rem' }}>
            ({BASE_URL})
          </span>
        </div>

        {/* Action icons: Notifications & Help */}
        <button
          title="Notifications"
          style={{
            background: '#F9FAFB',
            border: '1px solid var(--border-light)',
            borderRadius: '8px',
            width: '34px',
            height: '34px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
            fontSize: '0.9rem',
            color: 'var(--text-secondary)',
          }}
        >
          🔔
        </button>

        <button
          title="Help & Maritime Guide"
          style={{
            background: '#F9FAFB',
            border: '1px solid var(--border-light)',
            borderRadius: '8px',
            width: '34px',
            height: '34px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
            fontSize: '0.9rem',
            color: 'var(--text-secondary)',
          }}
        >
          ❓
        </button>

        {/* User Profile Avatar */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '4px 10px',
          borderRadius: '20px',
          background: '#F9FAFB',
          border: '1px solid var(--border-light)',
          fontSize: '0.78rem',
        }}>
          <div style={{
            width: '26px',
            height: '26px',
            borderRadius: '50%',
            background: '#EFF6FF',
            border: '1px solid #BFDBFE',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '0.82rem',
            color: '#2563EB',
            fontWeight: 700,
          }}>
            ⚓
          </div>
          <span style={{ fontWeight: 600, color: 'var(--text-main)' }}>Capt. Sharma</span>
        </div>
      </div>
    </header>
  );
}
