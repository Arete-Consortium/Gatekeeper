'use client';

import { useState, useEffect } from 'react';
import { GatekeeperAPI } from '@/lib/api';
import type { PilotDeepDiveStats } from '@/lib/types';
import { X, Loader2, Shield, Users, Clock, Building, Crosshair, TrendingUp, Skull } from 'lucide-react';

interface PilotDeepDiveProps {
  characterId: number;
  onClose: () => void;
}

function formatIsk(value: number): string {
  if (value >= 1e12) return `${(value / 1e12).toFixed(1)}T`;
  if (value >= 1e9) return `${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `${(value / 1e6).toFixed(1)}M`;
  if (value >= 1e3) return `${(value / 1e3).toFixed(0)}K`;
  return value.toFixed(0);
}

function formatDate(dateStr: string): string {
  if (!dateStr) return '';
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
  } catch {
    return dateStr;
  }
}

function timeSince(dateStr: string): string {
  if (!dateStr) return '';
  try {
    const now = new Date();
    const d = new Date(dateStr);
    const diffMs = now.getTime() - d.getTime();
    const days = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    if (days < 30) return `${days}d`;
    if (days < 365) return `${Math.floor(days / 30)}mo`;
    return `${(days / 365).toFixed(1)}y`;
  } catch {
    return '';
  }
}

const THREAT_COLORS: Record<string, string> = {
  extreme: '#ff453a',
  high: '#ff9f0a',
  moderate: '#ffd60a',
  low: '#32d74b',
  minimal: '#636366',
};

export function PilotDeepDive({ characterId, onClose }: PilotDeepDiveProps) {
  const [data, setData] = useState<PilotDeepDiveStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    GatekeeperAPI.getPilotDeepDive(characterId)
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [characterId]);

  if (loading) {
    return (
      <div className="bg-gray-900/95 border border-gray-700 rounded-lg p-8 text-center">
        <Loader2 className="h-6 w-6 animate-spin text-text-secondary mx-auto mb-2" />
        <p className="text-text-secondary text-sm">Loading deep-dive intel...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="bg-gray-900/95 border border-gray-700 rounded-lg p-6">
        <div className="flex justify-between items-center mb-3">
          <span className="text-red-400 text-sm">{error || 'No data available'}</span>
          <button onClick={onClose} className="text-gray-500 hover:text-white"><X className="h-4 w-4" /></button>
        </div>
      </div>
    );
  }

  // Activity bar chart max value
  const hourlyValues = Object.values(data.activity_pattern?.hourly || {});
  const maxActivity = Math.max(...hourlyValues, 1);

  return (
    <div className="bg-gray-900/95 border border-gray-700 rounded-lg shadow-2xl backdrop-blur-sm overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-700">
        <img
          src={`https://images.evetech.net/characters/${characterId}/portrait?size=64`}
          alt=""
          className="w-12 h-12 rounded"
        />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-bold text-white text-base truncate">{data.name}</span>
            <span
              className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded"
              style={{
                backgroundColor: (THREAT_COLORS[data.threat_level] || '#636366') + '25',
                color: THREAT_COLORS[data.threat_level] || '#636366',
              }}
            >
              {data.threat_level}
            </span>
          </div>
          <div className="text-xs text-gray-400 truncate">
            {data.corporation_name}
            {data.alliance_name && <span className="text-gray-500"> / {data.alliance_name}</span>}
          </div>
        </div>
        <button onClick={onClose} className="text-gray-500 hover:text-white p-1">
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-4 gap-px bg-gray-800">
        {[
          { label: 'Kills', value: data.kills.toLocaleString(), icon: Crosshair },
          { label: 'K/D', value: data.kd_ratio.toFixed(1), icon: TrendingUp },
          { label: 'Solo', value: data.solo_kills.toLocaleString(), icon: Shield },
          { label: 'ISK Destroyed', value: formatIsk(data.isk_destroyed), icon: Skull },
        ].map(({ label, value, icon: Icon }) => (
          <div key={label} className="bg-gray-900/80 px-3 py-2 text-center">
            <div className="flex items-center justify-center gap-1 text-gray-400 text-[10px] mb-0.5">
              <Icon className="h-2.5 w-2.5" />
              {label}
            </div>
            <div className="text-white text-sm font-mono font-medium">{value}</div>
          </div>
        ))}
      </div>

      <div className="p-4 space-y-4 max-h-[500px] overflow-y-auto">
        {/* Fleet Companions */}
        {data.fleet_companions.length > 0 && (
          <section>
            <h3 className="flex items-center gap-1.5 text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2">
              <Users className="h-3 w-3" />
              Fleet Companions ({data.fleet_companions.length})
            </h3>
            <div className="space-y-1">
              {data.fleet_companions.slice(0, 10).map((comp) => (
                <div
                  key={comp.character_id}
                  className="flex items-center gap-2 px-2 py-1 rounded bg-gray-800/50 hover:bg-gray-800 transition-colors"
                >
                  <img
                    src={`https://images.evetech.net/characters/${comp.character_id}/portrait?size=32`}
                    alt=""
                    className="w-5 h-5 rounded"
                  />
                  <span className="text-xs text-gray-200 flex-1 truncate">{comp.name}</span>
                  <span className="text-[10px] text-gray-500 font-mono">{comp.kills} kills</span>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Activity Pattern — 24h bar chart */}
        {hourlyValues.some((v) => v > 0) && (
          <section>
            <h3 className="flex items-center gap-1.5 text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2">
              <Clock className="h-3 w-3" />
              Activity by Hour (UTC)
              {data.active_timezone && (
                <span className="ml-auto text-cyan-400 normal-case tracking-normal">
                  Primary: {data.active_timezone}
                </span>
              )}
            </h3>
            <div className="flex items-end gap-px h-16">
              {Array.from({ length: 24 }, (_, h) => {
                const count = data.activity_pattern?.hourly?.[String(h)] || 0;
                const height = Math.max(2, (count / maxActivity) * 100);
                const isPeak = data.activity_pattern?.peak_hours?.includes(h);
                return (
                  <div
                    key={h}
                    className="flex-1 rounded-t transition-colors"
                    style={{
                      height: `${height}%`,
                      backgroundColor: isPeak ? '#22d3ee' : '#334155',
                    }}
                    title={`${String(h).padStart(2, '0')}:00 UTC — ${count} kills`}
                  />
                );
              })}
            </div>
            <div className="flex justify-between text-[8px] text-gray-600 mt-0.5">
              <span>00</span>
              <span>06</span>
              <span>12</span>
              <span>18</span>
              <span>23</span>
            </div>
          </section>
        )}

        {/* Top Ships */}
        {data.top_ships.length > 0 && (
          <section>
            <h3 className="flex items-center gap-1.5 text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2">
              <Crosshair className="h-3 w-3" />
              Ship Doctrine
            </h3>
            <div className="flex flex-wrap gap-1.5">
              {data.top_ships.map((ship) => (
                <div
                  key={ship.id}
                  className="flex items-center gap-1.5 px-2 py-1 rounded bg-gray-800/50 border border-gray-700/50"
                >
                  <img
                    src={`https://images.evetech.net/types/${ship.id}/icon?size=32`}
                    alt=""
                    className="w-4 h-4"
                  />
                  <span className="text-[11px] text-gray-200">{ship.name}</span>
                  <span className="text-[9px] text-gray-500 font-mono">{ship.kills}</span>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Corp History */}
        {data.corp_history.length > 0 && (
          <section>
            <h3 className="flex items-center gap-1.5 text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2">
              <Building className="h-3 w-3" />
              Corporation History ({data.corp_history.length})
            </h3>
            <div className="space-y-1">
              {data.corp_history.slice(0, 8).map((entry, i) => (
                <div
                  key={`${entry.corporation_id}-${i}`}
                  className="flex items-center gap-2 px-2 py-1 rounded bg-gray-800/50"
                >
                  <img
                    src={`https://images.evetech.net/corporations/${entry.corporation_id}/logo?size=32`}
                    alt=""
                    className="w-4 h-4 rounded"
                  />
                  <span className="text-[11px] text-gray-200 flex-1 truncate">{entry.corporation_name}</span>
                  <span className="text-[10px] text-gray-500">{formatDate(entry.start_date)}</span>
                  {i > 0 && data.corp_history[i - 1]?.start_date && (
                    <span className="text-[9px] text-gray-600 font-mono">
                      {timeSince(entry.start_date)}
                    </span>
                  )}
                </div>
              ))}
              {data.corp_history.length > 8 && (
                <div className="text-[10px] text-gray-500 px-2">
                  +{data.corp_history.length - 8} more
                </div>
              )}
            </div>
          </section>
        )}

        {/* Recent Kills Timeline */}
        {data.recent_kills.length > 0 && (
          <section>
            <h3 className="flex items-center gap-1.5 text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2">
              <Skull className="h-3 w-3" />
              Recent Kills
            </h3>
            <div className="space-y-1">
              {data.recent_kills.slice(0, 10).map((kill) => (
                <div
                  key={kill.kill_id}
                  className="flex items-center gap-2 px-2 py-1 rounded bg-gray-800/50"
                >
                  {kill.ship_type_id && (
                    <img
                      src={`https://images.evetech.net/types/${kill.ship_type_id}/icon?size=32`}
                      alt=""
                      className="w-4 h-4"
                    />
                  )}
                  <span className={`text-[11px] flex-1 truncate ${kill.is_loss ? 'text-red-400' : 'text-gray-200'}`}>
                    {kill.ship_name}
                    {kill.is_loss && <span className="text-[9px] ml-1 text-red-500">(loss)</span>}
                  </span>
                  <span className="text-[10px] text-gray-500 truncate">{kill.system_name}</span>
                  <span className="text-[10px] text-yellow-400/80 font-mono">{formatIsk(kill.value)}</span>
                  <span className="text-[9px] text-gray-600">{timeSince(kill.timestamp)}</span>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* zKill link */}
        <div className="pt-2 border-t border-gray-700">
          <a
            href={`https://zkillboard.com/character/${characterId}/`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[10px] text-cyan-500 hover:text-cyan-400"
          >
            View full profile on zKillboard →
          </a>
        </div>
      </div>
    </div>
  );
}
