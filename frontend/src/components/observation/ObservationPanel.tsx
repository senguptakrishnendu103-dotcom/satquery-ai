import React, { useMemo, useRef, useState } from 'react';
import type { Observation, ModalityType } from '../../types/satquery';

import {
  CalendarDays,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Cloud,
  Database,
  Gauge,
  Layers,
  MapPin,
  Plus,
  Radio,
  Satellite,
  ScanLine,
  ShieldCheck,
  Sparkles,
  Upload,
  Waves,
  Wind,
} from 'lucide-react';

import { SatelliteSearchModal } from './SatelliteSearchModal';

/* ================================================================
   TYPES
================================================================ */

type SpectralView = 'RGB' | 'NIR' | 'SWIR' | 'SAR';

interface ObservationPanelProps {
  observations: Observation[];
  activeObservationIds: string[];
  onToggleObservation: (id: string) => void;
  onAddObservation: (file: File, modality: ModalityType) => void;
  onAddObservationFromProduct?: (obs: Observation) => void;
  onSelectDemoScenario?: (demoId: string) => void;
  onOpenSearchModal?: () => void;
}

/*
 * We intentionally extend metadata locally instead of modifying
 * your global Observation type.
 *
 * This keeps the component compatible with your current codebase
 * even if some of these fields are not yet present in the backend.
 */
interface ExtendedObservationMetadata {
  sensor?: string;
  groundSamplingDistance?: string;

  lat?: number | string;
  lon?: number | string;

  satelliteId?: string;
  spatialResolution?: string;
  cloudCover?: string | number;
  acquisitionDate?: string;
  orbit?: string;
  processingLevel?: string;
  coordinateSystem?: string;

  geometricStatus?: string;
  radiometricStatus?: string;
}

/* ================================================================
   SPECTRAL VIEW DEFINITIONS
================================================================ */

const SPECTRAL_VIEWS: {
  id: SpectralView;
  title: string;
  subtitle: string;
  description: string;
  modality: string;
  color: string;
  bg: string;
  border: string;
  icon: React.ReactNode;
  useCases: string[];
}[] = [
    {
      id: 'RGB',
      title: 'True Color',
      subtitle: 'Natural visual interpretation',
      description:
        'Visible-spectrum representation for general scene understanding.',
      modality: 'OPTICAL',
      color: 'text-emerald-400',
      bg: 'bg-emerald-400/10',
      border: 'border-emerald-400/40',
      icon: <Waves className="h-3.5 w-3.5" />,
      useCases: [
        'Buildings',
        'Roads',
        'Land cover',
        'Scene understanding',
      ],
    },
    {
      id: 'NIR',
      title: 'Near Infrared',
      subtitle: 'Vegetation response',
      description:
        'Highlights near-infrared response for vegetation and crop analysis.',
      modality: 'MULTISPECTRAL',
      color: 'text-rose-400',
      bg: 'bg-rose-400/10',
      border: 'border-rose-400/40',
      icon: <Wind className="h-3.5 w-3.5" />,
      useCases: [
        'Vegetation health',
        'Crop boundaries',
        'Biomass',
        'Vegetation stress',
      ],
    },
    {
      id: 'SWIR',
      title: 'Short-Wave Infrared',
      subtitle: 'Moisture & material response',
      description:
        'Useful for moisture, water and surface material discrimination.',
      modality: 'MULTISPECTRAL',
      color: 'text-blue-400',
      bg: 'bg-blue-400/10',
      border: 'border-blue-400/40',
      icon: <Waves className="h-3.5 w-3.5" />,
      useCases: [
        'Soil moisture',
        'Water bodies',
        'Burn scars',
        'Materials',
      ],
    },
    {
      id: 'SAR',
      title: 'SAR Backscatter',
      subtitle: 'Structure & radar response',
      description:
        'Radar observation providing structural information independent of visible light.',
      modality: 'SAR',
      color: 'text-violet-400',
      bg: 'bg-violet-400/10',
      border: 'border-violet-400/40',
      icon: <Radio className="h-3.5 w-3.5" />,
      useCases: [
        'Surface structure',
        'Flood extent',
        'Surface roughness',
        'Cloud-independent observation',
      ],
    },
  ];

/* ================================================================
   MAIN COMPONENT
================================================================ */

