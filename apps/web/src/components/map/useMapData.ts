/**
 * Hook to fetch and transform map data for the Universe Map
 * Converts API systems to MapSystem format and builds efficient lookup structures
 */

import { useQuery } from '@tanstack/react-query';
import { useMemo } from 'react';
import type { MapSystem, MapGate } from './types';
import { buildQuadtree, type Quadtree } from './utils/spatial';

// API response types (adjust based on actual API shape)
interface ApiSystem {
  system_id: number;
  system_name: string;
  security_status: number;
  constellation_id: number;
  region_id?: number;
  position?: {
    x: number;
    y: number;
    z: number;
  };
}

interface ApiStargate {
  stargate_id: number;
  system_id: number;
  destination: {
    stargate_id: number;
    system_id: number;
  };
}

interface MapDataResult {
  systems: MapSystem[];
  gates: MapGate[];
  systemMap: Map<number, MapSystem>;
  quadtree: Quadtree | null;
  isLoading: boolean;
  error: Error | null;
}

// Scale factor for EVE coordinates (they're huge)
const COORDINATE_SCALE = 1e15;

// Fallback positions for when position data is unavailable
// Maps constellation_id to approximate x,y based on region groupings
function getApproximatePosition(
  systemId: number,
  constellationId: number,
  regionId: number
): { x: number; y: number } {
  // Use a deterministic hash-based layout when no coordinates available
  // This spreads systems out based on their IDs
  const regionAngle = ((regionId * 137.508) % 360) * (Math.PI / 180);
  const constellationRadius = 500 + (constellationId % 50) * 20;
  const systemOffset = (systemId % 100) * 5;

  const x = Math.cos(regionAngle) * constellationRadius + systemOffset;
  const y = Math.sin(regionAngle) * constellationRadius + systemOffset;

  return { x, y };
}

/**
 * Transform API system data to MapSystem format
 */
function transformSystem(apiSystem: ApiSystem): MapSystem {
  let x: number;
  let y: number;

  if (apiSystem.position) {
    // Use actual EVE coordinates, scaled down
    x = apiSystem.position.x / COORDINATE_SCALE;
    y = apiSystem.position.z / COORDINATE_SCALE; // Use Z for 2D map (X-Z plane)
  } else {
    // Generate approximate position
    const pos = getApproximatePosition(
      apiSystem.system_id,
      apiSystem.constellation_id,
      apiSystem.region_id || 0
    );
    x = pos.x;
    y = pos.y;
  }

  return {
    systemId: apiSystem.system_id,
    name: apiSystem.system_name,
    x,
    y,
    security: apiSystem.security_status,
    regionId: apiSystem.region_id || 0,
    constellationId: apiSystem.constellation_id,
  };
}

/**
 * Extract unique gate connections from stargates
 * Deduplicates bidirectional gates (A->B and B->A become one connection)
 */
function extractGates(stargates: ApiStargate[]): MapGate[] {
  const seen = new Set<string>();
  const gates: MapGate[] = [];

  for (const gate of stargates) {
    const fromId = gate.system_id;
    const toId = gate.destination.system_id;

    // Create consistent key for deduplication
    const key = fromId < toId ? `${fromId}-${toId}` : `${toId}-${fromId}`;

    if (!seen.has(key)) {
      seen.add(key);
      gates.push({
        fromSystemId: fromId,
        toSystemId: toId,
      });
    }
  }

  return gates;
}

/**
 * Fetch systems data from API
 */
