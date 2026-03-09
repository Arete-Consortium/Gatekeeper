'use client';

import React, { useMemo } from 'react';
import type { MapSystem, MapViewport } from './types';
import type { SovStructure } from '@/lib/types';

// Structure type IDs from ESI
const STRUCTURE_TYPES = {
  32458: 'iHub', // Infrastructure Hub
  32226: 'TCU',  // Territorial Claim Unit
} as const;

interface SovStructuresOverlayProps {
  structures: Record<string, SovStructure[]>;
  systems: Map<number, MapSystem>;
  viewport: MapViewport;
}

function admColor(level: number | null): string {
  if (level === null || level === 0) return '#6b7280';
  if (level <= 2) return '#ef4444'; // Low ADM - red
  if (level <= 4) return '#f59e0b'; // Medium ADM - amber
  return '#22c55e'; // High ADM - green
}

export const SovStructuresOverlay = React.memo(function SovStructuresOverlay({
  structures,
  systems,
  viewport,
}: SovStructuresOverlayProps) {
  const markers = useMemo(() => {
    // Only show at reasonable zoom levels
    if (viewport.zoom < 1.5) return [];

    const result: Array<{
      systemId: number;
      x: number;
      y: number;
      ihubAdm: number | null;
      hasTcu: boolean;
    }> = [];

    for (const [sidStr, structs] of Object.entries(structures)) {
      const system = systems.get(Number(sidStr));
      if (!system) continue;

      const sx = (system.x - viewport.x) * viewport.zoom + viewport.width / 2;
      const sy = (system.y - viewport.y) * viewport.zoom + viewport.height / 2;

      if (sx < -20 || sx > viewport.width + 20 || sy < -20 || sy > viewport.height + 20) continue;

      let ihubAdm: number | null = null;
      let hasTcu = false;

      for (const s of structs) {
        if (s.structure_type_id === 32458) {
          ihubAdm = s.vulnerability_occupancy_level;
        } else if (s.structure_type_id === 32226) {
          hasTcu = true;
        }
      }

      result.push({ systemId: system.systemId, x: sx, y: sy, ihubAdm, hasTcu });
    }

    return result;
  }, [structures, systems, viewport]);

  if (markers.length === 0) return null;

  return (
    <svg
      className="absolute inset-0 pointer-events-none"
      width={viewport.width}
      height={viewport.height}
      style={{ zIndex: 2 }}
    >
      {markers.map((m) => (
        <g key={m.systemId}>
          {/* iHub ADM indicator — small bar below system */}
          {m.ihubAdm !== null && (
            <>
              <rect
                x={m.x - 8}
                y={m.y + 8}
                width={16}
                height={3}
                rx={1}
                fill="#1f2937"
                opacity={0.8}
              />
              <rect
                x={m.x - 8}
                y={m.y + 8}
                width={Math.max(1, (m.ihubAdm / 6) * 16)}
                height={3}
                rx={1}
                fill={admColor(m.ihubAdm)}
                opacity={0.8}
              />
            </>
          )}
          {/* ADM level text at higher zoom */}
          {m.ihubAdm !== null && viewport.zoom > 3 && (
            <text
              x={m.x + 12}
              y={m.y + 12}
              fill={admColor(m.ihubAdm)}
              fontSize={8}
              opacity={0.7}
            >
              ADM {m.ihubAdm}
            </text>
          )}
        </g>
      ))}
    </svg>
  );
});

export default SovStructuresOverlay;
