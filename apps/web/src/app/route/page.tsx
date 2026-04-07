'use client';

import { Suspense, useState, useMemo, useCallback, useEffect, useRef } from 'react';
import { useSearchParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { useMultiRoute } from '@/hooks';
import { Card, Button, Toggle, Skeleton } from '@/components/ui';
import { Select } from '@/components/ui/Select';
import { RouteResult, WaypointList, generateWaypointId } from '@/components/route';
import type { Waypoint } from '@/components/route';
import { ROUTE_PROFILES } from '@/lib/utils';
import type { RouteProfile, CapitalShipType, FuelType, JumpRouteResponse, HotzoneResponse, HotzoneSystemData } from '@/lib/types';
import { GatekeeperAPI } from '@/lib/api';
import { Route, Loader2, Rocket, Fuel, Clock, ChevronDown, ChevronUp, Settings2, Share2, Check, Shield, Crosshair, Skull, Building2, AlertTriangle, Flame, TrendingUp, TrendingDown, Gauge, Map as MapIcon } from 'lucide-react';
import { ErrorMessage, getUserFriendlyError } from '@/components/ui';
import Link from 'next/link';
import { JumpStrip } from '@/components/route/JumpStrip';
import { SecurityBadge, RiskBadge } from '@/components/system';
import dynamic from 'next/dynamic';

const JumpRangeMap = dynamic(
  () => import('@/components/route/JumpRangeMap').then((m) => m.JumpRangeMap),
  { ssr: false, loading: () => <div className="w-full h-80 bg-card border border-border rounded-lg animate-pulse" /> }
);

const RouteMap = dynamic(
  () => import('@/components/route/RouteMap').then((m) => m.RouteMap),
  { ssr: false, loading: () => <div className="w-full h-80 bg-card border border-border rounded-lg animate-pulse" /> }
);

const profileOptions = Object.entries(ROUTE_PROFILES).map(([value, config]) => ({
  value,
  label: config.label,
}));

// Specific hull → backend ship category + fuel type
interface HullInfo {
  category: CapitalShipType;
  fuel: FuelType;
}

const HULLS: Record<string, HullInfo> = {
  // Jump Freighters
  'Ark':        { category: 'jump_freighter', fuel: 'helium' },
  'Anshar':     { category: 'jump_freighter', fuel: 'oxygen' },
  'Nomad':      { category: 'jump_freighter', fuel: 'hydrogen' },
  'Rhea':       { category: 'jump_freighter', fuel: 'nitrogen' },
  // Carriers
  'Archon':     { category: 'carrier', fuel: 'helium' },
  'Thanatos':   { category: 'carrier', fuel: 'oxygen' },
  'Nidhoggur':  { category: 'carrier', fuel: 'hydrogen' },
  'Chimera':    { category: 'carrier', fuel: 'nitrogen' },
  // Dreadnoughts
  'Revelation': { category: 'dreadnought', fuel: 'helium' },
  'Moros':      { category: 'dreadnought', fuel: 'oxygen' },
  'Naglfar':    { category: 'dreadnought', fuel: 'hydrogen' },
  'Phoenix':    { category: 'dreadnought', fuel: 'nitrogen' },
  // Force Auxiliary
  'Apostle':    { category: 'force_auxiliary', fuel: 'helium' },
  'Ninazu':     { category: 'force_auxiliary', fuel: 'oxygen' },
  'Lif':        { category: 'force_auxiliary', fuel: 'hydrogen' },
  'Minokawa':   { category: 'force_auxiliary', fuel: 'nitrogen' },
  // Supercarriers
  'Aeon':       { category: 'supercarrier', fuel: 'helium' },
  'Nyx':        { category: 'supercarrier', fuel: 'oxygen' },
  'Hel':        { category: 'supercarrier', fuel: 'hydrogen' },
  'Wyvern':     { category: 'supercarrier', fuel: 'nitrogen' },
  // Titans
  'Avatar':     { category: 'titan', fuel: 'helium' },
  'Erebus':     { category: 'titan', fuel: 'oxygen' },
  'Ragnarok':   { category: 'titan', fuel: 'hydrogen' },
  'Leviathan':  { category: 'titan', fuel: 'nitrogen' },
  // Industrial
  'Rorqual':    { category: 'rorqual', fuel: 'oxygen' },
  // Black Ops
  'Redeemer':   { category: 'black_ops', fuel: 'helium' },
  'Sin':        { category: 'black_ops', fuel: 'oxygen' },
  'Panther':    { category: 'black_ops', fuel: 'hydrogen' },
  'Widow':      { category: 'black_ops', fuel: 'nitrogen' },
  'Marshal':    { category: 'black_ops', fuel: 'nitrogen' },
};

const SHIP_OPTIONS: { value: string; label: string }[] = [
  { value: '---jf', label: '── Jump Freighters ──' },
  { value: 'Ark', label: 'Ark (Amarr)' },
  { value: 'Anshar', label: 'Anshar (Gallente)' },
  { value: 'Nomad', label: 'Nomad (Minmatar)' },
  { value: 'Rhea', label: 'Rhea (Caldari)' },
  { value: '---carrier', label: '── Carriers ──' },
  { value: 'Archon', label: 'Archon (Amarr)' },
  { value: 'Thanatos', label: 'Thanatos (Gallente)' },
  { value: 'Nidhoggur', label: 'Nidhoggur (Minmatar)' },
  { value: 'Chimera', label: 'Chimera (Caldari)' },
  { value: '---dread', label: '── Dreadnoughts ──' },
  { value: 'Revelation', label: 'Revelation (Amarr)' },
  { value: 'Moros', label: 'Moros (Gallente)' },
  { value: 'Naglfar', label: 'Naglfar (Minmatar)' },
  { value: 'Phoenix', label: 'Phoenix (Caldari)' },
  { value: '---fax', label: '── Force Auxiliary ──' },
  { value: 'Apostle', label: 'Apostle (Amarr)' },
  { value: 'Ninazu', label: 'Ninazu (Gallente)' },
  { value: 'Lif', label: 'Lif (Minmatar)' },
  { value: 'Minokawa', label: 'Minokawa (Caldari)' },
  { value: '---super', label: '── Supercarriers ──' },
  { value: 'Aeon', label: 'Aeon (Amarr)' },
  { value: 'Nyx', label: 'Nyx (Gallente)' },
  { value: 'Hel', label: 'Hel (Minmatar)' },
  { value: 'Wyvern', label: 'Wyvern (Caldari)' },
  { value: '---titan', label: '── Titans ──' },
  { value: 'Avatar', label: 'Avatar (Amarr)' },
  { value: 'Erebus', label: 'Erebus (Gallente)' },
  { value: 'Ragnarok', label: 'Ragnarok (Minmatar)' },
  { value: 'Leviathan', label: 'Leviathan (Caldari)' },
  { value: '---ind', label: '── Industrial ──' },
  { value: 'Rorqual', label: 'Rorqual (ORE)' },
  { value: '---blops', label: '── Black Ops ──' },
  { value: 'Redeemer', label: 'Redeemer (Amarr)' },
  { value: 'Sin', label: 'Sin (Gallente)' },
  { value: 'Panther', label: 'Panther (Minmatar)' },
  { value: 'Widow', label: 'Widow (Caldari)' },
  { value: 'Marshal', label: 'Marshal (SoCT)' },
];

// Fuel label mapping (for display in results)
const FUEL_LABELS: Record<FuelType, string> = {
  nitrogen: 'Nitrogen Isotopes',
  helium: 'Helium Isotopes',
  oxygen: 'Oxygen Isotopes',
  hydrogen: 'Hydrogen Isotopes',
};

const SKILL_OPTIONS = Array.from({ length: 6 }, (_, i) => ({
  value: i.toString(),
  label: `Level ${i}`,
}));

// Base jump range by ship category (must match backend SHIP_BASE_RANGE)
const BASE_RANGE: Record<CapitalShipType, number> = {
  jump_freighter: 5.0,
  carrier: 5.0,
  dreadnought: 5.0,
  force_auxiliary: 5.0,
  supercarrier: 5.0,
  titan: 5.0,
  rorqual: 5.0,
  black_ops: 4.0,
};

function formatIsk(value: number): string {
  if (value >= 1e12) return `${(value / 1e12).toFixed(2)}T`;
  if (value >= 1e9) return `${(value / 1e9).toFixed(2)}B`;
  if (value >= 1e6) return `${(value / 1e6).toFixed(2)}M`;
  if (value >= 1e3) return `${(value / 1e3).toFixed(1)}K`;
  return value.toFixed(2);
}

function formatMinutes(minutes: number): string {
  if (minutes < 1) return '< 1m';
  const hrs = Math.floor(minutes / 60);
  const mins = Math.round(minutes % 60);
  if (hrs === 0) return `${mins}m`;
  return `${hrs}h ${mins}m`;
}

function getJumpRiskColor(score: number): 'green' | 'yellow' | 'orange' | 'red' {
  if (score < 25) return 'green';
  if (score < 50) return 'yellow';
  if (score < 75) return 'orange';
  return 'red';
}

function JumpLegRow({ leg, idx, hotzone }: { leg: import('@/lib/types').JumpLegResponse; idx: number; hotzone?: HotzoneSystemData }) {
  const [expanded, setExpanded] = useState(false);
  const riskColor = getJumpRiskColor(leg.to_risk_score);
  const hasBreakdown = leg.to_risk_breakdown != null || hotzone != null;

  return (
    <div>
      {/* Desktop row */}
      <button
        type="button"
        onClick={() => hasBreakdown && setExpanded(!expanded)}
        className={`hidden sm:grid grid-cols-16 gap-2 px-3 py-2.5 border-t border-border hover:bg-card-hover transition-colors items-center min-w-[800px] text-sm w-full text-left ${hasBreakdown ? 'cursor-pointer' : ''}`}
      >
        <div className="col-span-1 text-center text-text-secondary font-mono">
          {idx + 1}
        </div>
        <div className="col-span-2 text-text font-medium truncate" title={leg.from_system}>
          {leg.from_system}
        </div>
        <div className="col-span-3 text-text font-medium truncate flex items-center gap-1.5" title={leg.to_system}>
          <span className="truncate">{leg.to_system}</span>
          {leg.to_pirate_suppressed && (
            <span className="text-[10px] font-medium text-red-400 bg-red-500/15 px-1 py-0.5 rounded shrink-0">SUP</span>
          )}
          {leg.to_has_npc_station && (
            <span title="Has NPC station"><Building2 className="h-3 w-3 text-text-secondary/60 shrink-0" /></span>
          )}
        </div>
        <div className="col-span-2 text-text-secondary text-xs truncate" title={leg.to_region_name}>
          {leg.to_region_name}
        </div>
        <div className="col-span-1 text-right text-blue-400 font-mono">
          {leg.distance_ly.toFixed(1)}
        </div>
        <div className="col-span-1 text-right text-yellow-400 font-mono">
          {leg.fuel_required.toLocaleString()}
        </div>
        <div className="col-span-1 text-right text-text-secondary font-mono">
          {formatMinutes(leg.total_fatigue_minutes)}
        </div>
        <div className="col-span-1 text-right font-mono">
          {leg.wait_time_minutes > 0 ? (
            <span className="text-risk-orange">{formatMinutes(leg.wait_time_minutes)}</span>
          ) : (
            <span className="text-green-400">Ready</span>
          )}
        </div>
        <div className="col-span-1 flex justify-center">
          <SecurityBadge security={leg.to_security_status} size="sm" />
        </div>
        <div className="col-span-1 flex justify-center">
          <RiskBadge riskColor={riskColor} riskScore={leg.to_risk_score} showIcon={false} size="sm" />
        </div>
        <div className="col-span-2 flex items-center justify-center">
          {hasBreakdown && (
            <ChevronDown className={`h-4 w-4 text-text-secondary transition-transform ${expanded ? 'rotate-180' : ''}`} />
          )}
        </div>
      </button>

      {/* Desktop expanded breakdown */}
      {expanded && (leg.to_risk_breakdown || hotzone) && (
        <div className="hidden sm:block px-3 pb-3 pt-0 border-t border-border/50 bg-card/50">
          <div className="ml-[calc(6.25%+0.5rem)] mr-4 space-y-2 pt-2">
            <div className="flex items-center justify-between">
              <div className="text-[10px] uppercase tracking-wider text-text-secondary/60 font-semibold">
                Destination Intel — {leg.to_system}
              </div>
              <Link
                href={`/map?system=${encodeURIComponent(leg.to_system)}`}
                className="flex items-center gap-1 px-2 py-0.5 text-[10px] font-medium rounded
                  bg-primary/15 text-primary/80 border border-primary/20
                  hover:bg-primary/25 hover:text-primary transition-colors"
                onClick={(e) => e.stopPropagation()}
              >
                <MapIcon className="h-3 w-3" />
                Map
              </Link>
            </div>
            {leg.to_risk_breakdown && (
              <div className="grid grid-cols-3 gap-4">
                <div className="flex items-center gap-2">
                  <Shield className="h-3.5 w-3.5 text-cyan-400" />
                  <span className="text-xs text-text-secondary">Security</span>
                  <span className="text-xs font-mono text-text ml-auto">{leg.to_risk_breakdown.security_component.toFixed(1)}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Crosshair className="h-3.5 w-3.5 text-orange-400" />
                  <span className="text-xs text-text-secondary">Kills</span>
                  <span className="text-xs font-mono text-text ml-auto">{leg.to_risk_breakdown.kills_component.toFixed(1)}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Skull className="h-3.5 w-3.5 text-red-400" />
                  <span className="text-xs text-text-secondary">Pods</span>
                  <span className="text-xs font-mono text-text ml-auto">{leg.to_risk_breakdown.pods_component.toFixed(1)}</span>
                </div>
              </div>
            )}
            {leg.to_zkill_stats && (leg.to_zkill_stats.recent_kills > 0 || leg.to_zkill_stats.recent_pods > 0) && (
              <div className="flex gap-4 pt-1.5 border-t border-border/30">
                <div className="flex items-center gap-1.5">
                  <Crosshair className="h-3 w-3 text-orange-400/70" />
                  <span className="text-xs text-text-secondary">
                    <span className="font-mono font-medium text-text">{leg.to_zkill_stats.recent_kills}</span> kills (24h)
                  </span>
                </div>
                <div className="flex items-center gap-1.5">
                  <Skull className="h-3 w-3 text-red-400/70" />
                  <span className="text-xs text-text-secondary">
                    <span className="font-mono font-medium text-text">{leg.to_zkill_stats.recent_pods}</span> pods (24h)
                  </span>
                </div>
              </div>
            )}
            {/* Hotzone intel — gate camp + trend */}
            {hotzone && (hotzone.kills_current + hotzone.pods_current) > 0 && (
              <div className="flex flex-wrap gap-3 pt-1.5 border-t border-border/30">
                {hotzone.gate_camp_likely && (
                  <div className="flex items-center gap-1.5">
                    <AlertTriangle className="h-3 w-3 text-red-400" />
                    <span className="text-xs font-medium text-red-400">Gate Camp Likely</span>
                  </div>
                )}
                <div className="flex items-center gap-1.5">
                  {hotzone.trend > 1.0 ? (
                    <TrendingUp className="h-3 w-3 text-orange-400" />
                  ) : (
                    <TrendingDown className="h-3 w-3 text-green-400" />
                  )}
                  <span className="text-xs text-text-secondary">
                    {hotzone.trend > 1.0 ? 'Heating up' : 'Cooling down'}
                    <span className="text-text-secondary/60"> ({hotzone.trend.toFixed(1)}x)</span>
                  </span>
                </div>
                {hotzone.predicted_1hr > 0 && (
                  <span className="text-xs text-text-secondary">
                    ~{hotzone.predicted_1hr} kills predicted (1h)
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Gate camp inline warning — visible without expanding */}
      {!expanded && hotzone?.gate_camp_likely && (
        <div className="hidden sm:flex items-center gap-1.5 px-3 pb-2 ml-[calc(6.25%+0.5rem)]">
          <AlertTriangle className="h-3 w-3 text-red-400" />
          <span className="text-[10px] font-medium text-red-400">Gate camp likely in {leg.to_system}</span>
        </div>
      )}

      {/* Mobile card */}
      <div className="sm:hidden px-3 py-2.5 border-t border-border space-y-1.5">
        <div className="flex items-center gap-2 text-sm">
          <span className="text-text-secondary font-mono">{idx + 1}.</span>
          <span className="text-text font-medium truncate">{leg.from_system}</span>
          <span className="text-text-secondary">&rarr;</span>
          <span className="text-text font-medium truncate">{leg.to_system}</span>
          <SecurityBadge security={leg.to_security_status} size="sm" />
        </div>
        {leg.to_region_name && (
          <div className="text-xs text-text-secondary ml-6">{leg.to_region_name}</div>
        )}
        <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
          <div className="flex justify-between">
            <span className="text-text-secondary">Distance</span>
            <span className="text-blue-400 font-mono">{leg.distance_ly.toFixed(1)} LY</span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-secondary">Fuel</span>
            <span className="text-yellow-400 font-mono">{leg.fuel_required.toLocaleString()}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-secondary">Fatigue</span>
            <span className="text-text-secondary font-mono">{formatMinutes(leg.total_fatigue_minutes)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-secondary">Wait</span>
            {leg.wait_time_minutes > 0 ? (
              <span className="text-risk-orange font-mono">{formatMinutes(leg.wait_time_minutes)}</span>
            ) : (
              <span className="text-green-400 font-mono">Ready</span>
            )}
          </div>
          <div className="flex justify-between">
            <span className="text-text-secondary">Risk</span>
            <RiskBadge riskColor={riskColor} riskScore={leg.to_risk_score} showIcon={false} size="sm" />
          </div>
          {leg.to_has_npc_station && (
            <div className="flex justify-between">
              <span className="text-text-secondary">Station</span>
              <span className="text-green-400 font-mono flex items-center gap-1"><Building2 className="h-3 w-3" /> Yes</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function RoutePageContent() {
  const searchParams = useSearchParams();

  const [waypoints, setWaypoints] = useState<Waypoint[]>(() => {
    const from = searchParams.get('from') ?? '';
    const to = searchParams.get('to') ?? '';
    const via = searchParams.get('via');
    const intermediates = via ? via.split(',').filter(Boolean) : [];
    return [
      { id: generateWaypointId(), system: from },
      ...intermediates.map((s) => ({ id: generateWaypointId(), system: s })),
      { id: generateWaypointId(), system: to },
    ];
  });

  const [avoidSystems, setAvoidSystems] = useState<string[]>(() => {
    const avoid = searchParams.get('avoid');
    return avoid ? avoid.split(',').filter(Boolean) : [];
  });
  const [profile, setProfile] = useState<RouteProfile>(() => {
    const p = searchParams.get('profile') as RouteProfile | null;
    return p && p in ROUTE_PROFILES ? p : 'safer';
  });
  const [includeBridges, setIncludeBridges] = useState(
    () => searchParams.get('bridges') === '1'
  );
  const [includeThera, setIncludeThera] = useState(
    () => searchParams.get('thera') === '1'
  );
  const [shouldFetch, setShouldFetch] = useState(
    () => !!(searchParams.get('from') && searchParams.get('to'))
  );

  // Capital jump drive state
  const [capitalMode, setCapitalMode] = useState(
    () => searchParams.get('capital') === '1'
  );
  const [selectedHull, setSelectedHull] = useState(() => {
    const hull = searchParams.get('hull');
    return hull && hull in HULLS ? hull : 'Rhea';
  });
  // Fuel type is auto-determined by hull — no manual override needed
  const [jdc, setJdc] = useState(() => {
    const v = searchParams.get('jdc');
    const n = v ? Number(v) : NaN;
    return n >= 0 && n <= 5 ? n : 5;
  });
  const [jfc, setJfc] = useState(() => {
    const v = searchParams.get('jfc');
    const n = v ? Number(v) : NaN;
    return n >= 0 && n <= 5 ? n : 5;
  });
  const [preferStations, setPreferStations] = useState(true);
  const [includePochven, setIncludePochven] = useState(
    () => searchParams.get('pochven') === '1'
  );
  const [optionsOpen, setOptionsOpen] = useState(false);

  // Share route state
  const [copied, setCopied] = useState(false);
  const autoTriggered = useRef(false);
  const [jumpResult, setJumpResult] = useState<JumpRouteResponse | null>(null);
  const [jumpLoading, setJumpLoading] = useState(false);
  const [jumpError, setJumpError] = useState<Error | null>(null);

  // Fetch hotzones for jump destination warnings (same pattern as RouteResult)
  const { data: jumpHotzoneData } = useQuery<HotzoneResponse>({
    queryKey: ['hotzones-jump-check'],
    queryFn: () => GatekeeperAPI.getHotzones(1, 50),
    staleTime: 60_000,
    refetchInterval: 60_000,
    enabled: capitalMode && jumpResult != null,
  });

  // Build hotzone lookup by system name for jump destinations
  const jumpHotzoneBySystem = useMemo(() => {
    const map = new Map<string, HotzoneSystemData>();
    for (const hz of jumpHotzoneData?.systems ?? []) {
      map.set(hz.system_name, hz);
    }
    return map;
  }, [jumpHotzoneData]);

  // Find jump destinations that are active hotzones
  const jumpHotzoneWarnings = useMemo(() => {
    if (!jumpResult || !jumpHotzoneData) return [];
    const destNames = new Set(jumpResult.legs.map((l) => l.to_system));
    return jumpHotzoneData.systems.filter(
      (hz) => destNames.has(hz.system_name) && (hz.kills_current + hz.pods_current) >= 3
    );
  }, [jumpResult, jumpHotzoneData]);

  // Max and avg risk across jump destinations
  const jumpRiskStats = useMemo(() => {
    if (!jumpResult || jumpResult.legs.length === 0) return { max: 0, avg: 0 };
    const scores = jumpResult.legs.map((l) => l.to_risk_score ?? 0);
    const max = Math.max(...scores);
    const avg = scores.reduce((a, b) => a + b, 0) / scores.length;
    return { max: Math.round(max * 10) / 10, avg: Math.round(avg * 10) / 10 };
  }, [jumpResult]);

  const hullInfo = HULLS[selectedHull] ?? { category: 'jump_freighter' as CapitalShipType, fuel: 'nitrogen' as FuelType };
  const fuelType = hullInfo.fuel;

  // Compute max jump range for map display
  const maxRangeLy = useMemo(() => {
    const baseRange = BASE_RANGE[hullInfo.category] ?? 5.0;
    return baseRange * (1.0 + 0.25 * jdc);
  }, [hullInfo.category, jdc]);

  // Add waypoint from map click
  const handleMapAddWaypoint = useCallback((systemName: string) => {
    setWaypoints((prev) => {
      // Insert before destination (last waypoint)
      const newWp: Waypoint = { id: generateWaypointId(), system: systemName };
      const copy = [...prev];
      copy.splice(copy.length - 1, 0, newWp);
      return copy;
    });
    setShouldFetch(false);
  }, []);

  // Build shareable URL from current route state
  const buildShareUrl = useCallback(() => {
    const url = new URL(window.location.origin + '/route');
    const from = waypoints[0]?.system;
    const to = waypoints[waypoints.length - 1]?.system;
    if (from) url.searchParams.set('from', from);
    if (to) url.searchParams.set('to', to);

    // Intermediate waypoints
    if (waypoints.length > 2) {
      const via = waypoints.slice(1, -1).map((wp) => wp.system).filter(Boolean);
      if (via.length > 0) url.searchParams.set('via', via.join(','));
    }

    if (capitalMode) {
      url.searchParams.set('capital', '1');
      url.searchParams.set('hull', selectedHull);
      if (jdc !== 5) url.searchParams.set('jdc', jdc.toString());
      if (jfc !== 5) url.searchParams.set('jfc', jfc.toString());
    } else {
      if (profile !== 'safer') url.searchParams.set('profile', profile);
      if (includeBridges) url.searchParams.set('bridges', '1');
      if (includeThera) url.searchParams.set('thera', '1');
      if (includePochven) url.searchParams.set('pochven', '1');
    }

    if (avoidSystems.length > 0) {
      url.searchParams.set('avoid', avoidSystems.join(','));
    }

    return url.toString();
  }, [waypoints, capitalMode, selectedHull, jdc, jfc, profile, includeBridges, includeThera, includePochven, avoidSystems]);

  const handleShareRoute = useCallback(async () => {
    const url = buildShareUrl();
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for non-HTTPS or denied permission
      const textarea = document.createElement('textarea');
      textarea.value = url;
      textarea.style.position = 'fixed';
      textarea.style.opacity = '0';
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [buildShareUrl]);

  const systems = useMemo(
    () => waypoints.map((wp) => wp.system),
    [waypoints]
  );

  const allFilled = useMemo(
    () => waypoints.length >= 2 && waypoints.every((wp) => wp.system.length > 0),
    [waypoints]
  );

  const {
    route,
    isLoading,
    error,
    segmentErrors,
    refetchAll,
  } = useMultiRoute({
    systems,
    profile,
    bridges: includeBridges,
    thera: includeThera,
    pochven: includePochven,
    avoid: avoidSystems,
    enabled: shouldFetch && allFilled,
  });

  const handleHullChange = useCallback((hull: string) => {
    if (hull.startsWith('---')) return;
    setSelectedHull(hull);
  }, []);

  const handleJumpCalculate = useCallback(async () => {
    if (!allFilled) return;
    const fromSys = waypoints[0].system;
    const toSys = waypoints[waypoints.length - 1].system;
    const midpoints = waypoints.length > 2
      ? waypoints.slice(1, -1).map((wp) => wp.system).filter(Boolean)
      : undefined;

    setJumpLoading(true);
    setJumpError(null);
    try {
      const res = await GatekeeperAPI.getJumpRoute(
        fromSys,
        toSys,
        hullInfo.category,
        jdc,
        jfc,
        fuelType,
        midpoints,
        preferStations
      );
      setJumpResult(res);
    } catch (err) {
      setJumpError(err instanceof Error ? err : new Error('Jump route failed'));
    } finally {
      setJumpLoading(false);
    }
  }, [allFilled, waypoints, hullInfo.category, jdc, jfc, fuelType, preferStations]);

  // Auto-trigger calculation when loaded from a shared URL
  useEffect(() => {
    if (autoTriggered.current) return;
    const hasFrom = searchParams.get('from');
    const hasTo = searchParams.get('to');
    if (!hasFrom || !hasTo) return;
    autoTriggered.current = true;
    // Capital mode auto-trigger needs a tick for state to settle
    if (searchParams.get('capital') === '1') {
      const timer = setTimeout(() => handleJumpCalculate(), 0);
      return () => clearTimeout(timer);
    }
    // Gate mode: shouldFetch is already true from init
  }, [searchParams, handleJumpCalculate]);

  const handleSearch = useCallback(() => {
    if (allFilled) {
      if (capitalMode) {
        handleJumpCalculate();
      } else {
        setShouldFetch(true);
        refetchAll();
      }
    }
  }, [allFilled, capitalMode, handleJumpCalculate, refetchAll]);

  const handleWaypointsChange = useCallback((newWaypoints: Waypoint[]) => {
    setWaypoints(newWaypoints);
    setShouldFetch(false);
  }, []);

  const handleAvoidChange = useCallback((systems: string[]) => {
    setAvoidSystems(systems);
    setShouldFetch(false);
  }, []);

  const displayError = error ?? segmentErrors.find((e) => e !== null) ?? null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-text">Route Planner</h1>
        <p className="text-text-secondary mt-1">
          Plan multi-stop routes with waypoints. Drag to reorder, paste routes, or avoid dangerous systems.
        </p>
      </div>

      {/* Waypoint List + Options */}
      <Card>
        <div className="space-y-4">
          <WaypointList
            waypoints={waypoints}
            onChange={handleWaypointsChange}
            avoidSystems={avoidSystems}
            onAvoidChange={handleAvoidChange}
          />

          {/* Options row */}
          <div className="space-y-3 pt-2 border-t border-border">
            {/* Main mode toggles — always visible */}
            <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
              <Toggle
                checked={capitalMode}
                onChange={(v) => {
                  setCapitalMode(v);
                  setJumpResult(null);
                  setJumpError(null);
                }}
                label="Jump Drive"
              />
              {!capitalMode && (
                <div className="max-w-xs flex-1 min-w-[160px]">
                  <Select
                    value={profile}
                    onChange={(e) => setProfile(e.target.value as RouteProfile)}
                    options={profileOptions}
                  />
                </div>
              )}
            </div>

            {/* Collapsible options dropdown */}
            <div>
              <button
                type="button"
                onClick={() => setOptionsOpen(!optionsOpen)}
                className="flex items-center gap-1.5 text-xs text-text-secondary hover:text-text transition-colors"
              >
                <Settings2 className="h-3.5 w-3.5" />
                <span>Route Options</span>
                {optionsOpen ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
              </button>

              {optionsOpen && (
                <div className="mt-3 space-y-3 pl-1">
                  {!capitalMode && (
                    <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
                      <Toggle
                        checked={includeBridges}
                        onChange={setIncludeBridges}
                        label="Jump Bridges"
                      />
                      <Toggle
                        checked={includeThera}
                        onChange={setIncludeThera}
                        label="Thera"
                      />
                      <Toggle
                        checked={includePochven}
                        onChange={setIncludePochven}
                        label="Pochven"
                      />
                    </div>
                  )}
                  {capitalMode && (
                    <>
                      <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
                        <Toggle
                          checked={preferStations}
                          onChange={setPreferStations}
                          label="Prefer Stations"
                        />
                      </div>
                      <div className="max-w-sm">
                        <Select
                          label="Ship"
                          options={SHIP_OPTIONS}
                          value={selectedHull}
                          onChange={(e) => handleHullChange(e.target.value)}
                        />
                      </div>
                      <div className="grid grid-cols-2 max-w-sm gap-3">
                        <Select
                          label="JDC Level"
                          options={SKILL_OPTIONS}
                          value={jdc.toString()}
                          onChange={(e) => setJdc(Number(e.target.value))}
                        />
                        <Select
                          label="JFC Level"
                          options={SKILL_OPTIONS}
                          value={jfc.toString()}
                          onChange={(e) => setJfc(Number(e.target.value))}
                        />
                      </div>
                      <div className="text-xs text-text-secondary">
                        Fuel: {FUEL_LABELS[fuelType]} · Max range: {maxRangeLy.toFixed(1)} LY
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Search + Share Buttons */}
          <div className="flex flex-wrap items-center gap-2">
            <Button
              onClick={handleSearch}
              disabled={!allFilled || (capitalMode ? jumpLoading : isLoading)}
              loading={capitalMode ? jumpLoading : isLoading}
              className="w-full sm:w-auto"
            >
              {capitalMode ? (
                <Rocket className="mr-2 h-4 w-4" />
              ) : (
                <Route className="mr-2 h-4 w-4" />
              )}
              {capitalMode ? 'Calculate Jump Route' : 'Calculate Route'}
            </Button>

            {/* Share Route — visible after results load */}
            {((!capitalMode && route) || (capitalMode && jumpResult)) && (
              <button
                type="button"
                onClick={handleShareRoute}
                className="inline-flex items-center gap-1.5 px-3 py-2 text-sm rounded-lg border border-border text-text-secondary hover:text-text hover:bg-card-hover transition-colors"
                title="Copy shareable route URL"
              >
                {copied ? (
                  <>
                    <Check className="h-4 w-4 text-green-400" />
                    <span className="text-green-400">Copied!</span>
                  </>
                ) : (
                  <>
                    <Share2 className="h-4 w-4" />
                    <span>Share Route</span>
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </Card>

      {/* Error State */}
      {!capitalMode && displayError && (
        <ErrorMessage
          title="Route calculation failed"
          message={getUserFriendlyError(displayError)}
          onRetry={handleSearch}
        />
      )}
      {capitalMode && jumpError && (
        <ErrorMessage
          title="Jump route calculation failed"
          message={getUserFriendlyError(jumpError)}
          onRetry={handleSearch}
        />
      )}

      {/* Route loading skeleton */}
      {!capitalMode && isLoading && (
        <Card className="p-4 space-y-4">
          <div className="flex items-center gap-3">
            <Skeleton variant="rectangular" className="h-8 w-32" />
            <Skeleton variant="text" className="h-5 w-48" />
          </div>
          <div className="grid grid-cols-4 gap-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} variant="rectangular" className="h-16" />
            ))}
          </div>
          <div className="space-y-2">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} variant="text" className="h-8" />
            ))}
          </div>
        </Card>
      )}

      {/* Route map — always visible in gate mode */}
      {!capitalMode && route && <RouteMap route={route} />}

      {/* Gate route results */}
      {!capitalMode && route && <RouteResult route={route} />}

      {/* Jump range map */}
      {capitalMode && (
        <JumpRangeMap
          originSystem={waypoints[0]?.system || undefined}
          destSystem={waypoints[waypoints.length - 1]?.system || undefined}
          maxRangeLy={maxRangeLy}
          waypoints={waypoints.map((wp) => wp.system).filter(Boolean)}
          onAddWaypoint={handleMapAddWaypoint}
          preferStations={preferStations}
        />
      )}

      {/* Capital jump results */}
      {capitalMode && jumpResult && (
        <div className="space-y-4">
          {/* Top actions */}
          <div className="flex justify-end">
            <Link
              href={`/map?from=${encodeURIComponent(jumpResult.from_system)}&to=${encodeURIComponent(jumpResult.to_system)}`}
              className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium rounded-lg
                bg-primary/20 text-primary border border-primary/30
                hover:bg-primary/30 hover:border-primary/50
                transition-colors"
            >
              <MapIcon className="h-4 w-4" />
              View on Map
            </Link>
          </div>

          {/* Summary cards */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <Card className="text-center">
              <div className="text-xs text-text-secondary uppercase mb-1">Jumps</div>
              <div className="text-xl font-bold text-text">{jumpResult.total_jumps}</div>
            </Card>
            <Card className="text-center">
              <div className="text-xs text-text-secondary uppercase mb-1">Distance</div>
              <div className="text-xl font-bold text-blue-400">
                {jumpResult.total_distance_ly.toFixed(2)} LY
              </div>
            </Card>
            <Card className="text-center">
              <div className="text-xs text-text-secondary uppercase mb-1">
                <Fuel className="h-3 w-3 inline mr-1" />
                Fuel
              </div>
              <div className="text-xl font-bold text-yellow-400">
                {jumpResult.total_fuel.toLocaleString()}
              </div>
              <div className="text-xs text-text-secondary mt-0.5">
                {jumpResult.fuel_type_name}
              </div>
            </Card>
            <Card className="text-center">
              <div className="text-xs text-text-secondary uppercase mb-1">
                <Clock className="h-3 w-3 inline mr-1" />
                Travel Time
              </div>
              <div className="text-xl font-bold text-text">
                {formatMinutes(jumpResult.total_travel_time_minutes)}
              </div>
            </Card>
            <Card className="text-center">
              <div className="text-xs text-text-secondary uppercase mb-1">
                <Gauge className="h-3 w-3 inline mr-1" />
                Max Risk
              </div>
              <div className="flex justify-center">
                <RiskBadge riskColor={getJumpRiskColor(jumpRiskStats.max)} riskScore={jumpRiskStats.max} showIcon={false} size="lg" />
              </div>
            </Card>
            <Card className="text-center">
              <div className="text-xs text-text-secondary uppercase mb-1">
                <Gauge className="h-3 w-3 inline mr-1" />
                Avg Risk
              </div>
              <div className="flex justify-center">
                <RiskBadge riskColor={getJumpRiskColor(jumpRiskStats.avg)} riskScore={jumpRiskStats.avg} showIcon={false} size="lg" />
              </div>
            </Card>
          </div>

          {/* Fuel cost */}
          {jumpResult.fuel_unit_cost > 0 && (
            <Card>
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm text-text-secondary">Fuel Cost (Jita Sell)</div>
                  <div className="text-xs text-text-secondary mt-0.5">
                    {jumpResult.total_fuel.toLocaleString()} × {formatIsk(jumpResult.fuel_unit_cost)} per unit
                  </div>
                </div>
                <div className="text-xl font-bold text-green-400">
                  {formatIsk(jumpResult.total_fuel_cost)} ISK
                </div>
              </div>
            </Card>
          )}

          {/* Hotzone warning for jump destinations */}
          {jumpHotzoneWarnings.length > 0 && (
            <div className="flex items-start gap-3 bg-orange-500/10 border border-orange-500/30 rounded-lg px-4 py-3">
              <Flame className="h-5 w-5 text-orange-400 shrink-0 mt-0.5" />
              <div>
                <div className="text-sm font-medium text-orange-400">
                  Active Hotzones at Jump Destinations
                </div>
                <div className="text-xs text-text-secondary mt-1">
                  {jumpHotzoneWarnings.length === 1
                    ? 'A destination system has significant recent kill activity. Light cyno with caution.'
                    : `${jumpHotzoneWarnings.length} destination systems have significant recent kill activity. Light cynos with caution.`}
                </div>
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {jumpHotzoneWarnings.map((hz) => (
                    <span key={hz.system_name} className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded bg-orange-500/20 text-orange-400 border border-orange-500/30">
                      {hz.system_name} — {hz.kills_current + hz.pods_current} kills
                      {hz.gate_camp_likely ? ' (camp)' : ''}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Jump strip — arc visualization */}
          <JumpStrip legs={jumpResult.legs} fuelTypeName={jumpResult.fuel_type_name} />

          {/* Fatigue warning */}
          {jumpResult.total_fatigue_minutes > 60 && (
            <div className="bg-risk-orange/10 border border-risk-orange/30 rounded-lg px-3 py-2">
              <div className="text-xs font-medium text-risk-orange">
                High Jump Fatigue
              </div>
              <div className="text-xs text-text-secondary mt-0.5">
                Total fatigue: {formatMinutes(jumpResult.total_fatigue_minutes)}. Plan rest stops.
              </div>
            </div>
          )}

          {/* Per-leg table */}
          {jumpResult.legs.length > 0 && (
            <div className="border border-border rounded-lg overflow-hidden">
              {/* Desktop table header */}
              <div className="hidden sm:grid grid-cols-16 gap-2 px-3 py-2.5 bg-card text-xs text-text-secondary uppercase font-semibold min-w-[800px]">
                <div className="col-span-1 text-center">#</div>
                <div className="col-span-2">From</div>
                <div className="col-span-3">To</div>
                <div className="col-span-2">Region</div>
                <div className="col-span-1 text-right">LY</div>
                <div className="col-span-1 text-right">Fuel</div>
                <div className="col-span-1 text-right">Fatigue</div>
                <div className="col-span-1 text-right">Wait</div>
                <div className="col-span-1 text-center">Sec</div>
                <div className="col-span-1 text-center">Risk</div>
                <div className="col-span-2 text-center">Info</div>
              </div>
              {jumpResult.legs.map((leg, idx) => (
                <JumpLegRow key={`${leg.from_system}-${leg.to_system}`} leg={leg} idx={idx} hotzone={jumpHotzoneBySystem.get(leg.to_system)} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Empty State */}
      {!capitalMode && !route && !isLoading && !displayError && (
        <Card className="text-center py-12">
          <Route className="h-12 w-12 text-text-secondary mx-auto mb-4" />
          <p className="text-text-secondary">
            Enter origin and destination systems to calculate a route
          </p>
        </Card>
      )}
      {capitalMode && !jumpResult && !jumpLoading && !jumpError && (
        <Card className="text-center py-12">
          <Rocket className="h-12 w-12 text-text-secondary mx-auto mb-4" />
          <p className="text-text-secondary">
            Enter origin and destination for capital jump route
          </p>
          <p className="text-xs text-text-secondary mt-2">
            Jump freighters, carriers, dreads, supers, titans, and black ops
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
        <div className="max-w-4xl mx-auto px-4 py-8 space-y-4">
          <Skeleton variant="rectangular" className="h-12 w-64" />
          <Card className="p-4 space-y-3">
            <Skeleton variant="text" className="h-10 w-full" />
            <Skeleton variant="text" className="h-10 w-full" />
            <Skeleton variant="rectangular" className="h-10 w-40" />
          </Card>
        </div>
      }
    >
      <RoutePageContent />
    </Suspense>
  );
}
