import React, { useState } from 'react';
import { analyzeFishingZone } from '../services/orcaApi';
import JsonViewer from './JsonViewer';

export default function FishingZoneSection() {
  const [formData, setFormData] = useState({
    latitude: '15.0',
    longitude: '72.0',
    location_name: 'Goa Coastal Waters',
    target_species: 'Mackerel',
  });
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState(null);
  const [error, setError] = useState(null);

  const applyPreset = (lat, lon, name, species) => {
    setFormData({ latitude: lat, longitude: lon, location_name: name, target_species: species });
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
    if (formData.target_species) payload.target_species = formData.target_species;

    try {
      const data = await analyzeFishingZone(payload);
      setResponse(data);
    } catch (err) {
      setError(err.message || 'Fishing Zone Agent request failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-panel" style={{ padding: '28px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h2 style={{ fontSize: '1.45rem', color: 'var(--text-main)' }}>3. Fishing Zone Agent</h2>
            <span className="badge badge-cyan">POST /api/agents/fishing-zone/analyze</span>
          </div>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.86rem', marginTop: '4px' }}>
            Marine operational feasibility for fishing crafts. Adheres to evidence grounding (never invents unverified fish schools).
          </p>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '20px' }}>
        <span style={{ fontSize: '0.78rem', color: 'var(--text-dim)', alignSelf: 'center' }}>Presets:</span>
        <button type="button" className="btn-preset" onClick={() => applyPreset('15.0', '72.0', 'Arabian Sea Shelf', 'Mackerel')}>
          Arabian Sea (15.0, 72.0) - Mackerel
        </button>
        <button type="button" className="btn-preset" onClick={() => applyPreset('18.9', '72.8', 'Mumbai Fishing Ground', 'Bombay Duck')}>
          Mumbai Ground (18.9, 72.8)
        </button>
        <button type="button" className="btn-preset" onClick={() => applyPreset('', '', 'Unspecified', '')}>
          Omit Coordinates (Test Validation)
        </button>
      </div>

      <form onSubmit={handleSubmit}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px', marginBottom: '18px' }}>
          <div>
            <label>Fishing Sector Label</label>
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
            <label>Target Species (Optional)</label>
            <input
              type="text"
              value={formData.target_species}
              onChange={e => setFormData({ ...formData, target_species: e.target.value })}
              placeholder="e.g. Tuna, Mackerel, Sardine"
            />
          </div>
        </div>

        <button type="submit" className="btn btn-primary" disabled={loading}>
          {loading ? <><span className="spinner" /> Evaluating Fisheries Evidence...</> : 'Invoke Fishing Zone Agent'}
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
                Status: {response.status.toUpperCase()}
              </span>
              {response.data_source?.is_offline_fixture ? (
                <span className="badge" style={{ background: '#fef3c7', color: '#92400e', border: '1px solid #fde68a', fontWeight: 'bold' }}>
                  OFFLINE CACHED FIXTURE
                </span>
              ) : (
                <span className="badge" style={{ background: 'rgba(16, 185, 129, 0.15)', color: '#059669', border: '1px solid rgba(16, 185, 129, 0.3)' }}>
                  LIVE OBSERVATIONS
                </span>
              )}
              <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                Target: <strong>{response.analysis?.target_species_queried}</strong>
              </span>
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
              Provider: {response.data_source?.provider} {response.data_source?.active_data_mode ? `(${response.data_source.active_data_mode})` : ''}
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '14px', marginBottom: '18px' }}>
            <div className="metric-card">
              <span className="metric-label">Vessel Operability</span>
              <div className="metric-value" style={{
                fontSize: '1.2rem',
                color: response.analysis?.operational_feasibility === 'FAVORABLE' ? 'var(--emerald)' : 'var(--amber)'
              }}>
                {response.analysis?.operational_feasibility || 'UNKNOWN'}
              </div>
            </div>
            <div className="metric-card">
              <span className="metric-label">Observed Wave Max</span>
              <div className="metric-value">
                {response.observations?.max_wave_height_m ?? '--'}
                <span className="metric-unit">m</span>
              </div>
            </div>
            <div className="metric-card">
              <span className="metric-label">Sea State</span>
              <div className="metric-value" style={{ fontSize: '1.15rem' }}>
                {response.observations?.sea_state_category || 'N/A'}
              </div>
            </div>
            <div className="metric-card">
              <span className="metric-label">Fisheries Telemetry</span>
              <div className="metric-value" style={{
                fontSize: '1.15rem',
                color: response.analysis?.verified_fish_distribution?.status === 'VERIFIED' ? 'var(--emerald)' : 'var(--amber)'
              }}>
                {response.analysis?.verified_fish_distribution?.status || 'UNVERIFIED'}
              </div>
            </div>
            <div className="metric-card">
              <span className="metric-label">Suitability Score</span>
              <div className="metric-value" style={{ fontSize: '1.15rem' }}>
                {response.analysis?.scoring?.suitability_score !== null && response.analysis?.scoring?.suitability_score !== undefined
                  ? `${response.analysis.scoring.suitability_score}/100`
                  : 'N/A'}
                <span className="metric-unit" style={{ fontSize: '0.75rem' }}>
                  ({response.analysis?.scoring?.evidence_coverage_pct ?? 0}% cov)
                </span>
              </div>
            </div>
          </div>

          {response.analysis?.zone_summary && (
            <div className="notice-box notice-info">
              {response.analysis.zone_summary}
            </div>
          )}

          {response.analysis?.criteria_applied && (
            <div style={{ marginTop: '16px', background: 'rgba(5, 12, 26, 0.7)', padding: '16px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-light)' }}>
              <h4 style={{ fontSize: '0.86rem', color: 'var(--text-muted)', marginBottom: '8px' }}>
                Evidence & Criteria Applied:
              </h4>
              <ul style={{ paddingLeft: '18px', fontSize: '0.82rem', color: '#cbd5e1', lineHeight: '1.6' }}>
                {response.analysis.criteria_applied.map((crit, idx) => (
                  <li key={idx}>{crit}</li>
                ))}
              </ul>
            </div>
          )}

          {response.analysis?.vessel_safety_notice && (
            <div className="notice-box notice-warning" style={{ marginTop: '16px' }}>
              <div>
                <strong>Vessel Safety Grounding:</strong>
                <p style={{ marginTop: '4px' }}>{response.analysis.vessel_safety_notice}</p>
              </div>
            </div>
          )}

          {response.analysis?.fish_distribution_disclaimer && (
            <div className="notice-box notice-warning" style={{ marginTop: '16px' }}>
              <div>
                <strong>Fisheries Grounding Guarantee:</strong>
                <p style={{ marginTop: '4px' }}>{response.analysis.fish_distribution_disclaimer}</p>
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

          <JsonViewer data={response} title="Fishing Zone Agent Response Payload" />
        </div>
      )}
    </div>
  );
}
