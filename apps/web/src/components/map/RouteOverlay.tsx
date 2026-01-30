'use client';

import { useMemo, memo } from 'react';
import type { MapRoute, MapSystem, MapViewport } from './types';

export interface RouteOverlayProps {
  routes: MapRoute[];
  systems: Map<number, MapSystem>;
  viewport: MapViewport;
  onRouteClick?: (routeIndex: number) => void;
}

/**
 * Route profile colors
 */
const ROUTE_COLORS = {
  safer: '#32d74b',      // Green
  shortest: '#ffd60a',   // Yellow
  paranoid: '#30b0ff',   // Blue
  default: '#ffffff',    // White fallback
} as const;

/**
 * Converts map coordinates to screen coordinates
 */
function mapToScreen(
  mapX: number,
  mapY: number,
  viewport: MapViewport
): { x: number; y: number } {
  const screenX = (mapX - viewport.x) * viewport.zoom + viewport.width / 2;
  const screenY = (mapY - viewport.y) * viewport.zoom + viewport.height / 2;
  return { x: screenX, y: screenY };
}

/**
 * Generate path data for a route
 */
function generateRoutePath(
  systemIds: number[],
  systems: Map<number, MapSystem>,
  viewport: MapViewport
): string {
  const points: { x: number; y: number }[] = [];

  for (const systemId of systemIds) {
    const system = systems.get(systemId);
    if (system) {
      const screenPos = mapToScreen(system.x, system.y, viewport);
      points.push(screenPos);
    }
  }

  if (points.length < 2) return '';

  // Build SVG path
  const pathParts = points.map((pt, i) =>
    i === 0 ? `M ${pt.x} ${pt.y}` : `L ${pt.x} ${pt.y}`
  );

  return pathParts.join(' ');
}

/**
 * Single route path component with animation
 */
const RoutePath = memo(function RoutePath({
  route,
  index,
  systems,
  viewport,
  onClick,
}: {
  route: MapRoute;
  index: number;
  systems: Map<number, MapSystem>;
  viewport: MapViewport;
  onClick?: () => void;
}) {
  const pathData = useMemo(
    () => generateRoutePath(route.systemIds, systems, viewport),
    [route.systemIds, systems, viewport]
  );

  // Determine color based on route label/profile
  const color = route.color || (
    route.label === 'safer' ? ROUTE_COLORS.safer :
    route.label === 'shortest' ? ROUTE_COLORS.shortest :
    route.label === 'paranoid' ? ROUTE_COLORS.paranoid :
    ROUTE_COLORS.default
  );

  // Get highlight points for route systems
  const highlightPoints = useMemo(() => {
    return route.systemIds.map(systemId => {
      const system = systems.get(systemId);
      if (!system) return null;
      const pos = mapToScreen(system.x, system.y, viewport);
      return { systemId, ...pos };
    }).filter(Boolean);
  }, [route.systemIds, systems, viewport]);

  if (!pathData) return null;

  const animationId = `route-animation-${index}`;
  const glowId = `route-glow-${index}`;
  const dashArray = route.animated !== false ? '12 6' : 'none';

  return (
    <g className="route-path-group" onClick={onClick} style={{ cursor: onClick ? 'pointer' : 'default' }}>
      {/* Glow filter definition */}
      <defs>
        <filter id={glowId} x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="3" result="coloredBlur" />
          <feMerge>
            <feMergeNode in="coloredBlur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* Background glow path */}
      <path
        d={pathData}
        fill="none"
        stroke={color}
        strokeWidth={6}
        strokeOpacity={0.3}
        strokeLinecap="round"
        strokeLinejoin="round"
        filter={`url(#${glowId})`}
      />

      {/* Main route path */}
      <path
        d={pathData}
        fill="none"
        stroke={color}
        strokeWidth={3}
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeDasharray={dashArray}
        className={route.animated !== false ? 'route-animated' : ''}
      >
        {route.animated !== false && (
          <animate
            attributeName="stroke-dashoffset"
            from="18"
            to="0"
            dur="0.5s"
            repeatCount="indefinite"
          />
        )}
      </path>

      {/* System highlight circles */}
      {highlightPoints.map((point, i) => point && (
        <circle
          key={point.systemId}
          cx={point.x}
          cy={point.y}
          r={i === 0 || i === highlightPoints.length - 1 ? 8 : 5}
          fill={color}
          fillOpacity={0.3}
          stroke={color}
          strokeWidth={2}
          filter={`url(#${glowId})`}
        />
      ))}

      {/* Start marker */}
      {highlightPoints.length > 0 && highlightPoints[0] && (
        <g transform={`translate(${highlightPoints[0].x}, ${highlightPoints[0].y})`}>
          <circle r={12} fill={color} fillOpacity={0.2} />
          <circle r={6} fill={color} />
          <text
            y={-18}
            textAnchor="middle"
            fill={color}
            fontSize={11}
            fontWeight="bold"
            className="route-label"
          >
            START
          </text>
        </g>
      )}

      {/* End marker */}
      {highlightPoints.length > 1 && highlightPoints[highlightPoints.length - 1] && (
        <g transform={`translate(${highlightPoints[highlightPoints.length - 1]!.x}, ${highlightPoints[highlightPoints.length - 1]!.y})`}>
          <circle r={12} fill={color} fillOpacity={0.2} />
          <polygon
            points="-5,-5 5,0 -5,5"
            fill={color}
          />
          <text
            y={-18}
            textAnchor="middle"
            fill={color}
            fontSize={11}
            fontWeight="bold"
            className="route-label"
          >
            END
          </text>
        </g>
      )}

      {/* Route label if provided */}
      {route.label && highlightPoints.length > 1 && (
        <text
          x={(highlightPoints[0]!.x + highlightPoints[Math.floor(highlightPoints.length / 2)]!.x) / 2}
          y={(highlightPoints[0]!.y + highlightPoints[Math.floor(highlightPoints.length / 2)]!.y) / 2 - 15}
          textAnchor="middle"
          fill={color}
          fontSize={12}
          fontWeight="bold"
          className="route-label"
        >
          {route.label.toUpperCase()}
        </text>
      )}
    </g>
  );
});

/**
 * RouteOverlay Component
 * Renders route paths as an SVG overlay on the map
 */
export function RouteOverlay({
  routes,
  systems,
  viewport,
  onRouteClick,
}: RouteOverlayProps) {
  if (routes.length === 0) return null;

  return (
    <svg
      className="route-overlay"
      width={viewport.width}
      height={viewport.height}
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        pointerEvents: 'none',
        overflow: 'visible',
      }}
    >
      <style>
        {`
          .route-animated {
            animation: marchingAnts 0.5s linear infinite;
          }

          @keyframes marchingAnts {
            from {
              stroke-dashoffset: 18;
            }
            to {
              stroke-dashoffset: 0;
            }
          }

          .route-path-group {
            pointer-events: stroke;
          }

          .route-path-group:hover path {
            stroke-width: 4;
          }

          .route-label {
            pointer-events: none;
            text-shadow: 0 0 4px rgba(0,0,0,0.8);
          }
        `}
      </style>

      {routes.map((route, index) => (
        <RoutePath
          key={`route-${index}`}
          route={route}
          index={index}
          systems={systems}
          viewport={viewport}
          onClick={onRouteClick ? () => onRouteClick(index) : undefined}
        />
      ))}
    </svg>
  );
}

export default RouteOverlay;
