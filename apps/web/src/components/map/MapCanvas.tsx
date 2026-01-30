'use client';

/**
 * MapCanvas - WebGL/Canvas renderer using PixiJS
 * Renders 8000+ system nodes efficiently with viewport culling
 */

import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { Stage, Container, Graphics, Text } from '@pixi/react';
import * as PIXI from 'pixi.js';
import type {
  MapSystem,
  MapGate,
  MapViewport,
  MapRoute,
  MapLayers,
} from './types';
import { getSecurityColor } from './types';
import {
  viewportToBounds,
  worldToScreen,
  screenToWorld,
  clamp,
  type Quadtree,
} from './utils/spatial';

// Rendering constants
const SYSTEM_BASE_RADIUS = 4;
const SYSTEM_SELECTED_RADIUS = 8;
const SYSTEM_HOVER_RADIUS = 6;
const GATE_LINE_WIDTH = 0.5;
const GATE_COLOR = 0x333333;
const ROUTE_LINE_WIDTH = 2;
const LABEL_ZOOM_THRESHOLD = 0.3;
const MIN_ZOOM = 0.02;
const MAX_ZOOM = 5;
const ZOOM_SPEED = 0.001;
const PAN_SPEED = 1;

// Culling margin (render slightly outside viewport for smooth scrolling)
const CULL_MARGIN = 100;

interface MapCanvasProps {
  systems: MapSystem[];
  gates: MapGate[];
  systemMap: Map<number, MapSystem>;
  quadtree: Quadtree | null;
  viewport: MapViewport;
  onViewportChange: (viewport: MapViewport) => void;
  selectedSystem?: number | null;
  hoveredSystem?: number | null;
  highlightedSystems?: Set<number>;
  routes?: MapRoute[];
  layers: MapLayers;
  onSystemClick?: (systemId: number) => void;
  onSystemHover?: (systemId: number | null) => void;
  onBackgroundClick?: () => void;
}

/**
 * Main map canvas component
 */
