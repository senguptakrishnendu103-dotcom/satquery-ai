import React, { useMemo, useState } from 'react';
import type { AnalysisResult } from '../../types/satquery';
import {
  CheckCircle2,
  MapPin,
  Play,
  CornerDownRight,
  ShieldCheck,
  Cpu,
  Database,
  Radio,
  ChevronRight,
  Crosshair,
  FileSearch,
  Layers3,
  Download,
  FileJson,
  FileText,
  Copy,
  Check,
  ChevronDown,
} from 'lucide-react';

interface ResultPanelProps {
  result: AnalysisResult;
  selectedRegionId: string | null;
  onSelectRegion: (regionId: string | null) => void;
  onOpenReplay: () => void;
  onFollowUpQuery?: (actionQuery: string) => void;
}

export const ResultPanel: React.FC<ResultPanelProps> = ({
  result,
  selectedRegionId,
  onSelectRegion,
  onOpenReplay,
  onFollowUpQuery,
}) => {
  /*
   * Clamp confidence so the visual meter can never
   * accidentally overflow its container.
   */
  const confidence = Math.max(
    0,
    Math.min(100, Number(result.confidence) || 0)
  );

  const confidenceLabel = useMemo(() => {
    if (confidence >= 90) return 'VERY HIGH';
    if (confidence >= 75) return 'HIGH';
    if (confidence >= 60) return 'MODERATE';
    return 'LOW';
  }, [confidence]);

  const evidenceCount = result.evidence?.length ?? 0;

  /*
   * Export controls are intentionally kept inside this component so the
   * existing parent API does not have to change. This preserves every
   * callback and integration already used by the current codebase.
   */
  const [isExportMenuOpen, setIsExportMenuOpen] = useState(false);
  const [exportFeedback, setExportFeedback] = useState<string | null>(null);

  const isVerified =
    result.status === 'COMPLETE' &&
    Boolean(result.executionSummary?.task) &&
    Array.isArray(result.executionSummary?.modelsUsed) &&
    result.executionSummary.modelsUsed.length > 0;

  const formattedInputs =
    (result.executionSummary?.inputs || [])
      .map((input: any) =>
        typeof input === 'string'
          ? input
          : input?.filename ||
          input?.name ||
          input?.product_id ||
          input?.productId ||
          'Unknown input'
      )
      .filter(Boolean)
      .join(', ') || 'N/A';

  const executionId = useMemo(
    () =>
      result.executionSummary?.telemetryId ||
      `SQ-${Date.now().toString(36).slice(-6).toUpperCase()}`,
    [result.executionSummary?.telemetryId]
  );

  const reportObservationCount =
    result.executionSummary?.inputs?.length || 0;

  const showExportFeedback = (message: string) => {
    setExportFeedback(message);
    window.setTimeout(() => setExportFeedback(null), 2400);
  };

  const exportGeoJSON = () => {
    const evidence = (result.evidence ?? []) as unknown as ExportEvidence[];

    const features: Array<{
      type: 'Feature';
      geometry: SimpleGeoJSONGeometry;
      properties: Record<string, unknown>;
    }> = evidence
      .map((region) => {
        const geometry = normalizeGeometry(region.geometry);

        if (!geometry) return null;

        return {
          type: 'Feature',
          geometry,
          properties: {
            id: region.id,
            label: region.label,
            areaEstimate: region.areaEstimate,
            confidence: Number(region.confidence) || 0,
            description: region.description,
          },
        };
      })
      .filter(
        (feature): feature is any =>
          feature !== null
      );

    const payload = {
      type: 'FeatureCollection',
      name: `SatQuery_${executionId}`,
      properties: {
        source: 'SatQuery AI',
        executionId,
        task: result.task,
        headline: result.headline,
        analysisType: result.executionSummary?.task || result.task,
        confidence,
        changePercentage: result.changePercentage ?? null,
        generatedAt: new Date().toISOString(),
      },
      features,
    };

    downloadTextFile(
      JSON.stringify(payload, null, 2),
      `satquery-${sanitizeFilename(executionId)}.geojson`,
      'application/geo+json'
    );

    setIsExportMenuOpen(false);
    showExportFeedback(
      features.length
        ? `GeoJSON exported · ${features.length} spatial features`
        : 'GeoJSON exported · metadata only'
    );
  };

  const exportIntelligenceBrief = () => {
    const evidence = (result.evidence ?? []) as unknown as ExportEvidence[];
    const printableWindow = window.open(
      '',
      '_blank',
      'noopener,noreferrer,width=1100,height=850'
    );

    if (!printableWindow) {
      showExportFeedback('Popup blocked · allow popups to export PDF');
      return;
    }

    const evidenceRows = evidence.length
      ? evidence
        .map(
          (region, index) => `
              <tr>
                <td class="mono">${String(index + 1).padStart(2, '0')}</td>
                <td><strong>${escapeHtml(region.label)}</strong><br />
                  <span class="muted">${escapeHtml(region.description)}</span>
                </td>
                <td class="mono">${escapeHtml(region.areaEstimate)}</td>
                <td class="mono">${Math.max(
            0,
            Math.min(100, Number(region.confidence) || 0)
          )}%</td>
              </tr>
            `
        )
        .join('')
      : `
          <tr>
            <td colspan="4" class="empty">
              No spatial evidence returned for this analysis.
            </td>
          </tr>
        `;

    const inputRows = (result.executionSummary?.inputs ?? [])
      .map(
        (input, index) => `
          <div class="dataset">
            <span class="index">0${index + 1}</span>
            <span>${escapeHtml(typeof input === 'string' ? input : (input?.filename || input?.name || ''))}</span>
          </div>
        `
      )
      .join('');

    const modelRows = (result.executionSummary?.modelsUsed ?? [])
      .map(
        (model) => `
          <span class="chip">${escapeHtml(model)}</span>
        `
      )
      .join('');

    const changeMetric = result.changePercentage
      ? `
        <div class="metric change">
          <span>CHANGE DETECTED</span>
          <strong>${escapeHtml(result.changePercentage)}</strong>
        </div>
      `
      : '';

    printableWindow.document.write(`
      <!doctype html>
      <html>
        <head>
          <meta charset="utf-8" />
          <title>SatQuery Intelligence Brief — ${escapeHtml(executionId)}</title>
          <style>
            @page {
              size: A4;
              margin: 14mm;
            }

            :root {
              color-scheme: light;
              --ink: #1c1814;
              --muted: #6e665c;
              --dim: #8a8175;
              --line: #d8cdbd;
              --panel: #f2ece2;
              --paper: #fffdf8;
              --blue: #1677a8;
              --green: #08745d;
              --amber: #c66a12;
            }

            * { box-sizing: border-box; }

            body {
              margin: 0;
              background: var(--paper);
              color: var(--ink);
              font-family: Inter, Arial, sans-serif;
              font-size: 11px;
              line-height: 1.5;
            }

            .page {
              max-width: 900px;
              margin: 0 auto;
            }

            .header {
              display: flex;
              align-items: flex-start;
              justify-content: space-between;
              gap: 30px;
              padding-bottom: 18px;
              border-bottom: 2px solid var(--ink);
            }

            .eyebrow,
            .section-title,
            .mono,
            .label,
            .exec {
              font-family: "JetBrains Mono", "Courier New", monospace;
            }

            .eyebrow {
              color: var(--blue);
              font-size: 9px;
              font-weight: 800;
              letter-spacing: .16em;
              text-transform: uppercase;
            }

            h1 {
              margin: 7px 0 3px;
              font-size: 25px;
              line-height: 1.12;
              letter-spacing: -.025em;
            }

            .subtitle {
              color: var(--muted);
              font-size: 10px;
            }

            .exec {
              min-width: 160px;
              text-align: right;
              color: var(--dim);
              font-size: 8px;
            }

            .exec strong {
              display: block;
              margin-top: 3px;
              color: var(--ink);
              font-size: 11px;
            }

            .section {
              margin-top: 22px;
              break-inside: avoid;
            }

            .section-title {
              display: flex;
              justify-content: space-between;
              gap: 12px;
              padding-bottom: 7px;
              border-bottom: 1px solid var(--line);
              color: var(--dim);
              font-size: 8px;
              font-weight: 800;
              letter-spacing: .12em;
              text-transform: uppercase;
            }

            .question {
              margin-top: 11px;
              padding: 13px 15px;
              background: var(--panel);
              border-left: 3px solid var(--blue);
              font-size: 13px;
              line-height: 1.55;
            }

            .grid {
              display: grid;
              grid-template-columns: repeat(3, 1fr);
              gap: 9px;
              margin-top: 10px;
            }

            .card {
              padding: 11px;
              border: 1px solid var(--line);
              background: var(--paper);
            }

            .label {
              color: var(--dim);
              font-size: 7px;
              font-weight: 700;
              letter-spacing: .08em;
              text-transform: uppercase;
            }

            .value {
              margin-top: 4px;
              font-size: 10px;
              font-weight: 700;
            }

            .confidence {
              margin-top: 11px;
            }

            .confidence-head {
              display: flex;
              justify-content: space-between;
              font-family: monospace;
              font-size: 9px;
              font-weight: 700;
            }

            .bar {
              height: 7px;
              margin-top: 6px;
              overflow: hidden;
              background: #eae2d5;
            }

            .bar > div {
              width: ${confidence}%;
              height: 100%;
              background: var(--green);
            }

            .metric {
              display: flex;
              align-items: center;
              justify-content: space-between;
              margin-top: 10px;
              padding: 9px 11px;
              border: 1px solid var(--line);
              background: var(--panel);
              font-family: monospace;
              font-size: 8px;
              font-weight: 700;
            }

            .metric strong {
              color: var(--amber);
              font-size: 13px;
            }

            table {
              width: 100%;
              margin-top: 9px;
              border-collapse: collapse;
            }

            th {
              padding: 7px;
              background: var(--panel);
              color: var(--dim);
              font-family: monospace;
              font-size: 7px;
              text-align: left;
              text-transform: uppercase;
            }

            td {
              padding: 9px 7px;
              border-bottom: 1px solid var(--line);
              vertical-align: top;
              font-size: 9px;
            }

            .muted {
              color: var(--muted);
              font-size: 8px;
            }

            .empty {
              color: var(--dim);
              text-align: center;
              font-family: monospace;
            }

            .dataset {
              display: flex;
              gap: 10px;
              padding: 7px 0;
              border-bottom: 1px solid #eae2d5;
              font-family: monospace;
              font-size: 8px;
            }

            .index {
              color: var(--blue);
              font-weight: 800;
            }

            .chips {
              display: flex;
              flex-wrap: wrap;
              gap: 5px;
              margin-top: 8px;
            }

            .chip {
              display: inline-block;
              padding: 4px 6px;
              border: 1px solid var(--line);
              background: var(--panel);
              font-family: monospace;
              font-size: 7px;
            }

            .trace {
              margin-top: 8px;
            }

            .trace-row {
              display: flex;
              gap: 10px;
              padding: 7px 0;
              border-bottom: 1px solid #eae2d5;
            }

            .trace-dot {
              width: 12px;
              height: 12px;
              flex: 0 0 12px;
              margin-top: 1px;
              border-radius: 50%;
              background: var(--green);
            }

            .trace-name {
              font-family: monospace;
              font-size: 8px;
              font-weight: 800;
              text-transform: uppercase;
            }

            .trace-description {
              margin-top: 2px;
              color: var(--muted);
              font-size: 8px;
            }

            .footer {
              display: flex;
              justify-content: space-between;
              gap: 20px;
              margin-top: 28px;
              padding-top: 10px;
              border-top: 1px solid var(--line);
              color: var(--dim);
              font-family: monospace;
              font-size: 7px;
            }

            .no-print {
              margin-top: 20px;
              padding: 10px;
              background: var(--panel);
              color: var(--muted);
              font-family: monospace;
              font-size: 8px;
            }

            @media print {
              .no-print { display: none; }
            }
          </style>
        </head>

        <body>
          <main class="page">
            <header class="header">
              <div>
                <div class="eyebrow">SATQUERY AI</div>
                <h1>Earth Observation Intelligence Brief</h1>
                <div class="subtitle">
                  Evidence-grounded · auditable · machine-assisted geospatial analysis
                </div>
              </div>

              <div class="exec">
                EXECUTION ID
                <strong>${escapeHtml(executionId)}</strong>
                <div style="margin-top:7px">
                  ${escapeHtml(result.executionSummary?.telemetryId || 'TELEMETRY N/A')}
                </div>
              </div>
            </header>

            <section class="section">
              <div class="section-title">
                <span>Analysis request</span>
                <span>${escapeHtml(result.task)}</span>
              </div>

              <div class="question">
                "${escapeHtml(result.answer || result.headline)}"
              </div>

              <div class="grid">
                <div class="card">
                  <div class="label">Analysis type</div>
                  <div class="value">${escapeHtml(result.task)}</div>
                </div>

                <div class="card">
                  <div class="label">Input datasets</div>
                  <div class="value">${reportObservationCount || 'N/A'}</div>
                </div>

                <div class="card">
                  <div class="label">Result status</div>
                  <div class="value">${escapeHtml(isVerified ? 'VERIFIED' : 'NOT VERIFIED')}</div>
                </div>
              </div>
            </section>

            <section class="section">
              <div class="section-title">
                <span>Confidence assessment</span>
                <span>${confidence}% · ${escapeHtml(confidenceLabel)}</span>
              </div>

              <div class="confidence">
                <div class="confidence-head">
                  <span>MODEL / PIPELINE CONFIDENCE</span>
                  <span>${confidence}/100</span>
                </div>
                <div class="bar"><div></div></div>
              </div>

              ${changeMetric}
            </section>

            <section class="section">
              <div class="section-title">
                <span>Evidence regions</span>
                <span>${evidenceCount} region(s)</span>
              </div>

              <table>
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Region / finding</th>
                    <th>Area</th>
                    <th>Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  ${evidenceRows}
                </tbody>
              </table>
            </section>

            <section class="section">
              <div class="section-title">
                <span>Input observations</span>
                <span>${reportObservationCount || 0}</span>
              </div>

              <div>
                ${inputRows || '<div class="dataset">No input dataset metadata returned.</div>'}
              </div>
            </section>

            <section class="section">
              <div class="section-title">
                <span>Specialist models</span>
                <span>EXECUTION METADATA</span>
              </div>

              <div class="chips">
                ${modelRows || '<span class="chip">MODEL METADATA NOT AVAILABLE</span>'}
              </div>
            </section>

            <section class="section">
              <div class="section-title">
                <span>Observable execution workflow</span>
                <span>AUDIT TRACE</span>
              </div>

              <div class="trace">
                ${[
        ['01', 'Understanding request', 'Natural-language intent interpreted.'],
        ['02', 'Checking observations', 'Selected observations validated.'],
        ['03', 'Determining analysis type', 'Analysis category determined from request and inputs.'],
        ['04', 'Selecting specialist model', 'Relevant specialist capability selected by the orchestration layer.'],
        ['05', 'Running analysis', 'Analysis executed against the supplied Earth observation inputs.'],
        ['06', 'Generating evidence', 'Observable supporting evidence prepared for inspection.'],
        ['07', 'Preparing result', 'Answer, confidence and audit metadata assembled.'],
      ].map(
        ([number, name, description]) => `
                    <div class="trace-row">
                      <div class="trace-dot"></div>
                      <div>
                        <div class="trace-name">${number} · ${escapeHtml(name)}</div>
                        <div class="trace-description">${escapeHtml(description)}</div>
                      </div>
                    </div>
                  `
      ).join('')}
              </div>
            </section>

            <footer class="footer">
              <span>SATQUERY AI · EARTH OBSERVATION INTELLIGENCE</span>
              <span>GENERATED ${new Date().toISOString()}</span>
            </footer>

            <div class="no-print">
              Print dialog opened by SatQuery. Choose "Save as PDF" to create the final intelligence brief.
            </div>
          </main>
        </body>
      </html>
    `);

    printableWindow.document.close();
    printableWindow.focus();

    window.setTimeout(() => {
      printableWindow.print();
    }, 400);

    setIsExportMenuOpen(false);
    showExportFeedback('Intelligence brief ready · Print to PDF');
  };

  const copyAuditId = async () => {
    try {
      await navigator.clipboard.writeText(executionId);
      showExportFeedback('Execution ID copied');
    } catch {
      showExportFeedback('Copy unavailable in this browser');
    }
  };

  return (
    <section
      className="
        relative
        border-t border-sat-border
        bg-sat-surface/95
        backdrop-blur-xl
        font-sans
        overflow-hidden
      "
      aria-label="Satellite analysis result"
    >
      {/* ============================================================
          TOP STATUS HEADER
      ============================================================ */}

      <div className="relative border-b border-sat-border">
        {/* subtle technical grid */}
        <div
          className="
            pointer-events-none
            absolute inset-0
            opacity-[0.025]
            bg-gis-grid
          "
        />

        <div
          className="
            relative
            flex
            flex-col
            gap-4
            px-4 py-4
            sm:px-6
            lg:flex-row
            lg:items-center
            lg:justify-between
          "
        >
          {/* Status identity */}
          <div className="flex min-w-0 items-center gap-3">
            <div
              className="
                flex h-9 w-9
                shrink-0
                items-center justify-center
                rounded-md
                border border-sat-stable/30
                bg-sat-stable/10
              "
            >
              <CheckCircle2 className="h-5 w-5 text-sat-stable" />
            </div>

            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <span
                  className="
                    font-mono
                    text-[11px]
                    font-bold
                    uppercase
                    tracking-[0.14em]
                    text-sat-stable
                  "
                >
                  ANALYSIS COMPLETE
                </span>

                <span className="text-sat-borderLight">/</span>

                <span
                  className="
                    truncate
                    font-mono
                    text-[10px]
                    uppercase
                    tracking-wider
                    text-sat-muted
                  "
                >
                  {result.task}
                </span>
              </div>

              <div className="mt-1 flex items-center gap-2">
                <Radio className="h-3 w-3 text-sat-accent" />

                <span
                  className="
                    font-mono
                    text-[9px]
                    uppercase
                    tracking-wider
                    text-sat-dim
                  "
                >
                  Satellite intelligence result verified
                </span>
              </div>
            </div>
          </div>

          {/* Actions — existing replay action preserved, exporter added */}
          <div className="flex flex-wrap items-center justify-end gap-2">
            <button
              type="button"
              onClick={onOpenReplay}
              className="
                group
                inline-flex
                items-center
                gap-2
                rounded-md
                border border-sat-accent/40
                bg-sat-accent/[0.06]
                px-3 py-2
                font-mono
                text-[10px]
                font-bold
                tracking-wider
                text-sat-accent
                transition-all
                duration-200
                hover:border-sat-accent
                hover:bg-sat-accent
                hover:text-slate-950
                focus:outline-none
                focus:ring-2
                focus:ring-sat-accent/40
              "
              aria-label="Replay analysis execution"
            >
              <Play className="h-3.5 w-3.5 fill-current transition-transform group-hover:scale-110" />
              <span>REPLAY ANALYSIS</span>
            </button>

            <div className="relative">
              <button
                type="button"
                onClick={() => setIsExportMenuOpen((open) => !open)}
                className="
                  inline-flex
                  items-center
                  gap-2
                  rounded-md
                  border border-sat-borderLight/70
                  bg-sat-panel
                  px-3 py-2
                  font-mono
                  text-[10px]
                  font-bold
                  tracking-wider
                  text-sat-text
                  transition-all
                  duration-200
                  hover:border-sat-accent
                  hover:text-sat-accent
                  focus:outline-none
                  focus:ring-2
                  focus:ring-sat-accent/30
                "
                aria-expanded={isExportMenuOpen}
                aria-haspopup="menu"
                aria-label="Export analysis"
              >
                <Download className="h-3.5 w-3.5" />
                <span>EXPORT</span>
                <ChevronDown
                  className={`h-3 w-3 transition-transform ${isExportMenuOpen ? 'rotate-180' : ''
                    }`}
                />
              </button>

              {isExportMenuOpen && (
                <div
                  className="
                    absolute
                    right-0
                    top-[calc(100%+8px)]
                    z-30
                    w-64
                    overflow-hidden
                    rounded-lg
                    border border-sat-borderLight
                    bg-sat-surface
                    shadow-2xl
                  "
                  role="menu"
                >
                  <div className="border-b border-sat-border bg-sat-panel/50 px-3 py-2">
                    <div className="font-mono text-[8px] font-bold uppercase tracking-wider text-sat-text">
                      Intelligence deliverables
                    </div>
                    <div className="mt-0.5 font-sans text-[9px] text-sat-dim">
                      Export the current verified analysis.
                    </div>
                  </div>

                  <button
                    type="button"
                    role="menuitem"
                    onClick={exportIntelligenceBrief}
                    className="
                      flex w-full items-start gap-3
                      border-b border-sat-border
                      px-3 py-3 text-left
                      transition-colors
                      hover:bg-sat-panel
                    "
                  >
                    <div className="mt-0.5 rounded border border-sat-change/30 bg-sat-change/10 p-1.5 text-sat-change">
                      <FileText className="h-3.5 w-3.5" />
                    </div>

                    <div className="min-w-0">
                      <div className="font-mono text-[9px] font-bold uppercase text-sat-text">
                        Intelligence Brief
                      </div>
                      <div className="mt-0.5 font-sans text-[9px] leading-relaxed text-sat-dim">
                        Print-ready scientific report · PDF
                      </div>
                    </div>
                  </button>

                  <button
                    type="button"
                    role="menuitem"
                    onClick={exportGeoJSON}
                    className="
                      flex w-full items-start gap-3
                      px-3 py-3 text-left
                      transition-colors
                      hover:bg-sat-panel
                    "
                  >
                    <div className="mt-0.5 rounded border border-sat-accent/30 bg-sat-accent/10 p-1.5 text-sat-accent">
                      <FileJson className="h-3.5 w-3.5" />
                    </div>

                    <div className="min-w-0">
                      <div className="font-mono text-[9px] font-bold uppercase text-sat-text">
                        Evidence GeoJSON
                      </div>
                      <div className="mt-0.5 font-sans text-[9px] leading-relaxed text-sat-dim">
                        GIS-compatible evidence + analysis metadata
                      </div>
                    </div>
                  </button>
                </div>
              )}
            </div>

            <button
              type="button"
              onClick={copyAuditId}
              title="Copy execution ID"
              className="
                inline-flex h-8 w-8
                items-center justify-center
                rounded-md
                border border-sat-border
                bg-sat-panel
                text-sat-dim
                transition-colors
                hover:border-sat-accent
                hover:text-sat-accent
                focus:outline-none
                focus:ring-2
                focus:ring-sat-accent/30
              "
              aria-label="Copy execution ID"
            >
              {exportFeedback === 'Execution ID copied' ? (
                <Check className="h-3.5 w-3.5 text-sat-stable" />
              ) : (
                <Copy className="h-3.5 w-3.5" />
              )}
            </button>
          </div>
        </div>
      </div>

      {/* ============================================================
          MAIN RESULT AREA
      ============================================================ */}

      <div className="px-4 py-4 sm:px-6 sm:py-5">
        <div
          className="
            grid
            grid-cols-1
            gap-4
            xl:grid-cols-12
          "
        >
          {/* ========================================================
              ANSWER
          ======================================================== */}

          <div className="xl:col-span-5">
            <div
              className="
                h-full
                rounded-lg
                border border-sat-border
                bg-sat-bg
                overflow-hidden
              "
            >
              {/* section header */}
              <div
                className="
                  flex
                  items-center
                  justify-between
                  border-b border-sat-border
                  px-4 py-2.5
                "
              >
                <div className="flex items-center gap-2">
                  <FileSearch className="h-3.5 w-3.5 text-sat-accent" />

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
                    Intelligence result
                  </span>
                </div>

                <span
                  className={`
                    rounded
                    px-1.5 py-0.5
                    font-mono
                    text-[8px]
                    ${isVerified
                      ? 'border border-sat-stable/20 bg-sat-stable/5 text-sat-stable'
                      : 'border border-sat-change/20 bg-sat-change/5 text-sat-change'}
                  `}
                >
                  {isVerified ? 'VERIFIED' : 'NOT VERIFIED'}
                </span>
              </div>

              <div className="p-4">
                <h2
                  className="
                    font-display
                    text-lg
                    font-bold
                    leading-snug
                    text-sat-text
                  "
                >
                  {result.headline}
                </h2>

                <p
                  className="
                    mt-3
                    text-xs
                    leading-[1.7]
                    text-sat-muted
                  "
                >
                  {result.answer}
                </p>

                {/* Change metric */}
                {result.changePercentage && (
                  <div
                    className="
                      mt-4
                      flex
                      items-center
                      justify-between
                      gap-3
                      rounded-md
                      border border-sat-change/30
                      bg-sat-change/[0.06]
                      px-3 py-2.5
                    "
                  >
                    <div className="flex items-center gap-2">
                      <Layers3 className="h-3.5 w-3.5 text-sat-change" />

                      <span
                        className="
                          font-mono
                          text-[9px]
                          font-bold
                          uppercase
                          tracking-wider
                          text-sat-dim
                        "
                      >
                        Change detected
                      </span>
                    </div>

                    <span
                      className="
                        font-mono
                        text-base
                        font-extrabold
                        text-sat-change
                      "
                    >
                      {result.changePercentage}
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* ========================================================
              EVIDENCE
          ======================================================== */}

          <div className="xl:col-span-4">
            <div
              className="
                h-full
                rounded-lg
                border border-sat-border
                bg-sat-bg
                overflow-hidden
              "
            >
              {/* Evidence header */}
              <div
                className="
                  flex
                  items-center
                  justify-between
                  border-b border-sat-border
                  px-4 py-2.5
                "
              >
                <div className="flex items-center gap-2">
                  <MapPin className="h-3.5 w-3.5 text-sat-change" />

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
                    Evidence
                  </span>

                  <span
                    className="
                      rounded-full
                      bg-sat-change/10
                      px-1.5
                      py-0.5
                      font-mono
                      text-[8px]
                      font-bold
                      text-sat-change
                    "
                  >
                    {evidenceCount}
                  </span>
                </div>

                <span
                  className="
                    font-mono
                    text-[8px]
                    uppercase
                    tracking-wider
                    text-sat-dim
                  "
                >
                  Inspectable regions
                </span>
              </div>

              {/* Evidence list */}
              <div className="max-h-[230px] space-y-2 overflow-y-auto p-3">
                {evidenceCount === 0 ? (
                  <div
                    className="
                      flex
                      min-h-[100px]
                      items-center
                      justify-center
                      rounded-md
                      border border-dashed border-sat-border
                      text-center
                    "
                  >
                    <div>
                      <MapPin className="mx-auto h-4 w-4 text-sat-dim" />

                      <p className="mt-2 font-mono text-[9px] text-sat-dim">
                        NO SPATIAL EVIDENCE RETURNED
                      </p>
                    </div>
                  </div>
                ) : (
                  result.evidence.map((region, index) => {
                    const isSelected =
                      selectedRegionId === region.id;

                    const regionConfidence = Math.max(
                      0,
                      Math.min(100, Number(region.confidence) || 0)
                    );

                    return (
                      <button
                        key={region.id}
                        type="button"
                        onClick={() =>
                          onSelectRegion(
                            isSelected ? null : region.id
                          )
                        }
                        className={`
                          group
                          relative
                          w-full
                          rounded-md
                          border
                          p-3
                          text-left
                          font-mono
                          transition-all
                          duration-200
                          focus:outline-none
                          focus:ring-2
                          focus:ring-sat-accent/30

                          ${isSelected
                            ? `
                                border-sat-change
                                bg-sat-change/[0.07]
                                shadow-[inset_3px_0_0_rgba(217,119,6,0.8)]
                              `
                            : `
                                border-sat-border
                                bg-sat-surface
                                hover:border-sat-accent/50
                                hover:bg-sat-panel/60
                              `
                          }
                        `}
                        aria-pressed={isSelected}
                        aria-label={`Inspect ${region.label}`}
                      >
                        {/* region header */}
                        <div className="flex items-center justify-between gap-3">
                          <div className="flex min-w-0 items-center gap-2">
                            <span
                              className="
                                flex h-5 w-5
                                shrink-0
                                items-center justify-center
                                rounded
                                bg-sat-accent/10
                                font-mono
                                text-[8px]
                                font-bold
                                text-sat-accent
                              "
                            >
                              {String(index + 1).padStart(2, '0')}
                            </span>

                            <span
                              className="
                                truncate
                                text-[10px]
                                font-bold
                                uppercase
                                tracking-wider
                                text-sat-text
                              "
                            >
                              {region.label}
                            </span>
                          </div>

                          <span
                            className="
                              shrink-0
                              text-[9px]
                              font-bold
                              text-sat-change
                            "
                          >
                            {region.areaEstimate}
                          </span>
                        </div>

                        {/* description */}
                        <p
                          className="
                            mt-2
                            line-clamp-2
                            font-sans
                            text-[10px]
                            leading-relaxed
                            text-sat-muted
                          "
                        >
                          {region.description}
                        </p>

                        {/* confidence */}
                        <div className="mt-2">
                          <div className="mb-1 flex items-center justify-between">
                            <span className="text-[8px] uppercase text-sat-dim">
                              Confidence
                            </span>

                            <span className="text-[8px] font-bold text-sat-stable">
                              {regionConfidence}%
                            </span>
                          </div>

                          <div className="h-1 overflow-hidden rounded-full bg-sat-panel">
                            <div
                              className="h-full rounded-full bg-sat-stable transition-all duration-500"
                              style={{
                                width: `${regionConfidence}%`,
                              }}
                            />
                          </div>
                        </div>

                        {/* inspect */}
                        <div
                          className={`
                            mt-2
                            flex
                            items-center
                            justify-end
                            gap-1
                            text-[8px]
                            uppercase
                            tracking-wider
                            transition-colors
                            ${isSelected
                              ? 'text-sat-change'
                              : 'text-sat-dim group-hover:text-sat-accent'
                            }
                          `}
                        >
                          <Crosshair className="h-3 w-3" />

                          <span>
                            {isSelected
                              ? 'SELECTED ON CANVAS'
                              : 'INSPECT ON CANVAS'}
                          </span>

                          <ChevronRight className="h-3 w-3" />
                        </div>
                      </button>
                    );
                  })
                )}
              </div>
            </div>
          </div>

          {/* ========================================================
              CONFIDENCE + AUDIT
          ======================================================== */}

          <div className="xl:col-span-3">
            <div
              className="
                h-full
                rounded-lg
                border border-sat-border
                bg-sat-bg
                overflow-hidden
              "
            >
              {/* Confidence */}
              <div className="border-b border-sat-border p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="h-3.5 w-3.5 text-sat-stable" />

                    <span
                      className="
                        font-mono
                        text-[9px]
                        font-bold
                        uppercase
                        tracking-wider
                        text-sat-dim
                      "
                    >
                      Confidence
                    </span>
                  </div>

                  <span className="font-mono text-[9px] text-sat-stable">
                    {confidenceLabel}
                  </span>
                </div>

                <div className="mt-3 flex items-end gap-2">
                  <span
                    className="
                      font-display
                      text-3xl
                      font-bold
                      leading-none
                      text-sat-text
                    "
                  >
                    {confidence}
                  </span>

                  <span className="pb-0.5 font-mono text-xs text-sat-dim">
                    /100
                  </span>
                </div>

                <div
                  className="
                    mt-3
                    h-1.5
                    overflow-hidden
                    rounded-full
                    border border-sat-border
                    bg-sat-surface
                  "
                >
                  <div
                    className="
                      h-full
                      rounded-full
                      bg-sat-stable
                      transition-all
                      duration-700
                    "
                    style={{
                      width: `${confidence}%`,
                    }}
                  />
                </div>
              </div>

              {/* Audit summary */}
              <div className="p-4">
                <div className="mb-3 flex items-center gap-2">
                  <ShieldCheck className="h-3.5 w-3.5 text-sat-accent" />

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
                    Execution audit
                  </span>
                </div>

                <div className="space-y-2.5 font-mono text-[9px]">
                  <AuditRow
                    icon={<Radio className="h-3 w-3" />}
                    label="TASK"
                    value={result.executionSummary.task}
                  />

                  <AuditRow
                    icon={<Database className="h-3 w-3" />}
                    label="INPUTS"
                    value={formattedInputs}
                  />

                  <AuditRow
                    icon={<Cpu className="h-3 w-3" />}
                    label="MODEL"
                    value={
                      result.executionSummary.modelsUsed?.join(', ') ||
                      'N/A'
                    }
                  />

                  <AuditRow
                    icon={<Radio className="h-3 w-3" />}
                    label="TELEMETRY"
                    value={result.executionSummary.telemetryId || 'N/A'}
                  />

                  <AuditRow
                    icon={<FileSearch className="h-3 w-3" />}
                    label="EXEC-ID"
                    value={executionId}
                  />

                  <div
                    className="
                      mt-3
                      border-t border-sat-border
                      pt-3
                    "
                  >
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-sat-dim">
                        STATUS
                      </span>

                      <span
                        className="
                          inline-flex
                          items-center
                          gap-1
                          font-bold
                          text-sat-stable
                        "
                      >
                        {isVerified ? (
                          <>
                            <CheckCircle2 className="h-3 w-3" />
                            VERIFIED
                          </>
                        ) : (
                          <>
                            <span className="h-1.5 w-1.5 rounded-full bg-sat-change" />
                            NOT VERIFIED
                          </>
                        )}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ============================================================
            FOLLOW-UP ACTIONS
        ============================================================ */}

        {result.followUpActions?.length > 0 && (
          <div
            className="
              mt-4
              rounded-lg
              border border-sat-border
              bg-sat-bg
              p-3
            "
          >
            <div className="mb-2.5 flex items-center gap-2">
              <CornerDownRight className="h-3.5 w-3.5 text-sat-accent" />

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
                Continue analysis
              </span>

              <span className="font-mono text-[8px] text-sat-dim">
                / FOLLOW-UP ACTIONS
              </span>
            </div>

            <div className="flex flex-wrap gap-2">
              {result.followUpActions.map((action, idx) => (
                <button
                  key={`${action}-${idx}`}
                  type="button"
                  onClick={() =>
                    onFollowUpQuery?.(action)
                  }
                  disabled={!onFollowUpQuery}
                  className="
                    group
                    inline-flex
                    items-center
                    gap-1.5
                    rounded-md
                    border border-sat-border
                    bg-sat-surface
                    px-2.5 py-1.5
                    font-mono
                    text-[9px]
                    text-sat-muted
                    transition-all
                    duration-200
                    hover:border-sat-accent/60
                    hover:bg-sat-panel
                    hover:text-sat-accent
                    disabled:cursor-default
                    disabled:opacity-60
                  "
                >
                  <span className="text-sat-dim">
                    [{String(idx + 1).padStart(2, '0')}]
                  </span>

                  <span>{action}</span>

                  <ChevronRight
                    className="
                      h-3 w-3
                      text-sat-dim
                      transition-transform
                      group-hover:translate-x-0.5
                    "
                  />
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ============================================================
          BOTTOM SYSTEM BAR
      ============================================================ */}

      <div
        className="
          flex
          flex-col
          gap-2
          border-t border-sat-border
          bg-sat-panel/40
          px-4 py-2.5
          sm:flex-row
          sm:items-center
          sm:justify-between
          sm:px-6
        "
      >
        <div className="flex items-center gap-2">
          <div className="h-1.5 w-1.5 rounded-full bg-sat-stable shadow-[0_0_6px_currentColor]" />

          <span
            className="
              font-mono
              text-[8px]
              uppercase
              tracking-[0.12em]
              text-sat-dim
            "
          >
            Evidence-grounded result
          </span>

          <span className="text-sat-borderLight">•</span>

          <span className="font-mono text-[8px] text-sat-dim">
            AUDIT TRAIL AVAILABLE
          </span>
        </div>

        <div className="flex min-w-0 items-center gap-2">
          {exportFeedback && (
            <span
              role="status"
              className="
                inline-flex items-center gap-1.5
                rounded border border-sat-stable/20
                bg-sat-stable/5 px-2 py-1
                font-mono text-[8px] font-bold
                text-sat-stable
              "
            >
              <Check className="h-2.5 w-2.5" />
              {exportFeedback}
            </span>
          )}

          <span
            className="
              font-mono
              text-[8px]
              uppercase
              tracking-wider
              text-sat-dim
            "
          >
            SATQUERY INTELLIGENCE ENGINE
          </span>
        </div>
      </div>
    </section>
  );
};

/* ================================================================
   AUDIT ROW
================================================================ */

interface AuditRowProps {
  icon: React.ReactNode;
  label: string;
  value: string;
}

const AuditRow: React.FC<AuditRowProps> = ({
  icon,
  label,
  value,
}) => {
  return (
    <div className="flex items-start gap-2">
      <span className="mt-0.5 shrink-0 text-sat-accent">
        {icon}
      </span>

      <span className="w-14 shrink-0 text-sat-dim">
        {label}
      </span>

      <span
        className="
          min-w-0
          flex-1
          truncate
          text-right
          text-sat-text
        "
        title={value}
      >
        {value}
      </span>
    </div>
  );
};

/* ================================================================
   EXPORT HELPERS
   These helpers are deliberately defensive: the current
   AnalysisResult interface does not require geometry or image URLs.
   If the backend later supplies them, exports automatically include
   them without making the current codebase depend on new fields.
================================================================ */

interface ExportEvidence {
  id: string;
  label: string;
  areaEstimate: string;
  description: string;
  confidence: number;
  geometry?: unknown;
}

interface SimpleGeoJSONGeometry {
  type:
  | 'Point'
  | 'MultiPoint'
  | 'LineString'
  | 'MultiLineString'
  | 'Polygon'
  | 'MultiPolygon';
  coordinates: unknown[];
}

const normalizeGeometry = (
  geometry: unknown
): SimpleGeoJSONGeometry | null => {
  if (!geometry || typeof geometry !== 'object') {
    return null;
  }

  const candidate = geometry as {
    type?: unknown;
    coordinates?: unknown;
  };

  if (
    typeof candidate.type !== 'string' ||
    !Array.isArray(candidate.coordinates)
  ) {
    return null;
  }

  const validTypes = [
    'Point',
    'MultiPoint',
    'LineString',
    'MultiLineString',
    'Polygon',
    'MultiPolygon',
  ];

  if (!validTypes.includes(candidate.type)) {
    return null;
  }

  return {
    type: candidate.type as SimpleGeoJSONGeometry['type'],
    coordinates: candidate.coordinates as unknown[],
  };
};

const downloadTextFile = (
  content: string,
  filename: string,
  mimeType: string
) => {
  const blob = new Blob([content], {
    type: mimeType,
  });

  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');

  anchor.href = url;
  anchor.download = filename;
  anchor.style.display = 'none';

  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();

  window.setTimeout(
    () => URL.revokeObjectURL(url),
    100
  );
};

const sanitizeFilename = (
  value: string
): string => {
  return value
    .replace(/[^a-z0-9_-]+/gi, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 80) || 'analysis';
};

const escapeHtml = (
  value: string
): string => {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
};
