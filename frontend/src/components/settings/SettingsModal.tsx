import React, { useState } from 'react';
import {
  Settings,
  X,
  Key,
  Cpu,
  Layers,
  FileText,
  CheckCircle2,
  Database,
  Globe,
  ShieldAlert,
  Save,
  RotateCcw,
} from 'lucide-react';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose }) => {
  const [activeTab, setActiveTab] = useState<'providers' | 'models' | 'canvas' | 'export'>('providers');

  // Provider Settings State
  const [cdseClientId, setCdseClientId] = useState<string>(
    () => localStorage.getItem('satquery_cdse_client_id') || ''
  );
  const [cdseClientSecret, setCdseClientSecret] = useState<string>(
    () => localStorage.getItem('satquery_cdse_client_secret') || ''
  );
  const [stacEndpoint, setStacEndpoint] = useState<string>(
    () => localStorage.getItem('satquery_stac_endpoint') || 'https://catalogue.dataspace.copernicus.eu/stac'
  );

  // AI Model Settings State
  const [defaultModel, setDefaultModel] = useState<string>(
    () => localStorage.getItem('satquery_default_model') || 'SatQuery-Opt-1A'
  );
  const [confidenceThreshold, setConfidenceThreshold] = useState<number>(
    () => Number(localStorage.getItem('satquery_confidence_threshold')) || 85
  );

  // Canvas Settings State
  const [gridOverlay, setGridOverlay] = useState<boolean>(
    () => localStorage.getItem('satquery_grid_overlay') !== 'false'
  );
  const [coordinateFormat, setCoordinateFormat] = useState<'decimal' | 'dms'>(
    () => (localStorage.getItem('satquery_coord_format') as 'decimal' | 'dms') || 'decimal'
  );

  // Export Settings State
  const [autoExportPdf, setAutoExportPdf] = useState<boolean>(
    () => localStorage.getItem('satquery_auto_pdf') === 'true'
  );

  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSave = () => {
    localStorage.setItem('satquery_cdse_client_id', cdseClientId);
    localStorage.setItem('satquery_cdse_client_secret', cdseClientSecret);
    localStorage.setItem('satquery_stac_endpoint', stacEndpoint);
    localStorage.setItem('satquery_default_model', defaultModel);
    localStorage.setItem('satquery_confidence_threshold', String(confidenceThreshold));
    localStorage.setItem('satquery_grid_overlay', String(gridOverlay));
    localStorage.setItem('satquery_coord_format', coordinateFormat);
    localStorage.setItem('satquery_auto_pdf', String(autoExportPdf));

    setSaveMessage('Settings successfully saved to local environment!');
    setTimeout(() => setSaveMessage(null), 3000);
  };

  const handleReset = () => {
    setCdseClientId('');
    setCdseClientSecret('');
    setStacEndpoint('https://catalogue.dataspace.copernicus.eu/stac');
    setDefaultModel('SatQuery-Opt-1A');
    setConfidenceThreshold(85);
    setGridOverlay(true);
    setCoordinateFormat('decimal');
    setAutoExportPdf(false);

    setSaveMessage('Settings reset to system defaults.');
    setTimeout(() => setSaveMessage(null), 3000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-sat-bg/85 backdrop-blur-md p-4 animate-in fade-in duration-200 selection:bg-sat-accent/30">
      <div className="relative w-full max-w-3xl max-h-[85vh] flex flex-col rounded-xl border border-sat-border bg-sat-surface/95 shadow-2xl shadow-sat-accent/10 overflow-hidden font-sans">
        
        {/* Header */}
        <div className="flex items-center justify-between border-b border-sat-border bg-sat-panel/80 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-sat-accent/30 bg-sat-accent/10 text-sat-accent">
              <Settings className="h-5 w-5 animate-spin" style={{ animationDuration: '20s' }} />
            </div>
            <div>
              <h2 className="font-display text-base font-bold uppercase tracking-wider text-sat-text">
                Platform Preferences & Engine Settings
              </h2>
              <p className="font-mono text-[9px] text-sat-dim uppercase tracking-wider">
                Geospatial AI & Remote Sensing Data Provider Configurations
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
            onClick={() => setActiveTab('providers')}
            className={`flex items-center gap-2 border-b-2 px-4 py-3 font-mono text-xs font-bold uppercase tracking-wider transition-all ${
              activeTab === 'providers'
                ? 'border-sat-accent text-sat-accent bg-sat-accent/5'
                : 'border-transparent text-sat-dim hover:text-sat-text'
            }`}
          >
            <Database className="h-4 w-4" />
            <span>Data Providers & API Keys</span>
          </button>

          <button
            onClick={() => setActiveTab('models')}
            className={`flex items-center gap-2 border-b-2 px-4 py-3 font-mono text-xs font-bold uppercase tracking-wider transition-all ${
              activeTab === 'models'
                ? 'border-sat-accent text-sat-accent bg-sat-accent/5'
                : 'border-transparent text-sat-dim hover:text-sat-text'
            }`}
          >
            <Cpu className="h-4 w-4" />
            <span>AI Model Registry</span>
          </button>

          <button
            onClick={() => setActiveTab('canvas')}
            className={`flex items-center gap-2 border-b-2 px-4 py-3 font-mono text-xs font-bold uppercase tracking-wider transition-all ${
              activeTab === 'canvas'
                ? 'border-sat-accent text-sat-accent bg-sat-accent/5'
                : 'border-transparent text-sat-dim hover:text-sat-text'
            }`}
          >
            <Layers className="h-4 w-4" />
            <span>GIS Canvas & Render</span>
          </button>

          <button
            onClick={() => setActiveTab('export')}
            className={`flex items-center gap-2 border-b-2 px-4 py-3 font-mono text-xs font-bold uppercase tracking-wider transition-all ${
              activeTab === 'export'
                ? 'border-sat-accent text-sat-accent bg-sat-accent/5'
                : 'border-transparent text-sat-dim hover:text-sat-text'
            }`}
          >
            <FileText className="h-4 w-4" />
            <span>Export & Audit</span>
          </button>
        </div>

        {/* Tab Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">

          {/* TAB 1: DATA PROVIDERS */}
          {activeTab === 'providers' && (
            <div className="space-y-5">
              <div className="rounded-lg border border-sat-accent/20 bg-sat-accent/5 p-4 flex items-start gap-3">
                <Globe className="h-5 w-5 text-sat-accent shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-mono text-xs font-bold uppercase text-sat-accent">Copernicus Data Space Ecosystem (CDSE) API</h4>
                  <p className="font-sans text-xs text-sat-muted mt-1 leading-relaxed">
                    SatQuery connects to the official Copernicus OData API to fetch Sentinel-1 and Sentinel-2 satellite scenes in real-time. Optional client credentials remove rate limits.
                  </p>
                </div>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block font-mono text-xs font-bold uppercase tracking-wider text-sat-text mb-1.5 flex items-center gap-2">
                    <Key className="h-3.5 w-3.5 text-sat-accent" />
                    CDSE OAuth Client ID
                  </label>
                  <input
                    type="text"
                    value={cdseClientId}
                    onChange={(e) => setCdseClientId(e.target.value)}
                    placeholder="e.g. cdse-oauth-client-id-xxxx"
                    className="w-full rounded-md border border-sat-border bg-sat-bg px-3 py-2 font-mono text-xs text-sat-text placeholder:text-sat-dim focus:border-sat-accent focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block font-mono text-xs font-bold uppercase tracking-wider text-sat-text mb-1.5 flex items-center gap-2">
                    <ShieldAlert className="h-3.5 w-3.5 text-sat-accent" />
                    CDSE OAuth Client Secret
                  </label>
                  <input
                    type="password"
                    value={cdseClientSecret}
                    onChange={(e) => setCdseClientSecret(e.target.value)}
                    placeholder="••••••••••••••••••••••••"
                    className="w-full rounded-md border border-sat-border bg-sat-bg px-3 py-2 font-mono text-xs text-sat-text placeholder:text-sat-dim focus:border-sat-accent focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block font-mono text-xs font-bold uppercase tracking-wider text-sat-text mb-1.5">
                    STAC Catalogue Endpoint URL
                  </label>
                  <input
                    type="text"
                    value={stacEndpoint}
                    onChange={(e) => setStacEndpoint(e.target.value)}
                    placeholder="https://catalogue.dataspace.copernicus.eu/stac"
                    className="w-full rounded-md border border-sat-border bg-sat-bg px-3 py-2 font-mono text-xs text-sat-text focus:border-sat-accent focus:outline-none"
                  />
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: AI MODELS */}
          {activeTab === 'models' && (
            <div className="space-y-5">
              <div>
                <label className="block font-mono text-xs font-bold uppercase tracking-wider text-sat-text mb-2">
                  Default Remote Sensing AI Specialist Model
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {[
                    { id: 'SatQuery-Opt-1A', name: 'SatQuery-Opt-1A (VQA)', desc: 'High-precision optical scene understanding & VQA' },
                    { id: 'SatQuery-SAR-Fusion', name: 'SatQuery-SAR-Fusion', desc: 'Optical + Sentinel-1 C-SAR multi-modal fusion' },
                    { id: 'PaliGemma-RS-3B', name: 'PaliGemma-RS-3B (Grounding)', desc: 'Bounding-box visual grounding & object detection' },
                    { id: 'BiTemp-Change-V2', name: 'BiTemp-Change-V2', desc: 'Bi-temporal land cover change detection engine' },
                  ].map((m) => (
                    <button
                      key={m.id}
                      type="button"
                      onClick={() => setDefaultModel(m.id)}
                      className={`text-left p-3 rounded-lg border transition-all ${
                        defaultModel === m.id
                          ? 'border-sat-accent bg-sat-accent/10 text-sat-text'
                          : 'border-sat-border bg-sat-panel/50 text-sat-muted hover:border-sat-borderLight'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-xs font-bold uppercase text-sat-text">{m.name}</span>
                        {defaultModel === m.id && <CheckCircle2 className="h-4 w-4 text-sat-accent" />}
                      </div>
                      <p className="font-sans text-[11px] text-sat-dim mt-1">{m.desc}</p>
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <div className="flex justify-between font-mono text-xs font-bold uppercase text-sat-text mb-1">
                  <span>Minimum AI Confidence Threshold</span>
                  <span className="text-sat-accent">{confidenceThreshold}%</span>
                </div>
                <input
                  type="range"
                  min="50"
                  max="99"
                  value={confidenceThreshold}
                  onChange={(e) => setConfidenceThreshold(Number(e.target.value))}
                  className="w-full h-1.5 bg-sat-border rounded-lg appearance-none cursor-pointer accent-sat-accent"
                />
                <p className="font-mono text-[9px] text-sat-dim mt-1">
                  Answers below this confidence level trigger automated fallback verification routines.
                </p>
              </div>
            </div>
          )}

          {/* TAB 3: GIS CANVAS */}
          {activeTab === 'canvas' && (
            <div className="space-y-5">
              <div className="flex items-center justify-between rounded-lg border border-sat-border bg-sat-panel/50 p-4">
                <div>
                  <h4 className="font-mono text-xs font-bold uppercase text-sat-text">GIS Telemetry Grid Overlay</h4>
                  <p className="font-sans text-xs text-sat-muted mt-0.5">Show WGS84 coordinate grid lines and scale bars over the imagery canvas</p>
                </div>
                <button
                  type="button"
                  onClick={() => setGridOverlay(!gridOverlay)}
                  className={`w-12 h-6 rounded-full p-1 transition-colors ${
                    gridOverlay ? 'bg-sat-accent' : 'bg-sat-border'
                  }`}
                >
                  <div
                    className={`w-4 h-4 rounded-full bg-slate-950 transition-transform ${
                      gridOverlay ? 'translate-x-6' : 'translate-x-0'
                    }`}
                  />
                </button>
              </div>

              <div>
                <label className="block font-mono text-xs font-bold uppercase tracking-wider text-sat-text mb-2">
                  Coordinate Readout Format
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={() => setCoordinateFormat('decimal')}
                    className={`p-3 rounded-lg border font-mono text-xs font-bold uppercase text-center transition-all ${
                      coordinateFormat === 'decimal'
                        ? 'border-sat-accent bg-sat-accent/10 text-sat-accent'
                        : 'border-sat-border text-sat-dim hover:text-sat-text'
                    }`}
                  >
                    Decimal Degrees (25.2048° N, 55.2708° E)
                  </button>

                  <button
                    type="button"
                    onClick={() => setCoordinateFormat('dms')}
                    className={`p-3 rounded-lg border font-mono text-xs font-bold uppercase text-center transition-all ${
                      coordinateFormat === 'dms'
                        ? 'border-sat-accent bg-sat-accent/10 text-sat-accent'
                        : 'border-sat-border text-sat-dim hover:text-sat-text'
                    }`}
                  >
                    DMS Format (25° 12' 17" N)
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: EXPORT & AUDIT */}
          {activeTab === 'export' && (
            <div className="space-y-5">
              <div className="flex items-center justify-between rounded-lg border border-sat-border bg-sat-panel/50 p-4">
                <div>
                  <h4 className="font-mono text-xs font-bold uppercase text-sat-text">Auto PDF Intelligence Brief</h4>
                  <p className="font-sans text-xs text-sat-muted mt-0.5">Automatically trigger PDF download upon completing an agent analysis run</p>
                </div>
                <button
                  type="button"
                  onClick={() => setAutoExportPdf(!autoExportPdf)}
                  className={`w-12 h-6 rounded-full p-1 transition-colors ${
                    autoExportPdf ? 'bg-sat-accent' : 'bg-sat-border'
                  }`}
                >
                  <div
                    className={`w-4 h-4 rounded-full bg-slate-950 transition-transform ${
                      autoExportPdf ? 'translate-x-6' : 'translate-x-0'
                    }`}
                  />
                </button>
              </div>
            </div>
          )}

        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-between border-t border-sat-border bg-sat-panel/80 px-6 py-4">
          <div className="flex items-center gap-2">
            {saveMessage && (
              <span className="flex items-center gap-1.5 font-mono text-xs text-sat-stable animate-in fade-in">
                <CheckCircle2 className="h-4 w-4" />
                {saveMessage}
              </span>
            )}
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={handleReset}
              className="flex items-center gap-1.5 rounded-lg border border-sat-border bg-sat-bg px-3 py-2 font-mono text-xs font-bold uppercase tracking-wider text-sat-dim hover:text-sat-text transition-colors"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Reset Defaults
            </button>

            <button
              type="button"
              onClick={handleSave}
              className="flex items-center gap-1.5 rounded-lg bg-sat-accent px-4 py-2 font-mono text-xs font-bold uppercase tracking-wider text-slate-950 shadow-sm hover:brightness-110 transition-all"
            >
              <Save className="h-3.5 w-3.5" />
              Save Preferences
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};