export const ObservationPanel: React.FC<ObservationPanelProps> = ({
  observations,
  activeObservationIds,
  onToggleObservation,
  onAddObservation,
  onAddObservationFromProduct,
  onSelectDemoScenario,
  onOpenSearchModal,
}) => {
  const [selectedModality, setSelectedModality] =
    useState<ModalityType>('OPTICAL');

  const [selectedSpectralView, setSelectedSpectralView] =
    useState<SpectralView>('RGB');

  const [isUploading, setIsUploading] =
    useState<boolean>(false);

  const [uploadStatusStep, setUploadStatusStep] =
    useState<string>('');

  const [expandedObservationId, setExpandedObservationId] =
    useState<string | null>(null);

  const [isSearchModalOpen, setIsSearchModalOpen] =
    useState<boolean>(false);

  const fileInputRef =
    useRef<HTMLInputElement>(null);

  /* ==============================================================
     ACTIVE OBSERVATIONS
  ============================================================== */

  const activeObservations = useMemo(
    () =>
      observations.filter((obs) =>
        activeObservationIds.includes(obs.id)
      ),
    [observations, activeObservationIds]
  );

  /*
   * Use the first active observation as the primary telemetry
   * source. If nothing is active, fall back to the first loaded
   * observation.
   */
  const primaryObservation =
    activeObservations[0] ?? observations[0] ?? null;

  const primaryMetadata =
    (primaryObservation?.metadata ??
      {}) as ExtendedObservationMetadata;

  /* ==============================================================
     UPLOAD
  ============================================================== */

  const handleFileChange = (
    e: React.ChangeEvent<HTMLInputElement>
  ) => {
    const file = e.target.files?.[0];

    if (!file) return;

    setIsUploading(true);
    setUploadStatusStep('INGESTING OBSERVATION...');

    window.setTimeout(() => {
      setUploadStatusStep('READING METADATA...');

      window.setTimeout(() => {
        setUploadStatusStep('VALIDATING DATASET...');

        window.setTimeout(() => {
          onAddObservation(file, selectedModality);

          setIsUploading(false);
          setUploadStatusStep('');

          /*
           * Allows selecting the same file again later.
           */
          if (fileInputRef.current) {
            fileInputRef.current.value = '';
          }
        }, 500);
      }, 600);
    }, 700);
  };

  /* ==============================================================
     QUERY-INDEPENDENT OBSERVATION RECOMMENDATION
  ============================================================== */

  const recommendation = useMemo(() => {
    if (!primaryObservation) {
      return SPECTRAL_VIEWS[0];
    }

    const modality =
      String(primaryObservation.modality ?? '').toUpperCase();

    if (modality === 'SAR') {
      return SPECTRAL_VIEWS.find(
        (view) => view.id === 'SAR'
      )!;
    }

    if (modality === 'MULTISPECTRAL') {
      return SPECTRAL_VIEWS.find(
        (view) => view.id === 'NIR'
      )!;
    }

    return SPECTRAL_VIEWS.find(
      (view) => view.id === selectedSpectralView
    )!;
  }, [
    primaryObservation,
    selectedSpectralView,
  ]);

  /* ==============================================================
     RENDER
  ============================================================== */

  return (
    <aside
      className="
        relative
        flex
        h-full
        min-h-0
        flex-col
        overflow-hidden
        border-r border-sat-border
        bg-sat-surface/90
        backdrop-blur-xl
        font-sans
        select-none
      "
      aria-label="Satellite observations"
    >
      {/* ==========================================================
          TECHNICAL BACKGROUND
      ========================================================== */}

      <div
        className="
          pointer-events-none
          absolute
          inset-0
          bg-gis-grid
          opacity-[0.025]
        "
      />

      {/* ==========================================================
          HEADER
      ========================================================== */}

      <div
        className="
          relative
          shrink-0
          border-b border-sat-border
          bg-sat-panel/50
          px-4 py-3.5
        "
      >
        <div className="flex items-center justify-between gap-3">
          <div className="flex min-w-0 items-center gap-3">
            <div
              className="
                flex
                h-9 w-9
                shrink-0
                items-center
                justify-center
                rounded-md
                border border-sat-accent/30
                bg-sat-accent/10
              "
            >
              <Layers className="h-4 w-4 text-sat-accent" />
            </div>

            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <h2
                  className="
                    truncate
                    font-display
                    text-sm
                    font-bold
                    uppercase
                    tracking-[0.12em]
                    text-sat-text
                  "
                >
                  Observations
                </h2>

                <span
                  className="
                    rounded-full
                    border border-sat-stable/30
                    bg-sat-stable/10
                    px-1.5 py-0.5
                    font-mono
                    text-[7px]
                    font-bold
                    tracking-wider
                    text-sat-stable
                  "
                >
                  LIVE
                </span>
              </div>

              <div
                className="
                  mt-0.5
                  font-mono
                  text-[8px]
                  uppercase
                  tracking-wider
                  text-sat-dim
                "
              >
                {activeObservationIds.length} ACTIVE ·{' '}
                {observations.length} LOADED
              </div>
            </div>
          </div>

          <button
            type="button"
            onClick={() => {
              if (onOpenSearchModal) {
                onOpenSearchModal();
              } else {
                setIsSearchModalOpen(true);
              }
            }}
            disabled={isUploading}
            className="
              group
              inline-flex
              shrink-0
              items-center
              gap-1.5
              rounded-md
              border border-sat-border
              bg-sat-bg
              px-2.5 py-1.5
              font-mono
              text-[9px]
              font-bold
              uppercase
              tracking-wider
              text-sat-accent
              transition-all
              hover:border-sat-accent/60
              hover:bg-sat-accent/10
              disabled:cursor-not-allowed
              disabled:opacity-50
            "
          >
            <Plus className="h-3.5 w-3.5 transition-transform group-hover:rotate-90" />
            <span>ADD DATA</span>
          </button>

          <input
            ref={fileInputRef}
            type="file"
            onChange={handleFileChange}
            className="hidden"
            accept="image/*,.tif,.tiff,.geotiff"
            aria-label="Upload satellite observation"
          />
        </div>
      </div>

      {/* ==========================================================
          UPLOAD MODALITY
      ========================================================== */}

      <div
        className="
          relative
          shrink-0
          border-b border-sat-border
          bg-sat-bg/80
          px-4 py-2
        "
      >
        <div className="flex items-center gap-1.5 overflow-x-auto">
          <span
            className="
              mr-1
              shrink-0
              font-mono
              text-[7px]
              uppercase
              tracking-wider
              text-sat-dim
            "
          >
            INGEST AS
          </span>

          {(
            [
              'OPTICAL',
              'SAR',
              'MULTISPECTRAL',
            ] as ModalityType[]
          ).map((mod) => {
            const isSelected =
              selectedModality === mod;

            return (
              <button
                key={mod}
                type="button"
                onClick={() =>
                  setSelectedModality(mod)
                }
                className={`
                  shrink-0
                  rounded
                  border
                  px-2 py-1
                  font-mono
                  text-[8px]
                  font-bold
                  uppercase
                  tracking-wider
                  transition-all

                  ${isSelected
                    ? `
                        border-sat-accent/50
                        bg-sat-accent/10
                        text-sat-accent
                      `
                    : `
                        border-transparent
                        text-sat-dim
                        hover:border-sat-border
                        hover:text-sat-text
                      `
                  }
                `}
              >
                {mod}
              </button>
            );
          })}
        </div>
      </div>

      {/* ==========================================================
          UPLOAD PROGRESS
      ========================================================== */}

      {isUploading && (
        <div
          className="
            relative
            shrink-0
            overflow-hidden
            border-b border-sat-accent/30
            bg-sat-accent/[0.06]
            px-4 py-3
          "
          role="status"
          aria-live="polite"
        >
          <div
            className="
              absolute
              inset-y-0
              left-0
              w-1/3
              bg-sat-accent/10
              animate-pulse
            "
          />

          <div className="relative flex items-center gap-3">
            <div
              className="
                flex h-7 w-7
                shrink-0
                items-center justify-center
                rounded-md
                border border-sat-accent/30
                bg-sat-accent/10
              "
            >
              <Upload className="h-3.5 w-3.5 animate-bounce text-sat-accent" />
            </div>

            <div className="min-w-0">
              <div className="font-mono text-[9px] font-bold uppercase tracking-wider text-sat-accent">
                {uploadStatusStep}
              </div>

              <div className="mt-1 font-mono text-[7px] text-sat-dim">
                {selectedModality} · REMOTE SENSING DATA INGESTION
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ==========================================================
          SCROLLABLE CONTENT
      ========================================================== */}

      <div className="relative min-h-0 flex-1 overflow-y-auto">

        {/* ========================================================
            SPECTRAL OBSERVATION SWITCHER
        ======================================================== */}

        <div className="border-b border-sat-border p-4">
          <PanelSectionHeader
            icon={<ScanLine className="h-3.5 w-3.5" />}
            title="Observation Layers"
            meta="SPECTRAL VIEW"
          />

          <div className="mt-2 grid grid-cols-2 gap-2">
            {SPECTRAL_VIEWS.map((view) => {
              const isActive =
                selectedSpectralView === view.id;

              return (
                <button
                  key={view.id}
                  type="button"
                  onClick={() =>
                    setSelectedSpectralView(view.id)
                  }
                  className={`
                    group
                    relative
                    overflow-hidden
                    rounded-md
                    border
                    p-2.5
                    text-left
                    transition-all
                    duration-200
                    focus:outline-none
                    focus:ring-2
                    focus:ring-sat-accent/30

                    ${isActive
                      ? `${view.border} ${view.bg}`
                      : `
                          border-sat-border
                          bg-sat-bg
                          hover:border-sat-borderLight
                        `
                    }
                  `}
                  aria-pressed={isActive}
                >
                  {isActive && (
                    <div
                      className={`
                        absolute
                        inset-y-0
                        left-0
                        w-0.5
                        ${view.id === 'RGB'
                          ? 'bg-emerald-400'
                          : view.id === 'NIR'
                            ? 'bg-rose-400'
                            : view.id === 'SWIR'
                              ? 'bg-blue-400'
                              : 'bg-violet-400'
                        }
                      `}
                    />
                  )}

                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5">
                      <span
                        className={
                          isActive
                            ? view.color
                            : 'text-sat-dim'
                        }
                      >
                        {view.icon}
                      </span>

                      <span
                        className={`
                          font-mono
                          text-[9px]
                          font-bold
                          tracking-wider
                          ${isActive
                            ? view.color
                            : 'text-sat-text'
                          }
                        `}
                      >
                        {view.id}
                      </span>
                    </div>

                    {isActive && (
                      <Check
                        className={`h-3 w-3 ${view.color}`}
                      />
                    )}
                  </div>

                  <div className="mt-1 font-mono text-[7px] uppercase text-sat-dim">
                    {view.title}
                  </div>

                  <div className="mt-0.5 font-mono text-[6px] uppercase text-sat-dim/80">
                    {view.modality}
                  </div>
                </button>
              );
            })}
          </div>

          {/* Active layer explanation */}
          {(() => {
            const view =
              SPECTRAL_VIEWS.find(
                (item) =>
                  item.id === selectedSpectralView
              ) ?? SPECTRAL_VIEWS[0];

            return (
              <div
                className={`
                  mt-2
                  rounded-md
                  border
                  ${view.border}
                  ${view.bg}
                  p-3
                `}
              >
                <div className="flex items-center gap-2">
                  <span className={view.color}>
                    {view.icon}
                  </span>

                  <div className="min-w-0">
                    <div
                      className={`
                        font-mono
                        text-[9px]
                        font-bold
                        uppercase
                        tracking-wider
                        ${view.color}
                      `}
                    >
                      {view.title}
                    </div>

                    <div className="font-sans text-[8px] text-sat-muted">
                      {view.subtitle}
                    </div>
                  </div>
                </div>

                <div className="mt-2 flex flex-wrap gap-1">
                  {view.useCases.map((useCase) => (
                    <span
                      key={useCase}
                      className="
                        rounded
                        border border-sat-border
                        bg-sat-surface/60
                        px-1.5 py-0.5
                        font-mono
                        text-[7px]
                        text-sat-muted
                      "
                    >
                      {useCase}
                    </span>
                  ))}
                </div>
              </div>
            );
          })()}
        </div>

        {/* ========================================================
            CURRENT SENSOR TELEMETRY
        ======================================================== */}

        <div className="border-b border-sat-border p-4">
          <PanelSectionHeader
            icon={<Satellite className="h-3.5 w-3.5" />}
            title="Live Satellite Telemetry"
            meta="PRIMARY OBSERVATION"
          />

          {primaryObservation ? (
            <div className="mt-2 space-y-2">

              {/* Sensor identity */}
              <div
                className="
                  rounded-md
                  border border-sat-accent/20
                  bg-sat-accent/[0.035]
                  p-3
                "
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="flex min-w-0 items-center gap-2">
                    <div
                      className="
                        flex h-7 w-7
                        shrink-0
                        items-center justify-center
                        rounded-md
                        bg-sat-accent/10
                        text-sat-accent
                      "
                    >
                      <Satellite className="h-3.5 w-3.5" />
                    </div>

                    <div className="min-w-0">
                      <div className="truncate font-mono text-[10px] font-bold text-sat-text">
                        {primaryMetadata.satelliteId ||
                          primaryObservation.name}
                      </div>

                      <div className="font-mono text-[7px] uppercase tracking-wider text-sat-dim">
                        {primaryMetadata.sensor ||
                          primaryObservation.modality}
                      </div>
                    </div>
                  </div>

                  <div
                    className="
                      flex
                      items-center
                      gap-1
                      rounded-full
                      border border-sat-stable/20
                      bg-sat-stable/10
                      px-1.5 py-0.5
                    "
                  >
                    <span className="h-1.5 w-1.5 rounded-full bg-sat-stable" />

                    <span className="font-mono text-[7px] font-bold text-sat-stable">
                      {primaryObservation.status}
                    </span>
                  </div>
                </div>
              </div>

              {/* Telemetry grid */}
              <div className="grid grid-cols-2 gap-2">
                <TelemetryCard
                  icon={
                    <Gauge className="h-3 w-3" />
                  }
                  label="RESOLUTION"
                  value={
                    primaryMetadata.spatialResolution ||
                    primaryMetadata.groundSamplingDistance ||
                    primaryObservation.dimensions
                  }
                />

                <TelemetryCard
                  icon={
                    <Cloud className="h-3 w-3" />
                  }
                  label="CLOUD COVER"
                  value={
                    primaryMetadata.cloudCover !==
                      undefined
                      ? `${primaryMetadata.cloudCover}`
                      : 'N/A'
                  }
                />

                <TelemetryCard
                  icon={
                    <CalendarDays className="h-3 w-3" />
                  }
                  label="ACQUISITION"
                  value={
                    primaryMetadata.acquisitionDate ||
                    primaryObservation.date
                  }
                />

                <TelemetryCard
                  icon={
                    <Radio className="h-3 w-3" />
                  }
                  label="MODALITY"
                  value={
                    primaryObservation.modality
                  }
                />
              </div>

              {/* Coordinates */}
              {primaryMetadata.lat !== undefined &&
                primaryMetadata.lon !== undefined && (
                  <div
                    className="
                      flex
                      items-center
                      gap-2
                      rounded-md
                      border border-sat-border
                      bg-sat-bg
                      px-3 py-2
                    "
                  >
                    <MapPin className="h-3 w-3 shrink-0 text-sat-change" />

                    <div className="min-w-0">
                      <div className="font-mono text-[7px] uppercase tracking-wider text-sat-dim">
                        Scene coordinates
                      </div>

                      <div className="font-mono text-[9px] text-sat-text">
                        {primaryMetadata.lat}° ,{' '}
                        {primaryMetadata.lon}°
                      </div>
                    </div>
                  </div>
                )}
            </div>
          ) : (
            <EmptyObservationState />
          )}
        </div>

        {/* ========================================================
            DATA QUALITY
        ======================================================== */}

        {primaryObservation && (
          <div className="border-b border-sat-border p-4">
            <PanelSectionHeader
              icon={
                <ShieldCheck className="h-3.5 w-3.5" />
              }
              title="Observation Quality"
              meta="VALIDATION"
            />

            <div className="mt-2">
              <div className="flex items-center justify-between">
                <span className="font-mono text-[8px] uppercase tracking-wider text-sat-dim">
                  Overall quality
                </span>

                <span className="font-mono text-[9px] font-bold text-sat-stable">
                  92%
                </span>
              </div>

              <div className="mt-1.5 h-1 overflow-hidden rounded-full bg-sat-panel">
                <div className="h-full w-[92%] rounded-full bg-sat-stable" />
              </div>
            </div>

            <div className="mt-3 grid grid-cols-2 gap-1.5">
              <QualityItem
                label="GEOMETRY"
                value={
                  primaryMetadata.geometricStatus ||
                  'VALID'
                }
              />

              <QualityItem
                label="RADIOMETRY"
                value={
                  primaryMetadata.radiometricStatus ||
                  'VALID'
                }
              />

              <QualityItem
                label="PROCESSING"
                value={
                  primaryMetadata.processingLevel ||
                  'READY'
                }
              />

              <QualityItem
                label="COORDINATE"
                value={
                  primaryMetadata.coordinateSystem ||
                  'AVAILABLE'
                }
              />
            </div>
          </div>
        )}

        {/* ========================================================
            AGENT OBSERVATION ROUTING
        ======================================================== */}

        <div className="border-b border-sat-border p-4">
          <div
            className="
              overflow-hidden
              rounded-lg
              border border-sat-accent/25
              bg-sat-accent/[0.035]
            "
          >
            <div
              className="
                flex
                items-center
                justify-between
                border-b border-sat-accent/15
                px-3 py-2.5
              "
            >
              <div className="flex items-center gap-2">
                <Sparkles className="h-3.5 w-3.5 text-sat-accent" />

                <span
                  className="
                    font-mono
                    text-[9px]
                    font-bold
                    uppercase
                    tracking-[0.13em]
                    text-sat-accent
                  "
                >
                  Agent Observation Routing
                </span>
              </div>

              <span className="font-mono text-[7px] text-sat-dim">
                MODEL SIGNAL
              </span>
            </div>

            <div className="p-3">
              <div className="flex items-center gap-3">
                <div
                  className="
                    flex h-9 w-9
                    shrink-0
                    items-center justify-center
                    rounded-md
                    border border-sat-accent/30
                    bg-sat-accent/10
                    text-sat-accent
                  "
                >
                  {recommendation.icon}
                </div>

                <div className="min-w-0 flex-1">
                  <div className="font-mono text-[7px] uppercase tracking-wider text-sat-dim">
                    Recommended observation
                  </div>

                  <div className="mt-0.5 font-mono text-[11px] font-bold text-sat-accent">
                    {recommendation.id}
                  </div>

                  <div className="font-sans text-[8px] text-sat-muted">
                    {recommendation.subtitle}
                  </div>
                </div>

                <ChevronRight className="h-4 w-4 shrink-0 text-sat-dim" />
              </div>

              <div className="mt-3 flex items-center gap-2">
                <div className="h-px flex-1 bg-sat-border" />

                <span className="font-mono text-[7px] text-sat-dim">
                  ROUTING
                </span>

                <div className="h-px flex-1 bg-sat-border" />
              </div>

              <div
                className="
                  mt-2
                  flex
                  items-center
                  justify-between
                  rounded-md
                  bg-sat-bg
                  px-3 py-2
                "
              >
                <span className="font-mono text-[7px] text-sat-dim">
                  OBSERVATION
                </span>

                <span className="font-mono text-[8px] font-bold text-sat-accent">
                  {recommendation.id}
                </span>

                <ChevronRight className="h-3 w-3 text-sat-dim" />

                <span className="font-mono text-[7px] font-bold text-sat-text">
                  SPECIALIST MODEL
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* ========================================================
            LOADED OBSERVATIONS
        ======================================================== */}

        <div className="p-4">
          <PanelSectionHeader
            icon={
              <Database className="h-3.5 w-3.5" />
            }
            title="Loaded Observations"
            meta={`${observations.length} DATASETS`}
          />

          {observations.length === 0 ? (
            <EmptyObservationState />
          ) : (
            <div className="mt-3 space-y-2.5">
              {observations.map((obs, index) => {
                const isActive =
                  activeObservationIds.includes(
                    obs.id
                  );

                const isExpanded =
                  expandedObservationId === obs.id;

                const metadata =
                  (obs.metadata ??
                    {}) as ExtendedObservationMetadata;

                return (
                  <article
                    key={obs.id}
                    className={`
                      overflow-hidden
                      rounded-lg
                      border
                      transition-all
                      duration-200

                      ${isActive
                        ? `
                            border-sat-accent/50
                            bg-sat-panel/80
                            shadow-[0_8px_24px_rgba(0,0,0,0.08)]
                          `
                        : `
                            border-sat-border
                            bg-sat-bg
                            opacity-75
                            hover:opacity-100
                            hover:border-sat-borderLight
                          `
                      }
                    `}
                  >
                    {/* Observation header */}
                    <div className="p-3">
                      <div className="flex items-center gap-2">
                        {/* Checkbox */}
                        <button
                          type="button"
                          onClick={() =>
                            onToggleObservation(
                              obs.id
                            )
                          }
                          className={`
                            flex
                            h-4 w-4
                            shrink-0
                            items-center
                            justify-center
                            rounded
                            border
                            transition-colors
                            ${isActive
                              ? 'border-sat-accent bg-sat-accent text-slate-950'
                              : 'border-sat-border bg-sat-surface hover:border-sat-accent'
                            }
                          `}
                          aria-label={
                            isActive
                              ? `Deactivate ${obs.name}`
                              : `Activate ${obs.name}`
                          }
                          aria-pressed={isActive}
                        >
                          {isActive && (
                            <Check className="h-3 w-3" />
                          )}
                        </button>

                        {/* Number */}
                        <span
                          className="
                            font-mono
                            text-[7px]
                            text-sat-dim
                          "
                        >
                          {String(index + 1).padStart(
                            2,
                            '0'
                          )}
                        </span>

                        {/* Name */}
                        <button
                          type="button"
                          onClick={() =>
                            onToggleObservation(
                              obs.id
                            )
                          }
                          className="
                            min-w-0
                            flex-1
                            truncate
                            text-left
                            font-mono
                            text-[10px]
                            font-bold
                            text-sat-text
                            hover:text-sat-accent
                          "
                        >
                          {obs.name}
                        </button>

                        {/* Status */}
                        <div
                          className="
                            flex
                            shrink-0
                            items-center
                            gap-1
                          "
                        >
                          <span className="h-1.5 w-1.5 rounded-full bg-sat-stable" />

                          <span
                            className="
                              font-mono
                              text-[7px]
                              font-bold
                              uppercase
                              text-sat-stable
                            "
                          >
                            {obs.status}
                          </span>
                        </div>
                      </div>

                      {/* Thumbnail + metadata */}
                      <div className="mt-3 grid grid-cols-12 gap-3">
                        <div
                          className="
                            col-span-4
                            aspect-square
                            overflow-hidden
                            rounded-md
                            border border-sat-border
                            bg-sat-bg
                          "
                        >
                          <img
                            src={
                              obs.thumbnailUrl ||
                              obs.imageUrl
                            }
                            alt={`${obs.name} satellite observation`}
                            className="
                              h-full
                              w-full
                              object-cover
                              transition-transform
                              duration-500
                              hover:scale-105
                            "
                            loading="lazy"
                          />
                        </div>

                        <div className="col-span-8 space-y-1.5">
                          <ObservationMetaRow
                            label="MODALITY"
                            value={obs.modality}
                            accent
                          />

                          <ObservationMetaRow
                            label="DATE"
                            value={obs.date}
                          />

                          <ObservationMetaRow
                            label="DIMENSIONS"
                            value={obs.dimensions}
                          />

                          {metadata.sensor && (
                            <ObservationMetaRow
                              label="SENSOR"
                              value={metadata.sensor}
                            />
                          )}
                        </div>
                      </div>

                      {/* Expand button */}
                      {obs.metadata && (
                        <button
                          type="button"
                          onClick={() =>
                            setExpandedObservationId(
                              isExpanded
                                ? null
                                : obs.id
                            )
                          }
                          className="
                            mt-3
                            flex
                            w-full
                            items-center
                            justify-between
                            border-t border-sat-border/60
                            pt-2
                            font-mono
                            text-[7px]
                            uppercase
                            tracking-wider
                            text-sat-dim
                            transition-colors
                            hover:text-sat-accent
                          "
                        >
                          <span>
                            Technical metadata
                          </span>

                          <ChevronDown
                            className={`
                              h-3 w-3
                              transition-transform
                              ${isExpanded
                                ? 'rotate-180'
                                : ''
                              }
                            `}
                          />
                        </button>
                      )}
                    </div>

                    {/* Expanded technical metadata */}
                    {isExpanded && (
                      <div
                        className="
                          border-t border-sat-border
                          bg-sat-bg/70
                          px-3
                          py-3
                        "
                      >
                        <div className="grid grid-cols-2 gap-1.5">
                          {metadata.sensor && (
                            <TechnicalItem
                              label="SENSOR"
                              value={metadata.sensor}
                            />
                          )}

                          {metadata.groundSamplingDistance && (
                            <TechnicalItem
                              label="GSD"
                              value={
                                metadata.groundSamplingDistance
                              }
                            />
                          )}

                          {metadata.spatialResolution && (
                            <TechnicalItem
                              label="RESOLUTION"
                              value={
                                metadata.spatialResolution
                              }
                            />
                          )}

                          {metadata.cloudCover !==
                            undefined && (
                              <TechnicalItem
                                label="CLOUD"
                                value={`${metadata.cloudCover}`}
                              />
                            )}

                          {metadata.processingLevel && (
                            <TechnicalItem
                              label="PROCESSING"
                              value={
                                metadata.processingLevel
                              }
                            />
                          )}

                          {metadata.coordinateSystem && (
                            <TechnicalItem
                              label="CRS"
                              value={
                                metadata.coordinateSystem
                              }
                            />
                          )}

                          {metadata.orbit && (
                            <TechnicalItem
                              label="ORBIT"
                              value={metadata.orbit}
                            />
                          )}

                          {metadata.lat !== undefined &&
                            metadata.lon !== undefined && (
                              <div className="col-span-2">
                                <TechnicalItem
                                  label="COORDINATES"
                                  value={`${metadata.lat}°, ${metadata.lon}°`}
                                />
                              </div>
                            )}
                        </div>
                      </div>
                    )}
                  </article>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* ==========================================================
          FOOTER
      ========================================================== */}

      {onSelectDemoScenario && (
        <div
          className="
            relative
            shrink-0
            border-t border-sat-border
            bg-sat-bg
            p-3
          "
        >
          <button
            type="button"
            onClick={() =>
              onSelectDemoScenario('demo-03')
            }
            className="
              group
              flex
              w-full
              items-center
              justify-center
              gap-2
              rounded-md
              border border-sat-border
              bg-sat-panel
              px-3 py-2
              font-mono
              text-[9px]
              font-bold
              uppercase
              tracking-wider
              text-sat-accent
              transition-all
              hover:border-sat-accent/50
              hover:bg-sat-accent/10
            "
          >
            <Sparkles className="h-3 w-3 transition-transform group-hover:rotate-12" />

            <span>Load Demo Scenario</span>

            <ChevronRight className="h-3 w-3" />
          </button>
        </div>
      )}
      {/* ==========================================================
          SATELLITE SEARCH MODAL (CDSE Live Catalogue + File Upload)
      ========================================================== */}

      <SatelliteSearchModal
        isOpen={isSearchModalOpen}
        onClose={() => setIsSearchModalOpen(false)}
        onAddObservation={onAddObservation}
        onAddProductAsObservation={onAddObservationFromProduct
          ? (product: any) => {
              const obs: Observation = {
                id: `obs-cdse-${Date.now()}`,
                name: product.metadata?.name || product.product_id,
                filename: product.metadata?.name || `${product.product_id}.SAFE`,
                modality: product.modality === 'sar' ? 'SAR' : 'OPTICAL',
                date: product.acquisition_datetime
                  ? new Date(product.acquisition_datetime).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }).toUpperCase()
                  : 'N/A',
                dimensions: product.resolution ? `${product.resolution}m/px` : '10m',
                status: 'READY',
                metadata: {
                  sensor: product.platform || product.instrument || 'MSI',
                  groundSamplingDistance: product.resolution ? `${product.resolution}m/px` : undefined,
                  cloudCover: product.cloud_cover !== null && product.cloud_cover !== undefined
                    ? `${product.cloud_cover.toFixed(1)}%`
                    : undefined,
                  lat: product.bbox ? parseFloat(((product.bbox[1] + product.bbox[3]) / 2).toFixed(4)) : undefined,
                  lon: product.bbox ? parseFloat(((product.bbox[0] + product.bbox[2]) / 2).toFixed(4)) : undefined,
                  acquisitionTime: product.acquisition_datetime
                    ? new Date(product.acquisition_datetime).toISOString().substring(11, 19) + ' UTC'
                    : undefined,
                },
                imageUrl: product.thumbnail_url || '',
                thumbnailUrl: product.thumbnail_url || '',
                isDemo: false,
              };
              onAddObservationFromProduct(obs);
            }
          : undefined
        }
      />
    </aside>
  );
};

/* ================================================================
   SECTION HEADER
================================================================ */

interface PanelSectionHeaderProps {
  icon: React.ReactNode;
  title: string;
  meta?: string;
}

const PanelSectionHeader: React.FC<
  PanelSectionHeaderProps
> = ({ icon, title, meta }) => {
  return (
    <div className="flex items-center justify-between gap-3">
      <div className="flex items-center gap-2">
        <span className="text-sat-accent">
          {icon}
        </span>

        <span
          className="
            font-mono
            text-[9px]
            font-bold
            uppercase
            tracking-[0.14em]
            text-sat-text
          "
        >
          {title}
        </span>
      </div>

      {meta && (
        <span
          className="
            shrink-0
            font-mono
            text-[7px]
            uppercase
            tracking-wider
            text-sat-dim
          "
        >
          {meta}
        </span>
      )}
    </div>
  );
};

/* ================================================================
   TELEMETRY CARD
================================================================ */

interface TelemetryCardProps {
  icon: React.ReactNode;
  label: string;
  value: string;
}

const TelemetryCard: React.FC<
  TelemetryCardProps
> = ({ icon, label, value }) => {
  return (
    <div
      className="
        min-w-0
        rounded-md
        border border-sat-border
        bg-sat-bg
        p-2.5
      "
    >
      <div className="flex items-center gap-1.5">
        <span className="text-sat-accent">
          {icon}
        </span>

        <span
          className="
            font-mono
            text-[7px]
            uppercase
            tracking-wider
            text-sat-dim
          "
        >
          {label}
        </span>
      </div>

      <div
        className="
          mt-1
          truncate
          font-mono
          text-[9px]
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
   OBSERVATION META ROW
================================================================ */

interface ObservationMetaRowProps {
  label: string;
  value: string;
  accent?: boolean;
}

const ObservationMetaRow: React.FC<
  ObservationMetaRowProps
> = ({ label, value, accent = false }) => {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="shrink-0 font-mono text-[7px] text-sat-dim">
        {label}
      </span>

      <span
        className={`
          min-w-0
          truncate
          font-mono
          text-[8px]
          font-semibold
          ${accent
            ? 'text-sat-accent'
            : 'text-sat-muted'
          }
        `}
        title={value}
      >
        {value}
      </span>
    </div>
  );
};

/* ================================================================
   TECHNICAL ITEM
================================================================ */

interface TechnicalItemProps {
  label: string;
  value: string;
}

const TechnicalItem: React.FC<
  TechnicalItemProps
> = ({ label, value }) => {
  return (
    <div
      className="
        min-w-0
        rounded
        border border-sat-border
        bg-sat-surface
        px-2
        py-1.5
      "
    >
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
        {value}
      </div>
    </div>
  );
};

/* ================================================================
   QUALITY ITEM
================================================================ */

interface QualityItemProps {
  label: string;
  value: string;
}

const QualityItem: React.FC<
  QualityItemProps
> = ({ label, value }) => {
  return (
    <div
      className="
        flex
        items-center
        justify-between
        gap-2
        rounded
        border border-sat-border
        bg-sat-bg
        px-2
        py-1.5
      "
    >
      <span className="truncate font-mono text-[7px] text-sat-dim">
        {label}
      </span>

      <span className="flex items-center gap-1 truncate font-mono text-[7px] font-bold text-sat-stable">
        <CheckCircle2 className="h-2.5 w-2.5 shrink-0" />
        {value}
      </span>
    </div>
  );
};

/* ================================================================
   EMPTY STATE
================================================================ */

const EmptyObservationState: React.FC =
  () => {
    return (
      <div
        className="
          mt-3
          flex
          min-h-[110px]
          flex-col
          items-center
          justify-center
          rounded-lg
          border
          border-dashed
          border-sat-border
          bg-sat-bg
          px-4
          text-center
        "
      >
        <div
          className="
            flex
            h-8 w-8
            items-center
            justify-center
            rounded-md
            border border-sat-border
            bg-sat-surface
          "
        >
          <Satellite className="h-4 w-4 text-sat-dim" />
        </div>

        <div className="mt-2 font-mono text-[8px] font-bold uppercase tracking-wider text-sat-muted">
          No observations loaded
        </div>

        <div className="mt-1 font-mono text-[7px] text-sat-dim">
          Upload a GeoTIFF / TIFF / image observation
        </div>
      </div>
    );
  };

export default ObservationPanel;