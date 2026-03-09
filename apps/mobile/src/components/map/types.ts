/**
 * Map-specific types for Skia rendering.
 */

export interface MapNode {
  systemId: number;
  name: string;
  x: number;
  y: number;
  security: number;
  category: string;
  regionId: number;
  regionName: string;
  constellationId: number;
  constellationName: string;
  riskScore: number;
  riskColor: string;
}

export interface MapEdge {
  fromName: string;
  toName: string;
  fromX: number;
  fromY: number;
  toX: number;
  toY: number;
}

export interface MapViewport {
  centerX: number;
  centerY: number;
  zoom: number;
  screenWidth: number;
  screenHeight: number;
}

export interface WorldBounds {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
  centerX: number;
  centerY: number;
  width: number;
  height: number;
}

export interface RegionCentroid {
  regionId: number;
  name: string;
  x: number;
  y: number;
  systemCount: number;
}

export interface ConstellationCentroid {
  constellationId: number;
  name: string;
  x: number;
  y: number;
  systemCount: number;
}

/** Response shape from /map/config backend endpoint */
export interface MapConfigResponse {
  metadata: {
    version: string;
    source: string;
    last_updated: string;
  };
  systems: Record<
    string,
    {
      id: number;
      region_id: number;
      region_name: string;
      constellation_id: number;
      constellation_name: string;
      security: number;
      category: string;
      position: { x: number; y: number };
      risk_score: number;
      risk_color: string;
    }
  >;
  gates: Array<{
    from_system: string;
    to_system: string;
  }>;
  layers: Record<string, unknown>;
}
