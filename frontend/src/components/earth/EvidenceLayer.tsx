import React from 'react';
import type { EvidenceRegion } from '../../types/satquery';
import { FeaturePopup } from './FeaturePopup';

interface EvidenceLayerProps {
  evidence: EvidenceRegion[];
  selectedRegionId: string | null;
  onSelectRegion: (regionId: string | null) => void;
  visibleLayers: string[];
}

export const EvidenceLayer: React.FC<EvidenceLayerProps> = ({
  evidence,
  selectedRegionId,
  onSelectRegion,
  visibleLayers
}) => {
  return (
    <>
      {evidence.map((region) => {
        // Map region category to layer config IDs
        const isVisible = visibleLayers.includes(region.type) || visibleLayers.includes('change_detection') || visibleLayers.includes('base');
        if (!isVisible) return null;

        const isSelected = selectedRegionId === region.id;

        return (
          <div
            key={region.id}
            onClick={(e) => {
              e.stopPropagation();
              onSelectRegion(isSelected ? null : region.id);
            }}
            className={`absolute rounded border-2 cursor-pointer transition-all z-20 ${
              isSelected 
                ? 'border-sat-change bg-sat-change/25 ring-4 ring-sat-change/30 shadow-lg scale-105' 
                : 'border-sat-accent bg-sat-accent/15 hover:bg-sat-accent/25 hover:border-sky-300'
            }`}
            style={{
              left: `${region.coords.x}%`,
              top: `${region.coords.y}%`,
              width: `${region.coords.width}%`,
              height: `${region.coords.height}%`,
            }}
          >
            {/* Region Label Tag */}
            <div className="absolute -top-6 left-0 bg-sat-bg/90 border border-sat-border text-slate-100 px-2 py-0.5 rounded text-[10px] font-mono whitespace-nowrap shadow flex items-center space-x-1">
              <span className="w-1.5 h-1.5 rounded-full bg-sat-change animate-ping" />
              <span className="font-semibold text-sat-accent">{region.label}</span>
              {region.areaEstimate && (
                <span className="text-sat-change font-bold">({region.areaEstimate})</span>
              )}
            </div>

            {/* Inspectable Feature Popup on selection */}
            {isSelected && (
              <FeaturePopup
                region={region}
                onClose={() => onSelectRegion(null)}
              />
            )}
          </div>
        );
      })}
    </>
  );
};
