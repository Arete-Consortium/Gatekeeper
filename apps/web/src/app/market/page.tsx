'use client';

import { useQuery } from '@tanstack/react-query';
import { GatekeeperAPI } from '@/lib/api';
import { MarketTicker } from '@/components/market';
import { TrendingUp } from 'lucide-react';
import { Card } from '@/components/ui';
import { ErrorMessage, SkeletonTable, getUserFriendlyError } from '@/components/ui';

export default function MarketPage() {
  const {
    data: tickerData,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['market-ticker'],
    queryFn: () => GatekeeperAPI.getMarketTicker(),
    refetchInterval: 5 * 60 * 1000, // 5 minutes
    staleTime: 4 * 60 * 1000,
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-text">Market Ticker</h1>
        <p className="text-text-secondary mt-1">
          Real-time prices for commonly traded items across major trade hubs
        </p>
      </div>

      {/* Stats summary */}
      {tickerData && tickerData.items.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4" role="region" aria-label="Market summary">
          <Card className="text-center">
            <div className="flex items-center justify-center gap-2 mb-1">
              <TrendingUp className="h-4 w-4 text-primary" aria-hidden="true" />
              <span className="text-xs text-text-secondary uppercase">Items</span>
            </div>
            <span className="text-2xl font-bold text-text">
              {tickerData.item_count}
            </span>
          </Card>
          <Card className="text-center">
            <div className="flex items-center justify-center gap-2 mb-1">
              <span className="text-xs text-text-secondary uppercase">Gainers</span>
            </div>
            <span className="text-2xl font-bold text-risk-green">
              {tickerData.items.filter((i) => i.price_change_pct > 0).length}
            </span>
          </Card>
          <Card className="text-center">
            <div className="flex items-center justify-center gap-2 mb-1">
              <span className="text-xs text-text-secondary uppercase">Losers</span>
            </div>
            <span className="text-2xl font-bold text-risk-red">
              {tickerData.items.filter((i) => i.price_change_pct < 0).length}
            </span>
          </Card>
        </div>
      )}

      {/* Content */}
      <section aria-labelledby="market-ticker-heading">
        <h2
          id="market-ticker-heading"
          className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-4"
        >
          Price Ticker
        </h2>

        {isLoading ? (
          <SkeletonTable rows={10} columns={6} aria-label="Loading market data" />
        ) : error ? (
          <ErrorMessage
            title="Unable to load market data"
            message={getUserFriendlyError(error)}
            onRetry={() => refetch()}
          />
        ) : tickerData ? (
          <MarketTicker items={tickerData.items} />
        ) : null}
      </section>
    </div>
  );
}
