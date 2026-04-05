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
  perun: '#22c55e',  // green
  svarog: '#3b82f6', // blue
  veles: '#f59e0b',  // orange
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

const NODE_RADIUS = 8;
const DIAMOND_SIZE = 10;

interface PochvenMapProps {
  killCounts?: Record<string, number>;
}

export function PochvenMap({ killCounts = {} }: PochvenMapProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ w: 900, h: 700 });
  const [hovered, setHovered] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [pulsePhase, setPulsePhase] = useState(0);

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

  const hitTest = useCallback(
    (cx: number, cy: number): string | null => {
      const hitRadius = 14; // generous hit area
      for (const sys of SYSTEMS) {
        const pos = toCanvas(sys.gx, sys.gy);
        const dx = cx - pos.x;
        const dy = cy - pos.y;
        if (dx * dx + dy * dy <= hitRadius * hitRadius) {
          return sys.name;
        }
      }
      return null;
    },
    [toCanvas]
  );

  const handleClick = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const hit = hitTest(e.clientX - rect.left, e.clientY - rect.top);
      setSelected(hit === selected ? null : hit);
    },
    [hitTest, selected]
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
        setSelected(hit === selected ? null : hit);
      }
    },
    [hitTest, selected]
  );

  // ── Canvas draw ───────────────────────────────────────────────────────────

  const hasKills = Object.values(killCounts).some((c) => c > 0);

  // Pulse animation for kill glow rings (~30fps)
  useEffect(() => {
    if (!hasKills) return;
    const id = setInterval(() => setPulsePhase((p) => p + 0.1), 33);
    return () => clearInterval(id);
  }, [hasKills]);

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

    const fontSize = Math.max(9, Math.min(12, size.w / 85));
    const nodeRadius = Math.max(5, Math.min(NODE_RADIUS, size.w / 120));
    const diamondSize = Math.max(6, Math.min(DIAMOND_SIZE, size.w / 100));

    // ── Krai region backgrounds ──
    const kraiSystems: Record<Krai, { x: number; y: number }[]> = {
      perun: [], svarog: [], veles: [],
    };
    for (const sys of SYSTEMS) {
      kraiSystems[sys.krai].push(toCanvas(sys.gx, sys.gy));
    }
    for (const krai of ['veles', 'svarog', 'perun'] as Krai[]) {
      const pts = kraiSystems[krai];
      if (pts.length === 0) continue;
      let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
      for (const p of pts) {
        minX = Math.min(minX, p.x);
        minY = Math.min(minY, p.y);
        maxX = Math.max(maxX, p.x);
        maxY = Math.max(maxY, p.y);
      }
      const pad = 25;
      ctx.fillStyle = KRAI_COLORS[krai] + '0a';
      ctx.strokeStyle = KRAI_COLORS[krai] + '18';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.roundRect(minX - pad, minY - pad, maxX - minX + pad * 2, maxY - minY + pad * 2, 8);
      ctx.fill();
      ctx.stroke();
    }

    // ── Krai labels (dim, behind everything) ──
    ctx.font = `600 ${Math.max(12, size.w / 55)}px system-ui, -apple-system, sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    const velesLabel = toCanvas(0.50, 0.28);
    ctx.fillStyle = KRAI_COLORS.veles + '20';
    ctx.fillText('KRAI VELES', velesLabel.x, velesLabel.y);

    const svarogLabel = toCanvas(0.15, 0.65);
    ctx.fillStyle = KRAI_COLORS.svarog + '20';
    ctx.fillText('KRAI SVAROG', svarogLabel.x, svarogLabel.y);

    const perunLabel = toCanvas(0.85, 0.65);
    ctx.fillStyle = KRAI_COLORS.perun + '20';
    ctx.fillText('KRAI PERUN', perunLabel.x, perunLabel.y);

    // ── Draw connections ──
    for (const gate of GATES) {
      const fromSys = SYSTEM_MAP.get(gate.from);
      const toSys = SYSTEM_MAP.get(gate.to);
      if (!fromSys || !toSys) continue;

      const fp = toCanvas(fromSys.gx, fromSys.gy);
      const tp = toCanvas(toSys.gx, toSys.gy);

      ctx.save();
      ctx.beginPath();
      ctx.moveTo(fp.x, fp.y);
      ctx.lineTo(tp.x, tp.y);

      if (gate.crossKrai) {
        ctx.setLineDash([4, 3]);
        ctx.strokeStyle = '#334155';
        ctx.globalAlpha = 0.5;
        ctx.lineWidth = 1.5;
      } else {
        ctx.strokeStyle = KRAI_COLORS[fromSys.krai] + '60';
        ctx.lineWidth = 2;
      }
      ctx.stroke();
      ctx.globalAlpha = 1;
      ctx.restore();
    }

    // ── Draw system nodes ──
    ctx.font = `600 ${fontSize}px system-ui, -apple-system, sans-serif`;

    // Helper: draw diamond shape
    const drawDiamond = (cx: number, cy: number, s: number) => {
      ctx.beginPath();
      ctx.moveTo(cx, cy - s);
      ctx.lineTo(cx + s, cy);
      ctx.lineTo(cx, cy + s);
      ctx.lineTo(cx - s, cy);
      ctx.closePath();
    };

    for (const sys of SYSTEMS) {
      const pos = toCanvas(sys.gx, sys.gy);
      const isHovered = hovered === sys.name;
      const isSelected = selected === sys.name;
      const color = KRAI_COLORS[sys.krai];
      const isBorder = sys.type === 'border';

      ctx.save();

      // Glow for hovered/selected
      if (isSelected) {
        ctx.shadowColor = '#22d3ee';
        ctx.shadowBlur = 16;
      } else if (isHovered) {
        ctx.shadowColor = color;
        ctx.shadowBlur = 12;
      }

      const r = isHovered ? nodeRadius + 2 : nodeRadius;
      const d = isHovered ? diamondSize + 2 : diamondSize;

      // Fill shape
      ctx.fillStyle = isSelected ? '#22d3ee' : color;
      if (isBorder) {
        drawDiamond(pos.x, pos.y, d);
      } else {
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, r, 0, Math.PI * 2);
      }
      ctx.fill();

      // Stroke for home systems (thicker ring)
      if (sys.type === 'home') {
        ctx.strokeStyle = '#ffffff60';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, r + 4, 0, Math.PI * 2);
        ctx.stroke();
      }

      // Selection ring
      if (isSelected) {
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 2;
        if (isBorder) {
          drawDiamond(pos.x, pos.y, d + 4);
        } else {
          ctx.beginPath();
          ctx.arc(pos.x, pos.y, r + 4, 0, Math.PI * 2);
        }
        ctx.stroke();
      }

      ctx.restore();

      // ── Kill indicators ──
      const sysKills = killCounts[sys.name] || 0;
      if (sysKills > 0) {
        const killPulse = (Math.sin(pulsePhase * 1.5) + 1) / 2;
        const intensity = Math.min(sysKills / 20, 1);
        const baseR = isBorder ? d : r;

        // Pulsing red glow ring
        ctx.save();
        const glowR = baseR + 6 + killPulse * 4 * intensity;
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, glowR, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255, 69, 58, ${0.06 + killPulse * 0.10 * intensity})`;
        ctx.fill();
        ctx.strokeStyle = `rgba(255, 69, 58, ${0.15 + killPulse * 0.25 * intensity})`;
        ctx.lineWidth = 1;
        ctx.stroke();
        ctx.restore();

        // Red pill badge above-right of node
        const bx = pos.x + baseR + 3;
        const by = pos.y - baseR - 3;
        const badgeText = sysKills > 99 ? '99+' : String(sysKills);
        ctx.save();
        ctx.font = 'bold 8px system-ui, -apple-system, sans-serif';
        const tw = ctx.measureText(badgeText).width;
        const bw = Math.max(tw + 6, 14);
        const bh = 11;
        // Pill background
        ctx.beginPath();
        ctx.roundRect(bx - bw / 2, by - bh / 2, bw, bh, bh / 2);
        ctx.fillStyle = '#dc2626';
        ctx.fill();
        // Badge text
        ctx.fillStyle = '#ffffff';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(badgeText, bx, by);
        ctx.restore();
      }

      // Label below node — subway style with text shadow
      ctx.font = `600 ${fontSize}px system-ui, -apple-system, sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      const labelY = pos.y + (isBorder ? d : r) + 4;
      // Text shadow for readability
      ctx.fillStyle = '#000000';
      ctx.globalAlpha = 0.6;
      ctx.fillText(sys.name, pos.x + 0.5, labelY + 0.5);
      // Label text
      ctx.fillStyle = isSelected || isHovered ? '#ffffff' : '#c8ccd4';
      ctx.globalAlpha = isSelected || isHovered ? 1 : 0.9;
      ctx.fillText(sys.name, pos.x, labelY);
      ctx.globalAlpha = 1;
    }

  }, [size, hovered, selected, toCanvas, killCounts, pulsePhase]);

  // ── Info panel data ─────────────────────────────────────────────────────────

  const selectedSys = useMemo(() => {
    return selected ? SYSTEM_MAP.get(selected) ?? null : null;
  }, [selected]);

  const selectedAdj = useMemo(() => {
    if (!selected) return [];
    return getAdjacent(selected).map((name) => SYSTEM_MAP.get(name)!).filter(Boolean);
  }, [selected]);

  const c729Systems = useMemo(() => {
    if (!selected) return [];
    return C729_CANDIDATES[selected] || [];
  }, [selected]);

  return (
    <div className="space-y-3">
      {/* Info bar */}
      <div className="flex flex-wrap items-center gap-2 min-h-[36px]">
        {!selected && (
          <span className="text-sm text-text-secondary">
            Click a system to view connections &amp; C729 entry points.
          </span>
        )}
        {selectedSys && (
          <div className="flex items-center gap-2">
            <Badge
              variant="default"
              className="text-xs"
              style={{ backgroundColor: KRAI_COLORS[selectedSys.krai] + '30', color: KRAI_COLORS[selectedSys.krai] }}
            >
              {KRAI_LABELS[selectedSys.krai]}
            </Badge>
            <span className="text-sm text-text font-medium">{selectedSys.name}</span>
            <span className="text-sm text-text-secondary capitalize">({selectedSys.type})</span>
            <span className="text-xs text-text-secondary ml-2">from {selectedSys.originRegion}</span>
          </div>
        )}
      </div>

      {/* Canvas + detail panel side-by-side */}
      <div className="flex gap-3">
        {/* Canvas */}
        <div ref={containerRef} className={`${selectedSys ? 'flex-1 min-w-0' : 'w-full'}`}>
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
        {selectedSys && (
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
                onClick={() => setSelected(null)}
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
                    onClick={() => setSelected(adj.name)}
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

    </div>
  );
}
