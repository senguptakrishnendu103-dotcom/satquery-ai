import React, { useState, useEffect, useMemo } from 'react';
import {
  Satellite,
  Search,
  Calendar,
  MapPin,
  Download,
  AlertCircle,
  CheckCircle,
  X,
  Loader2,
  Database,
  Radio,
} from 'lucide-react';
import { satQueryService } from '../../services/satQueryService';
import type { Observation, SatelliteProviderInfo } from '../../types/satquery';

interface SatelliteSearchModalProps {
  isOpen: boolean;
  onClose: () => void;
  onObservationAdded?: (observation: Observation) => void;
  initialBBox?: [number, number, number, number] | null;
}

interface CollectionOption {
  id: string;
  label: string;
}

// Known friendly labels for display enhancement when a provider returns raw IDs
const KNOWN_COLLECTION_LABELS: Record<string, string> = {
  'RESOURCESAT-2A': 'Resourcesat-2A (LISS-4 / LISS-3 / AWiFS)',
  'RESOURCESAT-2': 'Resourcesat-2 (LISS-4 / LISS-3 / AWiFS)',
  'CARTOSAT-1': 'Cartosat-1 (PAN)',
  'CARTOSAT-2': 'Cartosat-2 Series (High-Res PAN / Multi)',
  'RISAT-1': 'RISAT-1 (C-band SAR)',
  'EOS-04': 'EOS-04 / RISAT-1A (Radar Imaging)',
  'EOS-06': 'EOS-06 / Oceansat-3 (OCM / SSTM)',
};

// Provider-specific static configuration (only used if backend does not return collection capabilities for that specific provider).
// Not universally applied to other providers.
const PROVIDER_SPECIFIC_FALLBACK_COLLECTIONS: Record<string, CollectionOption[]> = {
  bhoonidhi: [
    { id: 'RESOURCESAT-2A', label: 'RESOURCESAT-2A — Resourcesat-2A (LISS-4 / LISS-3 / AWiFS)' },
    { id: 'RESOURCESAT-2', label: 'RESOURCESAT-2 — Resourcesat-2 (LISS-4 / LISS-3 / AWiFS)' },
    { id: 'CARTOSAT-1', label: 'CARTOSAT-1 — Cartosat-1 (PAN)' },
    { id: 'CARTOSAT-2', label: 'CARTOSAT-2 — Cartosat-2 Series (High-Res PAN / Multi)' },
    { id: 'RISAT-1', label: 'RISAT-1 — RISAT-1 (C-band SAR)' },
    { id: 'EOS-04', label: 'EOS-04 — EOS-04 / RISAT-1A (Radar Imaging)' },
    { id: 'EOS-06', label: 'EOS-06 — EOS-06 / Oceansat-3 (OCM / SSTM)' },
  ],
};

export interface BBoxValidationResult {
  isValid: boolean;
  error?: string;
  fieldErrors: {
    minLon?: string;
    minLat?: string;
    maxLon?: string;
    maxLat?: string;
  };
  bbox?: [number, number, number, number];
}

/**
 * Validates satellite bounding box coordinates:
 * - longitude: -180 to 180
 * - latitude: -90 to 90
 * - minLon < maxLon
 * - minLat < maxLat
 * Preserves bbox format: [minLon, minLat, maxLon, maxLat]
 */
export function validateBBoxCoordinates(
  minLonStr: string,
  minLatStr: string,
  maxLonStr: string,
  maxLatStr: string
): BBoxValidationResult {
  const minLonTrim = (minLonStr ?? '').trim();
  const minLatTrim = (minLatStr ?? '').trim();
  const maxLonTrim = (maxLonStr ?? '').trim();
  const maxLatTrim = (maxLatStr ?? '').trim();

  const fieldErrors: BBoxValidationResult['fieldErrors'] = {};

  if (!minLonTrim) fieldErrors.minLon = 'Required';
  if (!minLatTrim) fieldErrors.minLat = 'Required';
  if (!maxLonTrim) fieldErrors.maxLon = 'Required';
  if (!maxLatTrim) fieldErrors.maxLat = 'Required';

  if (Object.keys(fieldErrors).length > 0) {
    return {
      isValid: false,
      error: 'All four bounding box coordinates (Min Lon, Min Lat, Max Lon, Max Lat) are required.',
      fieldErrors,
    };
  }

  const minLon = parseFloat(minLonTrim);
  const minLat = parseFloat(minLatTrim);
  const maxLon = parseFloat(maxLonTrim);
  const maxLat = parseFloat(maxLatTrim);

  if (isNaN(minLon)) fieldErrors.minLon = 'Must be a number';
  if (isNaN(minLat)) fieldErrors.minLat = 'Must be a number';
  if (isNaN(maxLon)) fieldErrors.maxLon = 'Must be a number';
  if (isNaN(maxLat)) fieldErrors.maxLat = 'Must be a number';

  if (Object.keys(fieldErrors).length > 0) {
    return {
      isValid: false,
      error: 'All bounding box coordinates must be valid numbers.',
      fieldErrors,
    };
  }

  // Validate longitude: -180 to 180
  if (minLon < -180 || minLon > 180) {
    fieldErrors.minLon = 'Must be -180° to 180°';
  }
  if (maxLon < -180 || maxLon > 180) {
    fieldErrors.maxLon = 'Must be -180° to 180°';
  }

  // Validate latitude: -90 to 90
  if (minLat < -90 || minLat > 90) {
    fieldErrors.minLat = 'Must be -90° to 90°';
  }
  if (maxLat < -90 || maxLat > 90) {
    fieldErrors.maxLat = 'Must be -90° to 90°';
  }

  if (fieldErrors.minLon || fieldErrors.maxLon || fieldErrors.minLat || fieldErrors.maxLat) {
    return {
      isValid: false,
      error: 'Coordinate out of bounds: Longitudes must be between -180° and 180°, and Latitudes must be between -90° and 90°.',
      fieldErrors,
    };
  }

  // Validate minLon < maxLon
  if (minLon >= maxLon) {
    fieldErrors.minLon = 'Must be < Max Lon';
    fieldErrors.maxLon = 'Must be > Min Lon';
    return {
      isValid: false,
      error: `Invalid Longitude: Min Lon (${minLon}°) must be strictly less than Max Lon (${maxLon}°).`,
      fieldErrors,
    };
  }

  // Validate minLat < maxLat
  if (minLat >= maxLat) {
    fieldErrors.minLat = 'Must be < Max Lat';
    fieldErrors.maxLat = 'Must be > Min Lat';
    return {
      isValid: false,
      error: `Invalid Latitude: Min Lat (${minLat}°) must be strictly less than Max Lat (${maxLat}°).`,
      fieldErrors,
    };
  }

  return {
    isValid: true,
    fieldErrors: {},
    bbox: [minLon, minLat, maxLon, maxLat],
  };
}

