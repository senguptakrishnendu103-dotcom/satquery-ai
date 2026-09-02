import React from 'react';
import { ZoomIn, ZoomOut, RotateCcw, Eye, Crosshair, Layers } from 'lucide-react';

interface MapControlsProps {
  zoom: number;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onReset: () => void;
  showGrid: boolean;
  onToggleGrid: () => void;
  showOverlays: boolean;
  onToggleOverlays: () => void;
  showLayerPanel: boolean;
  onToggleLayerPanel: () => void;
}

export const MapControls: React.FC<MapControlsProps> = ({
  zoom,
  onZoomIn,
  onZoomOut,
  onReset,
  showGrid,
  onToggleGrid,
  showOverlays,
  onToggleOverlays,
  showLayerPanel,
  onToggleLayerPanel
}) => {
  return (
    <div className="flex items-center space-x-1.5 bg-sat-surface/90 border border-sat-border p-1 rounded shadow-lg backdrop-blur-md font-mono text-xs">
      <button
        onClick={onToggleLayerPanel}
        title="Toggle Layer Controller"
        className={`px-2 py-1 rounded transition-colors flex items-center space-x-1 ${
          showLayerPanel ? 'bg-sat-panel text-sat-accent border border-sat-accent/40 font-semibold' : 'text-sat-dim hover:text-slate-200'
        }`}
      >
        <Layers className="w-3.5 h-3.5" />
        <span className="hidden sm:inline text-[10px]">LAYERS</span>
      </button>

      <div className="h-4 w-px bg-sat-border" />

      <button
        onClick={onToggleOverlays}
        title="Toggle Evidence Overlays"
        className={`p-1.5 rounded transition-colors ${
          showOverlays ? 'bg-sat-panel text-sat-accent border border-sat-accent/40' : 'text-sat-dim hover:text-slate-200'
        }`}
      >
        <Eye className="w-4 h-4" />
      </button>

      <button
        onClick={onToggleGrid}
        title="Toggle Technical GIS Grid"
        className={`p-1.5 rounded transition-colors ${
          showGrid ? 'bg-sat-panel text-sat-accent border border-sat-accent/40' : 'text-sat-dim hover:text-slate-200'
        }`}
      >
        <Crosshair className="w-4 h-4" />
      </button>

      <div className="h-4 w-px bg-sat-border" />

      <button onClick={onZoomOut} title="Zoom Out" className="p-1.5 rounded text-slate-300 hover:bg-sat-panel">
        <ZoomOut className="w-4 h-4" />
      </button>
      <span className="text-[11px] text-sat-accent w-10 text-center font-semibold">{Math.round(zoom * 100)}%</span>
      <button onClick={onZoomIn} title="Zoom In" className="p-1.5 rounded text-slate-300 hover:bg-sat-panel">
        <ZoomIn className="w-4 h-4" />
      </button>
      <button onClick={onReset} title="Reset View" className="p-1.5 rounded text-slate-300 hover:bg-sat-panel">
        <RotateCcw className="w-4 h-4" />
      </button>
    </div>
  );
};
