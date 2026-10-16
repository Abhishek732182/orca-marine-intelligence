import React, { useState, useRef } from 'react';

/**
 * ORCA Interactive Geospatial Nautical Chart & Marine Radar Visualization
 * Renders high-contrast ocean bathymetry, sector markers, geodesic route vectors,
 * and wave height/sea-state hazard heatmaps.
 */

const SECTOR_PRESETS = [
  {
    id: 'goa',
    name: 'Offshore Goa Shelf',
    lat: 15.00,
    lon: 72.00,
    depth: '82m',
    seaState: 'Code 3 (Moderate)',
    waveHeight: '1.42m',
    risk: 'LOW',
    description: 'Active trawling shelf & coastal upwelling corridor',
  },
  {
    id: 'mumbai',
    name: 'Mumbai High Basin',
    lat: 19.42,
    lon: 71.30,
    depth: '75m',
    seaState: 'Code 4 (Rough)',
    waveHeight: '2.10m',
    risk: 'MODERATE',
    description: 'Deepwater offshore installations & commercial shipping channel',
  },
  {
    id: 'lakshadweep',
    name: 'Lakshadweep Pelagic Channel',
    lat: 10.56,
    lon: 72.64,
    depth: '1850m',
    seaState: 'Code 2 (Smooth)',
    waveHeight: '0.85m',
    risk: 'LOW',
    description: 'Pelagic tuna habitat & coral atoll oceanic trench',
  },
  {
    id: 'mannar',
    name: 'Gulf of Mannar Passage',
    lat: 8.80,
    lon: 78.50,
    depth: '22m',
    seaState: 'Code 5 (Very Rough)',
    waveHeight: '3.20m',
    risk: 'HIGH',
    description: 'Narrow bathymetric constriction; seasonal wind hazard envelope',
  },
];

