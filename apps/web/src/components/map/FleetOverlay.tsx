'use client';

import React, { useMemo } from 'react';
import type { MapSystem, MapViewport } from './types';
import type { FleetMember } from '@/lib/types';

// Color palette for fleet members — distinct, readable on dark background
const FLEET_COLORS = [
  '#f59e0b', // amber
  '#10b981', // emerald
  '#f43f5e', // rose
  '#8b5cf6', // violet
  '#06b6d4', // cyan
  '#ec4899', // pink
  '#84cc16', // lime
  '#f97316', // orange
  '#6366f1', // indigo
  '#14b8a6', // teal
];

interface FleetOverlayProps {
  members: FleetMember[];
  systems: Map<number, MapSystem>;
  viewport: MapViewport;
  /** Character ID of the current user (to skip — already rendered by CharacterMarker) */
  currentCharacterId?: number;
}

export const FleetOverlay = React.memo(function FleetOverlay({
  members,
  systems,
  viewport,
  currentCharacterId,
}: FleetOverlayProps) {
  const markers = useMemo(() => {
    const result: {
      member: FleetMember;
      x: number;
      y: number;
      color: string;
    }[] = [];

    let colorIndex = 0;
    for (const member of members) {
      // Skip current user (already shown by CharacterMarker)
      if (currentCharacterId && member.character_id === currentCharacterId) continue;
      // Skip members without location
      if (!member.system_id) continue;

      const system = systems.get(member.system_id);
      if (!system) continue;

      const x = (system.x - viewport.x) * viewport.zoom + viewport.width / 2;
      const y = (system.y - viewport.y) * viewport.zoom + viewport.height / 2;

      // Cull off-screen
      if (x < -50 || x > viewport.width + 50 || y < -50 || y > viewport.height + 50) {
        colorIndex++;
        continue;
      }

      result.push({
        member,
        x,
        y,
        color: FLEET_COLORS[colorIndex % FLEET_COLORS.length],
      });
      colorIndex++;
    }

    return result;
  }, [members, systems, viewport, currentCharacterId]);

  if (markers.length === 0) return null;

  return (
    <svg
      className="absolute inset-0 pointer-events-none"
      width={viewport.width}
      height={viewport.height}
      style={{ zIndex: 9 }}
    >
      <defs>
        <filter id="fleet-glow">
          <feGaussianBlur stdDeviation="3" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      {markers.map(({ member, x, y, color }) => (
        <g key={member.character_id} className="pointer-events-auto">
          {/* Outer ring */}
          <circle
            cx={x}
            cy={y}
            r={7}
            fill="none"
            stroke={color}
            strokeWidth={1.5}
            opacity={0.5}
            filter="url(#fleet-glow)"
          />
          {/* Solid dot */}
          <circle cx={x} cy={y} r={4} fill={color} stroke="#0a0e17" strokeWidth={1} />
          {/* Tooltip trigger (invisible larger circle for hover) */}
          <circle cx={x} cy={y} r={12} fill="transparent">
            <title>
              {member.character_name}
              {member.ship_type_name ? ` — ${member.ship_type_name}` : ''}
              {member.system_name ? ` (${member.system_name})` : ''}
            </title>
          </circle>
          {/* Label at sufficient zoom */}
          {viewport.zoom > 1 && (
            <>
              <rect
                x={x + 10}
                y={y - 8}
                width={member.character_name.length * 5.5 + 8}
                height={16}
                rx={3}
                fill="rgba(0,0,0,0.85)"
              />
              <text
                x={x + 14}
                y={y + 4}
                fill={color}
                fontSize={10}
                fontFamily="monospace"
                fontWeight="bold"
              >
                {member.character_name}
              </text>
            </>
          )}
        </g>
      ))}
    </svg>
  );
});

export default FleetOverlay;
