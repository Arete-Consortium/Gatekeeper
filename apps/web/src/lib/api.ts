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
} from './types';
import { getStoredToken, BillingStatus } from './auth';

const DEFAULT_API_URL =
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const TIMEOUT = 30000;

class GatekeeperAPIService {
  private baseUrl: string;

  constructor() {
    this.baseUrl = this.getStoredApiUrl() || DEFAULT_API_URL;
  }

  private getStoredApiUrl(): string | null {
    if (typeof window === 'undefined') return null;
    const stored = localStorage.getItem('gatekeeper_api_url');
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
    options?: { bridges?: boolean; thera?: boolean }
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
    return this.request<RouteResponse>(`/map/route?${params.toString()}`);
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
