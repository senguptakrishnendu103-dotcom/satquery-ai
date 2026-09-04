import type {
  Observation,
  AnalysisResult,
  QueryHistoryItem,
  ModalityType,
  ExecutionInput,
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


type BackendSearchResponse = {
  status: string;
  provider: string;
  count: number;
  products: any[];
};


type BackendIngestResponse = {
  status: string;
  message?: string;
  observation: any;
  downloaded?: boolean;
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
// observations from appearing in a real CDSE analysis session.
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

    const bands =
      Array.isArray(
        realMeta.bands
      )
        ? realMeta.bands
        : [];

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

        bands:
          bands.length > 0
            ? `${bands.length} Channels (${bands.join(', ')})`
            : 'Band information unavailable',

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
  // GET OBSERVATIONS
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


  // ==========================================================
  // SEARCH SATELLITE CATALOGUE
  // ==========================================================

  async searchSatelliteCatalogue(
    params: {
      provider?: string;

      bbox: number[];

      start_date: string;
      end_date: string;

      collection?: string;

      max_cloud_cover?: number;

      limit?: number;
    }
  ): Promise<BackendSearchResponse> {

    if (
      !Array.isArray(
        params.bbox
      ) ||
      params.bbox.length !== 4
    ) {
      throw new Error(
        'A valid bounding box is required for satellite search.'
      );
    }

    return fetchJson<BackendSearchResponse>(
      '/api/data-sources/search',
      {
        method:
          'POST',

        headers: {
          'Content-Type':
            'application/json',
        },

        body:
          JSON.stringify({
            provider:
              params.provider ||
              'copernicus',

            bbox:
              params.bbox,

            start_date:
              params.start_date,

            end_date:
              params.end_date,

            collection:
              params.collection ||
              'sentinel-2-l2a',

            max_cloud_cover:
              params.max_cloud_cover ??
              null,

            limit:
              params.limit ||
              10,
          }),
      }
    );
  },


  // ==========================================================
  // GET SATELLITE PROVIDERS
  // ==========================================================

  async getSatelliteProviders():
    Promise<any[]> {

    const data =
      await fetchJson<{
        providers?: any[];
      }>(
        '/api/data-sources/providers'
      );

    return Array.isArray(
      data.providers
    )
      ? data.providers
      : [];
  },


  // ==========================================================
  // SATELLITE PROVIDER HEALTH
  // ==========================================================

  async getSatelliteProviderHealth():
    Promise<any> {

    return fetchJson<any>(
      '/api/data-sources/health'
    );
  },


  // ==========================================================
  // GET CDSE PRODUCT
  // ==========================================================

  async getCopernicusProduct(
    productId: string
  ): Promise<any> {

    if (
      !productId ||
      !productId.trim()
    ) {
      throw new Error(
        'CDSE product ID is required.'
      );
    }

    return fetchJson<any>(
      `/api/data-sources/copernicus/product/${encodeURIComponent(
        productId
      )}`
    );
  },


  // ==========================================================
  // INGEST CDSE PRODUCT
  // ==========================================================

  async ingestCopernicusProduct(
    productId: string,
    modality: ModalityType = 'OPTICAL',
    downloadProduct = true
  ): Promise<Observation> {

    if (
      !productId ||
      !productId.trim()
    ) {
      throw new Error(
        'CDSE product ID is required.'
      );
    }

    const response =
      await fetchJson<BackendIngestResponse>(
        '/api/data-sources/copernicus/ingest',
        {
          method:
            'POST',

          headers: {
            'Content-Type':
              'application/json',
          },

          body:
            JSON.stringify({
              product_id:
                productId,

              modality:
                normalizeModalityForBackend(
                  modality
                ),

              download_product:
                downloadProduct,
            }),
        }
      );

    if (
      !response.observation
    ) {
      throw new Error(
        'CDSE ingestion succeeded but no observation was returned.'
      );
    }

    const observation =
      normalizeCDSEObservation(
        response.observation,
        modality
      );

    // Replace an existing observation with same ID.
    userObservations =
      userObservations.filter(
        (item) =>
          item.id !==
          observation.id
      );

    userObservations.unshift(
      observation
    );

    return observation;
  },


  // ==========================================================
  // GET COPERNICUS QUICKLOOK URL
  // ==========================================================

  getCopernicusQuicklookUrl(
    productId: string
  ): string {

    return (
      `/api/data-sources/copernicus/quicklook/${encodeURIComponent(
        productId
      )}`
    );
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
// CDSE OBSERVATION NORMALIZATION
// ============================================================

function normalizeCDSEObservation(
  raw: any,
  modality: ModalityType
): Observation {

  const productId =
    raw.product_id ||
    raw.productId;

  const quicklook =
    raw.image_url ||
    raw.imageUrl ||
    raw.thumbnail_url ||
    raw.thumbnailUrl ||
    (
      productId
        ? satQueryService
          .getCopernicusQuicklookUrl(
            String(productId)
          )
        : ''
    );

  const acquisitionDate =
    raw.acquisition_date ||
    raw.acquisitionDate ||
    null;

  const localPath =
    raw.file_path ||
    raw.local_path ||
    undefined;

  const metadata =
    isRecord(
      raw.product_metadata
    )
      ? raw.product_metadata
      : {};

  return {
    id:
      raw.id ||
      `cdse-${productId || Date.now()}`,

    name:
      raw.name ||
      raw.filename ||
      productId ||
      'Copernicus observation',

    filename:
      raw.filename ||
      raw.name ||
      productId ||
      'Copernicus observation',

    modality:
      modality,

    date:
      acquisitionDate
        ? formatObservationDate(
          acquisitionDate
        )
        : 'DATE NOT AVAILABLE',

    dimensions:
      formatDimensions(
        raw.dimensions
      ) || 'Unknown',

    status:
      localPath
        ? 'READY'
        : 'READY',


    metadata: {
      ...metadata,

      analysis_asset:
        raw.analysis_asset ||
        metadata.analysis_asset,

      remote_analysis_asset:
        raw.remote_analysis_asset ||
        metadata.remote_analysis_asset,

      analysis_asset_url:
        raw.analysis_asset_url ||
        metadata.analysis_asset_url,

      remote_asset_url:
        raw.remote_asset_url ||
        metadata.remote_asset_url,

      assets:
        raw.assets ||
        metadata.assets,

      sensor:
        raw.sensor ||
        raw.platform ||
        metadata.platform,

      lat:
        calculateCenterLatitude(
          raw.bbox ||
          metadata.bbox
        ),

      lon:
        calculateCenterLongitude(
          raw.bbox ||
          metadata.bbox
        ),

      cloudCover:
        formatOptionalPercentage(
          raw.cloud_cover ??
          metadata.cloud_cover
        ),

      bands:
        Array.isArray(
          raw.available_bands
        )
          ? `${raw.available_bands.length} Channels (${raw.available_bands.join(', ')})`
          : 'Band information unavailable',

      groundSamplingDistance:
        typeof raw.resolution === 'number'
          ? `${raw.resolution}m/px`
          : 'Not available',

      acquisitionTime:
        acquisitionDate
          ? formatAcquisitionTime(
            acquisitionDate
          )
          : 'Not available',

      provider:
        raw.provider ||
        'copernicus',

      productId:
        productId,

      product_id:
        productId,

      processingLevel:
        raw.processing_level,

      collection:
        raw.collection,

      crs:
        raw.crs,

      geoFootprint:
        raw.geo_footprint,
    },

    imageUrl:
      quicklook,

    thumbnailUrl:
      quicklook,

    isDemo:
      false,

    ...((
      {
        filePath:
          localPath,

        file_path:
          localPath,

        localPath:
          localPath,

        local_path:
          localPath,

        sourceType:
          raw.source_type ||
          'copernicus',

        source_type:
          raw.source_type ||
          'copernicus',

        ingestionStatus:
          raw.ingestion_status ||
          (
            localPath
              ? 'downloaded'
              : 'catalogue_only'
          ),

        ingestion_status:
          raw.ingestion_status ||
          (
            localPath
              ? 'downloaded'
              : 'catalogue_only'
          ),

        acquisitionDate:
          acquisitionDate,

        acquisition_date:
          acquisitionDate,

        provider:
          raw.provider ||
          'copernicus',

        productId:
          productId,

        product_id:
          productId,
      } as any
    )),
  } as Observation;
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


function calculateCenterLatitude(
  bbox: unknown
): number | undefined {

  if (
    !Array.isArray(
      bbox
    ) ||
    bbox.length < 4
  ) {
    return undefined;
  }

  const minLat =
    Number(bbox[1]);

  const maxLat =
    Number(bbox[3]);

  if (
    !Number.isFinite(minLat) ||
    !Number.isFinite(maxLat)
  ) {
    return undefined;
  }

  return (
    minLat +
    maxLat
  ) / 2;
}


function calculateCenterLongitude(
  bbox: unknown
): number | undefined {

  if (
    !Array.isArray(
      bbox
    ) ||
    bbox.length < 4
  ) {
    return undefined;
  }

  const minLon =
    Number(bbox[0]);

  const maxLon =
    Number(bbox[2]);

  if (
    !Number.isFinite(minLon) ||
    !Number.isFinite(maxLon)
  ) {
    return undefined;
  }

  return (
    minLon +
    maxLon
  ) / 2;
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