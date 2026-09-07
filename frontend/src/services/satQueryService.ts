import type {
  Observation,
  AnalysisResult,
  QueryHistoryItem,
  ModalityType,
  ExecutionInput,
  SatelliteProviderInfo,
} from '../types/satquery';



// ============================================================
// TYPES
// ============================================================

type BackendUploadMetadata = {
  id?: string;
  filename?: string;
  name?: string;

  url?: string;
  image_url?: string;
  imageUrl?: string;

  file_path?: string;
  local_path?: string;

  source_type?: string;
  ingestion_status?: string;

  sensor?: string;
  modality?: string;

  dimensions?: [number, number] | number[] | string;

  bounds?: number[];
  resolution?: number;

  bands?: string[] | string[];

  acquisition_date?: string | null;

  [key: string]: unknown;
};


type BackendAnalysisResponse = {
  query?: string;

  task?: string;

  input_mode?: string;

  selected_model?: {
    name?: string;
    description?: string;
  };

  processing_steps?: unknown[];

  answer?: string;

  confidence?: number;

  visual_evidence?: unknown;

  execution_summary?: {
    task?: string;

    inputs?: unknown[];

    models_used?: string[];
    modelsUsed?: string[];

    tools_used?: string[];
    toolsUsed?: string[];

    tools?: string[];

    execution_time_seconds?: number;

    execution_time_ms?: number;

    telemetry_id?: string;

    audit_timestamp?: string;

    model_version?: string;

    dataset_version?: string;

    execution_status?: string;

    [key: string]: unknown;
  };

  error?: boolean;
  message?: string;

  [key: string]: unknown;
};





type ServiceStepCallback = (
  stepIndex: number,
  label: string
) => void;


// ============================================================
// SESSION STATE
// ============================================================

// Keep the live workspace empty. Demo observations are loaded only when
// the user explicitly selects a demo scenario. This prevents demo/change
// observations from appearing in a real satellite analysis session.
let userObservations: Observation[] = [];


// Session history populated by backend responses.
let sessionHistory: QueryHistoryItem[] = [];


// ============================================================
// CONSTANTS
// ============================================================

const ANALYSIS_STEPS = [
  'Understanding request & parsing intent',
  'Checking active observation metadata',
  'Determining analysis type',
  'Selecting remote sensing AI model',
  'Running specialist analysis',
  'Generating spatial evidence',
  'Finalizing auditable result',
];


// ============================================================
// GENERIC HELPERS
// ============================================================

function isRecord(
  value: unknown
): value is Record<string, unknown> {
  return (
    typeof value === 'object' &&
    value !== null
  );
}


function formatDate(
  date: Date = new Date()
): string {
  return (
    date
      .toLocaleDateString(
        'en-GB',
        {
          day: '2-digit',
          month: 'short',
          year: 'numeric',
        }
      )
      .toUpperCase()
  );
}


function formatTimestamp(
  date: Date = new Date()
): string {
  return (
    `${formatDate(date)} ` +
    `${date.toISOString().substring(11, 16)} UTC`
  );
}


function normalizeConfidence(
  value: unknown
): number {
  const numeric = Number(value);

  if (!Number.isFinite(numeric)) {
    return 0;
  }

  let confidence = numeric;

  // Backend/model may provide 0..1 or 0..100.
  if (
    confidence >= 0 &&
    confidence <= 1
  ) {
    confidence *= 100;
  }

  return Math.max(
    0,
    Math.min(
      100,
      Math.round(confidence)
    )
  );
}


function getBackendError(
  response: Response,
  fallback: string
): Promise<Error> {
  return response
    .json()
    .catch(() => ({}))
    .then((data) => {
      let detailMessage: string | null = null;
      if (isRecord(data)) {
        if (typeof data.detail === 'string') {
          detailMessage = data.detail;
        } else if (isRecord(data.detail)) {
          detailMessage =
            (typeof data.detail.error === 'string' ? data.detail.error : null) ||
            (typeof data.detail.message === 'string' ? data.detail.message : null);
        } else if (typeof data.message === 'string') {
          detailMessage = data.message;
        }
      }

      return new Error(
        detailMessage ||
        fallback ||
        `Request failed with HTTP ${response.status}`
      );
    });
}


async function fetchJson<T>(
  input: RequestInfo | URL,
  init?: RequestInit
): Promise<T> {
  const response = await fetch(
    input,
    init
  );

  if (!response.ok) {
    throw await getBackendError(
      response,
      `Request failed with HTTP ${response.status}`
    );
  }

  return response.json() as Promise<T>;
}


// ============================================================
// OBSERVATION HELPERS
// ============================================================

function getObservationFilePath(
  observation: Observation
): string | undefined {
  const candidate: any =
    observation as any;

  return (
    candidate.filePath ||
    candidate.file_path ||
    candidate.localPath ||
    candidate.local_path ||
    candidate.metadata?.filePath ||
    candidate.metadata?.file_path ||
    undefined
  );
}


function getObservationSourceType(
  observation: Observation
): string | undefined {
  const candidate: any =
    observation as any;

  return (
    candidate.sourceType ||
    candidate.source_type ||
    candidate.metadata?.sourceType ||
    candidate.metadata?.source_type ||
    undefined
  );
}


function getObservationIngestionStatus(
  observation: Observation
): string | undefined {
  const candidate: any =
    observation as any;

  return (
    candidate.ingestionStatus ||
    candidate.ingestion_status ||
    candidate.metadata?.ingestionStatus ||
    candidate.metadata?.ingestion_status ||
    undefined
  );
}


function extractObservationAcquisitionDate(
  observation: Observation
): string | null {
  const candidate: any =
    observation as any;

  return (
    candidate.acquisitionDate ||
    candidate.acquisition_date ||
    candidate.metadata?.acquisitionDate ||
    candidate.metadata?.acquisition_date ||
    candidate.date ||
    null
  );
}


function extractObservationSensor(
  observation: Observation
): string | undefined {
  const candidate: any =
    observation as any;

  return (
    candidate.sensor ||
    candidate.metadata?.sensor ||
    undefined
  );
}


function formatBandsString(rawBands: any, _fallbackModality?: string): string {
  if (typeof rawBands === 'string' && rawBands.trim().length > 0) {
    return rawBands;
  }
  if (typeof rawBands === 'number') {
    return `${rawBands} Channels`;
  }
  if (Array.isArray(rawBands)) {
    if (rawBands.length === 0) return 'Not available';
    if (typeof rawBands[0] === 'object' && rawBands[0] !== null) {
      const descriptions = rawBands
        .map((b: any) => b.description || b.name || (b.index ? `B${b.index}` : ''))
        .filter(Boolean);
      return descriptions.length > 0
        ? `${rawBands.length} Channels (${descriptions.join(', ')})`
        : `${rawBands.length} Channels`;
    }
    return `${rawBands.length} Channels (${rawBands.join(', ')})`;
  }
  return 'Not available';
}


