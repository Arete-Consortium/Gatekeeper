'use client';

import React, { useMemo } from 'react';
import type { MapSystem, MapViewport } from './types';

// Alliance color palette — visually distinct colors for major blocs
const ALLIANCE_COLORS: Record<number, string> = {};
const FACTION_COLORS: Record<number, string> = {
  500001: '#c8aa00', // Caldari State
  500002: '#2a7fff', // Minmatar Republic
  500003: '#c83232', // Amarr Empire
  500004: '#1e8c1e', // Gallente Federation
  500010: '#8b5cf6', // Serpentis
  500011: '#ec4899', // Angel Cartel
  500012: '#06b6d4', // Sansha
  500027: '#6b7280', // Unknown (Jove?)
};

// Generate a deterministic color from an ID
function colorFromId(id: number): string {
  const hue = ((id * 137.508) % 360);
  return `hsl(${hue}, 60%, 50%)`;
}

interface SovereigntyOverlayProps {
  sovereignty: Record<string, { alliance_id: number | null; faction_id: number | null }>;
  alliances: Record<string, { name: string }>;
  systems: Map<number, MapSystem>;
  viewport: MapViewport;
  factions: Record<string, { name: string }>;
}

export const SovereigntyOverlay = React.memo(function SovereigntyOverlay({
  sovereignty,
  alliances,
  systems,
  viewport,
  factions,
}: SovereigntyOverlayProps) {
  const markers = useMemo(() => {
    const result: Array<{
      x: number;
      y: number;
      color: string;
      label: string;
      systemId: number;
    }> = [];

    for (const [sidStr, sovInfo] of Object.entries(sovereignty)) {
      const system = systems.get(Number(sidStr));
      if (!system) continue;

      // Only show player sov (alliance-held) — NPC faction sov is implied by security coloring
      if (!sovInfo.alliance_id) continue;

      const sx = (system.x - viewport.x) * viewport.zoom + viewport.width / 2;
      const sy = (system.y - viewport.y) * viewport.zoom + viewport.height / 2;

      if (sx < -20 || sx > viewport.width + 20 || sy < -20 || sy > viewport.height + 20) continue;

      const aid = sovInfo.alliance_id;
      const color = ALLIANCE_COLORS[aid] || colorFromId(aid);
      const allianceInfo = alliances[String(aid)];
      const label = allianceInfo?.name || `Alliance ${aid}`;

      result.push({ x: sx, y: sy, color, label, systemId: system.systemId });
    }

    return result;
  }, [sovereignty, alliances, systems, viewport]);

  if (markers.length === 0) return null;

  // Draw sovereignty as colored rings around systems
  const radius = Math.max(4, Math.min(12, 6 * viewport.zoom));

  return (
    <svg
      className="absolute inset-0 pointer-events-none"
      width={viewport.width}
      height={viewport.height}
      style={{ zIndex: 1 }}
    >
      {markers.map((m) => (
        <circle
          key={m.systemId}
          cx={m.x}
          cy={m.y}
          r={radius}
          fill="none"
          stroke={m.color}
          strokeWidth={1.5}
          opacity={0.6}
        />
      ))}
    </svg>
  );
});

export default SovereigntyOverlay;
