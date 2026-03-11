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
  offsetY: number;
  ihubAdm: number | null;
  hasTcu: boolean;
  hasSkyhook: boolean;
}

function rectsOverlap(
  a: { x: number; y: number; w: number; h: number },
  b: { x: number; y: number; w: number; h: number },
): boolean {
  return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
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

      // Render block for any system with iHub or Skyhook (even if ADM is null)
      if (!hasIhub && !hasSkyhook) continue;

      result.push({ systemId: system.systemId, name: system.name, x: sx, y: sy, offsetY: 0, ihubAdm, hasTcu, hasSkyhook });
    }

    // Collision avoidance: sort by x, then shift overlapping labels down
    result.sort((a, b) => a.x - b.x);

    // Estimated block dimensions for collision detection
    // Use conservative char width estimate (~0.62em of larger font)
    const estCharW = (isMobile ? 9 : 8) * (isZoomed ? 1.3 : 1.0) * 0.62;
    const estPadX = 4;
    const estBlockOffsetY = 4;
    const estFontName = Math.round((isMobile ? 9 : 8) * (isZoomed ? 1.3 : 1.0));
    const estFontAdm = Math.round((isMobile ? 8 : 7) * (isZoomed ? 1.3 : 1.0));
    const estLineH1 = estFontName + 3;
    const estLineH2 = estFontAdm + 3;
    const estPadY = 2;
    const estRowGap = 1;
    const estFullH = estPadY + estLineH1 + estRowGap + estLineH2 + estPadY;
    const collisionGap = 2;

    const placed: { x: number; y: number; w: number; h: number }[] = [];

    for (const m of result) {
      const w = m.name.length * estCharW + estPadX * 2;
      let curY = m.y + estBlockOffsetY + m.offsetY;
      const rect = { x: m.x - w / 2, y: curY, w, h: estFullH };

      // Shift down until no overlap
      let maxAttempts = 10;
      while (maxAttempts-- > 0) {
        const hasOverlap = placed.some((p) => rectsOverlap(rect, p));
        if (!hasOverlap) break;
        rect.y += estFullH + collisionGap;
      }

      m.offsetY = rect.y - (m.y + estBlockOffsetY);
      placed.push(rect);
    }

    return result;
  }, [structures, systems, viewport, isMobile, isZoomed]);

  if (markers.length === 0) return null;

  // Font sizes: readable but compact
  const baseFontName = isMobile ? 9 : 8;
  const baseFontAdm = isMobile ? 8 : 7;
  const fontScale = isZoomed ? 1.3 : 1.0;
  const fontName = Math.round(baseFontName * fontScale);
  const fontAdm = Math.round(baseFontAdm * fontScale);

  // Layout constants
  const lineH1 = fontName + 3; // row 1 height (name)
  const lineH2 = fontAdm + 3;  // row 2 height (ADM)
  const padX = 4;
  const padY = 2;
  const rowGap = 1;
  const blockH = padY + lineH1 + rowGap + lineH2 + padY;
  // Char width estimate for monospace (~0.6em)
  const charW = fontName * 0.62;
  const charWAdm = fontAdm * 0.62;

  // Position: covers the canvas label area (canvas label is at ~y+11, 9px font)
  // Canvas labels are suppressed for sov systems, so this block replaces them
  const blockOffsetY = 4;

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

        // Build row 2 text parts (may be empty for iHub with null ADM)
        const admText = hasAdm ? `ADM ${m.ihubAdm!.toFixed(1)}` : '';
        const skyText = hasSky ? 'S' : '';
        const row2Text = [admText, skyText].filter(Boolean).join('  ');
        const hasRow2 = row2Text.length > 0;

        // Calculate widths
        const nameW = m.name.length * charW;
        const row2W = hasRow2 ? row2Text.length * charWAdm : 0;
        const contentW = Math.max(nameW, row2W);
        const blockW = contentW + padX * 2;
        const thisBlockH = hasRow2 ? blockH : padY + lineH1 + padY;

        const bx = m.x - blockW / 2;
        const by = m.y + blockOffsetY + m.offsetY;

        // Text positions (vertically centered in each row)
        const nameY = by + padY + lineH1 / 2 + fontName * 0.35;
        const admY = by + padY + lineH1 + rowGap + lineH2 / 2 + fontAdm * 0.35;

        return (
          <g key={m.systemId}>
            {/* Dark opaque background block */}
            <rect
              x={bx}
              y={by}
              width={blockW}
              height={thisBlockH}
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
              fontFamily="monospace"
            >
              {m.name}
            </text>
            {/* Row 2: ADM level + Skyhook (only if data exists) */}
            {hasRow2 && (
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
            )}
          </g>
        );
      })}
    </svg>
  );
});

export default SovStructuresOverlay;
