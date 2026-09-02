import type { Observation, AnalysisResult, QueryHistoryItem, ModalityType } from '../types/satquery';
import { DEMO_SCENARIOS } from '../data/demoScenarios';

// In-memory state for local user activity during session
let userObservations: Observation[] = [...DEMO_SCENARIOS[2].observations]; // Default to demo 03
let sessionHistory: QueryHistoryItem[] = [
  {
    id: 'hist-001',
    queryText: 'What changed between 2024 and 2026 observations?',
    observationsUsed: ['optical_urban_base_2024.tif', 'optical_urban_recent_2026.tif'],
    analysisType: 'Bi-Temporal Change Detection',
    timestamp: '01 SEP 2026 20:20 UTC',
    status: 'Complete',
    confidence: 87,
    resultSummary: 'Built-up area increased (+14.2%, +5.8 km²)',
    result: DEMO_SCENARIOS[2].presetResult
  },
  {
    id: 'hist-002',
    queryText: 'Find water body boundaries and calculate area',
    observationsUsed: ['multispectral_lake_res_2026.tif'],
    analysisType: 'NDWI Hydrological Surface Grounding',
    timestamp: '01 SEP 2026 19:40 UTC',
    status: 'Complete',
    confidence: 96,
    resultSummary: 'Water surface area: 412.6 km² detected',
    result: DEMO_SCENARIOS[1].presetResult
  }
];

