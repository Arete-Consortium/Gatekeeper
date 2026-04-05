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
  DollarSign,
  TrendingUp,
  Lock,
  Map,
  Navigation,
  Search,
  Radio,
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

// Matches GET /api/v1/status/
interface ApiStatus {
  version?: string;
  uptime_seconds?: number;
  uptime_formatted?: string;
  status?: string;
  environment?: { debug: boolean; log_level: string };
  checks?: {
    database: string;
    cache: string;
    systems_loaded: number;
  };
  features?: Record<string, boolean>;
}

// Matches GET /api/v1/status/websocket-health
interface WebSocketHealth {
  zkill_listener?: {
    state: string;
    is_connected: boolean;
    is_running: boolean;
    health: {
      total_connections: number;
      total_disconnections: number;
      total_failed_reconnections: number;
      consecutive_failures: number;
      current_retry_attempt: number;
      last_message_received_at: number | null;
      total_reconnections: number;
    };
  };
  client_connections?: {
    active_connections: number;
  };
}

// Matches GET /api/v1/status/cache/stats
interface CacheStats {
  cache_type?: string;
  hits?: number;
  misses?: number;
  total_requests?: number;
  hit_ratio?: number;
  hit_percentage?: number;
  entries?: number;
}

// Matches GET /api/v1/status/universe
interface UniverseStatus {
  file?: string;
  exists?: boolean;
  last_modified?: string;
  age_hours?: number;
  age_days?: number;
  status?: string;
}

// Matches GET /api/v1/status/kills/stats
interface KillStats {
  enabled?: boolean;
  total_stored?: number;
  total_received?: number;
  systems_tracked?: number;
  regions_tracked?: number;
  max_entries?: number;
}

// Matches GET /api/v1/analytics/summary
interface AnalyticsSummary {
  total_views?: number;
  unique_paths?: number;
  paths?: Array<{ path: string; views: number }>;
}

// Matches GET /api/v1/admin/analytics
interface AdminAnalytics {
  active_subscribers: number;
  mrr: number;
  comp_users: number;
  total_users: number;
  dau_estimate: number;
  popular_endpoints: Array<{ endpoint: string; count: number }>;
  feature_usage: {
    map_views: number;
    route_calculations: number;
    intel_lookups: number;
    kill_feed_connections: number;
  };
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
  const [adminAnalytics, setAdminAnalytics] = useState<AdminAnalytics | null>(null);
  const [adminSecret, setAdminSecret] = useState('');
  const [adminError, setAdminError] = useState<string | null>(null);
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

  const fetchAdminAnalytics = useCallback(async () => {
    if (!apiUrl || !adminSecret) return;
    setAdminError(null);
    try {
      const res = await fetch(`${apiUrl}/api/v1/admin/analytics`, {
        headers: { 'X-Admin-Secret': adminSecret },
        signal: AbortSignal.timeout(10000),
      });
      if (res.status === 403) {
        setAdminError('Invalid admin secret');
        setAdminAnalytics(null);
        return;
      }
      if (!res.ok) {
        setAdminError(`Error: ${res.status}`);
        setAdminAnalytics(null);
        return;
      }
      const data = await res.json();
      setAdminAnalytics(data);
    } catch {
      setAdminError('Failed to fetch analytics');
      setAdminAnalytics(null);
    }
  }, [apiUrl, adminSecret]);

  // Initial fetch + auto-refresh every 30s
  useEffect(() => {
    if (!isAuthenticated || !isAdmin(user?.character_id)) return;
    void fetchData();
    const interval = setInterval(() => void fetchData(), 30000);
    return () => clearInterval(interval);
  }, [isAuthenticated, user, fetchData]);

  // Auto-fetch admin analytics when secret changes
  useEffect(() => {
    if (!adminSecret) return;
    void fetchAdminAnalytics();
    const interval = setInterval(() => void fetchAdminAnalytics(), 30000);
    return () => clearInterval(interval);
  }, [adminSecret, fetchAdminAnalytics]);

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

