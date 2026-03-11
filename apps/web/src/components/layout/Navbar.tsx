'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { cn } from '@/lib/utils';
import { useAuth } from '@/contexts/AuthContext';
import {
  Map,
  Globe,
  Route,
  Scale,
  Bell,
  Radar,
  Settings,
  Menu,
  X,
  LogIn,
  LogOut,
  User,
  Zap,
  CreditCard,
  Triangle,
  Swords,
} from 'lucide-react';
import { useState, useRef, useEffect, useCallback } from 'react';
import { GatekeeperAPI } from '@/lib/api';

interface NavItem {
  href: string;
  label: string;
  icon: React.ElementType;
}

const navItems: NavItem[] = [
  { href: '/', label: 'Map', icon: Globe },
  { href: '/route', label: 'Route', icon: Route },
  { href: '/appraisal', label: 'Appraisal', icon: Scale },
  { href: '/pochven', label: 'Pochven', icon: Triangle },
  { href: '/fw', label: 'FW Map', icon: Swords },
  { href: '/alerts', label: 'Alerts', icon: Bell },
  { href: '/intel', label: 'Intel', icon: Radar },
];

export function Navbar() {
  const pathname = usePathname();
  const router = useRouter();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);
  const { user, isAuthenticated, isPro, logout } = useAuth();

  // Close user dropdown on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setUserMenuOpen(false);
      }
    }
    if (userMenuOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [userMenuOpen]);

  const handleLogout = useCallback(() => {
    logout();
    setUserMenuOpen(false);
    router.replace('/');
  }, [logout, router]);

  const handleManageBilling = useCallback(async () => {
    try {
      const { portal_url } = await GatekeeperAPI.createPortalSession(
        window.location.href
      );
      window.location.href = portal_url;
    } catch {
      // Portal creation failed
    }
    setUserMenuOpen(false);
  }, []);

  const [imgErrors, setImgErrors] = useState<Set<string>>(new Set());
  const handleImgError = useCallback((key: string) => {
    setImgErrors((prev) => new Set(prev).add(key));
  }, []);

  return (
    <nav className="bg-card border-b border-border sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2" aria-label="EVE Gatekeeper home">
            <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
              <Map className="h-5 w-5 text-white" />
            </div>
            <span className="font-bold text-lg text-text hidden sm:block">
              EVE Gatekeeper
            </span>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-1">
            {navItems.map((item) => {
              const isActive = pathname === item.href || (item.href === '/' && pathname === '/map');
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    'flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-primary/20 text-primary'
                      : 'text-text-secondary hover:text-text hover:bg-card-hover'
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </Link>
              );
            })}
          </div>

          {/* Auth section + Mobile menu */}
          <div className="flex items-center gap-2">
            {/* User menu (desktop) */}
            <div className="hidden md:flex items-center gap-2">
              {isAuthenticated ? (
                <div ref={userMenuRef} className="relative">
                  <button
                    onClick={() => setUserMenuOpen(!userMenuOpen)}
                    className={cn(
                      'flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                      userMenuOpen
                        ? 'bg-primary/20 text-primary'
                        : 'text-text-secondary hover:text-text hover:bg-card-hover'
                    )}
                  >
                    {isPro && <Zap className="h-3 w-3 text-primary" />}
                    {user?.character_id && !imgErrors.has('nav') ? (
                      <img
                        src={`https://images.evetech.net/characters/${user.character_id}/portrait?size=32`}
                        alt={user.character_name}
                        className="h-6 w-6 rounded-full"
                        onError={() => handleImgError('nav')}
                      />
                    ) : (
                      <User className="h-4 w-4" />
                    )}
                    <span className="max-w-[120px] truncate">{user?.character_name}</span>
                  </button>
                  {userMenuOpen && (
                    <div className="absolute right-0 mt-1 w-56 bg-card border border-border rounded-lg shadow-lg z-50">
                      {/* Character header */}
                      <div className="px-3 py-3 border-b border-border">
                        <div className="flex items-center gap-3">
                          {user?.character_id && !imgErrors.has('dropdown') ? (
                            <img
                              src={`https://images.evetech.net/characters/${user.character_id}/portrait?size=64`}
                              alt={user.character_name}
                              className="h-10 w-10 rounded-full"
                              onError={() => handleImgError('dropdown')}
                            />
                          ) : (
                            <div className="h-10 w-10 rounded-full bg-primary/20 flex items-center justify-center">
                              <User className="h-5 w-5 text-primary" />
                            </div>
                          )}
                          <div className="min-w-0">
                            <div className="text-sm font-medium text-text truncate">
                              {user?.character_name}
                            </div>
                            <span
                              className={cn(
                                'inline-flex items-center gap-1 text-xs font-medium',
                                isPro ? 'text-primary' : 'text-text-secondary'
                              )}
                            >
                              {isPro && <Zap className="h-3 w-3" />}
                              {isPro ? 'Pro' : 'Free'}
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Menu links */}
                      <div className="py-1">
                        {isPro ? (
                          <button
                            onClick={handleManageBilling}
                            className="flex items-center gap-2 px-3 py-2 text-sm text-text-secondary hover:text-text hover:bg-card-hover w-full text-left transition-colors"
                          >
                            <CreditCard className="h-4 w-4" />
                            Manage Billing
                          </button>
                        ) : (
                          <Link
                            href="/pricing"
                            onClick={() => setUserMenuOpen(false)}
                            className="flex items-center gap-2 px-3 py-2 text-sm text-primary hover:bg-primary/10 transition-colors"
                          >
                            <Zap className="h-4 w-4" />
                            Upgrade to Pro
                          </Link>
                        )}
                        <Link
                          href="/settings"
                          onClick={() => setUserMenuOpen(false)}
                          className={cn(
                            'flex items-center gap-2 px-3 py-2 text-sm transition-colors',
                            pathname === '/settings'
                              ? 'text-primary bg-primary/10'
                              : 'text-text-secondary hover:text-text hover:bg-card-hover'
                          )}
                        >
                          <Settings className="h-4 w-4" />
                          Settings
                        </Link>
                      </div>

                      {/* Logout */}
                      <div className="border-t border-border py-1">
                        <button
                          onClick={handleLogout}
                          className="flex items-center gap-2 px-3 py-2 text-sm text-text-secondary hover:text-red-400 hover:bg-card-hover w-full text-left transition-colors"
                        >
                          <LogOut className="h-4 w-4" />
                          Log Out
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <Link
                  href="/login"
                  className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-primary hover:bg-primary/10 transition-colors"
                >
                  <LogIn className="h-4 w-4" />
                  Log in
                </Link>
              )}
            </div>

            {/* Mobile menu button */}
            <button
              className="md:hidden p-2 text-text-secondary hover:text-text"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              aria-label={mobileMenuOpen ? 'Close navigation menu' : 'Open navigation menu'}
            >
              {mobileMenuOpen ? (
                <X className="h-6 w-6" />
              ) : (
                <Menu className="h-6 w-6" />
              )}
            </button>
          </div>
        </div>

        {/* Mobile Navigation */}
        {mobileMenuOpen && (
          <div className="md:hidden py-4 border-t border-border">
            <div className="flex flex-col gap-1">
              {navItems.map((item) => {
                const isActive = pathname === item.href || (item.href === '/' && pathname === '/map');
                const Icon = item.icon;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setMobileMenuOpen(false)}
                    className={cn(
                      'flex items-center gap-3 px-3 py-3 rounded-lg text-sm font-medium transition-colors',
                      isActive
                        ? 'bg-primary/20 text-primary'
                        : 'text-text-secondary hover:text-text hover:bg-card-hover'
                    )}
                  >
                    <Icon className="h-5 w-5" />
                    {item.label}
                  </Link>
                );
              })}
              {/* Mobile user section */}
              <div className="border-t border-border mt-2 pt-2">
                {isAuthenticated ? (
                  <>
                    {/* Character info */}
                    <div className="flex items-center gap-3 px-3 py-3">
                      {user?.character_id && !imgErrors.has('mobile') ? (
                        <img
                          src={`https://images.evetech.net/characters/${user.character_id}/portrait?size=64`}
                          alt={user.character_name}
                          className="h-8 w-8 rounded-full"
                          onError={() => handleImgError('mobile')}
                        />
                      ) : (
                        <User className="h-5 w-5 text-text-secondary" />
                      )}
                      <div>
                        <div className="text-sm font-medium text-text">{user?.character_name}</div>
                        <span className={cn(
                          'text-xs',
                          isPro ? 'text-primary' : 'text-text-secondary'
                        )}>
                          {isPro && <Zap className="h-3 w-3 inline mr-0.5" />}
                          {isPro ? 'Pro' : 'Free'}
                        </span>
                      </div>
                    </div>
                    {isPro ? (
                      <button
                        onClick={() => { handleManageBilling(); setMobileMenuOpen(false); }}
                        className="flex items-center gap-3 px-3 py-3 rounded-lg text-sm font-medium text-text-secondary hover:text-text hover:bg-card-hover w-full text-left"
                      >
                        <CreditCard className="h-5 w-5" />
                        Manage Billing
                      </button>
                    ) : (
                      <Link
                        href="/pricing"
                        onClick={() => setMobileMenuOpen(false)}
                        className="flex items-center gap-3 px-3 py-3 rounded-lg text-sm font-medium text-primary hover:bg-primary/10"
                      >
                        <Zap className="h-5 w-5" />
                        Upgrade to Pro
                      </Link>
                    )}
                    <Link
                      href="/settings"
                      onClick={() => setMobileMenuOpen(false)}
                      className={cn(
                        'flex items-center gap-3 px-3 py-3 rounded-lg text-sm font-medium transition-colors',
                        pathname === '/settings'
                          ? 'bg-primary/20 text-primary'
                          : 'text-text-secondary hover:text-text hover:bg-card-hover'
                      )}
                    >
                      <Settings className="h-5 w-5" />
                      Settings
                    </Link>
                    <button
                      onClick={() => { handleLogout(); setMobileMenuOpen(false); }}
                      className="flex items-center gap-3 px-3 py-3 rounded-lg text-sm font-medium text-text-secondary hover:text-red-400 hover:bg-card-hover w-full text-left"
                    >
                      <LogOut className="h-5 w-5" />
                      Log Out
                    </button>
                  </>
                ) : (
                  <>
                    <Link
                      href="/settings"
                      onClick={() => setMobileMenuOpen(false)}
                      className={cn(
                        'flex items-center gap-3 px-3 py-3 rounded-lg text-sm font-medium transition-colors',
                        pathname === '/settings'
                          ? 'bg-primary/20 text-primary'
                          : 'text-text-secondary hover:text-text hover:bg-card-hover'
                      )}
                    >
                      <Settings className="h-5 w-5" />
                      Settings
                    </Link>
                    <Link
                      href="/pricing"
                      onClick={() => setMobileMenuOpen(false)}
                      className={cn(
                        'flex items-center gap-3 px-3 py-3 rounded-lg text-sm font-medium transition-colors',
                        pathname === '/pricing'
                          ? 'bg-primary/20 text-primary'
                          : 'text-text-secondary hover:text-text hover:bg-card-hover'
                      )}
                    >
                      <Zap className="h-5 w-5" />
                      Pricing
                    </Link>
                    <Link
                      href="/login"
                      onClick={() => setMobileMenuOpen(false)}
                      className="flex items-center gap-3 px-3 py-3 rounded-lg text-sm font-medium text-primary hover:bg-primary/10"
                    >
                      <LogIn className="h-5 w-5" />
                      Log in
                    </Link>
                  </>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </nav>
  );
}
