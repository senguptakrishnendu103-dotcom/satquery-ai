import React, { useState } from 'react';
import type { AnalysisResult } from '../../types/satquery';
import { X, Play } from 'lucide-react';

interface AnalysisReplayModalProps {
  result: AnalysisResult;
  onClose: () => void;
}

export const AnalysisReplayModal: React.FC<AnalysisReplayModalProps> = ({ result, onClose }) => {
  const [selectedStepIndex, setSelectedStepIndex] = useState<number>(0);

  const steps = result.replaySteps || [];
  const activeStep = steps[selectedStepIndex] || steps[0];

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/85 backdrop-blur-md flex items-center justify-center p-4 selection:bg-sat-accent/30">
      <div className="w-full max-w-4xl bg-sat-surface border border-sat-borderLight rounded-lg shadow-2xl overflow-hidden font-mono flex flex-col max-h-[90vh]">
        
        {/* Modal Header */}
        <div className="p-4 bg-sat-bg border-b border-sat-border flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded bg-sat-panel border border-sat-accent/50 flex items-center justify-center text-sat-accent">
              <Play className="w-4 h-4 fill-current" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-100 uppercase tracking-wider">
                REPLAY ANALYSIS — AUDIT LOG PIPELINE
              </h2>
              <p className="text-[10px] text-sat-dim mt-0.5">
                TELEMETRY ID: {result.executionSummary.telemetryId} • TASK: {result.task}
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded bg-sat-panel border border-sat-border text-sat-dim hover:text-slate-100 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Timeline Progress Bar (INPUTS → QUERY → TASK IDENTIFICATION → MODEL SELECTION → ANALYSIS → EVIDENCE → RESULT) */}
        <div className="p-4 bg-sat-panel border-b border-sat-border overflow-x-auto">
          <div className="flex items-center justify-between min-w-[700px] relative">
            
            {/* Horizontal Line */}
            <div className="absolute top-1/2 left-4 right-4 h-0.5 bg-sat-border -translate-y-1/2 z-0" />

            {steps.map((step, idx) => {
              const isSelected = idx === selectedStepIndex;
              return (
                <button
                  key={idx}
                  onClick={() => setSelectedStepIndex(idx)}
                  className="relative z-10 flex flex-col items-center group focus:outline-none"
                >
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center border text-xs font-bold transition-all ${
                    isSelected
                      ? 'bg-sat-accent border-sat-accent text-slate-950 scale-110 shadow-lg shadow-sat-accent/30'
                      : 'bg-sat-bg border-sat-borderLight text-sat-muted group-hover:border-sat-accent group-hover:text-slate-100'
                  }`}>
                    {idx + 1}
                  </div>
                  <span className={`text-[10px] uppercase font-bold mt-2 tracking-wider ${
                    isSelected ? 'text-sat-accent' : 'text-sat-dim group-hover:text-slate-300'
                  }`}>
                    {step.phase}
                  </span>
                  <span className="text-[9px] text-sat-dim">{step.timestamp}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Inspector Detail Body */}
        {activeStep && (
          <div className="p-6 flex-1 overflow-y-auto space-y-6 bg-sat-surface">
            
            <div className="flex items-center justify-between border-b border-sat-border pb-3">
              <div>
                <span className="text-[10px] text-sat-accent font-bold uppercase tracking-widest block">
                  PHASE {selectedStepIndex + 1}: {activeStep.phase}
                </span>
                <h3 className="text-base font-bold text-slate-100 mt-0.5">
                  {activeStep.label}
                </h3>
              </div>
              <span className="px-2.5 py-1 rounded bg-sat-stable/20 border border-sat-stable text-sat-stable text-xs font-bold">
                ✓ VERIFIED EXECUTION
              </span>
            </div>

            <div className="bg-sat-bg p-4 rounded border border-sat-border space-y-2">
              <span className="text-[10px] text-sat-dim uppercase block">EXECUTIVE DETAIL:</span>
              <p className="text-xs text-slate-200 leading-relaxed font-sans font-normal">
                {activeStep.details}
              </p>
            </div>

            {/* Technical Metadata breakdown for this step */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div className="p-3 bg-sat-panel rounded border border-sat-border space-y-1.5">
                <span className="text-[10px] text-sat-dim uppercase block font-bold">
                  INSTRUMENTATION PARAMS
                </span>
                <div className="flex justify-between text-[11px]">
                  <span className="text-sat-dim">Engine Version:</span>
                  <span className="text-slate-200">{result.executionSummary.modelVersion}</span>
                </div>
                <div className="flex justify-between text-[11px]">
                  <span className="text-sat-dim">Dataset Baseline:</span>
                  <span className="text-slate-200">{result.executionSummary.datasetVersion}</span>
                </div>
                <div className="flex justify-between text-[11px]">
                  <span className="text-sat-dim">Compute Overhead:</span>
                  <span className="text-sat-accent">{result.executionSummary.executionTimeMs} ms</span>
                </div>
              </div>

              <div className="p-3 bg-sat-panel rounded border border-sat-border space-y-1.5">
                <span className="text-[10px] text-sat-dim uppercase block font-bold">
                  MODEL & TOOLS EXECUTED
                </span>
                <div className="flex justify-between text-[11px]">
                  <span className="text-sat-dim">Specialist Models:</span>
                  <span className="text-sat-accent">{result.models.join(', ')}</span>
                </div>
                <div className="flex justify-between text-[11px]">
                  <span className="text-sat-dim">Tools Called:</span>
                  <span className="text-slate-200">{result.executionSummary.toolsExecuted.join(' → ')}</span>
                </div>
                <div className="flex justify-between text-[11px]">
                  <span className="text-sat-dim">Geospatial CRS:</span>
                  <span className="text-sat-stable">EPSG:4326 (WGS84)</span>
                </div>
              </div>
            </div>

          </div>
        )}

        {/* Modal Footer Controls */}
        <div className="p-4 bg-sat-bg border-t border-sat-border flex items-center justify-between text-xs">
          <div className="flex items-center space-x-2">
            <button
              disabled={selectedStepIndex === 0}
              onClick={() => setSelectedStepIndex(prev => Math.max(0, prev - 1))}
              className="px-3 py-1.5 rounded bg-sat-panel border border-sat-border disabled:opacity-40 text-slate-200 hover:text-sat-accent transition-colors"
            >
              ← PREVIOUS STEP
            </button>
            <button
              disabled={selectedStepIndex === steps.length - 1}
              onClick={() => setSelectedStepIndex(prev => Math.min(steps.length - 1, prev + 1))}
              className="px-3 py-1.5 rounded bg-sat-panel border border-sat-border disabled:opacity-40 text-slate-200 hover:text-sat-accent transition-colors"
            >
              NEXT STEP →
            </button>
          </div>

          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded bg-sat-accent text-slate-950 font-bold hover:bg-sky-300 transition-colors"
          >
            CLOSE REPLAY
          </button>
        </div>

      </div>
    </div>
  );
};
