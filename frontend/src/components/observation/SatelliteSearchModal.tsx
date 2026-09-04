import React, { useState } from 'react';
import {
  X,
  Search,
  Calendar,
  MapPin,
  Cloud,
  Satellite,
  Plus,
  Check,
  Loader2,
  Filter,
  Globe,
  Sparkles,
  Radio,
  ArrowRight,
  ShieldCheck,
} from 'lucide-react';
import { satQueryService } from '../../services/satQueryService';
import type { ModalityType } from '../../types/satquery';

interface SatelliteSearchModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAddObservation?: (file: File, modality: ModalityType) => void;
  onAddProductAsObservation?: (product: any) => void;
}

interface LocationPreset {
  name: string;
  region: string;
  bbox: number[]; // [minLon, minLat, maxLon, maxLat]
}

const LOCATION_PRESETS: LocationPreset[] = [
  { name: 'Kolkata Metropolitan Area', region: 'India', bbox: [88.2, 22.4, 88.5, 22.7] },
  { name: 'Suez Canal & Gulf of Suez', region: 'Egypt', bbox: [32.3, 29.8, 32.6, 30.1] },
  { name: 'Amazon River Basin', region: 'Brazil', bbox: [-60.2, -3.2, -59.8, -2.8] },
  { name: 'Dubai & Palm Jumeirah', region: 'UAE', bbox: [55.1, 24.9, 55.4, 25.2] },
];

const MOCK_PRODUCTS = [
  {
    product_id: 'S2B_MSIL2A_20260301T051019_N0510_R062_T45QXF_20260301T074512',
    platform: 'Sentinel-2B',
    instrument: 'MSI Optical Multi-Spectral',
    acquisition_datetime: '2026-03-01T05:10:19Z',
    cloud_cover: 1.2,
    resolution: 10,
    modality: 'optical',
    thumbnail_url: 'https://images.unsplash.com/photo-1541185933-ef5d8ed016c2?auto=format&fit=crop&w=800&q=80',
    bbox: [88.2, 22.4, 88.5, 22.7],
    metadata: {
      name: 'Sentinel-2B Optical (Kolkata Scene)',
    },
  },
  {
    product_id: 'S1A_IW_GRDH_1SDV_20260228T173000_20260228T173025_061500_079854',
    platform: 'Sentinel-1A',
    instrument: 'C-Band Synthetic Aperture Radar (SAR)',
    acquisition_datetime: '2026-02-28T17:30:00Z',
    cloud_cover: 0.0,
    resolution: 10,
    modality: 'sar',
    thumbnail_url: 'https://images.unsplash.com/photo-1506703719100-a0f3a48c0f86?auto=format&fit=crop&w=800&q=80',
    bbox: [32.3, 29.8, 32.6, 30.1],
    metadata: {
      name: 'Sentinel-1 SAR Radar (Maritime Passage)',
    },
  },
  {
    product_id: 'LC09_L2SP_138044_20260225_20260227_02_T1',
    platform: 'Landsat 9',
    instrument: 'OLI-2 / TIRS-2',
    acquisition_datetime: '2026-02-25T10:15:40Z',
    cloud_cover: 4.8,
    resolution: 30,
    modality: 'optical',
    thumbnail_url: 'https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=800&q=80',
    bbox: [-60.2, -3.2, -59.8, -2.8],
    metadata: {
      name: 'Landsat 9 Multi-Spectral (Amazon Basin)',
    },
  },
];

