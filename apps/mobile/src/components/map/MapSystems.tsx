/**
 * Renders visible systems as colored Skia circles.
 * Supports security-color and risk-color modes.
 */
import React from 'react';
import { Circle, Group } from '@shopify/react-native-skia';
import type { MapNode } from './types';
import { THEME } from '../../config';

export type ColorMode = 'security' | 'risk';

interface MapSystemsProps {
  nodes: MapNode[];
  zoom: number;
  colorMode?: ColorMode;
}

function getSecurityColor(security: number): string {
  if (security >= 0.5) return THEME.colors.highSec;
  if (security > 0.0) return THEME.colors.lowSec;
  return THEME.colors.nullSec;
}

function getNodeColor(node: MapNode, mode: ColorMode): string {
  if (mode === 'risk' && node.riskColor) return node.riskColor;
  return getSecurityColor(node.security);
}

/** Base radius in world units — scales with zoom for consistent screen size */
const BASE_RADIUS = 2;

export const MapSystems = React.memo(function MapSystems({
  nodes,
  zoom,
  colorMode = 'security',
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
          color={getNodeColor(node, colorMode)}
        />
      ))}
    </Group>
  );
});
