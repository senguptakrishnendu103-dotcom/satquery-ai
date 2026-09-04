import React, { useState } from 'react';
import type { Observation, AnalysisResult } from '../../types/satquery';
import {
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Eye,
  Layers,
  Crosshair,
  Sparkles,
  Sliders,
} from 'lucide-react';

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
  onSelectDemoScenario,
}) => {
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  const [compareMode, setCompareMode] =
    useState<'BEFORE' | 'AFTER' | 'CHANGE'>('CHANGE');
  const [wipePosition, setWipePosition] = useState(50);
  const [showOverlays, setShowOverlays] = useState(true);
  const [showGrid, setShowGrid] = useState(false);

  const [cursorCoords, setCursorCoords] = useState({
    lat: '22.5726° N',
    lon: '88.3639° E',
  });

  const activeObsList = observations.filter((o) =>
    activeObservationIds.includes(o.id)
  );
  const hasImages = activeObsList.length > 0;

  const obsBefore = activeObsList[0] || null;
  const obsAfter = activeObsList[1] || activeObsList[0] || null;
  const isMultiObs = activeObsList.length >= 2;

  const handleZoomIn = () => setZoom((prev) => Math.min(prev + 0.25, 3.5));
  const handleZoomOut = () => setZoom((prev) => Math.max(prev - 0.25, 0.75));

  const handleReset = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    setDragStart({
      x: e.clientX - pan.x,
      y: e.clientY - pan.y,
    });
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const xPct = (e.clientX - rect.left) / rect.width;
    const yPct = (e.clientY - rect.top) / rect.height;

    const latBase = obsBefore?.metadata?.lat || 22.5726;
    const lonBase = obsBefore?.metadata?.lon || 88.3639;

    const currLat = (latBase + (0.5 - yPct) * 0.05).toFixed(4);
    const currLon = (lonBase + (xPct - 0.5) * 0.05).toFixed(4);

    setCursorCoords({
      lat: `${Math.abs(Number(currLat))}° ${Number(currLat) >= 0 ? 'N' : 'S'
        }`,
      lon: `${Math.abs(Number(currLon))}° ${Number(currLon) >= 0 ? 'E' : 'W'
        }`,
    });

    if (isDragging) {
      setPan({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      });
    }
  };

  const handleMouseUp = () => setIsDragging(false);

  const selectedRegion = activeResult?.evidence?.find(
    (region) => region.id === selectedRegionId
  );

  return (
    <div className="relative flex h-full min-h-0 flex-1 flex-col overflow-hidden bg-[#07090C] select-none">
      {/* Simple map toolbar */}
      <div className="absolute left-4 right-4 top-4 z-20 flex flex-wrap items-start justify-between gap-3 pointer-events-none">
        <div className="pointer-events-auto rounded-xl border border-sat-border bg-sat-surface/95 p-1.5 shadow-lg backdrop-blur-md">
          {isMultiObs ? (
            <div className="flex flex-wrap items-center gap-1">
              <button
                onClick={() => setCompareMode('BEFORE')}
                className={`rounded-lg px-3 py-2 text-xs font-medium transition-colors ${compareMode === 'BEFORE'
                    ? 'bg-sat-panel text-sat-accent'
                    : 'text-slate-400 hover:bg-sat-panel hover:text-slate-200'
                  }`}
              >
                Before
                <span className="ml-1 text-[10px] opacity-60">
                  {obsBefore?.date || 'T1'}
                </span>
              </button>

              <button
                onClick={() => setCompareMode('AFTER')}
                className={`rounded-lg px-3 py-2 text-xs font-medium transition-colors ${compareMode === 'AFTER'
                    ? 'bg-sat-panel text-sat-accent'
                    : 'text-slate-400 hover:bg-sat-panel hover:text-slate-200'
                  }`}
              >
                After
                <span className="ml-1 text-[10px] opacity-60">
                  {obsAfter?.date || 'T2'}
                </span>
              </button>

              <button
                onClick={() => setCompareMode('CHANGE')}
                className={`rounded-lg px-3 py-2 text-xs font-medium transition-colors ${compareMode === 'CHANGE'
                    ? 'bg-sat-change text-slate-950'
                    : 'text-slate-400 hover:bg-sat-panel hover:text-slate-200'
                  }`}
              >
                Compare changes
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2 px-3 py-2 text-xs text-slate-300">
              <span className="h-2 w-2 rounded-full bg-sat-accent" />
              <span>Your satellite image</span>
            </div>
          )}
        </div>

        <div className="pointer-events-auto flex items-center gap-1.5 rounded-xl border border-sat-border bg-sat-surface/95 p-1.5 shadow-lg backdrop-blur-md">
          <button
            onClick={() => setShowOverlays(!showOverlays)}
            title={showOverlays ? 'Hide analysis areas' : 'Show analysis areas'}
            aria-label={showOverlays ? 'Hide analysis areas' : 'Show analysis areas'}
            className={`rounded-lg p-2 transition-colors ${showOverlays
                ? 'bg-sat-panel text-sat-accent'
                : 'text-slate-400 hover:bg-sat-panel hover:text-slate-200'
              }`}
          >
            <Eye className="h-4 w-4" />
          </button>

          <button
            onClick={() => setShowGrid(!showGrid)}
            title={showGrid ? 'Hide map grid' : 'Show map grid'}
            aria-label={showGrid ? 'Hide map grid' : 'Show map grid'}
            className={`rounded-lg p-2 transition-colors ${showGrid
                ? 'bg-sat-panel text-sat-accent'
                : 'text-slate-400 hover:bg-sat-panel hover:text-slate-200'
              }`}
          >
            <Crosshair className="h-4 w-4" />
          </button>

          <div className="mx-0.5 h-5 w-px bg-sat-border" />

          <button
            onClick={handleZoomOut}
            title="Zoom out"
            aria-label="Zoom out"
            className="rounded-lg p-2 text-slate-300 hover:bg-sat-panel"
          >
            <ZoomOut className="h-4 w-4" />
          </button>

          <span className="w-10 text-center text-xs font-medium text-slate-300">
            {Math.round(zoom * 100)}%
          </span>

          <button
            onClick={handleZoomIn}
            title="Zoom in"
            aria-label="Zoom in"
            className="rounded-lg p-2 text-slate-300 hover:bg-sat-panel"
          >
            <ZoomIn className="h-4 w-4" />
          </button>

          <button
            onClick={handleReset}
            title="Reset view"
            aria-label="Reset view"
            className="rounded-lg p-2 text-slate-300 hover:bg-sat-panel"
          >
            <RotateCcw className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Helpful context when comparing */}
      {hasImages && isMultiObs && compareMode === 'CHANGE' && (
        <div className="pointer-events-none absolute left-1/2 top-20 z-20 -translate-x-1/2 rounded-full border border-sat-border bg-sat-surface/90 px-4 py-2 text-xs text-slate-300 shadow-lg backdrop-blur-md">
          Drag the slider below to see what changed
        </div>
      )}

      {/* Main image area */}
      <div
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        className={`relative flex h-full w-full flex-1 items-center justify-center ${isDragging ? 'cursor-grabbing' : hasImages ? 'cursor-grab' : ''
          }`}
      >
        {showGrid && (
          <div className="pointer-events-none absolute inset-0 z-10 bg-gis-grid opacity-20" />
        )}

        {!hasImages ? (
          <div className="z-10 w-full max-w-md px-6">
            <div className="rounded-2xl border border-sat-border bg-sat-surface/95 p-7 text-center shadow-2xl backdrop-blur">
              <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-sat-panel text-sat-accent">
                <Layers className="h-7 w-7" />
              </div>

              <h3 className="mt-5 text-lg font-semibold text-slate-100">
                Your map is ready
              </h3>

              <p className="mt-2 text-sm leading-relaxed text-slate-400">
                Add a satellite image from the panel to start exploring an
                area, or try an example to see how SATQuery works.
              </p>

              {onSelectDemoScenario && (
                <button
                  onClick={() => onSelectDemoScenario('demo-03')}
                  className="
                    mt-5 flex w-full items-center justify-center gap-2
                    rounded-xl bg-sat-accent px-4 py-3
                    text-sm font-semibold text-slate-950
                    transition-colors hover:bg-sky-300
                  "
                >
                  <Sparkles className="h-4 w-4" />
                  <span>Try an example</span>
                </button>
              )}
            </div>
          </div>
        ) : (
          <div
            className="relative transition-transform duration-75 ease-out"
            style={{
              transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
              width: '90%',
              height: '85%',
              maxHeight: '700px',
            }}
          >
            {/* Base image */}
            <div className="absolute inset-0 overflow-hidden rounded-xl border border-sat-border bg-sat-surface">
              <img
                src={
                  compareMode === 'AFTER' && isMultiObs
                    ? obsAfter.imageUrl
                    : obsBefore.imageUrl
                }
                alt="Satellite image"
                className="h-full w-full object-cover"
                draggable={false}
              />
            </div>

            {/* Before/after wipe */}
            {isMultiObs && compareMode === 'CHANGE' && (
              <div
                className="pointer-events-none absolute inset-0 overflow-hidden rounded-xl"
                style={{
                  clipPath: `polygon(0 0, ${wipePosition}% 0, ${wipePosition}% 100%, 0 100%)`,
                }}
              >
                <img
                  src={obsAfter.imageUrl}
                  alt="Satellite image after"
                  className="h-full w-full object-cover"
                  draggable={false}
                />

                <div
                  className="absolute bottom-0 top-0 w-0.5 bg-sat-accent shadow-[0_0_10px_#38BDF8]"
                  style={{ left: `${wipePosition}%` }}
                />
              </div>
            )}

            {/* Analysis areas */}
            {showOverlays &&
              activeResult?.evidence &&
              activeResult.evidence.map((region) => {
                const isSelected = selectedRegionId === region.id;

                return (
                  <div
                    key={region.id}
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectRegion(isSelected ? null : region.id);
                    }}
                    className={`absolute z-20 cursor-pointer rounded-lg border-2 transition-all ${isSelected
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
                    <div className="absolute -top-7 left-0 flex items-center gap-1 whitespace-nowrap rounded-lg border border-sat-border bg-sat-bg/95 px-2.5 py-1 text-[10px] shadow">
                      <span className="h-1.5 w-1.5 rounded-full bg-sat-change" />
                      <span className="font-semibold text-slate-100">
                        {region.label}
                      </span>
                      {region.areaEstimate && (
                        <span className="text-sat-change">
                          · {region.areaEstimate}
                        </span>
                      )}
                    </div>

                    {isSelected && (
                      <div
                        className="
                          pointer-events-auto absolute left-0 top-full z-30 mt-2
                          w-72 rounded-xl border border-sat-borderLight
                          bg-sat-surface/95 p-4 shadow-2xl backdrop-blur
                        "
                        onClick={(e) => e.stopPropagation()}
                      >
                        <div className="flex items-start justify-between gap-3 border-b border-sat-border pb-3">
                          <div>
                            <div className="text-sm font-semibold text-slate-100">
                              {region.label}
                            </div>
                            <div className="mt-0.5 text-xs text-slate-500">
                              Area highlighted by SATQuery
                            </div>
                          </div>

                          <span className="shrink-0 rounded-full bg-sat-change/10 px-2 py-1 text-[10px] font-semibold text-sat-change">
                            {region.confidence}% confidence
                          </span>
                        </div>

                        <p className="mt-3 text-xs leading-relaxed text-slate-300">
                          {region.description}
                        </p>

                        {region.metrics && region.metrics.length > 0 && (
                          <div className="mt-3 space-y-2 rounded-lg bg-sat-bg/80 p-3">
                            {region.metrics.map((m, idx) => (
                              <div
                                key={idx}
                                className="flex justify-between gap-4 text-xs"
                              >
                                <span className="text-slate-500">{m.label}</span>
                                <span className="text-right font-medium text-slate-200">
                                  {m.value}
                                </span>
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

      {/* Before/after slider */}
      {hasImages && isMultiObs && compareMode === 'CHANGE' && (
        <div className="z-20 border-t border-sat-border bg-sat-surface/95 px-5 py-3 backdrop-blur-md">
          <div className="mb-2 flex items-center justify-between text-xs">
            <span className="text-slate-400">
              Before <span className="text-slate-500">({obsBefore?.date})</span>
            </span>

            <span className="font-medium text-sat-accent">
              Move slider to compare
            </span>

            <span className="text-slate-400">
              After <span className="text-slate-500">({obsAfter?.date})</span>
            </span>
          </div>

          <div className="flex items-center gap-3">
            <Sliders className="h-4 w-4 shrink-0 text-sat-accent" />

            <input
              type="range"
              min="0"
              max="100"
              value={wipePosition}
              onChange={(e) => setWipePosition(Number(e.target.value))}
              aria-label="Compare before and after satellite images"
              className="h-1.5 w-full cursor-pointer appearance-none rounded-lg bg-sat-border accent-sat-accent"
            />

            <span className="w-10 text-right text-xs font-medium text-slate-300">
              {wipePosition}%
            </span>
          </div>
        </div>
      )}

      {/* Minimal location/status bar */}
      <div className="z-10 flex items-center justify-between border-t border-sat-border bg-sat-bg px-4 py-2.5 text-xs font-medium text-slate-300">
        <div className="flex min-w-0 items-center gap-4">
          <span>
            Location:{' '}
            <span className="font-semibold text-slate-100">{cursorCoords.lat}</span>
            {' · '}
            <span className="font-semibold text-slate-100">{cursorCoords.lon}</span>
          </span>

          <span className="hidden sm:inline">
            Image type:{' '}
            <span className="font-semibold text-sat-accent">
              {obsBefore?.modality || 'Satellite image'}
            </span>
          </span>
        </div>

        <span className="shrink-0 font-semibold text-slate-200">Zoom {Math.round(zoom * 100)}%</span>
      </div>

      {/* Selected-result helper, intentionally subtle */}
      {selectedRegion && (
        <div className="pointer-events-none absolute bottom-14 left-1/2 z-20 hidden -translate-x-1/2 rounded-full border border-sat-border bg-sat-surface/90 px-3.5 py-1.5 text-xs text-slate-200 shadow-lg backdrop-blur sm:block">
          Click the highlighted area again to close its details
        </div>
      )}
    </div>
  );
};
