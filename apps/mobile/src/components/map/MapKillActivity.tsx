/**
 * Pulsing circles on systems with recent kill activity.
 * Intensity scales with kill count.
 */
import React from 'react';
import { Circle, Group } from '@shopify/react-native-skia';
import type { MapNode } from './types';

interface MapKillActivityProps {
  /** Visible nodes to check against hot systems */
  nodes: MapNode[];
  /** Map of system_name → recent_kills */
  hotSystems: Map<string, number>;
  zoom: number;
  /** 0-1 pulse phase from animation clock */
  pulsePhase: number;
}

const MAX_KILLS_FOR_SCALE = 30;
const PULSE_COLOR = 'rgba(255, 69, 58, '; // riskRed base

export const MapKillActivity = React.memo(function MapKillActivity({
  nodes,
  hotSystems,
  zoom,
  pulsePhase,
}: MapKillActivityProps) {
  if (hotSystems.size === 0) return null;

  const baseRadius = 4 / Math.sqrt(zoom);

  return (
    <Group>
      {nodes.map((node) => {
        const kills = hotSystems.get(node.name);
        if (!kills) return null;

        // Scale intensity by kill count (capped)
        const intensity = Math.min(kills / MAX_KILLS_FOR_SCALE, 1);
        // Pulsing radius oscillates between 1x and 2x base
        const pulseScale = 1 + pulsePhase * (0.5 + intensity * 0.5);
        const radius = baseRadius * pulseScale * (0.6 + intensity * 0.4);
        // Opacity fades as pulse expands
        const opacity = (0.3 + intensity * 0.4) * (1 - pulsePhase * 0.6);

        return (
          <Circle
            key={`kill-${node.systemId}`}
            cx={node.x}
            cy={node.y}
            r={radius}
            color={`${PULSE_COLOR}${opacity.toFixed(2)})`}
          />
        );
      })}
    </Group>
  );
});
