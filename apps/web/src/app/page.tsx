'use client';

import Link from 'next/link';
import { useHotSystems, useRouteHistory } from '@/hooks';
import { StatusIndicator } from '@/components/layout';
import { Card, CardTitle, CardDescription, Button, SkeletonCard, ErrorMessage, getUserFriendlyError } from '@/components/ui';
import { SystemCard } from '@/components/system';
import { formatRelativeTime, ROUTE_PROFILES } from '@/lib/utils';
import {
  Route,
  Wrench,
  Bell,
  Radar,
  ArrowRight,
  Zap,
} from 'lucide-react';

export default function DashboardPage() {
  const { data: hotSystems, isLoading: loadingHot, error: hotError, refetch: refetchHot } = useHotSystems(24, 5);
  const { data: historyData, isLoading: loadingHistory } = useRouteHistory(5);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="text-center py-8">
        <h1 className="text-3xl font-bold text-text">EVE Gatekeeper</h1>
        <p className="text-text-secondary mt-2">Intel & Route Planning</p>
        <div className="mt-4 flex justify-center">
          <StatusIndicator />
        </div>
      </div>

      {/* Quick Route Button */}
      <div className="flex justify-center">
        <Link href="/route">
          <Button size="lg" className="glow-primary">
            <Route className="mr-2 h-5 w-5" />
            Plan Route
          </Button>
        </Link>
      </div>

      {/* Hot Systems */}
      <section aria-labelledby="hot-systems-heading">
        <div className="flex items-center justify-between mb-4">
          <h2 id="hot-systems-heading" className="text-xs font-semibold text-text-secondary uppercase tracking-wide">
            Hot Systems (24h)
          </h2>
          <Link
            href="/intel"
            className="text-xs text-primary hover:text-primary-hover focus:outline-none focus:underline"
            aria-label="View all hot systems"
          >
            View All
          </Link>
        </div>
        {loadingHot ? (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3" aria-busy="true" aria-label="Loading hot systems">
            {[...Array(3)].map((_, i) => (
              <SkeletonCard key={i} lines={2} />
            ))}
          </div>
        ) : hotError ? (
          <ErrorMessage
            title="Unable to load hot systems"
            message={getUserFriendlyError(hotError)}
            onRetry={() => refetchHot()}
          />
        ) : hotSystems && hotSystems.length > 0 ? (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {hotSystems.map((system) => (
              <SystemCard
                key={system.system_id}
                systemName={system.system_name}
                security={system.security}
                riskColor="red"
                kills={system.recent_kills}
                pods={system.recent_pods}
              />
            ))}
          </div>
        ) : (
          <Card className="text-center py-8">
            <p className="text-text-secondary">No hot systems detected in the last 24 hours. Space is calm for now.</p>
          </Card>
        )}
      </section>

      {/* Recent Routes */}
      {historyData && historyData.items && historyData.items.length > 0 && (
        <section aria-labelledby="recent-routes-heading">
          <h2 id="recent-routes-heading" className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-4">
            Recent Routes
          </h2>
          <div className="grid gap-3 sm:grid-cols-2">
            {historyData.items.map((entry, index) => (
              <Link
                key={`${entry.from_system}-${entry.to_system}-${index}`}
                href={`/route?from=${encodeURIComponent(entry.from_system)}&to=${encodeURIComponent(entry.to_system)}`}
                aria-label={`Route from ${entry.from_system} to ${entry.to_system}, ${entry.jumps} jumps`}
              >
                <Card hover className="h-full">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-medium text-text">
                      {entry.from_system}
                    </span>
                    <ArrowRight className="h-4 w-4 text-text-secondary flex-shrink-0" aria-hidden="true" />
                    <span className="font-medium text-text">
                      {entry.to_system}
                    </span>
                  </div>
                  <div className="flex justify-between mt-2 text-sm text-text-secondary">
                    <span>{entry.jumps} jumps</span>
                    <span>{formatRelativeTime(entry.timestamp)}</span>
                  </div>
                </Card>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* Route Profiles */}
      <section aria-labelledby="route-profiles-heading">
        <h2 id="route-profiles-heading" className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-4">
          Route Profiles
        </h2>
        <div className="grid gap-3 grid-cols-1 sm:grid-cols-3">
          {Object.entries(ROUTE_PROFILES).map(([key, profile]) => (
            <Link key={key} href={`/route?profile=${key}`} aria-label={`${profile.label} route profile: ${profile.description}`}>
              <Card
                hover
                className={`border-l-4 h-full ${profile.borderColor}`}
              >
                <CardTitle className={profile.color}>{profile.label}</CardTitle>
                <CardDescription>{profile.description}</CardDescription>
              </Card>
            </Link>
          ))}
        </div>
      </section>

      {/* Tools Grid */}
      <section aria-labelledby="tools-heading">
        <h2 id="tools-heading" className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-4">
          Tools
        </h2>
        <nav aria-label="Tools navigation" className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
          <Link href="/fitting" aria-label="Fitting Analyzer - Parse EFT fittings for travel advice">
            <Card hover className="h-full">
              <div className="flex items-center gap-3 mb-2">
                <div className="p-2 bg-primary/20 rounded-lg" aria-hidden="true">
                  <Wrench className="h-5 w-5 text-primary" />
                </div>
                <CardTitle className="text-base">Fitting Analyzer</CardTitle>
              </div>
              <CardDescription>
                Parse EFT fittings for travel advice
              </CardDescription>
            </Card>
          </Link>

          <Link href="/alerts" aria-label="Kill Alerts - Discord and Slack kill notifications">
            <Card hover className="h-full">
              <div className="flex items-center gap-3 mb-2">
                <div className="p-2 bg-risk-orange/20 rounded-lg" aria-hidden="true">
                  <Bell className="h-5 w-5 text-risk-orange" />
                </div>
                <CardTitle className="text-base">Kill Alerts</CardTitle>
                <span className="ml-auto inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-primary/20 text-primary">
                  <Zap className="h-2.5 w-2.5" />
                  PRO
                </span>
              </div>
              <CardDescription>
                Discord & Slack kill notifications
              </CardDescription>
            </Card>
          </Link>

          <Link href="/intel" aria-label="Intel - Hot systems and kill activity">
            <Card hover className="h-full">
              <div className="flex items-center gap-3 mb-2">
                <div className="p-2 bg-risk-red/20 rounded-lg" aria-hidden="true">
                  <Radar className="h-5 w-5 text-risk-red" />
                </div>
                <CardTitle className="text-base">Intel</CardTitle>
              </div>
              <CardDescription>
                Hot systems and kill activity
              </CardDescription>
            </Card>
          </Link>
        </nav>
      </section>
    </div>
  );
}
