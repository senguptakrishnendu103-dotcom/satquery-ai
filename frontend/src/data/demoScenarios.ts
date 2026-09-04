import type { DemoScenario } from '../types/satquery';

export const DEMO_SCENARIOS: DemoScenario[] = [
  {
    id: 'demo-01',
    title: 'Single-Image Optical Grounding & VQA',
    badge: 'DEMO 01',
    description: 'High-resolution optical observation analysis over Port infrastructure and vessel localization.',
    observations: [
      {
        id: 'obs-dem-101',
        name: 'Palma Port Optical Observation',
        filename: 'optical_palma_0.3m_2026.tif',
        modality: 'OPTICAL',
        date: '14 AUG 2026',
        dimensions: '4096 × 4096',
        status: 'READY',
        metadata: {
          sensor: 'SatQuery-Opt-1A',
          lat: 39.5696,
          lon: 2.6502,
          cloudCover: '0.0%',
          bands: 'RGB (Red, Green, Blue)',
          fileSize: '48.2 MB',
          groundSamplingDistance: '0.3m/px',
          acquisitionTime: '10:42:18 UTC'
        },
        imageUrl: 'https://images.unsplash.com/photo-1541872703-74c5e44368f9?auto=format&fit=crop&w=1600&q=80',
        thumbnailUrl: 'https://images.unsplash.com/photo-1541872703-74c5e44368f9?auto=format&fit=crop&w=300&q=80',
        isDemo: true,
      }
    ],
    sampleQueries: [
      'Describe this observation and primary infrastructure',
      'Identify major maritime cargo vessels docked at the pier',
      'Detect water body boundaries and shoreline stability',
      'Calculate land-to-water coverage ratio'
    ],
    presetResult: {
      id: 'res-dem-101',
      queryText: 'Identify major maritime cargo vessels docked at the pier',
      task: 'Optical Visual Grounding & Feature Localization',
      models: ['SatQuery-VQA-v3.1', 'ResNet-GeoDetect-X'],
      status: 'COMPLETE',
      confidence: 94,
      headline: '4 Commercial Maritime Cargo Vessels Grounded',
      answer: 'Analysis identified 4 commercial cargo container vessels docked along Pier 4 and Pier 7. Total harbor activity is operating at normal capacity with clear navigational channels.',
      evidence: [
        {
          id: 'reg-101',
          label: 'Vessel ALPHA-01 (Cargo)',
          coords: { x: 28, y: 34, width: 14, height: 18 },
          areaEstimate: '185m length',
          confidence: 96,
          type: 'detection',
          description: 'Container carrier moored at North Quay. Draft alignment indicates active unloading.',
          metrics: [
            { label: 'Length', value: '185 meters' },
            { label: 'Beam', value: '32 meters' },
            { label: 'Orientation', value: '042° NE' }
          ]
        },
        {
          id: 'reg-102',
          label: 'Vessel BRAVO-02 (Tanker)',
          coords: { x: 55, y: 48, width: 16, height: 20 },
          areaEstimate: '210m length',
          confidence: 94,
          type: 'detection',
          description: 'Liquid bulk tanker grounded at Deepwater Terminal 2.',
          metrics: [
            { label: 'Length', value: '210 meters' },
            { label: 'Type', value: 'Petrochemical Tanker' }
          ]
        },
        {
          id: 'reg-103',
          label: 'Pier 7 Logistics Zone',
          coords: { x: 40, y: 22, width: 22, height: 25 },
          areaEstimate: '0.45 km²',
          confidence: 92,
          type: 'detection',
          description: 'High-density container storage yard with automated gantry cranes.',
          metrics: [
            { label: 'Stack Density', value: '82%' },
            { label: 'Occupancy', value: 'High' }
          ]
        }
      ],
      executionSummary: {
        task: 'Optical Visual Grounding',
        inputs: ['optical_palma_0.3m_2026.tif'],
        modelsUsed: ['SatQuery-VQA-v3.1', 'ResNet-GeoDetect-X'],
        toolsExecuted: ['ImagePreprocessor', 'BoundingBoxGrounder', 'ConfidenceScorer'],
        executionTimeMs: 1420,
        telemetryId: 'SQ-TEL-20260901-0081',
        modelVersion: 'v3.1.0-prod',
        datasetVersion: 'Sentinel2-Opt-2026.4',
        computeCostUnits: '0.041 GPU-hrs'
      },
      replaySteps: [
        { phase: 'INPUTS', label: 'Observation Ingestion', timestamp: '00:00.120', details: 'Ingested 1 optical observation (4096×4096px, 0.3m/px RGB).', status: 'complete' },
        { phase: 'QUERY', label: 'Query Parsing', timestamp: '00:00.310', details: 'Parsed intent: Maritime Vessel Grounding & Spatial Localization.', status: 'complete' },
        { phase: 'TASK IDENTIFICATION', label: 'Pipeline Selection', timestamp: '00:00.450', details: 'Routed to Optical Grounding & Zero-Shot Detector.', status: 'complete' },
        { phase: 'MODEL SELECTION', label: 'Model Load', timestamp: '00:00.680', details: 'Instantiated SatQuery-VQA-v3.1 with 0.3m spatial resolution adapter.', status: 'complete' },
        { phase: 'ANALYSIS', label: 'Convolutional Inference', timestamp: '00:01.020', details: 'Scanned 16.7M pixels across 3 spectral channels.', status: 'complete' },
        { phase: 'EVIDENCE', label: 'Bounding Box Bbox Synthesis', timestamp: '00:01.280', details: 'Synthesized 3 inspectable geospatial regions with high confidence.', status: 'complete' },
        { phase: 'RESULT', label: 'Audit Log Finalized', timestamp: '00:01.420', details: 'Analysis ready for operator verification.', status: 'complete' }
      ],
      followUpActions: [
        'Measure vessel lengths and berths',
        'Compare port container density with 2024 archive',
        'Check SAR radar imagery for night-time vessel positions'
      ],
      timestamp: '01 SEP 2026 20:14 UTC'
    }
  },
  {
    id: 'demo-02',
    title: 'Water Body Grounding & Hydrological Volume',
    badge: 'DEMO 02',
    description: 'Multispectral analysis of lake shoreline contraction and surface water surface area tracking.',
    observations: [
      {
        id: 'obs-dem-201',
        name: 'Lake Reservoir Multispectral Observation',
        filename: 'multispectral_lake_res_2026.tif',
        modality: 'MULTISPECTRAL',
        date: '02 AUG 2026',
        dimensions: '2048 × 2048',
        status: 'READY',
        metadata: {
          sensor: 'Sentinel-2B MSI',
          lat: 36.1424,
          lon: -114.7377,
          cloudCover: '0.1%',
          bands: 'RGB + NIR (B4, B3, B2, B8)',
          fileSize: '62.8 MB',
          groundSamplingDistance: '10m/px',
          acquisitionTime: '18:12:04 UTC'
        },
        imageUrl: 'https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=1600&q=80',
        thumbnailUrl: 'https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=300&q=80',
        isDemo: true,
      }
    ],
    sampleQueries: [
      'Find the water body and measure current surface area',
      'Detect shoreline recession and exposed bathymetry',
      'Analyze vegetation health index along reservoir perimeter',
      'Compare current water volume against baseline capacity'
    ],
    presetResult: {
      id: 'res-dem-202',
      queryText: 'Find the water body and measure current surface area',
      task: 'WATER_DETECTION',
      models: ['Hydro-NDWI Water Segmentation Tool'],
      status: 'COMPLETE',
      confidence: 95,
      headline: 'NDWI Water Segmentation',
      answer: 'NDWI water extraction completed using Green (B03) and NIR (B08) spectral channels.',
      evidence: [],
      executionSummary: {
        task: 'WATER_DETECTION',
        inputs: ['multispectral_lake_res_2026.tif'],
        modelsUsed: ['Hydro-NDWI Water Segmentation Tool'],
        toolsExecuted: ['BandMathNDWI'],
        executionTimeMs: 1180,
        telemetryId: 'SQ-TEL-DEMO-02',
        modelVersion: 'deterministic-raster-v1',
        datasetVersion: 'v1.0'
      },
      replaySteps: [
        { phase: 'INPUTS', label: 'Multispectral Channel Extraction', timestamp: '00:00.080', details: 'Extracted Near-Infrared (B8) and Green (B3) spectral bands.', status: 'complete' },
        { phase: 'QUERY', label: 'Hydrological Intent Filter', timestamp: '00:00.220', details: 'Targeted NDWI calculation formula: (Green - NIR) / (Green + NIR).', status: 'complete' },
        { phase: 'TASK IDENTIFICATION', label: 'Water Index Computation', timestamp: '00:00.410', details: 'Calculated continuous NDWI grid matrix.', status: 'complete' },
        { phase: 'MODEL SELECTION', label: 'Segmentation Thresholding', timestamp: '00:00.710', details: 'Applied Otsu thresholding (T = +0.22) for water contour vectorization.', status: 'complete' },
        { phase: 'ANALYSIS', label: 'Geospatial Area Calculation', timestamp: '00:00.950', details: 'Integrated cell areas accounting for WGS84 geodesic curvature.', status: 'complete' },
        { phase: 'EVIDENCE', label: 'Vector Polygons Generated', timestamp: '00:01.090', details: 'Rendered water perimeter and shallow bathymetric zones.', status: 'complete' },
        { phase: 'RESULT', label: 'Telemetry Verified', timestamp: '00:01.180', details: 'Hydrological report generated.', status: 'complete' }
      ],
      followUpActions: [
        'Compare with 2024 dry season observation',
        'Analyze surrounding agricultural water consumption',
        'Export vector GeoJSON of water boundary'
      ],
      timestamp: '01 SEP 2026 19:40 UTC'
    }
  },
  {
    id: 'demo-03',
    title: 'Bi-Temporal Change Detection (2024 vs 2026)',
    badge: 'DEMO 03',
    description: 'Multi-date optical observation comparison evaluating urban expansion and built-up land modification.',
    observations: [
      {
        id: 'obs-dem-301',
        name: 'Coastal Urban Baseline',
        filename: 'optical_urban_base_2024.tif',
        modality: 'OPTICAL',
        date: '14 AUG 2024',
        dimensions: '4096 × 4096',
        status: 'READY',
        metadata: {
          sensor: 'SatQuery-Opt-1A',
          lat: 25.2048,
          lon: 55.2708,
          cloudCover: '0.0%',
          bands: 'RGB',
          fileSize: '45.1 MB',
          groundSamplingDistance: '0.5m/px',
          acquisitionTime: '09:15:22 UTC'
        },
        imageUrl: 'https://images.unsplash.com/photo-1512453979798-5ea266f8880c?auto=format&fit=crop&w=1600&q=80',
        thumbnailUrl: 'https://images.unsplash.com/photo-1512453979798-5ea266f8880c?auto=format&fit=crop&w=300&q=80',
        isDemo: true,
      },
      {
        id: 'obs-dem-302',
        name: 'Coastal Urban Recent Observation',
        filename: 'optical_urban_recent_2026.tif',
        modality: 'OPTICAL',
        date: '14 AUG 2026',
        dimensions: '4096 × 4096',
        status: 'READY',
        metadata: {
          sensor: 'SatQuery-Opt-1B',
          lat: 25.2048,
          lon: 55.2708,
          cloudCover: '0.0%',
          bands: 'RGB',
          fileSize: '46.8 MB',
          groundSamplingDistance: '0.5m/px',
          acquisitionTime: '09:30:10 UTC'
        },
        imageUrl: 'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1600&q=80',
        thumbnailUrl: 'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=300&q=80',
        isDemo: true,
      }
    ],
    sampleQueries: [
      'What changed between these observations?',
      'Has the built-up area increased between 2024 and 2026?',
      'Locate new road infrastructure developments',
      'Measure coastal land reclamation growth rate'
    ],
    presetResult: {
      id: 'res-dem-303',
      queryText: 'What changed between these observations?',
      task: 'Bi-Temporal Change Detection & Urban Growth Analysis',
      models: ['SatQuery-ChangeNet-v2', 'FeatureAlign-Siamese'],
      status: 'COMPLETE',
      confidence: 87,
      headline: 'Built-Up Area Increased (+14.2%)',
      answer: 'Bi-temporal Siamese feature comparison detected significant urban land expansion between 14 AUG 2024 and 14 AUG 2026. A net increase of +14.2% (+5.8 km²) in built-up footprint was measured, driven primarily by commercial district construction.',
      changePercentage: '+14.2%',
      overlayType: 'change',
      evidence: [
        {
          id: 'reg-301',
          label: 'Commercial Tower Complex (New)',
          coords: { x: 30, y: 25, width: 20, height: 25 },
          areaEstimate: '+2.8 km²',
          confidence: 93,
          type: 'change',
          description: 'Newly constructed high-rise foundations and paved plaza replacing open sand lot.',
          metrics: [
            { label: '2024 Status', value: 'Unpaved Sand' },
            { label: '2026 Status', value: 'Built-Up Structure' },
            { label: 'Confidence', value: '93%' }
          ]
        },
        {
          id: 'reg-302',
          label: 'Northern Highway Extension',
          coords: { x: 62, y: 15, width: 28, height: 18 },
          areaEstimate: '+1.6 km²',
          confidence: 89,
          type: 'change',
          description: 'Six-lane arterial highway link completed connecting north sector.',
          metrics: [
            { label: 'Length', value: '4.2 km' },
            { label: 'Surface', value: 'Asphalt Concrete' }
          ]
        },
        {
          id: 'reg-303',
          label: 'Maritime Basin Reclamation',
          coords: { x: 15, y: 60, width: 25, height: 22 },
          areaEstimate: '+1.4 km²',
          confidence: 88,
          type: 'change',
          description: 'Coastal infill and seawall stabilization along southern marina extension.',
          metrics: [
            { label: 'Reclaimed Land', value: '1.4 km²' }
          ]
        }
      ],
      executionSummary: {
        task: 'Bi-Temporal Siamese Change Analysis',
        inputs: ['optical_urban_base_2024.tif', 'optical_urban_recent_2026.tif'],
        modelsUsed: ['SatQuery-ChangeNet-v2', 'FeatureAlign-Siamese'],
        toolsExecuted: ['SubPixelRegistrator', 'DeepDifferenceMap', 'ThresholdFilter'],
        executionTimeMs: 2310,
        telemetryId: 'SQ-TEL-20260901-0112',
        modelVersion: 'v2.2.0-change',
        datasetVersion: 'SatQuery-Change-V2'
      },
      replaySteps: [
        { phase: 'INPUTS', label: 'Bi-Temporal Ingestion', timestamp: '00:00.100', details: 'Ingested 2024 Optical (Base) and 2026 Optical (Target).', status: 'complete' },
        { phase: 'QUERY', label: 'Temporal Intent Extractor', timestamp: '00:00.280', details: 'Detected query requirement: Bi-temporal land cover difference map.', status: 'complete' },
        { phase: 'TASK IDENTIFICATION', label: 'Geometric Co-Registration', timestamp: '00:00.560', details: 'Sub-pixel image alignment executed (RMSE < 0.12 px).', status: 'complete' },
        { phase: 'MODEL SELECTION', label: 'Siamese Network Load', timestamp: '00:00.920', details: 'Loaded SatQuery-ChangeNet-v2 encoder pairs.', status: 'complete' },
        { phase: 'ANALYSIS', label: 'Difference Feature Extraction', timestamp: '00:01.650', details: 'Generated high-level feature delta maps across 5 spatial scales.', status: 'complete' },
        { phase: 'EVIDENCE', label: 'Cluster Segmentation', timestamp: '00:02.100', details: 'Clustered changed pixels into 3 primary inspectable land regions.', status: 'complete' },
        { phase: 'RESULT', label: 'Change Metric Calculation', timestamp: '00:02.310', details: 'Total change quantified at +14.2% (+5.8 km²).', status: 'complete' }
      ],
      followUpActions: [
        'SHOW WHERE (Highlight changed regions on map)',
        'MEASURE CHANGE (Detailed area breakdown)',
        'COMPARE WITH VEGETATION (Check loss of green space)',
        'ANALYZE ANOTHER DATE (Query 2020 archive)'
      ],
      timestamp: '01 SEP 2026 20:20 UTC'
    }
  },
  {
    id: 'demo-04',
    title: 'Optical + SAR Radar Sensor Fusion',
    badge: 'DEMO 04',
    description: 'Combining optical satellite imagery with Synthetic Aperture Radar (SAR) backscatter for cloud-penetrating flood response.',
    observations: [
      {
        id: 'obs-dem-401',
        name: 'Pre-Event Sentinel-2 Optical',
        filename: 'sentinel2_optical_pre_2026.tif',
        modality: 'OPTICAL',
        date: '10 AUG 2026',
        dimensions: '2048 × 2048',
        status: 'READY',
        metadata: {
          sensor: 'Sentinel-2A MSI',
          lat: 50.9375,
          lon: 6.9603,
          cloudCover: '12.4%',
          bands: 'RGB + NIR',
          fileSize: '54.0 MB',
          groundSamplingDistance: '10m/px',
          acquisitionTime: '11:05:00 UTC'
        },
        imageUrl: 'https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=1600&q=80',
        thumbnailUrl: 'https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=300&q=80',
        isDemo: true,
      },
      {
        id: 'obs-dem-402',
        name: 'Post-Event Sentinel-1 SAR Radar',
        filename: 'sentinel1_sar_vv_vh_2026.tif',
        modality: 'SAR',
        date: '14 AUG 2026',
        dimensions: '2048 × 2048',
        status: 'READY',
        metadata: {
          sensor: 'Sentinel-1B C-Band SAR',
          lat: 50.9375,
          lon: 6.9603,
          cloudCover: '0.0% (Radar)',
          bands: 'VV + VH Polarization Backscatter',
          fileSize: '38.5 MB',
          groundSamplingDistance: '10m/px',
          acquisitionTime: '05:40:12 UTC'
        },
        imageUrl: 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=1600&q=80',
        thumbnailUrl: 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=300&q=80',
        isDemo: true,
      }
    ],
    sampleQueries: [
      'Use optical and SAR observations together to detect flooded areas',
      'Compare optical and SAR information through heavy cloud cover',
      'Identify built-up regions impacted by standing water',
      'Map radar backscatter anomalies along river corridor'
    ],
    presetResult: {
      id: 'res-dem-404',
      queryText: 'Use the optical and SAR observations together to detect flooded areas',
      task: 'Optical-SAR Cross-Modality Sensor Fusion & Inundation Grounding',
      models: ['SatQuery-FusedSAR-v4', 'RadarBackscatterNet'],
      status: 'COMPLETE',
      confidence: 91,
      headline: 'Inundation Detected Across 18.4 km² via SAR Fusion',
      answer: 'Synthetic Aperture Radar (SAR) specular reflection analysis bypassed 85% cloud coverage present in the post-event optical pass. Cross-registering Sentinel-1 VV backscatter with pre-event optical baselines delineated 18.4 km² of inundated agricultural land and 2 critical roadway cutoffs.',
      overlayType: 'sar_fusion',
      evidence: [
        {
          id: 'reg-401',
          label: 'Primary River Inundation Plain',
          coords: { x: 22, y: 35, width: 45, height: 40 },
          areaEstimate: '14.2 km²',
          confidence: 95,
          type: 'water',
          description: 'Low SAR backscatter coefficient (-22dB) indicates smooth standing water surface.',
          metrics: [
            { label: 'SAR Backscatter', value: '-22.4 dB (Specular)' },
            { label: 'Cloud Obscuration', value: '0% (Radar Penetrated)' }
          ]
        },
        {
          id: 'reg-402',
          label: 'Submerged Highway Access Ramp',
          coords: { x: 70, y: 20, width: 18, height: 22 },
          areaEstimate: '4.2 km²',
          confidence: 88,
          type: 'anomaly',
          description: 'Transport corridor flooded. Double-bounce radar signature muted by water immersion.',
          metrics: [
            { label: 'Infrastructure', value: 'Submerged' }
          ]
        }
      ],
      executionSummary: {
        task: 'Optical-SAR Cross-Modality Fusion',
        inputs: ['sentinel2_optical_pre_2026.tif', 'sentinel1_sar_vv_vh_2026.tif'],
        modelsUsed: ['SatQuery-FusedSAR-v4', 'RadarBackscatterNet'],
        toolsExecuted: ['SARLeeFilter', 'SpecularReflectorDetect', 'CrossModalityRegister'],
        executionTimeMs: 1890,
        telemetryId: 'SQ-TEL-20260901-0155',
        modelVersion: 'v4.0.2-fusion',
        datasetVersion: 'Sentinel1/2-Fused-2026'
      },
      replaySteps: [
        { phase: 'INPUTS', label: 'Dual-Modality Ingestion', timestamp: '00:00.110', details: 'Ingested Optical RGB-NIR + C-Band Dual-Pol SAR (VV/VH).', status: 'complete' },
        { phase: 'QUERY', label: 'Cloud-Bypass Intent Parsing', timestamp: '00:00.290', details: 'Selected SAR backscatter priority due to optical cloud mask.', status: 'complete' },
        { phase: 'TASK IDENTIFICATION', label: 'Speckle Filtering & Calibration', timestamp: '00:00.580', details: 'Applied 5x5 Refined Lee filter to SAR amplitude matrix.', status: 'complete' },
        { phase: 'MODEL SELECTION', label: 'Cross-Attention Model Load', timestamp: '00:00.890', details: 'Loaded SatQuery-FusedSAR-v4 cross-modality transformer.', status: 'complete' },
        { phase: 'ANALYSIS', label: 'Specular Reflection Analysis', timestamp: '00:01.380', details: 'Identified low-backscatter water polygons (< -18dB).', status: 'complete' },
        { phase: 'EVIDENCE', label: 'Inundation Mask Overlay', timestamp: '00:01.690', details: 'Combined SAR water mask with pre-event optical land classification.', status: 'complete' },
        { phase: 'RESULT', label: 'Fusion Report Complete', timestamp: '00:01.890', details: 'Mapped 18.4 km² flooded footprint.', status: 'complete' }
      ],
      followUpActions: [
        'Export high-resolution evacuation zone mask',
        'Compare SAR backscatter with historical dry baseline',
        'Generate damage assessment report'
      ],
      timestamp: '01 SEP 2026 20:21 UTC'
    }
  }
];
