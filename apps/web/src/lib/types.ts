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
  security: number;
  category: string;
  region_id: number;
  region_name?: string;
  constellation_id?: number;
  constellation_name?: string;
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
  pirate_suppressed?: boolean;
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
  system_id: number;
  security_status: number;
  cumulative_jumps: number;
  cumulative_cost: number;
  risk_score: number;
  connection_type: string;
  pirate_suppressed?: boolean;
}

// Complete route response
export interface RouteResponse {
  from_system: string;
  to_system: string;
  path: RouteHop[];
  total_jumps: number;
  total_cost: number;
  max_risk: number;
  avg_risk: number;
  profile: 'shortest' | 'safer' | 'paranoid';
  bridges_used: number;
  thera_used: number;
  pochven_used: number;
  wormholes_used: number;
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

// System activity data
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

// Appraisal types
export interface AppraisalItem {
  name: string;
  type_id: number;
  quantity: number;
  buy_price: number;
  sell_price: number;
  buy_total: number;
  sell_total: number;
}

export interface AppraisalResponse {
  items: AppraisalItem[];
  total_buy: number;
  total_sell: number;
  unknown_items: string[];
  item_count: number;
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
  region_name?: string;
  min_value?: number;
  include_pods?: boolean;
  ship_types?: string[];
}

export interface TestAlertResponse {
  sent_count: number;
  message: string;
}

// Jump drive types
export type CapitalShipType = 'jump_freighter' | 'carrier' | 'dreadnought' | 'force_auxiliary' | 'supercarrier' | 'titan' | 'rorqual' | 'black_ops';

export type FuelType = 'nitrogen' | 'helium' | 'oxygen' | 'hydrogen';

export interface JumpLegResponse {
  from_system: string;
  to_system: string;
  distance_ly: number;
  fuel_required: number;
  fatigue_added_minutes: number;
  total_fatigue_minutes: number;
  wait_time_minutes: number;
}

export interface JumpRouteResponse {
  from_system: string;
  to_system: string;
  ship_type: string;
  total_jumps: number;
  total_distance_ly: number;
  total_fuel: number;
  total_fatigue_minutes: number;
  total_travel_time_minutes: number;
  legs: JumpLegResponse[];
  fuel_type_id: number;
  fuel_type_name: string;
  fuel_unit_cost: number;
  total_fuel_cost: number;
}

// Route profile type
export type RouteProfile = 'shortest' | 'safer' | 'paranoid';

// Route bookmark
export interface BookmarkResponse {
  id: number;
  character_id: number;
  name: string;
  from_system: string;
  to_system: string;
  profile: string;
  avoid_systems: string[];
  use_bridges: boolean;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface BookmarkListResponse {
  bookmarks: BookmarkResponse[];
  total: number;
}

export interface BookmarkCreate {
  name: string;
  from_system: string;
  to_system: string;
  profile?: string;
  avoid_systems?: string[];
  use_bridges?: boolean;
  notes?: string | null;
}

// Wormhole connection (user-submitted)
export interface WormholeConnection {
  id: string;
  from_system: string;
  from_system_id: number;
  to_system: string;
  to_system_id: number;
  wormhole_type: 'static' | 'wandering' | 'k162' | 'frigate' | 'drifter';
  mass_status: 'stable' | 'destabilized' | 'critical' | 'collapsed';
  life_status: 'stable' | 'eol' | 'expired';
  bidirectional: boolean;
  created_at: string;
  created_by: string | null;
  notes: string | null;
}

export interface WormholeListResponse {
  count: number;
  connections: WormholeConnection[];
}

// Jump bridge connection (user-submitted)
export interface JumpBridgeConnection {
  id: string;
  from_system: string;
  from_system_id: number;
  to_system: string;
  to_system_id: number;
  owner_alliance: string | null;
  status: 'online' | 'offline' | 'unknown';
  created_at: string;
  created_by: string | null;
  notes: string;
}

export interface JumpBridgeListResponse {
  bridges: JumpBridgeConnection[];
  total: number;
}

export interface JumpBridgeImportResponse {
  imported: number;
  skipped: number;
  errors: string[];
  bridges: JumpBridgeConnection[];
}

// Character location
export interface CharacterLocation {
  solar_system_id: number;
  solar_system_name: string | null;
  security: number | null;
  region_name: string | null;
  station_id: number | null;
  structure_id: number | null;
}

// Market hub data
export interface MarketHub {
  system_id: number;
  system_name: string;
  region_name: string;
  is_primary: boolean;
  daily_volume_estimate: number;
  active_orders?: number;
}

export interface MarketHubsResponse {
  hubs: MarketHub[];
}

// Intel chat parser types
export interface ParsedSystem {
  system_name: string;
  system_id: number;
  status: 'clear' | 'hostile' | 'unknown';
  hostile_count: number;
  mentioned_at: string;
}

export interface IntelParseResponse {
  systems: ParsedSystem[];
  unknown_lines: string[];
}

// Fleet composition analysis
export interface FleetShipEntry {
  name: string;
  count: number;
  role: string;
}

export interface FleetAnalysisResponse {
  total_pilots: number;
  total_ships: number;
  threat_level: 'minimal' | 'moderate' | 'significant' | 'critical' | 'overwhelming';
  composition: Record<string, number>;
  ship_list: FleetShipEntry[];
  has_logistics: boolean;
  has_capitals: boolean;
  has_tackle: boolean;
  estimated_dps_category: 'low' | 'medium' | 'high' | 'extreme';
  advice: string[];
}

// Multi-character management
export interface LinkedCharacter {
  character_id: number;
  character_name: string;
  is_active: boolean;
  preferences: Record<string, unknown> | null;
  location: CharacterLocation | null;
}

export interface CharacterListResponse {
  characters: LinkedCharacter[];
  active_character_id: number | null;
  total_count: number;
}

export interface LinkCharacterResponse {
  auth_url: string;
  state: string;
  message: string;
}

export interface UnlinkCharacterResponse {
  status: string;
  character_id: number;
  character_name: string | null;
}

// Market ticker
export interface MarketTickerItem {
  type_id: number;
  type_name: string;
  region_id: number;
  region_name: string;
  average_price: number;
  highest: number;
  lowest: number;
  volume: number;
  date: string;
  price_change_pct: number;
}

export interface MarketTickerResponse {
  items: MarketTickerItem[];
  item_count: number;
}

export interface MarketTickerHistoryResponse {
  type_id: number;
  type_name: string;
  history: MarketTickerItem[];
}

// Hotzone system with trend prediction
export interface HotzoneSystemData {
  system_id: number;
  system_name: string;
  security: number;
  category: string;
  region_name: string;
  kills_current: number;
  pods_current: number;
  kills_previous: number;
  trend: number;
  predicted_1hr: number;
  predicted_2hr: number;
  gate_camp_likely: boolean;
}

export interface HotzoneResponse {
  hours: number;
  total: number;
  systems: HotzoneSystemData[];
}

// Pilot threat assessment
export interface PilotThreatStats {
  character_id: number;
  name: string;
  corporation_id: number | null;
  corporation_name: string;
  alliance_id: number | null;
  alliance_name: string | null;
  security_status: number;
  birthday: string | null;
  kills: number;
  losses: number;
  kd_ratio: number;
  solo_kills: number;
  danger_ratio: number;
  gang_ratio: number;
  isk_destroyed: number;
  isk_lost: number;
  active_pvp_kills: number;
  threat_level: 'minimal' | 'low' | 'moderate' | 'high' | 'extreme';
  active_timezone: string | null;
  flags: string[];
  top_ships: { id: number; name: string; kills: number }[];
  top_systems: { id: number; name: string; kills: number }[];
}

// Pilot deep-dive intel report
export interface PilotDeepDiveStats extends PilotThreatStats {
  fleet_companions: { character_id: number; name: string; kills: number }[];
  activity_pattern: { hourly: Record<string, number>; peak_hours: number[] };
  corp_history: { corporation_id: number; corporation_name: string; start_date: string }[];
  recent_kills: {
    kill_id: number;
    timestamp: string;
    system_id: number | null;
    system_name: string;
    ship_type_id: number | null;
    ship_name: string;
    value: number;
    is_loss: boolean;
    attacker_count: number;
  }[];
}

// Fleet pilot lookup
export interface FleetPilotLookupResponse {
  total_pilots: number;
  resolved: number;
  failed_names: string[];
  pilots: PilotThreatStats[];
  aggregate: {
    avg_kd: number;
    timezone_breakdown: Record<string, number>;
    threat_breakdown: Record<string, number>;
    flag_counts: Record<string, number>;
    total_kills: number;
    total_losses: number;
  };
}

// Waypoint sync
export interface SetWaypointsRequest {
  systems: string[];
  clear_existing: boolean;
}

export interface SetWaypointsResponse {
  success: boolean;
  waypoints_set: number;
  systems: string[];
}
