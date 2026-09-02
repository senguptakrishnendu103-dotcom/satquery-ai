import React from 'react';
import { Sliders } from 'lucide-react';

interface ComparisonViewProps {
  compareMode: 'BEFORE' | 'AFTER' | 'CHANGE';
  onSetCompareMode: (mode: 'BEFORE' | 'AFTER' | 'CHANGE') => void;
  wipePosition: number;
  onWipeChange: (pos: number) => void;
  dateBefore?: string;
  dateAfter?: string;
  isMultiObs: boolean;
}

export const ComparisonView: React.FC<ComparisonViewProps> = ({
  compareMode,
  onSetCompareMode,
  wipePosition,
  onWipeChange,
  dateBefore = '2024',
  dateAfter = '2026',
  isMultiObs
}) => {
  return (
    <div className="w-full flex flex-col space-y-2 select-none">
      
      {/* Mode Switcher */}
      {isMultiObs && (
        <div className="flex items-center space-x-1 bg-sat-surface/90 border border-sat-border p-1 rounded shadow-lg backdrop-blur-md font-mono text-xs w-fit">
          <button
            onClick={() => onSetCompareMode('BEFORE')}
            className={`px-2.5 py-1 rounded text-[11px] font-semibold transition-colors ${
              compareMode === 'BEFORE'
                ? 'bg-sat-panel text-sat-accent border border-sat-accent/40'
                : 'text-sat-dim hover:text-slate-200'
            }`}
          >
            BEFORE ({dateBefore})
          </button>

          <button
            onClick={() => onSetCompareMode('AFTER')}
            className={`px-2.5 py-1 rounded text-[11px] font-semibold transition-colors ${
              compareMode === 'AFTER'
                ? 'bg-sat-panel text-sat-accent border border-sat-accent/40'
                : 'text-sat-dim hover:text-slate-200'
            }`}
          >
            AFTER ({dateAfter})
          </button>

          <button
            onClick={() => onSetCompareMode('CHANGE')}
            className={`px-2.5 py-1 rounded text-[11px] font-semibold transition-colors ${
              compareMode === 'CHANGE'
                ? 'bg-sat-change text-slate-950 font-bold shadow-sm'
                : 'text-sat-dim hover:text-slate-200'
            }`}
          >
            CHANGE WIPE
          </button>
        </div>
      )}

      {/* Wipe Slider Bar (When in CHANGE mode) */}
      {isMultiObs && compareMode === 'CHANGE' && (
        <div className="bg-sat-surface/90 border border-sat-border px-4 py-2 rounded shadow-lg backdrop-blur-md flex items-center justify-between font-mono text-xs">
          <span className="text-sat-dim text-[10px]">T1 ({dateBefore})</span>
          <div className="flex-1 mx-4 flex items-center space-x-3">
            <Sliders className="w-3.5 h-3.5 text-sat-accent shrink-0" />
            <input 
              type="range" 
              min="0" 
              max="100" 
              value={wipePosition} 
              onChange={(e) => onWipeChange(Number(e.target.value))}
              className="w-full h-1 bg-sat-border rounded-lg appearance-none cursor-pointer accent-sat-accent"
            />
            <span className="text-sat-accent text-[11px] font-bold w-8">{wipePosition}%</span>
          </div>
          <span className="text-sat-dim text-[10px]">T2 ({dateAfter})</span>
        </div>
      )}

    </div>
  );
};
