'use client';

import { memo, useState, useMemo, useCallback, useEffect } from 'react';
import { useHotSystems } from '@/hooks';
import { Card, Select, Badge } from '@/components/ui';
import { SecurityBadge } from '@/components/system';
import { Radar, Skull, TrendingUp, ArrowUpDown, ArrowUp, ArrowDown, Pin, X, MapPin, Building2, Shield } from 'lucide-react';
import { ErrorMessage, SkeletonTable, getUserFriendlyError } from '@/components/ui';
import { PilotThreatCard } from './PilotThreatCard';
import { SystemSummaryCard } from './SystemSummaryCard';
import { loadPinnedPilots, savePinnedPilots, type PinnedPilot } from './PilotLookupTab';
import {
  loadPinnedSystems, savePinnedSystems, type PinnedSystem,
  loadPinnedCorps, savePinnedCorps, type PinnedCorp,
  loadPinnedAlliances, savePinnedAlliances, type PinnedAlliance,
} from '@/lib/pinnedItems';
import type { HotSystem } from '@/lib/types';

const timeOptions = [
  { value: '1', label: 'Last 1 hour' },
  { value: '6', label: 'Last 6 hours' },
  { value: '24', label: 'Last 24 hours' },
  { value: '48', label: 'Last 48 hours' },
];

const limitOptions = [
  { value: '10', label: 'Top 10' },
  { value: '25', label: 'Top 25' },
  { value: '50', label: 'Top 50' },
];

/**
 * HotSystemRow - Memoized table row for performance in large lists
 */
interface HotSystemRowProps {
  system: HotSystem;
  index: number;
}

const HotSystemRow = memo(function HotSystemRow({ system, index }: HotSystemRowProps) {
  const secLabel = system.category === 'high_sec' ? 'Highsec' : system.category === 'low_sec' ? 'Lowsec' : 'Nullsec';
  const secBadgeVariant = system.category === 'high_sec' ? 'success' as const : system.category === 'low_sec' ? 'warning' as const : 'danger' as const;
  const secBadgeLetter = system.category === 'high_sec' ? 'H' : system.category === 'low_sec' ? 'L' : 'N';

  return (
    <>
      {/* Desktop table row (sm+) */}
      <div
        className="hidden sm:grid grid-cols-12 gap-2 sm:gap-4 px-3 sm:px-4 py-3 border-t border-border hover:bg-card-hover transition-colors items-center"
        role="row"
      >
        <div className="col-span-1 text-text-secondary text-sm" role="cell">
          {index + 1}
        </div>
        <div className="col-span-4 font-medium text-text truncate" role="cell">
          {system.system_name}
        </div>
        <div className="col-span-2" role="cell">
          <SecurityBadge security={system.security} size="sm" />
        </div>
        <div className="col-span-2 text-right" role="cell">
          <span className="text-risk-red font-medium">
            {system.recent_kills}
          </span>
        </div>
        <div className="col-span-2 text-right" role="cell">
          {system.recent_pods > 0 ? (
            <span className="text-risk-orange font-medium">
              {system.recent_pods}
            </span>
          ) : (
            <span className="text-text-secondary">0</span>
          )}
        </div>
        <div className="col-span-1 text-right" role="cell">
          <Badge
            variant={secBadgeVariant}
            size="sm"
            aria-label={secLabel}
          >
            {secBadgeLetter}
          </Badge>
        </div>
      </div>

      {/* Mobile card (<sm) */}
      <div
        className="sm:hidden border-t border-border px-3 py-3 hover:bg-card-hover transition-colors"
        role="row"
      >
        <div className="flex items-center gap-2">
          <span className="text-text-secondary text-sm">{index + 1}.</span>
          <span className="font-medium text-text truncate">{system.system_name}</span>
          <SecurityBadge security={system.security} size="sm" />
        </div>
        <div className="flex items-center gap-4 mt-1">
          <span className="text-risk-red font-medium text-sm">
            <Skull className="inline h-3 w-3 mr-1" aria-hidden="true" />
            {system.recent_kills} kills
          </span>
          <span className={`font-medium text-sm ${system.recent_pods > 0 ? 'text-risk-orange' : 'text-text-secondary'}`}>
            {system.recent_pods} pods
          </span>
        </div>
        <div className="mt-1 text-xs text-text-secondary">{secLabel}</div>
      </div>
    </>
  );
});

