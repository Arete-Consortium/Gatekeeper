'use client';

/**
 * PixiMapCanvas - WebGL renderer using PixiJS with dynamic import
 * Renders 8000+ system nodes efficiently with viewport culling
 * Uses dynamic import to avoid SSR issues with PixiJS
 */

import React, { useCallback, useEffect, useRef, useState } from 'react';
import dynamic from 'next/dynamic';
import type { MapSystem, MapGate, MapViewport, MapLayers, MapRegion } from './types';
import { getSecurityColor } from './types';

// Dynamically import PixiJS components with SSR disabled
const PixiStage = dynamic(
  () => import('@pixi/react').then((mod) => mod.Stage),
  { ssr: false }
);

const PixiContainer = dynamic(
  () => import('@pixi/react').then((mod) => mod.Container),
  { ssr: false }
);

const PixiGraphics = dynamic(
  () => import('@pixi/react').then((mod) => mod.Graphics),
  { ssr: false }
);

// Rendering constants
const SYSTEM_BASE_RADIUS = 4;
const SYSTEM_SELECTED_RADIUS = 8;
const GATE_LINE_WIDTH = 0.5;
const GATE_COLOR = 0x333333;
const MIN_ZOOM = 0.02;
const MAX_ZOOM = 5;
const ZOOM_SPEED = 0.001;

interface PixiMapCanvasProps {
  systems: MapSystem[];
  gates: MapGate[];
  viewport: MapViewport;
  onViewportChange: (viewport: MapViewport) => void;
  selectedSystem?: number | null;
  highlightedSystems?: number[];
  onSystemClick?: (systemId: number) => void;
  onSystemHover?: (systemId: number | null) => void;
  layers: MapLayers;
  colorMode?: 'security' | 'region' | 'activity';
  regions?: MapRegion[];
}

// Convert world coordinates to screen coordinates
function worldToScreen(
  worldX: number,
  worldY: number,
  viewport: MapViewport
): { x: number; y: number } {
  return {
    x: (worldX - viewport.x) * viewport.zoom + viewport.width / 2,
    y: (worldY - viewport.y) * viewport.zoom + viewport.height / 2,
  };
}

// Convert screen coordinates to world coordinates
function screenToWorld(
  screenX: number,
  screenY: number,
  viewport: MapViewport
): { x: number; y: number } {
  return {
    x: (screenX - viewport.width / 2) / viewport.zoom + viewport.x,
    y: (screenY - viewport.height / 2) / viewport.zoom + viewport.y,
  };
}

// Clamp value between min and max
function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

/**
 * Main PixiJS map canvas component
 */
