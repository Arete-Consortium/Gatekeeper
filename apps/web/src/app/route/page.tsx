'use client';

import { Suspense, useState, useMemo, useCallback } from 'react';
import { useSearchParams } from 'next/navigation';
import { useMultiRoute } from '@/hooks';
import { Card, Button, Toggle } from '@/components/ui';
import { Select } from '@/components/ui/Select';
import { RouteResult, WaypointList, generateWaypointId } from '@/components/route';
import type { Waypoint } from '@/components/route';
import { ROUTE_PROFILES } from '@/lib/utils';
import type { RouteProfile } from '@/lib/types';
import { Route, Loader2 } from 'lucide-react';
import { ErrorMessage, getUserFriendlyError } from '@/components/ui';

const profileOptions = Object.entries(ROUTE_PROFILES).map(([value, config]) => ({
  value,
  label: config.label,
}));

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

  const [profile, setProfile] = useState<RouteProfile>(() => {
    const p = searchParams.get('profile') as RouteProfile | null;
    return p && p in ROUTE_PROFILES ? p : 'safer';
  });
  const [includeBridges, setIncludeBridges] = useState(false);
  const [includeThera, setIncludeThera] = useState(false);
  const [shouldFetch, setShouldFetch] = useState(
    () => !!(searchParams.get('from') && searchParams.get('to'))
  );

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
    enabled: shouldFetch && allFilled,
  });

  const handleSearch = useCallback(() => {
    if (allFilled) {
      setShouldFetch(true);
      refetchAll();
    }
  }, [allFilled, refetchAll]);

  const handleWaypointsChange = useCallback((newWaypoints: Waypoint[]) => {
    setWaypoints(newWaypoints);
    setShouldFetch(false);
  }, []);

  // Find first segment with an error for display
  const displayError = error ?? segmentErrors.find((e) => e !== null) ?? null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-text">Route Planner</h1>
        <p className="text-text-secondary mt-1">
          Find the safest path between solar systems. Add waypoints to plan multi-stop routes.
        </p>
      </div>

      {/* Waypoint List */}
      <Card>
        <div className="space-y-4">
          <WaypointList
            waypoints={waypoints}
            onChange={handleWaypointsChange}
          />

          {/* Profile Selection */}
          <div className="grid sm:grid-cols-3 gap-4">
            <Select
              label="Route Profile"
              value={profile}
              onChange={(e) => setProfile(e.target.value as RouteProfile)}
              options={profileOptions}
            />

            <div className="flex items-end">
              <Toggle
                checked={includeBridges}
                onChange={setIncludeBridges}
                label="Include Jump Bridges"
              />
            </div>

            <div className="flex items-end">
              <Toggle
                checked={includeThera}
                onChange={setIncludeThera}
                label="Include Thera"
              />
            </div>
          </div>

          {/* Search Button */}
          <Button
            onClick={handleSearch}
            disabled={!allFilled || isLoading}
            loading={isLoading}
            className="w-full sm:w-auto"
          >
            <Route className="mr-2 h-4 w-4" />
            Calculate Route
          </Button>
        </div>
      </Card>

      {/* Error State */}
      {displayError && (
        <ErrorMessage
          title="Route calculation failed"
          message={getUserFriendlyError(displayError)}
          onRetry={handleSearch}
        />
      )}

      {/* Results */}
      {route && <RouteResult route={route} />}

      {/* Empty State */}
      {!route && !isLoading && !displayError && (
        <Card className="text-center py-12">
          <Route className="h-12 w-12 text-text-secondary mx-auto mb-4" />
          <p className="text-text-secondary">
            Enter origin and destination systems to calculate a route
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
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-text-secondary" />
        </div>
      }
    >
      <RoutePageContent />
    </Suspense>
  );
}
