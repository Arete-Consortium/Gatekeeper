'use client';

import { useRef, useState, useEffect, useMemo, useCallback } from 'react';
import { Card, Button } from '@/components/ui';
import { GatekeeperAPI } from '@/lib/api';
import type { MapConfig, FWSystem, HotSystem } from '@/lib/types';
import { RefreshCw, Route, X } from 'lucide-react';
import { FWSystemDetail } from './FWSystemDetail';
import { FWSidebar } from './FWSidebar';

// ── Faction Configuration ────────────────────────────────────────────────────

const FACTION_COLORS: Record<number, { fill: string; name: string; shortName: string }> = {
  500001: { fill: '#c8aa00', name: 'Caldari State', shortName: 'Caldari' },
  500002: { fill: '#2a7fff', name: 'Minmatar Republic', shortName: 'Minmatar' },
  500003: { fill: '#c83232', name: 'Amarr Empire', shortName: 'Amarr' },
  500004: { fill: '#1e8c1e', name: 'Gallente Federation', shortName: 'Gallente' },
};

const WARZONES = [
  { name: 'Caldari / Gallente Warzone', factions: [500001, 500004] },
  { name: 'Amarr / Minmatar Warzone', factions: [500003, 500002] },
];

const WARZONE_BUTTONS = [
  { key: 'calgal', label: 'Caldari / Gallente', warzoneIdx: 0, colors: ['#c8aa00', '#1e8c1e'] },
  { key: 'amarrmin', label: 'Amarr / Minmatar', warzoneIdx: 1, colors: ['#c83232', '#2a7fff'] },
] as const;

interface FWSystemNode {
  systemId: number;
  name: string;
  x: number;
  y: number;
  security: number;
  regionName: string;
  constellationName: string;
  category: string;
  fw: FWSystem;
}

interface FWGateConnection {
  fromId: number;
  toId: number;
}

type WarzoneFilter = number | null;

// ── BFS pathfinding ─────────────────────────────────────────────────────────

function bfsFW(from: number, to: number, gates: FWGateConnection[]): number[] {
  if (from === to) return [from];
  const adj: Record<number, number[]> = {};
  for (const g of gates) {
    (adj[g.fromId] ??= []).push(g.toId);
    (adj[g.toId] ??= []).push(g.fromId);
  }
  const visited = new Set<number>([from]);
  const parent: Record<number, number> = {};
  const queue = [from];
  while (queue.length > 0) {
    const current = queue.shift()!;
    for (const neighbor of adj[current] || []) {
      if (visited.has(neighbor)) continue;
      visited.add(neighbor);
      parent[neighbor] = current;
      if (neighbor === to) {
        const path: number[] = [];
        let node: number | undefined = to;
        while (node !== undefined) { path.unshift(node); node = parent[node]; }
        return path;
      }
      queue.push(neighbor);
    }
  }
  return [];
}

// ── Precomputed screen positions ────────────────────────────────────────────

interface ScreenNode {
  systemId: number;
  sx: number;
  sy: number;
  r: number;
  node: FWSystemNode;
}

// ── Component ───────────────────────────────────────────────────────────────

