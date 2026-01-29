/**
 * useCachedAPI Hook
 * Provides API access with automatic caching and offline fallback
 */
import { useState, useEffect, useCallback } from 'react';
import { GatekeeperAPI } from '../services/GatekeeperAPI';
import { cacheService } from '../services/CacheService';
import { networkService } from '../services/NetworkService';
import {
  RouteResponse,
  MapConfig,
  ShipProfile,
  RouteHistoryResponse,
  HotSystem,
  RiskReport,
} from '../types';

interface CachedAPIState {
  isOnline: boolean;
  isLoading: boolean;
  error: string | null;
}

/**
 * Hook for cached route calculation
 */
export function useCachedRoute() {
  const [state, setState] = useState<CachedAPIState>({
    isOnline: networkService.getIsConnected(),
    isLoading: false,
    error: null,
  });

  useEffect(() => {
    const unsubscribe = networkService.addListener((isConnected) => {
      setState((prev) => ({ ...prev, isOnline: isConnected }));
    });
    return unsubscribe;
  }, []);

  const getRoute = useCallback(
    async (
      from: string,
      to: string,
      profile: 'shortest' | 'safer' | 'paranoid' = 'safer',
      options?: { bridges?: boolean; thera?: boolean }
    ): Promise<RouteResponse | null> => {
      setState((prev) => ({ ...prev, isLoading: true, error: null }));

      try {
        // Try cache first if offline
        if (!networkService.getIsConnected()) {
          const cached = await cacheService.getCachedRoute(from, to, profile, options || {});
          if (cached) {
            setState((prev) => ({ ...prev, isLoading: false }));
            return cached as RouteResponse;
          }
          setState((prev) => ({
            ...prev,
            isLoading: false,
            error: 'Offline - no cached route available',
          }));
          return null;
        }

        // Fetch from API
        const route = await GatekeeperAPI.getRoute(from, to, profile, options);

        // Cache the result
        await cacheService.cacheRoute(from, to, profile, options || {}, route);

        setState((prev) => ({ ...prev, isLoading: false }));
        return route;
      } catch (error) {
        // Try cache as fallback
        const cached = await cacheService.getCachedRoute(from, to, profile, options || {});
        if (cached) {
          setState((prev) => ({ ...prev, isLoading: false }));
          return cached as RouteResponse;
        }

        setState((prev) => ({
          ...prev,
          isLoading: false,
          error: error instanceof Error ? error.message : 'Failed to calculate route',
        }));
        return null;
      }
    },
    []
  );

  return { ...state, getRoute };
}

/**
 * Hook for cached map configuration
 */
export function useCachedMapConfig() {
  const [data, setData] = useState<MapConfig | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      // Try network first
      if (networkService.getIsConnected()) {
        const config = await GatekeeperAPI.getMapConfig();
        await cacheService.cacheMapConfig(config);
        setData(config);
        setIsLoading(false);
        return;
      }

      // Offline - try cache
      const cached = await cacheService.getCachedMapConfig();
      if (cached) {
        setData(cached as MapConfig);
      } else {
        setError('Offline - no cached map config');
      }
    } catch (err) {
      // Try cache as fallback
      const cached = await cacheService.getCachedMapConfig();
      if (cached) {
        setData(cached as MapConfig);
      } else {
        setError(err instanceof Error ? err.message : 'Failed to load map config');
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetch();
  }, [fetch]);

  return { data, isLoading, error, refresh: fetch };
}

/**
 * Hook for cached ship profiles
 */
export function useCachedShipProfiles() {
  const [data, setData] = useState<ShipProfile[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      if (networkService.getIsConnected()) {
        const profiles = await GatekeeperAPI.getShipProfiles();
        await cacheService.cacheShipProfiles(profiles);
        setData(profiles);
        setIsLoading(false);
        return;
      }

      const cached = await cacheService.getCachedShipProfiles();
      if (cached) {
        setData(cached as ShipProfile[]);
      } else {
        setError('Offline - no cached profiles');
      }
    } catch (err) {
      const cached = await cacheService.getCachedShipProfiles();
      if (cached) {
        setData(cached as ShipProfile[]);
      } else {
        setError(err instanceof Error ? err.message : 'Failed to load profiles');
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetch();
  }, [fetch]);

  return { data, isLoading, error, refresh: fetch };
}

/**
 * Hook for cached route history
 */
export function useCachedRouteHistory(limit: number = 10) {
  const [data, setData] = useState<RouteHistoryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      if (networkService.getIsConnected()) {
        const history = await GatekeeperAPI.getRouteHistory(limit);
        await cacheService.cacheRouteHistory(history);
        setData(history);
        setIsLoading(false);
        return;
      }

      const cached = await cacheService.getCachedRouteHistory();
      if (cached) {
        setData(cached as RouteHistoryResponse);
      } else {
        setError('Offline - no cached history');
      }
    } catch (err) {
      const cached = await cacheService.getCachedRouteHistory();
      if (cached) {
        setData(cached as RouteHistoryResponse);
      } else {
        setError(err instanceof Error ? err.message : 'Failed to load history');
      }
    } finally {
      setIsLoading(false);
    }
  }, [limit]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  return { data, isLoading, error, refresh: fetch };
}

/**
 * Hook for cached hot systems
 */
export function useCachedHotSystems(hours: number = 24, limit: number = 10) {
  const [data, setData] = useState<HotSystem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      if (networkService.getIsConnected()) {
        const systems = await GatekeeperAPI.getHotSystems(hours, limit);
        await cacheService.cacheHotSystems(hours, systems);
        setData(systems);
        setIsLoading(false);
        return;
      }

      const cached = await cacheService.getCachedHotSystems(hours);
      if (cached) {
        setData(cached as HotSystem[]);
      } else {
        setError('Offline - no cached data');
      }
    } catch (err) {
      const cached = await cacheService.getCachedHotSystems(hours);
      if (cached) {
        setData(cached as HotSystem[]);
      } else {
        setError(err instanceof Error ? err.message : 'Failed to load hot systems');
      }
    } finally {
      setIsLoading(false);
    }
  }, [hours, limit]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  return { data, isLoading, error, refresh: fetch };
}

/**
 * Hook for cached system risk
 */
export function useCachedSystemRisk(systemName: string | null) {
  const [data, setData] = useState<RiskReport | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    if (!systemName) {
      setData(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      if (networkService.getIsConnected()) {
        const risk = await GatekeeperAPI.getSystemRisk(systemName);
        await cacheService.cacheSystemRisk(systemName, risk);
        setData(risk);
        setIsLoading(false);
        return;
      }

      const cached = await cacheService.getCachedSystemRisk(systemName);
      if (cached) {
        setData(cached as RiskReport);
      } else {
        setError('Offline - no cached risk data');
      }
    } catch (err) {
      const cached = await cacheService.getCachedSystemRisk(systemName);
      if (cached) {
        setData(cached as RiskReport);
      } else {
        setError(err instanceof Error ? err.message : 'Failed to load risk data');
      }
    } finally {
      setIsLoading(false);
    }
  }, [systemName]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  return { data, isLoading, error, refresh: fetch };
}

/**
 * Hook for network status
 */
export function useNetworkStatus() {
  const [isOnline, setIsOnline] = useState(networkService.getIsConnected());

  useEffect(() => {
    const unsubscribe = networkService.addListener(setIsOnline);
    return unsubscribe;
  }, []);

  return { isOnline, isOffline: !isOnline };
}
