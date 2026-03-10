'use client';

import { useMemo } from 'react';
import { useKillStream } from '@/components/map/useKillStream';
import type { MapKill } from '@/components/map/types';
import { Skull, Radio } from 'lucide-react';

function formatIsk(value: number): string {
  if (value >= 1e12) return `${(value / 1e12).toFixed(1)}T`;
  if (value >= 1e9) return `${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `${(value / 1e6).toFixed(1)}M`;
  if (value >= 1e3) return `${(value / 1e3).toFixed(0)}K`;
  return value.toFixed(0);
}

function formatTimeAgo(timestamp: number): string {
  const seconds = Math.floor((Date.now() - timestamp) / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  return `${Math.floor(seconds / 3600)}h ago`;
}

export function LiveKillFeed() {
  const { kills, isConnected } = useKillStream({
    maxKills: 10,
    includePods: false,
    minValue: 10_000_000,
  });

  const recentKills = useMemo(() => kills.slice(0, 8), [kills]);

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-xs font-semibold text-text-secondary uppercase tracking-wide flex items-center gap-2">
          <Radio className="h-3 w-3" />
          Live Kill Feed
        </h2>
        <div className="flex items-center gap-1.5">
          <span className={`h-1.5 w-1.5 rounded-full ${isConnected ? 'bg-green-400 animate-pulse' : 'bg-red-400'}`} />
          <span className="text-[10px] text-text-secondary">
            {isConnected ? 'LIVE' : 'OFFLINE'}
          </span>
        </div>
      </div>
      {recentKills.length > 0 ? (
        <div className="space-y-1">
          {recentKills.map((kill: MapKill) => (
            <div
              key={kill.killId}
              className="flex items-center justify-between px-3 py-1.5 rounded bg-card-hover/50 hover:bg-card-hover transition-colors text-sm"
            >
              <div className="flex items-center gap-2 min-w-0">
                <Skull className="h-3 w-3 text-risk-red flex-shrink-0" />
                <span className="text-text truncate">{kill.shipType}</span>
                {kill.systemName && (
                  <span className="text-text-secondary text-xs truncate hidden sm:inline">
                    in {kill.systemName}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-3 flex-shrink-0 ml-2">
                <span className="text-yellow-400 text-xs font-mono">
                  {formatIsk(kill.value)}
                </span>
                <span className="text-text-secondary text-[10px] w-12 text-right">
                  {formatTimeAgo(kill.timestamp)}
                </span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-6 text-text-secondary text-sm">
          {isConnected ? 'Waiting for kills...' : 'Connecting to kill feed...'}
        </div>
      )}
    </div>
  );
}
