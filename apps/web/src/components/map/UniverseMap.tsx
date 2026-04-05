'use client';

/**
 * UniverseMap - Main map component for EVE Gatekeeper
 * Manages viewport state, data fetching, and exposes imperative controls
 */

import React, {
  forwardRef,
  memo,
  useCallback,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
} from 'react';
import type {
  MapSystem,
  MapViewport,
  MapLayers,
  MapRegion,
  UniverseMapProps,
  UniverseMapRef,
} from './types';
import { useMapDataFromProps, calculateRegionCenters } from './useMapData';
import { calculateFitZoom, lerp, smoothStep } from './utils/spatial';
import { SimpleMapCanvas } from './SimpleMapCanvas';
import { RouteOverlay } from './RouteOverlay';
import { KillMarkers } from './KillMarkers';
import { RiskHeatmap } from './RiskHeatmap';
import { Minimap } from './Minimap';
import { TheraOverlay } from './TheraOverlay';
import { FWOverlay } from './FWOverlay';
// LandmarksOverlay removed — low ROI toggle
import { SovereigntyOverlay } from './SovereigntyOverlay';
import { ActivityOverlay } from './ActivityOverlay';
import { SovStructuresOverlay } from './SovStructuresOverlay';
import { SkyhookHaloOverlay } from './SkyhookHaloOverlay';
import { WormholeOverlay } from './WormholeOverlay';
import { JumpBridgeOverlay } from './JumpBridgeOverlay';
import { IncursionOverlay } from './IncursionOverlay';
// MarketHubsOverlay removed — low ROI toggle
import { CharacterMarker } from './CharacterMarker';
import { FleetOverlay } from './FleetOverlay';

// Default layer visibility
const DEFAULT_LAYERS: MapLayers = {
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
  showIncursions: false,
  showWormholes: false,
  showJumpBridges: false,
  showMarketHubs: false,
  showHighsec: true,
  showNullsec: true,
};

// Animation duration in ms
const ANIMATION_DURATION = 500;

/**
 * Main Universe Map component
 * Renders the EVE universe with systems, gates, and overlays
 */
