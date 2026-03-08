/**
 * Renders gate connections as a single batched Skia Path.
 */
import React from 'react';
import { Path, Skia } from '@shopify/react-native-skia';
import type { MapEdge } from './types';

interface MapGatesProps {
  edges: MapEdge[];
}

export const MapGates = React.memo(function MapGates({ edges }: MapGatesProps) {
  if (edges.length === 0) return null;

  const path = Skia.Path.Make();
  for (const edge of edges) {
    path.moveTo(edge.fromX, edge.fromY);
    path.lineTo(edge.toX, edge.toY);
  }

  return (
    <Path
      path={path}
      color="rgba(255, 255, 255, 0.12)"
      style="stroke"
      strokeWidth={0.3}
    />
  );
});
