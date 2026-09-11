import React, { useMemo, useState, useEffect, useRef } from 'react';
import * as maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import type {
  Observation,
  AnalysisResult,
  MapLayerConfig,
} from '../../types/satquery';
import { MapControls } from './MapControls';
import { LayerControl } from './LayerControl';
import { ComparisonView } from './ComparisonView';
import { EvidenceLayer } from './EvidenceLayer';
import {
  Activity,
  Crosshair,
  Database,
  Gauge,
  Layers,
  MapPin,
  Navigation,
  Radio,
  Satellite,
  ScanLine,
  Sparkles,
  Target,
  BoxSelect,
  Globe,
  Search,
  X,
  Maximize2,
} from 'lucide-react';

interface EarthCanvasProps {
  observations: Observation[];
  activeObservationIds: string[];
  activeResult: AnalysisResult | null;
  selectedRegionId: string | null;
  onSelectRegion: (regionId: string | null) => void;
  onSelectDemoScenario?: (demoId: string) => void;
  selectedAOI?: [number, number, number, number] | null;
  onSelectAOI?: (bbox: [number, number, number, number] | null) => void;
  onOpenSatelliteSearch?: (bbox: [number, number, number, number]) => void;
  onSelectObservation?: (id: string) => void;
}

type CanvasOverlayMode = 'EVIDENCE' | 'HEATMAP';
type CanvasViewMode = 'GEOGRAPHIC' | 'SCENE_INSPECT';

interface CursorPosition {
  lat: string;
  lon: string;
  x: number;
  y: number;
  visible: boolean;
}

const MAP_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    'esri-dark': {
      type: 'raster',
      tiles: [
        'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}',
      ],
      tileSize: 256,
      attribution: '&copy; Esri, DeLorme, NAVTEQ',
      maxzoom: 16,
    },
    'esri-satellite': {
      type: 'raster',
      tiles: [
        'https://services.arcgisonline.com/arcgis/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      ],
      tileSize: 256,
      attribution: '&copy; Esri, Maxar, Earthstar Geographics',
      maxzoom: 19,
    },
    'esri-boundaries': {
      type: 'raster',
      tiles: [
        'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}',
      ],
      tileSize: 256,
      attribution: '',
      maxzoom: 16,
    },
  },
  layers: [
    {
      id: 'esri-satellite-layer',
      type: 'raster',
      source: 'esri-satellite',
      minzoom: 0,
      maxzoom: 20,
      layout: {
        visibility: 'visible',
      },
    },
    {
      id: 'esri-dark-layer',
      type: 'raster',
      source: 'esri-dark',
      minzoom: 0,
      maxzoom: 20,
      layout: {
        visibility: 'none',
      },
    },
    {
      id: 'boundaries-layer',
      type: 'raster',
      source: 'esri-boundaries',
      minzoom: 0,
      maxzoom: 20,
      layout: {
        visibility: 'visible',
      },
    },
  ],
};

