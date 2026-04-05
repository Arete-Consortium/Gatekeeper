'use client';

/**
 * JumpBridgeOverlay — SVG overlay for user-submitted jump bridge connections
 * Renders dashed lines between connected systems with Ansiblex-style styling
 */

import React, { useMemo } from 'react';
import type { MapSystem, MapViewport } from './types';
import type { JumpBridgeConnection } from '@/lib/types';

interface JumpBridgeOverlayProps {
  connections: JumpBridgeConnection[];
  systems: Map<number, MapSystem>;
  viewport: MapViewport;
}

/** Orange for online bridges, cyan for unknown status, gray for offline */
function getBridgeColor(status: JumpBridgeConnection['status']): string {
  switch (status) {
    case 'online': return '#f97316';   // orange-500
    case 'offline': return '#6b7280';  // gray-500
    case 'unknown': return '#06b6d4';  // cyan-500
  }
}

function getBridgeOpacity(status: JumpBridgeConnection['status']): number {
  switch (status) {
    case 'online': return 0.8;
    case 'offline': return 0.3;
    case 'unknown': return 0.6;
  }
}

export const JumpBridgeOverlay = React.memo(function JumpBridgeOverlay({
  connections,
  systems,
  viewport,
}: JumpBridgeOverlayProps) {
  const lines = useMemo(() => {
    const result: Array<{
      id: string;
      x1: number;
      y1: number;
      x2: number;
      y2: number;
      fromName: string;
      toName: string;
      status: JumpBridgeConnection['status'];
      owner: string | null;
    }> = [];

    for (const conn of connections) {
      const from = systems.get(conn.from_system_id);
      const to = systems.get(conn.to_system_id);
      if (!from || !to) continue;

      const x1 = (from.x - viewport.x) * viewport.zoom + viewport.width / 2;
      const y1 = (from.y - viewport.y) * viewport.zoom + viewport.height / 2;
      const x2 = (to.x - viewport.x) * viewport.zoom + viewport.width / 2;
      const y2 = (to.y - viewport.y) * viewport.zoom + viewport.height / 2;

      // Viewport culling — skip if both endpoints off screen
      if (
        (x1 < -50 || x1 > viewport.width + 50) &&
        (x2 < -50 || x2 > viewport.width + 50)
      ) continue;
      if (
        (y1 < -50 || y1 > viewport.height + 50) &&
        (y2 < -50 || y2 > viewport.height + 50)
      ) continue;

      result.push({
        id: conn.id,
        x1, y1, x2, y2,
        fromName: conn.from_system,
        toName: conn.to_system,
        status: conn.status,
        owner: conn.owner_alliance,
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
        <filter id="jb-glow">
          <feGaussianBlur stdDeviation="3" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      {lines.map((line) => {
        const color = getBridgeColor(line.status);
        const opacity = getBridgeOpacity(line.status);
        const midX = (line.x1 + line.x2) / 2;
        const midY = (line.y1 + line.y2) / 2;

        // Curved path — quadratic bezier with perpendicular offset for visual clarity
        // This prevents JB lines from overlapping gate lines between the same systems
        const dx = line.x2 - line.x1;
        const dy = line.y2 - line.y1;
        const len = Math.sqrt(dx * dx + dy * dy);
        const curveOffset = Math.min(len * 0.15, 30);
        // Perpendicular normal
        const nx = -dy / (len || 1);
        const ny = dx / (len || 1);
        const cx = midX + nx * curveOffset;
        const cy = midY + ny * curveOffset;

        const pathD = `M ${line.x1} ${line.y1} Q ${cx} ${cy} ${line.x2} ${line.y2}`;

        return (
          <g key={line.id}>
            {/* Glow line */}
            <path
              d={pathD}
              fill="none"
              stroke={color}
              strokeWidth={3}
              opacity={opacity * 0.3}
              filter="url(#jb-glow)"
            />
            {/* Main dashed line */}
            <path
              d={pathD}
              fill="none"
              stroke={color}
              strokeWidth={2}
              strokeDasharray="8 4"
              opacity={opacity}
            />
            {/* Endpoint diamonds (Ansiblex markers) */}
            <g transform={`translate(${line.x1}, ${line.y1}) rotate(45)`}>
              <rect x={-3} y={-3} width={6} height={6} fill={color} opacity={opacity} />
            </g>
            <g transform={`translate(${line.x2}, ${line.y2}) rotate(45)`}>
              <rect x={-3} y={-3} width={6} height={6} fill={color} opacity={opacity} />
            </g>
            {/* "JB" label at curve apex when zoomed in */}
            {viewport.zoom > 1.2 && (
              <text
                x={cx}
                y={cy - 8}
                textAnchor="middle"
                fill={color}
                fontSize={9}
                fontWeight="bold"
                opacity={0.7}
              >
                JB
              </text>
            )}
            {/* Owner label at deeper zoom */}
            {viewport.zoom > 2.0 && line.owner && (
              <text
                x={cx}
                y={cy + 12}
                textAnchor="middle"
                fill={color}
                fontSize={8}
                opacity={0.5}
              >
                {line.owner}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
});

export default JumpBridgeOverlay;
