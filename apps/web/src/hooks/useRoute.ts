'use client';

import { useQuery } from '@tanstack/react-query';
import { GatekeeperAPI } from '@/lib/api';
import type { RouteResponse, RouteProfile } from '@/lib/types';

interface UseRouteOptions {
  from: string;
  to: string;
  profile?: RouteProfile;
  bridges?: boolean;
  thera?: boolean;
  enabled?: boolean;
}

export function useRoute({
  from,
  to,
  profile = 'safer',
  bridges = false,
  thera = false,
  enabled = true,
}: UseRouteOptions) {
  return useQuery<RouteResponse>({
    queryKey: ['route', from, to, profile, bridges, thera],
    queryFn: () => GatekeeperAPI.getRoute(from, to, profile, { bridges, thera }),
    enabled: enabled && !!from && !!to,
    staleTime: 60 * 1000, // 1 minute
    retry: false,
  });
}
