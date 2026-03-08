/**
 * Main Skia Canvas map with pan/zoom gesture handling.
 * Renders gates, systems, route overlay, and labels in world coordinates.
 */
import React, { useCallback, useMemo, useRef, useState } from 'react';
import { View, StyleSheet, useWindowDimensions } from 'react-native';
import { Canvas, Group } from '@shopify/react-native-skia';
import {
  Gesture,
  GestureDetector,
  GestureHandlerRootView,
} from 'react-native-gesture-handler';
import { MapSystems } from './MapSystems';
import { MapGates } from './MapGates';
import { MapRouteOverlay } from './MapRouteOverlay';
import { MapLabels } from './MapLabels';
import type { MapNode, MapEdge, MapViewport, RegionCentroid } from './types';
import type { RouteHop } from '../../types';
import { SpatialIndex } from '../../utils/SpatialIndex';
import { screenToWorld, getVisibleWorldRect } from '../../utils/mapProjection';
import { THEME } from '../../config';

const MIN_ZOOM = 0.02;
const MAX_ZOOM = 8;
const TAP_RADIUS_SCREEN = 30; // pixels

interface SkiaMapProps {
  nodes: MapNode[];
  edges: MapEdge[];
  spatialIndex: SpatialIndex;
  regionCentroids: RegionCentroid[];
  route?: RouteHop[];
  systemNameMap: Map<string, MapNode>;
  onSystemTap?: (system: MapNode) => void;
}

export function SkiaMap({
  nodes,
  edges,
  spatialIndex,
  regionCentroids,
  route,
  systemNameMap,
  onSystemTap,
}: SkiaMapProps) {
  const { width: screenWidth, height: screenHeight } = useWindowDimensions();
  const bounds = spatialIndex.getBounds();

  // Initialize viewport centered on the universe
  const [viewport, setViewport] = useState<MapViewport>(() => {
    // Fit the universe into the screen
    const scaleX = screenWidth / bounds.width;
    const scaleY = screenHeight / bounds.height;
    const initialZoom = Math.min(scaleX, scaleY) * 0.9;
    return {
      centerX: bounds.centerX,
      centerY: bounds.centerY,
      zoom: initialZoom,
      screenWidth,
      screenHeight,
    };
  });

  // Track gesture state with refs for smooth updates
  const panStartCenter = useRef({ x: viewport.centerX, y: viewport.centerY });
  const pinchStartZoom = useRef(viewport.zoom);

  // Pan gesture
  const panGesture = Gesture.Pan()
    .onStart(() => {
      panStartCenter.current = {
        x: viewport.centerX,
        y: viewport.centerY,
      };
    })
    .onUpdate((e) => {
      setViewport((prev) => ({
        ...prev,
        centerX: panStartCenter.current.x - e.translationX / prev.zoom,
        centerY: panStartCenter.current.y - e.translationY / prev.zoom,
      }));
    })
    .minPointers(1)
    .maxPointers(2);

  // Pinch gesture
  const pinchGesture = Gesture.Pinch()
    .onStart(() => {
      pinchStartZoom.current = viewport.zoom;
    })
    .onUpdate((e) => {
      const newZoom = Math.min(
        MAX_ZOOM,
        Math.max(MIN_ZOOM, pinchStartZoom.current * e.scale)
      );
      setViewport((prev) => ({
        ...prev,
        zoom: newZoom,
      }));
    });

  // Tap gesture for system selection
  const tapGesture = Gesture.Tap().onEnd((e) => {
    if (!onSystemTap) return;
    const { wx, wy } = screenToWorld(e.x, e.y, viewport);
    const tapRadius = TAP_RADIUS_SCREEN / viewport.zoom;
    const nearest = spatialIndex.findNearest(wx, wy, tapRadius);
    if (nearest) {
      onSystemTap(nearest);
    }
  });

  const composedGesture = Gesture.Simultaneous(
    panGesture,
    pinchGesture,
    tapGesture
  );

  // Viewport culling
  const { visibleNodes, visibleEdges } = useMemo(() => {
    const rect = getVisibleWorldRect(viewport);
    // Add margin for edges that cross the viewport boundary
    const margin = 50 / viewport.zoom;
    const visNodes = spatialIndex.queryRect(
      rect.minX - margin,
      rect.minY - margin,
      rect.maxX + margin,
      rect.maxY + margin
    );

    // Filter edges: include if either endpoint is in the visible set
    const visibleNames = new Set(visNodes.map((n) => n.name));
    const visEdges = edges.filter(
      (e) => visibleNames.has(e.fromName) || visibleNames.has(e.toName)
    );

    return { visibleNodes: visNodes, visibleEdges: visEdges };
  }, [viewport.centerX, viewport.centerY, viewport.zoom, spatialIndex, edges]);

  // Transform: translate so centerX/centerY maps to screen center, then scale
  const translateX = screenWidth / 2 - viewport.centerX * viewport.zoom;
  const translateY = screenHeight / 2 - viewport.centerY * viewport.zoom;

  return (
    <GestureHandlerRootView style={styles.container}>
      <GestureDetector gesture={composedGesture}>
        <View style={styles.container}>
          <Canvas style={styles.canvas}>
            <Group
              transform={[
                { translateX },
                { translateY },
                { scale: viewport.zoom },
              ]}
            >
              <MapGates edges={visibleEdges} />
              <MapSystems nodes={visibleNodes} zoom={viewport.zoom} />
              {route && route.length > 1 && (
                <MapRouteOverlay
                  route={route}
                  systemNameMap={systemNameMap}
                  zoom={viewport.zoom}
                />
              )}
              <MapLabels regions={regionCentroids} viewport={viewport} />
            </Group>
          </Canvas>
        </View>
      </GestureDetector>
    </GestureHandlerRootView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: THEME.colors.background,
  },
  canvas: {
    flex: 1,
  },
});
