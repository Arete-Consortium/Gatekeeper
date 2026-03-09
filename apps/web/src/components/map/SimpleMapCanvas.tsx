'use client';

/**
 * SimpleMapCanvas - Canvas2D renderer fallback
 * Works without PixiJS for reliable rendering
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { MapSystem, MapGate, MapViewport, MapLayers, MapRegion } from './types';
import { getSecurityColor } from './types';

const MIN_ZOOM = 0.1;
const MAX_ZOOM = 50;
const SYSTEM_RADIUS = 3;

// Zoom thresholds for showing different label types
const REGION_LABEL_MAX_ZOOM = 3; // Show region labels when zoomed out
const SYSTEM_LABEL_MIN_ZOOM = 8; // Show system labels when zoomed in

interface SimpleMapCanvasProps {
  systems: MapSystem[];
  gates: MapGate[];
  viewport: MapViewport;
  onViewportChange: (viewport: MapViewport) => void;
  selectedSystem?: number | null;
  highlightedSystems?: number[];
  onSystemClick?: (systemId: number) => void;
  onSystemHover?: (systemId: number | null) => void;
  layers: MapLayers;
  colorMode: 'security' | 'risk';
  regions?: MapRegion[];
}

export const SimpleMapCanvas = React.memo(function SimpleMapCanvas({
  systems,
  gates,
  viewport,
  onViewportChange,
  selectedSystem,
  highlightedSystems = [],
  onSystemClick,
  onSystemHover,
  layers,
  colorMode,
  regions = [],
}: SimpleMapCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const systemMapRef = useRef<Map<number, MapSystem>>(new Map());

  // Build system lookup map
  useEffect(() => {
    const map = new Map<number, MapSystem>();
    systems.forEach((s) => map.set(s.systemId, s));
    systemMapRef.current = map;
  }, [systems]);

  // Build highlighted systems set for O(1) lookup
  const highlightedSet = useMemo(
    () => new Set(highlightedSystems),
    [highlightedSystems]
  );

  // World to screen transformation
  const worldToScreen = useCallback(
    (wx: number, wy: number) => ({
      x: (wx - viewport.x) * viewport.zoom + viewport.width / 2,
      y: (wy - viewport.y) * viewport.zoom + viewport.height / 2,
    }),
    [viewport]
  );

  // Screen to world transformation
  const screenToWorld = useCallback(
    (sx: number, sy: number) => ({
      x: (sx - viewport.width / 2) / viewport.zoom + viewport.x,
      y: (sy - viewport.height / 2) / viewport.zoom + viewport.y,
    }),
    [viewport]
  );

  // Find system at screen position (viewport-filtered for performance)
  const findSystemAt = useCallback(
    (sx: number, sy: number): MapSystem | null => {
      const hitRadius = 10 / viewport.zoom;
      const world = screenToWorld(sx, sy);

      // Only check systems within the viewport bounds (+ margin)
      const margin = 50 / viewport.zoom;
      const viewLeft = (0 - viewport.width / 2) / viewport.zoom + viewport.x - margin;
      const viewRight = (viewport.width - viewport.width / 2) / viewport.zoom + viewport.x + margin;
      const viewTop = (0 - viewport.height / 2) / viewport.zoom + viewport.y - margin;
      const viewBottom = (viewport.height - viewport.height / 2) / viewport.zoom + viewport.y + margin;

      for (const system of systems) {
        if (system.x < viewLeft || system.x > viewRight || system.y < viewTop || system.y > viewBottom) continue;
        const dx = system.x - world.x;
        const dy = system.y - world.y;
        if (dx * dx + dy * dy < hitRadius * hitRadius) {
          return system;
        }
      }
      return null;
    },
    [systems, viewport, screenToWorld]
  );

  // Render canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear
    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, viewport.width, viewport.height);

    // Draw gates
    if (layers.showGates) {
      ctx.strokeStyle = '#4a5568';
      ctx.lineWidth = 1;
      ctx.globalAlpha = 0.6;
      ctx.beginPath();

      for (const gate of gates) {
        const from = systemMapRef.current.get(gate.fromSystemId);
        const to = systemMapRef.current.get(gate.toSystemId);
        if (!from || !to) continue;

        const fromScreen = worldToScreen(from.x, from.y);
        const toScreen = worldToScreen(to.x, to.y);

        // Skip if both points are off screen
        if (
          (fromScreen.x < -50 || fromScreen.x > viewport.width + 50) &&
          (toScreen.x < -50 || toScreen.x > viewport.width + 50)
        )
          continue;

        ctx.moveTo(fromScreen.x, fromScreen.y);
        ctx.lineTo(toScreen.x, toScreen.y);
      }

      ctx.stroke();
      ctx.globalAlpha = 1.0;
    }

    // Draw systems
    for (const system of systems) {
      const screen = worldToScreen(system.x, system.y);

      // Culling
      if (
        screen.x < -20 ||
        screen.x > viewport.width + 20 ||
        screen.y < -20 ||
        screen.y > viewport.height + 20
      )
        continue;

      const isHighlighted = highlightedSet.has(system.systemId);
      const isSelected = system.systemId === selectedSystem;
      const color = getSecurityColor(system.security);
      // Scale radius: smaller when zoomed out to show structure, larger when zoomed in
      const baseRadius = Math.max(1.5, Math.min(SYSTEM_RADIUS, SYSTEM_RADIUS * (viewport.zoom / 8)));
      const radius = isSelected ? baseRadius * 2 : baseRadius;

      // Draw highlight glow for search results
      if (isHighlighted) {
        ctx.save();
        ctx.shadowColor = '#00ffff';
        ctx.shadowBlur = 15;
        ctx.fillStyle = '#00ffff';
        ctx.beginPath();
        ctx.arc(screen.x, screen.y, radius + 4, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();

        // Highlight ring
        ctx.strokeStyle = '#00ffff';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(screen.x, screen.y, radius + 6, 0, Math.PI * 2);
        ctx.stroke();
      }

      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(screen.x, screen.y, radius, 0, Math.PI * 2);
      ctx.fill();

      // Selection ring
      if (isSelected) {
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(screen.x, screen.y, radius + 3, 0, Math.PI * 2);
        ctx.stroke();
      }
    }

    // Draw region labels when zoomed out
    if (layers.showRegionLabels && viewport.zoom < REGION_LABEL_MAX_ZOOM && regions.length > 0) {
      ctx.save();
      // Scale font size inversely with zoom so labels stay readable
      const fontSize = Math.max(12, Math.min(20, 60 / viewport.zoom));
      ctx.font = `bold ${fontSize}px Arial`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillStyle = '#ffffff';
      ctx.globalAlpha = 0.6;

      for (const region of regions) {
        const screen = worldToScreen(region.centerX, region.centerY);

        // Skip if off screen with generous margin for text
        if (
          screen.x < -100 ||
          screen.x > viewport.width + 100 ||
          screen.y < -50 ||
          screen.y > viewport.height + 50
        )
          continue;

        // Draw text with shadow for readability
        ctx.shadowColor = '#000000';
        ctx.shadowBlur = 4;
        ctx.shadowOffsetX = 1;
        ctx.shadowOffsetY = 1;
        ctx.fillText(region.name, screen.x, screen.y);
      }

      ctx.restore();
    }

    // Draw system labels at high zoom
    if (layers.showLabels && viewport.zoom > SYSTEM_LABEL_MIN_ZOOM) {
      ctx.fillStyle = '#ffffff';
      ctx.font = '10px Arial';
      ctx.textAlign = 'center';
      ctx.globalAlpha = 0.7;

      for (const system of systems) {
        const screen = worldToScreen(system.x, system.y);
        if (
          screen.x < 0 ||
          screen.x > viewport.width ||
          screen.y < 0 ||
          screen.y > viewport.height
        )
          continue;

        ctx.fillText(system.name, screen.x, screen.y + 15);
      }

      ctx.globalAlpha = 1;
    }
  }, [systems, gates, viewport, layers, selectedSystem, highlightedSet, regions, worldToScreen]);

  // Mouse wheel zoom
  const handleWheel = useCallback(
    (e: React.WheelEvent) => {
      e.preventDefault();
      const rect = canvasRef.current?.getBoundingClientRect();
      if (!rect) return;

      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;
      const worldBefore = screenToWorld(mouseX, mouseY);

      const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
      const newZoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, viewport.zoom * zoomFactor));

      // Adjust position to zoom towards mouse
      const newX = worldBefore.x - (mouseX - viewport.width / 2) / newZoom;
      const newY = worldBefore.y - (mouseY - viewport.height / 2) / newZoom;

      onViewportChange({ ...viewport, x: newX, y: newY, zoom: newZoom });
    },
    [viewport, onViewportChange, screenToWorld]
  );

  // Mouse down - start drag
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX, y: e.clientY });
  }, []);

  // Mouse move - drag pan
  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (isDragging) {
        const dx = (e.clientX - dragStart.x) / viewport.zoom;
        const dy = (e.clientY - dragStart.y) / viewport.zoom;
        onViewportChange({
          ...viewport,
          x: viewport.x - dx,
          y: viewport.y - dy,
        });
        setDragStart({ x: e.clientX, y: e.clientY });
      } else {
        // Hover detection
        const rect = canvasRef.current?.getBoundingClientRect();
        if (rect && onSystemHover) {
          const system = findSystemAt(e.clientX - rect.left, e.clientY - rect.top);
          onSystemHover(system?.systemId ?? null);
        }
      }
    },
    [isDragging, dragStart, viewport, onViewportChange, findSystemAt, onSystemHover]
  );

  // Mouse up - end drag or click
  const handleMouseUp = useCallback(
    (e: React.MouseEvent) => {
      if (isDragging) {
        setIsDragging(false);

        // If didn't move much, treat as click
        const dx = Math.abs(e.clientX - dragStart.x);
        const dy = Math.abs(e.clientY - dragStart.y);
        if (dx < 5 && dy < 5 && onSystemClick) {
          const rect = canvasRef.current?.getBoundingClientRect();
          if (rect) {
            const system = findSystemAt(e.clientX - rect.left, e.clientY - rect.top);
            if (system) {
              onSystemClick(system.systemId);
            }
          }
        }
      }
    },
    [isDragging, dragStart, onSystemClick, findSystemAt]
  );

  return (
    <canvas
      ref={canvasRef}
      width={viewport.width}
      height={viewport.height}
      onWheel={handleWheel}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={() => setIsDragging(false)}
      style={{ cursor: isDragging ? 'grabbing' : 'grab' }}
      className="w-full h-full"
    />
  );
});

export default SimpleMapCanvas;
