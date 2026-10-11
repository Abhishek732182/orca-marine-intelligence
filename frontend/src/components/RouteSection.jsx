import React, { useState } from 'react';
import { analyzeRoute } from '../services/orcaApi';
import JsonViewer from './JsonViewer';

export default function RouteSection() {
  const [formData, setFormData] = useState({
    origin_name: 'Mumbai Port',
    origin_latitude: '18.9388',
    origin_longitude: '72.8354',
    destination_name: 'Goa Mormugao Port',
    destination_latitude: '15.4989',
    destination_longitude: '73.8278',
    vessel_speed_knots: 12.0,
    waypoints: [
      { name: 'Ratnagiri Offing', latitude: '17.0000', longitude: '73.0000' },
    ],
  });
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState(null);
  const [error, setError] = useState(null);

  const addWaypoint = () => {
    setFormData(prev => ({
      ...prev,
      waypoints: [...prev.waypoints, { name: `Waypoint ${prev.waypoints.length + 1}`, latitude: '', longitude: '' }],
    }));
  };

  const removeWaypoint = (index) => {
    setFormData(prev => ({
      ...prev,
      waypoints: prev.waypoints.filter((_, i) => i !== index),
    }));
  };

  const updateWaypoint = (index, field, value) => {
    setFormData(prev => {
      const nextWps = [...prev.waypoints];
      nextWps[index][field] = value;
      return { ...prev, waypoints: nextWps };
    });
  };

  const applyPreset = (origin, dest, wps = [], speed = 12.0) => {
    setFormData({
      origin_name: origin.name,
      origin_latitude: origin.lat,
      origin_longitude: origin.lon,
      destination_name: dest.name,
      destination_latitude: dest.lat,
      destination_longitude: dest.lon,
      vessel_speed_knots: speed,
      waypoints: wps,
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResponse(null);

    const payload = {
      origin_name: formData.origin_name,
      origin_latitude: parseFloat(formData.origin_latitude),
      origin_longitude: parseFloat(formData.origin_longitude),
      destination_name: formData.destination_name,
      destination_latitude: parseFloat(formData.destination_latitude),
      destination_longitude: parseFloat(formData.destination_longitude),
      vessel_speed_knots: parseFloat(formData.vessel_speed_knots) || 12.0,
      waypoints: formData.waypoints
        .filter(wp => wp.latitude !== '' && wp.longitude !== '')
        .map(wp => ({
          name: wp.name,
          latitude: parseFloat(wp.latitude),
          longitude: parseFloat(wp.longitude),
        })),
    };

    try {
      const data = await analyzeRoute(payload);
      setResponse(data);
    } catch (err) {
      setError(err.message || 'Route Agent request failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-panel" style={{ padding: '28px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h2 style={{ fontSize: '1.45rem', color: 'var(--text-main)' }}>4. Route Agent</h2>
            <span className="badge badge-cyan">POST /api/agents/route/analyze</span>
          </div>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.86rem', marginTop: '4px' }}>
            Geodesic Great-Circle distance, leg bearings, waypoint interpolation, and transit calculation.
          </p>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '20px' }}>
        <span style={{ fontSize: '0.78rem', color: 'var(--text-dim)', alignSelf: 'center' }}>Presets:</span>
        <button
          type="button"
          className="btn-preset"
          onClick={() => applyPreset(
            { name: 'Mumbai Port', lat: '18.9388', lon: '72.8354' },
            { name: 'Goa Mormugao', lat: '15.4989', lon: '73.8278' },
            [{ name: 'Ratnagiri Offing', latitude: '17.0000', longitude: '73.0000' }]
          )}
        >
          Mumbai → Goa (via Ratnagiri)
        </button>
        <button
          type="button"
          className="btn-preset"
          onClick={() => applyPreset(
            { name: 'Kochi Port', lat: '9.965', lon: '76.242' },
            { name: 'Kavaratti Island', lat: '10.566', lon: '72.641' },
            []
          )}
        >
          Kochi → Kavaratti (Direct)
        </button>
      </div>

      <form onSubmit={handleSubmit}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '20px', marginBottom: '18px' }}>
          {/* Origin */}
          <div style={{ background: 'var(--bg-surface)', padding: '16px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-light)' }}>
            <h4 style={{ fontSize: '0.85rem', color: 'var(--primary-blue)', marginBottom: '12px' }}>Origin Waypoint</h4>
            <div style={{ marginBottom: '10px' }}>
              <label>Name</label>
              <input
                type="text"
                value={formData.origin_name}
                onChange={e => setFormData({ ...formData, origin_name: e.target.value })}
              />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <div>
                <label>Lat</label>
                <input
                  type="number"
                  step="any"
                  required
                  value={formData.origin_latitude}
                  onChange={e => setFormData({ ...formData, origin_latitude: e.target.value })}
                />
              </div>
              <div>
                <label>Lon</label>
                <input
                  type="number"
                  step="any"
                  required
                  value={formData.origin_longitude}
                  onChange={e => setFormData({ ...formData, origin_longitude: e.target.value })}
                />
              </div>
            </div>
          </div>

          {/* Destination */}
          <div style={{ background: 'var(--bg-surface)', padding: '16px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-light)' }}>
            <h4 style={{ fontSize: '0.85rem', color: 'var(--primary-blue)', marginBottom: '12px' }}>Destination Waypoint</h4>
            <div style={{ marginBottom: '10px' }}>
              <label>Name</label>
              <input
                type="text"
                value={formData.destination_name}
                onChange={e => setFormData({ ...formData, destination_name: e.target.value })}
              />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <div>
                <label>Lat</label>
                <input
                  type="number"
                  step="any"
                  required
                  value={formData.destination_latitude}
                  onChange={e => setFormData({ ...formData, destination_latitude: e.target.value })}
                />
              </div>
              <div>
                <label>Lon</label>
                <input
                  type="number"
                  step="any"
                  required
                  value={formData.destination_longitude}
                  onChange={e => setFormData({ ...formData, destination_longitude: e.target.value })}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Waypoints */}
        <div style={{ marginBottom: '18px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <label style={{ margin: 0 }}>Intermediate Waypoints ({formData.waypoints.length})</label>
            <button type="button" onClick={addWaypoint} className="btn-preset" style={{ color: 'var(--cyan)' }}>
              + Add Waypoint
            </button>
          </div>
          {formData.waypoints.map((wp, idx) => (
            <div key={idx} style={{ display: 'grid', gridTemplateColumns: '2fr 1.5fr 1.5fr auto', gap: '8px', alignItems: 'center', marginBottom: '8px' }}>
              <input
                type="text"
                placeholder="Waypoint Label"
                value={wp.name}
                onChange={e => updateWaypoint(idx, 'name', e.target.value)}
              />
              <input
                type="number"
                step="any"
                placeholder="Latitude"
                value={wp.latitude}
                onChange={e => updateWaypoint(idx, 'latitude', e.target.value)}
              />
              <input
                type="number"
                step="any"
                placeholder="Longitude"
                value={wp.longitude}
                onChange={e => updateWaypoint(idx, 'longitude', e.target.value)}
              />
              <button
                type="button"
                onClick={() => removeWaypoint(idx)}
                style={{ background: 'none', border: 'none', color: 'var(--coral)', cursor: 'pointer', fontSize: '1rem', padding: '6px' }}
                title="Remove waypoint"
              >
                ✕
              </button>
            </div>
          ))}
        </div>

        {/* Speed */}
        <div style={{ maxWidth: '240px', marginBottom: '20px' }}>
          <label>Estimated Cruising Speed (Knots)</label>
          <input
            type="number"
            min="1"
            max="60"
            step="0.5"
            value={formData.vessel_speed_knots}
            onChange={e => setFormData({ ...formData, vessel_speed_knots: e.target.value })}
          />
        </div>

        <button type="submit" className="btn btn-primary" disabled={loading}>
          {loading ? <><span className="spinner" /> Calculating Maritime Route...</> : 'Invoke Route Agent'}
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
                {response.location?.origin?.name} → {response.location?.destination?.name}
              </span>
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
              Method: {response.data_source?.calculation_method}
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: '14px', marginBottom: '18px' }}>
            <div className="metric-card">
              <span className="metric-label">Estimated Distance</span>
              <div className="metric-value">
                {response.observations?.total_distance_nm ?? '--'}
                <span className="metric-unit">NM</span>
              </div>
              <span style={{ fontSize: '0.74rem', color: 'var(--amber)' }}>
                Straight-line estimate ({response.observations?.total_distance_km} km)
              </span>
            </div>
            <div className="metric-card">
              <span className="metric-label">Estimated Transit</span>
              <div className="metric-value">
                {response.observations?.estimated_transit_time_hours ?? '--'}
                <span className="metric-unit">hours</span>
              </div>
              <span style={{ fontSize: '0.74rem', color: 'var(--text-dim)' }}>
                @ {response.observations?.vessel_speed_knots} knots (estimate)
              </span>
            </div>
            <div className="metric-card">
              <span className="metric-label">Passage Legs</span>
              <div className="metric-value">
                {response.observations?.leg_count ?? '--'}
              </div>
            </div>
            <div className="metric-card">
              <span className="metric-label">Route Classification</span>
              <div className="metric-value" style={{ fontSize: '1.02rem', color: 'var(--amber)' }}>
                Geodesic Estimate
              </div>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                Not verified navigable
              </span>
            </div>
          </div>

          {response.analysis?.summary && (
            <div className="notice-box notice-info">
              {response.analysis.summary}
            </div>
          )}

          {response.analysis?.navigable_route_disclaimer && (
            <div className="notice-box notice-warning" style={{ marginTop: '12px' }}>
              <div>
                <strong>Navigation Grounding & Disclaimer:</strong>
                <p style={{ marginTop: '4px' }}>{response.analysis.navigable_route_disclaimer}</p>
              </div>
            </div>
          )}

          {response.analysis?.legs && response.analysis.legs.length > 0 && (
            <div style={{ marginTop: '18px' }}>
              <h4 style={{ fontSize: '0.88rem', color: 'var(--text-muted)', marginBottom: '10px' }}>
                Leg Breakdown & Initial Compass Bearings:
              </h4>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem', textAlign: 'left' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border-light)', color: 'var(--text-dim)' }}>
                      <th style={{ padding: '8px' }}>Leg</th>
                      <th style={{ padding: '8px' }}>From</th>
                      <th style={{ padding: '8px' }}>To</th>
                      <th style={{ padding: '8px' }}>Distance (NM)</th>
                      <th style={{ padding: '8px' }}>Distance (km)</th>
                      <th style={{ padding: '8px' }}>Bearing</th>
                    </tr>
                  </thead>
                  <tbody>
                    {response.analysis.legs.map((leg, idx) => (
                      <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                        <td style={{ padding: '8px', color: 'var(--cyan)', fontWeight: 600 }}>#{idx + 1}</td>
                        <td style={{ padding: '8px' }}>{leg.from_name}</td>
                        <td style={{ padding: '8px' }}>{leg.to_name}</td>
                        <td style={{ padding: '8px', fontWeight: 600 }}>{leg.distance_nm} NM</td>
                        <td style={{ padding: '8px', color: 'var(--text-dim)' }}>{leg.distance_km} km</td>
                        <td style={{ padding: '8px', color: 'var(--emerald)', fontWeight: 600 }}>{leg.initial_bearing_deg}°</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {response.warnings && response.warnings.length > 0 && (
            <div className="notice-box notice-warning">
              <div>
                <strong>Navigation Warnings:</strong>
                <ul style={{ paddingLeft: '18px', marginTop: '4px' }}>
                  {response.warnings.map((w, idx) => <li key={idx}>{w}</li>)}
                </ul>
              </div>
            </div>
          )}

          <JsonViewer data={response} title="Route Agent Response Payload" />
        </div>
      )}
    </div>
  );
}
