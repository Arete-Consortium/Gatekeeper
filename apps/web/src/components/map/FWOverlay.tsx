'use client';

import React, { useMemo } from 'react';
import type { MapSystem, MapViewport } from './types';
import type { FWSystem } from '@/lib/types';

// Faction colors matching EVE lore
const FACTION_COLORS: Record<number, { color: string; name: string }> = {
  500001: { color: '#c8aa00', name: 'Caldari State' },
  500002: { color: '#2a7fff', name: 'Minmatar Republic' },
  500003: { color: '#c83232', name: 'Amarr Empire' },
  500004: { color: '#1e8c1e', name: 'Gallente Federation' },
};

interface FWOverlayProps {
  fwSystems: Record<string, FWSystem>;
  systems: Map<number, MapSystem>;
  viewport: MapViewport;
}

export const FWOverlay = React.memo(function FWOverlay({
  fwSystems,
  systems,
  viewport,
}: FWOverlayProps) {
  const markers = useMemo(() => {
    const result: Array<{
      x: number;
      y: number;
      systemId: number;
      ownerColor: string;
      occupierColor: string;
      contested: string;
      progress: number;
    }> = [];

    for (const [sidStr, fw] of Object.entries(fwSystems)) {
      const system = systems.get(Number(sidStr));
      if (!system) continue;

      const sx = (system.x - viewport.x) * viewport.zoom + viewport.width / 2;
      const sy = (system.y - viewport.y) * viewport.zoom + viewport.height / 2;

      if (sx < -20 || sx > viewport.width + 20 || sy < -20 || sy > viewport.height + 20) continue;

      const ownerInfo = FACTION_COLORS[fw.owner_faction_id];
      const occupierInfo = FACTION_COLORS[fw.occupier_faction_id];
      if (!ownerInfo || !occupierInfo) continue;

      const progress = fw.victory_points_threshold > 0
        ? fw.victory_points / fw.victory_points_threshold
        : 0;

      result.push({
        x: sx,
        y: sy,
        systemId: system.systemId,
        ownerColor: ownerInfo.color,
        occupierColor: occupierInfo.color,
        contested: fw.contested,
        progress,
      });
    }

    return result;
  }, [fwSystems, systems, viewport]);

  if (markers.length === 0) return null;

  const radius = Math.max(3, Math.min(10, 5 * viewport.zoom));

  return (
    <svg
      className="absolute inset-0 pointer-events-none"
      width={viewport.width}
      height={viewport.height}
      style={{ zIndex: 2 }}
    >
      {markers.map((m) => {
        const isContested = m.contested === 'contested' || m.contested === 'vulnerable';
        const isFlipped = m.ownerColor !== m.occupierColor;

        return (
          <g key={m.systemId}>
            {/* Occupier fill */}
            <circle
              cx={m.x}
              cy={m.y}
              r={radius}
              fill={m.occupierColor}
              opacity={0.25}
            />
            {/* Owner border */}
            <circle
              cx={m.x}
              cy={m.y}
              r={radius}
              fill="none"
              stroke={m.ownerColor}
              strokeWidth={isFlipped ? 2 : 1}
              opacity={0.7}
            />
            {/* Contested indicator — pulsing ring */}
            {isContested && (
              <circle
                cx={m.x}
                cy={m.y}
                r={radius + 3}
                fill="none"
                stroke={m.occupierColor}
                strokeWidth={1}
                strokeDasharray="3 3"
                opacity={0.5}
              />
            )}
          </g>
        );
      })}
    </svg>
  );
});

export default FWOverlay;
