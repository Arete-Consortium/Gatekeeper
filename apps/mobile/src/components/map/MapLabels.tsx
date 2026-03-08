/**
 * Zoom-level-aware region labels rendered via Skia Text.
 */
import React from 'react';
import { Text, useFont } from '@shopify/react-native-skia';
import type { RegionCentroid, MapViewport } from './types';
import { getVisibleWorldRect } from '../../utils/mapProjection';

interface MapLabelsProps {
  regions: RegionCentroid[];
  viewport: MapViewport;
}

export const MapLabels = React.memo(function MapLabels({
  regions,
  viewport,
}: MapLabelsProps) {
  const font = useFont(null, 14 / viewport.zoom);

  // Only show region labels at far zoom
  if (viewport.zoom > 1.5 || !font) return null;

  const visible = getVisibleWorldRect(viewport);

  return (
    <>
      {regions.map((region) => {
        if (
          region.x < visible.minX ||
          region.x > visible.maxX ||
          region.y < visible.minY ||
          region.y > visible.maxY
        ) {
          return null;
        }

        return (
          <Text
            key={region.regionId}
            x={region.x}
            y={region.y}
            text={region.name}
            font={font}
            color="rgba(255, 255, 255, 0.4)"
          />
        );
      })}
    </>
  );
});
