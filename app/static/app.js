/* SATQUERY AI - Frontend Application Core Logic */

let state = {
  inputMode: 'single_image', // 'single_image', 'bi_temporal', 'optical_sar'
  activeDemo: 'demo_1',
  images: [],
  currentQuery: '',
  analysisResult: null,
  
  // Viewer state
  zoomLevel: 1,
  showOverlay: true,
  showSplitView: false,
  splitPercentage: 50,
  maskOpacity: 0.85,
  
  // Demos cache
  demos: {}
};

// Initialize App on DOM Load
document.addEventListener('DOMContentLoaded', async () => {
  await fetchDemos();
  await fetchModelRegistry();
  await loadDemoScenario('demo_1');
  initSplitDrag();
});

// Fetch Demos from API
async function fetchDemos() {
  try {
    const res = await fetch('/api/demos');
    const data = await res.json();
    if (data.demos) {
      data.demos.forEach(d => {
        state.demos[d.id] = d;
      });
    }
  } catch (err) {
    console.error('Failed to fetch demos', err);
  }
}

// Fetch Registered Models
async function fetchModelRegistry() {
  try {
    const res = await fetch('/api/models');
    const data = await res.json();
    if (data.models) {
      renderModelsModal(data.models);
    }
  } catch (err) {
    console.error('Failed to fetch model registry', err);
  }
}

// Load Demo Scenario
async function loadDemoScenario(demoId) {
  state.activeDemo = demoId;
  const demo = state.demos[demoId];
  if (!demo) return;

  // Set mode
  setInputMode(demo.input_mode);

  // Set images
  state.images = [...demo.images];

  // Set default query & chips
  document.getElementById('query-textarea').value = demo.default_query;
  renderSuggestedChips(demo.suggested_queries);

  // Render images in file list & viewer
  renderFileList();
  updateViewerImages();

  // Reset results display
  document.getElementById('result-card').style.display = 'none';
  document.getElementById('processing-tracker').style.display = 'none';

  // Automatically execute demo analysis for instant delight!
  setTimeout(() => {
    executeAnalysis();
  }, 300);
}

// Set Input Mode
function setInputMode(mode) {
  state.inputMode = mode;

  // Update Radio cards active state
  document.getElementById('card-mode-single').classList.toggle('active', mode === 'single_image');
  document.getElementById('card-mode-bitemporal').classList.toggle('active', mode === 'bi_temporal');
  document.getElementById('card-mode-multimodal').classList.toggle('active', mode === 'optical_sar');

  // Update Radio input checked
  const radio = document.querySelector(`input[name="input_mode_radio"][value="${mode}"]`);
  if (radio) radio.checked = true;

  // Update Badge
  const badge = document.getElementById('input-mode-badge');
  if (mode === 'single_image') badge.innerText = 'MODE A: SINGLE IMAGE';
  else if (mode === 'bi_temporal') badge.innerText = 'MODE B: BI-TEMPORAL';
  else if (mode === 'optical_sar') badge.innerText = 'MODE C: OPTICAL + SAR';

  // Toggle Split View option visibility
  const splitBtn = document.getElementById('btn-toggle-split');
  if (mode === 'bi_temporal') {
    splitBtn.style.display = 'flex';
  } else {
    splitBtn.style.display = 'none';
    state.showSplitView = false;
    document.getElementById('split-overlay').style.display = 'none';
  }
}

// Render File List with Metadata Inspection
function renderFileList() {
  const container = document.getElementById('file-list');
  container.innerHTML = '';

  state.images.forEach((img, idx) => {
    const item = document.createElement('div');
    item.className = 'file-item';

    const dateDisplay = img.acquisition_date || 'Metadata unavailable';
    const dimensionsDisplay = (img.width && img.height) ? `${img.width}x${img.height} px` : 'Dimensions unavailable';

    item.innerHTML = `
      <img src="${img.url}" class="file-thumb" alt="Thumbnail">
      <div class="file-meta">
        <div class="file-name" title="${img.filename}">${img.filename}</div>
        <div class="file-details">${dimensionsDisplay} • ${img.modality || 'Optical'}</div>
        <span class="file-tag">${dateDisplay}</span>
      </div>
    `;
    container.appendChild(item);
  });
}

