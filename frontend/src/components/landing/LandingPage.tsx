import React, { useState, useEffect, useRef } from 'react';
import { ArrowRight, Play, Radar, Cpu, Sparkles } from 'lucide-react';
import { SystemWorkflowSection } from './SystemWorkflowSection';

interface LandingPageProps {
  onEnterWorkspace: () => void;
  onViewDemo: () => void;
  workflowRef?: React.RefObject<HTMLDivElement | null>;
}

// Realistic Satellite Observation Telemetry Points for Scientific Instrument Animation
const OBSERVATION_POINTS = [
  {
    id: 'OBS-0421',
    name: 'Coastal Urban & Maritime Basin',
    lat: '25.2048° N',
    lon: '55.2708° E',
    sensor: 'OPTICAL (0.5m/px)',
    status: 'ACQUIRED',
    confidence: '96%',
    delta: '+14.2% Built-up Growth',
    orbit: 'SSO 540KM',
    x: 0.62,
    y: 0.42
  },
  {
    id: 'OBS-0819',
    name: 'Palma De Mallorca Commercial Port',
    lat: '39.5696° N',
    lon: '2.6502° E',
    sensor: 'HIGH-RES RGB',
    status: 'ACQUIRED',
    confidence: '94%',
    delta: '1 Container Vessel Grounded',
    orbit: 'LEO 420KM',
    x: 0.38,
    y: 0.35
  },
  {
    id: 'OBS-1104',
    name: 'Hydrological Basin & Reservoir NDWI',
    lat: '36.8529° N',
    lon: '-75.9780° W',
    sensor: 'MULTISPECTRAL NDWI',
    status: 'ACQUIRED',
    confidence: '98%',
    delta: '-8.4% Surface Area',
    orbit: 'SENTINEL-2',
    x: 0.25,
    y: 0.48
  },
  {
    id: 'OBS-1932',
    name: 'Sentinel-1 SAR All-Weather Inundation',
    lat: '46.8182° N',
    lon: '8.2275° E',
    sensor: 'SAR X-BAND RADAR',
    status: 'ACQUIRED',
    confidence: '91%',
    delta: '18.4 km² Flood Inundation',
    orbit: 'SENTINEL-1 SAR',
    x: 0.48,
    y: 0.28
  }
];

