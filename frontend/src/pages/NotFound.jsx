import React from 'react';
import { Link } from 'react-router-dom';

export default function NotFound() {
  return (
    <div
      style={{
        minHeight: '70vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        textAlign: 'center',
        padding: '2rem',
      }}
    >
      <div style={{ fontSize: '4rem', marginBottom: '1rem' }}>🌊</div>
      <h1 style={{ fontSize: '2rem', color: 'var(--orca-navy-950)', marginBottom: '0.5rem' }}>
        Sector Not Found (404)
      </h1>
      <p style={{ color: 'var(--orca-text-secondary)', maxWidth: 450, marginBottom: '1.5rem' }}>
        The coordinates or oceanographic view you requested does not exist in the ORCA routing network.
      </p>
      <div style={{ display: 'flex', gap: '10px' }}>
        <Link to="/register" className="orca-btn orca-btn-primary">
          Return to Registration ➜
        </Link>
        <Link to="/user/dashboard" className="orca-btn orca-btn-outline">
          Go to User Dashboard ➜
        </Link>
      </div>
    </div>
  );
}
