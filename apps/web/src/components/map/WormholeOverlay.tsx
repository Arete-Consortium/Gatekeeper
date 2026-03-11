'use client';

import React, { useMemo } from 'react';
import type { MapSystem, MapViewport } from './types';
import type { WormholeConnection } from '@/lib/types';

interface WormholeOverlayProps {
  connections: WormholeConnection[];
  systems: Map<number, MapSystem>;
  viewport: MapViewport;
}

const WORMHOLE_COLOR = '#a855f7';

/** Line thickness by mass status */
function getMassStrokeWidth(mass: WormholeConnection['mass_status']): number {
  switch (mass) {
    case 'stable': return 2;
    case 'destabilized': return 1.5;
    case 'critical': return 1;
    case 'collapsed': return 0.5;
  }
}

/** Dash pattern by mass status */
function getMassDashArray(mass: WormholeConnection['mass_status']): string {
  switch (mass) {
    case 'critical': return '4 4';
    case 'collapsed': return '2 4';
    default: return '6 4';
  }
}

export const WormholeOverlay = React.memo(function WormholeOverlay({
  connections,
  systems,
  viewport,
}: WormholeOverlayProps) {
  const lines = useMemo(() => {
    const result: Array<{
      id: string;
      x1: number;
      y1: number;
      x2: number;
      y2: number;
      type: WormholeConnection['wormhole_type'];
      mass: WormholeConnection['mass_status'];
      life: WormholeConnection['life_status'];
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
        type: conn.wormhole_type,
        mass: conn.mass_status,
        life: conn.life_status,
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
        <filter id="wormhole-glow">
          <feGaussianBlur stdDeviation="3" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      {lines.map((line) => {
        const opacity = line.life === 'eol' ? 0.4 : 0.8;
        const strokeWidth = getMassStrokeWidth(line.mass);
        const dashArray = getMassDashArray(line.mass);

        return (
          <g key={line.id}>
            {/* Glow line */}
            <line
              x1={line.x1}
              y1={line.y1}
              x2={line.x2}
              y2={line.y2}
              stroke={WORMHOLE_COLOR}
              strokeWidth={strokeWidth + 1}
              opacity={opacity * 0.5}
              filter="url(#wormhole-glow)"
            />
            {/* Main dashed line */}
            <line
              x1={line.x1}
              y1={line.y1}
              x2={line.x2}
              y2={line.y2}
              stroke={WORMHOLE_COLOR}
              strokeWidth={strokeWidth}
              strokeDasharray={dashArray}
              opacity={opacity}
            />
            {/* Endpoint markers */}
            <circle cx={line.x1} cy={line.y1} r={3} fill={WORMHOLE_COLOR} opacity={opacity} />
            <circle cx={line.x2} cy={line.y2} r={3} fill={WORMHOLE_COLOR} opacity={opacity} />
            {/* Type label at midpoint when zoomed in */}
            {viewport.zoom > 1.5 && (
              <text
                x={(line.x1 + line.x2) / 2}
                y={(line.y1 + line.y2) / 2 - 8}
                textAnchor="middle"
                fill={WORMHOLE_COLOR}
                fontSize={10}
                opacity={0.7}
              >
                {line.type}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
});

export default WormholeOverlay;
