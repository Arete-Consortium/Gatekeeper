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

// Warzone groupings: which factions fight each other
const WARZONES = [
  { name: 'Caldari / Gallente Warzone', factions: [500001, 500004] },
  { name: 'Amarr / Minmatar Warzone', factions: [500003, 500002] },
];

// Warzone button configs
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

type WarzoneFilter = number | null; // null = all, 0 = Cal/Gal, 1 = Amarr/Min

// ── BFS pathfinding through FW gates ────────────────────────────────────────

function bfsFW(
  from: number,
  to: number,
  gates: FWGateConnection[]
): number[] {
  if (from === to) return [from];

  const adj: Record<number, number[]> = {};
  for (const g of gates) {
    if (!adj[g.fromId]) adj[g.fromId] = [];
    if (!adj[g.toId]) adj[g.toId] = [];
    adj[g.fromId].push(g.toId);
    adj[g.toId].push(g.fromId);
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
        while (node !== undefined) {
          path.unshift(node);
          node = parent[node];
        }
        return path;
      }
      queue.push(neighbor);
    }
  }
  return []; // unreachable
}

// ── Component ────────────────────────────────────────────────────────────────

export function FWMap() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ w: 900, h: 650 });
  const [hovered, setHovered] = useState<number | null>(null);
  const [selected, setSelected] = useState<number | null>(null);

  // Route planner
  const [routeMode, setRouteMode] = useState(false);
  const [routeEndpoints, setRouteEndpoints] = useState<[number | null, number | null]>([null, null]);

  // Pan & zoom state
  const [viewport, setViewport] = useState({ x: 0, y: 0, zoom: 1 });
  const dragRef = useRef<{ startX: number; startY: number; vpX: number; vpY: number } | null>(null);

  // Warzone filter — null = show all, 0 = Cal/Gal, 1 = Amarr/Min
  const [warzoneFilter, setWarzoneFilter] = useState<WarzoneFilter>(null);
  const [intelHours, setIntelHours] = useState(24);

  // Data
  const [fwSystems, setFwSystems] = useState<FWSystemNode[]>([]);
  const [fwGates, setFwGates] = useState<FWGateConnection[]>([]);
  const [mapConfig, setMapConfig] = useState<MapConfig | null>(null);
  const [fwData, setFwData] = useState<Record<string, FWSystem>>({});
  const [hotSystems, setHotSystems] = useState<HotSystem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Contested pulse animation
  const pulseRef = useRef(0);
  const [, setFrame] = useState(0);

  // ── Fetch hot systems when hours change ─────────────────────────────────────

  const fetchHotSystems = useCallback(async (hours: number) => {
    try {
      const hot = await GatekeeperAPI.getHotSystems(hours, 100);
      setHotSystems(hot);
    } catch {
      // Non-critical — keep existing data
    }
  }, []);

  // Re-fetch when intelHours changes (skip initial — handled by main fetch)
  const initialLoadDone = useRef(false);
  useEffect(() => {
    if (!initialLoadDone.current) return;
    fetchHotSystems(intelHours);
  }, [intelHours, fetchHotSystems]);

  // ── Fetch data ──────────────────────────────────────────────────────────────

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
        setFwData(fw.fw_systems);
        setHotSystems(hot);
        initialLoadDone.current = true;

        // Build FW system nodes
        const fwSystemIds = new Set(Object.keys(fw.fw_systems));
        const nodes: FWSystemNode[] = [];

        for (const [name, sys] of Object.entries(config.systems)) {
          const sidStr = String(sys.id);
          if (!fwSystemIds.has(sidStr)) continue;

          const fwInfo = fw.fw_systems[sidStr];
          nodes.push({
            systemId: sys.id,
            name,
            x: sys.position.x,
            y: sys.position.y,
            security: sys.security,
            regionName: sys.region_name,
            constellationName: sys.constellation_name,
            category: sys.category,
            fw: fwInfo,
          });
        }

        // Filter gate connections to only FW systems
        const fwIdSet = new Set(nodes.map((n) => n.systemId));
        const gates: FWGateConnection[] = [];
        for (const gate of config.gates) {
          const fromSys = config.systems[gate.from_system];
          const toSys = config.systems[gate.to_system];
          if (!fromSys || !toSys) continue;
          if (fwIdSet.has(fromSys.id) && fwIdSet.has(toSys.id)) {
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

  // ── Filtered systems for display ──────────────────────────────────────────

  // Visible systems based on warzone filter
  const visibleSystems = useMemo(() => {
    if (warzoneFilter === null) return fwSystems;
    const warzone = WARZONES[warzoneFilter];
    if (!warzone) return fwSystems;
    return fwSystems.filter((sys) =>
      warzone.factions.includes(sys.fw.owner_faction_id) ||
      warzone.factions.includes(sys.fw.occupier_faction_id)
    );
  }, [fwSystems, warzoneFilter]);

  // Hot system lookup (system_id -> kills)
  const hotSystemMap = useMemo(() => {
    const map = new Map<number, number>();
    for (const hs of hotSystems) map.set(hs.system_id, hs.recent_kills);
    return map;
  }, [hotSystems]);

  // Route path (BFS through visible FW gates)
  const routePath = useMemo(() => {
    const [a, b] = routeEndpoints;
    if (a && b) return bfsFW(a, b, fwGates);
    return [];
  }, [routeEndpoints, fwGates]);

  const routeEdges = useMemo(() => {
    const edges = new Set<string>();
    for (let i = 0; i < routePath.length - 1; i++) {
      edges.add(`${routePath[i]}|${routePath[i + 1]}`);
      edges.add(`${routePath[i + 1]}|${routePath[i]}`);
    }
    return edges;
  }, [routePath]);

  // ── Coordinate mapping ──────────────────────────────────────────────────────

  // Compute bounds of visible systems for viewport fitting
  const bounds = useMemo(() => {
    const systems = visibleSystems.length > 0 ? visibleSystems : fwSystems;
    if (systems.length === 0) return { minX: 0, maxX: 1, minY: 0, maxY: 1 };
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    for (const sys of systems) {
      if (sys.x < minX) minX = sys.x;
      if (sys.x > maxX) maxX = sys.x;
      if (sys.y < minY) minY = sys.y;
      if (sys.y > maxY) maxY = sys.y;
    }
    return { minX, maxX, minY, maxY };
  }, [visibleSystems, fwSystems]);

  // Map universe coordinates to canvas coordinates
  const toCanvas = useCallback(
    (ux: number, uy: number) => {
      const pad = 60;
      const rangeX = bounds.maxX - bounds.minX || 1;
      const rangeY = bounds.maxY - bounds.minY || 1;
      const scaleX = (size.w - pad * 2) / rangeX;
      const scaleY = (size.h - pad * 2) / rangeY;
      const scale = Math.min(scaleX, scaleY);

      const centerX = (bounds.minX + bounds.maxX) / 2;
      const centerY = (bounds.minY + bounds.maxY) / 2;

      const baseX = (ux - centerX) * scale + size.w / 2;
      const baseY = (uy - centerY) * scale + size.h / 2;

      // Apply pan & zoom
      return {
        x: (baseX - size.w / 2 - viewport.x) * viewport.zoom + size.w / 2,
        y: (baseY - size.h / 2 - viewport.y) * viewport.zoom + size.h / 2,
      };
    },
    [bounds, size, viewport]
  );

  // System lookup map
  const systemMap = useMemo(() => {
    const map = new Map<number, FWSystemNode>();
    for (const sys of fwSystems) map.set(sys.systemId, sys);
    return map;
  }, [fwSystems]);

  // Node radius scales with VP progress
  const getNodeRadius = useCallback(
    (fw: FWSystem) => {
      const base = Math.max(4, Math.min(8, size.w / 150));
      const progress = fw.victory_points_threshold > 0
        ? fw.victory_points / fw.victory_points_threshold
        : 0;
      return base + progress * base * 0.6;
    },
    [size]
  );

  // ── Warzone filter zoom ──────────────────────────────────────────────────

  const handleWarzoneClick = useCallback(
    (warzoneIdx: number) => {
      if (warzoneFilter === warzoneIdx) {
        setWarzoneFilter(null);
        setViewport({ x: 0, y: 0, zoom: 1 });
      } else {
        setWarzoneFilter(warzoneIdx);
        setViewport({ x: 0, y: 0, zoom: 1 });
      }
      setSelected(null);
    },
    [warzoneFilter]
  );

  const handleResetFilter = useCallback(() => {
    setWarzoneFilter(null);
    setViewport({ x: 0, y: 0, zoom: 1 });
    setSelected(null);
  }, []);

  // ── Hit test ────────────────────────────────────────────────────────────────

  const hitTest = useCallback(
    (cx: number, cy: number): number | null => {
      for (const sys of visibleSystems) {
        const pos = toCanvas(sys.x, sys.y);
        const r = getNodeRadius(sys.fw) + 6;
        const dx = cx - pos.x;
        const dy = cy - pos.y;
        if (dx * dx + dy * dy <= r * r) return sys.systemId;
      }
      return null;
    },
    [visibleSystems, toCanvas, getNodeRadius]
  );

  // ── Resize observer ─────────────────────────────────────────────────────────

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const observer = new ResizeObserver((entries) => {
      const { width } = entries[0].contentRect;
      const h = Math.min(Math.round(width * 0.72), 750);
      setSize({ w: Math.round(width), h });
    });
    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  // ── Mouse handlers ──────────────────────────────────────────────────────────

  const handleClick = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const hit = hitTest(x, y);

      if (routeMode) {
        if (!hit) {
          setRouteEndpoints([null, null]);
          return;
        }
        setRouteEndpoints((prev) => {
          if (!prev[0]) return [hit, null];
          if (prev[0] === hit) return [null, null];
          if (prev[1]) return [hit, null]; // reset and start new route
          return [prev[0], hit];
        });
      } else {
        setSelected(hit);
      }
    },
    [hitTest, routeMode]
  );

  const handleMove = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      // Handle drag
      if (dragRef.current) {
        const dx = (x - dragRef.current.startX) / viewport.zoom;
        const dy = (y - dragRef.current.startY) / viewport.zoom;
        setViewport((v) => ({
          ...v,
          x: dragRef.current!.vpX - dx,
          y: dragRef.current!.vpY - dy,
        }));
        return;
      }

      const hit = hitTest(x, y);
      setHovered(hit);
      canvas.style.cursor = hit ? 'pointer' : 'grab';
    },
    [hitTest, viewport.zoom]
  );

  const handleMouseDown = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const hit = hitTest(x, y);
      if (!hit) {
        dragRef.current = { startX: x, startY: y, vpX: viewport.x, vpY: viewport.y };
        canvas.style.cursor = 'grabbing';
      }
    },
    [hitTest, viewport]
  );

  const handleMouseUp = useCallback(() => {
    dragRef.current = null;
    const canvas = canvasRef.current;
    if (canvas) canvas.style.cursor = 'grab';
  }, []);

  const handleWheel = useCallback(
    (e: React.WheelEvent<HTMLCanvasElement>) => {
      e.preventDefault();
      const delta = e.deltaY > 0 ? 0.9 : 1.1;
      setViewport((v) => ({
        ...v,
        zoom: Math.max(0.3, Math.min(5, v.zoom * delta)),
      }));
    },
    []
  );

  // ── Canvas draw ─────────────────────────────────────────────────────────────

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || fwSystems.length === 0) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = size.w * dpr;
    canvas.height = size.h * dpr;
    canvas.style.width = `${size.w}px`;
    canvas.style.height = `${size.h}px`;
    ctx.scale(dpr, dpr);

    // Background
    ctx.fillStyle = '#0a0e17';
    ctx.fillRect(0, 0, size.w, size.h);

    // Visible system IDs for quick lookup
    const visibleIds = new Set(visibleSystems.map((s) => s.systemId));

    // Draw gate connections (only between visible systems)
    for (const gate of fwGates) {
      if (!visibleIds.has(gate.fromId) || !visibleIds.has(gate.toId)) continue;

      const fromSys = systemMap.get(gate.fromId);
      const toSys = systemMap.get(gate.toId);
      if (!fromSys || !toSys) continue;

      const fromPos = toCanvas(fromSys.x, fromSys.y);
      const toPos = toCanvas(toSys.x, toSys.y);

      // Skip off-screen connections
      if (
        fromPos.x < -50 && toPos.x < -50 ||
        fromPos.x > size.w + 50 && toPos.x > size.w + 50 ||
        fromPos.y < -50 && toPos.y < -50 ||
        fromPos.y > size.h + 50 && toPos.y > size.h + 50
      ) continue;

      // Color based on whether same warzone
      const fromFaction = fromSys.fw.occupier_faction_id;
      const toFaction = toSys.fw.occupier_faction_id;
      const sameWarzone = WARZONES.some(
        (wz) => wz.factions.includes(fromFaction) && wz.factions.includes(toFaction)
      );

      const isRouteEdge = routeEdges.has(`${gate.fromId}|${gate.toId}`);

      ctx.save();
      ctx.beginPath();
      ctx.moveTo(fromPos.x, fromPos.y);
      ctx.lineTo(toPos.x, toPos.y);

      if (isRouteEdge) {
        ctx.strokeStyle = '#22d3ee';
        ctx.lineWidth = 3;
        ctx.shadowColor = '#22d3ee';
        ctx.shadowBlur = 8;
      } else if (sameWarzone) {
        // Subway-style: color gate by occupier faction of 'from' system
        const factionColor = FACTION_COLORS[fromFaction]?.fill || '#334155';
        ctx.strokeStyle = factionColor;
        ctx.globalAlpha = 0.4;
        ctx.lineWidth = 1.5;
      } else {
        ctx.setLineDash([4, 3]);
        ctx.strokeStyle = '#334155';
        ctx.globalAlpha = 0.2;
        ctx.lineWidth = 0.8;
      }
      ctx.stroke();
      ctx.globalAlpha = 1;
      ctx.restore();
    }

    // Pulse value for contested systems and kill markers
    const pulse = (Math.sin(pulseRef.current) + 1) / 2;
    const killPulse = (Math.sin(pulseRef.current * 1.5) + 1) / 2;

    // Draw system nodes
    for (const sys of visibleSystems) {
      const pos = toCanvas(sys.x, sys.y);

      // Skip off-screen
      if (pos.x < -30 || pos.x > size.w + 30 || pos.y < -30 || pos.y > size.h + 30) continue;

      const faction = FACTION_COLORS[sys.fw.occupier_faction_id];
      if (!faction) continue;

      const r = getNodeRadius(sys.fw);
      const isHovered = hovered === sys.systemId;
      const isSelected = selected === sys.systemId;
      const isRouteNode = routePath.includes(sys.systemId);
      const isRouteEndpoint = routeEndpoints[0] === sys.systemId || routeEndpoints[1] === sys.systemId;
      const isContested = sys.fw.contested === 'contested' || sys.fw.contested === 'vulnerable';
      const isVulnerable = sys.fw.contested === 'vulnerable';
      const drawR = isHovered ? r + 2 : r;
      const killCount = hotSystemMap.get(sys.systemId) || 0;

      ctx.save();

      // Kill activity pulsing ring (pirate activity)
      if (killCount > 0) {
        const intensity = Math.min(killCount / 30, 1); // Normalize 0-30 kills
        const killR = drawR + 8 + killPulse * 4 * intensity;
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, killR, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255, 69, 58, ${0.08 + killPulse * 0.12 * intensity})`;
        ctx.fill();
        // Outer ring
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, killR, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(255, 69, 58, ${0.2 + killPulse * 0.3 * intensity})`;
        ctx.lineWidth = 1;
        ctx.stroke();
      }

      // Contested pulsing outer ring
      if (isContested) {
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, drawR + 4 + pulse * 2, 0, Math.PI * 2);
        ctx.strokeStyle = isVulnerable
          ? `rgba(255, 69, 58, ${0.3 + pulse * 0.4})`
          : `rgba(255, 214, 10, ${0.2 + pulse * 0.3})`;
        ctx.lineWidth = 1.5;
        ctx.setLineDash([3, 3]);
        ctx.stroke();
        ctx.setLineDash([]);
      }

      // Selection / route endpoint ring
      if (isSelected || isRouteEndpoint) {
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, drawR + 3, 0, Math.PI * 2);
        ctx.strokeStyle = '#22d3ee';
        ctx.lineWidth = 2;
        ctx.shadowColor = '#22d3ee';
        ctx.shadowBlur = isRouteEndpoint ? 12 : 8;
        ctx.stroke();
        ctx.shadowBlur = 0;
      } else if (isRouteNode) {
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, drawR + 2, 0, Math.PI * 2);
        ctx.strokeStyle = 'rgba(34, 211, 238, 0.5)';
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }

      // System dot
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, drawR, 0, Math.PI * 2);
      ctx.fillStyle = isSelected || isRouteEndpoint ? '#22d3ee' : faction.fill;
      ctx.fill();

      // Owner ring (if different from occupier)
      if (sys.fw.owner_faction_id !== sys.fw.occupier_faction_id) {
        const ownerFaction = FACTION_COLORS[sys.fw.owner_faction_id];
        if (ownerFaction) {
          ctx.beginPath();
          ctx.arc(pos.x, pos.y, drawR, 0, Math.PI * 2);
          ctx.strokeStyle = ownerFaction.fill;
          ctx.lineWidth = 2;
          ctx.stroke();
        }
      }

      // Kill count badge
      if (killCount > 0 && viewport.zoom >= 0.7) {
        const badgeX = pos.x + drawR + 2;
        const badgeY = pos.y - drawR - 2;
        const text = killCount > 99 ? '99+' : String(killCount);
        ctx.font = 'bold 8px system-ui, -apple-system, sans-serif';
        const tw = ctx.measureText(text).width;
        const bw = Math.max(tw + 4, 14);
        ctx.fillStyle = '#dc2626';
        ctx.fillRect(badgeX - bw / 2, badgeY - 6, bw, 12);
        ctx.fillStyle = '#ffffff';
        ctx.textAlign = 'center';
        ctx.fillText(text, badgeX, badgeY + 3);
      }

      ctx.restore();

      // Labels at higher zoom or for hovered/selected/route
      const showLabel = viewport.zoom >= 0.8 || isHovered || isSelected || isRouteNode;
      if (showLabel) {
        const fontSize = Math.max(9, Math.min(12, size.w / 90 * viewport.zoom));
        ctx.font = `${fontSize}px system-ui, -apple-system, sans-serif`;
        ctx.textAlign = 'center';
        // Text shadow for readability
        ctx.fillStyle = '#000000';
        ctx.globalAlpha = 0.6;
        ctx.fillText(sys.name, pos.x + 0.5, pos.y + drawR + fontSize - 1.5);
        // Label below node — subway style
        ctx.fillStyle = isSelected || isHovered || isRouteNode ? '#ffffff' : '#94a3b8';
        ctx.globalAlpha = isSelected || isHovered || isRouteNode ? 1 : 0.85;
        ctx.fillText(sys.name, pos.x, pos.y + drawR + fontSize - 2);
        ctx.globalAlpha = 1;
      }
    }

    // ── Legend ──────────────────────────────────────────────────────────────────

    const legendX = 12;
    const legendY = size.h - 120;
    ctx.font = '11px system-ui, -apple-system, sans-serif';

    // Faction colors
    for (const [i, [, info]] of Object.entries(FACTION_COLORS).entries()) {
      const y = legendY + i * 18;
      ctx.beginPath();
      ctx.arc(legendX + 6, y, 5, 0, Math.PI * 2);
      ctx.fillStyle = info.fill;
      ctx.fill();
      ctx.fillStyle = '#94a3b8';
      ctx.textAlign = 'left';
      ctx.fillText(info.shortName, legendX + 16, y + 4);
    }

    // Contested indicator
    const contestedY = legendY + 4 * 18;
    ctx.save();
    ctx.beginPath();
    ctx.arc(legendX + 6, contestedY, 5, 0, Math.PI * 2);
    ctx.strokeStyle = '#ffd60a';
    ctx.lineWidth = 1.5;
    ctx.setLineDash([3, 3]);
    ctx.stroke();
    ctx.restore();
    ctx.fillStyle = '#94a3b8';
    ctx.textAlign = 'left';
    ctx.fillText('Contested', legendX + 16, contestedY + 4);

    // Vulnerable indicator
    const vulnY = contestedY + 18;
    ctx.save();
    ctx.beginPath();
    ctx.arc(legendX + 6, vulnY, 5, 0, Math.PI * 2);
    ctx.strokeStyle = '#ff453a';
    ctx.lineWidth = 1.5;
    ctx.setLineDash([3, 3]);
    ctx.stroke();
    ctx.restore();
    ctx.fillStyle = '#94a3b8';
    ctx.textAlign = 'left';
    ctx.fillText('Vulnerable', legendX + 16, vulnY + 4);

    // Kill activity indicator
    const killLegY = vulnY + 18;
    ctx.beginPath();
    ctx.arc(legendX + 6, killLegY, 5, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(255, 69, 58, ${0.3 + killPulse * 0.4})`;
    ctx.fill();
    ctx.fillStyle = '#94a3b8';
    ctx.textAlign = 'left';
    ctx.fillText('Kill activity', legendX + 16, killLegY + 4);

    // Active filter indicator at top of canvas
    if (warzoneFilter !== null) {
      const activeWarzone = WARZONES[warzoneFilter];
      if (activeWarzone) {
        const label = activeWarzone.name;
        ctx.font = 'bold 12px system-ui, -apple-system, sans-serif';
        const labelW = ctx.measureText(label).width;
        ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
        ctx.fillRect(size.w / 2 - labelW / 2 - 12, 8, labelW + 24, 24);
        const btn = WARZONE_BUTTONS[warzoneFilter];
        ctx.fillStyle = btn?.colors[0] || '#ffffff';
        ctx.textAlign = 'center';
        ctx.fillText(label, size.w / 2, 25);
      }
    }
  }, [size, fwSystems, visibleSystems, fwGates, systemMap, hovered, selected, toCanvas, getNodeRadius, viewport, hotSystemMap, warzoneFilter, routePath, routeEdges, routeEndpoints]);

  // ── Animation loop for contested pulse + kill blink ────────────────────────

  useEffect(() => {
    const hasContested = fwSystems.some(
      (s) => s.fw.contested === 'contested' || s.fw.contested === 'vulnerable'
    );
    const hasKills = hotSystems.length > 0;
    if (!hasContested && !hasKills) return;

    const interval = setInterval(() => {
      pulseRef.current += 0.1;
      setFrame((f) => f + 1);
    }, 50); // ~20fps for pulse
    return () => clearInterval(interval);
  }, [fwSystems, hotSystems]);

  // ── Selected system detail ──────────────────────────────────────────────────

  const selectedSystem = useMemo(() => {
    if (!selected || !mapConfig) return null;
    const sys = systemMap.get(selected);
    if (!sys) return null;

    // Find adjacent FW systems
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

  // ── Computed stats ────────────────────────────────────────────────────────

  const factionCounts: Record<number, number> = {};
  const contestedCount = fwSystems.filter(
    (s) => s.fw.contested === 'contested' || s.fw.contested === 'vulnerable'
  ).length;
  const vulnerableCount = fwSystems.filter(
    (s) => s.fw.contested === 'vulnerable'
  ).length;
  for (const sys of fwSystems) {
    factionCounts[sys.fw.occupier_faction_id] = (factionCounts[sys.fw.occupier_faction_id] || 0) + 1;
  }

  // Count flipped systems per faction (occupier != owner)
  const flippedCounts: Record<number, number> = {};
  for (const sys of fwSystems) {
    if (sys.fw.occupier_faction_id !== sys.fw.owner_faction_id) {
      flippedCounts[sys.fw.occupier_faction_id] = (flippedCounts[sys.fw.occupier_faction_id] || 0) + 1;
    }
  }

  // FW kills in warzone systems
  const fwKillCount = fwSystems.reduce((sum, sys) => sum + (hotSystemMap.get(sys.systemId) || 0), 0);

  // Top hot FW systems
  const topHotFW = useMemo(() => {
    return hotSystems
      .filter((hs) => systemMap.has(hs.system_id))
      .slice(0, 10);
  }, [hotSystems, systemMap]);

  // ── Render ──────────────────────────────────────────────────────────────────

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
      {/* Main map area */}
      <div className="flex-1 min-w-0 space-y-3">
        {/* Toolbar: warzone buttons + intel feed */}
        <div className="flex items-center gap-2 min-h-[36px] flex-wrap">
          {/* Warzone filter buttons */}
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
            const warzone = WARZONES[btn.warzoneIdx];
            const count = warzone.factions.reduce((sum, fid) => sum + (factionCounts[fid] || 0), 0);
            return (
              <button
                key={btn.key}
                onClick={() => handleWarzoneClick(btn.warzoneIdx)}
                className={`inline-flex items-center gap-1.5 text-xs font-medium px-3 h-7 rounded-md transition-all cursor-pointer ${
                  isActive
                    ? 'shadow-md scale-105'
                    : 'hover:brightness-125 hover:scale-105 opacity-80 hover:opacity-100'
                }`}
                style={{
                  backgroundColor: isActive ? 'rgba(255,255,255,0.1)' : 'rgba(255,255,255,0.05)',
                  color: isActive ? '#ffffff' : '#94a3b8',
                  border: isActive ? '2px solid rgba(255,255,255,0.3)' : '2px solid transparent',
                }}
              >
                <span className="flex gap-0.5">
                  {btn.colors.map((c, i) => (
                    <span
                      key={i}
                      className="w-2 h-2 rounded-full"
                      style={{ backgroundColor: c }}
                    />
                  ))}
                </span>
                {btn.label}: {count}
              </button>
            );
          })}

          {/* Route mode toggle */}
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

          {/* Separator + Intel feed (right-aligned) */}
          <div className="flex items-center gap-2 ml-auto">
            <span className="text-xs font-bold text-text uppercase tracking-wider">Intel</span>
            <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
            <span className="text-[10px] text-text-secondary hidden sm:inline">
              {fwKillCount} kills · {hotSystems.reduce((s, h) => s + h.recent_pods, 0)} pods
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

        {/* Route info bar */}
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
                <button
                  onClick={() => setRouteEndpoints([null, null])}
                  className="text-text-secondary hover:text-text ml-1"
                >
                  <X className="h-3 w-3" />
                </button>
              </div>
            ) : (
              <span className="text-red-400">No route found</span>
            )}
          </div>
        )}

        {/* Canvas — Pochven aesthetic */}
        <div ref={containerRef} className="w-full relative rounded-lg border border-border overflow-hidden" style={{ backgroundColor: '#0a0e17' }}>
          <canvas
            ref={canvasRef}
            onClick={handleClick}
            onMouseMove={handleMove}
            onMouseDown={handleMouseDown}
            onMouseUp={handleMouseUp}
            onMouseLeave={() => {
              setHovered(null);
              handleMouseUp();
            }}
            onWheel={handleWheel}
            className="w-full"
            style={{ touchAction: 'none', cursor: 'grab' }}
          />

          {/* Detail panel */}
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

        {/* Zoom controls hint */}
        <div className="text-[10px] text-text-secondary text-center">
          Scroll to zoom · Drag to pan · {routeMode ? 'Click two systems to route' : 'Click a system for details'}
          {warzoneFilter !== null && ' · Click warzone button again to reset'}
        </div>
      </div>

      {/* Right sidebar */}
      <FWSidebar
        fwSystems={fwSystems}
        factionCounts={factionCounts}
        flippedCounts={flippedCounts}
        contestedCount={contestedCount}
        vulnerableCount={vulnerableCount}
        fwKillCount={fwKillCount}
        topHotSystems={topHotFW}
        systemMap={systemMap}
        onSystemClick={(systemId) => setSelected(systemId)}
        intelHours={intelHours}
      />
    </div>
  );
}
