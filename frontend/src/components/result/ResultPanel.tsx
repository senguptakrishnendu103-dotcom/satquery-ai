import React, { useMemo, useState } from 'react';
import type { AnalysisResult, Observation } from '../../types/satquery';
import {
  printIntelligenceBrief,
  downloadIntelligenceBriefHtml,
} from '../../utils/intelligenceBriefGenerator';
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
  observations?: Observation[];
  selectedRegionId: string | null;
  onSelectRegion: (regionId: string | null) => void;
  onOpenReplay: () => void;
  onFollowUpQuery?: (actionQuery: string) => void;
}

export const ResultPanel: React.FC<ResultPanelProps> = ({
  result,
  observations = [],
  selectedRegionId,
  onSelectRegion,
  onOpenReplay,
  onFollowUpQuery,
}) => {
  /*
   * Handle confidence safely: null/undefined for deterministic/uncalibrated tools.
   */
  const hasConfidence =
    result.confidence !== undefined &&
    result.confidence !== null &&
    !isNaN(Number(result.confidence));

  const confidence = hasConfidence
    ? Math.max(0, Math.min(100, Number(result.confidence)))
    : null;

  const confidenceLabel = useMemo(() => {
    if (confidence === null) return 'N/A (DETERMINISTIC)';
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
      .map((input: any) => {
        if (typeof input === 'string') return input;
        if (input && typeof input === 'object') {
          return (
            input.name ||
            input.filename ||
            input.label ||
            input.product_id ||
            input.productId ||
            'Raster Dataset'
          );
        }
        return 'Observation';
      })
      .filter(Boolean)
      .join(', ') || 'N/A';

  const executionId = useMemo(
    () =>
      result.executionSummary?.telemetryId ||
      `SQ-${Date.now().toString(36).slice(-6).toUpperCase()}`,
    [result.executionSummary?.telemetryId]
  );

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
    setIsExportMenuOpen(false);
    const success = printIntelligenceBrief(result, {
      executionId,
      observations,
      queryText: result.queryText,
    });

    if (success) {
      showExportFeedback('Intelligence brief opened · Ready to print / save as PDF');
    } else {
      showExportFeedback('Intelligence brief downloaded as HTML');
    }
  };

  const downloadBriefAsHtml = () => {
    setIsExportMenuOpen(false);
    downloadIntelligenceBriefHtml(result, {
      executionId,
      observations,
      queryText: result.queryText,
    });
    showExportFeedback('Intelligence brief downloaded');
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
                    onClick={downloadBriefAsHtml}
                    className="
                      flex w-full items-start gap-3
                      border-b border-sat-border
                      px-3 py-3 text-left
                      transition-colors
                      hover:bg-sat-panel
                    "
                  >
                    <div className="mt-0.5 rounded border border-sat-stable/30 bg-sat-stable/10 p-1.5 text-sat-stable">
                      <Download className="h-3.5 w-3.5" />
                    </div>

                    <div className="min-w-0">
                      <div className="font-mono text-[9px] font-bold uppercase text-sat-text">
                        Download Brief (HTML)
                      </div>
                      <div className="mt-0.5 font-sans text-[9px] leading-relaxed text-sat-dim">
                        Standalone interactive intelligence report
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

                <div
                  className="
                    mt-3
                    text-xs
                    leading-[1.7]
                    text-sat-muted
                  "
                >
                  {(() => {
                    const answer = result.answer || '';
                    const lines = answer.split('\n').filter((l: string) => l.trim() !== '');
                    return lines.map((line: string, idx: number) => {
                      // ### heading
                      if (line.trim().startsWith('### ')) {
                        return (
                          <h3
                            key={idx}
                            className="
                              font-mono text-[11px] font-bold uppercase
                              tracking-wider text-sat-accent mt-1 mb-2
                            "
                          >
                            {line.trim().replace(/^###\s*/, '')}
                          </h3>
                        );
                      }
                      // * bullet point
                      if (line.trim().startsWith('* ')) {
                        const content = line.trim().replace(/^\*\s*/, '');
                        // Parse **bold** segments
                        const parts = content.split(/(\*\*[^*]+\*\*)/g);
                        return (
                          <div key={idx} className="flex gap-2 mt-1.5 items-start">
                            <span className="text-sat-accent mt-0.5 shrink-0">•</span>
                            <span>
                              {parts.map((part: string, pidx: number) => {
                                if (part.startsWith('**') && part.endsWith('**')) {
                                  return (
                                    <strong key={pidx} className="text-sat-text font-semibold">
                                      {part.slice(2, -2)}
                                    </strong>
                                  );
                                }
                                return <span key={pidx}>{part}</span>;
                              })}
                            </span>
                          </div>
                        );
                      }
                      // Regular line — also parse **bold**
                      const parts = line.split(/(\*\*[^*]+\*\*)/g);
                      return (
                        <p key={idx} className="mt-1">
                          {parts.map((part: string, pidx: number) => {
                            if (part.startsWith('**') && part.endsWith('**')) {
                              return (
                                <strong key={pidx} className="text-sat-text font-semibold">
                                  {part.slice(2, -2)}
                                </strong>
                              );
                            }
                            return <span key={pidx}>{part}</span>;
                          })}
                        </p>
                      );
                    });
                  })()}
                </div>

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
                    {confidence !== null ? confidence : 'N/A'}
                  </span>

                  {confidence !== null && (
                    <span className="pb-0.5 font-mono text-xs text-sat-dim">
                      /100
                    </span>
                  )}
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
                    className={`
                      h-full
                      rounded-full
                      transition-all
                      duration-700
                      ${confidence !== null ? 'bg-sat-stable' : 'bg-sat-dim/30'}
                    `}
                    style={{
                      width: `${confidence !== null ? confidence : 100}%`,
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
