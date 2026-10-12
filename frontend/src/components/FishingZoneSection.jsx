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

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '14px', marginBottom: '18px' }}>
            <div className="metric-card">
              <span className="metric-label">Vessel Operability</span>
              <div className="metric-value" style={{
                fontSize: '1.15rem',
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
              <span className="metric-label">Observed SST</span>
              <div className="metric-value">
                {response.observations?.sea_surface_temperature_c ?? response.analysis?.environmental_habitat_indicators?.sea_surface_temperature_c ?? '--'}
                <span className="metric-unit">°C</span>
              </div>
            </div>
            <div className="metric-card">
              <span className="metric-label">Thermal Habitat</span>
              <div className="metric-value" style={{
                fontSize: '1.05rem',
                color: response.analysis?.environmental_habitat_indicators?.thermal_suitability === 'OPTIMAL' ? 'var(--emerald)' :
                       response.analysis?.environmental_habitat_indicators?.thermal_suitability === 'TOLERABLE' ? 'var(--amber)' :
                       response.analysis?.environmental_habitat_indicators?.thermal_suitability?.includes('UNFAVORABLE') ? 'var(--coral)' : 'var(--text-main)'
              }}>
                {response.analysis?.environmental_habitat_indicators?.thermal_suitability || 'N/A'}
              </div>
            </div>
            <div className="metric-card">
              <span className="metric-label">Fisheries Telemetry</span>
              <div className="metric-value" style={{
                fontSize: '1.05rem',
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

          {/* Divergence / Conflict Warnings */}
          {response.warnings && response.warnings.some(w => w.includes('CONFLICT / DIVERGENCE')) && (
            <div className="notice-box notice-warning" style={{ borderLeft: '4px solid var(--amber)', marginBottom: '14px' }}>
              <div>
                <strong>Operational vs Habitat Divergence:</strong>
                <ul style={{ paddingLeft: '18px', marginTop: '4px' }}>
                  {response.warnings.filter(w => w.includes('CONFLICT / DIVERGENCE')).map((w, idx) => (
                    <li key={idx} style={{ fontWeight: 500 }}>{w}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {response.analysis?.zone_summary && (
            <div className="notice-box notice-info" style={{ marginBottom: '14px' }}>
              {response.analysis.zone_summary}
            </div>
          )}

          {/* Environmental Habitat & Thermal Evaluation */}
          {response.analysis?.environmental_habitat_indicators && (
            <div style={{ marginTop: '16px', background: 'var(--bg-surface)', padding: '16px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-light)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <h4 style={{ fontSize: '0.86rem', color: 'var(--text-main)', fontWeight: 600 }}>
                  Environmental Habitat Indicators ({response.analysis?.target_species_queried || 'General'})
                </h4>
                {response.analysis?.environmental_habitat_indicators?.thermal_suitability && (
                  <span className={`badge ${
                    response.analysis.environmental_habitat_indicators.thermal_suitability === 'OPTIMAL' ? 'badge-success' :
                    response.analysis.environmental_habitat_indicators.thermal_suitability === 'TOLERABLE' ? 'badge-warning' : 'badge-danger'
                  }`}>
                    {response.analysis.environmental_habitat_indicators.thermal_suitability}
                  </span>
                )}
              </div>
              <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '8px' }}>
                {response.analysis.environmental_habitat_indicators.thermal_evaluation_rationale || 'Thermal evaluation pending.'}
              </p>
              {response.analysis.environmental_habitat_indicators.optimal_range_c && (
                <div style={{ display: 'flex', gap: '16px', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                  <span>Optimal SST: <strong>{response.analysis.environmental_habitat_indicators.optimal_range_c[0]} - {response.analysis.environmental_habitat_indicators.optimal_range_c[1]} °C</strong></span>
                  {response.analysis.environmental_habitat_indicators.tolerable_range_c && (
                    <span>Tolerable SST: <strong>{response.analysis.environmental_habitat_indicators.tolerable_range_c[0]} - {response.analysis.environmental_habitat_indicators.tolerable_range_c[1]} °C</strong></span>
                  )}
                  {response.observations?.chlorophyll_a_mg_m3 !== null && response.observations?.chlorophyll_a_mg_m3 !== undefined && (
                    <span>Chlorophyll-a: <strong>{response.observations.chlorophyll_a_mg_m3} mg/m³</strong></span>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Evidence Provenance & Freshness Table */}
          {response.observations?.evidence_provenance && Object.values(response.observations.evidence_provenance).some(Boolean) && (
            <div style={{ marginTop: '16px', background: '#FFFFFF', padding: '16px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-light)' }}>
              <h4 style={{ fontSize: '0.86rem', color: 'var(--text-main)', marginBottom: '10px', fontWeight: 600 }}>
                Evidence Provenance & Freshness Status:
              </h4>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem', textAlign: 'left' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border-light)', color: 'var(--text-secondary)' }}>
                      <th style={{ padding: '6px 8px' }}>Variable</th>
                      <th style={{ padding: '6px 8px' }}>Source / Sensor</th>
                      <th style={{ padding: '6px 8px' }}>Observed At</th>
                      <th style={{ padding: '6px 8px' }}>Coordinates (Grid vs Requested)</th>
                      <th style={{ padding: '6px 8px' }}>Freshness Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(response.observations.evidence_provenance).map(([key, prov]) => {
                      if (!prov) return null;
                      const freshBadgeClass = prov.freshness_status === 'valid' ? 'badge-success' :
                                              prov.freshness_status === 'stale' ? 'badge-warning' : 'badge-danger';
                      return (
                        <tr key={key} style={{ borderBottom: '1px solid var(--border-light)' }}>
                          <td style={{ padding: '8px', fontWeight: 600, textTransform: 'capitalize' }}>
                            {key.replace(/_/g, ' ')}
                          </td>
                          <td style={{ padding: '8px' }}>
                            <div>{prov.source}</div>
                            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{prov.sensor_description}</div>
                          </td>
                          <td style={{ padding: '8px', fontFamily: 'var(--font-mono)' }}>
                            {prov.observed_at ? new Date(prov.observed_at).toISOString().replace('T', ' ').substring(0, 19) + ' UTC' : 'N/A'}
                          </td>
                          <td style={{ padding: '8px', fontFamily: 'var(--font-mono)', fontSize: '0.72rem' }}>
                            <div>Grid: {prov.latitude?.toFixed(2)}°N, {prov.longitude?.toFixed(2)}°E</div>
                            <div style={{ color: 'var(--text-muted)' }}>Req: {prov.requested_latitude?.toFixed(2)}°N, {prov.requested_longitude?.toFixed(2)}°E</div>
                          </td>
                          <td style={{ padding: '8px' }}>
                            <span className={`badge ${freshBadgeClass}`}>
                              {prov.freshness_status || 'UNKNOWN'}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {response.analysis?.criteria_applied && (
            <div style={{ marginTop: '16px', background: 'var(--bg-surface)', padding: '16px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-light)' }}>
              <h4 style={{ fontSize: '0.86rem', color: 'var(--text-muted)', marginBottom: '8px' }}>
                Evidence & Criteria Applied:
              </h4>
              <ul style={{ paddingLeft: '18px', fontSize: '0.82rem', color: 'var(--text-secondary)', lineHeight: '1.6' }}>
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
