'use client';

import { Suspense, useState, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useRoute } from '@/hooks';
import { Card, Button, Toggle } from '@/components/ui';
import { Select } from '@/components/ui/Select';
import { SystemSearch, RouteResult } from '@/components/route';
import { ROUTE_PROFILES } from '@/lib/utils';
import type { RouteProfile } from '@/lib/types';
import { Route, Loader2, ArrowRightLeft } from 'lucide-react';
import { ErrorMessage, getUserFriendlyError } from '@/components/ui';

const profileOptions = Object.entries(ROUTE_PROFILES).map(([value, config]) => ({
  value,
  label: config.label,
}));

function RoutePageContent() {
  const searchParams = useSearchParams();
  const t = useTranslations('route');

  const [fromSystem, setFromSystem] = useState('');
  const [toSystem, setToSystem] = useState('');
  const [profile, setProfile] = useState<RouteProfile>('safer');
  const [includeBridges, setIncludeBridges] = useState(false);
  const [includeThera, setIncludeThera] = useState(false);
  const [shouldFetch, setShouldFetch] = useState(false);

  // Initialize from URL params
  useEffect(() => {
    const from = searchParams.get('from');
    const to = searchParams.get('to');
    const p = searchParams.get('profile') as RouteProfile | null;

    if (from) setFromSystem(from);
    if (to) setToSystem(to);
    if (p && p in ROUTE_PROFILES) setProfile(p);

    // Auto-search if both params provided
    if (from && to) {
      setShouldFetch(true);
    }
  }, [searchParams]);

  const {
    data: route,
    isLoading,
    error,
    refetch,
  } = useRoute({
    from: fromSystem,
    to: toSystem,
    profile,
    bridges: includeBridges,
    thera: includeThera,
    enabled: shouldFetch,
  });

  const handleSearch = () => {
    if (fromSystem && toSystem) {
      setShouldFetch(true);
      refetch();
    }
  };

  const handleSwap = () => {
    const temp = fromSystem;
    setFromSystem(toSystem);
    setToSystem(temp);
    setShouldFetch(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && fromSystem && toSystem) {
      handleSearch();
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-text">{t('title')}</h1>
        <p className="text-text-secondary mt-1">
          {t('subtitle')}
        </p>
      </div>

      {/* Search Form */}
      <Card>
        <div className="space-y-4">
          {/* From/To with Swap */}
          <div className="flex gap-4 items-end">
            <div className="flex-1" onKeyDown={handleKeyDown}>
              <SystemSearch
                label={t('from')}
                value={fromSystem}
                onChange={setFromSystem}
                placeholder={t('originPlaceholder')}
              />
            </div>

            <button
              type="button"
              onClick={handleSwap}
              className="p-2 mb-1 text-text-secondary hover:text-primary transition-colors rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 focus:ring-offset-background"
              aria-label={t('swapSystems')}
            >
              <ArrowRightLeft className="h-5 w-5" aria-hidden="true" />
            </button>

            <div className="flex-1" onKeyDown={handleKeyDown}>
              <SystemSearch
                label={t('to')}
                value={toSystem}
                onChange={setToSystem}
                placeholder={t('destPlaceholder')}
              />
            </div>
          </div>

          {/* Profile Selection */}
          <div className="grid sm:grid-cols-3 gap-4">
            <Select
              label={t('routeProfile')}
              value={profile}
              onChange={(e) => setProfile(e.target.value as RouteProfile)}
              options={profileOptions}
            />

            <div className="flex items-end">
              <Toggle
                checked={includeBridges}
                onChange={setIncludeBridges}
                label={t('includeBridges')}
              />
            </div>

            <div className="flex items-end">
              <Toggle
                checked={includeThera}
                onChange={setIncludeThera}
                label={t('includeThera')}
              />
            </div>
          </div>

          {/* Search Button */}
          <Button
            onClick={handleSearch}
            disabled={!fromSystem || !toSystem || isLoading}
            loading={isLoading}
            className="w-full sm:w-auto"
          >
            <Route className="mr-2 h-4 w-4" />
            {t('calculateRoute')}
          </Button>
        </div>
      </Card>

      {/* Error State */}
      {error && (
        <ErrorMessage
          title={t('routeFailed')}
          message={getUserFriendlyError(error)}
          onRetry={handleSearch}
        />
      )}

      {/* Results */}
      {route && <RouteResult route={route} />}

      {/* Empty State */}
      {!route && !isLoading && !error && (
        <Card className="text-center py-12">
          <Route className="h-12 w-12 text-text-secondary mx-auto mb-4" />
          <p className="text-text-secondary">
            {t('emptyState')}
          </p>
        </Card>
      )}
    </div>
  );
}

export default function RoutePage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-text-secondary" />
        </div>
      }
    >
      <RoutePageContent />
    </Suspense>
  );
}
