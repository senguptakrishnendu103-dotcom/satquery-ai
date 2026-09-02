import React, { useState } from 'react';
import {
  X,
  Search,
  Satellite,
  MapPin,
  Cloud,
  Upload,
  CheckCircle2,
  AlertCircle,
  Loader2,
  ExternalLink,
  Database,
  Filter,
  Check,
  Plus
} from 'lucide-react';
import { satQueryService } from '../../services/satQueryService';
import type { ModalityType } from '../../types/satquery';

interface SatelliteSearchModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAddObservation: (file: File, modality: ModalityType) => void;
  onAddProductAsObservation?: (product: any) => void;
}

const PRESET_LOCATIONS = [
  { name: 'Amazon Rainforest, Brazil', bbox: [-60.5, -3.2, -59.8, -2.5] as [number, number, number, number] },
  { name: 'Dubai Coast & Reclamation', bbox: [55.15, 25.05, 55.35, 25.25] as [number, number, number, number] },
  { name: 'Sundarbans Delta, India', bbox: [88.5, 21.6, 89.2, 22.2] as [number, number, number, number] },
  { name: 'London Metropolitan Area', bbox: [-0.35, 51.35, 0.15, 51.65] as [number, number, number, number] },
];

export const SatelliteSearchModal: React.FC<SatelliteSearchModalProps> = ({
  isOpen,
  onClose,
  onAddObservation,
  onAddProductAsObservation,
}) => {
  const [activeTab, setActiveTab] = useState<'catalogue' | 'file'>('catalogue');

  // Catalogue search state
  const [selectedCollection, setSelectedCollection] = useState<string>('sentinel-2-l2a');
  const [startDate, setStartDate] = useState<string>('2024-08-01');
  const [endDate, setEndDate] = useState<string>('2024-08-30');
  const [maxCloudCover, setMaxCloudCover] = useState<number>(20);
  const [minLon, setMinLon] = useState<number>(-60.5);
  const [minLat, setMinLat] = useState<number>(-3.2);
  const [maxLon, setMaxLon] = useState<number>(-59.8);
  const [maxLat, setMaxLat] = useState<number>(-2.5);

  const [isSearching, setIsSearching] = useState<boolean>(false);
  const [searchResults, setSearchResults] = useState<any[] | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [ingestedId, setIngestedId] = useState<string | null>(null);

  // File upload state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [modality, setModality] = useState<ModalityType>('OPTICAL');

  if (!isOpen) return null;

  const handleSelectPresetLocation = (bbox: [number, number, number, number]) => {
    setMinLon(bbox[0]);
    setMinLat(bbox[1]);
    setMaxLon(bbox[2]);
    setMaxLat(bbox[3]);
  };

  const handleExecuteSearch = async () => {
    setIsSearching(true);
    setErrorMsg(null);
    setSearchResults(null);

    try {
      const data = await satQueryService.searchSatelliteCatalogue({
        provider: 'copernicus',
        bbox: [minLon, minLat, maxLon, maxLat],
        start_date: startDate,
        end_date: endDate,
        collection: selectedCollection,
        max_cloud_cover: selectedCollection.includes('sentinel-2') ? maxCloudCover : undefined,
        limit: 10,
      });

      setSearchResults(data.products || []);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to search CDSE Copernicus catalogue.');
    } finally {
      setIsSearching(false);
    }
  };

  const handleIngestProduct = (prod: any) => {
    setIngestedId(prod.product_id);
    if (onAddProductAsObservation) {
      onAddProductAsObservation(prod);
    }
    setTimeout(() => {
      onClose();
      setIngestedId(null);
    }, 600);
  };

  const handleFileDrop = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleUploadSubmit = () => {
    if (selectedFile) {
      onAddObservation(selectedFile, modality);
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-sat-bg/80 backdrop-blur-md p-4 animate-in fade-in duration-200">
      <div className="relative w-full max-w-4xl max-h-[90vh] flex flex-col rounded-xl border border-sat-border bg-sat-surface/95 shadow-2xl shadow-sat-accent/10 overflow-hidden font-sans">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-sat-border bg-sat-panel/80 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-sat-accent/30 bg-sat-accent/10 text-sat-accent">
              <Database className="h-5 w-5" />
            </div>
            <div>
              <h2 className="font-display text-base font-bold uppercase tracking-wider text-sat-text">
                Ingest & Discover Satellite Data
              </h2>
              <p className="font-mono text-[9px] text-sat-dim uppercase tracking-wider">
                Copernicus Data Space Ecosystem (CDSE) Live Integration
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="rounded-lg p-2 text-sat-dim transition-colors hover:bg-sat-border/40 hover:text-sat-text"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Navigation Tabs */}
        <div className="flex border-b border-sat-border bg-sat-bg/60 px-6 pt-2">
          <button
            onClick={() => setActiveTab('catalogue')}
            className={`flex items-center gap-2 border-b-2 px-4 py-3 font-mono text-xs font-bold uppercase tracking-wider transition-all ${
              activeTab === 'catalogue'
                ? 'border-sat-accent text-sat-accent bg-sat-accent/5'
                : 'border-transparent text-sat-dim hover:text-sat-text'
            }`}
          >
            <Satellite className="h-4 w-4" />
            Live Catalogue Search (CDSE)
          </button>

          <button
            onClick={() => setActiveTab('file')}
            className={`flex items-center gap-2 border-b-2 px-4 py-3 font-mono text-xs font-bold uppercase tracking-wider transition-all ${
              activeTab === 'file'
                ? 'border-sat-accent text-sat-accent bg-sat-accent/5'
                : 'border-transparent text-sat-dim hover:text-sat-text'
            }`}
          >
            <Upload className="h-4 w-4" />
            Upload Local Raster Image
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {activeTab === 'catalogue' ? (
            <div className="space-y-6">
              {/* Presets */}
              <div>
                <label className="block font-mono text-[10px] font-bold uppercase tracking-wider text-sat-dim mb-2 flex items-center gap-1.5">
                  <MapPin className="h-3.5 w-3.5 text-sat-accent" />
                  Target Region Presets (WGS84 Bounding Box)
                </label>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                  {PRESET_LOCATIONS.map((preset) => (
                    <button
                      key={preset.name}
                      onClick={() => handleSelectPresetLocation(preset.bbox)}
                      className="rounded-lg border border-sat-border bg-sat-bg/80 p-2.5 text-left transition-all hover:border-sat-accent/40 hover:bg-sat-accent/5"
                    >
                      <div className="font-mono text-[10px] font-bold text-sat-text truncate">
                        {preset.name}
                      </div>
                      <div className="font-mono text-[8px] text-sat-dim mt-1">
                        [{preset.bbox.join(', ')}]
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Coordinates Inputs */}
              <div className="rounded-xl border border-sat-border bg-sat-bg/50 p-4 space-y-3">
                <div className="font-mono text-[10px] font-bold uppercase tracking-wider text-sat-accent flex items-center gap-2">
                  <Filter className="h-3.5 w-3.5" />
                  Spatial & Temporal Bounding Controls
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <div>
                    <label className="block font-mono text-[8px] text-sat-dim uppercase">Min Longitude</label>
                    <input
                      type="number"
                      step="0.01"
                      value={minLon}
                      onChange={(e) => setMinLon(parseFloat(e.target.value))}
                      className="mt-1 w-full rounded border border-sat-border bg-sat-surface px-2.5 py-1.5 font-mono text-xs text-sat-text focus:border-sat-accent focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block font-mono text-[8px] text-sat-dim uppercase">Min Latitude</label>
                    <input
                      type="number"
                      step="0.01"
                      value={minLat}
                      onChange={(e) => setMinLat(parseFloat(e.target.value))}
                      className="mt-1 w-full rounded border border-sat-border bg-sat-surface px-2.5 py-1.5 font-mono text-xs text-sat-text focus:border-sat-accent focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block font-mono text-[8px] text-sat-dim uppercase">Max Longitude</label>
                    <input
                      type="number"
                      step="0.01"
                      value={maxLon}
                      onChange={(e) => setMaxLon(parseFloat(e.target.value))}
                      className="mt-1 w-full rounded border border-sat-border bg-sat-surface px-2.5 py-1.5 font-mono text-xs text-sat-text focus:border-sat-accent focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block font-mono text-[8px] text-sat-dim uppercase">Max Latitude</label>
                    <input
                      type="number"
                      step="0.01"
                      value={maxLat}
                      onChange={(e) => setMaxLat(parseFloat(e.target.value))}
                      className="mt-1 w-full rounded border border-sat-border bg-sat-surface px-2.5 py-1.5 font-mono text-xs text-sat-text focus:border-sat-accent focus:outline-none"
                    />
                  </div>
                </div>

                {/* Collection & Dates */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
                  <div>
                    <label className="block font-mono text-[9px] text-sat-dim uppercase font-bold mb-1">
                      Satellite Collection
                    </label>
                    <select
                      value={selectedCollection}
                      onChange={(e) => setSelectedCollection(e.target.value)}
                      className="w-full rounded border border-sat-border bg-sat-surface px-3 py-2 font-mono text-xs text-sat-text focus:border-sat-accent focus:outline-none"
                    >
                      <option value="sentinel-2-l2a">Sentinel-2 MSI Level-2A (Optical)</option>
                      <option value="sentinel-2-l1c">Sentinel-2 MSI Level-1C (Optical)</option>
                      <option value="sentinel-1-grd">Sentinel-1 C-SAR GRD (Radar / SAR)</option>
                    </select>
                  </div>

                  <div>
                    <label className="block font-mono text-[9px] text-sat-dim uppercase font-bold mb-1">
                      Start Date
                    </label>
                    <input
                      type="date"
                      value={startDate}
                      onChange={(e) => setStartDate(e.target.value)}
                      className="w-full rounded border border-sat-border bg-sat-surface px-3 py-2 font-mono text-xs text-sat-text focus:border-sat-accent focus:outline-none"
                    />
                  </div>

                  <div>
                    <label className="block font-mono text-[9px] text-sat-dim uppercase font-bold mb-1">
                      End Date
                    </label>
                    <input
                      type="date"
                      value={endDate}
                      onChange={(e) => setEndDate(e.target.value)}
                      className="w-full rounded border border-sat-border bg-sat-surface px-3 py-2 font-mono text-xs text-sat-text focus:border-sat-accent focus:outline-none"
                    />
                  </div>
                </div>

                {/* Cloud Cover Slider for Sentinel-2 */}
                {selectedCollection.includes('sentinel-2') && (
                  <div className="pt-2">
                    <div className="flex items-center justify-between mb-1">
                      <label className="font-mono text-[9px] font-bold text-sat-dim uppercase flex items-center gap-1.5">
                        <Cloud className="h-3 w-3 text-sat-accent" />
                        Max Allowed Cloud Cover (%)
                      </label>
                      <span className="font-mono text-xs font-bold text-sat-accent">{maxCloudCover}%</span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={maxCloudCover}
                      onChange={(e) => setMaxCloudCover(parseFloat(e.target.value))}
                      className="w-full accent-sat-accent cursor-pointer"
                    />
                  </div>
                )}
              </div>

              {/* Action Button */}
              <div className="flex justify-end">
                <button
                  onClick={handleExecuteSearch}
                  disabled={isSearching}
                  className="flex items-center gap-2 rounded-lg border border-sat-accent/50 bg-sat-accent/20 px-6 py-2.5 font-mono text-xs font-bold uppercase tracking-wider text-sat-accent transition-all hover:bg-sat-accent/30 disabled:opacity-50"
                >
                  {isSearching ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Searching CDSE Catalogue...
                    </>
                  ) : (
                    <>
                      <Search className="h-4 w-4" />
                      Search Live Copernicus Catalogue
                    </>
                  )}
                </button>
              </div>

              {/* Error Display */}
              {errorMsg && (
                <div className="flex items-center gap-3 rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-red-400 font-mono text-xs">
                  <AlertCircle className="h-5 w-5 shrink-0" />
                  <div>{errorMsg}</div>
                </div>
              )}

              {/* Search Results */}
              {searchResults && (
                <div className="space-y-4 pt-2">
                  <div className="flex items-center justify-between border-b border-sat-border pb-2">
                    <span className="font-mono text-xs font-bold text-sat-text uppercase tracking-wider">
                      Search Results ({searchResults.length} Products Found)
                    </span>
                    <span className="font-mono text-[9px] text-sat-dim">
                      Live CDSE Catalogue Response
                    </span>
                  </div>

                  {searchResults.length === 0 ? (
                    <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-6 text-center font-mono text-xs text-sat-dim space-y-4">
                      <div className="flex items-center justify-center gap-2 text-amber-400 font-bold">
                        <AlertCircle className="h-4 w-4" />
                        <span>No Satellite Scenes Found for Current Filter Criteria</span>
                      </div>
                      <p className="text-[11px] text-sat-dim max-w-lg mx-auto leading-relaxed">
                        Tropical areas like the <strong className="text-sat-text">Amazon Rainforest</strong> often have high cloud cover. 
                        A strict <strong className="text-sat-text">{maxCloudCover}% cloud cover filter</strong> or narrow date range can eliminate all available images.
                      </p>
                      
                      <div className="flex flex-wrap items-center justify-center gap-2 pt-1">
                        <button
                          onClick={() => {
                            setMaxCloudCover(60);
                            setTimeout(handleExecuteSearch, 100);
                          }}
                          className="px-3 py-1.5 rounded border border-sat-accent/40 bg-sat-accent/10 text-sat-accent font-bold text-[10px] hover:bg-sat-accent/20 transition-all flex items-center gap-1.5"
                        >
                          ⚡ Increase Cloud Cover to 60% & Retry
                        </button>
                        <button
                          onClick={() => {
                            setStartDate('2024-01-01');
                            setEndDate('2024-08-30');
                            setTimeout(handleExecuteSearch, 100);
                          }}
                          className="px-3 py-1.5 rounded border border-sat-border bg-sat-surface text-sat-text font-bold text-[10px] hover:border-sat-accent transition-all flex items-center gap-1.5"
                        >
                          📅 Expand Date Range (Jan - Aug 2024)
                        </button>
                        <button
                          onClick={() => {
                            handleSelectPresetLocation([55.15, 25.05, 55.35, 25.25]); // Dubai
                            setMaxCloudCover(15);
                            setTimeout(handleExecuteSearch, 100);
                          }}
                          className="px-3 py-1.5 rounded border border-sat-border bg-sat-surface text-sat-text font-bold text-[10px] hover:border-sat-accent transition-all flex items-center gap-1.5"
                        >
                          ☀️ Try Dubai Coast (Clear Skies)
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-[320px] overflow-y-auto pr-1">
                      {searchResults.map((prod) => (
                        <div
                          key={prod.product_id}
                          className="rounded-xl border border-sat-border bg-sat-bg/90 p-4 transition-all hover:border-sat-accent/40 space-y-2"
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div className="min-w-0">
                              <span className="inline-block rounded bg-sat-accent/10 border border-sat-accent/30 px-1.5 py-0.5 font-mono text-[8px] font-bold text-sat-accent uppercase mb-1">
                                {prod.platform || prod.collection}
                              </span>
                              <h4 className="font-mono text-xs font-bold text-sat-text truncate" title={prod.metadata?.name || prod.product_id}>
                                {prod.metadata?.name || prod.product_id}
                              </h4>
                            </div>
                            <span className="font-mono text-[9px] text-sat-dim shrink-0">
                              {prod.modality?.toUpperCase()}
                            </span>
                          </div>

                          <div className="grid grid-cols-2 gap-2 pt-1 font-mono text-[9px] text-sat-dim">
                            <div>
                              Acquired: <span className="text-sat-text">{prod.acquisition_datetime?.substring(0, 10) || 'N/A'}</span>
                            </div>
                            <div>
                              Cloud Cover: <span className="text-sat-text">{prod.cloud_cover !== null ? `${prod.cloud_cover.toFixed(1)}%` : 'N/A'}</span>
                            </div>
                            <div>
                              Instrument: <span className="text-sat-text">{prod.instrument || 'MSI'}</span>
                            </div>
                            <div>
                              Resolution: <span className="text-sat-text">{prod.resolution ? `${prod.resolution}m/px` : '10m/px'}</span>
                            </div>
                          </div>

                          <div className="pt-2 flex items-center justify-between border-t border-sat-border/60">
                            <a
                              href={prod.product_url}
                              target="_blank"
                              rel="noreferrer"
                              className="font-mono text-[8px] text-sat-dim hover:text-sat-accent flex items-center gap-1"
                            >
                              <ExternalLink className="h-3 w-3" />
                              View Metadata
                            </a>

                            <button
                              onClick={() => handleIngestProduct(prod)}
                              disabled={ingestedId === prod.product_id}
                              className="flex items-center gap-1.5 rounded border border-sat-accent/40 bg-sat-accent/10 px-3 py-1 font-mono text-[9px] font-bold text-sat-accent hover:bg-sat-accent/20 transition-all"
                            >
                              {ingestedId === prod.product_id ? (
                                <>
                                  <Check className="h-3 w-3 text-emerald-400" />
                                  Ingested!
                                </>
                              ) : (
                                <>
                                  <Plus className="h-3 w-3" />
                                  Ingest to Workspace
                                </>
                              )}
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          ) : (
            /* File Upload Tab */
            <div className="space-y-6 py-4">
              <div className="rounded-xl border-2 border-dashed border-sat-border p-8 text-center hover:border-sat-accent/50 transition-all">
                <Upload className="mx-auto h-10 w-10 text-sat-dim mb-3" />
                <h3 className="font-mono text-sm font-bold text-sat-text uppercase tracking-wider mb-1">
                  Select Local Raster or Image File
                </h3>
                <p className="font-mono text-[10px] text-sat-dim mb-4">
                  Supports GeoTIFF, TIFF, PNG, JPG, and Satellite Imagery Formats
                </p>

                <input
                  type="file"
                  onChange={handleFileDrop}
                  className="hidden"
                  id="modal-file-input"
                  accept="image/*,.tif,.tiff,.geotiff"
                />
                <label
                  htmlFor="modal-file-input"
                  className="inline-flex items-center gap-2 rounded-lg border border-sat-accent/50 bg-sat-accent/10 px-5 py-2.5 font-mono text-xs font-bold text-sat-accent uppercase tracking-wider cursor-pointer hover:bg-sat-accent/20 transition-all"
                >
                  <Upload className="h-4 w-4" />
                  Browse Disk Files
                </label>

                {selectedFile && (
                  <div className="mt-4 flex items-center justify-center gap-2 font-mono text-xs text-sat-accent">
                    <CheckCircle2 className="h-4 w-4" />
                    Selected: {selectedFile.name} ({(selectedFile.size / (1024 * 1024)).toFixed(2)} MB)
                  </div>
                )}
              </div>

              {/* Modality Selector */}
              <div>
                <label className="block font-mono text-[10px] font-bold uppercase tracking-wider text-sat-dim mb-2">
                  Select Ingestion Remote-Sensing Modality
                </label>
                <div className="grid grid-cols-3 gap-3">
                  {(['OPTICAL', 'SAR', 'MULTISPECTRAL'] as ModalityType[]).map((mod) => (
                    <button
                      key={mod}
                      onClick={() => setModality(mod)}
                      className={`rounded-lg border p-3 font-mono text-xs font-bold uppercase tracking-wider transition-all ${
                        modality === mod
                          ? 'border-sat-accent bg-sat-accent/10 text-sat-accent'
                          : 'border-sat-border text-sat-dim hover:text-sat-text'
                      }`}
                    >
                      {mod}
                    </button>
                  ))}
                </div>
              </div>

              {/* Upload Button */}
              <div className="flex justify-end pt-2">
                <button
                  onClick={handleUploadSubmit}
                  disabled={!selectedFile}
                  className="flex items-center gap-2 rounded-lg border border-sat-accent/50 bg-sat-accent/20 px-6 py-2.5 font-mono text-xs font-bold uppercase tracking-wider text-sat-accent transition-all hover:bg-sat-accent/30 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  <Upload className="h-4 w-4" />
                  Ingest Image File
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
