'use client';

import { Suspense, useEffect, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter, useSearchParams } from 'next/navigation';
import { Card, CardTitle, CardDescription, Button } from '@/components/ui';
import type { BillingStatus } from '@/lib/auth';
import { User, Zap, CreditCard, LogOut } from 'lucide-react';
import Link from 'next/link';

export default function AccountPage() {
  return (
    <Suspense fallback={<div className="text-center py-8 text-text-secondary">Loading...</div>}>
      <AccountContent />
    </Suspense>
  );
}

function AccountContent() {
  const { user, token, isAuthenticated, isLoading, isPro, logout } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [billing, setBilling] = useState<BillingStatus | null>(null);
  const [billingLoading, setBillingLoading] = useState(false);
  const checkoutStatus = searchParams.get('checkout');

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace('/login');
    }
  }, [isAuthenticated, isLoading, router]);

  useEffect(() => {
    async function fetchBilling() {
      if (!token) return;
      setBillingLoading(true);
      const apiUrl =
        localStorage.getItem('gatekeeper_api_url') ||
        process.env.NEXT_PUBLIC_API_URL ||
        'http://localhost:8000';

      try {
        const response = await fetch(`${apiUrl}/api/v1/billing/status`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (response.ok) {
          setBilling(await response.json());
        }
      } catch {
        // Billing might not be configured — that's ok
      } finally {
        setBillingLoading(false);
      }
    }
    fetchBilling();
  }, [token]);

  const handleManageBilling = async () => {
    if (!token) return;
    const apiUrl =
      localStorage.getItem('gatekeeper_api_url') ||
      process.env.NEXT_PUBLIC_API_URL ||
      'http://localhost:8000';

    const response = await fetch(`${apiUrl}/api/v1/billing/create-portal`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        return_url: `${window.location.origin}/account`,
      }),
    });

    if (response.ok) {
      const data = await response.json();
      window.location.href = data.portal_url;
    }
  };

  const handleLogout = () => {
    logout();
    router.replace('/');
  };

  if (isLoading || !user) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Card className="max-w-md w-full text-center py-8">
          <div className="animate-pulse">
            <p className="text-text-secondary">Loading...</p>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Checkout success banner */}
      {checkoutStatus === 'success' && (
        <Card className="border-risk-green/40 bg-risk-green/10 text-center py-4">
          <p className="text-risk-green font-medium">
            Welcome to Pro! Your subscription is now active.
          </p>
        </Card>
      )}

      <h1 className="text-2xl font-bold text-text">Account</h1>

      {/* Character Info */}
      <Card className="p-6">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-primary/20 rounded-full">
            <User className="h-6 w-6 text-primary" />
          </div>
          <div>
            <CardTitle className="text-lg">{user.character_name}</CardTitle>
            <CardDescription>
              Character ID: {user.character_id}
            </CardDescription>
          </div>
          <div className="ml-auto">
            <span
              className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-bold ${
                isPro
                  ? 'bg-primary/20 text-primary'
                  : 'bg-card-hover text-text-secondary'
              }`}
            >
              {isPro && <Zap className="h-3 w-3" />}
              {isPro ? 'Pro' : 'Free'}
            </span>
          </div>
        </div>
      </Card>

      {/* Subscription */}
      <Card className="p-6">
        <CardTitle className="text-base mb-4 flex items-center gap-2">
          <CreditCard className="h-4 w-4" />
          Subscription
        </CardTitle>

        {billingLoading ? (
          <p className="text-text-secondary animate-pulse">Loading billing info...</p>
        ) : billing ? (
          <div className="space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-text-secondary">Plan</span>
              <span className="text-text font-medium capitalize">{billing.tier}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-text-secondary">Status</span>
              <span className="text-text font-medium">{billing.status}</span>
            </div>
            {billing.current_period_end && (
              <div className="flex justify-between text-sm">
                <span className="text-text-secondary">
                  {billing.cancel_at_period_end ? 'Access until' : 'Next billing'}
                </span>
                <span className="text-text font-medium">
                  {new Date(billing.current_period_end).toLocaleDateString()}
                </span>
              </div>
            )}
            {billing.cancel_at_period_end && (
              <p className="text-xs text-risk-orange mt-2">
                Your subscription will not renew. You keep Pro access until the end of the billing period.
              </p>
            )}

            <div className="pt-4 flex gap-3">
              {isPro ? (
                <Button variant="secondary" onClick={handleManageBilling}>
                  Manage Billing
                </Button>
              ) : (
                <Link href="/pricing">
                  <Button className="glow-primary">
                    <Zap className="mr-2 h-4 w-4" />
                    Upgrade to Pro
                  </Button>
                </Link>
              )}
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <p className="text-text-secondary text-sm">
              You&apos;re on the free plan.
            </p>
            <Link href="/pricing">
              <Button className="glow-primary">
                <Zap className="mr-2 h-4 w-4" />
                Upgrade to Pro
              </Button>
            </Link>
          </div>
        )}
      </Card>

      {/* Logout */}
      <Card className="p-6">
        <Button variant="secondary" onClick={handleLogout}>
          <LogOut className="mr-2 h-4 w-4" />
          Log Out
        </Button>
      </Card>
    </div>
  );
}
