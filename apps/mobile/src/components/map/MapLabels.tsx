/**
 * Zoom-level-aware labels rendered via Skia Text.
 * Far zoom: region names. Mid zoom: constellation names. Close zoom: system names.
 */
import React from 'react';
import { Text, useFont } from '@shopify/react-native-skia';
import type { MapNode, RegionCentroid, ConstellationCentroid, MapViewport } from './types';
import { getVisibleWorldRect } from '../../utils/mapProjection';

const CONSTELLATION_ZOOM_MIN = 0.3;
const SYSTEM_LABEL_ZOOM = 1.5;
const MAX_SYSTEM_LABELS = 100;

interface MapLabelsProps {
  regions: RegionCentroid[];
  constellations?: ConstellationCentroid[];
  viewport: MapViewport;
  visibleNodes?: MapNode[];
}

export const MapLabels = React.memo(function MapLabels({
  regions,
  constellations,
  viewport,
  visibleNodes,
}: MapLabelsProps) {
  const regionFont = useFont(null, 14 / viewport.zoom);
  const constFont = useFont(null, 10 / viewport.zoom);
  const systemFont = useFont(null, 8 / viewport.zoom);

  const visible = getVisibleWorldRect(viewport);
  const showSystemLabels = viewport.zoom >= SYSTEM_LABEL_ZOOM;
  const showConstellationLabels =
    viewport.zoom >= CONSTELLATION_ZOOM_MIN && viewport.zoom < SYSTEM_LABEL_ZOOM;
  const showRegionLabels = viewport.zoom < CONSTELLATION_ZOOM_MIN;

  function isInView(x: number, y: number): boolean {
    return x >= visible.minX && x <= visible.maxX && y >= visible.minY && y <= visible.maxY;
  }

  return (
    <>
      {/* Region labels at far zoom */}
      {showRegionLabels &&
        regionFont &&
        regions.map((region) => {
          if (!isInView(region.x, region.y)) return null;
          return (
            <Text
              key={region.regionId}
              x={region.x}
              y={region.y}
              text={region.name}
              font={regionFont}
              color="rgba(255, 255, 255, 0.4)"
            />
          );
        })}

      {/* Constellation labels at mid zoom */}
      {showConstellationLabels &&
        constFont &&
        constellations &&
        constellations.map((c) => {
          if (!isInView(c.x, c.y)) return null;
          return (
            <Text
              key={c.constellationId}
              x={c.x}
              y={c.y}
              text={c.name}
              font={constFont}
              color="rgba(255, 255, 255, 0.3)"
            />
          );
        })}

      {/* System name labels at close zoom */}
      {showSystemLabels &&
        systemFont &&
        visibleNodes &&
        visibleNodes.slice(0, MAX_SYSTEM_LABELS).map((node) => (
          <Text
            key={node.systemId}
            x={node.x}
            y={node.y - 6 / viewport.zoom}
            text={node.name}
            font={systemFont}
            color="rgba(255, 255, 255, 0.7)"
          />
        ))}
    </>
  );
});
