/**
 * SatQuery Core Data Types
 * Scientific Remote-Sensing Analysis Platform
 */

export type ModalityType = 'OPTICAL' | 'SAR' | 'MULTISPECTRAL' | 'THERMAL';
export type AnalysisStatus = 'IDLE' | 'PROCESSING' | 'COMPLETE' | 'FAILED';
export type ActiveView = 'LANDING' | 'WORKSPACE' | 'HISTORY';

export interface ObservationMetadata {
  sensor?: string;
  lat?: number;
  lon?: number;
  cloudCover?: string;
  bands?: string;
  fileSize?: string;
  groundSamplingDistance?: string;
  acquisitionTime?: string;
}

export interface Observation {
  id: string;
  name: string;
  filename: string;
  modality: ModalityType;
  date: string;
  dimensions: string;
  status: 'READY' | 'INGESTING' | 'VALIDATING' | 'FAILED';
  metadata: ObservationMetadata;
  imageUrl: string;
  thumbnailUrl: string;
  isDemo?: boolean;
}

/**
 * GeoJSON Compatible Evidence Format
 */
export interface GeoJsonGeometry {
  type: 'Polygon' | 'MultiPolygon' | 'Point';
  coordinates: any;
}

export interface EvidenceRegion {
  id: string;
  label: string;
  coords: { x: number; y: number; width: number; height: number }; // Bounding box % fallback
  geoJsonGeometry?: GeoJsonGeometry; // Real GeoJSON feature geometry
  centerCoordinates?: [number, number]; // [lon, lat]
  areaEstimate: string;
  confidence: number;
  type: 'change' | 'water' | 'built_up' | 'vegetation' | 'detection' | 'anomaly';
  description: string;
  metrics?: { label: string; value: string }[];
}

export interface ExecutionStep {
  phase: string;
  label: string;
  timestamp: string;
  details: string;
  status: 'pending' | 'running' | 'complete';
}

export interface ReplayStep {
  phase: string;
  label: string;
  timestamp: string;
  details: string;
  status: string;
}

export interface ExecutionSummary {
  task: string;
  inputs: string[];
  modelsUsed: string[];
  toolsExecuted: string[];
  executionTimeMs: number;
  telemetryId: string;
  modelVersion: string;
  datasetVersion: string;
  computeCostUnits?: string;
}

export interface AnalysisResult {
  id: string;
  queryText: string;
  task: string;
  models: string[];
  status: 'COMPLETE' | 'PROCESSING' | 'FAILED';
  confidence: number;
  headline: string;
  answer: string;
  changePercentage?: string;
  overlayType?: 'change' | 'ndwi' | 'sar_fusion' | 'detection';
  evidence: EvidenceRegion[];
  executionSummary: ExecutionSummary;
  replaySteps: ReplayStep[];
  followUpActions: string[];
  timestamp: string;
}

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

export interface DemoScenario {
  id: string;
  title: string;
  badge: string;
  description: string;
  observations: Observation[];
  sampleQueries: string[];
  presetResult: AnalysisResult;
}

export interface MapLayerConfig {
  id: string;
  name: string;
  visible: boolean;
  color: string;
  count?: number;
}
