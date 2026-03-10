'use client';

import { Suspense, useState, useRef, useMemo, useCallback, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { useSearchParams, useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { GatekeeperAPI } from '@/lib/api';
import { Card, Button, Badge, ErrorMessage, getUserFriendlyError } from '@/components/ui';
import { Toggle } from '@/components/ui/Toggle';
import {
  Map,
  Layers,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Loader2,
  Navigation,
  ChevronDown,
  ChevronRight,
  Palette,
  Info,
  Menu,
  X,
  Link2,
  Check,
} from 'lucide-react';
import type { UniverseMapRef, MapLayers, MapSystem, MapGate } from '@/components/map/types';
import type { MapConfig } from '@/lib/types';
import { useMapRoute } from '@/components/map/useMapRoute';
import { useIntelData } from '@/components/map/useIntelData';
import { useKillStream } from '@/components/map/useKillStream';
import { IntelControls } from '@/components/map/IntelControls';
import { RouteControls } from '@/components/map/RouteControls';
import { SystemDetailPanel } from '@/components/map/SystemDetailPanel';
import { SystemSearch } from '@/components/map/SystemSearch';

// Dynamically import the UniverseMap to avoid SSR issues with PixiJS
const UniverseMap = dynamic(
  () => import('@/components/map/UniverseMap').then((mod) => mod.UniverseMap),
  {
    ssr: false,
    loading: () => (
      <div className="absolute inset-0 flex items-center justify-center bg-black">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto mb-2" />
          <p className="text-text-secondary text-sm">Loading New Eden Map...</p>
        </div>
      </div>
    ),
  }
);

// Collapsible section component for sidebar
function CollapsibleSection({
  title,
  icon,
  defaultOpen = true,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <Card>
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2 text-left"
      >
        {icon}
        <span className="text-sm font-medium text-text flex-1">{title}</span>
        {open ? (
          <ChevronDown className="h-3.5 w-3.5 text-text-secondary" />
        ) : (
          <ChevronRight className="h-3.5 w-3.5 text-text-secondary" />
        )}
      </button>
      {open && <div className="mt-3">{children}</div>}
    </Card>
  );
}

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
      regionName: sys.region_name,
      constellationName: sys.constellation_name,
    };
    nameToId.set(name, sys.id);
    idToSystem.set(sys.id, mapSystem);
    mapSystems.push(mapSystem);

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
  return (
    <Suspense fallback={
      <div className="h-[calc(100vh-theme(spacing.16)-theme(spacing.12))] flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    }>
      <MapPageContent />
    </Suspense>
  );
}

function MapPageContent() {
  const mapRef = useRef<UniverseMapRef>(null);
  const searchParams = useSearchParams();
  const router = useRouter();
  const [linkCopied, setLinkCopied] = useState(false);
  const initializedFromUrl = useRef(false);
  const [layers, setLayers] = useState<MapLayers>({
    showGates: true,
    showLabels: true,
    showRoute: true,
    showKills: true,
    showHeatmap: false,
    showRegionLabels: true,
    showSovereignty: false,
    showThera: true,
    showFW: false,
    showLandmarks: true,
    showSovStructures: false,
  });
  const [colorMode, setColorMode] = useState<'security' | 'risk' | 'star'>('security');
  const [selectedSystem, setSelectedSystem] = useState<number | null>(null);
  const [showRoutePanel, setShowRoutePanel] = useState(false);
  const [showMobileSidebar, setShowMobileSidebar] = useState(false);

  // === Data Fetching ===

  const {
    data: mapConfig,
    isLoading: loadingConfig,
    error: configError,
  } = useQuery({
    queryKey: ['mapConfig'],
    queryFn: () => GatekeeperAPI.getMapConfig(),
    staleTime: 5 * 60 * 1000,
  });

  const { data: sovData } = useQuery({
    queryKey: ['sovereignty'],
    queryFn: () => GatekeeperAPI.getSovereignty(),
    staleTime: 10 * 60 * 1000,
    enabled: !!mapConfig,
  });

  const { data: theraData } = useQuery({
    queryKey: ['thera'],
    queryFn: () => GatekeeperAPI.getTheraConnections(),
    staleTime: 5 * 60 * 1000,
    enabled: !!mapConfig,
  });

  const { data: fwData } = useQuery({
    queryKey: ['fw'],
    queryFn: () => GatekeeperAPI.getFWStatus(),
    staleTime: 10 * 60 * 1000,
    enabled: !!mapConfig,
  });

  const { data: sovStructData } = useQuery({
    queryKey: ['sovStructures'],
    queryFn: () => GatekeeperAPI.getSovStructures(),
    staleTime: 30 * 60 * 1000,
    enabled: !!mapConfig,
  });

  const { data: activityData } = useQuery({
    queryKey: ['systemActivity'],
    queryFn: () => GatekeeperAPI.getSystemActivity(),
    staleTime: 5 * 60 * 1000,
    enabled: !!mapConfig,
  });

  // === Transform ===

  const { systems, gates, systemMap, regionNames } = useMemo(() => {
    if (!mapConfig) return {
      systems: [] as MapSystem[],
      gates: [] as MapGate[],
      systemMap: new globalThis.Map<number, MapSystem>(),
      regionNames: new globalThis.Map<number, string>(),
    };
    return transformMapConfig(mapConfig);
  }, [mapConfig]);

  // Kill stream
  const { kills, isConnected: killsConnected } = useKillStream({
    maxAge: 60 * 60 * 1000,
    maxReconnectAttempts: 5,
  });

  // Intel data
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
    setOrigin: setRouteOrigin,
    setDestination: setRouteDestination,
    addAvoidSystem,
    clearRoute,
    swapOriginDestination,
    getSystemName,
  } = useMapRoute({
    systems: systemMap,
    compareProfiles: true,
  });

  // === Derived ===

  const sovOverlay = useMemo(() => {
    if (!sovData) return { sovereignty: undefined, alliances: undefined };
    const sovereignty: Record<string, { alliance_id: number | null; faction_id: number | null }> = {};
    for (const [sid, entry] of Object.entries(sovData.sovereignty)) {
      sovereignty[sid] = {
        alliance_id: entry.alliance_id ?? null,
        faction_id: entry.faction_id ?? null,
      };
    }
    const alliances: Record<string, { name: string }> = {};
    for (const [aid, info] of Object.entries(sovData.alliances)) {
      alliances[aid] = { name: info.name };
    }
    return { sovereignty, alliances };
  }, [sovData]);

  // === URL Permalink Support ===

  // On mount (once systems are loaded), restore state from URL params
  useEffect(() => {
    if (initializedFromUrl.current || systems.length === 0) return;
    initializedFromUrl.current = true;

    const systemParam = searchParams.get('system');
    const xParam = searchParams.get('x');
    const yParam = searchParams.get('y');
    const zoomParam = searchParams.get('zoom');

    // Restore viewport if x/y/zoom are present
    if (xParam && yParam && zoomParam) {
      const x = parseFloat(xParam);
      const y = parseFloat(yParam);
      const zoom = parseFloat(zoomParam);
      if (!isNaN(x) && !isNaN(y) && !isNaN(zoom)) {
        // Small delay to ensure map is mounted
        requestAnimationFrame(() => {
          mapRef.current?.setViewport({ x, y, zoom });
        });
      }
    }

    // Restore selected system
    if (systemParam) {
      const systemId = parseInt(systemParam, 10);
      if (!isNaN(systemId) && systemMap.has(systemId)) {
        setSelectedSystem(systemId);
        // Only pan if no explicit viewport was provided
        if (!xParam) {
          requestAnimationFrame(() => {
            mapRef.current?.panTo(systemId);
          });
        }
      }
    }
  }, [systems.length, systemMap, searchParams]);

  // Update URL when selectedSystem changes (shallow, no reload)
  useEffect(() => {
    if (!initializedFromUrl.current) return;

    const params = new URLSearchParams(searchParams.toString());
    if (selectedSystem !== null) {
      params.set('system', String(selectedSystem));
    } else {
      params.delete('system');
    }

    // Remove viewport params from auto-update (only set by Copy Link)
    params.delete('x');
    params.delete('y');
    params.delete('zoom');

    const newUrl = params.toString() ? `?${params.toString()}` : '/map';
    router.replace(`/map${newUrl}`, { scroll: false });
  }, [selectedSystem, router, searchParams]);

  // Copy permalink handler
  const handleCopyLink = useCallback(() => {
    const viewport = mapRef.current?.getViewport();
    const params = new URLSearchParams();

    if (viewport) {
      params.set('x', viewport.x.toFixed(1));
      params.set('y', viewport.y.toFixed(1));
      params.set('zoom', viewport.zoom.toFixed(4));
    }

    if (selectedSystem !== null) {
      params.set('system', String(selectedSystem));
    }

    const url = `${window.location.origin}/map?${params.toString()}`;
    navigator.clipboard.writeText(url).then(() => {
      setLinkCopied(true);
      setTimeout(() => setLinkCopied(false), 2000);
    });
  }, [selectedSystem]);

  // === Context Menu Handlers ===

  const handleSetRouteOrigin = useCallback((systemId: number) => {
    setRouteOrigin(systemId);
    setShowRoutePanel(true);
  }, [setRouteOrigin]);

  const handleSetRouteDestination = useCallback((systemId: number) => {
    setRouteDestination(systemId);
    setShowRoutePanel(true);
  }, [setRouteDestination]);

  const handleAvoidSystem = useCallback((systemId: number) => {
    addAvoidSystem(systemId);
    setShowRoutePanel(true);
  }, [addAvoidSystem]);

  // === Handlers ===

  const handleZoomIn = useCallback(() => {
    const viewport = mapRef.current?.getViewport();
    if (viewport) mapRef.current?.zoomTo(viewport.zoom * 1.5);
  }, []);

  const handleZoomOut = useCallback(() => {
    const viewport = mapRef.current?.getViewport();
    if (viewport) mapRef.current?.zoomTo(viewport.zoom / 1.5);
  }, []);

  const handleFullscreen = useCallback(() => {
    const container = document.getElementById('map-container');
    if (container) {
      if (document.fullscreenElement) document.exitFullscreen();
      else container.requestFullscreen();
    }
  }, []);

  const handleSystemSelect = useCallback((systemId: number) => {
    setSelectedSystem(systemId);
    mapRef.current?.panTo(systemId);
    if (routeState.mode !== 'idle') selectRouteSystem(systemId);
  }, [routeState.mode, selectRouteSystem]);

  const handleSearchSelect = useCallback((system: MapSystem) => {
    setSelectedSystem(system.systemId);
    mapRef.current?.panTo(system.systemId);
    if (routeState.mode !== 'idle') selectRouteSystem(system.systemId);
  }, [routeState.mode, selectRouteSystem]);

  const updateLayer = useCallback((key: keyof MapLayers, value: boolean) => {
    setLayers((prev) => ({ ...prev, [key]: value }));
  }, []);

  const isLoading = loadingConfig;
  const error = configError;

  // Shared sidebar content used in both desktop aside and mobile overlay
  const sidebarContent = (
    <>
      {/* Layers — collapsible */}
      <CollapsibleSection
        title="Layers"
        icon={<Layers className="h-4 w-4 text-text-secondary" aria-hidden="true" />}
      >
        <div className="space-y-2.5">
          <Toggle checked={layers.showGates} onChange={(v) => updateLayer('showGates', v)} label="Gate connections" />
          <Toggle checked={layers.showLabels} onChange={(v) => updateLayer('showLabels', v)} label="System labels" />
          <Toggle checked={layers.showRegionLabels} onChange={(v) => updateLayer('showRegionLabels', v)} label="Region labels" />
          <Toggle checked={layers.showRoute} onChange={(v) => updateLayer('showRoute', v)} label="Route overlay" />
          <Toggle checked={layers.showKills} onChange={(v) => updateLayer('showKills', v)} label="Kill markers" />
          <Toggle checked={layers.showHeatmap} onChange={(v) => updateLayer('showHeatmap', v)} label="Risk heatmap" />
          <Toggle checked={layers.showSovereignty} onChange={(v) => updateLayer('showSovereignty', v)} label="Sovereignty" />
          <Toggle checked={layers.showThera} onChange={(v) => updateLayer('showThera', v)} label="Thera connections" />
          <Toggle checked={layers.showFW} onChange={(v) => updateLayer('showFW', v)} label="Faction warfare" />
          <Toggle checked={layers.showLandmarks} onChange={(v) => updateLayer('showLandmarks', v)} label="Landmarks" />
          <Toggle checked={layers.showSovStructures} onChange={(v) => updateLayer('showSovStructures', v)} label="iHub ADM levels" />
        </div>
      </CollapsibleSection>

      {/* Color Mode — collapsible */}
      <CollapsibleSection
        title="Color Mode"
        icon={<Palette className="h-4 w-4 text-text-secondary" aria-hidden="true" />}
        defaultOpen={false}
      >
        <div className="flex gap-2 flex-wrap">
          <Button variant={colorMode === 'security' ? 'primary' : 'secondary'} size="sm" onClick={() => setColorMode('security')} className="flex-1">Security</Button>
          <Button variant={colorMode === 'risk' ? 'primary' : 'secondary'} size="sm" onClick={() => setColorMode('risk')} className="flex-1">Risk</Button>
          <Button variant={colorMode === 'star' ? 'primary' : 'secondary'} size="sm" onClick={() => setColorMode('star')} className="flex-1">Star</Button>
        </div>
      </CollapsibleSection>

      {/* System Detail Panel — replaces old inline info */}
      {selectedSystem && (() => {
        const system = systems.find((s) => s.systemId === selectedSystem);
        if (!system) return null;
        return (
          <Card>
            <SystemDetailPanel
              system={system}
              gates={gates}
              systemMap={systemMap}
              sovData={sovData}
              fwData={fwData?.fw_systems}
              theraConnections={theraData?.connections}
              activityData={activityData}
              kills={kills}
              riskData={risks.find((r) => r.systemId === selectedSystem)}
              onClose={() => setSelectedSystem(null)}
              onSystemClick={handleSystemSelect}
              onSetOrigin={handleSetRouteOrigin}
              onSetDestination={handleSetRouteDestination}
            />
          </Card>
        );
      })()}

      {/* Legend — collapsed by default */}
      <CollapsibleSection
        title="Legend"
        icon={<Info className="h-4 w-4 text-text-secondary" aria-hidden="true" />}
        defaultOpen={false}
      >
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
          <div className="flex items-center gap-2 mt-2">
            <div className="h-3 w-3 rounded-full border-2 border-yellow-500" aria-hidden="true" />
            <span className="text-text-secondary">Trade Hub</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-2 w-4 border border-cyan-400 rounded-sm" style={{ borderStyle: 'dashed' }} aria-hidden="true" />
            <span className="text-text-secondary">Thera Connection</span>
          </div>
        </div>
      </CollapsibleSection>
    </>
  );

  return (
    <div className="-mx-4 -mb-6 sm:mx-0 sm:mb-0 h-[calc(100vh-theme(spacing.16)-theme(spacing.6))] sm:h-[calc(100vh-theme(spacing.16)-theme(spacing.12))] flex flex-col">
      {/* Header Controls */}
      <div className="flex items-center justify-between gap-4 mb-4 flex-wrap">
        <div className="flex items-center gap-2">
          <h1 className="text-xl font-bold text-text flex items-center gap-2">
            <Map className="h-5 w-5" />
            New Eden Map
          </h1>
          <Badge variant="info">Beta</Badge>
          {systems.length > 0 && (
            <Badge variant="default">{systems.length} systems</Badge>
          )}
        </div>

        {/* Quick Actions */}
        <div className="flex items-center gap-2 flex-wrap">
          {/* Intel Controls — inline in toolbar */}
          <div className="relative">
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
              className="w-auto min-w-0"
            />
          </div>
          <SystemSearch
            systems={systems}
            onSelect={handleSearchSelect}
          />
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
          <Button
            variant="ghost"
            size="sm"
            onClick={handleCopyLink}
            aria-label="Copy map link to clipboard"
            title="Copy link"
          >
            {linkCopied ? (
              <Check className="h-4 w-4 text-green-400" aria-hidden="true" />
            ) : (
              <Link2 className="h-4 w-4" aria-hidden="true" />
            )}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="lg:hidden"
            onClick={() => setShowMobileSidebar(!showMobileSidebar)}
            aria-label={showMobileSidebar ? 'Close sidebar' : 'Open sidebar'}
          >
            <Menu className="h-4 w-4" aria-hidden="true" />
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
                sovereignty={sovOverlay.sovereignty}
                alliances={sovOverlay.alliances}
                theraConnections={theraData?.connections}
                fwSystems={fwData?.fw_systems}
                landmarks={mapConfig?.landmarks}
                sovStructures={sovStructData?.structures}
                layers={layers}
                colorMode={colorMode}
                selectedSystem={selectedSystem}
                onSystemClick={handleSystemSelect}
                onSetRouteOrigin={handleSetRouteOrigin}
                onSetRouteDestination={handleSetRouteDestination}
                onAvoidSystem={handleAvoidSystem}
                onDeselect={() => setSelectedSystem(null)}
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

            </>
          )}
        </div>

        {/* Mobile Sidebar Overlay */}
        {showMobileSidebar && (
          <>
            <div
              className="fixed inset-0 bg-black/50 z-40 lg:hidden"
              onClick={() => setShowMobileSidebar(false)}
              aria-hidden="true"
            />
            <div className="fixed right-0 top-0 h-full w-full sm:w-72 max-w-[320px] bg-card border-l border-border z-50 overflow-y-auto p-4 lg:hidden">
              <div className="flex justify-end mb-3">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowMobileSidebar(false)}
                  aria-label="Close sidebar"
                >
                  <X className="h-4 w-4" aria-hidden="true" />
                </Button>
              </div>
              <div className="flex flex-col gap-3">
                {sidebarContent}
              </div>
            </div>
          </>
        )}

        {/* Side Panel — collapsible sections */}
        <aside className="hidden lg:flex w-72 flex-col gap-3 overflow-y-auto" aria-label="Map controls">
          {sidebarContent}
        </aside>
      </div>
    </div>
  );
}
