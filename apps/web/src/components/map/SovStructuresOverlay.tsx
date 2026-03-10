'use client';

import React, { useMemo } from 'react';
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

function admColor(level: number | null): string {
  if (level === null || level === 0) return '#6b7280';
  if (level <= 1) return '#ef4444'; // 1 - red
  if (level <= 2) return '#f97316'; // 2 - orange
  if (level <= 3) return '#f59e0b'; // 3 - amber
  if (level <= 4) return '#84cc16'; // 4 - lime
  return '#22c55e'; // 5-6 - green
}

const SKYHOOK_COLOR = '#38bdf8'; // sky-400

interface StructMarker {
  systemId: number;
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
  const isMobile = viewport.width < 768;

  const markers = useMemo(() => {
    if (viewport.zoom < 1.5) return [];

    const result: StructMarker[] = [];
    const pad = 30;

    for (const [sidStr, structs] of Object.entries(structures)) {
      const system = systems.get(Number(sidStr));
      if (!system) continue;

      const sx = (system.x - viewport.x) * viewport.zoom + viewport.width / 2;
      const sy = (system.y - viewport.y) * viewport.zoom + viewport.height / 2;

      if (sx < -pad || sx > viewport.width + pad || sy < -pad || sy > viewport.height + pad) continue;

      let ihubAdm: number | null = null;
      let hasTcu = false;
      let hasSkyhook = false;

      for (const s of structs) {
        if (s.structure_type_id === TYPE_IHUB) {
          ihubAdm = s.vulnerability_occupancy_level;
        } else if (s.structure_type_id === TYPE_TCU) {
          hasTcu = true;
        } else if (s.structure_type_id === TYPE_SKYHOOK) {
          hasSkyhook = true;
        }
      }

      result.push({ systemId: system.systemId, x: sx, y: sy, ihubAdm, hasTcu, hasSkyhook });
    }

    return result;
  }, [structures, systems, viewport]);

  if (markers.length === 0) return null;

  // Ring around system node — scales with zoom for visibility
  const baseR = isMobile ? 10 : 8;
  const ringR = Math.min(baseR * Math.sqrt(viewport.zoom), 20);
  const strokeW = isMobile ? 3 : 2.5;
  const fontSize = isMobile ? 11 : 9;
  const skyhookSize = isMobile ? 5 : 4;

  return (
    <svg
      className="absolute inset-0 pointer-events-none"
      width={viewport.width}
      height={viewport.height}
      style={{ zIndex: 2 }}
    >
      {markers.map((m) => (
        <g key={m.systemId}>
          {/* ADM ring around system node */}
          {m.ihubAdm !== null && (
            <circle
              cx={m.x}
              cy={m.y}
              r={ringR}
              fill="none"
              stroke={admColor(m.ihubAdm)}
              strokeWidth={strokeW}
              opacity={0.75}
            />
          )}
          {/* ADM number below system */}
          {m.ihubAdm !== null && viewport.zoom >= 2 && (
            <text
              x={m.x}
              y={m.y + ringR + fontSize + 1}
              textAnchor="middle"
              fill={admColor(m.ihubAdm)}
              fontSize={fontSize}
              fontWeight="bold"
              opacity={0.85}
            >
              {m.ihubAdm}
            </text>
          )}
          {/* Skyhook diamond — offset to upper-right of system */}
          {m.hasSkyhook && (
            <g transform={`translate(${m.x + ringR + 2}, ${m.y - ringR - 2})`}>
              <polygon
                points={`0,${-skyhookSize} ${skyhookSize},0 0,${skyhookSize} ${-skyhookSize},0`}
                fill={SKYHOOK_COLOR}
                opacity={0.85}
              />
            </g>
          )}
          {/* Labels at high zoom */}
          {viewport.zoom > 3 && (m.ihubAdm !== null || m.hasSkyhook) && (
            <text
              x={m.x + ringR + (m.hasSkyhook ? skyhookSize + 6 : 4)}
              y={m.y - ringR}
              fill={m.ihubAdm !== null ? admColor(m.ihubAdm) : SKYHOOK_COLOR}
              fontSize={fontSize - 1}
              opacity={0.65}
            >
              {m.ihubAdm !== null ? `ADM ${m.ihubAdm}` : ''}
              {m.ihubAdm !== null && m.hasSkyhook ? ' · ' : ''}
              {m.hasSkyhook ? 'Skyhook' : ''}
            </text>
          )}
        </g>
      ))}
    </svg>
  );
});

export default SovStructuresOverlay;
