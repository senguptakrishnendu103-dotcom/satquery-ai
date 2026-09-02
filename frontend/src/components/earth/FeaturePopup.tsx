import React from 'react';
import type { EvidenceRegion } from '../../types/satquery';
import { MapPin, X } from 'lucide-react';

interface FeaturePopupProps {
  region: EvidenceRegion;
  onClose: () => void;
}

export const FeaturePopup: React.FC<FeaturePopupProps> = ({ region, onClose }) => {
  return (
    <div className="absolute top-full mt-2 left-0 w-64 bg-sat-surface/95 border border-sat-borderLight p-3 rounded-md shadow-2xl z-30 font-mono text-xs space-y-2 pointer-events-auto backdrop-blur-md">
      
      {/* Top Bar */}
      <div className="flex items-center justify-between border-b border-sat-border pb-1.5">
        <div className="flex items-center space-x-1.5">
          <MapPin className="w-3.5 h-3.5 text-sat-change" />
          <span className="font-bold text-slate-100 uppercase tracking-wider text-[11px]">
            {region.label}
          </span>
        </div>
        <button onClick={onClose} className="text-sat-dim hover:text-slate-100 transition-colors">
          <X className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Description */}
      <p className="font-sans text-slate-300 text-[11px] leading-relaxed font-normal">
        {region.description}
      </p>

      {/* Area & Confidence Badges */}
      <div className="flex items-center justify-between text-[10px] pt-1">
        <span className="text-sat-dim uppercase">AREA ESTIMATE:</span>
        <span className="text-sat-change font-extrabold">{region.areaEstimate}</span>
      </div>
      <div className="flex items-center justify-between text-[10px]">
        <span className="text-sat-dim uppercase">MODEL CONFIDENCE:</span>
        <span className="text-sat-stable font-extrabold">{region.confidence}%</span>
      </div>

      {/* Metrics Array */}
      {region.metrics && region.metrics.length > 0 && (
        <div className="bg-sat-bg/90 p-2 rounded border border-sat-border space-y-1 text-[10px] mt-2">
          {region.metrics.map((m, idx) => (
            <div key={idx} className="flex justify-between">
              <span className="text-sat-dim">{m.label}:</span>
              <span className="text-slate-200 font-semibold">{m.value}</span>
            </div>
          ))}
        </div>
      )}

      {/* CRS Coordinate Reference */}
      <div className="pt-1.5 border-t border-sat-border/40 text-[9px] text-sat-dim flex justify-between">
        <span>GEOMETRY: GEOJSON POLYGON</span>
        <span className="text-sat-accent">EPSG:4326</span>
      </div>

    </div>
  );
};
