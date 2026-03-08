'use client';

import {
  createContext,
  useCallback,
  useContext,
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
} from '@/lib/auth';

interface AuthContextValue {
  user: AuthUser | null;
  token: string | null;
  isAuthenticated: boolean;
  isPro: boolean;
  isLoading: boolean;
  login: (token: string) => void;
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
  const isLoading = false;

  const login = useCallback((newToken: string) => {
    const newUser = userFromToken(newToken);
    if (!newUser) return;
    setStoredToken(newToken);
    setStoredUser(newUser);
    setSession({ token: newToken, user: newUser });
  }, []);

  const logout = useCallback(() => {
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