// Update Satellite Viewer Base & Secondary Images
function updateViewerImages() {
  const baseImg = document.getElementById('satellite-base-img');
  const secImg = document.getElementById('satellite-secondary-img');

  if (state.images.length > 0) {
    baseImg.src = state.images[0].url;
  }

  if (state.images.length > 1) {
    secImg.src = state.images[1].url;
  }

  redrawCanvasOverlay();
}

// Render Suggested Chips
function renderSuggestedChips(queries) {
  const chipsContainer = document.getElementById('suggested-chips');
  chipsContainer.innerHTML = '';

  queries.forEach(q => {
    const chip = document.createElement('button');
    chip.className = 'chip';
    chip.innerText = `• ${q}`;
    chip.onclick = () => {
      document.getElementById('query-textarea').value = q;
      executeAnalysis();
    };
    chipsContainer.appendChild(chip);
  });
}

// Handle Image File Upload
async function handleFileSelect(event) {
  const file = event.target.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch('/api/upload', {
      method: 'POST',
      body: formData
    });
    const meta = await res.json();

    if (!res.ok) {
      alert(meta.detail || 'Failed to upload image');
      return;
    }

    // Add to active images list
    if (state.inputMode === 'single_image') {
      state.images = [meta];
    } else {
      if (state.images.length >= 2) {
        state.images = [state.images[1], meta];
      } else {
        state.images.push(meta);
      }
    }

    renderFileList();
    updateViewerImages();
  } catch (err) {
    console.error('Error uploading file', err);
    alert('Failed to upload image');
  }
}

// Execute Analysis Pipeline
async function executeAnalysis() {
  const query = document.getElementById('query-textarea').value.trim();
  if (!query) {
    alert('Please enter a question or query for SatQuery AI.');
    return;
  }

  state.currentQuery = query;

  // Show processing sequence animation
  const trackerBox = document.getElementById('processing-tracker');
  const trackerSteps = document.getElementById('tracker-steps');
  const resultCard = document.getElementById('result-card');

  resultCard.style.display = 'none';
  trackerBox.style.display = 'flex';

  const stepsList = [
    "Understanding question...",
    "Checking uploaded imagery...",
    "Selecting analysis...",
    "Running model...",
    "Generating evidence...",
    "Preparing answer..."
  ];

  // Render initial pending steps
  trackerSteps.innerHTML = stepsList.map((step, idx) => `
    <div class="tracker-step" id="step-${idx}">
      <div class="step-icon">${idx+1}</div>
      <span>${step}</span>
    </div>
  `).join('');

  // Animate steps quickly
  for (let i = 0; i < stepsList.length; i++) {
    await new Promise(r => setTimeout(r, 120));
    const stepEl = document.getElementById(`step-${i}`);
    if (stepEl) {
      stepEl.classList.add('completed');
      stepEl.querySelector('.step-icon').innerHTML = '✓';
    }
  }

  // Call API Endpoint
  try {
    const res = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query: query,
        input_mode: state.inputMode,
        images: state.images
      })
    });

    const data = await res.json();
    if (data.error) {
      alert(data.message);
      trackerBox.style.display = 'none';
      return;
    }

    state.analysisResult = data;
    renderAnalysisResult(data);

    // Hide tracker after completion
    setTimeout(() => {
      trackerBox.style.display = 'none';
      resultCard.style.display = 'flex';
    }, 200);

  } catch (err) {
    console.error('Error executing analysis', err);
    alert('Analysis failed');
    trackerBox.style.display = 'none';
  }
}

// Render Analytical Results
function renderAnalysisResult(data) {
  document.getElementById('res-task').innerText = data.task;
  document.getElementById('res-confidence').innerText = `Model Confidence: ${Math.round(data.confidence * 100)}%`;
  document.getElementById('res-answer').innerText = data.answer;

  // Audit Summary Table
  const summary = data.execution_summary;
  document.getElementById('audit-task').innerText = summary.task;
  document.getElementById('audit-model').innerText = data.selected_model.name;
  
  const inputsStr = summary.inputs.map(i => `${i.label}: ${i.name} (${i.date})`).join(' | ');
  document.getElementById('audit-inputs').innerText = inputsStr;
  document.getElementById('audit-tools').innerText = summary.tools_used.join(', ');
  document.getElementById('audit-time').innerText = summary.audit_timestamp;

  // Redraw Canvas Visual Evidence
  redrawCanvasOverlay();
}

