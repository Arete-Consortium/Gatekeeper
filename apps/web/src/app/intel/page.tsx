'use client';

import { memo, useState, useMemo } from 'react';
import { useTranslations } from 'next-intl';
import { useHotSystems } from '@/hooks';
import { Card, Input, Select, Badge } from '@/components/ui';
import { SecurityBadge } from '@/components/system';
import { Radar, Skull, TrendingUp } from 'lucide-react';
import { ErrorMessage, SkeletonCard, SkeletonTable, getUserFriendlyError } from '@/components/ui';
import type { HotSystem } from '@/lib/types';

/**
 * HotSystemRow - Memoized table row for performance in large lists
 */
interface HotSystemRowProps {
  system: HotSystem;
  index: number;
}

const HotSystemRow = memo(function HotSystemRow({ system, index }: HotSystemRowProps) {
  return (
    <div
      className="grid grid-cols-12 gap-2 sm:gap-4 px-3 sm:px-4 py-3 border-t border-border hover:bg-card-hover transition-colors items-center min-w-[500px]"
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
          variant={
            system.category === 'high_sec'
              ? 'success'
              : system.category === 'low_sec'
                ? 'warning'
                : 'danger'
          }
          size="sm"
          aria-label={system.category === 'high_sec' ? 'High security' : system.category === 'low_sec' ? 'Low security' : 'Null security'}
        >
          {system.category === 'high_sec'
            ? 'H'
            : system.category === 'low_sec'
              ? 'L'
              : 'N'}
        </Badge>
      </div>
    </div>
  );
});

export default function IntelPage() {
  const t = useTranslations('intel');
  const tc = useTranslations('common');
  const [hours, setHours] = useState(24);
  const [limit, setLimit] = useState(25);
  const [search, setSearch] = useState('');

  const timeOptions = [
    { value: '1', label: t('last1h') },
    { value: '6', label: t('last6h') },
    { value: '24', label: t('last24h') },
    { value: '48', label: t('last48h') },
  ];

  const limitOptions = [
    { value: '10', label: t('top10') },
    { value: '25', label: t('top25') },
    { value: '50', label: t('top50') },
  ];

  const { data: hotSystems, isLoading, error, refetch } = useHotSystems(hours, limit);

  // Memoize filtered systems and stats to prevent recalculation on every render
  const filteredSystems = useMemo(() => {
    if (!hotSystems) return [];
    if (!search) return hotSystems;
    const lowerSearch = search.toLowerCase();
    return hotSystems.filter((system) =>
      system.system_name.toLowerCase().includes(lowerSearch)
    );
  }, [hotSystems, search]);

  // Memoize summary stats to avoid recalculating on every render
  const stats = useMemo(() => {
    if (!hotSystems || hotSystems.length === 0) return null;
    return {
      totalKills: hotSystems.reduce((sum, s) => sum + s.recent_kills, 0),
      totalPods: hotSystems.reduce((sum, s) => sum + s.recent_pods, 0),
      hottest: hotSystems[0]?.system_name || '-',
    };
  }, [hotSystems]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-text">{t('title')}</h1>
        <p className="text-text-secondary mt-1">
          {t('subtitle')}
        </p>
      </div>

      {/* Filters */}
      <Card>
        <div className="flex flex-wrap gap-4">
          <div className="flex-1 min-w-[200px]">
            <Input
              label={t('searchSystems')}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={t('systemPlaceholder')}
            />
          </div>
          <div className="w-40">
            <Select
              label={t('timeRange')}
              value={hours.toString()}
              onChange={(e) => setHours(parseInt(e.target.value))}
              options={timeOptions}
            />
          </div>
          <div className="w-32">
            <Select
              label={t('show')}
              value={limit.toString()}
              onChange={(e) => setLimit(parseInt(e.target.value))}
              options={limitOptions}
            />
          </div>
        </div>
      </Card>

      {/* Stats Summary */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4" role="region" aria-label={t('title')}>
          <Card className="text-center">
            <div className="flex items-center justify-center gap-2 mb-1">
              <Radar className="h-4 w-4 text-primary" aria-hidden="true" />
              <span className="text-xs text-text-secondary uppercase">{tc('systems')}</span>
            </div>
            <span className="text-2xl font-bold text-text">
              {hotSystems?.length || 0}
            </span>
          </Card>
          <Card className="text-center">
            <div className="flex items-center justify-center gap-2 mb-1">
              <Skull className="h-4 w-4 text-risk-red" aria-hidden="true" />
              <span className="text-xs text-text-secondary uppercase">
                {t('totalKills')}
              </span>
            </div>
            <span className="text-2xl font-bold text-risk-red">
              {stats.totalKills}
            </span>
          </Card>
          <Card className="text-center">
            <div className="flex items-center justify-center gap-2 mb-1">
              <Skull className="h-4 w-4 text-risk-orange" aria-hidden="true" />
              <span className="text-xs text-text-secondary uppercase">
                {t('totalPods')}
              </span>
            </div>
            <span className="text-2xl font-bold text-risk-orange">
              {stats.totalPods}
            </span>
          </Card>
          <Card className="text-center">
            <div className="flex items-center justify-center gap-2 mb-1">
              <TrendingUp className="h-4 w-4 text-risk-red" aria-hidden="true" />
              <span className="text-xs text-text-secondary uppercase">{t('hottest')}</span>
            </div>
            <span className="text-lg font-bold text-text truncate">
              {stats.hottest}
            </span>
          </Card>
        </div>
      )}

      {/* Hot Systems Table */}
      <section aria-labelledby="hot-systems-heading">
        <h2 id="hot-systems-heading" className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-4">
          {t('hotSystems')}
        </h2>

        {isLoading ? (
          <SkeletonTable rows={5} columns={6} aria-label={tc('loading')} />
        ) : error ? (
          <ErrorMessage
            title={t('unableToLoad')}
            message={getUserFriendlyError(error)}
            onRetry={() => refetch()}
          />
        ) : filteredSystems && filteredSystems.length > 0 ? (
          <div className="border border-border rounded-lg overflow-x-auto" role="table" aria-label={t('hotSystems')}>
            {/* Table Header */}
            <div className="grid grid-cols-12 gap-2 sm:gap-4 px-3 sm:px-4 py-3 bg-card text-xs text-text-secondary uppercase font-semibold min-w-[500px]" role="row">
              <div className="col-span-1" role="columnheader">#</div>
              <div className="col-span-4" role="columnheader">{t('system')}</div>
              <div className="col-span-2" role="columnheader">{tc('security')}</div>
              <div className="col-span-2 text-right" role="columnheader">{tc('kills')}</div>
              <div className="col-span-2 text-right" role="columnheader">{tc('pods')}</div>
              <div className="col-span-1 text-right" role="columnheader"><span className="sr-only">{t('cat')}</span>{t('cat')}</div>
            </div>

            {/* Table Body */}
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
              {search
                ? t('noMatch', { search })
                : t('spaceQuiet')}
            </p>
          </Card>
        )}
      </section>
    </div>
  );
}
