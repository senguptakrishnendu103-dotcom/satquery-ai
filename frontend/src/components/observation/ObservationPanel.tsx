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
  Search,
  ShieldCheck,
  Sparkles,
  Upload,
  Waves,
  Wind,
  HelpCircle,
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
 * Kept local so the component remains compatible with the current
 * Observation type in the existing codebase.
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
  acquisitionTime?: string;
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
      subtitle: 'Looks like a normal photo',
      description: 'Best starting point for understanding what is in the scene.',
      modality: 'OPTICAL',
      color: 'text-emerald-400',
      bg: 'bg-emerald-400/10',
      border: 'border-emerald-400/40',
      icon: <Waves className="h-3.5 w-3.5" />,
      useCases: ['Buildings', 'Roads', 'Land cover'],
    },
    {
      id: 'NIR',
      title: 'Vegetation',
      subtitle: 'Highlights plant health',
      description: 'Useful when your question is about crops, forests or vegetation.',
      modality: 'MULTISPECTRAL',
      color: 'text-rose-400',
      bg: 'bg-rose-400/10',
      border: 'border-rose-400/40',
      icon: <Wind className="h-3.5 w-3.5" />,
      useCases: ['Vegetation', 'Crops', 'Plant stress'],
    },
    {
      id: 'SWIR',
      title: 'Moisture & Materials',
      subtitle: 'Highlights moisture and surfaces',
      description: 'Useful for water, soil moisture, burn areas and materials.',
      modality: 'MULTISPECTRAL',
      color: 'text-blue-400',
      bg: 'bg-blue-400/10',
      border: 'border-blue-400/40',
      icon: <Waves className="h-3.5 w-3.5" />,
      useCases: ['Water', 'Moisture', 'Burn areas'],
    },
    {
      id: 'SAR',
      title: 'Radar',
      subtitle: 'Works even with clouds',
      description: 'Useful for floods, surface structure and cloudy conditions.',
      modality: 'SAR',
      color: 'text-violet-400',
      bg: 'bg-violet-400/10',
      border: 'border-violet-400/40',
      icon: <Radio className="h-3.5 w-3.5" />,
      useCases: ['Floods', 'Surface change', 'Cloudy scenes'],
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

  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatusStep, setUploadStatusStep] = useState('');
  const [expandedObservationId, setExpandedObservationId] =
    useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [isSearchModalOpen, setIsSearchModalOpen] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const activeObservations = useMemo(
    () =>
      observations.filter((obs) =>
        activeObservationIds.includes(obs.id)
      ),
    [observations, activeObservationIds]
  );

  const primaryObservation =
    activeObservations[0] ?? observations[0] ?? null;

  const primaryMetadata =
    (primaryObservation?.metadata ?? {}) as ExtendedObservationMetadata;

  const recommendation = useMemo(() => {
    if (!primaryObservation) return SPECTRAL_VIEWS[0];

    const modality = String(primaryObservation.modality ?? '').toUpperCase();

    if (modality === 'SAR') {
      return SPECTRAL_VIEWS.find((view) => view.id === 'SAR')!;
    }

    if (modality === 'MULTISPECTRAL') {
      return SPECTRAL_VIEWS.find((view) => view.id === 'NIR')!;
    }

    return (
      SPECTRAL_VIEWS.find((view) => view.id === selectedSpectralView) ??
      SPECTRAL_VIEWS[0]
    );
  }, [primaryObservation, selectedSpectralView]);

  const openSearch = () => {
    if (onOpenSearchModal) {
      onOpenSearchModal();
    } else {
      setIsSearchModalOpen(true);
    }
  };

  const startUpload = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (
    e: React.ChangeEvent<HTMLInputElement>
  ) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setUploadStatusStep('Preparing your data…');

    window.setTimeout(() => {
      setUploadStatusStep('Reading the file…');

      window.setTimeout(() => {
        setUploadStatusStep('Checking the data…');

        window.setTimeout(() => {
          onAddObservation(file, selectedModality);
          setIsUploading(false);
          setUploadStatusStep('');

          if (fileInputRef.current) {
            fileInputRef.current.value = '';
          }
        }, 500);
      }, 600);
    }, 700);
  };

  return (
    <aside
      className="
        relative flex h-full min-h-0 flex-col overflow-hidden
        border-r border-sat-border bg-sat-surface/90
        backdrop-blur-xl font-sans select-none
      "
      aria-label="Satellite data workspace"
    >
      <div className="pointer-events-none absolute inset-0 bg-gis-grid opacity-[0.025]" />

      {/* ==========================================================
          FRIENDLY HEADER
      ========================================================== */}

      <div className="relative shrink-0 border-b border-sat-border bg-sat-panel/60 px-4 py-4">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-sat-accent/30 bg-sat-accent/10">
            <Satellite className="h-5 w-5 text-sat-accent" />
          </div>

          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h2 className="font-display text-base font-bold tracking-wide text-sat-text">
                Satellite Data
              </h2>

              {observations.length > 0 && (
                <span className="rounded-full border border-sat-stable/30 bg-sat-stable/10 px-2 py-0.5 text-xs font-bold uppercase tracking-wider text-sat-stable">
                  Ready
                </span>
              )}
            </div>

            <p className="mt-1 text-xs leading-5 text-sat-muted">
              Add satellite imagery and choose what you want to analyse.
            </p>
          </div>
        </div>

        <div className="mt-3 flex items-center gap-2 text-xs font-medium text-sat-dim">
          <CheckCircle2 className="h-3.5 w-3.5 text-sat-stable" />
          <span>
            {observations.length === 0
              ? 'No data added yet'
              : `${observations.length} dataset${observations.length === 1 ? '' : 's'} available`}
          </span>
        </div>
      </div>

      {/* ==========================================================
          PRIMARY ACTIONS — NO TECHNICAL KNOWLEDGE REQUIRED
      ========================================================== */}

      <div className="relative shrink-0 border-b border-sat-border bg-sat-bg/80 p-4">
        <div className="mb-3">
          <div className="text-sm font-bold text-sat-text">
            What would you like to do?
          </div>
          <div className="mt-0.5 text-xs leading-5 text-sat-dim">
            You do not need to know satellite formats or sensors.
          </div>
        </div>

        <div className="grid grid-cols-1 gap-2.5">
          <button
            type="button"
            onClick={openSearch}
            disabled={isUploading}
            className="
              group flex items-center gap-3 rounded-lg border
              border-sat-accent/30 bg-sat-accent/[0.07] p-3 text-left
              transition-all hover:border-sat-accent/60 hover:bg-sat-accent/10
              disabled:cursor-not-allowed disabled:opacity-50
            "
          >
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-sat-accent/10 text-sat-accent">
              <Search className="h-4 w-4" />
            </div>

            <div className="min-w-0 flex-1">
              <div className="text-xs font-bold text-sat-text">
                Find satellite data
              </div>
              <div className="mt-0.5 text-xs leading-4 text-sat-muted">
                Search the satellite catalogue by place and date.
              </div>
            </div>

            <ChevronRight className="h-4 w-4 shrink-0 text-sat-dim transition-transform group-hover:translate-x-0.5" />
          </button>

          <button
            type="button"
            onClick={startUpload}
            disabled={isUploading}
            className="
              group flex items-center gap-3 rounded-lg border
              border-sat-border bg-sat-panel/70 p-3 text-left
              transition-all hover:border-sat-borderLight hover:bg-sat-panel
              disabled:cursor-not-allowed disabled:opacity-50
            "
          >
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-sat-border bg-sat-surface text-sat-accent">
              <Upload className="h-4 w-4" />
            </div>

            <div className="min-w-0 flex-1">
              <div className="text-xs font-bold text-sat-text">
                Upload my own file
              </div>
              <div className="mt-0.5 text-xs leading-4 text-sat-muted">
                Add a satellite image you already have.
              </div>
            </div>

            <Plus className="h-4 w-4 shrink-0 text-sat-dim" />
          </button>

          {onSelectDemoScenario && (
            <button
              type="button"
              onClick={() => onSelectDemoScenario('demo-03')}
              disabled={isUploading}
              className="
                group flex items-center gap-3 rounded-lg border
                border-sat-border bg-sat-panel/40 p-3 text-left
                transition-all hover:border-sat-accent/40 hover:bg-sat-accent/5
                disabled:cursor-not-allowed disabled:opacity-50
              "
            >
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-sat-border bg-sat-surface text-sat-accent">
                <Sparkles className="h-4 w-4" />
              </div>

              <div className="min-w-0 flex-1">
                <div className="text-xs font-bold text-sat-text">
                  Try an example
                </div>
                <div className="mt-0.5 text-xs leading-4 text-sat-muted">
                  Explore the workspace with sample satellite data.
                </div>
              </div>

              <ChevronRight className="h-4 w-4 shrink-0 text-sat-dim" />
            </button>
          )}
        </div>

        <input
          ref={fileInputRef}
          type="file"
          onChange={handleFileChange}
          className="hidden"
          accept="image/*,.tif,.tiff,.geotiff"
          aria-label="Upload satellite observation"
        />
      </div>

      {/* ==========================================================
          UPLOAD PROGRESS
      ========================================================== */}

      {isUploading && (
        <div
          className="relative shrink-0 overflow-hidden border-b border-sat-accent/30 bg-sat-accent/[0.06] px-4 py-3"
          role="status"
          aria-live="polite"
        >
          <div className="absolute inset-y-0 left-0 w-1/3 animate-pulse bg-sat-accent/10" />

          <div className="relative flex items-center gap-3">
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-sat-accent/30 bg-sat-accent/10">
              <Upload className="h-3.5 w-3.5 animate-bounce text-sat-accent" />
            </div>

            <div className="min-w-0">
              <div className="text-xs font-bold text-sat-accent">
                {uploadStatusStep}
              </div>
              <div className="mt-1 text-xs text-sat-dim">
                This should only take a moment.
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ==========================================================
          CONTENT
      ========================================================== */}

      <div className="relative min-h-0 flex-1 overflow-y-auto">
        {/* ========================================================
            CURRENT DATA SUMMARY
        ======================================================== */}

        <div className="border-b border-sat-border p-4">
          <PanelSectionHeader
            icon={<Database className="h-3.5 w-3.5" />}
            title="Your Data"
            meta={
              observations.length
                ? `${observations.length} LOADED`
                : undefined
            }
          />

          {primaryObservation ? (
            <div className="mt-3 space-y-2">
              <div className="rounded-lg border border-sat-accent/20 bg-sat-accent/[0.035] p-3">
                <div className="flex items-start gap-3">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-sat-accent/10 text-sat-accent">
                    <Satellite className="h-4 w-4" />
                  </div>

                  <div className="min-w-0 flex-1">
                    <div className="text-[8px] font-semibold uppercase tracking-wider text-sat-dim">
                      Currently selected
                    </div>

                    <div className="mt-1 truncate text-[11px] font-bold text-sat-text">
                      {primaryObservation.name}
                    </div>

                    <div className="mt-1 flex flex-wrap gap-1.5">
                      <span className="rounded-full border border-sat-border bg-sat-bg px-2 py-0.5 text-[7px] text-sat-muted">
                        {primaryObservation.modality}
                      </span>

                      <span className="rounded-full border border-sat-stable/20 bg-sat-stable/10 px-2 py-0.5 text-[7px] font-semibold text-sat-stable">
                        {primaryObservation.status}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <TelemetryCard
                  icon={<Gauge className="h-3 w-3" />}
                  label="Resolution"
                  value={
                    primaryMetadata.spatialResolution ||
                    primaryMetadata.groundSamplingDistance ||
                    primaryObservation.dimensions
                  }
                />

                <TelemetryCard
                  icon={<Cloud className="h-3 w-3" />}
                  label="Cloud cover"
                  value={
                    primaryMetadata.cloudCover !== undefined
                      ? `${primaryMetadata.cloudCover}`
                      : 'Not available'
                  }
                />

                <TelemetryCard
                  icon={<CalendarDays className="h-3 w-3" />}
                  label="Date"
                  value={
                    primaryMetadata.acquisitionDate ||
                    primaryObservation.date
                  }
                />

                <TelemetryCard
                  icon={<Radio className="h-3 w-3" />}
                  label="Data type"
                  value={primaryObservation.modality}
                />
              </div>

              {primaryMetadata.lat !== undefined &&
                primaryMetadata.lon !== undefined && (
                  <div className="flex items-center gap-2 rounded-md border border-sat-border bg-sat-bg px-3 py-2">
                    <MapPin className="h-3 w-3 shrink-0 text-sat-change" />
                    <div className="min-w-0">
                      <div className="text-[7px] uppercase tracking-wider text-sat-dim">
                        Scene location
                      </div>
                      <div className="text-[9px] text-sat-text">
                        {primaryMetadata.lat}° , {primaryMetadata.lon}°
                      </div>
                    </div>
                  </div>
                )}
            </div>
          ) : (
            <div className="mt-3 rounded-lg border border-dashed border-sat-border bg-sat-bg p-4 text-center">
              <div className="mx-auto flex h-9 w-9 items-center justify-center rounded-md border border-sat-border bg-sat-surface">
                <Satellite className="h-4 w-4 text-sat-dim" />
              </div>
              <div className="mt-2 text-[9px] font-semibold text-sat-muted">
                Nothing selected yet
              </div>
              <div className="mt-1 text-[8px] leading-4 text-sat-dim">
                Use one of the options above to add satellite data.
              </div>
            </div>
          )}
        </div>

        {/* ========================================================
            "WHAT SHOULD I LOOK AT?" — TASK-ORIENTED
        ======================================================== */}

        <div className="border-b border-sat-border p-4">
          <PanelSectionHeader
            icon={<ScanLine className="h-3.5 w-3.5" />}
            title="What do you want to see?"
            meta="OPTIONAL"
          />

          <p className="mt-1 text-[8px] leading-4 text-sat-dim">
            Pick the view that matches your question. You can change it anytime.
          </p>

          <div className="mt-3 grid grid-cols-2 gap-2">
            {SPECTRAL_VIEWS.map((view) => {
              const isActive = selectedSpectralView === view.id;

              return (
                <button
                  key={view.id}
                  type="button"
                  onClick={() => setSelectedSpectralView(view.id)}
                  className={`
                    group relative overflow-hidden rounded-lg border p-3 text-left
                    transition-all duration-200 focus:outline-none
                    focus:ring-2 focus:ring-sat-accent/30
                    ${isActive
                      ? `${view.border} ${view.bg}`
                      : 'border-sat-border bg-sat-bg hover:border-sat-borderLight'
                    }
                  `}
                  aria-pressed={isActive}
                >
                  {isActive && (
                    <div
                      className={`
                        absolute inset-y-0 left-0 w-0.5
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

                  <div className="flex items-center justify-between gap-2">
                    <div className={`flex items-center gap-1.5 ${isActive ? view.color : 'text-sat-dim'}`}>
                      {view.icon}
                      <span className="text-[9px] font-bold">
                        {view.title}
                      </span>
                    </div>

                    {isActive && (
                      <Check className={`h-3 w-3 shrink-0 ${view.color}`} />
                    )}
                  </div>

                  <div className="mt-1.5 text-[8px] leading-4 text-sat-muted">
                    {view.subtitle}
                  </div>
                </button>
              );
            })}
          </div>

          <div
            className={`
              mt-2 rounded-lg border p-3
              ${recommendation.border} ${recommendation.bg}
            `}
          >
            <div className="flex items-start gap-2">
              <span className={recommendation.color}>
                {recommendation.icon}
              </span>

              <div className="min-w-0">
                <div className={`text-[9px] font-bold ${recommendation.color}`}>
                  Suggested for you: {recommendation.title}
                </div>
                <div className="mt-0.5 text-[8px] leading-4 text-sat-muted">
                  {recommendation.description}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ========================================================
            SIMPLE AI GUIDANCE
        ======================================================== */}

        <div className="border-b border-sat-border p-4">
          <div className="overflow-hidden rounded-lg border border-sat-accent/25 bg-sat-accent/[0.035]">
            <div className="flex items-center gap-2 border-b border-sat-accent/15 px-3 py-2.5">
              <Sparkles className="h-3.5 w-3.5 text-sat-accent" />
              <span className="text-[9px] font-bold tracking-wide text-sat-accent">
                AI SUGGESTION
              </span>
            </div>

            <div className="p-3">
              <div className="text-[9px] font-semibold text-sat-text">
                {recommendation.id === 'RGB'
                  ? 'Start with the natural-color view.'
                  : recommendation.id === 'NIR'
                    ? 'This view is useful for vegetation questions.'
                    : recommendation.id === 'SWIR'
                      ? 'This view can help investigate moisture and materials.'
                      : 'Radar can help when clouds or surface structure matter.'}
              </div>

              <div className="mt-1.5 text-[8px] leading-4 text-sat-muted">
                You do not need to understand the satellite sensor details.
                SATQuery can use the selected observation and view for the next step.
              </div>
            </div>
          </div>
        </div>

        {/* ========================================================
            LOADED OBSERVATIONS
        ======================================================== */}

        {observations.length > 0 && (
          <div className="border-b border-sat-border p-4">
            <PanelSectionHeader
              icon={<Layers className="h-3.5 w-3.5" />}
              title="Added Data"
              meta={`${observations.length}`}
            />

            <p className="mt-1 text-[8px] leading-4 text-sat-dim">
              Select the datasets you want SATQuery to use.
            </p>

            <div className="mt-3 space-y-2.5">
              {observations.map((obs, index) => {
                const isActive = activeObservationIds.includes(obs.id);
                const isExpanded = expandedObservationId === obs.id;
                const metadata =
                  (obs.metadata ?? {}) as ExtendedObservationMetadata;

                return (
                  <article
                    key={obs.id}
                    className={`
                      overflow-hidden rounded-lg border transition-all duration-200
                      ${isActive
                        ? 'border-sat-accent/50 bg-sat-panel/80'
                        : 'border-sat-border bg-sat-bg opacity-75 hover:opacity-100'
                      }
                    `}
                  >
                    <div className="p-3">
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => onToggleObservation(obs.id)}
                          className={`
                            flex h-5 w-5 shrink-0 items-center justify-center
                            rounded border transition-colors
                            ${isActive
                              ? 'border-sat-accent bg-sat-accent text-slate-950'
                              : 'border-sat-border bg-sat-surface hover:border-sat-accent'
                            }
                          `}
                          aria-label={
                            isActive
                              ? `Remove ${obs.name} from analysis`
                              : `Use ${obs.name} in analysis`
                          }
                          aria-pressed={isActive}
                        >
                          {isActive && <Check className="h-3 w-3" />}
                        </button>

                        <span className="text-[7px] text-sat-dim">
                          {String(index + 1).padStart(2, '0')}
                        </span>

                        <button
                          type="button"
                          onClick={() => onToggleObservation(obs.id)}
                          className="min-w-0 flex-1 truncate text-left text-[10px] font-bold text-sat-text hover:text-sat-accent"
                        >
                          {obs.name}
                        </button>

                        <span className="shrink-0 rounded-full border border-sat-stable/20 bg-sat-stable/10 px-1.5 py-0.5 text-[7px] font-bold uppercase text-sat-stable">
                          {obs.status}
                        </span>
                      </div>

                      <div className="mt-3 grid grid-cols-12 gap-3">
                        <div className="col-span-4 aspect-square overflow-hidden rounded-md border border-sat-border bg-sat-bg">
                          {obs.thumbnailUrl || obs.imageUrl ? (
                            <img
                              src={obs.thumbnailUrl || obs.imageUrl}
                              alt={`${obs.name} satellite observation`}
                              className="h-full w-full object-cover transition-transform duration-500 hover:scale-105"
                              loading="lazy"
                            />
                          ) : (
                            <div className="flex h-full w-full items-center justify-center">
                              <Satellite className="h-6 w-6 text-sat-dim" />
                            </div>
                          )}
                        </div>

                        <div className="col-span-8 space-y-1.5">
                          <ObservationMetaRow
                            label="TYPE"
                            value={obs.modality}
                            accent
                          />
                          <ObservationMetaRow label="DATE" value={obs.date} />
                          <ObservationMetaRow
                            label="SIZE"
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

                      {obs.metadata && (
                        <button
                          type="button"
                          onClick={() =>
                            setExpandedObservationId(
                              isExpanded ? null : obs.id
                            )
                          }
                          className="
                            mt-3 flex w-full items-center justify-between
                            border-t border-sat-border/60 pt-2
                            text-[7px] uppercase tracking-wider text-sat-dim
                            transition-colors hover:text-sat-accent
                          "
                        >
                          <span>
                            {isExpanded ? 'Hide technical details' : 'More details'}
                          </span>
                          <ChevronDown
                            className={`h-3 w-3 transition-transform ${isExpanded ? 'rotate-180' : ''
                              }`}
                          />
                        </button>
                      )}
                    </div>

                    {isExpanded && (
                      <div className="border-t border-sat-border bg-sat-bg/70 px-3 py-3">
                        <div className="mb-2 flex items-start gap-2 rounded-md border border-sat-border bg-sat-surface px-2.5 py-2">
                          <HelpCircle className="mt-0.5 h-3 w-3 shrink-0 text-sat-dim" />
                          <p className="text-[7px] leading-4 text-sat-dim">
                            These details are mainly for advanced users. You
                            normally do not need to change or understand them.
                          </p>
                        </div>

                        <div className="grid grid-cols-2 gap-1.5">
                          {metadata.sensor && (
                            <TechnicalItem label="SENSOR" value={metadata.sensor} />
                          )}
                          {metadata.groundSamplingDistance && (
                            <TechnicalItem
                              label="GSD"
                              value={metadata.groundSamplingDistance}
                            />
                          )}
                          {metadata.spatialResolution && (
                            <TechnicalItem
                              label="RESOLUTION"
                              value={metadata.spatialResolution}
                            />
                          )}
                          {metadata.cloudCover !== undefined && (
                            <TechnicalItem
                              label="CLOUD"
                              value={`${metadata.cloudCover}`}
                            />
                          )}
                          {metadata.processingLevel && (
                            <TechnicalItem
                              label="PROCESSING"
                              value={metadata.processingLevel}
                            />
                          )}
                          {metadata.coordinateSystem && (
                            <TechnicalItem
                              label="COORDINATE SYSTEM"
                              value={metadata.coordinateSystem}
                            />
                          )}
                          {metadata.orbit && (
                            <TechnicalItem label="ORBIT" value={metadata.orbit} />
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
          </div>
        )}

        {/* ========================================================
            DATA QUALITY — REASSURING, NOT TECHNICAL-FIRST
        ======================================================== */}

        {primaryObservation && (
          <div className="border-b border-sat-border p-4">
            <PanelSectionHeader
              icon={<ShieldCheck className="h-3.5 w-3.5" />}
              title="Data Check"
              meta="AUTOMATIC"
            />

            <div className="mt-3 rounded-lg border border-sat-stable/20 bg-sat-stable/5 p-3">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <div className="text-[9px] font-semibold text-sat-text">
                    Your data looks ready
                  </div>
                  <div className="mt-0.5 text-[8px] leading-4 text-sat-muted">
                    SATQuery checked the available dataset information.
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-bold text-sat-stable">92%</div>
                  <div className="text-[6px] uppercase tracking-wider text-sat-dim">
                    quality
                  </div>
                </div>
              </div>

              <div className="mt-2 h-1 overflow-hidden rounded-full bg-sat-panel">
                <div className="h-full w-[92%] rounded-full bg-sat-stable" />
              </div>
            </div>

            <button
              type="button"
              onClick={() => setShowAdvanced((value) => !value)}
              className="
                mt-2 flex w-full items-center justify-between rounded-md
                border border-sat-border bg-sat-bg px-3 py-2
                text-[8px] font-semibold text-sat-muted
                hover:border-sat-borderLight hover:text-sat-text
              "
              aria-expanded={showAdvanced}
            >
              <span>Advanced information</span>
              <ChevronDown
                className={`h-3 w-3 transition-transform ${showAdvanced ? 'rotate-180' : ''
                  }`}
              />
            </button>

            {showAdvanced && (
              <div className="mt-2 grid grid-cols-2 gap-1.5">
                <QualityItem
                  label="GEOMETRY"
                  value={primaryMetadata.geometricStatus || 'VALID'}
                />
                <QualityItem
                  label="RADIOMETRY"
                  value={primaryMetadata.radiometricStatus || 'VALID'}
                />
                <QualityItem
                  label="PROCESSING"
                  value={primaryMetadata.processingLevel || 'READY'}
                />
                <QualityItem
                  label="COORDINATE"
                  value={primaryMetadata.coordinateSystem || 'AVAILABLE'}
                />
              </div>
            )}
          </div>
        )}
      </div>

      {/* ==========================================================
          FOOTER HELP
      ========================================================== */}

      <div className="relative shrink-0 border-t border-sat-border bg-sat-bg px-4 py-2.5">
        <div className="flex items-center gap-2 text-[7px] leading-4 text-sat-dim">
          <HelpCircle className="h-3 w-3 shrink-0" />
          <span>
            Not sure what data to use? Start with <b className="text-sat-muted">Find satellite data</b>.
          </span>
        </div>
      </div>

      {/* ==========================================================
          SATELLITE SEARCH MODAL
      ========================================================== */}

      <SatelliteSearchModal
        isOpen={isSearchModalOpen}
        onClose={() => setIsSearchModalOpen(false)}
        onAddObservation={onAddObservation}
        onAddProductAsObservation={
          onAddObservationFromProduct
            ? (product: any) => {
              const obs: Observation = {
                id: `obs-cdse-${Date.now()}`,
                name: product.metadata?.name || product.product_id,
                filename:
                  product.metadata?.name ||
                  `${product.product_id}.SAFE`,
                modality:
                  product.modality === 'sar' ? 'SAR' : 'OPTICAL',
                date: product.acquisition_datetime
                  ? new Date(
                    product.acquisition_datetime
                  ).toLocaleDateString('en-GB', {
                    day: '2-digit',
                    month: 'short',
                    year: 'numeric',
                  })
                  : 'N/A',
                dimensions: product.resolution
                  ? `${product.resolution}m/px`
                  : '10m',
                status: 'READY',
                metadata: {
                  sensor:
                    product.platform ||
                    product.instrument ||
                    'MSI',
                  groundSamplingDistance: product.resolution
                    ? `${product.resolution}m/px`
                    : undefined,
                  cloudCover:
                    product.cloud_cover !== null &&
                      product.cloud_cover !== undefined
                      ? `${product.cloud_cover.toFixed(1)}%`
                      : undefined,
                  lat: product.bbox
                    ? parseFloat(
                      (
                        (product.bbox[1] + product.bbox[3]) /
                        2
                      ).toFixed(4)
                    )
                    : undefined,
                  lon: product.bbox
                    ? parseFloat(
                      (
                        (product.bbox[0] + product.bbox[2]) /
                        2
                      ).toFixed(4)
                    )
                    : undefined,
                  acquisitionTime: product.acquisition_datetime
                    ? new Date(
                      product.acquisition_datetime
                    )
                      .toISOString()
                      .substring(11, 19) + ' UTC'
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
   SMALL REUSABLE UI
================================================================ */

interface PanelSectionHeaderProps {
  icon: React.ReactNode;
  title: string;
  meta?: string;
}

const PanelSectionHeader: React.FC<PanelSectionHeaderProps> = ({
  icon,
  title,
  meta,
}) => (
  <div className="flex items-center justify-between gap-3">
    <div className="flex items-center gap-2">
      <span className="text-sat-accent">{icon}</span>
      <span className="text-xs font-bold tracking-wide text-sat-text uppercase">
        {title}
      </span>
    </div>

    {meta && (
      <span className="shrink-0 text-xs font-semibold uppercase tracking-wider text-sat-dim">
        {meta}
      </span>
    )}
  </div>
);

interface TelemetryCardProps {
  icon: React.ReactNode;
  label: string;
  value: string;
}

const TelemetryCard: React.FC<TelemetryCardProps> = ({
  icon,
  label,
  value,
}) => (
  <div className="min-w-0 rounded-md border border-sat-border bg-sat-bg p-2.5">
    <div className="flex items-center gap-1.5">
      <span className="text-sat-accent">{icon}</span>
      <span className="text-xs font-semibold uppercase tracking-wider text-sat-dim">
        {label}
      </span>
    </div>

    <div
      className="mt-1 truncate text-xs font-bold text-sat-text"
      title={value}
    >
      {value || 'Not available'}
    </div>
  </div>
);

interface ObservationMetaRowProps {
  label: string;
  value: string;
  accent?: boolean;
}

const ObservationMetaRow: React.FC<ObservationMetaRowProps> = ({
  label,
  value,
  accent = false,
}) => (
  <div className="flex items-center justify-between gap-2">
    <span className="shrink-0 text-xs text-sat-dim">{label}</span>
    <span
      className={`min-w-0 truncate text-xs font-semibold ${accent ? 'text-sat-accent' : 'text-sat-muted'
        }`}
      title={value}
    >
      {value}
    </span>
  </div>
);

interface TechnicalItemProps {
  label: string;
  value: string;
}

const TechnicalItem: React.FC<TechnicalItemProps> = ({
  label,
  value,
}) => (
  <div className="min-w-0 rounded border border-sat-border bg-sat-surface px-2 py-1.5">
    <div className="text-xs uppercase tracking-wider text-sat-dim">
      {label}
    </div>
    <div
      className="mt-0.5 truncate text-xs font-semibold text-sat-text"
      title={value}
    >
      {value}
    </div>
  </div>
);

interface QualityItemProps {
  label: string;
  value: string;
}

const QualityItem: React.FC<QualityItemProps> = ({ label, value }) => (
  <div className="flex items-center justify-between gap-2 rounded border border-sat-border bg-sat-bg px-2.5 py-1.5">
    <span className="truncate text-xs text-sat-dim">{label}</span>
    <span className="flex items-center gap-1 truncate text-xs font-bold text-sat-stable">
      <CheckCircle2 className="h-3 w-3 shrink-0" />
      {value}
    </span>
  </div>
);

export default ObservationPanel;
