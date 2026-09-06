import React, { useState } from 'react';
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
} from 'lucide-react';
import { satQueryService } from '../../services/satQueryService';
import type { Observation } from '../../types/satquery';

interface SatelliteSearchModalProps {
  isOpen: boolean;
  onClose: () => void;
  onObservationAdded?: (observation: Observation) => void;
}

const ISRO_COLLECTIONS = [
  { id: 'RESOURCESAT-2A', label: 'Resourcesat-2A (LISS-4 / LISS-3 / AWiFS)', type: 'Optical' },
  { id: 'RESOURCESAT-2', label: 'Resourcesat-2 (LISS-4 / LISS-3)', type: 'Optical' },
  { id: 'CARTOSAT-2', label: 'Cartosat-2 (High-Res Panchromatic/MX)', type: 'Optical' },
  { id: 'EOS-04', label: 'EOS-04 / RISAT-1 (C-Band Radar SAR)', type: 'SAR' },
  { id: 'EOS-06', label: 'EOS-06 (Ocean Colour Monitor OCM-3)', type: 'Multispectral' },
];

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
}) => {
  const [provider] = useState('bhoonidhi');
  const [selectedCollection, setSelectedCollection] = useState('RESOURCESAT-2A');
  const [dateFrom, setDateFrom] = useState('2024-01-01');
  const [dateTo, setDateTo] = useState('2026-08-30');
  const [minLon, setMinLon] = useState('77.45');
  const [minLat, setMinLat] = useState('12.85');
  const [maxLon, setMaxLon] = useState('77.75');
  const [maxLat, setMaxLat] = useState('13.15');

  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleApplyPreset = (preset: typeof PRESET_AOIS[0]) => {
    setMinLon(preset.bbox[0].toString());
    setMinLat(preset.bbox[1].toString());
    setMaxLon(preset.bbox[2].toString());
    setMaxLat(preset.bbox[3].toString());
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSearching(true);
    setSearchError(null);
    setSearchResults([]);
    setSuccessMessage(null);

    try {
      const bbox: [number, number, number, number] = [
        parseFloat(minLon),
        parseFloat(minLat),
        parseFloat(maxLon),
        parseFloat(maxLat),
      ];

      const datetimeRange = dateFrom && dateTo ? `${dateFrom}/${dateTo}` : undefined;
      const resp = await satQueryService.searchSatelliteData({
        provider,
        collections: [selectedCollection],
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

  const handleDownloadAndIngest = async (product: any) => {
    setDownloadingId(product.product_id);
    setSearchError(null);

    try {
      const newObs = await satQueryService.downloadSatelliteProduct({
        productId: product.product_id,
        provider: 'bhoonidhi',
        collection: product.collection || selectedCollection,
      });

      setSuccessMessage(`Successfully fetched & ingested product ${product.product_id}!`);
      onObservationAdded?.(newObs);
      setTimeout(() => {
        onClose();
      }, 1200);
    } catch (err: any) {
      console.error('Download and ingestion failed:', err);
      setSearchError(err?.message || 'Download failed from ISRO Bhoonidhi.');
    } finally {
      setDownloadingId(null);
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
                Fetch Satellite Data — ISRO Bhoonidhi
                <span className="rounded-full border border-sat-accent/30 bg-sat-accent/10 px-2 py-0.5 text-[10px] font-bold text-sat-accent uppercase">
                  Web Provider
                </span>
              </h2>
              <p className="text-xs text-sat-muted">
                Search and download genuine remote sensing observations from the ISRO / NRSC Bhoonidhi Catalogue.
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

        {/* Modal Body */}
        <div className="grid flex-1 grid-cols-1 md:grid-cols-12 overflow-y-auto">
          {/* Search Form (Left column) */}
          <form onSubmit={handleSearch} className="md:col-span-5 border-r border-sat-border bg-sat-bg/60 p-5 space-y-4">
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-sat-dim mb-1.5">
                Satellite / Mission Collection
              </label>
              <select
                value={selectedCollection}
                onChange={(e) => setSelectedCollection(e.target.value)}
                className="w-full rounded-lg border border-sat-border bg-sat-panel/90 px-3 py-2 text-xs text-sat-text focus:border-sat-accent focus:outline-none"
              >
                {ISRO_COLLECTIONS.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-sat-dim mb-1.5">
                Quick AOI Presets (India)
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

            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-sat-dim mb-1.5 flex items-center gap-1.5">
                <MapPin className="h-3.5 w-3.5 text-sat-accent" />
                Bounding Box (Min Lon, Min Lat, Max Lon, Max Lat)
              </label>
              <div className="grid grid-cols-2 gap-2">
                <input
                  type="text"
                  placeholder="Min Lon"
                  value={minLon}
                  onChange={(e) => setMinLon(e.target.value)}
                  className="rounded border border-sat-border bg-sat-panel/80 px-2.5 py-1.5 text-xs text-sat-text focus:border-sat-accent focus:outline-none"
                  required
                />
                <input
                  type="text"
                  placeholder="Min Lat"
                  value={minLat}
                  onChange={(e) => setMinLat(e.target.value)}
                  className="rounded border border-sat-border bg-sat-panel/80 px-2.5 py-1.5 text-xs text-sat-text focus:border-sat-accent focus:outline-none"
                  required
                />
                <input
                  type="text"
                  placeholder="Max Lon"
                  value={maxLon}
                  onChange={(e) => setMaxLon(e.target.value)}
                  className="rounded border border-sat-border bg-sat-panel/80 px-2.5 py-1.5 text-xs text-sat-text focus:border-sat-accent focus:outline-none"
                  required
                />
                <input
                  type="text"
                  placeholder="Max Lat"
                  value={maxLat}
                  onChange={(e) => setMaxLat(e.target.value)}
                  className="rounded border border-sat-border bg-sat-panel/80 px-2.5 py-1.5 text-xs text-sat-text focus:border-sat-accent focus:outline-none"
                  required
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-sat-dim mb-1 flex items-center gap-1">
                  <Calendar className="h-3 w-3 text-sat-accent" /> From
                </label>
                <input
                  type="date"
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
                  className="w-full rounded border border-sat-border bg-sat-panel/80 px-2.5 py-1.5 text-xs text-sat-text focus:border-sat-accent focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-sat-dim mb-1 flex items-center gap-1">
                  <Calendar className="h-3 w-3 text-sat-accent" /> To
                </label>
                <input
                  type="date"
                  value={dateTo}
                  onChange={(e) => setDateTo(e.target.value)}
                  className="w-full rounded border border-sat-border bg-sat-panel/80 px-2.5 py-1.5 text-xs text-sat-text focus:border-sat-accent focus:outline-none"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isSearching}
              className="w-full flex items-center justify-center gap-2 rounded-lg border border-sat-accent bg-sat-accent/20 py-2.5 text-xs font-bold text-sat-accent hover:bg-sat-accent/30 disabled:opacity-50 transition-all shadow-lg"
            >
              {isSearching ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Searching Bhoonidhi Hub...
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
                  Products returned directly from ISRO Bhoonidhi will appear here for download.
                </div>
              </div>
            )}

            <div className="space-y-3 overflow-y-auto max-h-[50vh] pr-1">
              {searchResults.map((product) => (
                <div
                  key={product.product_id}
                  className="rounded-lg border border-sat-border bg-sat-panel/60 p-3.5 hover:border-sat-accent/40 transition-all flex flex-col justify-between gap-3"
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
                        <span className="text-sat-dim">Date:</span> {product.datetime?.substring(0, 10)}
                      </div>
                      <div>
                        <span className="text-sat-dim">Sensor:</span> {product.instrument || 'Multispectral'}
                      </div>
                      <div>
                        <span className="text-sat-dim">Cloud:</span>{' '}
                        {product.cloud_cover !== null ? `${product.cloud_cover}%` : 'N/A'}
                      </div>
                      <div>
                        <span className="text-sat-dim">Direct DL:</span>{' '}
                        <span className={product.is_downloadable ? 'text-sat-stable' : 'text-amber-400'}>
                          {product.is_downloadable ? 'Available' : 'Restricted'}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center justify-end gap-2 pt-2 border-t border-sat-border/40">
                    <button
                      type="button"
                      disabled={downloadingId === product.product_id || !product.is_downloadable}
                      onClick={() => handleDownloadAndIngest(product)}
                      className="flex items-center gap-1.5 rounded-md border border-sat-accent/40 bg-sat-accent/10 px-3 py-1.5 text-xs font-bold text-sat-accent hover:bg-sat-accent/20 disabled:opacity-50 transition-colors"
                    >
                      {downloadingId === product.product_id ? (
                        <>
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          Ingesting...
                        </>
                      ) : (
                        <>
                          <Download className="h-3.5 w-3.5" />
                          Download & Ingest
                        </>
                      )}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};