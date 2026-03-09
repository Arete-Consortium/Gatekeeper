/**
 * EVE Gatekeeper TypeScript Types
 * Matching backend Pydantic models
 */

// Gate connection between systems
export interface Gate {
  from_system: string;
  to_system: string;
  distance: number;
}

// Solar system information
export interface System {
  name: string;
  system_id: number;
  region_id: number;
  constellation_id: number;
  security_status: number;
  security_category: 'high_sec' | 'low_sec' | 'null_sec';
  x: number;
  y: number;
}

// Universe data
export interface Universe {
  systems: Record<string, System>;
  gates: Gate[];
}

// zKillboard statistics
export interface ZKillStats {
  recent_kills: number;
  recent_pods: number;
}

// Risk assessment report
export interface RiskReport {
  system_name: string;
  system_id: number;
  category: string;
  security: number;
  score: number;
  breakdown: {
    security_component: number;
    kills_component: number;
    pods_component: number;
  };
  zkill_stats: {
    recent_kills: number;
    recent_pods: number;
  };
  danger_level: string | null;
  ship_profile: string | null;
}

// Helper to get risk color from score
export function getRiskColorFromScore(score: number): 'green' | 'yellow' | 'orange' | 'red' {
  if (score <= 2) return 'green';
  if (score <= 5) return 'yellow';
  if (score <= 8) return 'orange';
  return 'red';
}

// Single hop in a route
export interface RouteHop {
  system_name: string;
  security_status: number;
  risk_score: number;
  distance: number;
  cumulative_cost: number;
}

// Complete route response
export interface RouteResponse {
  path: RouteHop[];
  total_jumps: number;
  total_distance: number;
  total_cost: number;
  max_risk: number;
  avg_risk: number;
  profile: 'shortest' | 'safer' | 'paranoid';
  bridges_used: number;
  thera_used: number;
}

// Routing profile configuration
export interface RoutingProfile {
  risk_factor: number;
}

// Risk configuration
export interface RiskConfig {
  security_category_weights: {
    high_sec: number;
    low_sec: number;
    null_sec: number;
  };
  kill_weights: {
    kills: number;
    pods: number;
  };
  clamp: {
    min: number;
    max: number;
  };
  risk_colors: Record<string, string>;
  routing_profiles: Record<string, RoutingProfile>;
}

// System data from /map/config endpoint
export interface MapConfigSystem {
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
  // SDE enhancement fields
  hub: boolean;
  border: boolean;
  corridor: boolean;
  fringe: boolean;
  spectral_class: string;
  npc_stations: number;
}

// Landmark from SDE
export interface Landmark {
  id: number;
  name: string;
  description: string;
  system_id: number | null;
  icon_id: number | null;
}

// Faction data
export interface Faction {
  name: string;
  home_system_id: number | null;
  militia_corp_id: number | null;
}

// Map configuration response from /map/config
export interface MapConfig {
  metadata: { version: string; source: string; last_updated: string };
  systems: Record<string, MapConfigSystem>;
  gates: Gate[];
  layers: Record<string, boolean>;
  landmarks: Landmark[];
  factions: Record<string, Faction>;
}

// Sovereignty data
export interface SovereigntyEntry {
  alliance_id: number | null;
  corporation_id: number | null;
  faction_id: number | null;
}

export interface SovereigntyResponse {
  sovereignty: Record<string, SovereigntyEntry>;
  alliances: Record<string, { name: string; category: string }>;
}

// Faction warfare system
export interface FWSystem {
  occupier_faction_id: number;
  owner_faction_id: number;
  contested: string;
  victory_points: number;
  victory_points_threshold: number;
}

export interface FWResponse {
  fw_systems: Record<string, FWSystem>;
}

// Sovereignty structures
export interface SovStructure {
  alliance_id: number;
  structure_type_id: number;
  vulnerability_occupancy_level: number | null;
  vulnerable_start_time: string | null;
  vulnerable_end_time: string | null;
}

export interface SovStructuresResponse {
  structures: Record<string, SovStructure[]>;
}

