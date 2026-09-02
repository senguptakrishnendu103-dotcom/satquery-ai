import React, {
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';

import type { Observation } from '../../types/satquery';

import {
  Activity,
  AudioLines,
  Check,
  ChevronDown,
  CircleAlert,
  CornerDownLeft,
  Cpu,
  Database,
  History,
  Loader2,
  Mic,
  MicOff,
  Send,
  Sparkles,
  Terminal,
  WandSparkles,
  X,
  Zap,
} from 'lucide-react';

/* ================================================================
   TYPES
================================================================ */

interface QueryInterfaceProps {
  observations: Observation[];
  activeObservationIds: string[];
  onExecuteQuery: (queryText: string) => void;
  isAnalyzing: boolean;
}

type QueryTask =
  | 'CHANGE DETECTION'
  | 'SCENE DESCRIPTION'
  | 'VISUAL QUESTION ANSWERING'
  | 'OBJECT / REGION GROUNDING'
  | 'OPTICAL + SAR ANALYSIS'
  | 'LAND COVER ANALYSIS';

type QueryTarget =
  | 'WATER BODIES'
  | 'VEGETATION'
  | 'BUILT-UP AREAS'
  | 'INFRASTRUCTURE'
  | 'FLOODED AREAS'
  | 'LAND COVER'
  | 'ANY TARGET';

type QueryTime =
  | 'CURRENT OBSERVATION'
  | 'BETWEEN SELECTED DATES'
  | 'BEFORE → AFTER'
  | '2024 → 2026';

interface RoutingPrediction {
  task: QueryTask;
  specialist: string;
  confidence: number;
  reason: string;
}


/*
 * Browser Speech Recognition is not available in every browser.
 * We define a minimal local type instead of adding another package.
 */
interface SpeechRecognitionEventLike extends Event {
  results: SpeechRecognitionResultList;
}

interface SpeechRecognitionLike {
  continuous: boolean;
  interimResults: boolean;
  lang: string;

  start: () => void;
  stop: () => void;

  onstart: (() => void) | null;
  onend: (() => void) | null;
  onerror: ((event: Event) => void) | null;
  onresult:
  | ((event: SpeechRecognitionEventLike) => void)
  | null;
}

declare global {
  interface Window {
    SpeechRecognition?: new () => SpeechRecognitionLike;
    webkitSpeechRecognition?: new () => SpeechRecognitionLike;
  }
}

/* ================================================================
   CONSTANTS
================================================================ */

const TASK_OPTIONS: QueryTask[] = [
  'CHANGE DETECTION',
  'SCENE DESCRIPTION',
  'VISUAL QUESTION ANSWERING',
  'OBJECT / REGION GROUNDING',
  'OPTICAL + SAR ANALYSIS',
  'LAND COVER ANALYSIS',
];

const TARGET_OPTIONS: QueryTarget[] = [
  'WATER BODIES',
  'VEGETATION',
  'BUILT-UP AREAS',
  'INFRASTRUCTURE',
  'FLOODED AREAS',
  'LAND COVER',
  'ANY TARGET',
];

const TIME_OPTIONS: QueryTime[] = [
  'CURRENT OBSERVATION',
  'BETWEEN SELECTED DATES',
  'BEFORE → AFTER',
  '2024 → 2026',
];

/* ================================================================
   COMPONENT
================================================================ */

export const QueryInterface: React.FC<
  QueryInterfaceProps
> = ({
  observations,
  activeObservationIds,
  onExecuteQuery,
  isAnalyzing,
}) => {
    /* ==============================================================
       STATE
    ============================================================== */

    const [queryText, setQueryText] =
      useState<string>('');

    const [showBuilder, setShowBuilder] =
      useState<boolean>(true);

    const [showRoutingDetails, setShowRoutingDetails] =
      useState<boolean>(true);

    const [isListening, setIsListening] =
      useState<boolean>(false);

    const [voiceSupported, setVoiceSupported] =
      useState<boolean>(false);

    const [interimTranscript, setInterimTranscript] =
      useState<string>('');

    const [selectedTask, setSelectedTask] =
      useState<QueryTask>('CHANGE DETECTION');

    const [selectedTarget, setSelectedTarget] =
      useState<QueryTarget>('WATER BODIES');

    const [selectedTime, setSelectedTime] =
      useState<QueryTime>('BETWEEN SELECTED DATES');

    const [recentQueries, setRecentQueries] =
      useState<string[]>([]);

    const [showHistory, setShowHistory] =
      useState<boolean>(false);

    const [builderOpen, setBuilderOpen] =
      useState<'task' | 'target' | 'time' | null>(
        null
      );

    const speechRecognitionRef =
      useRef<SpeechRecognitionLike | null>(null);

    const textareaRef =
      useRef<HTMLTextAreaElement>(null);

    /* ==============================================================
       ACTIVE OBSERVATIONS
    ============================================================== */

    const activeObsList = useMemo(
      () =>
        observations.filter((observation) =>
          activeObservationIds.includes(
            observation.id
          )
        ),
      [observations, activeObservationIds]
    );

    const isMultiObs =
      activeObsList.length >= 2;

    const isOpticalAndSar =
      activeObsList.some(
        (observation) =>
          observation.modality === 'OPTICAL'
      ) &&
      activeObsList.some(
        (observation) =>
          observation.modality === 'SAR'
      );

    const hasOptical =
      activeObsList.some(
        (observation) =>
          observation.modality === 'OPTICAL'
      );

    const hasSar =
      activeObsList.some(
        (observation) =>
          observation.modality === 'SAR'
      );

    /* ==============================================================
       SPEECH SUPPORT
    ============================================================== */

    useEffect(() => {
      const SpeechRecognition =
        window.SpeechRecognition ||
        window.webkitSpeechRecognition;

      setVoiceSupported(
        Boolean(SpeechRecognition)
      );

      if (!SpeechRecognition) {
        return;
      }

      const recognition =
        new SpeechRecognition();

      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'en-IN';

      recognition.onstart = () => {
        setIsListening(true);
        setInterimTranscript('');
      };

      recognition.onend = () => {
        setIsListening(false);
        setInterimTranscript('');
      };

      recognition.onerror = () => {
        setIsListening(false);
        setInterimTranscript('');
      };

      recognition.onresult = (
        event: SpeechRecognitionEventLike
      ) => {
        let finalTranscript = '';
        let interim = '';

        for (
          let i = event.results.length - 1;
          i >= 0;
          i--
        ) {
          const result =
            event.results[i];

          const transcript =
            result[0]?.transcript || '';

          if (result.isFinal) {
            finalTranscript =
              transcript + ' ' + finalTranscript;
          } else {
            interim =
              transcript + interim;
          }
        }

        if (finalTranscript.trim()) {
          setQueryText((current) => {
            const separator =
              current.trim().length > 0
                ? ' '
                : '';

            return (
              current.trim() +
              separator +
              finalTranscript.trim()
            );
          });
        }

        setInterimTranscript(
          interim.trim()
        );
      };

      speechRecognitionRef.current =
        recognition;

      return () => {
        recognition.stop();
        speechRecognitionRef.current =
          null;
      };
    }, []);

    /* ==============================================================
       VOICE CONTROL
    ============================================================== */

    const toggleVoiceInput = () => {
      if (!voiceSupported) {
        return;
      }

      const recognition =
        speechRecognitionRef.current;

      if (!recognition) {
        return;
      }

      if (isListening) {
        recognition.stop();
        return;
      }

      try {
        recognition.start();
      } catch {
        setIsListening(false);
      }
    };

    /* ==============================================================
       QUERY ROUTING
    ============================================================== */

    const routingPrediction =
      useMemo<RoutingPrediction>(() => {
        const query =
          queryText.toLowerCase();

        /*
         * Cross-modal takes priority because it is
         * a distinct SatQuery analysis mode.
         */
        if (
          isOpticalAndSar ||
          query.includes('optical') &&
          query.includes('sar') ||
          query.includes('radar')
        ) {
          return {
            task: 'OPTICAL + SAR ANALYSIS',
            specialist:
              'Optical-SAR Fusion Model',
            confidence: 96,
            reason:
              'Multiple sensor modalities detected.',
          };
        }

        /*
         * Temporal / change analysis.
         */
        if (
          isMultiObs ||
          query.includes('change') ||
          query.includes('changed') ||
          query.includes('between') ||
          query.includes('compare') ||
          query.includes('before') ||
          query.includes('after')
        ) {
          return {
            task: 'CHANGE DETECTION',
            specialist:
              'Change Understanding Model',
            confidence:
              isMultiObs ? 95 : 86,
            reason:
              'Temporal comparison intent detected.',
          };
        }

        /*
         * Object / region grounding.
         */
        if (
          query.includes('where') ||
          query.includes('locate') ||
          query.includes('find') ||
          query.includes('identify')
        ) {
          return {
            task: 'OBJECT / REGION GROUNDING',
            specialist:
              'Remote Sensing Grounding Model',
            confidence: 91,
            reason:
              'Spatial target identification detected.',
          };
        }

        /*
         * Land-cover intent.
         */
        if (
          query.includes('land cover') ||
          query.includes('landcover') ||
          query.includes('vegetation') ||
          query.includes('forest') ||
          query.includes('agriculture') ||
          query.includes('crop')
        ) {
          return {
            task: 'LAND COVER ANALYSIS',
            specialist:
              'Remote Sensing Classification Model',
            confidence: 89,
            reason:
              'Land-cover classification intent detected.',
          };
        }

        /*
         * Generic image question.
         */
        if (
          query.includes('?') ||
          query.includes('what') ||
          query.includes('how') ||
          query.includes('describe')
        ) {
          return {
            task: 'VISUAL QUESTION ANSWERING',
            specialist:
              'Remote Sensing VQA Model',
            confidence: 84,
            reason:
              'Natural-language visual question detected.',
          };
        }

        return {
          task: 'SCENE DESCRIPTION',
          specialist:
            'Remote Sensing Captioning Model',
          confidence: 72,
          reason:
            'General observation understanding selected.',
        };
      }, [
        queryText,
        isMultiObs,
        isOpticalAndSar,
      ]);

    /* ==============================================================
       QUERY SUGGESTIONS
    ============================================================== */

    const suggestions = useMemo(() => {
      if (isOpticalAndSar) {
        return [
          'Compare optical and SAR observations',
          'What does SAR reveal that optical imagery does not?',
          'Identify water-covered regions using both sensors',
          'Analyze surface changes using optical-SAR fusion',
        ];
      }

      if (isMultiObs) {
        return [
          'What changed between these observations?',
          'Has the built-up area increased?',
          'Show vegetation change between dates',
          'Identify newly developed regions',
        ];
      }

      if (hasSar) {
        return [
          'Describe the radar scene',
          'Identify surface structures',
          'Find water-covered regions',
          'Analyze radar backscatter patterns',
        ];
      }

      if (hasOptical) {
        return [
          'Describe this observation',
          'Identify major infrastructure objects',
          'Find the water bodies',
          'Analyze land cover categories',
        ];
      }

      return [
        'Describe this observation',
        'What are the major features in this image?',
        'Identify important regions',
        'Analyze the scene',
      ];
    }, [
      isOpticalAndSar,
      isMultiObs,
      hasSar,
      hasOptical,
    ]);

    /* ==============================================================
       BUILDER QUERY
    ============================================================== */

    const buildQueryFromTemplate = (
      task: QueryTask,
      target: QueryTarget,
      time: QueryTime
    ): string => {
      const targetText =
        target === 'ANY TARGET'
          ? 'the major features'
          : target.toLowerCase();

      switch (task) {
        case 'CHANGE DETECTION':
          if (
            time === 'CURRENT OBSERVATION'
          ) {
            return `Detect changes in ${targetText}.`;
          }

          return `Detect changes in ${targetText} ${time.toLowerCase()}.`;

        case 'SCENE DESCRIPTION':
          return `Describe the scene with focus on ${targetText}.`;

        case 'VISUAL QUESTION ANSWERING':
          return `What can be observed about ${targetText}?`;

        case 'OBJECT / REGION GROUNDING':
          return `Locate and identify ${targetText}.`;

        case 'OPTICAL + SAR ANALYSIS':
          return `Compare optical and SAR observations with focus on ${targetText}.`;

        case 'LAND COVER ANALYSIS':
          return `Analyze the ${targetText} and describe the dominant land-cover patterns.`;

        default:
          return '';
      }
    };

    const applyBuilder = () => {
      const generated =
        buildQueryFromTemplate(
          selectedTask,
          selectedTarget,
          selectedTime
        );

      setQueryText(generated);
      setBuilderOpen(null);

      window.setTimeout(() => {
        textareaRef.current?.focus();
      }, 0);
    };

    /* ==============================================================
       QUERY EXECUTION
    ============================================================== */

    const handleSubmit = (
      event: React.FormEvent
    ) => {
      event.preventDefault();

      const cleanQuery =
        queryText.trim();

      if (!cleanQuery || isAnalyzing) {
        return;
      }

      setRecentQueries((current) => {
        const filtered =
          current.filter(
            (query) => query !== cleanQuery
          );

        return [
          cleanQuery,
          ...filtered,
        ].slice(0, 5);
      });

      onExecuteQuery(cleanQuery);
    };

    /* ==============================================================
       SUGGESTION
    ============================================================== */

    const handleSuggestionClick = (
      suggestion: string
    ) => {
      setQueryText(suggestion);

      window.setTimeout(() => {
        textareaRef.current?.focus();
      }, 0);
    };

    /* ==============================================================
       KEYBOARD
    ============================================================== */

    const handleTextareaKeyDown = (
      event: React.KeyboardEvent<HTMLTextAreaElement>
    ) => {
      /*
       * Ctrl/Cmd + Enter always executes.
       *
       * Plain Enter remains available for multiline
       * natural-language queries.
       */
      if (
        event.key === 'Enter' &&
        (event.ctrlKey || event.metaKey)
      ) {
        event.preventDefault();

        if (
          queryText.trim() &&
          !isAnalyzing
        ) {
          onExecuteQuery(
            queryText.trim()
          );
        }
      }
    };

    /* ==============================================================
       ROUTING COLOR
    ============================================================== */

    const routingAccent =
      routingPrediction.task ===
        'OPTICAL + SAR ANALYSIS'
        ? 'text-sat-sar'
        : routingPrediction.task ===
          'CHANGE DETECTION'
          ? 'text-sat-change'
          : 'text-sat-accent';

    /* ==============================================================
       RENDER
    ============================================================== */

    return (
      <div
        className="
        relative
        flex
        h-full
        min-h-0
        flex-col
        overflow-hidden
        border-l
        border-sat-border
        bg-sat-surface/90
        backdrop-blur-xl
        font-sans
        select-none
      "
      >
        {/* ==========================================================
          HEADER
      ========================================================== */}

        <div
          className="
          shrink-0
          border-b border-sat-border
          bg-sat-panel/40
          px-4 py-3.5
        "
        >
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <div
                className="
                flex
                h-9 w-9
                shrink-0
                items-center
                justify-center
                rounded-md
                border border-sat-accent/30
                bg-sat-accent/10
                text-sat-accent
              "
              >
                <Terminal className="h-4 w-4" />
              </div>

              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <h2
                    className="
                    truncate
                    font-display
                    text-sm
                    font-bold
                    uppercase
                    tracking-[0.12em]
                    text-sat-text
                  "
                  >
                    Ask SatQuery
                  </h2>

                  <span
                    className="
                    rounded-full
                    border border-sat-stable/30
                    bg-sat-stable/10
                    px-1.5 py-0.5
                    font-mono
                    text-[7px]
                    font-bold
                    tracking-wider
                    text-sat-stable
                  "
                  >
                    AGENT
                  </span>
                </div>

                <div
                  className="
                  mt-0.5
                  font-mono
                  text-[8px]
                  uppercase
                  tracking-wider
                  text-sat-dim
                "
                >
                  Natural-language Earth observation
                </div>
              </div>
            </div>

            <div className="flex items-center gap-1.5">
              {recentQueries.length > 0 && (
                <button
                  type="button"
                  onClick={() =>
                    setShowHistory(
                      (current) => !current
                    )
                  }
                  className="
                  flex
                  h-7 w-7
                  items-center
                  justify-center
                  rounded-md
                  border border-sat-border
                  bg-sat-bg
                  text-sat-dim
                  transition-colors
                  hover:border-sat-accent
                  hover:text-sat-accent
                "
                  title="Recent queries"
                >
                  <History className="h-3.5 w-3.5" />
                </button>
              )}

              <div
                className="
                flex
                items-center
                gap-1.5
                rounded
                border border-sat-stable/20
                bg-sat-stable/10
                px-2
                py-1
              "
              >
                <span className="h-1.5 w-1.5 rounded-full bg-sat-stable" />

                <span className="font-mono text-[7px] font-bold uppercase tracking-wider text-sat-stable">
                  READY
                </span>
              </div>
            </div>
          </div>

          {/* ========================================================
            HISTORY DROPDOWN
        ======================================================== */}

          {showHistory && (
            <div
              className="
              mt-3
              overflow-hidden
              rounded-md
              border border-sat-border
              bg-sat-bg
            "
            >
              <div
                className="
                flex
                items-center
                justify-between
                border-b border-sat-border
                px-3 py-2
              "
              >
                <span className="font-mono text-[8px] font-bold uppercase tracking-wider text-sat-dim">
                  Recent queries
                </span>

                <button
                  type="button"
                  onClick={() =>
                    setShowHistory(false)
                  }
                  className="text-sat-dim hover:text-sat-text"
                >
                  <X className="h-3 w-3" />
                </button>
              </div>

              <div className="divide-y divide-sat-border">
                {recentQueries.map(
                  (query, index) => (
                    <button
                      key={`${query}-${index}`}
                      type="button"
                      onClick={() => {
                        setQueryText(query);
                        setShowHistory(false);
                      }}
                      className="
                      block
                      w-full
                      truncate
                      px-3 py-2
                      text-left
                      font-sans
                      text-[9px]
                      text-sat-muted
                      transition-colors
                      hover:bg-sat-panel
                      hover:text-sat-accent
                    "
                    >
                      {query}
                    </button>
                  )
                )}
              </div>
            </div>
          )}
        </div>

        {/* ==========================================================
          MAIN QUERY AREA
      ========================================================== */}

        <div
          className="
          shrink-0
          border-b border-sat-border
          bg-sat-bg/80
          p-4
        "
        >
          <form
            onSubmit={handleSubmit}
            className="space-y-3"
          >
            {/* Context line */}
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-1.5">
                <Activity className="h-3 w-3 text-sat-accent" />

                <span className="font-mono text-[8px] font-bold uppercase tracking-wider text-sat-dim">
                  QUERY INPUT
                </span>
              </div>

              <span className="font-mono text-[7px] uppercase tracking-wider text-sat-dim">
                {activeObsList.length}{' '}
                OBSERVATION
                {activeObsList.length === 1
                  ? ''
                  : 'S'}
              </span>
            </div>

            {/* ======================================================
              QUERY TEXTAREA
          ====================================================== */}

            <div
              className={`
              relative
              overflow-hidden
              rounded-lg
              border
              bg-sat-surface
              transition-all
              ${isListening
                  ? 'border-sat-change shadow-[0_0_0_1px_rgba(217,119,6,0.15)]'
                  : 'border-sat-border focus-within:border-sat-accent/70'
                }
            `}
            >
              <textarea
                ref={textareaRef}
                value={queryText}
                onChange={(event) =>
                  setQueryText(
                    event.target.value
                  )
                }
                onKeyDown={
                  handleTextareaKeyDown
                }
                placeholder="Ask anything about the selected Earth observations..."
                rows={4}
                disabled={isAnalyzing}
                aria-label="Earth observation query"
                className="
                block
                w-full
                resize-none
                bg-transparent
                px-3
                pb-11
                pt-3
                font-sans
                text-xs
                leading-relaxed
                text-sat-text
                outline-none
                placeholder:text-sat-dim
                disabled:cursor-not-allowed
                disabled:opacity-60
              "
              />

              {/* Character / status */}
              <div
                className="
                pointer-events-none
                absolute
                bottom-2
                left-3
                font-mono
                text-[7px]
                text-sat-dim
              "
              >
                {queryText.length} CHAR
              </div>

              {/* Voice button */}
              <button
                type="button"
                onClick={toggleVoiceInput}
                disabled={
                  !voiceSupported ||
                  isAnalyzing
                }
                title={
                  voiceSupported
                    ? isListening
                      ? 'Stop voice input'
                      : 'Start voice input'
                    : 'Speech recognition is not supported in this browser'
                }
                className={`
                absolute
                bottom-2
                right-2
                flex
                h-7
                w-7
                items-center
                justify-center
                rounded-md
                border
                transition-all
                ${isListening
                    ? `
                      border-sat-change
                      bg-sat-change/15
                      text-sat-change
                    `
                    : `
                      border-sat-border
                      bg-sat-panel
                      text-sat-dim
                      hover:border-sat-accent
                      hover:text-sat-accent
                    `
                  }
                disabled:cursor-not-allowed
                disabled:opacity-40
              `}
              >
                {isListening ? (
                  <MicOff className="h-3.5 w-3.5" />
                ) : (
                  <Mic className="h-3.5 w-3.5" />
                )}
              </button>

              {/* Voice listening indicator */}
              {isListening && (
                <div
                  className="
                  absolute
                  bottom-2
                  left-1/2
                  flex
                  -translate-x-1/2
                  items-center
                  gap-1
                  rounded-full
                  border border-sat-change/20
                  bg-sat-change/10
                  px-2
                  py-1
                "
                >
                  <AudioLines className="h-3 w-3 text-sat-change" />

                  <span className="font-mono text-[7px] font-bold uppercase tracking-wider text-sat-change">
                    LISTENING
                  </span>

                  <VoiceBars />
                </div>
              )}
            </div>

            {/* Interim transcript */}
            {isListening &&
              interimTranscript && (
                <div
                  className="
                  rounded-md
                  border border-sat-change/20
                  bg-sat-change/[0.04]
                  px-3 py-2
                "
                >
                  <div className="font-mono text-[7px] uppercase tracking-wider text-sat-dim">
                    LIVE TRANSCRIPT
                  </div>

                  <div className="mt-1 font-sans text-[10px] italic text-sat-muted">
                    {interimTranscript}
                  </div>
                </div>
              )}

            {/* ======================================================
              GUIDED QUERY BUILDER
          ====================================================== */}

            <div
              className="
              overflow-visible
              rounded-lg
              border border-sat-border
              bg-sat-surface
            "
            >
              <button
                type="button"
                onClick={() =>
                  setShowBuilder(
                    (current) => !current
                  )
                }
                className="
                flex
                w-full
                items-center
                justify-between
                px-3 py-2.5
                text-left
              "
              >
                <div className="flex items-center gap-2">
                  <WandSparkles className="h-3 w-3 text-sat-accent" />

                  <span className="font-mono text-[8px] font-bold uppercase tracking-wider text-sat-text">
                    Guided Query Builder
                  </span>
                </div>

                <ChevronDown
                  className={`
                  h-3.5 w-3.5
                  text-sat-dim
                  transition-transform
                  ${showBuilder
                      ? 'rotate-180'
                      : ''
                    }
                `}
                />
              </button>

              {showBuilder && (
                <div
                  className="
                  border-t border-sat-border
                  p-3
                "
                >
                  <div className="grid grid-cols-1 gap-2">
                    <BuilderSelector
                      label="TASK"
                      value={selectedTask}
                      options={TASK_OPTIONS}
                      open={
                        builderOpen ===
                        'task'
                      }
                      onToggle={() =>
                        setBuilderOpen(
                          builderOpen ===
                            'task'
                            ? null
                            : 'task'
                        )
                      }
                      onSelect={(value) => {
                        setSelectedTask(
                          value as QueryTask
                        );
                        setBuilderOpen(null);
                      }}
                    />

                    <BuilderSelector
                      label="TARGET"
                      value={selectedTarget}
                      options={TARGET_OPTIONS}
                      open={
                        builderOpen ===
                        'target'
                      }
                      onToggle={() =>
                        setBuilderOpen(
                          builderOpen ===
                            'target'
                            ? null
                            : 'target'
                        )
                      }
                      onSelect={(value) => {
                        setSelectedTarget(
                          value as QueryTarget
                        );
                        setBuilderOpen(null);
                      }}
                    />

                    <BuilderSelector
                      label="TEMPORAL"
                      value={selectedTime}
                      options={TIME_OPTIONS}
                      open={
                        builderOpen ===
                        'time'
                      }
                      onToggle={() =>
                        setBuilderOpen(
                          builderOpen ===
                            'time'
                            ? null
                            : 'time'
                        )
                      }
                      onSelect={(value) => {
                        setSelectedTime(
                          value as QueryTime
                        );
                        setBuilderOpen(null);
                      }}
                    />
                  </div>

                  <button
                    type="button"
                    onClick={
                      applyBuilder
                    }
                    className="
                    mt-2
                    flex
                    w-full
                    items-center
                    justify-center
                    gap-2
                    rounded-md
                    border border-sat-accent/30
                    bg-sat-accent/10
                    px-3 py-2
                    font-mono
                    text-[8px]
                    font-bold
                    uppercase
                    tracking-wider
                    text-sat-accent
                    transition-colors
                    hover:bg-sat-accent/15
                  "
                  >
                    <WandSparkles className="h-3 w-3" />
                    BUILD QUERY
                  </button>
                </div>
              )}
            </div>

            {/* ======================================================
              AUTO ROUTING
          ====================================================== */}

            <div
              className="
              overflow-hidden
              rounded-lg
              border border-sat-accent/20
              bg-sat-accent/[0.035]
            "
            >
              <button
                type="button"
                onClick={() =>
                  setShowRoutingDetails(
                    (current) => !current
                  )
                }
                className="
                flex
                w-full
                items-center
                justify-between
                px-3 py-2.5
                text-left
              "
              >
                <div className="flex items-center gap-2">
                  <Zap className="h-3 w-3 text-sat-accent" />

                  <span className="font-mono text-[8px] font-bold uppercase tracking-wider text-sat-accent">
                    Agent Routing
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  <span
                    className={`
                    font-mono
                    text-[7px]
                    font-bold
                    ${routingAccent}
                  `}
                  >
                    {routingPrediction.confidence}%
                  </span>

                  <ChevronDown
                    className={`
                    h-3 w-3
                    text-sat-dim
                    transition-transform
                    ${showRoutingDetails
                        ? 'rotate-180'
                        : ''
                      }
                  `}
                  />
                </div>
              </button>

              {showRoutingDetails && (
                <div
                  className="
                  border-t border-sat-accent/15
                  px-3
                  pb-3
                  pt-2.5
                "
                >
                  <div className="flex items-start gap-3">
                    <div
                      className="
                      flex
                      h-8 w-8
                      shrink-0
                      items-center
                      justify-center
                      rounded-md
                      border border-sat-accent/20
                      bg-sat-accent/10
                      text-sat-accent
                    "
                    >
                      <Cpu className="h-3.5 w-3.5" />
                    </div>

                    <div className="min-w-0 flex-1">
                      <div className="font-mono text-[7px] uppercase tracking-wider text-sat-dim">
                        TASK IDENTIFIED
                      </div>

                      <div
                        className={`
                        mt-0.5
                        font-mono
                        text-[10px]
                        font-bold
                        ${routingAccent}
                      `}
                      >
                        {routingPrediction.task}
                      </div>

                      <div className="mt-2 font-mono text-[7px] uppercase tracking-wider text-sat-dim">
                        SPECIALIST
                      </div>

                      <div className="mt-0.5 truncate font-mono text-[9px] font-semibold text-sat-text">
                        {routingPrediction.specialist}
                      </div>
                    </div>
                  </div>

                  <div
                    className="
                    mt-2.5
                    flex
                    items-center
                    gap-2
                    rounded
                    border border-sat-border
                    bg-sat-bg
                    px-2.5
                    py-2
                  "
                  >
                    <Check className="h-3 w-3 shrink-0 text-sat-stable" />

                    <span className="font-sans text-[8px] leading-relaxed text-sat-muted">
                      {routingPrediction.reason}
                    </span>
                  </div>

                  <div className="mt-2 flex items-center justify-between font-mono text-[7px]">
                    <span className="text-sat-dim">
                      INPUTS
                    </span>

                    <span className="font-semibold text-sat-text">
                      {activeObsList.length}{' '}
                      OBSERVATION
                      {activeObsList.length ===
                        1
                        ? ''
                        : 'S'}
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* ======================================================
              READINESS
          ====================================================== */}

            <QueryReadiness
              queryText={queryText}
              observationCount={
                activeObsList.length
              }
              isMultiObs={isMultiObs}
              isOpticalAndSar={
                isOpticalAndSar
              }
              predictedTask={
                routingPrediction.task
              }
            />

            {/* ======================================================
              ACTION BAR
          ====================================================== */}

            <div className="flex items-center justify-between gap-3 pt-1">
              <div className="flex items-center gap-1.5">
                <CornerDownLeft className="h-3 w-3 text-sat-dim" />

                <span className="font-mono text-[7px] uppercase tracking-wider text-sat-dim">
                  CTRL + ENTER TO RUN
                </span>
              </div>

              <button
                type="submit"
                disabled={
                  !queryText.trim() ||
                  isAnalyzing
                }
                className={`
                flex
                items-center
                gap-2
                rounded-md
                px-4
                py-2.5
                font-mono
                text-[9px]
                font-bold
                uppercase
                tracking-wider
                transition-all
                ${queryText.trim() &&
                    !isAnalyzing
                    ? `
                      bg-sat-accent
                      text-slate-950
                      shadow-md
                      shadow-sat-accent/20
                      hover:bg-sky-300
                    `
                    : `
                      cursor-not-allowed
                      border border-sat-border
                      bg-sat-panel
                      text-sat-dim
                    `
                  }
              `}
              >
                {isAnalyzing ? (
                  <>
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ANALYZING
                  </>
                ) : (
                  <>
                    RUN ANALYSIS
                    <Send className="h-3.5 w-3.5" />
                  </>
                )}
              </button>
            </div>
          </form>
        </div>

        {/* ==========================================================
          SUGGESTIONS
      ========================================================== */}

        <div
          className="
          min-h-0
          flex-1
          overflow-y-auto
          p-4
        "
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <Sparkles className="h-3.5 w-3.5 text-sat-accent" />

              <span
                className="
                font-mono
                text-[9px]
                font-bold
                uppercase
                tracking-[0.12em]
                text-sat-text
              "
              >
                Suggested Analysis
              </span>
            </div>

            <span className="font-mono text-[7px] uppercase tracking-wider text-sat-dim">
              CONTEXT AWARE
            </span>
          </div>

          <div className="mt-3 space-y-2">
            {suggestions.map(
              (suggestion, index) => (
                <button
                  key={`${suggestion}-${index}`}
                  type="button"
                  onClick={() =>
                    handleSuggestionClick(
                      suggestion
                    )
                  }
                  disabled={isAnalyzing}
                  className="
                  group
                  flex
                  w-full
                  items-start
                  justify-between
                  gap-3
                  rounded-md
                  border border-sat-border
                  bg-sat-bg
                  p-3
                  text-left
                  transition-all
                  hover:border-sat-accent/50
                  hover:bg-sat-panel
                  disabled:cursor-not-allowed
                  disabled:opacity-50
                "
                >
                  <div className="flex min-w-0 items-start gap-2">
                    <span
                      className="
                      mt-0.5
                      flex
                      h-4 w-4
                      shrink-0
                      items-center
                      justify-center
                      rounded
                      border border-sat-border
                      font-mono
                      text-[6px]
                      text-sat-dim
                      transition-colors
                      group-hover:border-sat-accent
                      group-hover:text-sat-accent
                    "
                    >
                      {String(index + 1).padStart(
                        2,
                        '0'
                      )}
                    </span>

                    <span className="font-sans text-[10px] leading-relaxed text-sat-muted transition-colors group-hover:text-sat-text">
                      {suggestion}
                    </span>
                  </div>

                  <span
                    className="
                    shrink-0
                    font-mono
                    text-[7px]
                    font-bold
                    uppercase
                    tracking-wider
                    text-sat-dim
                    transition-colors
                    group-hover:text-sat-accent
                  "
                  >
                    USE
                  </span>
                </button>
              )
            )}
          </div>

          {/* Context summary */}
          <div
            className="
            mt-4
            rounded-md
            border border-sat-border
            bg-sat-surface
            p-3
          "
          >
            <div className="flex items-center gap-2">
              <Database className="h-3 w-3 text-sat-accent" />

              <span className="font-mono text-[8px] font-bold uppercase tracking-wider text-sat-text">
                Query Context
              </span>
            </div>

            <div className="mt-2 grid grid-cols-2 gap-1.5">
              <ContextItem
                label="OBSERVATIONS"
                value={String(
                  activeObsList.length
                )}
              />

              <ContextItem
                label="TEMPORAL"
                value={
                  isMultiObs
                    ? 'PAIR AVAILABLE'
                    : 'SINGLE'
                }
              />

              <ContextItem
                label="OPTICAL"
                value={
                  hasOptical
                    ? 'AVAILABLE'
                    : '—'
                }
              />

              <ContextItem
                label="SAR"
                value={
                  hasSar
                    ? 'AVAILABLE'
                    : '—'
                }
              />
            </div>
          </div>
        </div>

        {/* ==========================================================
          FOOTER
      ========================================================== */}

        <div
          className="
          shrink-0
          space-y-1.5
          border-t border-sat-border
          bg-sat-bg
          p-3
          font-mono
          text-[7px]
        "
        >
          <div className="flex items-center justify-between">
            <span className="text-sat-dim">
              ORCHESTRATOR
            </span>

            <span className="font-semibold text-sat-text">
              SatQuery-Agent v3
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-sat-dim">
              PIPELINE
            </span>

            <span className="text-sat-accent">
              AGENTIC RS ANALYSIS
            </span>
          </div>

          <div className="flex items-center justify-between border-t border-sat-border/50 pt-1.5">
            <span className="text-sat-dim">
              EXECUTION
            </span>

            <span className="flex items-center gap-1 text-sat-stable">
              <span className="h-1.5 w-1.5 rounded-full bg-sat-stable" />
              AUDITABLE
            </span>
          </div>
        </div>
      </div>
    );
  };

/* ================================================================
   BUILDER SELECTOR
================================================================ */

interface BuilderSelectorProps {
  label: string;
  value: string;
  options: string[];
  open: boolean;
  onToggle: () => void;
  onSelect: (value: string) => void;
}

const BuilderSelector: React.FC<
  BuilderSelectorProps
> = ({
  label,
  value,
  options,
  open,
  onToggle,
  onSelect,
}) => {
    return (
      <div className="relative">
        <button
          type="button"
          onClick={onToggle}
          className="
          flex
          w-full
          items-center
          justify-between
          gap-3
          rounded-md
          border border-sat-border
          bg-sat-bg
          px-2.5
          py-2
          text-left
          transition-colors
          hover:border-sat-accent/50
        "
        >
          <div className="min-w-0">
            <div className="font-mono text-[6px] font-bold uppercase tracking-wider text-sat-dim">
              {label}
            </div>

            <div className="mt-0.5 truncate font-mono text-[9px] font-semibold text-sat-text">
              {value}
            </div>
          </div>

          <ChevronDown
            className={`
            h-3 w-3
            shrink-0
            text-sat-dim
            transition-transform
            ${open ? 'rotate-180' : ''}
          `}
          />
        </button>

        {open && (
          <div
            className="
            absolute
            left-0
            right-0
            top-full
            z-50
            mt-1
            overflow-hidden
            rounded-md
            border border-sat-border
            bg-sat-surface
            shadow-2xl
          "
          >
            {options.map((option) => (
              <button
                key={option}
                type="button"
                onClick={() =>
                  onSelect(option)
                }
                className="
                flex
                w-full
                items-center
                justify-between
                px-2.5
                py-2
                text-left
                font-mono
                text-[8px]
                text-sat-muted
                transition-colors
                hover:bg-sat-panel
                hover:text-sat-accent
              "
              >
                <span>{option}</span>

                {option === value && (
                  <Check className="h-3 w-3 text-sat-accent" />
                )}
              </button>
            ))}
          </div>
        )}
      </div>
    );
  };

/* ================================================================
   QUERY READINESS
================================================================ */

interface QueryReadinessProps {
  queryText: string;
  observationCount: number;
  isMultiObs: boolean;
  isOpticalAndSar: boolean;
  predictedTask: QueryTask;
}

const QueryReadiness: React.FC<
  QueryReadinessProps
> = ({
  queryText,
  observationCount,
  isMultiObs,
  isOpticalAndSar,
  predictedTask,
}) => {
    const hasQuery =
      queryText.trim().length > 0;

    const requiresPair =
      predictedTask ===
      'CHANGE DETECTION' ||
      predictedTask ===
      'OPTICAL + SAR ANALYSIS';

    const pairAvailable =
      predictedTask ===
        'OPTICAL + SAR ANALYSIS'
        ? isOpticalAndSar
        : isMultiObs;

    const items = [
      {
        label: 'QUERY',
        ok: hasQuery,
      },
      {
        label: 'OBSERVATION',
        ok: observationCount > 0,
      },
      {
        label: requiresPair
          ? 'REQUIRED INPUTS'
          : 'INPUTS',
        ok: requiresPair
          ? pairAvailable
          : observationCount > 0,
      },
    ];

    return (
      <div
        className="
        rounded-md
        border border-sat-border
        bg-sat-surface
        px-3
        py-2.5
      "
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <Activity className="h-3 w-3 text-sat-accent" />

            <span className="font-mono text-[7px] font-bold uppercase tracking-wider text-sat-dim">
              Query readiness
            </span>
          </div>

          <span
            className={`
            font-mono
            text-[7px]
            font-bold
            uppercase
            ${items.every((item) => item.ok)
                ? 'text-sat-stable'
                : 'text-sat-change'
              }
          `}
          >
            {items.every((item) => item.ok)
              ? 'READY'
              : 'CHECK INPUTS'}
          </span>
        </div>

        <div className="mt-2 grid grid-cols-3 gap-1.5">
          {items.map((item) => (
            <div
              key={item.label}
              className={`
              flex
              items-center
              gap-1.5
              rounded
              border
              px-2
              py-1.5
              ${item.ok
                  ? 'border-sat-stable/20 bg-sat-stable/5'
                  : 'border-sat-change/20 bg-sat-change/5'
                }
            `}
            >
              {item.ok ? (
                <Check className="h-2.5 w-2.5 shrink-0 text-sat-stable" />
              ) : (
                <CircleAlert className="h-2.5 w-2.5 shrink-0 text-sat-change" />
              )}

              <span className="truncate font-mono text-[6px] font-bold uppercase text-sat-dim">
                {item.label}
              </span>
            </div>
          ))}
        </div>
      </div>
    );
  };

/* ================================================================
   CONTEXT ITEM
================================================================ */

interface ContextItemProps {
  label: string;
  value: string;
}

const ContextItem: React.FC<
  ContextItemProps
> = ({ label, value }) => {
  return (
    <div
      className="
        rounded
        border border-sat-border
        bg-sat-bg
        px-2
        py-1.5
      "
    >
      <div className="font-mono text-[6px] uppercase tracking-wider text-sat-dim">
        {label}
      </div>

      <div className="mt-0.5 font-mono text-[8px] font-bold text-sat-text">
        {value}
      </div>
    </div>
  );
};

/* ================================================================
   VOICE BARS
================================================================ */

const VoiceBars: React.FC = () => {
  return (
    <div className="flex h-3 items-center gap-[2px]">
      {[2, 5, 8, 4, 7, 3].map(
        (height, index) => (
          <span
            key={index}
            className="
              w-[2px]
              rounded-full
              bg-sat-change
              animate-pulse
            "
            style={{
              height: `${height}px`,
              animationDelay: `${index * 80}ms`,
            }}
          />
        )
      )}
    </div>
  );
};

export default QueryInterface;