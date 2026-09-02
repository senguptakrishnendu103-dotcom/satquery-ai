import React, { useState, useEffect } from 'react';

interface SystemWorkflowSectionProps {
  onSelectStage?: (stage: 1 | 2 | 3) => void;
}

export const SystemWorkflowSection: React.FC<SystemWorkflowSectionProps> = ({ onSelectStage }) => {
  const [utcTime, setUtcTime] = useState<string>('');

  useEffect(() => {
    const updateClock = () => {
      const now = new Date();
      const timeStr = now.toISOString().split('T')[1].split('.')[0] + ' UTC';
      setUtcTime(timeStr);
    };

    updateClock();
    const interval = setInterval(updateClock, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="w-full bg-sat-surface/30 border-t border-sat-border/40 z-10 font-sans backdrop-blur-md">
      
      {/* Workflow Content Container */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        
        {/* Header Title Bar */}
        <div className="flex flex-col md:flex-row md:items-end justify-between border-b border-sat-border/50 pb-4 gap-4">
          <div>
            <span className="font-mono text-xs text-sat-accent tracking-widest uppercase block mb-1 font-bold">
              SYSTEM WORKFLOW
            </span>
            <h2 className="font-display text-2xl sm:text-3xl font-extrabold text-sat-text uppercase tracking-tight">
              SCIENTIFIC REMOTE-SENSING ANALYSIS IN THREE STEPS
            </h2>
          </div>
          <p className="text-sat-muted text-xs sm:text-sm max-w-md font-mono">
            Automated AI-agent orchestration turning satellite imagery into auditable evidence.
          </p>
        </div>

        {/* 3 Interactive Glassmorphic Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          
          {/* STAGE 01: OBSERVE */}
          <div 
            onClick={() => onSelectStage?.(1)}
            className={`bg-sat-surface/40 hover:bg-sat-surface/70 p-6 rounded-xl border border-sat-border/60 space-y-3.5 relative group hover:border-sat-accent/60 transition-all shadow-2xl backdrop-blur-md ${
              onSelectStage ? 'cursor-pointer' : ''
            }`}
          >
            <div className="font-mono text-xs text-sat-accent font-bold flex justify-between items-center">
              <span>STAGE 01</span>
              <span className="px-2.5 py-0.5 rounded bg-sat-panel/70 border border-sat-border/60 text-sat-text text-[10px] uppercase font-semibold">
                INPUTS
              </span>
            </div>
            <h3 className="font-display font-bold text-xl text-sat-text uppercase tracking-wide">
              01. OBSERVE
            </h3>
            <p className="text-xs text-sat-muted leading-relaxed font-sans font-normal">
              Load high-resolution optical, SAR radar backscatter, or multispectral satellite observations into the workspace.
            </p>
            <div className="pt-2 font-mono text-[10px] text-sat-dim flex items-center space-x-1.5 border-t border-sat-border/40">
              <span>SUPPORTED:</span>
              <span className="text-sat-accent font-bold">RGB • SAR • NDWI • NIR</span>
            </div>
          </div>

          {/* STAGE 02: ASK */}
          <div 
            onClick={() => onSelectStage?.(2)}
            className={`bg-sat-surface/40 hover:bg-sat-surface/70 p-6 rounded-xl border border-sat-border/60 space-y-3.5 relative group hover:border-sat-change/60 transition-all shadow-2xl backdrop-blur-md ${
              onSelectStage ? 'cursor-pointer' : ''
            }`}
          >
            <div className="font-mono text-xs text-sat-change font-bold flex justify-between items-center">
              <span>STAGE 02</span>
              <span className="px-2.5 py-0.5 rounded bg-sat-panel/70 border border-sat-border/60 text-sat-text text-[10px] uppercase font-semibold">
                NATURAL LANGUAGE
              </span>
            </div>
            <h3 className="font-display font-bold text-xl text-sat-text uppercase tracking-wide">
              02. ASK
            </h3>
            <p className="text-xs text-sat-muted leading-relaxed font-sans font-normal">
              Ask questions in plain language (e.g., "What changed between these observations?" or "Identify water bodies").
            </p>
            <div className="pt-2 font-mono text-[10px] text-sat-dim flex items-center space-x-1.5 border-t border-sat-border/40">
              <span>AGENT:</span>
              <span className="text-sat-change font-bold">Zero-Shot Model Selection</span>
            </div>
          </div>

          {/* STAGE 03: UNDERSTAND */}
          <div 
            onClick={() => onSelectStage?.(3)}
            className={`bg-sat-surface/40 hover:bg-sat-surface/70 p-6 rounded-xl border border-sat-border/60 space-y-3.5 relative group hover:border-sat-stable/60 transition-all shadow-2xl backdrop-blur-md ${
              onSelectStage ? 'cursor-pointer' : ''
            }`}
          >
            <div className="font-mono text-xs text-sat-stable font-bold flex justify-between items-center">
              <span>STAGE 03</span>
              <span className="px-2.5 py-0.5 rounded bg-sat-panel/70 border border-sat-border/60 text-sat-text text-[10px] uppercase font-semibold">
                EVIDENCE
              </span>
            </div>
            <h3 className="font-display font-bold text-xl text-sat-text uppercase tracking-wide">
              03. UNDERSTAND
            </h3>
            <p className="text-xs text-sat-muted leading-relaxed font-sans font-normal">
              Receive inspectable GeoJSON bounding boxes, confidence metrics, and an auditable step-by-step pipeline execution replay.
            </p>
            <div className="pt-2 font-mono text-[10px] text-sat-dim flex items-center space-x-1.5 border-t border-sat-border/40">
              <span>OUTPUT:</span>
              <span className="text-sat-stable font-bold">Auditable Analysis Summary</span>
            </div>
          </div>

        </div>

      </div>

      {/* Telemetry Status Bar Footer */}
      <footer className="border-t border-sat-border/40 bg-sat-surface/30 py-3 px-4 sm:px-6 lg:px-8 font-mono text-[11px] text-sat-dim backdrop-blur-md">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between space-y-2 sm:space-y-0">
          <div className="flex items-center space-x-3 flex-wrap justify-center sm:justify-start">
            <span className="text-sat-text font-semibold">LAT: 39.5696° N</span>
            <span className="text-sat-border">|</span>
            <span className="text-sat-text font-semibold">LON: 2.6502° E</span>
            <span className="text-sat-border">|</span>
            <span>ELEV: 540KM (LEO)</span>
            <span className="text-sat-border">|</span>
            <span>ORBIT: SSO</span>
          </div>

          <div className="flex items-center space-x-3">
            <span className="text-sat-accent font-bold">{utcTime || '15:30:16 UTC'}</span>
            <span className="text-sat-border">|</span>
            <span className="text-sat-stable font-bold flex items-center space-x-1">
              <span className="w-1.5 h-1.5 rounded-full bg-sat-stable animate-ping mr-1" />
              <span>NODE_01_ACTIVE</span>
            </span>
          </div>
        </div>
      </footer>

    </div>
  );
};
