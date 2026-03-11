'use client';

/**
 * JumpRangeMap — Mini map showing systems within capital jump range.
 * Renders on the route page when capital jump mode is active.
 * Click a system to add it as a cyno waypoint.
 */

import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { GatekeeperAPI } from '@/lib/api';
import type { MapConfig } from '@/lib/types';
import type { MapSystem, MapGate, MapViewport, MapLayers } from '@/components/map/types';
import { getSecurityColor } from '@/components/map/types';
import { calculateFitZoom, worldToScreen, screenToWorld, buildQuadtree } from '@/components/map/utils/spatial';
import type { Quadtree } from '@/components/map/utils/spatial';
import { Loader2 } from 'lucide-react';

// LY conversion factor must match backend
// Coords are EVE meters / 1e15, so 1 LY = 9.461 units. Conversion = 1/9.461
const LY_CONVERSION = 0.10570;

interface JumpRangeMapProps {
  /** Origin system name */
  originSystem?: string;
  /** Destination system name */
  destSystem?: string;
  /** Max jump range in LY */
  maxRangeLy: number;
  /** Currently planned waypoint system names */
  waypoints?: string[];
  /** Callback when user clicks a system to add as waypoint */
  onAddWaypoint?: (systemName: string) => void;
  /** Whether to highlight station systems */
  preferStations?: boolean;
}

// Transform MapConfig into MapSystem[]/MapGate[] (matches map page transform)
function transformConfig(config: MapConfig): {
  systems: MapSystem[];
  gates: MapGate[];
  nameToSystem: Map<string, MapSystem>;
} {
  const nameToId = new Map<string, number>();
  const nameToSystem = new Map<string, MapSystem>();
  const mapSystems: MapSystem[] = [];

  for (const [name, sys] of Object.entries(config.systems)) {
    const mapSystem: MapSystem = {
      systemId: sys.id,
      name,
      x: sys.position.x,
      y: sys.position.y,
      security: sys.security,
      regionId: sys.region_id,
      constellationId: sys.constellation_id,
      hub: sys.hub,
      npcStations: sys.npc_stations,
      regionName: sys.region_name,
      constellationName: sys.constellation_name,
    };
    nameToId.set(name, sys.id);
    nameToSystem.set(name, mapSystem);
    mapSystems.push(mapSystem);
  }

  const mapGates: MapGate[] = [];
  for (const gate of config.gates) {
    const fromId = nameToId.get(gate.from_system);
    const toId = nameToId.get(gate.to_system);
    if (fromId && toId) {
      mapGates.push({ fromSystemId: fromId, toSystemId: toId });
    }
  }

  return { systems: mapSystems, gates: mapGates, nameToSystem };
}

