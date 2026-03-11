'use client';

import React, { useMemo } from 'react';
import type { MapSystem, MapViewport } from './types';
import type { SovStructure } from '@/lib/types';

const TYPE_SKYHOOK = 81826;
const HALO_COLOR = '#7dd3fc'; // sky-300

interface SkyhookHaloOverlayProps {
  structures: Record<string, SovStructure[]>;
  systems: Map<number, MapSystem>;
  viewport: MapViewport;
}

export const SkyhookHaloOverlay = React.memo(function SkyhookHaloOverlay({
  structures,
  systems,
  viewport,
}: SkyhookHaloOverlayProps) {
  const halos = useMemo(() => {
    const result: { systemId: number; x: number; y: number }[] = [];
    const pad = 40;

    for (const [sidStr, structs] of Object.entries(structures)) {
      const hasSkyhook = structs.some((s) => s.structure_type_id === TYPE_SKYHOOK);
      if (!hasSkyhook) continue;

      const system = systems.get(Number(sidStr));
      if (!system) continue;

      const sx = (system.x - viewport.x) * viewport.zoom + viewport.width / 2;
      const sy = (system.y - viewport.y) * viewport.zoom + viewport.height / 2;

      if (sx < -pad || sx > viewport.width + pad || sy < -pad || sy > viewport.height + pad) continue;

      result.push({ systemId: system.systemId, x: sx, y: sy });
    }

    return result;
  }, [structures, systems, viewport]);

  if (halos.length === 0) return null;

  // Scale halo radius with zoom
  const baseRadius = Math.max(4, Math.min(12, 6 * viewport.zoom));

  return (
    <svg
      className="absolute inset-0 pointer-events-none"
      width={viewport.width}
      height={viewport.height}
      style={{ zIndex: 1 }}
    >
      <defs>
        <filter id="skyhook-glow" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur in="SourceGraphic" stdDeviation="3" />
        </filter>
      </defs>
      {halos.map((h) => (
        <g key={h.systemId}>
          {/* Outer glow */}
          <circle
            cx={h.x}
            cy={h.y}
            r={baseRadius + 4}
            fill="none"
            stroke={HALO_COLOR}
            strokeWidth={1.5}
            opacity={0.25}
            filter="url(#skyhook-glow)"
          />
          {/* Inner ring */}
          <circle
            cx={h.x}
            cy={h.y}
            r={baseRadius}
            fill="none"
            stroke={HALO_COLOR}
            strokeWidth={1}
            opacity={0.5}
          />
        </g>
      ))}
    </svg>
  );
});

export default SkyhookHaloOverlay;