async function fetchSystems(): Promise<ApiSystem[]> {
  const response = await fetch('/api/universe/systems');
  if (!response.ok) {
    throw new Error(`Failed to fetch systems: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Fetch stargates data from API
 */
async function fetchStargates(): Promise<ApiStargate[]> {
  const response = await fetch('/api/universe/stargates');
  if (!response.ok) {
    throw new Error(`Failed to fetch stargates: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Hook to load and transform universe map data
 * Returns systems, gates, lookup map, and spatial index
 */
export function useMapData(): MapDataResult {
  // Fetch systems
  const {
    data: apiSystems,
    isLoading: systemsLoading,
    error: systemsError,
  } = useQuery({
    queryKey: ['universe', 'systems'],
    queryFn: fetchSystems,
    staleTime: 1000 * 60 * 60, // Systems don't change often - 1 hour
    gcTime: 1000 * 60 * 60 * 24, // Keep in cache for 24 hours
  });

  // Fetch stargates
  const {
    data: apiStargates,
    isLoading: gatesLoading,
    error: gatesError,
  } = useQuery({
    queryKey: ['universe', 'stargates'],
    queryFn: fetchStargates,
    staleTime: 1000 * 60 * 60,
    gcTime: 1000 * 60 * 60 * 24,
  });

  // Transform systems
  const systems = useMemo(() => {
    if (!apiSystems) return [];
    return apiSystems.map(transformSystem);
  }, [apiSystems]);

  // Extract gates
  const gates = useMemo(() => {
    if (!apiStargates) return [];
    return extractGates(apiStargates);
  }, [apiStargates]);

  // Build system lookup map
  const systemMap = useMemo(() => {
    const map = new Map<number, MapSystem>();
    for (const system of systems) {
      map.set(system.systemId, system);
    }
    return map;
  }, [systems]);

  // Build spatial index
  const quadtree = useMemo(() => {
    if (systems.length === 0) return null;
    return buildQuadtree(systems);
  }, [systems]);

  return {
    systems,
    gates,
    systemMap,
    quadtree,
    isLoading: systemsLoading || gatesLoading,
    error: systemsError || gatesError || null,
  };
}

/**
 * Hook variant that accepts pre-loaded data (for SSR or testing)
 */
export function useMapDataFromProps(
  systems: MapSystem[],
  gates: MapGate[]
): Omit<MapDataResult, 'isLoading' | 'error'> {
  const systemMap = useMemo(() => {
    const map = new Map<number, MapSystem>();
    for (const system of systems) {
      map.set(system.systemId, system);
    }
    return map;
  }, [systems]);

  const quadtree = useMemo(() => {
    if (systems.length === 0) return null;
    return buildQuadtree(systems);
  }, [systems]);

  return {
    systems,
    gates,
    systemMap,
    quadtree,
  };
}

/**
 * Find systems by name (case-insensitive partial match)
 */
export function searchSystems(
  systems: MapSystem[],
  query: string,
  limit = 10
): MapSystem[] {
  if (!query || query.length < 2) return [];

  const lowerQuery = query.toLowerCase();
  const results: MapSystem[] = [];

  // Exact matches first
  for (const system of systems) {
    if (system.name.toLowerCase() === lowerQuery) {
      results.push(system);
      if (results.length >= limit) return results;
    }
  }

  // Starts with matches
  for (const system of systems) {
    if (
      system.name.toLowerCase().startsWith(lowerQuery) &&
      !results.includes(system)
    ) {
      results.push(system);
      if (results.length >= limit) return results;
    }
  }

  // Contains matches
  for (const system of systems) {
    if (
      system.name.toLowerCase().includes(lowerQuery) &&
      !results.includes(system)
    ) {
      results.push(system);
      if (results.length >= limit) return results;
    }
  }

  return results;
}

/**
 * Get all connected systems (1 jump away)
 */
export function getConnectedSystems(
  systemId: number,
  gates: MapGate[],
  systemMap: Map<number, MapSystem>
): MapSystem[] {
  const connected: MapSystem[] = [];

  for (const gate of gates) {
    let neighborId: number | null = null;

    if (gate.fromSystemId === systemId) {
      neighborId = gate.toSystemId;
    } else if (gate.toSystemId === systemId) {
      neighborId = gate.fromSystemId;
    }

    if (neighborId !== null) {
      const neighbor = systemMap.get(neighborId);
      if (neighbor) {
        connected.push(neighbor);
      }
    }
  }

  return connected;
}
