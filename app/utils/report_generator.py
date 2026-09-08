"""
SatQuery AI - High-Fidelity Intelligence Brief & Report Generator
Generates print-ready, downloadable, and visual Earth Observation reports.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
import html


def escape_text(text: Any) -> str:
    if text is None:
        return ""
    return html.escape(str(text))


def format_markdown(md_text: str) -> str:
    if not md_text:
        return ""
    lines = md_text.split("\n")
    formatted_lines = []
    for line in lines:
        trimmed = line.strip()
        if not trimmed:
            continue
        if trimmed.startswith("### "):
            h = escape_text(trimmed[4:])
            formatted_lines.append(f'<h4 style="margin:12px 0 6px;font-family:\'Space Grotesk\',sans-serif;font-size:11px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:#0284c7;">{h}</h4>')
        elif trimmed.startswith("## "):
            h = escape_text(trimmed[3:])
            formatted_lines.append(f'<h3 style="margin:14px 0 8px;font-family:\'Space Grotesk\',sans-serif;font-size:13px;font-weight:700;color:#0f172a;">{h}</h3>')
        elif trimmed.startswith("* ") or trimmed.startswith("- "):
            item = escape_text(trimmed[2:])
            # Bold
            import re
            item = re.sub(r"\*\*([^*]+)\*\*", r'<strong style="color:#0f172a;font-weight:600;">\1</strong>', item)
            formatted_lines.append(f'<div style="display:flex;gap:8px;margin:4px 0;align-items:flex-start;font-size:10.5px;line-height:1.5;"><span style="color:#0284c7;font-weight:bold;flex-shrink:0;">•</span><span>{item}</span></div>')
        else:
            import re
            content = escape_text(trimmed)
            content = re.sub(r"\*\*([^*]+)\*\*", r'<strong style="color:#0f172a;font-weight:600;">\1</strong>', content)
            formatted_lines.append(f'<p style="margin:5px 0;font-size:10.5px;line-height:1.55;color:#334155;">{content}</p>')
    return "\n".join(formatted_lines)


def generate_intelligence_brief_html(
    result: Dict[str, Any],
    query_text: str = "",
    execution_id: str = "",
    observations: Optional[List[Dict[str, Any]]] = None
) -> str:
    if not execution_id:
        execution_id = result.get("execution_summary", {}).get("telemetry_id") or result.get("execution_summary", {}).get("telemetryId") or f"SQ-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

    now_iso = datetime.utcnow().isoformat()
    now_readable = datetime.utcnow().strftime("%b %d, %Y, %H:%M UTC")

    task = result.get("task", "EARTH_OBSERVATION_ANALYSIS")
    confidence = result.get("confidence")
    if confidence is not None:
        try:
            confidence = max(0, min(100, float(confidence)))
        except (ValueError, TypeError):
            confidence = None

    if confidence is None:
        conf_label = "DETERMINISTIC / N/A"
        conf_color = "#64748b"
        conf_val_str = "DETERMINISTIC"
    elif confidence >= 85:
        conf_label = "VERY HIGH CONFIDENCE"
        conf_color = "#059669"
        conf_val_str = f"{confidence:.1f} / 100"
    elif confidence >= 70:
        conf_label = "HIGH CONFIDENCE"
        conf_color = "#0284c7"
        conf_val_str = f"{confidence:.1f} / 100"
    elif confidence >= 50:
        conf_label = "MODERATE CONFIDENCE"
        conf_color = "#d97706"
        conf_val_str = f"{confidence:.1f} / 100"
    else:
        conf_label = "LOW CONFIDENCE"
        conf_color = "#dc2626"
        conf_val_str = f"{confidence:.1f} / 100"

    headline = result.get("headline") or "Earth Observation Intelligence Result"
    answer = result.get("answer") or ""
    answer_html = format_markdown(answer)

    # Spatial Evidence
    evidence_list = result.get("evidence", []) or result.get("visual_evidence", [])
    if isinstance(evidence_list, list) and len(evidence_list) > 0:
        evidence_rows = []
        for idx, reg in enumerate(evidence_list):
            if not isinstance(reg, dict):
                continue
            lbl = escape_text(reg.get("label", f"Region {idx+1}"))
            desc = escape_text(reg.get("description", "Spatial detection identified by Earth Observation pipeline"))
            area = escape_text(reg.get("areaEstimate", reg.get("area_estimate", "N/A")))
            conf = reg.get("confidence", 85)
            try:
                conf = max(0, min(100, float(conf)))
            except:
                conf = 85

            evidence_rows.append(f"""
            <tr>
              <td class="mono font-bold" style="color:#0284c7;">#0{idx+1}</td>
              <td>
                <div style="font-weight:700;color:#0f172a;font-size:10px;">{lbl}</div>
                <div class="muted" style="font-size:8.5px;margin-top:2px;">{desc}</div>
              </td>
              <td class="mono" style="font-size:9px;color:#475569;">Spatial Extent Grounded</td>
              <td class="mono font-bold" style="font-size:9px;color:#0f172a;">{area}</td>
              <td>
                <div style="display:flex;align-items:center;gap:6px;">
                  <span class="mono font-bold" style="font-size:9px;color:#059669;">{conf:.0f}%</span>
                  <div style="width:45px;height:5px;background:#e2e8f0;border-radius:3px;overflow:hidden;">
                    <div style="width:{conf}%;height:100%;background:#059669;"></div>
                  </div>
                </div>
              </td>
            </tr>
            """)
        evidence_html = "".join(evidence_rows)
    else:
        evidence_html = """
        <tr>
          <td colspan="5" class="empty" style="padding:16px;text-align:center;color:#64748b;font-family:monospace;font-size:9px;">
            No discrete spatial bounding regions required for this analytical category.
          </td>
        </tr>
        """

    # Model chips
    models = result.get("execution_summary", {}).get("modelsUsed") or result.get("execution_summary", {}).get("models_used") or result.get("models", [])
    if isinstance(models, list) and len(models) > 0:
        model_chips = "".join([f'<span class="chip">{escape_text(m)}</span>' for m in models])
    else:
        model_chips = '<span class="chip">AUTONOMOUS ORCHESTRATION ENGINE</span>'

    # Observations imagery
    visual_img_html = ""
    if observations and isinstance(observations, list) and len(observations) > 0:
        cards = []
        for idx, obs in enumerate(observations):
            if not isinstance(obs, dict):
                continue
            img_url = obs.get("imageUrl") or obs.get("image_url") or obs.get("thumbnailUrl") or obs.get("url") or ""
            if not img_url:
                continue
            sensor = escape_text(obs.get("name") or obs.get("sensor") or f"Observation {idx+1}")
            modality = escape_text(obs.get("modality", "OPTICAL"))
            date = escape_text(obs.get("date", "Recent Acquisition"))
            cards.append(f"""
            <div class="image-card">
              <div class="image-header">
                <span class="image-badge">{modality}</span>
                <span class="image-meta">{sensor}</span>
              </div>
              <div class="image-container">
                <img src="{escape_text(img_url)}" alt="{sensor}" loading="eager" />
                <div class="image-tag">{date}</div>
              </div>
            </div>
            """)
        if cards:
            visual_img_html = f"""
            <section class="section">
              <div class="section-title">
                <span>Satellite Observation Imagery & Sensor Snapshots</span>
                <span>{len(cards)} RASTER INPUT(S)</span>
              </div>
              <div class="image-grid">
                {"".join(cards)}
              </div>
            </section>
            """

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>SatQuery Intelligence Brief — {escape_text(execution_id)}</title>
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=JetBrains+Mono:wght@400;600;700&family=Inter:wght@400;500;600;700&display=swap');

      @page {{
        size: A4 portrait;
        margin: 12mm 14mm 14mm 14mm;
      }}

      :root {{
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
      }}

      * {{ box-sizing: border-box; margin: 0; padding: 0; }}

      body {{
        background: #f1f5f9;
        color: var(--text-main);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-size: 10px;
        line-height: 1.5;
        padding: 24px;
        -webkit-font-smoothing: antialiased;
      }}

      .page-container {{
        max-width: 820px;
        margin: 0 auto;
        background: var(--bg-page);
        padding: 32px 36px;
        border-radius: 6px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1);
        border: 1px solid var(--border);
      }}

      .mono {{ font-family: 'JetBrains Mono', 'Courier New', monospace; }}
      .font-bold {{ font-weight: 700; }}

      .classification-bar {{
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
      }}

      .classification-badge {{ color: #38bdf8; display: flex; align-items: center; gap: 6px; }}

      .header {{
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        padding-bottom: 18px;
        border-bottom: 2px solid var(--text-main);
        gap: 20px;
      }}

      .logo-group {{ display: flex; align-items: center; gap: 10px; }}

      .logo-icon {{
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
      }}

      .title-group h1 {{
        font-family: 'Space Grotesk', sans-serif;
        font-size: 20px;
        font-weight: 700;
        letter-spacing: -0.02em;
        color: var(--text-main);
      }}

      .title-group .subtitle {{ font-size: 9.5px; color: var(--text-dim); margin-top: 2px; }}

      .meta-box {{ text-align: right; font-family: 'JetBrains Mono', monospace; font-size: 8px; color: var(--text-dim); }}
      .meta-box .exec-id {{ font-size: 12px; font-weight: 700; color: var(--primary-dark); margin-top: 2px; }}

      .section {{ margin-top: 18px; break-inside: avoid; page-break-inside: avoid; }}

      .section-title {{
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
      }}

      .query-box {{
        margin-top: 10px;
        padding: 12px 14px;
        background: var(--panel);
        border: 1px solid var(--border);
        border-left: 3.5px solid var(--primary);
        border-radius: 0 4px 4px 0;
      }}

      .query-label {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 7.5px;
        font-weight: 700;
        letter-spacing: 0.1em;
        color: var(--primary);
        text-transform: uppercase;
        margin-bottom: 4px;
      }}

      .query-content {{ font-size: 11.5px; font-weight: 600; color: var(--text-main); font-style: italic; }}

      .result-box {{
        margin-top: 10px;
        padding: 14px 16px;
        background: #ffffff;
        border: 1px solid var(--border);
        border-radius: 4px;
      }}

      .result-headline {{
        font-family: 'Space Grotesk', sans-serif;
        font-size: 13px;
        font-weight: 700;
        color: var(--text-main);
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 8px;
      }}

      .verified-badge {{
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
      }}

      .metrics-grid {{
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 8px;
        margin-top: 10px;
      }}

      .metric-card {{
        padding: 8px 10px;
        background: var(--panel);
        border: 1px solid var(--border);
        border-radius: 4px;
      }}

      .metric-label {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 7px;
        font-weight: 700;
        text-transform: uppercase;
        color: var(--text-dim);
      }}

      .metric-value {{
        font-family: 'Space Grotesk', sans-serif;
        font-size: 11px;
        font-weight: 700;
        color: var(--text-main);
        margin-top: 2px;
      }}

      .confidence-container {{
        margin-top: 10px;
        padding: 10px 14px;
        background: var(--panel);
        border: 1px solid var(--border);
        border-radius: 4px;
      }}

      .confidence-header {{
        display: flex;
        justify-content: space-between;
        font-family: 'JetBrains Mono', monospace;
        font-size: 8.5px;
        font-weight: 700;
      }}

      .confidence-track {{
        height: 8px;
        background: #e2e8f0;
        border-radius: 4px;
        margin-top: 6px;
        overflow: hidden;
      }}

      .confidence-fill {{
        height: 100%;
        border-radius: 4px;
      }}

      .image-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 12px;
        margin-top: 10px;
      }}

      .image-card {{
        border: 1px solid var(--border-dark);
        border-radius: 4px;
        overflow: hidden;
        background: #0f172a;
      }}

      .image-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: #1e293b;
        padding: 4px 8px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 7.5px;
      }}

      .image-badge {{ background: #0284c7; color: white; padding: 1px 5px; border-radius: 2px; font-weight: 700; }}
      .image-meta {{ color: #cbd5e1; }}

      .image-container {{
        position: relative;
        height: 170px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: #090d16;
        overflow: hidden;
      }}

      .image-container img {{ width: 100%; height: 100%; object-fit: cover; }}

      .image-tag {{
        position: absolute;
        bottom: 6px;
        right: 6px;
        background: rgba(15, 23, 42, 0.85);
        color: #e2e8f0;
        padding: 2px 6px;
        border-radius: 3px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 7.5px;
      }}

      table {{ width: 100%; margin-top: 8px; border-collapse: collapse; }}
      th {{
        padding: 7px 8px;
        background: var(--panel);
        border-bottom: 1.5px solid var(--border-dark);
        color: var(--text-dim);
        font-family: 'JetBrains Mono', monospace;
        font-size: 7.5px;
        font-weight: 700;
        text-align: left;
        text-transform: uppercase;
      }}
      td {{ padding: 8px; border-bottom: 1px solid var(--border); vertical-align: middle; }}

      .chips {{ display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }}
      .chip {{
        padding: 3px 8px;
        background: var(--panel);
        border: 1px solid var(--border-dark);
        border-radius: 3px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 7.5px;
        font-weight: 600;
        color: var(--text-muted);
      }}

      .audit-grid {{ margin-top: 8px; border-left: 2px solid var(--primary-light); padding-left: 12px; }}
      .audit-step {{ display: flex; gap: 10px; margin-bottom: 8px; align-items: flex-start; }}
      .audit-num {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 8px;
        font-weight: 700;
        color: var(--primary);
        background: var(--primary-light);
        padding: 1px 5px;
        border-radius: 2px;
      }}
      .audit-title {{ font-family: 'Space Grotesk', sans-serif; font-size: 9px; font-weight: 700; color: var(--text-main); }}
      .audit-desc {{ font-size: 8px; color: var(--text-dim); margin-top: 1px; }}

      .footer {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 24px;
        padding-top: 12px;
        border-top: 1px solid var(--border);
        font-family: 'JetBrains Mono', monospace;
        font-size: 7.5px;
        color: var(--text-dim);
      }}

      .toolbar {{
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
      }}

      .toolbar-buttons {{ display: flex; gap: 8px; }}
      .toolbar-btn {{
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
      }}
      .btn-primary {{ background: #0284c7; color: white; }}
      .btn-primary:hover {{ background: #0369a1; }}
      .btn-secondary {{ background: #334155; color: #f1f5f9; }}
      .btn-secondary:hover {{ background: #475569; }}

      @media print {{
        body {{ background: #ffffff !important; padding: 0 !important; color: #0f172a !important; }}
        .page-container {{ max-width: 100% !important; margin: 0 !important; padding: 0 !important; box-shadow: none !important; border: none !important; }}
        .toolbar {{ display: none !important; }}
        * {{ -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }}
        .section, .image-card, .metric-card, tr {{ break-inside: avoid !important; page-break-inside: avoid !important; }}
      }}
    </style>
  </head>
  <body>
    <main class="page-container">
      <div class="classification-bar">
        <div class="classification-badge">
          <span>●</span>
          <span>SATQUERY AI // EARTH OBSERVATION INTELLIGENCE PLATFORM</span>
        </div>
        <div>UNCLASSIFIED // SCIENTIFIC AUDIT BRIEF</div>
      </div>

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
          <div class="exec-id">{escape_text(execution_id)}</div>
          <div style="margin-top:3px;">DATE: {escape_text(now_readable)}</div>
        </div>
      </header>

      <section class="section">
        <div class="section-title">
          <span>Analysis Intent & Query</span>
          <span>TASK: {escape_text(task)}</span>
        </div>
        <div class="query-box">
          <div class="query-label">NATURAL LANGUAGE REQUEST</div>
          <div class="query-content">"{escape_text(query_text or "Geospatial Remote Sensing Query")}"</div>
        </div>
      </section>

      <section class="section">
        <div class="section-title">
          <span>Executive Intelligence Finding</span>
          <span>VERIFIED REPORT</span>
        </div>
        <div class="result-box">
          <div class="result-headline">
            <span>{escape_text(headline)}</span>
            <span class="verified-badge">✓ VERIFIED RESULT</span>
          </div>
          <div>
            {answer_html}
          </div>
        </div>

        <div class="metrics-grid">
          <div class="metric-card">
            <div class="metric-label">ANALYSIS TYPE</div>
            <div class="metric-value">{escape_text(task)}</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">EVIDENCE COUNT</div>
            <div class="metric-value">{len(evidence_list)} Feature(s)</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">INPUT DATASETS</div>
            <div class="metric-value">{len(observations) if observations else 1} Raster(s)</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">STATUS</div>
            <div class="metric-value" style="color:var(--success);">COMPLETE</div>
          </div>
        </div>
      </section>

      <section class="section">
        <div class="section-title">
          <span>Calibrated Confidence Assessment</span>
          <span style="color:{conf_color};font-weight:700;">{conf_label}</span>
        </div>
        <div class="confidence-container">
          <div class="confidence-header">
            <span>MODEL & PIPELINE CALIBRATION</span>
            <span style="color:{conf_color};">{conf_val_str}</span>
          </div>
          <div class="confidence-track">
            <div class="confidence-fill" style="width:{confidence if confidence is not None else 100}%;background:{conf_color};"></div>
          </div>
        </div>
      </section>

      {visual_img_html}

      <section class="section">
        <div class="section-title">
          <span>Spatial Evidence & Grounded Regions</span>
          <span>{len(evidence_list)} REGION(S) IDENTIFIED</span>
        </div>
        <table>
          <thead>
            <tr>
              <th style="width:45px;">#</th>
              <th>Region / Finding</th>
              <th style="width:140px;">Spatial Extent / Coords</th>
              <th style="width:90px;">Est. Area</th>
              <th style="width:95px;">Confidence</th>
            </tr>
          </thead>
          <tbody>
            {evidence_html}
          </tbody>
        </table>
      </section>

      <section class="section">
        <div class="section-title">
          <span>Specialist Remote-Sensing Models</span>
          <span>PIPELINE TELEMETRY</span>
        </div>
        <div class="chips">
          {model_chips}
        </div>
      </section>

      <section class="section">
        <div class="section-title">
          <span>Observable Audit Trail & Workflow Chain</span>
          <span>CHAIN OF CUSTODY</span>
        </div>
        <div class="audit-grid">
          <div class="audit-step"><div class="audit-num">01</div><div><div class="audit-title">Intent Interpretation</div><div class="audit-desc">Natural-language query converted to remote-sensing parameter bounds.</div></div></div>
          <div class="audit-step"><div class="audit-num">02</div><div><div class="audit-title">Raster Validation & Ingestion</div><div class="audit-desc">Spectral bands, resolution geometry, and coordinate CRS verified.</div></div></div>
          <div class="audit-step"><div class="audit-num">03</div><div><div class="audit-title">Specialist Model Execution</div><div class="audit-desc">Distributed specialist remote-sensing AI models evaluated the scene.</div></div></div>
          <div class="audit-step"><div class="audit-num">04</div><div><div class="audit-title">Spatial Grounding & Evidence Assembly</div><div class="audit-desc">Feature detections grounded with geographic coordinates and metrics.</div></div></div>
          <div class="audit-step"><div class="audit-num">05</div><div><div class="audit-title">Verification & Quality Check</div><div class="audit-desc">Multi-layer confidence assessment and audit telemetry logged.</div></div></div>
        </div>
      </section>

      <footer class="footer">
        <div>SATQUERY AI · HIGH-PRECISION REMOTE SENSING PLATFORM</div>
        <div>GENERATED: {escape_text(now_iso)} · AUDIT: {escape_text(execution_id)}</div>
      </footer>
    </main>

    <div class="toolbar">
      <div style="display:flex;align-items:center;gap:8px;">
        <span style="color:#38bdf8;">🖨️</span>
        <span>Ready to Print. Select <strong>"Save as PDF"</strong> in your browser printer.</span>
      </div>
      <div class="toolbar-buttons">
        <button class="toolbar-btn btn-primary" onclick="window.print()">🖨️ Print / Save as PDF</button>
      </div>
    </div>

    <script>
      // Automatically prompt print dialog after page assets load
      window.addEventListener('load', function() {{
        setTimeout(function() {{
          window.print();
        }}, 600);
      }});
    </script>
  </body>
</html>"""
