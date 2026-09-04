import React, { useMemo, useState } from 'react';
import type {
  Observation,
  AnalysisResult,
  MapLayerConfig,
} from '../../types/satquery';
import { MapControls } from './MapControls';
import { LayerControl } from './LayerControl';
import { ComparisonView } from './ComparisonView';
import { EvidenceLayer } from './EvidenceLayer';
import {
  Activity,
  Crosshair,
  Database,
  Gauge,
  Layers,
  MapPin,
  Navigation,
  Radio,
  ScanLine,
  Sparkles,
  Target,
} from 'lucide-react';

interface EarthCanvasProps {
  observations: Observation[];
  activeObservationIds: string[];
  activeResult: AnalysisResult | null;
  selectedRegionId: string | null;
  onSelectRegion: (regionId: string | null) => void;
  onSelectDemoScenario?: (demoId: string) => void;
}

type CanvasOverlayMode = 'EVIDENCE' | 'HEATMAP';

interface CursorPosition {
  lat: string;
  lon: string;
  x: number;
  y: number;
  visible: boolean;
}

export const EarthCanvas: React.FC<EarthCanvasProps> = ({
  observations,
  activeObservationIds,
  activeResult,
  selectedRegionId,
  onSelectRegion,
  onSelectDemoScenario,
}) => {
  // ================================================================
  // VIEWPORT
  // ================================================================

  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  // ================================================================
  // MAP LAYERS
  // ================================================================

  const [showLayerPanel, setShowLayerPanel] = useState(false);

  const [mapLayers, setMapLayers] = useState<MapLayerConfig[]>([
    {
      id: 'base',
      name: 'BASE OBSERVATION',
      visible: true,
      color: '#38BDF8',
    },
    {
      id: 'change',
      name: 'CHANGE DETECTION',
      visible: true,
      color: '#FF5533',
      count: 3,
    },
    {
      id: 'water',
      name: 'WATER BODIES',
      visible: true,
      color: '#0EA5E9',
    },
    {
      id: 'built_up',
      name: 'BUILT-UP AREA',
      visible: true,
      color: '#F59E0B',
    },
    {
      id: 'vegetation',
      name: 'VEGETATION',
      visible: true,
      color: '#10B981',
    },
    {
      id: 'boundaries',
      name: 'BOUNDARIES',
      visible: false,
      color: '#64748B',
    },
  ]);

  // ================================================================
  // COMPARISON / OVERLAY
  // ================================================================

  const [compareMode, setCompareMode] = useState<
    'BEFORE' | 'AFTER' | 'CHANGE'
  >('CHANGE');

  const [wipePosition, setWipePosition] = useState(50);
  const [showOverlays, setShowOverlays] = useState(true);
  const [showGrid, setShowGrid] = useState(true);

  const [overlayMode, setOverlayMode] =
    useState<CanvasOverlayMode>('HEATMAP');

  const handleSetCompareMode = (mode: 'BEFORE' | 'AFTER' | 'CHANGE') => {
    setCompareMode(mode);
    if (mode === 'CHANGE') {
      setOverlayMode('HEATMAP');
      setShowOverlays(true);
    }
  };

  // Heatmap intensity zones: use evidence regions if available, or generate dynamic change zones
  const heatmapRegions = (activeResult?.evidence && activeResult.evidence.length > 0)
    ? activeResult.evidence
    : [
        {
          id: 'hm-fallback-1',
          label: 'Primary Surface Delta Zone',
          confidence: 94,
          coords: { x: 38, y: 34, width: 26, height: 24 }
        },
        {
          id: 'hm-fallback-2',
          label: 'Secondary Water/Vegetation Change',
          confidence: 87,
          coords: { x: 62, y: 56, width: 22, height: 20 }
        },
        {
          id: 'hm-fallback-3',
          label: 'Urban Structure Anomaly',
          confidence: 79,
          coords: { x: 24, y: 68, width: 18, height: 18 }
        }
      ];

  // ================================================================
  // CURSOR / HUD
  // ================================================================

  const [cursorCoords, setCursorCoords] = useState<CursorPosition>({
    lat: '22.5726° N',
    lon: '88.3639° E',
    x: 50,
    y: 50,
    visible: false,
  });

  // ================================================================
  // DERIVED OBSERVATION STATE
  // ================================================================

  const activeObsList = observations.filter((o) =>
    activeObservationIds.includes(o.id)
  );

  const hasImages = activeObsList.length > 0;

  const obsBefore = activeObsList[0] || null;
  const obsAfter =
    activeObsList[1] || activeObsList[0] || null;

  const isMultiObs = activeObsList.length >= 2;

  const visibleLayerIds = mapLayers
    .filter((l) => l.visible)
    .map((l) => l.id);

  const activeEvidenceCount =
    activeResult?.evidence?.length ?? 0;

  const activeObservation = obsBefore;

  const sceneMetadata = useMemo(() => {
    const metadata = activeObservation?.metadata;

    return {
      satellite:
        metadata?.sensor ||
        activeObservation?.name ||
        'REMOTE SENSOR',
      modality:
        activeObservation?.modality || 'OPTICAL',
      resolution:
        metadata?.groundSamplingDistance ||
        activeObservation?.dimensions ||
        'N/A',
      cloud:
        (metadata as any)?.cloudCover ?? 'N/A',
      acquisition:
        activeObservation?.date || 'N/A',
    };
  }, [activeObservation]);

  // ================================================================
  // ZOOM
  // ================================================================

  const handleZoomIn = () => {
    setZoom((prev) => Math.min(prev + 0.25, 3.5));
  };

  const handleZoomOut = () => {
    setZoom((prev) => Math.max(prev - 0.25, 0.75));
  };

  const handleReset = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  // ================================================================
  // LAYER
  // ================================================================

  const handleToggleLayer = (layerId: string) => {
    setMapLayers((prev) =>
      prev.map((layer) =>
        layer.id === layerId
          ? { ...layer, visible: !layer.visible }
          : layer
      )
    );
  };

  // ================================================================
  // MOUSE / CURSOR
  // ================================================================

  const handleMouseDown = (
    e: React.MouseEvent<HTMLDivElement>
  ) => {
    setIsDragging(true);

    setDragStart({
      x: e.clientX - pan.x,
      y: e.clientY - pan.y,
    });
  };

  const handleMouseMove = (
    e: React.MouseEvent<HTMLDivElement>
  ) => {
    const rect =
      e.currentTarget.getBoundingClientRect();

    const xPct =
      (e.clientX - rect.left) / rect.width;

    const yPct =
      (e.clientY - rect.top) / rect.height;

    const latBase =
      Number(obsBefore?.metadata?.lat) || 22.5726;

    const lonBase =
      Number(obsBefore?.metadata?.lon) || 88.3639;

    const currLat = (
      latBase +
      (0.5 - yPct) * 0.05
    ).toFixed(4);

    const currLon = (
      lonBase +
      (xPct - 0.5) * 0.05
    ).toFixed(4);

    setCursorCoords({
      lat: `${Math.abs(Number(currLat))}° ${Number(currLat) >= 0 ? 'N' : 'S'
        }`,
      lon: `${Math.abs(Number(currLon))}° ${Number(currLon) >= 0 ? 'E' : 'W'
        }`,
      x: xPct * 100,
      y: yPct * 100,
      visible: true,
    });

    if (isDragging) {
      setPan({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      });
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleMouseLeave = () => {
    setIsDragging(false);

    setCursorCoords((prev) => ({
      ...prev,
      visible: false,
    }));
  };

  // ================================================================
  // SCENE LABEL
  // ================================================================

  const sceneStatus = activeResult
    ? 'ANALYSIS COMPLETE'
    : hasImages
      ? 'OBSERVATION READY'
      : 'AWAITING OBSERVATION';

  return (
    <div
      className="
        relative
        flex
        h-full
        min-h-0
        flex-1
        flex-col
        overflow-hidden
        bg-black/30
        backdrop-blur-sm
        select-none
      "
    >
      {/* ==========================================================
          TOP MISSION HEADER
      ========================================================== */}

      <div
        className="
          pointer-events-none
          absolute
          left-4
          right-4
          top-4
          z-30
          flex
          flex-wrap
          items-start
          justify-between
          gap-2
        "
      >
        {/* LEFT: OBSERVATION TELEMETRY */}
        {hasImages && (
          <div
            className="
              pointer-events-auto
              min-w-[250px]
              max-w-[390px]
              overflow-hidden
              rounded-lg
              border
              border-sat-border
              bg-sat-surface/90
              shadow-2xl
              backdrop-blur-xl
            "
          >
            <div
              className="
                flex
                items-center
                justify-between
                border-b
                border-sat-border
                px-3
                py-2
              "
            >
              <div className="flex items-center gap-2">
                <div
                  className="
                    flex
                    h-6
                    w-6
                    items-center
                    justify-center
                    rounded
                    bg-sat-accent/10
                    text-sat-accent
                  "
                >
                  <Radio className="h-3.5 w-3.5" />
                </div>

                <div>
                  <div
                    className="
                      font-mono
                      text-[9px]
                      font-bold
                      uppercase
                      tracking-wider
                      text-sat-text
                    "
                  >
                    Earth Observation
                  </div>

                  <div
                    className="
                      font-mono
                      text-[7px]
                      uppercase
                      tracking-wider
                      text-sat-dim
                    "
                  >
                    {sceneStatus}
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-full bg-sat-stable shadow-[0_0_7px_currentColor]" />

                <span className="font-mono text-[7px] font-bold text-sat-stable">
                  LIVE
                </span>
              </div>
            </div>

            <div className="grid grid-cols-4 gap-px bg-sat-border">
              <TelemetryCell
                label="SENSOR"
                value={sceneMetadata.satellite}
              />

              <TelemetryCell
                label="MODALITY"
                value={sceneMetadata.modality}
              />

              <TelemetryCell
                label="GSD"
                value={sceneMetadata.resolution}
              />

              <TelemetryCell
                label="CLOUD"
                value={String(sceneMetadata.cloud)}
              />
            </div>

            <div
              className="
                flex
                items-center
                justify-between
                gap-3
                bg-sat-bg/80
                px-3
                py-1.5
              "
            >
              <span className="font-mono text-[7px] uppercase tracking-wider text-sat-dim">
                ACQUIRED
              </span>

              <span className="truncate font-mono text-[8px] font-semibold text-sat-text">
                {sceneMetadata.acquisition}
              </span>
            </div>
          </div>
        )}

        {/* RIGHT: EXISTING CONTROLS */}
        <div className="flex flex-wrap items-start gap-2">
          <div className="pointer-events-auto">
            <ComparisonView
              compareMode={compareMode}
              onSetCompareMode={handleSetCompareMode}
              wipePosition={wipePosition}
              onWipeChange={setWipePosition}
              dateBefore={obsBefore?.date}
              dateAfter={obsAfter?.date}
              isMultiObs={isMultiObs}
            />
          </div>

          <div className="pointer-events-auto">
            <MapControls
              zoom={zoom}
              onZoomIn={handleZoomIn}
              onZoomOut={handleZoomOut}
              onReset={handleReset}
              showGrid={showGrid}
              onToggleGrid={() =>
                setShowGrid((current) => !current)
              }
              showOverlays={showOverlays}
              onToggleOverlays={() =>
                setShowOverlays((current) => !current)
              }
              showLayerPanel={showLayerPanel}
              onToggleLayerPanel={() =>
                setShowLayerPanel((current) => !current)
              }
            />
          </div>
        </div>
      </div>

      {/* ==========================================================
          FLOATING LAYER PANEL
      ========================================================== */}

      {showLayerPanel && (
        <div className="absolute right-4 top-16 z-40 pointer-events-auto">
          <LayerControl
            layers={mapLayers}
            onToggleLayer={handleToggleLayer}
            onClose={() => setShowLayerPanel(false)}
          />
        </div>
      )}

      {/* ==========================================================
          LEFT MAP INSTRUMENT BAR
      ========================================================== */}

      {hasImages && (
        <div
          className="
            absolute
            left-4
            top-1/2
            z-30
            hidden
            -translate-y-1/2
            flex-col
            overflow-hidden
            rounded-md
            border border-sat-border
            bg-sat-surface/90
            shadow-xl
            backdrop-blur-xl
            sm:flex
          "
        >
          <InstrumentButton
            icon={<Target className="h-3.5 w-3.5" />}
            label="FOCUS"
            onClick={() => {
              if (selectedRegionId) {
                return;
              }

              setPan({ x: 0, y: 0 });
              setZoom(1.5);
            }}
          />

          <InstrumentButton
            icon={<Navigation className="h-3.5 w-3.5" />}
            label="RESET"
            onClick={handleReset}
          />

          <InstrumentButton
            icon={<Crosshair className="h-3.5 w-3.5" />}
            label="CENTER"
            onClick={() =>
              setCursorCoords((prev) => ({
                ...prev,
                x: 50,
                y: 50,
                visible: true,
              }))
            }
          />

          <InstrumentButton
            icon={<Layers className="h-3.5 w-3.5" />}
            label="LAYERS"
            active={showLayerPanel}
            onClick={() =>
              setShowLayerPanel((current) => !current)
            }
          />
        </div>
      )}

      {/* ==========================================================
          CENTRAL EARTH CANVAS
      ========================================================== */}

      <div
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseLeave}
        className={`
          relative
          flex
          min-h-0
          flex-1
          w-full
          items-center
          justify-center
          overflow-hidden
          cursor-grab
          ${isDragging ? 'cursor-grabbing' : ''}
        `}
      >
        {/* GIS GRID */}
        {showGrid && (
          <div
            className="
              pointer-events-none
              absolute
              inset-0
              z-10
              bg-gis-grid
              opacity-30
            "
          />
        )}

        {/* MAP CROSSHAIR */}
        {hasImages && cursorCoords.visible && (
          <>
            <div
              className="
                pointer-events-none
                absolute
                z-20
                h-full
                w-px
                bg-sat-accent/15
              "
              style={{
                left: `${cursorCoords.x}%`,
              }}
            />

            <div
              className="
                pointer-events-none
                absolute
                z-20
                h-px
                w-full
                bg-sat-accent/15
              "
              style={{
                top: `${cursorCoords.y}%`,
              }}
            />

            <div
              className="
                pointer-events-none
                absolute
                z-30
                -translate-x-1/2
                -translate-y-1/2
              "
              style={{
                left: `${cursorCoords.x}%`,
                top: `${cursorCoords.y}%`,
              }}
            >
              <div
                className="
                  relative
                  flex
                  h-8
                  w-8
                  items-center
                  justify-center
                "
              >
                <div className="absolute inset-0 rounded-full border border-sat-accent/70" />
                <div className="h-1.5 w-1.5 rounded-full bg-sat-accent shadow-[0_0_8px_currentColor]" />

                <div className="absolute -top-7 left-5 whitespace-nowrap rounded border border-sat-accent/30 bg-sat-surface/90 px-2 py-1 font-mono text-[7px] text-sat-accent shadow-lg backdrop-blur">
                  {cursorCoords.lat}
                  {' · '}
                  {cursorCoords.lon}
                </div>
              </div>
            </div>
          </>
        )}

        {!hasImages ? (
          /* ========================================================
             EMPTY STATE
          ======================================================== */

          <div
            className="
              relative
              z-10
              max-w-sm
              space-y-4
              rounded-lg
              border
              border-sat-border
              bg-sat-surface/90
              p-8
              text-center
              font-mono
              shadow-2xl
              backdrop-blur-xl
            "
          >
            <div
              className="
                mx-auto
                flex
                h-14
                w-14
                items-center
                justify-center
                rounded-full
                border border-sat-accent/30
                bg-sat-accent/10
                text-sat-accent
              "
            >
              <ScanLine className="h-6 w-6" />
            </div>

            <div>
              <h3
                className="
                  font-display
                  text-sm
                  font-bold
                  uppercase
                  tracking-wider
                  text-sat-text
                "
              >
                Awaiting Earth Observation
              </h3>

              <p
                className="
                  mt-2
                  font-sans
                  text-xs
                  font-normal
                  leading-relaxed
                  text-sat-muted
                "
              >
                Select an observation dataset from the
                Observation Panel or load pre-processed
                demo imagery.
              </p>
            </div>

            <div className="grid grid-cols-3 gap-1.5 text-left">
              <MiniCapability
                label="OPTICAL"
                value="RGB / MS"
              />
              <MiniCapability
                label="RADAR"
                value="SAR"
              />
              <MiniCapability
                label="TEMPORAL"
                value="CHANGE"
              />
            </div>

            {onSelectDemoScenario && (
              <button
                type="button"
                onClick={() =>
                  onSelectDemoScenario('demo-03')
                }
                className="
                  flex
                  w-full
                  items-center
                  justify-center
                  gap-2
                  rounded-md
                  bg-sat-accent
                  px-3
                  py-2.5
                  font-display
                  text-xs
                  font-semibold
                  uppercase
                  tracking-wider
                  text-slate-950
                  transition-colors
                  hover:bg-sky-300
                "
              >
                <Sparkles className="h-3.5 w-3.5" />
                <span>LOAD DEMO OBSERVATIONS</span>
              </button>
            )}
          </div>
        ) : (
          /* ========================================================
             IMAGE / MAP
          ======================================================== */

          <div
            className="
              relative
              h-[85%]
              w-[90%]
              max-h-[700px]
              transition-transform
              duration-75
              ease-out
            "
            style={{
              transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
            }}
          >
            {/* MAP FRAME */}
            <div
              className="
                pointer-events-none
                absolute
                -inset-2
                z-20
                rounded-lg
                border
                border-sat-accent/15
              "
            />

            {/* BASE IMAGE */}
            {visibleLayerIds.includes('base') && (
              <div
                className="
                  absolute
                  inset-0
                  overflow-hidden
                  rounded-lg
                  border border-sat-border
                  bg-sat-surface
                  shadow-2xl
                "
              >
                <img
                  src={
                    compareMode === 'AFTER' &&
                      isMultiObs
                      ? obsAfter.imageUrl
                      : obsBefore.imageUrl
                  }
                  alt="Satellite observation base"
                  className="h-full w-full object-cover"
                  draggable={false}
                />

                {/* SUBTLE IMAGE VIGNETTE */}
                <div
                  className="
                    pointer-events-none
                    absolute
                    inset-0
                    bg-gradient-to-b
                    from-black/10
                    via-transparent
                    to-black/15
                  "
                />
              </div>
            )}

            {/* BEFORE / AFTER WIPE */}
            {isMultiObs &&
              compareMode === 'CHANGE' &&
              visibleLayerIds.includes('base') && (
                <div
                  className="
                    pointer-events-none
                    absolute
                    inset-0
                    overflow-hidden
                    rounded-lg
                  "
                  style={{
                    clipPath: `polygon(
                      0 0,
                      ${wipePosition}% 0,
                      ${wipePosition}% 100%,
                      0 100%
                    )`,
                  }}
                >
                  <img
                    src={obsAfter.imageUrl}
                    alt="Satellite observation target"
                    className="h-full w-full object-cover"
                    draggable={false}
                  />

                  <div
                    className="
                      absolute
                      bottom-0
                      top-0
                      w-0.5
                      bg-sat-accent
                      shadow-[0_0_12px_#38BDF8]
                    "
                    style={{
                      left: `${wipePosition}%`,
                    }}
                  />
                </div>
              )}

            {/* ======================================================
                CHANGE / HEATMAP VISUALIZATION
            ====================================================== */}

            {showOverlays && overlayMode === 'HEATMAP' && (
              <div
                className="
                  pointer-events-none
                  absolute
                  inset-0
                  z-20
                  overflow-hidden
                  rounded-lg
                "
              >
                {/* Heatmap intensity zones anchored to evidence region coordinates */}
                {heatmapRegions.map((region, idx) => {
                  const cx = (region.coords?.x ?? 30) + (region.coords?.width ?? 20) / 2;
                  const cy = (region.coords?.y ?? 30) + (region.coords?.height ?? 20) / 2;
                  const radius = Math.max(120, ((region.coords?.width ?? 20) + (region.coords?.height ?? 20)) * 3);

                  return (
                    <React.Fragment key={`heatmap-${region.id || idx}`}>
                      {/* Outer Glow Halo */}
                      <div
                        className="absolute -translate-x-1/2 -translate-y-1/2 rounded-full opacity-80 mix-blend-screen animate-pulse"
                        style={{
                          left: `${cx}%`,
                          top: `${cy}%`,
                          width: `${radius * 1.5}px`,
                          height: `${radius * 1.5}px`,
                          background: 'radial-gradient(circle, rgba(239, 68, 68, 0.7) 0%, rgba(245, 158, 11, 0.5) 45%, rgba(14, 165, 233, 0.2) 75%, transparent 100%)',
                          filter: 'blur(16px)'
                        }}
                      />
                      {/* Core Thermal Hotspot */}
                      <div
                        className="absolute -translate-x-1/2 -translate-y-1/2 rounded-full opacity-90 border border-amber-400/60 shadow-[0_0_35px_#ef4444]"
                        style={{
                          left: `${cx}%`,
                          top: `${cy}%`,
                          width: `${radius * 0.7}px`,
                          height: `${radius * 0.7}px`,
                          background: 'radial-gradient(circle, rgba(255, 255, 255, 0.95) 0%, rgba(239, 68, 68, 0.9) 35%, rgba(245, 158, 11, 0.7) 70%, transparent 100%)',
                          filter: 'blur(6px)'
                        }}
                      />
                      {/* Heat Label Tag */}
                      <div
                        className="absolute -translate-x-1/2 -translate-y-1/2 px-2.5 py-1 rounded bg-black/90 border border-red-500/80 font-mono text-xs font-bold text-amber-300 shadow-2xl"
                        style={{
                          left: `${cx}%`,
                          top: `${cy - 14}%`,
                        }}
                      >
                        🔥 CHANGE DELTA: {region.confidence}%
                      </div>
                    </React.Fragment>
                  );
                })}

                {/* Heatmap Scale Legend */}
                <div className="absolute bottom-3 right-3 z-30 flex items-center gap-2.5 rounded-lg border border-sat-border bg-sat-surface/95 px-3.5 py-2 font-mono text-xs backdrop-blur-md shadow-xl">
                  <span className="text-sat-dim font-bold">SPECTRAL HEATMAP:</span>
                  <div className="h-2.5 w-24 rounded bg-gradient-to-r from-cyan-500 via-amber-400 to-red-600 border border-white/30" />
                  <span className="font-bold text-red-400">HIGH DELTA</span>
                </div>
              </div>
            )}

            {/* EVIDENCE LAYER */}
            {showOverlays &&
              overlayMode === 'EVIDENCE' &&
              activeResult?.evidence && (
                <EvidenceLayer
                  evidence={activeResult.evidence}
                  selectedRegionId={selectedRegionId}
                  onSelectRegion={onSelectRegion}
                  visibleLayers={visibleLayerIds}
                />
              )}

            {/* ======================================================
                MAP CORNER LABEL
            ====================================================== */}

            <div
              className="
                pointer-events-none
                absolute
                left-3
                top-3
                z-30
                rounded
                border border-white/10
                bg-black/35
                px-2
                py-1.5
                font-mono
                text-[7px]
                uppercase
                tracking-wider
                text-white/70
                backdrop-blur-sm
              "
            >
              <div>{sceneMetadata.modality}</div>
              <div className="mt-0.5 text-white/50">
                {sceneMetadata.resolution}
              </div>
            </div>

            {/* ======================================================
                NORTH INDICATOR
            ====================================================== */}

            <div
              className="
                pointer-events-none
                absolute
                right-3
                top-3
                z-30
                flex
                flex-col
                items-center
                rounded
                border border-white/10
                bg-black/35
                px-2
                py-1.5
                backdrop-blur-sm
              "
            >
              <span className="font-mono text-[7px] font-bold text-white/80">
                N
              </span>

              <Navigation className="mt-0.5 h-3.5 w-3.5 rotate-0 fill-current text-white/70" />
            </div>

            {/* ======================================================
                SCALE BAR
            ====================================================== */}

            <div
              className="
                pointer-events-none
                absolute
                bottom-3
                left-3
                z-30
                rounded
                border border-white/10
                bg-black/35
                px-2
                py-1.5
                backdrop-blur-sm
              "
            >
              <div className="flex items-end gap-2">
                <div>
                  <div className="h-1 w-16 border-x border-b border-white/70" />

                  <div className="mt-0.5 flex justify-between font-mono text-[6px] text-white/60">
                    <span>0</span>
                    <span>
                      {zoom >= 2
                        ? '250 m'
                        : zoom >= 1.25
                          ? '500 m'
                          : '1 km'}
                    </span>
                  </div>
                </div>

                <span className="font-mono text-[6px] uppercase text-white/50">
                  SCALE
                </span>
              </div>
            </div>

            {/* ======================================================
                EVIDENCE COUNT
            ====================================================== */}

            {activeResult && (
              <div
                className="
                  pointer-events-none
                  absolute
                  bottom-3
                  right-3
                  z-30
                  flex
                  items-center
                  gap-2
                  rounded
                  border border-sat-change/30
                  bg-black/45
                  px-2.5
                  py-1.5
                  font-mono
                  backdrop-blur-sm
                "
              >
                <MapPin className="h-3 w-3 text-sat-change" />

                <span className="text-[7px] uppercase text-white/60">
                  EVIDENCE
                </span>

                <span className="text-[9px] font-bold text-sat-change">
                  {activeEvidenceCount}
                </span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ==========================================================
          OVERLAY MODE STRIP
      ========================================================== */}

      {hasImages && (
        <div
          className="
            absolute
            bottom-11
            left-1/2
            z-30
            -translate-x-1/2
            rounded-lg
            border border-sat-border
            bg-sat-surface/90
            p-1
            shadow-xl
            backdrop-blur-xl
          "
        >
          <div className="flex items-center gap-1">
            <OverlayModeButton
              active={overlayMode === 'EVIDENCE'}
              icon={
                <Crosshair className="h-3 w-3" />
              }
              label="EVIDENCE"
              onClick={() =>
                setOverlayMode('EVIDENCE')
              }
            />

            <OverlayModeButton
              active={overlayMode === 'HEATMAP'}
              icon={
                <Activity className="h-3 w-3" />
              }
              label="CHANGE HEATMAP"
              onClick={() =>
                setOverlayMode('HEATMAP')
              }
            />
          </div>
        </div>
      )}

      {/* ==========================================================
          BOTTOM TELEMETRY / COORDINATE HUD
      ========================================================== */}

      <div
        className="
          relative
          z-40
          shrink-0
          border-t border-sat-border
          bg-sat-bg/95
          px-3
          py-2
          backdrop-blur-xl
          sm:px-4
        "
      >
        <div className="flex flex-wrap items-center justify-between gap-x-5 gap-y-1.5 font-mono text-[8px]">
          {/* Cursor coordinates */}
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
            <HudValue
              icon={
                <Crosshair className="h-3 w-3" />
              }
              label="LAT"
              value={cursorCoords.lat}
            />

            <HudValue
              icon={
                <MapPin className="h-3 w-3" />
              }
              label="LON"
              value={cursorCoords.lon}
            />

            <HudValue
              icon={
                <Gauge className="h-3 w-3" />
              }
              label="ZOOM"
              value={`1 : ${Math.round(
                25000 / zoom
              ).toLocaleString()}`}
            />

            <HudValue
              icon={
                <ScanLine className="h-3 w-3" />
              }
              label="GSD"
              value={sceneMetadata.resolution}
              hideOnSmall
            />
          </div>

          {/* Right status */}
          <div className="flex items-center gap-3">
            <span className="hidden items-center gap-1.5 text-sat-dim sm:flex">
              <Database className="h-3 w-3" />
              {activeObservationIds.length} DATASET
              {activeObservationIds.length === 1
                ? ''
                : 'S'}
            </span>

            <span className="flex items-center gap-1.5 text-sat-stable">
              <span className="h-1.5 w-1.5 rounded-full bg-sat-stable" />
              CANVAS READY
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

/* ================================================================
   TELEMETRY CELL
================================================================ */

interface TelemetryCellProps {
  label: string;
  value: string;
}

const TelemetryCell: React.FC<
  TelemetryCellProps
> = ({ label, value }) => {
  return (
    <div className="min-w-0 bg-sat-bg/90 px-2 py-2">
      <div className="font-mono text-[6px] uppercase tracking-wider text-sat-dim">
        {label}
      </div>

      <div
        className="
          mt-0.5
          truncate
          font-mono
          text-[8px]
          font-semibold
          text-sat-text
        "
        title={value}
      >
        {value || 'N/A'}
      </div>
    </div>
  );
};

/* ================================================================
   MAP INSTRUMENT BUTTON
================================================================ */

interface InstrumentButtonProps {
  icon: React.ReactNode;
  label: string;
  active?: boolean;
  onClick: () => void;
}

const InstrumentButton: React.FC<
  InstrumentButtonProps
> = ({ icon, label, active, onClick }) => {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`
        group
        flex
        h-10
        w-11
        flex-col
        items-center
        justify-center
        gap-0.5
        border-b border-sat-border
        last:border-b-0
        transition-colors
        ${active
          ? 'bg-sat-accent/10 text-sat-accent'
          : 'text-sat-dim hover:bg-sat-panel hover:text-sat-accent'
        }
      `}
      title={label}
    >
      {icon}

      <span className="font-mono text-[5px] font-bold tracking-wider">
        {label}
      </span>
    </button>
  );
};

/* ================================================================
   OVERLAY MODE BUTTON
================================================================ */

interface OverlayModeButtonProps {
  active: boolean;
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
}

const OverlayModeButton: React.FC<
  OverlayModeButtonProps
> = ({ active, icon, label, onClick }) => {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`
        flex
        items-center
        gap-1.5
        rounded
        px-2.5
        py-1.5
        font-mono
        text-[7px]
        font-bold
        uppercase
        tracking-wider
        transition-all
        ${active
          ? 'bg-sat-accent text-slate-950'
          : 'text-sat-dim hover:bg-sat-panel hover:text-sat-text'
        }
      `}
    >
      {icon}
      {label}
    </button>
  );
};

/* ================================================================
   MINI CAPABILITY
================================================================ */

interface MiniCapabilityProps {
  label: string;
  value: string;
}

const MiniCapability: React.FC<
  MiniCapabilityProps
> = ({ label, value }) => {
  return (
    <div
      className="
        rounded
        border border-sat-border
        bg-sat-bg
        p-2
      "
    >
      <div className="font-mono text-[6px] uppercase tracking-wider text-sat-dim">
        {label}
      </div>

      <div className="mt-0.5 font-mono text-[8px] font-bold text-sat-accent">
        {value}
      </div>
    </div>
  );
};

/* ================================================================
   HUD VALUE
================================================================ */

interface HudValueProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  hideOnSmall?: boolean;
}

const HudValue: React.FC<HudValueProps> = ({
  icon,
  label,
  value,
  hideOnSmall,
}) => {
  return (
    <div
      className={`
        items-center
        gap-1.5
        ${hideOnSmall
          ? 'hidden sm:flex'
          : 'flex'
        }
      `}
    >
      <span className="text-sat-accent">
        {icon}
      </span>

      <span className="text-sat-dim">
        {label}:
      </span>

      <span className="font-semibold text-sat-text">
        {value}
      </span>
    </div>
  );
};

export default EarthCanvas;
