'use client';

import { useQuery } from '@tanstack/react-query';
import { GatekeeperAPI } from '@/lib/api';
import type { HotSystem } from '@/lib/types';

export function useHotSystems(hours: number = 24, limit: number = 10) {
  return useQuery<HotSystem[]>({
    queryKey: ['hotSystems', hours, limit],
    queryFn: () => GatekeeperAPI.getHotSystems(hours, limit),
    staleTime: 60 * 1000, // 1 minute
  });
}
