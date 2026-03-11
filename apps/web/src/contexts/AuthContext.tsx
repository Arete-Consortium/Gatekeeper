'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import type { AuthUser } from '@/lib/auth';
import {
  getStoredToken,
  getStoredUser,
  setStoredToken,
  setStoredUser,
  clearStoredToken,
  userFromToken,
  isTokenExpired,
  fetchSession,
} from '@/lib/auth';

interface AuthContextValue {
  user: AuthUser | null;
  token: string | null;
  isAuthenticated: boolean;
  isPro: boolean;
  isLoading: boolean;
  login: (token?: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function restoreSession(): { token: string | null; user: AuthUser | null } {
  if (typeof window === 'undefined') return { token: null, user: null };
  const storedToken = getStoredToken();
  if (storedToken && !isTokenExpired(storedToken)) {
    const storedUser = getStoredUser() || userFromToken(storedToken);
    if (storedUser) {
      return { token: storedToken, user: storedUser };
    }
    clearStoredToken();
  } else if (storedToken) {
    clearStoredToken();
  }
  return { token: null, user: null };
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState(() => restoreSession());
  const [isLoading, setIsLoading] = useState(true);

  // On mount, try cookie-based session first, fall back to localStorage
  useEffect(() => {
    let cancelled = false;
    fetchSession()
      .then((cookieUser) => {
        if (cancelled) return;
        if (cookieUser) {
          setSession({ token: null, user: cookieUser });
        }
        // If no cookie session but localStorage has a token, keep it (already restored)
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  const login = useCallback((newToken?: string) => {
    if (newToken) {
      // Legacy: token provided in body (backwards compat)
      const newUser = userFromToken(newToken);
      if (!newUser) return;
      setStoredToken(newToken);
      setStoredUser(newUser);
      setSession({ token: newToken, user: newUser });
    } else {
      // Cookie-based: fetch session from server
      fetchSession().then((cookieUser) => {
        if (cookieUser) {
          setSession({ token: null, user: cookieUser });
        }
      });
    }
  }, []);

  const logout = useCallback(() => {
    const apiUrl =
      (typeof window !== 'undefined' ? localStorage.getItem('gatekeeper_api_url') : null) ||
      process.env.NEXT_PUBLIC_API_URL ||
      'http://localhost:8000';
    // Call backend to clear cookie + revoke
    fetch(`${apiUrl}/api/v1/auth/logout`, {
      method: 'POST',
      credentials: 'include',
    }).catch(() => { /* best effort */ });
    clearStoredToken();
    setSession({ token: null, user: null });
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user: session.user,
      token: session.token,
      isAuthenticated: !!session.user,
      isPro: session.user?.subscription_tier === 'pro',
      isLoading,
      login,
      logout,
    }),
    [session, isLoading, login, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
}
