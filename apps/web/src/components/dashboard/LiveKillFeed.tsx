'use client';

import { useMemo, useState, useRef, useEffect, useCallback } from 'react';
import { useKillStream } from '@/components/map/useKillStream';
import type { MapKill } from '@/components/map/types';
import { PilotThreatCard } from '@/components/intel/PilotThreatCard';
import { PilotDeepDive } from '@/components/intel/PilotDeepDive';
import { SystemSummaryCard } from '@/components/intel/SystemSummaryCard';
import { loadPinnedCorps, savePinnedCorps, loadPinnedAlliances, savePinnedAlliances } from '@/lib/pinnedItems';
import type { PinnedCorp, PinnedAlliance } from '@/lib/pinnedItems';
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

type PopoverTarget =
  | { type: 'pilot'; characterId: number }
  | { type: 'system'; systemName: string; systemId: number };

export function LiveKillFeed() {
  const { kills, isConnected } = useKillStream({
    maxKills: 10,
    includePods: false,
    minValue: 10_000_000,
  });

  const recentKills = useMemo(() => kills.slice(0, 8), [kills]);
  const [popover, setPopover] = useState<PopoverTarget | null>(null);
  const [popoverPos, setPopoverPos] = useState<{ top: number; left: number } | null>(null);
  const popoverRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Pinned corps/alliances for popover PilotThreatCards
  const [pinnedCorps, setPinnedCorps] = useState<PinnedCorp[]>([]);
  const [pinnedAlliances, setPinnedAlliances] = useState<PinnedAlliance[]>([]);
  const [deepDiveId, setDeepDiveId] = useState<number | null>(null);

  useEffect(() => {
    setPinnedCorps(loadPinnedCorps());
    setPinnedAlliances(loadPinnedAlliances());
  }, []);

  const pinnedCorpIds = useMemo(() => new Set(pinnedCorps.map((c) => c.corporationId)), [pinnedCorps]);
  const pinnedAllianceIds = useMemo(() => new Set(pinnedAlliances.map((a) => a.allianceId)), [pinnedAlliances]);

  const handleTogglePinCorp = useCallback((corpId: number, corpName: string) => {
    setPinnedCorps((prev) => {
      const exists = prev.some((c) => c.corporationId === corpId);
      const next = exists ? prev.filter((c) => c.corporationId !== corpId) : [...prev, { corporationId: corpId, name: corpName }];
      savePinnedCorps(next);
      return next;
    });
  }, []);

  const handleTogglePinAlliance = useCallback((allianceId: number, allianceName: string) => {
    setPinnedAlliances((prev) => {
      const exists = prev.some((a) => a.allianceId === allianceId);
      const next = exists ? prev.filter((a) => a.allianceId !== allianceId) : [...prev, { allianceId, name: allianceName }];
      savePinnedAlliances(next);
      return next;
    });
  }, []);

  // Close popover on click outside
  useEffect(() => {
    if (!popover) return;
    const handleClick = (e: MouseEvent) => {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        setPopover(null);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [popover]);

  const positionPopover = (e: React.MouseEvent) => {
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    const containerRect = containerRef.current?.getBoundingClientRect();
    if (containerRect) {
      setPopoverPos({
        top: rect.top - containerRect.top + rect.height + 4,
        left: Math.min(rect.left - containerRect.left, containerRect.width - 320),
      });
    }
  };

  const handlePilotClick = (kill: MapKill, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!kill.victimCharacterId) return;
    if (popover?.type === 'pilot' && popover.characterId === kill.victimCharacterId) {
      setPopover(null);
      return;
    }
    positionPopover(e);
    setPopover({ type: 'pilot', characterId: kill.victimCharacterId });
  };

  const handleSystemClick = (kill: MapKill, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!kill.systemName) return;
    if (popover?.type === 'system' && popover.systemName === kill.systemName) {
      setPopover(null);
      return;
    }
    positionPopover(e);
    setPopover({ type: 'system', systemName: kill.systemName, systemId: kill.systemId });
  };

  return (
    <div ref={containerRef} className="relative">
      {/* Deep Dive Panel */}
      {deepDiveId && (
        <PilotDeepDive characterId={deepDiveId} onClose={() => setDeepDiveId(null)} />
      )}

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
                <span
                  className={`text-text truncate ${kill.victimCharacterId ? 'cursor-pointer hover:text-primary transition-colors' : ''}`}
                  onClick={(e) => handlePilotClick(kill, e)}
                >
                  {kill.shipType}
                </span>
                {kill.systemName && (
                  <span
                    className="text-text-secondary text-xs truncate hidden sm:inline cursor-pointer hover:text-primary transition-colors"
                    onClick={(e) => handleSystemClick(kill, e)}
                  >
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

      {/* Popover — Pilot Threat or System Summary */}
      {popover && popoverPos && (
        <div
          ref={popoverRef}
          className="absolute z-50 shadow-xl"
          style={{ top: popoverPos.top, left: Math.max(0, popoverPos.left) }}
        >
          {popover.type === 'pilot' ? (
            <PilotThreatCard
              characterId={popover.characterId}
              onClose={() => setPopover(null)}
              onPinCorp={handleTogglePinCorp}
              onPinAlliance={handleTogglePinAlliance}
              pinnedCorpIds={pinnedCorpIds}
              pinnedAllianceIds={pinnedAllianceIds}
              onDeepDive={(id) => { setDeepDiveId(id); setPopover(null); }}
            />
          ) : (
            <SystemSummaryCard
              systemName={popover.systemName}
              systemId={popover.systemId}
              onClose={() => setPopover(null)}
            />
          )}
        </div>
      )}
    </div>
  );
}
