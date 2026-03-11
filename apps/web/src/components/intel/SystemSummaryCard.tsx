'use client';

import { useState, useEffect } from 'react';
import { Card, Badge } from '@/components/ui';
import { SecurityBadge } from '@/components/system';
import { GatekeeperAPI } from '@/lib/api';
import type {
  RiskReport,
  SovereigntyResponse,
  SystemActivityResponse,
  SystemActivityKills,
  MapConfigSystem,
} from '@/lib/types';
import {
  X,
  Loader2,
  Shield,
  Skull,
  Navigation,
  AlertTriangle,
  Activity,
  MapPin,
  ExternalLink,
} from 'lucide-react';

interface SystemSummaryCardProps {
  systemName: string;
  systemId?: number;
  onClose?: () => void;
  onAvoidSystem?: (systemName: string) => void;
}

const FACTION_NAMES: Record<number, string> = {
  500001: 'Caldari State',
  500002: 'Minmatar Republic',
  500003: 'Amarr Empire',
  500004: 'Gallente Federation',
  500010: 'Serpentis',
  500011: 'Angel Cartel',
  500012: "Sansha's Nation",
};

function getDangerLevel(score: number): { label: string; color: string; bg: string } {
  if (score >= 75) return { label: 'EXTREME', color: 'text-red-400', bg: 'bg-red-500/10 border-red-500/30' };
  if (score >= 50) return { label: 'HIGH', color: 'text-orange-400', bg: 'bg-orange-500/10 border-orange-500/30' };
  if (score >= 25) return { label: 'MEDIUM', color: 'text-yellow-400', bg: 'bg-yellow-500/10 border-yellow-500/30' };
  return { label: 'LOW', color: 'text-green-400', bg: 'bg-green-500/10 border-green-500/30' };
}

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

interface SystemData {
  risk: RiskReport | null;
  sov: SovereigntyResponse | null;
  activity: SystemActivityResponse | null;
  config: MapConfigSystem | null;
}