// EVE Scout Thera connection
export interface TheraConnection {
  id: number;
  source_system_id: number;
  source_system_name: string;
  dest_system_id: number;
  dest_system_name: string;
  dest_region_name: string;
  wh_type: string;
  max_ship_size: string;
  remaining_hours: number;
  signature_id: string;
  completed: boolean;
}

export interface TheraResponse {
  connections: TheraConnection[];
}

// System activity data (Dotlan-style)
export interface SystemActivityKills {
  ship_kills: number;
  npc_kills: number;
  pod_kills: number;
}

export interface Incursion {
  type: string;
  state: string;
  staging_system_id: number;
  constellation_id: number;
  infested_systems: number[];
  has_boss: boolean;
  influence: number;
}

export interface SystemActivityResponse {
  jumps: Record<string, number>;
  kills: Record<string, SystemActivityKills>;
  incursions: Incursion[];
}

// Capital ship data
export interface CapitalShip {
  name: string;
  type_id: number;
  base_range: number;
  base_fuel: number;
  fuel_type: 'helium' | 'hydrogen' | 'nitrogen' | 'oxygen';
}

// Jump calculation result
export interface JumpCalculation {
  origin: string;
  destination: string;
  distance: number;
  fuel_required: number;
  in_range: boolean;
  ship: CapitalShip;
}

// API health response
export interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
}

// App settings
export interface AppSettings {
  apiUrl: string;
  defaultProfile: 'shortest' | 'safer' | 'paranoid';
  showSecurityStatus: boolean;
  darkMode: boolean;
}

// Ship profile for risk adjustment
export interface ShipProfile {
  name: string;
  description: string;
  highsec_multiplier: number;
  lowsec_multiplier: number;
  nullsec_multiplier: number;
  kills_multiplier: number;
  pods_multiplier: number;
}

// Ship profiles list response
export interface ShipProfileListResponse {
  profiles: ShipProfile[];
}

// Route history entry
export interface RouteHistoryEntry {
  from_system: string;
  to_system: string;
  profile: string;
  jumps: number;
  timestamp: string;
}

// Route history response (API returns items + pagination)
export interface RouteHistoryResponse {
  items: RouteHistoryEntry[];
  pagination: {
    total: number;
    limit: number;
    offset: number;
  };
}

// System stats from zkill
export interface SystemStats {
  system_id: number;
  system_name: string;
  recent_kills: number;
  recent_pods: number;
  hours: number;
}

// Hot system entry
export interface HotSystem {
  system_id: number;
  system_name: string;
  security: number;
  category: string;
  recent_kills: number;
  recent_pods: number;
}

// Fitting analysis types
export interface ParsedFitting {
  ship_name: string;
  ship_category: string;
  jump_capability: string;
  modules: string[];
  cargo: string[];
  drones: string[];
  charges: string[];
  is_covert_capable: boolean;
  is_cloak_capable: boolean;
  has_warp_stabs: boolean;
  is_bubble_immune: boolean;
  has_align_mods: boolean;
  has_warp_speed_mods: boolean;
}

export interface TravelRecommendation {
  ship_name: string;
  category: string;
  can_use_gates: boolean;
  can_use_jump_bridges: boolean;
  can_jump: boolean;
  can_bridge_others: boolean;
  can_covert_bridge: boolean;
  recommended_profile: string;
  warnings: string[];
  tips: string[];
}

export interface FittingAnalysisResponse {
  fitting: ParsedFitting;
  travel: TravelRecommendation;
}

// Alert subscription types
export interface AlertSubscription {
  id: string;
  name: string | null;
  webhook_type: 'discord' | 'slack';
  systems: string[];
  regions: number[];
  min_value: number | null;
  include_pods: boolean;
  ship_types: string[];
  enabled: boolean;
  created_at: string;
}

export interface AlertSubscriptionListResponse {
  total: number;
  subscriptions: AlertSubscription[];
}

export interface CreateAlertSubscriptionRequest {
  webhook_url: string;
  webhook_type: 'discord' | 'slack';
  name?: string;
  systems?: string[];
  regions?: number[];
  min_value?: number;
  include_pods?: boolean;
  ship_types?: string[];
}

export interface TestAlertResponse {
  sent_count: number;
  message: string;
}

// Route profile type
export type RouteProfile = 'shortest' | 'safer' | 'paranoid';
