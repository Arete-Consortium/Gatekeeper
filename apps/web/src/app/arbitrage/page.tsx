'use client';

import { useState, useMemo, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { GatekeeperAPI } from '@/lib/api';
import { Card, ErrorMessage, SkeletonTable, getUserFriendlyError } from '@/components/ui';
import { cn, formatIsk } from '@/lib/utils';
import { ArrowLeftRight, Search, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import type {
  ArbitrageCompareResponse,
  PopularItem,
  HubPriceData,
  ArbitrageOpportunity,
} from '@/lib/types';

/**
 * Format volume with K/M/B abbreviations
 */
function formatVolume(vol: number): string {
  if (vol >= 1_000_000_000) return `${(vol / 1_000_000_000).toFixed(1)}B`;
  if (vol >= 1_000_000) return `${(vol / 1_000_000).toFixed(1)}M`;
  if (vol >= 1_000) return `${(vol / 1_000).toFixed(1)}K`;
  return vol.toLocaleString();
}

/**
 * Hub price comparison table row
 */
function HubRow({ hub, bestSellHub, bestBuyHub }: {
  hub: HubPriceData;
  bestSellHub: number;
  bestBuyHub: number;
}) {
  const isBestSell = hub.system_id === bestSellHub && hub.best_sell > 0;
  const isBestBuy = hub.system_id === bestBuyHub && hub.best_buy > 0;

  return (
    <tr className="border-b border-border hover:bg-card-hover transition-colors">
      <td className="px-4 py-3 font-medium text-text">{hub.system_name}</td>
      <td className={cn('px-4 py-3 text-right font-mono text-sm', isBestBuy ? 'text-risk-green font-bold' : 'text-text')}>
        {hub.best_buy > 0 ? formatIsk(hub.best_buy) : <span className="text-text-secondary">--</span>}
      </td>
      <td className={cn('px-4 py-3 text-right font-mono text-sm', isBestSell ? 'text-risk-green font-bold' : 'text-text')}>
        {hub.best_sell > 0 ? formatIsk(hub.best_sell) : <span className="text-text-secondary">--</span>}
      </td>
      <td className={cn(
        'px-4 py-3 text-right font-mono text-sm',
        hub.spread > 10 ? 'text-risk-green' : hub.spread > 0 ? 'text-risk-yellow' : 'text-text-secondary'
      )}>
        {hub.spread > 0 ? `${hub.spread.toFixed(1)}%` : '--'}
      </td>
      <td className="px-4 py-3 text-right text-sm text-text-secondary">
        {formatVolume(hub.buy_volume + hub.sell_volume)}
      </td>
    </tr>
  );
}

/**
 * Arbitrage opportunity card
 */
function OpportunityCard({ opp }: { opp: ArbitrageOpportunity }) {
  return (
    <Card className="flex flex-col sm:flex-row items-start sm:items-center gap-3 sm:gap-6">
      <div className="flex items-center gap-3 min-w-0">
        <div className="text-sm">
          <span className="text-text-secondary">Buy at </span>
          <span className="text-text font-medium">{opp.buy_hub}</span>
          <span className="text-text-secondary ml-1 font-mono text-xs">({formatIsk(opp.buy_price)})</span>
        </div>
        <ArrowLeftRight className="h-4 w-4 text-text-secondary shrink-0" />
        <div className="text-sm">
          <span className="text-text-secondary">Sell at </span>
          <span className="text-text font-medium">{opp.sell_hub}</span>
          <span className="text-text-secondary ml-1 font-mono text-xs">({formatIsk(opp.sell_price)})</span>
        </div>
      </div>
      <div className="flex items-center gap-4 ml-auto">
        <div className="text-right">
          <div className="text-xs text-text-secondary">Profit/unit</div>
          <div className="text-sm font-mono font-bold text-risk-green">
            +{formatIsk(opp.profit_per_unit)}
          </div>
        </div>
        <div className="text-right">
          <div className="text-xs text-text-secondary">Margin</div>
          <div className={cn(
            'text-sm font-mono font-bold',
            opp.margin_pct >= 5 ? 'text-risk-green' : opp.margin_pct >= 2 ? 'text-risk-yellow' : 'text-risk-orange'
          )}>
            {opp.margin_pct.toFixed(1)}%
          </div>
        </div>
      </div>
    </Card>
  );
}

export default function ArbitragePage() {
  const [searchInput, setSearchInput] = useState('');
  const [selectedTypeId, setSelectedTypeId] = useState<number | null>(null);
  const [showSuggestions, setShowSuggestions] = useState(false);

  // Fetch popular items for autocomplete
  const { data: popularData } = useQuery({
    queryKey: ['arbitrage-popular'],
    queryFn: () => GatekeeperAPI.getArbitragePopular(),
    staleTime: 60 * 60 * 1000, // 1 hour
  });

  // Fetch arbitrage comparison when a type is selected
  const {
    data: compareData,
    isLoading: isComparing,
    error: compareError,
    refetch,
  } = useQuery({
    queryKey: ['arbitrage-compare', selectedTypeId],
    queryFn: () => GatekeeperAPI.getArbitrageCompare(selectedTypeId!),
    enabled: selectedTypeId !== null,
    staleTime: 4 * 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
  });

  // Filter popular items by search input
  const filteredItems = useMemo(() => {
    if (!popularData?.items) return [];
    if (!searchInput.trim()) return popularData.items;
    const q = searchInput.toLowerCase();
    return popularData.items.filter(
      (item) =>
        item.name.toLowerCase().includes(q) ||
        item.category.toLowerCase().includes(q) ||
        item.type_id.toString().includes(q)
    );
  }, [popularData?.items, searchInput]);

  // Group filtered items by category
  const groupedItems = useMemo(() => {
    const groups: Record<string, PopularItem[]> = {};
    for (const item of filteredItems) {
      if (!groups[item.category]) groups[item.category] = [];
      groups[item.category].push(item);
    }
    return groups;
  }, [filteredItems]);

  const handleSelectItem = useCallback((item: PopularItem) => {
    setSelectedTypeId(item.type_id);
    setSearchInput(item.name);
    setShowSuggestions(false);
  }, []);

  // Find best buy/sell hubs for highlighting
  const bestSellHub = useMemo(() => {
    if (!compareData?.hubs?.length) return 0;
    const sellHubs = compareData.hubs.filter((h) => h.best_sell > 0);
    if (!sellHubs.length) return 0;
    return sellHubs.reduce((a, b) => (a.best_sell < b.best_sell ? a : b)).system_id;
  }, [compareData?.hubs]);

  const bestBuyHub = useMemo(() => {
    if (!compareData?.hubs?.length) return 0;
    const buyHubs = compareData.hubs.filter((h) => h.best_buy > 0);
    if (!buyHubs.length) return 0;
    return buyHubs.reduce((a, b) => (a.best_buy > b.best_buy ? a : b)).system_id;
  }, [compareData?.hubs]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-text">Market Arbitrage</h1>
        <p className="text-text-secondary mt-1">
          Compare prices across EVE trade hubs and find profitable arbitrage opportunities
        </p>
      </div>

      {/* Search */}
      <Card>
        <div className="relative">
          <div className="flex items-center gap-2 px-3">
            <Search className="h-4 w-4 text-text-secondary shrink-0" />
            <input
              type="text"
              placeholder="Search items (e.g. PLEX, Tritanium, Ishtar...)"
              className="w-full bg-transparent py-3 text-text placeholder:text-text-secondary outline-none"
              value={searchInput}
              onChange={(e) => {
                setSearchInput(e.target.value);
                setShowSuggestions(true);
                if (!e.target.value.trim()) {
                  setSelectedTypeId(null);
                }
              }}
              onFocus={() => setShowSuggestions(true)}
            />
          </div>

          {/* Suggestions dropdown */}
          {showSuggestions && filteredItems.length > 0 && (
            <div className="absolute top-full left-0 right-0 z-50 mt-1 max-h-80 overflow-y-auto bg-card border border-border rounded-lg shadow-lg">
              {Object.entries(groupedItems).map(([category, items]) => (
                <div key={category}>
                  <div className="px-3 py-1.5 text-xs font-semibold text-text-secondary uppercase tracking-wide bg-background/50 sticky top-0">
                    {category}
                  </div>
                  {items.map((item) => (
                    <button
                      key={item.type_id}
                      onClick={() => handleSelectItem(item)}
                      className={cn(
                        'w-full text-left px-3 py-2 text-sm hover:bg-card-hover transition-colors flex justify-between items-center',
                        selectedTypeId === item.type_id ? 'bg-primary/10 text-primary' : 'text-text'
                      )}
                    >
                      <span>{item.name}</span>
                      <span className="text-xs text-text-secondary font-mono">{item.type_id}</span>
                    </button>
                  ))}
                </div>
              ))}
            </div>
          )}
        </div>
      </Card>

      {/* Results */}
      {isComparing && <SkeletonTable rows={5} columns={5} aria-label="Loading arbitrage data" />}

      {compareError && (
        <ErrorMessage
          title="Unable to load arbitrage data"
          message={getUserFriendlyError(compareError)}
          onRetry={() => refetch()}
        />
      )}

      {compareData && (
        <>
          {/* Item header */}
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-bold text-text">{compareData.type_name}</h2>
            <span className="text-xs text-text-secondary font-mono">ID: {compareData.type_id}</span>
          </div>

          {/* Hub comparison table */}
          <section aria-labelledby="hub-comparison-heading">
            <h3
              id="hub-comparison-heading"
              className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-3"
            >
              Trade Hub Comparison
            </h3>
            <Card className="overflow-x-auto">
              <table className="w-full text-sm" role="table">
                <thead>
                  <tr className="border-b border-border">
                    <th className="px-4 py-3 text-left text-xs font-semibold text-text-secondary uppercase">Hub</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-text-secondary uppercase">Best Buy</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-text-secondary uppercase">Best Sell</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-text-secondary uppercase">Spread</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-text-secondary uppercase">Volume</th>
                  </tr>
                </thead>
                <tbody>
                  {compareData.hubs.map((hub) => (
                    <HubRow
                      key={hub.system_id}
                      hub={hub}
                      bestSellHub={bestSellHub}
                      bestBuyHub={bestBuyHub}
                    />
                  ))}
                </tbody>
              </table>
            </Card>
          </section>

          {/* Arbitrage opportunities */}
          <section aria-labelledby="arbitrage-heading">
            <h3
              id="arbitrage-heading"
              className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-3"
            >
              Arbitrage Opportunities
            </h3>

            {compareData.opportunities.length > 0 ? (
              <div className="space-y-3">
                {compareData.opportunities.map((opp, idx) => (
                  <OpportunityCard key={`${opp.buy_hub_id}-${opp.sell_hub_id}-${idx}`} opp={opp} />
                ))}
              </div>
            ) : (
              <Card className="text-center py-8">
                <Minus className="h-8 w-8 text-text-secondary mx-auto mb-2" />
                <p className="text-text-secondary">
                  No profitable arbitrage opportunities found for this item across hubs.
                </p>
              </Card>
            )}
          </section>
        </>
      )}

      {/* Empty state */}
      {!selectedTypeId && !isComparing && (
        <Card className="text-center py-12">
          <ArrowLeftRight className="h-12 w-12 text-text-secondary mx-auto mb-4" />
          <h2 className="text-lg font-medium text-text mb-2">Select an Item to Compare</h2>
          <p className="text-text-secondary max-w-md mx-auto">
            Search for an item above to compare prices across Jita, Amarr, Dodixie, Rens, and Hek.
            Profitable arbitrage opportunities will be highlighted automatically.
          </p>
        </Card>
      )}
    </div>
  );
}