function observationToBackendPayload(
  observation: Observation
): Record<string, unknown> {
  const candidate: any =
    observation as any;

  const filePath =
    getObservationFilePath(
      observation
    );

  const sourceType =
    getObservationSourceType(
      observation
    );

  const ingestionStatus =
    getObservationIngestionStatus(
      observation
    );

  const acquisitionDate =
    extractObservationAcquisitionDate(
      observation
    );

  const sensor =
    extractObservationSensor(
      observation
    );

  return {
    id:
      candidate.id,

    name:
      candidate.name,

    filename:
      candidate.filename ||
      candidate.name,

    modality:
      normalizeModalityForBackend(
        candidate.modality
      ),

    // Keep both frontend/backend naming conventions.
    date:
      candidate.date,

    acquisition_date:
      acquisitionDate,

    acquisitionDate:
      acquisitionDate,

    url:
      candidate.imageUrl ||
      candidate.image_url ||
      candidate.url,

    image_url:
      candidate.imageUrl ||
      candidate.image_url ||
      candidate.url,

    imageUrl:
      candidate.imageUrl ||
      candidate.image_url ||
      candidate.url,

    thumbnail_url:
      candidate.thumbnailUrl ||
      candidate.thumbnail_url,

    thumbnailUrl:
      candidate.thumbnailUrl ||
      candidate.thumbnail_url,

    // CRITICAL:
    // Actual local backend/model asset.
    file_path:
      filePath,

    local_path:
      filePath,

    source_type:
      sourceType,

    ingestion_status:
      ingestionStatus,

    provider:
      candidate.provider ||
      candidate.metadata?.provider,

    product_id:
      candidate.productId ||
      candidate.product_id ||
      candidate.metadata?.productId ||
      candidate.metadata?.product_id,

    analysis_asset:
      candidate.analysis_asset ||
      candidate.metadata?.analysis_asset,

    remote_analysis_asset:
      candidate.remote_analysis_asset ||
      candidate.metadata?.remote_analysis_asset,

    analysis_asset_url:
      candidate.analysis_asset_url ||
      candidate.metadata?.analysis_asset_url,

    remote_asset_url:
      candidate.remote_asset_url ||
      candidate.metadata?.remote_asset_url,

    assets:
      candidate.assets ||
      candidate.metadata?.assets,

    sensor:
      sensor,

    metadata:
      candidate.metadata || {},
  };
}


function normalizeModalityForBackend(
  modality: unknown
): string {
  const value =
    String(
      modality || 'OPTICAL'
    )
      .trim()
      .toLowerCase();

  if (
    value === 'sar' ||
    value === 'radar'
  ) {
    return 'sar';
  }

  if (
    value === 'multispectral' ||
    value === 'multi-spectral' ||
    value === 'ms'
  ) {
    return 'optical';
  }

  return 'optical';
}


// ============================================================
// EVIDENCE NORMALIZATION
// ============================================================

function normalizeEvidence(
  rawEvidence: unknown
): any[] {
  if (
    Array.isArray(rawEvidence)
  ) {
    return rawEvidence;
  }

  if (
    isRecord(rawEvidence)
  ) {
    const candidateArrays = [
      rawEvidence.regions,
      rawEvidence.boxes,
      rawEvidence.detections,
      rawEvidence.features,
      rawEvidence.items,
    ];

    for (
      const candidate
      of candidateArrays
    ) {
      if (
        Array.isArray(candidate)
      ) {
        return candidate;
      }
    }
  }

  return [];
}


function normalizeEvidenceRegion(
  region: any,
  index: number
): any {
  if (!isRecord(region)) return null;

  const confidence =
    region?.confidence !== undefined
      ? normalizeConfidence(region.confidence)
      : undefined;

  const coords =
    region?.coords ||
    region?.bbox ||
    region?.box ||
    region?.coordinates;

  return {
    id:
      region?.id ||
      `reg-api-${index + 1}`,

    label:
      region?.label ||
      region?.name ||
      `Feature ${index + 1}`,

    coords:
      coords || undefined,

    areaEstimate:
      region?.areaEstimate ??
      region?.area ??
      region?.area_estimate ??
      undefined,

    confidence,

    type:
      region?.type ||
      'detection',

    description:
      region?.description ||
      undefined,

    metrics:
      Array.isArray(region?.metrics)
        ? region.metrics
        : undefined,
  };
}


// ============================================================
// BACKEND RESPONSE → FRONTEND RESULT
// ============================================================

