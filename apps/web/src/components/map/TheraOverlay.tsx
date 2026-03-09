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
  const lines = useMemo(() => {
    const result: Array<{
      id: number;
      x1: number;
      y1: number;
      x2: number;
      y2: number;
      label: string;
      hours: number;
    }> = [];

    for (const conn of connections) {
      if (!conn.completed) continue; // Only show verified connections

      const source = systems.get(conn.source_system_id);
      const dest = systems.get(conn.dest_system_id);
      if (!source || !dest) continue;

      const x1 = (source.x - viewport.x) * viewport.zoom + viewport.width / 2;
      const y1 = (source.y - viewport.y) * viewport.zoom + viewport.height / 2;
      const x2 = (dest.x - viewport.x) * viewport.zoom + viewport.width / 2;
      const y2 = (dest.y - viewport.y) * viewport.zoom + viewport.height / 2;

      // Skip if both endpoints off screen
      if (
        (x1 < -50 || x1 > viewport.width + 50) &&
        (x2 < -50 || x2 > viewport.width + 50)
      ) continue;

      result.push({
        id: conn.id,
        x1, y1, x2, y2,
        label: `${conn.source_system_name} → ${conn.dest_system_name}`,
        hours: conn.remaining_hours,
      });
    }

    return result;
  }, [connections, systems, viewport]);

  if (lines.length === 0) return null;

  return (
    <svg
      className="absolute inset-0 pointer-events-none"
      width={viewport.width}
      height={viewport.height}
      style={{ zIndex: 3 }}
    >
      <defs>
        <filter id="thera-glow">
          <feGaussianBlur stdDeviation="3" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      {lines.map((line) => (
        <g key={line.id}>
          {/* Glow line */}
          <line
            x1={line.x1}
            y1={line.y1}
            x2={line.x2}
            y2={line.y2}
            stroke="#00e5ff"
            strokeWidth={2}
            opacity={0.4}
            filter="url(#thera-glow)"
          />
          {/* Main line */}
          <line
            x1={line.x1}
            y1={line.y1}
            x2={line.x2}
            y2={line.y2}
            stroke="#00e5ff"
            strokeWidth={1.5}
            strokeDasharray="6 4"
            opacity={0.8}
          />
          {/* Endpoint markers */}
          <circle cx={line.x1} cy={line.y1} r={4} fill="#00e5ff" opacity={0.8} />
          <circle cx={line.x2} cy={line.y2} r={4} fill="#00e5ff" opacity={0.8} />
          {/* Label at midpoint */}
          {viewport.zoom > 1 && (
            <text
              x={(line.x1 + line.x2) / 2}
              y={(line.y1 + line.y2) / 2 - 8}
              textAnchor="middle"
              fill="#00e5ff"
              fontSize={10}
              opacity={0.7}
            >
              {line.hours}h
            </text>
          )}
        </g>
      ))}
    </svg>
  );
});

export default TheraOverlay;
