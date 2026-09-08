/**
 * SatQuery AI — High-Fidelity Intelligence Brief & PDF Generator
 * 
 * Provides print-ready, downloadable, and visual Earth Observation
 * Intelligence Briefs with embedded satellite imagery, spatial evidence,
 * confidence meters, and audit telemetry.
 */

import type { AnalysisResult, Observation, EvidenceRegion } from '../types/satquery';

export interface BriefGenerationOptions {
  executionId?: string;
  observations?: Observation[];
  queryText?: string;
}

/** Sanitize text for HTML injection */
function escapeHtml(unsafe: unknown): string {
  if (unsafe === null || unsafe === undefined) return '';
  return String(unsafe)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

/** Format markdown into print-ready styled HTML */
function formatMarkdown(md: string): string {
  if (!md) return '';
  return md
    .split('\n')
    .map((line: string) => {
      const trimmed = line.trim();
      if (!trimmed) return '';
      
      // Headings
      if (trimmed.startsWith('#### ')) {
        const heading = trimmed.replace(/^####\s*/, '');
        return `<h5 style="margin: 10px 0 4px; font-family: 'Space Grotesk', -apple-system, sans-serif; font-size: 10px; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; color: #475569;">${escapeHtml(heading)}</h5>`;
      }
      if (trimmed.startsWith('### ')) {
        const heading = trimmed.replace(/^###\s*/, '');
        return `<h4 style="margin: 14px 0 6px; font-family: 'Space Grotesk', -apple-system, sans-serif; font-size: 11.5px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: #0284c7; border-bottom: 1px solid #f1f5f9; padding-bottom: 3px;">${escapeHtml(heading)}</h4>`;
      }
      if (trimmed.startsWith('## ')) {
        const heading = trimmed.replace(/^##\s*/, '');
        return `<h3 style="margin: 16px 0 8px; font-family: 'Space Grotesk', -apple-system, sans-serif; font-size: 13px; font-weight: 700; color: #0f172a;">${escapeHtml(heading)}</h3>`;
      }

      // Numbered lists (1. , 2. )
      const numberedMatch = trimmed.match(/^(\d+)\.\s+(.*)/);
      if (numberedMatch) {
        const num = numberedMatch[1];
        const content = numberedMatch[2];
        const htmlContent = content.replace(/\*\*([^*]+)\*\*/g, '<strong style="color: #0f172a; font-weight: 600;">$1</strong>');
        return `<div style="display: flex; gap: 8px; margin: 5px 0; align-items: flex-start; font-size: 10.5px; line-height: 1.55;"><span style="color: #0284c7; font-family: 'JetBrains Mono', monospace; font-weight: 700; font-size: 9.5px; background: #e0f2fe; padding: 0 4px; border-radius: 2px; flex-shrink: 0;">${escapeHtml(num)}</span><span>${htmlContent}</span></div>`;
      }

      // Bullet points (* , - )
      if (trimmed.startsWith('* ') || trimmed.startsWith('- ')) {
        const content = trimmed.replace(/^[*\-]\s*/, '');
        const htmlContent = content.replace(/\*\*([^*]+)\*\*/g, '<strong style="color: #0f172a; font-weight: 600;">$1</strong>');
        return `<div style="display: flex; gap: 8px; margin: 4px 0; align-items: flex-start; font-size: 10.5px; line-height: 1.55;"><span style="color: #0284c7; font-weight: bold; flex-shrink: 0; margin-top: -1px;">•</span><span>${htmlContent}</span></div>`;
      }

      const htmlContent = trimmed.replace(/\*\*([^*]+)\*\*/g, '<strong style="color: #0f172a; font-weight: 600;">$1</strong>');
      return `<p style="margin: 5px 0; font-size: 10.5px; line-height: 1.55; color: #334155;">${htmlContent}</p>`;
    })
    .filter(Boolean)
    .join('\n');
}

/** Resolve absolute or relative image URL for print window */
function resolveImageUrl(url: string | undefined): string {
  if (!url) return '';
  if (url.startsWith('http://') || url.startsWith('https://') || url.startsWith('data:')) {
    return url;
  }
  if (typeof window !== 'undefined') {
    return `${window.location.origin}${url.startsWith('/') ? '' : '/'}${url}`;
  }
  return url;
}

/**
 * Build the complete HTML document for the Intelligence Brief.
 */
export function generateBriefHtml(
  result: AnalysisResult,
  options: BriefGenerationOptions = {}
): string {
  const executionId =
    options.executionId ||
    result.executionSummary?.telemetryId ||
    `SQ-${Date.now().toString(36).slice(-6).toUpperCase()}`;

  const generatedAt = new Date().toISOString();
  const readableDate = new Date().toLocaleString('en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
  });

  const queryText = options.queryText || result.queryText || 'Geospatial Query';
  const task = result.task || result.executionSummary?.task || 'EARTH_OBSERVATION_ANALYSIS';
  const confidence = typeof result.confidence === 'number' ? Math.max(0, Math.min(100, result.confidence)) : null;

  const confidenceLabel =
    confidence === null
      ? 'DETERMINISTIC / N/A'
      : confidence >= 90
      ? 'VERY HIGH CONFIDENCE'
      : confidence >= 75
      ? 'HIGH CONFIDENCE'
      : confidence >= 60
      ? 'MODERATE CONFIDENCE'
      : 'LOW CONFIDENCE';

  const confidenceColor =
    confidence === null
      ? '#64748b'
      : confidence >= 85
      ? '#059669'
      : confidence >= 70
      ? '#0284c7'
      : confidence >= 50
      ? '#d97706'
      : '#dc2626';

  const isVerified =
    result.status === 'COMPLETE' &&
    Boolean(result.executionSummary?.task) &&
    Array.isArray(result.executionSummary?.modelsUsed) &&
    result.executionSummary.modelsUsed.length > 0;

  // Observations / Imagery
  const observations = options.observations || [];
  const hasImages = observations.some(obs => obs.imageUrl || obs.thumbnailUrl);

  // Evidence Rows
  const evidence: EvidenceRegion[] = result.evidence || [];
  const evidenceRows = evidence.length
    ? evidence
        .map((region, index) => {
          const regionConfidence = Math.max(0, Math.min(100, Number(region.confidence) || 0));
          const coordsText = region.centerCoordinates
            ? `[${region.centerCoordinates[1].toFixed(4)}°N, ${region.centerCoordinates[0].toFixed(4)}°E]`
            : region.coords
            ? `Pixel [${Math.round(region.coords.x)}%, ${Math.round(region.coords.y)}%]`
            : 'Geotagged';

          return `
            <tr>
              <td class="mono font-bold" style="color: #0284c7;">#0${index + 1}</td>
              <td>
                <div style="font-weight: 700; color: #0f172a; font-size: 10px;">${escapeHtml(region.label)}</div>
                <div class="muted" style="font-size: 8.5px; margin-top: 2px;">${escapeHtml(region.description || 'Spatial detection confirmed by Earth Observation pipeline')}</div>
              </td>
              <td class="mono" style="font-size: 9px; color: #475569;">${escapeHtml(coordsText)}</td>
              <td class="mono font-bold" style="font-size: 9px; color: #0f172a;">${escapeHtml(region.areaEstimate || 'N/A')}</td>
              <td>
                <div style="display: flex; align-items: center; gap: 6px;">
                  <span class="mono font-bold" style="font-size: 9px; color: #059669;">${regionConfidence}%</span>
                  <div style="width: 45px; height: 5px; background: #e2e8f0; border-radius: 3px; overflow: hidden;">
                    <div style="width: ${regionConfidence}%; height: 100%; background: #059669;"></div>
                  </div>
                </div>
              </td>
            </tr>
          `;
        })
        .join('')
    : `
        <tr>
          <td colspan="5" class="empty" style="padding: 16px; text-align: center; color: #64748b; font-family: monospace; font-size: 9px;">
            No discreet spatial bounding regions required for this analytical category.
          </td>
        </tr>
      `;

  // Visual Imagery HTML
  let visualImageryHtml = '';
  if (hasImages) {
    const imageCards = observations
      .filter(obs => obs.imageUrl || obs.thumbnailUrl)
      .map((obs, idx) => {
        const resolvedUrl = resolveImageUrl(obs.imageUrl || obs.thumbnailUrl);
        const modality = obs.modality || obs.metadata?.modality || 'OPTICAL';
        const sensor = obs.metadata?.sensor || obs.name || `Observation ${idx + 1}`;
        const date = obs.date || obs.metadata?.acquisitionTime || obs.metadata?.acquisitionDate || 'Recent Acquisition';
        const gsd = obs.metadata?.groundSamplingDistance || (obs.metadata?.resolution ? `${obs.metadata.resolution}m` : '10m GSD');

        return `
          <div class="image-card">
            <div class="image-header">
              <span class="image-badge">${escapeHtml(modality)}</span>
              <span class="image-meta">${escapeHtml(sensor)} · ${escapeHtml(gsd)}</span>
            </div>
            <div class="image-container">
              <img src="${escapeHtml(resolvedUrl)}" alt="${escapeHtml(sensor)}" loading="eager" crossorigin="anonymous" />
              <div class="image-tag">${escapeHtml(date)}</div>
            </div>
          </div>
        `;
      })
      .join('');

    visualImageryHtml = `
      <section class="section">
        <div class="section-title">
          <span>Satellite Observation Imagery & Sensor Snapshots</span>
          <span>${observations.length} RASTER INPUT(S)</span>
        </div>
        <div class="image-grid">
          ${imageCards}
        </div>
      </section>
    `;
  }

  // Specialist Models Chips
  const modelsUsed = result.executionSummary?.modelsUsed || [];
  const modelChips = modelsUsed.length
    ? modelsUsed.map(m => `<span class="chip">${escapeHtml(m)}</span>`).join('')
    : '<span class="chip">AUTONOMOUS ORCHESTRATION ENGINE</span>';

  // Audit Steps
  const auditSteps = [
    { num: '01', title: 'Intent Interpretation', desc: 'Natural-language query converted to remote-sensing parameter bounds.' },
    { num: '02', title: 'Raster Validation & Ingestion', desc: 'Spectral bands, resolution geometry, and coordinate CRS verified.' },
    { num: '03', title: 'Specialist Model Execution', desc: 'Distributed specialist remote-sensing AI models evaluated the scene.' },
    { num: '04', title: 'Spatial Grounding & Evidence Assembly', desc: 'Feature detections grounded with geographic coordinates and metrics.' },
    { num: '05', title: 'Verification & Quality Check', desc: 'Multi-layer confidence assessment and audit telemetry logged.' },
  ];

  const auditHtml = auditSteps
    .map(
      s => `
        <div class="audit-step">
          <div class="audit-num">${s.num}</div>
          <div class="audit-body">
            <div class="audit-title">${s.title}</div>
            <div class="audit-desc">${s.desc}</div>
          </div>
        </div>
      `
    )
    .join('');

  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>SatQuery Intelligence Brief — ${escapeHtml(executionId)}</title>
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=JetBrains+Mono:wght@400;600;700&family=Inter:wght@400;500;600;700&display=swap');

      @page {
        size: A4 portrait;
        margin: 12mm 14mm 14mm 14mm;
      }

      :root {
        color-scheme: light;
        --bg-page: #ffffff;
        --text-main: #0f172a;
        --text-muted: #475569;
        --text-dim: #64748b;
        --primary: #0284c7;
        --primary-dark: #0369a1;
        --primary-light: #e0f2fe;
        --success: #059669;
        --success-light: #d1fae5;
        --warning: #d97706;
        --border: #e2e8f0;
        --border-dark: #cbd5e1;
        --panel: #f8fafc;
        --card-bg: #ffffff;
      }

      * {
        box-sizing: border-box;
        margin: 0;
        padding: 0;
      }

      body {
        background: #f1f5f9;
        color: var(--text-main);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-size: 10px;
        line-height: 1.5;
        padding: 24px;
        -webkit-font-smoothing: antialiased;
      }

      .page-container {
        max-width: 820px;
        margin: 0 auto;
        background: var(--bg-page);
        padding: 32px 36px;
        border-radius: 6px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
        border: 1px solid var(--border);
      }

      .mono {
        font-family: 'JetBrains Mono', 'Courier New', monospace;
      }

      .font-bold {
        font-weight: 700;
      }

      /* Classification & Security Bar */
      .classification-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: #0f172a;
        color: #94a3b8;
        padding: 5px 12px;
        border-radius: 4px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 7.5px;
        font-weight: 700;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        margin-bottom: 20px;
      }

      .classification-badge {
        color: #38bdf8;
        display: flex;
        align-items: center;
        gap: 6px;
      }

      /* Header */
      .header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        padding-bottom: 18px;
        border-bottom: 2px solid var(--text-main);
        gap: 20px;
      }

      .logo-group {
        display: flex;
        align-items: center;
        gap: 10px;
      }

      .logo-icon {
        width: 32px;
        height: 32px;
        background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%);
        border-radius: 6px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 800;
        font-size: 14px;
      }

      .title-group h1 {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 20px;
        font-weight: 700;
        letter-spacing: -0.02em;
        color: var(--text-main);
        line-height: 1.2;
      }

      .title-group .subtitle {
        font-size: 9.5px;
        color: var(--text-dim);
        font-weight: 500;
        margin-top: 2px;
      }

      .meta-box {
        text-align: right;
        font-family: 'JetBrains Mono', monospace;
        font-size: 8px;
        color: var(--text-dim);
      }

      .meta-box .exec-id {
        font-size: 12px;
        font-weight: 700;
        color: var(--primary-dark);
        margin-top: 2px;
      }

      /* Sections */
      .section {
        margin-top: 18px;
        break-inside: avoid;
        page-break-inside: avoid;
      }

      .section-title {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding-bottom: 5px;
        border-bottom: 1.5px solid var(--border-dark);
        font-family: 'Space Grotesk', sans-serif;
        font-size: 8.5px;
        font-weight: 700;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--text-dim);
      }

      /* Query Box */
      .query-box {
        margin-top: 10px;
        padding: 12px 14px;
        background: var(--panel);
        border: 1px solid var(--border);
        border-left: 3.5px solid var(--primary);
        border-radius: 0 4px 4px 0;
      }

      .query-label {
        font-family: 'JetBrains Mono', monospace;
        font-size: 7.5px;
        font-weight: 700;
        letter-spacing: 0.1em;
        color: var(--primary);
        text-transform: uppercase;
        margin-bottom: 4px;
      }

      .query-content {
        font-size: 11.5px;
        font-weight: 600;
        color: var(--text-main);
        font-style: italic;
      }

      /* Result Box */
      .result-box {
        margin-top: 10px;
        padding: 14px 16px;
        background: #ffffff;
        border: 1px solid var(--border);
        border-radius: 4px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
      }

      .result-headline {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 13px;
        font-weight: 700;
        color: var(--text-main);
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 8px;
      }

      .verified-badge {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        background: var(--success-light);
        color: var(--success);
        padding: 2px 6px;
        border-radius: 3px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 7.5px;
        font-weight: 700;
        letter-spacing: 0.06em;
      }

      /* Key Metrics Grid */
      .metrics-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 8px;
        margin-top: 10px;
      }

      .metric-card {
        padding: 8px 10px;
        background: var(--panel);
        border: 1px solid var(--border);
        border-radius: 4px;
      }

      .metric-label {
        font-family: 'JetBrains Mono', monospace;
        font-size: 7px;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--text-dim);
      }

      .metric-value {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 11px;
        font-weight: 700;
        color: var(--text-main);
        margin-top: 2px;
      }

      /* Confidence Gauge */
      .confidence-container {
        margin-top: 10px;
        padding: 10px 14px;
        background: var(--panel);
        border: 1px solid var(--border);
        border-radius: 4px;
      }

      .confidence-header {
        display: flex;
        justify-content: space-between;
        font-family: 'JetBrains Mono', monospace;
        font-size: 8.5px;
        font-weight: 700;
      }

      .confidence-track {
        height: 8px;
        background: #e2e8f0;
        border-radius: 4px;
        margin-top: 6px;
        overflow: hidden;
      }

      .confidence-fill {
        height: 100%;
        border-radius: 4px;
        transition: width 0.3s ease;
      }

      /* Satellite Imagery Grid */
      .image-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 12px;
        margin-top: 10px;
      }

      .image-card {
        border: 1px solid var(--border-dark);
        border-radius: 4px;
        overflow: hidden;
        background: #0f172a;
      }

      .image-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: #1e293b;
        padding: 4px 8px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 7.5px;
      }

      .image-badge {
        background: #0284c7;
        color: white;
        padding: 1px 5px;
        border-radius: 2px;
        font-weight: 700;
      }

      .image-meta {
        color: #cbd5e1;
      }

      .image-container {
        position: relative;
        height: 170px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: #090d16;
        overflow: hidden;
      }

      .image-container img {
        width: 100%;
        height: 100%;
        object-fit: cover;
      }

      .image-tag {
        position: absolute;
        bottom: 6px;
        right: 6px;
        background: rgba(15, 23, 42, 0.85);
        color: #e2e8f0;
        padding: 2px 6px;
        border-radius: 3px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 7.5px;
      }

      /* Evidence Table */
      table {
        width: 100%;
        margin-top: 8px;
        border-collapse: collapse;
      }

      th {
        padding: 7px 8px;
        background: var(--panel);
        border-bottom: 1.5px solid var(--border-dark);
        color: var(--text-dim);
        font-family: 'JetBrains Mono', monospace;
        font-size: 7.5px;
        font-weight: 700;
        text-align: left;
        text-transform: uppercase;
        letter-spacing: 0.08em;
      }

      td {
        padding: 8px;
        border-bottom: 1px solid var(--border);
        vertical-align: middle;
      }

      /* Specialist Models Chips */
      .chips {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        margin-top: 8px;
      }

      .chip {
        display: inline-flex;
        align-items: center;
        padding: 3px 8px;
        background: var(--panel);
        border: 1px solid var(--border-dark);
        border-radius: 3px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 7.5px;
        font-weight: 600;
        color: var(--text-muted);
      }

      /* Audit Steps */
      .audit-grid {
        margin-top: 8px;
        border-left: 2px solid var(--primary-light);
        padding-left: 12px;
      }

      .audit-step {
        display: flex;
        gap: 10px;
        margin-bottom: 8px;
        align-items: flex-start;
      }

      .audit-num {
        font-family: 'JetBrains Mono', monospace;
        font-size: 8px;
        font-weight: 700;
        color: var(--primary);
        background: var(--primary-light);
        padding: 1px 5px;
        border-radius: 2px;
      }

      .audit-title {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 9px;
        font-weight: 700;
        color: var(--text-main);
      }

      .audit-desc {
        font-size: 8px;
        color: var(--text-dim);
        margin-top: 1px;
      }

      /* Footer */
      .footer {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 24px;
        padding-top: 12px;
        border-top: 1px solid var(--border);
        font-family: 'JetBrains Mono', monospace;
        font-size: 7.5px;
        color: var(--text-dim);
      }

      /* Interactive Toolbar (Screen Only) */
      .toolbar {
        position: sticky;
        bottom: 20px;
        margin: 20px auto 0;
        max-width: 820px;
        padding: 12px 18px;
        background: #0f172a;
        color: white;
        border-radius: 8px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.25);
        font-family: 'JetBrains Mono', monospace;
        font-size: 9px;
        z-index: 1000;
      }

      .toolbar-buttons {
        display: flex;
        gap: 8px;
      }

      .toolbar-btn {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 7px 14px;
        border-radius: 4px;
        border: none;
        cursor: pointer;
        font-family: 'JetBrains Mono', monospace;
        font-size: 9px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        transition: all 0.2s ease;
      }

      .btn-primary {
        background: #0284c7;
        color: white;
      }

      .btn-primary:hover {
        background: #0369a1;
      }

      .btn-secondary {
        background: #334155;
        color: #f1f5f9;
      }

      .btn-secondary:hover {
        background: #475569;
      }

      /* PRINT STYLES */
      @media print {
        body {
          background: #ffffff !important;
          padding: 0 !important;
          color: #0f172a !important;
        }

        .page-container {
          max-width: 100% !important;
          margin: 0 !important;
          padding: 0 !important;
          box-shadow: none !important;
          border: none !important;
        }

        .toolbar {
          display: none !important;
        }

        * {
          -webkit-print-color-adjust: exact !important;
          print-color-adjust: exact !important;
        }

        .section, .image-card, .metric-card, tr {
          break-inside: avoid !important;
          page-break-inside: avoid !important;
        }
      }
    </style>
  </head>

  <body>
    <main class="page-container">
      <!-- Security / Mission Banner -->
      <div class="classification-bar">
        <div class="classification-badge">
          <span>●</span>
          <span>SATQUERY AI // EARTH OBSERVATION INTELLIGENCE PLATFORM</span>
        </div>
        <div>UNCLASSIFIED // SCIENTIFIC AUDIT BRIEF</div>
      </div>

      <!-- Header -->
      <header class="header">
        <div class="logo-group">
          <div class="logo-icon">SQ</div>
          <div class="title-group">
            <h1>Earth Observation Intelligence Brief</h1>
            <div class="subtitle">Evidence-Grounded · Machine-Assisted Geospatial Intelligence</div>
          </div>
        </div>

        <div class="meta-box">
          <div>EXECUTION ID</div>
          <div class="exec-id">${escapeHtml(executionId)}</div>
          <div style="margin-top: 3px;">DATE: ${escapeHtml(readableDate)}</div>
        </div>
      </header>

      <!-- Analysis Intent -->
      <section class="section">
        <div class="section-title">
          <span>Analysis Intent & Query</span>
          <span>TASK: ${escapeHtml(task)}</span>
        </div>

        <div class="query-box">
          <div class="query-label">NATURAL LANGUAGE REQUEST</div>
          <div class="query-content">"${escapeHtml(queryText)}"</div>
        </div>
      </section>

      <!-- Key Findings & Result -->
      <section class="section">
        <div class="section-title">
          <span>Executive Intelligence Finding</span>
          <span>${isVerified ? 'VERIFIED REPORT' : 'ANALYSIS COMPLETE'}</span>
        </div>

        <div class="result-box">
          <div class="result-headline">
            <span>${escapeHtml(result.headline || 'Geospatial Finding')}</span>
            ${isVerified ? '<span class="verified-badge">✓ VERIFIED RESULT</span>' : ''}
          </div>
          <div>
            ${formatMarkdown(result.answer || '')}
          </div>
        </div>

        <!-- Metrics Grid -->
        <div class="metrics-grid">
          <div class="metric-card">
            <div class="metric-label">ANALYSIS TYPE</div>
            <div class="metric-value">${escapeHtml(task)}</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">EVIDENCE COUNT</div>
            <div class="metric-value">${evidence.length} Feature(s)</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">INPUT DATASETS</div>
            <div class="metric-value">${observations.length || result.executionSummary?.inputs?.length || 1} Raster(s)</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">STATUS</div>
            <div class="metric-value" style="color: var(--success);">${escapeHtml(result.status)}</div>
          </div>
        </div>
      </section>

      <!-- Confidence Assessment -->
      <section class="section">
        <div class="section-title">
          <span>Calibrated Confidence Assessment</span>
          <span style="color: ${confidenceColor}; font-weight: 700;">${confidence !== null ? `${confidence}% · ` : ''}${escapeHtml(confidenceLabel)}</span>
        </div>

        <div class="confidence-container">
          <div class="confidence-header">
            <span>MODEL & PIPELINE CALIBRATION</span>
            <span style="color: ${confidenceColor};">${confidence !== null ? `${confidence} / 100` : 'DETERMINISTIC'}</span>
          </div>
          <div class="confidence-track">
            <div class="confidence-fill" style="width: ${confidence ?? 100}%; background: ${confidenceColor};"></div>
          </div>
        </div>
      </section>

      <!-- Visual Satellite Imagery -->
      ${visualImageryHtml}

      <!-- Spatial Evidence Breakdown -->
      <section class="section">
        <div class="section-title">
          <span>Spatial Evidence & Grounded Regions</span>
          <span>${evidence.length} REGION(S) IDENTIFIED</span>
        </div>

        <table>
          <thead>
            <tr>
              <th style="width: 45px;">#</th>
              <th>Region / Finding</th>
              <th style="width: 140px;">Spatial Extent / Coords</th>
              <th style="width: 90px;">Est. Area</th>
              <th style="width: 95px;">Confidence</th>
            </tr>
          </thead>
          <tbody>
            ${evidenceRows}
          </tbody>
        </table>
      </section>

      <!-- Specialist Models & Telemetry -->
      <section class="section">
        <div class="section-title">
          <span>Specialist Remote-Sensing Models</span>
          <span>PIPELINE TELEMETRY</span>
        </div>
        <div class="chips">
          ${modelChips}
        </div>
      </section>

      <!-- Audit Trail -->
      <section class="section">
        <div class="section-title">
          <span>Observable Audit Trail & Workflow Chain</span>
          <span>CHAIN OF CUSTODY</span>
        </div>
        <div class="audit-grid">
          ${auditHtml}
        </div>
      </section>

      <!-- Footer -->
      <footer class="footer">
        <div>SATQUERY AI · HIGH-PRECISION REMOTE SENSING PLATFORM</div>
        <div>GENERATED: ${escapeHtml(generatedAt)} · AUDIT: ${escapeHtml(executionId)}</div>
      </footer>
    </main>

    <!-- Screen Toolbar -->
    <div class="toolbar">
      <div style="display: flex; align-items: center; gap: 8px;">
        <span style="color: #38bdf8;">🖨️</span>
        <span>Ready to Print / Save as PDF. Select <strong>"Save as PDF"</strong> in your browser printer.</span>
      </div>
      <div class="toolbar-buttons">
        <button class="toolbar-btn btn-primary" onclick="window.print()">🖨️ Print / Save as PDF</button>
        <button class="toolbar-btn btn-secondary" onclick="downloadBrief()">💾 Download HTML</button>
      </div>
    </div>

    <script>
      function downloadBrief() {
        const blob = new Blob([document.documentElement.outerHTML], { type: 'text/html' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'satquery-intelligence-brief-${escapeHtml(executionId)}.html';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }
    </script>
  </body>
</html>`;
}

/**
 * Open and print the high-fidelity Intelligence Brief.
 */
export function printIntelligenceBrief(
  result: AnalysisResult,
  options: BriefGenerationOptions = {}
): boolean {
  const html = generateBriefHtml(result, options);
  const printWindow = window.open('', '_blank', 'width=1100,height=900');

  if (printWindow) {
    printWindow.document.open();
    printWindow.document.write(html);
    printWindow.document.close();
    printWindow.focus();

    // Give browser time to load webfonts and images before invoking print
    window.setTimeout(() => {
      try {
        printWindow.print();
      } catch (err) {
        console.error('Print invocation failed:', err);
      }
    }, 700);

    return true;
  }

  // Fallback: download HTML directly if popups are blocked
  downloadIntelligenceBriefHtml(result, options);
  return false;
}

/**
 * Download the standalone Intelligence Brief HTML file.
 */
export function downloadIntelligenceBriefHtml(
  result: AnalysisResult,
  options: BriefGenerationOptions = {}
): void {
  const html = generateBriefHtml(result, options);
  const executionId =
    options.executionId ||
    result.executionSummary?.telemetryId ||
    `SQ-${Date.now().toString(36).slice(-6).toUpperCase()}`;

  const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `satquery-intelligence-brief-${executionId.replace(/[^a-zA-Z0-9_-]/g, '_')}.html`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