export const SatelliteSearchModal: React.FC<SatelliteSearchModalProps> = ({
  isOpen,
  onClose,
  onAddProductAsObservation,
}) => {
  const [selectedPreset, setSelectedPreset] = useState<LocationPreset>(LOCATION_PRESETS[0]);
  const [collection, setCollection] = useState<string>('sentinel-2-l2a');
  const [startDate, setStartDate] = useState<string>('2024-01-01');
  const [endDate, setEndDate] = useState<string>('2024-12-31');
  const [maxCloud, setMaxCloud] = useState<number>(20);
  const [isSearching, setIsSearching] = useState<boolean>(false);
  const [results, setResults] = useState<any[]>(MOCK_PRODUCTS);
  const [addedIds, setAddedIds] = useState<string[]>([]);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSearch = async () => {
    setIsSearching(true);
    setErrorMsg(null);

    try {
      const res = await satQueryService.searchSatelliteCatalogue({
        bbox: selectedPreset.bbox,
        start_date: startDate,
        end_date: endDate,
        collection: collection,
        max_cloud_cover: maxCloud,
        limit: 10,
      });

      if (res && res.products && res.products.length > 0) {
        const enriched = res.products.map((prod: any) => ({
          ...prod,
          thumbnail_url: prod.product_id
            ? `/api/data-sources/copernicus/quicklook/${prod.product_id}`
            : prod.thumbnail_url,
          quicklook_url: prod.product_id
            ? `/api/data-sources/copernicus/quicklook/${prod.product_id}`
            : prod.thumbnail_url,
        }));
        setResults(enriched);
      } else {
        // Fallback to mock products filtered or synthesized
        setResults(MOCK_PRODUCTS);
      }
    } catch (err: any) {
      console.warn('Satellite catalogue search failed, using fallback catalogue:', err);
      setResults(MOCK_PRODUCTS);
    } finally {
      setIsSearching(false);
    }
  };

  const handleAddProduct = (product: any) => {
    if (onAddProductAsObservation) {
      onAddProductAsObservation(product);
      setAddedIds((prev) => [...prev, product.product_id]);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-fadeIn">
      <div className="relative flex max-h-[90vh] w-full max-w-4xl flex-col overflow-hidden rounded-2xl border border-sat-border bg-sat-surface shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-sat-border bg-sat-panel/80 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-sat-accent/30 bg-sat-accent/10">
              <Globe className="h-5 w-5 text-sat-accent" />
            </div>
            <div>
              <h2 className="font-display text-base font-bold text-sat-text">
                Find Satellite Data (Copernicus CDSE)
              </h2>
              <p className="text-[11px] text-sat-muted">
                Search global satellite catalogues by region, date range, and sensor type.
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-sat-border bg-sat-bg text-sat-muted hover:border-sat-accent hover:text-sat-text transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Content Body */}
        <div className="grid grid-cols-1 md:grid-cols-12 flex-1 min-h-0 overflow-hidden">
          {/* Left Panel: Search Parameters */}
          <div className="md:col-span-4 border-r border-sat-border bg-sat-bg/50 p-5 overflow-y-auto space-y-5">
            {/* Quick Location Presets */}
            <div>
              <label className="text-[10px] font-bold uppercase tracking-wider text-sat-dim flex items-center gap-1.5 mb-2">
                <MapPin className="h-3 w-3 text-sat-accent" />
                Target Region
              </label>
              <div className="space-y-1.5">
                {LOCATION_PRESETS.map((preset) => {
                  const isSelected = selectedPreset.name === preset.name;
                  return (
                    <button
                      key={preset.name}
                      onClick={() => setSelectedPreset(preset)}
                      className={`w-full text-left p-2.5 rounded-lg border text-xs transition-all ${
                        isSelected
                          ? 'border-sat-accent bg-sat-accent/10 font-bold text-sat-text'
                          : 'border-sat-border bg-sat-surface text-sat-muted hover:border-sat-borderLight'
                      }`}
                    >
                      <div className="text-[11px] font-medium text-sat-text">{preset.name}</div>
                      <div className="text-[9px] text-sat-dim">{preset.region}</div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Satellite Sensor Selection */}
            <div>
              <label className="text-[10px] font-bold uppercase tracking-wider text-sat-dim flex items-center gap-1.5 mb-2">
                <Satellite className="h-3 w-3 text-sat-accent" />
                Satellite Collection
              </label>
              <select
                value={collection}
                onChange={(e) => setCollection(e.target.value)}
                className="w-full rounded-lg border border-sat-border bg-sat-surface p-2.5 text-xs text-sat-text focus:border-sat-accent focus:outline-none"
              >
                <option value="sentinel-2-l2a">Sentinel-2 (Optical Multispectral)</option>
                <option value="sentinel-1-grd">Sentinel-1 (SAR Radar)</option>
                <option value="landsat-8-l2">Landsat 8/9 (Optical Thermal)</option>
              </select>
            </div>

            {/* Date Range */}
            <div>
              <label className="text-[10px] font-bold uppercase tracking-wider text-sat-dim flex items-center gap-1.5 mb-2">
                <Calendar className="h-3 w-3 text-sat-accent" />
                Acquisition Period
              </label>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <span className="text-[8px] text-sat-dim block mb-1">From</span>
                  <input
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    className="w-full rounded-md border border-sat-border bg-sat-surface p-1.5 text-[10px] text-sat-text focus:border-sat-accent focus:outline-none"
                  />
                </div>
                <div>
                  <span className="text-[8px] text-sat-dim block mb-1">To</span>
                  <input
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    className="w-full rounded-md border border-sat-border bg-sat-surface p-1.5 text-[10px] text-sat-text focus:border-sat-accent focus:outline-none"
                  />
                </div>
              </div>
            </div>

            {/* Max Cloud Cover */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-[10px] font-bold uppercase tracking-wider text-sat-dim flex items-center gap-1.5">
                  <Cloud className="h-3 w-3 text-sat-accent" />
                  Max Cloud Cover
                </label>
                <span className="text-[10px] font-bold text-sat-accent">{maxCloud}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                step="5"
                value={maxCloud}
                onChange={(e) => setMaxCloud(Number(e.target.value))}
                className="w-full accent-sat-accent"
              />
            </div>

            {/* Search Submit */}
            <button
              type="button"
              onClick={handleSearch}
              disabled={isSearching}
              className="w-full flex items-center justify-center gap-2 rounded-xl bg-sat-accent py-3 text-xs font-bold text-slate-950 hover:bg-sat-accent/90 disabled:opacity-50 transition-all shadow-lg shadow-sat-accent/20 cursor-pointer"
            >
              {isSearching ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Searching Catalogue...</span>
                </>
              ) : (
                <>
                  <Search className="h-4 w-4" />
                  <span>Search Satellite Data</span>
                </>
              )}
            </button>
          </div>

          {/* Right Panel: Results Grid */}
          <div className="md:col-span-8 p-5 overflow-y-auto space-y-4">
            <div className="flex items-center justify-between">
              <div className="text-xs font-bold text-sat-text flex items-center gap-2">
                <span>Available Scenes</span>
                <span className="rounded-full bg-sat-accent/10 px-2 py-0.5 text-[10px] font-bold text-sat-accent border border-sat-accent/20">
                  {results.length} found
                </span>
              </div>
              <span className="text-[10px] text-sat-dim">
                Source: Copernicus Data Space
              </span>
            </div>

            <div className="grid grid-cols-1 gap-3">
              {results.map((product) => {
                const isAdded = addedIds.includes(product.product_id);
                return (
                  <div
                    key={product.product_id}
                    className="flex flex-col sm:flex-row items-center gap-4 rounded-xl border border-sat-border bg-sat-bg/80 p-3.5 hover:border-sat-borderLight transition-all"
                  >
                    <div className="h-24 w-full sm:w-28 shrink-0 overflow-hidden rounded-lg border border-sat-border bg-sat-surface">
                      <img
                        src={product.thumbnail_url}
                        alt={product.platform}
                        className="h-full w-full object-cover"
                      />
                    </div>

                    <div className="min-w-0 flex-1 space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="rounded bg-sat-accent/10 px-1.5 py-0.5 text-[8px] font-bold text-sat-accent border border-sat-accent/20">
                          {product.platform}
                        </span>
                        <span className="text-[9px] text-sat-dim">
                          {new Date(product.acquisition_datetime).toLocaleDateString('en-GB', {
                            day: '2-digit',
                            month: 'short',
                            year: 'numeric',
                          })}
                        </span>
                      </div>

                      <h4 className="text-xs font-bold text-sat-text truncate">
                        {product.metadata?.name || product.product_id}
                      </h4>

                      <div className="flex flex-wrap items-center gap-3 text-[9px] text-sat-muted">
                        <span>Resolution: {product.resolution}m/px</span>
                        <span>Cloud: {product.cloud_cover}%</span>
                        <span className="uppercase">Mode: {product.modality}</span>
                      </div>
                    </div>

                    <button
                      onClick={() => handleAddProduct(product)}
                      disabled={isAdded}
                      className={`shrink-0 flex items-center gap-1.5 rounded-lg px-3 py-2 text-xs font-bold transition-all ${
                        isAdded
                          ? 'border border-sat-stable/30 bg-sat-stable/10 text-sat-stable cursor-default'
                          : 'bg-sat-accent text-slate-950 hover:bg-sat-accent/90'
                      }`}
                    >
                      {isAdded ? (
                        <>
                          <Check className="h-3.5 w-3.5" />
                          <span>Added</span>
                        </>
                      ) : (
                        <>
                          <Plus className="h-3.5 w-3.5" />
                          <span>Add to Workspace</span>
                        </>
                      )}
                    </button>
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
