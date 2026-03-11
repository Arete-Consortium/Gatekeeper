'use client';

import { useState } from 'react';
import dynamic from 'next/dynamic';
import { Card, Badge } from '@/components/ui';
import {
  Swords,
  ShieldAlert,
  Trophy,
  ChevronDown,
  ChevronUp,
  Coins,
  ExternalLink,
} from 'lucide-react';

// SSR-safe dynamic import for canvas component
const FWMap = dynamic(() => import('@/components/fw/FWMap').then((m) => ({ default: m.FWMap })), {
  ssr: false,
  loading: () => (
    <div className="w-full h-64 bg-card rounded-lg border border-border flex items-center justify-center">
      <span className="text-text-secondary text-sm">Loading FW Map...</span>
    </div>
  ),
});

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

// ── FW Reference Data ───────────────────────────────────────────────────────

const FW_RULES = [
  'Faction warfare is lowsec PvP — gate guns fire on aggressors',
  'Enlist via militia or FW-enabled corporation',
  'Capture systems by running complexes (plexes) and accumulating victory points',
  'System contested status: Stable → Contested → Vulnerable → Captured',
  'Capturing systems advances your faction\'s warzone tier',
  'Higher tier = better LP payouts from plexes and missions',
  'Pods can be freely attacked between opposing militia members',
  'Warp core stabilizers are banned inside FW plexes',
  'NPC navy will engage enemy militia in their sovereign space',
  'Docking rights are lost in enemy-controlled stations (use citadels)',
];

const TIER_REWARDS = [
  { tier: 1, lpMultiplier: '0.5x', description: 'Losing badly — minimal LP from plexes and missions' },
  { tier: 2, lpMultiplier: '1.0x', description: 'Standard payout — holding some ground' },
  { tier: 3, lpMultiplier: '1.5x', description: 'Advancing — good LP for effort' },
  { tier: 4, lpMultiplier: '2.25x', description: 'Dominant — excellent LP multiplier' },
  { tier: 5, lpMultiplier: '3.0x', description: 'Victory — maximum LP multiplier' },
];

const PLEX_TYPES = [
  { name: 'Novice', shipClass: 'T1/Navy Frigates', timer: '10 min', lpReward: '~10K LP' },
  { name: 'Small', shipClass: 'Frigates, Destroyers', timer: '15 min', lpReward: '~17.5K LP' },
  { name: 'Medium', shipClass: 'Up to Cruisers', timer: '20 min', lpReward: '~25K LP' },
  { name: 'Large', shipClass: 'Up to Battleships', timer: '20 min', lpReward: '~30K LP' },
  { name: 'Open', shipClass: 'All subcapitals', timer: '20 min', lpReward: '~40K LP' },
];

const FACTION_BADGE: Record<string, string> = {
  Caldari: 'bg-yellow-500/20 text-yellow-400',
  Gallente: 'bg-green-500/20 text-green-400',
  Amarr: 'bg-red-500/20 text-red-400',
  Minmatar: 'bg-blue-500/20 text-blue-400',
};

const LP_ITEMS = [
  { faction: 'Caldari', items: 'Navy Hookbill, Caldari Navy Ballistic Control, Caldari Navy Invulnerability Field' },
  { faction: 'Gallente', items: 'Navy Comet, Federation Navy Magnetic Field Stabilizer, Federation Navy Stasis Webifier' },
  { faction: 'Amarr', items: 'Navy Slicer, Imperial Navy Multifrequency, Imperial Navy Energized Adaptive Nano Membrane' },
  { faction: 'Minmatar', items: 'Fleet Firetail, Republic Fleet Gyrostabilizer, Republic Fleet Large Shield Extender' },
];

// ── Page ────────────────────────────────────────────────────────────────────

