/**
 * Highlighted route path overlay on the map.
 */
import React from 'react';
import { Path, Skia } from '@shopify/react-native-skia';
import type { MapNode } from './types';
import type { RouteHop } from '../../types';
import { THEME } from '../../config';

interface MapRouteOverlayProps {
  route: RouteHop[];
  systemNameMap: Map<string, MapNode>;
  zoom: number;
}

export const MapRouteOverlay = React.memo(function MapRouteOverlay({
  route,
  systemNameMap,
  zoom,
}: MapRouteOverlayProps) {
  if (route.length < 2) return null;

  // Glow layer (wider, lower opacity)
  const glowPath = Skia.Path.Make();
  // Main path
  const mainPath = Skia.Path.Make();

  let started = false;
  for (const hop of route) {
    const node = systemNameMap.get(hop.system_name);
    if (!node) continue;

    if (!started) {
      glowPath.moveTo(node.x, node.y);
      mainPath.moveTo(node.x, node.y);
      started = true;
    } else {
      glowPath.lineTo(node.x, node.y);
      mainPath.lineTo(node.x, node.y);
    }
  }

  if (!started) return null;

  const strokeBase = 1.5 / Math.sqrt(zoom);

  return (
    <>
      <Path
        path={glowPath}
        color={`${THEME.colors.primary}40`}
        style="stroke"
        strokeWidth={strokeBase * 3}
        strokeCap="round"
        strokeJoin="round"
      />
      <Path
        path={mainPath}
        color={THEME.colors.primary}
        style="stroke"
        strokeWidth={strokeBase}
        strokeCap="round"
        strokeJoin="round"
      />
    </>
  );
});
