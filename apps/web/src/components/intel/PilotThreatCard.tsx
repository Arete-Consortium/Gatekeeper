'use client';

import { useState, useEffect } from 'react';
import { Card, Badge } from '@/components/ui';
import { GatekeeperAPI } from '@/lib/api';
import type { PilotThreatStats } from '@/lib/types';
import {
  Shield,
  Skull,
  Clock,
  Target,
  X,
  Loader2,
  Crosshair,
  Users,
  Swords,
  AlertTriangle,
  Pin,
} from 'lucide-react';

interface PilotThreatCardProps {
  characterId: number;
  onClose?: () => void;
  onPin?: (characterId: number, name: string) => void;
  isPinned?: boolean;
}

const THREAT_COLORS: Record<string, string> = {
  minimal: 'text-gray-400',
  low: 'text-green-400',
  moderate: 'text-yellow-400',
  high: 'text-orange-400',
  extreme: 'text-red-400',
};

const THREAT_BG: Record<string, string> = {
  minimal: 'bg-gray-500/10 border-gray-500/30',
  low: 'bg-green-500/10 border-green-500/30',
  moderate: 'bg-yellow-500/10 border-yellow-500/30',
  high: 'bg-orange-500/10 border-orange-500/30',
  extreme: 'bg-red-500/10 border-red-500/30',
};

const FLAG_LABELS: Record<string, { label: string; variant: 'danger' | 'warning' | 'info' | 'success' }> = {
  solo_hunter: { label: 'Solo Hunter', variant: 'warning' },
  capital_pilot: { label: 'Capital Pilot', variant: 'danger' },
  possible_cyno: { label: 'Possible Cyno', variant: 'danger' },
  gang_focus: { label: 'Gang Focused', variant: 'info' },
  recently_active: { label: 'Recently Active', variant: 'warning' },
};

