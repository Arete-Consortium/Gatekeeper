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
import { SovereigntyOverlay } from './SovereigntyOverlay';
import { TheraOverlay } from './TheraOverlay';
import { FWOverlay } from './FWOverlay';
import { LandmarksOverlay } from './LandmarksOverlay';
import { SovStructuresOverlay } from './SovStructuresOverlay';

// Default layer visibility
const DEFAULT_LAYERS: MapLayers = {
  showGates: true,
  showLabels: true,
  showRoute: true,
  showKills: false,
  showHeatmap: false,
  showRegionLabels: true,
  showSovereignty: false,
  showThera: true,
  showFW: false,
  showLandmarks: true,
  showSovStructures: false,
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
      sovereignty,
      alliances,
      factions,
      theraConnections = [],
      fwSystems,
      landmarks = [],
      sovStructures,
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

    // Build efficient data structures (systemMap used for panTo/fitToSystems)
    const { systemMap } = useMapDataFromProps(systems, gates);

    // Calculate region centers for labels
    const regions = useMemo(
      () => calculateRegionCenters(systems, regionNames),
      [systems, regionNames]
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
      if (initializedRef.current || systems.length === 0 || viewport.width === 0) return;
      initializedRef.current = true;
      const fit = calculateFitZoom(systems, viewport.width, viewport.height);
      const frameId = requestAnimationFrame(() => {
        setViewport((prev) => ({
          ...prev,
          x: fit.x,
          y: fit.y,
          zoom: fit.zoom,
        }));
      });
      return () => cancelAnimationFrame(frameId);
    }, [systems, viewport.width, viewport.height]);

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

    return (
      <div
        ref={containerRef}
        className={`relative w-full h-full overflow-hidden bg-black ${className || ''}`}
      >
        <SimpleMapCanvas
          systems={systems}
          gates={gates}
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
        />

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

        {/* Sovereignty Overlay */}
        {layers.showSovereignty && sovereignty && (
          <SovereigntyOverlay
            sovereignty={sovereignty}
            alliances={alliances || {}}
            systems={systemMap}
            viewport={viewport}
            factions={factions || {}}
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

        {/* Landmarks */}
        {layers.showLandmarks && landmarks.length > 0 && (
          <LandmarksOverlay
            landmarks={landmarks}
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
          systems={systems}
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
