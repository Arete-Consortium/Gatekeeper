'use client';

import { useRef, useState, useEffect, useMemo, useCallback } from 'react';
import { Badge } from '@/components/ui';

// ── Data ────────────────────────────────────────────────────────────────────

type Krai = 'perun' | 'svarog' | 'veles';
type SystemType = 'home' | 'border' | 'internal';

interface PochvenSystem {
  name: string;
  krai: Krai;
  type: SystemType;
  gx: number;
  gy: number;
  /** Original k-space region before Triglavian invasion */
  originRegion: string;
}

interface PochvenGate {
  from: string;
  to: string;
  crossKrai: boolean;
}

const KRAI_COLORS: Record<Krai, string> = {
  veles: '#22c55e',  // green
  svarog: '#ef4444', // red
  perun: '#3b82f6',  // blue
};

const KRAI_LABELS: Record<Krai, string> = {
  veles: 'Krai Veles',
  svarog: 'Krai Svarog',
  perun: 'Krai Perun',
};

// ── Triangle Layout ─────────────────────────────────────────────────────────
// Positions match the canonical Pochven triangle diagram:
//   Veles (green) at top, Svarog (red) bottom-left, Perun (blue) bottom-right
//   Bottom row: horizontal baseline connecting Svarog → Perun

const SYSTEMS: PochvenSystem[] = [
  // ── Krai Veles (green) — top of triangle ──
  { name: 'Archee',     krai: 'veles',  type: 'home',     gx: 0.50, gy: 0.04, originRegion: 'Solitude' },
  { name: 'Vale',       krai: 'veles',  type: 'internal', gx: 0.42, gy: 0.12, originRegion: 'Solitude' },
  { name: 'Angymonne',  krai: 'veles',  type: 'internal', gx: 0.56, gy: 0.12, originRegion: 'Solitude' },
  { name: 'Ala',        krai: 'veles',  type: 'internal', gx: 0.39, gy: 0.20, originRegion: 'Domain' },
  { name: 'Ichoriya',   krai: 'veles',  type: 'internal', gx: 0.60, gy: 0.20, originRegion: 'The Citadel' },
  { name: 'Wirashoda',  krai: 'veles',  type: 'internal', gx: 0.33, gy: 0.28, originRegion: 'Sinq Laison' },
  { name: 'Kaunokka',   krai: 'veles',  type: 'internal', gx: 0.65, gy: 0.28, originRegion: 'The Citadel' },
  { name: 'Senda',      krai: 'veles',  type: 'border',   gx: 0.27, gy: 0.36, originRegion: 'Sinq Laison' },
  { name: 'Arvasaras',  krai: 'veles',  type: 'border',   gx: 0.71, gy: 0.36, originRegion: 'The Citadel' },

  // ── Krai Svarog (red) — left leg ──
  { name: 'Ahtila',     krai: 'svarog', type: 'border',   gx: 0.22, gy: 0.44, originRegion: 'Sinq Laison' },
  { name: 'Kuharah',    krai: 'svarog', type: 'internal', gx: 0.18, gy: 0.51, originRegion: 'Kor-Azor' },
  { name: 'Tunudan',    krai: 'svarog', type: 'internal', gx: 0.14, gy: 0.58, originRegion: 'Tash-Murkon' },
  { name: 'Harva',      krai: 'svarog', type: 'internal', gx: 0.09, gy: 0.66, originRegion: 'Domain' },
  { name: 'Niarja',     krai: 'svarog', type: 'home',     gx: 0.05, gy: 0.80, originRegion: 'Domain' },
  { name: 'Raravoss',   krai: 'svarog', type: 'internal', gx: 0.15, gy: 0.80, originRegion: 'Domain' },
  { name: 'Skarkon',    krai: 'svarog', type: 'internal', gx: 0.25, gy: 0.80, originRegion: 'Molden Heath' },
  { name: 'Nani',       krai: 'svarog', type: 'internal', gx: 0.35, gy: 0.80, originRegion: 'Molden Heath' },
  { name: 'Urhinichi',  krai: 'svarog', type: 'border',   gx: 0.45, gy: 0.80, originRegion: 'Molden Heath' },

  // ── Krai Perun (blue) — right leg ──
  { name: 'Sakenta',    krai: 'perun',  type: 'border',   gx: 0.76, gy: 0.44, originRegion: 'The Citadel' },
  { name: 'Komo',       krai: 'perun',  type: 'internal', gx: 0.80, gy: 0.51, originRegion: 'The Citadel' },
  { name: 'Ignebaener', krai: 'perun',  type: 'internal', gx: 0.84, gy: 0.58, originRegion: 'Metropolis' },
  { name: 'Otela',      krai: 'perun',  type: 'internal', gx: 0.88, gy: 0.66, originRegion: 'The Forge' },
  { name: 'Kino',       krai: 'perun',  type: 'home',     gx: 0.95, gy: 0.80, originRegion: 'Lonetrek' },
  { name: 'Nalvula',    krai: 'perun',  type: 'internal', gx: 0.85, gy: 0.80, originRegion: 'Lonetrek' },
  { name: 'Konola',     krai: 'perun',  type: 'internal', gx: 0.75, gy: 0.80, originRegion: 'The Forge' },
  { name: 'Krirald',    krai: 'perun',  type: 'internal', gx: 0.65, gy: 0.80, originRegion: 'The Forge' },
  { name: 'Otanuomi',   krai: 'perun',  type: 'border',   gx: 0.55, gy: 0.80, originRegion: 'The Forge' },
];