function formatIsk(value: number): string {
  if (value >= 1e12) return `${(value / 1e12).toFixed(1)}T`;
  if (value >= 1e9) return `${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `${(value / 1e6).toFixed(1)}M`;
  if (value >= 1e3) return `${(value / 1e3).toFixed(0)}K`;
  return value.toString();
}

export function PilotThreatCard({ characterId, onClose, onPin, isPinned }: PilotThreatCardProps) {
  const [pilot, setPilot] = useState<PilotThreatStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch on mount
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    (async () => {
      try {
        const data = await GatekeeperAPI.getPilotStats(characterId);
        if (!cancelled) {
          setPilot(data);
          setLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load pilot data');
          setLoading(false);
        }
      }
    })();
    return () => { cancelled = true; };
  }, [characterId]);

  if (loading) {
    return (
      <Card className="w-80 p-4">
        <div className="flex items-center justify-center gap-2 py-8">
          <Loader2 className="h-5 w-5 animate-spin text-primary" />
          <span className="text-sm text-text-secondary">Loading pilot intel...</span>
        </div>
      </Card>
    );
  }

  if (error || !pilot) {
    return (
      <Card className="w-80 p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-red-400">Pilot not found</span>
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

  const threatColor = THREAT_COLORS[pilot.threat_level] || THREAT_COLORS.minimal;
  const threatBg = THREAT_BG[pilot.threat_level] || THREAT_BG.minimal;

  return (
    <Card className="w-80 p-0 overflow-hidden">
      {/* Header with threat level */}
      <div className={`px-4 py-3 border-b ${threatBg}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {/* EVE character portrait */}
            <img
              src={`https://images.evetech.net/characters/${pilot.character_id}/portrait?size=64`}
              alt={pilot.name}
              className="w-10 h-10 rounded-lg border border-white/10"
            />
            <div>
              <div className="font-semibold text-text text-sm">{pilot.name}</div>
              <div className="text-[11px] text-text-secondary">
                {pilot.corporation_name}
                {pilot.alliance_name && (
                  <span className="text-text-secondary/60"> [{pilot.alliance_name}]</span>
                )}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-1">
            {onPin && pilot && (
              <button
                onClick={() => onPin(pilot.character_id, pilot.name)}
                className={`p-1 transition-colors ${isPinned ? 'text-cyan-400 hover:text-cyan-300' : 'text-text-secondary hover:text-text'}`}
                title={isPinned ? 'Unpin from Kill Feed' : 'Pin to Kill Feed'}
              >
                <Pin className={`h-4 w-4 ${isPinned ? 'fill-current' : ''}`} />
              </button>
            )}
            {onClose && (
              <button onClick={onClose} className="text-text-secondary hover:text-text p-1">
                <X className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2 mt-2">
          <AlertTriangle className={`h-3.5 w-3.5 ${threatColor}`} />
          <span className={`text-xs font-bold uppercase tracking-wider ${threatColor}`}>
            {pilot.threat_level} threat
          </span>
          {pilot.active_timezone && (
            <span className="text-[10px] text-text-secondary ml-auto flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {pilot.active_timezone}
            </span>
          )}
        </div>
      </div>

      {/* Stats grid */}
      <div className="px-4 py-3 grid grid-cols-3 gap-3 border-b border-border">
        <div className="text-center">
          <div className="flex items-center justify-center gap-1 mb-0.5">
            <Skull className="h-3 w-3 text-red-400" />
            <span className="text-[10px] text-text-secondary uppercase">Kills</span>
          </div>
          <span className="text-sm font-bold text-text">{pilot.kills.toLocaleString()}</span>
        </div>
        <div className="text-center">
          <div className="flex items-center justify-center gap-1 mb-0.5">
            <Shield className="h-3 w-3 text-blue-400" />
            <span className="text-[10px] text-text-secondary uppercase">Losses</span>
          </div>
          <span className="text-sm font-bold text-text">{pilot.losses.toLocaleString()}</span>
        </div>
        <div className="text-center">
          <div className="flex items-center justify-center gap-1 mb-0.5">
            <Crosshair className="h-3 w-3 text-yellow-400" />
            <span className="text-[10px] text-text-secondary uppercase">K/D</span>
          </div>
          <span className="text-sm font-bold text-text">{pilot.kd_ratio}</span>
        </div>
      </div>

      {/* Danger & ISK */}
      <div className="px-4 py-3 grid grid-cols-2 gap-3 border-b border-border">
        <div>
          <div className="flex items-center gap-1.5 mb-1">
            <Target className="h-3 w-3 text-orange-400" />
            <span className="text-[10px] text-text-secondary uppercase">Danger</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex-1 h-1.5 bg-background rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-green-500 via-yellow-500 to-red-500 rounded-full"
                style={{ width: `${Math.min(pilot.danger_ratio, 100)}%` }}
              />
            </div>
            <span className="text-xs font-mono text-text-secondary">{pilot.danger_ratio}%</span>
          </div>
        </div>
        <div>
          <div className="flex items-center gap-1.5 mb-1">
            <Users className="h-3 w-3 text-cyan-400" />
            <span className="text-[10px] text-text-secondary uppercase">Gang</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex-1 h-1.5 bg-background rounded-full overflow-hidden">
              <div
                className="h-full bg-cyan-500 rounded-full"
                style={{ width: `${Math.min(pilot.gang_ratio, 100)}%` }}
              />
            </div>
            <span className="text-xs font-mono text-text-secondary">{pilot.gang_ratio}%</span>
          </div>
        </div>
      </div>

      {/* ISK stats */}
      <div className="px-4 py-2 flex items-center justify-between text-[11px] border-b border-border">
        <span className="text-text-secondary">
          <Swords className="h-3 w-3 inline mr-1 text-green-400" />
          ISK Destroyed: <span className="text-text font-medium">{formatIsk(pilot.isk_destroyed)}</span>
        </span>
        <span className="text-text-secondary">
          ISK Lost: <span className="text-text font-medium">{formatIsk(pilot.isk_lost)}</span>
        </span>
      </div>

      {/* Flags */}
      {pilot.flags.length > 0 && (
        <div className="px-4 py-2 flex flex-wrap gap-1.5 border-b border-border">
          {pilot.flags.map((flag) => {
            const flagInfo = FLAG_LABELS[flag] || { label: flag, variant: 'info' as const };
            return (
              <Badge key={flag} variant={flagInfo.variant} size="sm">
                {flagInfo.label}
              </Badge>
            );
          })}
        </div>
      )}

      {/* Top ships */}
      {pilot.top_ships.length > 0 && (
        <div className="px-4 py-2">
          <div className="text-[10px] text-text-secondary uppercase tracking-wider mb-1.5">
            Top Ships
          </div>
          <div className="space-y-1">
            {pilot.top_ships.map((ship) => (
              <div key={ship.id} className="flex items-center justify-between text-xs">
                <span className="text-text">{ship.name}</span>
                <span className="text-text-secondary font-mono">{ship.kills}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Security status footer */}
      <div className="px-4 py-2 bg-background text-[11px] text-text-secondary flex items-center justify-between">
        <span>
          Sec Status:{' '}
          <span className={pilot.security_status < -2 ? 'text-red-400' : pilot.security_status < 0 ? 'text-orange-400' : 'text-green-400'}>
            {pilot.security_status.toFixed(2)}
          </span>
        </span>
        <a
          href={`https://zkillboard.com/character/${pilot.character_id}/`}
          target="_blank"
          rel="noopener noreferrer"
          className="text-primary hover:text-primary/80 transition-colors"
        >
          zKillboard →
        </a>
      </div>
    </Card>
  );
}
