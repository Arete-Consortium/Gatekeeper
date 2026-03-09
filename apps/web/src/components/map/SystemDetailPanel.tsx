'use client';

import React from 'react';
import type { MapSystem, MapGate, MapKill } from './types';
import type {
  SovereigntyResponse,
  FWSystem,
  TheraConnection,
  SystemActivityResponse,
  Incursion,
} from '@/lib/types';

// Faction name lookup
const FACTION_NAMES: Record<number, string> = {
  500001: 'Caldari State',
  500002: 'Minmatar Republic',
  500003: 'Amarr Empire',
  500004: 'Gallente Federation',
  500010: 'Serpentis',
  500011: 'Angel Cartel',
  500012: "Sansha's Nation",
};

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

function formatIsk(value: number): string {
  if (value >= 1e9) return `${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `${(value / 1e6).toFixed(0)}M`;
  return `${(value / 1e3).toFixed(0)}K`;
}

interface SystemDetailPanelProps {
  system: MapSystem;
  gates: MapGate[];
  systemMap: Map<number, MapSystem>;
  sovData?: SovereigntyResponse;
  fwData?: Record<string, FWSystem>;
  theraConnections?: TheraConnection[];
  activityData?: SystemActivityResponse;
  kills?: MapKill[];
  onClose: () => void;
  onSystemClick?: (systemId: number) => void;
}

export function SystemDetailPanel({
  system,
  gates,
  systemMap,
  sovData,
  fwData,
  theraConnections,
  activityData,
  kills = [],
  onClose,
  onSystemClick,
}: SystemDetailPanelProps) {
  const sid = String(system.systemId);

  // Activity data
  const jumps = activityData?.jumps[sid] ?? null;
  const killStats = activityData?.kills[sid] ?? null;

  // Sovereignty
  const sov = sovData?.sovereignty[sid];
  const sovAllianceName = sov?.alliance_id
    ? sovData?.alliances[String(sov.alliance_id)]?.name || `Alliance ${sov.alliance_id}`
    : null;
  const sovFactionName = sov?.faction_id
    ? FACTION_NAMES[sov.faction_id] || `Faction ${sov.faction_id}`
    : null;

  // FW
  const fw = fwData?.[sid];
  const fwProgress = fw && fw.victory_points_threshold > 0
    ? Math.round((fw.victory_points / fw.victory_points_threshold) * 100)
    : 0;

  // Thera connections
  const theraHere = theraConnections?.filter(
    (c) => c.completed && (c.source_system_id === system.systemId || c.dest_system_id === system.systemId)
  ) ?? [];

  // Incursions affecting this system
  const incursion = activityData?.incursions.find(
    (inc) => inc.infested_systems.includes(system.systemId)
  );

  // Recent kills in system
  const systemKills = kills.filter((k) => k.systemId === system.systemId);

  // Connected systems
  const neighbors = gates
    .filter((g) => g.fromSystemId === system.systemId || g.toSystemId === system.systemId)
    .map((g) => {
      const neighborId = g.fromSystemId === system.systemId ? g.toSystemId : g.fromSystemId;
      return systemMap.get(neighborId);
    })
    .filter((s): s is MapSystem => s !== undefined)
    .sort((a, b) => a.name.localeCompare(b.name));

  // Security color
  const secColor = system.security >= 0.5
    ? 'text-green-400'
    : system.security > 0
      ? 'text-yellow-400'
      : 'text-red-400';

  return (
    <div className="space-y-3 text-sm">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-lg font-bold text-white">{system.name}</h3>
          <div className="flex items-center gap-2 mt-0.5">
            <span className={`font-mono text-sm ${secColor}`}>{system.security.toFixed(2)}</span>
            {system.spectralClass && (
              <span className="text-gray-500 text-xs">Class {system.spectralClass}</span>
            )}
          </div>
        </div>
        <button
          onClick={onClose}
          className="text-gray-500 hover:text-gray-300 text-lg leading-none"
          aria-label="Close system detail"
        >
          &times;
        </button>
      </div>

      {/* Activity Stats (Dotlan-style) */}
      <div className="grid grid-cols-2 gap-2">
        <StatBox
          label="Jumps"
          value={jumps !== null ? formatNumber(jumps) : '—'}
          sublabel="1 hour"
          color="text-blue-400"
        />
        <StatBox
          label="Ship Kills"
          value={killStats ? formatNumber(killStats.ship_kills) : '—'}
          sublabel="1 hour"
          color="text-red-400"
        />
        <StatBox
          label="NPC Kills"
          value={killStats ? formatNumber(killStats.npc_kills) : '—'}
          sublabel="1 hour"
          color="text-orange-400"
        />
        <StatBox
          label="Pod Kills"
          value={killStats ? formatNumber(killStats.pod_kills) : '—'}
          sublabel="1 hour"
          color="text-pink-400"
        />
      </div>

      {/* System Info */}
      <Section title="System Info">
        <InfoRow label="Region" value={system.regionId ? String(system.regionId) : '—'} />
        {system.npcStations != null && system.npcStations > 0 && (
          <InfoRow label="NPC Stations" value={String(system.npcStations)} />
        )}
        {system.hub && <InfoRow label="Classification" value="Hub System" valueColor="text-amber-400" />}
        {system.border && <InfoRow label="Classification" value="Border System" valueColor="text-cyan-400" />}
      </Section>

      {/* Sovereignty */}
      {(sovAllianceName || sovFactionName) && (
        <Section title="Sovereignty">
          {sovAllianceName && <InfoRow label="Alliance" value={sovAllianceName} valueColor="text-purple-400" />}
          {sovFactionName && <InfoRow label="Faction" value={sovFactionName} valueColor="text-cyan-400" />}
        </Section>
      )}

      {/* Faction Warfare */}
      {fw && (
        <Section title="Faction Warfare">
          <InfoRow
            label="Status"
            value={fw.contested}
            valueColor={fw.contested === 'contested' || fw.contested === 'vulnerable' ? 'text-amber-400' : 'text-green-400'}
          />
          <InfoRow label="Owner" value={FACTION_NAMES[fw.owner_faction_id] || String(fw.owner_faction_id)} />
          {fw.occupier_faction_id !== fw.owner_faction_id && (
            <InfoRow label="Occupier" value={FACTION_NAMES[fw.occupier_faction_id] || String(fw.occupier_faction_id)} valueColor="text-red-400" />
          )}
          {(fw.contested === 'contested' || fw.contested === 'vulnerable') && (
            <div className="mt-1">
              <div className="flex items-center justify-between text-xs mb-0.5">
                <span className="text-gray-400">Capture</span>
                <span className="text-amber-400">{fwProgress}%</span>
              </div>
              <div className="h-1.5 bg-gray-700 rounded-full">
                <div className="h-full bg-amber-400 rounded-full" style={{ width: `${Math.min(fwProgress, 100)}%` }} />
              </div>
            </div>
          )}
        </Section>
      )}

      {/* Incursion */}
      {incursion && (
        <Section title="Incursion Active">
          <div className="bg-red-900/30 border border-red-800/50 rounded px-2 py-1.5">
            <div className="flex items-center justify-between">
              <span className="text-red-300 text-xs font-medium">{incursion.state}</span>
              {incursion.has_boss && <span className="text-red-400 text-[10px]">BOSS</span>}
            </div>
            <div className="mt-1">
              <div className="flex items-center justify-between text-xs mb-0.5">
                <span className="text-gray-400">Influence</span>
                <span className="text-red-400">{Math.round(incursion.influence * 100)}%</span>
              </div>
              <div className="h-1 bg-gray-700 rounded-full">
                <div className="h-full bg-red-500 rounded-full" style={{ width: `${incursion.influence * 100}%` }} />
              </div>
            </div>
          </div>
        </Section>
      )}

      {/* Thera Connections */}
      {theraHere.length > 0 && (
        <Section title="Thera Connections">
          {theraHere.map((c) => (
            <div key={c.id} className="flex items-center justify-between text-xs py-0.5">
              <span className="text-cyan-300">{c.wh_type}</span>
              <span className="text-gray-400">{c.max_ship_size}</span>
              <span className="text-gray-500">{c.remaining_hours}h</span>
            </div>
          ))}
        </Section>
      )}

      {/* Recent Kills */}
      {systemKills.length > 0 && (
        <Section title={`Recent Kills (${systemKills.length})`}>
          {systemKills.slice(0, 5).map((k) => (
            <div key={k.killId} className="flex items-center justify-between text-xs py-0.5">
              <span className={k.isPod ? 'text-orange-400' : 'text-red-300'}>{k.shipType}</span>
              <span className="text-gray-400">{formatIsk(k.value)} ISK</span>
            </div>
          ))}
        </Section>
      )}

      {/* Connected Systems */}
      <Section title={`Gates (${neighbors.length})`}>
        <div className="max-h-32 overflow-y-auto space-y-0.5">
          {neighbors.map((n) => (
            <button
              key={n.systemId}
              onClick={() => onSystemClick?.(n.systemId)}
              className="w-full flex items-center justify-between text-xs py-0.5 hover:bg-gray-700/30 rounded px-1 -mx-1"
            >
              <span className="text-gray-200">{n.name}</span>
              <span className={`font-mono ${
                n.security >= 0.5 ? 'text-green-400' : n.security > 0 ? 'text-yellow-400' : 'text-red-400'
              }`}>
                {n.security.toFixed(1)}
              </span>
            </button>
          ))}
        </div>
      </Section>

      {/* External Links */}
      <div className="flex gap-2 pt-1">
        <a
          href={`https://zkillboard.com/system/${system.systemId}/`}
          target="_blank"
          rel="noopener noreferrer"
          className="flex-1 text-center text-xs py-1.5 bg-gray-800 hover:bg-gray-700 rounded text-orange-400 transition-colors"
        >
          zKillboard
        </a>
        <a
          href={`https://evemaps.dotlan.net/system/${encodeURIComponent(system.name)}`}
          target="_blank"
          rel="noopener noreferrer"
          className="flex-1 text-center text-xs py-1.5 bg-gray-800 hover:bg-gray-700 rounded text-blue-400 transition-colors"
        >
          Dotlan
        </a>
      </div>
    </div>
  );
}

// Stat box for activity numbers
function StatBox({ label, value, sublabel, color }: {
  label: string;
  value: string;
  sublabel: string;
  color: string;
}) {
  return (
    <div className="bg-gray-800/50 rounded px-2 py-1.5 text-center">
      <div className={`text-base font-bold ${color}`}>{value}</div>
      <div className="text-[10px] text-gray-400">{label}</div>
      <div className="text-[9px] text-gray-600">{sublabel}</div>
    </div>
  );
}

// Section wrapper
function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-xs font-medium text-gray-400 mb-1 uppercase tracking-wider">{title}</div>
      {children}
    </div>
  );
}

// Info row
function InfoRow({ label, value, valueColor }: {
  label: string;
  value: string;
  valueColor?: string;
}) {
  return (
    <div className="flex items-center justify-between text-xs py-0.5">
      <span className="text-gray-500">{label}</span>
      <span className={valueColor || 'text-gray-200'}>{value}</span>
    </div>
  );
}

export default SystemDetailPanel;
