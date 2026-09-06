import React, { useState, useEffect, useMemo } from 'react';
import {
  Database,
  CheckCircle2,
  AlertCircle,
  X,
  Loader2,
  ArrowRight,
  FileCheck,
  Search,
  Layers,
  HelpCircle,
  Sparkles,
} from 'lucide-react';
import { satQueryService } from '../../services/satQueryService';
import type { Observation, SIHResourceItem, SIHSampleItem } from '../../types/satquery';

interface SIHResourcesModalProps {
  isOpen: boolean;
  onClose: () => void;
  onObservationAdded?: (observation: Observation, suggestedQuery?: string) => void;
}

export const SIHResourcesModal: React.FC<SIHResourcesModalProps> = ({
  isOpen,
  onClose,
  onObservationAdded,
}) => {
  const [resources, setResources] = useState<SIHResourceItem[]>([]);
  const [selectedResourceId, setSelectedResourceId] = useState<string | null>(null);
  const [samples, setSamples] = useState<SIHSampleItem[]>([]);
  const [selectedSample, setSelectedSample] = useState<SIHSampleItem | null>(null);

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTaskFilter, setSelectedTaskFilter] = useState<string>('ALL');

  const [isLoadingResources, setIsLoadingResources] = useState(false);
  const [isLoadingSamples, setIsLoadingSamples] = useState(false);
  const [isMaterializing, setIsMaterializing] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Load resources list upon opening
  useEffect(() => {
    if (isOpen) {
      loadResources();
      setSelectedSample(null);
      setSearchQuery('');
      setSelectedTaskFilter('ALL');
      setSuccessMessage(null);
      setErrorMessage(null);
    }
  }, [isOpen]);

  // Load samples when selected resource changes
  useEffect(() => {
    if (selectedResourceId) {
      const activeRes = resources.find((r) => r.resource_id === selectedResourceId);
      if (activeRes && activeRes.availability === 'AVAILABLE') {
        loadSamples(selectedResourceId);
      } else {
        setSamples([]);
        setSelectedSample(null);
      }
    } else {
      setSamples([]);
      setSelectedSample(null);
    }
  }, [selectedResourceId, resources]);

  const loadResources = async () => {
    setIsLoadingResources(true);
    setErrorMessage(null);
    try {
      const resp = await satQueryService.getSIHResources();
      setResources(resp.resources || []);
      // Auto-select first available resource or BigEarthNet
      const firstAvailable = resp.resources.find((r) => r.availability === 'AVAILABLE');
      if (firstAvailable) {
        setSelectedResourceId(firstAvailable.resource_id);
      } else if (resp.resources.length > 0) {
        setSelectedResourceId(resp.resources[0].resource_id);
      }
    } catch (err: any) {
      setErrorMessage(err?.message || 'Failed to retrieve SIH data resource catalogue.');
    } finally {
      setIsLoadingResources(false);
    }
  };

  const loadSamples = async (resourceId: string) => {
    setIsLoadingSamples(true);
    setErrorMessage(null);
    try {
      const resp = await satQueryService.getSIHResourceSamples(resourceId, 50);
      setSamples(resp.samples || []);
      if (resp.samples && resp.samples.length > 0) {
        setSelectedSample(resp.samples[0]);
      } else {
        setSelectedSample(null);
      }
    } catch (err: any) {
      setErrorMessage(err?.message || `Failed to load samples for resource '${resourceId}'.`);
      setSamples([]);
      setSelectedSample(null);
    } finally {
      setIsLoadingSamples(false);
    }
  };

  const handleSelectSampleForAnalysis = async () => {
    if (!selectedResourceId || !selectedSample) return;

    setIsMaterializing(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const result = await satQueryService.loadSIHSample(
        selectedResourceId,
        selectedSample.sample_id
      );

      const sampleDisplayName =
        selectedSample.primary_label ||
        selectedSample.filename ||
        selectedSample.sample_id;

      setSuccessMessage(
        result.companionObservation
          ? `Bi-temporal pair (${result.observation.filename} & ${result.companionObservation.filename}) loaded into workspace!`
          : `Sample '${sampleDisplayName}' loaded into workspace with pre-configured query!`
      );

      if (onObservationAdded) {
        onObservationAdded(result.observation, result.suggestedQuery);
        if (result.companionObservation) {
          onObservationAdded(result.companionObservation);
        }
      }

      setTimeout(() => {
        onClose();
      }, 700);
    } catch (err: any) {
      setErrorMessage(err?.message || 'Failed to materialize sample for analysis.');
    } finally {
      setIsMaterializing(false);
    }
  };

  // Filter samples based on search query and task filter
  const filteredSamples = useMemo(() => {
    return samples.filter((sample) => {
      // 1. Search filter
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const idMatch = (sample.sample_id || '').toLowerCase().includes(q);
        const nameMatch = (sample.filename || '').toLowerCase().includes(q);
        const labelMatch = (sample.primary_label || '').toLowerCase().includes(q);
        const labelsMatch = Array.isArray(sample.labels) && sample.labels.some((l) => l.toLowerCase().includes(q));
        const queryMatch = (sample.suggested_query || '').toLowerCase().includes(q);
        const changeMatch = (sample.change_type || '').toLowerCase().includes(q);

        if (!idMatch && !nameMatch && !labelMatch && !labelsMatch && !queryMatch && !changeMatch) {
          return false;
        }
      }

      // 2. Task filter
      if (selectedTaskFilter !== 'ALL') {
        const tasks = sample.task_compatibility || [];
        if (selectedTaskFilter === 'VQA' && !tasks.includes('SINGLE_IMAGE_VQA')) {
          return false;
        }
        if (selectedTaskFilter === 'GROUNDING' && !tasks.includes('OBJECT_GROUNDING')) {
          return false;
        }
        if (selectedTaskFilter === 'CHANGE' && !tasks.includes('CHANGE_DETECTION') && !tasks.includes('BI_TEMPORAL_VQA')) {
          return false;
        }
      }

      return true;
    });
  }, [samples, searchQuery, selectedTaskFilter]);

  if (!isOpen) return null;

  const currentResource = resources.find((r) => r.resource_id === selectedResourceId);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 animate-in fade-in duration-200 select-none">
      <div
        className="flex h-[88vh] w-full max-w-6xl flex-col rounded-2xl border border-sat-border bg-sat-surface shadow-2xl overflow-hidden text-sat-text"
        onClick={(e) => e.stopPropagation()}
      >
        {/* ========================================================
            MODAL HEADER
        ======================================================== */}
        <div className="flex items-center justify-between border-b border-sat-border bg-sat-panel/80 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-sat-accent/40 bg-sat-accent/15 text-sat-accent shadow-sm">
              <Database className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2.5">
                <h2 className="text-base font-bold text-sat-text tracking-wide">
                  SIH26167 Data Resources & Benchmark Hub
                </h2>
                <span className="rounded-md border border-sat-accent/40 bg-sat-accent/10 px-2 py-0.5 text-[10px] font-bold text-sat-accent uppercase tracking-wider">
                  TRAINING / EVALUATION DATA
                </span>
              </div>
              <p className="text-xs text-sat-muted mt-0.5">
                Curated remote-sensing datasets, evaluation benchmarks, and ISRO/SAC mission products for AI analysis.
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-2 text-sat-dim transition-colors hover:bg-sat-panel hover:text-sat-text"
            aria-label="Close modal"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* ========================================================
            MODAL BODY (SPLIT VIEW)
        ======================================================== */}
        <div className="grid grid-cols-12 flex-1 overflow-hidden">
          {/* ====================================================
              LEFT COLUMN: DATASET / RESOURCE SELECTOR
          ==================================================== */}
          <div className="col-span-4 flex flex-col border-r border-sat-border bg-sat-panel/30 overflow-y-auto p-4 space-y-2.5">
            <div className="flex items-center justify-between px-2 mb-1">
              <span className="text-[11px] font-bold uppercase tracking-wider text-sat-dim flex items-center gap-1.5">
                <Layers className="h-3.5 w-3.5 text-sat-accent" />
                SIH Datasets ({resources.length})
              </span>
              <span className="text-[10px] text-sat-muted">Choose dataset</span>
            </div>

            {isLoadingResources ? (
              <div className="flex flex-col items-center justify-center p-8 text-sat-muted">
                <Loader2 className="h-6 w-6 animate-spin text-sat-accent mb-2" />
                <span className="text-xs">Loading datasets...</span>
              </div>
            ) : (
              resources.map((res) => {
                const isSelected = res.resource_id === selectedResourceId;
                const isAvailable = res.availability === 'AVAILABLE';

                let typeBadge = 'Benchmark';
                if (res.resource_type === 'training_adaptation_dataset') {
                  typeBadge = 'Training Dataset';
                } else if (res.resource_type === 'isro_sac_evaluation_resource') {
                  typeBadge = 'ISRO Mission Evaluation';
                }

                return (
                  <button
                    key={res.resource_id}
                    type="button"
                    onClick={() => setSelectedResourceId(res.resource_id)}
                    className={`
                      w-full rounded-xl border p-3.5 text-left transition-all relative
                      ${
                        isSelected
                          ? 'border-sat-accent bg-sat-accent/15 text-sat-text shadow-md ring-1 ring-sat-accent/50'
                          : 'border-sat-border/70 bg-sat-panel/40 text-sat-muted hover:border-sat-border hover:bg-sat-panel/80'
                      }
                    `}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="font-bold text-xs text-sat-text leading-tight">
                        {res.name}
                      </div>
                      <span
                        className={`
                          shrink-0 rounded px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider border
                          ${
                            isAvailable
                              ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400'
                              : 'border-sat-border bg-sat-surface text-sat-dim'
                          }
                        `}
                      >
                        {isAvailable ? 'Ready' : 'Not Configured'}
                      </span>
                    </div>

                    <div className="mt-1 flex items-center gap-1.5">
                      <span className="rounded bg-sat-surface px-1.5 py-0.2 text-[9px] font-medium text-sat-accent">
                        {typeBadge}
                      </span>
                    </div>

                    <div className="mt-2 line-clamp-2 text-[11px] leading-4 text-sat-dim">
                      {res.description}
                    </div>

                    <div className="mt-2.5 flex flex-wrap items-center gap-1">
                      {res.supported_modalities.map((mod) => (
                        <span
                          key={mod}
                          className="rounded bg-sat-surface/90 px-1.5 py-0.2 text-[9px] text-sat-muted uppercase font-mono"
                        >
                          {mod}
                        </span>
                      ))}
                    </div>
                  </button>
                );
              })
            )}

            {/* Bottom Clarification Notice */}
            <div className="mt-auto pt-3 border-t border-sat-border/60 text-[10px] text-sat-dim flex items-start gap-2 px-1">
              <Sparkles className="h-3.5 w-3.5 shrink-0 text-sat-accent mt-0.5" />
              <span>
                Standard Manual Upload is active anytime in the workspace for external GeoTIFF files.
              </span>
            </div>
          </div>

          {/* ====================================================
              RIGHT COLUMN: SAMPLE BROWSER & PREVIEW
          ==================================================== */}
          <div className="col-span-8 flex flex-col overflow-y-auto p-6 bg-sat-surface">
            {currentResource ? (
              <div className="flex flex-col h-full space-y-4">
                {/* Resource Header Card */}
                <div className="rounded-xl border border-sat-border bg-sat-panel/40 p-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="text-sm font-bold text-sat-text">{currentResource.name}</h3>
                        <span
                          className={`
                            rounded px-1.5 py-0.2 text-[9px] font-bold uppercase tracking-wider border
                            ${
                              currentResource.availability === 'AVAILABLE'
                                ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400'
                                : 'border-amber-500/40 bg-amber-500/10 text-amber-300'
                            }
                          `}
                        >
                          {currentResource.availability === 'AVAILABLE' ? 'Dataset Available' : 'Not Configured'}
                        </span>
                      </div>
                      <div className="text-xs text-sat-accent/90 mt-1 font-medium">
                        {currentResource.official_reference}
                      </div>
                    </div>
                  </div>

                  <div className="mt-2.5 text-xs leading-relaxed text-sat-muted">
                    {currentResource.description}
                  </div>

                  <div className="mt-3 flex flex-wrap gap-2 text-xs">
                    <div className="rounded-md border border-sat-border bg-sat-surface px-2.5 py-1 text-sat-dim">
                      <strong className="text-sat-text">Modalities:</strong> {currentResource.supported_modalities.join(', ')}
                    </div>
                    <div className="rounded-md border border-sat-border bg-sat-surface px-2.5 py-1 text-sat-dim">
                      <strong className="text-sat-text">Tasks:</strong> {currentResource.supported_tasks.join(', ')}
                    </div>
                  </div>
                </div>

                {/* Unavailable / Unconfigured Message */}
                {currentResource.availability !== 'AVAILABLE' && (
                  <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-5 text-left">
                    <div className="flex items-start gap-3">
                      <AlertCircle className="h-5 w-5 shrink-0 text-amber-400 mt-0.5" />
                      <div>
                        <div className="text-xs font-bold text-amber-300">
                          Dataset Not Configured Locally
                        </div>
                        <div className="mt-1 text-xs text-sat-muted leading-relaxed">
                          This benchmark resource is currently not configured on disk. You can use manual upload for your own satellite imagery.
                        </div>
                        <div className="mt-3 rounded bg-sat-panel p-2.5 text-[11px] font-mono text-sat-dim border border-sat-border">
                          {currentResource.availability_reason}
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Available Samples Section */}
                {currentResource.availability === 'AVAILABLE' && (
                  <div className="flex-1 flex flex-col space-y-3 min-h-0">
                    {/* Search & Filter Controls */}
                    <div className="flex items-center gap-2">
                      <div className="relative flex-1">
                        <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-sat-dim" />
                        <input
                          type="text"
                          value={searchQuery}
                          onChange={(e) => setSearchQuery(e.target.value)}
                          placeholder="Search samples by ID, label, change type, or question..."
                          className="w-full rounded-lg border border-sat-border bg-sat-panel/80 pl-9 pr-3 py-1.5 text-xs text-sat-text placeholder:text-sat-dim focus:border-sat-accent focus:outline-none"
                        />
                        {searchQuery && (
                          <button
                            type="button"
                            onClick={() => setSearchQuery('')}
                            className="absolute right-2.5 top-2 text-sat-dim hover:text-sat-text"
                          >
                            <X className="h-3.5 w-3.5" />
                          </button>
                        )}
                      </div>

                      {/* Task Filter Chips */}
                      <div className="flex items-center gap-1 shrink-0">
                        {['ALL', 'VQA', 'GROUNDING', 'CHANGE'].map((f) => (
                          <button
                            key={f}
                            type="button"
                            onClick={() => setSelectedTaskFilter(f)}
                            className={`
                              rounded-lg px-2.5 py-1.5 text-[10px] font-bold uppercase tracking-wider transition-all border
                              ${
                                selectedTaskFilter === f
                                  ? 'border-sat-accent bg-sat-accent/15 text-sat-accent font-bold'
                                  : 'border-sat-border bg-sat-panel text-sat-dim hover:text-sat-text'
                              }
                            `}
                          >
                            {f}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="flex items-center justify-between text-[11px] text-sat-dim px-1">
                      <span>
                        Showing {filteredSamples.length} of {samples.length} sample{samples.length === 1 ? '' : 's'}
                      </span>
                      {isLoadingSamples && (
                        <span className="flex items-center gap-1 text-sat-accent text-xs">
                          <Loader2 className="h-3 w-3 animate-spin" />
                          Loading samples...
                        </span>
                      )}
                    </div>

                    {/* Sample Grid / List */}
                    <div className="grid grid-cols-2 gap-2.5 max-h-48 overflow-y-auto p-1 rounded-lg border border-sat-border/40 bg-sat-panel/20">
                      {filteredSamples.length === 0 ? (
                        <div className="col-span-2 flex flex-col items-center justify-center p-8 text-sat-muted text-xs">
                          No matching samples found for this query/filter.
                        </div>
                      ) : (
                        filteredSamples.map((sample) => {
                          const isSelected = selectedSample?.sample_id === sample.sample_id;

                          return (
                            <button
                              key={sample.sample_id}
                              type="button"
                              onClick={() => setSelectedSample(sample)}
                              className={`
                                flex flex-col rounded-lg border p-2.5 text-left transition-all
                                ${
                                  isSelected
                                    ? 'border-sat-accent bg-sat-accent/20 ring-1 ring-sat-accent shadow-sm'
                                    : 'border-sat-border/80 bg-sat-panel/60 hover:border-sat-border hover:bg-sat-panel'
                                }
                              `}
                            >
                              <div className="flex items-center justify-between gap-1.5">
                                <span className="text-xs font-bold text-sat-text truncate">
                                  {sample.filename || sample.sample_id}
                                </span>
                                <span className="rounded bg-sat-surface px-1.5 py-0.2 text-[9px] font-mono text-sat-accent uppercase shrink-0">
                                  {sample.modality || 'optical'}
                                </span>
                              </div>

                              {sample.primary_label && (
                                <div className="mt-1 text-[11px] text-emerald-400 font-medium truncate">
                                  {sample.primary_label}
                                </div>
                              )}

                              {sample.change_type && (
                                <div className="mt-1 text-[10px] text-amber-400 font-medium truncate uppercase">
                                  Change: {sample.change_type.replace(/_/g, ' ')}
                                </div>
                              )}

                              {sample.suggested_query && (
                                <div className="mt-1 line-clamp-1 text-[11px] text-sat-dim italic">
                                  "{sample.suggested_query}"
                                </div>
                              )}
                            </button>
                          );
                        })
                      )}
                    </div>

                    {/* Selected Sample Details & Inspection Panel */}
                    {selectedSample && (
                      <div className="rounded-xl border border-sat-accent/30 bg-sat-accent/[0.04] p-4 space-y-3">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <FileCheck className="h-4 w-4 text-sat-accent shrink-0" />
                            <span className="text-xs font-bold text-sat-text">
                              Sample: {selectedSample.filename || selectedSample.sample_id}
                            </span>
                          </div>

                          <span className="rounded bg-sat-accent/15 border border-sat-accent/30 px-2 py-0.5 text-[10px] font-mono font-bold text-sat-accent uppercase">
                            {selectedSample.modality}
                          </span>
                        </div>

                        {/* Labels / Classes Chips */}
                        {selectedSample.labels && selectedSample.labels.length > 0 && (
                          <div className="flex flex-wrap items-center gap-1.5">
                            <span className="text-[10px] font-bold text-sat-dim uppercase">Annotations:</span>
                            {selectedSample.labels.map((l) => (
                              <span
                                key={l}
                                className="rounded border border-sat-accent/30 bg-sat-accent/10 px-1.5 py-0.2 text-[10px] text-sat-accent font-medium"
                              >
                                {l}
                              </span>
                            ))}
                          </div>
                        )}

                        {/* Grounding Bounding Box Count if applicable */}
                        {selectedSample.grounding_boxes && selectedSample.grounding_boxes.length > 0 && (
                          <div className="text-xs text-sat-dim">
                            <strong className="text-sat-muted">Grounding Targets: </strong>
                            {selectedSample.grounding_boxes.length} annotated region(s)
                          </div>
                        )}

                        {/* Suggested Benchmark Query Box */}
                        {selectedSample.suggested_query && (
                          <div className="rounded-lg bg-sat-panel/90 p-3 text-xs text-sat-text border border-sat-border shadow-inner">
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-[10px] font-bold uppercase tracking-wider text-sat-accent flex items-center gap-1">
                                <HelpCircle className="h-3 w-3" />
                                Pre-configured Benchmark Query
                              </span>
                            </div>
                            <div className="font-medium text-sat-text">
                              "{selectedSample.suggested_query}"
                            </div>
                          </div>
                        )}

                        {/* Ground Truth Answer Context */}
                        {selectedSample.ground_truth_answer && (
                          <div className="text-xs text-sat-dim px-1">
                            <strong className="text-sat-muted">Reference Answer: </strong>
                            <span className="text-sat-text">{selectedSample.ground_truth_answer}</span>
                          </div>
                        )}

                        {/* Action Buttons */}
                        <div className="pt-2 flex items-center justify-between border-t border-sat-border/40">
                          <div className="text-[11px] text-sat-dim">
                            Loads verified raster & populates query into active workspace.
                          </div>

                          <button
                            type="button"
                            onClick={handleSelectSampleForAnalysis}
                            disabled={isMaterializing}
                            className="
                              flex items-center gap-2 rounded-xl bg-sat-accent px-4 py-2 text-xs font-bold text-slate-950
                              transition-all hover:bg-sat-accent/90 hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed
                            "
                          >
                            {isMaterializing ? (
                              <>
                                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                Materializing Sample...
                              </>
                            ) : (
                              <>
                                Load Sample & Set Query
                                <ArrowRight className="h-3.5 w-3.5" />
                              </>
                            )}
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Feedback Alerts */}
                {errorMessage && (
                  <div className="rounded-xl border border-rose-500/40 bg-rose-500/10 p-3 text-xs text-rose-300 flex items-center gap-2">
                    <AlertCircle className="h-4 w-4 shrink-0" />
                    {errorMessage}
                  </div>
                )}

                {successMessage && (
                  <div className="rounded-xl border border-emerald-500/40 bg-emerald-500/10 p-3 text-xs text-emerald-300 flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 shrink-0" />
                    {successMessage}
                  </div>
                )}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-sat-muted">
                <Database className="h-8 w-8 text-sat-dim mb-2" />
                <span className="text-xs">Select a dataset from the left to browse samples.</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