const GATES: PochvenGate[] = [
  // Krai Veles internal
  { from: 'Archee', to: 'Vale', crossKrai: false },
  { from: 'Archee', to: 'Angymonne', crossKrai: false },
  { from: 'Vale', to: 'Angymonne', crossKrai: false },
  { from: 'Vale', to: 'Ala', crossKrai: false },
  { from: 'Angymonne', to: 'Ichoriya', crossKrai: false },
  { from: 'Ala', to: 'Wirashoda', crossKrai: false },
  { from: 'Ichoriya', to: 'Kaunokka', crossKrai: false },
  { from: 'Wirashoda', to: 'Senda', crossKrai: false },
  { from: 'Kaunokka', to: 'Arvasaras', crossKrai: false },
  // Krai Svarog internal
  { from: 'Ahtila', to: 'Kuharah', crossKrai: false },
  { from: 'Kuharah', to: 'Tunudan', crossKrai: false },
  { from: 'Tunudan', to: 'Harva', crossKrai: false },
  { from: 'Harva', to: 'Niarja', crossKrai: false },
  { from: 'Niarja', to: 'Raravoss', crossKrai: false },
  { from: 'Raravoss', to: 'Skarkon', crossKrai: false },
  { from: 'Skarkon', to: 'Nani', crossKrai: false },
  { from: 'Nani', to: 'Urhinichi', crossKrai: false },
  { from: 'Harva', to: 'Raravoss', crossKrai: false },
  // Krai Perun internal
  { from: 'Sakenta', to: 'Komo', crossKrai: false },
  { from: 'Komo', to: 'Ignebaener', crossKrai: false },
  { from: 'Ignebaener', to: 'Otela', crossKrai: false },
  { from: 'Otela', to: 'Kino', crossKrai: false },
  { from: 'Otela', to: 'Nalvula', crossKrai: false },
  { from: 'Kino', to: 'Nalvula', crossKrai: false },
  { from: 'Nalvula', to: 'Konola', crossKrai: false },
  { from: 'Konola', to: 'Krirald', crossKrai: false },
  { from: 'Krirald', to: 'Otanuomi', crossKrai: false },
  // Cross-Krai
  { from: 'Senda', to: 'Ahtila', crossKrai: true },
  { from: 'Arvasaras', to: 'Sakenta', crossKrai: true },
  { from: 'Urhinichi', to: 'Otanuomi', crossKrai: true },
];

// ── BFS pathfinding ─────────────────────────────────────────────────────────

