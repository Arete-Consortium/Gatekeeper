/**
 * Gatekeeper API Service
 * Client for the FastAPI backend
 */
import axios, { AxiosInstance, AxiosError } from 'axios';
import { API_CONFIG } from '../config';
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
} from '../types';

class GatekeeperAPIService {
  private client: AxiosInstance;
  private baseUrl: string;

  constructor() {
    this.baseUrl = API_CONFIG.GATEKEEPER_URL;
    this.client = axios.create({
      baseURL: this.baseUrl,
      timeout: API_CONFIG.TIMEOUT,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        console.error('API Error:', error.message);
        if (error.response) {
          console.error('Status:', error.response.status);
          console.error('Data:', error.response.data);
        }
        return Promise.reject(error);
      }
    );
  }

  /**
   * Update the API base URL (for settings)
   */
  setBaseUrl(url: string): void {
    this.baseUrl = url;
    this.client.defaults.baseURL = url;
  }

  /**
   * Get current base URL
   */
  getBaseUrl(): string {
    return this.baseUrl;
  }

  // ==================== Health ====================

  /**
   * Check API health status
   */
  async getHealth(): Promise<HealthResponse> {
    const response = await this.client.get('/health');
    return response.data;
  }

  /**
   * Get API info
   */
  async getInfo(): Promise<{ name: string; version: string }> {
    const response = await this.client.get('/');
    return response.data;
  }

  // ==================== Systems ====================

  /**
   * Get all solar systems
   */
  async getSystems(): Promise<System[]> {
    const response = await this.client.get('/systems/');
    return response.data;
  }

  /**
   * Get risk report for a system
   */
  async getSystemRisk(
    systemName: string,
    shipProfile?: string
  ): Promise<RiskReport> {
    const params: Record<string, string> = {};
    if (shipProfile) {
      params.ship_profile = shipProfile;
    }
    const response = await this.client.get(
      `/systems/${encodeURIComponent(systemName)}/risk`,
      { params }
    );
    return response.data;
  }

  /**
   * Get available ship profiles
   */
  async getShipProfiles(): Promise<ShipProfile[]> {
    const response = await this.client.get<ShipProfileListResponse>('/systems/profiles/ships');
    return response.data.profiles;
  }

  /**
   * Get neighboring systems (connected by gates)
   */
  async getSystemNeighbors(systemName: string): Promise<Gate[]> {
    const response = await this.client.get(`/systems/${encodeURIComponent(systemName)}/neighbors`);
    return response.data;
  }

  // ==================== Routing ====================

  /**
   * Calculate route between two systems
   */
  async getRoute(
    fromSystem: string,
    toSystem: string,
    profile: 'shortest' | 'safer' | 'paranoid' = 'safer',
    options?: { bridges?: boolean; thera?: boolean }
  ): Promise<RouteResponse> {
    const params: Record<string, string | boolean> = {
      from: fromSystem,
      to: toSystem,
      profile,
    };
    if (options?.bridges) {
      params.bridges = true;
    }
    if (options?.thera) {
      params.thera = true;
    }
    const response = await this.client.get('/map/route', { params });
    return response.data;
  }

  /**
   * Get full map configuration (systems, gates, risk config)
   */
  async getMapConfig(): Promise<MapConfig> {
    const response = await this.client.get('/map/config');
    return response.data;
  }

  /**
   * Get route calculation history
   */
  async getRouteHistory(limit: number = 10): Promise<RouteHistoryResponse> {
    const response = await this.client.get('/route/history', {
      params: { limit },
    });
    return response.data;
  }

  // ==================== Stats ====================

  /**
   * Get zkill stats for a system
   */
  async getSystemStats(systemName: string, hours: number = 24): Promise<SystemStats> {
    const response = await this.client.get(
      `/stats/system/${encodeURIComponent(systemName)}`,
      { params: { hours } }
    );
    return response.data;
  }

  /**
   * Get zkill stats for multiple systems
   */
  async getBulkStats(
    systemNames: string[],
    hours: number = 24
  ): Promise<Record<string, SystemStats>> {
    const response = await this.client.post('/stats/bulk', {
      systems: systemNames,
      hours,
    });
    return response.data.stats;
  }

  /**
   * Get hottest systems by recent activity
   */
  async getHotSystems(hours: number = 24, limit: number = 10): Promise<HotSystem[]> {
    const response = await this.client.get('/stats/hot', {
      params: { hours, limit },
    });
    return response.data.systems;
  }

  // ==================== Batch Operations ====================

  /**
   * Get risk reports for multiple systems
   */
  async getMultipleSystemRisks(systemNames: string[]): Promise<Map<string, RiskReport>> {
    const riskMap = new Map<string, RiskReport>();

    const promises = systemNames.map(async (name) => {
      try {
        const risk = await this.getSystemRisk(name);
        riskMap.set(name, risk);
      } catch (error) {
        console.warn(`Failed to get risk for ${name}:`, error);
      }
    });

    await Promise.all(promises);
    return riskMap;
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
