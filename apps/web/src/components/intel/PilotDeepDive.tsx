'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { GatekeeperAPI } from '@/lib/api';
import type { PilotDeepDiveStats } from '@/lib/types';
import { X, Loader2, Shield, Users, Clock, Building, Crosshair, TrendingUp, Skull, ArrowLeft, ExternalLink } from 'lucide-react';
import { Skeleton } from '@/components/ui';

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
  const containerRef = useRef<HTMLDivElement>(null);
  const [activeId, setActiveId] = useState(characterId);
  const [history, setHistory] = useState<number[]>([]);
  const [data, setData] = useState<PilotDeepDiveStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const navigateTo = useCallback((targetId: number) => {
    setHistory((prev) => [...prev, activeId]);
    setActiveId(targetId);
  }, [activeId]);

  const navigateBack = useCallback(() => {
    setHistory((prev) => {
      const next = [...prev];
      const prevId = next.pop();
      if (prevId !== undefined) setActiveId(prevId);
      return next;
    });
  }, []);

  // Scroll deep dive into view on open and companion navigation
  useEffect(() => {
    containerRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, [activeId]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    GatekeeperAPI.getPilotDeepDive(activeId)
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
  }, [activeId]);

  if (loading) {
    return (
      <div className="bg-gray-900/95 border border-gray-700 rounded-lg overflow-hidden">
        {/* Header skeleton */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-700">
          <Skeleton variant="circular" className="h-12 w-12" />
          <div className="flex-1 space-y-2">
            <Skeleton variant="text" className="h-5 w-40" />
            <Skeleton variant="text" className="h-3 w-56" />
          </div>
        </div>
        {/* Stats skeleton */}
        <div className="px-4 py-3 grid grid-cols-4 gap-3 border-b border-gray-700">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="text-center space-y-1">
              <Skeleton variant="text" className="h-3 w-12 mx-auto" />
              <Skeleton variant="text" className="h-5 w-16 mx-auto" />
            </div>
          ))}
        </div>
        {/* Activity chart skeleton */}
        <div className="px-4 py-3 border-b border-gray-700">
          <Skeleton variant="text" className="h-3 w-32 mb-2" />
          <div className="flex items-end gap-px h-16">
            {Array.from({ length: 24 }).map((_, i) => (
              <Skeleton key={i} variant="rectangular" className="flex-1" height={`${20 + Math.random() * 80}%`} />
            ))}
          </div>
        </div>
        {/* Content skeleton */}
        <div className="px-4 py-3 space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} variant="text" className="h-4" style={{ width: `${70 + Math.random() * 30}%` }} />
          ))}
        </div>
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
    <div ref={containerRef} className="bg-gray-900/95 border border-gray-700 rounded-lg shadow-2xl backdrop-blur-sm overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-700">
        {history.length > 0 && (
          <button
            onClick={navigateBack}
            className="text-gray-400 hover:text-white p-1 -ml-1 rounded hover:bg-gray-800 transition-colors"
            title="Back"
          >
            <ArrowLeft className="h-4 w-4" />
          </button>
        )}
        <img
          src={`https://images.evetech.net/characters/${activeId}/portrait?size=64`}
          alt=""
          className="w-12 h-12 rounded"
        />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <a
              href={`https://zkillboard.com/character/${activeId}/`}
              target="_blank"
              rel="noopener noreferrer"
              className="font-bold text-white text-base truncate hover:text-cyan-400 transition-colors"
            >{data.name}</a>
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
          <div className="text-xs truncate">
            <a
              href={`https://zkillboard.com/corporation/${data.corporation_id}/`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-gray-400 hover:text-cyan-400 transition-colors"
            >
              {data.corporation_name}
            </a>
            {data.alliance_name && data.alliance_id && (
              <span className="text-gray-500"> / <a
                href={`https://zkillboard.com/alliance/${data.alliance_id}/`}
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-cyan-400 transition-colors"
              >
                {data.alliance_name}
              </a></span>
            )}
            {data.alliance_name && !data.alliance_id && (
              <span className="text-gray-500"> / {data.alliance_name}</span>
            )}
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
                  className="flex items-center gap-2 px-2 py-1 rounded bg-gray-800/50 hover:bg-gray-700 transition-colors"
                >
                  <button
                    onClick={() => navigateTo(comp.character_id)}
                    className="flex items-center gap-2 flex-1 min-w-0 cursor-pointer text-left"
                    title={`View ${comp.name}'s deep dive`}
                  >
                    <img
                      src={`https://images.evetech.net/characters/${comp.character_id}/portrait?size=32`}
                      alt=""
                      className="w-5 h-5 rounded"
                    />
                    <span className="text-xs text-cyan-300 hover:text-cyan-200 flex-1 truncate">{comp.name}</span>
                  </button>
                  <a
                    href={`https://zkillboard.com/character/${comp.character_id}/`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-gray-500 hover:text-cyan-400 transition-colors shrink-0"
                    title={`${comp.name} on zKillboard`}
                    onClick={(e) => e.stopPropagation()}
                  >
                    <ExternalLink className="h-3 w-3" />
                  </a>
                  <span className="text-[10px] text-gray-500 font-mono shrink-0">{comp.kills} kills</span>
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
                <a
                  key={ship.id}
                  href={`https://zkillboard.com/character/${activeId}/shipTypeID/${ship.id}/`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 px-2 py-1 rounded bg-gray-800/50 border border-gray-700/50 hover:border-cyan-500/50 hover:bg-gray-700/50 transition-colors cursor-pointer"
                  title={`View ${ship.name} killmails & fittings on zKillboard`}
                >
                  <img
                    src={`https://images.evetech.net/types/${ship.id}/icon?size=32`}
                    alt=""
                    className="w-4 h-4"
                  />
                  <span className="text-[11px] text-gray-200">{ship.name}</span>
                  <span className="text-[9px] text-gray-500 font-mono">{ship.kills}</span>
                </a>
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
                <a
                  key={`${entry.corporation_id}-${i}`}
                  href={`https://zkillboard.com/corporation/${entry.corporation_id}/`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 px-2 py-1 rounded bg-gray-800/50 hover:bg-gray-700 transition-colors"
                >
                  <img
                    src={`https://images.evetech.net/corporations/${entry.corporation_id}/logo?size=32`}
                    alt=""
                    className="w-4 h-4 rounded"
                  />
                  <span className="text-[11px] text-cyan-300 hover:text-cyan-200 flex-1 truncate">{entry.corporation_name}</span>
                  <span className="text-[10px] text-gray-500">{formatDate(entry.start_date)}</span>
                  {i > 0 && data.corp_history[i - 1]?.start_date && (
                    <span className="text-[9px] text-gray-600 font-mono">
                      {timeSince(entry.start_date)}
                    </span>
                  )}
                </a>
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
                <a
                  key={kill.kill_id}
                  href={`https://zkillboard.com/kill/${kill.kill_id}/`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 px-2 py-1 rounded bg-gray-800/50 hover:bg-gray-700 transition-colors"
                >
                  {kill.ship_type_id && (
                    <img
                      src={`https://images.evetech.net/types/${kill.ship_type_id}/icon?size=32`}
                      alt=""
                      className="w-4 h-4"
                    />
                  )}
                  <span className={`text-[11px] flex-1 truncate ${kill.is_loss ? 'text-red-400' : 'text-cyan-300 hover:text-cyan-200'}`}>
                    {kill.ship_name}
                    {kill.is_loss && <span className="text-[9px] ml-1 text-red-500">(loss)</span>}
                  </span>
                  <span className="text-[10px] text-gray-500 truncate">{kill.system_name}</span>
                  <span className="text-[10px] text-yellow-400/80 font-mono">{formatIsk(kill.value)}</span>
                  <span className="text-[9px] text-gray-600">{timeSince(kill.timestamp)}</span>
                </a>
              ))}
            </div>
          </section>
        )}

        {/* zKill link */}
        <div className="pt-2 border-t border-gray-700">
          <a
            href={`https://zkillboard.com/character/${activeId}/`}
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
