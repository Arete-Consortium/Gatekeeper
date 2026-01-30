'use client';

/**
 * Minimap - Overview map showing current viewport position
 * Displays all systems as tiny dots with a viewport rectangle
 * Click to navigate to a location
 */

import React, { useCallback, useEffect, useMemo, useRef } from 'react';
import type { MapSystem, MapViewport } from './types';
import { getSecurityColor } from './types';

interface MinimapProps {
  systems: MapSystem[];
  viewport: MapViewport;
  onViewportChange: (viewport: Partial<MapViewport>) => void;
  size?: number; // Width/height in pixels
}

export function Minimap({
  systems,
  viewport,
  onViewportChange,
  size = 150,
}: MinimapProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Calculate bounds of all systems
  const bounds = useMemo(() => {
    if (systems.length === 0) {
      return { minX: 0, maxX: 1000, minY: 0, maxY: 1000 };
    }

    let minX = Infinity;
    let maxX = -Infinity;
    let minY = Infinity;
    let maxY = -Infinity;

    for (const system of systems) {
      minX = Math.min(minX, system.x);
      maxX = Math.max(maxX, system.x);
      minY = Math.min(minY, system.y);
      maxY = Math.max(maxY, system.y);
    }

    // Add padding
    const padding = (maxX - minX) * 0.05;
    return {
      minX: minX - padding,
      maxX: maxX + padding,
      minY: minY - padding,
      maxY: maxY + padding,
    };
  }, [systems]);

  // World to minimap coordinates
  const worldToMinimap = useCallback(
    (wx: number, wy: number) => {
      const rangeX = bounds.maxX - bounds.minX;
      const rangeY = bounds.maxY - bounds.minY;
      return {
        x: ((wx - bounds.minX) / rangeX) * size,
        y: ((wy - bounds.minY) / rangeY) * size,
      };
    },
    [bounds, size]
  );

  // Minimap to world coordinates
  const minimapToWorld = useCallback(
    (mx: number, my: number) => {
      const rangeX = bounds.maxX - bounds.minX;
      const rangeY = bounds.maxY - bounds.minY;
      return {
        x: (mx / size) * rangeX + bounds.minX,
        y: (my / size) * rangeY + bounds.minY,
      };
    },
    [bounds, size]
  );

  // Render minimap
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear with dark background
    ctx.fillStyle = '#0a0a0a';
    ctx.fillRect(0, 0, size, size);

    // Draw border
    ctx.strokeStyle = '#333333';
    ctx.lineWidth = 1;
    ctx.strokeRect(0, 0, size, size);

    // Draw systems as tiny dots
    for (const system of systems) {
      const pos = worldToMinimap(system.x, system.y);
      const color = getSecurityColor(system.security);

      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, 0.75, 0, Math.PI * 2);
      ctx.fill();
    }

    // Calculate viewport rectangle in minimap coordinates
    const worldWidth = viewport.width / viewport.zoom;
    const worldHeight = viewport.height / viewport.zoom;
    const viewTopLeft = worldToMinimap(
      viewport.x - worldWidth / 2,
      viewport.y - worldHeight / 2
    );
    const viewBottomRight = worldToMinimap(
      viewport.x + worldWidth / 2,
      viewport.y + worldHeight / 2
    );

    const rectWidth = viewBottomRight.x - viewTopLeft.x;
    const rectHeight = viewBottomRight.y - viewTopLeft.y;

    // Draw viewport rectangle
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 1.5;
    ctx.strokeRect(viewTopLeft.x, viewTopLeft.y, rectWidth, rectHeight);

    // Draw fill with transparency
    ctx.fillStyle = 'rgba(255, 255, 255, 0.1)';
    ctx.fillRect(viewTopLeft.x, viewTopLeft.y, rectWidth, rectHeight);
  }, [systems, viewport, size, worldToMinimap]);

  // Handle click to navigate
  const handleClick = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const rect = canvasRef.current?.getBoundingClientRect();
      if (!rect) return;

      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;
      const world = minimapToWorld(mx, my);

      onViewportChange({ x: world.x, y: world.y });
    },
    [minimapToWorld, onViewportChange]
  );

  // Handle drag to pan
  const handleMouseDown = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      e.preventDefault();
      handleClick(e);

      const handleMouseMove = (moveEvent: MouseEvent) => {
        const rect = canvasRef.current?.getBoundingClientRect();
        if (!rect) return;

        const mx = moveEvent.clientX - rect.left;
        const my = moveEvent.clientY - rect.top;
        const world = minimapToWorld(mx, my);

        onViewportChange({ x: world.x, y: world.y });
      };

      const handleMouseUp = () => {
        window.removeEventListener('mousemove', handleMouseMove);
        window.removeEventListener('mouseup', handleMouseUp);
      };

      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
    },
    [handleClick, minimapToWorld, onViewportChange]
  );

  if (systems.length === 0) {
    return null;
  }

  return (
    <div className="absolute bottom-4 left-4 z-10">
      <canvas
        ref={canvasRef}
        width={size}
        height={size}
        onMouseDown={handleMouseDown}
        className="cursor-crosshair rounded shadow-lg"
        title="Click to navigate"
      />
    </div>
  );
}

export default Minimap;
