import React, { useState } from 'react';
import { analyzeOcean } from '../services/orcaApi';
import JsonViewer from './JsonViewer';

export default function OceanSection() {
  const [formData, setFormData] = useState({
    latitude: '15.0',
    longitude: '72.0',
    location_name: 'Offshore Arabian Sea',
    forecast_time_window_hours: 24,
  });
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState(null);
  const [error, setError] = useState(null);

  const applyPreset = (lat, lon, name) => {
    setFormData(prev => ({ ...prev, latitude: lat, longitude: lon, location_name: name }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResponse(null);

    const payload = {
      latitude: parseFloat(formData.latitude),
      longitude: parseFloat(formData.longitude),
      location_name: formData.location_name,
      forecast_time_window_hours: parseInt(formData.forecast_time_window_hours, 10) || 24,
    };

    try {
      const data = await analyzeOcean(payload);
      setResponse(data);
    } catch (err) {
      setError(err.message || 'Ocean Agent request failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-panel" style={{ padding: '28px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h2 style={{ fontSize: '1.45rem', color: 'var(--text-main)' }}>2. Ocean Agent</h2>
            <span className="badge badge-cyan">POST /api/agents/ocean/analyze</span>
          </div>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.86rem', marginTop: '4px' }}>
            Reuses validated Open-Meteo Marine evidence & WMO Code Table 3700 Sea State Classification.
          </p>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '20px' }}>
        <span style={{ fontSize: '0.78rem', color: 'var(--text-dim)', alignSelf: 'center' }}>Presets:</span>
        <button type="button" className="btn-preset" onClick={() => applyPreset('15.0', '72.0', 'Offshore Goa')}>
          Offshore Goa (15.0, 72.0)
        </button>
        <button type="button" className="btn-preset" onClick={() => applyPreset('18.9', '72.8', 'Offshore Mumbai')}>
          Offshore Mumbai (18.9, 72.8)
        </button>
        <button type="button" className="btn-preset" onClick={() => applyPreset('21.15', '79.09', 'Inland Nagpur (Land Test)')}>
          Inland Nagpur (Land Test - Expects Insufficient Evidence)
        </button>
      </div>

      <form onSubmit={handleSubmit}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px', marginBottom: '18px' }}>
          <div>
            <label>Location Label</label>
            <input
              type="text"
              value={formData.location_name}
              onChange={e => setFormData({ ...formData, location_name: e.target.value })}
            />
          </div>
          <div>
            <label>Latitude (-90 to 90)</label>
            <input
              type="number"
              step="any"
              required
              value={formData.latitude}
              onChange={e => setFormData({ ...formData, latitude: e.target.value })}
            />
          </div>
          <div>
            <label>Longitude (-180 to 180)</label>
            <input
              type="number"
              step="any"
              required
              value={formData.longitude}
              onChange={e => setFormData({ ...formData, longitude: e.target.value })}
            />
          </div>
          <div>
            <label>Window (Hours 1 - 168)</label>
            <input
              type="number"
              min="1"
              max="168"
              value={formData.forecast_time_window_hours}
              onChange={e => setFormData({ ...formData, forecast_time_window_hours: e.target.value })}
            />
          </div>
        </div>

        <button type="submit" className="btn btn-primary" disabled={loading}>
          {loading ? <><span className="spinner" /> Analyzing Ocean Conditions...</> : 'Invoke Ocean Agent'}
        </button>
      </form>

      {error && (
        <div className="notice-box notice-danger">
          <strong>Error:</strong> {error}
        </div>
      )}

      {response && (
        <div style={{ marginTop: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span className={`badge badge-${response.status}`}>
                Status: {response.status}
              </span>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                {response.location?.location_name} ({response.location?.requested_latitude}°N, {response.location?.requested_longitude}°E)
              </span>
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
              Provenance: {response.data_source?.provider}
            </span>
          </div>

          {response.status === 'success' && response.observations && (
            <>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '14px', marginBottom: '18px' }}>
                <div className="metric-card">
                  <span className="metric-label">Max Wave Height</span>
                  <div className="metric-value">
                    {response.observations.max_wave_height_m ?? '--'}
                    <span className="metric-unit">m</span>
                  </div>
                </div>
                <div className="metric-card">
                  <span className="metric-label">Average Wave Height</span>
                  <div className="metric-value">
                    {response.observations.avg_wave_height_m ?? '--'}
                    <span className="metric-unit">m</span>
                  </div>
                </div>
                <div className="metric-card">
                  <span className="metric-label">Min Wave Height</span>
                  <div className="metric-value">
                    {response.observations.min_wave_height_m ?? '--'}
                    <span className="metric-unit">m</span>
                  </div>
                </div>
                <div className="metric-card">
                  <span className="metric-label">WMO Sea State</span>
                  <div className="metric-value" style={{ fontSize: '1.2rem', color: 'var(--cyan)' }}>
                    Code {response.analysis.sea_state_code ?? 'N/A'}
                  </div>
                  <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
                    {response.analysis.sea_state_category}
                  </span>
                </div>
              </div>

              {response.analysis?.summary && (
                <div className="notice-box notice-info">
                  {response.analysis.summary}
                </div>
              )}

              {response.observations.timeseries && response.observations.timeseries.length > 0 && (
                <div style={{ marginTop: '20px' }}>
                  <h4 style={{ fontSize: '0.9rem', marginBottom: '10px', color: 'var(--text-muted)' }}>
                    Wave Height Profile (Next {Math.min(12, response.observations.timeseries.length)} Hours)
                  </h4>
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'flex-end', height: '110px', background: 'var(--bg-surface)', padding: '12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-light)' }}>
                    {response.observations.timeseries.slice(0, 12).map((pt, idx) => {
                      const h = pt.wave_height_m || 0;
                      const maxVal = Math.max(1, ...response.observations.timeseries.map(p => p.wave_height_m || 0));
                      const pct = Math.max(10, Math.min(100, (h / maxVal) * 100));
                      return (
                        <div key={idx} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', height: '100%', justifyContent: 'flex-end' }}>
                          <span style={{ fontSize: '0.66rem', color: 'var(--primary-blue)', fontWeight: 600, marginBottom: '3px' }}>{h.toFixed(1)}m</span>
                          <div style={{
                            width: '100%',
                            height: `${pct}%`,
                            background: 'var(--primary-blue)',
                            borderRadius: '3px 3px 0 0',
                          }} />
                          <span style={{ fontSize: '0.62rem', color: 'var(--text-dim)', marginTop: '4px' }}>
                            {pt.timestamp ? pt.timestamp.split('T')[1]?.slice(0, 2) : idx}h
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </>
          )}

          {response.status === 'insufficient_evidence' && (
            <div className="notice-box notice-warning">
              <div>
                <strong>Insufficient Evidence Notice:</strong>
                <p style={{ marginTop: '4px' }}>{response.analysis?.summary}</p>
              </div>
            </div>
          )}

          {response.warnings && response.warnings.length > 0 && (
            <div className="notice-box notice-warning">
              <div>
                <strong>Operational Warnings:</strong>
                <ul style={{ paddingLeft: '18px', marginTop: '4px' }}>
                  {response.warnings.map((w, idx) => <li key={idx}>{w}</li>)}
                </ul>
              </div>
            </div>
          )}

          <JsonViewer data={response} title="Ocean Agent Response Payload" />
        </div>
      )}
    </div>
  );
}
