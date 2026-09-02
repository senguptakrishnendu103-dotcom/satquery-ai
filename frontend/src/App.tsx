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
import { SystemWorkflowSection } from './components/landing/SystemWorkflowSection';


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

  // Workflow section ref for smooth scrolling
  const workflowRef = useRef<HTMLDivElement>(null);
  const handleScrollToWorkflow = () => {
    if (activeView !== 'WORKSPACE') {
      setActiveView('WORKSPACE');
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
    setActiveObservationIds(prev => [newObs.id, ...prev]);
  };

  // Handle Ingesting Satellite Product from CDSE Catalogue Search
  const handleAddObservationFromProduct = (obs: Observation) => {
    setObservations(prev => [obs, ...prev]);
    setActiveObservationIds(prev => [obs.id, ...prev]);
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
            onEnterWorkspace={() => setActiveView('WORKSPACE')}
            onViewDemo={() => {
              handleSelectDemoScenario(DEMO_SCENARIOS[2]);
            }}
          />
        )}

        {/* VIEW 2: WORKSPACE (DESKTOP & RESPONSIVE STACK) */}
        {activeView === 'WORKSPACE' && (
          <div className="flex-1 flex flex-col overflow-y-auto min-h-0">
            
            {/* Desktop 3-Column Layout & Central Canvas */}
            <div className="flex-none h-[calc(100vh-3.5rem)] grid grid-cols-1 lg:grid-cols-12 overflow-hidden border-b border-sat-border">
              
              {/* Left Column: Data / Observations Panel (3 Cols) */}
              <div className="lg:col-span-3 h-full overflow-hidden border-b lg:border-b-0 border-sat-border">
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

              {/* Center Column: Central Earth GIS Canvas (6 Cols) */}
              <div className="lg:col-span-6 h-full overflow-hidden border-b lg:border-b-0 border-sat-border">
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

              {/* Right Column: Ask SatQuery Interface (3 Cols) */}
              <div className="lg:col-span-3 h-full overflow-hidden">
                <QueryInterface
                  observations={observations}
                  activeObservationIds={activeObservationIds}
                  onExecuteQuery={handleExecuteQuery}
                  isAnalyzing={isAnalyzing}
                />
              </div>

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

            {/* System Workflow Pipeline & Telemetry Display */}
            <div ref={workflowRef}>
              <SystemWorkflowSection />
            </div>

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