function backendToAnalysisResult(
  backendData: BackendAnalysisResponse,
  queryText: string,
  activeObservations: Observation[]
): AnalysisResult {
  const rawEvidence =
    normalizeEvidence(
      backendData.visual_evidence
    );

  const evidence = rawEvidence
    .map(normalizeEvidenceRegion)
    .filter(Boolean);

  const modelsUsed =
    Array.isArray(
      backendData.execution_summary?.models_used
    )
      ? backendData.execution_summary!.models_used!
      : Array.isArray(
        backendData.execution_summary?.modelsUsed
      )
        ? backendData.execution_summary!.modelsUsed!
        : backendData.selected_model?.name
          ? [
            backendData.selected_model.name,
          ]
          : [];

  const toolsExecuted =
    Array.isArray(
      backendData.execution_summary?.tools_used
    )
      ? backendData.execution_summary!.tools_used!
      : Array.isArray(
        backendData.execution_summary?.toolsUsed
      )
        ? backendData.execution_summary!.toolsUsed!
        : Array.isArray(
          backendData.execution_summary?.tools
        )
          ? backendData.execution_summary!.tools!
          : [];

  const confidence =
    backendData.confidence !== undefined
      ? normalizeConfidence(backendData.confidence)
      : 0;

  const executionTimeSeconds =
    Number(
      backendData.execution_summary
        ?.execution_time_seconds ??
      0
    );

  const executionTimeMs =
    Number.isFinite(
      executionTimeSeconds
    ) && executionTimeSeconds > 0
      ? Math.round(
        executionTimeSeconds * 1000
      )
      : Number(
        backendData.execution_summary
          ?.execution_time_ms ??
        0
      );

  const executionInputs: Array<string | ExecutionInput> =
    Array.isArray(
      backendData.execution_summary
        ?.inputs
    )
      ? (backendData.execution_summary!.inputs! as Array<string | ExecutionInput>)
      : activeObservations.map(
        (
          observation
        ) =>
          observation.filename ||
          observation.name
      );

  const processingSteps =
    Array.isArray(
      backendData.processing_steps
    )
      ? backendData.processing_steps
      : [];

  const replaySteps =
    processingSteps.map(
      (
        step: unknown,
        index: number
      ) => {
        const label =
          typeof step === 'string'
            ? step
            : isRecord(step) &&
              typeof step.label === 'string'
              ? step.label
              : `Processing step ${index + 1}`;

        const status =
          isRecord(step) &&
            typeof step.status === 'string'
            ? step.status
            : 'complete';

        return {
          phase:
            `STEP ${String(index + 1).padStart(2, '0')}`,

          label,

          timestamp:
            'backend',

          details:
            isRecord(step) &&
              typeof step.details === 'string'
              ? step.details
              : `Executed ${label}`,

          status,
        };
      }
    );

  const timestamp =
    backendData.execution_summary
      ?.audit_timestamp ||
    formatTimestamp();

  const telemetryId =
    (backendData.execution_summary?.telemetry_id as string) ||
    (backendData.execution_summary?.telemetryId as string) ||
    undefined;

  const modelVersion =
    (backendData.execution_summary?.model_version as string) ||
    (backendData.execution_summary?.modelVersion as string) ||
    undefined;

  const datasetVersion =
    (backendData.execution_summary?.dataset_version as string) ||
    (backendData.execution_summary?.datasetVersion as string) ||
    undefined;

  const result: AnalysisResult = {
    id:
      `res-api-${Date.now()}`,

    queryText:
      backendData.query ||
      queryText,

    task:
      backendData.task ||
      'SatQuery AI Analysis',

    models:
      modelsUsed,

    status:
      'COMPLETE',

    confidence,

    headline:
      backendData.task ||
      'Remote-Sensing Analysis Complete',

    answer:
      typeof backendData.answer === 'string' &&
        backendData.answer.trim()
        ? backendData.answer
        : (() => {
          throw new Error(
            'Analysis backend returned no textual answer.'
          );
        })(),

    changePercentage:
      deriveChangePercentage(
        backendData
      ),

    overlayType:
      determineOverlayTypeFromBackend(
        backendData
      ),

    evidence,

    executionSummary: {
      task:
        backendData.task ||
        'SatQuery AI Execution',

      inputs:
        executionInputs,

      modelsUsed,

      toolsExecuted,

      executionTimeMs:
        executionTimeMs || undefined,

      telemetryId,

      modelVersion,

      datasetVersion,
    },

    replaySteps,

    followUpActions: [
      'SHOW WHERE (Highlight evidence on map)',
      'MEASURE AREA (Detailed metric breakdown)',
      'EXPORT REPORT (Generate PDF/GeoJSON audit summary)',
    ],

    timestamp,
  };

  return result;
}


// ============================================================
// CHANGE PERCENTAGE
// ============================================================

function deriveChangePercentage(
  backendData: BackendAnalysisResponse
): string | undefined {
  const candidate: any =
    backendData as any;

  const directCandidates = [
    candidate.change_percentage,
    candidate.changePercentage,
    candidate.execution_summary?.change_percentage,
    candidate.execution_summary?.changePercentage,
  ];

  for (
    const value
    of directCandidates
  ) {
    if (
      typeof value === 'number' &&
      Number.isFinite(value)
    ) {
      const sign =
        value > 0
          ? '+'
          : '';

      return `${sign}${value}%`;
    }

    if (
      typeof value === 'string' &&
      value.trim()
    ) {
      return value;
    }
  }

  const statistics =
    candidate.change_statistics ||
    candidate.execution_summary?.change_statistics;

  if (
    isRecord(statistics)
  ) {
    const percentage =
      statistics.percentage ??
      statistics.change_percentage ??
      statistics.changePercentage;

    if (
      typeof percentage === 'number' &&
      Number.isFinite(percentage)
    ) {
      const sign =
        percentage > 0
          ? '+'
          : '';

      return `${sign}${percentage}%`;
    }

    if (
      typeof percentage === 'string'
    ) {
      return percentage;
    }
  }

  // No synthetic number.
  return undefined;
}


// ============================================================
// OVERLAY TYPE
// ============================================================

function determineOverlayTypeFromBackend(
  backendData: BackendAnalysisResponse
):
  'change' |
  'ndwi' |
  'sar_fusion' |
  'detection' {
  const task =
    String(
      backendData.task || ''
    ).toLowerCase();

  const inputMode =
    String(
      backendData.input_mode || ''
    ).toLowerCase();

  if (
    task.includes('water') ||
    task.includes('ndwi')
  ) {
    return 'ndwi';
  }

  if (
    inputMode === 'optical_sar' ||
    task.includes('sar') ||
    task.includes('radar')
  ) {
    return 'sar_fusion';
  }

  if (
    inputMode === 'bi_temporal' ||
    task.includes('change')
  ) {
    return 'change';
  }

  return 'detection';
}


// ============================================================
// INPUT MODE
// ============================================================

function determineInputMode(
  activeObservations: Observation[]
): string {
  const count =
    activeObservations.length;

  const hasSar =
    activeObservations.some(
      (observation) =>
        normalizeModalityForBackend(
          (observation as any).modality
        ) === 'sar'
    );

  const hasOptical =
    activeObservations.some(
      (observation) => {
        const modality =
          normalizeModalityForBackend(
            (observation as any).modality
          );

        return (
          modality === 'optical' ||
          modality === 'multispectral'
        );
      }
    );

  if (
    count >= 2 &&
    hasSar &&
    hasOptical
  ) {
    return 'optical_sar';
  }

  if (
    count >= 2
  ) {
    return 'bi_temporal';
  }

  return 'single_image';
}


// ============================================================
// PUBLIC SERVICE
// ============================================================

