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

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Restore session from localStorage on mount
  useEffect(() => {
    const storedToken = getStoredToken();
    if (storedToken && !isTokenExpired(storedToken)) {
      const storedUser = getStoredUser() || userFromToken(storedToken);
      if (storedUser) {
        setToken(storedToken);
        setUser(storedUser);
      } else {
        clearStoredToken();
      }
    } else if (storedToken) {
      // Expired — clean up
      clearStoredToken();
    }
    setIsLoading(false);
  }, []);

  const login = useCallback((newToken: string) => {
    const newUser = userFromToken(newToken);
    if (!newUser) return;
    setStoredToken(newToken);
    setStoredUser(newUser);
    setToken(newToken);
    setUser(newUser);
  }, []);

  const logout = useCallback(() => {
    clearStoredToken();
    setToken(null);
    setUser(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      token,
      isAuthenticated: !!user,
      isPro: user?.subscription_tier === 'pro',
      isLoading,
      login,
      logout,
    }),
    [user, token, isLoading, login, logout]
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
