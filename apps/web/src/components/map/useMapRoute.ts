'use client';

import { useState, useCallback, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { GatekeeperAPI } from '@/lib/api';
import type { RouteResponse, RouteProfile } from '@/lib/types';
import type { MapRoute, MapSystem } from './types';

/**
 * Selection mode for route planning
 */
export type RouteSelectionMode = 'idle' | 'origin' | 'destination';

/**
 * Route comparison entry
 */
export interface RouteComparison {
  profile: RouteProfile;
  route: RouteResponse | null;
  isLoading: boolean;
  error: Error | null;
}

/**
 * Options for the useMapRoute hook
 */
export interface UseMapRouteOptions {
  /** System lookup map for converting IDs to names */
  systems?: Map<number, MapSystem>;
  /** Whether to auto-compare all profiles */
  compareProfiles?: boolean;
  /** Include jump bridges in route calculation */
  bridges?: boolean;
  /** Include Thera connections in route calculation */
  thera?: boolean;
}

/**
 * Route state for the map
 */
export interface MapRouteState {
  /** Currently selected origin system ID */
  originId: number | null;
  /** Currently selected destination system ID */
  destinationId: number | null;
  /** Current selection mode */
  mode: RouteSelectionMode;
  /** Selected routing profile */
  profile: RouteProfile;
  /** Include jump bridges */
  bridges: boolean;
  /** Include Thera connections */
  thera: boolean;
}

/**
 * Return type for useMapRoute hook
 */
export interface UseMapRouteResult {
  /** Current route state */
  state: MapRouteState;

  /** Primary route (for selected profile) */
  route: RouteResponse | null;
  isLoading: boolean;
  error: Error | null;

  /** All profile comparisons (if compareProfiles enabled) */
  comparisons: RouteComparison[];

  /** Routes formatted for MapRoute overlay */
  mapRoutes: MapRoute[];

  /** Avoid systems */
  avoidSystems: Set<number>;
  addAvoidSystem: (systemId: number) => void;
  removeAvoidSystem: (systemId: number) => void;
  clearAvoidSystems: () => void;

  /** Actions */
  setMode: (mode: RouteSelectionMode) => void;
  setProfile: (profile: RouteProfile) => void;
  setBridges: (enabled: boolean) => void;
  setThera: (enabled: boolean) => void;
  selectSystem: (systemId: number) => void;
  setOrigin: (systemId: number | null) => void;
  setDestination: (systemId: number | null) => void;
  clearRoute: () => void;
  swapOriginDestination: () => void;

  /** Helpers */
  getSystemName: (systemId: number) => string | null;
  isSystemOnRoute: (systemId: number) => boolean;
}

/**
 * Profile colors for route display
 */
const PROFILE_COLORS: Record<RouteProfile, string> = {
  safer: '#32d74b',
  shortest: '#ffd60a',
  paranoid: '#30b0ff',
};

/**
 * Hook for managing route state on the universe map
 */
export function useMapRoute(options: UseMapRouteOptions = {}): UseMapRouteResult {
  const {
    systems,
    compareProfiles = false,
    bridges: defaultBridges = false,
    thera: defaultThera = false,
  } = options;

  // Route state
  const [originId, setOriginId] = useState<number | null>(null);
  const [destinationId, setDestinationId] = useState<number | null>(null);
  const [mode, setMode] = useState<RouteSelectionMode>('idle');
  const [profile, setProfile] = useState<RouteProfile>('safer');
  const [bridges, setBridges] = useState(defaultBridges);
  const [thera, setThera] = useState(defaultThera);
  const [avoidSystems, setAvoidSystems] = useState<Set<number>>(new Set());

  // Build system name lookup
  const systemNameLookup = useMemo(() => {
    const lookup = new Map<number, string>();

    // From systems Map (MapSystem format)
    if (systems) {
      systems.forEach((sys, id) => {
        lookup.set(id, sys.name);
      });
    }

    return lookup;
  }, [systems]);

  // Get system name helper
  const getSystemName = useCallback(
    (systemId: number): string | null => {
      return systemNameLookup.get(systemId) ?? null;
    },
    [systemNameLookup]
  );

  // Get origin/destination names for API calls
  const originName = originId ? getSystemName(originId) : null;
  const destinationName = destinationId ? getSystemName(destinationId) : null;

  // Primary route query
  const primaryQuery = useQuery<RouteResponse>({
    queryKey: ['mapRoute', originName, destinationName, profile, bridges, thera],
    queryFn: () =>
      GatekeeperAPI.getRoute(originName!, destinationName!, profile, {
        bridges,
        thera,
      }),
    enabled: !!originName && !!destinationName,
    staleTime: 60 * 1000,
    retry: false,
  });

  // Comparison queries (only if enabled and we have origin/destination)
  const saferQuery = useQuery<RouteResponse>({
    queryKey: ['mapRoute', originName, destinationName, 'safer', bridges, thera],
    queryFn: () =>
      GatekeeperAPI.getRoute(originName!, destinationName!, 'safer', {
        bridges,
        thera,
      }),
    enabled: compareProfiles && !!originName && !!destinationName && profile !== 'safer',
    staleTime: 60 * 1000,
    retry: false,
  });

  const shortestQuery = useQuery<RouteResponse>({
    queryKey: ['mapRoute', originName, destinationName, 'shortest', bridges, thera],
    queryFn: () =>
      GatekeeperAPI.getRoute(originName!, destinationName!, 'shortest', {
        bridges,
        thera,
      }),
    enabled: compareProfiles && !!originName && !!destinationName && profile !== 'shortest',
    staleTime: 60 * 1000,
    retry: false,
  });

  const paranoidQuery = useQuery<RouteResponse>({
    queryKey: ['mapRoute', originName, destinationName, 'paranoid', bridges, thera],
    queryFn: () =>
      GatekeeperAPI.getRoute(originName!, destinationName!, 'paranoid', {
        bridges,
        thera,
      }),
    enabled: compareProfiles && !!originName && !!destinationName && profile !== 'paranoid',
    staleTime: 60 * 1000,
    retry: false,
  });

  // Build comparisons array
  const comparisons = useMemo((): RouteComparison[] => {
    if (!compareProfiles) return [];

    return [
      {
        profile: 'safer',
        route: profile === 'safer' ? primaryQuery.data ?? null : saferQuery.data ?? null,
        isLoading: profile === 'safer' ? primaryQuery.isLoading : saferQuery.isLoading,
        error: profile === 'safer'
          ? primaryQuery.error as Error | null
          : saferQuery.error as Error | null,
      },
      {
        profile: 'shortest',
        route: profile === 'shortest' ? primaryQuery.data ?? null : shortestQuery.data ?? null,
        isLoading: profile === 'shortest' ? primaryQuery.isLoading : shortestQuery.isLoading,
        error: profile === 'shortest'
          ? primaryQuery.error as Error | null
          : shortestQuery.error as Error | null,
      },
      {
        profile: 'paranoid',
        route: profile === 'paranoid' ? primaryQuery.data ?? null : paranoidQuery.data ?? null,
        isLoading: profile === 'paranoid' ? primaryQuery.isLoading : paranoidQuery.isLoading,
        error: profile === 'paranoid'
          ? primaryQuery.error as Error | null
          : paranoidQuery.error as Error | null,
      },
    ];
  }, [
    compareProfiles,
    profile,
    primaryQuery.data,
    primaryQuery.isLoading,
    primaryQuery.error,
    saferQuery.data,
    saferQuery.isLoading,
    saferQuery.error,
    shortestQuery.data,
    shortestQuery.isLoading,
    shortestQuery.error,
    paranoidQuery.data,
    paranoidQuery.isLoading,
    paranoidQuery.error,
  ]);

  // Build system ID lookup from names (reverse lookup)
  const systemIdLookup = useMemo(() => {
    const lookup = new Map<string, number>();

    if (systems) {
      systems.forEach((sys, id) => {
        lookup.set(sys.name, id);
      });
    }

    return lookup;
  }, [systems]);

  // Convert route response to MapRoute format
  const routeToMapRoute = useCallback(
    (response: RouteResponse, routeProfile: RouteProfile): MapRoute => {
      const systemIds = response.path.map((hop) => {
        return systemIdLookup.get(hop.system_name) ?? 0;
      }).filter((id) => id !== 0);

      return {
        systemIds,
        color: PROFILE_COLORS[routeProfile],
        animated: true,
        label: routeProfile,
      };
    },
    [systemIdLookup]
  );

  // Build MapRoute array for overlay
  const mapRoutes = useMemo((): MapRoute[] => {
    const routes: MapRoute[] = [];

    if (compareProfiles) {
      // Add all comparison routes
      for (const comparison of comparisons) {
        if (comparison.route) {
          routes.push(routeToMapRoute(comparison.route, comparison.profile));
        }
      }
    } else if (primaryQuery.data) {
      // Just the primary route
      routes.push(routeToMapRoute(primaryQuery.data, profile));
    }

    return routes;
  }, [compareProfiles, comparisons, primaryQuery.data, profile, routeToMapRoute]);

  // Check if system is on current route
  const isSystemOnRoute = useCallback(
    (systemId: number): boolean => {
      return mapRoutes.some((route) => route.systemIds.includes(systemId));
    },
    [mapRoutes]
  );

  // Select system based on current mode
  const selectSystem = useCallback(
    (systemId: number) => {
      if (mode === 'origin') {
        setOriginId(systemId);
        setMode('destination');
      } else if (mode === 'destination') {
        setDestinationId(systemId);
        setMode('idle');
      }
    },
    [mode]
  );

  // Avoid system management
  const addAvoidSystem = useCallback((systemId: number) => {
    setAvoidSystems((prev) => new Set(prev).add(systemId));
  }, []);

  const removeAvoidSystem = useCallback((systemId: number) => {
    setAvoidSystems((prev) => {
      const next = new Set(prev);
      next.delete(systemId);
      return next;
    });
  }, []);

  const clearAvoidSystems = useCallback(() => {
    setAvoidSystems(new Set());
  }, []);

  // Clear route
  const clearRoute = useCallback(() => {
    setOriginId(null);
    setDestinationId(null);
    setMode('idle');
    setAvoidSystems(new Set());
  }, []);

  // Swap origin and destination
  const swapOriginDestination = useCallback(() => {
    setOriginId(destinationId);
    setDestinationId(originId);
  }, [originId, destinationId]);

  // Set origin directly
  const setOrigin = useCallback((systemId: number | null) => {
    setOriginId(systemId);
  }, []);

  // Set destination directly
  const setDestination = useCallback((systemId: number | null) => {
    setDestinationId(systemId);
  }, []);

  return {
    state: {
      originId,
      destinationId,
      mode,
      profile,
      bridges,
      thera,
    },

    route: primaryQuery.data ?? null,
    isLoading: primaryQuery.isLoading,
    error: primaryQuery.error as Error | null,

    comparisons,
    mapRoutes,

    avoidSystems,
    addAvoidSystem,
    removeAvoidSystem,
    clearAvoidSystems,

    setMode,
    setProfile,
    setBridges,
    setThera,
    selectSystem,
    setOrigin,
    setDestination,
    clearRoute,
    swapOriginDestination,

    getSystemName,
    isSystemOnRoute,
  };
}

export default useMapRoute;
