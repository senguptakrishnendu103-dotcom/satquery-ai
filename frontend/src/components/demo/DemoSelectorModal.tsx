import React from 'react';
import { DEMO_SCENARIOS } from '../../data/demoScenarios';
import type { DemoScenario } from '../../types/satquery';
import { Sparkles, X, ArrowRight } from 'lucide-react';

interface DemoSelectorModalProps {
  onSelectScenario: (scenario: DemoScenario) => void;
  onClose: () => void;
  currentDemoId?: string;
}

export const DemoSelectorModal: React.FC<DemoSelectorModalProps> = ({
  onSelectScenario,
  onClose,
  currentDemoId
}) => {
  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 selection:bg-sat-accent/30">
      <div className="w-full max-w-3xl bg-sat-surface border border-sat-borderLight rounded-lg shadow-2xl p-6 space-y-6 font-mono relative">
        
        {/* Header */}
        <div className="flex items-center justify-between border-b border-sat-border pb-4">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded bg-sat-panel border border-sat-accent/50 flex items-center justify-center text-sat-accent">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-100 uppercase tracking-wider">
                SELECT PRESET DEMO SCENARIO
              </h2>
              <p className="text-[10px] text-sat-dim mt-0.5">
                INTERACTIVE SCIENTIFIC DATASETS & MOCK INFERENCE PIPELINES
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

        {/* Demo Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {DEMO_SCENARIOS.map((demo) => {
            const isSelected = currentDemoId === demo.id;
            return (
              <div
                key={demo.id}
                onClick={() => {
                  onSelectScenario(demo);
                  onClose();
                }}
                className={`p-4 rounded-lg border cursor-pointer transition-all flex flex-col justify-between space-y-3 group ${
                  isSelected
                    ? 'bg-sat-panel border-sat-accent shadow-lg shadow-sat-accent/10'
                    : 'bg-sat-bg border-sat-border hover:border-sat-borderLight hover:bg-sat-panel/50'
                }`}
              >
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="px-2 py-0.5 rounded bg-sat-accent/20 border border-sat-accent text-sat-accent text-[10px] font-bold">
                      {demo.badge}
                    </span>
                    <span className="text-[10px] text-sat-dim font-mono">
                      {demo.observations.length} {demo.observations.length === 1 ? 'OBSERVATION' : 'OBSERVATIONS'}
                    </span>
                  </div>

                  <h3 className="font-display font-bold text-sm text-slate-100 group-hover:text-sat-accent transition-colors">
                    {demo.title}
                  </h3>

                  <p className="font-sans text-xs text-sat-muted leading-relaxed">
                    {demo.description}
                  </p>
                </div>

                <div className="pt-2 border-t border-sat-border/60 flex items-center justify-between text-[11px]">
                  <span className="text-sat-dim">
                    MODALITY: <span className="text-slate-300">{demo.observations.map(o => o.modality).join(' + ')}</span>
                  </span>
                  <span className="text-sat-accent font-bold group-hover:translate-x-1 transition-transform flex items-center space-x-1">
                    <span>LOAD DATA</span>
                    <ArrowRight className="w-3 h-3 inline" />
                  </span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Notice Disclaimer (Section 21: Clearly label demo outputs) */}
        <div className="p-3 rounded bg-sat-bg border border-sat-border text-[10px] text-sat-dim flex items-center justify-between font-mono">
          <span>NOTICE: PRESET DEMO DATASETS ARE LABELED AS DEMO DEMONSTRATION RUNS.</span>
          <span className="text-sat-accent">SCIENTIFIC INTEGRITY</span>
        </div>

      </div>
    </div>
  );
};