function bfs(from: string, to: string): string[] {
  if (from === to) return [from];
  const adj: Record<string, string[]> = {};
  for (const g of GATES) {
    if (!adj[g.from]) adj[g.from] = [];
    if (!adj[g.to]) adj[g.to] = [];
    adj[g.from].push(g.to);
    adj[g.to].push(g.from);
  }
  const visited = new Set<string>([from]);
  const parent: Record<string, string> = {};
  const queue = [from];
  while (queue.length > 0) {
    const current = queue.shift()!;
    for (const neighbor of adj[current] || []) {
      if (visited.has(neighbor)) continue;
      visited.add(neighbor);
      parent[neighbor] = current;
      if (neighbor === to) {
        const path: string[] = [];
        let node: string | undefined = to;
        while (node) {
          path.unshift(node);
          node = parent[node];
        }
        return path;
      }
      queue.push(neighbor);
    }
  }
  return [];
}

// ── Component ───────────────────────────────────────────────────────────────

const SYSTEM_MAP = new Map(SYSTEMS.map((s) => [s.name, s]));

// Get adjacent systems for a given system
function getAdjacent(name: string): string[] {
  const adj: string[] = [];
  for (const g of GATES) {
    if (g.from === name) adj.push(g.to);
    else if (g.to === name) adj.push(g.from);
  }
  return adj;
}

// Node box dimensions
const NODE_H = 22;
const NODE_PAD_X = 10;

