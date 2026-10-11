import React, { useState } from 'react';
import { analyzeWeather } from '../services/orcaApi';
import JsonViewer from './JsonViewer';

export default function WeatherSection() {
  const [formData, setFormData] = useState({
    latitude: '15.0',
    longitude: '72.0',
    location_name: 'Offshore Goa',
    forecast_days: 1,
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

    const payload = {};
    if (formData.latitude !== '') payload.latitude = parseFloat(formData.latitude);
    if (formData.longitude !== '') payload.longitude = parseFloat(formData.longitude);
    if (formData.location_name) payload.location_name = formData.location_name;
    payload.forecast_days = parseInt(formData.forecast_days, 10) || 1;

    try {
      const data = await analyzeWeather(payload);
      setResponse(data);
    } catch (err) {
      setError(err.message || 'Weather Agent request failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-panel" style={{ padding: '28px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h2 style={{ fontSize: '1.45rem', color: 'var(--text-main)' }}>1. Weather Agent</h2>
            <span className="badge badge-cyan">POST /api/agents/weather/analyze</span>
          </div>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.86rem', marginTop: '4px' }}>
            Live atmospheric telemetry: wind speed, Beaufort scale classification, temperature, and precipitation.
          </p>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '20px' }}>
        <span style={{ fontSize: '0.78rem', color: 'var(--text-dim)', alignSelf: 'center' }}>Presets:</span>
        <button type="button" className="btn-preset" onClick={() => applyPreset('15.0', '72.0', 'Offshore Goa')}>
          Offshore Goa (15.0, 72.0)
        </button>
        <button type="button" className="btn-preset" onClick={() => applyPreset('18.93', '72.83', 'Mumbai Port')}>
          Mumbai Port (18.93, 72.83)
        </button>
        <button type="button" className="btn-preset" onClick={() => applyPreset('', '', 'Panaji')}>
          Panaji (Geocoding Only)
        </button>
      </div>

      <form onSubmit={handleSubmit}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px', marginBottom: '18px' }}>
          <div>
            <label>Location Label / Query</label>
            <input
              type="text"
              value={formData.location_name}
              onChange={e => setFormData({ ...formData, location_name: e.target.value })}
              placeholder="e.g. Offshore Goa"
            />
          </div>
          <div>
            <label>Latitude (-90 to 90)</label>
            <input
              type="number"
              step="any"
              value={formData.latitude}
              onChange={e => setFormData({ ...formData, latitude: e.target.value })}
              placeholder="e.g. 15.0"
            />
          </div>
          <div>
            <label>Longitude (-180 to 180)</label>
            <input
              type="number"
              step="any"
              value={formData.longitude}
              onChange={e => setFormData({ ...formData, longitude: e.target.value })}
              placeholder="e.g. 72.0"
            />
          </div>
          <div>
            <label>Forecast Days (1 - 7)</label>
            <input
              type="number"
              min="1"
              max="7"
              value={formData.forecast_days}
              onChange={e => setFormData({ ...formData, forecast_days: e.target.value })}
            />
          </div>
        </div>

        <button type="submit" className="btn btn-primary" disabled={loading}>
          {loading ? <><span className="spinner" /> Analyzing Weather...</> : 'Invoke Weather Agent'}
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
                {response.location?.location_name} ({response.location?.latitude?.toFixed(3)}°N, {response.location?.longitude?.toFixed(3)}°E)
              </span>
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
              Source: {response.data_source?.provider}
            </span>
          </div>

          {response.status === 'success' && response.observations && (
            <>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: '14px', marginBottom: '18px' }}>
                <div className="metric-card">
                  <span className="metric-label">Air Temperature</span>
                  <div className="metric-value">
                    {response.observations.temperature_c ?? '--'}
                    <span className="metric-unit">°C</span>
                  </div>
                </div>
                <div className="metric-card">
                  <span className="metric-label">Wind Velocity</span>
                  <div className="metric-value">
                    {response.observations.wind_speed_knots ?? '--'}
                    <span className="metric-unit">kts</span>
                  </div>
                  <span style={{ fontSize: '0.74rem', color: 'var(--text-dim)' }}>
                    ({response.observations.wind_speed_kmh} km/h)
                  </span>
                </div>
                <div className="metric-card">
                  <span className="metric-label">Beaufort Scale</span>
                  <div className="metric-value" style={{ fontSize: '1.2rem', color: 'var(--cyan)' }}>
                    Force {response.observations.beaufort_scale?.force ?? '--'}
                  </div>
                  <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
                    {response.observations.beaufort_scale?.name}
                  </span>
                </div>
                <div className="metric-card">
                  <span className="metric-label">Wind Direction</span>
                  <div className="metric-value">
                    {response.observations.wind_direction_deg ?? '--'}
                    <span className="metric-unit">°</span>
                  </div>
                </div>
              </div>

              {response.analysis?.summary && (
                <div className="notice-box notice-info" style={{ marginTop: '10px' }}>
                  {response.analysis.summary}
                </div>
              )}

              {response.forecast && response.forecast.length > 0 && (
                <div style={{ marginTop: '20px' }}>
                  <h4 style={{ fontSize: '0.9rem', marginBottom: '10px', color: 'var(--text-muted)' }}>
                    Hourly Forecast Preview (First 8h of {response.forecast.length}h)
                  </h4>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(110px, 1fr))', gap: '10px' }}>
                    {response.forecast.slice(0, 8).map((item, i) => (
                      <div key={i} style={{
                        background: 'var(--bg-surface)',
                        padding: '10px',
                        borderRadius: 'var(--radius-sm)',
                        border: '1px solid var(--border-light)',
                        textAlign: 'center',
                        fontSize: '0.78rem',
                      }}>
                        <div style={{ color: 'var(--text-dim)', fontSize: '0.72rem' }}>
                          {item.timestamp ? item.timestamp.split('T')[1]?.slice(0, 5) : '--'}
                        </div>
                        <div style={{ fontWeight: 700, margin: '4px 0', color: 'var(--text-main)' }}>
                          {item.temperature_c}°C
                        </div>
                        <div style={{ color: 'var(--primary-blue)', fontWeight: 600 }}>
                          {item.wind_speed_knots} kts
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}

          {response.status === 'insufficient_evidence' && (
            <div className="notice-box notice-warning">
              <div>
                <strong>Insufficient Evidence Notice:</strong>
                <p style={{ marginTop: '4px' }}>{response.analysis?.summary || 'Required weather telemetry is unavailable for this query.'}</p>
              </div>
            </div>
          )}

          {response.warnings && response.warnings.length > 0 && (
            <div className="notice-box notice-warning">
              <div>
                <strong>Warnings:</strong>
                <ul style={{ paddingLeft: '18px', marginTop: '4px' }}>
                  {response.warnings.map((w, idx) => <li key={idx}>{w}</li>)}
                </ul>
              </div>
            </div>
          )}

          <JsonViewer data={response} title="Weather Agent Response Payload" />
        </div>
      )}
    </div>
  );
}
