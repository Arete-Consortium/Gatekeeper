'use client';

import { useRef, useState, useEffect, useMemo, useCallback } from 'react';
import { Card, Badge } from '@/components/ui';

// ── Data ────────────────────────────────────────────────────────────────────

type Krai = 'perun' | 'svarog' | 'veles';
type SystemType = 'home' | 'border' | 'internal';

interface PochvenSystem {
  name: string;
  krai: Krai;
  type: SystemType;
  // Subway map grid coords (0-1 normalized, mapped to canvas)
  gx: number;
  gy: number;
  // Label offset direction
  labelDir: 'top' | 'bottom' | 'left' | 'right';
}

interface PochvenGate {
  from: string;
  to: string;
  crossKrai: boolean;
}

const KRAI_COLORS: Record<Krai, string> = {
  perun: '#3b82f6',  // blue (Caldari)
  svarog: '#f59e0b', // amber (Amarr)
  veles: '#22c55e',  // green (Gallente/Minmatar)
};

const KRAI_LABELS: Record<Krai, string> = {
  perun: 'Krai Perun',
  svarog: 'Krai Svarog',
  veles: 'Krai Veles',
};

// Hardcoded subway-map positions (normalized 0-1).
// Layout: Veles top-left, Perun right, Svarog bottom.
// Tuned for clean lines and no label overlap.
const SYSTEMS: PochvenSystem[] = [
  // ── Krai Veles (green) ──
  { name: 'Archee',    krai: 'veles',  type: 'home',     gx: 0.12, gy: 0.18, labelDir: 'top' },
  { name: 'Vale',      krai: 'veles',  type: 'internal', gx: 0.22, gy: 0.18, labelDir: 'top' },
  { name: 'Angymonne', krai: 'veles',  type: 'internal', gx: 0.22, gy: 0.30, labelDir: 'right' },
  { name: 'Ichoriya',  krai: 'veles',  type: 'internal', gx: 0.12, gy: 0.38, labelDir: 'left' },
  { name: 'Kaunokka',  krai: 'veles',  type: 'internal', gx: 0.22, gy: 0.46, labelDir: 'right' },
  { name: 'Arvasaras', krai: 'veles',  type: 'border',   gx: 0.34, gy: 0.46, labelDir: 'bottom' },
  { name: 'Wirashoda', krai: 'veles',  type: 'internal', gx: 0.12, gy: 0.58, labelDir: 'left' },
  { name: 'Ala',       krai: 'veles',  type: 'internal', gx: 0.22, gy: 0.58, labelDir: 'right' },
  { name: 'Senda',     krai: 'veles',  type: 'border',   gx: 0.12, gy: 0.72, labelDir: 'left' },

  // ── Krai Perun (blue) ──
  { name: 'Kino',      krai: 'perun',  type: 'home',     gx: 0.62, gy: 0.12, labelDir: 'top' },
  { name: 'Otela',     krai: 'perun',  type: 'internal', gx: 0.52, gy: 0.22, labelDir: 'left' },
  { name: 'Nalvula',   krai: 'perun',  type: 'internal', gx: 0.62, gy: 0.28, labelDir: 'right' },
  { name: 'Ignebaener',krai: 'perun',  type: 'internal', gx: 0.52, gy: 0.38, labelDir: 'left' },
  { name: 'Konola',    krai: 'perun',  type: 'internal', gx: 0.72, gy: 0.34, labelDir: 'right' },
  { name: 'Komo',      krai: 'perun',  type: 'internal', gx: 0.46, gy: 0.46, labelDir: 'top' },
  { name: 'Sakenta',   krai: 'perun',  type: 'border',   gx: 0.46, gy: 0.56, labelDir: 'right' },
  { name: 'Krirald',   krai: 'perun',  type: 'internal', gx: 0.78, gy: 0.46, labelDir: 'right' },
  { name: 'Otanuomi',  krai: 'perun',  type: 'border',   gx: 0.78, gy: 0.58, labelDir: 'right' },

  // ── Krai Svarog (amber) ──
  { name: 'Niarja',    krai: 'svarog', type: 'home',     gx: 0.50, gy: 0.72, labelDir: 'left' },
  { name: 'Raravoss',  krai: 'svarog', type: 'internal', gx: 0.62, gy: 0.72, labelDir: 'right' },
  { name: 'Harva',     krai: 'svarog', type: 'internal', gx: 0.50, gy: 0.82, labelDir: 'left' },
  { name: 'Skarkon',   krai: 'svarog', type: 'internal', gx: 0.72, gy: 0.66, labelDir: 'right' },
  { name: 'Nani',      krai: 'svarog', type: 'internal', gx: 0.78, gy: 0.76, labelDir: 'right' },
  { name: 'Urhinichi', krai: 'svarog', type: 'border',   gx: 0.86, gy: 0.66, labelDir: 'right' },
  { name: 'Tunudan',   krai: 'svarog', type: 'internal', gx: 0.38, gy: 0.82, labelDir: 'left' },
  { name: 'Kuharah',   krai: 'svarog', type: 'internal', gx: 0.26, gy: 0.82, labelDir: 'bottom' },
  { name: 'Ahtila',    krai: 'svarog', type: 'border',   gx: 0.18, gy: 0.82, labelDir: 'bottom' },
];