export const satQueryService = {

  // ==========================================================
  // UPLOAD OBSERVATION
  // ==========================================================

  async uploadObservation(
    file: File,
    name?: string,
    modality: ModalityType = 'OPTICAL'
  ): Promise<Observation> {

    const formData =
      new FormData();

    formData.append(
      'file',
      file
    );

    let realMeta:
      BackendUploadMetadata;

    try {

      realMeta =
        await fetchJson<BackendUploadMetadata>(
          '/api/upload',
          {
            method:
              'POST',

            body:
              formData,
          }
        );

    } catch (error) {

      // Do NOT silently create a fake "backend-ready"
      // observation if upload fails.
      console.error(
        'SatQuery backend upload failed:',
        error
      );

      throw error;
    }

    const backendModality =
      normalizeModalityForBackend(
        modality
      );

    const dimensions =
      formatDimensions(
        realMeta.dimensions
      );

    const bounds =
      Array.isArray(
        realMeta.bounds
      ) &&
        realMeta.bounds.length >= 4
        ? realMeta.bounds
        : undefined;

    const centerLat =
      bounds
        ? (
          Number(bounds[1]) +
          Number(bounds[3])
        ) / 2
        : undefined;

    const centerLon =
      bounds
        ? (
          Number(bounds[0]) +
          Number(bounds[2])
        ) / 2
        : undefined;

    const acquisitionDate =
      realMeta.acquisition_date ||
      null;

    const newObs: Observation = {
      id:
        String(
          realMeta.id ||
          `obs-user-${Date.now()}`
        ),

      name:
        name ||
        realMeta.name ||
        file.name.replace(
          /\.[^/.]+$/,
          ''
        ),

      filename:
        realMeta.filename ||
        file.name,

      modality:
        modality,

      date:
        acquisitionDate
          ? formatObservationDate(
            acquisitionDate
          )
          : 'DATE NOT AVAILABLE',

      dimensions:
        dimensions ||
        'Unknown',

      status:
        'READY',

      metadata: {
        sensor:
          realMeta.sensor ||
          `UserUpload-${backendModality}`,

        lat:
          centerLat,

        lon:
          centerLon,

        cloudCover:
          formatOptionalPercentage(
            findMetadataValue(
              realMeta,
              [
                'cloud_cover',
                'cloudCover',
                'cloudCoverPercentage',
              ]
            )
          ),

        bands: formatBandsString(realMeta.bands, modality),

        fileSize:
          `${(
            file.size /
            (1024 * 1024)
          ).toFixed(1)} MB`,

        groundSamplingDistance:
          typeof realMeta.resolution === 'number'
            ? `${realMeta.resolution}m/px`
            : 'Not available',

        acquisitionTime:
          acquisitionDate
            ? formatAcquisitionTime(
              acquisitionDate
            )
            : 'Not available',

        // Preserve actual backend metadata.
        ...realMeta,
      },

      imageUrl:
        String(
          realMeta.url ||
          realMeta.image_url ||
          ''
        ),

      thumbnailUrl:
        String(
          realMeta.url ||
          realMeta.image_url ||
          ''
        ),

      isDemo:
        false,

      // ------------------------------------------------------
      // The next properties are runtime-compatible even if
      // your Observation interface is currently narrower.
      // Cast happens below without changing UI contracts.
      // ------------------------------------------------------
      ...((
        {
          filePath:
            realMeta.file_path,

          file_path:
            realMeta.file_path,

          localPath:
            realMeta.local_path ||
            realMeta.file_path,

          local_path:
            realMeta.local_path ||
            realMeta.file_path,

          sourceType:
            realMeta.source_type ||
            'upload',

          source_type:
            realMeta.source_type ||
            'upload',

          ingestionStatus:
            realMeta.ingestion_status ||
            'ready',

          ingestion_status:
            realMeta.ingestion_status ||
            'ready',

          acquisitionDate:
            acquisitionDate,

          acquisition_date:
            acquisitionDate,

          provider:
            realMeta.provider,

          productId:
            realMeta.product_id,

          product_id:
            realMeta.product_id,
        } as any
      )),
    } as Observation;

    userObservations.unshift(
      newObs
    );

    return newObs;
  },


  // ==========================================================
  // WEB SATELLITE DATA SEARCH & FETCH
  // ==========================================================

  async getSatelliteProviders(): Promise<SatelliteProviderInfo[]> {
    try {
      const data = await fetchJson<{ providers?: SatelliteProviderInfo[] }>('/api/data/providers');
      return Array.isArray(data.providers) ? data.providers : [];
    } catch (err) {
      console.warn('Failed to load satellite providers:', err);
      return [];
    }
  },

  async searchSatelliteData(params: {
    provider?: string;
    collections?: string[];
    bbox?: [number, number, number, number];
    datetimeRange?: string;
    limit?: number;
    filters?: Record<string, any>;
  }): Promise<{ provider: string; total_matched: number; items: any[] }> {
    const payload = {
      provider: params.provider || '',
      collections: params.collections || [],
      bbox: params.bbox,
      datetime_range: params.datetimeRange,
      limit: params.limit || 10,
      filters: params.filters || {},
    };

    const resp = await fetchJson<{
      provider: string;
      total_matched: number;
      items: any[];
    }>('/api/data/search', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    return resp;
  },

  async downloadSatelliteProduct(params: {
    productId: string;
    provider?: string;
    collection?: string;
  }): Promise<Observation> {
    const activeProvider = params.provider || '';
    const payload = {
      provider: activeProvider,
      product_id: params.productId,
      collection: params.collection,
    };

    const resp = await fetchJson<{
      status: string;
      download_result?: {
        local_path?: string;
        file_size_bytes?: number;
        provider?: string;
        product_id?: string;
        collection?: string;
      };
      observation: BackendUploadMetadata;
    }>('/api/data/download', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    const realMeta = resp.observation || ({} as BackendUploadMetadata);

    // Verify local analysis asset
    const analysisAsset =
      (typeof realMeta.analysis_asset === 'string' && realMeta.analysis_asset.trim()) ||
      (typeof realMeta.local_path === 'string' && realMeta.local_path.trim()) ||
      (typeof realMeta.file_path === 'string' && realMeta.file_path.trim()) ||
      (typeof resp.download_result?.local_path === 'string' && resp.download_result.local_path.trim()) ||
      null;

    if (!analysisAsset) {
      throw new Error(
        'Backend confirmed download, but did not provide a valid local analysis asset for ingestion.'
      );
    }

    // 1. Provider, Product ID & Collection from real response
    const providerVal =
      (typeof realMeta.provider === 'string' && realMeta.provider.trim()) ||
      (typeof resp.download_result?.provider === 'string' && resp.download_result.provider.trim()) ||
      activeProvider ||
      null;

    const productIdVal =
      (typeof realMeta.product_id === 'string' && realMeta.product_id.trim()) ||
      (typeof realMeta.productId === 'string' && realMeta.productId.trim()) ||
      (typeof resp.download_result?.product_id === 'string' && resp.download_result.product_id.trim()) ||
      params.productId ||
      null;

    const collectionVal =
      (typeof realMeta.collection === 'string' && realMeta.collection.trim()) ||
      (typeof resp.download_result?.collection === 'string' && resp.download_result.collection.trim()) ||
      params.collection ||
      null;

    // 2. Acquisition Date from real response
    const rawAcqDate =
      (typeof realMeta.acquisition_date === 'string' && realMeta.acquisition_date.trim()) ||
      (typeof realMeta.acquisitionDate === 'string' && realMeta.acquisitionDate.trim()) ||
      (typeof realMeta.date === 'string' && realMeta.date.trim()) ||
      null;

    const acquisitionDate = rawAcqDate ? rawAcqDate : null;
    const dateDisplayStr = rawAcqDate
      ? (rawAcqDate.length >= 10 ? rawAcqDate.substring(0, 10) : rawAcqDate)
      : 'Not available';

    // 3. Sensor, Platform & Instrument from real response
    const sensorVal =
      (typeof realMeta.sensor === 'string' && realMeta.sensor.trim()) ||
      (typeof realMeta.instrument === 'string' && realMeta.instrument.trim()) ||
      null;

    const platformVal =
      (typeof realMeta.platform === 'string' && realMeta.platform.trim()) ||
      null;

    const instrumentVal =
      (typeof realMeta.instrument === 'string' && realMeta.instrument.trim()) ||
      null;

    const satelliteLabel =
      platformVal ||
      sensorVal ||
      instrumentVal ||
      collectionVal ||
      providerVal ||
      'Not available';

    // 4. Modality from real response
    let normalizedModality: ModalityType = 'OPTICAL';
    if (typeof realMeta.modality === 'string') {
      const m = realMeta.modality.toUpperCase().trim();
      if (m === 'SAR') normalizedModality = 'SAR';
      else if (m === 'MULTISPECTRAL') normalizedModality = 'MULTISPECTRAL';
      else if (m === 'THERMAL') normalizedModality = 'THERMAL';
      else if (m === 'OPTICAL') normalizedModality = 'OPTICAL';
    }

    // 5. Resolution from real response
    const rawResNumber =
      typeof realMeta.resolution === 'number'
        ? realMeta.resolution
        : typeof (realMeta as any).spatial_resolution === 'number'
        ? (realMeta as any).spatial_resolution
        : typeof (realMeta as any).spatial_resolution_m === 'number'
        ? (realMeta as any).spatial_resolution_m
        : typeof (realMeta as any).spatialResolution === 'number'
        ? (realMeta as any).spatialResolution
        : undefined;

    const rawResStr =
      typeof (realMeta as any).resolution === 'string' && (realMeta as any).resolution.trim()
        ? (realMeta as any).resolution.trim()
        : typeof (realMeta as any).spatial_resolution === 'string' && (realMeta as any).spatial_resolution.trim()
        ? (realMeta as any).spatial_resolution.trim()
        : typeof (realMeta as any).spatialResolution === 'string' && (realMeta as any).spatialResolution.trim()
        ? (realMeta as any).spatialResolution.trim()
        : undefined;

    const resolutionDisplay =
      rawResNumber !== undefined
        ? `${rawResNumber}m`
        : rawResStr || 'Not available';

    // 6. Bands from real response
    const bandCount =
      Array.isArray(realMeta.bands)
        ? realMeta.bands.length
        : typeof realMeta.bands === 'number'
        ? realMeta.bands
        : typeof realMeta.band_count === 'number'
        ? realMeta.band_count
        : undefined;

    const bandsString = formatBandsString(realMeta.bands, realMeta.modality as string | undefined);

    // 7. CRS from real response
    const crsVal =
      (typeof realMeta.crs === 'string' && realMeta.crs.trim()) ||
      (typeof realMeta.coordinate_system === 'string' && realMeta.coordinate_system.trim()) ||
      (typeof realMeta.coordinateSystem === 'string' && realMeta.coordinateSystem.trim()) ||
      null;

    // 8. Bounds from real response
    const rawBounds = realMeta.bounds || realMeta.bbox;
    const boundsVal =
      Array.isArray(rawBounds) && rawBounds.length === 4
        ? (rawBounds as [number, number, number, number])
        : null;

    // 9. Dimensions from real response
    const dimensionsDisplay = formatDimensions(realMeta.dimensions as any) || 'Not available';

    // 10. File Size & Cloud Cover from real response
    const fileSizeVal =
      (typeof realMeta.file_size === 'string' && realMeta.file_size.trim()) ||
      (typeof realMeta.fileSize === 'string' && realMeta.fileSize.trim()) ||
      (typeof realMeta.file_size_bytes === 'number'
        ? `${(realMeta.file_size_bytes / (1024 * 1024)).toFixed(2)} MB`
        : typeof resp.download_result?.file_size_bytes === 'number'
        ? `${(resp.download_result.file_size_bytes / (1024 * 1024)).toFixed(2)} MB`
        : null);

    const cloudCoverVal =
      realMeta.cloud_cover !== null && realMeta.cloud_cover !== undefined
        ? `${realMeta.cloud_cover}%`
        : realMeta.cloudCover !== null && realMeta.cloudCover !== undefined
        ? `${realMeta.cloudCover}%`
        : null;

    const displayName =
      (typeof realMeta.filename === 'string' && realMeta.filename.trim()) ||
      (typeof realMeta.name === 'string' && realMeta.name.trim()) ||
      productIdVal ||
      'Not available';

    const newObs: Observation = {
      id: (typeof realMeta.id === 'string' && realMeta.id.trim()) || `obs-${providerVal || 'download'}-${Date.now()}`,
      name: displayName,
      filename: displayName,
      date: dateDisplayStr,
      satellite: satelliteLabel,
      modality: normalizedModality,
      dimensions: dimensionsDisplay,
      imageUrl: (typeof realMeta.url === 'string' && realMeta.url) || (typeof realMeta.image_url === 'string' && realMeta.image_url) || '',
      thumbnailUrl: (typeof realMeta.url === 'string' && realMeta.url) || (typeof realMeta.image_url === 'string' && realMeta.image_url) || '',
      status: 'READY',
      isDemo: false,
      metadata: {
        ...realMeta,
        provider: providerVal || undefined,
        productId: productIdVal || undefined,
        product_id: productIdVal || undefined,
        collection: collectionVal || undefined,
        sensor: sensorVal || undefined,
        platform: platformVal || undefined,
        instrument: instrumentVal || undefined,
        modality: typeof realMeta.modality === 'string' ? realMeta.modality : undefined,
        acquisitionDate: acquisitionDate,
        acquisition_date: acquisitionDate,
        resolution: rawResNumber,
        spatialResolution: rawResNumber,
        groundSamplingDistance: rawResNumber !== undefined ? `${rawResNumber}m/px` : rawResStr || 'Not available',
        bands: bandsString !== 'Not available' ? bandsString : undefined,
        crs: crsVal || undefined,
        coordinateSystem: crsVal || undefined,
        bounds: boundsVal || undefined,
        bbox: boundsVal || undefined,
        fileSize: fileSizeVal || undefined,
        cloudCover: cloudCoverVal || undefined,
        sourceType: 'web_fetch',
        ingestionStatus: 'ready',
        analysisAsset: analysisAsset,
        analysis_asset: analysisAsset,
      },
      ...(({
        filePath: analysisAsset,
        file_path: analysisAsset,
        localPath: analysisAsset,
        local_path: analysisAsset,
        analysisAsset: analysisAsset,
        analysis_asset: analysisAsset,
        sourceType: 'web_fetch',
        source_type: 'web_fetch',
        ingestionStatus: 'ready',
        ingestion_status: 'ready',
        provider: providerVal || undefined,
        productId: productIdVal || undefined,
        product_id: productIdVal || undefined,
        collection: collectionVal || undefined,
        sensor: sensorVal || undefined,
        platform: platformVal || undefined,
        instrument: instrumentVal || undefined,
        acquisitionDate: acquisitionDate,
        acquisition_date: acquisitionDate,
        crs: crsVal || undefined,
        bounds: boundsVal || undefined,
        bbox: boundsVal || undefined,
        resolution: resolutionDisplay,
        bands: bandCount,
      } as any)),
    } as Observation;

    userObservations.unshift(newObs);
    return newObs;
  },


  // ==========================================================
  // SIH DATA RESOURCES (SIH26167)
  // ==========================================================

  async getSIHResources(params?: {
    resourceType?: string;
    availableOnly?: boolean;
  }): Promise<{
    resources: import('../types/satquery').SIHResourceItem[];
    summary: { total_registered: number; available_count: number };
  }> {
    const queryParams = new URLSearchParams();
    if (params?.resourceType) queryParams.set('resource_type', params.resourceType);
    if (params?.availableOnly) queryParams.set('available_only', 'true');

    const url = `/api/resources/sih${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
    return await fetchJson<{
      resources: import('../types/satquery').SIHResourceItem[];
      summary: { total_registered: number; available_count: number };
    }>(url);
  },

  async getSIHResourceSamples(
    resourceId: string,
    limit: number = 50,
    filterTask?: string
  ): Promise<{
    resource: import('../types/satquery').SIHResourceItem;
    samples: import('../types/satquery').SIHSampleItem[];
  }> {
    const queryParams = new URLSearchParams();
    if (limit) queryParams.set('limit', limit.toString());
    if (filterTask) queryParams.set('filter_task', filterTask);

    const url = `/api/resources/sih/${encodeURIComponent(resourceId)}/samples?${queryParams.toString()}`;
    return await fetchJson<{
      resource: import('../types/satquery').SIHResourceItem;
      samples: import('../types/satquery').SIHSampleItem[];
    }>(url);
  },

  async loadSIHSample(
    resourceId: string,
    sampleId: string
  ): Promise<{
    observation: Observation;
    companionObservation?: Observation;
    suggestedQuery?: string;
    groundTruthAnswer?: string;
  }> {
    const resp = await fetchJson<{
      status: string;
      resource_id: string;
      sample_id: string;
      data: any;
    }>('/api/resources/sih/load', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        resource_id: resourceId,
        sample_id: sampleId,
      }),
    });

    const data = resp.data;

    // Check if bi-temporal pair (CDVQA)
    if (data.primary_observation && data.companion_observation) {
      const pObs = data.primary_observation;
      const cObs = data.companion_observation;

      const primary: Observation = {
        id: pObs.id || `sih_${resourceId}_${sampleId}_t1`,
        name: pObs.name || pObs.filename || `${sampleId} (T1)`,
        filename: pObs.filename || `${sampleId}_t1.tif`,
        date: pObs.acquisition_date ? String(pObs.acquisition_date).substring(0, 10) : 'Pre-change Pass',
        satellite: pObs.platform || pObs.sensor || 'Benchmark Reference T1',
        modality: (String(pObs.modality || '').toUpperCase() === 'SAR' ? 'SAR' : 'OPTICAL') as ModalityType,
        resolution: pObs.resolution ? (typeof pObs.resolution === 'number' ? `${pObs.resolution}m` : String(pObs.resolution)) : 'Unknown',
        bands: Array.isArray(pObs.bands) ? pObs.bands.length : (typeof pObs.bands === 'number' ? pObs.bands : 0),
        imageUrl: pObs.url || pObs.image_url || pObs.imageUrl || '',
        thumbnailUrl: pObs.url || pObs.image_url || pObs.imageUrl || '',
        status: 'AVAILABLE',
        isDemo: false,
        metadata: {
          ...pObs,
          bands: formatBandsString(pObs.bands, pObs.modality),
          sourceType: 'sih_resource',
          resourceId: resourceId,
          sampleId: sampleId,
          ingestionStatus: 'ready',
        },
        ...(({
          filePath: pObs.file_path,
          file_path: pObs.file_path,
          localPath: pObs.local_path || pObs.file_path,
          local_path: pObs.local_path || pObs.file_path,
          sourceType: 'sih_resource',
          source_type: 'sih_resource',
          ingestionStatus: 'ready',
          ingestion_status: 'ready',
        } as any)),
      } as Observation;

      const companion: Observation = {
        id: cObs.id || `sih_${resourceId}_${sampleId}_t2`,
        name: cObs.name || cObs.filename || `${sampleId} (T2)`,
        filename: cObs.filename || `${sampleId}_t2.tif`,
        date: cObs.acquisition_date ? String(cObs.acquisition_date).substring(0, 10) : (cObs.date ? String(cObs.date) : 'N/A'),
        satellite: cObs.platform || cObs.sensor || 'Benchmark Reference T2',
        modality: (String(cObs.modality || '').toUpperCase() === 'SAR' ? 'SAR' : 'OPTICAL') as ModalityType,
        resolution: cObs.resolution ? (typeof cObs.resolution === 'number' ? `${cObs.resolution}m` : String(cObs.resolution)) : 'Unknown',
        bands: Array.isArray(cObs.bands) ? cObs.bands.length : (typeof cObs.bands === 'number' ? cObs.bands : 0),
        imageUrl: cObs.url || cObs.image_url || cObs.imageUrl || '',
        thumbnailUrl: cObs.url || cObs.image_url || cObs.imageUrl || '',
        status: 'AVAILABLE',
        isDemo: false,
        metadata: {
          ...cObs,
          bands: formatBandsString(cObs.bands, cObs.modality),
          sourceType: 'sih_resource',
          resourceId: resourceId,
          sampleId: sampleId,
          ingestionStatus: 'ready',
        },
        ...(({
          filePath: cObs.file_path,
          file_path: cObs.file_path,
          localPath: cObs.local_path || cObs.file_path,
          local_path: cObs.local_path || cObs.file_path,
          sourceType: 'sih_resource',
          source_type: 'sih_resource',
          ingestionStatus: 'ready',
          ingestion_status: 'ready',
        } as any)),
      } as Observation;

      userObservations.unshift(companion);
      userObservations.unshift(primary);

      return {
        observation: primary,
        companionObservation: companion,
        suggestedQuery: data.suggested_query,
        groundTruthAnswer: data.ground_truth_answer,
      };
    }

    // Single observation
    const realMeta = data;
    const obs: Observation = {
      id: realMeta.id || `sih_${resourceId}_${sampleId}`,
      name: realMeta.name || realMeta.filename || sampleId,
      filename: realMeta.filename || sampleId,
      date: realMeta.acquisition_date ? String(realMeta.acquisition_date).substring(0, 10) : (realMeta.date ? String(realMeta.date) : 'N/A'),
      satellite: realMeta.platform || realMeta.sensor || realMeta.dataset_name || 'SIH Benchmark',
      modality: (String(realMeta.modality || '').toUpperCase() === 'SAR' ? 'SAR' : 'OPTICAL') as ModalityType,
      resolution: typeof realMeta.resolution === 'number' ? `${realMeta.resolution}m` : (realMeta.resolution ? String(realMeta.resolution) : 'Unknown'),
      bands: Array.isArray(realMeta.bands) ? realMeta.bands.length : (typeof realMeta.bands === 'number' ? realMeta.bands : 0),
      imageUrl: realMeta.url || realMeta.image_url || realMeta.imageUrl || '',
      thumbnailUrl: realMeta.url || realMeta.image_url || realMeta.imageUrl || '',
      status: 'AVAILABLE',
      isDemo: false,
      metadata: {
        ...realMeta,
        bands: formatBandsString(realMeta.bands, realMeta.modality),
        sourceType: 'sih_resource',
        resourceId: resourceId,
        sampleId: sampleId,
        ingestionStatus: 'ready',
      },
      ...(({
        filePath: realMeta.file_path,
        file_path: realMeta.file_path,
        localPath: realMeta.local_path || realMeta.file_path,
        local_path: realMeta.local_path || realMeta.file_path,
        sourceType: 'sih_resource',
        source_type: 'sih_resource',
        ingestionStatus: 'ready',
        ingestion_status: 'ready',
      } as any)),
    } as Observation;

    userObservations.unshift(obs);

    return {
      observation: obs,
      suggestedQuery: realMeta.suggested_query,
      groundTruthAnswer: realMeta.ground_truth_answer,
    };
  },
  // ==========================================================

  async getObservations():
    Promise<Observation[]> {

    return [
      ...userObservations,
    ];
  },


  // ==========================================================
  // SUBMIT QUERY
  // ==========================================================

  async submitQuery(
    queryText: string,
    activeObservations: Observation[],
    onStepUpdate?: ServiceStepCallback
  ): Promise<AnalysisResult> {

    const query =
      String(
        queryText || ''
      ).trim();

    if (!query) {
      throw new Error(
        'Please enter a question before running analysis.'
      );
    }

    if (
      !activeObservations ||
      activeObservations.length === 0
    ) {
      throw new Error(
        'Select at least one observation before running analysis.'
      );
    }

    // --------------------------------------------------------
    // Update UI status immediately.
    // These are status notifications, NOT fake analysis.
    // --------------------------------------------------------

    const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

    onStepUpdate?.(0, ANALYSIS_STEPS[0]);
    const inputMode = determineInputMode(activeObservations);
    await delay(150);

    onStepUpdate?.(1, ANALYSIS_STEPS[1]);
    validateFrontendObservations(activeObservations, inputMode);
    await delay(150);

    onStepUpdate?.(2, ANALYSIS_STEPS[2]);
    await delay(150);

    onStepUpdate?.(3, ANALYSIS_STEPS[3]);
    await delay(150);

    const backendImages = activeObservations.map(observationToBackendPayload);

    onStepUpdate?.(4, ANALYSIS_STEPS[4]);

    let backendData: BackendAnalysisResponse;

    try {
      backendData = await fetchJson<BackendAnalysisResponse>(
        '/api/analyze',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            query,
            input_mode: inputMode,
            images: backendImages,
          }),
        }
      );
    } catch (error) {
      console.error('SatQuery backend analysis failed:', error);
      throw new Error(
        error instanceof Error
          ? error.message
          : 'SatQuery analysis failed.'
      );
    }

    if (backendData.error) {
      throw new Error(
        backendData.message ||
        'SatQuery backend reported an analysis error.'
      );
    }

    onStepUpdate?.(5, ANALYSIS_STEPS[5]);
    await delay(150);

    const result = backendToAnalysisResult(
      backendData,
      query,
      activeObservations
    );

    onStepUpdate?.(6, ANALYSIS_STEPS[6]);
    await delay(150);

    // --------------------------------------------------------
    // Store successful backend result.
    // --------------------------------------------------------

    const historyItem:
      QueryHistoryItem = {
      id:
        `hist-${Date.now()}`,

      queryText:
        query,

      observationsUsed:
        activeObservations.map(
          (observation) =>
            observation.filename ||
            observation.name
        ),

      analysisType:
        result.task,

      timestamp:
        result.timestamp,

      status:
        'Complete',

      confidence:
        result.confidence,

      resultSummary:
        result.headline,

      result,
    };

    sessionHistory.unshift(
      historyItem
    );

    return result;
  },


  // ==========================================================
  // GET HISTORY
  // ==========================================================

  async getHistory():
    Promise<QueryHistoryItem[]> {

    try {

      const backendData =
        await fetchJson<{
          history?: any[];
        }>(
          '/api/history'
        );

      if (
        Array.isArray(
          backendData.history
        ) &&
        backendData.history.length > 0
      ) {

        return normalizeBackendHistory(
          backendData.history
        );
      }

    } catch (error) {

      console.warn(
        'Backend history unavailable; returning session history.',
        error
      );
    }

    return [
      ...sessionHistory,
    ];
  },


  // ==========================================================
  // GET MODEL REGISTRY
  // ==========================================================

  async getModels():
    Promise<
      {
        name: string;
        type: string;
        accuracy: string;
        status: string;
      }[]
    > {

    try {

      const data =
        await fetchJson<{
          models?: any[];
        }>(
          '/api/models'
        );

      const models =
        Array.isArray(
          data.models
        )
          ? data.models
          : [];

      return models.map(
        (model: any) => ({
          name:
            String(
              model.name ||
              model.model_name ||
              'Unnamed model'
            ),

          type:
            String(
              model.type ||
              model.model_family ||
              model.description ||
              'Remote sensing model'
            ),

          accuracy:
            formatModelAccuracy(
              model.accuracy
            ),

          status:
            normalizeModelStatus(
              model.status
            ),
        })
      );

    } catch (error) {

      console.warn(
        'Backend model registry unavailable.',
        error
      );

      // Do not return fictional model performance.
      return [];
    }
  },


};


// ============================================================
// LOCAL VALIDATION
// ============================================================

function validateFrontendObservations(
  observations: Observation[],
  inputMode: string
): void {

  if (
    inputMode === 'bi_temporal' &&
    observations.length !== 2
  ) {
    throw new Error(
      'Bi-temporal analysis requires exactly two observations.'
    );
  }

  if (
    inputMode === 'optical_sar' &&
    observations.length !== 2
  ) {
    throw new Error(
      'Optical + SAR analysis requires exactly two observations.'
    );
  }

  // Real observations must have backend-readable files.
  for (
    const observation
    of observations
  ) {

    const sourceType =
      String(
        getObservationSourceType(
          observation
        ) || ''
      ).toLowerCase();

    const ingestionStatus =
      String(
        getObservationIngestionStatus(
          observation
        ) || ''
      ).toLowerCase();

    // Existing demos are allowed because their registered
    // scenario/model pipeline can explicitly handle them.
    if (
      sourceType === 'demo' ||
      (observation as any).isDemo === true
    ) {
      continue;
    }

    const filePath =
      getObservationFilePath(observation) ||
      (observation as any).file_path ||
      (observation as any).filePath ||
      (observation as any).local_path ||
      (observation as any).image_url ||
      (observation as any).imageUrl ||
      (observation as any).quicklook_url ||
      (observation as any).url;

    const candidate = observation as any;
    const hasAnalysisAsset = Boolean(
      filePath ||
      candidate.analysis_asset ||
      candidate.remote_analysis_asset ||
      candidate.analysis_asset_url ||
      candidate.remote_asset_url ||
      candidate.metadata?.analysis_asset ||
      candidate.metadata?.remote_analysis_asset ||
      candidate.metadata?.analysis_asset_url ||
      candidate.metadata?.remote_asset_url
    );

    if (!hasAnalysisAsset) {
      if (ingestionStatus === 'catalogue_only') {
        throw new Error(
          `Observation "${observation.name}" is catalogue-only and has no image URL or raster asset.`
        );
      }

      throw new Error(
        `Observation "${observation.name}" is not connected to a readable image asset. Re-ingest it first.`
      );
    }
  }
}


// ============================================================
// HISTORY NORMALIZATION
// ============================================================

function normalizeBackendHistory(
  items: any[]
): QueryHistoryItem[] {

  return items.map(
    (
      item,
      index
    ) => {

      const fullResult =
        isRecord(
          item.full_result
        )
          ? backendToAnalysisResult(
            item.full_result as BackendAnalysisResponse,
            item.query || '',
            []
          )
          : undefined;

      return {
        id:
          String(
            item.id ||
            `hist-backend-${index}`
          ),

        queryText:
          String(
            item.query ||
            ''
          ),

        observationsUsed:
          Array.isArray(
            item.observationsUsed
          )
            ? item.observationsUsed
            : Array.isArray(
              item.observations_used
            )
              ? item.observations_used
              : [],

        analysisType:
          String(
            item.task ||
            item.analysisType ||
            'SatQuery AI Analysis'
          ),

        timestamp:
          String(
            item.timestamp ||
            ''
          ),

        status:
          String(
            item.status ||
            'Complete'
          ),

        confidence:
          normalizeConfidence(
            item.confidence
          ),

        resultSummary:
          String(
            item.answer_summary ||
            item.resultSummary ||
            ''
          ),

        result:
          fullResult ||
          item.result,
      } as QueryHistoryItem;
    }
  );
}


// ============================================================
// FORMATTING HELPERS
// ============================================================

function formatDimensions(
  dimensions:
    | [number, number]
    | number[]
    | string
    | undefined
): string | undefined {

  if (
    typeof dimensions === 'string' &&
    dimensions.trim()
  ) {
    return dimensions;
  }

  if (
    Array.isArray(
      dimensions
    ) &&
    dimensions.length >= 2
  ) {
    return (
      `${dimensions[0]} × ${dimensions[1]}`
    );
  }

  return undefined;
}


function formatObservationDate(
  value: string
): string {

  const parsed =
    new Date(value);

  if (
    Number.isNaN(
      parsed.getTime()
    )
  ) {
    return value;
  }

  return formatDate(
    parsed
  );
}


function formatAcquisitionTime(
  value: string
): string {

  const parsed =
    new Date(value);

  if (
    Number.isNaN(
      parsed.getTime()
    )
  ) {
    return 'Not available';
  }

  return (
    `${parsed.toISOString().substring(11, 19)} UTC`
  );
}


function formatOptionalPercentage(
  value: unknown
): string {

  if (
    value === null ||
    value === undefined ||
    value === ''
  ) {
    return 'Not available';
  }

  const numeric =
    Number(value);

  if (
    Number.isFinite(
      numeric
    )
  ) {
    return `${numeric.toFixed(1)}%`;
  }

  return String(
    value
  );
}


function findMetadataValue(
  object: Record<string, unknown>,
  keys: string[]
): unknown {

  for (
    const key of keys
  ) {
    if (
      object[key] !== undefined &&
      object[key] !== null
    ) {
      return object[key];
    }
  }

  return undefined;
}





function formatModelAccuracy(
  value: unknown
): string {

  if (
    value === null ||
    value === undefined ||
    value === ''
  ) {
    return 'Not reported';
  }

  if (
    typeof value === 'number' &&
    Number.isFinite(value)
  ) {

    if (
      value >= 0 &&
      value <= 1
    ) {
      return `${Math.round(value * 100)}%`;
    }

    return `${value}%`;
  }

  return String(
    value
  );
}


function normalizeModelStatus(
  value: unknown
): string {

  if (
    !value
  ) {
    return 'AVAILABLE';
  }

  return String(
    value
  ).toUpperCase();
}