export function JumpRangeMap({
  originSystem,
  destSystem,
  maxRangeLy,
  waypoints = [],
  onAddWaypoint,
  preferStations = true,
}: JumpRangeMapProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const quadtreeRef = useRef<Quadtree | null>(null);
  const [viewport, setViewport] = useState<MapViewport>({
    x: 0, y: 0, zoom: 1, width: 600, height: 400,
  });
  const [hoveredSystem, setHoveredSystem] = useState<MapSystem | null>(null);
  const isPanning = useRef(false);
  const panStart = useRef({ x: 0, y: 0 });

  // Load map config
  const { data: config } = useQuery({
    queryKey: ['mapConfig'],
    queryFn: () => GatekeeperAPI.getMapConfig(),
    staleTime: 5 * 60 * 1000,
  });

  const { systems: allSystems, gates: allGates, nameToSystem } = useMemo(() => {
    if (!config) return { systems: [], gates: [], nameToSystem: new Map<string, MapSystem>() };
    return transformConfig(config);
  }, [config]);

  // Resolve origin/dest to MapSystem
  const originSys = useMemo(
    () => (originSystem ? nameToSystem.get(originSystem) : undefined),
    [originSystem, nameToSystem]
  );
  const destSys = useMemo(
    () => (destSystem ? nameToSystem.get(destSystem) : undefined),
    [destSystem, nameToSystem]
  );

  // World-space jump range radius
  const rangeWorld = maxRangeLy / LY_CONVERSION;

  // Filter systems within range of origin OR destination
  const { visibleSystems, visibleGates, inRangeIds } = useMemo(() => {
    if (!originSys && !destSys) {
      return { visibleSystems: allSystems, visibleGates: allGates, inRangeIds: new Set<number>() };
    }

    const inRange = new Set<number>();
    // Generous bounding — show systems within 1.5x range for context
    const showRadius = rangeWorld * 1.5;

    for (const sys of allSystems) {
      let show = false;
      if (originSys) {
        const dx = sys.x - originSys.x;
        const dy = sys.y - originSys.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist <= showRadius) show = true;
        if (dist <= rangeWorld) inRange.add(sys.systemId);
      }
      if (destSys) {
        const dx = sys.x - destSys.x;
        const dy = sys.y - destSys.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist <= showRadius) show = true;
      }
      if (!show) {
        // Always include origin, dest, and waypoints
        const isWaypoint = waypoints.some((wp) => {
          const wpSys = nameToSystem.get(wp);
          return wpSys && wpSys.systemId === sys.systemId;
        });
        if (isWaypoint) show = true;
      }
      if (show) inRange.add(sys.systemId); // track all visible for gate filtering
    }

    // Re-filter: systems actually in cyno range (lowsec/nullsec only — no
    // highsec, WH, or Pochven). Origin is always included.
    const jumpRangeIds = new Set<number>();
    for (const sys of allSystems) {
      if (!originSys) continue;
      const dx = sys.x - originSys.x;
      const dy = sys.y - originSys.y;
      if (Math.sqrt(dx * dx + dy * dy) <= rangeWorld) {
        // Only cyno-eligible systems: lowsec/nullsec, not Pochven
        // Always include origin itself
        if ((sys.security < 0.45 && sys.regionName !== 'Pochven') || sys.systemId === originSys.systemId) {
          jumpRangeIds.add(sys.systemId);
        }
      }
    }

    const visSys = allSystems.filter((s) => inRange.has(s.systemId));
    const visGates = allGates.filter(
      (g) => inRange.has(g.fromSystemId) && inRange.has(g.toSystemId)
    );

    return { visibleSystems: visSys, visibleGates: visGates, inRangeIds: jumpRangeIds };
  }, [allSystems, allGates, originSys, destSys, rangeWorld, waypoints, nameToSystem]);

  // Build quadtree for click detection
  useEffect(() => {
    if (visibleSystems.length > 0) {
      quadtreeRef.current = buildQuadtree(visibleSystems);
    }
  }, [visibleSystems]);

  // Waypoint system IDs for highlighting
  const waypointIds = useMemo(() => {
    const ids = new Set<number>();
    for (const wp of waypoints) {
      const sys = nameToSystem.get(wp);
      if (sys) ids.add(sys.systemId);
    }
    return ids;
  }, [waypoints, nameToSystem]);

  // Fit viewport to visible systems on data load or origin change (deferred to avoid sync setState)
  useEffect(() => {
    if (visibleSystems.length === 0) return;
    const id = requestAnimationFrame(() => {
      const container = containerRef.current;
      const w = container?.clientWidth ?? 600;
      const h = container?.clientHeight ?? 400;
      const fit = calculateFitZoom(visibleSystems, w, h, 40);
      setViewport({ x: fit.x, y: fit.y, zoom: fit.zoom, width: w, height: h });
    });
    return () => cancelAnimationFrame(id);
  }, [visibleSystems, originSystem, destSystem]);

  // Resize observer
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setViewport((v) => ({
          ...v,
          width: entry.contentRect.width,
          height: entry.contentRect.height,
        }));
      }
    });
    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  // Build system lookup for rendering
  const systemById = useMemo(() => {
    const map = new Map<number, MapSystem>();
    for (const s of visibleSystems) map.set(s.systemId, s);
    return map;
  }, [visibleSystems]);

  // Render canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = viewport.width * dpr;
    canvas.height = viewport.height * dpr;
    ctx.scale(dpr, dpr);

    // Clear
    ctx.fillStyle = '#0a0e17';
    ctx.fillRect(0, 0, viewport.width, viewport.height);

    // Draw jump range circle from origin
    if (originSys) {
      const center = worldToScreen(originSys.x, originSys.y, viewport);
      const edgePoint = worldToScreen(originSys.x + rangeWorld, originSys.y, viewport);
      const radius = edgePoint.x - center.x;

      ctx.beginPath();
      ctx.arc(center.x, center.y, radius, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(59, 130, 246, 0.06)';
      ctx.fill();
      ctx.strokeStyle = 'rgba(59, 130, 246, 0.25)';
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // Draw gate lines (faint, for context)
    ctx.lineWidth = 0.3;
    ctx.strokeStyle = '#334155';
    ctx.globalAlpha = 0.3;
    for (const gate of visibleGates) {
      const from = systemById.get(gate.fromSystemId);
      const to = systemById.get(gate.toSystemId);
      if (!from || !to) continue;
      const p1 = worldToScreen(from.x, from.y, viewport);
      const p2 = worldToScreen(to.x, to.y, viewport);
      ctx.beginPath();
      ctx.moveTo(p1.x, p1.y);
      ctx.lineTo(p2.x, p2.y);
      ctx.stroke();
    }
    ctx.globalAlpha = 1;

    // Draw jump route legs (waypoint connections)
    if (waypoints.length >= 2) {
      ctx.lineWidth = 2;
      ctx.strokeStyle = '#f59e0b';
      ctx.globalAlpha = 0.8;
      ctx.setLineDash([6, 3]);
      for (let i = 0; i < waypoints.length - 1; i++) {
        const fromSys = nameToSystem.get(waypoints[i]);
        const toSys = nameToSystem.get(waypoints[i + 1]);
        if (!fromSys || !toSys) continue;
        const p1 = worldToScreen(fromSys.x, fromSys.y, viewport);
        const p2 = worldToScreen(toSys.x, toSys.y, viewport);
        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.stroke();
      }
      ctx.setLineDash([]);
      ctx.globalAlpha = 1;
    }

    // Draw systems
    for (const sys of visibleSystems) {
      const pos = worldToScreen(sys.x, sys.y, viewport);
      const isOrigin = originSys && sys.systemId === originSys.systemId;
      const isDest = destSys && sys.systemId === destSys.systemId;
      const isWaypoint = waypointIds.has(sys.systemId);
      const isInRange = inRangeIds.has(sys.systemId);
      const isHovered = hoveredSystem?.systemId === sys.systemId;
      const hasStation = (sys.npcStations ?? 0) > 0;

      let radius = 2;
      let color = getSecurityColor(sys.security);
      let alpha = isInRange ? 1.0 : 0.25;

      // Station systems get a slightly larger dot when preferStations is on
      if (preferStations && hasStation && isInRange) {
        radius = 2.5;
      }

      // Origin/dest/waypoint special rendering
      if (isOrigin || isDest) {
        radius = 5;
        alpha = 1;
        color = isOrigin ? '#22c55e' : '#ef4444';
      } else if (isWaypoint) {
        radius = 4;
        alpha = 1;
        color = '#f59e0b';
      }

      if (isHovered) {
        radius += 2;
        ctx.shadowColor = color;
        ctx.shadowBlur = 8;
      }

      ctx.globalAlpha = alpha;
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, radius, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.fill();

      // Station halo — bright cyan glow ring that pops against the dark bg
      if (hasStation && isInRange && !isOrigin && !isDest && !isWaypoint) {
        const haloRadius = radius + 3;
        ctx.save();
        ctx.shadowColor = '#22d3ee';
        ctx.shadowBlur = 6;
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, haloRadius, 0, Math.PI * 2);
        ctx.strokeStyle = 'rgba(34, 211, 238, 0.6)';
        ctx.lineWidth = 1.2;
        ctx.stroke();
        ctx.restore();
      }

      ctx.shadowColor = 'transparent';
      ctx.shadowBlur = 0;
      ctx.globalAlpha = 1;

      // Labels for origin, dest, waypoints, and hovered
      if (isOrigin || isDest || isWaypoint || isHovered) {
        ctx.font = '11px system-ui, sans-serif';
        ctx.fillStyle = '#e2e8f0';
        ctx.textAlign = 'center';
        ctx.fillText(sys.name, pos.x, pos.y - radius - 4);
      }
    }

    // Legend
    ctx.font = '10px system-ui, sans-serif';
    ctx.textAlign = 'left';
    const legendY = viewport.height - 12;
    // Origin
    ctx.fillStyle = '#22c55e';
    ctx.fillRect(8, legendY - 6, 8, 8);
    ctx.fillStyle = '#94a3b8';
    ctx.fillText('Origin', 20, legendY + 2);
    // Dest
    ctx.fillStyle = '#ef4444';
    ctx.fillRect(70, legendY - 6, 8, 8);
    ctx.fillStyle = '#94a3b8';
    ctx.fillText('Dest', 82, legendY + 2);
    // Waypoint
    ctx.fillStyle = '#f59e0b';
    ctx.fillRect(120, legendY - 6, 8, 8);
    ctx.fillStyle = '#94a3b8';
    ctx.fillText('Cyno', 132, legendY + 2);
    // Station (cyan halo)
    ctx.save();
    ctx.shadowColor = '#22d3ee';
    ctx.shadowBlur = 4;
    ctx.strokeStyle = 'rgba(34, 211, 238, 0.6)';
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.arc(178, legendY - 2, 5, 0, Math.PI * 2);
    ctx.stroke();
    ctx.restore();
    ctx.fillStyle = '#94a3b8';
    ctx.fillText('Station', 188, legendY + 2);

  }, [viewport, visibleSystems, visibleGates, systemById, originSys, destSys, waypointIds, inRangeIds, hoveredSystem, rangeWorld, nameToSystem, waypoints, preferStations]);

  // Mouse handlers
  const findSystemAtScreen = useCallback((screenX: number, screenY: number): MapSystem | null => {
    if (!quadtreeRef.current) return null;
    const world = screenToWorld(screenX, screenY, viewport);
    const hitRadius = Math.max(8, 12 / viewport.zoom) / viewport.zoom;
    return quadtreeRef.current.findNearest(world.x, world.y, hitRadius);
  }, [viewport]);

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    if (isPanning.current) {
      const dx = (x - panStart.current.x) / viewport.zoom;
      const dy = (y - panStart.current.y) / viewport.zoom;
      setViewport((v) => ({ ...v, x: v.x - dx, y: v.y - dy }));
      panStart.current = { x, y };
      return;
    }

    const sys = findSystemAtScreen(x, y);
    setHoveredSystem(sys);
    if (canvasRef.current) {
      canvasRef.current.style.cursor = sys ? 'pointer' : 'grab';
    }
  }, [findSystemAtScreen, viewport.zoom]);

  const handleMouseDown = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    isPanning.current = true;
    panStart.current = { x: e.clientX - rect.left, y: e.clientY - rect.top };
  }, []);

  const handleMouseUp = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isPanning.current) return;
    isPanning.current = false;

    // If barely moved, treat as click
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const dx = x - panStart.current.x;
    const dy = y - panStart.current.y;
    if (Math.abs(dx) < 3 && Math.abs(dy) < 3) {
      const sys = findSystemAtScreen(x, y);
      if (sys && onAddWaypoint) {
        onAddWaypoint(sys.name);
      }
    }
  }, [findSystemAtScreen, onAddWaypoint]);

  const handleWheel = useCallback((e: React.WheelEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    setViewport((v) => ({
      ...v,
      zoom: Math.min(Math.max(v.zoom * delta, 0.1), 20),
    }));
  }, []);

  if (!config) {
    return (
      <div className="w-full h-64 bg-card border border-border rounded-lg flex items-center justify-center">
        <Loader2 className="h-5 w-5 animate-spin text-text-secondary" />
      </div>
    );
  }

  return (
    <div ref={containerRef} className="w-full h-80 lg:h-96 bg-[#0a0e17] border border-border rounded-lg overflow-hidden relative">
      <canvas
        ref={canvasRef}
        style={{ width: '100%', height: '100%' }}
        onMouseMove={handleMouseMove}
        onMouseDown={handleMouseDown}
        onMouseUp={handleMouseUp}
        onMouseLeave={() => {
          isPanning.current = false;
          setHoveredSystem(null);
        }}
        onWheel={handleWheel}
      />
      {/* Hover tooltip */}
      {hoveredSystem && (
        <div className="absolute top-2 right-2 bg-card/90 border border-border rounded px-2 py-1 text-xs pointer-events-none">
          <div className="font-medium text-text">{hoveredSystem.name}</div>
          <div className="text-text-secondary">
            Sec: {hoveredSystem.security.toFixed(1)}
            {(hoveredSystem.npcStations ?? 0) > 0 && ' · NPC Station'}
          </div>
          {originSys && (
            <div className="text-blue-400">
              {(Math.sqrt(
                (hoveredSystem.x - originSys.x) ** 2 + (hoveredSystem.y - originSys.y) ** 2
              ) * LY_CONVERSION).toFixed(2)} LY from origin
            </div>
          )}
          <div className="text-text-secondary mt-0.5">Click to add as waypoint</div>
        </div>
      )}
      {/* Range info */}
      {originSys && (
        <div className="absolute top-2 left-2 bg-card/90 border border-border rounded px-2 py-1 text-xs text-text-secondary">
          Jump range: {maxRangeLy.toFixed(1)} LY · {inRangeIds.size} systems in range
        </div>
      )}
    </div>
  );
}
