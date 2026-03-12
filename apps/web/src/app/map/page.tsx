'use client';

import { Suspense, useState, useRef, useMemo, useCallback, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { useSearchParams, useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { GatekeeperAPI } from '@/lib/api';
import { Card, Button, ErrorMessage, getUserFriendlyError } from '@/components/ui';
import { Toggle } from '@/components/ui/Toggle';
import Link from 'next/link';
import {
  AlertCircle,
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
  RefreshCw,
  Lock,
} from 'lucide-react';
import type { UniverseMapRef, MapLayers, MapSystem, MapGate } from '@/components/map/types';
import type { MapConfig } from '@/lib/types';
import { useMapRoute } from '@/components/map/useMapRoute';
import { useIntelData } from '@/components/map/useIntelData';
import { useKillStream } from '@/components/map/useKillStream';
import { RouteControls } from '@/components/map/RouteControls';
import { SystemDetailPanel } from '@/components/map/SystemDetailPanel';
import { SystemSearch } from '@/components/map/SystemSearch';
import { useAuth } from '@/contexts/AuthContext';
import { SavedRoutes } from '@/components/map/SavedRoutes';
import { Bookmark } from 'lucide-react';

// Dynamically import the UniverseMap to avoid SSR issues with PixiJS
const UniverseMap = dynamic(
  () => import('@/components/map/UniverseMap').then((mod) => mod.UniverseMap),
  {
    ssr: false,
    loading: () => (
      <div className="absolute inset-0 flex items-center justify-center" style={{ backgroundColor: '#0a0e17' }}>
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

// Pro-gated toggle — disabled with lock badge + pricing link for free users
function ProToggle({
  checked,
  onChange,
  label,
  isPro,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  label: string;
  isPro: boolean;
}) {
  return (
    <div className="flex items-center gap-2">
      <Toggle
        checked={isPro ? checked : false}
        onChange={isPro ? onChange : () => {}}
        label={label}
        disabled={!isPro}
      />
      {!isPro && (
        <Link
          href="/pricing"
          className="flex items-center gap-1 text-[10px] text-primary hover:underline"
        >
          <Lock className="h-3 w-3" />
          Pro
        </Link>
      )}
    </div>
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
  const { isPro, user } = useAuth();
  const mapRef = useRef<UniverseMapRef>(null);
  const searchParams = useSearchParams();
  const router = useRouter();
  const [linkCopied, setLinkCopied] = useState(false);
  const initializedFromUrl = useRef(false);
  const [layers, setLayers] = useState<MapLayers>(() => {
    const defaults: MapLayers = {
      showGates: true,
      showLabels: true,
      showRoute: true,
      showKills: false,
      showHeatmap: false,
      showRegionLabels: true,
      showThera: false,
      showFW: false,
      showLandmarks: true,
      showSovStructures: false,
      showSkyhooks: false,
      showSovereignty: false,
      showActivity: false,
      showWormholes: false,
      showMarketHubs: false,
    };
    if (typeof window === 'undefined') return defaults;
    try {
      const saved = localStorage.getItem('gk_map_layers');
      if (saved) return { ...defaults, ...JSON.parse(saved) };
    } catch { /* ignore corrupt data */ }
    return defaults;
  });
  const [colorMode, setColorMode] = useState<'security' | 'risk' | 'star'>(() => {
    if (typeof window === 'undefined') return 'security';
    return (localStorage.getItem('gk_map_color_mode') as 'security' | 'risk' | 'star') || 'security';
  });
  const [selectedSystem, setSelectedSystem] = useState<number | null>(null);
  const [selectedRegion, setSelectedRegion] = useState<number | null>(null);
  const [showRoutePanel, setShowRoutePanel] = useState(false);
  const [showMobileSidebar, setShowMobileSidebar] = useState(false);

  // === Data Fetching ===

  const {
    data: mapConfig,
    isLoading: loadingConfig,
    error: configError,
    refetch: refetchMapConfig,
  } = useQuery({
    queryKey: ['mapConfig'],
    queryFn: () => GatekeeperAPI.getMapConfig(),
    staleTime: 5 * 60 * 1000,
  });

  // Sov data for system detail panel (not an overlay — available to all users)
  const { data: sovData, error: sovError } = useQuery({
    queryKey: ['sovereignty'],
    queryFn: () => GatekeeperAPI.getSovereignty(),
    staleTime: 10 * 60 * 1000,
    enabled: !!mapConfig,
  });

  const { data: theraData, error: theraError } = useQuery({
    queryKey: ['thera'],
    queryFn: () => GatekeeperAPI.getTheraConnections(),
    staleTime: 5 * 60 * 1000,
    enabled: !!mapConfig && isPro && layers.showThera,
  });

  const { data: fwData, error: fwError } = useQuery({
    queryKey: ['fw'],
    queryFn: () => GatekeeperAPI.getFWStatus(),
    staleTime: 10 * 60 * 1000,
    enabled: !!mapConfig && isPro && layers.showFW,
  });

  const { data: sovStructData, error: sovStructError } = useQuery({
    queryKey: ['sovStructures'],
    queryFn: () => GatekeeperAPI.getSovStructures(),
    staleTime: 30 * 60 * 1000,
    enabled: !!mapConfig && isPro && (layers.showSovStructures || layers.showSkyhooks),
  });

  const { data: activityData, error: activityError } = useQuery({
    queryKey: ['systemActivity'],
    queryFn: () => GatekeeperAPI.getSystemActivity(),
    staleTime: 5 * 60 * 1000,
    enabled: !!mapConfig,
  });

  const { data: wormholeData } = useQuery({
    queryKey: ['wormholes'],
    queryFn: () => GatekeeperAPI.getWormholes(),
    staleTime: 2 * 60 * 1000,
    enabled: !!mapConfig && isPro && layers.showWormholes === true,
  });

  const { data: marketHubData } = useQuery({
    queryKey: ['marketHubs'],
    queryFn: () => GatekeeperAPI.getMarketHubs(),
    staleTime: 30 * 60 * 1000, // 30 min — static data
    enabled: !!mapConfig && layers.showMarketHubs === true,
  });

  const { data: characterLocation } = useQuery({
    queryKey: ['characterLocation'],
    queryFn: () => GatekeeperAPI.getCharacterLocation(),
    refetchInterval: 10_000, // Poll every 10s
    enabled: !!user && !!mapConfig,
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

  // Region filter: sorted region options for dropdown
  const regionOptions = useMemo(() => {
    const entries: { id: number; name: string }[] = [];
    regionNames.forEach((name, id) => entries.push({ id, name }));
    entries.sort((a, b) => a.name.localeCompare(b.name));
    return entries;
  }, [regionNames]);

  // Region-filtered systems and gates (region + border systems)
  const regionFilteredSystems = useMemo(() => {
    if (!selectedRegion) return systems;
    // Systems in the selected region
    const regionSystemIds = new Set(
      systems.filter((s) => s.regionId === selectedRegion).map((s) => s.systemId)
    );
    // Border systems: systems in other regions that share a gate with a region system
    const borderIds = new Set<number>();
    for (const g of gates) {
      if (regionSystemIds.has(g.fromSystemId) && !regionSystemIds.has(g.toSystemId)) {
        borderIds.add(g.toSystemId);
      }
      if (regionSystemIds.has(g.toSystemId) && !regionSystemIds.has(g.fromSystemId)) {
        borderIds.add(g.fromSystemId);
      }
    }
    const visibleIds = new Set([...regionSystemIds, ...borderIds]);
    return systems.filter((s) => visibleIds.has(s.systemId));
  }, [systems, gates, selectedRegion]);

  const regionFilteredGates = useMemo(() => {
    if (!selectedRegion) return gates;
    const visibleIds = new Set(regionFilteredSystems.map((s) => s.systemId));
    return gates.filter((g) => visibleIds.has(g.fromSystemId) && visibleIds.has(g.toSystemId));
  }, [gates, regionFilteredSystems, selectedRegion]);

  // Auto-fit viewport when region changes
  const prevRegionRef = useRef<number | null>(null);
  useEffect(() => {
    if (selectedRegion === prevRegionRef.current) return;
    prevRegionRef.current = selectedRegion;
    if (selectedRegion && regionFilteredSystems.length > 0) {
      const ids = regionFilteredSystems.map((s) => s.systemId);
      requestAnimationFrame(() => mapRef.current?.fitToSystems(ids));
    }
  }, [selectedRegion, regionFilteredSystems]);

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

  const handleSearchSelect = useCallback(
    (system: MapSystem) => {
      // Clear region filter so the searched system is visible
      setSelectedRegion(null);
      setSelectedSystem(system.systemId);
      requestAnimationFrame(() => {
        mapRef.current?.panTo(system.systemId);
        mapRef.current?.zoomTo(2);
      });
      if (routeState.mode !== 'idle') selectRouteSystem(system.systemId);
    },
    [routeState.mode, selectRouteSystem]
  );

  const updateLayer = useCallback((key: keyof MapLayers, value: boolean) => {
    setLayers((prev) => {
      const next = { ...prev, [key]: value };
      try { localStorage.setItem('gk_map_layers', JSON.stringify(next)); } catch { /* ignore */ }
      return next;
    });
  }, []);

  const isLoading = loadingConfig;
  const error = configError;
  const [isRetrying, setIsRetrying] = useState(false);
  const [dismissedToasts, setDismissedToasts] = useState<Set<string>>(new Set());

  // Retry handler for map config errors
  const handleRetry = useCallback(async () => {
    setIsRetrying(true);
    try {
      await refetchMapConfig();
    } finally {
      setIsRetrying(false);
    }
  }, [refetchMapConfig]);

  // Overlay data failure toasts — non-blocking warnings
  const overlayErrors = useMemo(() => {
    const errors: { key: string; message: string }[] = [];
    if (sovError) errors.push({ key: 'sov', message: 'Sovereignty data unavailable' });
    if (theraError) errors.push({ key: 'thera', message: 'Thera connections unavailable' });
    if (fwError) errors.push({ key: 'fw', message: 'Faction warfare data unavailable' });
    if (sovStructError) errors.push({ key: 'sovStruct', message: 'Sov structure data unavailable' });
    if (activityError) errors.push({ key: 'activity', message: 'System activity data unavailable' });
    if (!killsConnected && systems.length > 0) errors.push({ key: 'kills', message: 'Kill data connection lost' });
    return errors.filter((e) => !dismissedToasts.has(e.key));
  }, [sovError, theraError, fwError, sovStructError, activityError, killsConnected, systems.length, dismissedToasts]);

  // Auto-dismiss overlay toasts after 5 seconds
  useEffect(() => {
    if (overlayErrors.length === 0) return;
    const timer = setTimeout(() => {
      setDismissedToasts((prev) => {
        const next = new Set(prev);
        for (const e of overlayErrors) next.add(e.key);
        return next;
      });
    }, 5000);
    return () => clearTimeout(timer);
  }, [overlayErrors]);

  // Reset dismissed toasts when errors resolve (so they re-appear if error recurs)
  useEffect(() => {
    const currentErrorKeys = new Set<string>();
    if (sovError) currentErrorKeys.add('sov');
    if (theraError) currentErrorKeys.add('thera');
    if (fwError) currentErrorKeys.add('fw');
    if (sovStructError) currentErrorKeys.add('sovStruct');
    if (activityError) currentErrorKeys.add('activity');
    if (!killsConnected && systems.length > 0) currentErrorKeys.add('kills');

    setDismissedToasts((prev) => {
      const next = new Set<string>();
      for (const key of prev) {
        if (currentErrorKeys.has(key)) next.add(key);
      }
      return next.size !== prev.size ? next : prev;
    });
  }, [sovError, theraError, fwError, sovStructError, activityError, killsConnected, systems.length]);

  // Shared sidebar content used in both desktop aside and mobile overlay
  const sidebarContent = (
    <>
      {/* Region Filter */}
      <CollapsibleSection
        title="Region"
        icon={<Map className="h-4 w-4 text-text-secondary" aria-hidden="true" />}
      >
        <select
          value={selectedRegion ?? ''}
          onChange={(e) => setSelectedRegion(e.target.value ? Number(e.target.value) : null)}
          className="w-full px-2 py-1.5 bg-card border border-border rounded-lg text-sm text-text focus:outline-none focus:ring-2 focus:ring-primary"
        >
          <option value="">All Regions</option>
          {regionOptions.map((r) => (
            <option key={r.id} value={r.id}>{r.name}</option>
          ))}
        </select>
      </CollapsibleSection>

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
          <ProToggle checked={layers.showKills} onChange={(v) => updateLayer('showKills', v)} label="Kill markers" isPro={isPro} />
          <ProToggle checked={layers.showHeatmap} onChange={(v) => updateLayer('showHeatmap', v)} label="Risk heatmap" isPro={isPro} />
          <ProToggle checked={layers.showActivity === true} onChange={(v) => updateLayer('showActivity', v)} label="System activity" isPro={isPro} />
          <ProToggle checked={layers.showThera} onChange={(v) => updateLayer('showThera', v)} label="Thera connections" isPro={isPro} />
          <ProToggle checked={layers.showFW} onChange={(v) => updateLayer('showFW', v)} label="Faction warfare" isPro={isPro} />
          <ProToggle checked={layers.showSovereignty === true} onChange={(v) => updateLayer('showSovereignty', v)} label="Alliance sovereignty" isPro={isPro} />
          <ProToggle checked={layers.showSovStructures} onChange={(v) => updateLayer('showSovStructures', v)} label="iHub ADM" isPro={isPro} />
          <div className="flex items-center gap-2">
            <Toggle checked={false} onChange={() => {}} label="Upwell structures" disabled />
            <span className="text-[10px] text-text-secondary italic">No public ESI endpoint</span>
          </div>
          <ProToggle checked={layers.showWormholes === true} onChange={(v) => updateLayer('showWormholes', v)} label="Wormhole connections" isPro={isPro} />
        </div>

        {/* Security filters */}
        <div className="mt-3 pt-3 border-t border-border space-y-2.5">
          <div className="text-xs font-medium text-text-secondary uppercase tracking-wide">Filter</div>
          <Toggle checked={layers.showHighsec !== false} onChange={(v) => updateLayer('showHighsec', v)} label="Highsec systems" />
          <Toggle checked={layers.showNullsec !== false} onChange={(v) => updateLayer('showNullsec', v)} label="Nullsec systems" />
        </div>

        {/* Intel controls — mobile only (desktop version in toolbar above) */}
        <div className="mt-3 pt-3 border-t border-border space-y-2.5 sm:hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-text-secondary uppercase tracking-wide">Intel Feed</span>
            <div className="flex items-center gap-1.5">
              <div className={`w-2 h-2 rounded-full ${killsConnected ? 'bg-green-500' : 'bg-red-500'}`} />
              <span className="text-xs text-text-secondary">{killsConnected ? 'Live' : 'Offline'}</span>
              <button
                onClick={refreshIntel}
                disabled={intelLoading}
                className="ml-1 p-1 rounded hover:bg-card-hover text-text-secondary hover:text-text transition-colors"
                title="Refresh intel"
              >
                <RefreshCw className={`h-3 w-3 ${intelLoading ? 'animate-spin' : ''}`} />
              </button>
            </div>
          </div>
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value as typeof timeRange)}
            className="w-full px-2 py-1.5 bg-card border border-border rounded-lg text-sm text-text"
          >
            <option value="1h">Last 1 Hour</option>
            <option value="4h">Last 4 Hours</option>
            <option value="12h">Last 12 Hours</option>
            <option value="24h">Last 24 Hours</option>
            <option value="48h">Last 48 Hours</option>
          </select>
          <div className="flex items-center gap-4 text-xs">
            {isPro ? (
              <>
                <span className="text-text-secondary">
                  <span className="inline-block w-2 h-2 rounded-full bg-red-500 mr-1" />{totalKills} kills
                </span>
                <span className="text-text-secondary">
                  <span className="inline-block w-2 h-2 rounded-full bg-orange-500 mr-1" />{totalPods} pods
                </span>
              </>
            ) : (
              <>
                <span className="text-text-secondary">
                  <span className="inline-block w-2 h-2 rounded-full bg-red-500 mr-1" />--- kills
                </span>
                <span className="text-text-secondary">
                  <span className="inline-block w-2 h-2 rounded-full bg-orange-500 mr-1" />--- pods
                </span>
                <Link href="/pricing" className="flex items-center gap-1 text-[10px] text-primary hover:underline ml-auto">
                  <Lock className="h-3 w-3" />
                  Pro
                </Link>
              </>
            )}
          </div>
        </div>
      </CollapsibleSection>

      {/* Color Mode — collapsible */}
      <CollapsibleSection
        title="Color Mode"
        icon={<Palette className="h-4 w-4 text-text-secondary" aria-hidden="true" />}
        defaultOpen={false}
      >
        <div className="flex gap-2 flex-wrap">
          <Button variant={colorMode === 'security' ? 'primary' : 'secondary'} size="sm" onClick={() => { setColorMode('security'); try { localStorage.setItem('gk_map_color_mode', 'security'); } catch {} }} className="flex-1">Security</Button>
          <Button variant={colorMode === 'risk' ? 'primary' : 'secondary'} size="sm" onClick={() => { setColorMode('risk'); try { localStorage.setItem('gk_map_color_mode', 'risk'); } catch {} }} className="flex-1">Risk</Button>
          <Button variant={colorMode === 'star' ? 'primary' : 'secondary'} size="sm" onClick={() => { setColorMode('star'); try { localStorage.setItem('gk_map_color_mode', 'star'); } catch {} }} className="flex-1">Star</Button>
        </div>
      </CollapsibleSection>

      {/* Saved Routes — collapsible */}
      <CollapsibleSection
        title="Saved Routes"
        icon={<Bookmark className="h-4 w-4 text-text-secondary" aria-hidden="true" />}
        defaultOpen={false}
      >
        <SavedRoutes
          currentOrigin={routeState.originId ? getSystemName(routeState.originId) ?? undefined : undefined}
          currentDestination={routeState.destinationId ? getSystemName(routeState.destinationId) ?? undefined : undefined}
          currentProfile={routeState.profile}
          currentUseBridges={routeState.bridges}
          onLoad={(bm) => {
            // Find system IDs by name and set route
            const origin = systems.find((s) => s.name === bm.from_system);
            const dest = systems.find((s) => s.name === bm.to_system);
            if (origin) setRouteOrigin(origin.systemId);
            if (dest) setRouteDestination(dest.systemId);
            setShowRoutePanel(true);
          }}
        />
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
              fwData={isPro ? fwData?.fw_systems : undefined}
              theraConnections={isPro ? theraData?.connections : undefined}
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
            <div className="h-3 w-3 rotate-45 border border-amber-400 bg-amber-500/30" aria-hidden="true" />
            <span className="text-text-secondary">Market Hub Volume</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-2 w-4 border border-cyan-400 rounded-sm" style={{ borderStyle: 'dashed' }} aria-hidden="true" />
            <span className="text-text-secondary">Thera Connection</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-2 w-4 border border-purple-400 rounded-sm" style={{ borderStyle: 'dashed' }} aria-hidden="true" />
            <span className="text-text-secondary">Wormhole</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded-full bg-cyan-400" aria-hidden="true" />
            <span className="text-text-secondary">Your Location</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex gap-0.5" aria-hidden="true">
              <span className="inline-block w-3.5 h-3.5 rounded-full bg-red-900 border border-red-300 text-red-300 text-[8px] font-bold text-center leading-[14px]">1</span>
              <span className="inline-block w-3.5 h-3.5 rounded-full bg-green-900 border border-green-300 text-green-300 text-[8px] font-bold text-center leading-[14px]">5</span>
            </div>
            <span className="text-text-secondary">iHub ADM Level</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded-full border border-sky-300 opacity-40" style={{ boxShadow: '0 0 4px #7dd3fc' }} aria-hidden="true" />
            <span className="text-text-secondary">Upwell structures <span className="text-[9px] italic">(pending data)</span></span>
          </div>
        </div>
      </CollapsibleSection>
    </>
  );

  return (
    <div className="-mx-4 -mb-6 sm:mx-0 sm:mb-0 h-[calc(100vh-theme(spacing.16)-theme(spacing.6))] sm:h-[calc(100vh-theme(spacing.16)-theme(spacing.12))] flex flex-col lg:flex-row gap-4">
      {/* Left Column: toolbar + map (aligned edges) */}
      <div className="flex-1 flex flex-col min-h-0 min-w-0">
        {/* Single toolbar row — title, search, controls, intel */}
        <div className="flex items-center gap-2 mb-2 sm:mb-3 min-h-[36px]">
          {/* Title (desktop only) */}
          <h1 className="hidden sm:flex items-center gap-1.5 text-sm font-bold text-text whitespace-nowrap">
            <Map className="h-4 w-4" />
            New Eden
          </h1>

          {/* Search */}
          <SystemSearch
            systems={systems}
            onSelect={handleSearchSelect}
          />

          {/* Map controls */}
          <Button
            variant={showRoutePanel ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => setShowRoutePanel(!showRoutePanel)}
            aria-label={showRoutePanel ? 'Close route planner' : 'Open route planner'}
            aria-pressed={showRoutePanel}
          >
            <Navigation className="h-4 w-4" aria-hidden="true" />
          </Button>
          <Button variant="ghost" size="sm" onClick={handleZoomIn} aria-label="Zoom in" className="hidden sm:inline-flex">
            <ZoomIn className="h-4 w-4" aria-hidden="true" />
          </Button>
          <Button variant="ghost" size="sm" onClick={handleZoomOut} aria-label="Zoom out" className="hidden sm:inline-flex">
            <ZoomOut className="h-4 w-4" aria-hidden="true" />
          </Button>
          <Button variant="ghost" size="sm" onClick={handleFullscreen} aria-label="Toggle fullscreen mode" className="hidden sm:inline-flex">
            <Maximize2 className="h-4 w-4" aria-hidden="true" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleCopyLink}
            aria-label="Copy map link to clipboard"
            title="Copy link"
            className="hidden sm:inline-flex"
          >
            {linkCopied ? (
              <Check className="h-4 w-4 text-green-400" aria-hidden="true" />
            ) : (
              <Link2 className="h-4 w-4" aria-hidden="true" />
            )}
          </Button>

          {/* Intel strip (right-aligned, desktop) */}
          <div className="hidden sm:flex items-center gap-2 text-xs ml-auto">
            <span className="font-semibold text-text-secondary uppercase tracking-wide">Intel</span>
            <div className={`w-2 h-2 rounded-full ${killsConnected ? 'bg-green-500' : 'bg-red-500'}`} />
            {isPro ? (
              <span className="text-text-secondary whitespace-nowrap">
                {totalKills} kills · {totalPods} pods
              </span>
            ) : (
              <>
                <span className="text-text-secondary">---</span>
                <Link href="/pricing" className="flex items-center gap-1 text-[10px] text-primary hover:underline">
                  <Lock className="h-3 w-3" />
                  Pro
                </Link>
              </>
            )}
            <select
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value as typeof timeRange)}
              className="px-1.5 py-0.5 bg-card border border-border rounded text-xs text-text"
            >
              <option value="1h">1h</option>
              <option value="4h">4h</option>
              <option value="12h">12h</option>
              <option value="24h">24h</option>
              <option value="48h">48h</option>
            </select>
            <button
              onClick={refreshIntel}
              disabled={intelLoading}
              className="p-1 rounded hover:bg-card-hover text-text-secondary hover:text-text transition-colors"
              title="Refresh intel"
            >
              <RefreshCw className={`h-3 w-3 ${intelLoading ? 'animate-spin' : ''}`} />
            </button>
          </div>

          {/* Mobile sidebar toggle */}
          <Button
            variant="ghost"
            size="sm"
            className="lg:hidden ml-auto sm:ml-0"
            onClick={() => setShowMobileSidebar(!showMobileSidebar)}
            aria-label={showMobileSidebar ? 'Close sidebar' : 'Open sidebar'}
          >
            <Menu className="h-4 w-4" aria-hidden="true" />
          </Button>
        </div>

        {/* Map Container — Pochven aesthetic */}
        <div
          id="map-container"
          className="flex-1 min-h-[300px] lg:min-h-0 rounded-lg border border-border relative overflow-hidden"
          style={{ backgroundColor: '#0a0e17' }}
          role="application"
          aria-label="Interactive universe map"
        >
          {error ? (
            <div className="absolute inset-0 flex items-center justify-center p-4 bg-[#0a0e17]">
              <ErrorMessage
                title="Unable to load map data"
                message={getUserFriendlyError(error)}
                onRetry={handleRetry}
                isRetrying={isRetrying}
                className="max-w-md"
              />
            </div>
          ) : isLoading ? (
            <div className="absolute inset-0 flex flex-col bg-[#0a0e17]">
              {/* Skeleton grid to simulate map topology */}
              <div className="absolute inset-0 overflow-hidden opacity-10">
                <div className="absolute inset-0" style={{
                  backgroundImage: 'radial-gradient(circle, rgba(255,255,255,0.15) 1px, transparent 1px)',
                  backgroundSize: '40px 40px',
                }} />
                {/* Simulated gate lines */}
                <svg className="absolute inset-0 w-full h-full">
                  <line x1="15%" y1="20%" x2="35%" y2="30%" stroke="rgba(255,255,255,0.2)" strokeWidth="1" />
                  <line x1="35%" y1="30%" x2="55%" y2="25%" stroke="rgba(255,255,255,0.2)" strokeWidth="1" />
                  <line x1="55%" y1="25%" x2="70%" y2="45%" stroke="rgba(255,255,255,0.2)" strokeWidth="1" />
                  <line x1="25%" y1="55%" x2="45%" y2="60%" stroke="rgba(255,255,255,0.2)" strokeWidth="1" />
                  <line x1="45%" y1="60%" x2="65%" y2="55%" stroke="rgba(255,255,255,0.2)" strokeWidth="1" />
                  <line x1="35%" y1="30%" x2="25%" y2="55%" stroke="rgba(255,255,255,0.2)" strokeWidth="1" />
                  <line x1="55%" y1="25%" x2="45%" y2="60%" stroke="rgba(255,255,255,0.2)" strokeWidth="1" />
                  <line x1="70%" y1="45%" x2="80%" y2="70%" stroke="rgba(255,255,255,0.2)" strokeWidth="1" />
                </svg>
              </div>
              {/* Central spinner */}
              <div className="flex-1 flex items-center justify-center relative z-10">
                <div className="text-center">
                  <Loader2 className="h-10 w-10 animate-spin text-primary mx-auto mb-3" />
                  <p className="text-text-secondary text-sm font-medium">Loading New Eden...</p>
                  <p className="text-text-secondary/50 text-xs mt-1">Preparing 5,400+ systems</p>
                </div>
              </div>
            </div>
          ) : (
            <>
              <UniverseMap
                ref={mapRef}
                systems={regionFilteredSystems}
                gates={regionFilteredGates}
                regionNames={regionNames}
                routes={mapRoutes}
                kills={isPro ? kills : []}
                risks={risks}
                theraConnections={isPro ? theraData?.connections : undefined}
                fwSystems={isPro ? fwData?.fw_systems : undefined}
                landmarks={mapConfig?.landmarks}
                sovStructures={isPro ? sovStructData?.structures : undefined}
                sovereigntyData={isPro ? sovData?.sovereignty : undefined}
                allianceData={isPro ? sovData?.alliances : undefined}
                activityData={isPro ? activityData : undefined}
                wormholeConnections={isPro ? wormholeData?.connections : undefined}
                marketHubs={marketHubData?.hubs}
                characterSystemId={characterLocation?.solar_system_id}
                characterName={user?.character_name}
                layers={isPro ? layers : {
                  ...layers,
                  showKills: false,
                  showHeatmap: false,
                  showThera: false,
                  showFW: false,
                  showSovereignty: false,
                  showActivity: false,
                  showSovStructures: false,
                  showSkyhooks: false,
                  showWormholes: false,
                }}
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

              {/* Overlay data failure toasts */}
              {overlayErrors.length > 0 && (
                <div className="absolute bottom-3 left-1/2 -translate-x-1/2 z-20 flex flex-col gap-1.5 items-center pointer-events-none">
                  {overlayErrors.map((toast) => (
                    <div
                      key={toast.key}
                      className="pointer-events-auto flex items-center gap-2 px-3 py-1.5 bg-card/90 backdrop-blur border border-border rounded-lg shadow-lg text-xs text-text-secondary animate-in fade-in slide-in-from-bottom-2 duration-300"
                    >
                      <AlertCircle className="h-3.5 w-3.5 text-risk-orange flex-shrink-0" aria-hidden="true" />
                      <span>{toast.message}</span>
                      <button
                        onClick={() => setDismissedToasts((prev) => new Set(prev).add(toast.key))}
                        className="ml-1 p-0.5 rounded hover:bg-card-hover text-text-secondary hover:text-text transition-colors"
                        aria-label={`Dismiss ${toast.message}`}
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </div>
                  ))}
                </div>
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
            <div className="fixed right-0 top-0 h-full w-[85vw] sm:w-72 max-w-[320px] bg-card border-l border-border z-50 overflow-y-auto p-4 pb-[env(safe-area-inset-bottom)] lg:hidden">
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
      </div>{/* end left column */}

      {/* Side Panel — collapsible sections */}
      <aside className="hidden lg:flex w-72 flex-col gap-3 overflow-y-auto" aria-label="Map controls">
        {sidebarContent}
      </aside>
    </div>
  );
}
