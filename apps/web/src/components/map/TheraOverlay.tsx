'use client';

import React, { useMemo } from 'react';
import type { MapSystem, MapViewport } from './types';
import type { TheraConnection } from '@/lib/types';

interface TheraOverlayProps {
  connections: TheraConnection[];
  systems: Map<number, MapSystem>;
  viewport: MapViewport;
}

export const TheraOverlay = React.memo(function TheraOverlay({
  connections,
  systems,
  viewport,
}: TheraOverlayProps) {
  const markers = useMemo(() => {
    const result: Array<{
      id: number;
      x: number;
      y: number;
      systemName: string;
      regionName: string;
      whType: string;
      maxShipSize: string;
      hours: number;
    }> = [];

    for (const conn of connections) {
      if (!conn.completed) continue;

      const system = systems.get(conn.system_id);
      if (!system) continue;

      const x = (system.x - viewport.x) * viewport.zoom + viewport.width / 2;
      const y = (system.y - viewport.y) * viewport.zoom + viewport.height / 2;

      // Skip if off screen
      if (x < -50 || x > viewport.width + 50 || y < -50 || y > viewport.height + 50) continue;

      result.push({
        id: conn.id,
        x, y,
        systemName: conn.system_name,
        regionName: conn.region_name,
        whType: conn.wh_type,
        maxShipSize: conn.max_ship_size,
        hours: conn.remaining_hours,
      });
    }

    return result;
  }, [connections, systems, viewport]);

  if (markers.length === 0) return null;

  return (
    <svg
      className="absolute inset-0 pointer-events-none"
      width={viewport.width}
      height={viewport.height}
      style={{ zIndex: 3 }}
    >
      <defs>
        <filter id="thera-glow">
          <feGaussianBlur stdDeviation="4" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      {markers.map((marker) => (
        <g key={marker.id}>
          {/* Outer pulsing ring */}
          <circle
            cx={marker.x}
            cy={marker.y}
            r={10}
            fill="none"
            stroke="#00e5ff"
            strokeWidth={1.5}
            opacity={0.3}
            filter="url(#thera-glow)"
          >
            <animate
              attributeName="r"
              values="8;14;8"
              dur="2s"
              repeatCount="indefinite"
            />
            <animate
              attributeName="opacity"
              values="0.4;0.1;0.4"
              dur="2s"
              repeatCount="indefinite"
            />
          </circle>
          {/* Inner dot */}
          <circle
            cx={marker.x}
            cy={marker.y}
            r={5}
            fill="#00e5ff"
            opacity={0.8}
            filter="url(#thera-glow)"
          />
          {/* "T" marker */}
          <text
            x={marker.x}
            y={marker.y + 3.5}
            textAnchor="middle"
            fill="#0a0e17"
            fontSize={8}
            fontWeight="bold"
          >
            T
          </text>
          {/* Label */}
          {viewport.zoom > 0.8 && (
            <text
              x={marker.x}
              y={marker.y - 14}
              textAnchor="middle"
              fill="#00e5ff"
              fontSize={9}
              opacity={0.8}
            >
              Thera {marker.hours > 0 ? `(${Math.round(marker.hours)}h)` : ''}
            </text>
          )}
        </g>
      ))}
    </svg>
  );
});

export default TheraOverlay;
