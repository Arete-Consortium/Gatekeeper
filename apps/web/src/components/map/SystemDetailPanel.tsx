'use client';

import React, { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import type { MapSystem, MapGate, MapKill, SystemRisk } from './types';
import type {
  SovereigntyResponse,
  FWSystem,
  TheraConnection,
  SystemActivityResponse,
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

function getDangerLevel(score: number): { label: string; color: string; bg: string } {
  if (score >= 75) return { label: 'EXTREME', color: 'text-red-400', bg: 'bg-red-500/20' };
  if (score >= 50) return { label: 'HIGH', color: 'text-orange-400', bg: 'bg-orange-500/20' };
  if (score >= 25) return { label: 'MEDIUM', color: 'text-yellow-400', bg: 'bg-yellow-500/20' };
  return { label: 'LOW', color: 'text-green-400', bg: 'bg-green-500/20' };
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
  riskData?: SystemRisk;
  onClose: () => void;
  onSystemClick?: (systemId: number) => void;
  onSetOrigin?: (systemId: number) => void;
  onSetDestination?: (systemId: number) => void;
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
  riskData,
  onClose,
  onSystemClick,
  onSetOrigin,
  onSetDestination,
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

  // Gate camp detection: pod:kill ratio > 0.5 with meaningful sample
  const podRatio = killStats && killStats.ship_kills > 0
    ? killStats.pod_kills / killStats.ship_kills
    : 0;
  const likelyGateCamp = podRatio > 0.5 && killStats && (killStats.ship_kills + killStats.pod_kills) >= 3;

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

  // Danger level from risk score
  const danger = riskData ? getDangerLevel(riskData.riskScore) : null;

  // Has active threats?
  const hasThreats = incursion || theraHere.length > 0 || likelyGateCamp;
  const hasSov = !!(sovAllianceName || sovFactionName || fw);

  return (
    <div className="space-y-2.5 text-sm">
      {/* ═══ TIER 1: Always visible ═══ */}

      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="min-w-0">
          <h3 className="text-lg font-bold text-white truncate">{system.name}</h3>
          <div className="flex items-center gap-2 mt-0.5 flex-wrap">
            <span className={`font-mono text-sm ${secColor}`}>{system.security.toFixed(2)}</span>
            {system.spectralClass && (
              <span className="text-gray-500 text-xs">Class {system.spectralClass}</span>
            )}
            {danger && (
              <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${danger.color} ${danger.bg}`}>
                {danger.label}
              </span>
            )}
          </div>
        </div>
        <button
          onClick={onClose}
          className="text-gray-500 hover:text-gray-300 active:text-white text-lg leading-none p-2 -m-2 rounded-lg min-w-[44px] min-h-[44px] flex items-center justify-center flex-shrink-0"
          aria-label="Close system detail"
        >
          &times;
        </button>
      </div>

      {/* Risk Score Bar */}
      {riskData && (
        <div>
          <div className="flex items-center justify-between text-xs mb-1">
            <span className="text-gray-400">Risk Score</span>
            <span className={danger?.color || 'text-gray-200'}>{Math.round(riskData.riskScore)}/100</span>
          </div>
          <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${
                riskData.riskColor === 'red' ? 'bg-red-500' :
                riskData.riskColor === 'orange' ? 'bg-orange-500' :
                riskData.riskColor === 'yellow' ? 'bg-yellow-500' :
                'bg-green-500'
              }`}
              style={{ width: `${Math.min(riskData.riskScore, 100)}%` }}
            />
          </div>
        </div>
      )}

      {/* Activity Stats — 2x2 grid */}
      <div className="grid grid-cols-4 gap-1.5">
        <StatBox
          label="Jumps"
          value={jumps !== null ? formatNumber(jumps) : '—'}
          color="text-blue-400"
        />
        <StatBox
          label="Ships"
          value={killStats ? formatNumber(killStats.ship_kills) : '—'}
          color="text-red-400"
        />
        <StatBox
          label="NPCs"
          value={killStats ? formatNumber(killStats.npc_kills) : '—'}
          color="text-orange-400"
        />
        <StatBox
          label="Pods"
          value={killStats ? formatNumber(killStats.pod_kills) : '—'}
          color="text-pink-400"
        />
      </div>

      {/* Gate Camp Warning */}
      {likelyGateCamp && (
        <div className="bg-red-900/30 border border-red-800/50 rounded-lg px-2.5 py-1.5 flex items-center gap-2">
          <span className="text-red-400 text-xs font-bold">GATE CAMP</span>
          <span className="text-gray-400 text-xs">High pod:kill ratio detected</span>
        </div>
      )}

      {/* Route Actions */}
      {(onSetOrigin || onSetDestination) && (
        <div className="flex gap-2">
          {onSetOrigin && (
            <button
              onClick={() => onSetOrigin(system.systemId)}
              className="flex-1 text-sm py-2.5 bg-green-900/40 hover:bg-green-800/50 active:bg-green-700/50 border border-green-700/50 rounded-lg text-green-400 transition-colors font-medium"
            >
              Origin
            </button>
          )}
          {onSetDestination && (
            <button
              onClick={() => onSetDestination(system.systemId)}
              className="flex-1 text-sm py-2.5 bg-blue-900/40 hover:bg-blue-800/50 active:bg-blue-700/50 border border-blue-700/50 rounded-lg text-blue-400 transition-colors font-medium"
            >
              Destination
            </button>
          )}
        </div>
      )}

      {/* ═══ TIER 2: Auto-expanded when relevant ═══ */}

      {/* Incursion Alert */}
      {incursion && (
        <Accordion title="Incursion Active" defaultOpen={true} variant="danger">
          <div className="flex items-center justify-between">
            <span className="text-red-300 text-xs font-medium">{incursion.state}</span>
            {incursion.has_boss && <span className="text-red-400 text-[10px] font-bold">BOSS</span>}
          </div>
          <div className="mt-1.5">
            <div className="flex items-center justify-between text-xs mb-0.5">
              <span className="text-gray-400">Influence</span>
              <span className="text-red-400">{Math.round(incursion.influence * 100)}%</span>
            </div>
            <div className="h-1 bg-gray-700 rounded-full">
              <div className="h-full bg-red-500 rounded-full" style={{ width: `${incursion.influence * 100}%` }} />
            </div>
          </div>
        </Accordion>
      )}

      {/* Thera Connections */}
      {theraHere.length > 0 && (
        <Accordion title={`Thera (${theraHere.length})`} defaultOpen={true} variant="info">
          {theraHere.map((c) => (
            <div key={c.id} className="flex items-center justify-between text-xs py-0.5">
              <span className="text-cyan-300">{c.wh_type}</span>
              <span className="text-gray-400">{c.max_ship_size}</span>
              <span className="text-gray-500">{c.remaining_hours}h left</span>
            </div>
          ))}
        </Accordion>
      )}

      {/* Sovereignty / FW — auto-expand if contested */}
      {hasSov && (
        <Accordion
          title={fw ? 'Faction Warfare' : 'Sovereignty'}
          defaultOpen={!!(fw && (fw.contested === 'contested' || fw.contested === 'vulnerable'))}
        >
          {sovAllianceName && <InfoRow label="Alliance" value={sovAllianceName} valueColor="text-purple-400" />}
          {sovFactionName && <InfoRow label="Faction" value={sovFactionName} valueColor="text-cyan-400" />}
          {fw && (
            <>
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
            </>
          )}
        </Accordion>
      )}

      {/* ═══ TIER 3: Collapsed by default ═══ */}

      {/* System Info */}
      <Accordion title="System Info" defaultOpen={false}>
        <InfoRow label="Region" value={system.regionName || String(system.regionId)} />
        {system.constellationName && (
          <InfoRow label="Constellation" value={system.constellationName} />
        )}
        {system.npcStations != null && system.npcStations > 0 && (
          <InfoRow label="NPC Stations" value={String(system.npcStations)} />
        )}
        {system.hub && <InfoRow label="Classification" value="Hub System" valueColor="text-amber-400" />}
        {system.border && <InfoRow label="Classification" value="Border System" valueColor="text-cyan-400" />}
        {riskData && riskData.recentKills > 0 && (
          <InfoRow label="Kills (24h)" value={String(riskData.recentKills)} valueColor="text-red-400" />
        )}
        {riskData && riskData.recentPods > 0 && (
          <InfoRow label="Pods (24h)" value={String(riskData.recentPods)} valueColor="text-pink-400" />
        )}
      </Accordion>

      {/* Recent Kills */}
      {systemKills.length > 0 && (
        <Accordion title={`Recent Kills (${systemKills.length})`} defaultOpen={false}>
          {systemKills.slice(0, 8).map((k) => (
            <div key={k.killId} className="flex items-center justify-between text-xs py-1">
              <span className={k.isPod ? 'text-orange-400' : 'text-red-300'}>{k.shipType}</span>
              <span className="text-gray-400">{formatIsk(k.value)}</span>
            </div>
          ))}
        </Accordion>
      )}

      {/* Connected Systems */}
      <Accordion title={`Gates (${neighbors.length})`} defaultOpen={false}>
        <div className="max-h-40 overflow-y-auto -mx-1">
          {neighbors.map((n) => (
            <button
              key={n.systemId}
              onClick={() => onSystemClick?.(n.systemId)}
              className="w-full flex items-center justify-between text-sm py-2 hover:bg-gray-700/30 active:bg-gray-600/40 rounded-lg px-2"
            >
              <span className="text-gray-200">{n.name}</span>
              <span className={`font-mono text-xs ${
                n.security >= 0.5 ? 'text-green-400' : n.security > 0 ? 'text-yellow-400' : 'text-red-400'
              }`}>
                {n.security.toFixed(1)}
              </span>
            </button>
          ))}
        </div>
      </Accordion>

      {/* zKillboard */}
      <a
        href={`https://zkillboard.com/system/${system.systemId}/`}
        target="_blank"
        rel="noopener noreferrer"
        className="block text-center text-xs py-2 bg-gray-800/50 hover:bg-gray-700/50 active:bg-gray-600/50 rounded-lg text-orange-400/70 hover:text-orange-400 transition-colors"
      >
        zKillboard
      </a>
    </div>
  );
}

// ─── Accordion ───────────────────────────────────────────────────────────────

function Accordion({
  title,
  defaultOpen = false,
  variant,
  children,
}: {
  title: string;
  defaultOpen?: boolean;
  variant?: 'danger' | 'info';
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);

  const borderColor = variant === 'danger'
    ? 'border-red-800/40'
    : variant === 'info'
      ? 'border-cyan-800/40'
      : 'border-gray-700/50';

  const titleColor = variant === 'danger'
    ? 'text-red-400'
    : variant === 'info'
      ? 'text-cyan-400'
      : 'text-gray-400';

  return (
    <div className={`border rounded-lg overflow-hidden ${borderColor}`}>
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-2.5 py-2 hover:bg-gray-800/30 active:bg-gray-700/30 transition-colors"
      >
        <span className={`text-xs font-medium uppercase tracking-wider ${titleColor}`}>{title}</span>
        {open ? (
          <ChevronDown className="h-3 w-3 text-gray-500 flex-shrink-0" />
        ) : (
          <ChevronRight className="h-3 w-3 text-gray-500 flex-shrink-0" />
        )}
      </button>
      {open && (
        <div className="px-2.5 pb-2 border-t border-gray-800/50">
          <div className="pt-1.5">{children}</div>
        </div>
      )}
    </div>
  );
}

// ─── Stat Box ────────────────────────────────────────────────────────────────

function StatBox({ label, value, color }: {
  label: string;
  value: string;
  color: string;
}) {
  return (
    <div className="bg-gray-800/50 rounded px-1.5 py-1.5 text-center">
      <div className={`text-sm font-bold leading-tight ${color}`}>{value}</div>
      <div className="text-[9px] text-gray-500 uppercase">{label}</div>
    </div>
  );
}

// ─── Info Row ────────────────────────────────────────────────────────────────

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