export function PochvenMap() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ w: 900, h: 700 });
  const [hovered, setHovered] = useState<string | null>(null);
  const [selected, setSelected] = useState<[string | null, string | null]>([null, null]);

  const path = useMemo(() => {
    const [a, b] = selected;
    if (a && b) return bfs(a, b);
    return [];
  }, [selected]);

  const pathEdges = useMemo(() => {
    const edges = new Set<string>();
    for (let i = 0; i < path.length - 1; i++) {
      edges.add(`${path[i]}|${path[i + 1]}`);
      edges.add(`${path[i + 1]}|${path[i]}`);
    }
    return edges;
  }, [path]);

  // Resize observer
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const observer = new ResizeObserver((entries) => {
      const { width } = entries[0].contentRect;
      const h = Math.min(Math.round(width * 0.78), 750);
      setSize({ w: Math.round(width), h });
    });
    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  // Convert normalized coords to canvas pixels
  const toCanvas = useCallback(
    (gx: number, gy: number) => {
      const padX = 50;
      const padY = 30;
      return {
        x: padX + gx * (size.w - padX * 2),
        y: padY + gy * (size.h - padY * 2),
      };
    },
    [size]
  );

  // Measure node box width (cached per render)
  const nodeWidths = useMemo(() => {
    if (typeof document === 'undefined') return new Map<string, number>();
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    if (!ctx) return new Map<string, number>();
    const fontSize = Math.max(10, Math.min(13, size.w / 75));
    ctx.font = `bold ${fontSize}px system-ui, -apple-system, sans-serif`;
    const widths = new Map<string, number>();
    for (const sys of SYSTEMS) {
      widths.set(sys.name, ctx.measureText(sys.name).width + NODE_PAD_X * 2);
    }
    return widths;
  }, [size.w]);

  // Hit test — check if point is inside any node rectangle
  const hitTest = useCallback(
    (cx: number, cy: number): string | null => {
      for (const sys of SYSTEMS) {
        const pos = toCanvas(sys.gx, sys.gy);
        const w = nodeWidths.get(sys.name) || 80;
        const halfW = w / 2;
        const halfH = NODE_H / 2;
        if (cx >= pos.x - halfW - 4 && cx <= pos.x + halfW + 4 &&
            cy >= pos.y - halfH - 4 && cy <= pos.y + halfH + 4) {
          return sys.name;
        }
      }
      return null;
    },
    [toCanvas, nodeWidths]
  );

  // Click handler
  const handleClick = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const hit = hitTest(x, y);
      if (!hit) { setSelected([null, null]); return; }
      setSelected((prev) => {
        if (!prev[0]) return [hit, null];
        if (prev[0] === hit) return [null, null];
        if (prev[1]) return [hit, null];
        return [prev[0], hit];
      });
    },
    [hitTest]
  );

  // Hover handler
  const handleMove = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const hit = hitTest(e.clientX - rect.left, e.clientY - rect.top);
      setHovered(hit);
      canvas.style.cursor = hit ? 'pointer' : 'default';
    },
    [hitTest]
  );

  // Touch handler
  const handleTouch = useCallback(
    (e: React.TouchEvent<HTMLCanvasElement>) => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const touch = e.touches[0];
      const hit = hitTest(touch.clientX - rect.left, touch.clientY - rect.top);
      if (hit) {
        e.preventDefault();
        setSelected((prev) => {
          if (!prev[0]) return [hit, null];
          if (prev[0] === hit) return [null, null];
          if (prev[1]) return [hit, null];
          return [prev[0], hit];
        });
      }
    },
    [hitTest]
  );

  // ── Canvas draw ───────────────────────────────────────────────────────────

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
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

    const fontSize = Math.max(10, Math.min(13, size.w / 75));

    // Helper: get node edge point towards another node (for line connections)
    const getEdgePoint = (from: PochvenSystem, to: PochvenSystem) => {
      const fp = toCanvas(from.gx, from.gy);
      const tp = toCanvas(to.gx, to.gy);
      const fw = (nodeWidths.get(from.name) || 80) / 2;
      const fh = NODE_H / 2;
      const dx = tp.x - fp.x;
      const dy = tp.y - fp.y;
      const angle = Math.atan2(dy, dx);
      // Determine exit side based on angle
      const tanA = Math.abs(dy / (dx || 0.001));
      const tanBox = fh / fw;
      let ex: number, ey: number;
      if (tanA <= tanBox) {
        // Exit from left or right
        ex = fp.x + Math.sign(dx) * fw;
        ey = fp.y + Math.sign(dx) * fw * Math.tan(angle);
      } else {
        // Exit from top or bottom
        ey = fp.y + Math.sign(dy) * fh;
        ex = fp.x + Math.sign(dy) * fh / Math.tan(angle);
      }
      return { x: ex, y: ey };
    };

    // Draw connections
    for (const gate of GATES) {
      const fromSys = SYSTEM_MAP.get(gate.from);
      const toSys = SYSTEM_MAP.get(gate.to);
      if (!fromSys || !toSys) continue;

      const fromEdge = getEdgePoint(fromSys, toSys);
      const toEdge = getEdgePoint(toSys, fromSys);
      const isOnPath = pathEdges.has(`${gate.from}|${gate.to}`);

      ctx.save();
      ctx.beginPath();
      ctx.moveTo(fromEdge.x, fromEdge.y);
      ctx.lineTo(toEdge.x, toEdge.y);

      if (isOnPath) {
        ctx.strokeStyle = '#22d3ee';
        ctx.lineWidth = 3;
        ctx.shadowColor = '#22d3ee';
        ctx.shadowBlur = 8;
      } else if (gate.crossKrai) {
        ctx.setLineDash([6, 4]);
        ctx.strokeStyle = '#64748b';
        ctx.lineWidth = 1.5;
      } else {
        // Same color as the krai, dimmed
        ctx.strokeStyle = KRAI_COLORS[fromSys.krai] + '60';
        ctx.lineWidth = 2;
      }
      ctx.stroke();
      ctx.restore();
    }

    // Draw system nodes as colored rectangles with labels
    ctx.font = `bold ${fontSize}px system-ui, -apple-system, sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    for (const sys of SYSTEMS) {
      const pos = toCanvas(sys.gx, sys.gy);
      const w = nodeWidths.get(sys.name) || 80;
      const halfW = w / 2;
      const halfH = NODE_H / 2;
      const isHovered = hovered === sys.name;
      const isSelected = selected[0] === sys.name || selected[1] === sys.name;
      const isOnPath = path.includes(sys.name);
      const color = KRAI_COLORS[sys.krai];

      ctx.save();

      // Glow for selected/path nodes
      if (isSelected || isOnPath) {
        ctx.shadowColor = isSelected ? '#22d3ee' : color;
        ctx.shadowBlur = isSelected ? 14 : 8;
      }

      // Hover glow
      if (isHovered && !isSelected) {
        ctx.shadowColor = color;
        ctx.shadowBlur = 10;
      }

      // Rectangle background
      const rx = pos.x - halfW;
      const ry = pos.y - halfH;
      const expandH = isHovered ? 2 : 0;
      const expandW = isHovered ? 2 : 0;

      ctx.fillStyle = isSelected ? '#22d3ee' : color;
      ctx.beginPath();
      ctx.roundRect(rx - expandW, ry - expandH, w + expandW * 2, NODE_H + expandH * 2, 4);
      ctx.fill();

      // Selection ring
      if (isSelected) {
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.roundRect(rx - 3, ry - 3, w + 6, NODE_H + 6, 6);
        ctx.stroke();
      }

      ctx.restore();

      // Label text inside rectangle
      ctx.fillStyle = '#ffffff';
      ctx.font = `bold ${fontSize}px system-ui, -apple-system, sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(sys.name, pos.x, pos.y);
    }

    // ── Krai Labels ─────────────────────────────────────────────────────────

    ctx.font = `600 ${Math.max(12, size.w / 60)}px system-ui, -apple-system, sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    // Krai Veles — between the two legs at top
    const velesLabel = toCanvas(0.50, 0.22);
    ctx.fillStyle = KRAI_COLORS.veles + '40';
    ctx.fillText('Krai Veles', velesLabel.x, velesLabel.y);

    // Krai Svarog — left side
    const svarogLabel = toCanvas(0.18, 0.62);
    ctx.fillStyle = KRAI_COLORS.svarog + '40';
    ctx.fillText('Krai Svarog', svarogLabel.x, svarogLabel.y);

    // Krai Perun — right side
    const perunLabel = toCanvas(0.82, 0.62);
    ctx.fillStyle = KRAI_COLORS.perun + '40';
    ctx.fillText('Krai Perun', perunLabel.x, perunLabel.y);

    // "Pochven Region" — center
    ctx.font = `bold ${Math.max(16, size.w / 40)}px system-ui, -apple-system, sans-serif`;
    ctx.fillStyle = '#334155';
    const centerLabel = toCanvas(0.50, 0.55);
    ctx.fillText('Pochven Region', centerLabel.x, centerLabel.y);

  }, [size, hovered, selected, path, pathEdges, toCanvas, nodeWidths]);

  // ── Info panel ────────────────────────────────────────────────────────────

  const selectedSys = useMemo(() => {
    return selected[0] ? SYSTEM_MAP.get(selected[0]) ?? null : null;
  }, [selected]);

  const selectedAdj = useMemo(() => {
    if (!selected[0]) return [];
    return getAdjacent(selected[0]).map((name) => SYSTEM_MAP.get(name)!).filter(Boolean);
  }, [selected]);

  const selectedInfo = useMemo(() => {
    const [a, b] = selected;
    const sysA = a ? SYSTEM_MAP.get(a) : null;
    const sysB = b ? SYSTEM_MAP.get(b) : null;
    return { sysA, sysB };
  }, [selected]);

  return (
    <div className="space-y-3">
      {/* Info bar */}
      <div className="flex flex-wrap items-center gap-2 min-h-[36px]">
        {!selected[0] && (
          <span className="text-sm text-text-secondary">
            Click a system to view connections. Click a second to find shortest path.
          </span>
        )}
        {selectedInfo.sysA && !selectedInfo.sysB && (
          <div className="flex items-center gap-2">
            <Badge
              variant="default"
              className="text-xs"
              style={{ backgroundColor: KRAI_COLORS[selectedInfo.sysA.krai] + '30', color: KRAI_COLORS[selectedInfo.sysA.krai] }}
            >
              {KRAI_LABELS[selectedInfo.sysA.krai]}
            </Badge>
            <span className="text-sm text-text font-medium">{selectedInfo.sysA.name}</span>
            <span className="text-sm text-text-secondary capitalize">({selectedInfo.sysA.type})</span>
            <span className="text-xs text-text-secondary ml-2">Click another system for route</span>
          </div>
        )}
        {selectedInfo.sysA && selectedInfo.sysB && path.length > 0 && (
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm text-text font-medium">{selectedInfo.sysA.name}</span>
            <span className="text-xs text-text-secondary">to</span>
            <span className="text-sm text-text font-medium">{selectedInfo.sysB.name}</span>
            <Badge variant="default" className="text-xs bg-cyan-500/20 text-cyan-400">
              {path.length - 1} {path.length - 1 === 1 ? 'jump' : 'jumps'}
            </Badge>
            <span className="text-xs text-text-secondary hidden sm:inline">
              {path.join(' \u2192 ')}
            </span>
          </div>
        )}
      </div>

      {/* Canvas + detail panel */}
      <div className="relative">
        <div ref={containerRef} className="w-full">
          <canvas
            ref={canvasRef}
            onClick={handleClick}
            onMouseMove={handleMove}
            onMouseLeave={() => setHovered(null)}
            onTouchStart={handleTouch}
            className="w-full rounded-lg border border-border"
            style={{ touchAction: 'manipulation', backgroundColor: '#0a0e17' }}
          />
        </div>

        {/* System detail overlay — centered on canvas */}
        {selectedSys && !selected[1] && (
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-10 bg-gray-900/95 border border-gray-600 rounded-lg shadow-2xl backdrop-blur-sm p-4 min-w-[260px] max-w-[340px]">
            {/* Header */}
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div
                  className="w-3 h-3 rounded-sm"
                  style={{ backgroundColor: KRAI_COLORS[selectedSys.krai] }}
                />
                <span className="font-bold text-white text-sm">{selectedSys.name}</span>
                <span className="text-[10px] text-gray-400 capitalize">({selectedSys.type})</span>
              </div>
              <button
                onClick={() => setSelected([null, null])}
                className="text-gray-500 hover:text-white text-xs"
              >
                ✕
              </button>
            </div>

            {/* Krai + Origin */}
            <div className="space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-gray-400">Krai</span>
                <span style={{ color: KRAI_COLORS[selectedSys.krai] }}>
                  {KRAI_LABELS[selectedSys.krai]}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Origin Region</span>
                <span className="text-gray-200">{selectedSys.originRegion}</span>
              </div>
            </div>

            {/* Internal connections */}
            <div className="mt-3 pt-3 border-t border-gray-700">
              <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">
                Gate Connections
              </span>
              <div className="mt-1.5 flex flex-wrap gap-1.5">
                {selectedAdj.map((adj) => (
                  <button
                    key={adj.name}
                    onClick={(e) => { e.stopPropagation(); setSelected([adj.name, null]); }}
                    className="text-[11px] px-2 py-0.5 rounded-md font-medium transition-colors hover:brightness-125"
                    style={{
                      backgroundColor: KRAI_COLORS[adj.krai] + '25',
                      color: KRAI_COLORS[adj.krai],
                    }}
                  >
                    {adj.name}
                    {adj.krai !== selectedSys.krai && (
                      <span className="ml-1 text-[9px] opacity-60">(cross)</span>
                    )}
                  </button>
                ))}
              </div>
            </div>

            {/* Wormhole connection info */}
            <div className="mt-3 pt-3 border-t border-gray-700">
              <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">
                Wormhole Connections
              </span>
              <p className="text-[11px] text-gray-300 mt-1.5">
                {selectedSys.type === 'home' && (
                  <>Wandering wormholes to C5/C6 space. Filament entry from k-space.</>
                )}
                {selectedSys.type === 'internal' && (
                  <>Wormhole connections spawn to {selectedSys.originRegion} and adjacent regions.</>
                )}
                {selectedSys.type === 'border' && (
                  <>Border system — cross-Krai gate access. Wormholes to {selectedSys.originRegion}.</>
                )}
              </p>
              <p className="text-[10px] text-gray-500 mt-1 italic">
                Connections change dynamically. Scan in-game for current exits.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Path detail on mobile */}
      {path.length > 2 && (
        <div className="sm:hidden text-xs text-text-secondary px-1">
          <span className="font-medium text-text">Route: </span>
          {path.join(' \u2192 ')}
        </div>
      )}
    </div>
  );
}
