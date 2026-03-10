/**
 * Universe Map Components
 * Export all map-related components and hooks
 */

// Types
export * from './types';

// Main map components
export { UniverseMap } from './UniverseMap';
export { default as MapCanvas } from './MapCanvas';

// Data hooks
export { useMapData, useMapDataFromProps, searchSystems, getConnectedSystems, calculateRegionCenters } from './useMapData';

// Spatial utilities
export {
  Quadtree,
  buildQuadtree,
  viewportToBounds,
  worldToScreen,
  screenToWorld,
  calculateFitZoom,
  clamp,
  lerp,
  smoothStep,
} from './utils/spatial';
export type { BoundingBox } from './utils/spatial';

// Route Layer
export { RouteOverlay } from './RouteOverlay';
export type { RouteOverlayProps } from './RouteOverlay';

export { RouteControls } from './RouteControls';
export type { RouteControlsProps } from './RouteControls';

export { SystemTooltip } from './SystemTooltip';
export type { SystemTooltipProps } from './SystemTooltip';

export { useMapRoute } from './useMapRoute';
export type {
  UseMapRouteOptions,
  UseMapRouteResult,
  MapRouteState,
  RouteSelectionMode,
  RouteComparison,
} from './useMapRoute';

// Overlay components
export { KillMarkers } from './KillMarkers';
export { RiskHeatmap, RiskHeatmapLegend } from './RiskHeatmap';
export { Minimap } from './Minimap';

// System detail & search
export { SystemDetailPanel } from './SystemDetailPanel';
export { SystemSearch } from './SystemSearch';

// Intel controls
export { IntelControls, IntelStatusBadge } from './IntelControls';

// Intel hooks
export { useKillStream } from './useKillStream';
export { useIntelData, TIME_RANGE_OPTIONS } from './useIntelData';
export type { TimeRange } from './useIntelData';
