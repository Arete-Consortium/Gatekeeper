'use client';

import { Suspense, useState, useMemo, useCallback } from 'react';
import { useSearchParams } from 'next/navigation';
import { useMultiRoute } from '@/hooks';
import { Card, Button, Toggle, Skeleton } from '@/components/ui';
import { Select } from '@/components/ui/Select';
import { RouteResult, WaypointList, generateWaypointId } from '@/components/route';
import type { Waypoint } from '@/components/route';
import { ROUTE_PROFILES } from '@/lib/utils';
import type { RouteProfile, CapitalShipType, FuelType, JumpRouteResponse } from '@/lib/types';
import { GatekeeperAPI } from '@/lib/api';
import { Route, Loader2, Rocket, Fuel, Clock } from 'lucide-react';
import { ErrorMessage, getUserFriendlyError } from '@/components/ui';
import { JumpStrip } from '@/components/route/JumpStrip';
import dynamic from 'next/dynamic';

const JumpRangeMap = dynamic(
  () => import('@/components/route/JumpRangeMap').then((m) => m.JumpRangeMap),
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

function RoutePageContent() {
  const searchParams = useSearchParams();

  const [waypoints, setWaypoints] = useState<Waypoint[]>(() => {
    const from = searchParams.get('from') ?? '';
    const to = searchParams.get('to') ?? '';
    return [
      { id: generateWaypointId(), system: from },
      { id: generateWaypointId(), system: to },
    ];
  });

  const [avoidSystems, setAvoidSystems] = useState<string[]>([]);
  const [profile, setProfile] = useState<RouteProfile>(() => {
    const p = searchParams.get('profile') as RouteProfile | null;
    return p && p in ROUTE_PROFILES ? p : 'safer';
  });
  const [includeBridges, setIncludeBridges] = useState(false);
  const [includeThera, setIncludeThera] = useState(false);
  const [shouldFetch, setShouldFetch] = useState(
    () => !!(searchParams.get('from') && searchParams.get('to'))
  );

  // Capital jump drive state
  const [capitalMode, setCapitalMode] = useState(false);
  const [selectedHull, setSelectedHull] = useState('Rhea');
  // Fuel type is auto-determined by hull — no manual override needed
  const [jdc, setJdc] = useState(5);
  const [jfc, setJfc] = useState(5);
  const [preferStations, setPreferStations] = useState(true);
  const [jumpResult, setJumpResult] = useState<JumpRouteResponse | null>(null);
  const [jumpLoading, setJumpLoading] = useState(false);
  const [jumpError, setJumpError] = useState<Error | null>(null);

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
          <div className="space-y-4 pt-2 border-t border-border">
            {/* Toggles — consistent horizontal row */}
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
                <>
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
                </>
              )}
              {capitalMode && (
                <Toggle
                  checked={preferStations}
                  onChange={setPreferStations}
                  label="Prefer Stations"
                />
              )}
            </div>

            {/* Gate route profile */}
            {!capitalMode && (
              <div className="max-w-xs">
                <Select
                  label="Route Profile"
                  value={profile}
                  onChange={(e) => setProfile(e.target.value as RouteProfile)}
                  options={profileOptions}
                />
              </div>
            )}

            {/* Jump drive options */}
            {capitalMode && (
              <div className="space-y-3">
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
              </div>
            )}
          </div>

          {/* Search Button */}
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
          {/* Summary cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
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
            <div className="border border-border rounded-lg overflow-x-auto">
              {/* Desktop table header */}
              <div className="hidden sm:grid grid-cols-12 gap-2 px-3 py-2.5 bg-card text-xs text-text-secondary uppercase font-semibold min-w-[650px]">
                <div className="col-span-1 text-center">#</div>
                <div className="col-span-3">From</div>
                <div className="col-span-3">To</div>
                <div className="col-span-1 text-right">LY</div>
                <div className="col-span-1 text-right">Fuel</div>
                <div className="col-span-1 text-right">Fatigue</div>
                <div className="col-span-2 text-right">Wait</div>
              </div>
              {jumpResult.legs.map((leg, idx) => (
                <div key={`${leg.from_system}-${leg.to_system}`}>
                  {/* Desktop table row */}
                  <div className="hidden sm:grid grid-cols-12 gap-2 px-3 py-2.5 border-t border-border hover:bg-card-hover transition-colors items-center min-w-[650px] text-sm">
                    <div className="col-span-1 text-center text-text-secondary font-mono">
                      {idx + 1}
                    </div>
                    <div className="col-span-3 text-text font-medium truncate" title={leg.from_system}>
                      {leg.from_system}
                    </div>
                    <div className="col-span-3 text-text font-medium truncate" title={leg.to_system}>
                      {leg.to_system}
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
                    <div className="col-span-2 text-right font-mono">
                      {leg.wait_time_minutes > 0 ? (
                        <span className="text-risk-orange">{formatMinutes(leg.wait_time_minutes)}</span>
                      ) : (
                        <span className="text-green-400">Ready</span>
                      )}
                    </div>
                  </div>
                  {/* Mobile card */}
                  <div className="sm:hidden px-3 py-2.5 border-t border-border space-y-1.5">
                    <div className="flex items-center gap-2 text-sm">
                      <span className="text-text-secondary font-mono">{idx + 1}.</span>
                      <span className="text-text font-medium truncate">{leg.from_system}</span>
                      <span className="text-text-secondary">&rarr;</span>
                      <span className="text-text font-medium truncate">{leg.to_system}</span>
                    </div>
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
                    </div>
                  </div>
                </div>
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
