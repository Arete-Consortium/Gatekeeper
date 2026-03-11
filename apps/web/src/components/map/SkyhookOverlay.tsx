'use client';

import React, { useMemo } from 'react';
import type { MapSystem, MapViewport } from './types';
import type { SovStructure } from '@/lib/types';

const TYPE_SKYHOOK = 81826;
const SKYHOOK_COLOR = '#7dd3fc'; // sky-300

interface SkyhookOverlayProps {
  structures: Record<string, SovStructure[]>;
  systems: Map<number, MapSystem>;
  viewport: MapViewport;
}

export const SkyhookOverlay = React.memo(function SkyhookOverlay({
  structures,
  systems,
  viewport,
}: SkyhookOverlayProps) {
  const markers = useMemo(() => {
    const result: Array<{
      x: number;
      y: number;
      systemId: number;
      name: string;
    }> = [];

    for (const [sidStr, structs] of Object.entries(structures)) {
      const hasSkyhook = structs.some((s) => s.structure_type_id === TYPE_SKYHOOK);
      if (!hasSkyhook) continue;

      const system = systems.get(Number(sidStr));
      if (!system) continue;

      const sx = (system.x - viewport.x) * viewport.zoom + viewport.width / 2;
      const sy = (system.y - viewport.y) * viewport.zoom + viewport.height / 2;

      if (sx < -20 || sx > viewport.width + 20 || sy < -20 || sy > viewport.height + 20) continue;

      result.push({ x: sx, y: sy, systemId: system.systemId, name: system.name });
    }

    return result;
  }, [structures, systems, viewport]);

  if (markers.length === 0) return null;

  const radius = Math.max(4, Math.min(12, 6 * viewport.zoom));

  return (
    <svg
      className="absolute inset-0 pointer-events-none"
      width={viewport.width}
      height={viewport.height}
      style={{ zIndex: 1 }}
    >
      {markers.map((m) => (
        <circle
          key={m.systemId}
          cx={m.x}
          cy={m.y}
          r={radius}
          fill="none"
          stroke={SKYHOOK_COLOR}
          strokeWidth={1.5}
          opacity={0.7}
        >
          <title>{m.name} — Skyhook</title>
        </circle>
      ))}
    </svg>
  );
});

export default SkyhookOverlay;
