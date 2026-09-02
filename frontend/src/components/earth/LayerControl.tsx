import React from 'react';
import type { MapLayerConfig } from '../../types/satquery';
import { Layers, CheckSquare, Square, X } from 'lucide-react';

interface LayerControlProps {
  layers: MapLayerConfig[];
  onToggleLayer: (layerId: string) => void;
  onClose: () => void;
}

export const LayerControl: React.FC<LayerControlProps> = ({ layers, onToggleLayer, onClose }) => {
  return (
    <div className="w-56 bg-sat-surface/95 border border-sat-borderLight p-3 rounded-lg shadow-2xl backdrop-blur-md font-mono text-xs space-y-3 z-30 select-none">
      
      {/* Header */}
      <div className="flex items-center justify-between border-b border-sat-border pb-2">
        <div className="flex items-center space-x-1.5 text-slate-100 font-bold uppercase tracking-wider text-[11px]">
          <Layers className="w-3.5 h-3.5 text-sat-accent" />
          <span>LAYER CONTROL</span>
        </div>
        <button
          onClick={onClose}
          className="text-sat-dim hover:text-slate-100 transition-colors p-0.5"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Layer List */}
      <div className="space-y-1">
        {layers.map((layer) => (
          <button
            key={layer.id}
            onClick={() => onToggleLayer(layer.id)}
            className={`w-full flex items-center justify-between p-1.5 rounded transition-all text-[11px] ${
              layer.visible
                ? 'bg-sat-panel text-slate-100 border border-sat-border'
                : 'text-sat-dim hover:text-slate-300 hover:bg-sat-bg'
            }`}
          >
            <div className="flex items-center space-x-2">
              {layer.visible ? (
                <CheckSquare className="w-3.5 h-3.5 text-sat-accent shrink-0" />
              ) : (
                <Square className="w-3.5 h-3.5 text-sat-dim shrink-0" />
              )}
              <span className={layer.visible ? 'font-bold' : ''}>{layer.name}</span>
            </div>

            {layer.count !== undefined && layer.count > 0 && (
              <span 
                className="px-1.5 py-0.2 rounded text-[9px] font-bold"
                style={{ backgroundColor: `${layer.color}25`, color: layer.color, border: `1px solid ${layer.color}` }}
              >
                {layer.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* CRS Footer */}
      <div className="pt-2 border-t border-sat-border/60 text-[9px] text-sat-dim flex justify-between">
        <span>PROJECTION:</span>
        <span className="text-slate-300">EPSG:4326 (WGS84)</span>
      </div>

    </div>
  );
};
