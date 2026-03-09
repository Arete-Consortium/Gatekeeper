'use client';

import { useState, useRef, useMemo, useCallback } from 'react';
import dynamic from 'next/dynamic';
import { useQuery } from '@tanstack/react-query';
import { GatekeeperAPI } from '@/lib/api';
import { Card, Button, Badge, ErrorMessage, getUserFriendlyError } from '@/components/ui';
import { Toggle } from '@/components/ui/Toggle';
import {
  Map,
  Layers,
  Search,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Loader2,
  Navigation,
} from 'lucide-react';
import type { UniverseMapRef, MapLayers, MapSystem, MapGate } from '@/components/map/types';
import type { MapConfig, MapConfigSystem } from '@/lib/types';
import { useMapRoute } from '@/components/map/useMapRoute';
import { useIntelData } from '@/components/map/useIntelData';
import { useKillStream } from '@/components/map/useKillStream';
import { IntelControls } from '@/components/map/IntelControls';
import { RouteControls } from '@/components/map/RouteControls';

// Dynamically import the UniverseMap to avoid SSR issues with PixiJS
const UniverseMap = dynamic(
  () => import('@/components/map/UniverseMap').then((mod) => mod.UniverseMap),
  {
    ssr: false,
    loading: () => (
      <div className="absolute inset-0 flex items-center justify-center bg-black">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto mb-2" />
          <p className="text-text-secondary text-sm">Loading Universe Map...</p>
        </div>
      </div>
    ),
  }
);

// Transform /map/config response to map component types
function transformMapConfig(config: MapConfig): {
  systems: MapSystem[];
  gates: MapGate[];
  systemMap: globalThis.Map<number, MapSystem>;
  regionNames: globalThis.Map<number, string>;
} {
  const nameToId = new globalThis.Map<string, number>();
  const idToSystem = new globalThis.Map<number, MapSystem>();
  const regionNames = new globalThis.Map<number, string>();
  const mapSystems: MapSystem[] = [];

  for (const [name, sys] of Object.entries(config.systems)) {
    const mapSystem: MapSystem = {
      systemId: sys.id,
      name,
      x: sys.position.x,
      y: sys.position.y,
      security: sys.security,
      regionId: sys.region_id,
      constellationId: sys.constellation_id,
      hub: sys.hub,
      border: sys.border,
      spectralClass: sys.spectral_class,
      npcStations: sys.npc_stations,
    };
    nameToId.set(name, sys.id);
    idToSystem.set(sys.id, mapSystem);
    mapSystems.push(mapSystem);

    // Collect region names
    if (sys.region_name && !regionNames.has(sys.region_id)) {
      regionNames.set(sys.region_id, sys.region_name);
    }
  }

  const mapGates: MapGate[] = [];
  for (const gate of config.gates) {
    const fromId = nameToId.get(gate.from_system);
    const toId = nameToId.get(gate.to_system);
    if (fromId && toId) {
      mapGates.push({ fromSystemId: fromId, toSystemId: toId });
    }
  }

  return { systems: mapSystems, gates: mapGates, systemMap: idToSystem, regionNames };
}

