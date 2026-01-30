'use client';

/**
 * UniverseMap - Main map component for EVE Gatekeeper
 * Manages viewport state, data fetching, and exposes imperative controls
 */

import React, {
  forwardRef,
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
  UniverseMapProps,
  UniverseMapRef,
} from './types';
import { useMapDataFromProps } from './useMapData';
import { calculateFitZoom, lerp, smoothStep } from './utils/spatial';
import { SimpleMapCanvas } from './SimpleMapCanvas';
import { RouteOverlay } from './RouteOverlay';
import { KillMarkers } from './KillMarkers';
import { RiskHeatmap } from './RiskHeatmap';

// Default layer visibility
const DEFAULT_LAYERS: MapLayers = {
  showGates: true,
  showLabels: true,
  showRoute: true,
  showKills: false,
  showHeatmap: false,
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
      routes = [],
      kills = [],
      risks = [],
      selectedSystem,
      highlightedSystems: _highlightedSystems,
      onSystemClick,
      onSystemHover,
      onRouteRequest: _onRouteRequest,
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

    // Center on systems when they first load
    useEffect(() => {
      if (systems.length > 0 && viewport.x === 0 && viewport.y === 0) {
        const fit = calculateFitZoom(systems, viewport.width, viewport.height);
        setViewport((prev) => ({
          ...prev,
          x: fit.x,
          y: fit.y,
          zoom: fit.zoom,
        }));
      }
    }, [systems, viewport.width, viewport.height, viewport.x, viewport.y]);

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
          onSystemClick={handleSystemClick}
          onSystemHover={handleSystemHover}
          layers={layers}
          colorMode={colorMode}
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

        {/* Hovered system tooltip */}
        {hoveredSystem && (
          <SystemTooltip
            system={systemMap.get(hoveredSystem)}
            viewport={viewport}
          />
        )}

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
 */
interface SystemTooltipProps {
  system: MapSystem | undefined;
  viewport: MapViewport;
}

function SystemTooltip({ system, viewport }: SystemTooltipProps) {
  if (!system) return null;

  // Calculate screen position
  const x = (system.x - viewport.x) * viewport.zoom + viewport.width / 2;
  const y = (system.y - viewport.y) * viewport.zoom + viewport.height / 2;

  // Security status formatting
  const secStatus = system.security.toFixed(1);
  const secColor =
    system.security >= 0.5
      ? 'text-green-400'
      : system.security > 0
        ? 'text-yellow-400'
        : 'text-red-400';

  return (
    <div
      className="absolute pointer-events-none bg-gray-900/95 border border-gray-700 rounded-lg px-3 py-2 text-sm shadow-lg z-50"
      style={{
        left: x + 15,
        top: y - 10,
        transform: 'translateY(-50%)',
      }}
    >
      <div className="font-semibold text-white">{system.name}</div>
      <div className="text-gray-400 text-xs mt-1">
        Security: <span className={secColor}>{secStatus}</span>
      </div>
    </div>
  );
}

export default UniverseMap;