// Redraw HTML5 Canvas Overlay with Visual Evidence (Bounding boxes & masks)
function redrawCanvasOverlay() {
  const canvas = document.getElementById('overlay-canvas');
  const img = document.getElementById('satellite-base-img');

  if (!img.complete || img.naturalWidth === 0) return;

  canvas.width = img.clientWidth;
  canvas.height = img.clientHeight;

  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  if (!state.showOverlay || !state.analysisResult || !state.analysisResult.visual_evidence) {
    return;
  }

  const ev = state.analysisResult.visual_evidence;
  const scaleX = canvas.width / 800; // Normalized base width 800
  const scaleY = canvas.height / 600; // Normalized base height 600

  ctx.globalAlpha = state.maskOpacity;

  // Draw Bounding Boxes
  if (ev.boxes) {
    ev.boxes.forEach(box => {
      const bx = box.x * scaleX;
      const by = box.y * scaleY;
      const bw = box.w * scaleX;
      const bh = box.h * scaleY;
      const color = ev.color || ev.highlight_color || '#00F0FF';

      // Semi-transparent fill
      ctx.fillStyle = hexToRgba(color, 0.25);
      ctx.fillRect(bx, by, bw, bh);

      // Bright border
      ctx.strokeStyle = color;
      ctx.lineWidth = 2.5;
      ctx.setLineDash([6, 3]);
      ctx.strokeRect(bx, by, bw, bh);
      ctx.setLineDash([]);

      // Badge label
      if (box.label) {
        ctx.fillStyle = color;
        ctx.fillRect(bx, by - 22, ctx.measureText(box.label).width + 16, 20);
        ctx.fillStyle = '#000';
        ctx.font = 'bold 11px JetBrains Mono, monospace';
        ctx.fillText(box.label, bx + 8, by - 8);
      }
    });
  }

  // Draw Changed Regions (for Change Detection)
  if (ev.changed_regions) {
    ev.changed_regions.forEach(reg => {
      const box = reg.box;
      const bx = box.x * scaleX;
      const by = box.y * scaleY;
      const bw = box.w * scaleX;
      const bh = box.h * scaleY;

      ctx.fillStyle = hexToRgba(reg.color, 0.4);
      ctx.fillRect(bx, by, bw, bh);

      ctx.strokeStyle = reg.color;
      ctx.lineWidth = 3;
      ctx.strokeRect(bx, by, bw, bh);

      // Label
      ctx.fillStyle = reg.color;
      ctx.fillRect(bx, by - 22, ctx.measureText(reg.type).width + 16, 20);
      ctx.fillStyle = '#000';
      ctx.font = 'bold 10px JetBrains Mono, monospace';
      ctx.fillText(reg.type, bx + 8, by - 8);
    });
  }

  // Draw Features (for Optical-SAR)
  if (ev.features) {
    ev.features.forEach(feat => {
      const box = feat.box;
      const bx = box.x * scaleX;
      const by = box.y * scaleY;
      const bw = box.w * scaleX;
      const bh = box.h * scaleY;

      ctx.fillStyle = hexToRgba(feat.color, 0.35);
      ctx.fillRect(bx, by, bw, bh);

      ctx.strokeStyle = feat.color;
      ctx.lineWidth = 2.5;
      ctx.strokeRect(bx, by, bw, bh);

      ctx.fillStyle = feat.color;
      ctx.fillRect(bx, by - 22, ctx.measureText(feat.class).width + 14, 20);
      ctx.fillStyle = '#000';
      ctx.font = 'bold 10px JetBrains Mono, monospace';
      ctx.fillText(feat.class, bx + 6, by - 8);
    });
  }
}

// Convert Hex to RGBA
function hexToRgba(hex, alpha) {
  let c = hex.replace('#', '');
  if (c.length === 3) c = c.split('').map(x => x + x).join('');
  const num = parseInt(c, 16);
  return `rgba(${(num >> 16) & 255}, ${(num >> 8) & 255}, ${num & 255}, ${alpha})`;
}

// Viewer Controls
function zoomIn() {
  state.zoomLevel = Math.min(state.zoomLevel + 0.2, 3);
  applyZoom();
}

function zoomOut() {
  state.zoomLevel = Math.max(state.zoomLevel - 0.2, 0.6);
  applyZoom();
}