export const LandingPage: React.FC<LandingPageProps> = ({ onEnterWorkspace, onViewDemo, workflowRef }) => {
  // Active Satellite Observation Cycle State
  const [activePointIndex, setActivePointIndex] = useState(0);
  const [orbitAngle, setOrbitAngle] = useState(0);
  const [scanPulse, setScanPulse] = useState(false);
  const [mode, setMode] = useState<'SIMULATION' | 'LIVE_SCAN'>('SIMULATION');
  const [liveCoords, setLiveCoords] = useState({ lat: 39.5696, lon: 2.6502 });

  // Mouse telemetry tracking
  const canvasRef = useRef<HTMLDivElement>(null);
  const [mousePos, setMousePos] = useState({ x: 0.5, y: 0.5 });
  const [isReducedMotion, setIsReducedMotion] = useState(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    setIsReducedMotion(mediaQuery.matches);
    const handler = (e: MediaQueryListEvent) => setIsReducedMotion(e.matches);
    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }, []);

  useEffect(() => {
    if (isReducedMotion) return;

    const speed = mode === 'LIVE_SCAN' ? 1.5 : 0.5;
    const orbitInterval = setInterval(() => {
      setOrbitAngle(prev => (prev + speed) % 360);
    }, 40);

    const scanInterval = setInterval(() => {
      setScanPulse(true);
      setTimeout(() => setScanPulse(false), 1200);
      if (mode === 'SIMULATION') {
        setActivePointIndex(prev => (prev + 1) % OBSERVATION_POINTS.length);
      } else {
        // In Live Scan, subtly update live coordinates
        setLiveCoords(prev => ({
          lat: +(prev.lat + (Math.random() * 0.008 - 0.004)).toFixed(4),
          lon: +(prev.lon + (Math.random() * 0.008 - 0.004)).toFixed(4)
        }));
      }
    }, mode === 'LIVE_SCAN' ? 2500 : 5000);

    return () => {
      clearInterval(orbitInterval);
      clearInterval(scanInterval);
    };
  }, [isReducedMotion, mode]);

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!canvasRef.current) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const x = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    const y = Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height));
    setMousePos({ x, y });
  };

  const currentObs = OBSERVATION_POINTS[activePointIndex];
  const displayLat = mode === 'LIVE_SCAN' ? `${liveCoords.lat}° N` : currentObs.lat;
  const displayLon = mode === 'LIVE_SCAN' ? `${liveCoords.lon}° E` : currentObs.lon;

  return (
    <div className="min-h-[calc(100vh-3.5rem)] flex flex-col justify-between relative bg-transparent text-sat-text selection:bg-sat-accent/20 transition-colors duration-200 overflow-x-hidden">
      
      {/* GIS Grid Patterns */}
      <div 
        className="absolute inset-0 bg-gis-grid opacity-25 pointer-events-none transition-transform duration-500 ease-out z-0"
        style={{
          transform: isReducedMotion ? 'none' : `translate(${(mousePos.x - 0.5) * 12}px, ${(mousePos.y - 0.5) * 12}px)`
        }}
      />
      <div className="absolute inset-0 bg-gis-cross opacity-15 pointer-events-none z-0" />

      {/* Hero Section Container (Left: Celestial Satellite Display / Right: Editorial Typography Layout) */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 md:py-16 w-full grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-16 items-center z-10 flex-grow">
        
        {/* Left Column: Unified Orbital Mission Control Instrument Display */}
        <div className="lg:col-span-6">
          <div
            ref={canvasRef}
            onMouseMove={handleMouseMove}
            className="relative rounded-2xl bg-sat-surface/40 border border-sat-border/60 overflow-hidden select-none cursor-crosshair group hover:border-sat-accent/60 transition-all shadow-2xl backdrop-blur-md flex flex-col justify-between"
          >
            {/* Top Bar Telemetry Header */}
            <div className="flex items-center justify-between font-mono text-[10px] text-sat-dim border-b border-sat-border/50 p-4 pb-3">
              <div className="flex items-center space-x-2">
                <Radar className={`w-4 h-4 ${mode === 'LIVE_SCAN' ? 'text-red-400 animate-pulse' : 'text-sat-accent animate-spin'}`} style={{ animationDuration: mode === 'LIVE_SCAN' ? '1s' : '8s' }} />
                <span className="text-sat-text font-bold uppercase tracking-wider">
                  EARTH OBSERVATION CANVAS
                </span>
              </div>
              <div className="flex items-center space-x-1 p-0.5 bg-black/40 rounded-lg border border-sat-border/40">
                <button
                  onClick={() => setMode('SIMULATION')}
                  className={`px-2.5 py-1 rounded text-[10px] font-bold transition-all ${
                    mode === 'SIMULATION'
                      ? 'bg-sat-accent text-sat-bg shadow-sm'
                      : 'text-sat-dim hover:text-sat-text'
                  }`}
                >
                  SIMULATION
                </button>
                <button
                  onClick={() => setMode('LIVE_SCAN')}
                  className={`px-2.5 py-1 rounded text-[10px] font-bold flex items-center space-x-1 transition-all ${
                    mode === 'LIVE_SCAN'
                      ? 'bg-red-500/90 text-white shadow-sm animate-pulse'
                      : 'text-sat-dim hover:text-sat-text'
                  }`}
                >
                  <span className={`w-1.5 h-1.5 rounded-full ${mode === 'LIVE_SCAN' ? 'bg-white' : 'bg-red-500'}`} />
                  <span>LIVE SCAN</span>
                </button>
              </div>
            </div>

            {/* Central Animated Scientific Globe, Elliptical Orbit & Scanning Pulse */}
            <div className="relative w-full h-[270px] flex items-center justify-center p-2">
              <svg className="w-full h-full max-w-[300px] max-h-[300px]" viewBox="0 0 400 400">
                <defs>
                  <radialGradient id="earthBodyGradient" cx="50%" cy="50%" r="50%">
                    <stop offset="0%" stopColor="var(--color-sat-panel)" stopOpacity="0.95" />
                    <stop offset="70%" stopColor="var(--color-sat-surface)" stopOpacity="0.95" />
                    <stop offset="100%" stopColor="var(--color-sat-bg)" stopOpacity="1" />
                  </radialGradient>
                </defs>

                <circle cx="200" cy="200" r="185" fill="none" stroke="var(--color-sat-border)" strokeWidth="1" strokeDasharray="3 3" />
                
                <ellipse 
                  cx="200" cy="200" rx="170" ry="85" fill="none" stroke={mode === 'LIVE_SCAN' ? '#ef4444' : 'var(--color-sat-accent)'} strokeWidth="1.5" strokeOpacity="0.4" strokeDasharray="8 4"
                  style={{
                    transform: `rotate(-20deg)`,
                    transformOrigin: '200px 200px'
                  }}
                />

                <circle cx="200" cy="200" r="125" fill="url(#earthBodyGradient)" stroke="var(--color-sat-borderLight)" strokeWidth="1.5" />

                <g style={{
                  transform: `rotate(${isReducedMotion ? 0 : orbitAngle * 0.4}deg)`,
                  transformOrigin: '200px 200px'
                }}>
                  <ellipse cx="200" cy="200" rx="125" ry="40" fill="none" stroke="var(--color-sat-border)" strokeWidth="1" />
                  <ellipse cx="200" cy="200" rx="125" ry="85" fill="none" stroke="var(--color-sat-border)" strokeWidth="1" />
                  <ellipse cx="200" cy="200" rx="40" ry="125" fill="none" stroke="var(--color-sat-border)" strokeWidth="1" />
                  <ellipse cx="200" cy="200" rx="85" ry="125" fill="none" stroke="var(--color-sat-border)" strokeWidth="1" />
                </g>

                {(() => {
                  const rad = ((orbitAngle - 20) * Math.PI) / 180;
                  const satX = 200 + 170 * Math.cos(rad);
                  const satY = 200 + 85 * Math.sin(rad);
                  const targetX = 100 + currentObs.x * 200;
                  const targetY = 100 + currentObs.y * 200;

                  return (
                    <g>
                      <line 
                        x1={satX} y1={satY} x2={targetX} y2={targetY} 
                        stroke={mode === 'LIVE_SCAN' ? '#ef4444' : 'var(--color-sat-accent)'} strokeWidth="1" strokeDasharray="3 3" strokeOpacity="0.6" 
                      />

                      <circle cx={satX} cy={satY} r="6" fill={mode === 'LIVE_SCAN' ? '#ef4444' : 'var(--color-sat-accent)'} />
                      <circle cx={satX} cy={satY} r="12" fill="none" stroke={mode === 'LIVE_SCAN' ? '#ef4444' : 'var(--color-sat-accent)'} strokeWidth="1" strokeOpacity="0.8">
                        <animate attributeName="r" values="6;16;6" dur="2s" repeatCount="indefinite" />
                      </circle>
                      <text x={satX + 10} y={satY - 8} fill={mode === 'LIVE_SCAN' ? '#ef4444' : 'var(--color-sat-accent)'} fontSize="9" fontFamily="JetBrains Mono" fontWeight="bold">
                        {mode === 'LIVE_SCAN' ? 'LIVE_SAT_SENTINEL' : 'SAT_01'}
                      </text>
                    </g>
                  );
                })()}

                {(() => {
                  const targetX = 100 + currentObs.x * 200;
                  const targetY = 100 + currentObs.y * 200;

                  return (
                    <g>
                      <rect 
                        x={targetX - 25} y={targetY - 20} width="50" height="40" 
                        fill={mode === 'LIVE_SCAN' ? 'rgba(239, 68, 68, 0.15)' : 'rgba(2, 132, 199, 0.15)'} 
                        stroke={mode === 'LIVE_SCAN' ? '#ef4444' : 'var(--color-sat-change)'} strokeWidth="1.5" strokeDasharray="4 2"
                      />

                      {scanPulse && (
                        <circle cx={targetX} cy={targetY} r="35" fill="none" stroke={mode === 'LIVE_SCAN' ? '#ef4444' : 'var(--color-sat-change)'} strokeWidth="2">
                          <animate attributeName="r" values="10;45" dur="1s" repeatCount="1" />
                          <animate attributeName="opacity" values="1;0" dur="1s" repeatCount="1" />
                        </circle>
                      )}

                      <circle cx={targetX} cy={targetY} r="3" fill={mode === 'LIVE_SCAN' ? '#ef4444' : 'var(--color-sat-change)'} />
                    </g>
                  );
                })()}

                <g style={{
                  transform: `translate(${(mousePos.x - 0.5) * 120}px, ${(mousePos.y - 0.5) * 120}px)`,
                  transition: 'transform 0.05s ease-out'
                }}>
                  <circle cx="200" cy="200" r="18" fill="none" stroke="var(--color-sat-accent)" strokeWidth="1" strokeDasharray="2 2" opacity="0.7" />
                  <line x1="178" y1="200" x2="192" y2="200" stroke="var(--color-sat-accent)" strokeWidth="1.5" />
                  <line x1="208" y1="200" x2="222" y2="200" stroke="var(--color-sat-accent)" strokeWidth="1.5" />
                  <line x1="200" y1="178" x2="200" y2="192" stroke="var(--color-sat-accent)" strokeWidth="1.5" />
                  <line x1="200" y1="208" x2="200" y2="222" stroke="var(--color-sat-accent)" strokeWidth="1.5" />
                </g>
              </svg>

              <div className="absolute top-2 left-2 bg-sat-surface/80 backdrop-blur-md border border-sat-border/50 p-2.5 rounded-md font-mono text-[10px] space-y-1 text-sat-text shadow-lg max-w-[190px]">
                <div className="flex justify-between items-center text-sat-accent font-bold border-b border-sat-border/40 pb-1 mb-1">
                  <span>{mode === 'LIVE_SCAN' ? 'LIVE-PASS' : currentObs.id}</span>
                  <span className={`text-[9px] uppercase font-bold ${mode === 'LIVE_SCAN' ? 'text-red-400 animate-pulse' : 'text-sat-stable'}`}>
                    {mode === 'LIVE_SCAN' ? 'STREAMING' : currentObs.status}
                  </span>
                </div>
                <div>LAT: <span className="text-sat-accent font-bold">{displayLat}</span></div>
                <div>LON: <span className="text-sat-accent font-bold">{displayLon}</span></div>
                <div>SENSOR: <span className="text-sat-text">{mode === 'LIVE_SCAN' ? 'CDSE REALTIME STAC' : currentObs.sensor}</span></div>
                <div className="text-sat-change font-bold pt-0.5 truncate">
                  {mode === 'LIVE_SCAN' ? '🔴 Live Downlink Active' : currentObs.delta}
                </div>
              </div>

              <div className="absolute bottom-2 right-2 flex items-center space-x-1 font-mono text-[9px] bg-sat-surface/80 backdrop-blur-md border border-sat-border/50 p-1 rounded">
                {OBSERVATION_POINTS.map((pt, idx) => (
                  <button
                    key={pt.id}
                    onClick={() => setActivePointIndex(idx)}
                    className={`px-1.5 py-0.5 rounded transition-all cursor-pointer ${
                      activePointIndex === idx
                        ? 'bg-sat-accent text-slate-950 font-bold'
                        : 'text-sat-dim hover:text-sat-text'
                    }`}
                  >
                    {idx + 1}
                  </button>
                ))}
              </div>
            </div>

            {/* Seamless Integrated Telemetry Footer Section inside the SAME Monitor Container */}
            <div className="border-t border-sat-border/50 bg-sat-surface/30 p-3.5 font-mono text-xs space-y-2 backdrop-blur-md">
              <div className="flex items-center justify-between text-[11px] font-bold text-sat-text uppercase">
                <span className="flex items-center space-x-1.5">
                  <Cpu className="w-3.5 h-3.5 text-sat-accent" />
                  <span>TARGET: {currentObs.name}</span>
                </span>
                <span className="text-sat-stable font-extrabold">CONFIDENCE: {currentObs.confidence}</span>
              </div>

              <div className="grid grid-cols-3 gap-2 text-[10px] text-sat-dim pt-1 border-t border-sat-border/40">
                <div className="bg-sat-panel/60 p-1.5 rounded border border-sat-border/50">
                  <span>ORBIT:</span> <strong className="text-sat-accent block">{currentObs.orbit}</strong>
                </div>
                <div className="bg-sat-panel/60 p-1.5 rounded border border-sat-border/50">
                  <span>SENSOR:</span> <strong className="text-sat-text block truncate">{currentObs.sensor}</strong>
                </div>
                <div className="bg-sat-panel/60 p-1.5 rounded border border-sat-border/50">
                  <span>STATUS:</span> <strong className="text-sat-stable block">VERIFIED ●</strong>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Editorial Hero Writing Layout (Inspired directly by user reference image) */}
        <div className="lg:col-span-6 flex flex-col justify-center items-center lg:items-end text-center lg:text-right space-y-6 bg-sat-surface/60 backdrop-blur-md p-6 sm:p-8 rounded-2xl border border-sat-border/50 shadow-2xl">
          
          {/* Main Display Headline (Serif + Bold Emphasis matching reference image) */}
          <div className="space-y-3">
            <h1 className="font-serif-display text-5xl sm:text-6xl md:text-7xl font-light tracking-tight text-sat-text leading-[1.05]">
              Intelligence for <br />
              our <span className="font-bold text-sat-text italic">Earth.</span>
            </h1>

            {/* Subtitle Label (Matching "DESIGN STUDIO" in user image) */}
            <div className="font-mono text-xs tracking-[0.25em] text-sat-accent uppercase pt-1 font-bold">
              SATQUERY PLATFORM
            </div>
          </div>

          {/* Editorial Paragraph (Matching narrative text in user reference image) */}
          <p className="text-sat-text/90 text-base sm:text-lg max-w-md font-sans font-medium leading-relaxed">
            Our AI analysis agents turn satellite imagery into inspectable, evidence-backed answers. Built for bi-temporal change detection, optical-SAR groundings, and clear scientific summaries.
          </p>

          {/* Action CTAs (Matching rounded pill button "read more" in user reference image) */}
          <div className="flex flex-col sm:flex-row items-center space-y-3 sm:space-y-0 sm:space-x-4 pt-4">
            
            {/* Pill Outlined Secondary Button */}
            <button
              onClick={onViewDemo}
              className="px-8 py-3 rounded-full border border-sat-borderLight text-sat-text font-mono text-xs font-semibold tracking-wider uppercase flex items-center justify-center space-x-2 hover:border-sat-accent hover:text-sat-accent transition-all cursor-pointer bg-sat-surface/40 hover:bg-sat-surface shadow-md"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>read demo</span>
            </button>

            {/* Pill Primary CTA Button */}
            <button
              onClick={onEnterWorkspace}
              className="px-8 py-3 rounded-full bg-sat-text text-sat-bg font-mono font-bold text-xs tracking-wider flex items-center justify-center space-x-2.5 hover:opacity-90 transition-all shadow-lg group uppercase cursor-pointer"
            >
              <span>ENTER WORKSPACE</span>
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform stroke-[2.5]" />
            </button>
          </div>

          {/* System Pipeline Readiness Indicator */}
          <div className="pt-4 font-mono text-[11px] text-sat-dim flex items-center space-x-2">
            <span className="w-2 h-2 rounded-full bg-sat-stable animate-ping" />
            <span>ORCHESTRATOR STATUS:</span>
            <span className="text-sat-stable font-bold">READY ●</span>
          </div>

        </div>

      </main>

      {/* System Workflow Pipeline & Telemetry Status Bar Section */}
      <div ref={workflowRef}>
        <SystemWorkflowSection onSelectStage={() => onEnterWorkspace()} />
      </div>

    </div>
  );
};
