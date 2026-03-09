'use client';

import React, { useMemo, useState } from 'react';
import type { MapSystem, MapViewport } from './types';
import type { Landmark } from '@/lib/types';

interface LandmarksOverlayProps {
  landmarks: Landmark[];
  systems: Map<number, MapSystem>;
  viewport: MapViewport;
}

export const LandmarksOverlay = React.memo(function LandmarksOverlay({
  landmarks,
  systems,
  viewport,
}: LandmarksOverlayProps) {
  const [hoveredId, setHoveredId] = useState<number | null>(null);

  const markers = useMemo(() => {
    const result: Array<{
      id: number;
      x: number;
      y: number;
      name: string;
      description: string;
    }> = [];

    for (const lm of landmarks) {
      if (!lm.system_id) continue;

      const system = systems.get(lm.system_id);
      if (!system) continue;

      const sx = (system.x - viewport.x) * viewport.zoom + viewport.width / 2;
      const sy = (system.y - viewport.y) * viewport.zoom + viewport.height / 2;

      if (sx < -30 || sx > viewport.width + 30 || sy < -30 || sy > viewport.height + 30) continue;

      result.push({
        id: lm.id,
        x: sx,
        y: sy,
        name: lm.name,
        description: lm.description,
      });
    }

    return result;
  }, [landmarks, systems, viewport]);

  if (markers.length === 0) return null;

  return (
    <div
      className="absolute inset-0 pointer-events-none"
      style={{ zIndex: 4 }}
    >
      {markers.map((m) => (
        <div
          key={m.id}
          className="absolute pointer-events-auto cursor-pointer"
          style={{
            left: m.x - 6,
            top: m.y - 6,
          }}
          onMouseEnter={() => setHoveredId(m.id)}
          onMouseLeave={() => setHoveredId(null)}
        >
          {/* Diamond marker */}
          <div
            className="w-3 h-3 rotate-45 border border-amber-400/80 bg-amber-400/20"
          />

          {/* Label (always visible at high zoom) */}
          {viewport.zoom > 2 && (
            <span
              className="absolute left-5 top-0 whitespace-nowrap text-amber-300/70 text-[10px] font-medium select-none"
            >
              {m.name}
            </span>
          )}

          {/* Tooltip on hover */}
          {hoveredId === m.id && (
            <div
              className="absolute left-5 -top-2 bg-gray-900/95 border border-amber-400/40 rounded px-2 py-1.5 z-50 min-w-[180px] max-w-[280px]"
            >
              <div className="text-amber-300 text-xs font-semibold">{m.name}</div>
              {m.description && (
                <div className="text-gray-400 text-[10px] mt-0.5 line-clamp-3">
                  {m.description}
                </div>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
});

export default LandmarksOverlay;
