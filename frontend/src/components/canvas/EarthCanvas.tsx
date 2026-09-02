import React, { useState } from 'react';
import type { Observation, AnalysisResult } from '../../types/satquery';
import { ZoomIn, ZoomOut, RotateCcw, Eye, Layers, Crosshair, Sparkles, Sliders } from 'lucide-react';

interface EarthCanvasProps {
  observations: Observation[];
  activeObservationIds: string[];
  activeResult: AnalysisResult | null;
  selectedRegionId: string | null;
  onSelectRegion: (regionId: string | null) => void;
  onSelectDemoScenario?: (demoId: string) => void;
}

export const EarthCanvas: React.FC<EarthCanvasProps> = ({
  observations,
  activeObservationIds,
  activeResult,
  selectedRegionId,
  onSelectRegion,
  onSelectDemoScenario
}) => {
  // Canvas viewport state
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  // Comparison & Overlay state
  const [compareMode, setCompareMode] = useState<'BEFORE' | 'AFTER' | 'CHANGE'>('CHANGE');
  const [wipePosition, setWipePosition] = useState(50); // percentage split slider
  const [showOverlays, setShowOverlays] = useState(true);
  const [showGrid, setShowGrid] = useState(true);

  // Mouse coordinate HUD telemetry
  const [cursorCoords, setCursorCoords] = useState({ lat: '22.5726° N', lon: '88.3639° E' });

  const activeObsList = observations.filter(o => activeObservationIds.includes(o.id));
  const hasImages = activeObsList.length > 0;

  // Primary image (Before or Single) and Secondary image (After)
  const obsBefore = activeObsList[0] || null;
  const obsAfter = activeObsList[1] || activeObsList[0] || null;
  const isMultiObs = activeObsList.length >= 2;

  // Handle Zoom
  const handleZoomIn = () => setZoom(prev => Math.min(prev + 0.25, 3.5));
  const handleZoomOut = () => setZoom(prev => Math.max(prev - 0.25, 0.75));
  const handleReset = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  // Handle Mouse Drag Pan
  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const xPct = (e.clientX - rect.left) / rect.width;
    const yPct = (e.clientY - rect.top) / rect.height;

    // Calculate latitude / longitude dynamically from center
    const latBase = obsBefore?.metadata?.lat || 22.5726;
    const lonBase = obsBefore?.metadata?.lon || 88.3639;
    const currLat = (latBase + (0.5 - yPct) * 0.05).toFixed(4);
    const currLon = (lonBase + (xPct - 0.5) * 0.05).toFixed(4);

    setCursorCoords({
      lat: `${Math.abs(Number(currLat))}° ${Number(currLat) >= 0 ? 'N' : 'S'}`,
      lon: `${Math.abs(Number(currLon))}° ${Number(currLon) >= 0 ? 'E' : 'W'}`
    });

    if (isDragging) {
      setPan({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y
      });
    }
  };

  const handleMouseUp = () => setIsDragging(false);

  return (
    <div className="flex-1 flex flex-col h-full bg-[#07090C] relative overflow-hidden select-none">
      
      {/* Top Floating GIS Toolbar */}
      <div className="absolute top-4 left-4 right-4 z-20 flex flex-wrap items-center justify-between gap-2 pointer-events-none">
        
        {/* Left: Mode & Comparison Switcher */}
        <div className="pointer-events-auto flex items-center space-x-2 bg-sat-surface/90 border border-sat-border p-1 rounded shadow-lg backdrop-blur-md font-mono text-xs">
          {isMultiObs ? (
            <div className="flex items-center space-x-1">
              <button
                onClick={() => setCompareMode('BEFORE')}
                className={`px-2.5 py-1 rounded text-[11px] font-semibold transition-colors ${
                  compareMode === 'BEFORE' ? 'bg-sat-panel text-sat-accent border border-sat-accent/40' : 'text-sat-dim hover:text-slate-200'
                }`}
              >
                BEFORE ({obsBefore?.date || 'T1'})
              </button>
              <button
                onClick={() => setCompareMode('AFTER')}
                className={`px-2.5 py-1 rounded text-[11px] font-semibold transition-colors ${
                  compareMode === 'AFTER' ? 'bg-sat-panel text-sat-accent border border-sat-accent/40' : 'text-sat-dim hover:text-slate-200'
                }`}
              >
                AFTER ({obsAfter?.date || 'T2'})
              </button>
              <button
                onClick={() => setCompareMode('CHANGE')}
                className={`px-2.5 py-1 rounded text-[11px] font-semibold transition-colors ${
                  compareMode === 'CHANGE' ? 'bg-sat-change text-slate-950 font-bold shadow-sm' : 'text-sat-dim hover:text-slate-200'
                }`}
              >
                CHANGE WIPE
              </button>
            </div>
          ) : (
            <div className="px-3 py-1 text-[11px] text-sat-muted flex items-center space-x-2">
              <span className="w-2 h-2 rounded-full bg-sat-accent" />
              <span>SINGLE OBSERVATION VIEW</span>
            </div>
          )}
        </div>

        {/* Right: Map Controls (Zoom, Reset, Grid, Overlay Toggle) */}
        <div className="pointer-events-auto flex items-center space-x-1.5 bg-sat-surface/90 border border-sat-border p-1 rounded shadow-lg backdrop-blur-md font-mono text-xs">
          <button
            onClick={() => setShowOverlays(!showOverlays)}
            title="Toggle Evidence Overlay"
            className={`p-1.5 rounded transition-colors ${
              showOverlays ? 'bg-sat-panel text-sat-accent border border-sat-accent/40' : 'text-sat-dim hover:text-slate-200'
            }`}
          >
            <Eye className="w-4 h-4" />
          </button>
          <button
            onClick={() => setShowGrid(!showGrid)}
            title="Toggle Technical Grid"
            className={`p-1.5 rounded transition-colors ${
              showGrid ? 'bg-sat-panel text-sat-accent border border-sat-accent/40' : 'text-sat-dim hover:text-slate-200'
            }`}
          >
            <Crosshair className="w-4 h-4" />
          </button>

          <div className="h-4 w-px bg-sat-border" />

          <button onClick={handleZoomOut} title="Zoom Out" className="p-1.5 rounded text-slate-300 hover:bg-sat-panel">
            <ZoomOut className="w-4 h-4" />
          </button>
          <span className="text-[11px] text-sat-accent w-10 text-center font-semibold">{Math.round(zoom * 100)}%</span>
          <button onClick={handleZoomIn} title="Zoom In" className="p-1.5 rounded text-slate-300 hover:bg-sat-panel">
            <ZoomIn className="w-4 h-4" />
          </button>
          <button onClick={handleReset} title="Reset View" className="p-1.5 rounded text-slate-300 hover:bg-sat-panel">
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>

      </div>

      {/* Main Canvas Viewport Area */}
      <div 
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        className={`flex-1 relative w-full h-full flex items-center justify-center cursor-grab ${
          isDragging ? 'cursor-grabbing' : ''
        }`}
      >
        {/* Technical GIS Grid Overlay */}
        {showGrid && <div className="absolute inset-0 bg-gis-grid opacity-30 pointer-events-none z-10" />}

        {!hasImages ? (
          /* Empty State */
          <div className="z-10 text-center p-8 max-w-sm border border-sat-border bg-sat-surface/90 rounded-lg shadow-2xl backdrop-blur space-y-4">
            <div className="w-12 h-12 mx-auto rounded-full bg-sat-panel border border-sat-borderLight flex items-center justify-center text-sat-accent">
              <Layers className="w-6 h-6" />
            </div>
            <div>
              <h3 className="font-mono text-sm font-semibold text-slate-100 uppercase tracking-wider">
                DROP AN OBSERVATION
              </h3>
              <p className="text-xs text-sat-muted mt-1 font-sans">
                Select an observation dataset from the left panel or load pre-processed demo imagery.
              </p>
            </div>
            {onSelectDemoScenario && (
              <button
                onClick={() => onSelectDemoScenario('demo-03')}
                className="w-full py-2.5 rounded bg-sat-accent text-slate-950 font-display font-semibold text-xs tracking-wider uppercase hover:bg-sky-300 transition-colors flex items-center justify-center space-x-2"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>LOAD DEMO OBSERVATIONS</span>
              </button>
            )}
          </div>
        ) : (
          /* Satellite Imagery Display Container with Pan/Zoom Transform */
          <div 
            className="relative transition-transform duration-75 ease-out"
            style={{
              transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
              width: '90%',
              height: '85%',
              maxHeight: '700px'
            }}
          >
            {/* Base Image (Before or Single) */}
            <div className="absolute inset-0 rounded border border-sat-border overflow-hidden bg-sat-surface">
              <img 
                src={compareMode === 'AFTER' && isMultiObs ? obsAfter.imageUrl : obsBefore.imageUrl} 
                alt="Satellite Observation Base"
                className="w-full h-full object-cover"
                draggable={false}
              />
            </div>

            {/* Split Slider / Wipe Overlay Mode (When in CHANGE mode with two images) */}
            {isMultiObs && compareMode === 'CHANGE' && (
              <div 
                className="absolute inset-0 rounded overflow-hidden pointer-events-none"
                style={{ clipPath: `polygon(0 0, ${wipePosition}% 0, ${wipePosition}% 100%, 0 100%)` }}
              >
                <img 
                  src={obsAfter.imageUrl} 
                  alt="Satellite Observation After"
                  className="w-full h-full object-cover"
                  draggable={false}
                />
                {/* Wipe Line Divider */}
                <div 
                  className="absolute top-0 bottom-0 w-0.5 bg-sat-accent shadow-[0_0_10px_#38BDF8]"
                  style={{ left: `${wipePosition}%` }}
                />
              </div>
            )}

            {/* Interactive Analytical Evidence Bounding Box Overlays */}
            {showOverlays && activeResult?.evidence && activeResult.evidence.map((region) => {
              const isSelected = selectedRegionId === region.id;
              return (
                <div
                  key={region.id}
                  onClick={(e) => {
                    e.stopPropagation();
                    onSelectRegion(isSelected ? null : region.id);
                  }}
                  className={`absolute rounded border-2 cursor-pointer transition-all z-20 ${
                    isSelected 
                      ? 'border-sat-change bg-sat-change/25 ring-4 ring-sat-change/30 shadow-lg scale-105' 
                      : 'border-sat-accent bg-sat-accent/15 hover:bg-sat-accent/25 hover:border-sky-300'
                  }`}
                  style={{
                    left: `${region.coords.x}%`,
                    top: `${region.coords.y}%`,
                    width: `${region.coords.width}%`,
                    height: `${region.coords.height}%`,
                  }}
                >
                  {/* Region Label Tag */}
                  <div className="absolute -top-6 left-0 bg-sat-bg/90 border border-sat-border text-slate-100 px-2 py-0.5 rounded text-[10px] font-mono whitespace-nowrap shadow flex items-center space-x-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-sat-change animate-ping" />
                    <span className="font-semibold text-sat-accent">{region.label}</span>
                    {region.areaEstimate && (
                      <span className="text-sat-change font-bold">({region.areaEstimate})</span>
                    )}
                  </div>

                  {/* Popover Card when Region is Selected */}
                  {isSelected && (
                    <div className="absolute top-full mt-2 left-0 w-64 bg-sat-surface/95 border border-sat-borderLight p-3 rounded-md shadow-2xl z-30 font-mono text-xs space-y-2 pointer-events-auto">
                      <div className="flex items-center justify-between border-b border-sat-border pb-1">
                        <span className="font-bold text-slate-100">{region.label}</span>
                        <span className="text-sat-change text-[10px] font-bold">CONF: {region.confidence}%</span>
                      </div>
                      <p className="font-sans text-slate-300 text-[11px] leading-relaxed">
                        {region.description}
                      </p>
                      {region.metrics && region.metrics.length > 0 && (
                        <div className="bg-sat-bg/80 p-2 rounded border border-sat-border space-y-1 text-[10px]">
                          {region.metrics.map((m, idx) => (
                            <div key={idx} className="flex justify-between">
                              <span className="text-sat-dim">{m.label}:</span>
                              <span className="text-slate-200 font-semibold">{m.value}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Bottom Wipe Controller (When in CHANGE mode) */}
      {hasImages && isMultiObs && compareMode === 'CHANGE' && (
        <div className="bg-sat-surface/90 border-t border-sat-border px-6 py-2 flex items-center justify-between z-20 font-mono text-xs">
          <span className="text-sat-dim text-[10px]">T1 ({obsBefore?.date})</span>
          <div className="flex-1 mx-4 flex items-center space-x-3">
            <Sliders className="w-3.5 h-3.5 text-sat-accent shrink-0" />
            <input 
              type="range" 
              min="0" 
              max="100" 
              value={wipePosition} 
              onChange={(e) => setWipePosition(Number(e.target.value))}
              className="w-full h-1 bg-sat-border rounded-lg appearance-none cursor-pointer accent-sat-accent"
            />
            <span className="text-sat-accent text-[11px] font-bold w-8">{wipePosition}%</span>
          </div>
          <span className="text-sat-dim text-[10px]">T2 ({obsAfter?.date})</span>
        </div>
      )}

      {/* Bottom Canvas Telemetry Strip */}
      <div className="bg-sat-bg border-t border-sat-border px-4 py-2 flex items-center justify-between text-[11px] font-mono text-sat-dim z-10">
        <div className="flex items-center space-x-4">
          <span>LAT: <span className="text-slate-300">{cursorCoords.lat}</span></span>
          <span>LON: <span className="text-slate-300">{cursorCoords.lon}</span></span>
          <span className="hidden sm:inline">SENSOR: <span className="text-sat-accent">{obsBefore?.modality || 'OPTICAL'}</span></span>
        </div>
        <div>
          <span>ZOOM: {Math.round(zoom * 100)}%</span>
        </div>
      </div>

    </div>
  );
};
