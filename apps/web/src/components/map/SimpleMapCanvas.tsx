'use client';

/**
 * SimpleMapCanvas - Canvas2D renderer for the EVE universe map
 * Handles system dots, gate lines, labels, hover glow, and context menu
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { MapSystem, MapGate, MapViewport, MapLayers, MapRegion, SystemRisk } from './types';
import { getSecurityColor, getSpectralColor, getRiskColor } from './types';
import { buildQuadtree, type Quadtree } from './utils/spatial';

const MIN_ZOOM = 0.1;
const MAX_ZOOM = 20;
const SYSTEM_RADIUS = 2;

// Zoom thresholds for showing different label types
const REGION_LABEL_MAX_ZOOM = 2.5;
const SYSTEM_LABEL_MIN_ZOOM = 3;

// Well-known trade hubs
const TRADE_HUBS = new Set([30000142, 30002187, 30002659, 30002510, 30002053]); // Jita, Amarr, Dodixie, Rens, Hek

interface ContextMenuState {
  x: number;
  y: number;
  systemId: number;
  systemName: string;
}

interface SimpleMapCanvasProps {
  systems: MapSystem[];
  gates: MapGate[];
  viewport: MapViewport;
  onViewportChange: (viewport: MapViewport) => void;
  selectedSystem?: number | null;
  highlightedSystems?: number[];
  onSystemClick?: (systemId: number) => void;
  onSystemHover?: (systemId: number | null) => void;
  onSetRouteOrigin?: (systemId: number) => void;
  onSetRouteDestination?: (systemId: number) => void;
  onAvoidSystem?: (systemId: number) => void;
  onDeselect?: () => void;
  layers: MapLayers;
  colorMode: 'security' | 'risk' | 'star';
  risks?: SystemRisk[];
  regions?: MapRegion[];
  hoveredSystemId?: number | null;
  sovStructureSystems?: Set<number>;
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
  onSetRouteOrigin,
  onSetRouteDestination,
  onAvoidSystem,
  onDeselect,
  layers,
  colorMode,
  risks = [],
  regions = [],
  hoveredSystemId,
  sovStructureSystems,
}: SimpleMapCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const ctxRef = useRef<CanvasRenderingContext2D | null>(null);
  const isDraggingRef = useRef(false);
  const dragStartRef = useRef({ x: 0, y: 0 });
  const systemMapRef = useRef<Map<number, MapSystem>>(new Map());
  const quadtreeRef = useRef<Quadtree | null>(null);
  const [contextMenu, setContextMenu] = useState<ContextMenuState | null>(null);

  // Touch state refs
  const touchStartRef = useRef<{ x: number; y: number; time: number } | null>(null);
  const pinchStartDistRef = useRef<number | null>(null);
  const pinchStartZoomRef = useRef<number>(1);
  const longPressTimerRef = useRef<NodeJS.Timeout | null>(null);
  const isTouchDraggingRef = useRef(false);

  // Cache canvas context on mount
  useEffect(() => {
    const canvas = canvasRef.current;
    if (canvas) {
      ctxRef.current = canvas.getContext('2d');
    }
  }, []);

  // Build system lookup map + quadtree for fast hover detection
  useEffect(() => {
    const map = new Map<number, MapSystem>();
    systems.forEach((s) => map.set(s.systemId, s));
    systemMapRef.current = map;
    quadtreeRef.current = systems.length > 0 ? buildQuadtree(systems) : null;
  }, [systems]);

  // Keyboard shortcuts for pan, zoom, and dismiss
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      const delta = 50 / viewport.zoom;

      switch (e.key) {
        case 'ArrowUp':
          e.preventDefault();
          onViewportChange({ ...viewport, y: viewport.y - delta });
          break;
        case 'ArrowDown':
          e.preventDefault();
          onViewportChange({ ...viewport, y: viewport.y + delta });
          break;
        case 'ArrowLeft':
          e.preventDefault();
          onViewportChange({ ...viewport, x: viewport.x - delta });
          break;
        case 'ArrowRight':
          e.preventDefault();
          onViewportChange({ ...viewport, x: viewport.x + delta });
          break;
        case '+':
        case '=':
          e.preventDefault();
          onViewportChange({
            ...viewport,
            zoom: Math.min(MAX_ZOOM, viewport.zoom * 1.5),
          });
          break;
        case '-':
          e.preventDefault();
          onViewportChange({
            ...viewport,
            zoom: Math.max(MIN_ZOOM, viewport.zoom / 1.5),
          });
          break;
        case 'Escape':
          setContextMenu(null);
          onDeselect?.();
          break;
      }
    };

    container.addEventListener('keydown', handleKeyDown);
    return () => container.removeEventListener('keydown', handleKeyDown);
  }, [viewport, onViewportChange, onDeselect]);

  // Build highlighted systems set for O(1) lookup
  const highlightedSet = useMemo(
    () => new Set(highlightedSystems),
    [highlightedSystems]
  );

  // Build system lookup map for cross-region check (avoids ref access during render)
  const systemLookup = useMemo(() => {
    const map = new Map<number, MapSystem>();
    for (const s of systems) map.set(s.systemId, s);
    return map;
  }, [systems]);

  // Build cross-region gate set for dimming
  const crossRegionGates = useMemo(() => {
    const set = new Set<string>();
    for (const gate of gates) {
      const from = systemLookup.get(gate.fromSystemId);
      const to = systemLookup.get(gate.toSystemId);
      if (from && to && from.regionId !== to.regionId) {
        set.add(`${gate.fromSystemId}-${gate.toSystemId}`);
      }
    }
    return set;
  }, [gates, systemLookup]);

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

  // Find system at screen position using quadtree (O(log n))
  const findSystemAt = useCallback(
    (sx: number, sy: number): MapSystem | null => {
      const world = screenToWorld(sx, sy);
      const tree = quadtreeRef.current;
      if (!tree) return null;

      // Use quadtree findNearest with a radius based on zoom
      const hitRadius = Math.max(8, 12 / viewport.zoom);
      return tree.findNearest(world.x, world.y, hitRadius);
    },
    [viewport, screenToWorld]
  );

  // Render canvas
  useEffect(() => {
    const ctx = ctxRef.current;
    if (!ctx) return;

    // Clear
    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, viewport.width, viewport.height);

    // Draw gates with visual hierarchy
    if (layers.showGates) {
      // Intra-region gates — thin Photon-style lines
      ctx.strokeStyle = '#334155';
      ctx.lineWidth = 0.5;
      ctx.globalAlpha = 0.4;
      ctx.beginPath();

      const crossRegionPaths: Array<{ fx: number; fy: number; tx: number; ty: number }> = [];

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
        ) continue;

        const key = `${gate.fromSystemId}-${gate.toSystemId}`;
        if (crossRegionGates.has(key)) {
          crossRegionPaths.push({ fx: fromScreen.x, fy: fromScreen.y, tx: toScreen.x, ty: toScreen.y });
        } else {
          ctx.moveTo(fromScreen.x, fromScreen.y);
          ctx.lineTo(toScreen.x, toScreen.y);
        }
      }
      ctx.stroke();

      // Cross-region gates — very subtle
      if (crossRegionPaths.length > 0) {
        ctx.strokeStyle = '#1e293b';
        ctx.globalAlpha = 0.2;
        ctx.beginPath();
        for (const p of crossRegionPaths) {
          ctx.moveTo(p.fx, p.fy);
          ctx.lineTo(p.tx, p.ty);
        }
        ctx.stroke();
      }

      ctx.globalAlpha = 1.0;
    }

    // Build risk lookup for risk color mode
    const riskMap = new Map(risks.map((r) => [r.systemId, r]));

    // Draw systems
    for (const system of systems) {
      const screen = worldToScreen(system.x, system.y);

      // Culling
      if (
        screen.x < -20 ||
        screen.x > viewport.width + 20 ||
        screen.y < -20 ||
        screen.y > viewport.height + 20
      ) continue;

      const isHighlighted = highlightedSet.has(system.systemId);
      const isSelected = system.systemId === selectedSystem;
      const isHovered = system.systemId === hoveredSystemId;
      const isTradeHub = TRADE_HUBS.has(system.systemId);
      let color: string;
      if (colorMode === 'star') {
        color = getSpectralColor(system.spectralClass || 'G');
      } else if (colorMode === 'risk') {
        const risk = riskMap.get(system.systemId);
        color = risk ? getRiskColor(risk.riskColor) : '#1e293b'; // dim gray for no data
      } else {
        color = getSecurityColor(system.security);
      }

      // Scale radius with zoom + hub importance — tight Photon-style dots
      const isHub = isTradeHub || system.hub || (system.npcStations && system.npcStations >= 5);
      const baseRadius = Math.max(1, Math.min(SYSTEM_RADIUS, SYSTEM_RADIUS * (viewport.zoom / 2)));
      const hubBonus = isTradeHub ? baseRadius * 1.2 : isHub ? baseRadius * 0.5 : 0;
      const radius = isSelected ? (baseRadius + hubBonus) * 1.8 : baseRadius + hubBonus;

      // Hover glow effect — tight bloom
      if (isHovered && !isSelected) {
        ctx.save();
        ctx.shadowColor = color;
        ctx.shadowBlur = 8;
        ctx.fillStyle = color;
        ctx.globalAlpha = 0.35;
        ctx.beginPath();
        ctx.arc(screen.x, screen.y, radius + 3, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
      }

      // Trade hub outer glow — subtle ring
      if (isTradeHub) {
        ctx.save();
        ctx.shadowColor = '#ffd700';
        ctx.shadowBlur = 6;
        ctx.strokeStyle = '#ffd700';
        ctx.lineWidth = 0.8;
        ctx.globalAlpha = 0.4;
        ctx.beginPath();
        ctx.arc(screen.x, screen.y, radius + 2.5, 0, Math.PI * 2);
        ctx.stroke();
        ctx.restore();
      }

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

        ctx.strokeStyle = '#00ffff';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(screen.x, screen.y, radius + 6, 0, Math.PI * 2);
        ctx.stroke();
      }

      // Main dot
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

      // Hover ring
      if (isHovered && !isSelected) {
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 1;
        ctx.globalAlpha = 0.6;
        ctx.beginPath();
        ctx.arc(screen.x, screen.y, radius + 2, 0, Math.PI * 2);
        ctx.stroke();
        ctx.globalAlpha = 1;
      }
    }

    // Draw region labels when zoomed out (collision avoidance + high contrast)
    if (layers.showRegionLabels && viewport.zoom < REGION_LABEL_MAX_ZOOM && regions.length > 0) {
      ctx.save();
      const fontSize = Math.max(11, Math.min(18, 14 / viewport.zoom));
      ctx.font = `600 ${fontSize}px -apple-system, BlinkMacSystemFont, sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';

      // Sort by system count (larger regions get priority)
      const sorted = [...regions].sort((a, b) => b.systemCount - a.systemCount);
      const placedLabels: Array<{ x: number; y: number; w: number; h: number }> = [];

      for (const region of sorted) {
        const screen = worldToScreen(region.centerX, region.centerY);

        if (
          screen.x < -100 ||
          screen.x > viewport.width + 100 ||
          screen.y < -50 ||
          screen.y > viewport.height + 50
        ) continue;

        const metrics = ctx.measureText(region.name);
        const tw = metrics.width;
        const th = fontSize;
        const rect = { x: screen.x - tw / 2, y: screen.y - th / 2, w: tw, h: th };

        const overlaps = placedLabels.some(
          (p) =>
            rect.x < p.x + p.w + 12 &&
            rect.x + rect.w + 12 > p.x &&
            rect.y < p.y + p.h + 6 &&
            rect.y + rect.h + 6 > p.y
        );
        if (overlaps) continue;

        placedLabels.push(rect);

        // Dark background pill for readability
        ctx.globalAlpha = 0.35;
        ctx.fillStyle = '#000000';
        const padX = 6;
        const padY = 3;
        ctx.beginPath();
        const rx = screen.x - tw / 2 - padX;
        const ry = screen.y - th / 2 - padY;
        const rw = tw + padX * 2;
        const rh = th + padY * 2;
        const cr = 4;
        ctx.moveTo(rx + cr, ry);
        ctx.lineTo(rx + rw - cr, ry);
        ctx.quadraticCurveTo(rx + rw, ry, rx + rw, ry + cr);
        ctx.lineTo(rx + rw, ry + rh - cr);
        ctx.quadraticCurveTo(rx + rw, ry + rh, rx + rw - cr, ry + rh);
        ctx.lineTo(rx + cr, ry + rh);
        ctx.quadraticCurveTo(rx, ry + rh, rx, ry + rh - cr);
        ctx.lineTo(rx, ry + cr);
        ctx.quadraticCurveTo(rx, ry, rx + cr, ry);
        ctx.fill();

        // Label text — bright with strong shadow
        ctx.globalAlpha = 0.75;
        ctx.fillStyle = '#cbd5e1';
        ctx.shadowColor = '#000000';
        ctx.shadowBlur = 6;
        ctx.shadowOffsetX = 0;
        ctx.shadowOffsetY = 0;
        ctx.fillText(region.name, screen.x, screen.y);
        ctx.shadowBlur = 0;
      }

      ctx.restore();
    }

    // Draw system labels at high zoom
    if (layers.showLabels && viewport.zoom > SYSTEM_LABEL_MIN_ZOOM) {
      ctx.font = '9px -apple-system, BlinkMacSystemFont, sans-serif';
      ctx.textAlign = 'center';

      // Skip labels for systems that have sov structure overlays (rendered by SVG)
      // Only suppress when zoom >= 1.5 (sov overlay visibility threshold)
      const skipLabelSet = layers.showSovStructures && viewport.zoom >= 1.5 ? sovStructureSystems : undefined;

      for (const system of systems) {
        if (skipLabelSet?.has(system.systemId)) continue;

        const screen = worldToScreen(system.x, system.y);
        if (
          screen.x < 0 ||
          screen.x > viewport.width ||
          screen.y < 0 ||
          screen.y > viewport.height
        ) continue;

        // Subtle text shadow for readability
        ctx.fillStyle = '#000000';
        ctx.globalAlpha = 0.5;
        ctx.fillText(system.name, screen.x + 0.5, screen.y + 11.5);
        ctx.fillStyle = '#94a3b8';
        ctx.globalAlpha = 0.8;
        ctx.fillText(system.name, screen.x, screen.y + 11);
      }

      ctx.globalAlpha = 1;
    }
  }, [systems, gates, viewport, layers, selectedSystem, highlightedSet, regions, worldToScreen, colorMode, risks, crossRegionGates, hoveredSystemId, sovStructureSystems]);

  // Mouse wheel zoom — exponential curve (#2)
  const handleWheel = useCallback(
    (e: React.WheelEvent) => {
      e.preventDefault();
      const rect = canvasRef.current?.getBoundingClientRect();
      if (!rect) return;

      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;
      const worldBefore = screenToWorld(mouseX, mouseY);

      // Exponential zoom: feels smooth at all scales
      const zoomDelta = -e.deltaY * 0.001;
      const zoomFactor = Math.pow(2, zoomDelta);
      const newZoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, viewport.zoom * zoomFactor));

      // Adjust position to zoom towards mouse
      const newX = worldBefore.x - (mouseX - viewport.width / 2) / newZoom;
      const newY = worldBefore.y - (mouseY - viewport.height / 2) / newZoom;

      onViewportChange({ ...viewport, x: newX, y: newY, zoom: newZoom });
    },
    [viewport, onViewportChange, screenToWorld]
  );

  // Helper: update cursor directly on the canvas element (avoids re-render)
  const setCursor = useCallback((cursor: string) => {
    const canvas = canvasRef.current;
    if (canvas) canvas.style.cursor = cursor;
  }, []);

  // Mouse down - start drag
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button === 2) return; // Right-click handled by context menu
    isDraggingRef.current = true;
    dragStartRef.current = { x: e.clientX, y: e.clientY };
    setCursor('grabbing');
    setContextMenu(null);
  }, [setCursor]);

  // Mouse move - drag pan + hover
  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (isDraggingRef.current) {
        const dx = (e.clientX - dragStartRef.current.x) / viewport.zoom;
        const dy = (e.clientY - dragStartRef.current.y) / viewport.zoom;
        onViewportChange({
          ...viewport,
          x: viewport.x - dx,
          y: viewport.y - dy,
        });
        dragStartRef.current = { x: e.clientX, y: e.clientY };
      } else {
        // Hover detection using quadtree (#6)
        const rect = canvasRef.current?.getBoundingClientRect();
        if (rect) {
          const system = findSystemAt(e.clientX - rect.left, e.clientY - rect.top);
          setCursor(system ? 'pointer' : 'grab');
          onSystemHover?.(system?.systemId ?? null);
        }
      }
    },
    [viewport, onViewportChange, findSystemAt, onSystemHover, setCursor]
  );

  // Mouse up - end drag or click
  const handleMouseUp = useCallback(
    (e: React.MouseEvent) => {
      if (isDraggingRef.current) {
        isDraggingRef.current = false;
        setCursor('grab');

        // If didn't move much, treat as click
        const dx = Math.abs(e.clientX - dragStartRef.current.x);
        const dy = Math.abs(e.clientY - dragStartRef.current.y);
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
    [onSystemClick, findSystemAt, setCursor]
  );

  // === Touch Event Handlers ===

  const getTouchDistance = useCallback((t1: React.Touch, t2: React.Touch) => {
    const dx = t1.clientX - t2.clientX;
    const dy = t1.clientY - t2.clientY;
    return Math.sqrt(dx * dx + dy * dy);
  }, []);

  const getTouchCenter = useCallback((t1: React.Touch, t2: React.Touch) => ({
    x: (t1.clientX + t2.clientX) / 2,
    y: (t1.clientY + t2.clientY) / 2,
  }), []);

  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    setContextMenu(null);

    if (e.touches.length === 2) {
      // Pinch zoom start
      e.preventDefault();
      pinchStartDistRef.current = getTouchDistance(e.touches[0], e.touches[1]);
      pinchStartZoomRef.current = viewport.zoom;
      if (longPressTimerRef.current) {
        clearTimeout(longPressTimerRef.current);
        longPressTimerRef.current = null;
      }
      return;
    }

    if (e.touches.length === 1) {
      const touch = e.touches[0];
      dragStartRef.current = { x: touch.clientX, y: touch.clientY };
      touchStartRef.current = { x: touch.clientX, y: touch.clientY, time: Date.now() };
      isTouchDraggingRef.current = false;

      // Long-press for context menu (500ms)
      longPressTimerRef.current = setTimeout(() => {
        const rect = canvasRef.current?.getBoundingClientRect();
        if (!rect || !touchStartRef.current) return;
        const system = findSystemAt(
          touchStartRef.current.x - rect.left,
          touchStartRef.current.y - rect.top
        );
        if (system) {
          setContextMenu({
            x: touchStartRef.current.x - rect.left,
            y: touchStartRef.current.y - rect.top,
            systemId: system.systemId,
            systemName: system.name,
          });
          // Prevent the touch from also being a drag
          isTouchDraggingRef.current = false;
          touchStartRef.current = null;
        }
      }, 500);
    }
  }, [viewport.zoom, getTouchDistance, findSystemAt]);

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    if (e.touches.length === 2 && pinchStartDistRef.current !== null) {
      // Pinch zoom
      e.preventDefault();
      const currentDist = getTouchDistance(e.touches[0], e.touches[1]);
      const scale = currentDist / pinchStartDistRef.current;
      const newZoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, pinchStartZoomRef.current * scale));

      // Zoom towards pinch center
      const rect = canvasRef.current?.getBoundingClientRect();
      if (rect) {
        const center = getTouchCenter(e.touches[0], e.touches[1]);
        const cx = center.x - rect.left;
        const cy = center.y - rect.top;
        const worldBefore = screenToWorld(cx, cy);
        const newX = worldBefore.x - (cx - viewport.width / 2) / newZoom;
        const newY = worldBefore.y - (cy - viewport.height / 2) / newZoom;
        onViewportChange({ ...viewport, x: newX, y: newY, zoom: newZoom });
      }
      return;
    }

    if (e.touches.length === 1) {
      const touch = e.touches[0];
      const dx = touch.clientX - dragStartRef.current.x;
      const dy = touch.clientY - dragStartRef.current.y;

      // Cancel long-press if moved more than 10px
      if (Math.abs(dx) > 10 || Math.abs(dy) > 10) {
        if (longPressTimerRef.current) {
          clearTimeout(longPressTimerRef.current);
          longPressTimerRef.current = null;
        }
        isTouchDraggingRef.current = true;
      }

      if (isTouchDraggingRef.current) {
        e.preventDefault();
        onViewportChange({
          ...viewport,
          x: viewport.x - dx / viewport.zoom,
          y: viewport.y - dy / viewport.zoom,
        });
        dragStartRef.current = { x: touch.clientX, y: touch.clientY };
      }
    }
  }, [viewport, onViewportChange, getTouchDistance, getTouchCenter, screenToWorld]);

  const handleTouchEnd = useCallback((e: React.TouchEvent) => {
    if (longPressTimerRef.current) {
      clearTimeout(longPressTimerRef.current);
      longPressTimerRef.current = null;
    }

    // Reset pinch state
    if (e.touches.length < 2) {
      pinchStartDistRef.current = null;
    }

    // Tap to select (short touch, didn't drag)
    if (
      e.touches.length === 0 &&
      touchStartRef.current &&
      !isTouchDraggingRef.current &&
      Date.now() - touchStartRef.current.time < 300
    ) {
      const rect = canvasRef.current?.getBoundingClientRect();
      if (rect) {
        const system = findSystemAt(
          touchStartRef.current.x - rect.left,
          touchStartRef.current.y - rect.top
        );
        if (system) {
          onSystemClick?.(system.systemId);
        }
      }
    }

    touchStartRef.current = null;
    isTouchDraggingRef.current = false;
  }, [findSystemAt, onSystemClick]);

  // Right-click context menu (#10)
  const handleContextMenu = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      const rect = canvasRef.current?.getBoundingClientRect();
      if (!rect) return;

      const system = findSystemAt(e.clientX - rect.left, e.clientY - rect.top);
      if (system) {
        setContextMenu({
          x: e.clientX - rect.left,
          y: e.clientY - rect.top,
          systemId: system.systemId,
          systemName: system.name,
        });
      } else {
        setContextMenu(null);
      }
    },
    [findSystemAt]
  );

  return (
    <div ref={containerRef} tabIndex={0} className="relative w-full h-full outline-none">
      <canvas
        ref={canvasRef}
        width={viewport.width}
        height={viewport.height}
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={() => {
          isDraggingRef.current = false;
          setCursor('grab');
          onSystemHover?.(null);
        }}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
        onContextMenu={handleContextMenu}
        style={{ cursor: 'grab', touchAction: 'none' }}
        className="w-full h-full"
      />

      {/* Context Menu (#10) */}
      {contextMenu && (
        <div
          className="absolute bg-gray-900/95 border border-gray-600 rounded-lg shadow-xl py-1 z-50 min-w-[200px]"
          style={{
            left: Math.min(contextMenu.x, viewport.width - 210),
            top: Math.min(contextMenu.y, viewport.height - 200),
          }}
        >
          <div className="px-3 py-2 text-sm text-gray-400 border-b border-gray-700 font-medium">
            {contextMenu.systemName}
          </div>
          <button
            className="w-full px-3 py-3 text-sm text-left text-gray-200 hover:bg-gray-700/50 active:bg-gray-600/50 flex items-center gap-3"
            onClick={() => {
              onSetRouteOrigin?.(contextMenu.systemId);
              setContextMenu(null);
            }}
          >
            <span className="text-green-400 font-bold">A</span> Set as Origin
          </button>
          <button
            className="w-full px-3 py-3 text-sm text-left text-gray-200 hover:bg-gray-700/50 active:bg-gray-600/50 flex items-center gap-3"
            onClick={() => {
              onSetRouteDestination?.(contextMenu.systemId);
              setContextMenu(null);
            }}
          >
            <span className="text-red-400 font-bold">B</span> Set as Destination
          </button>
          <button
            className="w-full px-3 py-3 text-sm text-left text-gray-200 hover:bg-gray-700/50 active:bg-gray-600/50 flex items-center gap-3"
            onClick={() => {
              onAvoidSystem?.(contextMenu.systemId);
              setContextMenu(null);
            }}
          >
            <span className="text-yellow-400 font-bold">!</span> Avoid System
          </button>
          <a
            href={`https://zkillboard.com/system/${contextMenu.systemId}/`}
            target="_blank"
            rel="noopener noreferrer"
            className="w-full px-3 py-3 text-sm text-left text-gray-200 hover:bg-gray-700/50 active:bg-gray-600/50 flex items-center gap-3"
            onClick={() => setContextMenu(null)}
          >
            <span className="text-orange-400 font-bold">z</span> zKillboard
          </a>
        </div>
      )}
    </div>
  );
});

export default SimpleMapCanvas;