  const dbOk = status?.checks?.database === 'ok';
  const cacheOk = status?.checks?.cache === 'memory' || status?.checks?.cache === 'redis';
  const zkillOk = wsHealth?.zkill_listener?.is_connected ?? false;
  const allHealthy = dbOk && cacheOk && zkillOk;

  // Pageview data sorted by count
  const pageviewEntries = analytics?.paths
    ? analytics.paths.sort((a, b) => b.views - a.views)
    : [];
  const totalPageviews = analytics?.total_views ?? 0;

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
            v{status?.version || '?'} &middot; uptime {status?.uptime_formatted || (status?.uptime_seconds ? formatUptime(status.uptime_seconds) : '?')}
          </span>
          {!zkillOk && wsHealth?.zkill_listener && (
            <span className="text-xs text-red-400 ml-2">
              zKill: {wsHealth.zkill_listener.state} ({wsHealth.zkill_listener.health.consecutive_failures} failures)
            </span>
          )}
        </div>
      </div>

      {/* Admin Analytics */}
      <section>
        <h2 className="text-sm font-semibold text-text-secondary uppercase tracking-wider mb-3 flex items-center gap-2">
          <TrendingUp className="h-4 w-4" /> Business Analytics
        </h2>
        <div className="flex items-center gap-3 mb-4">
          <div className="flex items-center gap-2 flex-1 max-w-md">
            <Lock className="h-4 w-4 text-text-secondary" />
            <input
              type="password"
              placeholder="Enter admin secret..."
              value={adminSecret}
              onChange={(e) => setAdminSecret(e.target.value)}
              className="flex-1 px-3 py-2 text-sm bg-gray-900/50 border border-gray-700 rounded-lg text-text placeholder:text-text-secondary/50 focus:outline-none focus:border-cyan-500"
            />
          </div>
          {adminSecret && (
            <button
              onClick={fetchAdminAnalytics}
              className="px-3 py-2 text-sm font-medium text-text-secondary hover:text-text hover:bg-card-hover rounded-lg transition-colors"
            >
              <RefreshCw className="h-4 w-4" />
            </button>
          )}
        </div>

        {adminError && (
          <div className="flex items-center gap-2 px-4 py-3 mb-4 rounded-lg border bg-red-500/5 border-red-500/20">
            <XCircle className="h-4 w-4 text-red-400" />
            <span className="text-sm text-red-400">{adminError}</span>
          </div>
        )}

