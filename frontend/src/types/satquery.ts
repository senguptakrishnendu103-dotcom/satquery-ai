/**
 * SatQuery Core Data Types
 * Scientific Remote-Sensing Analysis Platform
 *
 * Shared contract between:
 *   React frontend
 *   FastAPI backend
 *   CDSE data providers
 *   Agent orchestrator
 *   Specialist remote-sensing models
 */

// ============================================================
// BASIC TYPES
// ============================================================

export type ModalityType =
  | 'OPTICAL'
  | 'SAR'
  | 'MULTISPECTRAL'
  | 'THERMAL';

export type AnalysisStatus =
  | 'IDLE'
  | 'PROCESSING'
  | 'COMPLETE'
  | 'FAILED';

export type ActiveView =
  | 'LANDING'
  | 'WORKSPACE'
  | 'HISTORY';


// ============================================================
// OBSERVATION / DATA SOURCE TYPES
// ============================================================

export type ObservationSourceType =
  | 'upload'
  | 'copernicus'
  | 'demo'
  | 'sample'
  | 'local'
  | 'remote';

export type ObservationIngestionStatus =
  | 'pending'
  | 'catalogue_only'
  | 'metadata_only'
  | 'downloading'
  | 'downloaded'
  | 'ingested'
  | 'ready'
  | 'failed';


// ============================================================
// OBSERVATION METADATA
// ============================================================

export interface ObservationMetadata {
  // ----------------------------------------------------------
  // Existing UI metadata
  // ----------------------------------------------------------

  sensor?: string;

  lat?: number;

  lon?: number;

  cloudCover?: string;

  bands?: string;

  fileSize?: string;

  groundSamplingDistance?: string;

  acquisitionTime?: string;


  // ----------------------------------------------------------
  // Additional geospatial information
  // ----------------------------------------------------------

  crs?: string;

  coordinateSystem?: string;

  resolution?: number;

  spatialResolution?: number;

  bounds?: [
    number,
    number,
    number,
    number
  ];

  bbox?: [
    number,
    number,
    number,
    number
  ];

  geoFootprint?: GeoJsonGeometry;


  // ----------------------------------------------------------
  // Satellite/product information
  // ----------------------------------------------------------

  provider?: string;

  productId?: string;

  product_id?: string;

  satelliteId?: string;

  collection?: string;

  processingLevel?: string;

  platform?: string;

  instrument?: string;


  // ----------------------------------------------------------
  // Acquisition information
  // ----------------------------------------------------------

  acquisitionDate?: string | null;

  acquisition_date?: string | null;


  // ----------------------------------------------------------
  // Ingestion state
  // ----------------------------------------------------------

  sourceType?: ObservationSourceType;

  source_type?: ObservationSourceType;

  ingestionStatus?: ObservationIngestionStatus;

  ingestion_status?: ObservationIngestionStatus;


  // ----------------------------------------------------------
  // Provider/model metadata
  // ----------------------------------------------------------

  productMetadata?: Record<string, unknown>;

  product_metadata?: Record<string, unknown>;

  attributes?: Record<string, unknown>;

  assets?: Record<string, unknown>;


  // ----------------------------------------------------------
  // Preserve provider-specific metadata
  // ----------------------------------------------------------

  [key: string]: unknown;
}


// ============================================================
// OBSERVATION
// ============================================================

export interface Observation {
  // ----------------------------------------------------------
  // Existing frontend identity
  // ----------------------------------------------------------

  id: string;

  name: string;

  filename: string;

  modality: ModalityType;

  date: string;

  dimensions: string;


  // ----------------------------------------------------------
  // Frontend status
  // ----------------------------------------------------------

  status:
  | 'READY'
  | 'INGESTING'
  | 'VALIDATING'
  | 'FAILED';


  // ----------------------------------------------------------
  // Display metadata
  // ----------------------------------------------------------

  metadata: ObservationMetadata;


  // ----------------------------------------------------------
  // Browser/display image
  //
  // This can be:
  //   - local/static preview
  //   - CDSE quicklook
  //   - generated preview
  //
  // It is NOT necessarily the model input.
  // ----------------------------------------------------------

