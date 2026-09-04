import {
  useState,
  useEffect,
  useRef,
} from 'react';

import type {
  ActiveView,
  Observation,
  AnalysisResult,
  QueryHistoryItem,
  DemoScenario,
  ModalityType,
} from './types/satquery';

import { DEMO_SCENARIOS } from './data/demoScenarios';

import {
  satQueryService,
} from './services/satQueryService';

import { HeaderBar } from './components/navigation/HeaderBar';
import { LandingPage } from './components/landing/LandingPage';
import { ObservationPanel } from './components/observation/ObservationPanel';
import { EarthCanvas } from './components/earth/EarthCanvas';
import { QueryInterface } from './components/query/QueryInterface';
import { AnalysisStatusModal } from './components/analysis/AnalysisStatusModal';
import { ResultPanel } from './components/result/ResultPanel';
import { AnalysisReplayModal } from './components/replay/AnalysisReplayModal';
import { HistoryView } from './components/history/HistoryView';
import { DemoSelectorModal } from './components/demo/DemoSelectorModal';
import { SatelliteSearchModal } from './components/observation/SatelliteSearchModal';
import { SettingsModal } from './components/settings/SettingsModal';
import { LiveSpaceBackground } from './components/background/LiveSpaceBackground';


// ============================================================
// HELPERS
// ============================================================

function getObservationFilePath(
  observation: Observation
): string | undefined {
  const candidate =
    observation as any;

  return (
    candidate.filePath ||
    candidate.file_path ||
    candidate.localPath ||
    candidate.local_path ||
    candidate.metadata?.filePath ||
    candidate.metadata?.file_path
  );
}


function getObservationSourceType(
  observation: Observation
): string | undefined {
  const candidate =
    observation as any;

  return (
    candidate.sourceType ||
    candidate.source_type ||
    candidate.metadata?.sourceType ||
    candidate.metadata?.source_type
  );
}


function getObservationIngestionStatus(
  observation: Observation
): string | undefined {
  const candidate =
    observation as any;

  return (
    candidate.ingestionStatus ||
    candidate.ingestion_status ||
    candidate.metadata?.ingestionStatus ||
    candidate.metadata?.ingestion_status
  );
}


function getObservationProductId(
  observation: Observation
): string | undefined {
  const candidate =
    observation as any;

  return (
    candidate.productId ||
    candidate.product_id ||
    candidate.metadata?.productId ||
    candidate.metadata?.product_id
  );
}


function isDemoObservation(
  observation: Observation
): boolean {
  const sourceType =
    getObservationSourceType(
      observation
    );

  return (
    observation.isDemo === true ||
    sourceType === 'demo' ||
    sourceType === 'sample'
  );
}


function getObservationImageUrl(
  observation: Observation
): string | undefined {
  const candidate =
    observation as any;

  return (
    candidate.imageUrl ||
    candidate.image_url ||
    candidate.url ||
    candidate.thumbnailUrl ||
    candidate.thumbnail_url ||
    candidate.metadata?.imageUrl ||
    candidate.metadata?.image_url ||
    candidate.metadata?.url ||
    candidate.metadata?.thumbnailUrl ||
    candidate.metadata?.thumbnail_url
  );
}

function observationHasModelAsset(
  observation: Observation
): boolean {
  if (
    isDemoObservation(
      observation
    )
  ) {
    return true;
  }

  const filePath =
    getObservationFilePath(
      observation
    );

  if (
    filePath
  ) {
    return true;
  }

  const imageUrl =
    getObservationImageUrl(
      observation
    );

  if (
    imageUrl
  ) {
    return true;
  }

  const ingestionStatus =
    getObservationIngestionStatus(
      observation
    );

  return (
    ingestionStatus === 'ready' ||
    ingestionStatus === 'downloaded' ||
    ingestionStatus === 'ingested' ||
    ingestionStatus === 'local' ||
    ingestionStatus === 'metadata_only' ||
    ingestionStatus === 'selected'
  );
}