export default function MarineMap({
  selectedCoords = { lat: 15.00, lon: 72.00 },
  onSelectCoords,
  onQueryAgent,
}) {
  const [activePreset, setActivePreset] = useState('goa');
  const [hoverCoords, setHoverCoords] = useState(null);
  const [radarActive, setRadarActive] = useState(true);
  const [showWaveOverlay, setShowWaveOverlay] = useState(true);
  const [showDepthContours, setShowDepthContours] = useState(true);
  const mapSvgRef = useRef(null);

  // Map geographic bounds (Arabian Sea / West Indian Ocean shelf: Lat 6° to 24°N, Lon 67° to 81°E)
  const BOUNDS = {
    minLat: 6.0,
    maxLat: 24.0,
    minLon: 67.0,
    maxLon: 81.0,
  };

  // Convert lat/lon to SVG coordinate space (800 x 500)
  const toSvgX = (lon) => {
    return ((lon - BOUNDS.minLon) / (BOUNDS.maxLon - BOUNDS.minLon)) * 800;
  };

  const toSvgY = (lat) => {
    // Invert Y because latitude increases upward
    return ((BOUNDS.maxLat - lat) / (BOUNDS.maxLat - BOUNDS.minLat)) * 500;
  };

  // Convert SVG click back to lat/lon
  const handleMapClick = (e) => {
    if (!mapSvgRef.current) return;
    const rect = mapSvgRef.current.getBoundingClientRect();
    const clickX = ((e.clientX - rect.left) / rect.width) * 800;
    const clickY = ((e.clientY - rect.top) / rect.height) * 500;

    const clickedLon = BOUNDS.minLon + (clickX / 800) * (BOUNDS.maxLon - BOUNDS.minLon);
    const clickedLat = BOUNDS.maxLat - (clickY / 500) * (BOUNDS.maxLat - BOUNDS.minLat);

    const formatted = {
      lat: Number(clickedLat.toFixed(2)),
      lon: Number(clickedLon.toFixed(2)),
      sector: `Offshore Vector (${clickedLat.toFixed(2)}°N, ${clickedLon.toFixed(2)}°E)`,
    };

    setActivePreset(null);
    if (onSelectCoords) {
      onSelectCoords(formatted);
    }
  };

  const handleMouseMove = (e) => {
    if (!mapSvgRef.current) return;
    const rect = mapSvgRef.current.getBoundingClientRect();
    const clickX = ((e.clientX - rect.left) / rect.width) * 800;
    const clickY = ((e.clientY - rect.top) / rect.height) * 500;

    const currentLon = BOUNDS.minLon + (clickX / 800) * (BOUNDS.maxLon - BOUNDS.minLon);
    const currentLat = BOUNDS.maxLat - (clickY / 500) * (BOUNDS.maxLat - BOUNDS.minLat);

    setHoverCoords({
      lat: currentLat.toFixed(2),
      lon: currentLon.toFixed(2),
    });
  };

  const handleSelectPreset = (preset) => {
    setActivePreset(preset.id);
    if (onSelectCoords) {
      onSelectCoords({
        lat: preset.lat,
        lon: preset.lon,
        sector: preset.name,
      });
    }
  };

  const currentX = toSvgX(selectedCoords.lon || 72.0);
  const currentY = toSvgY(selectedCoords.lat || 15.0);

  return (
    <div
      className="orca-card"
      style={{
        background: 'linear-gradient(180deg, #07152b 0%, #040c1a 100%)',
        border: '1px solid rgba(14, 165, 233, 0.25)',
        color: '#f8fafc',
        overflow: 'hidden',
        boxShadow: '0 8px 32px rgba(2, 6, 23, 0.5)',
      }}
    >
      {/* Map Control Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '16px 20px',
          borderBottom: '1px solid rgba(14, 165, 233, 0.15)',
          background: 'rgba(10, 25, 47, 0.7)',
          backdropFilter: 'blur(8px)',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '1.4rem' }}>🧭</span>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#38bdf8', margin: 0 }}>
                ORCA Oceanographic Geospatial Visualizer
              </h3>
              <span className="orca-badge badge-cyan" style={{ fontSize: '0.65rem', padding: '2px 8px' }}>
                WGS-84 BATHYMETRIC
              </span>
            </div>
            <p style={{ fontSize: '0.74rem', color: '#94a3b8', margin: 0 }}>
              Live Open-Meteo & ECMWF marine forecast grid • Arabian Sea & Coastal Shelf
            </p>
          </div>
        </div>

        {/* Dynamic Telemetry Coordinates Readout */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div
            style={{
              fontFamily: 'monospace',
              fontSize: '0.78rem',
              background: 'rgba(3, 105, 161, 0.2)',
              border: '1px solid rgba(56, 189, 248, 0.3)',
              padding: '6px 12px',
              borderRadius: '6px',
              color: '#38bdf8',
            }}
          >
            TARGET: {selectedCoords.lat?.toFixed ? selectedCoords.lat.toFixed(2) : selectedCoords.lat}°N,{' '}
            {selectedCoords.lon?.toFixed ? selectedCoords.lon.toFixed(2) : selectedCoords.lon}°E
            {hoverCoords && (
              <span style={{ color: '#94a3b8', marginLeft: '10px' }}>
                CURSOR: {hoverCoords.lat}°N, {hoverCoords.lon}°E
              </span>
            )}
          </div>

          <div style={{ display: 'flex', gap: '6px' }}>
            <button
              type="button"
              className={`orca-btn orca-btn-sm ${showWaveOverlay ? 'orca-btn-primary' : 'orca-btn-secondary'}`}
              style={{ fontSize: '0.72rem', padding: '4px 10px' }}
              onClick={() => setShowWaveOverlay(!showWaveOverlay)}
            >
              🌊 Waves Overlay
            </button>
            <button
              type="button"
              className={`orca-btn orca-btn-sm ${showDepthContours ? 'orca-btn-primary' : 'orca-btn-secondary'}`}
              style={{ fontSize: '0.72rem', padding: '4px 10px' }}
              onClick={() => setShowDepthContours(!showDepthContours)}
            >
              📐 Contours
            </button>
            <button
              type="button"
              className={`orca-btn orca-btn-sm ${radarActive ? 'orca-btn-primary' : 'orca-btn-secondary'}`}
              style={{ fontSize: '0.72rem', padding: '4px 10px' }}
              onClick={() => setRadarActive(!radarActive)}
            >
              📡 Sweep Radar
            </button>
          </div>
        </div>
      </div>

      {/* Preset Sector Bar */}
      <div
        style={{
          display: 'flex',
          gap: '8px',
          padding: '10px 20px',
          background: 'rgba(5, 13, 26, 0.85)',
          borderBottom: '1px solid rgba(14, 165, 233, 0.1)',
          overflowX: 'auto',
          alignItems: 'center',
        }}
      >
        <span style={{ fontSize: '0.74rem', color: '#64748b', fontWeight: 600 }}>Quick Maritime Presets:</span>
        {SECTOR_PRESETS.map((preset) => (
          <button
            key={preset.id}
            type="button"
            onClick={() => handleSelectPreset(preset)}
            style={{
              background: activePreset === preset.id ? 'rgba(14, 165, 233, 0.25)' : 'rgba(15, 43, 72, 0.4)',
              border: `1px solid ${activePreset === preset.id ? '#0ea5e9' : 'rgba(14, 165, 233, 0.2)'}`,
              color: activePreset === preset.id ? '#38bdf8' : '#cbd5e1',
              padding: '4px 10px',
              borderRadius: '20px',
              fontSize: '0.74rem',
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              transition: 'all 0.2s ease',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <span>{preset.name}</span>
            <span
              style={{
                fontSize: '0.65rem',
                color: preset.risk === 'HIGH' ? '#f87171' : preset.risk === 'MODERATE' ? '#fbbf24' : '#34d399',
              }}
            >
              ({preset.waveHeight})
            </span>
          </button>
        ))}
      </div>

      {/* Interactive SVG Chart Container */}
      <div
        style={{
          position: 'relative',
          width: '100%',
          height: '420px',
          background: 'radial-gradient(circle at 50% 50%, #0a2244 0%, #040d1c 85%)',
          cursor: 'crosshair',
          overflow: 'hidden',
        }}
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setHoverCoords(null)}
      >
        <svg
          ref={mapSvgRef}
          viewBox="0 0 800 500"
          style={{ width: '100%', height: '100%', display: 'block' }}
          onClick={handleMapClick}
        >
          <defs>
            {/* Grid Pattern */}
            <pattern id="nautical-grid" width="50" height="50" patternUnits="userSpaceOnUse">
              <path d="M 50 0 L 0 0 0 50" fill="none" stroke="rgba(56, 189, 248, 0.08)" strokeWidth="0.8" />
            </pattern>

            {/* Cyan Radar Glow */}
            <radialGradient id="target-glow" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.8" />
              <stop offset="60%" stopColor="#0ea5e9" stopOpacity="0.3" />
              <stop offset="100%" stopColor="#0284c7" stopOpacity="0" />
            </radialGradient>

            {/* Wave hazard gradient */}
            <linearGradient id="wave-hazard-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="rgba(244, 63, 94, 0.15)" />
              <stop offset="50%" stopColor="rgba(245, 158, 11, 0.1)" />
              <stop offset="100%" stopColor="rgba(16, 185, 129, 0.08)" />
            </linearGradient>
          </defs>

          {/* Background Grid */}
          <rect width="800" height="500" fill="url(#nautical-grid)" />

          {/* Bathymetric Depth Contours */}
          {showDepthContours && (
            <g opacity="0.6">
              {/* 50m Coastal shelf line */}
              <path
                d="M 580 0 Q 560 120 540 220 T 620 380 Q 640 450 670 500"
                fill="none"
                stroke="rgba(14, 165, 233, 0.25)"
                strokeWidth="1.2"
                strokeDasharray="4,4"
              />
              <text x="545" y="240" fill="rgba(56, 189, 248, 0.4)" fontSize="9" fontFamily="monospace">
                -50m isobath
              </text>

              {/* 200m Continental shelf break */}
              <path
                d="M 440 0 Q 420 110 390 200 T 460 360 Q 500 440 530 500"
                fill="none"
                stroke="rgba(6, 182, 212, 0.35)"
                strokeWidth="1.5"
              />
              <text x="400" y="215" fill="rgba(6, 182, 212, 0.6)" fontSize="9" fontFamily="monospace">
                -200m shelf break
              </text>

              {/* 1000m Abyssal plain drop-off */}
              <path
                d="M 300 0 Q 280 130 250 230 T 320 380 Q 360 450 390 500"
                fill="none"
                stroke="rgba(3, 105, 161, 0.4)"
                strokeWidth="1.2"
              />
              <text x="260" y="245" fill="rgba(3, 105, 161, 0.6)" fontSize="9" fontFamily="monospace">
                -1000m abyssal zone
              </text>
            </g>
          )}

          {/* Wave Height Spectral Field (Heatmap simulation) */}
          {showWaveOverlay && (
            <g opacity="0.45">
              {/* Moderate wave field (Goa & Central Shelf) */}
              <ellipse cx="420" cy="250" rx="180" ry="120" fill="url(#wave-hazard-gradient)" />
              {/* High wave hazard region (South offshore) */}
              <circle cx="560" cy="400" r="85" fill="rgba(239, 68, 68, 0.12)" stroke="rgba(239, 68, 68, 0.3)" strokeDasharray="3,3" />
              <text x="510" y="405" fill="#fca5a5" fontSize="10" fontFamily="monospace">
                ⚠️ Swell Collision &gt; 3.0m
              </text>
            </g>
          )}

          {/* India Coastline Silhouette Approximation (Western Seaboard) */}
          <path
            d="M 680 0 L 670 40 L 640 100 L 630 160 L 620 220 L 650 300 L 680 380 L 730 460 L 760 500 L 800 500 L 800 0 Z"
            fill="rgba(15, 33, 64, 0.7)"
            stroke="rgba(56, 189, 248, 0.45)"
            strokeWidth="1.8"
          />

          {/* Major Coastal Landmark Labels */}
          <g fontSize="10" fontFamily="sans-serif" fill="#94a3b8">
            <text x="650" y="115">Mumbai</text>
            <circle cx="640" cy="112" r="3" fill="#38bdf8" />

            <text x="635" y="225">Goa (Mormugao)</text>
            <circle cx="625" cy="222" r="3" fill="#38bdf8" />

            <text x="665" y="360">Mangalore</text>
            <circle cx="655" cy="358" r="3" fill="#38bdf8" />

            <text x="695" y="440">Kochi</text>
            <circle cx="685" cy="438" r="3" fill="#38bdf8" />
          </g>

          {/* Sector Preset Markers */}
          {SECTOR_PRESETS.map((preset) => {
            const px = toSvgX(preset.lon);
            const py = toSvgY(preset.lat);
            const isSelected = activePreset === preset.id;

            return (
              <g
                key={preset.id}
                style={{ cursor: 'pointer' }}
                onClick={(e) => {
                  e.stopPropagation();
                  handleSelectPreset(preset);
                }}
              >
                <circle
                  cx={px}
                  cy={py}
                  r={isSelected ? 10 : 6}
                  fill={isSelected ? '#0ea5e9' : 'rgba(56, 189, 248, 0.4)'}
                  stroke="#ffffff"
                  strokeWidth={isSelected ? 2 : 1}
                />
                {isSelected && (
                  <circle
                    cx={px}
                    cy={py}
                    r="18"
                    fill="none"
                    stroke="#38bdf8"
                    strokeWidth="1.5"
                    strokeDasharray="2,2"
                  >
                    <animate attributeName="r" values="10;26;10" dur="3s" repeatCount="indefinite" />
                    <animate attributeName="opacity" values="0.8;0.2;0.8" dur="3s" repeatCount="indefinite" />
                  </circle>
                )}
                <text
                  x={px + 12}
                  y={py + 4}
                  fontSize="11"
                  fontWeight={isSelected ? 'bold' : 'normal'}
                  fill={isSelected ? '#38bdf8' : '#e2e8f0'}
                  fontFamily="sans-serif"
                >
                  {preset.name}
                </text>
              </g>
            );
          })}

          {/* Active Target Crosshair */}
          <g>
            <line x1={currentX - 25} y1={currentY} x2={currentX + 25} y2={currentY} stroke="#38bdf8" strokeWidth="1.5" />
            <line x1={currentX} y1={currentY - 25} x2={currentX} y2={currentY + 25} stroke="#38bdf8" strokeWidth="1.5" />
            <circle cx={currentX} cy={currentY} r="14" fill="url(#target-glow)" />
            <circle cx={currentX} cy={currentY} r="7" fill="#0284c7" stroke="#ffffff" strokeWidth="2" />
            <circle cx={currentX} cy={currentY} r="24" fill="none" stroke="#38bdf8" strokeWidth="1" strokeDasharray="3,3" />
          </g>

          {/* Great-Circle Route Vector Line (if waypoints provided or Mumbai -> Target) */}
          <g>
            <line
              x1={toSvgX(72.83)}
              y1={toSvgY(18.93)}
              x2={currentX}
              y2={currentY}
              stroke="#00f2fe"
              strokeWidth="2.5"
              strokeDasharray="6,4"
            >
              <animate attributeName="stroke-dashoffset" values="20;0" dur="1.5s" repeatCount="indefinite" />
            </line>

            {/* Geodesic midpoint label */}
            <rect
              x={(toSvgX(72.83) + currentX) / 2 - 45}
              y={(toSvgY(18.93) + currentY) / 2 - 12}
              width="90"
              height="20"
              rx="4"
              fill="rgba(5, 13, 26, 0.85)"
              stroke="#00f2fe"
              strokeWidth="1"
            />
            <text
              x={(toSvgX(72.83) + currentX) / 2}
              y={(toSvgY(18.93) + currentY) / 2 + 2}
              textAnchor="middle"
              fill="#00f2fe"
              fontSize="9.5"
              fontFamily="monospace"
              fontWeight="bold"
            >
              GREAT CIRCLE
            </text>
          </g>

          {/* Sweeping Radar Scanner Line */}
          {radarActive && (
            <g>
              <line x1={currentX} y1={currentY} x2={currentX + 130} y2={currentY - 80} stroke="rgba(56, 189, 248, 0.6)" strokeWidth="1.5">
                <animateTransform
                  attributeName="transform"
                  type="rotate"
                  from={`0 ${currentX} ${currentY}`}
                  to={`360 ${currentX} ${currentY}`}
                  dur="6s"
                  repeatCount="indefinite"
                />
              </line>
            </g>
          )}
        </svg>

        {/* Map Legend Overlay */}
        <div
          style={{
            position: 'absolute',
            bottom: '12px',
            left: '14px',
            background: 'rgba(5, 13, 26, 0.85)',
            border: '1px solid rgba(14, 165, 233, 0.25)',
            borderRadius: '8px',
            padding: '8px 14px',
            fontSize: '0.72rem',
            color: '#cbd5e1',
            backdropFilter: 'blur(6px)',
            display: 'flex',
            flexDirection: 'column',
            gap: '4px',
            pointerEvents: 'none',
          }}
        >
          <div style={{ fontWeight: 'bold', color: '#38bdf8', marginBottom: '2px' }}>
            NAUTICAL CHART TELEMETRY
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ display: 'inline-block', width: 10, height: 10, background: '#38bdf8', borderRadius: '50%' }} />
            <span>Target Observation Point</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ display: 'inline-block', width: 14, height: 2, background: '#00f2fe' }} />
            <span>Geodesic Transit Vector (Great Circle)</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ display: 'inline-block', width: 14, height: 2, borderBottom: '1px dashed #38bdf8' }} />
            <span>Bathymetric Depth Isobath</span>
          </div>
        </div>

        {/* Action Prompt */}
        <div
          style={{
            position: 'absolute',
            top: '12px',
            right: '14px',
            background: 'rgba(5, 13, 26, 0.9)',
            border: '1px solid rgba(14, 165, 233, 0.3)',
            borderRadius: '8px',
            padding: '10px 14px',
            maxWidth: '220px',
            backdropFilter: 'blur(8px)',
          }}
        >
          <div style={{ fontSize: '0.78rem', fontWeight: 600, color: '#38bdf8', marginBottom: '4px' }}>
            📍 Location-Grounded Query
          </div>
          <p style={{ fontSize: '0.72rem', color: '#94a3b8', margin: '0 0 8px 0', lineHeight: 1.35 }}>
            Click anywhere on the maritime shelf to pin coordinates and analyze with specialist agents.
          </p>
          {onQueryAgent && (
            <button
              type="button"
              className="orca-btn orca-btn-primary"
              style={{ width: '100%', fontSize: '0.74rem', padding: '6px 10px' }}
              onClick={() => onQueryAgent(selectedCoords)}
            >
              Query All Agents for Coordinates ➜
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
