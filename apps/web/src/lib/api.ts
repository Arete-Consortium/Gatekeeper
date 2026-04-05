/**
 * Gatekeeper API Service
 * Client for the FastAPI backend (Web version using fetch)
 */
import {
  RouteResponse,
  RiskReport,
  MapConfig,
  System,
  Gate,
  HealthResponse,
  ShipProfile,
  ShipProfileListResponse,
  RouteHistoryResponse,
  SystemStats,
  HotSystem,
  FittingAnalysisResponse,
  AlertSubscription,
  AlertSubscriptionListResponse,
  CreateAlertSubscriptionRequest,
  TestAlertResponse,
  RouteProfile,
  SovereigntyResponse,
  FWResponse,
  SovStructuresResponse,
  TheraResponse,
  SystemActivityResponse,
  AppraisalResponse,
  CapitalShipType,
  FuelType,
  JumpRouteResponse,
  BookmarkListResponse,
  BookmarkResponse,
  BookmarkCreate,
  WormholeListResponse,
  JumpBridgeListResponse,
  JumpBridgeConnection,
  JumpBridgeImportResponse,
  CharacterLocation,
  SetWaypointsResponse,
  MarketHubsResponse,
  MarketTickerResponse,
  MarketTickerHistoryResponse,
  IntelParseResponse,
  PilotThreatStats,
  FleetPilotLookupResponse,
  HotzoneResponse,
  FleetAnalysisResponse,
  CharacterListResponse,
  LinkCharacterResponse,
  UnlinkCharacterResponse,
  LinkedCharacter,
} from './types';
import { getStoredToken, BillingStatus } from './auth';