export default function MapPage() {
  const mapRef = useRef<UniverseMapRef>(null);
  const [layers, setLayers] = useState<MapLayers>({
    showGates: true,
    showLabels: true,
    showRoute: true,
    showKills: true,
    showHeatmap: false,
    showRegionLabels: true,
  });
  const [colorMode, setColorMode] = useState<'security' | 'risk' | 'star'>('security');
  const [selectedSystem, setSelectedSystem] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [showRoutePanel, setShowRoutePanel] = useState(false);

  // Fetch map config (systems + gates in one call)
  const {
    data: mapConfig,
    isLoading: loadingConfig,
    error: configError,
  } = useQuery({
    queryKey: ['mapConfig'],
    queryFn: () => GatekeeperAPI.getMapConfig(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Transform data for the map
  const { systems, gates, systemMap, regionNames } = useMemo(() => {
    if (!mapConfig) return {
      systems: [] as MapSystem[],
      gates: [] as MapGate[],
      systemMap: new globalThis.Map<number, MapSystem>(),
      regionNames: new globalThis.Map<number, string>(),
    };
    return transformMapConfig(mapConfig);
  }, [mapConfig]);

  // Kill stream for live kill data
  // Set NEXT_PUBLIC_USE_MOCK_KILLS=true in .env.local for mock data
  const { kills, isConnected: killsConnected, isMock, reconnectAttempts, error: killStreamError } = useKillStream({
    maxAge: 60 * 60 * 1000, // 1 hour
    maxReconnectAttempts: 5,
  });

  // Intel data for risk assessment
  const {
    risks,
    totalKills,
    totalPods,
    isLoading: intelLoading,
    timeRange,
    setTimeRange,
    refresh: refreshIntel,
  } = useIntelData({
    timeRange: '24h',
    kills,
  });

  // Route planning
  const {
    state: routeState,
    mapRoutes,
    isLoading: routeLoading,
    error: routeError,
    comparisons,
    route,
    setMode: setRouteMode,
    setProfile: setRouteProfile,
    setBridges: setRouteBridges,
    setThera: setRouteThera,
    selectSystem: selectRouteSystem,
    clearRoute,
    swapOriginDestination,
    getSystemName,
  } = useMapRoute({
    systems: systemMap,
    compareProfiles: true,
  });

  // Filter systems by search - memoized for performance
  const filteredSystems = useMemo(() => {
    if (!searchQuery) return [];
    const lowerQuery = searchQuery.toLowerCase();
    return systems.filter((s) => s.name.toLowerCase().includes(lowerQuery));
  }, [systems, searchQuery]);

  // Memoized handlers to prevent unnecessary re-renders
  const handleZoomIn = useCallback(() => {
    const viewport = mapRef.current?.getViewport();
    if (viewport) {
      mapRef.current?.zoomTo(viewport.zoom * 1.5);
    }
  }, []);

  const handleZoomOut = useCallback(() => {
    const viewport = mapRef.current?.getViewport();
    if (viewport) {
      mapRef.current?.zoomTo(viewport.zoom / 1.5);
    }
  }, []);

  const handleFullscreen = useCallback(() => {
    const container = document.getElementById('map-container');
    if (container) {
      if (document.fullscreenElement) {
        document.exitFullscreen();
      } else {
        container.requestFullscreen();
      }
    }
  }, []);

  const handleSystemSelect = useCallback((systemId: number) => {
    setSelectedSystem(systemId);
    mapRef.current?.panTo(systemId);

    // If in route selection mode, handle route selection
    if (routeState.mode !== 'idle') {
      selectRouteSystem(systemId);
    }
  }, [routeState.mode, selectRouteSystem]);

  const handleSearchSelect = useCallback((system: MapSystem) => {
    setSearchQuery('');
    setSelectedSystem(system.systemId);
    mapRef.current?.panTo(system.systemId);

    // If in route selection mode, handle route selection
    if (routeState.mode !== 'idle') {
      selectRouteSystem(system.systemId);
    }
  }, [routeState.mode, selectRouteSystem]);

  const updateLayer = useCallback((key: keyof MapLayers, value: boolean) => {
    setLayers((prev) => ({ ...prev, [key]: value }));
  }, []);

  const isLoading = loadingConfig;
  const error = configError;

  return (
    <div className="h-[calc(100vh-theme(spacing.16)-theme(spacing.12))] flex flex-col">
      {/* Header Controls */}
      <div className="flex items-center justify-between gap-4 mb-4 flex-wrap">
        <div className="flex items-center gap-2">
          <h1 className="text-xl font-bold text-text flex items-center gap-2">
            <Map className="h-5 w-5" />
            Universe Map
          </h1>
          <Badge variant="info">Beta</Badge>
          {systems.length > 0 && (
            <Badge variant="default">{systems.length} systems</Badge>
          )}
        </div>

        {/* Quick Actions */}
        <div className="flex items-center gap-2 flex-wrap">
          <div className="relative">
            <label htmlFor="system-search" className="sr-only">Search for a system</label>
            <input
              id="system-search"
              type="text"
              role="combobox"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search system..."
              className="w-36 sm:w-48 px-3 py-1.5 bg-card border border-border rounded-lg text-sm text-text placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary"
              aria-autocomplete="list"
              aria-expanded={!!(searchQuery && filteredSystems.length > 0)}
              aria-controls="search-results"
              aria-haspopup="listbox"
            />
            <Search className="absolute right-2 top-1/2 -translate-y-1/2 h-4 w-4 text-text-secondary" aria-hidden="true" />

            {/* Search Results Dropdown */}
            {searchQuery && filteredSystems.length > 0 && (
              <div
                id="search-results"
                className="absolute z-50 w-full mt-1 bg-card border border-border rounded-lg shadow-lg max-h-60 overflow-y-auto"
                role="listbox"
                aria-label="System search results"
              >
                {filteredSystems.slice(0, 10).map((system) => (
                  <button
                    key={system.systemId}
                    onClick={() => handleSearchSelect(system)}
                    className="w-full px-3 py-2 text-left text-sm hover:bg-card-hover focus:bg-card-hover focus:outline-none flex justify-between items-center"
                    role="option"
                    aria-selected={false}
                    aria-label={`${system.name}, security ${system.security.toFixed(1)}`}
                  >
                    <span className="text-text">{system.name}</span>
                    <span
                      className={`text-xs ${
                        system.security >= 0.5
                          ? 'text-high-sec'
                          : system.security > 0
                            ? 'text-low-sec'
                            : 'text-null-sec'
                      }`}
                    >
                      {system.security.toFixed(1)}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>
          <Button
            variant={showRoutePanel ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => setShowRoutePanel(!showRoutePanel)}
            aria-label={showRoutePanel ? 'Close route planner' : 'Open route planner'}
            aria-pressed={showRoutePanel}
          >
            <Navigation className="h-4 w-4" aria-hidden="true" />
          </Button>
          <Button variant="ghost" size="sm" onClick={handleZoomIn} aria-label="Zoom in">
            <ZoomIn className="h-4 w-4" aria-hidden="true" />
          </Button>
          <Button variant="ghost" size="sm" onClick={handleZoomOut} aria-label="Zoom out">
            <ZoomOut className="h-4 w-4" aria-hidden="true" />
          </Button>
          <Button variant="ghost" size="sm" onClick={handleFullscreen} aria-label="Toggle fullscreen mode">
            <Maximize2 className="h-4 w-4" aria-hidden="true" />
          </Button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col lg:flex-row gap-4 min-h-0">
        {/* Map Container */}
        <div
          id="map-container"
          className="flex-1 min-h-[300px] lg:min-h-0 bg-black rounded-lg border border-border relative overflow-hidden"
          role="application"
          aria-label="Interactive universe map"
        >
          {error ? (
            <div className="absolute inset-0 flex items-center justify-center p-4">
              <ErrorMessage
                title="Unable to load map data"
                message={getUserFriendlyError(error)}
                className="max-w-md"
              />
            </div>
          ) : isLoading ? (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center">
                <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto mb-2" />
                <p className="text-text-secondary text-sm">Loading map data...</p>
              </div>
            </div>
          ) : (
            <>
              <UniverseMap
                ref={mapRef}
                systems={systems}
                gates={gates}
                regionNames={regionNames}
                routes={mapRoutes}
                kills={kills}
                risks={risks}
                layers={layers}
                colorMode={colorMode}
                selectedSystem={selectedSystem}
                onSystemClick={handleSystemSelect}
              />

              {/* Route Controls Panel */}
              {showRoutePanel && (
                <RouteControls
                  state={routeState}
                  getSystemName={getSystemName}
                  isLoading={routeLoading}
                  error={routeError}
                  comparisons={comparisons}
                  routeSummary={route ? {
                    jumps: route.total_jumps,
                    maxRisk: route.max_risk,
                    avgRisk: route.avg_risk,
                  } : null}
                  onModeChange={setRouteMode}
                  onProfileChange={setRouteProfile}
                  onBridgesChange={setRouteBridges}
                  onTheraChange={setRouteThera}
                  onClearRoute={clearRoute}
                  onSwapRoute={swapOriginDestination}
                />
              )}

              {/* Intel Controls Panel */}
              <div className="absolute top-4 right-4 z-10">
                <IntelControls
                  timeRange={timeRange}
                  onTimeRangeChange={setTimeRange}
                  showKillMarkers={layers.showKills}
                  onShowKillMarkersChange={(v) => updateLayer('showKills', v)}
                  showHeatmap={layers.showHeatmap}
                  onShowHeatmapChange={(v) => updateLayer('showHeatmap', v)}
                  totalKills={totalKills}
                  totalPods={totalPods}
                  isConnected={killsConnected}
                  isLoading={intelLoading}
                  onRefresh={refreshIntel}
                  className="w-72"
                />
              </div>
            </>
          )}
        </div>

        {/* Side Panel - hidden on mobile, shown on lg+ screens */}
        <aside className="hidden lg:flex w-72 flex-col gap-4 overflow-y-auto" aria-label="Map controls">
          {/* Layer Controls */}
          <Card>
            <div className="flex items-center gap-2 mb-3">
              <Layers className="h-4 w-4 text-text-secondary" aria-hidden="true" />
              <span className="text-sm font-medium text-text">Layers</span>
            </div>
            <div className="space-y-3">
              <Toggle
                checked={layers.showGates}
                onChange={(v) => updateLayer('showGates', v)}
                label="Gate connections"
              />
              <Toggle
                checked={layers.showLabels}
                onChange={(v) => updateLayer('showLabels', v)}
                label="System labels"
              />
              <Toggle
                checked={layers.showRoute}
                onChange={(v) => updateLayer('showRoute', v)}
                label="Route overlay"
              />
              <Toggle
                checked={layers.showKills}
                onChange={(v) => updateLayer('showKills', v)}
                label="Kill markers"
              />
              <Toggle
                checked={layers.showHeatmap}
                onChange={(v) => updateLayer('showHeatmap', v)}
                label="Risk heatmap"
              />
            </div>
          </Card>

          {/* Color Mode */}
          <Card>
            <div className="flex items-center gap-2 mb-3">
              <div className="h-3 w-3 rounded-full bg-gradient-to-r from-high-sec via-low-sec to-null-sec" />
              <span className="text-sm font-medium text-text">Color Mode</span>
            </div>
            <div className="flex gap-2 flex-wrap">
              <Button
                variant={colorMode === 'security' ? 'primary' : 'secondary'}
                size="sm"
                onClick={() => setColorMode('security')}
                className="flex-1"
              >
                Security
              </Button>
              <Button
                variant={colorMode === 'risk' ? 'primary' : 'secondary'}
                size="sm"
                onClick={() => setColorMode('risk')}
                className="flex-1"
              >
                Risk
              </Button>
              <Button
                variant={colorMode === 'star' ? 'primary' : 'secondary'}
                size="sm"
                onClick={() => setColorMode('star')}
                className="flex-1"
              >
                Star
              </Button>
            </div>
          </Card>

          {/* Selected System Info */}
          {selectedSystem && (
            <Card>
              <span className="text-sm font-medium text-text mb-2 block">
                Selected System
              </span>
              {(() => {
                const system = systems.find((s) => s.systemId === selectedSystem);
                if (!system) return null;
                return (
                  <div className="space-y-2">
                    <p className="text-lg font-bold text-text">{system.name}</p>
                    <div className="flex items-center gap-2">
                      <span className="text-text-secondary text-sm">Security:</span>
                      <span
                        className={`font-mono ${
                          system.security >= 0.5
                            ? 'text-high-sec'
                            : system.security > 0
                              ? 'text-low-sec'
                              : 'text-null-sec'
                        }`}
                      >
                        {system.security.toFixed(2)}
                      </span>
                    </div>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setSelectedSystem(null)}
                      className="w-full mt-2"
                    >
                      Clear Selection
                    </Button>
                  </div>
                );
              })()}
            </Card>
          )}

          {/* Legend */}
          <Card>
            <span className="text-sm font-medium text-text mb-3 block">Legend</span>
            <div className="space-y-2 text-xs">
              <div className="flex items-center gap-2">
                <div className="h-3 w-3 rounded-full bg-high-sec" aria-hidden="true" />
                <span className="text-text-secondary">High Sec (0.5 - 1.0)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="h-3 w-3 rounded-full bg-low-sec" aria-hidden="true" />
                <span className="text-text-secondary">Low Sec (0.1 - 0.4)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="h-3 w-3 rounded-full bg-null-sec" aria-hidden="true" />
                <span className="text-text-secondary">Null Sec (0.0 and below)</span>
              </div>
            </div>
          </Card>
        </aside>
      </div>
    </div>
  );
}