export function SystemSummaryCard({
  systemName,
  systemId,
  onClose,
  onAvoidSystem,
}: SystemSummaryCardProps) {
  const [data, setData] = useState<SystemData>({
    risk: null,
    sov: null,
    activity: null,
    config: null,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    (async () => {
      try {
        // Fetch risk data (includes zkill stats), sov, activity, and map config in parallel
        const [riskResult, sovResult, activityResult, configResult] = await Promise.allSettled([
          GatekeeperAPI.getSystemRisk(systemName),
          GatekeeperAPI.getSovereignty(),
          GatekeeperAPI.getSystemActivity(),
          GatekeeperAPI.getMapConfig(),
        ]);

        if (cancelled) return;

        const risk = riskResult.status === 'fulfilled' ? riskResult.value : null;
        const sov = sovResult.status === 'fulfilled' ? sovResult.value : null;
        const activity = activityResult.status === 'fulfilled' ? activityResult.value : null;

        let config: MapConfigSystem | null = null;
        if (configResult.status === 'fulfilled') {
          config = configResult.value.systems[systemName] || null;
        }

        setData({ risk, sov, activity, config });
        setLoading(false);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load system data');
          setLoading(false);
        }
      }
    })();

    return () => { cancelled = true; };
  }, [systemName]);

  if (loading) {
    return (
      <Card className="w-80 p-4">
        <div className="flex items-center justify-center gap-2 py-8">
          <Loader2 className="h-5 w-5 animate-spin text-primary" />
          <span className="text-sm text-text-secondary">Loading system intel...</span>
        </div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="w-80 p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-red-400">System not found</span>
          {onClose && (
            <button onClick={onClose} className="text-text-secondary hover:text-text">
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
        <p className="text-xs text-text-secondary">{error}</p>
      </Card>
    );
  }

  const { risk, sov, activity, config } = data;
  const sid = String(systemId || risk?.system_id || config?.id || '');
  const security = risk?.security ?? config?.security ?? 0;
  const regionName = config?.region_name;
  const constellationName = config?.constellation_name;

  // Sovereignty
  const sovEntry = sov?.sovereignty[sid];
  const sovAllianceName = sovEntry?.alliance_id
    ? sov?.alliances[String(sovEntry.alliance_id)]?.name || `Alliance ${sovEntry.alliance_id}`
    : null;
  const sovFactionName = sovEntry?.faction_id
    ? FACTION_NAMES[sovEntry.faction_id] || `Faction ${sovEntry.faction_id}`
    : null;

  // Activity
  const jumps = activity?.jumps[sid] ?? null;
  const killStats: SystemActivityKills | null = activity?.kills[sid] ?? null;

  // Gate camp detection
  const podRatio = killStats && killStats.ship_kills > 0
    ? killStats.pod_kills / killStats.ship_kills
    : 0;
  const likelyGateCamp = podRatio > 0.5 && killStats && (killStats.ship_kills + killStats.pod_kills) >= 3;

  // Incursion
  const realSystemId = risk?.system_id || config?.id;
  const incursion = realSystemId
    ? activity?.incursions.find((inc) => inc.infested_systems.includes(realSystemId))
    : null;

  // Danger level
  const danger = risk ? getDangerLevel(risk.score) : null;

  return (
    <Card className="w-80 p-0 overflow-hidden">
      {/* Header */}
      <div className={`px-4 py-3 border-b ${danger?.bg || 'bg-card border-border'}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MapPin className="h-4 w-4 text-text-secondary" />
            <span className="font-semibold text-text">{systemName}</span>
            <SecurityBadge security={security} size="sm" />
          </div>
          {onClose && (
            <button onClick={onClose} className="text-text-secondary hover:text-text p-1">
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
        <div className="flex items-center gap-2 mt-1.5">
          {regionName && (
            <span className="text-[11px] text-text-secondary">{regionName}</span>
          )}
          {constellationName && (
            <span className="text-[11px] text-text-secondary/60">/ {constellationName}</span>
          )}
          {danger && (
            <span className={`text-[10px] font-bold uppercase tracking-wider ml-auto ${danger.color}`}>
              {danger.label}
            </span>
          )}
        </div>
      </div>

      {/* Risk Score Bar */}
      {risk && (
        <div className="px-4 py-2.5 border-b border-border">
          <div className="flex items-center justify-between text-xs mb-1">
            <span className="text-text-secondary">Risk Score</span>
            <span className={danger?.color || 'text-text'}>{Math.round(risk.score)}/100</span>
          </div>
          <div className="h-1.5 bg-background rounded-full overflow-hidden">
            <div
              className="h-full rounded-full bg-gradient-to-r from-green-500 via-yellow-500 to-red-500"
              style={{ width: `${Math.min(risk.score, 100)}%` }}
            />
          </div>
          {risk.pirate_suppressed && (
            <div className="flex items-center gap-1.5 mt-1.5">
              <AlertTriangle className="h-3 w-3 text-red-400" />
              <span className="text-[10px] font-medium text-red-400">PIRATE SUPPRESSED — Nullsec rules</span>
            </div>
          )}
        </div>
      )}

      {/* Activity Stats */}
      <div className="px-4 py-2.5 grid grid-cols-4 gap-2 border-b border-border">
        <div className="text-center">
          <div className="text-xs font-bold text-blue-400">{jumps !== null ? formatNumber(jumps) : '—'}</div>
          <div className="text-[9px] text-text-secondary uppercase">Jumps</div>
        </div>
        <div className="text-center">
          <div className="text-xs font-bold text-red-400">
            {killStats ? formatNumber(killStats.ship_kills) : '—'}
          </div>
          <div className="text-[9px] text-text-secondary uppercase">Ships</div>
        </div>
        <div className="text-center">
          <div className="text-xs font-bold text-orange-400">
            {killStats ? formatNumber(killStats.npc_kills) : '—'}
          </div>
          <div className="text-[9px] text-text-secondary uppercase">NPCs</div>
        </div>
        <div className="text-center">
          <div className="text-xs font-bold text-pink-400">
            {killStats ? formatNumber(killStats.pod_kills) : '—'}
          </div>
          <div className="text-[9px] text-text-secondary uppercase">Pods</div>
        </div>
      </div>

      {/* Warnings */}
      {(likelyGateCamp || incursion) && (
        <div className="px-4 py-2 border-b border-border space-y-1.5">
          {likelyGateCamp && (
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-3.5 w-3.5 text-red-400" />
              <span className="text-xs font-medium text-red-400">GATE CAMP LIKELY</span>
              <span className="text-[10px] text-text-secondary">High pod:kill ratio</span>
            </div>
          )}
          {incursion && (
            <div className="flex items-center gap-2">
              <Activity className="h-3.5 w-3.5 text-orange-400" />
              <span className="text-xs font-medium text-orange-400">INCURSION</span>
              <span className="text-[10px] text-text-secondary">{incursion.state}</span>
            </div>
          )}
        </div>
      )}

      {/* Sovereignty */}
      {(sovAllianceName || sovFactionName) && (
        <div className="px-4 py-2 border-b border-border">
          <div className="text-[10px] text-text-secondary uppercase tracking-wider mb-1">Sovereignty</div>
          {sovAllianceName && (
            <div className="flex items-center justify-between text-xs">
              <span className="text-text-secondary">Alliance</span>
              <span className="text-purple-400">{sovAllianceName}</span>
            </div>
          )}
          {sovFactionName && (
            <div className="flex items-center justify-between text-xs">
              <span className="text-text-secondary">Faction</span>
              <span className="text-cyan-400">{sovFactionName}</span>
            </div>
          )}
        </div>
      )}

      {/* zKill Stats from risk */}
      {risk?.zkill_stats && (risk.zkill_stats.recent_kills > 0 || risk.zkill_stats.recent_pods > 0) && (
        <div className="px-4 py-2 border-b border-border">
          <div className="text-[10px] text-text-secondary uppercase tracking-wider mb-1">zKill (24h)</div>
          <div className="flex items-center gap-4 text-xs">
            <span className="flex items-center gap-1">
              <Skull className="h-3 w-3 text-red-400" />
              <span className="text-text">{risk.zkill_stats.recent_kills} kills</span>
            </span>
            {risk.zkill_stats.recent_pods > 0 && (
              <span className="flex items-center gap-1">
                <Shield className="h-3 w-3 text-pink-400" />
                <span className="text-text">{risk.zkill_stats.recent_pods} pods</span>
              </span>
            )}
          </div>
        </div>
      )}

      {/* Classification tags */}
      {config && (config.hub || config.border || config.corridor || config.fringe) && (
        <div className="px-4 py-2 border-b border-border flex flex-wrap gap-1.5">
          {config.hub && <Badge variant="warning" size="sm">Hub</Badge>}
          {config.border && <Badge variant="info" size="sm">Border</Badge>}
          {config.corridor && <Badge variant="info" size="sm">Corridor</Badge>}
          {config.fringe && <Badge variant="info" size="sm">Fringe</Badge>}
          {config.npc_stations > 0 && (
            <Badge variant="success" size="sm">{config.npc_stations} NPC Station{config.npc_stations > 1 ? 's' : ''}</Badge>
          )}
        </div>
      )}

      {/* Actions footer */}
      <div className="px-4 py-2 bg-background flex items-center justify-between">
        {onAvoidSystem && (
          <button
            onClick={() => onAvoidSystem(systemName)}
            className="flex items-center gap-1.5 text-[11px] text-red-400 hover:text-red-300 transition-colors"
          >
            <Navigation className="h-3 w-3" />
            Avoid System
          </button>
        )}
        <a
          href={`https://zkillboard.com/system/${realSystemId || ''}/`}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 text-[11px] text-primary hover:text-primary/80 transition-colors ml-auto"
        >
          zKillboard <ExternalLink className="h-3 w-3" />
        </a>
      </div>
    </Card>
  );
}
