/**
 * Processes raw /map/config API data into indexed map structures.
 */
import { useEffect, useMemo, useState } from 'react';
import { GatekeeperAPI } from '../services';
import { CacheService } from '../services/CacheService';
import { SpatialIndex } from '../utils/SpatialIndex';
import type {
  MapNode,
  MapEdge,
  RegionCentroid,
  ConstellationCentroid,
  MapConfigResponse,
} from '../components/map/types';

const CACHE_KEY = 'map_config_v2';
const CACHE_TTL = 60 * 60 * 1000; // 1 hour

interface MapData {
  nodes: MapNode[];
  edges: MapEdge[];
  spatialIndex: SpatialIndex;
  regionCentroids: RegionCentroid[];
  constellationCentroids: ConstellationCentroid[];
  systemNameMap: Map<string, MapNode>;
  isLoading: boolean;
  error: string | null;
}

function processMapConfig(raw: MapConfigResponse): {
  nodes: MapNode[];
  edges: MapEdge[];
  regionCentroids: RegionCentroid[];
  constellationCentroids: ConstellationCentroid[];
  systemNameMap: Map<string, MapNode>;
} {
  const nodes: MapNode[] = [];
  const systemNameMap = new Map<string, MapNode>();
  const systemByName = new Map<string, { x: number; y: number }>();

  // Build nodes
  for (const [name, sys] of Object.entries(raw.systems)) {
    const node: MapNode = {
      systemId: sys.id,
      name,
      x: sys.position.x,
      y: sys.position.y,
      security: sys.security,
      category: sys.category,
      regionId: sys.region_id,
      regionName: sys.region_name || '',
      constellationId: sys.constellation_id ?? 0,
      constellationName: sys.constellation_name || '',
      riskScore: sys.risk_score,
      riskColor: sys.risk_color,
    };
    nodes.push(node);
    systemNameMap.set(name, node);
    systemByName.set(name, { x: sys.position.x, y: sys.position.y });
  }

  // Build edges with pre-resolved coordinates
  const edges: MapEdge[] = [];
  if (raw.gates) {
    for (const gate of raw.gates) {
      const from = systemByName.get(gate.from_system);
      const to = systemByName.get(gate.to_system);
      if (from && to) {
        edges.push({
          fromName: gate.from_system,
          toName: gate.to_system,
          fromX: from.x,
          fromY: from.y,
          toX: to.x,
          toY: to.y,
        });
      }
    }
  }

  // Compute region centroids
  const regionGroups = new Map<
    number,
    { name: string; sumX: number; sumY: number; count: number }
  >();
  for (const node of nodes) {
    const group = regionGroups.get(node.regionId);
    if (group) {
      group.sumX += node.x;
      group.sumY += node.y;
      group.count++;
    } else {
      regionGroups.set(node.regionId, {
        name: node.regionName || `Region ${node.regionId}`,
        sumX: node.x,
        sumY: node.y,
        count: 1,
      });
    }
  }

  const regionCentroids: RegionCentroid[] = [];
  for (const [regionId, group] of regionGroups) {
    regionCentroids.push({
      regionId,
      name: group.name,
      x: group.sumX / group.count,
      y: group.sumY / group.count,
      systemCount: group.count,
    });
  }

  // Compute constellation centroids
  const constGroups = new Map<
    number,
    { name: string; sumX: number; sumY: number; count: number }
  >();
  for (const node of nodes) {
    if (!node.constellationId) continue;
    const group = constGroups.get(node.constellationId);
    if (group) {
      group.sumX += node.x;
      group.sumY += node.y;
      group.count++;
    } else {
      constGroups.set(node.constellationId, {
        name: node.constellationName || `Constellation ${node.constellationId}`,
        sumX: node.x,
        sumY: node.y,
        count: 1,
      });
    }
  }

  const constellationCentroids: ConstellationCentroid[] = [];
  for (const [constellationId, group] of constGroups) {
    constellationCentroids.push({
      constellationId,
      name: group.name,
      x: group.sumX / group.count,
      y: group.sumY / group.count,
      systemCount: group.count,
    });
  }

  return { nodes, edges, regionCentroids, constellationCentroids, systemNameMap };
}

export function useMapData(): MapData {
  const [rawData, setRawData] = useState<MapConfigResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchData() {
      setIsLoading(true);
      setError(null);

      try {
        // Try network first
        const data = (await GatekeeperAPI.getMapConfig()) as unknown as MapConfigResponse;
        if (!cancelled) {
          setRawData(data);
          // Cache for offline use
          await CacheService.set(CACHE_KEY, data, CACHE_TTL);
        }
      } catch {
        // Fall back to cache
        try {
          const cached = await CacheService.get<MapConfigResponse>(CACHE_KEY);
          if (!cancelled && cached) {
            setRawData(cached);
          } else if (!cancelled) {
            setError('Unable to load map data. Check your connection.');
          }
        } catch {
          if (!cancelled) {
            setError('Unable to load map data. Check your connection.');
          }
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    fetchData();
    return () => {
      cancelled = true;
    };
  }, []);

  const processed = useMemo(() => {
    if (!rawData) return null;
    return processMapConfig(rawData);
  }, [rawData]);

  const spatialIndex = useMemo(() => {
    if (!processed) return null;
    return new SpatialIndex(processed.nodes);
  }, [processed]);

  if (!processed || !spatialIndex) {
    return {
      nodes: [],
      edges: [],
      spatialIndex: new SpatialIndex([]),
      regionCentroids: [],
      constellationCentroids: [],
      systemNameMap: new Map(),
      isLoading,
      error,
    };
  }

  return {
    nodes: processed.nodes,
    edges: processed.edges,
    spatialIndex,
    regionCentroids: processed.regionCentroids,
    constellationCentroids: processed.constellationCentroids,
    systemNameMap: processed.systemNameMap,
    isLoading,
    error,
  };
}