export function FWMap() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ w: 900, h: 650 });
  const [hovered, setHovered] = useState<number | null>(null);
  const [selected, setSelected] = useState<number | null>(null);

  const [routeMode, setRouteMode] = useState(false);
  const [routeEndpoints, setRouteEndpoints] = useState<[number | null, number | null]>([null, null]);

  const [viewport, setViewport] = useState({ x: 0, y: 0, zoom: 1 });
  const dragRef = useRef<{ startX: number; startY: number; vpX: number; vpY: number } | null>(null);

  const [warzoneFilter, setWarzoneFilter] = useState<WarzoneFilter>(null);
  const [intelHours, setIntelHours] = useState(24);

  const [fwSystems, setFwSystems] = useState<FWSystemNode[]>([]);
  const [fwGates, setFwGates] = useState<FWGateConnection[]>([]);
  const [mapConfig, setMapConfig] = useState<MapConfig | null>(null);
  const [hotSystems, setHotSystems] = useState<HotSystem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Animation ref — no state updates, driven by rAF
  const pulseRef = useRef(0);
  const rafIdRef = useRef(0);

  // ── Fetch hot systems ────────────────────────────────────────────────────

  const fetchHotSystems = useCallback(async (hours: number) => {
    try {
      const hot = await GatekeeperAPI.getHotSystems(hours, 100);
      setHotSystems(hot);
    } catch { /* non-critical */ }
  }, []);

  const initialLoadDone = useRef(false);
  useEffect(() => {
    if (!initialLoadDone.current) return;
    fetchHotSystems(intelHours);
  }, [intelHours, fetchHotSystems]);

  // ── Fetch data ────────────────────────────────────────────────────────────

  useEffect(() => {
    let cancelled = false;
    async function fetchData() {
      try {
        const [config, fw, hot] = await Promise.all([
          GatekeeperAPI.getMapConfig(),
          GatekeeperAPI.getFWStatus(),
          GatekeeperAPI.getHotSystems(intelHours, 100),
        ]);
        if (cancelled) return;

        setMapConfig(config);
        setHotSystems(hot);
        initialLoadDone.current = true;

        const fwSystemIds = new Set(Object.keys(fw.fw_systems));
        const nodes: FWSystemNode[] = [];
        for (const [name, sys] of Object.entries(config.systems)) {
          const sidStr = String(sys.id);
          if (!fwSystemIds.has(sidStr)) continue;
          nodes.push({
            systemId: sys.id, name,
            x: sys.position.x, y: sys.position.y,
            security: sys.security,
            regionName: sys.region_name,
            constellationName: sys.constellation_name,
            category: sys.category,
            fw: fw.fw_systems[sidStr],
          });
        }

        const fwIdSet = new Set(nodes.map((n) => n.systemId));
        const gates: FWGateConnection[] = [];
        for (const gate of config.gates) {
          const fromSys = config.systems[gate.from_system];
          const toSys = config.systems[gate.to_system];
          if (fromSys && toSys && fwIdSet.has(fromSys.id) && fwIdSet.has(toSys.id)) {
            gates.push({ fromId: fromSys.id, toId: toSys.id });
          }
        }

        setFwSystems(nodes);
        setFwGates(gates);
        setLoading(false);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load FW data');
          setLoading(false);
        }
      }
    }
    fetchData();
    return () => { cancelled = true; };
  }, []);

  // ── Memoized derived data ─────────────────────────────────────────────────

  const filteredSystems = useMemo(() => {
    if (warzoneFilter === null) return fwSystems;
    const warzone = WARZONES[warzoneFilter];
    if (!warzone) return fwSystems;
    return fwSystems.filter((sys) =>
      warzone.factions.includes(sys.fw.owner_faction_id) ||
      warzone.factions.includes(sys.fw.occupier_faction_id)
    );
  }, [fwSystems, warzoneFilter]);

  const systemMap = useMemo(() => {
    const map = new Map<number, FWSystemNode>();
    for (const sys of fwSystems) map.set(sys.systemId, sys);
    return map;
  }, [fwSystems]);

  const hotSystemMap = useMemo(() => {
    const map = new Map<number, number>();
    for (const hs of hotSystems) map.set(hs.system_id, hs.recent_kills);
    return map;
  }, [hotSystems]);

  const routePath = useMemo(() => {
    const [a, b] = routeEndpoints;
    if (a && b) return bfsFW(a, b, fwGates);
    return [];
  }, [routeEndpoints, fwGates]);

  const routeEdgeSet = useMemo(() => {
    const edges = new Set<string>();
    for (let i = 0; i < routePath.length - 1; i++) {
      edges.add(`${routePath[i]}|${routePath[i + 1]}`);
      edges.add(`${routePath[i + 1]}|${routePath[i]}`);
    }
    return edges;
  }, [routePath]);

  const routeNodeSet = useMemo(() => new Set(routePath), [routePath]);

  // Memoize stats
  const stats = useMemo(() => {
    const factionCounts: Record<number, number> = {};
    const flippedCounts: Record<number, number> = {};
    let contestedCount = 0;
    let vulnerableCount = 0;

    for (const sys of fwSystems) {
      factionCounts[sys.fw.occupier_faction_id] = (factionCounts[sys.fw.occupier_faction_id] || 0) + 1;
      if (sys.fw.contested === 'contested' || sys.fw.contested === 'vulnerable') contestedCount++;
      if (sys.fw.contested === 'vulnerable') vulnerableCount++;
      if (sys.fw.occupier_faction_id !== sys.fw.owner_faction_id) {
        flippedCounts[sys.fw.occupier_faction_id] = (flippedCounts[sys.fw.occupier_faction_id] || 0) + 1;
      }
    }

    const fwKillCount = fwSystems.reduce((sum, sys) => sum + (hotSystemMap.get(sys.systemId) || 0), 0);
    return { factionCounts, flippedCounts, contestedCount, vulnerableCount, fwKillCount };
  }, [fwSystems, hotSystemMap]);

  const topHotFW = useMemo(() => {
    return hotSystems.filter((hs) => systemMap.has(hs.system_id)).slice(0, 10);
  }, [hotSystems, systemMap]);

  // ── Bounds and coordinate transform ───────────────────────────────────────

  const bounds = useMemo(() => {
    const systems = filteredSystems.length > 0 ? filteredSystems : fwSystems;
    if (systems.length === 0) return { minX: 0, maxX: 1, minY: 0, maxY: 1 };
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    for (const sys of systems) {
      if (sys.x < minX) minX = sys.x;
      if (sys.x > maxX) maxX = sys.x;
      if (sys.y < minY) minY = sys.y;
      if (sys.y > maxY) maxY = sys.y;
    }
    return { minX, maxX, minY, maxY };
  }, [filteredSystems, fwSystems]);

  const toCanvas = useCallback(
    (ux: number, uy: number) => {
      const pad = 60;
      const rangeX = bounds.maxX - bounds.minX || 1;
      const rangeY = bounds.maxY - bounds.minY || 1;
      const scale = Math.min((size.w - pad * 2) / rangeX, (size.h - pad * 2) / rangeY);
      const cx = (bounds.minX + bounds.maxX) / 2;
      const cy = (bounds.minY + bounds.maxY) / 2;
      const baseX = (ux - cx) * scale + size.w / 2;
      const baseY = (uy - cy) * scale + size.h / 2;
      return {
        x: (baseX - size.w / 2 - viewport.x) * viewport.zoom + size.w / 2,
        y: (baseY - size.h / 2 - viewport.y) * viewport.zoom + size.h / 2,
      };
    },
    [bounds, size, viewport]
  );

  // Precompute screen positions + radii for all visible systems
  const screenNodes = useMemo(() => {
    const baseR = Math.max(4, Math.min(8, size.w / 150));
    return filteredSystems.map((sys): ScreenNode => {
      const pos = toCanvas(sys.x, sys.y);
      const progress = sys.fw.victory_points_threshold > 0
        ? sys.fw.victory_points / sys.fw.victory_points_threshold : 0;
      return {
        systemId: sys.systemId,
        sx: pos.x, sy: pos.y,
        r: baseR + progress * baseR * 0.6,
        node: sys,
      };
    });
  }, [filteredSystems, toCanvas, size]);

  // ── Hit test using precomputed positions ──────────────────────────────────

  const hitTest = useCallback(
    (cx: number, cy: number): number | null => {
      // Reverse iterate so topmost (last drawn) is checked first
      for (let i = screenNodes.length - 1; i >= 0; i--) {
        const sn = screenNodes[i];
        const dx = cx - sn.sx;
        const dy = cy - sn.sy;
        const hitR = sn.r + 6;
        if (dx * dx + dy * dy <= hitR * hitR) return sn.systemId;
      }
      return null;
    },
    [screenNodes]
  );

  // ── Resize observer ───────────────────────────────────────────────────────

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const observer = new ResizeObserver((entries) => {
      const { width } = entries[0].contentRect;
      setSize({ w: Math.round(width), h: Math.min(Math.round(width * 0.72), 750) });
    });
    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  // ── Warzone filter ────────────────────────────────────────────────────────

  const handleWarzoneClick = useCallback((warzoneIdx: number) => {
    setWarzoneFilter((prev) => prev === warzoneIdx ? null : warzoneIdx);
    setViewport({ x: 0, y: 0, zoom: 1 });
    setSelected(null);
  }, []);

  const handleResetFilter = useCallback(() => {
    setWarzoneFilter(null);
    setViewport({ x: 0, y: 0, zoom: 1 });
    setSelected(null);
  }, []);

  // ── Mouse handlers ────────────────────────────────────────────────────────

  const handleClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const hit = hitTest(e.clientX - rect.left, e.clientY - rect.top);
    if (routeMode) {
      if (!hit) { setRouteEndpoints([null, null]); return; }
      setRouteEndpoints((prev) => {
        if (!prev[0]) return [hit, null];
        if (prev[0] === hit) return [null, null];
        if (prev[1]) return [hit, null];
        return [prev[0], hit];
      });
    } else {
      setSelected(hit);
    }
  }, [hitTest, routeMode]);

  const handleMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    if (dragRef.current) {
      const dx = (x - dragRef.current.startX) / viewport.zoom;
      const dy = (y - dragRef.current.startY) / viewport.zoom;
      setViewport((v) => ({ ...v, x: dragRef.current!.vpX - dx, y: dragRef.current!.vpY - dy }));
      return;
    }
    const hit = hitTest(x, y);
    setHovered(hit);
    canvas.style.cursor = hit ? 'pointer' : 'grab';
  }, [hitTest, viewport.zoom]);

  const handleMouseDown = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    if (!hitTest(x, y)) {
      dragRef.current = { startX: x, startY: y, vpX: viewport.x, vpY: viewport.y };
      canvas.style.cursor = 'grabbing';
    }
  }, [hitTest, viewport]);

  const handleMouseUp = useCallback(() => {
    dragRef.current = null;
    if (canvasRef.current) canvasRef.current.style.cursor = 'grab';
  }, []);

  // Smooth exponential zoom toward mouse position
  const handleWheel = useCallback((e: React.WheelEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;

    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;
    const clampedDelta = Math.max(-150, Math.min(150, e.deltaY));
    const factor = Math.pow(2, -clampedDelta * 0.002);

    setViewport((v) => {
      const newZoom = Math.max(0.3, Math.min(5, v.zoom * factor));
      // Zoom toward mouse position
      const wx = (mouseX - size.w / 2) / v.zoom + v.x;
      const wy = (mouseY - size.h / 2) / v.zoom + v.y;
      const newX = wx - (mouseX - size.w / 2) / newZoom;
      const newY = wy - (mouseY - size.h / 2) / newZoom;
      return { x: newX, y: newY, zoom: newZoom };
    });
  }, [size]);

  // ── Canvas draw via rAF ───────────────────────────────────────────────────

  const drawCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || fwSystems.length === 0) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    if (canvas.width !== size.w * dpr || canvas.height !== size.h * dpr) {
      canvas.width = size.w * dpr;
      canvas.height = size.h * dpr;
      canvas.style.width = `${size.w}px`;
      canvas.style.height = `${size.h}px`;
    }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    // Background
    ctx.fillStyle = '#0a0e17';
    ctx.fillRect(0, 0, size.w, size.h);

    const visibleIds = new Set(filteredSystems.map((s) => s.systemId));
    const pulse = (Math.sin(pulseRef.current) + 1) / 2;
    const killPulse = (Math.sin(pulseRef.current * 1.5) + 1) / 2;

    // ── Batch gates by type ─────────────────────────────────────────────

    // Build screen position lookup from precomputed nodes
    const posMap = new Map<number, { x: number; y: number }>();
    for (const sn of screenNodes) posMap.set(sn.systemId, { x: sn.sx, y: sn.sy });

    // Separate gates into batches for fewer state changes
    const routeGates: [number, number, number, number][] = [];
    const sameWarzoneGates: Map<string, [number, number, number, number][]> = new Map();
    const crossGates: [number, number, number, number][] = [];

    for (const gate of fwGates) {
      if (!visibleIds.has(gate.fromId) || !visibleIds.has(gate.toId)) continue;
      const fp = posMap.get(gate.fromId);
      const tp = posMap.get(gate.toId);
      if (!fp || !tp) continue;

      // Cull off-screen
      if ((fp.x < -50 && tp.x < -50) || (fp.x > size.w + 50 && tp.x > size.w + 50) ||
          (fp.y < -50 && tp.y < -50) || (fp.y > size.h + 50 && tp.y > size.h + 50)) continue;

      const seg: [number, number, number, number] = [fp.x, fp.y, tp.x, tp.y];

      if (routeEdgeSet.has(`${gate.fromId}|${gate.toId}`)) {
        routeGates.push(seg);
        continue;
      }

      const fromSys = systemMap.get(gate.fromId);
      const toSys = systemMap.get(gate.toId);
      if (!fromSys || !toSys) continue;

      const sameWZ = WARZONES.some(
        (wz) => wz.factions.includes(fromSys.fw.occupier_faction_id) &&
                wz.factions.includes(toSys.fw.occupier_faction_id)
      );

      if (sameWZ) {
        const color = FACTION_COLORS[fromSys.fw.occupier_faction_id]?.fill || '#334155';
        let batch = sameWarzoneGates.get(color);
        if (!batch) { batch = []; sameWarzoneGates.set(color, batch); }
        batch.push(seg);
      } else {
        crossGates.push(seg);
      }
    }

    // Draw same-warzone gates (batched by color)
    for (const [color, segs] of sameWarzoneGates) {
      ctx.strokeStyle = color;
      ctx.globalAlpha = 0.4;
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      for (const [x1, y1, x2, y2] of segs) {
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
      }
      ctx.stroke();
    }
    ctx.globalAlpha = 1;

    // Draw cross-warzone gates (batched)
    if (crossGates.length > 0) {
      ctx.save();
      ctx.setLineDash([4, 3]);
      ctx.strokeStyle = '#334155';
      ctx.globalAlpha = 0.2;
      ctx.lineWidth = 0.8;
      ctx.beginPath();
      for (const [x1, y1, x2, y2] of crossGates) {
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
      }
      ctx.stroke();
      ctx.restore();
    }

    // Draw route gates
    if (routeGates.length > 0) {
      ctx.save();
      ctx.strokeStyle = '#22d3ee';
      ctx.lineWidth = 3;
      ctx.shadowColor = '#22d3ee';
      ctx.shadowBlur = 8;
      ctx.beginPath();
      for (const [x1, y1, x2, y2] of routeGates) {
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
      }
      ctx.stroke();
      ctx.restore();
    }

    // ── Draw systems ────────────────────────────────────────────────────

    for (const sn of screenNodes) {
      const { sx, sy, r, node: sys, systemId } = sn;

      // Cull
      if (sx < -30 || sx > size.w + 30 || sy < -30 || sy > size.h + 30) continue;

      const faction = FACTION_COLORS[sys.fw.occupier_faction_id];
      if (!faction) continue;

      const isHov = hovered === systemId;
      const isSel = selected === systemId;
      const isRouteNode = routeNodeSet.has(systemId);
      const isRouteEP = routeEndpoints[0] === systemId || routeEndpoints[1] === systemId;
      const isContested = sys.fw.contested === 'contested' || sys.fw.contested === 'vulnerable';
      const isVulnerable = sys.fw.contested === 'vulnerable';
      const drawR = isHov ? r + 2 : r;
      const killCount = hotSystemMap.get(systemId) || 0;

      ctx.save();

      // Kill halo
      if (killCount > 0) {
        const intensity = Math.min(killCount / 30, 1);
        const killR = drawR + 8 + killPulse * 4 * intensity;
        ctx.beginPath();
        ctx.arc(sx, sy, killR, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255, 69, 58, ${0.08 + killPulse * 0.12 * intensity})`;
        ctx.fill();
        ctx.strokeStyle = `rgba(255, 69, 58, ${0.2 + killPulse * 0.3 * intensity})`;
        ctx.lineWidth = 1;
        ctx.stroke();
      }

      // Contested pulse
      if (isContested) {
        ctx.beginPath();
        ctx.arc(sx, sy, drawR + 4 + pulse * 2, 0, Math.PI * 2);
        ctx.strokeStyle = isVulnerable
          ? `rgba(255, 69, 58, ${0.3 + pulse * 0.4})`
          : `rgba(255, 214, 10, ${0.2 + pulse * 0.3})`;
        ctx.lineWidth = 1.5;
        ctx.setLineDash([3, 3]);
        ctx.stroke();
        ctx.setLineDash([]);
      }

      // Selection / route ring
      if (isSel || isRouteEP) {
        ctx.beginPath();
        ctx.arc(sx, sy, drawR + 3, 0, Math.PI * 2);
        ctx.strokeStyle = '#22d3ee';
        ctx.lineWidth = 2;
        ctx.shadowColor = '#22d3ee';
        ctx.shadowBlur = isRouteEP ? 12 : 8;
        ctx.stroke();
        ctx.shadowBlur = 0;
      } else if (isRouteNode) {
        ctx.beginPath();
        ctx.arc(sx, sy, drawR + 2, 0, Math.PI * 2);
        ctx.strokeStyle = 'rgba(34, 211, 238, 0.5)';
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }

      // System dot
      ctx.beginPath();
      ctx.arc(sx, sy, drawR, 0, Math.PI * 2);
      ctx.fillStyle = isSel || isRouteEP ? '#22d3ee' : faction.fill;
      ctx.fill();

      // Owner ring (flipped system)
      if (sys.fw.owner_faction_id !== sys.fw.occupier_faction_id) {
        const ownerFaction = FACTION_COLORS[sys.fw.owner_faction_id];
        if (ownerFaction) {
          ctx.beginPath();
          ctx.arc(sx, sy, drawR, 0, Math.PI * 2);
          ctx.strokeStyle = ownerFaction.fill;
          ctx.lineWidth = 2;
          ctx.stroke();
        }
      }

      // Kill badge
      if (killCount > 0 && viewport.zoom >= 0.7) {
        const bx = sx + drawR + 2;
        const by = sy - drawR - 2;
        const text = killCount > 99 ? '99+' : String(killCount);
        ctx.font = 'bold 8px system-ui, -apple-system, sans-serif';
        const tw = ctx.measureText(text).width;
        const bw = Math.max(tw + 4, 14);
        ctx.fillStyle = '#dc2626';
        ctx.fillRect(bx - bw / 2, by - 6, bw, 12);
        ctx.fillStyle = '#ffffff';
        ctx.textAlign = 'center';
        ctx.fillText(text, bx, by + 3);
      }

      ctx.restore();

      // Labels
      const showLabel = viewport.zoom >= 0.8 || isHov || isSel || isRouteNode;
      if (showLabel) {
        const fontSize = Math.max(9, Math.min(12, size.w / 90 * viewport.zoom));
        ctx.font = `${fontSize}px system-ui, -apple-system, sans-serif`;
        ctx.textAlign = 'center';
        ctx.fillStyle = '#000000';
        ctx.globalAlpha = 0.6;
        ctx.fillText(sys.name, sx + 0.5, sy + drawR + fontSize - 1.5);
        ctx.fillStyle = isSel || isHov || isRouteNode ? '#ffffff' : '#94a3b8';
        ctx.globalAlpha = isSel || isHov || isRouteNode ? 1 : 0.85;
        ctx.fillText(sys.name, sx, sy + drawR + fontSize - 2);
        ctx.globalAlpha = 1;
      }
    }

    // ── Legend ───────────────────────────────────────────────────────────

    const lx = 12;
    const ly = size.h - 120;
    ctx.font = '11px system-ui, -apple-system, sans-serif';
    ctx.textAlign = 'left';

    for (const [i, [, info]] of Object.entries(FACTION_COLORS).entries()) {
      const y = ly + i * 18;
      ctx.beginPath();
      ctx.arc(lx + 6, y, 5, 0, Math.PI * 2);
      ctx.fillStyle = info.fill;
      ctx.fill();
      ctx.fillStyle = '#94a3b8';
      ctx.fillText(info.shortName, lx + 16, y + 4);
    }

    const cy1 = ly + 4 * 18;
    ctx.save();
    ctx.beginPath();
    ctx.arc(lx + 6, cy1, 5, 0, Math.PI * 2);
    ctx.strokeStyle = '#ffd60a';
    ctx.lineWidth = 1.5;
    ctx.setLineDash([3, 3]);
    ctx.stroke();
    ctx.restore();
    ctx.fillStyle = '#94a3b8';
    ctx.fillText('Contested', lx + 16, cy1 + 4);

    const vy = cy1 + 18;
    ctx.save();
    ctx.beginPath();
    ctx.arc(lx + 6, vy, 5, 0, Math.PI * 2);
    ctx.strokeStyle = '#ff453a';
    ctx.lineWidth = 1.5;
    ctx.setLineDash([3, 3]);
    ctx.stroke();
    ctx.restore();
    ctx.fillStyle = '#94a3b8';
    ctx.fillText('Vulnerable', lx + 16, vy + 4);

    const ky = vy + 18;
    ctx.beginPath();
    ctx.arc(lx + 6, ky, 5, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(255, 69, 58, ${0.3 + killPulse * 0.4})`;
    ctx.fill();
    ctx.fillStyle = '#94a3b8';
    ctx.fillText('Kill activity', lx + 16, ky + 4);

    // Active warzone label
    if (warzoneFilter !== null) {
      const activeWarzone = WARZONES[warzoneFilter];
      if (activeWarzone) {
        ctx.font = 'bold 12px system-ui, -apple-system, sans-serif';
        const lw = ctx.measureText(activeWarzone.name).width;
        ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
        ctx.fillRect(size.w / 2 - lw / 2 - 12, 8, lw + 24, 24);
        ctx.fillStyle = WARZONE_BUTTONS[warzoneFilter]?.colors[0] || '#ffffff';
        ctx.textAlign = 'center';
        ctx.fillText(activeWarzone.name, size.w / 2, 25);
      }
    }
  }, [size, fwSystems, filteredSystems, fwGates, systemMap, hovered, selected,
      screenNodes, viewport, hotSystemMap, warzoneFilter, routeEdgeSet,
      routeNodeSet, routeEndpoints]);

  // ── Animation loop (rAF instead of setInterval + setState) ────────────

  useEffect(() => {
    if (fwSystems.length === 0) return;

    const hasAnimated = fwSystems.some(
      (s) => s.fw.contested === 'contested' || s.fw.contested === 'vulnerable'
    ) || hotSystems.length > 0;

    function frame() {
      if (hasAnimated) pulseRef.current += 0.1;
      drawCanvas();
      rafIdRef.current = requestAnimationFrame(frame);
    }

    // If nothing animated, draw once then stop
    if (!hasAnimated) {
      drawCanvas();
      return;
    }

    rafIdRef.current = requestAnimationFrame(frame);
    return () => cancelAnimationFrame(rafIdRef.current);
  }, [drawCanvas, fwSystems, hotSystems]);

  // Redraw on non-animated state changes
  useEffect(() => { drawCanvas(); }, [drawCanvas]);

  // ── Selected system detail ────────────────────────────────────────────────

  const selectedSystem = useMemo(() => {
    if (!selected || !mapConfig) return null;
    const sys = systemMap.get(selected);
    if (!sys) return null;

    const adjacent: string[] = [];
    for (const gate of fwGates) {
      if (gate.fromId === selected) {
        const adj = systemMap.get(gate.toId);
        if (adj) adjacent.push(adj.name);
      } else if (gate.toId === selected) {
        const adj = systemMap.get(gate.fromId);
        if (adj) adjacent.push(adj.name);
      }
    }

    const configSys = mapConfig.systems[sys.name];
    if (!configSys) return null;
    return { sys, configSys, adjacent };
  }, [selected, mapConfig, systemMap, fwGates]);

  // ── Render ────────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <Card className="p-8 text-center">
        <div className="text-text-secondary text-sm">Loading Faction Warfare data...</div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="p-8 text-center">
        <div className="text-red-400 text-sm">{error}</div>
      </Card>
    );
  }

  return (
    <div className="flex gap-3 relative">
      <div className="flex-1 min-w-0 space-y-3">
        {/* Toolbar */}
        <div className="flex items-center gap-2 min-h-[36px] flex-wrap">
          <Button
            variant={warzoneFilter === null ? 'primary' : 'ghost'}
            size="sm"
            onClick={handleResetFilter}
            className="text-xs h-7 px-3"
          >
            All FW ({fwSystems.length})
          </Button>
          {WARZONE_BUTTONS.map((btn) => {
            const isActive = warzoneFilter === btn.warzoneIdx;
            const count = WARZONES[btn.warzoneIdx].factions.reduce(
              (sum, fid) => sum + (stats.factionCounts[fid] || 0), 0
            );
            return (
              <button
                key={btn.key}
                onClick={() => handleWarzoneClick(btn.warzoneIdx)}
                className={`inline-flex items-center gap-1.5 text-xs font-medium px-3 h-7 rounded-md transition-all cursor-pointer ${
                  isActive ? 'shadow-md scale-105' : 'hover:brightness-125 hover:scale-105 opacity-80 hover:opacity-100'
                }`}
                style={{
                  backgroundColor: isActive ? 'rgba(255,255,255,0.1)' : 'rgba(255,255,255,0.05)',
                  color: isActive ? '#ffffff' : '#94a3b8',
                  border: isActive ? '2px solid rgba(255,255,255,0.3)' : '2px solid transparent',
                }}
              >
                <span className="flex gap-0.5">
                  {btn.colors.map((c, i) => (
                    <span key={i} className="w-2 h-2 rounded-full" style={{ backgroundColor: c }} />
                  ))}
                </span>
                {btn.label}: {count}
              </button>
            );
          })}

          <button
            onClick={() => { setRouteMode(!routeMode); setRouteEndpoints([null, null]); }}
            className={`inline-flex items-center gap-1 text-xs font-medium px-2.5 h-7 rounded-md transition-all cursor-pointer ${
              routeMode
                ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40'
                : 'text-text-secondary hover:text-text hover:bg-card-hover border border-transparent'
            }`}
          >
            <Route className="h-3.5 w-3.5" />
            Route
          </button>

          <div className="flex items-center gap-2 ml-auto">
            <span className="text-xs font-bold text-text uppercase tracking-wider">Intel</span>
            <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
            <span className="text-[10px] text-text-secondary hidden sm:inline">
              {stats.fwKillCount} kills · {hotSystems.reduce((s, h) => s + h.recent_pods, 0)} pods
            </span>
            <select
              value={intelHours}
              onChange={(e) => setIntelHours(Number(e.target.value))}
              className="text-[11px] bg-background border border-border rounded px-1.5 py-0.5 text-text cursor-pointer focus:outline-none focus:ring-1 focus:ring-primary h-7"
            >
              <option value={1}>1h</option>
              <option value={4}>4h</option>
              <option value={12}>12h</option>
              <option value={24}>24h</option>
              <option value={48}>48h</option>
            </select>
            <button
              onClick={() => fetchHotSystems(intelHours)}
              className="text-text-secondary hover:text-text transition-colors"
              aria-label="Refresh intel"
            >
              <RefreshCw className="h-3 w-3" />
            </button>
          </div>
        </div>

        {/* Route info */}
        {routeMode && (
          <div className="flex items-center gap-2 text-xs px-1">
            {!routeEndpoints[0] ? (
              <span className="text-text-secondary">Click a system to set route origin</span>
            ) : !routeEndpoints[1] ? (
              <div className="flex items-center gap-2">
                <span className="text-cyan-400 font-medium">{systemMap.get(routeEndpoints[0])?.name}</span>
                <span className="text-text-secondary">→ Click destination</span>
              </div>
            ) : routePath.length > 0 ? (
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-cyan-400 font-medium">{systemMap.get(routeEndpoints[0])?.name}</span>
                <span className="text-text-secondary">→</span>
                <span className="text-cyan-400 font-medium">{systemMap.get(routeEndpoints[1])?.name}</span>
                <span className="bg-cyan-500/20 text-cyan-400 px-1.5 py-0.5 rounded text-[10px] font-medium">
                  {routePath.length - 1} {routePath.length - 1 === 1 ? 'jump' : 'jumps'}
                </span>
                <span className="text-text-secondary hidden sm:inline">
                  {routePath.map((id) => systemMap.get(id)?.name).join(' → ')}
                </span>
                <button onClick={() => setRouteEndpoints([null, null])} className="text-text-secondary hover:text-text ml-1">
                  <X className="h-3 w-3" />
                </button>
              </div>
            ) : (
              <span className="text-red-400">No route found</span>
            )}
          </div>
        )}

        {/* Canvas */}
        <div ref={containerRef} className="w-full relative rounded-lg border border-border overflow-hidden" style={{ backgroundColor: '#0a0e17' }}>
          <canvas
            ref={canvasRef}
            onClick={handleClick}
            onMouseMove={handleMove}
            onMouseDown={handleMouseDown}
            onMouseUp={handleMouseUp}
            onMouseLeave={() => { setHovered(null); handleMouseUp(); }}
            onWheel={handleWheel}
            className="w-full"
            style={{ touchAction: 'none', cursor: 'grab' }}
          />

          {selectedSystem && (
            <FWSystemDetail
              systemName={selectedSystem.sys.name}
              systemData={selectedSystem.configSys}
              fwData={selectedSystem.sys.fw}
              adjacentSystems={selectedSystem.adjacent}
              killCount={hotSystemMap.get(selected!) || 0}
              onClose={() => setSelected(null)}
            />
          )}
        </div>

        <div className="text-[10px] text-text-secondary text-center">
          Scroll to zoom · Drag to pan · {routeMode ? 'Click two systems to route' : 'Click a system for details'}
        </div>
      </div>

      <FWSidebar
        fwSystems={fwSystems}
        factionCounts={stats.factionCounts}
        flippedCounts={stats.flippedCounts}
        contestedCount={stats.contestedCount}
        vulnerableCount={stats.vulnerableCount}
        fwKillCount={stats.fwKillCount}
        topHotSystems={topHotFW}
        systemMap={systemMap}
        onSystemClick={(systemId) => setSelected(systemId)}
        intelHours={intelHours}
      />
    </div>
  );
}