export function PixiMapCanvas({
  systems,
  gates,
  viewport,
  onViewportChange,
  selectedSystem,
  highlightedSystems = [],
  onSystemClick,
  onSystemHover,
  layers,
}: PixiMapCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const isDragging = useRef(false);
  const lastMousePos = useRef({ x: 0, y: 0 });
  const [isClient] = useState(() => typeof window !== 'undefined');

  // Build system map for quick lookup
  const systemMap = React.useMemo(() => {
    const map = new Map<number, MapSystem>();
    for (const system of systems) {
      map.set(system.systemId, system);
    }
    return map;
  }, [systems]);

  // Get visible systems (simple bounds check)
  const visibleSystems = React.useMemo(() => {
    const margin = 100 / viewport.zoom;
    const minX = viewport.x - viewport.width / 2 / viewport.zoom - margin;
    const maxX = viewport.x + viewport.width / 2 / viewport.zoom + margin;
    const minY = viewport.y - viewport.height / 2 / viewport.zoom - margin;
    const maxY = viewport.y + viewport.height / 2 / viewport.zoom + margin;

    return systems.filter(
      (s) => s.x >= minX && s.x <= maxX && s.y >= minY && s.y <= maxY
    );
  }, [systems, viewport]);

  // Get visible gates
  const visibleGates = React.useMemo(() => {
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

      const worldBefore = screenToWorld(mouseX, mouseY, viewport);
      const delta = -e.deltaY * ZOOM_SPEED;
      const newZoom = clamp(viewport.zoom * (1 + delta), MIN_ZOOM, MAX_ZOOM);

      const newViewport: MapViewport = { ...viewport, zoom: newZoom };
      const worldAfter = screenToWorld(mouseX, mouseY, newViewport);

      onViewportChange({
        ...newViewport,
        x: viewport.x + (worldBefore.x - worldAfter.x),
        y: viewport.y + (worldBefore.y - worldAfter.y),
      });
    },
    [viewport, onViewportChange]
  );

  // Handle mouse down for panning
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button === 0) {
      isDragging.current = true;
      lastMousePos.current = { x: e.clientX, y: e.clientY };
    }
  }, []);

  // Handle mouse move for panning and hover
  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      const rect = containerRef.current?.getBoundingClientRect();
      if (!rect) return;

      if (isDragging.current) {
        const dx = e.clientX - lastMousePos.current.x;
        const dy = e.clientY - lastMousePos.current.y;

        onViewportChange({
          ...viewport,
          x: viewport.x - dx / viewport.zoom,
          y: viewport.y - dy / viewport.zoom,
        });

        lastMousePos.current = { x: e.clientX, y: e.clientY };
      } else if (onSystemHover) {
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;
        const worldPos = screenToWorld(mouseX, mouseY, viewport);

        // Find nearest system within radius
        const searchRadius = 20 / viewport.zoom;
        let nearest: MapSystem | null = null;
        let nearestDist = Infinity;

        for (const system of visibleSystems) {
          const dx = system.x - worldPos.x;
          const dy = system.y - worldPos.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < searchRadius && dist < nearestDist) {
            nearest = system;
            nearestDist = dist;
          }
        }

        onSystemHover(nearest?.systemId ?? null);
      }
    },
    [viewport, onViewportChange, onSystemHover, visibleSystems]
  );

  // Handle mouse up
  const handleMouseUp = useCallback(() => {
    isDragging.current = false;
  }, []);

  // Handle click
  const handleClick = useCallback(
    (e: React.MouseEvent) => {
      if (!onSystemClick) return;

      const rect = containerRef.current?.getBoundingClientRect();
      if (!rect) return;

      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;
      const worldPos = screenToWorld(mouseX, mouseY, viewport);

      const searchRadius = 20 / viewport.zoom;
      let nearest: MapSystem | null = null;
      let nearestDist = Infinity;

      for (const system of visibleSystems) {
        const dx = system.x - worldPos.x;
        const dy = system.y - worldPos.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < searchRadius && dist < nearestDist) {
          nearest = system;
          nearestDist = dist;
        }
      }

      if (nearest) {
        onSystemClick(nearest.systemId);
      }
    },
    [viewport, visibleSystems, onSystemClick]
  );

  // Add wheel listener
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    container.addEventListener('wheel', handleWheel, { passive: false });
    return () => container.removeEventListener('wheel', handleWheel);
  }, [handleWheel]);

  // Draw gates
  const drawGates = useCallback(
    (g: any) => {
      g.clear();
      g.lineStyle(GATE_LINE_WIDTH, GATE_COLOR, 0.6);

      for (const gate of visibleGates) {
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
    [visibleGates, systemMap, viewport]
  );

  // Draw systems
  const highlightedSet = React.useMemo(
    () => new Set(highlightedSystems),
    [highlightedSystems]
  );

  const drawSystems = useCallback(
    (g: any) => {
      g.clear();

      // Draw normal systems
      for (const system of visibleSystems) {
        const isSelected = system.systemId === selectedSystem;
        const isHighlighted = highlightedSet.has(system.systemId);

        if (isSelected || isHighlighted) continue;

        const screen = worldToScreen(system.x, system.y, viewport);
        const color = parseInt(
          getSecurityColor(system.security).replace('#', ''),
          16
        );

        g.beginFill(color, 0.8);
        g.drawCircle(screen.x, screen.y, SYSTEM_BASE_RADIUS);
        g.endFill();
      }

      // Draw highlighted systems
      for (const system of visibleSystems) {
        if (!highlightedSet.has(system.systemId)) continue;
        if (system.systemId === selectedSystem) continue;

        const screen = worldToScreen(system.x, system.y, viewport);
        const color = parseInt(
          getSecurityColor(system.security).replace('#', ''),
          16
        );

        g.lineStyle(2, 0xffffff, 0.8);
        g.beginFill(color, 1);
        g.drawCircle(screen.x, screen.y, SYSTEM_BASE_RADIUS + 1);
        g.endFill();
        g.lineStyle(0);
      }

      // Draw selected system
      if (selectedSystem) {
        const system = systemMap.get(selectedSystem);
        if (system) {
          const screen = worldToScreen(system.x, system.y, viewport);
          const color = parseInt(
            getSecurityColor(system.security).replace('#', ''),
            16
          );

          g.lineStyle(3, 0xffffff, 0.5);
          g.drawCircle(screen.x, screen.y, SYSTEM_SELECTED_RADIUS + 4);
          g.lineStyle(2, 0xffffff, 1);
          g.beginFill(color, 1);
          g.drawCircle(screen.x, screen.y, SYSTEM_SELECTED_RADIUS);
          g.endFill();
        }
      }
    },
    [visibleSystems, viewport, selectedSystem, highlightedSet, systemMap]
  );

  // Don't render on server
  if (!isClient) {
    return (
      <div
        ref={containerRef}
        className="w-full h-full bg-black flex items-center justify-center"
      >
        <span className="text-gray-500">Loading map...</span>
      </div>
    );
  }

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
      <PixiStage
        width={viewport.width}
        height={viewport.height}
        options={{
          backgroundColor: 0x000000,
          antialias: true,
          resolution: typeof window !== 'undefined' ? window.devicePixelRatio || 1 : 1,
          autoDensity: true,
        }}
      >
        <PixiContainer>
          {layers.showGates && <PixiGraphics draw={drawGates} />}
          <PixiGraphics draw={drawSystems} />
        </PixiContainer>
      </PixiStage>
    </div>
  );
}

export default PixiMapCanvas;
