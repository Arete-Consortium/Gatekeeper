'use client';

import { useState, useMemo } from 'react';
import dynamic from 'next/dynamic';
import { useKillStream } from '@/components/map/useKillStream';

const PochvenMap = dynamic(
  () => import('@/components/pochven/PochvenMap').then((m) => m.PochvenMap),
  { ssr: false }
);
const StreamingKillFeed = dynamic(
  () => import('@/components/intel/StreamingKillFeed').then((m) => m.StreamingKillFeed),
  { ssr: false }
);
import { Card, Badge } from '@/components/ui';
import {
  Map,
  Compass,
  ShieldAlert,
  Landmark,
  ChevronDown,
  ChevronUp,
  ExternalLink,
} from 'lucide-react';

const POCHVEN_REGION_ID = 10000070;

// ── Pochven Reference Data ──────────────────────────────────────────────────

const WORMHOLE_TYPES = [
  { type: 'C729', origin: 'K-Space (3-jump radius)', dest: 'Pochven', mass: '1B kg', maxJump: '410M kg', life: '12h', guards: 'EDENCOM', note: 'Guaranteed — every system has one at all times' },
  { type: 'X450', origin: 'Pochven', dest: 'Nullsec', mass: '1B kg', maxJump: '300M kg', life: '16h', guards: 'Rogue Drones', note: '' },
  { type: 'R081', origin: 'Pochven', dest: 'C4 Wormhole', mass: '1B kg', maxJump: '300M kg', life: '16h', guards: 'Drifters', note: '' },
  { type: 'U372', origin: 'Drone Regions', dest: 'Pochven', mass: '1B kg', maxJump: '300M kg', life: '16h', guards: 'Rogue Drones', note: '' },
  { type: 'F216', origin: 'Wormhole Space', dest: 'Pochven', mass: '1B kg', maxJump: '300M kg', life: '16h', guards: 'Drifters', note: '' },
];

const FILAMENT_TYPES = [
  { name: 'Pochven Home', dest: 'Niarja, Archee, or Kino', group: 'Entry' },
  { name: 'Pochven Border', dest: 'Senda, Ahtila, Arvasaras, Sakenta, Urhinichi, Otanuomi', group: 'Entry' },
  { name: 'Pochven Inner', dest: 'Any internal system', group: 'Entry' },
  { name: 'Cladistic (Veles)', dest: 'Random Veles system', group: 'Entry' },
  { name: 'Cladistic (Perun)', dest: 'Random Perun system', group: 'Entry' },
  { name: 'Cladistic (Svarog)', dest: 'Random Svarog system', group: 'Entry' },
  { name: 'Glorification Devana', dest: 'Random Trig minor victory system (k-space)', group: 'Exit' },
  { name: 'Proximity Extraction', dest: 'Near your original map location', group: 'Exit' },
];

const SYSTEM_SUITABILITY = [
  { system: 'Senda', score: 93, candidates: 7, security: 'All HS', krai: 'Veles' },
  { system: 'Harva', score: 88, candidates: 10, security: 'All HS', krai: 'Svarog' },
  { system: 'Nani', score: 83, candidates: 10, security: 'All HS', krai: 'Svarog' },
  { system: 'Archee', score: 74, candidates: 12, security: 'All HS', krai: 'Veles' },
  { system: 'Otela', score: 67, candidates: 13, security: 'All HS', krai: 'Perun' },
  { system: 'Urhinichi', score: 66, candidates: 14, security: 'All HS', krai: 'Svarog' },
  { system: 'Angymonne', score: 62, candidates: 15, security: 'All HS', krai: 'Veles' },
  { system: 'Krirald', score: 61, candidates: 10, security: 'HS (Hagilur choke)', krai: 'Perun' },
  { system: 'Konola', score: 60, candidates: 9, security: 'HS', krai: 'Perun' },
  { system: 'Sakenta', score: 59, candidates: 16, security: 'All HS', krai: 'Perun' },
];

