'use client';

import { useState, useRef, useMemo } from 'react';
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
import type { System, Gate } from '@/lib/types';
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

// Transform API System to MapSystem
function transformSystem(system: System): MapSystem {
  return {
    systemId: system.system_id ?? 0,
    name: system.name ?? 'Unknown',
    x: (system.x ?? 0) / 1e16, // Scale down EVE coordinates
    y: (system.y ?? 0) / 1e16,
    security: system.security_status ?? 0,
    regionId: system.region_id ?? 0,
    constellationId: system.constellation_id ?? 0,
  };
}

// Transform API Gate to MapGate
function transformGate(gate: Gate, systemNameToId: Map<string, number>): MapGate | null {
  const fromId = systemNameToId.get(gate.from_system);
  const toId = systemNameToId.get(gate.to_system);
  if (!fromId || !toId) return null;
  return {
    fromSystemId: fromId,
    toSystemId: toId,
  };
}

export default function MapPage() {
  const mapRef = useRef<UniverseMapRef>(null);
  const [layers, setLayers] = useState<MapLayers>({
    showGates: true,
    showLabels: true,
    showRoute: true,
    showKills: true,
    showHeatmap: false,
  });
  const [colorMode, setColorMode] = useState<'security' | 'risk'>('security');
  const [selectedSystem, setSelectedSystem] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [showRoutePanel, setShowRoutePanel] = useState(false);

  // Fetch systems from API
  const {
    data: systemsData,
    isLoading: loadingSystems,
    error: systemsError,
  } = useQuery({
    queryKey: ['systems'],
    queryFn: () => GatekeeperAPI.getSystems(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Fetch map config (includes gates)
  const {
    data: mapConfig,
    isLoading: loadingConfig,
    error: configError,
  } = useQuery({
    queryKey: ['mapConfig'],
    queryFn: () => GatekeeperAPI.getMapConfig(),
    staleTime: 5 * 60 * 1000,
  });

  // Transform data for the map
  const { systems, gates, systemMap } = useMemo(() => {
    if (!systemsData) return {
      systems: [] as MapSystem[],
      gates: [] as MapGate[],
      systemMap: new globalThis.Map<number, MapSystem>(),
    };

    const nameToId: globalThis.Map<string, number> = new globalThis.Map();
    const idToSystem: globalThis.Map<number, MapSystem> = new globalThis.Map();
    const mapSystems = systemsData.map((s) => {
      nameToId.set(s.name, s.system_id);
      const mapSystem = transformSystem(s);
      idToSystem.set(s.system_id, mapSystem);
      return mapSystem;
    });

    const mapGates: MapGate[] = [];
    if (mapConfig?.gates) {
      for (const gate of mapConfig.gates) {
        const mapped = transformGate(gate, nameToId);
        if (mapped) mapGates.push(mapped);
      }
    }

    return { systems: mapSystems, gates: mapGates, systemMap: idToSystem };
  }, [systemsData, mapConfig]);

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
    systemData: systemsData,
    compareProfiles: true,
  });

  // Filter systems by search
  const filteredSystems = searchQuery
    ? systems.filter((s) =>
        s.name.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : [];

  const handleZoomIn = () => {
    const viewport = mapRef.current?.getViewport();
    if (viewport) {
      mapRef.current?.zoomTo(viewport.zoom * 1.5);
    }
  };

  const handleZoomOut = () => {
    const viewport = mapRef.current?.getViewport();
    if (viewport) {
      mapRef.current?.zoomTo(viewport.zoom / 1.5);
    }
  };

  const handleFullscreen = () => {
    const container = document.getElementById('map-container');
    if (container) {
      if (document.fullscreenElement) {
        document.exitFullscreen();
      } else {
        container.requestFullscreen();
      }
    }
  };

  const handleSystemSelect = (systemId: number) => {
    setSelectedSystem(systemId);
    mapRef.current?.panTo(systemId);

    // If in route selection mode, handle route selection
    if (routeState.mode !== 'idle') {
      selectRouteSystem(systemId);
    }
  };

  const handleSearchSelect = (system: MapSystem) => {
    setSearchQuery('');
    handleSystemSelect(system.systemId);
  };

  const updateLayer = (key: keyof MapLayers, value: boolean) => {
    setLayers((prev) => ({ ...prev, [key]: value }));
  };

  const isLoading = loadingSystems || loadingConfig;
  const error = systemsError || configError;

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
            <div className="flex gap-2">
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
