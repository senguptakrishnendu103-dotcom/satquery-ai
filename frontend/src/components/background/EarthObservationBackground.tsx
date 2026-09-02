import React from 'react';

export const EarthObservationBackground: React.FC = () => {
  return (
    <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden select-none transition-opacity duration-500">
      
      {/* 1. Full-Bleed High-Resolution Cosmic Deep Space Galaxy Background Image */}
      <div 
        className="absolute inset-0 bg-cover bg-center bg-no-repeat transition-all duration-500 pointer-events-none"
        style={{
          backgroundImage: `url('/assets/images/galaxy-background.jpg')`,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          backgroundRepeat: 'no-repeat',
          opacity: 0.85
        }}
      />

      {/* 2. Photorealistic Celestial Earth Phase Photo Layer (Left Side) */}
      <div 
        className="absolute top-0 bottom-0 left-0 w-full md:w-3/5 bg-no-repeat bg-left-center bg-contain opacity-75 transition-all duration-500 pointer-events-none"
        style={{
          backgroundImage: `url('/celestial_earth.png')`,
          backgroundPosition: 'left 5% center'
        }}
      />

      {/* 3. Gradient Vignette Overlay for Readability */}
      <div className="absolute inset-0 bg-gradient-to-r from-black/40 via-black/20 to-black/70 pointer-events-none" />

      {/* 4. Scientific Topographic DEM Isolines & Orbital Trajectory Vector SVG Overlay */}
      <svg 
        className="w-full h-full stroke-sat-accent/40 fill-none absolute inset-0 pointer-events-none" 
        xmlns="http://www.w3.org/2000/svg"
        preserveAspectRatio="none"
      >
        <defs>
          <pattern id="cozyGrid" width="60" height="60" patternUnits="userSpaceOnUse">
            <path d="M 60 0 L 0 0 0 60" fill="none" stroke="currentColor" strokeWidth="0.75" strokeOpacity="0.3" strokeDasharray="2 4" />
            <circle cx="0" cy="0" r="1.5" fill="currentColor" fillOpacity="0.4" />
            <circle cx="60" cy="0" r="1.5" fill="currentColor" fillOpacity="0.4" />
          </pattern>
        </defs>

        {/* Global Coordinate Grid */}
        <rect width="100%" height="100%" fill="url(#cozyGrid)" />

        {/* Topographic Terrain Elevation Contour Lines */}
        <g strokeWidth="1" strokeOpacity="0.4" strokeDasharray="6 3">
          <path d="M -100 150 Q 200 80, 500 220 T 1100 180 T 1800 280" />
          <path d="M -100 450 Q 350 320, 800 520 T 1500 420 T 2000 580" strokeWidth="1.5" strokeOpacity="0.5" />
          <path d="M -100 700 Q 400 600, 950 780 T 1600 680 T 2100 820" />
        </g>

        {/* Orbital Trajectory Vector Arcs */}
        <g stroke="var(--color-sat-accent)" strokeWidth="1.25" strokeOpacity="0.5" strokeDasharray="12 6">
          <path d="M -200 900 C 400 100, 1200 50, 2000 700" />
          <path d="M -200 100 C 600 800, 1400 750, 2000 200" />
        </g>

        {/* Latitude & Longitude Degree Tickers */}
        <g className="font-mono text-[9px] fill-sat-accent stroke-none opacity-70">
          <text x="40" y="80">LAT 45.0000° N</text>
          <text x="40" y="320">LAT 30.0000° N</text>
          <text x="40" y="560">LAT 15.0000° N</text>

          <text x="500" y="30">LON 30.0000° E</text>
          <text x="1000" y="30">LON 60.0000° E</text>
          <text x="1500" y="30">LON 90.0000° E</text>
        </g>
      </svg>

    </div>
  );
};