const SPACE_RULES = [
  'Local chat is delayed (like wormhole space)',
  'Bubbles, bombs, and boosts all functional',
  'Cynosural fields cannot be lit',
  'Structures cannot be anchored',
  'Jump drives can jump OUT but not IN',
  'Home systems require 7.0 Triglavian standing for gate access',
  'All other systems open to all capsuleers',
  'C729 wormhole guaranteed in every system (respawns instantly if rolled)',
  'Filaments require fleet, yellow/red safety, 1000km+ from objects, 15min cooldown',
];

// ── Collapsible Section ─────────────────────────────────────────────────────

function Section({
  title,
  icon: Icon,
  defaultOpen = false,
  children,
}: {
  title: string;
  icon: React.ComponentType<{ className?: string }>;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <Card>
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3 text-left"
      >
        <div className="flex items-center gap-2">
          <Icon className="h-4 w-4 text-text-secondary" />
          <span className="text-sm font-semibold text-text">{title}</span>
        </div>
        {open ? (
          <ChevronUp className="h-4 w-4 text-text-secondary" />
        ) : (
          <ChevronDown className="h-4 w-4 text-text-secondary" />
        )}
      </button>
      {open && <div className="px-4 pb-4">{children}</div>}
    </Card>
  );
}

// ── Krai color helper ───────────────────────────────────────────────────────

const KRAI_BADGE: Record<string, string> = {
  Veles: 'bg-green-500/20 text-green-400',
  Perun: 'bg-blue-500/20 text-blue-400',
  Svarog: 'bg-amber-500/20 text-amber-400',
};

// ── Page ─────────────────────────────────────────────────────────────────────

const POCHVEN_REGION_FILTER = [POCHVEN_REGION_ID];