export const UniverseMap = forwardRef<UniverseMapRef, UniverseMapProps>(
  function UniverseMap(
    {
      systems,
      gates,
      regionNames,
      routes = [],
      kills = [],
      risks = [],
      theraConnections = [],
      fwSystems,
      landmarks = [],
      sovStructures,
      sovereigntyData,
      allianceData,
      activityData,
      wormholeConnections = [],
      jumpBridgeConnections = [],
      marketHubs = [],
      characterSystemId,
      characterName,
      fleetMembers,
      currentCharacterId,
      selectedSystem,
      highlightedSystems = [],
      onSystemClick,
      onSystemHover,
      onRouteRequest: _onRouteRequest,
      onSetRouteOrigin,
      onSetRouteDestination,
      onAvoidSystem,
      onDeselect,
      layers: layersProp,
      colorMode = 'security',
      layoutMode = 'subway',
      className,
    },
    ref
  ) {
    const containerRef = useRef<HTMLDivElement>(null);
    const animationRef = useRef<number | null>(null);

    // Merge layers with defaults
    const layers = useMemo(
      () => ({ ...DEFAULT_LAYERS, ...layersProp }),
      [layersProp]
    );

    // Exclude Pochven (region 10000070) — has its own dedicated /pochven page
    const POCHVEN_REGION_ID = 10000070;

    // Apply layout transform based on mode
    // 'subway': Compress inter-region distances by 50% for compact subway-style view
    // 'dotlan': Use raw EVE coordinates for CCP/Dotlan-style 2D layout
    const compressedSystems = useMemo(() => {
      const baseSystems = systems.filter((s) => s.regionId !== POCHVEN_REGION_ID);
      if (baseSystems.length === 0) return baseSystems;

      // In dotlan mode, use raw coordinates — no compression
      if (layoutMode === 'dotlan') return baseSystems;

      // Calculate region centroids
      const regionSums = new Map<number, { sx: number; sy: number; count: number }>();
      for (const s of baseSystems) {
        const acc = regionSums.get(s.regionId) || { sx: 0, sy: 0, count: 0 };
        acc.sx += s.x;
        acc.sy += s.y;
        acc.count += 1;
        regionSums.set(s.regionId, acc);
      }
      const regionCentroids = new Map<number, { cx: number; cy: number }>();
      for (const [rid, { sx, sy, count }] of regionSums) {
        regionCentroids.set(rid, { cx: sx / count, cy: sy / count });
      }

      // Global centroid (average of all region centroids)
      let gcx = 0, gcy = 0;
      for (const { cx, cy } of regionCentroids.values()) { gcx += cx; gcy += cy; }
      gcx /= regionCentroids.size;
      gcy /= regionCentroids.size;

      // Compress: newPos = pos + (globalCenter - regionCenter) * (1 - factor)
      // factor=0.5 means 50% compression of inter-region gaps
      const factor = 0.5;
      return baseSystems.map((s) => {
        const rc = regionCentroids.get(s.regionId);
        if (!rc) return s;
        const dx = (gcx - rc.cx) * (1 - factor);
        const dy = (gcy - rc.cy) * (1 - factor);
        return { ...s, x: s.x + dx, y: s.y + dy };
      });
    }, [systems, layoutMode]);

    // Filter systems by security class (highsec/nullsec toggles)
    const filteredSystems = useMemo(() => {
      const hideHighsec = layers.showHighsec === false;
      const hideNullsec = layers.showNullsec === false;
      if (!hideHighsec && !hideNullsec) return compressedSystems;
      return compressedSystems.filter((s) => {
        if (hideHighsec && s.security >= 0.5) return false;
        if (hideNullsec && s.security <= 0.0) return false;
        return true;
      });
    }, [compressedSystems, layers.showHighsec, layers.showNullsec]);

    // Filter gates to only include those between visible systems
    const filteredGates = useMemo(() => {
      const hideHighsec = layers.showHighsec === false;
      const hideNullsec = layers.showNullsec === false;
      if (!hideHighsec && !hideNullsec) return gates;
      const visibleIds = new Set(filteredSystems.map((s) => s.systemId));
      return gates.filter((g) => visibleIds.has(g.fromSystemId) && visibleIds.has(g.toSystemId));
    }, [gates, filteredSystems, layers.showHighsec, layers.showNullsec]);

    // Build efficient data structures (systemMap used for panTo/fitToSystems)
    const { systemMap } = useMapDataFromProps(filteredSystems, filteredGates);

    // Calculate region centers for labels
    const regions = useMemo(
      () => calculateRegionCenters(filteredSystems, regionNames),
      [filteredSystems, regionNames]
    );

    // Viewport state
    const [viewport, setViewport] = useState<MapViewport>({
      x: 0,
      y: 0,
      zoom: 0.1,
      width: 800,
      height: 600,
    });

    // Hovered system state
    const [hoveredSystem, setHoveredSystem] = useState<number | null>(null);

    // Update container size on mount and resize
    useEffect(() => {
      const container = containerRef.current;
      if (!container) return;

      const updateSize = () => {
        const rect = container.getBoundingClientRect();
        setViewport((prev) => ({
          ...prev,
          width: rect.width,
          height: rect.height,
        }));
      };

      updateSize();

      const resizeObserver = new ResizeObserver(updateSize);
      resizeObserver.observe(container);

      return () => resizeObserver.disconnect();
    }, []);

    // Center on systems when they first load (deferred to avoid synchronous setState in effect)
    const initializedRef = useRef(false);
    useEffect(() => {
      if (initializedRef.current || filteredSystems.length === 0 || viewport.width === 0) return;
      initializedRef.current = true;
      const fit = calculateFitZoom(filteredSystems, viewport.width, viewport.height);
      const frameId = requestAnimationFrame(() => {
        setViewport((prev) => ({
          ...prev,
          x: fit.x,
          y: fit.y,
          zoom: fit.zoom,
        }));
      });
      return () => cancelAnimationFrame(frameId);
    }, [filteredSystems, viewport.width, viewport.height]);

    // Re-fit viewport when layout mode changes (placeholder — effect added after animateViewport)
    const prevLayoutRef = useRef(layoutMode);

    // Animate viewport to target
    const animateViewport = useCallback(
      (target: Partial<MapViewport>, duration = ANIMATION_DURATION) => {
        // Cancel any existing animation
        if (animationRef.current) {
          cancelAnimationFrame(animationRef.current);
        }

        const start = { ...viewport };
        const startTime = performance.now();

        const animate = (currentTime: number) => {
          const elapsed = currentTime - startTime;
          const progress = Math.min(elapsed / duration, 1);
          const eased = smoothStep(progress);

          setViewport((prev) => ({
            ...prev,
            x: target.x !== undefined ? lerp(start.x, target.x, eased) : prev.x,
            y: target.y !== undefined ? lerp(start.y, target.y, eased) : prev.y,
            zoom:
              target.zoom !== undefined
                ? lerp(start.zoom, target.zoom, eased)
                : prev.zoom,
          }));

          if (progress < 1) {
            animationRef.current = requestAnimationFrame(animate);
          } else {
            animationRef.current = null;
          }
        };

        animationRef.current = requestAnimationFrame(animate);
      },
      [viewport]
    );

    // Re-fit viewport when layout mode changes
    useEffect(() => {
      if (prevLayoutRef.current === layoutMode) return;
      prevLayoutRef.current = layoutMode;
      if (filteredSystems.length === 0 || viewport.width === 0) return;
      const fit = calculateFitZoom(filteredSystems, viewport.width, viewport.height);
      animateViewport(fit, 600);
    }, [layoutMode, filteredSystems, viewport.width, viewport.height, animateViewport]);

    // Imperative handle for external control
    useImperativeHandle(
      ref,
      () => ({
        panTo: (systemId: number) => {
          const system = systemMap.get(systemId);
          if (system) {
            animateViewport({ x: system.x, y: system.y });
          }
        },

        zoomTo: (level: number) => {
          animateViewport({ zoom: level });
        },

        fitToSystems: (systemIds: number[]) => {
          const targetSystems = systemIds
            .map((id) => systemMap.get(id))
            .filter((s): s is MapSystem => s !== undefined);

          if (targetSystems.length > 0) {
            const fit = calculateFitZoom(
              targetSystems,
              viewport.width,
              viewport.height
            );
            animateViewport(fit);
          }
        },

        getViewport: () => viewport,

        setViewport: (partial: Partial<MapViewport>) => {
          setViewport((prev) => ({ ...prev, ...partial }));
        },
      }),
      [systemMap, viewport, animateViewport]
    );

    // Handle viewport changes from canvas
    const handleViewportChange = useCallback((newViewport: MapViewport) => {
      // Cancel any running animation when user manually pans/zooms
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
        animationRef.current = null;
      }
      setViewport(newViewport);
    }, []);

    // Handle minimap navigation — animate to clicked location (#8)
    const handleMinimapViewportChange = useCallback(
      (partial: Partial<MapViewport>) => {
        animateViewport(partial, 300);
      },
      [animateViewport]
    );

    // Handle system hover
    const handleSystemHover = useCallback(
      (systemId: number | null) => {
        setHoveredSystem(systemId);
        onSystemHover?.(systemId);
      },
      [onSystemHover]
    );

    // Handle system click
    const handleSystemClick = useCallback(
      (systemId: number) => {
        onSystemClick?.(systemId);
      },
      [onSystemClick]
    );

    // Cleanup animation on unmount
    useEffect(() => {
      return () => {
        if (animationRef.current) {
          cancelAnimationFrame(animationRef.current);
        }
      };
    }, []);

    // Set of system IDs where the SVG overlay renders (iHub or Skyhook only)
    // TCU-only systems still need canvas labels
    const sovStructureSystemIds = useMemo(() => {
      if (!sovStructures) return undefined;
      const ids = new Set<number>();
      for (const [sid, structs] of Object.entries(sovStructures)) {
        const hasRenderable = structs.some(
          (s) => s.structure_type_id === 32458 || s.structure_type_id === 81826
        );
        if (hasRenderable) ids.add(Number(sid));
      }
      return ids.size > 0 ? ids : undefined;
    }, [sovStructures]);

    return (
      <div
        ref={containerRef}
        className={`relative w-full h-full overflow-hidden ${className || ''}`}
        style={{ backgroundColor: '#0a0e17' }}
      >
        <SimpleMapCanvas
          systems={filteredSystems}
          gates={filteredGates}
          viewport={viewport}
          onViewportChange={handleViewportChange}
          selectedSystem={selectedSystem}
          highlightedSystems={highlightedSystems}
          onSystemClick={handleSystemClick}
          onSystemHover={handleSystemHover}
          layers={layers}
          colorMode={colorMode}
          risks={risks}
          regions={regions}
          hoveredSystemId={hoveredSystem}
          onSetRouteOrigin={onSetRouteOrigin}
          onSetRouteDestination={onSetRouteDestination}
          onAvoidSystem={onAvoidSystem}
          onDeselect={onDeselect}
          sovStructureSystems={sovStructureSystemIds}
        />

        {/* Sovereignty Overlay (colored rings per alliance) */}
        {layers.showSovereignty && sovereigntyData && allianceData && (
          <SovereigntyOverlay
            sovereignty={sovereigntyData}
            alliances={allianceData}
            systems={systemMap}
            viewport={viewport}
            factions={{}}
          />
        )}

        {/* Activity Overlay (jump traffic + kill activity) */}
        {layers.showActivity && activityData && (
          <ActivityOverlay
            activityData={activityData}
            systems={systemMap}
            viewport={viewport}
          />
        )}

        {/* Incursion Overlay (Sansha staging + infested systems) */}
        {layers.showIncursions && activityData?.incursions && activityData.incursions.length > 0 && (
          <IncursionOverlay
            incursions={activityData.incursions}
            systems={systemMap}
            viewport={viewport}
          />
        )}

        {/* Risk Heatmap (renders behind other overlays) */}
        {layers.showHeatmap && risks.length > 0 && (
          <RiskHeatmap
            risks={risks}
            systems={systemMap}
            viewport={viewport}
            opacity={0.6}
          />
        )}

        {/* Route Overlay */}
        {layers.showRoute && routes.length > 0 && (
          <RouteOverlay
            routes={routes}
            systems={systemMap}
            viewport={viewport}
          />
        )}

        {/* Kill Markers */}
        {layers.showKills && kills.length > 0 && (
          <KillMarkers
            kills={kills}
            systems={systemMap}
            viewport={viewport}
            maxAge={60 * 60 * 1000}
          />
        )}

        {/* Thera/Turnur Connections */}
        {layers.showThera && theraConnections.length > 0 && (
          <TheraOverlay
            connections={theraConnections}
            systems={systemMap}
            viewport={viewport}
          />
        )}

        {/* Faction Warfare Overlay */}
        {layers.showFW && fwSystems && (
          <FWOverlay
            fwSystems={fwSystems}
            systems={systemMap}
            viewport={viewport}
          />
        )}

        {/* Sov Structures (iHub ADM) */}
        {layers.showSovStructures && sovStructures && (
          <SovStructuresOverlay
            structures={sovStructures}
            systems={systemMap}
            viewport={viewport}
          />
        )}

        {/* Skyhook Halos */}
        {layers.showSkyhooks && sovStructures && (
          <SkyhookHaloOverlay
            structures={sovStructures}
            systems={systemMap}
            viewport={viewport}
          />
        )}

        {/* Wormhole Connections */}
        {layers.showWormholes && wormholeConnections && wormholeConnections.length > 0 && (
          <WormholeOverlay
            connections={wormholeConnections}
            systems={systemMap}
            viewport={viewport}
          />
        )}

        {/* Jump Bridge Connections */}
        {layers.showJumpBridges && jumpBridgeConnections && jumpBridgeConnections.length > 0 && (
          <JumpBridgeOverlay
            connections={jumpBridgeConnections}
            systems={systemMap}
            viewport={viewport}
          />
        )}

        {/* Landmarks and Market Hubs removed — low ROI */}

        {/* Fleet member markers */}
        {fleetMembers && fleetMembers.length > 0 && (
          <FleetOverlay
            members={fleetMembers}
            systems={systemMap}
            viewport={viewport}
            currentCharacterId={currentCharacterId}
          />
        )}

        {/* Character location marker */}
        {characterSystemId && characterName && (
          <CharacterMarker
            systemId={characterSystemId}
            characterName={characterName}
            systems={systemMap}
            viewport={viewport}
          />
        )}

        {/* Hovered system tooltip */}
        {hoveredSystem && (
          <SystemTooltip
            system={systemMap.get(hoveredSystem)}
            viewport={viewport}
          />
        )}

        {/* Minimap overview */}
        <Minimap
          systems={filteredSystems}
          viewport={viewport}
          onViewportChange={handleMinimapViewportChange}
          size={150}
        />

        {/* Zoom level indicator */}
        <div className="absolute bottom-4 right-4 bg-black/70 text-gray-400 text-xs px-2 py-1 rounded">
          Zoom: {(viewport.zoom * 100).toFixed(0)}%
        </div>
      </div>
    );
  }
);

