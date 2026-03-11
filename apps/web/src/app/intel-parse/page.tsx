'use client';

import { useState, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { Card, Button } from '@/components/ui';
import { ErrorMessage, getUserFriendlyError } from '@/components/ui';
import { GatekeeperAPI } from '@/lib/api';
import type { IntelParseResponse, ParsedSystem } from '@/lib/types';
import { MessageSquareText, MapPin, Loader2, AlertTriangle, CheckCircle, HelpCircle } from 'lucide-react';

function StatusIndicator({ status }: { status: ParsedSystem['status'] }) {
  switch (status) {
    case 'clear':
      return (
        <span className="inline-flex items-center gap-1 text-xs font-medium text-green-400">
          <CheckCircle className="h-3 w-3" />
          Clear
        </span>
      );
    case 'hostile':
      return (
        <span className="inline-flex items-center gap-1 text-xs font-medium text-red-400">
          <AlertTriangle className="h-3 w-3" />
          Hostile
        </span>
      );
    default:
      return (
        <span className="inline-flex items-center gap-1 text-xs font-medium text-gray-400">
          <HelpCircle className="h-3 w-3" />
          Unknown
        </span>
      );
  }
}

export default function IntelParsePage() {
  const router = useRouter();
  const [rawText, setRawText] = useState('');
  const [result, setResult] = useState<IntelParseResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const handleParse = useCallback(async () => {
    if (!rawText.trim()) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await GatekeeperAPI.parseIntel(rawText);
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Parse failed'));
    } finally {
      setIsLoading(false);
    }
  }, [rawText]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        handleParse();
      }
    },
    [handleParse]
  );

  const handleHighlightOnMap = useCallback(() => {
    if (!result || result.systems.length === 0) return;
    const systemNames = result.systems.map((s) => s.system_name).join(',');
    router.push(`/map?highlight=${encodeURIComponent(systemNames)}`);
  }, [result, router]);

  const stats = useMemo(() => {
    if (!result) return null;
    return {
      total: result.systems.length,
      clear: result.systems.filter((s) => s.status === 'clear').length,
      hostile: result.systems.filter((s) => s.status === 'hostile').length,
      unknown: result.systems.filter((s) => s.status === 'unknown').length,
      totalHostiles: result.systems.reduce((sum, s) => sum + s.hostile_count, 0),
    };
  }, [result]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-text">Intel Parser</h1>
        <p className="text-text-secondary mt-1">
          Paste intel or local chat to extract system names and highlight them on the map
        </p>
      </div>

      {/* Input */}
      <Card>
        <div className="space-y-3">
          <textarea
            value={rawText}
            onChange={(e) => setRawText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              'Paste intel/local chat here...\n\nSupported formats:\n  [timestamp] Player > Jita clear\n  HED-GP +5\n  EC-P8R hostile 3\n  1DQ1-A red\n  Amarr nv'
            }
            className="w-full h-48 px-3 py-2 bg-background border border-border rounded-lg text-sm text-text placeholder:text-text-secondary focus:outline-none focus:ring-1 focus:ring-primary resize-y font-mono"
            data-testid="intel-textarea"
          />
          <div className="flex items-center justify-between">
            <span className="text-xs text-text-secondary">
              {rawText.trim()
                ? `${rawText.trim().split('\n').filter((l) => l.trim()).length} lines`
                : 'Ctrl+Enter to parse'}
            </span>
            <Button onClick={handleParse} disabled={!rawText.trim() || isLoading} loading={isLoading}>
              <MessageSquareText className="mr-2 h-4 w-4" />
              Parse
            </Button>
          </div>
        </div>
      </Card>

      {/* Error */}
      {error && (
        <ErrorMessage title="Parse failed" message={getUserFriendlyError(error)} onRetry={handleParse} />
      )}

      {/* Results */}
      {result && (
        <div className="space-y-4">
          {/* Summary */}
          {stats && (
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
              <Card className="text-center">
                <div className="text-xs text-text-secondary uppercase mb-1">Systems</div>
                <div className="text-xl font-bold text-text">{stats.total}</div>
              </Card>
              <Card className="text-center">
                <div className="text-xs text-text-secondary uppercase mb-1">Clear</div>
                <div className="text-xl font-bold text-green-400">{stats.clear}</div>
              </Card>
              <Card className="text-center">
                <div className="text-xs text-text-secondary uppercase mb-1">Hostile</div>
                <div className="text-xl font-bold text-red-400">{stats.hostile}</div>
              </Card>
              <Card className="text-center">
                <div className="text-xs text-text-secondary uppercase mb-1">Unknown</div>
                <div className="text-xl font-bold text-gray-400">{stats.unknown}</div>
              </Card>
              <Card className="text-center">
                <div className="text-xs text-text-secondary uppercase mb-1">Hostiles</div>
                <div className="text-xl font-bold text-red-400">{stats.totalHostiles}</div>
              </Card>
            </div>
          )}

          {/* Highlight on Map button */}
          {result.systems.length > 0 && (
            <Button onClick={handleHighlightOnMap} className="w-full sm:w-auto">
              <MapPin className="mr-2 h-4 w-4" />
              Highlight on Map ({result.systems.length} systems)
            </Button>
          )}

          {/* Systems table */}
          {result.systems.length > 0 && (
            <section aria-labelledby="parsed-systems-heading">
              <h2
                id="parsed-systems-heading"
                className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-3"
              >
                Parsed Systems
              </h2>
              <div
                className="border border-border rounded-lg overflow-hidden"
                role="table"
                aria-label="Parsed intel systems"
              >
                {/* Desktop header */}
                <div className="hidden sm:grid grid-cols-12 gap-2 px-3 py-2.5 bg-card text-xs text-text-secondary uppercase font-semibold">
                  <div className="col-span-3" role="columnheader">
                    System
                  </div>
                  <div className="col-span-2" role="columnheader">
                    Status
                  </div>
                  <div className="col-span-2 text-right" role="columnheader">
                    Hostiles
                  </div>
                  <div className="col-span-5" role="columnheader">
                    Source
                  </div>
                </div>

                {/* Rows */}
                {result.systems.map((system) => (
                  <SystemRow key={system.system_id} system={system} />
                ))}
              </div>
            </section>
          )}

          {/* Unknown lines */}
          {result.unknown_lines.length > 0 && (
            <div className="bg-card border border-border rounded-lg px-3 py-3">
              <div className="text-xs font-medium text-text-secondary uppercase mb-2">
                Unrecognized Lines ({result.unknown_lines.length})
              </div>
              <div className="space-y-1">
                {result.unknown_lines.map((line, i) => (
                  <div key={i} className="text-xs text-text-secondary font-mono truncate" title={line}>
                    {line}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Empty State */}
      {!result && !isLoading && !error && (
        <Card className="text-center py-12">
          <MessageSquareText className="h-12 w-12 text-text-secondary mx-auto mb-4" />
          <p className="text-text-secondary">
            Paste intel channel or local chat to identify systems and their status
          </p>
        </Card>
      )}
    </div>
  );
}

function SystemRow({ system }: { system: ParsedSystem }) {
  return (
    <>
      {/* Desktop row */}
      <div
        className="hidden sm:grid grid-cols-12 gap-2 px-3 py-2.5 border-t border-border hover:bg-card-hover transition-colors items-center text-sm"
        role="row"
      >
        <div className="col-span-3 font-medium text-text" role="cell">
          {system.system_name}
        </div>
        <div className="col-span-2" role="cell">
          <StatusIndicator status={system.status} />
        </div>
        <div className="col-span-2 text-right" role="cell">
          {system.hostile_count > 0 ? (
            <span className="text-red-400 font-medium">{system.hostile_count}</span>
          ) : (
            <span className="text-text-secondary">-</span>
          )}
        </div>
        <div className="col-span-5 text-text-secondary text-xs font-mono truncate" role="cell" title={system.mentioned_at}>
          {system.mentioned_at}
        </div>
      </div>

      {/* Mobile card */}
      <div className="sm:hidden border-t border-border px-3 py-2.5 hover:bg-card-hover transition-colors">
        <div className="flex items-center justify-between">
          <span className="font-medium text-text text-sm">{system.system_name}</span>
          <StatusIndicator status={system.status} />
        </div>
        {system.hostile_count > 0 && (
          <div className="text-xs text-red-400 mt-0.5">{system.hostile_count} hostiles</div>
        )}
        <div className="text-xs text-text-secondary font-mono mt-1 truncate">{system.mentioned_at}</div>
      </div>
    </>
  );
}
