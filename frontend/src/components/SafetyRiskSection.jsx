import React, { useState } from 'react';
import { analyzeSafetyRisk } from '../services/orcaApi';
import JsonViewer from './JsonViewer';

export default function SafetyRiskSection() {
  const [formData, setFormData] = useState({
    latitude: '15.0',
    longitude: '72.0',
    location_name: 'Offshore Arabian Sea',
    vessel_type: 'small_craft',
    wave_height_m: '',
    wind_speed_knots: '',
    precipitation_mm: '',
  });
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState(null);
  const [error, setError] = useState(null);

  const applyPreset = (lat, lon, name, vtype, wave = '', wind = '', rain = '') => {
    setFormData({
      latitude: lat,
      longitude: lon,
      location_name: name,
      vessel_type: vtype,
      wave_height_m: wave,
      wind_speed_knots: wind,
      precipitation_mm: rain,
    });
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
      vessel_type: formData.vessel_type,
    };
    if (formData.wave_height_m !== '') payload.wave_height_m = parseFloat(formData.wave_height_m);
    if (formData.wind_speed_knots !== '') payload.wind_speed_knots = parseFloat(formData.wind_speed_knots);
    if (formData.precipitation_mm !== '') payload.precipitation_mm = parseFloat(formData.precipitation_mm);

    try {
      const data = await analyzeSafetyRisk(payload);
      setResponse(data);
    } catch (err) {
      setError(err.message || 'Safety/Risk Agent request failed');
    } finally {
      setLoading(false);
    }
  };

  const getRiskColor = (cat) => {
    if (!cat) return 'var(--text-muted)';
    const upper = cat.toUpperCase();
    if (upper.includes('CRITICAL')) return 'var(--coral)';
    if (upper.includes('HIGH')) return '#ff6b4a';
    if (upper.includes('MODERATE')) return 'var(--amber)';
    if (upper.includes('LOW')) return 'var(--emerald)';
    return 'var(--amber)';
  };

  return (
    <div className="glass-panel" style={{ padding: '28px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h2 style={{ fontSize: '1.45rem', color: 'var(--text-main)' }}>5. Safety/Risk Agent</h2>
            <span className="badge badge-cyan">POST /api/agents/safety-risk/analyze</span>
          </div>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.86rem', marginTop: '4px' }}>
            Autonomous marine hazard assessment, vessel operational risk envelopes, and weather safety rules.
          </p>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '20px' }}>
        <span style={{ fontSize: '0.78rem', color: 'var(--text-dim)', alignSelf: 'center' }}>Presets:</span>
        <button
          type="button"
          className="btn-preset"
          onClick={() => applyPreset('15.0', '72.0', 'Offshore Goa', 'small_craft')}
        >
          Offshore Goa (Live Telemetry)
        </button>
        <button
          type="button"
          className="btn-preset"
          onClick={() => applyPreset('15.0', '72.0', 'Storm Hazard Test', 'small_craft', '3.8', '38.0', '12.0')}
        >
          Simulate Severe Gale (Hs=3.8m, 38kts Wind)
        </button>
        <button
          type="button"
          className="btn-preset"
          onClick={() => applyPreset('21.15', '79.09', 'Inland Nagpur (Land Test)', 'small_craft')}
        >
          Inland Nagpur (Missing Evidence != Safe)
        </button>
      </div>

      <form onSubmit={handleSubmit}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px', marginBottom: '16px' }}>
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
            <label>Vessel Category</label>
            <select
              value={formData.vessel_type}
              onChange={e => setFormData({ ...formData, vessel_type: e.target.value })}
            >
              <option value="small_craft">Small Craft / Motorboat (&lt; 12m)</option>
              <option value="trawler">Mechanized Fishing Trawler</option>
              <option value="commercial_cargo">Commercial Cargo / Tanker</option>
              <option value="passenger">Passenger Ferry</option>
            </select>
          </div>
        </div>

        <div style={{ background: 'var(--bg-surface)', padding: '14px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-light)', marginBottom: '18px' }}>
          <span style={{ fontSize: '0.76rem', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: '8px' }}>
            Optional In-Situ Observation Overrides (Leave blank to fetch live provider telemetry)
          </span>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '12px' }}>
            <div>
              <label style={{ fontSize: '0.74rem' }}>Significant Wave Height (m)</label>
              <input
                type="number"
                step="0.1"
                min="0"
                placeholder="Auto-fetch if blank"
                value={formData.wave_height_m}
                onChange={e => setFormData({ ...formData, wave_height_m: e.target.value })}
              />
            </div>
            <div>
              <label style={{ fontSize: '0.74rem' }}>Wind Speed (knots)</label>
              <input
                type="number"
                step="0.5"
                min="0"
                placeholder="Auto-fetch if blank"
                value={formData.wind_speed_knots}
                onChange={e => setFormData({ ...formData, wind_speed_knots: e.target.value })}
              />
            </div>
            <div>
              <label style={{ fontSize: '0.74rem' }}>Precipitation Rate (mm/h)</label>
              <input
                type="number"
                step="0.1"
                min="0"
                placeholder="Auto-fetch if blank"
                value={formData.precipitation_mm}
                onChange={e => setFormData({ ...formData, precipitation_mm: e.target.value })}
              />
            </div>
          </div>
        </div>

        <button type="submit" className="btn btn-primary" disabled={loading}>
          {loading ? <><span className="spinner" /> Assessing Marine Risk...</> : 'Invoke Safety/Risk Agent'}
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
                Vessel: <strong style={{ textTransform: 'capitalize' }}>{response.observations?.vessel_type?.replace('_', ' ')}</strong>
              </span>
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
              Data Completeness: {response.observations?.data_completeness}
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: '14px', marginBottom: '18px' }}>
            <div className="metric-card" style={{ borderColor: getRiskColor(response.analysis?.risk_category) }}>
              <span className="metric-label">Risk Category</span>
              <div className="metric-value" style={{ color: getRiskColor(response.analysis?.risk_category), fontSize: '1.25rem' }}>
                {response.analysis?.risk_category || 'UNKNOWN'}
              </div>
            </div>
            <div className="metric-card">
              <span className="metric-label">Assessed Wave</span>
              <div className="metric-value">
                {response.observations?.wave_height_m != null ? response.observations.wave_height_m.toFixed(2) : '--'}
                <span className="metric-unit">m</span>
              </div>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>
                ({response.observations?.sea_state_category || 'Sea state'})
              </span>
            </div>
            <div className="metric-card">
              <span className="metric-label">Assessed Wind</span>
              <div className="metric-value">
                {response.observations?.wind_speed_knots != null ? response.observations.wind_speed_knots.toFixed(1) : '--'}
                <span className="metric-unit">kts</span>
              </div>
            </div>
            <div className="metric-card">
              <span className="metric-label">Precipitation</span>
              <div className="metric-value">
                {response.observations?.precipitation_mm != null ? response.observations.precipitation_mm.toFixed(1) : '--'}
                <span className="metric-unit">mm/h</span>
              </div>
            </div>
          </div>

          <div className="notice-box notice-info" style={{ marginBottom: '14px' }}>
            <div>
              <strong>Vessel Safety Principle:</strong>
              <p style={{ marginTop: '4px' }}>
                A LOW risk score reflects only numerical model thresholds (wave height, wind, precipitation) and does NOT certify vessel safety, sailing clearance, or vessel seaworthiness. Real-time harbor alerts, barometric pressure, current sets, and vessel stability must always be verified.
              </p>
            </div>
          </div>

          {response.status === 'insufficient_evidence' && (
            <div className="notice-box notice-warning" style={{ marginBottom: '14px' }}>
              <div>
                <strong>Evidence Incomplete Notice:</strong>
                <p style={{ marginTop: '4px' }}>
                  Required marine or atmospheric hazard telemetry is unavailable or stale for this location. Missing evidence is strictly NOT classified as safe.
                </p>
              </div>
            </div>
          )}

          {response.analysis?.risk_reasons && response.analysis.risk_reasons.length > 0 && (
            <div style={{ background: 'var(--bg-surface)', padding: '16px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-light)', marginBottom: '14px' }}>
              <h4 style={{ fontSize: '0.86rem', color: 'var(--text-muted)', marginBottom: '8px' }}>
                Risk Factors & Contributing Hazards:
              </h4>
              <ul style={{ paddingLeft: '18px', fontSize: '0.82rem', color: 'var(--text-main)', lineHeight: '1.6' }}>
                {response.analysis.risk_reasons.map((reason, idx) => (
                  <li key={idx}>{reason}</li>
                ))}
              </ul>
            </div>
          )}

          {response.analysis?.recommendations && response.analysis.recommendations.length > 0 && (
            <div style={{ background: 'var(--bg-surface)', padding: '16px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-light)', marginBottom: '14px' }}>
              <h4 style={{ fontSize: '0.86rem', color: 'var(--primary-blue)', marginBottom: '8px' }}>
                Operational Recommendations:
              </h4>
              <ul style={{ paddingLeft: '18px', fontSize: '0.82rem', color: 'var(--text-main)', lineHeight: '1.6' }}>
                {response.analysis.recommendations.map((rec, idx) => (
                  <li key={idx}>{rec}</li>
                ))}
              </ul>
            </div>
          )}

          {response.analysis?.legal_notice && (
            <div className="notice-box notice-warning">
              <div>
                <strong>Decision Support Notice:</strong>
                <p style={{ marginTop: '4px' }}>{response.analysis.legal_notice}</p>
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

          <JsonViewer data={response} title="Safety/Risk Agent Response Payload" />
        </div>
      )}
    </div>
  );
}
