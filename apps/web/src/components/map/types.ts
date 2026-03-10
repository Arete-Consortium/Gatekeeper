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
  // SDE enhancements
  hub?: boolean;
  border?: boolean;
  spectralClass?: string;
  npcStations?: number;
  regionName?: string;
  constellationName?: string;
  // Live data (populated by overlays)
  sovAllianceId?: number;
  sovFactionId?: number;
  fwContested?: string;
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
  showSovereignty: boolean;
  showThera: boolean;
  showFW: boolean;
  showLandmarks: boolean;
  showSovStructures: boolean;
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
  regionNames?: Map<number, string>;

  // Optional overlays
  routes?: MapRoute[];
  kills?: MapKill[];
  risks?: SystemRisk[];

  // Sovereignty & live data
  sovereignty?: Record<string, { alliance_id: number | null; faction_id: number | null }>;
  alliances?: Record<string, { name: string }>;
  factions?: Record<string, { name: string }>;
  theraConnections?: import('@/lib/types').TheraConnection[];
  fwSystems?: Record<string, import('@/lib/types').FWSystem>;
  landmarks?: import('@/lib/types').Landmark[];
  sovStructures?: Record<string, import('@/lib/types').SovStructure[]>;

  // Interaction
  selectedSystem?: number | null;
  highlightedSystems?: number[];

  // Events
  onSystemClick?: (systemId: number) => void;
  onSystemHover?: (systemId: number | null) => void;
  onRouteRequest?: (fromId: number, toId: number) => void;
  onSetRouteOrigin?: (systemId: number) => void;
  onSetRouteDestination?: (systemId: number) => void;
  onAvoidSystem?: (systemId: number) => void;
  onDeselect?: () => void;

  // Display options
  layers?: Partial<MapLayers>;
  colorMode?: 'security' | 'risk' | 'star';

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

// Star spectral class colors (astronomically accurate)
export const SPECTRAL_COLORS: Record<string, string> = {
  O: '#9bb0ff', // Blue
  B: '#aabfff', // Blue-white
  A: '#cad7ff', // White
  F: '#f8f7ff', // Yellow-white
  G: '#fff4ea', // Yellow (Sol-like)
  K: '#ffd2a1', // Orange
  M: '#ffcc6f', // Red-orange
} as const;

export function getSpectralColor(spectralClass: string): string {
  return SPECTRAL_COLORS[spectralClass] || SPECTRAL_COLORS.G;
}

export function getRiskColor(riskColor: 'green' | 'yellow' | 'orange' | 'red'): string {
  return RISK_COLORS[riskColor];
}
