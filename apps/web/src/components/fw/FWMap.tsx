'use client';

import { useRef, useState, useEffect, useMemo, useCallback } from 'react';
import { Card, Badge } from '@/components/ui';
import { GatekeeperAPI } from '@/lib/api';
import type { MapConfig, MapConfigSystem, Gate, FWSystem, FWResponse } from '@/lib/types';
import { FWSystemDetail } from './FWSystemDetail';

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

// ── Component ────────────────────────────────────────────────────────────────

export function FWMap() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ w: 900, h: 650 });
  const [hovered, setHovered] = useState<number | null>(null);
  const [selected, setSelected] = useState<number | null>(null);

  // Pan & zoom state
  const [viewport, setViewport] = useState({ x: 0, y: 0, zoom: 1 });
  const dragRef = useRef<{ startX: number; startY: number; vpX: number; vpY: number } | null>(null);

  // Data
  const [fwSystems, setFwSystems] = useState<FWSystemNode[]>([]);
  const [fwGates, setFwGates] = useState<FWGateConnection[]>([]);
  const [mapConfig, setMapConfig] = useState<MapConfig | null>(null);
  const [fwData, setFwData] = useState<Record<string, FWSystem>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Contested pulse animation
  const pulseRef = useRef(0);
  const [, setFrame] = useState(0);

  // ── Fetch data ──────────────────────────────────────────────────────────────

  useEffect(() => {
    let cancelled = false;

    async function fetchData() {
      try {
        const [config, fw] = await Promise.all([
          GatekeeperAPI.getMapConfig(),
          GatekeeperAPI.getFWStatus(),
        ]);

        if (cancelled) return;

        setMapConfig(config);
        setFwData(fw.fw_systems);

        // Build FW system nodes
        const fwSystemIds = new Set(Object.keys(fw.fw_systems));
        const nodes: FWSystemNode[] = [];
        const systemIdToName = new Map<number, string>();

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
          systemIdToName.set(sys.id, name);
        }

        // Filter gate connections to only FW systems
        const fwIdSet = new Set(nodes.map((n) => n.systemId));
        const gates: FWGateConnection[] = [];
        for (const gate of config.gates) {
          // Gate uses system names — resolve to IDs
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

  // ── Coordinate mapping ──────────────────────────────────────────────────────

  // Compute bounds of FW systems for viewport fitting
  const bounds = useMemo(() => {
    if (fwSystems.length === 0) return { minX: 0, maxX: 1, minY: 0, maxY: 1 };
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    for (const sys of fwSystems) {
      if (sys.x < minX) minX = sys.x;
      if (sys.x > maxX) maxX = sys.x;
      if (sys.y < minY) minY = sys.y;
      if (sys.y > maxY) maxY = sys.y;
    }
    return { minX, maxX, minY, maxY };
  }, [fwSystems]);

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

  // ── Hit test ────────────────────────────────────────────────────────────────

  const hitTest = useCallback(
    (cx: number, cy: number): number | null => {
      for (const sys of fwSystems) {
        const pos = toCanvas(sys.x, sys.y);
        const r = getNodeRadius(sys.fw) + 6;
        const dx = cx - pos.x;
        const dy = cy - pos.y;
        if (dx * dx + dy * dy <= r * r) return sys.systemId;
      }
      return null;
    },
    [fwSystems, toCanvas, getNodeRadius]
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
      setSelected(hit);
    },
    [hitTest]
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

    // Draw gate connections
    for (const gate of fwGates) {
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

      ctx.save();
      ctx.beginPath();
      ctx.moveTo(fromPos.x, fromPos.y);
      ctx.lineTo(toPos.x, toPos.y);

      if (sameWarzone) {
        ctx.strokeStyle = '#334155';
        ctx.lineWidth = 1;
      } else {
        ctx.setLineDash([4, 3]);
        ctx.strokeStyle = '#1e293b';
        ctx.lineWidth = 0.5;
      }
      ctx.stroke();
      ctx.restore();
    }

    // Pulse value for contested systems
    const pulse = (Math.sin(pulseRef.current) + 1) / 2;

    // Draw system nodes
    for (const sys of fwSystems) {
      const pos = toCanvas(sys.x, sys.y);

      // Skip off-screen
      if (pos.x < -30 || pos.x > size.w + 30 || pos.y < -30 || pos.y > size.h + 30) continue;

      const faction = FACTION_COLORS[sys.fw.occupier_faction_id];
      if (!faction) continue;

      const r = getNodeRadius(sys.fw);
      const isHovered = hovered === sys.systemId;
      const isSelected = selected === sys.systemId;
      const isContested = sys.fw.contested === 'contested' || sys.fw.contested === 'vulnerable';
      const isVulnerable = sys.fw.contested === 'vulnerable';
      const drawR = isHovered ? r + 2 : r;

      ctx.save();

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

      // Selection ring
      if (isSelected) {
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, drawR + 3, 0, Math.PI * 2);
        ctx.strokeStyle = '#22d3ee';
        ctx.lineWidth = 2;
        ctx.shadowColor = '#22d3ee';
        ctx.shadowBlur = 8;
        ctx.stroke();
        ctx.shadowBlur = 0;
      }

      // System dot
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, drawR, 0, Math.PI * 2);
      ctx.fillStyle = isSelected ? '#22d3ee' : faction.fill;
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

      ctx.restore();

      // Labels at higher zoom or for hovered/selected
      const showLabel = viewport.zoom >= 0.8 || isHovered || isSelected;
      if (showLabel) {
        const fontSize = Math.max(9, Math.min(12, size.w / 90 * viewport.zoom));
        ctx.font = `${fontSize}px system-ui, -apple-system, sans-serif`;
        ctx.fillStyle = isSelected || isHovered ? '#ffffff' : '#94a3b8';
        ctx.textAlign = 'center';
        ctx.fillText(sys.name, pos.x, pos.y - drawR - 4);
      }
    }

    // ── Legend ──────────────────────────────────────────────────────────────────

    const legendX = 12;
    const legendY = size.h - 100;
    ctx.font = '11px system-ui, -apple-system, sans-serif';

    // Faction colors
    for (const [i, [factionId, info]] of Object.entries(FACTION_COLORS).entries()) {
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
  }, [size, fwSystems, fwGates, systemMap, hovered, selected, toCanvas, getNodeRadius, viewport]);

  // ── Animation loop for contested pulse ──────────────────────────────────────

  useEffect(() => {
    const hasContested = fwSystems.some(
      (s) => s.fw.contested === 'contested' || s.fw.contested === 'vulnerable'
    );
    if (!hasContested) return;

    const interval = setInterval(() => {
      pulseRef.current += 0.1;
      setFrame((f) => f + 1);
    }, 50); // ~20fps for pulse
    return () => clearInterval(interval);
  }, [fwSystems]);

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

  // Summary stats
  const factionCounts: Record<number, number> = {};
  const contestedCount = fwSystems.filter(
    (s) => s.fw.contested === 'contested' || s.fw.contested === 'vulnerable'
  ).length;
  for (const sys of fwSystems) {
    factionCounts[sys.fw.occupier_faction_id] = (factionCounts[sys.fw.occupier_faction_id] || 0) + 1;
  }

  return (
    <div className="space-y-3 relative">
      {/* Summary bar */}
      <div className="flex flex-wrap items-center gap-3 min-h-[36px]">
        <span className="text-sm text-text-secondary">
          {fwSystems.length} systems &middot; {contestedCount} contested
        </span>
        <div className="flex flex-wrap gap-2">
          {Object.entries(FACTION_COLORS).map(([fid, info]) => {
            const count = factionCounts[Number(fid)] || 0;
            return (
              <Badge
                key={fid}
                variant="default"
                className="text-[10px] px-1.5 py-0"
                style={{ backgroundColor: info.fill + '30', color: info.fill }}
              >
                {info.shortName}: {count}
              </Badge>
            );
          })}
        </div>
      </div>

      {/* Canvas */}
      <div ref={containerRef} className="w-full relative">
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
          className="w-full rounded-lg border border-border"
          style={{ touchAction: 'none', cursor: 'grab' }}
        />

        {/* Detail panel */}
        {selectedSystem && (
          <FWSystemDetail
            systemName={selectedSystem.sys.name}
            systemData={selectedSystem.configSys}
            fwData={selectedSystem.sys.fw}
            adjacentSystems={selectedSystem.adjacent}
            onClose={() => setSelected(null)}
          />
        )}
      </div>

      {/* Zoom controls hint */}
      <div className="text-[10px] text-text-secondary text-center">
        Scroll to zoom &middot; Drag to pan &middot; Click a system for details
      </div>
    </div>
  );
}