const DEFAULT_API_URL =
  (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').trim();
const TIMEOUT = 30000;

class GatekeeperAPIService {
  private baseUrl: string;

  constructor() {
    this.baseUrl = this.getStoredApiUrl() || DEFAULT_API_URL;
  }

  private getStoredApiUrl(): string | null {
    if (typeof window === 'undefined') return null;
    const stored = localStorage.getItem('gatekeeper_api_url')?.trim();
    if (stored && this.isValidApiUrl(stored)) return stored;
    return null;
  }

  /**
   * Validate that a URL is safe to use as an API endpoint.
   */
  private isValidApiUrl(url: string): boolean {
    try {
      const parsed = new URL(url);
      return ['http:', 'https:'].includes(parsed.protocol);
    } catch {
      return false;
    }
  }

  /**
   * Update the API base URL (for settings)
   */
  setBaseUrl(url: string): void {
    if (!this.isValidApiUrl(url)) {
      throw new Error('Invalid API URL: must be an HTTP or HTTPS URL');
    }
    this.baseUrl = url;
    if (typeof window !== 'undefined') {
      localStorage.setItem('gatekeeper_api_url', url);
    }
  }

  /**
   * Get current base URL
   */
  getBaseUrl(): string {
    return this.baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), TIMEOUT);

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    // Attach JWT if available
    const token = getStoredToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        ...options,
        signal: controller.signal,
        credentials: 'include',
        headers: {
          ...headers,
          ...options.headers,
        },
      });

      if (response.status === 402) {
        if (typeof window !== 'undefined') {
          window.location.href = '/pricing';
        }
        throw new Error('Pro subscription required');
      }

      if (!response.ok) {
        throw new Error(`API Error: ${response.status} ${response.statusText}`);
      }

      return response.json();
    } finally {
      clearTimeout(timeoutId);
    }
  }

  // ==================== Health ====================

  /**
   * Check API health status
   */
  async getHealth(): Promise<HealthResponse> {
    return this.request<HealthResponse>('/health');
  }

  /**
   * Get API info
   */
  async getInfo(): Promise<{ name: string; version: string }> {
    return this.request<{ name: string; version: string }>('/');
  }

  // ==================== Systems ====================

  /**
   * Get all solar systems
   */
  async getSystems(): Promise<System[]> {
    return this.request<System[]>('/systems/');
  }

  /**
   * Get risk report for a system
   */
  async getSystemRisk(
    systemName: string,
    shipProfile?: string
  ): Promise<RiskReport> {
    const params = new URLSearchParams();
    if (shipProfile) {
      params.set('ship_profile', shipProfile);
    }
    const query = params.toString() ? `?${params.toString()}` : '';
    return this.request<RiskReport>(
      `/systems/${encodeURIComponent(systemName)}/risk${query}`
    );
  }

  /**
   * Get available ship profiles
   */
  async getShipProfiles(): Promise<ShipProfile[]> {
    const response = await this.request<ShipProfileListResponse>(
      '/api/v1/systems/profiles/ships'
    );
    return response.profiles;
  }

  /**
   * Get neighboring systems (connected by gates)
   */
  async getSystemNeighbors(systemName: string): Promise<Gate[]> {
    return this.request<Gate[]>(
      `/systems/${encodeURIComponent(systemName)}/neighbors`
    );
  }

  /**
   * Search systems by name prefix
   */
  async searchSystems(query: string, limit: number = 10): Promise<System[]> {
    const systems = await this.getSystems();
    const lowerQuery = query.toLowerCase();
    return systems
      .filter((s) => s.name.toLowerCase().startsWith(lowerQuery))
      .slice(0, limit);
  }

  // ==================== Routing ====================

  /**
   * Calculate route between two systems
   */
  async getRoute(
    fromSystem: string,
    toSystem: string,
    profile: RouteProfile = 'safer',
    options?: { bridges?: boolean; thera?: boolean; pochven?: boolean; avoid?: string[] }
  ): Promise<RouteResponse> {
    const params = new URLSearchParams({
      from: fromSystem,
      to: toSystem,
      profile,
    });
    if (options?.bridges) {
      params.set('bridges', 'true');
    }
    if (options?.thera) {
      params.set('thera', 'true');
    }
    if (options?.pochven) {
      params.set('pochven', 'true');
    }
    if (options?.avoid && options.avoid.length > 0) {
      for (const system of options.avoid) {
        params.append('avoid', system);
      }
    }
    return this.request<RouteResponse>(`/api/v1/route/?${params.toString()}`);
  }

  /**
   * Get full map configuration (systems, gates, risk config)
   */
  async getMapConfig(): Promise<MapConfig> {
    return this.request<MapConfig>('/map/config');
  }

  async getSovereignty(): Promise<SovereigntyResponse> {
    return this.request<SovereigntyResponse>('/map/sovereignty');
  }

  async getFWStatus(): Promise<FWResponse> {
    return this.request<FWResponse>('/map/fw');
  }

  async getSovStructures(): Promise<SovStructuresResponse> {
    return this.request<SovStructuresResponse>('/map/sovereignty/structures');
  }

  async getTheraConnections(): Promise<TheraResponse> {
    return this.request<TheraResponse>('/map/thera');
  }

  async getSystemActivity(): Promise<SystemActivityResponse> {
    return this.request<SystemActivityResponse>('/map/activity');
  }

  /**
   * Get route calculation history
   */
  async getRouteHistory(limit: number = 10): Promise<RouteHistoryResponse> {
    return this.request<RouteHistoryResponse>(`/api/v1/route/history?limit=${limit}`);
  }

  // ==================== Stats ====================

  /**
   * Get zkill stats for a system
   */
  async getSystemStats(
    systemName: string,
    hours: number = 24
  ): Promise<SystemStats> {
    return this.request<SystemStats>(
      `/api/v1/stats/system/${encodeURIComponent(systemName)}?hours=${hours}`
    );
  }

  /**
   * Get zkill stats for multiple systems
   */
  async getBulkStats(
    systemNames: string[],
    hours: number = 24
  ): Promise<Record<string, SystemStats>> {
    const response = await this.request<{ stats: Record<string, SystemStats> }>(
      '/api/v1/stats/bulk',
      {
        method: 'POST',
        body: JSON.stringify({ systems: systemNames, hours }),
      }
    );
    return response.stats;
  }

  /**
   * Get hottest systems by recent activity
   */
  async getHotSystems(hours: number = 24, limit: number = 10): Promise<HotSystem[]> {
    const response = await this.request<{ systems: HotSystem[] }>(
      `/api/v1/stats/hot?hours=${hours}&limit=${limit}`
    );
    return response.systems;
  }

  // ==================== Fitting Analysis ====================

  /**
   * Analyze a ship fitting for travel recommendations
   */
  async analyzeFitting(eftText: string): Promise<FittingAnalysisResponse> {
    return this.request<FittingAnalysisResponse>('/api/v1/fitting/analyze', {
      method: 'POST',
      body: JSON.stringify({ eft_text: eftText }),
    });
  }

  // ==================== Fleet Analysis ====================

  /**
   * Analyze a fleet composition for threat assessment
   */
  async analyzeFleet(text: string): Promise<FleetAnalysisResponse> {
    return this.request<FleetAnalysisResponse>('/api/v1/fleet/analyze', {
      method: 'POST',
      body: JSON.stringify({ text }),
    });
  }

  // ==================== Appraisal ====================

  /**
   * Appraise pasted EVE items with Jita market prices
   */
  async appraise(rawText: string): Promise<AppraisalResponse> {
    return this.request<AppraisalResponse>('/api/v1/appraisal', {
      method: 'POST',
      body: JSON.stringify({ raw_text: rawText }),
    });
  }

  // ==================== Jump Drive ====================

  /**
   * Calculate a capital ship jump route between two systems
   */
  async getJumpRoute(
    fromSystem: string,
    toSystem: string,
    ship: CapitalShipType = 'jump_freighter',
    jdc: number = 5,
    jfc: number = 5,
    fuel?: FuelType,
    via?: string[],
    preferStations: boolean = true
  ): Promise<JumpRouteResponse> {
    const params = new URLSearchParams({
      from: fromSystem,
      to: toSystem,
      ship,
      jdc: jdc.toString(),
      jfc: jfc.toString(),
      prefer_stations: preferStations.toString(),
    });
    if (fuel) params.set('fuel', fuel);
    if (via && via.length > 0) {
      for (const system of via) {
        params.append('via', system);
      }
    }
    return this.request<JumpRouteResponse>(`/api/v1/jump/route?${params.toString()}`);
  }

  // ==================== Alert Subscriptions ====================

  /**
   * List all alert subscriptions
   */
  async listAlertSubscriptions(): Promise<AlertSubscriptionListResponse> {
    return this.request<AlertSubscriptionListResponse>('/api/v1/alerts/subscriptions');
  }

  /**
   * Create a new alert subscription
   */
  async createAlertSubscription(
    data: CreateAlertSubscriptionRequest
  ): Promise<AlertSubscription> {
    return this.request<AlertSubscription>('/api/v1/alerts/subscriptions', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  /**
   * Delete an alert subscription
   */
  async deleteAlertSubscription(subscriptionId: string): Promise<void> {
    await this.request<void>(`/api/v1/alerts/subscriptions/${subscriptionId}`, {
      method: 'DELETE',
    });
  }

  /**
   * Update an alert subscription (e.g. toggle enabled)
   */
  async updateAlertSubscription(
    subscriptionId: string,
    data: { enabled?: boolean }
  ): Promise<AlertSubscription> {
    return this.request<AlertSubscription>(
      `/api/v1/alerts/subscriptions/${subscriptionId}`,
      { method: 'PATCH', body: JSON.stringify(data) }
    );
  }

  /**
   * Send a test alert to verify webhook configuration
   */
  async sendTestAlert(
    systemName: string = 'Jita',
    shipType: string = 'Caracal',
    totalValue: number = 100000000
  ): Promise<TestAlertResponse> {
    return this.request<TestAlertResponse>('/api/v1/alerts/test', {
      method: 'POST',
      body: JSON.stringify({
        system_name: systemName,
        ship_type: shipType,
        total_value: totalValue,
      }),
    });
  }

  // ==================== Billing ====================

  /**
   * Get current subscription/billing status
   */
  async getSubscriptionStatus(): Promise<BillingStatus> {
    return this.request<BillingStatus>('/api/v1/billing/status');
  }

  /**
   * Create a Stripe checkout session for Pro upgrade
   */
  async createCheckoutSession(
    successUrl: string,
    cancelUrl: string
  ): Promise<{ checkout_url: string }> {
    return this.request<{ checkout_url: string }>(
      '/api/v1/billing/create-checkout',
      {
        method: 'POST',
        body: JSON.stringify({
          success_url: successUrl,
          cancel_url: cancelUrl,
        }),
      }
    );
  }

  /**
   * Create a Stripe portal session for billing management
   */
  async createPortalSession(
    returnUrl: string
  ): Promise<{ portal_url: string }> {
    return this.request<{ portal_url: string }>(
      '/api/v1/billing/create-portal',
      {
        method: 'POST',
        body: JSON.stringify({ return_url: returnUrl }),
      }
    );
  }

  // ==================== Bookmarks ====================

  async getBookmarks(): Promise<BookmarkListResponse> {
    return this.request<BookmarkListResponse>('/api/v1/bookmarks/');
  }

  async createBookmark(data: BookmarkCreate): Promise<BookmarkResponse> {
    return this.request<BookmarkResponse>('/api/v1/bookmarks/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async deleteBookmark(id: number): Promise<void> {
    await this.request<void>(`/api/v1/bookmarks/${id}`, {
      method: 'DELETE',
    });
  }

  // ==================== Wormhole Connections ====================

  async getWormholes(): Promise<WormholeListResponse> {
    return this.request<WormholeListResponse>('/api/v1/wormholes/');
  }

  async getSystemWormholes(systemName: string): Promise<WormholeListResponse> {
    return this.request<WormholeListResponse>(
      `/api/v1/wormholes/system/${encodeURIComponent(systemName)}`
    );
  }

  // ==================== Jump Bridge Connections ====================

  async getJumpBridges(): Promise<JumpBridgeListResponse> {
    return this.request<JumpBridgeListResponse>('/api/v1/jumpbridges/');
  }

  async addJumpBridge(fromSystem: string, toSystem: string, ownerAlliance?: string): Promise<JumpBridgeConnection> {
    return this.request<JumpBridgeConnection>('/api/v1/jumpbridges/', {
      method: 'POST',
      body: JSON.stringify({
        from_system: fromSystem,
        to_system: toSystem,
        owner_alliance: ownerAlliance || null,
      }),
    });
  }

  async deleteJumpBridge(bridgeId: string): Promise<void> {
    await this.request<void>(`/api/v1/jumpbridges/${bridgeId}`, {
      method: 'DELETE',
    });
  }

  async importJumpBridges(text: string): Promise<JumpBridgeImportResponse> {
    return this.request<JumpBridgeImportResponse>('/api/v1/jumpbridges/import', {
      method: 'POST',
      body: JSON.stringify({ text }),
    });
  }

  // ==================== Character ====================

  async getCharacterLocation(): Promise<CharacterLocation> {
    return this.request<CharacterLocation>('/api/v1/character/location');
  }

  async setWaypoints(systems: string[], clearExisting: boolean = true): Promise<SetWaypointsResponse> {
    return this.request<SetWaypointsResponse>('/api/v1/character/set-waypoints', {
      method: 'POST',
      body: JSON.stringify({ systems, clear_existing: clearExisting }),
    });
  }

  // ==================== Characters (Multi-Character) ====================

  /**
   * List all linked characters with their status
   */
  async getLinkedCharacters(sessionId?: string): Promise<CharacterListResponse> {
    const headers: Record<string, string> = {};
    if (sessionId) {
      headers['X-Session-Id'] = sessionId;
    }
    return this.request<CharacterListResponse>('/api/v1/characters/', { headers });
  }

  /**
   * Link a new alt character (starts SSO flow)
   */
  async linkCharacter(): Promise<LinkCharacterResponse> {
    return this.request<LinkCharacterResponse>('/api/v1/characters/link', {
      method: 'POST',
    });
  }

  /**
   * Unlink a character by removing its token and preferences
   */
  async unlinkCharacter(characterId: number): Promise<UnlinkCharacterResponse> {
    return this.request<UnlinkCharacterResponse>(`/api/v1/characters/${characterId}`, {
      method: 'DELETE',
    });
  }

  /**
   * Set a character as the active character
   */
  async setActiveCharacter(characterId: number, sessionId: string): Promise<LinkedCharacter> {
    return this.request<LinkedCharacter>(`/api/v1/characters/${characterId}/active`, {
      method: 'POST',
      headers: { 'X-Session-Id': sessionId },
    });
  }

  // ==================== Hotzones ====================

  /**
   * Get hotzone systems with trends and predictions
   */
  async getHotzones(hours: number = 1, limit: number = 25, sec?: string): Promise<HotzoneResponse> {
    const params = new URLSearchParams({ hours: hours.toString(), limit: limit.toString() });
    if (sec) params.set('sec', sec);
    return this.request<HotzoneResponse>(`/api/v1/stats/hotzones?${params.toString()}`);
  }

  // ==================== Pilot Intel ====================

  /**
   * Get pilot threat assessment by character ID
   */
  async getPilotStats(characterId: number): Promise<PilotThreatStats> {
    return this.request<PilotThreatStats>(`/api/v1/intel/pilot/${characterId}`);
  }

  /**
   * Bulk pilot threat lookup by names
   */
  async fleetPilotLookup(names: string[]): Promise<FleetPilotLookupResponse> {
    return this.request<FleetPilotLookupResponse>('/api/v1/intel/pilot/fleet-lookup', {
      method: 'POST',
      body: JSON.stringify({ names }),
    });
  }

  /**
   * Search for character names (autocomplete)
   */
  async searchCharacters(query: string): Promise<{ results: { id: number; name: string }[] }> {
    return this.request<{ results: { id: number; name: string }[] }>(
      `/api/v1/intel/pilot/search?q=${encodeURIComponent(query)}`
    );
  }

  /**
   * Search for system names via ESI (autocomplete)
   */
  async searchSystemsESI(query: string): Promise<{ results: { id: number; name: string }[] }> {
    return this.request<{ results: { id: number; name: string }[] }>(
      `/api/v1/intel/system/search?q=${encodeURIComponent(query)}`
    );
  }

  /**
   * Get pilot deep-dive intel report
   */
  async getPilotDeepDive(characterId: number): Promise<import('./types').PilotDeepDiveStats> {
    return this.request<import('./types').PilotDeepDiveStats>(
      `/api/v1/intel/pilot/${characterId}/deep-dive`
    );
  }

  // ==================== Intel Parse ====================

  /**
   * Parse intel/local chat text to extract systems and status
   */
  async parseIntel(text: string): Promise<IntelParseResponse> {
    return this.request<IntelParseResponse>('/api/v1/intel-parse/parse', {
      method: 'POST',
      body: JSON.stringify({ text }),
    });
  }

  // ==================== Market Hubs ====================

  /**
   * Get market hub data for the 5 major trade hubs
   */
  async getMarketHubs(): Promise<MarketHubsResponse> {
    return this.request<MarketHubsResponse>('/map/market-hubs');
  }

  // ==================== Market Ticker ====================

  /**
   * Get market ticker with latest prices for all tracked items
   */
  async getMarketTicker(): Promise<MarketTickerResponse> {
    return this.request<MarketTickerResponse>('/api/v1/market/ticker');
  }

  /**
   * Get market history for a specific item across trade hub regions
   */
  async getMarketTickerItem(typeId: number): Promise<MarketTickerHistoryResponse> {
    return this.request<MarketTickerHistoryResponse>(`/api/v1/market/ticker/${typeId}`);
  }

  // ==================== Utility ====================

  /**
   * Test connection to the API
   */
  async testConnection(): Promise<boolean> {
    try {
      await this.getHealth();
      return true;
    } catch {
      return false;
    }
  }
}

// Export singleton instance
export const GatekeeperAPI = new GatekeeperAPIService();
export default GatekeeperAPI;
