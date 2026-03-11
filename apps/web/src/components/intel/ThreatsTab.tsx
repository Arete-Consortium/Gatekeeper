'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import { Card, Badge, Select } from '@/components/ui';
import { SecurityBadge } from '@/components/system';
import { GatekeeperAPI } from '@/lib/api';
import type { HotzoneSystemData } from '@/lib/types';
import {
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  Minus,
  Skull,
  RefreshCw,
  Shield,
  Loader2,
} from 'lucide-react';

const timeOptions = [
  { value: '1', label: '1 hour' },
  { value: '6', label: '6 hours' },
  { value: '24', label: '24 hours' },
];

const secOptions = [
  { value: '', label: 'All' },
  { value: 'null', label: 'Nullsec' },
  { value: 'low', label: 'Lowsec' },
  { value: 'high', label: 'Highsec' },
];

const limitOptions = [
  { value: '10', label: 'Top 10' },
  { value: '25', label: 'Top 25' },
  { value: '50', label: 'Top 50' },
];

function TrendIcon({ trend }: { trend: number }) {
  if (trend >= 1.5) return <TrendingUp className="h-3.5 w-3.5 text-red-400" />;
  if (trend >= 1.0) return <TrendingUp className="h-3.5 w-3.5 text-orange-400" />;
  if (trend >= 0.5) return <Minus className="h-3.5 w-3.5 text-yellow-400" />;
  return <TrendingDown className="h-3.5 w-3.5 text-green-400" />;
}

function TrendLabel({ trend }: { trend: number }) {
  if (trend >= 2.0) return <span className="text-red-400 font-bold">SURGING</span>;
  if (trend >= 1.5) return <span className="text-red-400">Heating</span>;
  if (trend >= 1.0) return <span className="text-orange-400">Active</span>;
  if (trend >= 0.5) return <span className="text-yellow-400">Steady</span>;
  return <span className="text-green-400">Cooling</span>;
}

