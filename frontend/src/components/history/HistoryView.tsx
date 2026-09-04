import React, { useMemo, useState } from 'react';
import type { QueryHistoryItem } from '../../types/satquery';
import {
  ArrowUpRight,
  BarChart3,
  Check,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock,
  Download,
  FileJson,
  FileText,
  History,
  Play,
  RotateCcw,
  Search,
  ShieldCheck,
  Sparkles,
  X,
} from 'lucide-react';

interface HistoryViewProps {
  historyItems: QueryHistoryItem[];
  onOpenHistoryResult: (item: QueryHistoryItem) => void;
}

type ReplayStep = {
  label: string;
  shortLabel: string;
  description: string;
};

const REPLAY_STEPS: ReplayStep[] = [
  {
    label: 'Understanding request',
    shortLabel: 'UNDERSTAND',
    description:
      'The natural-language Earth observation question is interpreted and converted into an analysis intent.',
  },
  {
    label: 'Checking observations',
    shortLabel: 'VALIDATE',
    description:
      'The selected observation datasets are checked for availability and basic compatibility.',
  },
  {
    label: 'Determining analysis type',
    shortLabel: 'CLASSIFY',
    description:
      'The request is classified into the appropriate remote-sensing analysis category.',
  },
  {
    label: 'Selecting specialist model',
    shortLabel: 'ROUTE',
    description:
      'The SatQuery orchestration layer routes the request toward the relevant specialist capability.',
  },
  {
    label: 'Running analysis',
    shortLabel: 'ANALYZE',
    description:
      'The selected analysis is executed against the supplied Earth observation inputs.',
  },
  {
    label: 'Generating evidence',
    shortLabel: 'EVIDENCE',
    description:
      'Observable evidence and supporting analysis outputs are prepared for inspection.',
  },
  {
    label: 'Preparing result',
    shortLabel: 'RESULT',
    description:
      'The final answer, confidence and execution metadata are assembled into the result.',
  },
];

