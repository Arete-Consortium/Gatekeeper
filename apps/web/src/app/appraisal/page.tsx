'use client';

import { useState, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, Button } from '@/components/ui';
import { ErrorMessage, SkeletonTable, getUserFriendlyError } from '@/components/ui';
import { GatekeeperAPI } from '@/lib/api';
import { MarketTicker } from '@/components/market';
import type { AppraisalResponse, AppraisalItem } from '@/lib/types';
import { Scale, Copy, Check, Loader2, TrendingUp } from 'lucide-react';
import { cn } from '@/lib/utils';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatIsk(value: number): string {
  if (value >= 1e12) return `${(value / 1e12).toFixed(2)}T`;
  if (value >= 1e9) return `${(value / 1e9).toFixed(2)}B`;
  if (value >= 1e6) return `${(value / 1e6).toFixed(2)}M`;
  if (value >= 1e3) return `${(value / 1e3).toFixed(1)}K`;
  return value.toFixed(2);
}

function formatQuantity(n: number): string {
  return n.toLocaleString();
}

// ---------------------------------------------------------------------------
// Tab types
// ---------------------------------------------------------------------------

type Tab = 'appraisal' | 'market';

const tabs: { key: Tab; label: string; icon: React.ElementType }[] = [
  { key: 'appraisal', label: 'Appraisal', icon: Scale },
  { key: 'market', label: 'Market', icon: TrendingUp },
];

// ---------------------------------------------------------------------------
// Appraisal content
// ---------------------------------------------------------------------------