export interface DateValidationResult {
  isValid: boolean;
  error?: string;
  fieldErrors: {
    dateFrom?: string;
    dateTo?: string;
  };
}

/**
 * Validates satellite search date range:
 * - dateFrom and dateTo must be valid calendar dates
 * - dateFrom <= dateTo
 * Does not silently modify the user's dates.
 */
export function validateDateRange(
  dateFromStr: string,
  dateToStr: string
): DateValidationResult {
  const fromTrim = (dateFromStr ?? '').trim();
  const toTrim = (dateToStr ?? '').trim();

  const fieldErrors: DateValidationResult['fieldErrors'] = {};
  const dateRegex = /^\d{4}-\d{2}-\d{2}$/;

  let parsedFrom: Date | null = null;
  let parsedTo: Date | null = null;

  if (fromTrim) {
    if (!dateRegex.test(fromTrim)) {
      fieldErrors.dateFrom = 'Must be YYYY-MM-DD';
    } else {
      const d = new Date(`${fromTrim}T00:00:00Z`);
      if (isNaN(d.getTime()) || d.toISOString().slice(0, 10) !== fromTrim) {
        fieldErrors.dateFrom = 'Invalid calendar date';
      } else {
        parsedFrom = d;
      }
    }
  }

  if (toTrim) {
    if (!dateRegex.test(toTrim)) {
      fieldErrors.dateTo = 'Must be YYYY-MM-DD';
    } else {
      const d = new Date(`${toTrim}T00:00:00Z`);
      if (isNaN(d.getTime()) || d.toISOString().slice(0, 10) !== toTrim) {
        fieldErrors.dateTo = 'Invalid calendar date';
      } else {
        parsedTo = d;
      }
    }
  }

  if (fieldErrors.dateFrom || fieldErrors.dateTo) {
    const errorDetails = [
      fieldErrors.dateFrom && `Start Date (${fromTrim}): ${fieldErrors.dateFrom}`,
      fieldErrors.dateTo && `End Date (${toTrim}): ${fieldErrors.dateTo}`,
    ]
      .filter(Boolean)
      .join('; ');
    return {
      isValid: false,
      error: `Invalid date format: ${errorDetails}. Please enter valid calendar dates.`,
      fieldErrors,
    };
  }

  // Ensure dateFrom <= dateTo
  if (parsedFrom && parsedTo) {
    if (parsedFrom.getTime() > parsedTo.getTime()) {
      fieldErrors.dateFrom = 'Must be ≤ End Date';
      fieldErrors.dateTo = 'Must be ≥ Start Date';
      return {
        isValid: false,
        error: `Invalid Date Range: Start date (${fromTrim}) cannot be after end date (${toTrim}). Ensure dateFrom <= dateTo.`,
        fieldErrors,
      };
    }
  }

  return {
    isValid: true,
    fieldErrors: {},
  };
}

export type DownloadLifecycleState = 'idle' | 'downloading' | 'ingesting' | 'ready' | 'failed';

export interface ProductDownloadStatus {
  state: DownloadLifecycleState;
  error?: string;
  analysisAsset?: string;
  observation?: Observation;
}

const PRESET_AOIS = [
  { name: 'Bengaluru (ISRO HQ)', bbox: [77.45, 12.85, 77.75, 13.15] },
  { name: 'Mumbai Coast & Port', bbox: [72.75, 18.85, 73.05, 19.15] },
  { name: 'Delhi NCR Urban Zone', bbox: [76.95, 28.50, 77.35, 28.80] },
  { name: 'Sundarbans Delta', bbox: [88.50, 21.50, 89.20, 22.20] },
  { name: 'Chennai Harbor', bbox: [80.15, 13.00, 80.35, 13.20] },
];

