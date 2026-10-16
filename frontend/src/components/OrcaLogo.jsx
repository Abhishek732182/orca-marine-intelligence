import React from 'react';

/**
 * Custom ORCA Marine Intelligence Vector Emblem
 * Recreates the circular emblem from the design reference:
 * An orca whale breaching dynamically through turquoise & cyan ocean waves inside a circular badge.
 */
export function OrcaCircularEmblem({ className = 'w-10 h-10' }) {
  return (
    <svg
      className={className}
      viewBox="0 0 160 160"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <defs>
        {/* Sky / Deep Ocean Inner Radial Gradient */}
        <radialGradient id="oceanBgGrad" cx="50%" cy="40%" r="60%">
          <stop offset="0%" stopColor="#1e4e8c" />
          <stop offset="55%" stopColor="#0e2f5d" />
          <stop offset="100%" stopColor="#061834" />
        </radialGradient>

        {/* Primary Crest Wave (Cyan to Light Seafoam) */}
        <linearGradient id="waveCyanGrad" x1="20" y1="120" x2="140" y2="80" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#0284c7" />
          <stop offset="50%" stopColor="#06b6d4" />
          <stop offset="100%" stopColor="#38bdf8" />
        </linearGradient>

        {/* Secondary Foam Wave (Light Sky to White) */}
        <linearGradient id="waveFoamGrad" x1="40" y1="140" x2="130" y2="90" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#0891b2" />
          <stop offset="60%" stopColor="#38bdf8" />
          <stop offset="100%" stopColor="#e0f2fe" />
        </linearGradient>

        {/* Orca Whale Body (Glossy Deep Oceanic Black) */}
        <linearGradient id="orcaSkinGrad" x1="60" y1="20" x2="120" y2="90" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#0b1b36" />
          <stop offset="60%" stopColor="#051124" />
          <stop offset="100%" stopColor="#020914" />
        </linearGradient>

        {/* Outer Circular Glow Ring */}
        <linearGradient id="ringGrad" x1="0" y1="0" x2="160" y2="160" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#38bdf8" />
          <stop offset="50%" stopColor="#0284c7" />
          <stop offset="100%" stopColor="#0891b2" />
        </linearGradient>
      </defs>

      {/* Outer Glow Halo */}
      <circle cx="80" cy="80" r="76" stroke="url(#ringGrad)" strokeWidth="3" opacity="0.85" />
      <circle cx="80" cy="80" r="74" fill="url(#oceanBgGrad)" />

      {/* Background Water Swirl Arc */}
      <path
        d="M26 95 C38 60 75 42 110 50 C125 54 135 63 138 72 C134 62 120 52 105 48 C70 38 35 56 22 92 C19 101 22 103 26 95 Z"
        fill="#38bdf8"
        opacity="0.55"
      />

      {/* ================= BREACHING ORCA BODY ================= */}
      <g id="orca-whale">
        {/* Main Body Arch (breaching upward towards top right) */}
        <path
          d="M 52 118
             C 50 102 58 78 72 58
             C 84 41 101 32 120 30
             C 126 29 135 34 138 40
             C 134 46 126 49 119 50
             C 107 52 98 57 91 66
             C 82 78 79 92 84 106
             C 82 112 76 116 70 119
             C 63 122 55 124 52 118 Z"
          fill="url(#orcaSkinGrad)"
        />

        {/* Dorsal Fin (Iconic tall curved fin on back) */}
        <path
          d="M 88 42
             C 91 30 94 18 97 12
             C 99 19 103 30 108 34
             C 101 36 94 38 88 42 Z"
          fill="#051124"
        />

        {/* Tail Flukes (Lower left) */}
        <path
          d="M 56 114
             C 47 117 38 123 32 131
             C 38 126 46 124 51 126
             C 48 132 46 139 47 144
             C 52 138 56 128 60 120
             Z"
          fill="#051124"
        />

        {/* Pectoral Fin (Side flipper extending into splash) */}
        <path
          d="M 82 78
             C 86 86 91 97 93 105
             C 89 104 84 97 81 90
             C 79 85 80 81 82 78 Z"
          fill="#0b1b36"
        />

        {/* Orca Distinctive White Belly Patch & Under-Jaw */}
        <path
          d="M 120 42
             C 114 44 104 46 96 52
             C 88 59 84 69 82 80
             C 85 74 91 68 99 63
             C 108 58 116 54 125 50
             C 127 46 124 43 120 42 Z"
          fill="#ffffff"
        />

        {/* Orca Distinctive White Eye Oval Patch */}
        <ellipse
          cx="114"
          cy="38"
          rx="6"
          ry="3"
          transform="rotate(-20 114 38)"
          fill="#ffffff"
        />
        <circle cx="118" cy="38" r="1.5" fill="#051124" />
      </g>

      {/* ================= SPLASHING OCEAN WAVES ================= */}
      {/* Dynamic Base Wave Swirl */}
      <path
        d="M 18 105
           C 28 85 45 74 65 72
           C 78 71 88 78 96 87
           C 105 97 118 102 132 98
           C 142 95 148 88 152 80
           C 147 96 136 109 120 116
           C 102 124 82 120 68 110
           C 54 99 40 98 28 108
           C 22 113 18 112 18 105 Z"
        fill="url(#waveCyanGrad)"
      />

      {/* Foreground Foaming Crest Splash */}
      <path
        d="M 28 118
           C 42 102 60 96 78 98
           C 92 100 104 108 118 108
           C 130 108 140 102 146 94
           C 140 110 126 124 108 128
           C 90 132 72 126 56 117
           C 44 110 35 112 28 118 Z"
        fill="url(#waveFoamGrad)"
        opacity="0.95"
      />

      {/* Stylized White Foam Highlights & Water Spray */}
      <path
        d="M 72 73 C 80 73 88 78 94 85 C 86 81 78 80 72 82 C 68 76 70 73 72 73 Z"
        fill="#ffffff"
      />
      <circle cx="98" cy="74" r="2.5" fill="#ffffff" opacity="0.9" />
      <circle cx="106" cy="68" r="1.8" fill="#e0f2fe" opacity="0.85" />
      <circle cx="124" cy="76" r="2.2" fill="#ffffff" opacity="0.9" />
      <circle cx="134" cy="85" r="1.5" fill="#38bdf8" opacity="0.8" />
      <circle cx="48" cy="84" r="2" fill="#ffffff" opacity="0.8" />
      <circle cx="40" cy="94" r="1.5" fill="#e0f2fe" opacity="0.75" />

      {/* Bottom Curve Wave Curl */}
      <path
        d="M 40 134
           C 56 122 75 120 94 125
           C 112 130 128 128 142 120
           C 132 134 116 142 98 143
           C 78 144 58 139 40 134 Z"
        fill="#0284c7"
      />
    </svg>
  );
}