export default function FWPage() {
  return (
    <div className="space-y-4">
      <div>
        <div className="flex items-center gap-2">
          <Swords className="h-6 w-6 text-primary" />
          <h1 className="text-2xl font-bold text-text">Faction Warfare Map</h1>
        </div>
        <p className="text-text-secondary text-sm mt-1">
          Live occupancy and contested status across all faction warfare zones.
          Systems sized by victory point progress. Click a system for details.
        </p>
      </div>

      <FWMap />

      {/* Reference panels — Pochven style */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        {/* FW Rules */}
        <Section title="Faction Warfare Rules" icon={ShieldAlert} defaultOpen>
          <ul className="space-y-1.5">
            {FW_RULES.map((rule) => (
              <li key={rule} className="flex items-start gap-2 text-xs text-text-secondary">
                <span className="mt-1 w-1 h-1 rounded-full bg-primary shrink-0" />
                {rule}
              </li>
            ))}
          </ul>
        </Section>

        {/* Plex Types */}
        <Section title="Complex (Plex) Types" icon={Swords} defaultOpen>
          <div className="overflow-x-auto -mx-1">
            <table className="hidden sm:table w-full text-xs">
              <thead>
                <tr className="text-left text-text-secondary border-b border-border">
                  <th className="pb-1.5 pr-2 font-medium">Type</th>
                  <th className="pb-1.5 pr-2 font-medium">Ship Restriction</th>
                  <th className="pb-1.5 pr-2 font-medium">Timer</th>
                  <th className="pb-1.5 pr-2 font-medium">LP (T1)</th>
                </tr>
              </thead>
              <tbody>
                {PLEX_TYPES.map((p) => (
                  <tr key={p.name} className="border-b border-border/50">
                    <td className="py-1.5 pr-2 font-medium text-text">{p.name}</td>
                    <td className="py-1.5 pr-2 text-text-secondary">{p.shipClass}</td>
                    <td className="py-1.5 pr-2 text-text-secondary">{p.timer}</td>
                    <td className="py-1.5 pr-2 text-cyan-400 font-mono">{p.lpReward}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {/* Mobile cards */}
            <div className="sm:hidden space-y-2">
              {PLEX_TYPES.map((p) => (
                <div key={p.name} className="border border-border/50 rounded-lg p-2.5">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-text text-xs">{p.name}</span>
                    <span className="text-[10px] text-cyan-400 font-mono">{p.lpReward}</span>
                  </div>
                  <div className="text-xs text-text-secondary mt-1">{p.shipClass}</div>
                  <div className="text-[10px] text-text-secondary mt-0.5">Timer: {p.timer}</div>
                </div>
              ))}
            </div>
          </div>
        </Section>

        {/* Warzone Tier Rewards */}
        <Section title="Warzone Tier Rewards" icon={Trophy}>
          <p className="text-xs text-text-secondary mb-2">
            LP multiplier scales with your faction&apos;s warzone control tier.
          </p>
          <div className="space-y-1">
            {TIER_REWARDS.map((t) => (
              <div key={t.tier} className="flex items-center gap-2 text-xs">
                <span className="w-6 text-right font-mono font-bold text-text">T{t.tier}</span>
                <div className="flex-1 mx-2">
                  <div className="h-1.5 bg-card rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full bg-cyan-500"
                      style={{ width: `${(t.tier / 5) * 100}%` }}
                    />
                  </div>
                </div>
                <span className="w-10 text-right font-mono text-cyan-400">{t.lpMultiplier}</span>
                <span className="text-text-secondary hidden sm:inline">{t.description}</span>
              </div>
            ))}
          </div>
        </Section>

        {/* LP Store Highlights */}
        <Section title="LP Store Highlights" icon={Coins}>
          <p className="text-xs text-text-secondary mb-2">
            Popular items from each faction&apos;s LP store.
          </p>
          <div className="space-y-2">
            {LP_ITEMS.map((f) => (
              <div key={f.faction}>
                <Badge variant="default" className={`text-[10px] px-1.5 py-0 ${FACTION_BADGE[f.faction]}`}>
                  {f.faction}
                </Badge>
                <p className="text-xs text-text-secondary mt-1">{f.items}</p>
              </div>
            ))}
          </div>
        </Section>
      </div>

      {/* Attribution */}
      <p className="text-[10px] text-text-secondary text-center">
        Faction warfare data from{' '}
        <a
          href="https://esi.evetech.net/ui/#/Faction%20Warfare"
          target="_blank"
          rel="noopener noreferrer"
          className="text-cyan-500 hover:underline inline-flex items-center gap-0.5"
        >
          EVE ESI
          <ExternalLink className="h-2.5 w-2.5" />
        </a>
      </p>
    </div>
  );
}
