'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { cn } from '@/lib/utils';
import {
  Map,
  Globe,
  Route,
  Wrench,
  Bell,
  Radar,
  Settings,
  CreditCard,
  Menu,
  X,
} from 'lucide-react';
import { useState } from 'react';
import { LanguageSwitcher } from './LanguageSwitcher';

interface NavItem {
  href: string;
  labelKey: string;
  icon: React.ElementType;
}

const navItems: NavItem[] = [
  { href: '/', labelKey: 'dashboard', icon: Map },
  { href: '/map', labelKey: 'map', icon: Globe },
  { href: '/route', labelKey: 'route', icon: Route },
  { href: '/fitting', labelKey: 'fitting', icon: Wrench },
  { href: '/alerts', labelKey: 'alerts', icon: Bell },
  { href: '/intel', labelKey: 'intel', icon: Radar },
  { href: '/pricing', labelKey: 'pro', icon: CreditCard },
  { href: '/settings', labelKey: 'settings', icon: Settings },
];

export function Navbar() {
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const t = useTranslations('nav');

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
                  {t(item.labelKey)}
                </Link>
              );
            })}
            <div className="ml-2 border-l border-border pl-2">
              <LanguageSwitcher />
            </div>
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
                    {t(item.labelKey)}
                  </Link>
                );
              })}
              <div className="px-3 py-3">
                <LanguageSwitcher />
              </div>
            </div>
          </div>
        )}
      </div>
    </nav>
  );
}