export function ThreatsTab() {
  const [hours, setHours] = useState(1);
  const [secFilter, setSecFilter] = useState('');
  const [regionFilter, setRegionFilter] = useState('');
  const [limit, setLimit] = useState(25);
  const [systems, setSystems] = useState<HotzoneSystemData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await GatekeeperAPI.getHotzones(hours, limit, secFilter || undefined);
      setSystems(result.systems);
      setLastRefresh(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load threat data');
    } finally {
      setLoading(false);
    }
  }, [hours, limit, secFilter]);

  useEffect(() => {
    fetchData();
    // Auto-refresh every 60s
    const interval = setInterval(fetchData, 60000);
    return () => clearInterval(interval);
  }, [fetchData]);

  // Extract unique regions for dropdown
  const regionOptions = useMemo(() => {
    const regions = new Set<string>();
    for (const sys of systems) {
      if (sys.region_name) regions.add(sys.region_name);
    }
    return [
      { value: '', label: 'All Regions' },
      ...[...regions].sort().map((r) => ({ value: r, label: r })),
    ];
  }, [systems]);

  // Filter by region (client-side, after API fetch)
  const filteredSystems = useMemo(() => {
    if (!regionFilter) return systems;
    return systems.filter((s) => s.region_name === regionFilter);
  }, [systems, regionFilter]);

  const stats = useMemo(() => {
    if (filteredSystems.length === 0) return null;
    const totalKills = filteredSystems.reduce((s, sys) => s + sys.kills_current, 0);
    const totalPods = filteredSystems.reduce((s, sys) => s + sys.pods_current, 0);
    const gateCamps = filteredSystems.filter((s) => s.gate_camp_likely).length;
    const surging = filteredSystems.filter((s) => s.trend >= 1.5).length;
    return { totalKills, totalPods, gateCamps, surging };
  }, [filteredSystems]);

  return (
    <div className="space-y-6">
      {/* Filters */}
      <Card>
        <div className="flex flex-wrap items-end gap-4">
          <div className="w-32">
            <Select
              label="Time Range"
              value={hours.toString()}
              onChange={(e) => setHours(parseInt(e.target.value))}
              options={timeOptions}
            />
          </div>
          <div className="w-28">
            <Select
              label="Security"
              value={secFilter}
              onChange={(e) => setSecFilter(e.target.value)}
              options={secOptions}
            />
          </div>
          <div className="w-40">
            <Select
              label="Region"
              value={regionFilter}
              onChange={(e) => setRegionFilter(e.target.value)}
              options={regionOptions}
            />
          </div>
          <div className="w-28">
            <Select
              label="Show"
              value={limit.toString()}
              onChange={(e) => setLimit(parseInt(e.target.value))}
              options={limitOptions}
            />
          </div>
          <button
            onClick={fetchData}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-2 text-sm rounded-lg bg-card-hover hover:bg-card-hover/80 text-text-secondary hover:text-text transition-colors"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          {lastRefresh && (
            <span className="text-[10px] text-text-secondary ml-auto">
              Updated {lastRefresh.toLocaleTimeString()}
            </span>
          )}
        </div>
      </Card>

      {/* Summary Stats */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <Card className="text-center">
            <div className="flex items-center justify-center gap-1.5 mb-1">
              <Skull className="h-4 w-4 text-red-400" />
              <span className="text-xs text-text-secondary uppercase">Kills</span>
            </div>
            <span className="text-2xl font-bold text-red-400">{stats.totalKills}</span>
          </Card>
          <Card className="text-center">
            <div className="flex items-center justify-center gap-1.5 mb-1">
              <Shield className="h-4 w-4 text-pink-400" />
              <span className="text-xs text-text-secondary uppercase">Pods</span>
            </div>
            <span className="text-2xl font-bold text-pink-400">{stats.totalPods}</span>
          </Card>
          <Card className="text-center">
            <div className="flex items-center justify-center gap-1.5 mb-1">
              <TrendingUp className="h-4 w-4 text-orange-400" />
              <span className="text-xs text-text-secondary uppercase">Surging</span>
            </div>
            <span className="text-2xl font-bold text-orange-400">{stats.surging}</span>
          </Card>
          <Card className="text-center">
            <div className="flex items-center justify-center gap-1.5 mb-1">
              <AlertTriangle className="h-4 w-4 text-yellow-400" />
              <span className="text-xs text-text-secondary uppercase">Gate Camps</span>
            </div>
            <span className="text-2xl font-bold text-yellow-400">{stats.gateCamps}</span>
          </Card>
        </div>
      )}

      {/* Threats Table */}
      {loading && filteredSystems.length === 0 ? (
        <Card className="flex items-center justify-center py-12 gap-3">
          <Loader2 className="h-5 w-5 animate-spin text-primary" />
          <span className="text-text-secondary">Analyzing threat landscape...</span>
        </Card>
      ) : error ? (
        <Card className="text-center py-12">
          <AlertTriangle className="h-8 w-8 text-red-400 mx-auto mb-3" />
          <p className="text-red-400 text-sm">{error}</p>
          <button onClick={fetchData} className="mt-3 text-sm text-primary hover:underline">
            Retry
          </button>
        </Card>
      ) : filteredSystems.length === 0 ? (
        <Card className="text-center py-12">
          <Shield className="h-8 w-8 text-green-400 mx-auto mb-3" />
          <p className="text-text-secondary">No active threats detected. Space is quiet.</p>
        </Card>
      ) : (
        <div className="border border-border rounded-lg overflow-hidden">
          {/* Header */}
          <div className="hidden sm:grid grid-cols-12 gap-2 px-4 py-3 bg-card text-[10px] text-text-secondary uppercase font-semibold tracking-wider">
            <div className="col-span-1">#</div>
            <div className="col-span-3">System</div>
            <div className="col-span-1">Sec</div>
            <div className="col-span-2 text-right">Kills</div>
            <div className="col-span-1 text-center">Trend</div>
            <div className="col-span-1 text-right">+1hr</div>
            <div className="col-span-1 text-right">+2hr</div>
            <div className="col-span-2 text-right">Status</div>
          </div>

          {/* Rows */}
          {filteredSystems.map((sys, idx) => (
            <div key={sys.system_id}>
              {/* Desktop row */}
              <div className="hidden sm:grid grid-cols-12 gap-2 px-4 py-2.5 border-t border-border hover:bg-card-hover transition-colors items-center">
                <div className="col-span-1 text-text-secondary text-sm">{idx + 1}</div>
                <div className="col-span-3 min-w-0">
                  <div className="font-medium text-text text-sm truncate">{sys.system_name}</div>
                  {sys.region_name && (
                    <div className="text-[10px] text-text-secondary truncate">{sys.region_name}</div>
                  )}
                </div>
                <div className="col-span-1">
                  <SecurityBadge security={sys.security} size="sm" />
                </div>
                <div className="col-span-2 text-right">
                  <span className="text-red-400 font-medium text-sm">{sys.kills_current}</span>
                  {sys.pods_current > 0 && (
                    <span className="text-pink-400 text-xs ml-1">+{sys.pods_current}p</span>
                  )}
                </div>
                <div className="col-span-1 flex justify-center">
                  <TrendIcon trend={sys.trend} />
                </div>
                <div className="col-span-1 text-right text-xs text-text-secondary font-mono">
                  {sys.predicted_1hr}
                </div>
                <div className="col-span-1 text-right text-xs text-text-secondary font-mono">
                  {sys.predicted_2hr}
                </div>
                <div className="col-span-2 text-right flex items-center justify-end gap-1.5">
                  <span className="text-[11px]"><TrendLabel trend={sys.trend} /></span>
                  {sys.gate_camp_likely && (
                    <Badge variant="danger" size="sm">CAMP</Badge>
                  )}
                </div>
              </div>

              {/* Mobile row */}
              <div className="sm:hidden border-t border-border px-3 py-3 hover:bg-card-hover transition-colors">
                <div className="flex items-center gap-2">
                  <span className="text-text-secondary text-sm">{idx + 1}.</span>
                  <span className="font-medium text-text truncate">{sys.system_name}</span>
                  <SecurityBadge security={sys.security} size="sm" />
                  <TrendIcon trend={sys.trend} />
                  {sys.gate_camp_likely && <Badge variant="danger" size="sm">CAMP</Badge>}
                </div>
                <div className="flex items-center gap-4 mt-1 text-xs">
                  <span className="text-red-400">{sys.kills_current} kills</span>
                  {sys.pods_current > 0 && <span className="text-pink-400">{sys.pods_current} pods</span>}
                  <span className="text-text-secondary ml-auto">+1h: {sys.predicted_1hr} | +2h: {sys.predicted_2hr}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