/**
 * Main ORCA Logo Component
 * Supports:
 * - 'hero': Centered large circular emblem + bold letter-spaced ORCA + Marine Intelligence
 * - 'sidebar': Horizontal lockup for the dark navy sidebar
 * - 'icon': Standalone circular badge
 * - 'horizontal': Light-background lockup
 */
export default function OrcaLogo({ variant = 'horizontal', className = '' }) {
  if (variant === 'icon') {
    return <OrcaCircularEmblem className={className || 'w-9 h-9'} />;
  }

  // Large Hero for Welcome Screen
  if (variant === 'hero' || variant === 'large') {
    return (
      <div className={`flex flex-col items-center text-center ${className}`}>
        {/* Large Circular Emblem matching reference image */}
        <div className="relative mb-3 group">
          <div className="w-28 h-28 sm:w-32 sm:h-32 transition-transform duration-300 group-hover:scale-105 drop-shadow-xl">
            <OrcaCircularEmblem className="w-full h-full" />
          </div>
        </div>

        {/* Bold Spaced Wordmark */}
        <h1 className="text-3xl sm:text-4xl font-extrabold tracking-[0.25em] text-[#091b33] uppercase font-sans">
          O R C A
        </h1>

        {/* Refined Subtitle */}
        <p className="text-xs sm:text-sm font-semibold tracking-[0.2em] text-slate-500 uppercase mt-1">
          Marine Intelligence
        </p>
      </div>
    );
  }

  // Sidebar Header Lockup (Dark Navy Background)
  if (variant === 'sidebar') {
    return (
      <div className={`flex items-center gap-3 ${className}`}>
        <div className="w-9 h-9 shrink-0 drop-shadow-md">
          <OrcaCircularEmblem className="w-full h-full" />
        </div>
        <div className="min-w-0">
          <div className="text-base font-extrabold tracking-wider text-white leading-tight font-sans">
            ORCA
          </div>
          <div className="text-[11px] font-medium tracking-wide text-sky-300 leading-none mt-0.5 truncate">
            Marine Intelligence
          </div>
        </div>
      </div>
    );
  }

  // Default Horizontal Lockup for Light Backgrounds
  return (
    <div className={`flex items-center gap-2.5 ${className}`}>
      <div className="w-8 h-8 shrink-0 drop-shadow-sm">
        <OrcaCircularEmblem className="w-full h-full" />
      </div>
      <div className="min-w-0">
        <div className="text-sm font-extrabold tracking-wider text-slate-900 leading-tight">
          ORCA
        </div>
        <div className="text-[11px] font-medium tracking-tight text-slate-500 leading-none mt-0.5 truncate">
          Marine Intelligence
        </div>
      </div>
    </div>
  );
}
