'use client';

import React, { useMemo, useState, useCallback } from 'react';
import type { MapSystem, MapViewport } from './types';
import type { SovStructure } from '@/lib/types';

// Structure type IDs from ESI
const TYPE_IHUB = 32458;
const TYPE_TCU = 32226;
const TYPE_SKYHOOK = 81826; // Orbital Skyhook (Equinox)

interface SovStructuresOverlayProps {
  structures: Record<string, SovStructure[]>;
  systems: Map<number, MapSystem>;
  viewport: MapViewport;
}

// ADM text color — bright, readable
function admColor(level: number | null): string {
  if (level === null || level === 0) return '#9ca3af';
  if (level <= 1) return '#fca5a5';
  if (level <= 2) return '#fdba74';
  if (level <= 3) return '#fcd34d';
  if (level <= 4) return '#bef264';
  return '#86efac';
}

// ADM dot color (smaller version of the same scale)
function admDotColor(level: number | null): string {
  if (level === null || level === 0) return '#6b7280';
  if (level <= 1) return '#ef4444';
  if (level <= 2) return '#f97316';
  if (level <= 3) return '#eab308';
  if (level <= 4) return '#84cc16';
  return '#22c55e';
}

const SKYHOOK_FG = '#7dd3fc';

interface StructMarker {
  systemId: number;
  name: string;
  x: number;
  y: number;
  ihubAdm: number | null;
  hasTcu: boolean;
  hasSkyhook: boolean;
}

export const SovStructuresOverlay = React.memo(function SovStructuresOverlay({
  structures,
  systems,
  viewport,
}: SovStructuresOverlayProps) {
  const [hoveredSystem, setHoveredSystem] = useState<number | null>(null);

  const markers = useMemo(() => {
    if (viewport.zoom < 1.5) return [];

    const result: StructMarker[] = [];
    const pad = 60;

    for (const [sidStr, structs] of Object.entries(structures)) {
      const system = systems.get(Number(sidStr));
      if (!system) continue;

      const sx = (system.x - viewport.x) * viewport.zoom + viewport.width / 2;
      const sy = (system.y - viewport.y) * viewport.zoom + viewport.height / 2;

      if (sx < -pad || sx > viewport.width + pad || sy < -pad || sy > viewport.height + pad) continue;

      let ihubAdm: number | null = null;
      let hasIhub = false;
      let hasTcu = false;
      let hasSkyhook = false;

      for (const s of structs) {
        if (s.structure_type_id === TYPE_IHUB) {
          hasIhub = true;
          ihubAdm = s.vulnerability_occupancy_level;
        } else if (s.structure_type_id === TYPE_TCU) {
          hasTcu = true;
        } else if (s.structure_type_id === TYPE_SKYHOOK) {
          hasSkyhook = true;
        }
      }

      if (!hasIhub && !hasSkyhook) continue;

      result.push({ systemId: system.systemId, name: system.name, x: sx, y: sy, ihubAdm, hasTcu, hasSkyhook });
    }

    return result;
  }, [structures, systems, viewport]);

  const handleMouseEnter = useCallback((systemId: number) => {
    setHoveredSystem(systemId);
  }, []);

  const handleMouseLeave = useCallback(() => {
    setHoveredSystem(null);
  }, []);

  if (markers.length === 0) return null;

  const dotRadius = Math.max(2, Math.min(4, 3 * (viewport.zoom / 2)));
  const hoveredMarker = hoveredSystem ? markers.find((m) => m.systemId === hoveredSystem) : null;

  return (
    <>
      <svg
        className="absolute inset-0"
        width={viewport.width}
        height={viewport.height}
        style={{ zIndex: 2, pointerEvents: 'none' }}
      >
        {markers.map((m) => {
          const color = admDotColor(m.ihubAdm);
          return (
            <g key={m.systemId}>
              {/* Small ADM indicator dot offset to upper-right of system */}
              <circle
                cx={m.x + 5}
                cy={m.y - 5}
                r={dotRadius}
                fill={color}
                opacity={0.9}
              />
              {/* Skyhook indicator — tiny sky-blue dot */}
              {m.hasSkyhook && (
                <circle
                  cx={m.x + 5 + dotRadius * 2 + 1}
                  cy={m.y - 5}
                  r={dotRadius * 0.7}
                  fill={SKYHOOK_FG}
                  opacity={0.9}
                />
              )}
              {/* Invisible hit area for hover */}
              <circle
                cx={m.x}
                cy={m.y}
                r={Math.max(dotRadius + 6, 10)}
                fill="transparent"
                style={{ pointerEvents: 'all' }}
                onMouseEnter={() => handleMouseEnter(m.systemId)}
                onMouseLeave={handleMouseLeave}
              />
            </g>
          );
        })}
      </svg>
      {/* Hover tooltip with full ADM info */}
      {hoveredMarker && (
        <div
          className="absolute pointer-events-none z-50"
          style={{
            left: hoveredMarker.x + 12,
            top: hoveredMarker.y - 10,
            transform: hoveredMarker.x > viewport.width - 200 ? 'translateX(calc(-100% - 24px))' : undefined,
          }}
        >
          <div className="bg-gray-900/95 border border-gray-600 rounded px-2.5 py-1.5 text-xs shadow-lg backdrop-blur-sm whitespace-nowrap">
            <div className="font-semibold text-slate-200 mb-1">{hoveredMarker.name}</div>
            {hoveredMarker.ihubAdm !== null && (
              <div style={{ color: admColor(hoveredMarker.ihubAdm) }} className="font-mono font-bold">
                ADM {hoveredMarker.ihubAdm.toFixed(1)}
              </div>
            )}
            {hoveredMarker.ihubAdm === null && (
              <div className="text-gray-500 font-mono">iHub (no ADM)</div>
            )}
            {hoveredMarker.hasTcu && (
              <div className="text-gray-400">TCU</div>
            )}
            {hoveredMarker.hasSkyhook && (
              <div style={{ color: SKYHOOK_FG }} className="font-bold">Skyhook</div>
            )}
          </div>
        </div>
      )}
    </>
  );
});

export default SovStructuresOverlay;