  imageUrl: string;

  thumbnailUrl: string;


  // ----------------------------------------------------------
  // Demo marker
  // ----------------------------------------------------------

  isDemo?: boolean;


  // ==========================================================
  // BACKEND INGESTION CONTRACT
  // ==========================================================

  /**
   * Absolute/local backend file path when the observation
   * has been downloaded or uploaded to the backend.
   *
   * This is the path used by the model pipeline.
   */
  filePath?: string;

  file_path?: string;


  /**
   * Alias used by the backend orchestrator/model adapters.
   */
  localPath?: string;

  local_path?: string;


  // ==========================================================
  // DATA SOURCE CONTRACT
  // ==========================================================

  sourceType?: ObservationSourceType;

  source_type?: ObservationSourceType;


  ingestionStatus?: ObservationIngestionStatus;

  ingestion_status?: ObservationIngestionStatus;


  // ==========================================================
  // CDSE / PROVIDER INFORMATION
  // ==========================================================

  provider?: string;

  productId?: string;

  product_id?: string;

  collection?: string;

  processingLevel?: string;

  platform?: string;

  instrument?: string;

  satelliteId?: string;


  // ==========================================================
  // REAL ACQUISITION DATE
  // ==========================================================

  acquisitionDate?: string | null;

  acquisition_date?: string | null;


  // ==========================================================
  // OPTIONAL PRODUCT METADATA
  // ==========================================================

  productMetadata?: Record<string, unknown>;

  product_metadata?: Record<string, unknown>;


  /**
   * Provider-generated asset information, e.g.
   *
   * {
   *   quicklook: {...},
   *   download: {...}
   * }
   */
  assets?: Record<string, unknown>;


  /**
   * Provider-neutral bounding box.
   */
  bbox?: [
    number,
    number,
    number,
    number
  ];


  /**
   * Provider-neutral CRS.
   */
  crs?: string;


  /**
   * Optional raw/provider payload.
   */
  rawMetadata?: Record<string, unknown>;
}


// ============================================================
// GEOJSON
// ============================================================

export interface GeoJsonGeometry {
  type:
  | 'Point'
  | 'LineString'
  | 'Polygon'
  | 'MultiPoint'
  | 'MultiLineString'
  | 'MultiPolygon';

  coordinates: any;
}


export interface GeoJsonFeature {
  type: 'Feature';

  geometry: GeoJsonGeometry;

  properties?: Record<
    string,
    unknown
  >;
}


// ============================================================
// EVIDENCE
// ============================================================

export interface EvidenceMetric {
  label: string;

  value: string;
}


export interface EvidenceRegion {
  id: string;

  label: string;


  /**
   * Percentage-based image bounding box fallback.
   *
   * x, y, width, height are expressed relative to the
   * displayed observation image.
   */
  coords: {
    x: number;
    y: number;
    width: number;
    height: number;
  };


  /**
   * Real geospatial geometry when supplied by the backend.
   */
  geoJsonGeometry?: GeoJsonGeometry;


  /**
   * Geographic center:
   *
   * [longitude, latitude]
   */
  centerCoordinates?: [
    number,
    number
  ];


  /**
   * Optional pixel-space bounding box supplied directly
   * by a model.
   */
  pixelBbox?: {
    x: number;
    y: number;
    width: number;
    height: number;
  };


  /**
   * Optional geographic bounding box.
   */
  geoBbox?: [
    number,
    number,
    number,
    number
  ];


  areaEstimate?: string;

  confidence: number;


  type:
  | 'change'
  | 'water'
  | 'built_up'
  | 'vegetation'
  | 'detection'
  | 'anomaly';


  description: string;

  metrics?: EvidenceMetric[];


  /**
   * Optional raw evidence generated by the specialist.
   */
  raw?: Record<string, unknown>;
}


// ============================================================
// EXECUTION
// ============================================================

export type ExecutionStepStatus =
  | 'pending'
  | 'running'
  | 'complete'
  | 'failed';


export interface ExecutionStep {
  phase: string;

  label: string;

  timestamp: string;

  details: string;