export const HistoryView: React.FC<HistoryViewProps> = ({
  historyItems,
  onOpenHistoryResult,
}) => {
  const [searchTerm, setSearchTerm] =
    useState('');

  const [selectedItem, setSelectedItem] =
    useState<QueryHistoryItem | null>(null);

  const [isReplayOpen, setIsReplayOpen] =
    useState(false);

  const [replayStep, setReplayStep] =
    useState(0);

  const [showExportMenu, setShowExportMenu] =
    useState<string | null>(null);

  const [sortNewestFirst, setSortNewestFirst] =
    useState(true);

  /* ================================================================
     FILTER + SORT
  ================================================================= */

  const filteredItems = useMemo(() => {
    const normalizedSearch =
      searchTerm.trim().toLowerCase();

    const filtered = historyItems.filter(
      (item) =>
        !normalizedSearch ||
        item.queryText
          .toLowerCase()
          .includes(normalizedSearch) ||
        item.analysisType
          .toLowerCase()
          .includes(normalizedSearch) ||
        item.observationsUsed.some((o) =>
          o.toLowerCase().includes(normalizedSearch)
        )
    );

    return [...filtered].sort((a, b) => {
      const first = a.timestamp;
      const second = b.timestamp;

      const comparison =
        first.localeCompare(second);

      return sortNewestFirst
        ? -comparison
        : comparison;
    });
  }, [
    historyItems,
    searchTerm,
    sortNewestFirst,
  ]);

  /* ================================================================
     SUMMARY METRICS
  ================================================================= */

  const averageConfidence = useMemo(() => {
    if (!historyItems.length) return 0;

    return Math.round(
      historyItems.reduce(
        (sum, item) => sum + item.confidence,
        0
      ) / historyItems.length
    );
  }, [historyItems]);

  const verifiedCount = historyItems.filter(
    (item) =>
      item.status
        .toLowerCase()
        .includes('complete') ||
      item.status
        .toLowerCase()
        .includes('verified')
  ).length;

  const uniqueAnalysisTypes = new Set(
    historyItems.map(
      (item) => item.analysisType
    )
  ).size;

  /* ================================================================
     OPEN RESULT
  ================================================================= */

  const openItem = (item: QueryHistoryItem) => {
    onOpenHistoryResult(item);
  };

  /* ================================================================
     REPLAY
  ================================================================= */

  const openReplay = (
    item: QueryHistoryItem
  ) => {
    setSelectedItem(item);
    setReplayStep(0);
    setIsReplayOpen(true);
    setShowExportMenu(null);
  };

  const closeReplay = () => {
    setIsReplayOpen(false);
    setSelectedItem(null);
    setReplayStep(0);
  };

  /* ================================================================
     EXPORT JSON

     This exports only fields guaranteed by the current
     QueryHistoryItem interface. It intentionally does not
     fabricate evidence geometry that is not present here.
  ================================================================= */

  const exportGeoJSON = (
    item: QueryHistoryItem
  ) => {
    const geoJson = {
      type: 'FeatureCollection',
      name: `SatQuery-${item.id}`,
      properties: {
        source: 'SatQuery AI',
        historyId: item.id,
        query: item.queryText,
        analysisType: item.analysisType,
        confidence: item.confidence,
        status: item.status,
        timestamp: item.timestamp,
        observations: item.observationsUsed,
        note:
          'No evidence geometry was present in QueryHistoryItem; this archive export therefore contains metadata only.',
      },
      features: [],
    };

    downloadFile(
      JSON.stringify(
        geoJson,
        null,
        2
      ),
      `satquery-${item.id}.geojson`,
      'application/geo+json'
    );

    setShowExportMenu(null);
  };

  /* ================================================================
     INTELLIGENCE BRIEF

     Uses a print-friendly HTML document so the browser's
     Print -> Save as PDF can produce a real PDF without
     adding a frontend dependency.
  ================================================================= */

  const exportIntelligenceBrief = (
    item: QueryHistoryItem
  ) => {
    const reportWindow =
      window.open(
        '',
        '_blank',
        'noopener,noreferrer,width=1100,height=800'
      );

    if (!reportWindow) {
      return;
    }

    const escapedQuery =
      escapeHtml(item.queryText);

    const escapedType =
      escapeHtml(item.analysisType);

    const escapedStatus =
      escapeHtml(item.status);

    const escapedTimestamp =
      escapeHtml(item.timestamp);

    const observationRows =
      item.observationsUsed
        .map(
          (observation, index) => `
            <div class="obs-row">
              <span class="obs-index">0${index + 1}</span>
              <span>${escapeHtml(
            observation
          )}</span>
            </div>
          `
        )
        .join('');

    const confidence =
      Math.max(
        0,
        Math.min(100, item.confidence)
      );

    reportWindow.document.write(`
      <!doctype html>
      <html>
        <head>
          <meta charset="utf-8" />
          <title>SatQuery Intelligence Brief — ${escapedType}</title>

          <style>
            @page {
              size: A4;
              margin: 16mm;
            }

            * {
              box-sizing: border-box;
            }

            body {
              margin: 0;
              color: #1c1814;
              background: #fffdf8;
              font-family:
                Inter,
                Arial,
                sans-serif;
            }

            .page {
              max-width: 900px;
              margin: 0 auto;
            }

            .header {
              display: flex;
              justify-content: space-between;
              align-items: flex-start;
              padding-bottom: 18px;
              border-bottom: 2px solid #1c1814;
            }

            .eyebrow {
              font-family: monospace;
              font-size: 10px;
              letter-spacing: 0.16em;
              font-weight: 700;
              text-transform: uppercase;
              color: #1677a8;
            }

            h1 {
              margin: 8px 0 4px;
              font-size: 26px;
              line-height: 1.1;
              letter-spacing: -0.02em;
            }

            .subtitle {
              color: #6b6257;
              font-size: 12px;
            }

            .exec {
              text-align: right;
              font-family: monospace;
              font-size: 9px;
              color: #6b6257;
            }

            .section {
              margin-top: 24px;
              break-inside: avoid;
            }

            .section-title {
              display: flex;
              justify-content: space-between;
              padding-bottom: 7px;
              border-bottom: 1px solid #d8cdbd;
              font-family: monospace;
              font-size: 10px;
              font-weight: 800;
              letter-spacing: 0.12em;
              text-transform: uppercase;
            }

            .question {
              margin-top: 12px;
              padding: 15px;
              background: #f2ece2;
              border-left: 3px solid #1677a8;
              font-size: 14px;
              line-height: 1.55;
            }

            .grid {
              display: grid;
              grid-template-columns: 1fr 1fr;
              gap: 10px;
              margin-top: 12px;
            }

            .card {
              padding: 13px;
              border: 1px solid #d8cdbd;
              background: #fffdf8;
            }

            .label {
              font-family: monospace;
              font-size: 8px;
              color: #81776a;
              text-transform: uppercase;
              letter-spacing: 0.08em;
            }

            .value {
              margin-top: 5px;
              font-family: monospace;
              font-size: 11px;
              font-weight: 700;
            }

            .confidence {
              margin-top: 12px;
            }

            .bar {
              height: 8px;
              margin-top: 7px;
              background: #eae2d5;
              overflow: hidden;
            }

            .fill {
              height: 100%;
              width: ${confidence}%;
              background: #08745d;
            }

            .obs-row {
              display: flex;
              gap: 12px;
              padding: 10px 0;
              border-bottom: 1px solid #eae2d5;
              font-family: monospace;
              font-size: 10px;
            }

            .obs-index {
              color: #1677a8;
              font-weight: 800;
            }

            .timeline {
              margin-top: 10px;
            }

            .step {
              display: flex;
              gap: 12px;
              padding: 9px 0;
              border-bottom: 1px solid #eae2d5;
            }

            .dot {
              width: 16px;
              height: 16px;
              flex: 0 0 16px;
              border-radius: 50%;
              background: #08745d;
            }

            .step-title {
              font-family: monospace;
              font-size: 10px;
              font-weight: 800;
            }

            .step-description {
              margin-top: 3px;
              color: #6b6257;
              font-size: 10px;
              line-height: 1.4;
            }

            .footer {
              margin-top: 35px;
              padding-top: 12px;
              border-top: 1px solid #d8cdbd;
              display: flex;
              justify-content: space-between;
              font-family: monospace;
              font-size: 8px;
              color: #81776a;
            }

            @media print {
              .no-print {
                display: none;
              }
            }
          </style>
        </head>

        <body>
          <main class="page">

            <header class="header">
              <div>
                <div class="eyebrow">
                  SATQUERY AI
                </div>

                <h1>
                  Earth Observation
                  Intelligence Brief
                </h1>

                <div class="subtitle">
                  Auditable analysis archive
                </div>
              </div>

              <div class="exec">
                <div>HISTORY ID</div>
                <strong>${escapeHtml(
      item.id
    )}</strong>

                <div style="margin-top:8px">
                  ${escapedTimestamp}
                </div>
              </div>
            </header>

            <section class="section">
              <div class="section-title">
                <span>Analysis</span>
                <span>${escapedStatus}</span>
              </div>

              <div class="question">
                "${escapedQuery}"
              </div>

              <div class="grid">
                <div class="card">
                  <div class="label">
                    Analysis type
                  </div>
                  <div class="value">
                    ${escapedType}
                  </div>
                </div>

                <div class="card">
                  <div class="label">
                    Observations
                  </div>
                  <div class="value">
                    ${item.observationsUsed.length}
                    DATASET(S)
                  </div>
                </div>
              </div>
            </section>

            <section class="section">
              <div class="section-title">
                <span>Confidence</span>
                <span>${confidence}%</span>
              </div>

              <div class="confidence">
                <div class="bar">
                  <div class="fill"></div>
                </div>
              </div>
            </section>

            <section class="section">
              <div class="section-title">
                <span>Input observations</span>
                <span>${item.observationsUsed.length}</span>
              </div>

              <div style="margin-top: 8px">
                ${observationRows}
              </div>
            </section>

            <section class="section">
              <div class="section-title">
                <span>Execution workflow</span>
                <span>OBSERVABLE TRACE</span>
              </div>

              <div class="timeline">
                ${REPLAY_STEPS.map(
      (step, index) => `
                    <div class="step">
                      <div class="dot"></div>
                      <div>
                        <div class="step-title">
                          0${index + 1}
                          &nbsp;
                          ${escapeHtml(
        step.label
      )}
                        </div>
                        <div class="step-description">
                          ${escapeHtml(
        step.description
      )}
                        </div>
                      </div>
                    </div>
                  `
    ).join('')}
              </div>
            </section>

            <div class="footer">
              <span>
                SATQUERY AI · AUDITABLE EARTH OBSERVATION
              </span>

              <span>
                GENERATED ${new Date().toISOString()}
              </span>
            </div>

            <div
              class="no-print"
              style="
                margin-top:24px;
                padding:12px;
                background:#f2ece2;
                font-family:monospace;
                font-size:10px;
              "
            >
              Use your browser's Print dialog and choose
              "Save as PDF" to create the final PDF.
            </div>

          </main>
        </body>
      </html>
    `);

    reportWindow.document.close();

    reportWindow.focus();

    window.setTimeout(() => {
      reportWindow.print();
    }, 350);

    setShowExportMenu(null);
  };

  /* ================================================================
     RENDER
  ================================================================= */

  return (
    <div
      className="
        mx-auto
        max-w-7xl
        space-y-6
        p-4
        font-sans
        sm:p-6
        md:p-8
      "
    >
      {/* ============================================================
          HEADER
      ============================================================= */}

      <div
        className="
          flex
          flex-col
          gap-4
          border-b border-sat-border
          pb-5
          lg:flex-row
          lg:items-end
          lg:justify-between
        "
      >
        <div>
          <div className="flex items-center gap-2">
            <div
              className="
                flex
                h-9 w-9
                items-center
                justify-center
                rounded-md
                border border-sat-accent/30
                bg-sat-accent/10
                text-sat-accent
              "
            >
              <History className="h-4 w-4" />
            </div>

            <div>
              <div
                className="
                  flex
                  items-center
                  gap-2
                  font-mono
                "
              >
                <h1
                  className="
                    text-2xl
                    font-bold
                    uppercase
                    tracking-wider
                    text-sat-text
                  "
                >
                  Analysis Audit History
                </h1>

                <span
                  className="
                    rounded-full
                    border border-sat-stable/30
                    bg-sat-stable/10
                    px-2.5
                    py-0.5
                    text-xs
                    font-bold
                    text-sat-stable
                  "
                >
                  ARCHIVE
                </span>
              </div>

              <p
                className="
                  mt-1
                  font-mono
                  text-xs
                  uppercase
                  tracking-wider
                  text-sat-dim
                "
              >
                VERIFIED GEOSPATIAL ANALYSIS
                LOGS · TELEMETRY · REPORTS
              </p>
            </div>
          </div>
        </div>

        {/* Search */}
        <div className="flex w-full gap-2 sm:w-auto">
          <div className="relative w-full sm:w-80">
            <Search
              className="
                absolute
                left-3
                top-1/2
                h-4
                w-4
                -translate-y-1/2
                text-sat-dim
              "
            />

            <input
              type="text"
              value={searchTerm}
              onChange={(event) =>
                setSearchTerm(
                  event.target.value
                )
              }
              placeholder="Search queries, models, files..."
              aria-label="Search analysis history"
              className="
                w-full
                rounded-lg
                border border-sat-border
                bg-sat-surface
                py-2.5
                pl-10
                pr-4
                font-sans
                text-sm
                text-sat-text
                outline-none
                placeholder:text-sat-dim
                focus:border-sat-accent
                focus:ring-1
                focus:ring-sat-accent/20
              "
            />
          </div>

          <button
            type="button"
            onClick={() =>
              setSortNewestFirst(
                (current) => !current
              )
            }
            title={
              sortNewestFirst
                ? 'Showing newest first'
                : 'Showing oldest first'
            }
            className="
              flex
              shrink-0
              items-center
              justify-center
              rounded-lg
              border border-sat-border
              bg-sat-surface
              px-4
              font-mono
              text-xs
              font-bold
              text-sat-dim
              transition-colors
              hover:border-sat-accent
              hover:text-sat-accent
            "
          >
            {sortNewestFirst
              ? 'NEWEST'
              : 'OLDEST'}
          </button>
        </div>
      </div>

      {/* ============================================================
          METRICS
      ============================================================= */}

      <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
        <MetricCard
          icon={
            <History className="h-3.5 w-3.5" />
          }
          label="TOTAL ANALYSES"
          value={String(
            historyItems.length
          )}
        />

        <MetricCard
          icon={
            <BarChart3 className="h-3.5 w-3.5" />
          }
          label="AVG CONFIDENCE"
          value={`${averageConfidence}%`}
          accent="stable"
        />

        <MetricCard
          icon={
            <Sparkles className="h-3.5 w-3.5" />
          }
          label="ANALYSIS TYPES"
          value={String(
            uniqueAnalysisTypes
          )}
          accent="accent"
        />

        <MetricCard
          icon={
            <ShieldCheck className="h-3.5 w-3.5" />
          }
          label="VERIFIED"
          value={`${verifiedCount}/${historyItems.length || 0}`}
          accent="stable"
        />
      </div>

      {/* ============================================================
          TABLE
      ============================================================= */}

      <div
        className="
          overflow-hidden
          rounded-lg
          border border-sat-border
          bg-sat-surface
          shadow-xl
        "
      >
        {/* Table header */}
        <div
          className="
            flex
            flex-col
            gap-2
            border-b border-sat-border
            bg-sat-panel/60
            px-4
            py-3
            sm:flex-row
            sm:items-center
            sm:justify-between
          "
        >
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4 text-sat-accent" />

            <span className="font-mono text-sm font-bold uppercase tracking-wider text-sat-text">
              Execution Archive
            </span>
          </div>

          <span className="font-mono text-xs text-sat-dim">
            {filteredItems.length} OF{' '}
            {historyItems.length} RECORDS
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[980px] border-collapse text-left">
            <thead>
              <tr
                className="
                  border-b border-sat-border
                  bg-sat-bg
                  font-mono
                  text-xs
                  uppercase
                  tracking-wider
                  text-sat-dim
                "
              >
                <th className="px-4 py-3.5 font-bold">
                  TIMESTAMP
                </th>

                <th className="px-4 py-3.5 font-bold">
                  QUESTION / QUERY
                </th>

                <th className="px-4 py-3.5 font-bold">
                  ANALYSIS
                </th>

                <th className="px-4 py-3.5 font-bold">
                  INPUT DATA
                </th>

                <th className="px-4 py-3.5 text-center font-bold">
                  CONFIDENCE
                </th>

                <th className="px-4 py-3.5 text-center font-bold">
                  STATUS
                </th>

                <th className="px-4 py-3.5 text-right font-bold">
                  ACTIONS
                </th>
              </tr>
            </thead>

            <tbody className="divide-y divide-sat-border/60">
              {filteredItems.length === 0 ? (
                <tr>
                  <td
                    colSpan={7}
                    className="p-12 text-center"
                  >
                    <div className="mx-auto max-w-sm">
                      <Search className="mx-auto h-6 w-6 text-sat-dim" />

                      <div className="mt-3 font-mono text-sm font-bold uppercase tracking-wider text-sat-text">
                        NO ANALYSIS HISTORY FOUND
                      </div>

                      <div className="mt-1 font-sans text-sm text-sat-dim">
                        Try a different query,
                        analysis type or
                        observation name.
                      </div>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredItems.map((item) => {
                  const confidence =
                    Math.max(
                      0,
                      Math.min(
                        100,
                        item.confidence
                      )
                    );

                  return (
                    <tr
                      key={item.id}
                      onClick={() =>
                        openItem(item)
                      }
                      className="
                        group
                        cursor-pointer
                        transition-colors
                        hover:bg-sat-panel/60
                      "
                    >
                      <td className="whitespace-nowrap px-4 py-4 font-mono text-xs text-sat-dim">
                        {item.timestamp}
                      </td>

                      <td className="max-w-[320px] px-4 py-4">
                        <div className="truncate font-sans text-sm font-medium text-sat-text transition-colors group-hover:text-sat-accent">
                          "{item.queryText}"
                        </div>
                      </td>

                      <td className="px-4 py-4">
                        <span
                          className="
                            rounded-md
                            border border-sat-accent/20
                            bg-sat-accent/5
                            px-2.5
                            py-1
                            font-mono
                            text-xs
                            font-bold
                            text-sat-accent
                          "
                        >
                          {item.analysisType}
                        </span>
                      </td>

                      <td className="max-w-[240px] px-4 py-4">
                        <div className="flex items-center gap-1.5">
                          <span className="font-mono text-xs font-bold text-sat-dim">
                            [{item.observationsUsed.length}]
                          </span>

                          <span className="truncate font-mono text-xs text-sat-muted">
                            {item.observationsUsed.join(
                              ', '
                            )}
                          </span>
                        </div>
                      </td>

                      <td className="px-4 py-4">
                        <div className="mx-auto w-24">
                          <div className="flex items-center justify-between font-mono text-xs">
                            <span className="font-bold text-sat-stable">
                              {confidence}%
                            </span>
                          </div>

                          <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-sat-panel">
                            <div
                              className="h-full rounded-full bg-sat-stable transition-all"
                              style={{
                                width: `${confidence}%`,
                              }}
                            />
                          </div>
                        </div>
                      </td>

                      <td className="px-4 py-4 text-center">
                        <span
                          className="
                            inline-flex
                            items-center
                            gap-1.5
                            rounded-md
                            border border-sat-stable/20
                            bg-sat-stable/5
                            px-2.5
                            py-1
                            font-mono
                            text-xs
                            font-bold
                            uppercase
                            text-sat-stable
                          "
                        >
                          <CheckCircle2 className="h-3.5 w-3.5" />
                          {item.status}
                        </span>
                      </td>

                      <td className="px-4 py-4">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            type="button"
                            onClick={(event) => {
                              event.stopPropagation();
                              exportIntelligenceBrief(item);
                            }}
                            title="Download PDF Brief"
                            className="
                              flex
                              h-8
                              items-center
                              gap-1.5
                              rounded-md
                              border border-amber-500/40
                              bg-amber-500/10
                              px-3
                              font-mono
                              text-xs
                              font-bold
                              text-amber-400
                              transition-colors
                              hover:bg-amber-500/20
                            "
                          >
                            <FileText className="h-3.5 w-3.5" />
                            PDF BRIEF
                          </button>

                          <button
                            type="button"
                            onClick={(event) => {
                              event.stopPropagation();
                              openReplay(item);
                            }}
                            title="Replay analysis"
                            className="
                              flex
                              h-8
                              items-center
                              gap-1.5
                              rounded-md
                              border border-sat-border
                              bg-sat-panel
                              px-3
                              font-mono
                              text-xs
                              font-bold
                              text-sat-muted
                              transition-colors
                              hover:border-sat-accent
                              hover:text-sat-accent
                            "
                          >
                            <Play className="h-3 w-3 fill-current" />
                            REPLAY
                          </button>

                          <div className="relative">
                            <button
                              type="button"
                              onClick={(event) => {
                                event.stopPropagation();

                                setShowExportMenu(
                                  showExportMenu ===
                                    item.id
                                    ? null
                                    : item.id
                                );
                              }}
                              title="Export intelligence brief"
                              className="
                                flex
                                h-8
                                items-center
                                gap-1.5
                                rounded-md
                                border border-sat-accent/30
                                bg-sat-accent/5
                                px-3
                                font-mono
                                text-xs
                                font-bold
                                text-sat-accent
                                transition-colors
                                hover:bg-sat-accent/10
                              "
                            >
                              <Download className="h-3.5 w-3.5" />
                              EXPORT
                            </button>

                            {showExportMenu ===
                              item.id && (
                                <div
                                  className="
                                  absolute
                                  right-0
                                  top-8
                                  z-50
                                  w-48
                                  overflow-hidden
                                  rounded-md
                                  border border-sat-border
                                  bg-sat-surface
                                  shadow-2xl
                                "
                                  onClick={(event) =>
                                    event.stopPropagation()
                                  }
                                >
                                  <button
                                    type="button"
                                    onClick={() =>
                                      exportIntelligenceBrief(
                                        item
                                      )
                                    }
                                    className="
                                    flex
                                    w-full
                                    items-center
                                    gap-2
                                    px-3
                                    py-2.5
                                    text-left
                                    transition-colors
                                    hover:bg-sat-panel
                                  "
                                  >
                                    <FileText className="h-3.5 w-3.5 text-sat-change" />

                                    <span>
                                      <span className="block font-mono text-[8px] font-bold text-sat-text">
                                        INTELLIGENCE BRIEF
                                      </span>

                                      <span className="block font-sans text-[8px] text-sat-dim">
                                        Print / Save as PDF
                                      </span>
                                    </span>
                                  </button>

                                  <button
                                    type="button"
                                    onClick={() =>
                                      exportGeoJSON(
                                        item
                                      )
                                    }
                                    className="
                                    flex
                                    w-full
                                    items-center
                                    gap-2
                                    border-t border-sat-border
                                    px-3
                                    py-2.5
                                    text-left
                                    transition-colors
                                    hover:bg-sat-panel
                                  "
                                  >
                                    <FileJson className="h-3.5 w-3.5 text-sat-accent" />

                                    <span>
                                      <span className="block font-mono text-[8px] font-bold text-sat-text">
                                        GEOJSON ARCHIVE
                                      </span>

                                      <span className="block font-sans text-[8px] text-sat-dim">
                                        Export GIS metadata
                                      </span>
                                    </span>
                                  </button>
                                </div>
                              )}
                          </div>

                          <button
                            type="button"
                            onClick={(event) => {
                              event.stopPropagation();
                              openItem(item);
                            }}
                            title="Open analysis"
                            className="
                              flex
                              h-7
                              w-7
                              items-center
                              justify-center
                              rounded
                              border border-sat-border
                              bg-sat-panel
                              text-sat-dim
                              transition-colors
                              hover:border-sat-accent
                              hover:text-sat-accent
                            "
                          >
                            <ArrowUpRight className="h-3 w-3" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* ============================================================
          REPLAY MODAL
      ============================================================= */}

      {isReplayOpen &&
        selectedItem && (
          <ReplayModal
            item={selectedItem}
            currentStep={replayStep}
            onStepChange={setReplayStep}
            onClose={closeReplay}
            onOpenResult={() =>
              openItem(selectedItem)
            }
          />
        )}
    </div>
  );
};

/* ================================================================
   METRIC CARD
================================================================ */

interface MetricCardProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  accent?: 'accent' | 'stable';
}

const MetricCard: React.FC<
  MetricCardProps
> = ({
  icon,
  label,
  value,
  accent = 'accent',
}) => {
    return (
      <div
        className="
        rounded-lg
        border border-sat-border
        bg-sat-surface
        p-4
        shadow-sm
      "
      >
        <div className="flex items-center justify-between">
          <div
            className={`
            ${accent === 'stable'
                ? 'text-sat-stable'
                : 'text-sat-accent'
              }
          `}
          >
            {icon}
          </div>

          <span className="font-mono text-xs uppercase tracking-wider text-sat-dim">
            TELEMETRY
          </span>
        </div>

        <div className="mt-3 font-mono text-2xl font-bold text-sat-text">
          {value}
        </div>

        <div className="mt-1 font-mono text-xs font-bold uppercase tracking-wider text-sat-dim">
          {label}
        </div>
      </div>
    );
  };

/* ================================================================
   REPLAY MODAL
================================================================ */

interface ReplayModalProps {
  item: QueryHistoryItem;
  currentStep: number;
  onStepChange: (step: number) => void;
  onClose: () => void;
  onOpenResult: () => void;
}

const ReplayModal: React.FC<
  ReplayModalProps
> = ({
  item,
  currentStep,
  onStepChange,
  onClose,
  onOpenResult,
}) => {
    const step =
      REPLAY_STEPS[currentStep];

    const progress =
      ((currentStep + 1) /
        REPLAY_STEPS.length) *
      100;

    const canGoBack =
      currentStep > 0;

    const canGoForward =
      currentStep <
      REPLAY_STEPS.length - 1;

    return (
      <div
        className="
        fixed
        inset-0
        z-[100]
        flex
        items-center
        justify-center
        bg-black/70
        p-4
        backdrop-blur-sm
      "
        role="dialog"
        aria-modal="true"
        aria-label="Analysis replay"
      >
        <div
          className="
          flex
          max-h-[90vh]
          w-full
          max-w-3xl
          flex-col
          overflow-hidden
          rounded-lg
          border border-sat-borderLight
          bg-sat-surface
          shadow-2xl
        "
        >
          {/* Modal header */}
          <div
            className="
            flex
            items-start
            justify-between
            gap-4
            border-b border-sat-border
            bg-sat-panel/50
            p-4
          "
          >
            <div className="flex min-w-0 items-start gap-3">
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
                <RotateCcw className="h-4 w-4" />
              </div>

              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <h2 className="font-display text-sm font-bold uppercase tracking-wider text-sat-text">
                    Analysis Replay
                  </h2>

                  <span className="rounded border border-sat-stable/20 bg-sat-stable/5 px-1.5 py-0.5 font-mono text-[6px] font-bold text-sat-stable">
                    AUDIT VIEW
                  </span>
                </div>

                <p className="mt-1 truncate font-sans text-[10px] text-sat-muted">
                  "{item.queryText}"
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={onClose}
              className="
              flex
              h-7
              w-7
              shrink-0
              items-center
              justify-center
              rounded
              border border-sat-border
              text-sat-dim
              transition-colors
              hover:border-sat-accent
              hover:text-sat-accent
            "
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>

          {/* Progress */}
          <div className="border-b border-sat-border bg-sat-bg px-4 py-3">
            <div className="flex items-center justify-between font-mono text-[7px]">
              <span className="font-bold uppercase tracking-wider text-sat-dim">
                EXECUTION TIMELINE
              </span>

              <span className="text-sat-accent">
                STEP {currentStep + 1} /{' '}
                {REPLAY_STEPS.length}
              </span>
            </div>

            <div className="relative mt-4">
              <div className="absolute left-0 right-0 top-1/2 h-px bg-sat-border" />

              <div
                className="
                absolute
                left-0
                top-1/2
                h-px
                bg-sat-accent
                transition-all
              "
                style={{
                  width: `${Math.max(
                    0,
                    progress
                  )}%`,
                }}
              />

              <div className="relative flex justify-between">
                {REPLAY_STEPS.map(
                  (timelineStep, index) => {
                    const isDone =
                      index <= currentStep;

                    const isCurrent =
                      index === currentStep;

                    return (
                      <button
                        key={
                          timelineStep.shortLabel
                        }
                        type="button"
                        onClick={() =>
                          onStepChange(index)
                        }
                        title={
                          timelineStep.label
                        }
                        className="group flex flex-col items-center"
                      >
                        <span
                          className={`
                          flex
                          h-4
                          w-4
                          items-center
                          justify-center
                          rounded-full
                          border
                          transition-all
                          ${isCurrent
                              ? 'scale-125 border-sat-accent bg-sat-accent text-slate-950'
                              : isDone
                                ? 'border-sat-accent bg-sat-accent/20 text-sat-accent'
                                : 'border-sat-border bg-sat-surface text-sat-dim'
                            }
                        `}
                        >
                          {isDone ? (
                            <Check className="h-2.5 w-2.5" />
                          ) : (
                            <span className="font-mono text-[5px]">
                              {index + 1}
                            </span>
                          )}
                        </span>

                        <span
                          className={`
                          mt-2
                          hidden
                          font-mono
                          text-[5px]
                          font-bold
                          uppercase
                          tracking-wider
                          sm:block
                          ${isCurrent
                              ? 'text-sat-accent'
                              : 'text-sat-dim'
                            }
                        `}
                        >
                          {
                            timelineStep.shortLabel
                          }
                        </span>
                      </button>
                    );
                  }
                )}
              </div>
            </div>
          </div>

          {/* Main replay content */}
          <div className="min-h-0 flex-1 overflow-y-auto p-4 sm:p-5">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              {/* Current step */}
              <div
                className="
                md:col-span-2
                rounded-lg
                border border-sat-accent/20
                bg-sat-bg
                p-5
              "
              >
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[8px] font-bold text-sat-accent">
                    0{currentStep + 1}
                  </span>

                  <span className="font-mono text-[8px] uppercase tracking-wider text-sat-dim">
                    OBSERVABLE EXECUTION STEP
                  </span>
                </div>

                <h3 className="mt-3 font-display text-lg font-bold text-sat-text">
                  {step.label}
                </h3>

                <p className="mt-2 max-w-xl font-sans text-xs leading-relaxed text-sat-muted">
                  {step.description}
                </p>

                <div
                  className="
                  mt-5
                  rounded-md
                  border border-sat-border
                  bg-sat-surface
                  p-3
                "
                >
                  <div className="font-mono text-[7px] font-bold uppercase tracking-wider text-sat-dim">
                    ARCHIVED ANALYSIS
                  </div>

                  <div className="mt-2 font-mono text-[9px] font-semibold text-sat-accent">
                    {item.analysisType}
                  </div>

                  <div className="mt-3 grid grid-cols-2 gap-2">
                    <ReplayData
                      label="CONFIDENCE"
                      value={`${item.confidence}%`}
                    />

                    <ReplayData
                      label="OBSERVATIONS"
                      value={String(
                        item.observationsUsed
                          .length
                      )}
                    />

                    <ReplayData
                      label="STATUS"
                      value={item.status}
                    />

                    <ReplayData
                      label="TIMESTAMP"
                      value={item.timestamp}
                    />
                  </div>
                </div>
              </div>

              {/* Step list */}
              <div
                className="
                rounded-lg
                border border-sat-border
                bg-sat-bg
                p-3
              "
              >
                <div className="font-mono text-xs font-bold uppercase tracking-wider text-sat-dim">
                  EXECUTION PATH
                </div>

                <div className="mt-3 space-y-1">
                  {REPLAY_STEPS.map(
                    (timelineStep, index) => {
                      const active =
                        index === currentStep;

                      const complete =
                        index < currentStep;

                      return (
                        <button
                          key={
                            timelineStep.shortLabel
                          }
                          type="button"
                          onClick={() =>
                            onStepChange(
                              index
                            )
                          }
                          className={`
                          flex
                          w-full
                          items-center
                          gap-2.5
                          rounded-md
                          px-3
                          py-2.5
                          text-left
                          transition-colors
                          ${active
                              ? 'bg-sat-accent/10 text-sat-accent font-bold'
                              : 'text-sat-dim hover:bg-sat-panel hover:text-sat-text'
                            }
                        `}
                        >
                          <span
                            className={`
                            flex
                            h-5
                            w-5
                            shrink-0
                            items-center
                            justify-center
                            rounded-full
                            border
                            font-mono
                            text-xs
                            ${complete ||
                                active
                                ? 'border-sat-accent bg-sat-accent/15 text-sat-accent'
                                : 'border-sat-border'
                              }
                          `}
                          >
                            {complete ? (
                              <Check className="h-3 w-3" />
                            ) : (
                              index + 1
                            )}
                          </span>

                          <span className="truncate font-mono text-xs font-bold uppercase">
                            {
                              timelineStep.label
                            }
                          </span>
                        </button>
                      );
                    }
                  )}
                </div>
              </div>
            </div>

            {/* Observation archive */}
            <div
              className="
              mt-4
              rounded-lg
              border border-sat-border
              bg-sat-bg
              p-4
            "
            >
              <div className="font-mono text-xs font-bold uppercase tracking-wider text-sat-dim">
                INPUT DATASETS
              </div>

              <div className="mt-2 flex flex-wrap gap-2">
                {item.observationsUsed.map(
                  (observation, index) => (
                    <span
                      key={`${observation}-${index}`}
                      className="
                      rounded-md
                      border border-sat-border
                      bg-sat-surface
                      px-2.5
                      py-1.5
                      font-mono
                      text-xs
                      text-sat-muted
                    "
                    >
                      {observation}
                    </span>
                  )
                )}
              </div>
            </div>
          </div>

          {/* Footer controls */}
          <div
            className="
            flex
            flex-col
            gap-2
            border-t border-sat-border
            bg-sat-panel/40
            p-4
            sm:flex-row
            sm:items-center
            sm:justify-between
          "
          >
            <div className="font-mono text-xs text-sat-dim">
              STEP {currentStep + 1}:{' '}
              {step.shortLabel}
            </div>

            <div className="flex items-center justify-end gap-2">
              <button
                type="button"
                disabled={!canGoBack}
                onClick={() =>
                  onStepChange(
                    currentStep - 1
                  )
                }
                className="
                flex
                items-center
                gap-1.5
                rounded-md
                border border-sat-border
                bg-sat-surface
                px-4
                py-2
                font-mono
                text-xs
                font-bold
                text-sat-muted
                transition-colors
                hover:border-sat-accent
                hover:text-sat-accent
                disabled:cursor-not-allowed
                disabled:opacity-30
              "
              >
                <ChevronLeft className="h-4 w-4" />
                PREVIOUS
              </button>

              {canGoForward ? (
                <button
                  type="button"
                  onClick={() =>
                    onStepChange(
                      currentStep + 1
                    )
                  }
                  className="
                  flex
                  items-center
                  gap-1.5
                  rounded-md
                  bg-sat-accent
                  px-4
                  py-2
                  font-mono
                  text-xs
                  font-bold
                  text-slate-950
                  transition-colors
                  hover:bg-sky-300
                "
                >
                  NEXT
                  <ChevronRight className="h-4 w-4" />
                </button>
              ) : (
                <button
                  type="button"
                  onClick={onOpenResult}
                  className="
                  flex
                  items-center
                  gap-1.5
                  rounded-md
                  bg-sat-accent
                  px-4
                  py-2
                  font-mono
                  text-xs
                  font-bold
                  text-slate-950
                  transition-colors
                  hover:bg-sky-300
                "
                >
                  OPEN RESULT
                  <ArrowUpRight className="h-4 w-4" />
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  };

/* ================================================================
   REPLAY DATA
================================================================ */

interface ReplayDataProps {
  label: string;
  value: string;
}

const ReplayData: React.FC<
  ReplayDataProps
> = ({ label, value }) => {
  return (
    <div
      className="
        min-w-0
        rounded-md
        border border-sat-border
        bg-sat-bg
        p-2.5
      "
    >
      <div className="font-mono text-xs uppercase tracking-wider text-sat-dim">
        {label}
      </div>

      <div
        className="
          mt-1
          truncate
          font-mono
          text-xs
          font-bold
          text-sat-text
        "
        title={value}
      >
        {value}
      </div>
    </div>
  );
};

/* ================================================================
   FILE DOWNLOAD HELPER
================================================================ */

const downloadFile = (
  content: string,
  filename: string,
  mimeType: string
) => {
  const blob = new Blob(
    [content],
    { type: mimeType }
  );

  const url =
    URL.createObjectURL(blob);

  const anchor =
    document.createElement('a');

  anchor.href = url;
  anchor.download = filename;

  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();

  URL.revokeObjectURL(url);
};

/* ================================================================
   HTML ESCAPE
================================================================ */

const escapeHtml = (
  value: string
): string => {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
};

export default HistoryView;
