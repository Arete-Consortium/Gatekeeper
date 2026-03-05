'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import { useAuth } from '@/contexts/AuthContext';
import {
  Map,
  Globe,
  Route,
  Wrench,
  Bell,
  Radar,
  Settings,
  Menu,
  X,
  LogIn,
  User,
  Zap,
} from 'lucide-react';
import { useState } from 'react';

interface NavItem {
  href: string;
  label: string;
  icon: React.ElementType;
}

const navItems: NavItem[] = [
  { href: '/', label: 'Dashboard', icon: Map },
  { href: '/map', label: 'Map', icon: Globe },
  { href: '/route', label: 'Route', icon: Route },
  { href: '/fitting', label: 'Fitting', icon: Wrench },
  { href: '/alerts', label: 'Alerts', icon: Bell },
  { href: '/intel', label: 'Intel', icon: Radar },
  { href: '/settings', label: 'Settings', icon: Settings },
];

export function Navbar() {
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { user, isAuthenticated, isPro } = useAuth();

  return (
    <nav className="bg-card border-b border-border sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2">
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
              const isActive = pathname === item.href;
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
            {/* Auth button (desktop) */}
            <div className="hidden md:flex items-center gap-2">
              {isAuthenticated ? (
                <Link
                  href="/account"
                  className={cn(
                    'flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                    pathname === '/account'
                      ? 'bg-primary/20 text-primary'
                      : 'text-text-secondary hover:text-text hover:bg-card-hover'
                  )}
                >
                  {isPro && <Zap className="h-3 w-3 text-primary" />}
                  <User className="h-4 w-4" />
                  <span className="max-w-[120px] truncate">{user?.character_name}</span>
                </Link>
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
                const isActive = pathname === item.href;
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
              {/* Mobile auth link */}
              {isAuthenticated ? (
                <Link
                  href="/account"
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex items-center gap-3 px-3 py-3 rounded-lg text-sm font-medium text-text-secondary hover:text-text hover:bg-card-hover border-t border-border mt-2 pt-4"
                >
                  <User className="h-5 w-5" />
                  {user?.character_name}
                  {isPro && <Zap className="h-3 w-3 text-primary ml-auto" />}
                </Link>
              ) : (
                <Link
                  href="/login"
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex items-center gap-3 px-3 py-3 rounded-lg text-sm font-medium text-primary hover:bg-primary/10 border-t border-border mt-2 pt-4"
                >
                  <LogIn className="h-5 w-5" />
                  Log in
                </Link>
              )}
            </div>
          </div>
        )}
      </div>
    </nav>
  );
}
