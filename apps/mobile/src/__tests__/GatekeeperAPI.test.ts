/**
 * Tests for GatekeeperAPI service
 */
import axios from 'axios';

// Mock axios
jest.mock('axios', () => ({
  create: jest.fn(() => ({
    get: jest.fn(),
    post: jest.fn(),
    defaults: { baseURL: '' },
    interceptors: {
      response: {
        use: jest.fn(),
      },
    },
  })),
}));

// Import after mocking
import { GatekeeperAPI } from '../services/GatekeeperAPI';

describe('GatekeeperAPI', () => {
  let mockClient: {
    get: jest.Mock;
    post: jest.Mock;
    defaults: { baseURL: string };
  };

  beforeEach(() => {
    jest.clearAllMocks();
    // Get the mock client
    mockClient = (axios.create as jest.Mock).mock.results[0]?.value || {
      get: jest.fn(),
      post: jest.fn(),
      defaults: { baseURL: '' },
    };
  });

  describe('setBaseUrl', () => {
    it('should update the base URL', () => {
      const newUrl = 'http://new-api.example.com';
      GatekeeperAPI.setBaseUrl(newUrl);
      expect(GatekeeperAPI.getBaseUrl()).toBe(newUrl);
    });
  });

  describe('getBaseUrl', () => {
    it('should return the current base URL', () => {
      const url = GatekeeperAPI.getBaseUrl();
      expect(typeof url).toBe('string');
    });
  });

  describe('testConnection', () => {
    it('should return true when API is reachable', async () => {
      // Mock successful health check
      const mockGet = jest.fn().mockResolvedValue({ data: { status: 'ok' } });
      (GatekeeperAPI as any).client = { get: mockGet, post: jest.fn(), defaults: { baseURL: '' } };

      const result = await GatekeeperAPI.testConnection();
      expect(result).toBe(true);
      expect(mockGet).toHaveBeenCalledWith('/health');
    });

    it('should return false when API is unreachable', async () => {
      // Mock failed health check
      const mockGet = jest.fn().mockRejectedValue(new Error('Network error'));
      (GatekeeperAPI as any).client = { get: mockGet, post: jest.fn(), defaults: { baseURL: '' } };

      const result = await GatekeeperAPI.testConnection();
      expect(result).toBe(false);
    });
  });

  describe('getHealth', () => {
    it('should return health status', async () => {
      const healthData = { status: 'ok', version: '1.0.0' };
      const mockGet = jest.fn().mockResolvedValue({ data: healthData });
      (GatekeeperAPI as any).client = { get: mockGet, post: jest.fn(), defaults: { baseURL: '' } };

      const result = await GatekeeperAPI.getHealth();
      expect(result).toEqual(healthData);
      expect(mockGet).toHaveBeenCalledWith('/health');
    });
  });

  describe('getInfo', () => {
    it('should return API info', async () => {
      const infoData = { name: 'EVE Gatekeeper', version: '1.3.0' };
      const mockGet = jest.fn().mockResolvedValue({ data: infoData });
      (GatekeeperAPI as any).client = { get: mockGet, post: jest.fn(), defaults: { baseURL: '' } };

      const result = await GatekeeperAPI.getInfo();
      expect(result).toEqual(infoData);
      expect(mockGet).toHaveBeenCalledWith('/');
    });
  });

  describe('getSystems', () => {
    it('should return list of systems', async () => {
      const systemsData = [
        { name: 'Jita', security: 0.9 },
        { name: 'Amarr', security: 1.0 },
      ];
      const mockGet = jest.fn().mockResolvedValue({ data: systemsData });
      (GatekeeperAPI as any).client = { get: mockGet, post: jest.fn(), defaults: { baseURL: '' } };

      const result = await GatekeeperAPI.getSystems();
      expect(result).toEqual(systemsData);
      expect(mockGet).toHaveBeenCalledWith('/systems/');
    });
  });

  describe('getSystemRisk', () => {
    it('should return risk report for a system', async () => {
      const riskData = { system: 'Jita', risk_level: 'low', score: 0.2 };
      const mockGet = jest.fn().mockResolvedValue({ data: riskData });
      (GatekeeperAPI as any).client = { get: mockGet, post: jest.fn(), defaults: { baseURL: '' } };

      const result = await GatekeeperAPI.getSystemRisk('Jita');
      expect(result).toEqual(riskData);
      expect(mockGet).toHaveBeenCalledWith('/systems/Jita/risk', { params: {} });
    });

    it('should include ship profile when provided', async () => {
      const riskData = { system: 'Jita', risk_level: 'medium', score: 0.5 };
      const mockGet = jest.fn().mockResolvedValue({ data: riskData });
      (GatekeeperAPI as any).client = { get: mockGet, post: jest.fn(), defaults: { baseURL: '' } };

      const result = await GatekeeperAPI.getSystemRisk('Jita', 'hauler');
      expect(result).toEqual(riskData);
      expect(mockGet).toHaveBeenCalledWith('/systems/Jita/risk', {
        params: { ship_profile: 'hauler' },
      });
    });

    it('should encode special characters in system name', async () => {
      const mockGet = jest.fn().mockResolvedValue({ data: {} });
      (GatekeeperAPI as any).client = { get: mockGet, post: jest.fn(), defaults: { baseURL: '' } };

      await GatekeeperAPI.getSystemRisk('HED-GP');
      expect(mockGet).toHaveBeenCalledWith('/systems/HED-GP/risk', { params: {} });
    });
  });

  describe('getShipProfiles', () => {
    it('should return list of ship profiles', async () => {
      const profilesData = {
        profiles: [
          { name: 'default', description: 'Standard' },
          { name: 'hauler', description: 'Industrial' },
        ],
      };
      const mockGet = jest.fn().mockResolvedValue({ data: profilesData });
      (GatekeeperAPI as any).client = { get: mockGet, post: jest.fn(), defaults: { baseURL: '' } };

      const result = await GatekeeperAPI.getShipProfiles();
      expect(result).toEqual(profilesData.profiles);
      expect(mockGet).toHaveBeenCalledWith('/systems/profiles/ships');
    });
  });

  describe('getRoute', () => {
    it('should calculate route between systems', async () => {
      const routeData = {
        route: ['Jita', 'Perimeter', 'Urlen'],
        jumps: 2,
        profile: 'safer',
      };
      const mockGet = jest.fn().mockResolvedValue({ data: routeData });
      (GatekeeperAPI as any).client = { get: mockGet, post: jest.fn(), defaults: { baseURL: '' } };

      const result = await GatekeeperAPI.getRoute('Jita', 'Urlen');
      expect(result).toEqual(routeData);
      expect(mockGet).toHaveBeenCalledWith('/map/route', {
        params: { from: 'Jita', to: 'Urlen', profile: 'safer' },
      });
    });

    it('should use specified profile', async () => {
      const mockGet = jest.fn().mockResolvedValue({ data: {} });
      (GatekeeperAPI as any).client = { get: mockGet, post: jest.fn(), defaults: { baseURL: '' } };

      await GatekeeperAPI.getRoute('Jita', 'Amarr', 'paranoid');
      expect(mockGet).toHaveBeenCalledWith('/map/route', {
        params: { from: 'Jita', to: 'Amarr', profile: 'paranoid' },
      });
    });
  });

  describe('getRouteHistory', () => {
    it('should return route history', async () => {
      const historyData = {
        history: [
          { from_system: 'Jita', to_system: 'Amarr', timestamp: '2025-01-01' },
        ],
        total: 1,
      };
      const mockGet = jest.fn().mockResolvedValue({ data: historyData });
      (GatekeeperAPI as any).client = { get: mockGet, post: jest.fn(), defaults: { baseURL: '' } };

      const result = await GatekeeperAPI.getRouteHistory(5);
      expect(result).toEqual(historyData);
      expect(mockGet).toHaveBeenCalledWith('/route/history', { params: { limit: 5 } });
    });

    it('should use default limit', async () => {
      const mockGet = jest.fn().mockResolvedValue({ data: { history: [], total: 0 } });
      (GatekeeperAPI as any).client = { get: mockGet, post: jest.fn(), defaults: { baseURL: '' } };

      await GatekeeperAPI.getRouteHistory();
      expect(mockGet).toHaveBeenCalledWith('/route/history', { params: { limit: 10 } });
    });
  });

  describe('getSystemStats', () => {
    it('should return system stats', async () => {
      const statsData = { kills: 10, ships_destroyed: 5 };
      const mockGet = jest.fn().mockResolvedValue({ data: statsData });
      (GatekeeperAPI as any).client = { get: mockGet, post: jest.fn(), defaults: { baseURL: '' } };

      const result = await GatekeeperAPI.getSystemStats('Tama', 12);
      expect(result).toEqual(statsData);
      expect(mockGet).toHaveBeenCalledWith('/stats/system/Tama', { params: { hours: 12 } });
    });
  });

  describe('getBulkStats', () => {
    it('should return stats for multiple systems', async () => {
      const bulkData = {
        stats: {
          Jita: { kills: 5 },
          Amarr: { kills: 3 },
        },
      };
      const mockPost = jest.fn().mockResolvedValue({ data: bulkData });
      (GatekeeperAPI as any).client = { get: jest.fn(), post: mockPost, defaults: { baseURL: '' } };

      const result = await GatekeeperAPI.getBulkStats(['Jita', 'Amarr'], 24);
      expect(result).toEqual(bulkData.stats);
      expect(mockPost).toHaveBeenCalledWith('/stats/bulk', {
        systems: ['Jita', 'Amarr'],
        hours: 24,
      });
    });
  });

  describe('getHotSystems', () => {
    it('should return hottest systems', async () => {
      const hotData = {
        systems: [
          { system_name: 'Tama', recent_kills: 50 },
          { system_name: 'Amamake', recent_kills: 30 },
        ],
      };
      const mockGet = jest.fn().mockResolvedValue({ data: hotData });
      (GatekeeperAPI as any).client = { get: mockGet, post: jest.fn(), defaults: { baseURL: '' } };

      const result = await GatekeeperAPI.getHotSystems(48, 5);
      expect(result).toEqual(hotData.systems);
      expect(mockGet).toHaveBeenCalledWith('/stats/hot', { params: { hours: 48, limit: 5 } });
    });
  });

  describe('getMultipleSystemRisks', () => {
    it('should return risk reports for multiple systems', async () => {
      const mockGet = jest
        .fn()
        .mockResolvedValueOnce({ data: { system: 'Jita', score: 0.2 } })
        .mockResolvedValueOnce({ data: { system: 'Amarr', score: 0.1 } });
      (GatekeeperAPI as any).client = { get: mockGet, post: jest.fn(), defaults: { baseURL: '' } };

      const result = await GatekeeperAPI.getMultipleSystemRisks(['Jita', 'Amarr']);
      expect(result.size).toBe(2);
      expect(result.get('Jita')).toEqual({ system: 'Jita', score: 0.2 });
      expect(result.get('Amarr')).toEqual({ system: 'Amarr', score: 0.1 });
    });

    it('should handle partial failures gracefully', async () => {
      const mockGet = jest
        .fn()
        .mockResolvedValueOnce({ data: { system: 'Jita', score: 0.2 } })
        .mockRejectedValueOnce(new Error('Not found'));
      (GatekeeperAPI as any).client = { get: mockGet, post: jest.fn(), defaults: { baseURL: '' } };

      // Should not throw
      const result = await GatekeeperAPI.getMultipleSystemRisks(['Jita', 'Unknown']);
      expect(result.size).toBe(1);
      expect(result.has('Jita')).toBe(true);
      expect(result.has('Unknown')).toBe(false);
    });
  });
});