export const satQueryService = {
  /**
   * Upload an observation image file
   */
  async uploadObservation(file: File, name?: string, modality: ModalityType = 'OPTICAL'): Promise<Observation> {
    return new Promise((resolve) => {
      setTimeout(() => {
        const objectUrl = URL.createObjectURL(file);
        const newObs: Observation = {
          id: `obs-user-${Date.now()}`,
          name: name || file.name.replace(/\.[^/.]+$/, ""),
          filename: file.name,
          modality: modality,
          date: new Date().toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }).toUpperCase(),
          dimensions: '3840 × 2160',
          status: 'READY',
          metadata: {
            sensor: `UserUpload-${modality.substring(0, 3)}`,
            lat: 22.5726 + (Math.random() * 0.05 - 0.025),
            lon: 88.3639 + (Math.random() * 0.05 - 0.025),
            cloudCover: '0.0%',
            bands: modality === 'SAR' ? 'VV Radar Backscatter' : 'RGB High-Res',
            fileSize: `${(file.size / (1024 * 1024)).toFixed(1)} MB`,
            groundSamplingDistance: '0.5m/px',
            acquisitionTime: new Date().toISOString().substring(11, 19) + ' UTC'
          },
          imageUrl: objectUrl,
          thumbnailUrl: objectUrl,
          isDemo: false
        };
        userObservations.unshift(newObs);
        resolve(newObs);
      }, 600);
    });
  },

  /**
   * Get active observations
   */
  async getObservations(): Promise<Observation[]> {
    return [...userObservations];
  },

  /**
   * Submit natural language query on satellite observations
   */
  async submitQuery(
    queryText: string,
    activeObservations: Observation[],
    onStepUpdate?: (stepIndex: number, label: string) => void
  ): Promise<AnalysisResult> {
    const steps = [
      "Understanding request",
      "Checking observations",
      "Determining analysis type",
      "Selecting specialist model",
      "Running analysis",
      "Generating evidence",
      "Preparing result"
    ];

    // Simulate real-time progress steps for human instrument UX
    for (let i = 0; i < steps.length; i++) {
      if (onStepUpdate) {
        onStepUpdate(i, steps[i]);
      }
      await new Promise(r => setTimeout(r, 450));
    }

    // Dynamic prompt intent parsing to select appropriate AI specialist model & evidence
    const queryLower = queryText.toLowerCase();
    const count = activeObservations.length;
    const isMultiDate = count >= 2;

    let matchedScenario = DEMO_SCENARIOS[0]; // Default VQA Optical

    if (queryLower.includes('water') || queryLower.includes('lake') || queryLower.includes('flood') || queryLower.includes('river') || queryLower.includes('ndwi') || queryLower.includes('hydro') || queryLower.includes('reservoir')) {
      matchedScenario = DEMO_SCENARIOS[1]; // Water Grounding / NDWI
    } else if (queryLower.includes('ship') || queryLower.includes('vessel') || queryLower.includes('sar') || queryLower.includes('radar') || queryLower.includes('port') || queryLower.includes('maritime') || queryLower.includes('sea')) {
      matchedScenario = DEMO_SCENARIOS[3]; // SAR Ship Detection / Maritime
    } else if (queryLower.includes('change') || queryLower.includes('growth') || queryLower.includes('compare') || queryLower.includes('urban') || queryLower.includes('building') || queryLower.includes('date') || isMultiDate) {
      matchedScenario = DEMO_SCENARIOS[2]; // Bi-temporal Change Detection
    } else if (queryLower.includes('vegetation') || queryLower.includes('forest') || queryLower.includes('crop') || queryLower.includes('ndvi') || queryLower.includes('greenery')) {
      matchedScenario = DEMO_SCENARIOS[1]; // Multispectral / Vegetation Index
    }

    // Synthesize result dynamically matching active query prompt
    const baseResult = matchedScenario.presetResult;
    
    // Customize headline and answer based on query text if custom user prompt
    let dynamicHeadline = baseResult.headline;
    let dynamicTask = baseResult.task;
    let dynamicAnswer = baseResult.answer;

    if (queryLower.includes('water')) {
      dynamicHeadline = "Water Body Surface Extent & Hydrological Boundary Mapped";
      dynamicTask = "Multispectral NDWI Water Grounding & Change Analysis";
      dynamicAnswer = `Analysis of water indices across selected observations identified key surface water boundaries. Spectral band processing confirms high moisture retention and active hydrological channels.`;
    } else if (queryLower.includes('ship') || queryLower.includes('vessel')) {
      dynamicHeadline = "Maritime Vessel Congestion & Polarized SAR Detection";
      dynamicTask = "SAR Cross-Modality Ship Grounding & Tracking";
      dynamicAnswer = `Dual-polarization SAR backscatter processing detected high-intensity metallic signatures corresponding to maritime vessels and port infrastructure.`;
    } else if (queryLower.includes('vegetation') || queryLower.includes('crop')) {
      dynamicHeadline = "NDVI Vegetation Density & Canopy Health Mapped";
      dynamicTask = "Multispectral Crop & Forest Health Index Analysis";
      dynamicAnswer = `Near-Infrared (NIR) to Red band ratio calculations indicate healthy canopy density across active agricultural plots with optimal photosynthetic absorption.`;
    }

    const customResult: AnalysisResult = {
      ...baseResult,
      id: `res-run-${Date.now()}`,
      queryText: queryText,
      task: dynamicTask,
      headline: dynamicHeadline,
      answer: dynamicAnswer,
      timestamp: new Date().toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }).toUpperCase() + ' ' + new Date().toISOString().substring(11, 16) + ' UTC',
      executionSummary: {
        ...baseResult.executionSummary,
        task: dynamicTask,
        inputs: activeObservations.map(o => o.filename),
        telemetryId: `SQ-TEL-${Date.now().toString().slice(-8)}`
      }
    };

    // Add to history
    const historyItem: QueryHistoryItem = {
      id: `hist-${Date.now()}`,
      queryText,
      observationsUsed: activeObservations.map(o => o.filename),
      analysisType: customResult.task,
      timestamp: customResult.timestamp,
      status: 'Complete',
      confidence: customResult.confidence,
      resultSummary: customResult.headline,
      result: customResult
    };
    sessionHistory.unshift(historyItem);

    return customResult;
  },

  /**
   * Retrieve query history
   */
  async getHistory(): Promise<QueryHistoryItem[]> {
    return [...sessionHistory];
  },

  /**
   * Get available model registry
   */
  async getModels(): Promise<{ name: string; type: string; accuracy: string; status: string }[]> {
    return [
      { name: 'SatQuery-VQA-v3.1', type: 'Visual Question Answering', accuracy: '94.2%', status: 'ONLINE' },
      { name: 'SatQuery-ChangeNet-v2', type: 'Bi-Temporal Change Detection', accuracy: '89.6%', status: 'ONLINE' },
      { name: 'SatQuery-Hydro-NDWI', type: 'Multispectral Water Grounding', accuracy: '96.8%', status: 'ONLINE' },
      { name: 'SatQuery-FusedSAR-v4', type: 'Optical-SAR Cross-Modality', accuracy: '91.4%', status: 'ONLINE' },
      { name: 'FeatureAlign-Siamese', type: 'Sub-Pixel Image Co-Registration', accuracy: '98.1%', status: 'ONLINE' }
    ];
  },

  /**
   * Search satellite data catalogue (CDSE Copernicus) via backend API
   */
  async searchSatelliteCatalogue(params: {
    provider?: string;
    bbox: number[];
    start_date: string;
    end_date: string;
    collection?: string;
    max_cloud_cover?: number;
    limit?: number;
  }): Promise<{ status: string; provider: string; count: number; products: any[] }> {
    const response = await fetch('/api/data-sources/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        provider: params.provider || 'copernicus',
        bbox: params.bbox,
        start_date: params.start_date,
        end_date: params.end_date,
        collection: params.collection || 'sentinel-2-l2a',
        max_cloud_cover: params.max_cloud_cover ?? null,
        limit: params.limit || 10,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `CDSE search failed with HTTP ${response.status}`);
    }

    return response.json();
  },

  /**
   * Get registered satellite data providers from backend
   */
  async getSatelliteProviders(): Promise<any[]> {
    const response = await fetch('/api/data-sources/providers');
    if (!response.ok) {
      throw new Error('Failed to fetch satellite providers');
    }
    const data = await response.json();
    return data.providers || [];
  }
};