  status: ExecutionStepStatus;
}


export interface ReplayStep {
  phase: string;

  label: string;

  timestamp: string;

  details: string;

  status:
  | 'pending'
  | 'running'
  | 'complete'
  | 'failed'
  | string;
}


// ============================================================
// AUDIT INPUT
// ============================================================

/**
 * Structured input information returned by the backend
 * ExecutionTracker.
 *
 * This replaces the old string-only assumption while
 * remaining backwards compatible with frontend components.
 */
export interface ExecutionInput {
  index?: number;

  label?: string;

  name?: string;

  filename?: string;

  date?: string | null;

  acquisition_date?: string | null;

  modality?: string;

  sensor?: string;

  provider?: string;

  product_id?: string;

  productId?: string;

  source_type?: string;

  sourceType?: string;

  ingestion_status?: string;

  ingestionStatus?: string;

  dimensions?: {
    width?: number;

    height?: number;
  };

  file_path?: string;

  local_path?: string;

  [key: string]: unknown;
}


// ============================================================
// EXECUTION SUMMARY
// ============================================================

export interface ExecutionSummary {
  task: string;


  /**
   * Backend may return:
   *
   * ExecutionInput[]
   *
   * Older results may contain:
   *
   * string[]
   *
   * Keeping both makes the frontend backwards compatible.
   */
  inputs: Array<
    string | ExecutionInput
  >;


  modelsUsed: string[];

  toolsExecuted: string[];


  executionTimeMs?: number;


  telemetryId?: string;

  modelVersion?: string;

  datasetVersion?: string;


  // ----------------------------------------------------------
  // Optional audit information
  // ----------------------------------------------------------

  executionStatus?: string;

  inputMode?: string;

  modelInputType?: string;

  numImages?: number;

  modalities?: string[];

  executionTimeSeconds?: number;

  evidenceCount?: number;


  /**
   * Concise routing explanation intended for auditability.
   *
   * This is NOT hidden model reasoning.
   */
  routingReason?: string;


  /**
   * Backend confidence of task classification.
   */
  taskConfidence?: number;


  /**
   * Optional parameter configuration.
   */
  parameters?: Record<
    string,
    unknown
  >;


  /**
   * Optional tool list using backend naming.
   */
  tools?: string[];


  /**
   * Optional change-analysis information.
   */
  changeStatistics?: Record<
    string,
    unknown
  >;


  /**
   * Optional compute indicator.
   */
  computeCostUnits?: string;


  /**
   * Backend audit timestamp.
   */
  auditTimestamp?: string;


  /**
   * Preserve additional backend audit fields without
   * forcing all provider/model implementations to have
   * exactly the same output.
   */
  [key: string]: unknown;
}


// ============================================================
// ANALYSIS RESULT
// ============================================================

export interface AnalysisResult {
  id: string;

  queryText: string;

  task: string;

  models: string[];


  status:
  | 'COMPLETE'
  | 'PROCESSING'
  | 'FAILED';


  confidence: number;

  headline: string;

  answer: string;


  /**
   * Only populated when the backend actually reports
   * a change percentage.
   */
  changePercentage?: string;


  overlayType?:
  | 'change'
  | 'ndwi'
  | 'sar_fusion'
  | 'detection';


  evidence: EvidenceRegion[];


  executionSummary: ExecutionSummary;


  replaySteps: ReplayStep[];


  followUpActions: string[];


  timestamp: string;
}


// ============================================================
// QUERY HISTORY
// ============================================================

export interface QueryHistoryItem {
  id: string;

  queryText: string;

  observationsUsed: string[];

  analysisType: string;

  timestamp: string;

  status: string;

  confidence: number;

  resultSummary: string;

  result: AnalysisResult;
}


// ============================================================
// DEMO
// ============================================================

export interface DemoScenario {
  id: string;

  title: string;

  badge: string;

  description: string;

  observations: Observation[];

  sampleQueries: string[];

  presetResult: AnalysisResult;
}


// ============================================================
// MAP
// ============================================================

export interface MapLayerConfig {
  id: string;

  name: string;

  visible: boolean;

  color: string;

  count?: number;
}