import React, { useEffect, useMemo, useState } from 'react';
import {
  Check,
  CheckCircle2,
  ChevronRight,
  Cpu,
  Database,
  Loader2,
  Radar,
  Satellite,
  Shield,
  Sparkles,
  Activity,
  Crosshair,
} from 'lucide-react';

interface AnalysisStatusModalProps {
  currentStepIndex: number;
  currentStepLabel: string;
  queryText: string;
}

export const ANALYSIS_STEPS = [
  'Understanding request',
  'Checking observations',
  'Determining analysis type',
  'Selecting specialist model',
  'Running analysis',
  'Generating evidence',
  'Preparing result',
];

const STEP_ICONS = [
  Sparkles,
  Database,
  Crosshair,
  Cpu,
  Activity,
  Radar,
  CheckCircle2,
];

export const AnalysisStatusModal: React.FC<AnalysisStatusModalProps> = ({
  currentStepIndex,
  currentStepLabel,
  queryText,
}) => {
  const [executionId] = useState(
    () => `SQ-${Math.random().toString(36).slice(2, 8).toUpperCase()}`
  );

  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const startedAt = Date.now();

    const timer = window.setInterval(() => {
      setElapsed(Date.now() - startedAt);
    }, 100);

    return () => window.clearInterval(timer);
  }, []);

  const progress = useMemo(() => {
    if (currentStepIndex < 0) return 0;

    return Math.min(
      100,
      Math.round(
        ((currentStepIndex + 1) / ANALYSIS_STEPS.length) * 100
      )
    );
  }, [currentStepIndex]);

  const activeStep =
    currentStepLabel ||
    ANALYSIS_STEPS[currentStepIndex] ||
    'SATQUERY AGENT ORCHESTRATION';

  const elapsedSeconds = (elapsed / 1000).toFixed(1);

  return (
    <div
      className="
        fixed inset-0 z-50
        flex items-center justify-center
        bg-slate-950/85
        backdrop-blur-md
        p-4
      "
      role="dialog"
      aria-modal="true"
      aria-labelledby="satquery-analysis-title"
    >
      {/* Ambient instrument glow */}
      <div
        className="
          pointer-events-none
          absolute
          h-[520px]
          w-[520px]
          rounded-full
          border border-sat-accent/10
          opacity-60
          animate-pulse
        "
      />

      <div
        className="
          relative
          w-full
          max-w-2xl
          overflow-hidden
          rounded-xl
          border border-sat-borderLight
          bg-sat-surface
          shadow-[0_30px_100px_rgba(0,0,0,0.55)]
        "
      >
        {/* =========================================================
            TOP INSTRUMENT BAR
        ========================================================= */}

        <div
          className="
            relative
            border-b border-sat-border
            bg-sat-panel/80
          "
        >
          {/* Fine scanline */}
          <div
            className="
              pointer-events-none
              absolute inset-0
              opacity-[0.035]
              bg-[linear-gradient(to_bottom,transparent_50%,currentColor_50%)]
              bg-[length:100%_4px]
            "
          />

          <div className="relative px-6 py-5">
            <div className="flex items-start justify-between gap-5">
              <div className="flex items-center gap-4">
                {/* Radar core */}
                <div
                  className="
                    relative
                    flex h-12 w-12 shrink-0
                    items-center justify-center
                    overflow-hidden
                    rounded-lg
                    border border-sat-accent/40
                    bg-sat-bg
                    text-sat-accent
                  "
                >
                  <div
                    className="
                      absolute inset-1
                      rounded-full
                      border border-sat-accent/20
                    "
                  />

                  <div
                    className="
                      absolute
                      h-full w-px
                      bg-sat-accent/40
                      origin-bottom
                      animate-spin
                    "
                    style={{
                      animationDuration: '3.5s',
                    }}
                  />

                  <Radar className="relative z-10 h-6 w-6" />
                </div>

                <div>
                  <div className="flex items-center gap-2">
                    <Satellite className="h-3.5 w-3.5 text-sat-accent" />

                    <h3
                      id="satquery-analysis-title"
                      className="
                        font-mono
                        text-xs
                        font-bold
                        tracking-[0.16em]
                        text-slate-100
                      "
                    >
                      SATQUERY ENGINE
                    </h3>
                  </div>

                  <p
                    className="
                      mt-1
                      font-mono
                      text-[10px]
                      uppercase
                      tracking-[0.12em]
                      text-sat-accent
                    "
                    aria-live="polite"
                  >
                    {activeStep}
                  </p>
                </div>
              </div>

              {/* Execution identifier */}
              <div className="hidden text-right sm:block">
                <div className="font-mono text-[9px] uppercase tracking-widest text-sat-dim">
                  Execution
                </div>

                <div className="mt-1 font-mono text-[10px] font-semibold text-slate-300">
                  {executionId}
                </div>

                <div className="mt-1 font-mono text-[9px] text-sat-dim">
                  {elapsedSeconds}s elapsed
                </div>
              </div>
            </div>

            {/* Progress telemetry */}
            <div className="mt-5">
              <div className="mb-2 flex items-center justify-between">
                <span className="font-mono text-[9px] uppercase tracking-widest text-sat-dim">
                  Analysis progression
                </span>

                <span className="font-mono text-[10px] font-bold text-sat-accent">
                  {progress}%
                </span>
              </div>

              <div
                className="
                  h-1
                  overflow-hidden
                  rounded-full
                  bg-sat-bg
                "
              >
                <div
                  className="
                    h-full
                    rounded-full
                    bg-sat-accent
                    shadow-[0_0_12px_rgba(56,189,248,0.55)]
                    transition-all
                    duration-500
                  "
                  style={{
                    width: `${progress}%`,
                  }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* =========================================================
            QUERY / OBSERVATION TARGET
        ========================================================= */}

        <div className="px-6 pt-5">
          <div
            className="
              overflow-hidden
              rounded-lg
              border border-sat-border
              bg-sat-bg
            "
          >
            {/* Target header */}
            <div
              className="
                flex items-center justify-between
                border-b border-sat-border
                px-4 py-2.5
              "
            >
              <div className="flex items-center gap-2">
                <Crosshair className="h-3.5 w-3.5 text-sat-accent" />

                <span
                  className="
                    font-mono
                    text-[9px]
                    font-bold
                    uppercase
                    tracking-[0.14em]
                    text-sat-dim
                  "
                >
                  Target question
                </span>
              </div>

              <span className="font-mono text-[9px] text-sat-dim">
                NATURAL LANGUAGE
              </span>
            </div>

            <div className="px-4 py-3">
              <p
                className="
                  font-sans
                  text-sm
                  font-medium
                  leading-relaxed
                  text-slate-200
                "
              >
                "{queryText}"
              </p>
            </div>
          </div>
        </div>

        {/* =========================================================
            AGENT PIPELINE
        ========================================================= */}

        <div className="px-6 py-5">
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Cpu className="h-3.5 w-3.5 text-sat-accent" />

              <span
                className="
                  font-mono
                  text-[9px]
                  font-bold
                  uppercase
                  tracking-[0.14em]
                  text-sat-dim
                "
              >
                Agent execution pipeline
              </span>
            </div>

            <span className="font-mono text-[9px] text-sat-dim">
              {currentStepIndex + 1}/{ANALYSIS_STEPS.length}
            </span>
          </div>

          <div className="space-y-1">
            {ANALYSIS_STEPS.map((step, idx) => {
              const isDone = idx < currentStepIndex;
              const isCurrent = idx === currentStepIndex;
              const isPending = idx > currentStepIndex;

              const Icon = STEP_ICONS[idx] || Activity;

              return (
                <div
                  key={step}
                  className={`
                    group
                    relative
                    flex
                    items-center
                    gap-3
                    rounded-lg
                    border
                    px-3
                    py-2.5
                    transition-all
                    duration-300

                    ${isCurrent
                      ? `
                          border-sat-accent/40
                          bg-sat-accent/[0.07]
                          shadow-[inset_3px_0_0_rgba(56,189,248,0.7)]
                        `
                      : isDone
                        ? `
                          border-transparent
                          bg-sat-stable/[0.025]
                        `
                        : `
                          border-transparent
                          opacity-40
                        `
                    }
                  `}
                >
                  {/* Step number */}
                  <div
                    className={`
                      flex
                      h-7
                      w-7
                      shrink-0
                      items-center
                      justify-center
                      rounded-md
                      border
                      font-mono
                      text-[9px]
                      font-bold

                      ${isCurrent
                        ? 'border-sat-accent/40 bg-sat-accent/10 text-sat-accent'
                        : isDone
                          ? 'border-sat-stable/30 bg-sat-stable/10 text-sat-stable'
                          : 'border-sat-border bg-sat-bg text-sat-dim'
                      }
                    `}
                  >
                    {isDone ? (
                      <Check className="h-3.5 w-3.5" />
                    ) : (
                      <span>{String(idx + 1).padStart(2, '0')}</span>
                    )}
                  </div>

                  {/* Icon */}
                  <Icon
                    className={`
                      h-3.5
                      w-3.5
                      shrink-0

                      ${isCurrent
                        ? 'text-sat-accent'
                        : isDone
                          ? 'text-sat-stable'
                          : 'text-sat-dim'
                      }
                    `}
                  />

                  {/* Step text */}
                  <div className="min-w-0 flex-1">
                    <div
                      className={`
                        font-mono
                        text-[11px]

                        ${isCurrent
                          ? 'font-bold text-slate-100'
                          : isDone
                            ? 'text-slate-300'
                            : 'text-sat-dim'
                        }
                      `}
                    >
                      {step}
                    </div>

                    {isCurrent && (
                      <div className="mt-0.5 font-mono text-[8px] uppercase tracking-wider text-sat-accent/70">
                        Specialist operation active
                      </div>
                    )}
                  </div>

                  {/* Status */}
                  <div className="shrink-0">
                    {isDone && (
                      <CheckCircle2 className="h-4 w-4 text-sat-stable" />
                    )}

                    {isCurrent && (
                      <Loader2 className="h-4 w-4 animate-spin text-sat-accent" />
                    )}

                    {isPending && (
                      <ChevronRight className="h-3.5 w-3.5 text-sat-dim" />
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* =========================================================
            SYSTEM TELEMETRY
        ========================================================= */}

        <div
          className="
            border-t border-sat-border
            bg-sat-panel/40
            px-6
            py-4
          "
        >
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <TelemetryItem
              label="ENGINE"
              value="ONLINE"
              icon={<Activity className="h-3 w-3" />}
              accent="stable"
            />

            <TelemetryItem
              label="AGENT"
              value="ACTIVE"
              icon={<Cpu className="h-3 w-3" />}
              accent="accent"
            />

            <TelemetryItem
              label="EVIDENCE"
              value={currentStepIndex >= 5 ? 'READY' : 'BUILDING'}
              icon={<Radar className="h-3 w-3" />}
              accent={currentStepIndex >= 5 ? 'stable' : 'accent'}
            />

            <TelemetryItem
              label="AUDIT"
              value="ENABLED"
              icon={<Shield className="h-3 w-3" />}
              accent="stable"
            />
          </div>
        </div>

        {/* =========================================================
            FOOTER
        ========================================================= */}

        <div
          className="
            flex
            flex-col
            gap-2
            border-t border-sat-border
            px-6
            py-3
            sm:flex-row
            sm:items-center
            sm:justify-between
          "
        >
          <div className="flex items-center gap-2">
            <Shield className="h-3 w-3 text-sat-stable" />

            <span
              className="
                font-mono
                text-[9px]
                uppercase
                tracking-wider
                text-sat-dim
              "
            >
              Auditable satellite intelligence
            </span>
          </div>

          <div className="font-mono text-[9px] text-sat-dim">
            COMPUTE EST. · 0.04 GPU-HRS
          </div>
        </div>
      </div>
    </div>
  );
};

/* =============================================================
   TELEMETRY COMPONENT
============================================================= */

interface TelemetryItemProps {
  label: string;
  value: string;
  icon: React.ReactNode;
  accent: 'stable' | 'accent';
}

const TelemetryItem: React.FC<TelemetryItemProps> = ({
  label,
  value,
  icon,
  accent,
}) => {
  const accentClass =
    accent === 'stable'
      ? 'text-sat-stable'
      : 'text-sat-accent';

  return (
    <div
      className="
        flex
        min-w-0
        items-center
        gap-2
        rounded-md
        border border-sat-border
        bg-sat-bg/60
        px-2.5
        py-2
      "
    >
      <span className={accentClass}>{icon}</span>

      <div className="min-w-0">
        <div className="truncate font-mono text-[8px] text-sat-dim">
          {label}
        </div>

        <div
          className={`
            truncate
            font-mono
            text-[9px]
            font-bold
            ${accentClass}
          `}
        >
          {value}
        </div>
      </div>
    </div>
  );
};