const GATES: PochvenGate[] = [
  // Krai Perun internal
  { from: 'Otela', to: 'Kino', crossKrai: false },
  { from: 'Otela', to: 'Nalvula', crossKrai: false },
  { from: 'Otela', to: 'Ignebaener', crossKrai: false },
  { from: 'Kino', to: 'Nalvula', crossKrai: false },
  { from: 'Nalvula', to: 'Konola', crossKrai: false },
  { from: 'Konola', to: 'Krirald', crossKrai: false },
  { from: 'Krirald', to: 'Otanuomi', crossKrai: false },
  { from: 'Ignebaener', to: 'Komo', crossKrai: false },
  { from: 'Komo', to: 'Sakenta', crossKrai: false },
  // Krai Svarog internal
  { from: 'Niarja', to: 'Raravoss', crossKrai: false },
  { from: 'Niarja', to: 'Harva', crossKrai: false },
  { from: 'Raravoss', to: 'Harva', crossKrai: false },
  { from: 'Raravoss', to: 'Skarkon', crossKrai: false },
  { from: 'Skarkon', to: 'Nani', crossKrai: false },
  { from: 'Nani', to: 'Urhinichi', crossKrai: false },
  { from: 'Harva', to: 'Tunudan', crossKrai: false },
  { from: 'Tunudan', to: 'Kuharah', crossKrai: false },
  { from: 'Kuharah', to: 'Ahtila', crossKrai: false },
  // Krai Veles internal
  { from: 'Archee', to: 'Angymonne', crossKrai: false },
  { from: 'Archee', to: 'Vale', crossKrai: false },
  { from: 'Angymonne', to: 'Vale', crossKrai: false },
  { from: 'Angymonne', to: 'Ichoriya', crossKrai: false },
  { from: 'Ichoriya', to: 'Kaunokka', crossKrai: false },
  { from: 'Kaunokka', to: 'Arvasaras', crossKrai: false },
  { from: 'Wirashoda', to: 'Ala', crossKrai: false },
  { from: 'Wirashoda', to: 'Senda', crossKrai: false },
  { from: 'Ala', to: 'Vale', crossKrai: false },
  // Cross-Krai
  { from: 'Arvasaras', to: 'Sakenta', crossKrai: true },
  { from: 'Senda', to: 'Ahtila', crossKrai: true },
  { from: 'Otanuomi', to: 'Urhinichi', crossKrai: true },
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
        // Reconstruct path
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
  return []; // unreachable
}

// ── Component ───────────────────────────────────────────────────────────────

const SYSTEM_MAP = new Map(SYSTEMS.map((s) => [s.name, s]));

