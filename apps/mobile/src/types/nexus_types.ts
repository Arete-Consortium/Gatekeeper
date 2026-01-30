// ESI/EVE Online Types
export interface Character {
  character_id: number;
  character_name: string;
  corporation_id: number;
  alliance_id?: number;
  birthday: string;
  security_status: number;
  access_token?: string;
  refresh_token?: string;
  token_expiry?: number;
}

export interface Asset {
  item_id: number;
  location_id: number;
  location_type: string;
  type_id: number;
  type_name?: string;
  quantity: number;
  location_flag: string;
  is_singleton: boolean;
}

export interface MarketOrder {
  order_id: number;
  type_id: number;
  type_name?: string;
  location_id: number;
  volume_total: number;
  volume_remain: number;
  min_volume: number;
  price: number;
  is_buy_order: boolean;
  duration: number;
  issued: string;
  range: string;
}

export interface ShipFit {
  ship_type_id: number;
  ship_name: string;
  fit_name: string;
  description?: string;
  low_slots: FitModule[];
  mid_slots: FitModule[];
  high_slots: FitModule[];
  rig_slots: FitModule[];
  subsystems?: FitModule[];
  drones?: FitModule[];
  cargo?: FitModule[];
}

export interface FitModule {
  type_id: number;
  type_name: string;
  slot: string;
  quantity: number;
}

export interface SolarSystem {
  system_id: number;
  system_name: string;
  constellation_id: number;
  region_id: number;
  security_status: number;
  star_id: number;
  stargates?: number[];
  stations?: number[];
  planets?: number[];
  position: {
    x: number;
    y: number;
    z: number;
  };
}

export interface Stargate {
  stargate_id: number;
  system_id: number;
  destination: {
    stargate_id: number;
    system_id: number;
  };
  position: {
    x: number;
    y: number;
    z: number;
  };
}

export interface Route {
  origin: number;
  destination: number;
  systems: number[];
  jumps: number;
  avoid_systems?: number[];
  route_type: "shortest" | "safest" | "jump_capable";
}

export interface ZKillboardData {
  system_id: number;
  kills_last_hour: number;
  danger_rating: "low" | "medium" | "high" | "extreme";
  recent_kills: KillmailSummary[];
}

export interface KillmailSummary {
  killmail_id: number;
  killmail_time: string;
  solar_system_id: number;
  victim_ship_type_id: number;
  total_value: number;
}

export interface JumpCapableShip {
  type_id: number;
  jump_drive_range: number;
  jump_fuel_consumption: number;
  current_fuel: number;
}

export interface AIRouteSuggestion {
  route: Route;
  risk_assessment: string;
  estimated_time: number;
  fuel_required?: number;
  alternative_routes: Route[];
  warnings: string[];
}

export interface Skills {
  character_id: number;
  skills: Skill[];
  total_sp: number;
}

export interface Skill {
  skill_id: number;
  skill_name?: string;
  trained_skill_level: number;
  active_skill_level: number;
  skillpoints_in_skill: number;
}
