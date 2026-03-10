'use client';

import { useQueries } from '@tanstack/react-query';
import { useMemo } from 'react';
import { GatekeeperAPI } from '@/lib/api';
import type { RouteResponse, RouteHop, RouteProfile } from '@/lib/types';

interface UseMultiRouteOptions {
  /** Ordered list of system names (origin, waypoints..., destination) */
  systems: string[];
  profile?: RouteProfile;
  bridges?: boolean;
  thera?: boolean;
  enabled?: boolean;
}

export interface MultiRouteResult {
  /** Combined route across all segments */
  route: RouteResponse | null;
  /** Individual segment routes */
  segments: (RouteResponse | null)[];
  /** Whether any segment is loading */
  isLoading: boolean;
  /** First error encountered */
  error: Error | null;
  /** Per-segment errors */
  segmentErrors: (Error | null)[];
  /** Refetch all segments */
  refetchAll: () => void;
}

/**
 * Calculate routes for multiple segments and merge them.
 * Given systems [A, B, C, D], calculates A→B, B→C, C→D and merges.
 */
export function useMultiRoute({
  systems,
  profile = 'safer',
  bridges = false,
  thera = false,
  enabled = true,
}: UseMultiRouteOptions): MultiRouteResult {
  // Build segment pairs: [A,B], [B,C], [C,D]
  const pairs = useMemo(() => {
    const validSystems = systems.filter((s) => s.length > 0);
    if (validSystems.length < 2) return [];
    const result: [string, string][] = [];
    for (let i = 0; i < validSystems.length - 1; i++) {
      result.push([validSystems[i], validSystems[i + 1]]);
    }
    return result;
  }, [systems]);

  const queries = useQueries({
    queries: pairs.map(([from, to]) => ({
      queryKey: ['route', from, to, profile, bridges, thera],
      queryFn: () => GatekeeperAPI.getRoute(from, to, profile, { bridges, thera }),
      enabled: enabled && from.length > 0 && to.length > 0,
      staleTime: 60 * 1000,
      retry: false,
    })),
  });

  const result = useMemo((): MultiRouteResult => {
    const segments = queries.map((q) => q.data ?? null);
    const segmentErrors = queries.map((q) => (q.error as Error) ?? null);
    const isLoading = queries.some((q) => q.isLoading);
    const firstError = segmentErrors.find((e) => e !== null) ?? null;

    // Merge segments into combined route
    let route: RouteResponse | null = null;
    const validSegments = segments.filter((s): s is RouteResponse => s !== null);

    if (validSegments.length > 0 && validSegments.length === pairs.length) {
      const combinedPath: RouteHop[] = [];
      let totalJumps = 0;
      let totalDistance = 0;
      let totalCost = 0;
      let maxRisk = 0;
      let bridgesUsed = 0;
      let theraUsed = 0;
      const allRisks: number[] = [];

      for (let i = 0; i < validSegments.length; i++) {
        const seg = validSegments[i];
        // Skip first hop of subsequent segments (it's the same as last hop of previous)
        const hops = i === 0 ? seg.path : seg.path.slice(1);
        combinedPath.push(...hops);
        totalJumps += seg.total_jumps;
        totalDistance += seg.total_distance;
        totalCost += seg.total_cost;
        maxRisk = Math.max(maxRisk, seg.max_risk);
        bridgesUsed += seg.bridges_used;
        theraUsed += seg.thera_used;
        seg.path.forEach((h) => allRisks.push(h.risk_score));
      }

      const avgRisk = allRisks.length > 0
        ? allRisks.reduce((a, b) => a + b, 0) / allRisks.length
        : 0;

      route = {
        path: combinedPath,
        total_jumps: totalJumps,
        total_distance: totalDistance,
        total_cost: totalCost,
        max_risk: maxRisk,
        avg_risk: avgRisk,
        profile: validSegments[0].profile,
        bridges_used: bridgesUsed,
        thera_used: theraUsed,
      };
    }

    return {
      route,
      segments,
      isLoading,
      error: firstError,
      segmentErrors,
      refetchAll: () => queries.forEach((q) => q.refetch()),
    };
  }, [queries, pairs]);

  return result;
}
