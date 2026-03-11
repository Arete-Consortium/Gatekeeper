'use client';

import { useEffect, useState, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import { Card } from '@/components/ui';
import {
  Shield,
  Activity,
  Database,
  Wifi,
  Globe,
  Zap,
  BarChart3,
  Clock,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Server,
  Users,
  Eye,
} from 'lucide-react';

// ── Admin Gate ──────────────────────────────────────────────────────────────
// Set NEXT_PUBLIC_ADMIN_IDS as comma-separated character IDs in .env.local / Vercel

const ADMIN_IDS = new Set(
  (process.env.NEXT_PUBLIC_ADMIN_IDS || '')
    .split(',')
    .map((id) => parseInt(id.trim(), 10))
    .filter((id) => !isNaN(id))
);

function isAdmin(characterId: number | undefined): boolean {
  if (!characterId) return false;
  return ADMIN_IDS.has(characterId);
}

// ── Types ───────────────────────────────────────────────────────────────────

interface ApiStatus {
  version?: string;
  uptime_seconds?: number;
  database?: { status: string };
  cache?: { status: string; backend?: string };
  systems_loaded?: number;
  debug?: boolean;
  features?: Record<string, boolean>;
}

interface WebSocketHealth {
  zkill_listener?: { connected: boolean; last_kill_at?: string; kills_processed?: number };
  connections?: { total: number; killfeed?: number; map?: number };
}

interface CacheStats {
  hits?: number;
  misses?: number;
  hit_ratio?: number;
  route_cache?: { hits: number; misses: number; hit_ratio: number };
  risk_cache?: { hits: number; misses: number; hit_ratio: number };
}

interface UniverseStatus {
  file_path?: string;
  file_size_mb?: number;
  last_modified?: string;
  systems_count?: number;
  gates_count?: number;
}

interface KillStats {
  total_kills?: number;
  kills_24h?: number;
  kills_1h?: number;
  oldest_kill?: string;
  newest_kill?: string;
}

interface AnalyticsSummary {
  pageviews?: Record<string, number>;
  total?: number;
}

// ── Helpers ─────────────────────────────────────────────────────────────────

function formatUptime(seconds: number): string {
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (d > 0) return `${d}d ${h}h ${m}m`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

function formatBytes(mb: number): string {
  if (mb >= 1024) return `${(mb / 1024).toFixed(1)} GB`;
  return `${mb.toFixed(1)} MB`;
}

function StatusDot({ ok }: { ok: boolean }) {
  return (
    <span className={`inline-block w-2 h-2 rounded-full ${ok ? 'bg-green-500' : 'bg-red-500'}`} />
  );
}

function MetricCard({
  icon: Icon,
  label,
  value,
  sub,
  color = 'text-text',
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  sub?: string;
  color?: string;
}) {
  return (
    <div className="bg-gray-900/50 border border-gray-800 rounded-lg p-3">
      <div className="flex items-center gap-2 mb-1">
        <Icon className="h-3.5 w-3.5 text-text-secondary" />
        <span className="text-[10px] text-text-secondary uppercase tracking-wider font-medium">{label}</span>
      </div>
      <div className={`text-lg font-bold ${color}`}>{value}</div>
      {sub && <div className="text-[10px] text-text-secondary mt-0.5">{sub}</div>}
    </div>
  );
}

// ── Dashboard ───────────────────────────────────────────────────────────────

export default function AdminDashboard() {
  const { user, isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  const [status, setStatus] = useState<ApiStatus | null>(null);
  const [wsHealth, setWsHealth] = useState<WebSocketHealth | null>(null);
  const [cacheStats, setCacheStats] = useState<CacheStats | null>(null);
  const [universeStatus, setUniverseStatus] = useState<UniverseStatus | null>(null);
  const [killStats, setKillStats] = useState<KillStats | null>(null);
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());
  const [refreshing, setRefreshing] = useState(false);

  // Redirect non-admins
  useEffect(() => {
    if (!isLoading && (!isAuthenticated || !isAdmin(user?.character_id))) {
      router.replace('/');
    }
  }, [isLoading, isAuthenticated, user, router]);

  const apiUrl = typeof window !== 'undefined'
    ? localStorage.getItem('gatekeeper_api_url')?.trim() || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    : '';

  const fetchData = useCallback(async () => {
    if (!apiUrl) return;
    setRefreshing(true);

    const fetchJson = async <T,>(endpoint: string): Promise<T | null> => {
      try {
        const res = await fetch(`${apiUrl}${endpoint}`, {
          credentials: 'include',
          signal: AbortSignal.timeout(10000),
        });
        if (!res.ok) return null;
        return await res.json();
      } catch {
        return null;
      }
    };

    const [s, ws, cache, universe, kills, ana] = await Promise.all([
      fetchJson<ApiStatus>('/api/v1/status/'),
      fetchJson<WebSocketHealth>('/api/v1/status/websocket-health'),
      fetchJson<CacheStats>('/api/v1/status/cache/stats'),
      fetchJson<UniverseStatus>('/api/v1/status/universe'),
      fetchJson<KillStats>('/api/v1/status/kills/stats'),
      fetchJson<AnalyticsSummary>('/api/v1/analytics/summary'),
    ]);

    setStatus(s);
    setWsHealth(ws);
    setCacheStats(cache);
    setUniverseStatus(universe);
    setKillStats(kills);
    setAnalytics(ana);
    setLastRefresh(new Date());
    setRefreshing(false);
  }, [apiUrl]);

  // Initial fetch + auto-refresh every 30s
  useEffect(() => {
    if (!isAuthenticated || !isAdmin(user?.character_id)) return;
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [isAuthenticated, user, fetchData]);

  // Gate render
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <RefreshCw className="h-6 w-6 text-text-secondary animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated || !isAdmin(user?.character_id)) {
    return null;
  }

  const dbOk = status?.database?.status === 'ok' || status?.database?.status === 'connected';
  const cacheOk = status?.cache?.status === 'ok' || status?.cache?.status === 'connected';
  const zkillOk = wsHealth?.zkill_listener?.connected ?? false;
  const allHealthy = dbOk && cacheOk && zkillOk;

  // Pageview data sorted by count
  const pageviewEntries = analytics?.pageviews
    ? Object.entries(analytics.pageviews).sort(([, a], [, b]) => b - a)
    : [];
  const totalPageviews = pageviewEntries.reduce((sum, [, count]) => sum + count, 0);

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-amber-500/20 rounded-lg flex items-center justify-center">
            <Shield className="h-5 w-5 text-amber-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-text">Admin Dashboard</h1>
            <p className="text-xs text-text-secondary">
              Last refresh: {lastRefresh.toLocaleTimeString()} &middot; Auto-refreshes every 30s
            </p>
          </div>
        </div>
        <button
          onClick={fetchData}
          disabled={refreshing}
          className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-text-secondary hover:text-text hover:bg-card-hover transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Overall health banner */}
      <div className={`flex items-center gap-3 px-4 py-3 rounded-lg border ${
        allHealthy
          ? 'bg-green-500/5 border-green-500/20'
          : 'bg-amber-500/5 border-amber-500/20'
      }`}>
        {allHealthy ? (
          <CheckCircle2 className="h-5 w-5 text-green-400" />
        ) : (
          <AlertTriangle className="h-5 w-5 text-amber-400" />
        )}
        <div>
          <span className={`text-sm font-medium ${allHealthy ? 'text-green-400' : 'text-amber-400'}`}>
            {allHealthy ? 'All Systems Operational' : 'Degraded Performance'}
          </span>
          <span className="text-xs text-text-secondary ml-2">
            v{status?.version || '?'} &middot; uptime {status?.uptime_seconds ? formatUptime(status.uptime_seconds) : '?'}
          </span>
        </div>
      </div>

      {/* System Health */}
      <section>
        <h2 className="text-sm font-semibold text-text-secondary uppercase tracking-wider mb-3 flex items-center gap-2">
          <Server className="h-4 w-4" /> System Health
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Card className="p-3">
            <div className="flex items-center gap-2 mb-2">
              <StatusDot ok={dbOk} />
              <span className="text-xs font-medium text-text">Database</span>
            </div>
            <div className="text-lg font-bold text-text">{dbOk ? 'Connected' : 'Down'}</div>
            <div className="text-[10px] text-text-secondary">
              {status?.systems_loaded ? `${status.systems_loaded.toLocaleString()} systems loaded` : ''}
            </div>
          </Card>

          <Card className="p-3">
            <div className="flex items-center gap-2 mb-2">
              <StatusDot ok={cacheOk} />
              <span className="text-xs font-medium text-text">Cache</span>
            </div>
            <div className="text-lg font-bold text-text">{cacheOk ? 'Active' : 'Down'}</div>
            <div className="text-[10px] text-text-secondary">
              {status?.cache?.backend || 'memory'} backend
            </div>
          </Card>

          <Card className="p-3">
            <div className="flex items-center gap-2 mb-2">
              <StatusDot ok={zkillOk} />
              <span className="text-xs font-medium text-text">zKill Listener</span>
            </div>
            <div className="text-lg font-bold text-text">{zkillOk ? 'Connected' : 'Disconnected'}</div>
            <div className="text-[10px] text-text-secondary">
              {wsHealth?.zkill_listener?.kills_processed?.toLocaleString() || 0} kills processed
            </div>
          </Card>

          <Card className="p-3">
            <div className="flex items-center gap-2 mb-2">
              <Wifi className="h-3 w-3 text-text-secondary" />
              <span className="text-xs font-medium text-text">WebSockets</span>
            </div>
            <div className="text-lg font-bold text-text">
              {wsHealth?.connections?.total ?? 0}
            </div>
            <div className="text-[10px] text-text-secondary">
              {wsHealth?.connections?.killfeed ?? 0} killfeed, {wsHealth?.connections?.map ?? 0} map
            </div>
          </Card>
        </div>
      </section>

      {/* Key Metrics */}
      <section>
        <h2 className="text-sm font-semibold text-text-secondary uppercase tracking-wider mb-3 flex items-center gap-2">
          <Activity className="h-4 w-4" /> Key Metrics
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
          <MetricCard
            icon={Eye}
            label="Pageviews (24h)"
            value={totalPageviews.toLocaleString()}
            sub={`${pageviewEntries.length} unique routes`}
            color="text-cyan-400"
          />
          <MetricCard
            icon={Zap}
            label="Kills (1h)"
            value={killStats?.kills_1h?.toLocaleString() ?? '—'}
            sub={`${killStats?.kills_24h?.toLocaleString() ?? '?'} in 24h`}
            color="text-red-400"
          />
          <MetricCard
            icon={Users}
            label="WS Clients"
            value={wsHealth?.connections?.total ?? 0}
            sub="Active connections"
            color="text-green-400"
          />
          <MetricCard
            icon={Database}
            label="Cache Hit Ratio"
            value={cacheStats?.hit_ratio != null ? `${(cacheStats.hit_ratio * 100).toFixed(1)}%` : '—'}
            sub={`${cacheStats?.hits?.toLocaleString() ?? 0} hits / ${cacheStats?.misses?.toLocaleString() ?? 0} misses`}
            color="text-amber-400"
          />
          <MetricCard
            icon={Globe}
            label="Universe Data"
            value={universeStatus?.systems_count?.toLocaleString() ?? '—'}
            sub={universeStatus?.file_size_mb ? formatBytes(universeStatus.file_size_mb) : 'systems'}
            color="text-blue-400"
          />
        </div>
      </section>

      {/* Cache Details */}
      {cacheStats && (cacheStats.route_cache || cacheStats.risk_cache) && (
        <section>
          <h2 className="text-sm font-semibold text-text-secondary uppercase tracking-wider mb-3 flex items-center gap-2">
            <BarChart3 className="h-4 w-4" /> Cache Breakdown
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {cacheStats.route_cache && (
              <Card className="p-3">
                <div className="text-xs font-medium text-text mb-2">Route Cache</div>
                <div className="flex items-center gap-3">
                  <div className="flex-1">
                    <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-cyan-500 rounded-full"
                        style={{ width: `${(cacheStats.route_cache.hit_ratio * 100).toFixed(0)}%` }}
                      />
                    </div>
                  </div>
                  <span className="text-sm font-bold text-cyan-400">
                    {(cacheStats.route_cache.hit_ratio * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="text-[10px] text-text-secondary mt-1">
                  {cacheStats.route_cache.hits.toLocaleString()} hits / {cacheStats.route_cache.misses.toLocaleString()} misses
                </div>
              </Card>
            )}
            {cacheStats.risk_cache && (
              <Card className="p-3">
                <div className="text-xs font-medium text-text mb-2">Risk Cache</div>
                <div className="flex items-center gap-3">
                  <div className="flex-1">
                    <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-amber-500 rounded-full"
                        style={{ width: `${(cacheStats.risk_cache.hit_ratio * 100).toFixed(0)}%` }}
                      />
                    </div>
                  </div>
                  <span className="text-sm font-bold text-amber-400">
                    {(cacheStats.risk_cache.hit_ratio * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="text-[10px] text-text-secondary mt-1">
                  {cacheStats.risk_cache.hits.toLocaleString()} hits / {cacheStats.risk_cache.misses.toLocaleString()} misses
                </div>
              </Card>
            )}
          </div>
        </section>
      )}

      {/* Pageviews by Route */}
      {pageviewEntries.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold text-text-secondary uppercase tracking-wider mb-3 flex items-center gap-2">
            <BarChart3 className="h-4 w-4" /> Pageviews by Route (24h)
          </h2>
          <Card className="p-3">
            <div className="space-y-2">
              {pageviewEntries.map(([path, count]) => {
                const pct = totalPageviews > 0 ? (count / totalPageviews) * 100 : 0;
                return (
                  <div key={path} className="flex items-center gap-3 text-xs">
                    <span className="w-28 text-text-secondary font-mono truncate" title={path}>
                      {path}
                    </span>
                    <div className="flex-1">
                      <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary rounded-full transition-all"
                          style={{ width: `${Math.max(pct, 1)}%` }}
                        />
                      </div>
                    </div>
                    <span className="w-12 text-right text-text font-medium">
                      {count.toLocaleString()}
                    </span>
                    <span className="w-12 text-right text-text-secondary">
                      {pct.toFixed(1)}%
                    </span>
                  </div>
                );
              })}
            </div>
          </Card>
        </section>
      )}

      {/* Kill Activity */}
      {killStats && (
        <section>
          <h2 className="text-sm font-semibold text-text-secondary uppercase tracking-wider mb-3 flex items-center gap-2">
            <Activity className="h-4 w-4" /> Kill Activity
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <MetricCard
              icon={Zap}
              label="Total Stored"
              value={killStats.total_kills?.toLocaleString() ?? '—'}
            />
            <MetricCard
              icon={Clock}
              label="Last 24h"
              value={killStats.kills_24h?.toLocaleString() ?? '—'}
              color="text-red-400"
            />
            <MetricCard
              icon={Clock}
              label="Last Hour"
              value={killStats.kills_1h?.toLocaleString() ?? '—'}
              color="text-amber-400"
            />
            <MetricCard
              icon={Clock}
              label="Latest Kill"
              value={killStats.newest_kill ? new Date(killStats.newest_kill).toLocaleTimeString() : '—'}
              sub={killStats.newest_kill ? new Date(killStats.newest_kill).toLocaleDateString() : ''}
            />
          </div>
        </section>
      )}

      {/* Universe Data */}
      {universeStatus && (
        <section>
          <h2 className="text-sm font-semibold text-text-secondary uppercase tracking-wider mb-3 flex items-center gap-2">
            <Globe className="h-4 w-4" /> Universe Data
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <MetricCard
              icon={Globe}
              label="Systems"
              value={universeStatus.systems_count?.toLocaleString() ?? '—'}
            />
            <MetricCard
              icon={Globe}
              label="Gates"
              value={universeStatus.gates_count?.toLocaleString() ?? '—'}
            />
            <MetricCard
              icon={Database}
              label="File Size"
              value={universeStatus.file_size_mb ? formatBytes(universeStatus.file_size_mb) : '—'}
            />
            <MetricCard
              icon={Clock}
              label="Last Modified"
              value={universeStatus.last_modified ? new Date(universeStatus.last_modified).toLocaleDateString() : '—'}
              sub={universeStatus.last_modified ? new Date(universeStatus.last_modified).toLocaleTimeString() : ''}
            />
          </div>
        </section>
      )}

      {/* Feature Flags */}
      {status?.features && (
        <section>
          <h2 className="text-sm font-semibold text-text-secondary uppercase tracking-wider mb-3 flex items-center gap-2">
            <Zap className="h-4 w-4" /> Feature Flags
          </h2>
          <Card className="p-3">
            <div className="flex flex-wrap gap-2">
              {Object.entries(status.features).map(([key, enabled]) => (
                <span
                  key={key}
                  className={`inline-flex items-center gap-1.5 text-xs px-2 py-1 rounded-md border ${
                    enabled
                      ? 'bg-green-500/10 border-green-500/30 text-green-400'
                      : 'bg-gray-800 border-gray-700 text-gray-500'
                  }`}
                >
                  {enabled ? (
                    <CheckCircle2 className="h-3 w-3" />
                  ) : (
                    <XCircle className="h-3 w-3" />
                  )}
                  {key.replace(/_/g, ' ')}
                </span>
              ))}
            </div>
          </Card>
        </section>
      )}

      {/* Footer */}
      <div className="text-center text-[10px] text-text-secondary py-4 border-t border-border">
        EVE Gatekeeper Admin &middot; v{status?.version || '?'} &middot; {status?.debug ? 'Debug Mode' : 'Production'}
      </div>
    </div>
  );
}