function AppraisalContent() {
  const [rawText, setRawText] = useState('');
  const [result, setResult] = useState<AppraisalResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [copiedField, setCopiedField] = useState<string | null>(null);

  const handleAppraise = useCallback(async () => {
    if (!rawText.trim()) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await GatekeeperAPI.appraise(rawText);
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Appraisal failed'));
    } finally {
      setIsLoading(false);
    }
  }, [rawText]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      handleAppraise();
    }
  }, [handleAppraise]);

  const copyToClipboard = useCallback((text: string, field: string) => {
    navigator.clipboard.writeText(text);
    setCopiedField(field);
    setTimeout(() => setCopiedField(null), 1500);
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <p className="text-text-secondary mt-1">
          Paste items from EVE to get Jita 4-4 market prices
        </p>
      </div>

      {/* Input */}
      <Card>
        <div className="space-y-3">
          <textarea
            value={rawText}
            onChange={(e) => setRawText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={"Paste items here...\n\nSupported formats:\n  Tritanium\t1,000\n  1000 Tritanium\n  Tritanium x1000\n  Tritanium"}
            className="w-full h-40 px-3 py-2 bg-background border border-border rounded-lg text-sm text-text placeholder:text-text-secondary focus:outline-none focus:ring-1 focus:ring-primary resize-y font-mono"
          />
          <div className="flex items-center justify-between">
            <span className="text-xs text-text-secondary">
              {rawText.trim() ? `${rawText.trim().split('\n').filter(l => l.trim()).length} lines` : 'Ctrl+Enter to appraise'}
            </span>
            <Button
              onClick={handleAppraise}
              disabled={!rawText.trim() || isLoading}
              loading={isLoading}
            >
              <Scale className="mr-2 h-4 w-4" />
              Appraise
            </Button>
          </div>
        </div>
      </Card>

      {/* Error */}
      {error && (
        <ErrorMessage
          title="Appraisal failed"
          message={getUserFriendlyError(error)}
          onRetry={handleAppraise}
        />
      )}

      {/* Results */}
      {result && (
        <div className="space-y-4">
          {/* Totals */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
            <Card className="text-center">
              <div className="text-xs text-text-secondary uppercase mb-1">Sell Value</div>
              <div className="text-xl font-bold text-green-400">{formatIsk(result.total_sell)}</div>
              <button
                onClick={() => copyToClipboard(result.total_sell.toFixed(2), 'sell')}
                className="text-xs text-text-secondary hover:text-text mt-1 inline-flex items-center gap-1"
              >
                {copiedField === 'sell' ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                {copiedField === 'sell' ? 'Copied' : 'Copy'}
              </button>
            </Card>
            <Card className="text-center">
              <div className="text-xs text-text-secondary uppercase mb-1">Buy Value</div>
              <div className="text-xl font-bold text-blue-400">{formatIsk(result.total_buy)}</div>
              <button
                onClick={() => copyToClipboard(result.total_buy.toFixed(2), 'buy')}
                className="text-xs text-text-secondary hover:text-text mt-1 inline-flex items-center gap-1"
              >
                {copiedField === 'buy' ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                {copiedField === 'buy' ? 'Copied' : 'Copy'}
              </button>
            </Card>
            <Card className="text-center sm:col-span-1 col-span-2">
              <div className="text-xs text-text-secondary uppercase mb-1">Items</div>
              <div className="text-xl font-bold text-text">{result.item_count}</div>
              {result.unknown_items.length > 0 && (
                <div className="text-xs text-risk-orange mt-1">
                  {result.unknown_items.length} unresolved
                </div>
              )}
            </Card>
          </div>

          {/* Unknown items warning */}
          {result.unknown_items.length > 0 && (
            <div className="bg-risk-orange/10 border border-risk-orange/30 rounded-lg px-3 py-2">
              <div className="text-xs font-medium text-risk-orange mb-1">Could not resolve:</div>
              <div className="text-xs text-text-secondary">
                {result.unknown_items.join(', ')}
              </div>
            </div>
          )}

          {/* Items table */}
          {result.items.length > 0 && (
            <div className="border border-border rounded-lg overflow-hidden">
              {/* Desktop header */}
              <div className="hidden sm:grid grid-cols-12 gap-2 px-3 py-2.5 bg-card text-xs text-text-secondary uppercase font-semibold">
                <div className="col-span-4">Item</div>
                <div className="col-span-2 text-right">Qty</div>
                <div className="col-span-3 text-right">Sell Price</div>
                <div className="col-span-3 text-right">Total</div>
              </div>

              {/* Rows */}
              {result.items.map((item) => (
                <ItemRow key={item.type_id} item={item} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Empty State */}
      {!result && !isLoading && !error && (
        <Card className="text-center py-12">
          <Scale className="h-12 w-12 text-text-secondary mx-auto mb-4" />
          <p className="text-text-secondary">
            Paste items from your inventory, contracts, or cargo to get Jita prices
          </p>
        </Card>
      )}
    </div>
  );
}

function ItemRow({ item }: { item: AppraisalItem }) {
  return (
    <>
      {/* Desktop row */}
      <div className="hidden sm:grid grid-cols-12 gap-2 px-3 py-2.5 border-t border-border hover:bg-card-hover transition-colors items-center text-sm">
        <div className="col-span-4 text-text font-medium truncate" title={item.name}>
          {item.name}
        </div>
        <div className="col-span-2 text-right text-text-secondary font-mono">
          {formatQuantity(item.quantity)}
        </div>
        <div className="col-span-3 text-right text-text-secondary font-mono">
          {formatIsk(item.sell_price)}
        </div>
        <div className="col-span-3 text-right text-green-400 font-mono font-medium">
          {formatIsk(item.sell_total)}
        </div>
      </div>

      {/* Mobile card */}
      <div className="sm:hidden border-t border-border px-3 py-2.5 hover:bg-card-hover transition-colors">
        <div className="text-sm text-text font-medium mb-1">{item.name}</div>
        <div className="flex items-center justify-between text-xs font-mono">
          <span className="text-text-secondary">x{formatQuantity(item.quantity)}</span>
          <span className="text-text-secondary">{formatIsk(item.buy_price)} / {formatIsk(item.sell_price)}</span>
          <span className="text-green-400 font-medium">{formatIsk(item.sell_total)}</span>
        </div>
      </div>
    </>
  );
}

// ---------------------------------------------------------------------------
// Market content
// ---------------------------------------------------------------------------

function MarketContent() {
  const {
    data: tickerData,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['market-ticker'],
    queryFn: () => GatekeeperAPI.getMarketTicker(),
    refetchInterval: 5 * 60 * 1000,
    staleTime: 4 * 60 * 1000,
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
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

// ---------------------------------------------------------------------------
// Unified page
// ---------------------------------------------------------------------------

export default function AppraisalPage() {
  const [activeTab, setActiveTab] = useState<Tab>('appraisal');

  return (
    <div className="space-y-6">
      {/* Page title */}
      <h1 className="text-2xl font-bold text-text">
        {activeTab === 'appraisal' ? 'Appraisal' : 'Market Ticker'}
      </h1>

      {/* Tab bar */}
      <div className="flex border-b border-border">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.key;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={cn(
                'flex items-center gap-2 px-4 py-2.5 text-sm font-medium transition-colors -mb-px',
                isActive
                  ? 'text-primary border-b-2 border-primary'
                  : 'text-text-secondary hover:text-text'
              )}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab content */}
      {activeTab === 'appraisal' ? <AppraisalContent /> : <MarketContent />}
    </div>
  );
}
