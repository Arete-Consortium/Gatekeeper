'use client';

import React, { useMemo } from 'react';
import type { MapSystem, MapViewport } from './types';
import type { PirateOccupiedSystem } from '@/lib/types';

interface PirateInsurgencyOverlayProps {
  systems: Map<number, MapSystem>;
  viewport: MapViewport;
  pirateOccupied: PirateOccupiedSystem[];
}

/** Color by pirate faction. */
function factionColor(factionId: number): string {
  switch (factionId) {
    case 500010: // Guristas Pirates
      return '#22d3ee'; // cyan-400
    case 500011: // Angel Cartel
      return '#f87171'; // red-400
    default:
      return '#ef4444'; // red-500
  }
}

interface PirateMarker {
  key: string;
  x: number;
  y: number;
  color: string;
  factionName: string;
  systemName: string;
}

/**
 * Renders pirate insurgency markers on the map.
 * Systems with pirate faction occupation have security suppressed to
 * effectively nullsec-level danger. Shows a red dashed ring with
 * skull icon and "SUPPRESSED" label at higher zoom.
 */
export const PirateInsurgencyOverlay = React.memo(function PirateInsurgencyOverlay({
  systems,
  viewport,
  pirateOccupied,
}: PirateInsurgencyOverlayProps) {
  const markers = useMemo(() => {
    const result: PirateMarker[] = [];

    for (const occ of pirateOccupied) {
      const system = systems.get(occ.system_id);
      if (!system) continue;

      const x = (system.x - viewport.x) * viewport.zoom + viewport.width / 2;
      const y = (system.y - viewport.y) * viewport.zoom + viewport.height / 2;

      // Cull off-screen markers
      if (x < -40 || x > viewport.width + 40 || y < -40 || y > viewport.height + 40) {
        continue;
      }

      result.push({
        key: `pirate-${occ.system_id}`,
        x,
        y,
        color: factionColor(occ.occupier_faction_id),
        factionName: occ.faction_name,
        systemName: occ.system_name,
      });
    }

    return result;
  }, [pirateOccupied, systems, viewport]);

  if (markers.length === 0) return null;

  return (
    <svg
      className="absolute inset-0 pointer-events-none"
      width={viewport.width}
      height={viewport.height}
      style={{ zIndex: 4 }}
    >
      <defs>
        <filter id="pirate-glow">
          <feGaussianBlur stdDeviation="2.5" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {markers.map((m) => (
        <g key={m.key}>
          {/* Outer pulsing dashed ring */}
          <circle
            cx={m.x}
            cy={m.y}
            r={12}
            fill="none"
            stroke={m.color}
            strokeWidth={1.5}
            strokeDasharray="4 3"
            opacity={0.5}
            filter="url(#pirate-glow)"
          >
            <animate
              attributeName="r"
              values="10;15;10"
              dur="2.5s"
              repeatCount="indefinite"
            />
            <animate
              attributeName="opacity"
              values="0.5;0.15;0.5"
              dur="2.5s"
              repeatCount="indefinite"
            />
          </circle>

          {/* Inner steady dashed ring */}
          <circle
            cx={m.x}
            cy={m.y}
            r={8}
            fill="none"
            stroke={m.color}
            strokeWidth={1}
            strokeDasharray="3 2"
            opacity={0.7}
          />

          {/* Skull crossbones icon (simplified) */}
          {/* Skull circle */}
          <circle
            cx={m.x}
            cy={m.y - 1}
            r={3.5}
            fill={m.color}
            opacity={0.85}
          />
          {/* Eyes */}
          <circle cx={m.x - 1.2} cy={m.y - 1.5} r={0.8} fill="#0a0e17" />
          <circle cx={m.x + 1.2} cy={m.y - 1.5} r={0.8} fill="#0a0e17" />
          {/* Crossbones — two small diagonal lines */}
          <line
            x1={m.x - 3} y1={m.y + 2.5}
            x2={m.x + 3} y2={m.y + 5}
            stroke={m.color} strokeWidth={1} opacity={0.7}
          />
          <line
            x1={m.x + 3} y1={m.y + 2.5}
            x2={m.x - 3} y2={m.y + 5}
            stroke={m.color} strokeWidth={1} opacity={0.7}
          />

          {/* "SUPPRESSED" label (visible at zoom > 0.6) */}
          {viewport.zoom > 0.6 && (
            <>
              <text
                x={m.x}
                y={m.y - 16}
                textAnchor="middle"
                fill={m.color}
                fontSize={8}
                fontWeight="bold"
                opacity={0.9}
              >
                SUPPRESSED
              </text>
              {/* Faction name at higher zoom */}
              {viewport.zoom > 1.2 && (
                <text
                  x={m.x}
                  y={m.y + 18}
                  textAnchor="middle"
                  fill={m.color}
                  fontSize={7}
                  opacity={0.6}
                >
                  {m.factionName}
                </text>
              )}
            </>
          )}
        </g>
      ))}
    </svg>
  );
});

export default PirateInsurgencyOverlay;
