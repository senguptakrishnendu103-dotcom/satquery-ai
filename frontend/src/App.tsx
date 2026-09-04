import { useState, useEffect, useRef } from 'react';
import type { ActiveView, Observation, AnalysisResult, QueryHistoryItem, DemoScenario, ModalityType } from './types/satquery';
import { DEMO_SCENARIOS } from './data/demoScenarios';
import { satQueryService } from './services/satQueryService';
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


export function App() {
  // Navigation State (Default to LANDING overview page upon page refresh)
  const [activeView, setActiveView] = useState<ActiveView>('LANDING');
  const [isSearchModalOpen, setIsSearchModalOpen] = useState<boolean>(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState<boolean>(false);

  // Theme State ('dark' | 'light') - Default to Cozy Warm White Theme
  const [theme, setTheme] = useState<'dark' | 'light'>(() => {
    const saved = localStorage.getItem('satquery_theme');
    return saved === 'dark' ? 'dark' : 'light';
  });

  useEffect(() => {
    localStorage.setItem('satquery_theme', theme);
    const root = document.documentElement;
    if (theme === 'light') {
      root.classList.add('light');
      root.classList.remove('dark');
    } else {
      root.classList.add('dark');
      root.classList.remove('light');
    }
  }, [theme]);

  const handleToggleTheme = () => {
    setTheme(prev => (prev === 'dark' ? 'light' : 'dark'));
  };

  // Observations State (Defaulting to Demo 03: Bi-temporal change)
  const [observations, setObservations] = useState<Observation[]>(DEMO_SCENARIOS[2].observations);
  const [activeObservationIds, setActiveObservationIds] = useState<string[]>(
    DEMO_SCENARIOS[2].observations.map(o => o.id)
  );

  // Analysis Result & Evidence Inspection State
  const [activeResult, setActiveResult] = useState<AnalysisResult | null>(DEMO_SCENARIOS[2].presetResult);
  const [selectedRegionId, setSelectedRegionId] = useState<string | null>(null);

  // Agent Orchestration & Execution Animation State
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [analysisStepIndex, setAnalysisStepIndex] = useState<number>(0);
  const [analysisStepLabel, setAnalysisStepLabel] = useState<string>('');
  const [currentQueryText, setCurrentQueryText] = useState<string>('');

  // Modals & History State
  const [isReplayOpen, setIsReplayOpen] = useState<boolean>(false);
  const [isDemoModalOpen, setIsDemoModalOpen] = useState<boolean>(false);
  const [currentDemoId, setCurrentDemoId] = useState<string>('demo-03');
  const [historyItems, setHistoryItems] = useState<QueryHistoryItem[]>([]);

  // Workspace Simplification State
  // The Observation panel now lives in a slide-over drawer, closed by
  // default, so a new user sees just "the map" and "the question box"
  // instead of three permanently-competing columns.
  const [isObservationDrawerOpen, setIsObservationDrawerOpen] = useState<boolean>(false);

  // Workflow section ref for smooth scrolling to Landing overview page bottom
  const workflowRef = useRef<HTMLDivElement>(null);
  const handleScrollToWorkflow = () => {
    if (activeView !== 'LANDING') {
      setActiveView('LANDING');
      setTimeout(() => {
        workflowRef.current?.scrollIntoView({ behavior: 'smooth' });
      }, 100);
    } else {
      workflowRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  };

  // Load initial history
  useEffect(() => {
    satQueryService.getHistory().then(setHistoryItems);
  }, []);

  // Handle Observation Select / Deselect
  const handleToggleObservation = (id: string) => {
    setActiveObservationIds(prev => {
      if (prev.includes(id)) {
        // Prevent removing all
        if (prev.length === 1) return prev;
        return prev.filter(i => i !== id);
      } else {
        return [...prev, id];
      }
    });
  };

  // Handle Custom User Upload
  const handleAddObservation = async (file: File, modality: ModalityType) => {
    const newObs = await satQueryService.uploadObservation(file, file.name.replace(/\.[^/.]+$/, ""), modality);
    setObservations(prev => [newObs, ...prev]);
    setActiveObservationIds([newObs.id]); // Activate ONLY the new observation
    setActiveResult(null); // Reset old result panel to reflect fresh observation
  };

  // Handle Ingesting Satellite Product from CDSE Catalogue Search
  const handleAddObservationFromProduct = (prod: any) => {
    const modality: ModalityType = (prod.modality?.toUpperCase() === 'SAR' || (prod.platform && prod.platform.includes('Sentinel-1'))) ? 'SAR' : 'OPTICAL';
    const isSar = modality === 'SAR';
    const defaultImg = isSar
      ? 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=1600&q=80'
      : 'https://images.unsplash.com/photo-1541872703-74c5e44368f9?auto=format&fit=crop&w=1600&q=80';
    const defaultThumb = isSar
      ? 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=300&q=80'
      : 'https://images.unsplash.com/photo-1541872703-74c5e44368f9?auto=format&fit=crop&w=300&q=80';

    const dateStr = prod.acquisition_datetime
      ? new Date(prod.acquisition_datetime).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }).toUpperCase()
      : new Date().toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }).toUpperCase();

    const newObs: Observation = {
      id: `obs-cdse-${Date.now()}`,
      name: prod.metadata?.name || prod.title || prod.product_id || 'Copernicus Observation',
      filename: `${prod.product_id || 'sentinel'}.tif`,
      modality: modality,
      date: dateStr,
      dimensions: prod.resolution ? `${Math.round(2048 * (10 / (prod.resolution || 10)))} × 2048` : '3840 × 2160',
      status: 'READY',
      metadata: {
        sensor: prod.platform || prod.instrument || `Sentinel-${isSar ? '1 SAR' : '2 MSI'}`,
        lat: prod.bbox ? (prod.bbox[1] + prod.bbox[3]) / 2 : 25.2048,
        lon: prod.bbox ? (prod.bbox[0] + prod.bbox[2]) / 2 : 55.2708,
        cloudCover: prod.cloud_cover !== null && prod.cloud_cover !== undefined ? `${prod.cloud_cover.toFixed(1)}%` : '0.0%',
        bands: isSar ? 'VV + VH Polarized Radar' : 'RGB High-Res',
        fileSize: prod.size ? `${(prod.size / (1024 * 1024)).toFixed(1)} MB` : '52.4 MB',
        groundSamplingDistance: prod.resolution ? `${prod.resolution}m/px` : '10m/px',
        acquisitionTime: prod.acquisition_datetime ? prod.acquisition_datetime.substring(11, 19) + ' UTC' : '10:00:00 UTC'
      },
      imageUrl: prod.quicklook_url || defaultImg,
      thumbnailUrl: prod.quicklook_url || defaultThumb,
      isDemo: false
    };

    setObservations(prev => [newObs, ...prev]);
    setActiveObservationIds([newObs.id]); // Activate ONLY the newly ingested product
    setActiveResult(null); // Reset previous result panel
  };

  // Handle Query Submission & Agent Sequence
  const handleExecuteQuery = async (queryText: string) => {
    setCurrentQueryText(queryText);
    setIsAnalyzing(true);
    setAnalysisStepIndex(0);
    setSelectedRegionId(null);

    const activeObs = observations.filter(o => activeObservationIds.includes(o.id));

    try {
      const result = await satQueryService.submitQuery(
        queryText,
        activeObs,
        (stepIdx, label) => {
          setAnalysisStepIndex(stepIdx);
          setAnalysisStepLabel(label);
        }
      );

      setActiveResult(result);
      // Refresh history
      const updatedHistory = await satQueryService.getHistory();
      setHistoryItems(updatedHistory);
    } catch (err) {
      console.error("Analysis execution error:", err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Handle Loading Preset Demo Scenario
  const handleSelectDemoScenario = (scenario: DemoScenario) => {
    setCurrentDemoId(scenario.id);
    setObservations(scenario.observations);
    setActiveObservationIds(scenario.observations.map(o => o.id));
    setActiveResult(scenario.presetResult);
    setSelectedRegionId(null);
    setActiveView('WORKSPACE');
  };

  // Handle Opening History Item back in Workspace
  const handleOpenHistoryResult = (item: QueryHistoryItem) => {
    setActiveResult(item.result);
    setSelectedRegionId(null);
    setActiveView('WORKSPACE');
  };

  return (
    <div className="min-h-screen bg-transparent text-sat-text flex flex-col font-sans selection:bg-sat-accent/30 selection:text-sat-accent transition-colors duration-200 relative overflow-x-hidden">

      {/* Live Animated Space Background (Mouse Parallax + Cosmic Drift + Twinkling Stars) */}
      <LiveSpaceBackground />

      {/* Top Mission Control Header */}
      <HeaderBar
        activeView={activeView}
        setActiveView={setActiveView}
        theme={theme}
        onToggleTheme={handleToggleTheme}
        activeDemoId={currentDemoId}
        onOpenDemoSelector={() => setIsDemoModalOpen(true)}
        onOpenSettings={() => setIsSettingsOpen(true)}
        onScrollToWorkflow={handleScrollToWorkflow}
      />

      {/* Main Container Views */}
      <div className="flex-1 flex flex-col overflow-hidden z-10 relative">

        {/* VIEW 1: LANDING PAGE */}
        {activeView === 'LANDING' && (
          <LandingPage
            workflowRef={workflowRef}
            onEnterWorkspace={() => setActiveView('WORKSPACE')}
            onViewDemo={() => {
              handleSelectDemoScenario(DEMO_SCENARIOS[2]);
            }}
          />
        )}

        {/* VIEW 2: WORKSPACE (DESKTOP & RESPONSIVE STACK) */}
        {activeView === 'WORKSPACE' && (
          <div className="flex-1 flex flex-col overflow-y-auto min-h-0">



            {/* Two-Zone Workspace: Canvas + Query. Observation management
                lives in a drawer (see below) rather than a permanent column,
                so a new user has two things to look at, not three. */}
            <div className="flex-none h-[calc(100vh-3.5rem)] grid grid-cols-1 lg:grid-cols-9 overflow-hidden border-b border-sat-border relative">

              {/* Center: Central Earth GIS Canvas */}
              <div className="lg:col-span-6 h-full overflow-hidden border-b lg:border-b-0 lg:border-r border-sat-border relative">
                {/* Floating toggle for the Observation drawer */}
                <button
                  onClick={() => setIsObservationDrawerOpen(true)}
                  className="absolute top-3 left-3 z-20 flex items-center gap-1.5 px-3 py-1.5 rounded bg-sat-surface/90 backdrop-blur border border-sat-border hover:border-sat-accent text-xs font-mono text-sat-text hover:text-sat-accent transition-colors shadow-md"
                >
                  🛰️ Images ({observations.length})
                </button>

                <EarthCanvas
                  observations={observations}
                  activeObservationIds={activeObservationIds}
                  activeResult={activeResult}
                  selectedRegionId={selectedRegionId}
                  onSelectRegion={setSelectedRegionId}
                  onSelectDemoScenario={(demoId) => {
                    const scenario = DEMO_SCENARIOS.find(s => s.id === demoId);
                    if (scenario) handleSelectDemoScenario(scenario);
                  }}
                />
              </div>

              {/* Right: Ask SatQuery Interface */}
              <div className="lg:col-span-3 h-full overflow-hidden">
                <QueryInterface
                  observations={observations}
                  activeObservationIds={activeObservationIds}
                  onExecuteQuery={handleExecuteQuery}
                  isAnalyzing={isAnalyzing}
                />
              </div>

              {/* Slide-over Drawer: Observation / Data Panel.
                  Same ObservationPanel component and props as before —
                  only its container changed, from a permanent column to
                  an on-demand overlay. */}
              {isObservationDrawerOpen && (
                <div className="fixed inset-0 z-50 flex">
                  <div
                    className="absolute inset-0 bg-black/60 backdrop-blur-sm"
                    onClick={() => setIsObservationDrawerOpen(false)}
                  />
                  <div className="relative w-full max-w-lg md:w-[480px] h-full bg-sat-surface border-r border-sat-border shadow-2xl overflow-y-auto">
                    <div className="flex items-center justify-between p-4 border-b border-sat-border bg-sat-panel">
                      <span className="font-mono text-sm font-bold uppercase tracking-wider text-sat-text">🛰️ SATELLITE DATASETS ({observations.length})</span>
                      <button
                        onClick={() => setIsObservationDrawerOpen(false)}
                        className="text-sat-dim hover:text-sat-accent transition-colors px-2 py-1 font-mono text-sm font-bold"
                        aria-label="Close"
                      >
                        ✕ CLOSE
                      </button>
                    </div>
                    <ObservationPanel
                      observations={observations}
                      activeObservationIds={activeObservationIds}
                      onToggleObservation={handleToggleObservation}
                      onAddObservation={handleAddObservation}
                      onAddObservationFromProduct={handleAddObservationFromProduct}
                      onOpenSearchModal={() => setIsSearchModalOpen(true)}
                      onSelectDemoScenario={(demoId) => {
                        const scenario = DEMO_SCENARIOS.find(s => s.id === demoId);
                        if (scenario) handleSelectDemoScenario(scenario);
                      }}
                    />
                  </div>
                </div>
              )}

            </div>

            {/* Bottom Integrated Result Experience Panel */}
            {activeResult && !isAnalyzing && (
              <ResultPanel
                result={activeResult}
                selectedRegionId={selectedRegionId}
                onSelectRegion={setSelectedRegionId}
                onOpenReplay={() => setIsReplayOpen(true)}
                onFollowUpQuery={handleExecuteQuery}
              />
            )}

          </div>
        )}

        {/* VIEW 3: AUDIT HISTORY */}
        {activeView === 'HISTORY' && (
          <div className="flex-1 overflow-y-auto bg-transparent">
            <HistoryView
              historyItems={historyItems}
              onOpenHistoryResult={handleOpenHistoryResult}
            />
          </div>
        )}

      </div>

      {/* MODAL 1: AI Agent Analysis Execution Progress Sequence */}
      {isAnalyzing && (
        <AnalysisStatusModal
          currentStepIndex={analysisStepIndex}
          currentStepLabel={analysisStepLabel}
          queryText={currentQueryText}
        />
      )}

      {/* MODAL 2: Auditable Analysis Replay Pipeline */}
      {isReplayOpen && activeResult && (
        <AnalysisReplayModal
          result={activeResult}
          onClose={() => setIsReplayOpen(false)}
        />
      )}

      {/* MODAL 3: Preset Demo Selector */}
      {isDemoModalOpen && (
        <DemoSelectorModal
          onSelectScenario={handleSelectDemoScenario}
          onClose={() => setIsDemoModalOpen(false)}
          currentDemoId={currentDemoId}
        />
      )}

      {/* MODAL 4: Satellite Data Search & Ingestion (Copernicus CDSE) */}
      <SatelliteSearchModal
        isOpen={isSearchModalOpen}
        onClose={() => setIsSearchModalOpen(false)}
        onAddObservation={handleAddObservation}
        onAddProductAsObservation={handleAddObservationFromProduct}
      />

      {/* MODAL 5: Platform Preferences & Engine Settings */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
      />

    </div>
  );
}

export default App;