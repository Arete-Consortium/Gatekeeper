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

// ADM text color — bright, readable
function admColor(level: number | null): string {
  if (level === null || level === 0) return '#9ca3af';
  if (level <= 1) return '#fca5a5';
  if (level <= 2) return '#fdba74';
  if (level <= 3) return '#fcd34d';
  if (level <= 4) return '#bef264';
  return '#86efac';
}

const SKYHOOK_FG = '#7dd3fc';
const BLOCK_BG = 'rgba(0,0,0,0.85)';
const NAME_COLOR = '#e2e8f0'; // slate-200

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
  const isMobile = viewport.width < 768;
  const isZoomed = viewport.zoom >= 3;

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

      result.push({ systemId: system.systemId, name: system.name, x: sx, y: sy, ihubAdm, hasTcu, hasSkyhook });
    }

    return result;
  }, [structures, systems, viewport]);

  if (markers.length === 0) return null;

  // Font sizes: base + 30% boost when zoomed in
  const baseFontName = isMobile ? 10 : 9;
  const baseFontAdm = isMobile ? 10 : 9;
  const fontScale = isZoomed ? 1.3 : 1.0;
  const fontName = Math.round(baseFontName * fontScale);
  const fontAdm = Math.round(baseFontAdm * fontScale);

  // Layout constants
  const lineH1 = fontName + 4; // row 1 height (name)
  const lineH2 = fontAdm + 4;  // row 2 height (ADM)
  const padX = 6;
  const padY = 3;
  const rowGap = 1;
  const blockH = padY + lineH1 + rowGap + lineH2 + padY;
  // Char width estimate for monospace (~0.6em)
  const charW = fontName * 0.62;
  const charWAdm = fontAdm * 0.62;

  // Position: cover the Pixi label area (label is at ~y+12, 10px font)
  // Block starts at y+5 to cover the Pixi label with opaque bg
  const blockOffsetY = 5;

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

        // Build row 2 text parts
        const admText = hasAdm ? `ADM ${m.ihubAdm!.toFixed(1)}` : '';
        const skyText = hasSky ? 'S' : '';
        const row2Text = [admText, skyText].filter(Boolean).join('  ');

        // Calculate widths
        const nameW = m.name.length * charW;
        const row2W = row2Text.length * charWAdm;
        const contentW = Math.max(nameW, row2W);
        const blockW = contentW + padX * 2;

        const bx = m.x - blockW / 2;
        const by = m.y + blockOffsetY;

        // Text positions (vertically centered in each row)
        const nameY = by + padY + lineH1 / 2 + fontName * 0.35;
        const admY = by + padY + lineH1 + rowGap + lineH2 / 2 + fontAdm * 0.35;

        return (
          <g key={m.systemId}>
            {/* Dark opaque background block covering Pixi label */}
            <rect
              x={bx}
              y={by}
              width={blockW}
              height={blockH}
              rx={3}
              fill={BLOCK_BG}
            />
            {/* Row 1: System name */}
            <text
              x={m.x}
              y={nameY}
              textAnchor="middle"
              fill={NAME_COLOR}
              fontSize={fontName}
              fontWeight="bold"
              fontFamily="monospace"
            >
              {m.name}
            </text>
            {/* Row 2: ADM level + Skyhook */}
            <text
              x={m.x}
              y={admY}
              textAnchor="middle"
              fontSize={fontAdm}
              fontFamily="monospace"
            >
              {hasAdm && (
                <tspan fill={admColor(m.ihubAdm)} fontWeight="bold">
                  ADM {m.ihubAdm!.toFixed(1)}
                </tspan>
              )}
              {hasAdm && hasSky && (
                <tspan fill={NAME_COLOR}>{' '}</tspan>
              )}
              {hasSky && (
                <tspan fill={SKYHOOK_FG} fontWeight="bold">S</tspan>
              )}
            </text>
          </g>
        );
      })}
    </svg>
  );
});

export default SovStructuresOverlay;