export function MapCanvas({
  systems,
  gates,
  systemMap,
  quadtree,
  viewport,
  onViewportChange,
  selectedSystem,
  hoveredSystem,
  highlightedSystems,
  routes,
  layers,
  onSystemClick,
  onSystemHover,
  onBackgroundClick,
}: MapCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const isDragging = useRef(false);
  const lastMousePos = useRef({ x: 0, y: 0 });

  // Get visible systems using quadtree for efficient culling
  const visibleSystems = useMemo(() => {
    if (!quadtree) return systems;

    const bounds = viewportToBounds(viewport);
    // Add margin for smooth scrolling
    bounds.x -= CULL_MARGIN / viewport.zoom;
    bounds.y -= CULL_MARGIN / viewport.zoom;
    bounds.width += (CULL_MARGIN * 2) / viewport.zoom;
    bounds.height += (CULL_MARGIN * 2) / viewport.zoom;

    return quadtree.query(bounds);
  }, [quadtree, systems, viewport]);

  // Get visible gates (only between visible systems)
  const visibleGates = useMemo(() => {
    if (!layers.showGates) return [];

    const visibleIds = new Set(visibleSystems.map((s) => s.systemId));
    return gates.filter(
      (gate) =>
        visibleIds.has(gate.fromSystemId) && visibleIds.has(gate.toSystemId)
    );
  }, [gates, visibleSystems, layers.showGates]);

  // Handle mouse wheel zoom
  const handleWheel = useCallback(
    (e: WheelEvent) => {
      e.preventDefault();

      const rect = containerRef.current?.getBoundingClientRect();
      if (!rect) return;

      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      // Get world position under mouse before zoom
      const worldBefore = screenToWorld(mouseX, mouseY, viewport);

      // Calculate new zoom
      const delta = -e.deltaY * ZOOM_SPEED;
      const newZoom = clamp(viewport.zoom * (1 + delta), MIN_ZOOM, MAX_ZOOM);

      // Calculate new viewport position to keep mouse position stable
      const newViewport: MapViewport = {
        ...viewport,
        zoom: newZoom,
      };

      // Get world position under mouse after zoom
      const worldAfter = screenToWorld(mouseX, mouseY, newViewport);

      // Adjust viewport to compensate
      onViewportChange({
        ...newViewport,
        x: viewport.x + (worldBefore.x - worldAfter.x),
        y: viewport.y + (worldBefore.y - worldAfter.y),
      });
    },
    [viewport, onViewportChange]
  );

  // Handle mouse down for panning
  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (e.button === 0) {
        isDragging.current = true;
        lastMousePos.current = { x: e.clientX, y: e.clientY };
      }
    },
    []
  );

  // Handle mouse move for panning and hover
  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      const rect = containerRef.current?.getBoundingClientRect();
      if (!rect) return;

      if (isDragging.current) {
        const dx = (e.clientX - lastMousePos.current.x) * PAN_SPEED;
        const dy = (e.clientY - lastMousePos.current.y) * PAN_SPEED;

        onViewportChange({
          ...viewport,
          x: viewport.x - dx / viewport.zoom,
          y: viewport.y - dy / viewport.zoom,
        });

        lastMousePos.current = { x: e.clientX, y: e.clientY };
      } else if (onSystemHover && quadtree) {
        // Find system under mouse
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;
        const worldPos = screenToWorld(mouseX, mouseY, viewport);

        // Search radius in world coordinates
        const searchRadius = 20 / viewport.zoom;
        const nearest = quadtree.findNearest(
          worldPos.x,
          worldPos.y,
          searchRadius
        );

        onSystemHover(nearest?.systemId ?? null);
      }
    },
    [viewport, onViewportChange, onSystemHover, quadtree]
  );

  // Handle mouse up
  const handleMouseUp = useCallback(() => {
    isDragging.current = false;
  }, []);

  // Handle click
  const handleClick = useCallback(
    (e: React.MouseEvent) => {
      const rect = containerRef.current?.getBoundingClientRect();
      if (!rect) return;

      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;
      const worldPos = screenToWorld(mouseX, mouseY, viewport);

      if (quadtree) {
        const searchRadius = 20 / viewport.zoom;
        const nearest = quadtree.findNearest(
          worldPos.x,
          worldPos.y,
          searchRadius
        );

        if (nearest && onSystemClick) {
          onSystemClick(nearest.systemId);
        } else if (onBackgroundClick) {
          onBackgroundClick();
        }
      }
    },
    [viewport, quadtree, onSystemClick, onBackgroundClick]
  );

  // Add wheel listener
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    container.addEventListener('wheel', handleWheel, { passive: false });
    return () => container.removeEventListener('wheel', handleWheel);
  }, [handleWheel]);

  // Stage options for PixiJS
  const stageOptions = useMemo(
    () => ({
      backgroundColor: 0x000000,
      antialias: true,
      resolution: window.devicePixelRatio || 1,
      autoDensity: true,
    }),
    []
  );

  return (
    <div
      ref={containerRef}
      className="w-full h-full cursor-grab active:cursor-grabbing"
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      onClick={handleClick}
    >
      <Stage
        width={viewport.width}
        height={viewport.height}
        options={stageOptions}
      >
        <Container>
          {/* Gate connections layer */}
          {layers.showGates && (
            <GatesLayer
              gates={visibleGates}
              systemMap={systemMap}
              viewport={viewport}
            />
          )}

          {/* Route overlay layer */}
          {layers.showRoute && routes && routes.length > 0 && (
            <RoutesLayer
              routes={routes}
              systemMap={systemMap}
              viewport={viewport}
            />
          )}

          {/* System nodes layer */}
          <SystemsLayer
            systems={visibleSystems}
            viewport={viewport}
            selectedSystem={selectedSystem}
            hoveredSystem={hoveredSystem}
            highlightedSystems={highlightedSystems}
          />

          {/* Labels layer (only at higher zoom levels) */}
          {layers.showLabels && viewport.zoom >= LABEL_ZOOM_THRESHOLD && (
            <LabelsLayer systems={visibleSystems} viewport={viewport} />
          )}
        </Container>
      </Stage>
    </div>
  );
}

/**
 * Gates layer - draws lines between connected systems
 */
interface GatesLayerProps {
  gates: MapGate[];
  systemMap: Map<number, MapSystem>;
  viewport: MapViewport;
}

function GatesLayer({ gates, systemMap, viewport }: GatesLayerProps) {
  const draw = useCallback(
    (g: PIXI.Graphics) => {
      g.clear();
      g.lineStyle(GATE_LINE_WIDTH, GATE_COLOR, 0.6);

      for (const gate of gates) {
        const from = systemMap.get(gate.fromSystemId);
        const to = systemMap.get(gate.toSystemId);

        if (from && to) {
          const fromScreen = worldToScreen(from.x, from.y, viewport);
          const toScreen = worldToScreen(to.x, to.y, viewport);

          g.moveTo(fromScreen.x, fromScreen.y);
          g.lineTo(toScreen.x, toScreen.y);
        }
      }
    },
    [gates, systemMap, viewport]
  );

  return <Graphics draw={draw} />;
}

/**
 * Routes layer - draws highlighted route paths
 */
interface RoutesLayerProps {
  routes: MapRoute[];
  systemMap: Map<number, MapSystem>;
  viewport: MapViewport;
}

