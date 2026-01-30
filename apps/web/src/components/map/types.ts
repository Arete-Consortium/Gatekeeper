/**
 * Shared types for Universe Map components
 * All map agents build to these interfaces
 */

// System node on the map
export interface MapSystem {
  systemId: number;
  name: string;
  x: number;
  y: number;
  security: number;
  regionId: number;
  constellationId: number;
}

// Gate connection between systems
export interface MapGate {
  fromSystemId: number;
  toSystemId: number;
}

// Viewport state for the map
export interface MapViewport {
  x: number;
  y: number;
  zoom: number;
  width: number;
  height: number;
}

// Map interaction events
export interface MapEvents {
  onSystemClick?: (systemId: number) => void;
  onSystemHover?: (systemId: number | null) => void;
  onViewportChange?: (viewport: MapViewport) => void;
  onBackgroundClick?: () => void;
}

// Route to display on map
export interface MapRoute {
  systemIds: number[];
  color: string;
  animated?: boolean;
  label?: string;
}

// Kill event for live feed
export interface MapKill {
  killId: number;
  systemId: number;
  timestamp: number;
  shipType: string;
  value: number;
  isPod: boolean;
}

// Risk level for heatmap
export interface SystemRisk {
  systemId: number;
  riskScore: number;
  riskColor: 'green' | 'yellow' | 'orange' | 'red';
  recentKills: number;
  recentPods: number;
}

// Map layer visibility controls
export interface MapLayers {
  showGates: boolean;
  showLabels: boolean;
  showRoute: boolean;
  showKills: boolean;
  showHeatmap: boolean;
  showRegionLabels: boolean;
}

// Region data for map labels
export interface MapRegion {
  regionId: number;
  name: string;
  centerX: number;
  centerY: number;
  systemCount: number;
}

// Props for the main UniverseMap component
export interface UniverseMapProps {
  // Data
  systems: MapSystem[];
  gates: MapGate[];

  // Optional overlays
  routes?: MapRoute[];
  kills?: MapKill[];
  risks?: SystemRisk[];

  // Interaction
  selectedSystem?: number | null;
  highlightedSystems?: number[];

  // Events
  onSystemClick?: (systemId: number) => void;
  onSystemHover?: (systemId: number | null) => void;
  onRouteRequest?: (fromId: number, toId: number) => void;

  // Display options
  layers?: Partial<MapLayers>;
  colorMode?: 'security' | 'risk';

  // Sizing
  className?: string;
}

// Props for RouteOverlay component
export interface RouteOverlayProps {
  routes: MapRoute[];
  systems: Map<number, MapSystem>;
  viewport: MapViewport;
  onRouteClick?: (routeIndex: number) => void;
}

// Props for KillFeed overlay
export interface KillFeedProps {
  kills: MapKill[];
  systems: Map<number, MapSystem>;
  viewport: MapViewport;
  maxAge?: number; // Max age in ms before kills fade
}

// Props for RiskHeatmap overlay
export interface RiskHeatmapProps {
  risks: SystemRisk[];
  systems: Map<number, MapSystem>;
  viewport: MapViewport;
  opacity?: number;
}

// Ref interface for imperative map control
export interface UniverseMapRef {
  panTo: (systemId: number) => void;
  zoomTo: (level: number) => void;
  fitToSystems: (systemIds: number[]) => void;
  getViewport: () => MapViewport;
  setViewport: (viewport: Partial<MapViewport>) => void;
}

// Color utilities
export const SECURITY_COLORS = {
  highSec: '#00ff00',
  lowSec: '#ffaa00',
  nullSec: '#ff0000',
} as const;

export const RISK_COLORS = {
  green: '#32d74b',
  yellow: '#ffd60a',
  orange: '#ff9f0a',
  red: '#ff453a',
} as const;

export function getSecurityColor(security: number): string {
  if (security >= 0.5) return SECURITY_COLORS.highSec;
  if (security > 0) return SECURITY_COLORS.lowSec;
  return SECURITY_COLORS.nullSec;
}

export function getRiskColor(riskColor: 'green' | 'yellow' | 'orange' | 'red'): string {
  return RISK_COLORS[riskColor];
}
