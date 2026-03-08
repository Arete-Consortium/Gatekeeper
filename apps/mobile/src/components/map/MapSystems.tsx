/**
 * Renders visible systems as colored Skia circles.
 */
import React from 'react';
import { Circle, Group } from '@shopify/react-native-skia';
import type { MapNode } from './types';
import { THEME } from '../../config';

interface MapSystemsProps {
  nodes: MapNode[];
  zoom: number;
}

function getSecurityColor(security: number): string {
  if (security >= 0.5) return THEME.colors.highSec;
  if (security > 0.0) return THEME.colors.lowSec;
  return THEME.colors.nullSec;
}

/** Base radius in world units — scales with zoom for consistent screen size */
const BASE_RADIUS = 2;

export const MapSystems = React.memo(function MapSystems({
  nodes,
  zoom,
}: MapSystemsProps) {
  // Radius shrinks as you zoom in so dots stay consistent on screen
  const radius = BASE_RADIUS / Math.sqrt(zoom);

  return (
    <Group>
      {nodes.map((node) => (
        <Circle
          key={node.systemId}
          cx={node.x}
          cy={node.y}
          r={radius}
          color={getSecurityColor(node.security)}
        />
      ))}
    </Group>
  );
});