export function PochvenMap() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ w: 800, h: 600 });
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
      const a = path[i], b = path[i + 1];
      edges.add(`${a}|${b}`);
      edges.add(`${b}|${a}`);
    }
    return edges;
  }, [path]);

  // Resize observer
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const observer = new ResizeObserver((entries) => {
      const { width } = entries[0].contentRect;
      // Maintain 4:3 aspect ratio, clamp height
      const h = Math.min(Math.round(width * 0.75), 700);
      setSize({ w: Math.round(width), h });
    });
    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  // Convert normalized coords to canvas pixels
  const toCanvas = useCallback(
    (gx: number, gy: number) => {
      const pad = 40;
      return {
        x: pad + gx * (size.w - pad * 2),
        y: pad + gy * (size.h - pad * 2),
      };
    },
    [size]
  );

  const nodeRadius = Math.max(8, Math.min(14, size.w / 70));

  // Hit test
  const hitTest = useCallback(
    (cx: number, cy: number): string | null => {
      const hitR = nodeRadius + 8; // generous touch target
      for (const sys of SYSTEMS) {
        const pos = toCanvas(sys.gx, sys.gy);
        const dx = cx - pos.x;
        const dy = cy - pos.y;
        if (dx * dx + dy * dy <= hitR * hitR) return sys.name;
      }
      return null;
    },
    [toCanvas, nodeRadius]
  );

  // Click handler
  const handleClick = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      const x = (e.clientX - rect.left) * dpr;
      const y = (e.clientY - rect.top) * dpr;
      const hit = hitTest(x / dpr, y / dpr);

      if (!hit) {
        setSelected([null, null]);
        return;
      }

      setSelected((prev) => {
        if (!prev[0]) return [hit, null];
        if (prev[0] === hit) return [null, null]; // deselect
        if (prev[1]) return [hit, null]; // reset
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
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const hit = hitTest(x, y);
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
      const x = touch.clientX - rect.left;
      const y = touch.clientY - rect.top;
      const hit = hitTest(x, y);
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

    // Draw Krai region backgrounds (subtle)
    for (const krai of ['veles', 'svarog', 'perun'] as Krai[]) {
      const systems = SYSTEMS.filter((s) => s.krai === krai);
      if (systems.length === 0) continue;
      const positions = systems.map((s) => toCanvas(s.gx, s.gy));
      const minX = Math.min(...positions.map((p) => p.x)) - 30;
      const maxX = Math.max(...positions.map((p) => p.x)) + 30;
      const minY = Math.min(...positions.map((p) => p.y)) - 30;
      const maxY = Math.max(...positions.map((p) => p.y)) + 30;
      ctx.fillStyle = KRAI_COLORS[krai] + '08'; // very subtle bg
      ctx.beginPath();
      ctx.roundRect(minX, minY, maxX - minX, maxY - minY, 12);
      ctx.fill();
    }

    // Draw connections
    for (const gate of GATES) {
      const fromSys = SYSTEM_MAP.get(gate.from);
      const toSys = SYSTEM_MAP.get(gate.to);
      if (!fromSys || !toSys) continue;

      const fromPos = toCanvas(fromSys.gx, fromSys.gy);
      const toPos = toCanvas(toSys.gx, toSys.gy);
      const isOnPath = pathEdges.has(`${gate.from}|${gate.to}`);

      ctx.save();
      ctx.beginPath();
      ctx.moveTo(fromPos.x, fromPos.y);
      ctx.lineTo(toPos.x, toPos.y);

      if (isOnPath) {
        // Bright path highlight
        ctx.strokeStyle = '#22d3ee';
        ctx.lineWidth = 3;
        ctx.shadowColor = '#22d3ee';
        ctx.shadowBlur = 8;
      } else if (gate.crossKrai) {
        ctx.setLineDash([6, 4]);
        ctx.strokeStyle = '#64748b';
        ctx.lineWidth = 1.5;
      } else {
        const color = KRAI_COLORS[fromSys.krai];
        ctx.strokeStyle = color + '50'; // 30% opacity
        ctx.lineWidth = 2;
      }
      ctx.stroke();
      ctx.restore();
    }

    // Draw system nodes
    for (const sys of SYSTEMS) {
      const pos = toCanvas(sys.gx, sys.gy);
      const isHovered = hovered === sys.name;
      const isSelected = selected[0] === sys.name || selected[1] === sys.name;
      const isOnPath = path.includes(sys.name);
      const r = isHovered ? nodeRadius + 2 : nodeRadius;
      const color = KRAI_COLORS[sys.krai];

      ctx.save();

      // Glow for path/selected nodes
      if (isOnPath || isSelected) {
        ctx.shadowColor = isSelected ? '#22d3ee' : color;
        ctx.shadowBlur = isSelected ? 12 : 6;
      }

      // Home system: larger ring
      if (sys.type === 'home') {
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, r + 4, 0, Math.PI * 2);
        ctx.strokeStyle = color + '40';
        ctx.lineWidth = 2;
        ctx.stroke();
      }

      // Border system: diamond shape
      if (sys.type === 'border') {
        ctx.beginPath();
        ctx.moveTo(pos.x, pos.y - r);
        ctx.lineTo(pos.x + r, pos.y);
        ctx.lineTo(pos.x, pos.y + r);
        ctx.lineTo(pos.x - r, pos.y);
        ctx.closePath();
        ctx.fillStyle = isSelected ? '#22d3ee' : color;
        ctx.fill();
      } else {
        // Circle for internal/home
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, r, 0, Math.PI * 2);
        ctx.fillStyle = isSelected ? '#22d3ee' : color;
        ctx.fill();
      }

      // Selection ring
      if (isSelected) {
        ctx.beginPath();
        if (sys.type === 'border') {
          const rr = r + 4;
          ctx.moveTo(pos.x, pos.y - rr);
          ctx.lineTo(pos.x + rr, pos.y);
          ctx.lineTo(pos.x, pos.y + rr);
          ctx.lineTo(pos.x - rr, pos.y);
          ctx.closePath();
        } else {
          ctx.arc(pos.x, pos.y, r + 4, 0, Math.PI * 2);
        }
        ctx.strokeStyle = '#22d3ee';
        ctx.lineWidth = 2;
        ctx.stroke();
      }

      ctx.restore();

      // Label
      const fontSize = Math.max(10, Math.min(12, size.w / 80));
      ctx.font = `${fontSize}px system-ui, -apple-system, sans-serif`;
      ctx.fillStyle = isOnPath || isSelected || isHovered ? '#ffffff' : '#94a3b8';
      ctx.textAlign = 'center';

      let lx = pos.x;
      let ly = pos.y;
      const labelOffset = r + fontSize + 2;
      switch (sys.labelDir) {
        case 'top':    ly -= labelOffset - fontSize; break;
        case 'bottom': ly += labelOffset; break;
        case 'left':   lx -= r + 4; ctx.textAlign = 'right'; ly += fontSize / 3; break;
        case 'right':  lx += r + 4; ctx.textAlign = 'left'; ly += fontSize / 3; break;
      }
      ctx.fillText(sys.name, lx, ly);
    }

    // Legend
    const legendX = 10;
    const legendY = size.h - 80;
    ctx.font = '11px system-ui, -apple-system, sans-serif';

    for (const [i, krai] of (['perun', 'svarog', 'veles'] as Krai[]).entries()) {
      const y = legendY + i * 18;
      ctx.beginPath();
      ctx.arc(legendX + 6, y, 5, 0, Math.PI * 2);
      ctx.fillStyle = KRAI_COLORS[krai];
      ctx.fill();
      ctx.fillStyle = '#94a3b8';
      ctx.textAlign = 'left';
      ctx.fillText(KRAI_LABELS[krai], legendX + 16, y + 4);
    }

    // Cross-Krai legend
    const crossY = legendY + 54;
    ctx.save();
    ctx.setLineDash([4, 3]);
    ctx.beginPath();
    ctx.moveTo(legendX, crossY);
    ctx.lineTo(legendX + 12, crossY);
    ctx.strokeStyle = '#64748b';
    ctx.lineWidth = 1.5;
    ctx.stroke();
    ctx.restore();
    ctx.fillStyle = '#94a3b8';
    ctx.textAlign = 'left';
    ctx.fillText('Cross-Krai Gate', legendX + 16, crossY + 4);
  }, [size, hovered, selected, path, pathEdges, toCanvas, nodeRadius]);

  // ── Info panel content ────────────────────────────────────────────────────

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
            Click a system to start routing. Click a second to find shortest path.
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
            <span className="text-sm text-text font-medium">
              {selectedInfo.sysA.name}
            </span>
            <span className="text-xs text-text-secondary">to</span>
            <span className="text-sm text-text font-medium">
              {selectedInfo.sysB.name}
            </span>
            <Badge variant="default" className="text-xs bg-cyan-500/20 text-cyan-400">
              {path.length - 1} {path.length - 1 === 1 ? 'jump' : 'jumps'}
            </Badge>
            <span className="text-xs text-text-secondary hidden sm:inline">
              {path.join(' \u2192 ')}
            </span>
          </div>
        )}
      </div>

      {/* Canvas */}
      <div ref={containerRef} className="w-full">
        <canvas
          ref={canvasRef}
          onClick={handleClick}
          onMouseMove={handleMove}
          onMouseLeave={() => setHovered(null)}
          onTouchStart={handleTouch}
          className="w-full rounded-lg border border-border"
          style={{ touchAction: 'manipulation' }}
        />
      </div>

      {/* Path detail on mobile (arrows too long for info bar) */}
      {path.length > 2 && (
        <div className="sm:hidden">
          <Card>
            <div className="text-xs text-text-secondary">
              <span className="font-medium text-text">Route: </span>
              {path.join(' \u2192 ')}
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