function resetZoom() {
  state.zoomLevel = 1;
  applyZoom();
}

function applyZoom() {
  const container = document.getElementById('canvas-container');
  container.style.transform = `scale(${state.zoomLevel})`;
  container.style.transformOrigin = 'center center';
}

function toggleOverlay() {
  state.showOverlay = !state.showOverlay;
  const btn = document.getElementById('btn-toggle-overlay');
  btn.classList.toggle('active', state.showOverlay);
  redrawCanvasOverlay();
}

function updateOverlayOpacity(val) {
  state.maskOpacity = val / 100;
  document.getElementById('opacity-val').innerText = `${val}%`;
  redrawCanvasOverlay();
}

function toggleSplitView() {
  state.showSplitView = !state.showSplitView;
  const overlay = document.getElementById('split-overlay');
  overlay.style.display = state.showSplitView ? 'block' : 'none';
  document.getElementById('btn-toggle-split').classList.toggle('active', state.showSplitView);
}

// Split Viewer Slider Drag
function initSplitDrag() {
  const overlay = document.getElementById('split-overlay');
  const viewport = document.getElementById('viewport');

  let isDragging = false;

  viewport.addEventListener('mousemove', (e) => {
    if (!state.showSplitView) return;
    const rect = viewport.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const pct = Math.max(0, Math.min(100, (x / rect.width) * 100));
    overlay.style.width = `${pct}%`;
  });
}

// Modal Handlers
function openModal(modalId) {
  document.getElementById(modalId).classList.add('active');
  if (modalId === 'modal-history') {
    loadHistoryModal();
  }
}

function closeModal(modalId) {
  document.getElementById(modalId).classList.remove('active');
}

// Load History Modal Data
async function loadHistoryModal() {
  const body = document.getElementById('history-modal-body');
  try {
    const res = await fetch('/api/history');
    const data = await res.json();
    if (!data.history || data.history.length === 0) {
      body.innerHTML = '<p style="color: var(--text-muted);">No analysis history logged in current session.</p>';
      return;
    }

    body.innerHTML = data.history.map(item => `
      <div style="background: var(--bg-card); border: 1px solid var(--border-color); padding: 14px; border-radius: 8px; font-size: 12px; margin-bottom: 10px;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px;">
          <strong style="color: var(--cyan); font-size: 13px;">${item.query}</strong>
          <span style="color: var(--emerald); font-family: var(--font-mono); font-weight: bold;">${Math.round(item.confidence * 100)}% Confidence</span>
        </div>
        <div style="color: var(--text-muted); font-size: 11px; margin-bottom: 8px;">
          Task: ${item.task} | Model: ${item.model_used} | ${item.timestamp}
        </div>
        <div style="color: var(--text-main); line-height: 1.4; margin-bottom: 10px;">${item.answer_summary}</div>
        <button type="button" onclick="downloadIntelligenceBriefPDF()" style="background: var(--amber, #f59e0b); color: #000; border: none; padding: 5px 12px; border-radius: 4px; font-weight: bold; font-size: 11px; cursor: pointer;">
          📄 EXPORT PDF BRIEF
        </button>
      </div>
    `).join('');
  } catch (err) {
    console.error('Failed to load history', err);
  }
}

// Render Models Modal Data
function renderModelsModal(models) {
  const body = document.getElementById('models-modal-body');
  body.innerHTML = models.map(m => `
    <div style="background: var(--bg-card); border: 1px solid var(--border-color); padding: 14px; border-radius: 8px;">
      <h4 style="color: var(--cyan); font-size: 14px; margin-bottom: 4px;">${m.name}</h4>
      <p style="color: var(--text-muted); font-size: 12px; margin-bottom: 8px;">${m.description}</p>
      <div style="display: flex; gap: 8px; font-family: var(--font-mono); font-size: 10px;">
        <span style="background: rgba(0, 255, 157, 0.15); color: var(--emerald); padding: 2px 6px; border-radius: 4px;">Supported Tasks: ${m.supported_tasks.join(', ')}</span>
        <span style="background: rgba(0, 240, 255, 0.15); color: var(--cyan); padding: 2px 6px; border-radius: 4px;">Inputs: ${m.supported_input_types.join(', ')}</span>
      </div>
    </div>
  `).join('');
}
