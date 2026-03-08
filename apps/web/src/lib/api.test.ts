import { describe, it, expect, vi, beforeEach, afterEach, Mock } from 'vitest';
import { GatekeeperAPI } from './api';

describe('GatekeeperAPI', () => {
  const mockFetch = global.fetch as Mock;

  beforeEach(() => {
    vi.clearAllMocks();
    // Reset localStorage mock
    (window.localStorage.getItem as Mock).mockReturnValue(null);
  });

  afterEach(() => {
    vi.clearAllTimers();
  });

  const mockSuccessResponse = (data: unknown) => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(data),
    });
  };

  const mockErrorResponse = (status: number, statusText: string) => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status,
      statusText,
    });
  };

  describe('getHealth', () => {
    it('returns health status on success', async () => {
      mockSuccessResponse({ status: 'healthy' });

      const result = await GatekeeperAPI.getHealth();

      expect(result).toEqual({ status: 'healthy' });
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/health'),
        expect.any(Object)
      );
    });

    it('throws error on API failure', async () => {
      mockErrorResponse(500, 'Internal Server Error');

      await expect(GatekeeperAPI.getHealth()).rejects.toThrow(
        'API Error: 500 Internal Server Error'
      );
    });
  });

  describe('getRoute', () => {
    it('builds correct query params for basic route', async () => {
      mockSuccessResponse({
        path: [],
        total_jumps: 5,
        total_distance: 100,
        total_cost: 50,
        max_risk: 0.5,
        avg_risk: 0.3,
        profile: 'safer',
        bridges_used: 0,
        thera_used: 0,
      });

      await GatekeeperAPI.getRoute('Jita', 'Amarr', 'safer');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/map/route?from=Jita&to=Amarr&profile=safer'),
        expect.any(Object)
      );
    });

    it('includes bridge option when enabled', async () => {
      mockSuccessResponse({
        path: [],
        total_jumps: 3,
        total_distance: 80,
        total_cost: 30,
        max_risk: 0.2,
        avg_risk: 0.1,
        profile: 'safer',
        bridges_used: 1,
        thera_used: 0,
      });

      await GatekeeperAPI.getRoute('Jita', 'Amarr', 'safer', { bridges: true });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('bridges=true'),
        expect.any(Object)
      );
    });

    it('includes thera option when enabled', async () => {
      mockSuccessResponse({
        path: [],
        total_jumps: 2,
        total_distance: 50,
        total_cost: 20,
        max_risk: 0.4,
        avg_risk: 0.3,
        profile: 'safer',
        bridges_used: 0,
        thera_used: 1,
      });

      await GatekeeperAPI.getRoute('Jita', 'Amarr', 'safer', { thera: true });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('thera=true'),
        expect.any(Object)
      );
    });

    it('uses different routing profiles', async () => {
      mockSuccessResponse({ path: [], total_jumps: 10 });

      await GatekeeperAPI.getRoute('Jita', 'Amarr', 'shortest');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('profile=shortest'),
        expect.any(Object)
      );
    });
  });

  describe('getSystemRisk', () => {
    it('fetches risk for a system', async () => {
      mockSuccessResponse({
        system_name: 'Jita',
        system_id: 30000142,
        category: 'highsec',
        security: 0.95,
        score: 11.0,
        breakdown: {
          security_component: 1.0,
          kills_component: 10.0,
          pods_component: 0.0,
        },
        zkill_stats: {
          recent_kills: 200,
          recent_pods: 0,
        },
        danger_level: null,
        ship_profile: null,
      });

      const result = await GatekeeperAPI.getSystemRisk('Jita');

      expect(result.system_name).toBe('Jita');
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/systems/Jita/risk'),
        expect.any(Object)
      );
    });

    it('includes ship profile when provided', async () => {
      mockSuccessResponse({
        system_name: 'Jita',
        system_id: 30000142,
        category: 'highsec',
        security: 0.95,
        score: 5.0,
        breakdown: { security_component: 1.0, kills_component: 4.0, pods_component: 0.0 },
        zkill_stats: { recent_kills: 50, recent_pods: 0 },
        danger_level: null,
        ship_profile: 'hauler',
      });

      await GatekeeperAPI.getSystemRisk('Jita', 'hauler');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('ship_profile=hauler'),
        expect.any(Object)
      );
    });

    it('URL encodes system names', async () => {
      mockSuccessResponse({
        system_name: 'J123456',
        system_id: 31000001,
        category: 'wormhole',
        security: -1.0,
        score: 8.0,
        breakdown: { security_component: 0.0, kills_component: 5.0, pods_component: 3.0 },
        zkill_stats: { recent_kills: 10, recent_pods: 5 },
        danger_level: null,
        ship_profile: null,
      });

      await GatekeeperAPI.getSystemRisk('J123456');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/systems/J123456/risk'),
        expect.any(Object)
      );
    });
  });

  describe('getHotSystems', () => {
    it('fetches hot systems with default params', async () => {
      mockSuccessResponse({
        systems: [
          { system_id: 1, system_name: 'Tama', recent_kills: 100 },
          { system_id: 2, system_name: 'Amamake', recent_kills: 80 },
        ],
      });

      const result = await GatekeeperAPI.getHotSystems();

      expect(result).toHaveLength(2);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/stats/hot?hours=24&limit=10'),
        expect.any(Object)
      );
    });

    it('uses custom hours and limit', async () => {
      mockSuccessResponse({ systems: [] });

      await GatekeeperAPI.getHotSystems(48, 20);

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('hours=48&limit=20'),
        expect.any(Object)
      );
    });
  });

  describe('analyzeFitting', () => {
    it('sends EFT text for analysis', async () => {
      const eftText = '[Heron, Explorer]\nCore Probe Launcher I';
      mockSuccessResponse({
        fitting: {
          ship_name: 'Heron',
          ship_category: 'frigate',
          modules: ['Core Probe Launcher I'],
        },
        travel: {
          ship_name: 'Heron',
          recommended_profile: 'paranoid',
          warnings: ['Paper thin tank'],
        },
      });

      const result = await GatekeeperAPI.analyzeFitting(eftText);

      expect(result.fitting.ship_name).toBe('Heron');
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/fitting/analyze'),
        expect.objectContaining({
          method: 'POST',
          body: expect.stringContaining('Heron'),
        })
      );
    });
  });

  describe('testConnection', () => {
    it('returns true on successful health check', async () => {
      mockSuccessResponse({ status: 'healthy' });

      const result = await GatekeeperAPI.testConnection();

      expect(result).toBe(true);
    });

    it('returns false on failed health check', async () => {
      mockErrorResponse(500, 'Internal Server Error');

      const result = await GatekeeperAPI.testConnection();

      expect(result).toBe(false);
    });
  });

  describe('402 redirect', () => {
    it('redirects to /pricing on 402 response', async () => {
      const originalLocation = window.location.href;
      // Mock window.location.href setter
      const locationSpy = vi.spyOn(window, 'location', 'get').mockReturnValue({
        ...window.location,
        href: originalLocation,
      } as Location);

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 402,
        statusText: 'Payment Required',
      });

      await expect(GatekeeperAPI.getHealth()).rejects.toThrow(
        'Pro subscription required'
      );

      locationSpy.mockRestore();
    });
  });

  describe('getSubscriptionStatus', () => {
    it('fetches billing status', async () => {
      mockSuccessResponse({
        tier: 'pro',
        status: 'active',
        character_id: 12345,
        character_name: 'Test Pilot',
        subscription_id: 'sub_abc',
        current_period_end: '2026-04-01T00:00:00Z',
        cancel_at_period_end: false,
      });

      const result = await GatekeeperAPI.getSubscriptionStatus();

      expect(result.tier).toBe('pro');
      expect(result.status).toBe('active');
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/billing/status'),
        expect.any(Object)
      );
    });
  });

  describe('createCheckoutSession', () => {
    it('sends correct URLs for checkout', async () => {
      mockSuccessResponse({ checkout_url: 'https://checkout.stripe.com/abc' });

      const result = await GatekeeperAPI.createCheckoutSession(
        'https://example.com/account?checkout=success',
        'https://example.com/pricing?checkout=cancelled'
      );

      expect(result.checkout_url).toBe('https://checkout.stripe.com/abc');
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/billing/create-checkout'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            success_url: 'https://example.com/account?checkout=success',
            cancel_url: 'https://example.com/pricing?checkout=cancelled',
          }),
        })
      );
    });
  });

  describe('createPortalSession', () => {
    it('sends correct return URL', async () => {
      mockSuccessResponse({ portal_url: 'https://billing.stripe.com/xyz' });

      const result = await GatekeeperAPI.createPortalSession(
        'https://example.com/account'
      );

      expect(result.portal_url).toBe('https://billing.stripe.com/xyz');
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/billing/create-portal'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            return_url: 'https://example.com/account',
          }),
        })
      );
    });
  });

  describe('setBaseUrl', () => {
    it('updates base URL and stores in localStorage', () => {
      const newUrl = 'http://custom-api.example.com';

      GatekeeperAPI.setBaseUrl(newUrl);

      expect(GatekeeperAPI.getBaseUrl()).toBe(newUrl);
      expect(window.localStorage.setItem).toHaveBeenCalledWith(
        'gatekeeper_api_url',
        newUrl
      );
    });
  });

  describe('createAlertSubscription', () => {
    it('creates subscription with correct payload', async () => {
      const subscriptionData = {
        webhook_url: 'https://discord.com/webhook/123',
        webhook_type: 'discord' as const,
        name: 'Test Alert',
        systems: ['Jita', 'Amarr'],
        min_value: 100000000,
      };

      mockSuccessResponse({
        id: 'sub-123',
        ...subscriptionData,
        enabled: true,
        created_at: '2024-01-15T12:00:00Z',
      });

      const result = await GatekeeperAPI.createAlertSubscription(subscriptionData);

      expect(result.id).toBe('sub-123');
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/alerts/subscriptions'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(subscriptionData),
        })
      );
    });
  });

  describe('deleteAlertSubscription', () => {
    it('sends DELETE request for subscription', async () => {
      mockSuccessResponse(undefined);

      await GatekeeperAPI.deleteAlertSubscription('sub-123');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/alerts/subscriptions/sub-123'),
        expect.objectContaining({
          method: 'DELETE',
        })
      );
    });
  });
});
