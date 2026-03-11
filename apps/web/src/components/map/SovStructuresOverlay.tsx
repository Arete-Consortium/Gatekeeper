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

// ADM badge background — dark, saturated
function admBgColor(level: number | null): string {
  if (level === null || level === 0) return '#374151';
  if (level <= 1) return '#991b1b';
  if (level <= 2) return '#9a3412';
  if (level <= 3) return '#92400e';
  if (level <= 4) return '#3f6212';
  return '#166534';
}

// ADM badge foreground — bright, readable
function admFgColor(level: number | null): string {
  if (level === null || level === 0) return '#9ca3af';
  if (level <= 1) return '#fca5a5';
  if (level <= 2) return '#fdba74';
  if (level <= 3) return '#fcd34d';
  if (level <= 4) return '#bef264';
  return '#86efac';
}

const SKYHOOK_BG = '#0c4a6e';
const SKYHOOK_FG = '#7dd3fc';
const BLOCK_BG = 'rgba(0,0,0,0.75)';

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

  // Solid block below system name
  // Pixi name label: center-anchored 10px font at y+12, bottom edge ~y+18
  // Block starts well below at y+22 with its own opaque background
  const blockTop = 22;
  const blockH = isMobile ? 18 : 16;
  const blockPadX = 4;
  const fontSize = isMobile ? 10 : 9;
  const pillH = blockH - 4;
  const pillR = pillH / 2;

  return (
    <svg
      className="absolute inset-0 pointer-events-none"
      width={viewport.width}
      height={viewport.height}
      style={{ zIndex: 2 }}
    >
      {markers.map((m) => {
        const hasAdm = m.ihubAdm !== null;
        const hasSky = m.hasSkyhook;
        if (!hasAdm && !hasSky) return null;

        const admLabel = hasAdm ? String(Math.round(m.ihubAdm!)) : '';
        const admPillW = hasAdm ? fontSize + 6 : 0;
        const skyPillW = hasSky ? fontSize + 8 : 0;
        const gap = hasAdm && hasSky ? 3 : 0;
        const contentW = admPillW + skyPillW + gap;
        const blockW = contentW + blockPadX * 2;

        const bx = m.x - blockW / 2;
        const by = m.y + blockTop;

        return (
          <g key={m.systemId}>
            {/* Solid dark background block */}
            <rect
              x={bx}
              y={by}
              width={blockW}
              height={blockH}
              rx={3}
              fill={BLOCK_BG}
            />
            {/* ADM pill inside block */}
            {hasAdm && (() => {
              const px = bx + blockPadX;
              const py = by + (blockH - pillH) / 2;
              const cx = px + admPillW / 2;
              return (
                <>
                  <rect
                    x={px}
                    y={py}
                    width={admPillW}
                    height={pillH}
                    rx={pillR}
                    fill={admBgColor(m.ihubAdm)}
                    stroke={admFgColor(m.ihubAdm)}
                    strokeWidth={1}
                  />
                  <text
                    x={cx}
                    y={by + blockH / 2 + fontSize * 0.35}
                    textAnchor="middle"
                    fill={admFgColor(m.ihubAdm)}
                    fontSize={fontSize}
                    fontWeight="bold"
                    fontFamily="monospace"
                  >
                    {admLabel}
                  </text>
                </>
              );
            })()}
            {/* Skyhook pill inside block */}
            {hasSky && (() => {
              const px = bx + blockPadX + (hasAdm ? admPillW + gap : 0);
              const py = by + (blockH - pillH) / 2;
              const cx = px + skyPillW / 2;
              return (
                <>
                  <rect
                    x={px}
                    y={py}
                    width={skyPillW}
                    height={pillH}
                    rx={pillR}
                    fill={SKYHOOK_BG}
                    stroke={SKYHOOK_FG}
                    strokeWidth={1}
                  />
                  <text
                    x={cx}
                    y={by + blockH / 2 + fontSize * 0.35}
                    textAnchor="middle"
                    fill={SKYHOOK_FG}
                    fontSize={fontSize}
                    fontWeight="bold"
                    fontFamily="monospace"
                  >
                    S
                  </text>
                </>
              );
            })()}
          </g>
        );
      })}
    </svg>
  );
});

export default SovStructuresOverlay;