        {adminAnalytics && (
          <>
            {/* Revenue & Users */}
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3 mb-4">
              <MetricCard
                icon={DollarSign}
                label="MRR"
                value={`$${adminAnalytics.mrr.toFixed(0)}`}
                sub={`${adminAnalytics.active_subscribers} paying subs`}
                color="text-green-400"
              />
              <MetricCard
                icon={Users}
                label="Active Subscribers"
                value={adminAnalytics.active_subscribers}
                sub="Stripe subscriptions"
                color="text-cyan-400"
              />
              <MetricCard
                icon={Eye}
                label="DAU (est.)"
                value={adminAnalytics.dau_estimate}
                sub="Unique IPs, 24h"
                color="text-amber-400"
              />
              <MetricCard
                icon={Users}
                label="Total Users"
                value={adminAnalytics.total_users}
                sub={`${adminAnalytics.comp_users} comp`}
                color="text-blue-400"
              />
              <MetricCard
                icon={Shield}
                label="Comp Users"
                value={adminAnalytics.comp_users}
                sub="Active comp grants"
                color="text-purple-400"
              />
            </div>

            {/* Feature Usage */}
            <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2 flex items-center gap-2">
              <Zap className="h-3.5 w-3.5" /> Feature Usage (since restart)
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
              <MetricCard
                icon={Map}
                label="Map Views"
                value={adminAnalytics.feature_usage.map_views.toLocaleString()}
                color="text-cyan-400"
              />
              <MetricCard
                icon={Navigation}
                label="Route Calcs"
                value={adminAnalytics.feature_usage.route_calculations.toLocaleString()}
                color="text-green-400"
              />
              <MetricCard
                icon={Search}
                label="Intel Lookups"
                value={adminAnalytics.feature_usage.intel_lookups.toLocaleString()}
                color="text-amber-400"
              />
              <MetricCard
                icon={Radio}
                label="Kill Feed Conns"
                value={adminAnalytics.feature_usage.kill_feed_connections.toLocaleString()}
                color="text-red-400"
              />
            </div>

            {/* Popular Endpoints */}
            {adminAnalytics.popular_endpoints.length > 0 && (
              <>
                <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2 flex items-center gap-2">
                  <BarChart3 className="h-3.5 w-3.5" /> Top Endpoints (since restart)
                </h3>
                <Card className="p-3 mb-4">
                  <div className="space-y-2">
                    {adminAnalytics.popular_endpoints.map((ep) => {
                      const maxCount = adminAnalytics.popular_endpoints[0]?.count || 1;
                      const pct = (ep.count / maxCount) * 100;
                      return (
                        <div key={ep.endpoint} className="flex items-center gap-3 text-xs">
                          <span className="w-48 text-text-secondary font-mono truncate" title={ep.endpoint}>
                            {ep.endpoint}
                          </span>
                          <div className="flex-1">
                            <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                              <div
                                className="h-full bg-cyan-500 rounded-full transition-all"
                                style={{ width: `${Math.max(pct, 1)}%` }}
                              />
                            </div>
                          </div>
                          <span className="w-16 text-right text-text font-medium">
                            {ep.count.toLocaleString()}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </Card>
              </>
            )}
          </>
        )}

        {!adminSecret && (
          <div className="text-xs text-text-secondary italic">
            Enter admin secret to view business analytics (MRR, subscribers, DAU, feature usage).
          </div>
        )}
      </section>

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
              {status?.checks?.systems_loaded ? `${status.checks.systems_loaded.toLocaleString()} systems loaded` : ''}
            </div>
          </Card>

          <Card className="p-3">
            <div className="flex items-center gap-2 mb-2">
              <StatusDot ok={cacheOk} />
              <span className="text-xs font-medium text-text">Cache</span>
            </div>
            <div className="text-lg font-bold text-text">{cacheOk ? 'Active' : 'Down'}</div>
            <div className="text-[10px] text-text-secondary">
              {status?.checks?.cache || 'memory'} backend &middot; {cacheStats?.entries ?? 0} entries
            </div>
          </Card>

          <Card className="p-3">
            <div className="flex items-center gap-2 mb-2">
              <StatusDot ok={zkillOk} />
              <span className="text-xs font-medium text-text">zKill Listener</span>
            </div>
            <div className="text-lg font-bold text-text">
              {zkillOk ? 'Connected' : wsHealth?.zkill_listener?.state || 'Disconnected'}
            </div>
            <div className="text-[10px] text-text-secondary">
              {wsHealth?.zkill_listener?.health.consecutive_failures
                ? `${wsHealth.zkill_listener.health.consecutive_failures} consecutive failures`
                : 'Healthy'}
            </div>
          </Card>

          <Card className="p-3">
            <div className="flex items-center gap-2 mb-2">
              <Wifi className="h-3 w-3 text-text-secondary" />
              <span className="text-xs font-medium text-text">WebSockets</span>
            </div>
            <div className="text-lg font-bold text-text">
              {wsHealth?.client_connections?.active_connections ?? 0}
            </div>
            <div className="text-[10px] text-text-secondary">
              active client connections
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
            label="Kills Received"
            value={killStats?.total_received?.toLocaleString() ?? '0'}
            sub={`${killStats?.total_stored?.toLocaleString() ?? '0'} stored / ${killStats?.max_entries?.toLocaleString() ?? '?'} max`}
            color="text-red-400"
          />
          <MetricCard
            icon={Users}
            label="WS Clients"
            value={wsHealth?.client_connections?.active_connections ?? 0}
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
            value={universeStatus?.status === 'fresh' ? 'Fresh' : universeStatus?.status ?? '—'}
            sub={universeStatus?.age_hours != null ? `${universeStatus.age_hours.toFixed(1)}h old` : ''}
            color="text-blue-400"
          />
        </div>
      </section>

      {/* Cache Details */}
      {cacheStats && cacheStats.hit_ratio != null && (
        <section>
          <h2 className="text-sm font-semibold text-text-secondary uppercase tracking-wider mb-3 flex items-center gap-2">
            <BarChart3 className="h-4 w-4" /> Cache Performance
          </h2>
          <Card className="p-3">
            <div className="flex items-center gap-3 mb-2">
              <div className="text-xs font-medium text-text">
                {cacheStats.cache_type || 'memory'} cache &middot; {cacheStats.entries ?? 0} entries
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex-1">
                <div className="h-3 bg-gray-800 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-cyan-500 rounded-full transition-all"
                    style={{ width: `${(cacheStats.hit_ratio * 100).toFixed(0)}%` }}
                  />
                </div>
              </div>
              <span className="text-sm font-bold text-cyan-400">
                {cacheStats.hit_percentage?.toFixed(1) ?? (cacheStats.hit_ratio * 100).toFixed(1)}%
              </span>
            </div>
            <div className="flex justify-between text-[10px] text-text-secondary mt-1">
              <span>{cacheStats.hits?.toLocaleString() ?? 0} hits / {cacheStats.misses?.toLocaleString() ?? 0} misses</span>
              <span>{cacheStats.total_requests?.toLocaleString() ?? 0} total requests</span>
            </div>
          </Card>
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
              {pageviewEntries.map((entry) => {
                const pct = totalPageviews > 0 ? (entry.views / totalPageviews) * 100 : 0;
                return (
                  <div key={entry.path} className="flex items-center gap-3 text-xs">
                    <span className="w-28 text-text-secondary font-mono truncate" title={entry.path}>
                      {entry.path}
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
                      {entry.views.toLocaleString()}
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
              label="Total Received"
              value={killStats.total_received?.toLocaleString() ?? '0'}
              color="text-red-400"
            />
            <MetricCard
              icon={Database}
              label="Stored"
              value={killStats.total_stored?.toLocaleString() ?? '0'}
              sub={`max ${killStats.max_entries?.toLocaleString() ?? '?'}`}
            />
            <MetricCard
              icon={Globe}
              label="Systems Tracked"
              value={killStats.systems_tracked?.toLocaleString() ?? '0'}
            />
            <MetricCard
              icon={Globe}
              label="Regions Tracked"
              value={killStats.regions_tracked?.toLocaleString() ?? '0'}
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
              icon={CheckCircle2}
              label="Status"
              value={universeStatus.status ?? '—'}
              color={universeStatus.status === 'fresh' ? 'text-green-400' : 'text-amber-400'}
            />
            <MetricCard
              icon={Clock}
              label="Data Age"
              value={universeStatus.age_hours != null ? `${universeStatus.age_hours.toFixed(1)}h` : '—'}
              sub={universeStatus.age_days != null ? `${universeStatus.age_days.toFixed(1)} days` : ''}
            />
            <MetricCard
              icon={Database}
              label="Systems Loaded"
              value={status?.checks?.systems_loaded?.toLocaleString() ?? '—'}
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
        Gatekeeper Admin &middot; v{status?.version || '?'} &middot; {status?.environment?.debug ? 'Debug Mode' : 'Production'}
      </div>
    </div>
  );
}
