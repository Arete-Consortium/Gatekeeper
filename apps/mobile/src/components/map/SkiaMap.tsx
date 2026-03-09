/**
 * Main Skia Canvas map with pan/zoom gesture handling.
 * Renders gates, systems, route overlay, and labels in world coordinates.
 */
import React, { useCallback, useEffect, useImperativeHandle, useMemo, useRef, useState, forwardRef } from 'react';
import { View, StyleSheet, useWindowDimensions } from 'react-native';
import { Canvas, Group } from '@shopify/react-native-skia';
import {
  Gesture,
  GestureDetector,
  GestureHandlerRootView,
} from 'react-native-gesture-handler';
import { MapSystems } from './MapSystems';
import type { ColorMode } from './MapSystems';
import { MapGates } from './MapGates';
import { MapRouteOverlay } from './MapRouteOverlay';
import { MapLabels } from './MapLabels';
import { MapKillActivity } from './MapKillActivity';
import type { MapNode, MapEdge, MapViewport, RegionCentroid, ConstellationCentroid } from './types';
import type { RouteHop } from '../../types';
import { SpatialIndex } from '../../utils/SpatialIndex';
import { screenToWorld, getVisibleWorldRect } from '../../utils/mapProjection';
import { animateViewport } from '../../utils/animateViewport';
import { THEME } from '../../config';

const MIN_ZOOM = 0.02;
const MAX_ZOOM = 8;
const TAP_RADIUS_SCREEN = 30; // pixels

interface SkiaMapProps {
  nodes: MapNode[];
  edges: MapEdge[];
  spatialIndex: SpatialIndex;
  regionCentroids: RegionCentroid[];
  constellationCentroids?: ConstellationCentroid[];
  colorMode?: ColorMode;
  hotSystems?: Map<string, number>;
  route?: RouteHop[];
  systemNameMap: Map<string, MapNode>;
  onSystemTap?: (system: MapNode) => void;
}

export interface SkiaMapHandle {
  focusSystem: (x: number, y: number, zoom?: number) => void;
  fitBounds: (minX: number, minY: number, maxX: number, maxY: number) => void;
}

export const SkiaMap = forwardRef<SkiaMapHandle, SkiaMapProps>(function SkiaMap({
  nodes,
  edges,
  spatialIndex,
  regionCentroids,
  constellationCentroids,
  colorMode = 'security',
  hotSystems,
  route,
  systemNameMap,
  onSystemTap,
}, ref) {
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

  // Track active animation so we can cancel on new gesture
  const cancelAnimation = useRef<(() => void) | null>(null);

  function animateTo(target: { centerX: number; centerY: number; zoom: number }) {
    cancelAnimation.current?.();
    cancelAnimation.current = animateViewport(setViewport, target);
  }

  // Expose imperative focus and fitBounds methods
  useImperativeHandle(ref, () => ({
    focusSystem(x: number, y: number, zoom = 3) {
      animateTo({ centerX: x, centerY: y, zoom });
    },
    fitBounds(minX: number, minY: number, maxX: number, maxY: number) {
      const cx = (minX + maxX) / 2;
      const cy = (minY + maxY) / 2;
      const width = maxX - minX || 1;
      const height = maxY - minY || 1;
      const padding = 1.2;
      const zoomX = screenWidth / (width * padding);
      const zoomY = screenHeight / (height * padding);
      const zoom = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, Math.min(zoomX, zoomY)));
      animateTo({ centerX: cx, centerY: cy, zoom });
    },
  }));

  // Track gesture state with refs for smooth updates
  const panStartCenter = useRef({ x: viewport.centerX, y: viewport.centerY });
  const pinchStartZoom = useRef(viewport.zoom);

  // Pan gesture
  const panGesture = Gesture.Pan()
    .onStart(() => {
      cancelAnimation.current?.();
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
      cancelAnimation.current?.();
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

  // Double-tap to zoom in, centering on tap point (animated)
  const doubleTapGesture = Gesture.Tap()
    .numberOfTaps(2)
    .onEnd((e) => {
      const { wx, wy } = screenToWorld(e.x, e.y, viewport);
      animateTo({
        centerX: wx,
        centerY: wy,
        zoom: Math.min(MAX_ZOOM, viewport.zoom * 2.5),
      });
    });

  const composedGesture = Gesture.Simultaneous(
    panGesture,
    pinchGesture,
    Gesture.Exclusive(doubleTapGesture, tapGesture)
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

  // Pulse animation for kill activity (0→1 sawtooth, ~2s period)
  const [pulsePhase, setPulsePhase] = useState(0);
  const hasHotSystems = hotSystems && hotSystems.size > 0;
  useEffect(() => {
    if (!hasHotSystems) return;
    let rafId: number;
    let start: number | null = null;
    function tick(ts: number) {
      if (start === null) start = ts;
      setPulsePhase(((ts - start) % 2000) / 2000);
      rafId = requestAnimationFrame(tick);
    }
    rafId = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafId);
  }, [hasHotSystems]);

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
              <MapSystems nodes={visibleNodes} zoom={viewport.zoom} colorMode={colorMode} />
              {hasHotSystems && (
                <MapKillActivity
                  nodes={visibleNodes}
                  hotSystems={hotSystems!}
                  zoom={viewport.zoom}
                  pulsePhase={pulsePhase}
                />
              )}
              {route && route.length > 1 && (
                <MapRouteOverlay
                  route={route}
                  systemNameMap={systemNameMap}
                  zoom={viewport.zoom}
                />
              )}
              <MapLabels
                regions={regionCentroids}
                constellations={constellationCentroids}
                viewport={viewport}
                visibleNodes={visibleNodes}
              />
            </Group>
          </Canvas>
        </View>
      </GestureDetector>
    </GestureHandlerRootView>
  );
});

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: THEME.colors.background,
  },
  canvas: {
    flex: 1,
  },
});