export const EarthCanvas: React.FC<EarthCanvasProps> = ({
  observations,
  activeObservationIds,
  activeResult,
  selectedRegionId,
  onSelectRegion,
  onSelectDemoScenario,
  selectedAOI = null,
  onSelectAOI,
  onOpenSatelliteSearch,
  onSelectObservation,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const isMapLoadedRef = useRef(false);

  // ================================================================
  // VIEWPORT & VIEW MODE
  // ================================================================

  const [canvasViewMode, setCanvasViewMode] = useState<CanvasViewMode>('GEOGRAPHIC');
  const [zoom, setZoom] = useState(1);
  const [mapZoomLevel, setMapZoomLevel] = useState(3.5);
  const [isAoiMode, setIsAoiMode] = useState(false);
  const isAoiModeRef = useRef(false);
  const [localAOI, setLocalAOI] = useState<[number, number, number, number] | null>(selectedAOI || null);
  const [dragBox, setDragBox] = useState<{
    startX: number;
    startY: number;
    currentX: number;
    currentY: number;
  } | null>(null);
  const isDrawingRef = useRef(false);
  const dragBoxRef = useRef<{
    startX: number;
    startY: number;
    currentX: number;
    currentY: number;
  } | null>(null);

  // ================================================================
  // MAP LAYERS
  // ================================================================

  const [showLayerPanel, setShowLayerPanel] = useState(false);

  const [mapLayers, setMapLayers] = useState<MapLayerConfig[]>([
    {
      id: 'base',
      name: 'DARK GIS BASEMAP',
      visible: false,
      color: '#38BDF8',
    },
    {
      id: 'satellite',
      name: 'SATELLITE IMAGERY',
      visible: true,
      color: '#10B981',
    },
    {
      id: 'change',
      name: 'CHANGE DETECTION',
      visible: true,
      color: '#FF5533',
      count: 3,
    },
    {
      id: 'water',
      name: 'WATER BODIES',
      visible: true,
      color: '#0EA5E9',
    },
    {
      id: 'built_up',
      name: 'BUILT-UP AREA',
      visible: true,
      color: '#F59E0B',
    },
    {
      id: 'vegetation',
      name: 'VEGETATION',
      visible: true,
      color: '#10B981',
    },
    {
      id: 'boundaries',
      name: 'BOUNDARIES & REGIONS',
      visible: true,
      color: '#64748B',
    },
  ]);

  // ================================================================
  // COMPARISON / OVERLAY
  // ================================================================

  const [compareMode, setCompareMode] = useState<
    'BEFORE' | 'AFTER' | 'CHANGE'
  >('BEFORE');

  const [wipePosition, setWipePosition] = useState(50);
  const [showOverlays, setShowOverlays] = useState(true);
  const [showGrid, setShowGrid] = useState(true);

  const [overlayMode, setOverlayMode] =
    useState<CanvasOverlayMode>('EVIDENCE');

  const handleSetCompareMode = (mode: 'BEFORE' | 'AFTER' | 'CHANGE') => {
    setCompareMode(mode);
  };

  const heatmapRegions = (activeResult?.evidence && activeResult.evidence.length > 0)
    ? activeResult.evidence
    : [];

  // ================================================================
  // CURSOR / HUD
  // ================================================================

  const [cursorCoords, setCursorCoords] = useState<CursorPosition>({
    lat: '20.5937° N',
    lon: '78.9629° E',
    x: 50,
    y: 50,
    visible: false,
  });

  // ================================================================
  // DERIVED OBSERVATION STATE
  // ================================================================

  const activeObsList = observations.filter((o) =>
    activeObservationIds.includes(o.id)
  );

  const hasImages = activeObsList.length > 0;

  const obsBefore = activeObsList[0] || null;
  const obsAfter =
    activeObsList[1] || activeObsList[0] || null;

  const isMultiObs = activeObsList.length >= 2;

  const visibleLayerIds = mapLayers
    .filter((l) => l.visible)
    .map((l) => l.id);

  const activeEvidenceCount =
    activeResult?.evidence?.length ?? 0;

  const activeObservation = obsBefore;

  const getObsImageUrl = (obs: Observation | null) => {
    if (!obs) return '';
    const candidate = obs.imageUrl || (obs as any).url || (obs as any).image_url || obs.thumbnailUrl;
    if (!candidate) return '';
    return candidate.startsWith('/static')
      ? `${window.location.origin}${candidate}`
      : candidate;
  };

  // Keep GEOGRAPHIC map as default active mode so user always sees the satellite earth canvas
  // Users can click 'Scene Inspect' in top toolbar if they want to view raw scene image card

  // Sync external selectedAOI
  useEffect(() => {
    if (selectedAOI) {
      setLocalAOI(selectedAOI);
    }
  }, [selectedAOI]);

  const sceneMetadata = useMemo(() => {
    const metadata = activeObservation?.metadata;

    return {
      satellite:
        typeof metadata?.sensor === 'object' && metadata?.sensor !== null
          ? JSON.stringify(metadata?.sensor)
          : String(metadata?.sensor || activeObservation?.name || 'REMOTE SENSOR'),
      modality:
        String(activeObservation?.modality || 'OPTICAL'),
      resolution:
        typeof metadata?.groundSamplingDistance === 'object' && metadata?.groundSamplingDistance !== null
          ? JSON.stringify(metadata?.groundSamplingDistance)
          : String(metadata?.groundSamplingDistance || activeObservation?.dimensions || 'N/A'),
      cloud:
        typeof (metadata as any)?.cloudCover === 'object' && (metadata as any)?.cloudCover !== null
          ? JSON.stringify((metadata as any)?.cloudCover)
          : String((metadata as any)?.cloudCover ?? 'N/A'),
      acquisition:
        String(activeObservation?.date || 'N/A'),
    };
  }, [activeObservation]);

  // ================================================================
  // MAPLIBRE INITIALIZATION & EVENT WIRING
  // ================================================================

  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    let initialCenter: [number, number] = [78.9629, 20.5937];
    let initialZoom = 3.5;

    if (activeObservation?.metadata?.lon && activeObservation?.metadata?.lat) {
      initialCenter = [
        Number(activeObservation.metadata.lon),
        Number(activeObservation.metadata.lat),
      ];
      initialZoom = 9.5;
    }

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: MAP_STYLE,
      center: initialCenter,
      zoom: initialZoom,
      attributionControl: false,
    });

    mapRef.current = map;
    (window as any)._map = map;

    map.on('load', () => {
      isMapLoadedRef.current = true;

      // Add AOI Source & Layers
      if (!map.getSource('aoi-source')) {
        map.addSource('aoi-source', {
          type: 'geojson',
          data: {
            type: 'FeatureCollection',
            features: [],
          },
        });

        map.addLayer({
          id: 'aoi-fill',
          type: 'fill',
          source: 'aoi-source',
          paint: {
            'fill-color': '#0EA5E9',
            'fill-opacity': 0.2,
          },
        });

        map.addLayer({
          id: 'aoi-stroke',
          type: 'line',
          source: 'aoi-source',
          paint: {
            'line-color': '#38BDF8',
            'line-width': 2.5,
            'line-dasharray': [3, 2],
          },
        });
      }

      // Add Observation Footprint Layer
      if (!map.getSource('obs-footprint-source')) {
        map.addSource('obs-footprint-source', {
          type: 'geojson',
          data: {
            type: 'FeatureCollection',
            features: [],
          },
        });

        map.addLayer({
          id: 'obs-footprint-fill',
          type: 'fill',
          source: 'obs-footprint-source',
          paint: {
            'fill-color': '#22C55E',
            'fill-opacity': 0.15,
          },
        });

        map.addLayer({
          id: 'obs-footprint-stroke',
          type: 'line',
          source: 'obs-footprint-source',
          paint: {
            'line-color': '#4ADE80',
            'line-width': 2,
          },
        });
      }

      // If an existing AOI is set, render it
      if (localAOI) {
        renderAoiBox(map, localAOI);
      }

      // Apply initial basemap visibility
      const isSatVisible = mapLayers.find((l) => l.id === 'satellite')?.visible ?? false;
      const isDarkVisible = mapLayers.find((l) => l.id === 'base')?.visible ?? true;
      if (map.getLayer('esri-satellite-layer')) {
        map.setLayoutProperty('esri-satellite-layer', 'visibility', isSatVisible ? 'visible' : 'none');
      }
      if (map.getLayer('esri-dark-layer')) {
        map.setLayoutProperty('esri-dark-layer', 'visibility', (!isSatVisible && isDarkVisible) ? 'visible' : 'none');
      }
    });

    map.on('zoom', () => {
      const z = map.getZoom();
      setMapZoomLevel(z);
      setZoom(Math.max(0.5, Math.min(3.5, Number((z / 4).toFixed(2)))));
    });

    map.on('mousemove', (e) => {
      const lng = e.lngLat.lng;
      const lat = e.lngLat.lat;

      const latStr = `${Math.abs(lat).toFixed(4)}° ${lat >= 0 ? 'N' : 'S'}`;
      const lonStr = `${Math.abs(lng).toFixed(4)}° ${lng >= 0 ? 'E' : 'W'}`;

      setCursorCoords({
        lat: latStr,
        lon: lonStr,
        x: e.point.x,
        y: e.point.y,
        visible: true,
      });

    });

    map.on('mouseout', () => {
      setCursorCoords((prev) => ({ ...prev, visible: false }));
    });

    return () => {
      map.remove();
      mapRef.current = null;
      isMapLoadedRef.current = false;
    };
  }, []);

  // Helper to draw or clear AOI polygon on map
  const renderAoiBox = (map: maplibregl.Map, bbox: [number, number, number, number] | null) => {
    const source = map.getSource('aoi-source') as maplibregl.GeoJSONSource | undefined;
    if (!source) return;

    if (!bbox) {
      source.setData({ type: 'FeatureCollection', features: [] });
      return;
    }

    const [minLon, minLat, maxLon, maxLat] = bbox;
    const polygonGeoJson: any = {
      type: 'Feature',
      properties: {},
      geometry: {
        type: 'Polygon',
        coordinates: [
          [
            [minLon, minLat],
            [maxLon, minLat],
            [maxLon, maxLat],
            [minLon, maxLat],
            [minLon, minLat],
          ],
        ],
      },
    };

    source.setData({
      type: 'FeatureCollection',
      features: [polygonGeoJson],
    });
  };

  // Direct Basemap Mode Switcher
  const setBasemapMode = (mode: 'satellite' | 'base') => {
    // Always ensure we are in GEOGRAPHIC mode so the basemap is visible
    setCanvasViewMode('GEOGRAPHIC');

    const map = mapRef.current;
    if (map) {
      try {
        if (mode === 'satellite') {
          if (map.getLayer('esri-satellite-layer')) {
            map.setLayoutProperty('esri-satellite-layer', 'visibility', 'visible');
          }
          if (map.getLayer('esri-dark-layer')) {
            map.setLayoutProperty('esri-dark-layer', 'visibility', 'none');
          }
        } else {
          if (map.getLayer('esri-dark-layer')) {
            map.setLayoutProperty('esri-dark-layer', 'visibility', 'visible');
          }
          if (map.getLayer('esri-satellite-layer')) {
            map.setLayoutProperty('esri-satellite-layer', 'visibility', 'none');
          }
        }
      } catch (e) {
        console.warn('Direct basemap switch warning:', e);
      }
    }

    setMapLayers((prev) =>
      prev.map((layer) => {
        if (mode === 'satellite') {
          if (layer.id === 'satellite') return { ...layer, visible: true };
          if (layer.id === 'base') return { ...layer, visible: false };
        } else {
          if (layer.id === 'base') return { ...layer, visible: true };
          if (layer.id === 'satellite') return { ...layer, visible: false };
        }
        return layer;
      })
    );
  };

  // Synchronize Basemap, Satellite & Boundaries layers with LayerControl
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const applyLayers = () => {
      const isDarkVisible = mapLayers.find((l) => l.id === 'base')?.visible ?? false;
      const isSatVisible = mapLayers.find((l) => l.id === 'satellite')?.visible ?? true;
      const isBoundariesVisible = mapLayers.find((l) => l.id === 'boundaries')?.visible ?? true;

      try {
        if (map.getLayer('esri-satellite-layer')) {
          map.setLayoutProperty('esri-satellite-layer', 'visibility', isSatVisible ? 'visible' : 'none');
        }
        if (map.getLayer('esri-dark-layer')) {
          map.setLayoutProperty('esri-dark-layer', 'visibility', isDarkVisible && !isSatVisible ? 'visible' : 'none');
        }
        if (map.getLayer('boundaries-layer')) {
          map.setLayoutProperty('boundaries-layer', 'visibility', isBoundariesVisible ? 'visible' : 'none');
        }
      } catch (e) {
        console.warn('Layer sync warning:', e);
      }
    };

    applyLayers();
  }, [mapLayers]);

  // Synchronize Observation Footprint on Map
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;

    const source = map.getSource('obs-footprint-source') as maplibregl.GeoJSONSource | undefined;
    if (!source) return;

    if (!activeObservation) {
      source.setData({ type: 'FeatureCollection', features: [] });
      return;
    }

    const rawBounds = activeObservation.metadata?.bounds || activeObservation.metadata?.bbox;
    let footprintBbox: [number, number, number, number] | null = null;

    if (Array.isArray(rawBounds) && rawBounds.length === 4) {
      footprintBbox = [rawBounds[0], rawBounds[1], rawBounds[2], rawBounds[3]];
    } else if (activeObservation.metadata?.lon && activeObservation.metadata?.lat) {
      const cLon = Number(activeObservation.metadata.lon);
      const cLat = Number(activeObservation.metadata.lat);
      const delta = 0.08;
      footprintBbox = [cLon - delta, cLat - delta, cLon + delta, cLat + delta];
    }

    if (footprintBbox) {
      const [minLon, minLat, maxLon, maxLat] = footprintBbox;
      source.setData({
        type: 'FeatureCollection',
        features: [
          {
            type: 'Feature',
            properties: { title: activeObservation.name },
            geometry: {
              type: 'Polygon',
              coordinates: [
                [
                  [minLon, minLat],
                  [maxLon, minLat],
                  [maxLon, maxLat],
                  [minLon, maxLat],
                  [minLon, minLat],
                ],
              ],
            },
          },
        ],
      });

      map.fitBounds(
        [
          [minLon, minLat],
          [maxLon, maxLat],
        ],
        { padding: 100, maxZoom: 12, duration: 1200 }
      );

      // Dynamically project active observation image overlay onto geographic map
      const rawImgUrl = activeObservation.imageUrl || (activeObservation as any).url || (activeObservation as any).image_url;
      if (rawImgUrl) {
        const fullImgUrl = rawImgUrl.startsWith('/static')
          ? `${window.location.origin}${rawImgUrl}`
          : rawImgUrl;

        try {
          if (map.getLayer('obs-raster-layer')) {
            map.removeLayer('obs-raster-layer');
          }
          if (map.getSource('obs-raster-source')) {
            map.removeSource('obs-raster-source');
          }

          map.addSource('obs-raster-source', {
            type: 'image',
            url: fullImgUrl,
            coordinates: [
              [minLon, maxLat],
              [maxLon, maxLat],
              [maxLon, minLat],
              [minLon, minLat],
            ],
          });

          map.addLayer(
            {
              id: 'obs-raster-layer',
              type: 'raster',
              source: 'obs-raster-source',
              paint: {
                'raster-opacity': 0.9,
                'raster-fade-duration': 300,
              },
            },
            map.getLayer('obs-footprint-stroke') ? 'obs-footprint-stroke' : undefined
          );
        } catch (overlayErr) {
          console.warn('Could not add MapLibre raster overlay:', overlayErr);
        }
      }
    } else {
      try {
        if (map.getLayer('obs-raster-layer')) map.removeLayer('obs-raster-layer');
        if (map.getSource('obs-raster-source')) map.removeSource('obs-raster-source');
      } catch (err) {}
    }
  }, [activeObservation]);

  // Synchronize AOI mode cursor
  useEffect(() => {
    isAoiModeRef.current = isAoiMode;
    const map = mapRef.current;
    if (!map) return;
    if (isAoiMode) {
      map.getCanvas().style.cursor = 'crosshair';
      map.dragPan.disable();
    } else {
      map.getCanvas().style.cursor = '';
      map.dragPan.enable();
    }
  }, [isAoiMode]);

  // ================================================================
  // ZOOM & CONTROL HANDLERS
  // ================================================================

  const handleZoomIn = () => {
    mapRef.current?.zoomIn({ duration: 300 });
  };

  const handleZoomOut = () => {
    mapRef.current?.zoomOut({ duration: 300 });
  };

  const handleReset = () => {
    if (activeObservation?.metadata?.lon && activeObservation?.metadata?.lat) {
      mapRef.current?.flyTo({
        center: [Number(activeObservation.metadata.lon), Number(activeObservation.metadata.lat)],
        zoom: 9.5,
        duration: 1000,
      });
    } else {
      mapRef.current?.flyTo({
        center: [78.9629, 20.5937],
        zoom: 3.5,
        duration: 1000,
      });
    }
  };

  const handleToggleLayer = (layerId: string) => {
    if (layerId === 'satellite') {
      const isCurrentlySat = mapLayers.find((l) => l.id === 'satellite')?.visible;
      setBasemapMode(isCurrentlySat ? 'base' : 'satellite');
      return;
    }
    if (layerId === 'base') {
      const isCurrentlyBase = mapLayers.find((l) => l.id === 'base')?.visible;
      setBasemapMode(isCurrentlyBase ? 'satellite' : 'base');
      return;
    }

    // Other layers (boundaries, water, etc.)
    const targetLayer = mapLayers.find((l) => l.id === layerId);
    const newVisibility = !targetLayer?.visible;

    const map = mapRef.current;
    if (map && layerId === 'boundaries') {
      try {
        if (map.getLayer('boundaries-layer')) {
          map.setLayoutProperty('boundaries-layer', 'visibility', newVisibility ? 'visible' : 'none');
        }
      } catch (e) {}
    }

    setMapLayers((prev) =>
      prev.map((layer) =>
        layer.id === layerId ? { ...layer, visible: newVisibility } : layer
      )
    );
  };

  const handleToggleAoiMode = () => {
    setIsAoiMode((prev) => {
      const next = !prev;
      if (next) {
        setCanvasViewMode('GEOGRAPHIC');
      }
      return next;
    });
  };

  const handleClearAOI = () => {
    setLocalAOI(null);
    dragBoxRef.current = null;
    setDragBox(null);
    onSelectAOI?.(null);
    if (mapRef.current) {
      renderAoiBox(mapRef.current, null);
    }
  };

  const handleAoiOverlayMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!isAoiMode) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    isDrawingRef.current = true;
    const initialBox = {
      startX: x,
      startY: y,
      currentX: x,
      currentY: y,
    };
    dragBoxRef.current = initialBox;
    setDragBox(initialBox);
  };

  const handleAoiOverlayMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    if (mapRef.current) {
      try {
        const lngLat = mapRef.current.unproject([x, y]);
        const latStr = `${Math.abs(lngLat.lat).toFixed(4)}° ${lngLat.lat >= 0 ? 'N' : 'S'}`;
        const lonStr = `${Math.abs(lngLat.lng).toFixed(4)}° ${lngLat.lng >= 0 ? 'E' : 'W'}`;
        setCursorCoords({
          lat: latStr,
          lon: lonStr,
          x,
          y,
          visible: true,
        });
      } catch {
        // ignore
      }
    }

    if (!isDrawingRef.current || !dragBoxRef.current) return;

    const currentBox = { ...dragBoxRef.current, currentX: x, currentY: y };
    dragBoxRef.current = currentBox;
    setDragBox(currentBox);

    if (mapRef.current) {
      try {
        const p1 = mapRef.current.unproject([Math.min(currentBox.startX, x), Math.min(currentBox.startY, y)]);
        const p2 = mapRef.current.unproject([Math.max(currentBox.startX, x), Math.max(currentBox.startY, y)]);
        const minLon = Math.min(p1.lng, p2.lng);
        const maxLon = Math.max(p1.lng, p2.lng);
        const minLat = Math.min(p1.lat, p2.lat);
        const maxLat = Math.max(p1.lat, p2.lat);
        renderAoiBox(mapRef.current, [minLon, minLat, maxLon, maxLat]);
      } catch {
        // ignore
      }
    }
  };

  const handleAoiOverlayMouseUp = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!isDrawingRef.current || !dragBoxRef.current) {
      isDrawingRef.current = false;
      dragBoxRef.current = null;
      setDragBox(null);
      return;
    }

    isDrawingRef.current = false;
    const currentBox = dragBoxRef.current;
    const rect = e.currentTarget.getBoundingClientRect();
    const endX = e.clientX - rect.left;
    const endY = e.clientY - rect.top;

    const width = Math.abs(endX - currentBox.startX);
    const height = Math.abs(endY - currentBox.startY);

    if (width > 8 && height > 8 && mapRef.current) {
      try {
        const p1 = mapRef.current.unproject([Math.min(currentBox.startX, endX), Math.min(currentBox.startY, endY)]);
        const p2 = mapRef.current.unproject([Math.max(currentBox.startX, endX), Math.max(currentBox.startY, endY)]);
        const minLon = Math.min(p1.lng, p2.lng);
        const maxLon = Math.max(p1.lng, p2.lng);
        const minLat = Math.min(p1.lat, p2.lat);
        const maxLat = Math.max(p1.lat, p2.lat);

        if (Math.abs(maxLon - minLon) > 0.001 && Math.abs(maxLat - minLat) > 0.001) {
          const clampedMinLon = Math.max(-180, Math.min(180, minLon));
          const clampedMaxLon = Math.max(-180, Math.min(180, maxLon));
          const clampedMinLat = Math.max(-90, Math.min(90, minLat));
          const clampedMaxLat = Math.max(-90, Math.min(90, maxLat));

          const newBbox: [number, number, number, number] = [
            Number(clampedMinLon.toFixed(4)),
            Number(clampedMinLat.toFixed(4)),
            Number(clampedMaxLon.toFixed(4)),
            Number(clampedMaxLat.toFixed(4)),
          ];
          setLocalAOI(newBbox);
          onSelectAOI?.(newBbox);
          renderAoiBox(mapRef.current, newBbox);
          if (onOpenSatelliteSearch) {
            onOpenSatelliteSearch(newBbox);
          }
        }
      } catch (err) {
        console.error('AOI unproject error:', err);
      }
    }

    dragBoxRef.current = null;
    setDragBox(null);
    setIsAoiMode(false);
  };

  const sceneStatus = activeResult
    ? 'ANALYSIS COMPLETE'
    : hasImages
    ? 'OBSERVATION READY'
    : 'AWAITING OBSERVATION';

  return (
    <div className="relative flex h-full min-h-0 flex-1 flex-col overflow-hidden bg-black/40 backdrop-blur-sm select-none">
      {/* ==========================================================
          TOP MISSION HEADER
      ========================================================== */}
      <div className="pointer-events-none absolute left-4 right-4 top-4 z-30 flex flex-wrap items-start justify-between gap-2">
        {/* LEFT: OBSERVATION TELEMETRY */}
        {hasImages && (
          <div className="pointer-events-auto min-w-[250px] max-w-[390px] overflow-hidden rounded-lg border border-sat-border bg-sat-surface/90 shadow-2xl backdrop-blur-xl">
            <div className="flex items-center justify-between border-b border-sat-border px-3 py-2">
              <div className="flex items-center gap-2">
                <div className="flex h-6 w-6 items-center justify-center rounded bg-sat-accent/10 text-sat-accent">
                  <Radio className="h-3.5 w-3.5" />
                </div>

                <div>
                  <div className="font-mono text-[9px] font-bold uppercase tracking-wider text-sat-text">
                    Earth Observation
                  </div>

                  <div className="font-mono text-[7px] uppercase tracking-wider text-sat-dim">
                    {sceneStatus}
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-full bg-sat-stable shadow-[0_0_7px_currentColor]" />
                <span className="font-mono text-[7px] font-bold text-sat-stable">
                  LIVE
                </span>
              </div>
            </div>

            <div className="grid grid-cols-4 gap-px bg-sat-border">
              <TelemetryCell label="SENSOR" value={sceneMetadata.satellite} />
              <TelemetryCell label="MODALITY" value={sceneMetadata.modality} />
              <TelemetryCell label="GSD" value={sceneMetadata.resolution} />
              <TelemetryCell label="CLOUD" value={String(sceneMetadata.cloud)} />
            </div>

            <div className="flex items-center justify-between gap-3 bg-sat-bg/80 px-3 py-1.5">
              <span className="font-mono text-[7px] uppercase tracking-wider text-sat-dim">
                ACQUIRED
              </span>

              <span className="truncate font-mono text-[8px] font-semibold text-sat-text">
                {sceneMetadata.acquisition}
              </span>
            </div>
          </div>
        )}

        {/* RIGHT: VIEW CONTROLS & COMPARISON */}
        <div className="flex flex-wrap items-start gap-2">
          {hasImages && (
            <div className="pointer-events-auto flex items-center rounded-lg border border-sat-border bg-sat-surface/90 p-1 shadow-lg backdrop-blur-md">
              <button
                type="button"
                onClick={() => setCanvasViewMode('GEOGRAPHIC')}
                className={`flex items-center gap-1.5 rounded px-2.5 py-1 font-mono text-[10px] font-bold uppercase tracking-wider transition-colors ${
                  canvasViewMode === 'GEOGRAPHIC'
                    ? 'bg-sat-accent text-slate-950 shadow-sm'
                    : 'text-sat-dim hover:text-sat-text'
                }`}
              >
                <Globe className="h-3.5 w-3.5" />
                <span>Geographic Map</span>
              </button>

              <button
                type="button"
                onClick={() => setCanvasViewMode('SCENE_INSPECT')}
                className={`flex items-center gap-1.5 rounded px-2.5 py-1 font-mono text-[10px] font-bold uppercase tracking-wider transition-colors ${
                  canvasViewMode === 'SCENE_INSPECT'
                    ? 'bg-sat-accent text-slate-950 shadow-sm'
                    : 'text-sat-dim hover:text-sat-text'
                }`}
              >
                <Maximize2 className="h-3.5 w-3.5" />
                <span>Inspect Scene</span>
              </button>
            </div>
          )}

          {/* SATELLITE BASEMAP TOGGLE ON TOP TOOLBAR */}
          {canvasViewMode === 'GEOGRAPHIC' && (
            <div className="pointer-events-auto flex items-center rounded-lg border border-sat-border bg-sat-surface/95 p-1 shadow-lg backdrop-blur-md font-mono text-[10px]">
              <button
                type="button"
                onClick={() => setBasemapMode('base')}
                className={`flex items-center gap-1.5 rounded px-2.5 py-1 font-bold transition-all cursor-pointer ${
                  mapLayers.find((l) => l.id === 'base')?.visible
                    ? 'bg-sat-panel text-sat-text border border-sat-borderLight shadow-xs font-extrabold'
                    : 'text-sat-dim hover:text-sat-text'
                }`}
                title="Switch to Dark Vector GIS Basemap"
              >
                <span>Dark GIS</span>
              </button>

              <button
                type="button"
                onClick={() => setBasemapMode('satellite')}
                className={`flex items-center gap-1.5 rounded px-2.5 py-1 font-bold transition-all cursor-pointer ${
                  mapLayers.find((l) => l.id === 'satellite')?.visible
                    ? 'bg-emerald-500 text-slate-950 shadow-md font-extrabold'
                    : 'text-emerald-400 hover:text-emerald-300'
                }`}
                title="Switch to True Earth Satellite Imagery Basemap"
              >
                <Satellite className="h-3.5 w-3.5" />
                <span>🛰️ Satellite Imagery</span>
              </button>
            </div>
          )}

          {hasImages && canvasViewMode === 'SCENE_INSPECT' && (
            <div className="pointer-events-auto">
              <ComparisonView
                compareMode={compareMode}
                onSetCompareMode={handleSetCompareMode}
                wipePosition={wipePosition}
                onWipeChange={setWipePosition}
                dateBefore={obsBefore?.date}
                dateAfter={obsAfter?.date}
                isMultiObs={isMultiObs}
              />
            </div>
          )}

          <div className="pointer-events-auto">
            <MapControls
              zoom={zoom}
              onZoomIn={handleZoomIn}
              onZoomOut={handleZoomOut}
              onReset={handleReset}
              showGrid={showGrid}
              onToggleGrid={() => setShowGrid((c) => !c)}
              showOverlays={showOverlays}
              onToggleOverlays={() => setShowOverlays((c) => !c)}
              showLayerPanel={showLayerPanel}
              onToggleLayerPanel={() => setShowLayerPanel((c) => !c)}
            />
          </div>
        </div>
      </div>

      {/* ==========================================================
          FLOATING LAYER PANEL
      ========================================================== */}
      {showLayerPanel && (
        <div className="absolute right-4 top-16 z-40 pointer-events-auto">
          <LayerControl
            layers={mapLayers}
            onToggleLayer={handleToggleLayer}
            onClose={() => setShowLayerPanel(false)}
          />
        </div>
      )}

      {/* ==========================================================
          LEFT MAP INSTRUMENT BAR
      ========================================================== */}
      <div className="absolute left-4 top-1/2 z-30 -translate-y-1/2 flex flex-col overflow-hidden rounded-md border border-sat-border bg-sat-surface/90 shadow-xl backdrop-blur-xl">
        <InstrumentButton
          icon={<BoxSelect className="h-3.5 w-3.5" />}
          label="AOI"
          active={isAoiMode}
          onClick={handleToggleAoiMode}
        />

        <InstrumentButton
          icon={<Target className="h-3.5 w-3.5" />}
          label="FOCUS"
          onClick={() => {
            if (activeObservation?.metadata?.lon && activeObservation?.metadata?.lat) {
              mapRef.current?.flyTo({
                center: [Number(activeObservation.metadata.lon), Number(activeObservation.metadata.lat)],
                zoom: 11,
              });
            } else {
              handleReset();
            }
          }}
        />

        <InstrumentButton
          icon={<Navigation className="h-3.5 w-3.5" />}
          label="RESET"
          onClick={handleReset}
        />

        <InstrumentButton
          icon={<Crosshair className="h-3.5 w-3.5" />}
          label="CENTER"
          onClick={() => {
            if (mapRef.current) {
              const center = mapRef.current.getCenter();
              setCursorCoords((prev) => ({
                ...prev,
                lat: `${Math.abs(center.lat).toFixed(4)}° ${center.lat >= 0 ? 'N' : 'S'}`,
                lon: `${Math.abs(center.lng).toFixed(4)}° ${center.lng >= 0 ? 'E' : 'W'}`,
                visible: true,
              }));
            }
          }}
        />

        <InstrumentButton
          icon={<Layers className="h-3.5 w-3.5" />}
          label="LAYERS"
          active={showLayerPanel}
          onClick={() => setShowLayerPanel((c) => !c)}
        />
      </div>

      {/* ==========================================================
          CENTRAL MAPLIBRE GEOGRAPHIC EARTH MAP
      ========================================================== */}
      <div className="relative flex min-h-0 flex-1 w-full items-center justify-center overflow-hidden">
        {/* MapLibre GL Canvas Container */}
        <div
          ref={mapContainerRef}
          className="absolute inset-0 h-full w-full bg-black z-0"
        />

        {/* GIS Grid Overlay */}
        {showGrid && (
          <div className="pointer-events-none absolute inset-0 z-10 bg-gis-grid opacity-25" />
        )}

        {/* Interactive AOI Drag Surface */}
        {isAoiMode && (
          <div
            className="absolute inset-0 z-20 cursor-crosshair select-none"
            onMouseDown={handleAoiOverlayMouseDown}
            onMouseMove={handleAoiOverlayMouseMove}
            onMouseUp={handleAoiOverlayMouseUp}
            onMouseLeave={() => {
              if (isDrawingRef.current) {
                isDrawingRef.current = false;
                dragBoxRef.current = null;
                setDragBox(null);
              }
            }}
          >
            {dragBox && (
              <div
                className="absolute border-2 border-dashed border-sky-400 bg-sky-500/20 shadow-[0_0_20px_rgba(56,189,248,0.5)] pointer-events-none"
                style={{
                  left: Math.min(dragBox.startX, dragBox.currentX),
                  top: Math.min(dragBox.startY, dragBox.currentY),
                  width: Math.abs(dragBox.currentX - dragBox.startX),
                  height: Math.abs(dragBox.currentY - dragBox.startY),
                }}
              >
                <div className="absolute -top-6 left-0 bg-sat-surface/95 border border-sky-400 text-sky-300 font-mono text-[9px] px-2 py-0.5 rounded shadow-lg whitespace-nowrap">
                  AOI: {Math.round(Math.abs(dragBox.currentX - dragBox.startX))} × {Math.round(Math.abs(dragBox.currentY - dragBox.startY))} px
                </div>
              </div>
            )}
          </div>
        )}

        {/* AOI Selection Hint Mode */}
        {isAoiMode && (
          <div className="pointer-events-none absolute top-20 left-1/2 -translate-x-1/2 z-30 flex items-center gap-2 rounded-full border border-sky-400 bg-black/80 px-4 py-1.5 font-mono text-xs font-semibold text-sky-300 shadow-2xl backdrop-blur-md animate-pulse">
            <BoxSelect className="h-4 w-4 text-sky-400" />
            <span>AOI DRAWING MODE: Click & drag on the map to define a bounding box</span>
          </div>
        )}

        {/* Observation Scene Inspection Card Mode */}
        {hasImages && canvasViewMode === 'SCENE_INSPECT' && (
          <div
            className="
              relative
              z-20
              h-[85%]
              w-[90%]
              max-h-[700px]
              rounded-lg
              border border-sat-accent/30
              bg-black/80
              shadow-2xl
              backdrop-blur-xl
              overflow-hidden
            "
          >
            {/* BASE IMAGE */}
            {(visibleLayerIds.includes('base') || visibleLayerIds.includes('satellite')) && (
              <div className="absolute inset-0 overflow-hidden rounded-lg bg-sat-surface flex items-center justify-center">
                {getObsImageUrl(compareMode === 'AFTER' && isMultiObs ? obsAfter : obsBefore) ? (
                  <img
                    src={getObsImageUrl(compareMode === 'AFTER' && isMultiObs ? obsAfter : obsBefore)}
                    alt="Satellite observation base"
                    className="h-full w-full object-contain bg-black/90"
                    draggable={false}
                    onError={(e) => {
                      (e.currentTarget as HTMLElement).style.display = 'none';
                      const fb = (e.currentTarget.parentNode as HTMLElement)?.querySelector('.canvas-preview-fallback') as HTMLElement;
                      if (fb) fb.style.display = 'flex';
                    }}
                  />
                ) : null}

                <div
                  className={`canvas-preview-fallback absolute inset-0 flex flex-col items-center justify-center p-4 text-center bg-sat-bg/90 ${
                    getObsImageUrl(compareMode === 'AFTER' && isMultiObs ? obsAfter : obsBefore) ? 'hidden' : 'flex'
                  }`}
                >
                  <Satellite className="h-8 w-8 text-sat-dim/50 mb-2" />
                  <span className="text-xs font-mono font-medium text-sat-dim">
                    Preview unavailable
                  </span>
                </div>
              </div>
            )}

            {/* BEFORE / AFTER WIPE */}
            {isMultiObs && compareMode === 'CHANGE' && (visibleLayerIds.includes('base') || visibleLayerIds.includes('satellite')) && (
              <div
                className="pointer-events-none absolute inset-0 overflow-hidden rounded-lg"
                style={{
                  clipPath: `polygon(0 0, ${wipePosition}% 0, ${wipePosition}% 100%, 0 100%)`,
                }}
              >
                <img
                  src={getObsImageUrl(obsAfter)}
                  alt="Satellite observation target"
                  className="h-full w-full object-contain bg-black/90"
                  draggable={false}
                />
                <div
                  className="absolute bottom-0 top-0 w-0.5 bg-sat-accent shadow-[0_0_12px_#38BDF8]"
                  style={{ left: `${wipePosition}%` }}
                />
              </div>
            )}

            {/* HEATMAP VISUALIZATION */}
            {showOverlays && overlayMode === 'HEATMAP' && activeResult && heatmapRegions.length > 0 && (
              <div className="pointer-events-none absolute inset-0 z-20 overflow-hidden rounded-lg">
                {heatmapRegions.map((region, idx) => {
                  const cx = (region.coords?.x ?? 30) + (region.coords?.width ?? 20) / 2;
                  const cy = (region.coords?.y ?? 30) + (region.coords?.height ?? 20) / 2;
                  const radius = Math.max(120, ((region.coords?.width ?? 20) + (region.coords?.height ?? 20)) * 3);

                  return (
                    <React.Fragment key={`heatmap-${region.id || idx}`}>
                      <div
                        className="absolute -translate-x-1/2 -translate-y-1/2 rounded-full opacity-80 mix-blend-screen animate-pulse"
                        style={{
                          left: `${cx}%`,
                          top: `${cy}%`,
                          width: `${radius * 1.5}px`,
                          height: `${radius * 1.5}px`,
                          background: 'radial-gradient(circle, rgba(239, 68, 68, 0.7) 0%, rgba(245, 158, 11, 0.5) 45%, rgba(14, 165, 233, 0.2) 75%, transparent 100%)',
                          filter: 'blur(16px)',
                        }}
                      />
                      <div
                        className="absolute -translate-x-1/2 -translate-y-1/2 rounded-full opacity-90 border border-amber-400/60 shadow-[0_0_35px_#ef4444]"
                        style={{
                          left: `${cx}%`,
                          top: `${cy}%`,
                          width: `${radius * 0.7}px`,
                          height: `${radius * 0.7}px`,
                          background: 'radial-gradient(circle, rgba(255, 255, 255, 0.95) 0%, rgba(239, 68, 68, 0.9) 35%, rgba(245, 158, 11, 0.7) 70%, transparent 100%)',
                          filter: 'blur(6px)',
                        }}
                      />
                      <div
                        className="absolute -translate-x-1/2 -translate-y-1/2 px-2.5 py-1 rounded bg-black/90 border border-red-500/80 font-mono text-xs font-bold text-amber-300 shadow-2xl"
                        style={{ left: `${cx}%`, top: `${cy - 14}%` }}
                      >
                        🔥 CHANGE DELTA: {region.confidence}%
                      </div>
                    </React.Fragment>
                  );
                })}

                <div className="absolute bottom-3 right-3 z-30 flex items-center gap-2.5 rounded-lg border border-sat-border bg-sat-surface/95 px-3.5 py-2 font-mono text-xs backdrop-blur-md shadow-xl">
                  <span className="text-sat-dim font-bold">SPECTRAL HEATMAP:</span>
                  <div className="h-2.5 w-24 rounded bg-gradient-to-r from-cyan-500 via-amber-400 to-red-600 border border-white/30" />
                  <span className="font-bold text-red-400">HIGH DELTA</span>
                </div>
              </div>
            )}

            {/* EVIDENCE LAYER */}
            {showOverlays && overlayMode === 'EVIDENCE' && activeResult?.evidence && (
              <EvidenceLayer
                evidence={activeResult.evidence}
                selectedRegionId={selectedRegionId}
                onSelectRegion={onSelectRegion}
                visibleLayers={visibleLayerIds}
              />
            )}

            {/* MAP CORNER LABEL */}
            <div className="pointer-events-none absolute left-3 top-3 z-30 rounded border border-white/10 bg-black/50 px-2 py-1.5 font-mono text-[7px] uppercase tracking-wider text-white/80 backdrop-blur-sm">
              <div>{sceneMetadata.modality}</div>
              <div className="mt-0.5 text-white/50">{sceneMetadata.resolution}</div>
            </div>

            {/* NORTH INDICATOR */}
            <div className="pointer-events-none absolute right-3 top-3 z-30 flex flex-col items-center rounded border border-white/10 bg-black/50 px-2 py-1.5 backdrop-blur-sm">
              <span className="font-mono text-[7px] font-bold text-white/80">N</span>
              <Navigation className="mt-0.5 h-3.5 w-3.5 rotate-0 fill-current text-white/70" />
            </div>

            {/* SCALE BAR */}
            <div className="pointer-events-none absolute bottom-3 left-3 z-30 rounded border border-white/10 bg-black/50 px-2 py-1.5 backdrop-blur-sm">
              <div className="flex items-end gap-2">
                <div>
                  <div className="h-1 w-16 border-x border-b border-white/70" />
                  <div className="mt-0.5 flex justify-between font-mono text-[6px] text-white/60">
                    <span>0</span>
                    <span>{zoom >= 2 ? '250 m' : zoom >= 1.25 ? '500 m' : '1 km'}</span>
                  </div>
                </div>
                <span className="font-mono text-[6px] uppercase text-white/50">SCALE</span>
              </div>
            </div>

            {/* EVIDENCE COUNT */}
            {activeResult && (
              <div className="pointer-events-none absolute bottom-3 right-3 z-30 flex items-center gap-2 rounded border border-sat-change/30 bg-black/60 px-2.5 py-1.5 font-mono backdrop-blur-sm">
                <MapPin className="h-3 w-3 text-sat-change" />
                <span className="text-[7px] uppercase text-white/60">EVIDENCE</span>
                <span className="text-[9px] font-bold text-sat-change">{activeEvidenceCount}</span>
              </div>
            )}
          </div>
        )}

        {/* Empty State Banner (Only when no images and user wants intro) */}
        {!hasImages && (
          <div className="pointer-events-none absolute top-6 left-1/2 -translate-x-1/2 z-20 max-w-md rounded-lg border border-sat-border/80 bg-sat-surface/90 p-4 text-center font-mono shadow-2xl backdrop-blur-xl">
            <div className="flex items-center justify-center gap-2 text-sat-accent">
              <Globe className="h-5 w-5" />
              <h3 className="font-display text-xs font-bold uppercase tracking-wider text-sat-text">
                Global Earth Canvas Active
              </h3>
            </div>
            <p className="mt-1 font-sans text-[11px] text-sat-muted leading-relaxed">
              Explore the planetary map, drag to pan, scroll to zoom, inspect real coordinates, or use the <strong className="text-sat-accent">AOI tool</strong> to select a region for satellite search.
            </p>
            {onSelectDemoScenario && (
              <button
                type="button"
                onClick={() => onSelectDemoScenario('demo-03')}
                className="pointer-events-auto mt-3 inline-flex items-center gap-1.5 rounded-md bg-sat-accent px-3 py-1.5 font-display text-[10px] font-bold uppercase tracking-wider text-slate-950 hover:bg-sky-300 transition-colors shadow-md"
              >
                <Sparkles className="h-3 w-3" />
                <span>Load Demo Observations</span>
              </button>
            )}
          </div>
        )}

        {/* Selected AOI Floating Action Card */}
        {localAOI && (
          <div className="absolute bottom-16 left-1/2 -translate-x-1/2 z-30 flex flex-wrap items-center gap-3 rounded-lg border border-sky-400/50 bg-sat-surface/95 px-4 py-2.5 shadow-2xl backdrop-blur-xl animate-in slide-in-from-bottom duration-200">
            <div className="flex items-center gap-2">
              <div className="flex h-7 w-7 items-center justify-center rounded-md bg-sky-500/20 text-sky-400">
                <BoxSelect className="h-4 w-4" />
              </div>
              <div>
                <div className="font-mono text-[9px] font-bold uppercase tracking-wider text-sat-text">
                  Selected AOI Bounding Box
                </div>
                <div className="font-mono text-[8px] text-sat-accent">
                  [{localAOI[0].toFixed(3)}, {localAOI[1].toFixed(3)}] → [{localAOI[2].toFixed(3)}, {localAOI[3].toFixed(3)}]
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2 ml-2">
              <button
                type="button"
                onClick={() => {
                  if (onOpenSatelliteSearch) {
                    onOpenSatelliteSearch(localAOI);
                  } else {
                    onSelectAOI?.(localAOI);
                  }
                }}
                className="flex items-center gap-1.5 rounded bg-sat-accent px-3 py-1.5 font-mono text-[10px] font-bold uppercase tracking-wider text-slate-950 hover:bg-sky-300 transition-all shadow-md"
                title="Search real satellite products in this AOI"
              >
                <Search className="h-3 w-3" />
                <span>Search Satellite Products</span>
              </button>

              <button
                type="button"
                onClick={handleClearAOI}
                className="flex items-center gap-1 rounded border border-sat-border bg-sat-bg/80 px-2 py-1.5 font-mono text-[10px] text-sat-dim hover:text-rose-400 hover:border-rose-400 transition-colors"
                title="Clear AOI selection"
              >
                <X className="h-3 w-3" />
                <span>Clear</span>
              </button>
            </div>
          </div>
        )}
      </div>

      {/* ==========================================================
          OVERLAY MODE STRIP (SCENE INSPECT)
      ========================================================== */}
      {hasImages && canvasViewMode === 'SCENE_INSPECT' && (
        <div className="absolute bottom-11 left-1/2 z-30 -translate-x-1/2 rounded-lg border border-sat-border bg-sat-surface/90 p-1 shadow-xl backdrop-blur-xl">
          <div className="flex items-center gap-1">
            <OverlayModeButton
              active={overlayMode === 'EVIDENCE'}
              icon={<Crosshair className="h-3 w-3" />}
              label="EVIDENCE"
              onClick={() => setOverlayMode('EVIDENCE')}
            />

            <OverlayModeButton
              active={overlayMode === 'HEATMAP'}
              icon={<Activity className="h-3 w-3" />}
              label="CHANGE HEATMAP"
              onClick={() => setOverlayMode('HEATMAP')}
            />
          </div>
        </div>
      )}

      {/* ==========================================================
          SATELLITE OBSERVATIONS QUICK SWITCHER RIBBON
      ========================================================== */}
      {observations.length > 0 && (
        <div className="absolute bottom-12 left-4 right-4 z-30 pointer-events-none flex justify-center">
          <div className="pointer-events-auto flex items-center gap-1.5 overflow-x-auto max-w-full rounded-xl border border-sat-border bg-sat-surface/95 px-2.5 py-1.5 shadow-2xl backdrop-blur-xl scrollbar-none">
            <div className="flex items-center gap-1 shrink-0 pr-1.5 border-r border-sat-border/60 text-[9px] font-bold font-mono text-sat-accent uppercase tracking-wider">
              <Satellite className="h-3 w-3 text-sat-accent animate-pulse" />
              <span className="hidden sm:inline">SATELLITE IMAGERY ({observations.length}):</span>
            </div>

            {observations.map((obs) => {
              const isActive = activeObservationIds.includes(obs.id);
              const isPrimary = obsBefore?.id === obs.id;
              const imgUrl = getObsImageUrl(obs);

              return (
                <button
                  key={obs.id}
                  type="button"
                  onClick={() => onSelectObservation ? onSelectObservation(obs.id) : null}
                  className={`
                    flex items-center gap-1.5 shrink-0 rounded-lg px-2 py-1 transition-all text-left cursor-pointer border text-[9px] font-mono
                    ${isPrimary
                      ? 'border-sat-accent bg-sat-accent/20 text-sat-text font-bold shadow-sm'
                      : isActive
                        ? 'border-sat-accent/40 bg-sat-panel/80 text-sat-text hover:border-sat-accent'
                        : 'border-sat-border bg-sat-bg/70 text-sat-muted hover:text-sat-text hover:bg-sat-panel'
                    }
                  `}
                  title={`Click to view: ${obs.name} (${obs.modality})`}
                >
                  {imgUrl ? (
                    <img
                      src={imgUrl}
                      alt={obs.name}
                      className="h-4 w-4 rounded object-cover border border-sat-border shrink-0"
                    />
                  ) : (
                    <Satellite className="h-3 w-3 shrink-0 text-sat-dim" />
                  )}

                  <span className="truncate max-w-[130px] font-sans font-medium">
                    {obs.name}
                  </span>

                  <span className={`text-[7px] uppercase font-bold px-1 rounded border ${
                    obs.modality === 'SAR'
                      ? 'border-violet-500/30 bg-violet-500/10 text-violet-400'
                      : obs.modality === 'MULTISPECTRAL'
                        ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400'
                        : 'border-sat-accent/30 bg-sat-accent/10 text-sat-accent'
                  }`}>
                    {obs.modality}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* ==========================================================
          BOTTOM TELEMETRY / GENUINE GEOGRAPHIC COORDINATE HUD
      ========================================================== */}
      <div className="relative z-40 shrink-0 border-t border-sat-border bg-sat-bg/95 px-3 py-2 backdrop-blur-xl sm:px-4">
        <div className="flex flex-wrap items-center justify-between gap-x-5 gap-y-1.5 font-mono text-[8px]">
          {/* Genuine Geographic coordinates */}
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
            <HudValue
              icon={<Crosshair className="h-3 w-3" />}
              label="LAT"
              value={cursorCoords.lat}
            />

            <HudValue
              icon={<MapPin className="h-3 w-3" />}
              label="LON"
              value={cursorCoords.lon}
            />

            <HudValue
              icon={<Gauge className="h-3 w-3" />}
              label="ZOOM"
              value={`Z ${mapZoomLevel.toFixed(1)}`}
            />

            <HudValue
              icon={<ScanLine className="h-3 w-3" />}
              label="GSD"
              value={sceneMetadata.resolution}
              hideOnSmall
            />
          </div>

          {/* Right status */}
          <div className="flex items-center gap-3">
            <span className="hidden items-center gap-1.5 text-sat-dim sm:flex">
              <Database className="h-3 w-3" />
              {activeObservationIds.length} DATASET{activeObservationIds.length === 1 ? '' : 'S'}
            </span>

            <span className="flex items-center gap-1.5 text-sat-stable">
              <span className="h-1.5 w-1.5 rounded-full bg-sat-stable shadow-[0_0_6px_currentColor]" />
              GEOGRAPHIC MAP READY
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

/* ================================================================
   TELEMETRY CELL
================================================================ */

interface TelemetryCellProps {
  label: string;
  value: any;
}

const TelemetryCell: React.FC<TelemetryCellProps> = ({ label, value }) => {
  const displayVal = typeof value === 'object' && value !== null ? JSON.stringify(value) : String(value || 'N/A');
  return (
    <div className="min-w-0 bg-sat-bg/90 px-2 py-2">
      <div className="font-mono text-[6px] uppercase tracking-wider text-sat-dim">
        {label}
      </div>

      <div
        className="mt-0.5 truncate font-mono text-[8px] font-semibold text-sat-text"
        title={displayVal}
      >
        {displayVal}
      </div>
    </div>
  );
};

/* ================================================================
   MAP INSTRUMENT BUTTON
================================================================ */

interface InstrumentButtonProps {
  icon: React.ReactNode;
  label: string;
  active?: boolean;
  onClick: () => void;
}

const InstrumentButton: React.FC<InstrumentButtonProps> = ({
  icon,
  label,
  active,
  onClick,
}) => {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`group flex h-10 w-11 flex-col items-center justify-center gap-0.5 border-b border-sat-border last:border-b-0 transition-colors ${
        active
          ? 'bg-sat-accent/20 text-sat-accent font-bold'
          : 'text-sat-dim hover:bg-sat-panel hover:text-sat-accent'
      }`}
      title={label}
    >
      {icon}
      <span className="font-mono text-[5px] font-bold tracking-wider">
        {label}
      </span>
    </button>
  );
};

/* ================================================================
   OVERLAY MODE BUTTON
================================================================ */

interface OverlayModeButtonProps {
  active: boolean;
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
}

const OverlayModeButton: React.FC<OverlayModeButtonProps> = ({
  active,
  icon,
  label,
  onClick,
}) => {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex items-center gap-1.5 rounded px-2.5 py-1.5 font-mono text-[7px] font-bold uppercase tracking-wider transition-all ${
        active
          ? 'bg-sat-accent text-slate-950'
          : 'text-sat-dim hover:bg-sat-panel hover:text-sat-text'
      }`}
    >
      {icon}
      {label}
    </button>
  );
};

/* ================================================================
   HUD VALUE
================================================================ */

interface HudValueProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  hideOnSmall?: boolean;
}

const HudValue: React.FC<HudValueProps> = ({
  icon,
  label,
  value,
  hideOnSmall,
}) => {
  return (
    <div
      className={`items-center gap-1.5 ${
        hideOnSmall ? 'hidden sm:flex' : 'flex'
      }`}
    >
      <span className="text-sat-accent">{icon}</span>
      <span className="text-sat-dim">{label}:</span>
      <span className="font-semibold text-sat-text">{value}</span>
    </div>
  );
};

export default EarthCanvas;