export const SatelliteSearchModal: React.FC<SatelliteSearchModalProps> = ({
  isOpen,
  onClose,
  onObservationAdded,
  initialBBox,
}) => {
  const [providers, setProviders] = useState<SatelliteProviderInfo[]>([]);
  const [selectedProviderId, setSelectedProviderId] = useState<string>('');
  const [isLoadingProviders, setIsLoadingProviders] = useState<boolean>(true);
  const [providersError, setProvidersError] = useState<string | null>(null);

  const [selectedCollection, setSelectedCollection] = useState<string>('');
  const [dateFrom, setDateFrom] = useState('2024-01-01');
  const [dateTo, setDateTo] = useState('2026-08-30');
  const [minLon, setMinLon] = useState('77.45');
  const [minLat, setMinLat] = useState('12.85');
  const [maxLon, setMaxLon] = useState('77.75');
  const [maxLat, setMaxLat] = useState('13.15');
  const [coordErrors, setCoordErrors] = useState<{
    minLon?: string;
    minLat?: string;
    maxLon?: string;
    maxLat?: string;
  }>({});
  const [dateErrors, setDateErrors] = useState<{
    dateFrom?: string;
    dateTo?: string;
  }>({});

  useEffect(() => {
    if (initialBBox && Array.isArray(initialBBox) && initialBBox.length === 4) {
      setMinLon(Number(initialBBox[0]).toFixed(4));
      setMinLat(Number(initialBBox[1]).toFixed(4));
      setMaxLon(Number(initialBBox[2]).toFixed(4));
      setMaxLat(Number(initialBBox[3]).toFixed(4));
      setCoordErrors({});
      setSearchError(null);
    }
  }, [initialBBox, isOpen]);

  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [productStatuses, setProductStatuses] = useState<Record<string, ProductDownloadStatus>>({});
  const [activeDownloadId, setActiveDownloadId] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;

    let isMounted = true;
    setIsLoadingProviders(true);
    setProvidersError(null);

    satQueryService
      .getSatelliteProviders()
      .then((list) => {
        if (!isMounted) return;
        setProviders(list);

        if (list.length > 0) {
          setSelectedProviderId((prev) => {
            const exists = list.some((p) => p.id === prev);
            return exists ? prev : list[0].id;
          });
        }
      })
      .catch((err) => {
        if (!isMounted) return;
        console.error('Failed to load satellite providers:', err);
        setProvidersError('Failed to load satellite providers from /api/data/providers.');
      })
      .finally(() => {
        if (isMounted) setIsLoadingProviders(false);
      });

    return () => {
      isMounted = false;
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const currentProvider = providers.find((p) => p.id === selectedProviderId) || (providers.length > 0 ? providers[0] : null);
  const isProviderConfigured = Boolean(
    currentProvider &&
    currentProvider.is_configured !== false &&
    currentProvider.is_available !== false
  );

  // Derive collections based on the selected provider's capabilities.
  // Never treat ISRO collections as universally available across all providers.
  const { collections: availableCollections, isProviderSpecificConfig } = useMemo(() => {
    if (!currentProvider) {
      return { collections: [] as CollectionOption[], isProviderSpecificConfig: false };
    }

    // 1. Prioritize collections returned dynamically by the provider capabilities
    if (
      Array.isArray(currentProvider.supported_collections) &&
      currentProvider.supported_collections.length > 0
    ) {
      const mapped = currentProvider.supported_collections.map((item: any) => {
        if (typeof item === 'string') {
          const friendly = KNOWN_COLLECTION_LABELS[item];
          return {
            id: item,
            label: friendly ? `${item} — ${friendly}` : item,
          };
        } else if (item && typeof item === 'object' && item.id) {
          return {
            id: item.id,
            label: item.name ? `${item.id} — ${item.name}` : item.id,
          };
        }
        return { id: String(item), label: String(item) };
      });
      return { collections: mapped, isProviderSpecificConfig: false };
    }

    // 2. If backend does not provide collection information, check provider-specific configuration.
    // Treated strictly as provider-specific configuration for that provider, NOT universal.
    const providerKey = (currentProvider.id || '').toLowerCase();
    const fallbackList = PROVIDER_SPECIFIC_FALLBACK_COLLECTIONS[providerKey];
    if (fallbackList && fallbackList.length > 0) {
      return { collections: fallbackList, isProviderSpecificConfig: true };
    }

    // 3. For any provider with no backend collection capabilities and no provider-specific config,
    // do not invent collections.
    return { collections: [] as CollectionOption[], isProviderSpecificConfig: false };
  }, [currentProvider]);

  // Keep selectedCollection in sync with the available collections of the active provider
  useEffect(() => {
    if (availableCollections.length > 0) {
      setSelectedCollection((prev) => {
        const stillValid = availableCollections.some((c) => c.id === prev);
        return stillValid ? prev : availableCollections[0].id;
      });
    } else {
      setSelectedCollection('');
    }
  }, [availableCollections]);

  const handleProviderChange = (newProviderId: string) => {
    setSelectedProviderId(newProviderId);
    setSearchResults([]);
    setSearchError(null);
  };

  const handleApplyPreset = (preset: typeof PRESET_AOIS[0]) => {
    setMinLon(preset.bbox[0].toString());
    setMinLat(preset.bbox[1].toString());
    setMaxLon(preset.bbox[2].toString());
    setMaxLat(preset.bbox[3].toString());
    setCoordErrors({});
    setDateErrors({});
    setSearchError(null);
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isProviderConfigured) {
      setSearchError(`Provider '${currentProvider?.name || selectedProviderId}' is not configured or offline. Search is disabled.`);
      return;
    }

    if (!selectedCollection) {
      setSearchError(`Please select a collection supported by ${currentProvider?.name || 'the selected provider'}.`);
      return;
    }

    // Validate bounding box coordinates strictly
    const bboxValidation = validateBBoxCoordinates(minLon, minLat, maxLon, maxLat);
    if (!bboxValidation.isValid) {
      setCoordErrors(bboxValidation.fieldErrors);
      setSearchError(bboxValidation.error || 'Invalid bounding box coordinates.');
      return;
    }
    setCoordErrors({});

    // Validate date range strictly: dateFrom <= dateTo without modifying user dates
    const dateValidation = validateDateRange(dateFrom, dateTo);
    if (!dateValidation.isValid) {
      setDateErrors(dateValidation.fieldErrors);
      setSearchError(dateValidation.error || 'Invalid date range.');
      return;
    }
    setDateErrors({});

    setIsSearching(true);
    setSearchError(null);
    setSearchResults([]);
    setSuccessMessage(null);

    try {
      // Preserved exact bbox contract: [minLon, minLat, maxLon, maxLat]
      const bbox = bboxValidation.bbox!;

      const datetimeRange = dateFrom && dateTo ? `${dateFrom}/${dateTo}` : undefined;
      const resp = await satQueryService.searchSatelliteData({
        provider: selectedProviderId,
        collections: selectedCollection ? [selectedCollection] : [],
        bbox,
        datetimeRange,
        limit: 10,
      });

      setSearchResults(resp.items || []);
      if (!resp.items || resp.items.length === 0) {
        setSearchError('No matching satellite products found for the selected collection and AOI.');
      }
    } catch (err: any) {
      console.error('Satellite search failed:', err);
      setSearchError(err?.message || 'Search failed. Check network connectivity or provider parameters.');
    } finally {
      setIsSearching(false);
    }
  };

  const isDownloadingAny = Object.values(productStatuses).some((s) => s.state === 'downloading');
  const isIngestingAny = Object.values(productStatuses).some((s) => s.state === 'ingesting');
  const hasAnyReady = Object.values(productStatuses).some((s) => s.state === 'ready');

  const handleDownloadAndIngest = async (product: any) => {
    const pid = product.product_id;
    setActiveDownloadId(pid);
    setSearchError(null);
    setSuccessMessage(null);

    // State: Downloading
    setProductStatuses((prev) => ({
      ...prev,
      [pid]: { state: 'downloading' },
    }));

    // Transition to Ingesting while file extraction and raster ingestion take place
    const ingestTimer = setTimeout(() => {
      setProductStatuses((prev) => {
        if (prev[pid]?.state === 'downloading') {
          return { ...prev, [pid]: { state: 'ingesting' } };
        }
        return prev;
      });
    }, 1000);

    try {
      const newObs = await satQueryService.downloadSatelliteProduct({
        productId: pid,
        provider: selectedProviderId || currentProvider?.id || '',
        collection: product.collection || selectedCollection,
      });

      clearTimeout(ingestTimer);

      // Verify that the backend returned a genuine local analysis asset
      const realLocalAsset =
        (newObs as any).analysisAsset ||
        (newObs as any).analysis_asset ||
        (newObs as any).filePath ||
        (newObs as any).file_path ||
        (newObs as any).localPath ||
        (newObs as any).local_path ||
        newObs.metadata?.analysis_asset ||
        newObs.metadata?.file_path ||
        newObs.metadata?.local_path;

      if (!realLocalAsset || typeof realLocalAsset !== 'string' || !realLocalAsset.trim()) {
        throw new Error(
          'Backend download completed, but did not provide a valid local analysis asset.'
        );
      }

      // State: Ready (only after backend confirms ingestion and provides local asset)
      setProductStatuses((prev) => ({
        ...prev,
        [pid]: {
          state: 'ready',
          analysisAsset: realLocalAsset,
          observation: newObs,
        },
      }));

      setSuccessMessage(`Product ${pid} downloaded & ingested. Ready for analysis!`);
      onObservationAdded?.(newObs);
    } catch (err: any) {
      clearTimeout(ingestTimer);
      const actualError = err?.message || String(err) || 'Download/ingestion failed.';
      console.error('Download and ingestion failed for product:', pid, actualError);

      // On failure, show the actual error honestly
      setProductStatuses((prev) => ({
        ...prev,
        [pid]: {
          state: 'failed',
          error: actualError,
        },
      }));

      setSearchError(actualError);
    } finally {
      setActiveDownloadId(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 animate-in fade-in duration-200">
      <div className="relative flex max-h-[90vh] w-full max-w-4xl flex-col overflow-hidden rounded-xl border border-sat-accent/30 bg-sat-surface/95 shadow-2xl backdrop-blur-xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-sat-border bg-sat-panel/80 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-sat-accent/40 bg-sat-accent/10 text-sat-accent">
              <Satellite className="h-5 w-5 animate-pulse" />
            </div>
            <div>
              <h2 className="font-display text-base font-bold tracking-wide text-sat-text flex items-center gap-2">
                Fetch Satellite Data {currentProvider ? `— ${currentProvider.name}` : ''}
                <span
                  className={`rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase ${
                    isProviderConfigured
                      ? 'border-sat-accent/30 bg-sat-accent/10 text-sat-accent'
                      : 'border-amber-500/30 bg-amber-500/10 text-amber-400'
                  }`}
                >
                  {isLoadingProviders
                    ? 'Loading...'
                    : isProviderConfigured
                    ? 'Provider Ready'
                    : 'Not Configured'}
                </span>
              </h2>
              <p className="text-xs text-sat-muted">
                {currentProvider
                  ? `Search and download genuine remote sensing observations from ${currentProvider.name}.`
                  : 'Search and download genuine remote sensing observations from registered satellite data providers.'}
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="rounded-lg p-2 text-sat-dim hover:bg-sat-panel hover:text-sat-text transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Workflow Pipeline Status Bar: Searching → Downloading → Ingesting → Ready */}
        <div className="flex flex-wrap items-center justify-between border-b border-sat-border bg-sat-bg/80 px-6 py-2.5 text-xs">
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-bold uppercase tracking-wider text-sat-dim">Pipeline:</span>
            <div className="flex items-center gap-1.5 font-mono text-[11px]">
              {/* 1. Searching */}
              <span
                className={`flex items-center gap-1 px-2 py-0.5 rounded transition-all ${
                  isSearching
                    ? 'bg-sat-accent/20 text-sat-accent font-bold ring-1 ring-sat-accent/40 animate-pulse'
                    : searchResults.length > 0
                    ? 'bg-emerald-500/10 text-emerald-400 font-medium'
                    : 'text-sat-dim bg-sat-panel/40'
                }`}
              >
                {isSearching ? <Loader2 className="h-3 w-3 animate-spin" /> : searchResults.length > 0 ? <CheckCircle className="h-3 w-3 text-emerald-400" /> : null}
                Searching
              </span>

              <span className="text-sat-dim/40">→</span>

              {/* 2. Downloading */}
              <span
                className={`flex items-center gap-1 px-2 py-0.5 rounded transition-all ${
                  isDownloadingAny
                    ? 'bg-sky-500/20 text-sky-400 font-bold ring-1 ring-sky-500/40 animate-pulse'
                    : hasAnyReady || isIngestingAny
                    ? 'bg-emerald-500/10 text-emerald-400 font-medium'
                    : 'text-sat-dim bg-sat-panel/40'
                }`}
              >
                {isDownloadingAny ? <Loader2 className="h-3 w-3 animate-spin" /> : (hasAnyReady || isIngestingAny) ? <CheckCircle className="h-3 w-3 text-emerald-400" /> : null}
                Downloading
              </span>

              <span className="text-sat-dim/40">→</span>

              {/* 3. Ingesting */}
              <span
                className={`flex items-center gap-1 px-2 py-0.5 rounded transition-all ${
                  isIngestingAny
                    ? 'bg-amber-500/20 text-amber-300 font-bold ring-1 ring-amber-500/40 animate-pulse'
                    : hasAnyReady
                    ? 'bg-emerald-500/10 text-emerald-400 font-medium'
                    : 'text-sat-dim bg-sat-panel/40'
                }`}
              >
                {isIngestingAny ? <Loader2 className="h-3 w-3 animate-spin text-amber-400" /> : hasAnyReady ? <CheckCircle className="h-3 w-3 text-emerald-400" /> : null}
                Ingesting
              </span>

              <span className="text-sat-dim/40">→</span>

              {/* 4. Ready */}
              <span
                className={`flex items-center gap-1 px-2 py-0.5 rounded transition-all ${
                  hasAnyReady
                    ? 'bg-emerald-500/20 text-emerald-300 font-bold ring-1 ring-emerald-500/50'
                    : 'text-sat-dim bg-sat-panel/40'
                }`}
              >
                {hasAnyReady && <CheckCircle className="h-3 w-3 text-emerald-400" />}
                Ready
              </span>
            </div>
          </div>

          {hasAnyReady && (
            <span className="text-[10px] font-semibold text-emerald-400 flex items-center gap-1">
              <CheckCircle className="h-3 w-3" /> Ready for analysis
            </span>
          )}
        </div>

        {/* Modal Body */}
        <div className="grid flex-1 grid-cols-1 md:grid-cols-12 overflow-y-auto">
          {/* Search Form (Left column) */}
          <form onSubmit={handleSearch} className="md:col-span-5 border-r border-sat-border bg-sat-bg/60 p-5 space-y-4">
            {/* Provider Selector */}
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-sat-dim mb-1.5 flex items-center gap-1.5">
                <Radio className="h-3.5 w-3.5 text-sat-accent" />
                Satellite Data Provider
              </label>

              {isLoadingProviders ? (
                <div className="flex items-center gap-2 rounded-lg border border-sat-border bg-sat-panel/90 px-3 py-2 text-xs text-sat-muted">
                  <Loader2 className="h-3.5 w-3.5 animate-spin text-sat-accent" />
                  <span>Loading providers from /api/data/providers...</span>
                </div>
              ) : providersError ? (
                <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-2.5 text-xs text-rose-300">
                  {providersError}
                </div>
              ) : providers.length === 0 ? (
                <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-2.5 text-xs text-amber-300">
                  No satellite providers returned from backend.
                </div>
              ) : (
                <select
                  value={selectedProviderId}
                  onChange={(e) => handleProviderChange(e.target.value)}
                  className="w-full rounded-lg border border-sat-border bg-sat-panel/90 px-3 py-2 text-xs text-sat-text focus:border-sat-accent focus:outline-none"
                >
                  {providers.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} {p.is_configured === false ? '— (Not Configured)' : '— (Ready)'}
                    </option>
                  ))}
                </select>
              )}
            </div>

            {/* Provider Not Configured Notification */}
            {!isLoadingProviders && currentProvider && !isProviderConfigured && (
              <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-200 space-y-1">
                <div className="flex items-center gap-1.5 font-bold text-amber-300">
                  <AlertCircle className="h-4 w-4 shrink-0 text-amber-400" />
                  <span>Provider Not Configured</span>
                </div>
                <p className="text-[11px] text-amber-300/80 leading-relaxed">
                  {currentProvider.message ||
                    `Credentials for ${currentProvider.name} are not configured on the backend. Search and live downloads are disabled until credentials are configured.`}
                </p>
              </div>
            )}

            {/* Collection Selector */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-bold uppercase tracking-wider text-sat-dim">
                  Mission / Sensor Collection
                </label>
                {isProviderSpecificConfig ? (
                  <span
                    className="text-[10px] font-semibold text-sat-dim bg-sat-panel/80 border border-sat-border/70 px-1.5 py-0.5 rounded"
                    title="Backend did not provide collection information; using provider-specific configuration."
                  >
                    Provider Configuration
                  </span>
                ) : availableCollections.length > 0 ? (
                  <span className="text-[10px] font-semibold text-sat-accent/80">
                    {availableCollections.length} available
                  </span>
                ) : null}
              </div>

              {availableCollections.length > 0 ? (
                <select
                  value={selectedCollection}
                  onChange={(e) => setSelectedCollection(e.target.value)}
                  className="w-full rounded-lg border border-sat-border bg-sat-panel/90 px-3 py-2 text-xs text-sat-text focus:border-sat-accent focus:outline-none"
                >
                  {availableCollections.map((col) => (
                    <option key={col.id} value={col.id}>
                      {col.label}
                    </option>
                  ))}
                </select>
              ) : (
                <div className="rounded-lg border border-sat-border/60 bg-sat-panel/40 px-3 py-2 text-xs text-sat-muted">
                  No collections available for {currentProvider?.name || 'this provider'}.
                </div>
              )}

              {isProviderSpecificConfig && currentProvider && (
                <p className="mt-1 text-[10px] text-sat-dim">
                  Provider-specific collection configuration for {currentProvider.name}.
                </p>
              )}
            </div>

            {/* Presets */}
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-sat-dim mb-1.5">
                Quick AOI Presets
              </label>
              <div className="flex flex-wrap gap-1.5">
                {PRESET_AOIS.map((preset) => (
                  <button
                    key={preset.name}
                    type="button"
                    onClick={() => handleApplyPreset(preset)}
                    className="rounded border border-sat-border bg-sat-panel/60 px-2 py-1 text-[11px] text-sat-muted hover:border-sat-accent hover:text-sat-accent transition-colors"
                  >
                    {preset.name}
                  </button>
                ))}
              </div>
            </div>

            {/* Bounding Box */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-bold uppercase tracking-wider text-sat-dim flex items-center gap-1.5">
                  <MapPin className="h-3.5 w-3.5 text-sat-accent" />
                  Bounding Box (Min Lon, Min Lat, Max Lon, Max Lat)
                </label>
                <span className="text-[10px] text-sat-dim/70">[-180..180, -90..90]</span>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <div className="text-[10px] text-sat-dim mb-0.5">Min Longitude</div>
                  <input
                    type="text"
                    placeholder="-180 to 180"
                    value={minLon}
                    onChange={(e) => {
                      setMinLon(e.target.value);
                      if (coordErrors.minLon) setCoordErrors((prev) => ({ ...prev, minLon: undefined }));
                    }}
                    className={`w-full rounded border px-2.5 py-1.5 text-xs text-sat-text focus:outline-none transition-colors ${
                      coordErrors.minLon
                        ? 'border-rose-500 bg-rose-500/10 focus:border-rose-400'
                        : 'border-sat-border bg-sat-panel/80 focus:border-sat-accent'
                    }`}
                    required
                  />
                  {coordErrors.minLon && (
                    <span className="text-[10px] text-rose-400 mt-0.5 block">{coordErrors.minLon}</span>
                  )}
                </div>
                <div>
                  <div className="text-[10px] text-sat-dim mb-0.5">Min Latitude</div>
                  <input
                    type="text"
                    placeholder="-90 to 90"
                    value={minLat}
                    onChange={(e) => {
                      setMinLat(e.target.value);
                      if (coordErrors.minLat) setCoordErrors((prev) => ({ ...prev, minLat: undefined }));
                    }}
                    className={`w-full rounded border px-2.5 py-1.5 text-xs text-sat-text focus:outline-none transition-colors ${
                      coordErrors.minLat
                        ? 'border-rose-500 bg-rose-500/10 focus:border-rose-400'
                        : 'border-sat-border bg-sat-panel/80 focus:border-sat-accent'
                    }`}
                    required
                  />
                  {coordErrors.minLat && (
                    <span className="text-[10px] text-rose-400 mt-0.5 block">{coordErrors.minLat}</span>
                  )}
                </div>
                <div>
                  <div className="text-[10px] text-sat-dim mb-0.5">Max Longitude</div>
                  <input
                    type="text"
                    placeholder="-180 to 180"
                    value={maxLon}
                    onChange={(e) => {
                      setMaxLon(e.target.value);
                      if (coordErrors.maxLon) setCoordErrors((prev) => ({ ...prev, maxLon: undefined }));
                    }}
                    className={`w-full rounded border px-2.5 py-1.5 text-xs text-sat-text focus:outline-none transition-colors ${
                      coordErrors.maxLon
                        ? 'border-rose-500 bg-rose-500/10 focus:border-rose-400'
                        : 'border-sat-border bg-sat-panel/80 focus:border-sat-accent'
                    }`}
                    required
                  />
                  {coordErrors.maxLon && (
                    <span className="text-[10px] text-rose-400 mt-0.5 block">{coordErrors.maxLon}</span>
                  )}
                </div>
                <div>
                  <div className="text-[10px] text-sat-dim mb-0.5">Max Latitude</div>
                  <input
                    type="text"
                    placeholder="-90 to 90"
                    value={maxLat}
                    onChange={(e) => {
                      setMaxLat(e.target.value);
                      if (coordErrors.maxLat) setCoordErrors((prev) => ({ ...prev, maxLat: undefined }));
                    }}
                    className={`w-full rounded border px-2.5 py-1.5 text-xs text-sat-text focus:outline-none transition-colors ${
                      coordErrors.maxLat
                        ? 'border-rose-500 bg-rose-500/10 focus:border-rose-400'
                        : 'border-sat-border bg-sat-panel/80 focus:border-sat-accent'
                    }`}
                    required
                  />
                  {coordErrors.maxLat && (
                    <span className="text-[10px] text-rose-400 mt-0.5 block">{coordErrors.maxLat}</span>
                  )}
                </div>
              </div>
            </div>

            {/* Date Range */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-bold uppercase tracking-wider text-sat-dim flex items-center gap-1">
                  <Calendar className="h-3 w-3 text-sat-accent" /> Date Range (From / To)
                </span>
                <span className="text-[10px] text-sat-dim/70">From ≤ To</span>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-[10px] text-sat-dim mb-0.5">Start Date</label>
                  <input
                    type="date"
                    value={dateFrom}
                    onChange={(e) => {
                      setDateFrom(e.target.value);
                      if (dateErrors.dateFrom || dateErrors.dateTo) setDateErrors({});
                    }}
                    className={`w-full rounded border px-2.5 py-1.5 text-xs text-sat-text focus:outline-none transition-colors ${
                      dateErrors.dateFrom
                        ? 'border-rose-500 bg-rose-500/10 focus:border-rose-400'
                        : 'border-sat-border bg-sat-panel/80 focus:border-sat-accent'
                    }`}
                  />
                  {dateErrors.dateFrom && (
                    <span className="text-[10px] text-rose-400 mt-0.5 block">{dateErrors.dateFrom}</span>
                  )}
                </div>
                <div>
                  <label className="block text-[10px] text-sat-dim mb-0.5">End Date</label>
                  <input
                    type="date"
                    value={dateTo}
                    onChange={(e) => {
                      setDateTo(e.target.value);
                      if (dateErrors.dateFrom || dateErrors.dateTo) setDateErrors({});
                    }}
                    className={`w-full rounded border px-2.5 py-1.5 text-xs text-sat-text focus:outline-none transition-colors ${
                      dateErrors.dateTo
                        ? 'border-rose-500 bg-rose-500/10 focus:border-rose-400'
                        : 'border-sat-border bg-sat-panel/80 focus:border-sat-accent'
                    }`}
                  />
                  {dateErrors.dateTo && (
                    <span className="text-[10px] text-rose-400 mt-0.5 block">{dateErrors.dateTo}</span>
                  )}
                </div>
              </div>
            </div>

            {/* Search Submit Button */}
            <button
              type="submit"
              disabled={
                isSearching ||
                !isProviderConfigured ||
                isLoadingProviders ||
                !selectedCollection ||
                availableCollections.length === 0
              }
              className="w-full flex items-center justify-center gap-2 rounded-lg border border-sat-accent bg-sat-accent/20 py-2.5 text-xs font-bold text-sat-accent hover:bg-sat-accent/30 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg"
              title={
                !isProviderConfigured
                  ? 'Search is disabled: selected provider credentials are not configured on backend.'
                  : availableCollections.length === 0
                  ? 'Search is disabled: no collections available for this provider.'
                  : 'Search Satellite Products'
              }
            >
              {isSearching ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Searching {currentProvider?.name || 'Catalogue'}...
                </>
              ) : (
                <>
                  <Search className="h-4 w-4" />
                  Search Satellite Products
                </>
              )}
            </button>
          </form>

          {/* Results List (Right column) */}
          <div className="md:col-span-7 flex flex-col p-5 bg-sat-surface/40">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-bold uppercase tracking-wider text-sat-text flex items-center gap-1.5">
                <Database className="h-4 w-4 text-sat-accent" />
                Found Products ({searchResults.length})
              </span>
            </div>

            {searchError && (
              <div className="mb-3 flex items-start gap-2.5 rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-300">
                <AlertCircle className="h-4 w-4 shrink-0 mt-0.5 text-rose-400" />
                <span>{searchError}</span>
              </div>
            )}

            {successMessage && (
              <div className="mb-3 flex items-center gap-2.5 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-emerald-300">
                <CheckCircle className="h-4 w-4 text-emerald-400" />
                <span>{successMessage}</span>
              </div>
            )}

            {searchResults.length === 0 && !isSearching && !searchError && (
              <div className="flex flex-1 flex-col items-center justify-center text-center p-8 text-sat-muted">
                <Satellite className="h-10 w-10 text-sat-dim/60 mb-2" />
                <div className="text-xs font-medium">Select criteria and click Search Satellite Products</div>
                <div className="text-[11px] text-sat-dim mt-1">
                  Products returned directly from {currentProvider?.name || 'the selected satellite provider'} will appear here for download.
                </div>
              </div>
            )}

            <div className="space-y-3 overflow-y-auto max-h-[50vh] pr-1">
              {searchResults.map((product) => {
                const statusInfo = productStatuses[product.product_id] || { state: 'idle' };

                return (
                  <div
                    key={product.product_id}
                    className={`rounded-lg border bg-sat-panel/60 p-3.5 transition-all flex flex-col justify-between gap-3 ${
                      statusInfo.state === 'ready'
                        ? 'border-emerald-500/50 bg-emerald-500/[0.04]'
                        : statusInfo.state === 'failed'
                        ? 'border-rose-500/40 bg-rose-500/[0.04]'
                        : 'border-sat-border hover:border-sat-accent/40'
                    }`}
                  >
                    <div>
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-xs font-bold text-sat-text truncate">
                          {product.product_id}
                        </span>
                        <span className="shrink-0 rounded border border-sat-accent/30 bg-sat-accent/10 px-1.5 py-0.5 text-[10px] font-bold text-sat-accent uppercase">
                          {product.platform || product.collection}
                        </span>
                      </div>

                      <div className="mt-2 grid grid-cols-2 gap-x-2 gap-y-1 text-[11px] text-sat-muted">
                        <div>
                          <span className="text-sat-dim">Date:</span> {product.datetime ? product.datetime.substring(0, 10) : 'N/A'}
                        </div>
                        <div>
                          <span className="text-sat-dim">Sensor:</span> {product.instrument || 'N/A'}
                        </div>
                        <div>
                          <span className="text-sat-dim">Cloud:</span>{' '}
                          {product.cloud_cover !== null && product.cloud_cover !== undefined ? `${product.cloud_cover}%` : 'N/A'}
                        </div>
                        <div>
                          <span className="text-sat-dim">Direct DL:</span>{' '}
                          <span className={product.is_downloadable ? 'text-sat-stable' : 'text-amber-400'}>
                            {product.is_downloadable ? 'Available' : 'Restricted'}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Action & Lifecycle Status */}
                    <div className="flex flex-col gap-2 pt-2 border-t border-sat-border/40">
                      <div className="flex items-center justify-between gap-2">
                        {/* State Description */}
                        <div className="text-[11px]">
                          {statusInfo.state === 'downloading' && (
                            <span className="text-sky-400 font-medium flex items-center gap-1">
                              <Loader2 className="h-3.5 w-3.5 animate-spin" /> Fetching raw archive...
                            </span>
                          )}
                          {statusInfo.state === 'ingesting' && (
                            <span className="text-amber-300 font-medium flex items-center gap-1">
                              <Loader2 className="h-3.5 w-3.5 animate-spin text-amber-400" /> Ingesting & extracting rasters...
                            </span>
                          )}
                          {statusInfo.state === 'ready' && (
                            <span className="text-emerald-400 font-semibold flex items-center gap-1">
                              <CheckCircle className="h-3.5 w-3.5 text-emerald-400" /> Ingestion confirmed
                            </span>
                          )}
                          {statusInfo.state === 'failed' && (
                            <span className="text-rose-400 font-medium flex items-center gap-1">
                              <AlertCircle className="h-3.5 w-3.5 text-rose-400" /> Download/Ingest failed
                            </span>
                          )}
                          {statusInfo.state === 'idle' && (
                            <span className="text-sat-dim text-[10px]">
                              {product.is_downloadable ? 'Ready to materialize from provider' : 'Provider restricted'}
                            </span>
                          )}
                        </div>

                        {/* Action Control */}
                        <div>
                          {statusInfo.state === 'idle' && (
                            <button
                              type="button"
                              disabled={!product.is_downloadable || activeDownloadId !== null}
                              onClick={() => handleDownloadAndIngest(product)}
                              className="flex items-center gap-1.5 rounded-md border border-sat-accent/40 bg-sat-accent/10 px-3 py-1.5 text-xs font-bold text-sat-accent hover:bg-sat-accent/20 disabled:opacity-50 transition-colors shadow-sm"
                            >
                              <Download className="h-3.5 w-3.5" />
                              Download & Ingest
                            </button>
                          )}

                          {statusInfo.state === 'downloading' && (
                            <div className="flex items-center gap-1.5 rounded-md border border-sky-500/40 bg-sky-500/10 px-3 py-1.5 text-xs font-bold text-sky-400">
                              <Loader2 className="h-3.5 w-3.5 animate-spin" />
                              Downloading...
                            </div>
                          )}

                          {statusInfo.state === 'ingesting' && (
                            <div className="flex items-center gap-1.5 rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-1.5 text-xs font-bold text-amber-300">
                              <Loader2 className="h-3.5 w-3.5 animate-spin text-amber-400" />
                              Ingesting...
                            </div>
                          )}

                          {statusInfo.state === 'ready' && (
                            <div className="flex items-center gap-2">
                              <div className="flex items-center gap-1.5 rounded-md border border-emerald-500/50 bg-emerald-500/20 px-3 py-1.5 text-xs font-bold text-emerald-300 shadow-sm">
                                <CheckCircle className="h-3.5 w-3.5 text-emerald-400" />
                                Ready for analysis
                              </div>
                              <button
                                type="button"
                                onClick={onClose}
                                className="text-[11px] font-semibold text-sat-dim hover:text-sat-accent underline transition-colors"
                              >
                                View in Workspace
                              </button>
                            </div>
                          )}

                          {statusInfo.state === 'failed' && (
                            <button
                              type="button"
                              disabled={activeDownloadId !== null}
                              onClick={() => handleDownloadAndIngest(product)}
                              className="flex items-center gap-1.5 rounded-md border border-rose-500/40 bg-rose-500/10 px-3 py-1.5 text-xs font-bold text-rose-300 hover:bg-rose-500/20 transition-colors"
                            >
                              Retry
                            </button>
                          )}
                        </div>
                      </div>

                      {/* Confirmed Local Analysis Asset Snippet (Shown ONLY after backend confirms successful ingestion) */}
                      {statusInfo.state === 'ready' && statusInfo.analysisAsset && (
                        <div className="text-[10px] font-mono text-emerald-300 bg-emerald-950/40 border border-emerald-500/30 rounded p-2 flex items-center justify-between gap-2 break-all">
                          <span><span className="font-bold text-emerald-400">Analysis Asset:</span> {statusInfo.analysisAsset}</span>
                          <span className="shrink-0 text-[9px] font-bold uppercase tracking-wider text-emerald-300 bg-emerald-500/20 border border-emerald-500/40 px-1.5 py-0.5 rounded">
                            Verified Local Asset
                          </span>
                        </div>
                      )}

                      {/* Error details on failure (Actual error, no simulated success) */}
                      {statusInfo.state === 'failed' && statusInfo.error && (
                        <div className="text-[11px] font-mono text-rose-300 bg-rose-950/40 border border-rose-500/30 rounded p-2 flex items-start gap-1.5">
                          <AlertCircle className="h-3.5 w-3.5 text-rose-400 shrink-0 mt-0.5" />
                          <span className="break-all">{statusInfo.error}</span>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};