export default function PochvenPage() {
  const { kills } = useKillStream({ regionFilter: POCHVEN_REGION_FILTER });

  // Aggregate kills by system name
  const killCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const kill of kills) {
      const name = kill.systemName;
      if (name) {
        counts[name] = (counts[name] || 0) + 1;
      }
    }
    return counts;
  }, [kills]);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-text">Pochven Navigation</h1>
        <p className="text-text-secondary text-sm mt-1">
          Internal conduit gate network &middot; 27 systems &middot; 3 Krais.
          Click two systems to find the shortest route.
        </p>
      </div>

      <PochvenMap killCounts={killCounts} />

      {/* Pochven Kill Feed */}
      <Card className="p-4">
        <StreamingKillFeed
          regionFilter={[POCHVEN_REGION_ID]}
          title="Pochven Kill Feed"
          maxDisplay={15}
        />
      </Card>

      {/* Reference panels */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        {/* Space Rules */}
        <Section title="Pochven Space Rules" icon={ShieldAlert} defaultOpen>
          <ul className="space-y-1.5">
            {SPACE_RULES.map((rule) => (
              <li key={rule} className="flex items-start gap-2 text-xs text-text-secondary">
                <span className="mt-1 w-1 h-1 rounded-full bg-red-400 shrink-0" />
                {rule}
              </li>
            ))}
          </ul>
        </Section>

        {/* C729 Entry Suitability */}
        <Section title="C729 Entry Suitability (Top 10)" icon={Compass} defaultOpen>
          <p className="text-xs text-text-secondary mb-2">
            Ranked by ease of finding a C729 wormhole from k-space. Every Pochven system has a guaranteed C729 within 3 jumps.
          </p>
          <div className="space-y-1">
            {SYSTEM_SUITABILITY.map((s, i) => (
              <div key={s.system} className="flex items-center gap-2 text-xs">
                <span className="w-5 text-right text-text-secondary font-mono">{i + 1}.</span>
                <span className="font-medium text-text w-24">{s.system}</span>
                <Badge variant="default" className={`text-[10px] px-1.5 py-0 ${KRAI_BADGE[s.krai]}`}>
                  {s.krai}
                </Badge>
                <div className="flex-1 mx-2">
                  <div className="h-1.5 bg-card rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full bg-cyan-500"
                      style={{ width: `${s.score}%` }}
                    />
                  </div>
                </div>
                <span className="text-text-secondary w-8 text-right">{s.score}%</span>
                <span className="text-text-secondary w-16 text-right">{s.candidates} sys</span>
              </div>
            ))}
          </div>
        </Section>

        {/* Wormhole Types */}
        <Section title="Wormhole Connections" icon={Map}>
          <div className="overflow-x-auto -mx-1">
            {/* Desktop table */}
            <table className="hidden sm:table w-full text-xs">
              <thead>
                <tr className="text-left text-text-secondary border-b border-border">
                  <th className="pb-1.5 pr-2 font-medium">Type</th>
                  <th className="pb-1.5 pr-2 font-medium">From</th>
                  <th className="pb-1.5 pr-2 font-medium">To</th>
                  <th className="pb-1.5 pr-2 font-medium">Life</th>
                  <th className="pb-1.5 pr-2 font-medium">Guards</th>
                </tr>
              </thead>
              <tbody>
                {WORMHOLE_TYPES.map((wh) => (
                  <tr key={wh.type} className="border-b border-border/50">
                    <td className="py-1.5 pr-2 font-mono text-cyan-400">{wh.type}</td>
                    <td className="py-1.5 pr-2 text-text">{wh.origin}</td>
                    <td className="py-1.5 pr-2 text-text">{wh.dest}</td>
                    <td className="py-1.5 pr-2 text-text-secondary">{wh.life}</td>
                    <td className="py-1.5 pr-2 text-text-secondary">{wh.guards}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {/* Mobile cards */}
            <div className="sm:hidden space-y-2">
              {WORMHOLE_TYPES.map((wh) => (
                <div key={wh.type} className="border border-border/50 rounded-lg p-2.5">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-cyan-400 text-xs">{wh.type}</span>
                    <span className="text-[10px] text-text-secondary">{wh.life}</span>
                  </div>
                  <div className="text-xs text-text mt-1">{wh.origin} &rarr; {wh.dest}</div>
                  <div className="text-[10px] text-text-secondary mt-0.5">Guards: {wh.guards}</div>
                  {wh.note && <div className="text-[10px] text-amber-400 mt-0.5">{wh.note}</div>}
                </div>
              ))}
            </div>
          </div>
        </Section>

        {/* Filament Types */}
        <Section title="Filament Types" icon={Landmark}>
          <div className="space-y-3">
            {(['Entry', 'Exit'] as const).map((group) => (
              <div key={group}>
                <h4 className="text-xs font-medium text-text-secondary uppercase tracking-wide mb-1.5">
                  {group} Filaments
                </h4>
                <div className="space-y-1">
                  {FILAMENT_TYPES.filter((f) => f.group === group).map((f) => (
                    <div key={f.name} className="flex items-start gap-2 text-xs">
                      <span className="text-text font-medium whitespace-nowrap">{f.name}</span>
                      <span className="text-text-secondary">&rarr; {f.dest}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
            <p className="text-[10px] text-text-secondary mt-1">
              Requires fleet formation, yellow/red safety, 1000km+ from celestials. 15-minute cooldown.
            </p>
          </div>
        </Section>
      </div>

      {/* Attribution */}
      <p className="text-[10px] text-text-secondary text-center">
        Wormhole and entry data sourced from{' '}
        <a
          href="https://pochven.electusmatari.com/"
          target="_blank"
          rel="noopener noreferrer"
          className="text-cyan-500 hover:underline inline-flex items-center gap-0.5"
        >
          Electus Matari Pochven Entry Manual
          <ExternalLink className="h-2.5 w-2.5" />
        </a>
      </p>
    </div>
  );
}
