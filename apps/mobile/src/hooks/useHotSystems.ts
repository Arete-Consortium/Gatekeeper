/**
 * Polls /api/v1/stats/hot for live kill activity.
 * Returns a Set of system names with recent kills for fast lookup.
 */
import { useEffect, useState } from 'react';
import { GatekeeperAPI } from '../services/GatekeeperAPI';

const POLL_INTERVAL = 60_000; // 1 minute

interface HotSystemEntry {
  system_name: string;
  recent_kills: number;
}

export function useHotSystems(): Map<string, number> {
  const [hotMap, setHotMap] = useState<Map<string, number>>(new Map());

  useEffect(() => {
    let cancelled = false;

    async function fetch() {
      try {
        const systems: HotSystemEntry[] = await GatekeeperAPI.getHotSystems(1, 50);
        if (!cancelled) {
          const map = new Map<string, number>();
          for (const s of systems) {
            map.set(s.system_name, s.recent_kills);
          }
          setHotMap(map);
        }
      } catch {
        // Silent fail — hot systems are non-critical
      }
    }

    fetch();
    const interval = setInterval(fetch, POLL_INTERVAL);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  return hotMap;
}