function normalizeModality(
  modality: unknown
): ModalityType {
  const value =
    String(
      modality ||
      'OPTICAL'
    )
      .trim()
      .toUpperCase();

  if (
    value === 'SAR' ||
    value === 'RADAR'
  ) {
    return 'SAR';
  }

  if (
    value === 'MULTISPECTRAL' ||
    value === 'MULTI-SPECTRAL' ||
    value === 'MS'
  ) {
    return 'MULTISPECTRAL';
  }

  if (
    value === 'THERMAL'
  ) {
    return 'THERMAL';
  }

  return 'OPTICAL';
}


// ============================================================
// APP
// ============================================================

export function App() {

  // ==========================================================
  // NAVIGATION
  // ==========================================================

  const [
    activeView,
    setActiveView,
  ] = useState<ActiveView>(
    'LANDING'
  );

  const [
    isSearchModalOpen,
    setIsSearchModalOpen,
  ] = useState<boolean>(
    false
  );

  const [
    isSettingsOpen,
    setIsSettingsOpen,
  ] = useState<boolean>(
    false
  );


  // ==========================================================
  // THEME
  // ==========================================================

  const [
    theme,
    setTheme,
  ] = useState<
    'dark' | 'light'
  >(() => {

    try {

      const saved =
        localStorage.getItem(
          'satquery_theme'
        );

      return (
        saved === 'dark'
          ? 'dark'
          : 'light'
      );

    } catch {

      return 'light';
    }
  });


  useEffect(() => {

    try {

      localStorage.setItem(
        'satquery_theme',
        theme
      );

    } catch {
      // Ignore localStorage failures.
    }

    const root =
      document.documentElement;

    if (
      theme === 'light'
    ) {

      root.classList.add(
        'light'
      );

      root.classList.remove(
        'dark'
      );

    } else {

      root.classList.add(
        'dark'
      );

      root.classList.remove(
        'light'
      );
    }

  }, [
    theme,
  ]);


  const handleToggleTheme =
    () => {

      setTheme(
        previous =>
          previous === 'dark'
            ? 'light'
            : 'dark'
      );
    };


  // ==========================================================
  // OBSERVATIONS
  // ==========================================================

  const [
    observations,
    setObservations,
  ] = useState<Observation[]>(
    DEMO_SCENARIOS[2].observations
  );

  const [
    activeObservationIds,
    setActiveObservationIds,
  ] = useState<string[]>(
    DEMO_SCENARIOS[2]
      .observations
      .map(
        observation =>
          observation.id
      )
  );


  // ==========================================================
  // ANALYSIS RESULT
  // ==========================================================

  const [
    activeResult,
    setActiveResult,
  ] = useState<AnalysisResult | null>(
    null
  );

  const [
    selectedRegionId,
    setSelectedRegionId,
  ] = useState<string | null>(
    null
  );


  // ==========================================================
  // ANALYSIS STATE
  // ==========================================================

  const [
    isAnalyzing,
    setIsAnalyzing,
  ] = useState<boolean>(
    false
  );

  const [
    analysisStepIndex,
    setAnalysisStepIndex,
  ] = useState<number>(
    0
  );

  const [
    analysisStepLabel,
    setAnalysisStepLabel,
  ] = useState<string>(
    ''
  );

  const [
    currentQueryText,
    setCurrentQueryText,
  ] = useState<string>(
    ''
  );


  // ==========================================================
  // USER FEEDBACK / ERROR
  // ==========================================================

  const [
    appError,
    setAppError,
  ] = useState<string | null>(
    null
  );


  // ==========================================================
  // OTHER UI STATE
  // ==========================================================

  const [
    isReplayOpen,
    setIsReplayOpen,
  ] = useState<boolean>(
    false
  );

  const [
    isDemoModalOpen,
    setIsDemoModalOpen,
  ] = useState<boolean>(
    false
  );

  const [
    currentDemoId,
    setCurrentDemoId,
  ] = useState<string>(
    'demo-03'
  );

  const [
    historyItems,
    setHistoryItems,
  ] = useState<QueryHistoryItem[]>(
    []
  );

  const [
    isObservationDrawerOpen,
    setIsObservationDrawerOpen,
  ] = useState<boolean>(
    false
  );


  // ==========================================================
  // WORKFLOW REF
  // ==========================================================

  const workflowRef =
    useRef<HTMLDivElement>(
      null
    );


  const handleScrollToWorkflow =
    () => {

      if (
        activeView !==
        'LANDING'
      ) {

        setActiveView(
          'LANDING'
        );

        setTimeout(
          () => {
            workflowRef.current
              ?.scrollIntoView({
                behavior:
                  'smooth',
              });
          },
          100
        );

      } else {

        workflowRef.current
          ?.scrollIntoView({
            behavior:
              'smooth',
          });
      }
    };


  // ==========================================================
  // INITIAL HISTORY LOAD
  // ==========================================================

  useEffect(() => {

    let cancelled =
      false;

    const loadHistory =
      async () => {

        try {

          const history =
            await satQueryService
              .getHistory();

          if (
            !cancelled
          ) {
            setHistoryItems(
              history
            );
          }

        } catch (
        error
        ) {

          console.warn(
            'Unable to load SatQuery history:',
            error
          );
        }
      };

    loadHistory();

    return () => {
      cancelled = true;
    };

  }, []);


  // ==========================================================
  // OBSERVATION SELECT / DESELECT
  // ==========================================================

  const handleToggleObservation =
    (
      id: string
    ) => {

      setActiveObservationIds(
        previous => {

          if (
            previous.includes(
              id
            )
          ) {

            // Do not allow zero active observations.
            if (
              previous.length ===
              1
            ) {
              return previous;
            }

            return previous.filter(
              itemId =>
                itemId !== id
            );

          }

          return [
            ...previous,
            id,
          ];
        }
      );

      // A changed observation selection means an old
      // result may no longer represent the active inputs.
      setActiveResult(
        null
      );

      setSelectedRegionId(
        null
      );
    };


  // ==========================================================
  // LOCAL UPLOAD
  // ==========================================================

  const handleAddObservation =
    async (
      file: File,
      modality: ModalityType
    ) => {

      setAppError(
        null
      );

      try {

        const newObservation =
          await satQueryService
            .uploadObservation(
              file,
              file.name.replace(
                /\.[^/.]+$/,
                ''
              ),
              modality
            );

        setObservations(
          previous => [
            newObservation,
            ...previous,
          ]
        );

        // New upload becomes the only active input.
        setActiveObservationIds([
          newObservation.id,
        ]);

        setActiveResult(
          null
        );

        setSelectedRegionId(
          null
        );

        setActiveView(
          'WORKSPACE'
        );

        // Keep drawer open if the user needs to inspect the
        // newly uploaded observation.
        setIsObservationDrawerOpen(
          false
        );

      } catch (
      error
      ) {

        console.error(
          'Observation upload failed:',
          error
        );

        setAppError(
          error instanceof Error
            ? error.message
            : 'Unable to upload the observation.'
        );
      }
    };


  // ==========================================================
  // CDSE PRODUCT INGESTION
  // ==========================================================

  const handleAddObservationFromProduct =
    async (
      productOrObservation: any
    ) => {

      setAppError(
        null
      );

      try {

        // ------------------------------------------------------
        // The updated SatelliteSearchModal sends the already
        // ingested Observation returned by the backend.
        //
        // Keep a compatibility path for callers that still
        // provide a raw CDSE product object.
        // ------------------------------------------------------

        const candidate =
          productOrObservation as any;

        const hasObservationIdentity =
          Boolean(
            candidate &&
            candidate.id &&
            (
              candidate.sourceType ||
              candidate.source_type ||
              candidate.ingestionStatus ||
              candidate.ingestion_status
            )
          );

        let observation:
          Observation;

        if (
          hasObservationIdentity &&
          candidate.filename
        ) {

          observation =
            candidate as Observation;

        } else {

          // ----------------------------------------------------
          // Legacy/raw product compatibility.
          //
          // IMPORTANT:
          // Never construct a fake READY observation.
          // Delegate ingestion to the backend instead.
          // ----------------------------------------------------

          const productId =
            candidate?.product_id ||
            candidate?.productId ||
            candidate?.id;

          if (
            !productId
          ) {
            throw new Error(
              'The selected Copernicus product has no product ID.'
            );
          }

          const modality =
            normalizeModality(
              candidate?.modality
            );

          observation =
            await satQueryService
              .ingestCopernicusProduct(
                String(
                  productId
                ),
                modality,
                true
              );
        }

        // ------------------------------------------------------
        // Verify that CDSE ingestion actually produced a
        // model-readable local asset.
        // ------------------------------------------------------

        if (
          !observationHasModelAsset(
            observation
          )
        ) {

          const productId =
            getObservationProductId(
              observation
            ) ||
            'selected product';

          throw new Error(
            `The Copernicus product "${productId}" was selected, ` +
            `but the backend did not return a model-readable ` +
            `analysis asset. The product has not been marked READY.`
          );
        }

        // ------------------------------------------------------
        // Make sure it's represented as a real external
        // observation rather than a demo.
        // ------------------------------------------------------

        const normalizedObservation =
          {
            ...observation,

            isDemo:
              false,

            status:
              'READY',
          } as Observation;

        // ------------------------------------------------------
        // Replace same observation if it already exists.
        // ------------------------------------------------------

        setObservations(
          previous => {

            const withoutDuplicate =
              previous.filter(
                existing =>
                  existing.id !==
                  normalizedObservation.id
              );

            return [
              normalizedObservation,
              ...withoutDuplicate,
            ];
          }
        );

        // ------------------------------------------------------
        // Activate only the new CDSE observation.
        // ------------------------------------------------------

        setActiveObservationIds([
          normalizedObservation.id,
        ]);

        setActiveResult(
          null
        );

        setSelectedRegionId(
          null
        );

        setActiveView(
          'WORKSPACE'
        );

        setIsObservationDrawerOpen(
          false
        );

      } catch (
      error
      ) {

        console.error(
          'Copernicus observation ingestion failed:',
          error
        );

        setAppError(
          error instanceof Error
            ? error.message
            : 'Unable to ingest the Copernicus product.'
        );
      }
    };


  // ==========================================================
  // EXECUTE QUERY
  // ==========================================================

  const handleExecuteQuery =
    async (
      queryText: string
    ) => {

      const query =
        String(
          queryText || ''
        ).trim();

      setAppError(
        null
      );

      if (
        !query
      ) {

        setAppError(
          'Please enter a question before running analysis.'
        );

        return;
      }

      const activeObs =
        observations.filter(
          observation =>
            activeObservationIds
              .includes(
                observation.id
              )
        );

      if (
        activeObs.length ===
        0
      ) {

        setAppError(
          'Select at least one observation before running analysis.'
        );

        return;
      }

      // --------------------------------------------------------
      // Important:
      // Do not send catalogue-only observations to the backend.
      // --------------------------------------------------------

      const invalidObservation =
        activeObs.find(
          observation =>
            !observationHasModelAsset(
              observation
            )
        );

      if (
        invalidObservation
      ) {

        const productId =
          getObservationProductId(
            invalidObservation
          );

        setAppError(
          productId
            ? `Satellite product ${productId} has not been ingested into a model-readable asset yet.`
            : `Observation "${invalidObservation.name}" is not connected to a model-readable backend asset.`
        );

        return;
      }

      setCurrentQueryText(
        query
      );

      setIsAnalyzing(
        true
      );

      setAnalysisStepIndex(
        0
      );

      setAnalysisStepLabel(
        'Understanding request & parsing intent'
      );

      setSelectedRegionId(
        null
      );

      try {

        const result =
          await satQueryService
            .submitQuery(
              query,
              activeObs,
              (
                stepIndex,
                label
              ) => {

                setAnalysisStepIndex(
                  stepIndex
                );

                setAnalysisStepLabel(
                  label
                );
              }
            );

        setActiveResult(
          result
        );

        // Refresh audit history from backend/session.
        try {

          const updatedHistory =
            await satQueryService
              .getHistory();

          setHistoryItems(
            updatedHistory
          );

        } catch (
        historyError
        ) {

          console.warn(
            'Unable to refresh analysis history:',
            historyError
          );
        }

      } catch (
      error
      ) {

        console.error(
          'Analysis execution error:',
          error
        );

        setActiveResult(
          null
        );

        setAppError(
          error instanceof Error
            ? error.message
            : 'SatQuery analysis failed.'
        );

      } finally {

        setIsAnalyzing(
          false
        );
      }
    };


  // ==========================================================
  // LOAD DEMO
  // ==========================================================

  const handleSelectDemoScenario =
    (
      scenario: DemoScenario
    ) => {

      setCurrentDemoId(
        scenario.id
      );

      setObservations(
        scenario.observations
      );

      setActiveObservationIds(
        scenario.observations.map(
          observation =>
            observation.id
        )
      );

      setActiveResult(
        scenario.presetResult
      );

      setSelectedRegionId(
        null
      );

      setAppError(
        null
      );

      setActiveView(
        'WORKSPACE'
      );
    };


  // ==========================================================
  // HISTORY → WORKSPACE
  // ==========================================================

  const handleOpenHistoryResult =
    (
      item: QueryHistoryItem
    ) => {

      setActiveResult(
        item.result
      );

      setSelectedRegionId(
        null
      );

      setAppError(
        null
      );

      setActiveView(
        'WORKSPACE'
      );
    };


  // ==========================================================
  // RENDER
  // ==========================================================

  return (
    <div
      className="
        min-h-screen
        bg-transparent
        text-sat-text
        flex
        flex-col
        font-sans
        selection:bg-sat-accent/30
        selection:text-sat-accent
        transition-colors
        duration-200
        relative
        overflow-x-hidden
      "
    >

      {/* ====================================================
          BACKGROUND
      ==================================================== */}

      <LiveSpaceBackground />


      {/* ====================================================
          HEADER
      ==================================================== */}

      <HeaderBar
        activeView={
          activeView
        }

        setActiveView={
          setActiveView
        }

        theme={
          theme
        }

        onToggleTheme={
          handleToggleTheme
        }

        activeDemoId={
          currentDemoId
        }

        onOpenDemoSelector={() =>
          setIsDemoModalOpen(
            true
          )
        }

        onOpenSettings={() =>
          setIsSettingsOpen(
            true
          )
        }

        onScrollToWorkflow={
          handleScrollToWorkflow
        }
      />


      {/* ====================================================
          MAIN
      ==================================================== */}

      <div
        className="
          flex-1
          flex
          flex-col
          overflow-hidden
          z-10
          relative
        "
      >

        {/* ==================================================
            LANDING
        ================================================== */}

        {activeView ===
          'LANDING' && (
            <LandingPage
              workflowRef={
                workflowRef
              }

              onEnterWorkspace={() =>
                setActiveView(
                  'WORKSPACE'
                )
              }

              onViewDemo={() =>
                setIsDemoModalOpen(
                  true
                )
              }
            />
          )}


        {/* ==================================================
            WORKSPACE
        ================================================== */}

        {activeView ===
          'WORKSPACE' && (

            <div
              className="
              flex-1
              flex
              flex-col
              overflow-y-auto
              min-h-0
            "
            >

              {/* ==================================================
                APP ERROR
            ================================================== */}

              {appError && (
                <div
                  className="
                  mx-4
                  mt-3
                  rounded-xl
                  border
                  border-sat-border
                  bg-sat-surface
                  px-4
                  py-3
                  text-sm
                  text-sat-text
                  shadow-lg
                "
                >

                  <div
                    className="
                    flex
                    items-start
                    justify-between
                    gap-4
                  "
                  >

                    <div>

                      <div
                        className="
                        font-semibold
                        text-sat-text
                      "
                      >
                        Analysis / data error
                      </div>

                      <div
                        className="
                        mt-1
                        text-xs
                        text-sat-muted
                      "
                      >
                        {appError}
                      </div>

                    </div>

                    <button
                      type="button"
                      onClick={() =>
                        setAppError(
                          null
                        )
                      }
                      className="
                      shrink-0
                      text-xs
                      font-semibold
                      text-sat-muted
                      hover:text-sat-text
                    "
                    >
                      DISMISS
                    </button>

                  </div>

                </div>
              )}


              {/* ==================================================
                TWO-ZONE WORKSPACE
            ================================================== */}

              <div
                className="
                flex-none
                h-[calc(100vh-3.5rem)]
                grid
                grid-cols-1
                lg:grid-cols-9
                overflow-hidden
                border-b
                border-sat-border
                relative
              "
              >

                {/* ==================================================
                  EARTH CANVAS
              ================================================== */}

                <div
                  className="
                  lg:col-span-6
                  h-full
                  overflow-hidden
                  border-b
                  lg:border-b-0
                  lg:border-r
                  border-sat-border
                  relative
                "
                >

                  {/* Observation drawer button */}

                  <button
                    onClick={() =>
                      setIsObservationDrawerOpen(
                        true
                      )
                    }
                    className="
                    absolute
                    top-3
                    left-3
                    z-20
                    flex
                    items-center
                    gap-1.5
                    px-3
                    py-1.5
                    rounded
                    bg-sat-surface/90
                    backdrop-blur
                    border
                    border-sat-border
                    hover:border-sat-accent
                    text-xs
                    font-mono
                    text-sat-text
                    hover:text-sat-accent
                    transition-colors
                    shadow-md
                  "
                  >
                    🛰️ Images ({
                      observations.length
                    })
                  </button>


                  <EarthCanvas
                    observations={
                      observations
                    }

                    activeObservationIds={
                      activeObservationIds
                    }

                    activeResult={
                      activeResult
                    }

                    selectedRegionId={
                      selectedRegionId
                    }

                    onSelectRegion={
                      setSelectedRegionId
                    }

                    onSelectDemoScenario={
                      (
                        demoId
                      ) => {

                        const scenario =
                          DEMO_SCENARIOS.find(
                            item =>
                              item.id ===
                              demoId
                          );

                        if (
                          scenario
                        ) {
                          handleSelectDemoScenario(
                            scenario
                          );
                        }
                      }
                    }
                  />

                </div>


                {/* ==================================================
                  QUERY INTERFACE
              ================================================== */}

                <div
                  className="
                  lg:col-span-3
                  h-full
                  overflow-hidden
                "
                >

                  <QueryInterface
                    observations={
                      observations
                    }

                    activeObservationIds={
                      activeObservationIds
                    }

                    onExecuteQuery={
                      handleExecuteQuery
                    }

                    isAnalyzing={
                      isAnalyzing
                    }
                  />

                </div>


                {/* ==================================================
                  OBSERVATION DRAWER
              ================================================== */}

                {isObservationDrawerOpen && (
                  <div
                    className="
                    fixed
                    inset-0
                    z-50
                    flex
                  "
                  >

                    {/* Overlay */}

                    <div
                      className="
                      absolute
                      inset-0
                      bg-black/60
                      backdrop-blur-sm
                    "
                      onClick={() =>
                        setIsObservationDrawerOpen(
                          false
                        )
                      }
                    />


                    {/* Drawer */}

                    <div
                      className="
                      relative
                      w-full
                      max-w-lg
                      md:w-[480px]
                      h-full
                      bg-sat-surface
                      border-r
                      border-sat-border
                      shadow-2xl
                      overflow-y-auto
                    "
                    >

                      {/* Drawer header */}

                      <div
                        className="
                        flex
                        items-center
                        justify-between
                        p-4
                        border-b
                        border-sat-border
                        bg-sat-panel
                      "
                      >

                        <span
                          className="
                          font-mono
                          text-sm
                          font-bold
                          uppercase
                          tracking-wider
                          text-sat-text
                        "
                        >
                          🛰️ SATELLITE DATASETS ({
                            observations.length
                          })
                        </span>

                        <button
                          onClick={() =>
                            setIsObservationDrawerOpen(
                              false
                            )
                          }
                          className="
                          text-sat-dim
                          hover:text-sat-accent
                          transition-colors
                          px-2
                          py-1
                          font-mono
                          text-sm
                          font-bold
                        "
                          aria-label="Close observation drawer"
                        >
                          ✕ CLOSE
                        </button>

                      </div>


                      <ObservationPanel
                        observations={
                          observations
                        }

                        activeObservationIds={
                          activeObservationIds
                        }

                        onToggleObservation={
                          handleToggleObservation
                        }

                        onAddObservation={
                          handleAddObservation
                        }

                        onAddObservationFromProduct={
                          handleAddObservationFromProduct
                        }

                        onOpenSearchModal={() =>
                          setIsSearchModalOpen(
                            true
                          )
                        }

                        onSelectDemoScenario={
                          (
                            demoId
                          ) => {

                            const scenario =
                              DEMO_SCENARIOS.find(
                                item =>
                                  item.id ===
                                  demoId
                              );

                            if (
                              scenario
                            ) {

                              handleSelectDemoScenario(
                                scenario
                              );

                              setIsObservationDrawerOpen(
                                false
                              );
                            }
                          }
                        }
                      />

                    </div>

                  </div>
                )}

              </div>


              {/* ==================================================
                RESULT PANEL
            ================================================== */}

              {activeResult &&
                !isAnalyzing && (
                  <ResultPanel
                    result={
                      activeResult
                    }

                    selectedRegionId={
                      selectedRegionId
                    }

                    onSelectRegion={
                      setSelectedRegionId
                    }

                    onOpenReplay={() =>
                      setIsReplayOpen(
                        true
                      )
                    }

                    onFollowUpQuery={
                      handleExecuteQuery
                    }
                  />
                )}

            </div>
          )}


        {/* ==================================================
            HISTORY
        ================================================== */}

        {activeView ===
          'HISTORY' && (

            <div
              className="
              flex-1
              overflow-y-auto
              bg-transparent
            "
            >

              <HistoryView
                historyItems={
                  historyItems
                }

                onOpenHistoryResult={
                  handleOpenHistoryResult
                }
              />

            </div>
          )}

      </div>


      {/* ====================================================
          ANALYSIS PROGRESS
      ==================================================== */}

      {isAnalyzing && (
        <AnalysisStatusModal
          currentStepIndex={
            analysisStepIndex
          }

          currentStepLabel={
            analysisStepLabel
          }

          queryText={
            currentQueryText
          }
        />
      )}


      {/* ====================================================
          REPLAY
      ==================================================== */}

      {isReplayOpen &&
        activeResult && (
          <AnalysisReplayModal
            result={
              activeResult
            }

            onClose={() =>
              setIsReplayOpen(
                false
              )
            }
          />
        )}


      {/* ====================================================
          DEMO SELECTOR
      ==================================================== */}

      {isDemoModalOpen && (
        <DemoSelectorModal
          onSelectScenario={
            (
              scenario
            ) => {

              handleSelectDemoScenario(
                scenario
              );

              setIsDemoModalOpen(
                false
              );
            }
          }

          onClose={() =>
            setIsDemoModalOpen(
              false
            )
          }

          currentDemoId={
            currentDemoId
          }
        />
      )}


      {/* ====================================================
          CDSE SEARCH
      ==================================================== */}

      <SatelliteSearchModal
        isOpen={
          isSearchModalOpen
        }

        onClose={() =>
          setIsSearchModalOpen(
            false
          )
        }

        onAddObservation={
          handleAddObservation
        }

        onAddProductAsObservation={
          handleAddObservationFromProduct
        }
      />


      {/* ====================================================
          SETTINGS
      ==================================================== */}

      <SettingsModal
        isOpen={
          isSettingsOpen
        }

        onClose={() =>
          setIsSettingsOpen(
            false
          )
        }
      />

    </div>
  );
}


export default App;