type SortKey = 'kills' | 'pods' | 'security' | 'name';
type SortDir = 'asc' | 'desc';

function SortHeader({ label, sortKey, col, currentKey, currentDir, onSort, align }: {
  label: string;
  sortKey: SortKey;
  col: string;
  currentKey: SortKey;
  currentDir: SortDir;
  onSort: (key: SortKey) => void;
  align?: 'right';
}) {
  const active = currentKey === sortKey;
  return (
    <div className={col} role="columnheader">
      <button
        onClick={() => onSort(sortKey)}
        className={`inline-flex items-center gap-1 hover:text-text transition-colors ${align === 'right' ? 'ml-auto' : ''}`}
      >
        {label}
        {active ? (
          currentDir === 'asc' ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />
        ) : (
          <ArrowUpDown className="h-3 w-3 opacity-30" />
        )}
      </button>
    </div>
  );
}

export default function IntelFeed() {
  const [hours, setHours] = useState(24);
  const [limit, setLimit] = useState(25);
  const [sortKey, setSortKey] = useState<SortKey>('kills');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const [pinnedPilots, setPinnedPilots] = useState<PinnedPilot[]>([]);
  const [pinnedSystems, setPinnedSystems] = useState<PinnedSystem[]>([]);
  const [pinnedCorps, setPinnedCorps] = useState<PinnedCorp[]>([]);
  const [pinnedAlliances, setPinnedAlliances] = useState<PinnedAlliance[]>([]);

  // Load all pinned items
  useEffect(() => {
    setPinnedPilots(loadPinnedPilots());
    setPinnedSystems(loadPinnedSystems());
    setPinnedCorps(loadPinnedCorps());
    setPinnedAlliances(loadPinnedAlliances());
    const handler = () => {
      setPinnedPilots(loadPinnedPilots());
      setPinnedSystems(loadPinnedSystems());
      setPinnedCorps(loadPinnedCorps());
      setPinnedAlliances(loadPinnedAlliances());
    };
    window.addEventListener('storage', handler);
    return () => window.removeEventListener('storage', handler);
  }, []);

  const handleUnpinPilot = useCallback((characterId: number) => {
    setPinnedPilots((prev) => {
      const next = prev.filter((p) => p.characterId !== characterId);
      savePinnedPilots(next);
      return next;
    });
  }, []);

  const handleTogglePinSystem = useCallback((systemId: number, name: string) => {
    setPinnedSystems((prev) => {
      const exists = prev.some((s) => s.systemId === systemId);
      const next = exists
        ? prev.filter((s) => s.systemId !== systemId)
        : [...prev, { systemId, name }];
      savePinnedSystems(next);
      return next;
    });
  }, []);

  const handleUnpinCorp = useCallback((corporationId: number) => {
    setPinnedCorps((prev) => {
      const next = prev.filter((c) => c.corporationId !== corporationId);
      savePinnedCorps(next);
      return next;
    });
  }, []);

  const handleUnpinAlliance = useCallback((allianceId: number) => {
    setPinnedAlliances((prev) => {
      const next = prev.filter((a) => a.allianceId !== allianceId);
      savePinnedAlliances(next);
      return next;
    });
  }, []);

  const { data: hotSystems, isLoading, error, refetch } = useHotSystems(hours, limit);

  const handleSort = useCallback((key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  }, [sortKey]);

  // Memoize sorted systems
  const filteredSystems = useMemo(() => {
    if (!hotSystems) return [];
    const dir = sortDir === 'asc' ? 1 : -1;
    return [...hotSystems].sort((a, b) => {
      switch (sortKey) {
        case 'kills': return (a.recent_kills - b.recent_kills) * dir;
        case 'pods': return (a.recent_pods - b.recent_pods) * dir;
        case 'security': return (a.security - b.security) * dir;
        case 'name': return a.system_name.localeCompare(b.system_name) * dir;
        default: return 0;
      }
    });
  }, [hotSystems, sortKey, sortDir]);

  // Memoize summary stats to avoid recalculating on every render
  const stats = useMemo(() => {
    if (!hotSystems || hotSystems.length === 0) return null;
    return {
      totalKills: hotSystems.reduce((sum, s) => sum + s.recent_kills, 0),
      totalPods: hotSystems.reduce((sum, s) => sum + s.recent_pods, 0),
      hottest: hotSystems[0]?.system_name || '-',
    };
  }, [hotSystems]);

  const hasPinnedItems = pinnedPilots.length > 0 || pinnedSystems.length > 0 || pinnedCorps.length > 0 || pinnedAlliances.length > 0;

  return (
    <div className="space-y-6">
      {/* Pinned Items */}
      {hasPinnedItems && (
        <div className="space-y-5">
          {/* Pinned Pilots */}
          {pinnedPilots.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Pin className="h-4 w-4 text-cyan-400" />
                <span className="text-sm font-medium text-text">Watched Pilots</span>
                <span className="text-[10px] text-text-secondary">({pinnedPilots.length})</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
                {pinnedPilots.map((p) => (
                  <PilotThreatCard
                    key={p.characterId}
                    characterId={p.characterId}
                    onClose={() => handleUnpinPilot(p.characterId)}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Pinned Systems */}
          {pinnedSystems.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <MapPin className="h-4 w-4 text-cyan-400" />
                <span className="text-sm font-medium text-text">Watched Systems</span>
                <span className="text-[10px] text-text-secondary">({pinnedSystems.length})</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
                {pinnedSystems.map((s) => (
                  <SystemSummaryCard
                    key={s.systemId}
                    systemName={s.name}
                    systemId={s.systemId}
                    onClose={() => handleTogglePinSystem(s.systemId, s.name)}
                    onPin={handleTogglePinSystem}
                    isPinned
                  />
                ))}
              </div>
            </div>
          )}

          {/* Pinned Corporations */}
          {pinnedCorps.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Building2 className="h-4 w-4 text-cyan-400" />
                <span className="text-sm font-medium text-text">Watched Corporations</span>
                <span className="text-[10px] text-text-secondary">({pinnedCorps.length})</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {pinnedCorps.map((c) => (
                  <div
                    key={c.corporationId}
                    className="flex items-center gap-2 px-3 py-1.5 bg-card border border-border rounded-lg text-sm"
                  >
                    <img
                      src={`https://images.evetech.net/corporations/${c.corporationId}/logo?size=32`}
                      alt=""
                      className="h-5 w-5 rounded"
                    />
                    <span className="text-text">{c.name}</span>
                    <a
                      href={`https://zkillboard.com/corporation/${c.corporationId}/`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[10px] text-primary hover:text-primary/80"
                    >
                      zKill
                    </a>
                    <button
                      onClick={() => handleUnpinCorp(c.corporationId)}
                      className="text-text-secondary hover:text-red-400 transition-colors"
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Pinned Alliances */}
          {pinnedAlliances.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Shield className="h-4 w-4 text-cyan-400" />
                <span className="text-sm font-medium text-text">Watched Alliances</span>
                <span className="text-[10px] text-text-secondary">({pinnedAlliances.length})</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {pinnedAlliances.map((a) => (
                  <div
                    key={a.allianceId}
                    className="flex items-center gap-2 px-3 py-1.5 bg-card border border-border rounded-lg text-sm"
                  >
                    <img
                      src={`https://images.evetech.net/alliances/${a.allianceId}/logo?size=32`}
                      alt=""
                      className="h-5 w-5 rounded"
                    />
                    <span className="text-text">{a.name}</span>
                    <a
                      href={`https://zkillboard.com/alliance/${a.allianceId}/`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[10px] text-primary hover:text-primary/80"
                    >
                      zKill
                    </a>
                    <button
                      onClick={() => handleUnpinAlliance(a.allianceId)}
                      className="text-text-secondary hover:text-red-400 transition-colors"
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Filters */}
      <Card>
        <div className="flex flex-wrap gap-4">
          <div className="w-40">
            <Select
              label="Time Range"
              value={hours.toString()}
              onChange={(e) => setHours(parseInt(e.target.value))}
              options={timeOptions}
            />
          </div>
          <div className="w-32">
            <Select
              label="Show"
              value={limit.toString()}
              onChange={(e) => setLimit(parseInt(e.target.value))}
              options={limitOptions}
            />
          </div>
        </div>
      </Card>

      {/* Stats Summary */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4" role="region" aria-label="Kill statistics summary">
          <Card className="text-center">
            <div className="flex items-center justify-center gap-2 mb-1">
              <Radar className="h-4 w-4 text-primary" aria-hidden="true" />
              <span className="text-xs text-text-secondary uppercase">Systems</span>
            </div>
            <span className="text-2xl font-bold text-text" aria-label={`${hotSystems?.length || 0} systems`}>
              {hotSystems?.length || 0}
            </span>
          </Card>
          <Card className="text-center">
            <div className="flex items-center justify-center gap-2 mb-1">
              <Skull className="h-4 w-4 text-risk-red" aria-hidden="true" />
              <span className="text-xs text-text-secondary uppercase">
                Total Kills
              </span>
            </div>
            <span className="text-2xl font-bold text-risk-red" aria-label={`${stats.totalKills} total kills`}>
              {stats.totalKills}
            </span>
          </Card>
          <Card className="text-center">
            <div className="flex items-center justify-center gap-2 mb-1">
              <Skull className="h-4 w-4 text-risk-orange" aria-hidden="true" />
              <span className="text-xs text-text-secondary uppercase">
                Total Pods
              </span>
            </div>
            <span className="text-2xl font-bold text-risk-orange" aria-label={`${stats.totalPods} total pods`}>
              {stats.totalPods}
            </span>
          </Card>
          <Card className="text-center">
            <div className="flex items-center justify-center gap-2 mb-1">
              <TrendingUp className="h-4 w-4 text-risk-red" aria-hidden="true" />
              <span className="text-xs text-text-secondary uppercase">Hottest</span>
            </div>
            <span className="text-lg font-bold text-text truncate" aria-label={`Hottest system: ${stats.hottest}`}>
              {stats.hottest}
            </span>
          </Card>
        </div>
      )}

      {/* Hot Systems Table */}
      <section aria-labelledby="hot-systems-heading">
        <h2 id="hot-systems-heading" className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-4">
          Hot Systems
        </h2>

        {isLoading ? (
          <SkeletonTable rows={5} columns={6} aria-label="Loading hot systems data" />
        ) : error ? (
          <ErrorMessage
            title="Unable to load intel data"
            message={getUserFriendlyError(error)}
            onRetry={() => refetch()}
          />
        ) : filteredSystems && filteredSystems.length > 0 ? (
          <div className="border border-border rounded-lg overflow-hidden" role="table" aria-label="Hot systems with kill activity">
            {/* Table Header */}
            <div className="hidden sm:grid grid-cols-12 gap-2 sm:gap-4 px-3 sm:px-4 py-3 bg-card text-xs text-text-secondary uppercase font-semibold" role="row">
              <div className="col-span-1" role="columnheader">#</div>
              <SortHeader label="System" sortKey="name" col="col-span-4" currentKey={sortKey} currentDir={sortDir} onSort={handleSort} />
              <SortHeader label="Security" sortKey="security" col="col-span-2" currentKey={sortKey} currentDir={sortDir} onSort={handleSort} />
              <SortHeader label="Kills" sortKey="kills" col="col-span-2 text-right" currentKey={sortKey} currentDir={sortDir} onSort={handleSort} align="right" />
              <SortHeader label="Pods" sortKey="pods" col="col-span-2 text-right" currentKey={sortKey} currentDir={sortDir} onSort={handleSort} align="right" />
              <div className="col-span-1 text-right" role="columnheader">Sec</div>
            </div>

            {/* Table Body - Using memoized HotSystemRow for performance */}
            {filteredSystems.map((system, index) => (
              <HotSystemRow
                key={system.system_id}
                system={system}
                index={index}
              />
            ))}
          </div>
        ) : (
          <Card className="text-center py-12">
            <Radar className="h-12 w-12 text-text-secondary mx-auto mb-4" aria-hidden="true" />
            <p className="text-text-secondary">
              No systems with recent kill activity. Space is quiet for now.
            </p>
          </Card>
        )}
      </section>
    </div>
  );
}
