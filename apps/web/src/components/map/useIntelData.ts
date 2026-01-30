'use client';

import { useState, useEffect, useMemo, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { GatekeeperAPI } from '@/lib/api';
import type { HotSystem } from '@/lib/types';
import type { SystemRisk, MapKill } from './types';

/**
 * Time range options for intel data
 */
export type TimeRange = '1h' | '6h' | '24h' | '48h';

const TIME_RANGE_HOURS: Record<TimeRange, number> = {
  '1h': 1,
  '6h': 6,
  '24h': 24,
  '48h': 48,
};

interface UseIntelDataOptions {
  /** Time range for intel data */
  timeRange?: TimeRange;
  /** Maximum number of hot systems to fetch */
  limit?: number;
  /** Kill data from useKillStream */
  kills?: MapKill[];
  /** Auto-refresh interval in ms (0 = disabled) */
  refreshInterval?: number;
}

interface UseIntelDataReturn {
  /** Risk data by system */
  risks: SystemRisk[];
  /** Hot systems from API */
  hotSystems: HotSystem[];
  /** Total kills in current time window */
  totalKills: number;
  /** Total pod kills in current time window */
  totalPods: number;
  /** Loading state */
  isLoading: boolean;
  /** Error state */
  error: string | null;
  /** Current time range */
  timeRange: TimeRange;
  /** Set time range */
  setTimeRange: (range: TimeRange) => void;
  /** Manually refresh data */
  refresh: () => void;
}

/**
 * Calculate risk color from score
 */
function getRiskColorFromScore(score: number): 'green' | 'yellow' | 'orange' | 'red' {
  if (score <= 2) return 'green';
  if (score <= 4) return 'yellow';
  if (score <= 7) return 'orange';
  return 'red';
}

/**
 * Transform HotSystem data to SystemRisk format
 */
function transformToSystemRisk(hotSystem: HotSystem): SystemRisk {
  // Calculate risk score based on kills and security
  // More kills = higher risk, lower security = higher base risk
  const killScore = Math.min(hotSystem.recent_kills * 0.5, 5); // Cap kill contribution
  const podScore = Math.min(hotSystem.recent_pods * 1.0, 3); // Pods are more dangerous
  const securityBonus = hotSystem.security >= 0.5 ? 0 : hotSystem.security > 0 ? 2 : 4;

  const riskScore = Math.min(10, killScore + podScore + securityBonus);

  return {
    systemId: hotSystem.system_id,
    riskScore,
    riskColor: getRiskColorFromScore(riskScore),
    recentKills: hotSystem.recent_kills,
    recentPods: hotSystem.recent_pods,
  };
}

/**
 * Aggregate kills by system into risk data
 */
function aggregateKillsToRisk(kills: MapKill[], existingRisks: Map<number, SystemRisk>): SystemRisk[] {
  const riskMap = new Map(existingRisks);

  // Count kills by system
  const killsBySystem = new Map<number, { kills: number; pods: number }>();
  for (const kill of kills) {
    const current = killsBySystem.get(kill.systemId) || { kills: 0, pods: 0 };
    if (kill.isPod) {
      current.pods++;
    } else {
      current.kills++;
    }
    killsBySystem.set(kill.systemId, current);
  }

  // Update or create risk entries
  for (const [systemId, counts] of Array.from(killsBySystem.entries())) {
    const existing = riskMap.get(systemId);
    if (existing) {
      // Boost existing risk based on recent kills
      const killBoost = Math.min(counts.kills * 0.3, 2);
      const podBoost = Math.min(counts.pods * 0.5, 2);
      const newScore = Math.min(10, existing.riskScore + killBoost + podBoost);
      riskMap.set(systemId, {
        ...existing,
        riskScore: newScore,
        riskColor: getRiskColorFromScore(newScore),
        recentKills: existing.recentKills + counts.kills,
        recentPods: existing.recentPods + counts.pods,
      });
    } else {
      // Create new risk entry for unknown system
      const killScore = Math.min(counts.kills * 0.5, 5);
      const podScore = Math.min(counts.pods * 1.0, 3);
      const riskScore = Math.min(10, killScore + podScore + 2); // Base risk of 2 for unknown
      riskMap.set(systemId, {
        systemId,
        riskScore,
        riskColor: getRiskColorFromScore(riskScore),
        recentKills: counts.kills,
        recentPods: counts.pods,
      });
    }
  }

  return Array.from(riskMap.values());
}

/**
 * Hook for fetching and managing intel data
 *
 * Combines:
 * - Hot systems from API (historical data)
 * - Live kill data (if provided)
 * - Computed risk scores
 *
 * Usage:
 * ```tsx
 * const { kills } = useKillStream({ useMock: true });
 * const { risks, hotSystems, setTimeRange } = useIntelData({
 *   timeRange: '24h',
 *   kills,
 * });
 * ```
 */
export function useIntelData(options: UseIntelDataOptions = {}): UseIntelDataReturn {
  const {
    timeRange: initialTimeRange = '24h',
    limit = 50,
    kills = [],
    refreshInterval = 60000, // 1 minute default
  } = options;

  const [timeRange, setTimeRange] = useState<TimeRange>(initialTimeRange);

  const hours = TIME_RANGE_HOURS[timeRange];

  // Fetch hot systems from API
  const {
    data: hotSystems = [],
    isLoading,
    error: queryError,
    refetch,
  } = useQuery<HotSystem[]>({
    queryKey: ['hotSystems', hours, limit],
    queryFn: () => GatekeeperAPI.getHotSystems(hours, limit),
    staleTime: 60 * 1000, // 1 minute
    refetchInterval: refreshInterval > 0 ? refreshInterval : undefined,
  });

  // Transform hot systems to base risk data
  const baseRisks = useMemo(() => {
    const riskMap = new Map<number, SystemRisk>();
    for (const hs of hotSystems) {
      const risk = transformToSystemRisk(hs);
      riskMap.set(risk.systemId, risk);
    }
    return riskMap;
  }, [hotSystems]);

  // Combine base risks with live kill data
  const risks = useMemo(() => {
    if (kills.length === 0) {
      return Array.from(baseRisks.values());
    }
    return aggregateKillsToRisk(kills, baseRisks);
  }, [baseRisks, kills]);

  // Calculate totals
  const { totalKills, totalPods } = useMemo(() => {
    let totalKills = 0;
    let totalPods = 0;

    // Count from hot systems
    for (const hs of hotSystems) {
      totalKills += hs.recent_kills;
      totalPods += hs.recent_pods;
    }

    // Add live kills not already counted
    const hotSystemIds = new Set(hotSystems.map((hs) => hs.system_id));
    for (const kill of kills) {
      if (!hotSystemIds.has(kill.systemId)) {
        if (kill.isPod) {
          totalPods++;
        } else {
          totalKills++;
        }
      }
    }

    return { totalKills, totalPods };
  }, [hotSystems, kills]);

  // Refresh handler
  const refresh = useCallback(() => {
    refetch();
  }, [refetch]);

  // Error handling
  const error = queryError ? (queryError as Error).message : null;

  return {
    risks,
    hotSystems,
    totalKills,
    totalPods,
    isLoading,
    error,
    timeRange,
    setTimeRange,
    refresh,
  };
}

/**
 * Time range options for UI
 */
export const TIME_RANGE_OPTIONS: { value: TimeRange; label: string }[] = [
  { value: '1h', label: '1 Hour' },
  { value: '6h', label: '6 Hours' },
  { value: '24h', label: '24 Hours' },
  { value: '48h', label: '48 Hours' },
];

export default useIntelData;
