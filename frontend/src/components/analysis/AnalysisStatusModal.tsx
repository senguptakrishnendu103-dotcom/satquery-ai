import React, { useEffect, useMemo, useState } from 'react';
import {
  Check,
  CheckCircle2,
  Loader2,
  Radar,
  Satellite,
  Sparkles,
  Database,
  Crosshair,
  Cpu,
  Activity,
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

const FRIENDLY_STEP_LABELS = [
  'Understanding what you asked',
  'Checking your satellite data',
  'Choosing the right analysis',
  'Choosing the best AI model',
  'Analyzing the satellite data',
  'Checking the evidence',
  'Getting your answer ready',
];

const FRIENDLY_STEP_DESCRIPTIONS = [
  'Turning your question into an analysis plan.',
  'Making sure the right observations are available.',
  'Figuring out what kind of analysis will answer your question.',
  'Selecting the specialist model that fits the task.',
  'Processing the satellite information now.',
  'Checking the result against available evidence.',
  'Putting everything into a clear result for you.',
];

export const AnalysisStatusModal: React.FC<AnalysisStatusModalProps> = ({
  currentStepIndex,
  currentStepLabel,
  queryText,
}) => {
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
      Math.round(((currentStepIndex + 1) / ANALYSIS_STEPS.length) * 100)
    );
  }, [currentStepIndex]);

  const activeStep =
    currentStepLabel ||
    ANALYSIS_STEPS[currentStepIndex] ||
    'Preparing your analysis';

  const friendlyActiveStep =
    FRIENDLY_STEP_LABELS[currentStepIndex] || activeStep;

  const elapsedSeconds = (elapsed / 1000).toFixed(1);

  return (
    <div
      className="
        fixed inset-0 z-50
        flex items-center justify-center
        bg-slate-950/80
        p-4
        backdrop-blur-sm
      "
      role="dialog"
      aria-modal="true"
      aria-labelledby="satquery-analysis-title"
      aria-describedby="satquery-analysis-description"
    >
      <div
        className="
          relative w-full max-w-xl overflow-hidden
          rounded-2xl border border-sat-borderLight
          bg-sat-surface
          shadow-[0_30px_100px_rgba(0,0,0,0.55)]
        "
      >
        {/* Simple visual progress indicator */}
        <div className="h-1 bg-sat-bg">
          <div
            className="h-full bg-sat-accent transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>

        {/* Header */}
        <div className="px-6 pb-5 pt-6">
          <div className="flex items-start gap-4">
            <div
              className="
                flex h-12 w-12 shrink-0 items-center justify-center
                rounded-xl border border-sat-accent/30
                bg-sat-accent/10 text-sat-accent
              "
            >
              <Radar className="h-6 w-6" />
            </div>

            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <Satellite className="h-4 w-4 text-sat-accent" />
                <h3
                  id="satquery-analysis-title"
                  className="text-base font-semibold text-slate-100"
                >
                  Analyzing your satellite data
                </h3>
              </div>

              <p
                id="satquery-analysis-description"
                className="mt-1.5 text-sm leading-relaxed text-slate-400"
                aria-live="polite"
              >
                {friendlyActiveStep}. You don't need to do anything while we
                work.
              </p>
            </div>
          </div>

          {/* Progress summary */}
          <div className="mt-6">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-xs font-medium text-slate-400">
                Progress
              </span>
              <span className="text-sm font-semibold text-sat-accent">
                {progress}%
              </span>
            </div>

            <div
              className="h-2 overflow-hidden rounded-full bg-sat-bg"
              aria-label={`Analysis progress: ${progress}%`}
              role="progressbar"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={progress}
            >
              <div
                className="
                  h-full rounded-full bg-sat-accent
                  transition-all duration-500
                "
                style={{ width: `${progress}%` }}
              />
            </div>

            <div className="mt-2 flex items-center justify-between text-xs text-slate-500">
              <span>
                Step {Math.min(Math.max(currentStepIndex + 1, 0), ANALYSIS_STEPS.length)} of{' '}
                {ANALYSIS_STEPS.length}
              </span>
              <span>{elapsedSeconds}s</span>
            </div>
          </div>
        </div>

        {/* What the user asked */}
        <div className="px-6">
          <div
            className="
              rounded-xl border border-sat-border
              bg-sat-bg/60
              px-4 py-4
            "
          >
            <div className="mb-2 flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-sat-accent" />
              <span className="text-xs font-semibold text-slate-300">
                Your question
              </span>
            </div>

            <p className="text-sm leading-relaxed text-slate-200">
              “{queryText}”
            </p>
          </div>
        </div>

        {/* Friendly step list */}
        <div className="px-6 py-5">
          <div className="mb-3 flex items-center justify-between">
            <h4 className="text-sm font-semibold text-slate-200">
              What SATQuery is doing
            </h4>

            <span className="text-xs text-slate-500">
              {progress === 100 ? 'Almost done' : 'Working automatically'}
            </span>
          </div>

          <div className="space-y-2">
            {ANALYSIS_STEPS.map((step, idx) => {
              const isDone = idx < currentStepIndex;
              const isCurrent = idx === currentStepIndex;
              const isPending = idx > currentStepIndex;

              const Icon = STEP_ICONS[idx] || Activity;

              return (
                <div
                  key={step}
                  className={`
                    flex items-center gap-3 rounded-xl border px-3 py-3
                    transition-all duration-300
                    ${isCurrent
                      ? 'border-sat-accent/30 bg-sat-accent/[0.07]'
                      : isDone
                        ? 'border-sat-stable/10 bg-sat-stable/[0.025]'
                        : 'border-sat-border/40 bg-transparent opacity-55'
                    }
                  `}
                >
                  <div
                    className={`
                      flex h-8 w-8 shrink-0 items-center justify-center
                      rounded-full border
                      ${isCurrent
                        ? 'border-sat-accent/40 bg-sat-accent/10 text-sat-accent'
                        : isDone
                          ? 'border-sat-stable/30 bg-sat-stable/10 text-sat-stable'
                          : 'border-sat-border bg-sat-bg text-sat-dim'
                      }
                    `}
                  >
                    {isDone ? (
                      <Check className="h-4 w-4" />
                    ) : (
                      <Icon className="h-4 w-4" />
                    )}
                  </div>

                  <div className="min-w-0 flex-1">
                    <div
                      className={`
                        text-sm
                        ${isCurrent
                          ? 'font-semibold text-slate-100'
                          : isDone
                            ? 'text-slate-300'
                            : 'text-slate-500'
                        }
                      `}
                    >
                      {FRIENDLY_STEP_LABELS[idx]}
                    </div>

                    {(isCurrent || isDone) && (
                      <div className="mt-0.5 text-xs leading-relaxed text-slate-500">
                        {FRIENDLY_STEP_DESCRIPTIONS[idx]}
                      </div>
                    )}
                  </div>

                  <div className="shrink-0">
                    {isDone && (
                      <CheckCircle2 className="h-4 w-4 text-sat-stable" />
                    )}

                    {isCurrent && (
                      <Loader2 className="h-4 w-4 animate-spin text-sat-accent" />
                    )}

                    {isPending && (
                      <div className="h-2 w-2 rounded-full bg-slate-600" />
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Small reassuring footer */}
        <div
          className="
            border-t border-sat-border
            bg-sat-panel/30
            px-6 py-4
          "
        >
          <div className="flex items-center justify-center gap-2 text-xs text-slate-500">
            <Activity className="h-3.5 w-3.5 text-sat-stable" />
            <span>
              SATQuery is handling the technical processing automatically.
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
