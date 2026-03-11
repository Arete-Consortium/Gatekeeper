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

// Bold, saturated fills for the badge background
function admBgColor(level: number | null): string {
  if (level === null || level === 0) return '#374151'; // gray-700
  if (level <= 1) return '#991b1b'; // red-800
  if (level <= 2) return '#9a3412'; // orange-800
  if (level <= 3) return '#92400e'; // amber-800
  if (level <= 4) return '#3f6212'; // lime-800
  return '#166534'; // green-800
}

// Bright text/border color
function admFgColor(level: number | null): string {
  if (level === null || level === 0) return '#9ca3af';
  if (level <= 1) return '#fca5a5'; // red-300
  if (level <= 2) return '#fdba74'; // orange-300
  if (level <= 3) return '#fcd34d'; // amber-300
  if (level <= 4) return '#bef264'; // lime-300
  return '#86efac'; // green-300
}

const SKYHOOK_BG = '#0c4a6e'; // sky-900
const SKYHOOK_FG = '#7dd3fc'; // sky-300

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
    const pad = 40;

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

  // Badge dimensions — pill shape centered below system name
  // Pixi labels: center-anchored at y+12, 10px font → bottom edge ~y+17
  // Add generous gap so badge never overlaps name text
  const badgeH = isMobile ? 16 : 14;
  const badgeR = badgeH / 2;
  const fontSize = isMobile ? 11 : 10;
  const offsetY = 32; // well below system node + name label

  return (
    <svg
      className="absolute inset-0 pointer-events-none"
      width={viewport.width}
      height={viewport.height}
      style={{ zIndex: 2 }}
    >
      <defs>
        <filter id="adm-shadow" x="-20%" y="-20%" width="140%" height="140%">
          <feDropShadow dx="0" dy="1" stdDeviation="1.5" floodColor="#000" floodOpacity="0.5" />
        </filter>
      </defs>
      {markers.map((m) => {
        const by = m.y + offsetY;

        // ADM badge width based on content
        const admText = m.ihubAdm !== null ? String(m.ihubAdm) : null;
        const admBadgeW = admText ? (admText.length === 1 ? badgeH : badgeH + 4) : 0;

        // Skyhook badge
        const skBadgeW = badgeH + 6;
        const hasAdm = admBadgeW > 0;
        const hasSky = m.hasSkyhook;

        // Center all badges as a group under the system
        const totalW = (hasAdm ? admBadgeW : 0) + (hasSky ? skBadgeW : 0) + (hasAdm && hasSky ? 2 : 0);
        const groupX = m.x - totalW / 2;
        const admCx = groupX + admBadgeW / 2;
        const skCx = groupX + (hasAdm ? admBadgeW + 2 : 0) + skBadgeW / 2;

        return (
          <g key={m.systemId} filter="url(#adm-shadow)">
            {/* ADM badge — rounded pill with number */}
            {admText !== null && (
              <>
                <rect
                  x={admCx - admBadgeW / 2}
                  y={by - badgeR}
                  width={admBadgeW}
                  height={badgeH}
                  rx={badgeR}
                  fill={admBgColor(m.ihubAdm)}
                  stroke={admFgColor(m.ihubAdm)}
                  strokeWidth={1.5}
                  opacity={0.92}
                />
                <text
                  x={admCx}
                  y={by + fontSize * 0.35}
                  textAnchor="middle"
                  fill={admFgColor(m.ihubAdm)}
                  fontSize={fontSize}
                  fontWeight="bold"
                  fontFamily="monospace"
                >
                  {admText}
                </text>
              </>
            )}
            {/* Skyhook badge — "S" in sky-blue pill */}
            {m.hasSkyhook && (
              <>
                <rect
                  x={skCx - skBadgeW / 2}
                  y={by - badgeR}
                  width={skBadgeW}
                  height={badgeH}
                  rx={badgeR}
                  fill={SKYHOOK_BG}
                  stroke={SKYHOOK_FG}
                  strokeWidth={1.5}
                  opacity={0.92}
                />
                <text
                  x={skCx}
                  y={by + fontSize * 0.35}
                  textAnchor="middle"
                  fill={SKYHOOK_FG}
                  fontSize={fontSize - 1}
                  fontWeight="bold"
                  fontFamily="monospace"
                >
                  S
                </text>
              </>
            )}
          </g>
        );
      })}
    </svg>
  );
});

export default SovStructuresOverlay;
