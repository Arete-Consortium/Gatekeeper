'use client';

import { useQuery } from '@tanstack/react-query';
import { GatekeeperAPI } from '@/lib/api';
import type { RouteHistoryResponse } from '@/lib/types';

export function useRouteHistory(limit: number = 10) {
  return useQuery<RouteHistoryResponse>({
    queryKey: ['routeHistory', limit],
    queryFn: () => GatekeeperAPI.getRouteHistory(limit),
    staleTime: 30 * 1000, // 30 seconds
  });
}