function RoutesLayer({ routes, systemMap, viewport }: RoutesLayerProps) {
  const draw = useCallback(
    (g: PIXI.Graphics) => {
      g.clear();

      for (const route of routes) {
        const color = parseInt(route.color.replace('#', ''), 16);
        g.lineStyle(ROUTE_LINE_WIDTH, color, 0.9);

        let started = false;
        for (const systemId of route.systemIds) {
          const system = systemMap.get(systemId);
          if (system) {
            const screen = worldToScreen(system.x, system.y, viewport);
            if (!started) {
              g.moveTo(screen.x, screen.y);
              started = true;
            } else {
              g.lineTo(screen.x, screen.y);
            }
          }
        }
      }
    },
    [routes, systemMap, viewport]
  );

  return <Graphics draw={draw} />;
}

/**
 * Systems layer - draws system nodes as circles
 */
interface SystemsLayerProps {
  systems: MapSystem[];
  viewport: MapViewport;
  selectedSystem?: number | null;
  hoveredSystem?: number | null;
  highlightedSystems?: Set<number>;
}

function SystemsLayer({
  systems,
  viewport,
  selectedSystem,
  hoveredSystem,
  highlightedSystems,
}: SystemsLayerProps) {
  const draw = useCallback(
    (g: PIXI.Graphics) => {
      g.clear();

      // Draw normal systems first
      for (const system of systems) {
        const isSelected = system.systemId === selectedSystem;
        const isHovered = system.systemId === hoveredSystem;
        const isHighlighted = highlightedSystems?.has(system.systemId);

        // Skip special systems - draw them on top
        if (isSelected || isHovered || isHighlighted) continue;

        const screen = worldToScreen(system.x, system.y, viewport);
        const color = parseInt(getSecurityColor(system.security).replace('#', ''), 16);
        const radius = SYSTEM_BASE_RADIUS;

        g.beginFill(color, 0.8);
        g.drawCircle(screen.x, screen.y, radius);
        g.endFill();
      }

      // Draw highlighted systems
      if (highlightedSystems) {
        for (const system of systems) {
          if (!highlightedSystems.has(system.systemId)) continue;
          if (system.systemId === selectedSystem || system.systemId === hoveredSystem) continue;

          const screen = worldToScreen(system.x, system.y, viewport);
          const color = parseInt(getSecurityColor(system.security).replace('#', ''), 16);

          g.lineStyle(2, 0xffffff, 0.8);
          g.beginFill(color, 1);
          g.drawCircle(screen.x, screen.y, SYSTEM_BASE_RADIUS + 1);
          g.endFill();
          g.lineStyle(0);
        }
      }

      // Draw hovered system
      if (hoveredSystem) {
        const system = systems.find((s) => s.systemId === hoveredSystem);
        if (system) {
          const screen = worldToScreen(system.x, system.y, viewport);
          const color = parseInt(getSecurityColor(system.security).replace('#', ''), 16);

          g.lineStyle(2, 0xffffff, 0.9);
          g.beginFill(color, 1);
          g.drawCircle(screen.x, screen.y, SYSTEM_HOVER_RADIUS);
          g.endFill();
          g.lineStyle(0);
        }
      }

      // Draw selected system
      if (selectedSystem) {
        const system = systems.find((s) => s.systemId === selectedSystem);
        if (system) {
          const screen = worldToScreen(system.x, system.y, viewport);
          const color = parseInt(getSecurityColor(system.security).replace('#', ''), 16);

          // Outer glow
          g.lineStyle(3, 0xffffff, 0.5);
          g.drawCircle(screen.x, screen.y, SYSTEM_SELECTED_RADIUS + 4);
          g.lineStyle(0);

          // Inner fill
          g.lineStyle(2, 0xffffff, 1);
          g.beginFill(color, 1);
          g.drawCircle(screen.x, screen.y, SYSTEM_SELECTED_RADIUS);
          g.endFill();
        }
      }
    },
    [systems, viewport, selectedSystem, hoveredSystem, highlightedSystems]
  );

  return <Graphics draw={draw} />;
}

/**
 * Labels layer - draws system names at higher zoom levels
 */
interface LabelsLayerProps {
  systems: MapSystem[];
  viewport: MapViewport;
}

function LabelsLayer({ systems, viewport }: LabelsLayerProps) {
  // Limit number of labels for performance
  const maxLabels = 200;
  const labelledSystems = useMemo(() => {
    if (systems.length <= maxLabels) return systems;

    // Prioritize high-security systems when there are too many
    return [...systems]
      .sort((a, b) => b.security - a.security)
      .slice(0, maxLabels);
  }, [systems]);

  const textStyle = useMemo(
    () =>
      new PIXI.TextStyle({
        fontFamily: 'Arial',
        fontSize: 10,
        fill: 0xffffff,
        align: 'center',
      }),
    []
  );

  return (
    <>
      {labelledSystems.map((system) => {
        const screen = worldToScreen(system.x, system.y, viewport);
        return (
          <Text
            key={system.systemId}
            text={system.name}
            x={screen.x}
            y={screen.y + 12}
            anchor={0.5}
            style={textStyle}
            alpha={0.7}
          />
        );
      })}
    </>
  );
}

export default MapCanvas;
