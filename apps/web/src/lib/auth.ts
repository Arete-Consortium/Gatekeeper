/**
 * Auth types and utilities for EVE Gatekeeper
 */

export interface AuthUser {
  character_id: number;
  character_name: string;
  subscription_tier: 'free' | 'pro';
  scopes: string[];
  expires_at: string;
}

export interface JWTTokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  character_id: number;
  character_name: string;
}

export interface BillingStatus {
  tier: string;
  status: string;
  character_id: number | null;
  character_name: string | null;
  subscription_id: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean | null;
}

const TOKEN_KEY = 'gatekeeper_jwt';
const USER_KEY = 'gatekeeper_user';

export function getStoredToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearStoredToken(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function getStoredUser(): AuthUser | null {
  if (typeof window === 'undefined') return null;
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

export function setStoredUser(user: AuthUser): void {
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

/**
 * Decode JWT payload without verification (client-side only).
 * We trust the server — this is just for reading claims.
 */
export function decodeJWTPayload(token: string): Record<string, unknown> | null {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    const payload = JSON.parse(atob(parts[1]));
    return payload;
  } catch {
    return null;
  }
}

/**
 * Check if a JWT token is expired (with 60s buffer).
 */
export function isTokenExpired(token: string): boolean {
  const payload = decodeJWTPayload(token);
  if (!payload || typeof payload.exp !== 'number') return true;
  return Date.now() / 1000 > payload.exp - 60;
}

/**
 * Extract AuthUser from a JWT token.
 */
export function userFromToken(token: string): AuthUser | null {
  const payload = decodeJWTPayload(token);
  if (!payload) return null;
  return {
    character_id: (payload.sub ?? payload.character_id) as number,
    character_name: (payload.name ?? payload.character_name) as string,
    subscription_tier: (payload.tier as 'free' | 'pro') || 'free',
    scopes: (payload.scopes as string[]) || [],
    expires_at: new Date((payload.exp as number) * 1000).toISOString(),
  };
}

/**
 * Fetch session info from the httpOnly cookie via /auth/session.
 * Returns null if no valid session exists.
 */
export async function fetchSession(): Promise<AuthUser | null> {
  if (typeof window === 'undefined') return null;
  const apiUrl =
    localStorage.getItem('gatekeeper_api_url') ||
    process.env.NEXT_PUBLIC_API_URL ||
    'http://localhost:8000';
  try {
    const res = await fetch(`${apiUrl}/api/v1/auth/session`, {
      credentials: 'include',
    });
    if (!res.ok) return null;
    const data = await res.json();
    return {
      character_id: data.character_id,
      character_name: data.character_name,
      subscription_tier: data.subscription_tier,
      scopes: data.scopes,
      expires_at: data.expires_at,
    };
  } catch {
    return null;
  }
}

/**
 * Build the ESI OAuth login URL.
 */
export function getLoginUrl(): string {
  const apiUrl = localStorage.getItem('gatekeeper_api_url') || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const origin = encodeURIComponent(window.location.origin);
  return `${apiUrl}/api/v1/auth/login/redirect?frontend_origin=${origin}`;
}
