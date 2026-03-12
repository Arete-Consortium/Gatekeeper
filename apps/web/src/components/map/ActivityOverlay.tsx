'use client';

import React, { useMemo } from 'react';
import type { MapSystem, MapViewport } from './types';
import type { SystemActivityResponse } from '@/lib/types';

interface ActivityOverlayProps {
  activityData: SystemActivityResponse;
  systems: Map<number, MapSystem>;
  viewport: MapViewport;
}

/**
 * Renders per-system activity indicators on the map.
 * Shows jump traffic as blue rings and kill activity as red pulses.
 */
export const ActivityOverlay = React.memo(function ActivityOverlay({
  activityData,
  systems,
  viewport,
}: ActivityOverlayProps) {
  const markers = useMemo(() => {
    const result: Array<{
      x: number;
      y: number;
      systemId: number;
      jumps: number;
      shipKills: number;
      podKills: number;
      npcKills: number;
      intensity: number;
    }> = [];

    // Merge jump + kill data
    const allSystemIds = new Set([
      ...Object.keys(activityData.jumps || {}),
      ...Object.keys(activityData.kills || {}),
    ]);

    // Find max values for normalization
    let maxActivity = 1;
    for (const sid of allSystemIds) {
      const jumps = activityData.jumps?.[sid] ?? 0;
      const kills = activityData.kills?.[sid];
      const totalKills = kills ? kills.ship_kills + kills.pod_kills : 0;
      maxActivity = Math.max(maxActivity, jumps + totalKills * 5);
    }

    for (const sid of allSystemIds) {
      const system = systems.get(Number(sid));
      if (!system) continue;

      const jumps = activityData.jumps?.[sid] ?? 0;
      const kills = activityData.kills?.[sid];
      const shipKills = kills?.ship_kills ?? 0;
      const podKills = kills?.pod_kills ?? 0;
      const npcKills = kills?.npc_kills ?? 0;

      // Skip systems with no meaningful activity
      if (jumps === 0 && shipKills === 0 && podKills === 0) continue;

      const sx = (system.x - viewport.x) * viewport.zoom + viewport.width / 2;
      const sy = (system.y - viewport.y) * viewport.zoom + viewport.height / 2;

      if (sx < -30 || sx > viewport.width + 30 || sy < -30 || sy > viewport.height + 30) continue;

      const activity = jumps + (shipKills + podKills) * 5;
      const intensity = Math.min(1, activity / maxActivity);

      result.push({ x: sx, y: sy, systemId: system.systemId, jumps, shipKills, podKills, npcKills, intensity });
    }

    return result;
  }, [activityData, systems, viewport]);

  if (markers.length === 0) return null;

  const baseRadius = Math.max(3, Math.min(10, 5 * viewport.zoom));

  return (
    <svg
      className="absolute inset-0 pointer-events-none"
      width={viewport.width}
      height={viewport.height}
      style={{ zIndex: 1 }}
    >
      <defs>
        <radialGradient id="activity-jump">
          <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.6} />
          <stop offset="100%" stopColor="#3b82f6" stopOpacity={0} />
        </radialGradient>
        <radialGradient id="activity-kill">
          <stop offset="0%" stopColor="#ef4444" stopOpacity={0.7} />
          <stop offset="100%" stopColor="#ef4444" stopOpacity={0} />
        </radialGradient>
      </defs>
      {markers.map((m) => {
        const hasKills = m.shipKills + m.podKills > 0;
        const radius = baseRadius * (1 + m.intensity * 2);
        return (
          <g key={m.systemId}>
            {/* Jump traffic ring (blue) */}
            {m.jumps > 0 && (
              <circle
                cx={m.x}
                cy={m.y}
                r={radius}
                fill="url(#activity-jump)"
                opacity={0.3 + m.intensity * 0.4}
              />
            )}
            {/* Kill activity dot (red, on top) */}
            {hasKills && (
              <circle
                cx={m.x}
                cy={m.y}
                r={radius * 0.6}
                fill="url(#activity-kill)"
                opacity={0.4 + m.intensity * 0.5}
              />
            )}
          </g>
        );
      })}
    </svg>
  );
});

export default ActivityOverlay;