/**
 * Tooltip displayed when hovering over a system
 * Memoized to prevent re-renders when other map state changes
 */
interface SystemTooltipProps {
  system: MapSystem | undefined;
  viewport: MapViewport;
}

const SystemTooltip = memo(function SystemTooltip({ system, viewport }: SystemTooltipProps) {
  if (!system) return null;

  const x = (system.x - viewport.x) * viewport.zoom + viewport.width / 2;
  const y = (system.y - viewport.y) * viewport.zoom + viewport.height / 2;

  const secStatus = system.security.toFixed(2);
  const secColor =
    system.security >= 0.5
      ? 'text-green-400'
      : system.security > 0
        ? 'text-yellow-400'
        : 'text-red-400';

  // Flip tooltip to left side if near right edge
  const flipLeft = x > viewport.width - 200;
  const tooltipX = flipLeft ? x - 15 : x + 15;
  const transform = flipLeft
    ? 'translateY(-50%) translateX(-100%)'
    : 'translateY(-50%)';

  return (
    <div
      className="absolute pointer-events-none z-50 transition-opacity duration-150"
      style={{
        left: tooltipX,
        top: y,
        transform,
      }}
    >
      {/* Arrow */}
      <div
        className="absolute top-1/2 -translate-y-1/2 w-0 h-0"
        style={flipLeft ? {
          right: -4,
          borderTop: '5px solid transparent',
          borderBottom: '5px solid transparent',
          borderLeft: '5px solid rgba(55, 65, 81, 0.95)',
        } : {
          left: -4,
          borderTop: '5px solid transparent',
          borderBottom: '5px solid transparent',
          borderRight: '5px solid rgba(55, 65, 81, 0.95)',
        }}
      />
      <div className="bg-gray-800/95 border border-gray-600 rounded-lg px-3 py-2 text-sm shadow-xl backdrop-blur-sm">
        <div className="font-semibold text-white text-xs">{system.name}</div>
        <div className="flex items-center gap-3 mt-1">
          <span className={`font-mono text-xs ${secColor}`}>{secStatus}</span>
          {system.spectralClass && (
            <span className="text-gray-500 text-[10px]">Class {system.spectralClass}</span>
          )}
          {system.npcStations != null && system.npcStations > 0 && (
            <span className="text-gray-500 text-[10px]">{system.npcStations} stn</span>
          )}
        </div>
      </div>
    </div>
  );
});

export default UniverseMap;
