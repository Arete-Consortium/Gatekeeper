import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  decodeJWTPayload,
  isTokenExpired,
  userFromToken,
  getStoredToken,
  setStoredToken,
  clearStoredToken,
  getStoredUser,
  setStoredUser,
  getLoginUrl,
} from './auth';

// Helper: create a fake JWT with given payload
function fakeJWT(payload: Record<string, unknown>): string {
  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
  const body = btoa(JSON.stringify(payload));
  return `${header}.${body}.fakesig`;
}

// The global vitest.setup.ts mocks localStorage with vi.fn() stubs.
// We work with those mocks directly.
const mockGetItem = vi.mocked(localStorage.getItem);
const mockSetItem = vi.mocked(localStorage.setItem);
const mockRemoveItem = vi.mocked(localStorage.removeItem);

describe('auth utilities', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('decodeJWTPayload', () => {
    it('decodes a valid JWT payload', () => {
      const token = fakeJWT({ character_id: 123, tier: 'pro' });
      const payload = decodeJWTPayload(token);
      expect(payload).toEqual({ character_id: 123, tier: 'pro' });
    });

    it('returns null for invalid token', () => {
      expect(decodeJWTPayload('not.a.token')).toBeNull();
      expect(decodeJWTPayload('single')).toBeNull();
      expect(decodeJWTPayload('')).toBeNull();
    });
  });

  describe('isTokenExpired', () => {
    it('returns false for a token expiring in the future', () => {
      const token = fakeJWT({ exp: Date.now() / 1000 + 3600 });
      expect(isTokenExpired(token)).toBe(false);
    });

    it('returns true for an expired token', () => {
      const token = fakeJWT({ exp: Date.now() / 1000 - 100 });
      expect(isTokenExpired(token)).toBe(true);
    });

    it('returns true within 60s buffer', () => {
      const token = fakeJWT({ exp: Date.now() / 1000 + 30 });
      expect(isTokenExpired(token)).toBe(true);
    });

    it('returns true for token without exp', () => {
      const token = fakeJWT({ foo: 'bar' });
      expect(isTokenExpired(token)).toBe(true);
    });
  });

  describe('userFromToken', () => {
    it('extracts user from valid token', () => {
      const exp = Math.floor(Date.now() / 1000) + 3600;
      const token = fakeJWT({
        character_id: 456,
        character_name: 'Test Pilot',
        tier: 'pro',
        scopes: ['esi-skills.read_skills.v1'],
        exp,
      });
      const user = userFromToken(token);
      expect(user).not.toBeNull();
      expect(user!.character_id).toBe(456);
      expect(user!.character_name).toBe('Test Pilot');
      expect(user!.subscription_tier).toBe('pro');
      expect(user!.scopes).toEqual(['esi-skills.read_skills.v1']);
    });

    it('defaults tier to free when missing', () => {
      const token = fakeJWT({
        character_id: 789,
        character_name: 'Free Pilot',
        exp: Math.floor(Date.now() / 1000) + 3600,
      });
      const user = userFromToken(token);
      expect(user!.subscription_tier).toBe('free');
    });

    it('returns null for invalid token', () => {
      expect(userFromToken('garbage')).toBeNull();
    });
  });

  describe('localStorage helpers', () => {
    it('setStoredToken calls localStorage.setItem', () => {
      setStoredToken('abc123');
      expect(mockSetItem).toHaveBeenCalledWith('gatekeeper_jwt', 'abc123');
    });

    it('getStoredToken calls localStorage.getItem', () => {
      mockGetItem.mockReturnValueOnce('abc123');
      expect(getStoredToken()).toBe('abc123');
      expect(mockGetItem).toHaveBeenCalledWith('gatekeeper_jwt');
    });

    it('getStoredToken returns null when no token', () => {
      mockGetItem.mockReturnValueOnce(null);
      expect(getStoredToken()).toBeNull();
    });

    it('clearStoredToken removes both keys', () => {
      clearStoredToken();
      expect(mockRemoveItem).toHaveBeenCalledWith('gatekeeper_jwt');
      expect(mockRemoveItem).toHaveBeenCalledWith('gatekeeper_user');
    });

    it('setStoredUser serializes to JSON', () => {
      const user = {
        character_id: 42,
        character_name: 'Space Trucker',
        subscription_tier: 'pro' as const,
        scopes: [],
        expires_at: '2026-01-01T00:00:00Z',
      };
      setStoredUser(user);
      expect(mockSetItem).toHaveBeenCalledWith(
        'gatekeeper_user',
        JSON.stringify(user)
      );
    });

    it('getStoredUser parses stored JSON', () => {
      const user = {
        character_id: 42,
        character_name: 'Space Trucker',
        subscription_tier: 'pro',
        scopes: [],
        expires_at: '2026-01-01T00:00:00Z',
      };
      mockGetItem.mockReturnValueOnce(JSON.stringify(user));
      expect(getStoredUser()).toEqual(user);
    });

    it('getStoredUser returns null for corrupted JSON', () => {
      mockGetItem.mockReturnValueOnce('{invalid json');
      expect(getStoredUser()).toBeNull();
    });

    it('getStoredUser returns null when nothing stored', () => {
      mockGetItem.mockReturnValueOnce(null);
      expect(getStoredUser()).toBeNull();
    });
  });

  describe('getLoginUrl', () => {
    it('uses default API URL when nothing stored', () => {
      mockGetItem.mockReturnValueOnce(null);
      const url = getLoginUrl();
      expect(url).toContain('/api/v1/auth/login');
    });

    it('uses stored API URL', () => {
      mockGetItem.mockReturnValueOnce('https://my-api.example.com');
      const url = getLoginUrl();
      expect(url).toBe('https://my-api.example.com/api/v1/auth/login');
    });
  });
});
