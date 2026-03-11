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
// Perfect triangle: apex (0.50, 0.05) → bottom-left (0.05, 0.90) → bottom-right (0.95, 0.90)
// Left edge:  x = 0.50 - (y - 0.05) * 0.5294
// Right edge: x = 0.50 + (y - 0.05) * 0.5294

const SYSTEMS: PochvenSystem[] = [
  // ── Krai Veles (green) — top pyramid ──
  { name: 'Archee',     krai: 'veles',  type: 'home',     gx: 0.50, gy: 0.05, originRegion: 'Solitude' },
  { name: 'Vale',       krai: 'veles',  type: 'internal', gx: 0.45, gy: 0.15, originRegion: 'Verge Vendor' },
  { name: 'Angymonne',  krai: 'veles',  type: 'internal', gx: 0.55, gy: 0.15, originRegion: 'Everyshore' },
  { name: 'Ala',        krai: 'veles',  type: 'internal', gx: 0.39, gy: 0.25, originRegion: 'Solitude' },
  { name: 'Ichoriya',   krai: 'veles',  type: 'internal', gx: 0.61, gy: 0.25, originRegion: 'Black Rise' },
  { name: 'Wirashoda',  krai: 'veles',  type: 'internal', gx: 0.34, gy: 0.35, originRegion: 'The Forge' },
  { name: 'Kaunokka',   krai: 'veles',  type: 'internal', gx: 0.66, gy: 0.35, originRegion: 'Lonetrek' },
  { name: 'Senda',      krai: 'veles',  type: 'border',   gx: 0.28, gy: 0.45, originRegion: 'The Forge' },
  { name: 'Arvasaras',  krai: 'veles',  type: 'border',   gx: 0.72, gy: 0.45, originRegion: 'The Citadel' },

  // ── Krai Svarog (red) — left leg + bottom-left ──
  { name: 'Ahtila',     krai: 'svarog', type: 'border',   gx: 0.24, gy: 0.53, originRegion: 'Black Rise' },
  { name: 'Kuharah',    krai: 'svarog', type: 'internal', gx: 0.20, gy: 0.61, originRegion: 'Devoid' },
  { name: 'Tunudan',    krai: 'svarog', type: 'internal', gx: 0.15, gy: 0.69, originRegion: 'Lonetrek' },
  { name: 'Harva',      krai: 'svarog', type: 'internal', gx: 0.11, gy: 0.77, originRegion: 'Domain' },
  { name: 'Niarja',     krai: 'svarog', type: 'home',     gx: 0.05, gy: 0.90, originRegion: 'Domain' },
  { name: 'Raravoss',   krai: 'svarog', type: 'internal', gx: 0.15, gy: 0.90, originRegion: 'Domain' },
  { name: 'Skarkon',    krai: 'svarog', type: 'internal', gx: 0.25, gy: 0.90, originRegion: 'Molden Heath' },
  { name: 'Nani',       krai: 'svarog', type: 'internal', gx: 0.35, gy: 0.90, originRegion: 'The Citadel' },
  { name: 'Urhinichi',  krai: 'svarog', type: 'border',   gx: 0.45, gy: 0.90, originRegion: 'The Forge' },

  // ── Krai Perun (blue) — right leg + bottom-right ──
  { name: 'Sakenta',    krai: 'perun',  type: 'border',   gx: 0.76, gy: 0.53, originRegion: 'The Citadel' },
  { name: 'Komo',       krai: 'perun',  type: 'internal', gx: 0.80, gy: 0.61, originRegion: 'The Citadel' },
  { name: 'Ignebaener', krai: 'perun',  type: 'internal', gx: 0.85, gy: 0.69, originRegion: 'Sinq Laison' },
  { name: 'Otela',      krai: 'perun',  type: 'internal', gx: 0.89, gy: 0.77, originRegion: 'The Forge' },
  { name: 'Kino',       krai: 'perun',  type: 'home',     gx: 0.95, gy: 0.90, originRegion: 'Lonetrek' },
  { name: 'Nalvula',    krai: 'perun',  type: 'internal', gx: 0.85, gy: 0.90, originRegion: 'Lonetrek' },
  { name: 'Konola',     krai: 'perun',  type: 'internal', gx: 0.75, gy: 0.90, originRegion: 'The Forge' },
  { name: 'Krirald',    krai: 'perun',  type: 'internal', gx: 0.65, gy: 0.90, originRegion: 'Metropolis' },
  { name: 'Otanuomi',   krai: 'perun',  type: 'border',   gx: 0.55, gy: 0.90, originRegion: 'The Forge' },
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

// ── C729 Wormhole Entry Candidates (from pochven.electusmatari.com) ─────────
// Each Pochven system has a guaranteed C729 wormhole that spawns in one of these
// k-space systems (within ~3 jumps of the system's original location).

const C729_CANDIDATES: Record<string, string[]> = {
  // Home systems
  Archee: ['Adrallezoen', 'Ardene', 'Atier', 'Bawilan', 'Boillair', 'Brapelille', 'Brybier', 'Caretyn', 'Croleur', 'Fricoure', 'Ney', 'Ardallabier'],
  Niarja: ['Amarr', 'Arbaz', 'Ashab', 'Bahromab', 'Bhizheba', 'Chaven', 'Fabum', 'Hedion', 'Kehour', 'Kudi', 'Madirmilire', 'Penirgman', 'Saana', 'Sayartchen', 'Sharji', 'Teshi', 'Aphend', 'Romi', 'Halaima', 'Ikao', 'Inaro', 'Kaaputenen', 'Kamio', 'Sirppala', 'Waskisen', 'Sirseshin'],
  Kino: ['Ajanen', 'Erenta', 'Isanamo', 'Kuoka', 'Litiura', 'Ouranienen', 'Sotrentaira', 'Uemisaisen', 'Hogimo', 'Huttaken', 'Kulelen', 'Venilen', 'Yria'],
  // Border systems
  Senda: ['Geras', 'Shihuken', 'Sirseshin', 'Tuuriainas', 'Uitra', 'Unpas', 'Urlen'],
  Ahtila: ['Aivonen', 'Akidagi', 'Asakai', 'Astoh', 'Enaluri', 'Ikoskio', 'Innia', 'Kinakka', 'Martoh', 'Nennamaila', 'Onnamon', 'Prism', 'Raihbaka', 'Rohamaa', 'Samanuni', 'Tsuruma', 'Uchomida', 'Uuhulanen', 'Elonaya', 'Haajinen', 'Piak'],
  Arvasaras: ['Aikoro', 'Alikara', 'Kaimon', 'Akonoinen', 'Autaris', 'Hageken', 'Isanamo', 'Jan', 'Vaajaita', 'Vellaine', 'New Caldari'],
  Sakenta: ['Ahynada', 'Muvolailen', 'Ansila', 'Aokannitoh', 'Hirtamon', 'Hykkota', 'Ikuchi', 'Maurasi', 'New Caldari', 'Niyabainen', 'Perimeter', 'Ichinumi', 'Nourvukaiken', 'Sarekuwa', 'Sobaseki', 'Tunttaras'],
  Otanuomi: ['Akkilen', 'Eruka', 'Friggi', 'Hentogaira', 'Ihakana', 'Kiainti', 'Mastakomon', 'Ohkunen', 'Osaa', 'Otitoh', 'Otomainen', 'Otsela', 'Uchoshi', 'Vasala', 'Vouskiaho', 'Walvalin'],
  Urhinichi: ['Anttiri', 'Inaro', 'Isikesu', 'Juunigaishi', 'Kaaputenen', 'Kusomonmon', 'Sirppala', 'Suroken', 'Waskisen', 'Kisogo', 'Perimeter', 'Sirseshin', 'Unpas', 'Urlen'],
  // Internal systems
  Harva: ['Aghesi', 'Airshaz', 'Charra', 'Fabin', 'Madimal', 'Maiah', 'Murema', 'Murzi', 'Patzcha', 'Yuhelia'],
  Nani: ['Autama', 'Iidoken', 'Isanamo', 'Kirras', 'Nourvukaiken', 'Ouranienen', 'Sarekuwa', 'Tsuguwa', 'Tsukuras', 'Veisto'],
  Otela: ['Alikara', 'Geras', 'Hirtamon', 'Josameto', 'Liekuri', 'New Caldari', 'Niyabainen', 'Nomaa', 'Obanen', 'Olo', 'Poinen', 'Saisio', 'Malkalen'],
  Angymonne: ['Aice', 'Amattens', 'Antollare', 'Avele', 'Averon', 'Bereye', 'Carirgnottin', 'Enedore', 'Jurlesel', 'Laic', 'Leremblompes', 'Muer', 'Odixie', 'Scuelazyns', 'Tolle'],
  Ala: ['Adrallezoen', 'Aliette', 'Ardene', 'Boillair', 'Fasse', 'Gratesier', 'Ney', 'Odette', 'Ravarin', 'Schoorasana', 'Stegette', 'Ardallabier', 'Mormelot', 'Kurniainen', 'Saidusairos'],
  Ignebaener: ['Adirain', 'Aere', 'Aeschee', 'Arnon', 'Attyn', 'Hulmate', 'Ladistier', 'Laurvier', 'Lisbaetanne', 'Onne', 'Amoderia', 'Arraron', 'Chantrousse', 'Jovainnon', 'Stou'],
  Raravoss: ['Anka', 'Gammel', 'Iesa', 'Kamela', 'Myyhera', 'Netsalakka', 'Saikamon', 'Sasiekko', 'Sosala', 'Uusanen', 'Ardishapur Prime', 'Ekid', 'Gid', 'Mai', 'Nakri', 'Orkashu', 'Rasile', 'Sharhelund', 'Thebeka', 'Youl', 'Zaimeth'],
  Vale: ['Allamotte', 'Andole', 'Arant', 'Atlangeins', 'Cat', 'Derririntel', 'Old Man Star', 'Ommare', 'Pemene', 'Villore', 'Erme', 'Tierijev'],
  Konola: ['Ahynada', 'Aikoro', 'Eitu', 'Erila', 'Horkkisen', 'Inoue', 'Isaziwa', 'Kaimon', 'Oiniken'],
  Krirald: ['Anher', 'Ansen', 'Arifsdald', 'Arwa', 'Bei', 'Dudreda', 'Hagilur', 'Hakisalki', 'Ragnarg', 'Thelan'],
  Kuharah: ['Doril', 'Futzchag', 'Jayneleb', 'Kazna', 'Lilmad', 'Mifrata', 'Onsooh', 'Podion', 'Sendaya'],
  Kaunokka: ['Erenta', 'Hogimo', 'Huttaken', 'Hysera', 'Kulelen', 'Oisio', 'Oshaima', 'Venilen', 'Yria'],
  Komo: ['Ahynada', 'Aikoro', 'Annaro', 'Aramachi', 'Auviken', 'Isaziwa', 'Isenairos', 'Kaimon', 'Kausaaja', 'Laah', 'Motsu', 'Muvolailen', 'Oichiya', 'Oiniken', 'Paara', 'Saila', 'Uotila', 'Ichinumi', 'Nourvukaiken', 'Sarekuwa', 'Tunttaras', 'Ikuchi', 'Niyabainen'],
  Nalvula: ['Akonoinen', 'Aurohunen', 'Autaris', 'Hageken', 'Hakonen', 'Jan', 'Oimmo', 'Otsasai', 'Taisy', 'Uosusuokko', 'Vaajaita', 'Vellaine', 'Vuorrassi', 'E-OGL4', 'FY0W-N', 'J-GAMP', 'M-OEE8', 'V0DF-2', 'Obe', 'Ohkunen', 'P3EN-E'],
  Skarkon: ['C-4D0W', 'CT8K-0', 'IL-H0A', 'L4X-1V', 'M9-LAN', 'PX-IHN', 'WPV-JN', 'Ennur', 'Fegomenko', 'Illamur', 'Meildolf', 'Mimiror', 'Orien', 'Osvetur', 'Unertek', 'Offikatlin', 'Tabbetzur'],
  Tunudan: ['Enderailen', 'Hogimo', 'Huttaken', 'Kubinen', 'Kulelen', 'Oisio', 'Oshaima', 'Rairomon', 'Sivala', 'Uedama', 'Venilen', 'Yria'],
  Wirashoda: ['Eruka', 'Mastakomon', 'Ohkunen', 'Osaa', 'Uchoshi', 'Vasala', 'Vouskiaho'],
  Ichoriya: ['Aivonen', 'Akidagi', 'Enaluri', 'Hallanen', 'Hikkoken', 'Ikoskio', 'Immuri', 'Kinakka', 'Nennamaila', 'Onnamon', 'Pavanakka', 'Rohamaa', 'Samanuni', 'Tsuruma', 'Uchomida', 'Uuhulanen', 'Piak', 'Aldranette'],
};

// Wormhole types that connect to Pochven
const WH_TYPES = [
  { type: 'C729', dir: 'K-Space → Pochven', mass: '1B kg', jump: '410M kg', life: '12h', note: 'Guaranteed — every system always has one' },
  { type: 'X450', dir: 'Pochven → Nullsec', mass: '1B kg', jump: '300M kg', life: '16h', note: '' },
  { type: 'R081', dir: 'Pochven → C4 WH', mass: '1B kg', jump: '300M kg', life: '16h', note: '' },
  { type: 'U372', dir: 'Drone Regions → Pochven', mass: '1B kg', jump: '300M kg', life: '16h', note: '' },
  { type: 'F216', dir: 'WH Space → Pochven', mass: '1B kg', jump: '300M kg', life: '16h', note: '' },
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

function getAdjacent(name: string): string[] {
  const adj: string[] = [];
  for (const g of GATES) {
    if (g.from === name) adj.push(g.to);
    else if (g.to === name) adj.push(g.from);
  }
  return adj;
}

const NODE_H = 24;
const NODE_PAD_X = 12;

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

  const toCanvas = useCallback(
    (gx: number, gy: number) => {
      const padX = 60;
      const padY = 30;
      return {
        x: padX + gx * (size.w - padX * 2),
        y: padY + gy * (size.h - padY * 2),
      };
    },
    [size]
  );

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

    // Edge-to-edge line connection helper
    const getEdgePoint = (from: PochvenSystem, to: PochvenSystem) => {
      const fp = toCanvas(from.gx, from.gy);
      const tp = toCanvas(to.gx, to.gy);
      const fw = (nodeWidths.get(from.name) || 80) / 2;
      const fh = NODE_H / 2;
      const dx = tp.x - fp.x;
      const dy = tp.y - fp.y;
      const angle = Math.atan2(dy, dx);
      const tanA = Math.abs(dy / (dx || 0.001));
      const tanBox = fh / fw;
      let ex: number, ey: number;
      if (tanA <= tanBox) {
        ex = fp.x + Math.sign(dx) * fw;
        ey = fp.y + Math.sign(dx) * fw * Math.tan(angle);
      } else {
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
        ctx.strokeStyle = KRAI_COLORS[fromSys.krai] + '70';
        ctx.lineWidth = 2;
      }
      ctx.stroke();
      ctx.restore();
    }

    // Draw system nodes
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

      if (isSelected || isOnPath) {
        ctx.shadowColor = isSelected ? '#22d3ee' : color;
        ctx.shadowBlur = isSelected ? 14 : 8;
      }
      if (isHovered && !isSelected) {
        ctx.shadowColor = color;
        ctx.shadowBlur = 10;
      }

      const rx = pos.x - halfW;
      const ry = pos.y - halfH;
      const expand = isHovered ? 2 : 0;

      ctx.fillStyle = isSelected ? '#22d3ee' : color;
      ctx.beginPath();
      ctx.roundRect(rx - expand, ry - expand, w + expand * 2, NODE_H + expand * 2, 4);
      ctx.fill();

      if (isSelected) {
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.roundRect(rx - 3, ry - 3, w + 6, NODE_H + 6, 6);
        ctx.stroke();
      }

      // Home system diamond marker
      if (sys.type === 'home') {
        ctx.strokeStyle = '#ffffff80';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.roundRect(rx - 5, ry - 5, w + 10, NODE_H + 10, 8);
        ctx.stroke();
      }

      ctx.restore();

      // Label
      ctx.fillStyle = '#ffffff';
      ctx.font = `bold ${fontSize}px system-ui, -apple-system, sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(sys.name, pos.x, pos.y);
    }

    // Krai labels (dim, in background)
    ctx.font = `600 ${Math.max(12, size.w / 55)}px system-ui, -apple-system, sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    const velesLabel = toCanvas(0.50, 0.28);
    ctx.fillStyle = KRAI_COLORS.veles + '25';
    ctx.fillText('KRAI VELES', velesLabel.x, velesLabel.y);

    const svarogLabel = toCanvas(0.15, 0.65);
    ctx.fillStyle = KRAI_COLORS.svarog + '25';
    ctx.fillText('KRAI SVAROG', svarogLabel.x, svarogLabel.y);

    const perunLabel = toCanvas(0.85, 0.65);
    ctx.fillStyle = KRAI_COLORS.perun + '25';
    ctx.fillText('KRAI PERUN', perunLabel.x, perunLabel.y);

  }, [size, hovered, selected, path, pathEdges, toCanvas, nodeWidths]);

  // ── Info panel data ─────────────────────────────────────────────────────────

  const selectedSys = useMemo(() => {
    return selected[0] ? SYSTEM_MAP.get(selected[0]) ?? null : null;
  }, [selected]);

  const selectedAdj = useMemo(() => {
    if (!selected[0]) return [];
    return getAdjacent(selected[0]).map((name) => SYSTEM_MAP.get(name)!).filter(Boolean);
  }, [selected]);

  const selectedInfo = useMemo(() => {
    const [a, b] = selected;
    return { sysA: a ? SYSTEM_MAP.get(a) : null, sysB: b ? SYSTEM_MAP.get(b) : null };
  }, [selected]);

  const c729Systems = useMemo(() => {
    if (!selected[0]) return [];
    return C729_CANDIDATES[selected[0]] || [];
  }, [selected]);

  return (
    <div className="space-y-3">
      {/* Info bar */}
      <div className="flex flex-wrap items-center gap-2 min-h-[36px]">
        {!selected[0] && (
          <span className="text-sm text-text-secondary">
            Click a system to view connections &amp; C729 entry points. Click a second for shortest route.
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
            <span className="text-xs text-text-secondary ml-2">Click another for route</span>
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

      {/* Canvas + detail panel side-by-side */}
      <div className="flex gap-3">
        {/* Canvas */}
        <div ref={containerRef} className={`${selectedSys && !selected[1] ? 'flex-1 min-w-0' : 'w-full'}`}>
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

        {/* System detail panel — right side */}
        {selectedSys && !selected[1] && (
          <div className="w-[340px] shrink-0 bg-gray-900/95 border border-gray-700 rounded-lg shadow-2xl backdrop-blur-sm p-4 overflow-y-auto max-h-[750px]">
            {/* Header */}
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div
                  className="w-3 h-3 rounded-sm"
                  style={{ backgroundColor: KRAI_COLORS[selectedSys.krai] }}
                />
                <span className="font-bold text-white text-base">{selectedSys.name}</span>
              </div>
              <button
                onClick={() => setSelected([null, null])}
                className="text-gray-500 hover:text-white text-sm px-1"
              >
                ✕
              </button>
            </div>

            {/* System info */}
            <div className="space-y-1.5 text-xs">
              <div className="flex justify-between">
                <span className="text-gray-400">Krai</span>
                <span style={{ color: KRAI_COLORS[selectedSys.krai] }}>
                  {KRAI_LABELS[selectedSys.krai]}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Type</span>
                <span className="text-gray-200 capitalize">{selectedSys.type}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Origin Region</span>
                <span className="text-gray-200">{selectedSys.originRegion}</span>
              </div>
              {selectedSys.type === 'home' && (
                <div className="mt-1 px-2 py-1 bg-amber-500/10 border border-amber-500/30 rounded text-amber-400 text-[10px]">
                  Gate access requires 7.0 Triglavian standing
                </div>
              )}
            </div>

            {/* Gate connections */}
            <div className="mt-4 pt-3 border-t border-gray-700">
              <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">
                Gate Connections ({selectedAdj.length})
              </span>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {selectedAdj.map((adj) => (
                  <button
                    key={adj.name}
                    onClick={() => setSelected([adj.name, null])}
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

            {/* C729 Entry Systems */}
            <div className="mt-4 pt-3 border-t border-gray-700">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">
                  C729 Entry Systems
                </span>
                <span className="text-[10px] text-cyan-400 font-mono">
                  {c729Systems.length} candidates
                </span>
              </div>
              <p className="text-[10px] text-gray-500 mt-1">
                K-space systems where the guaranteed C729 wormhole can spawn (scan from these systems to find entry)
              </p>
              <div className="mt-2 flex flex-wrap gap-1">
                {c729Systems.map((sys) => (
                  <span
                    key={sys}
                    className="text-[10px] px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/20"
                  >
                    {sys}
                  </span>
                ))}
              </div>
              {c729Systems.length === 0 && (
                <p className="text-[10px] text-gray-500 mt-1 italic">No candidate data available</p>
              )}
            </div>

            {/* Wormhole Types */}
            <div className="mt-4 pt-3 border-t border-gray-700">
              <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">
                Wormhole Types
              </span>
              <div className="mt-2 space-y-1.5">
                {WH_TYPES.map((wh) => (
                  <div key={wh.type} className="flex items-start gap-2 text-[10px]">
                    <span className="font-mono text-cyan-400 w-8 shrink-0">{wh.type}</span>
                    <span className="text-gray-300 flex-1">{wh.dir}</span>
                    <span className="text-gray-500 shrink-0">{wh.life}</span>
                  </div>
                ))}
              </div>
              <p className="text-[10px] text-gray-500 mt-2 italic">
                C729 guaranteed &amp; respawns instantly if rolled. Others spawn dynamically.
              </p>
            </div>

            {/* Source attribution */}
            <div className="mt-4 pt-3 border-t border-gray-700">
              <p className="text-[9px] text-gray-600">
                C729 candidate data from{' '}
                <a
                  href="https://pochven.electusmatari.com/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-cyan-600 hover:text-cyan-400 underline"
                >
                  Electus Matari Pochven Manual
                </a>
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
