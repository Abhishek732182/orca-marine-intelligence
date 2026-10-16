import React, { useState } from 'react';

/**
 * Lightweight inline nautical radar and route chart.
 * Renders ONLY when real coordinate evidence or route points are returned by backend agents.
 */
export default function InlineMarineMap({ coordinates, routeData }) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!coordinates && !routeData) return null;

  // Extract coordinates safely
  const originLat = coordinates?.origin_lat != null
    ? Number(coordinates.origin_lat)
    : (coordinates?.latitude != null ? Number(coordinates.latitude) : null);
  const originLon = coordinates?.origin_lon != null
    ? Number(coordinates.origin_lon)
    : (coordinates?.longitude != null ? Number(coordinates.longitude) : null);
  const originName = coordinates?.origin_name || coordinates?.location_name || 'Origin';

  const destLat = coordinates?.dest_lat != null
    ? Number(coordinates.dest_lat)
    : (coordinates?.destination_latitude != null ? Number(coordinates.destination_latitude) : null);
  const destLon = coordinates?.dest_lon != null
    ? Number(coordinates.dest_lon)
    : (coordinates?.destination_longitude != null ? Number(coordinates.destination_longitude) : null);
  const destName = coordinates?.dest_name || coordinates?.destination_name || 'Destination';

  const hasRoute = originLat != null && originLon != null && destLat != null && destLon != null;
  const singlePoint = originLat != null && originLon != null;

  if (!singlePoint && !hasRoute) return null;

  // Simple coordinate to SVG projection (covering Indian Ocean / Arabian Sea sector bounds approx 65-85E, 5-25N)
  const projectX = (lon) => {
    const minLon = 65, maxLon = 85;
    const clamped = Math.max(minLon, Math.min(maxLon, lon));
    return ((clamped - minLon) / (maxLon - minLon)) * 360 + 20;
  };

  const projectY = (lat) => {
    const minLat = 5, maxLat = 25;
    const clamped = Math.max(minLat, Math.min(maxLat, lat));
    return 220 - ((clamped - minLat) / (maxLat - minLat)) * 180;
  };

  const x1 = projectX(originLon);
  const y1 = projectY(originLat);
  const x2 = hasRoute ? projectX(destLon) : null;
  const y2 = hasRoute ? projectY(destLat) : null;

  return (
    <div className="my-3 border border-slate-200 rounded-xl bg-slate-50 overflow-hidden shadow-xs">
      <div className="px-3.5 py-2.5 bg-slate-100/70 border-b border-slate-200 flex items-center justify-between text-xs">
        <div className="flex items-center gap-2 font-medium text-slate-800">
          <svg className="w-4 h-4 text-sky-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
          </svg>
          <span>Geospatial Radar & Marine Positioning</span>
        </div>
        <button
          type="button"
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-slate-500 hover:text-slate-800 text-[11px] font-medium transition-colors"
        >
          {isExpanded ? 'Collapse Chart' : 'Expand Chart'}
        </button>
      </div>

      <div className={`p-3 transition-all ${isExpanded ? 'block' : 'hidden sm:block'}`}>
        <div className="relative w-full aspect-2/1 max-h-56 bg-slate-900 rounded-lg overflow-hidden border border-slate-800">
          <svg className="w-full h-full" viewBox="0 0 400 240" fill="none">
            {/* Background Grid */}
            <defs>
              <pattern id="radar-grid" width="20" height="20" patternUnits="userSpaceOnUse">
                <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#1E293B" strokeWidth="0.5" />
              </pattern>
            </defs>
            <rect width="100%" height="100%" fill="url(#radar-grid)" />

            {/* Simulated Coastal Shelf Silhouette Reference */}
            <path
              d="M 330 0 Q 300 80 290 140 T 260 240"
              stroke="#334155"
              strokeWidth="2"
              strokeDasharray="4 4"
              fill="none"
            />
            <text x="310" y="30" fill="#64748B" fontSize="9" fontFamily="sans-serif">Indian Continental Shelf</text>

            {/* Geodesic Route Vector */}
            {hasRoute && (
              <>
                <line
                  x1={x1}
                  y1={y1}
                  x2={x2}
                  y2={y2}
                  stroke="#38BDF8"
                  strokeWidth="2"
                  strokeDasharray="5 3"
                />
                {/* Destination Point */}
                <circle cx={x2} cy={y2} r="5" fill="#38BDF8" />
                <circle cx={x2} cy={y2} r="9" stroke="#38BDF8" strokeWidth="1" opacity="0.6" />
                <text x={x2 + 8} y={y2 + 4} fill="#F8FAFC" fontSize="10" fontWeight="600">
                  {destName} ({destLat.toFixed(1)}°N, {destLon.toFixed(1)}°E)
                </text>
              </>
            )}

            {/* Origin Point */}
            <circle cx={x1} cy={y1} r="5" fill="#34D399" />
            <circle cx={x1} cy={y1} r="9" stroke="#34D399" strokeWidth="1" opacity="0.6" />
            <text x={x1 + 8} y={y1 + 4} fill="#F8FAFC" fontSize="10" fontWeight="600">
              {originName} ({originLat.toFixed(1)}°N, {originLon.toFixed(1)}°E)
            </text>
          </svg>
        </div>

        {/* Disclaimer Note */}
        <div className="mt-2 text-[11px] text-slate-500 leading-normal flex items-start gap-1.5">
          <svg className="w-3.5 h-3.5 text-amber-500 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>
            Geodesic straight-line approximation for situational awareness. Not verified for hydrographic navigability, shallow bathymetry, or marine traffic separation schemes.
          </span>
        </div>
      </div>
    </div>
  );
}
