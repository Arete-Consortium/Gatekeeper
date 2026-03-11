'use client';

import { memo, useState, useMemo, useCallback } from 'react';
import { Card } from '@/components/ui';
import { cn, formatIsk } from '@/lib/utils';
import { ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react';
import type { MarketTickerItem } from '@/lib/types';

type SortKey = 'name' | 'price' | 'change' | 'volume' | 'region';
type SortDir = 'asc' | 'desc';

interface MarketTickerProps {
  items: MarketTickerItem[];
}

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
 * Get CSS class for price change direction
 */
function getPriceChangeClass(pct: number): string {
  if (pct > 0) return 'text-risk-green';
  if (pct < 0) return 'text-risk-red';
  return 'text-text-secondary';
}

/**
 * Format price change with sign
 */
function formatPriceChange(pct: number): string {
  const sign = pct > 0 ? '+' : '';
  return `${sign}${pct.toFixed(2)}%`;
}

/**
 * Memoized table row for performance
 */
const TickerRow = memo(function TickerRow({
  item,
}: {
  item: MarketTickerItem;
}) {
  const changeClass = getPriceChangeClass(item.price_change_pct);

  return (
    <>
      {/* Desktop row (sm+) */}
      <div
        className="hidden sm:grid grid-cols-12 gap-2 sm:gap-4 px-3 sm:px-4 py-3 border-t border-border hover:bg-card-hover transition-colors items-center"
        role="row"
      >
        <div className="col-span-3 font-medium text-text truncate" role="cell">
          {item.type_name}
        </div>
        <div className="col-span-2 text-text-secondary text-sm truncate" role="cell">
          {item.region_name}
        </div>
        <div className="col-span-2 text-right font-mono text-sm text-text" role="cell">
          {formatIsk(item.average_price)}
        </div>
        <div className={cn('col-span-2 text-right font-mono text-sm font-medium', changeClass)} role="cell">
          {formatPriceChange(item.price_change_pct)}
        </div>
        <div className="col-span-1 text-right text-sm text-text-secondary font-mono" role="cell">
          {formatVolume(item.volume)}
        </div>
        <div className="col-span-2 text-right text-xs text-text-secondary" role="cell">
          {item.date}
        </div>
      </div>

      {/* Mobile card (<sm) */}
      <div
        className="sm:hidden border-t border-border px-3 py-3 hover:bg-card-hover transition-colors"
        role="row"
      >
        <div className="flex items-center justify-between">
          <span className="font-medium text-text truncate">{item.type_name}</span>
          <span className={cn('font-mono text-sm font-medium', changeClass)}>
            {formatPriceChange(item.price_change_pct)}
          </span>
        </div>
        <div className="flex items-center justify-between mt-1">
          <span className="text-xs text-text-secondary">{item.region_name}</span>
          <span className="font-mono text-sm text-text">
            {formatIsk(item.average_price)}
          </span>
        </div>
        <div className="flex items-center justify-between mt-1">
          <span className="text-xs text-text-secondary">Vol: {formatVolume(item.volume)}</span>
          <span className="text-xs text-text-secondary">{item.date}</span>
        </div>
      </div>
    </>
  );
});

function SortHeader({
  label,
  sortKey,
  col,
  currentKey,
  currentDir,
  onSort,
  align,
}: {
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
          currentDir === 'asc' ? (
            <ArrowUp className="h-3 w-3" />
          ) : (
            <ArrowDown className="h-3 w-3" />
          )
        ) : (
          <ArrowUpDown className="h-3 w-3 opacity-30" />
        )}
      </button>
    </div>
  );
}

export function MarketTicker({ items }: MarketTickerProps) {
  const [sortKey, setSortKey] = useState<SortKey>('name');
  const [sortDir, setSortDir] = useState<SortDir>('asc');
  const [search, setSearch] = useState('');

  const handleSort = useCallback(
    (key: SortKey) => {
      if (sortKey === key) {
        setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
      } else {
        setSortKey(key);
        setSortDir(key === 'name' ? 'asc' : 'desc');
      }
    },
    [sortKey]
  );

  const filteredItems = useMemo(() => {
    let list = items;
    if (search) {
      const lowerSearch = search.toLowerCase();
      list = list.filter(
        (i) =>
          i.type_name.toLowerCase().includes(lowerSearch) ||
          i.region_name.toLowerCase().includes(lowerSearch)
      );
    }
    const dir = sortDir === 'asc' ? 1 : -1;
    return [...list].sort((a, b) => {
      switch (sortKey) {
        case 'name':
          return a.type_name.localeCompare(b.type_name) * dir;
        case 'price':
          return (a.average_price - b.average_price) * dir;
        case 'change':
          return (a.price_change_pct - b.price_change_pct) * dir;
        case 'volume':
          return (a.volume - b.volume) * dir;
        case 'region':
          return a.region_name.localeCompare(b.region_name) * dir;
        default:
          return 0;
      }
    });
  }, [items, search, sortKey, sortDir]);

  if (items.length === 0) {
    return (
      <Card className="text-center py-12">
        <p className="text-text-secondary">
          No market data available. ESI may be experiencing issues.
        </p>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Search filter */}
      <input
        type="text"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="Filter items or regions..."
        className="w-full sm:w-64 px-3 py-2 bg-card border border-border rounded-lg text-sm text-text placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary"
        aria-label="Filter market ticker"
      />

      {/* Table */}
      <div
        className="border border-border rounded-lg overflow-hidden"
        role="table"
        aria-label="Market ticker prices"
      >
        {/* Header */}
        <div
          className="hidden sm:grid grid-cols-12 gap-2 sm:gap-4 px-3 sm:px-4 py-3 bg-card text-xs text-text-secondary uppercase font-semibold"
          role="row"
        >
          <SortHeader
            label="Item"
            sortKey="name"
            col="col-span-3"
            currentKey={sortKey}
            currentDir={sortDir}
            onSort={handleSort}
          />
          <SortHeader
            label="Region"
            sortKey="region"
            col="col-span-2"
            currentKey={sortKey}
            currentDir={sortDir}
            onSort={handleSort}
          />
          <SortHeader
            label="Avg Price"
            sortKey="price"
            col="col-span-2 text-right"
            currentKey={sortKey}
            currentDir={sortDir}
            onSort={handleSort}
            align="right"
          />
          <SortHeader
            label="Change"
            sortKey="change"
            col="col-span-2 text-right"
            currentKey={sortKey}
            currentDir={sortDir}
            onSort={handleSort}
            align="right"
          />
          <SortHeader
            label="Vol"
            sortKey="volume"
            col="col-span-1 text-right"
            currentKey={sortKey}
            currentDir={sortDir}
            onSort={handleSort}
            align="right"
          />
          <div className="col-span-2 text-right" role="columnheader">
            Date
          </div>
        </div>

        {/* Body */}
        {filteredItems.map((item) => (
          <TickerRow
            key={`${item.type_id}-${item.region_id}`}
            item={item}
          />
        ))}

        {filteredItems.length === 0 && (
          <div className="px-4 py-8 text-center text-text-secondary text-sm">
            No items match your filter.
          </div>
        )}
      </div>
    </div>
  );
}
