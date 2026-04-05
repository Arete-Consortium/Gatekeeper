'use client';

import { useState } from 'react';
import dynamic from 'next/dynamic';
import { useRouter } from 'next/navigation';
import { Card, Badge, Button } from '@/components/ui';
import { GatekeeperAPI } from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';
import { ProGate } from '@/components/ProGate';
import {
  Swords,
  ShieldAlert,
  ChevronDown,
  ChevronUp,
  Coins,
  ExternalLink,
  MapPin,
  Navigation,
  Store,
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

// LP Store stations by faction militia corp
const LP_STORE_LOCATIONS: Record<string, { station: string; system: string; systemId: number; region: string }[]> = {
  Caldari: [
    { station: 'Ichoriya - State Protectorate Logistic Support', system: 'Ichoriya', systemId: 30045344, region: 'Black Rise' },
    { station: 'Enaluri - State Protectorate Logistic Support', system: 'Enaluri', systemId: 30045329, region: 'Black Rise' },
    { station: 'Aivonen - State Protectorate Logistic Support', system: 'Aivonen', systemId: 30045353, region: 'Black Rise' },
    { station: 'Hasmijaala - State Protectorate Logistic Support', system: 'Hasmijaala', systemId: 30045316, region: 'Black Rise' },
  ],
  Gallente: [
    { station: 'Villore - Federal Defence Union Logistic Support', system: 'Villore', systemId: 30003838, region: 'Essence' },
    { station: 'Intaki - Federal Defence Union Logistic Support', system: 'Intaki', systemId: 30003788, region: 'Placid' },
    { station: 'Heydieles - Federal Defence Union Logistic Support', system: 'Heydieles', systemId: 30003836, region: 'Essence' },
    { station: 'Old Man Star - Federal Defence Union Logistic Support', system: 'Old Man Star', systemId: 30003837, region: 'Essence' },
  ],
  Amarr: [
    { station: 'Sarum Prime - 24th Imperial Crusade Logistic Support', system: 'Sarum Prime', systemId: 30003504, region: 'Domain' },
    { station: 'Arzad - 24th Imperial Crusade Logistic Support', system: 'Arzad', systemId: 30003067, region: 'Devoid' },
    { station: 'Huola - 24th Imperial Crusade Logistic Support', system: 'Huola', systemId: 30003068, region: 'Devoid' },
    { station: 'Kamela - 24th Imperial Crusade Logistic Support', system: 'Kamela', systemId: 30003069, region: 'Devoid' },
  ],
  Minmatar: [
    { station: 'Amo - Tribal Liberation Force Logistic Support', system: 'Amo', systemId: 30002543, region: 'Heimatar' },
    { station: 'Auga - Tribal Liberation Force Logistic Support', system: 'Auga', systemId: 30002539, region: 'Heimatar' },
    { station: 'Kourmonen - Tribal Liberation Force Logistic Support', system: 'Kourmonen', systemId: 30003070, region: 'Devoid' },
    { station: 'Dal - Tribal Liberation Force Logistic Support', system: 'Dal', systemId: 30002537, region: 'Heimatar' },
  ],
};

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
  const router = useRouter();
  const { user, isPro } = useAuth();
  const [activeFaction, setActiveFaction] = useState<string>('Caldari');
  const [settingDestination, setSettingDestination] = useState<string | null>(null);

  const handleShowOnMap = (systemId: number) => {
    router.push(`/map?system=${systemId}`);
  };

  const handleSetDestination = async (systemName: string) => {
    if (!user) return;
    setSettingDestination(systemName);
    try {
      await GatekeeperAPI.setWaypoints([systemName], true);
    } catch {
      // Non-critical — ESI waypoint may fail if not in-game
    } finally {
      setSettingDestination(null);
    }
  };

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

      <ProGate feature="Faction Warfare Map">
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

        {/* LP Store Locations */}
        <Section title="LP Store Locations" icon={Store} defaultOpen>
          {/* Faction tabs */}
          <div className="flex gap-1 mb-3">
            {Object.keys(LP_STORE_LOCATIONS).map((faction) => (
              <button
                key={faction}
                onClick={() => setActiveFaction(faction)}
                className={`text-[11px] font-medium px-2.5 py-1 rounded-md transition-colors ${
                  activeFaction === faction
                    ? `${FACTION_BADGE[faction]} border border-current/20`
                    : 'text-text-secondary hover:text-text hover:bg-card-hover'
                }`}
              >
                {faction}
              </button>
            ))}
          </div>

          {/* Stations for active faction */}
          <div className="space-y-2">
            {LP_STORE_LOCATIONS[activeFaction]?.map((loc) => (
              <div
                key={loc.station}
                className="flex items-center gap-2 text-xs border border-border/50 rounded-lg p-2"
              >
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-text truncate">{loc.system}</div>
                  <div className="text-[10px] text-text-secondary truncate">{loc.station}</div>
                  <div className="text-[10px] text-text-secondary">{loc.region}</div>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <button
                    onClick={() => handleShowOnMap(loc.systemId)}
                    className="p-1.5 rounded hover:bg-card-hover text-text-secondary hover:text-cyan-400 transition-colors"
                    title="Show on map"
                  >
                    <MapPin className="h-3.5 w-3.5" />
                  </button>
                  {user && (
                    <button
                      onClick={() => handleSetDestination(loc.system)}
                      disabled={settingDestination === loc.system}
                      className="p-1.5 rounded hover:bg-card-hover text-text-secondary hover:text-cyan-400 transition-colors disabled:opacity-50"
                      title="Set destination in-game"
                    >
                      <Navigation className={`h-3.5 w-3.5 ${settingDestination === loc.system ? 'animate-pulse' : ''}`} />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
          <p className="text-[10px] text-text-secondary mt-2">
            Click <MapPin className="inline h-3 w-3" /> to view on map{user ? ' or ' : ''}
            {user && <><Navigation className="inline h-3 w-3" /> to set in-game destination</>}
          </p>
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
      </ProGate>
    </div>
  );
}
