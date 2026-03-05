'use client';

import Link from 'next/link';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardTitle, CardDescription, Button } from '@/components/ui';
import { Lock } from 'lucide-react';

interface ProGateProps {
  children: React.ReactNode;
  feature?: string;
}

/**
 * Wraps content that requires a Pro subscription.
 * Shows an upgrade CTA if the user is on the free tier.
 */
export function ProGate({ children, feature }: ProGateProps) {
  const { isPro, isAuthenticated } = useAuth();

  if (isPro) {
    return <>{children}</>;
  }

  return (
    <Card className="text-center py-8 border-primary/30">
      <div className="flex justify-center mb-4">
        <div className="p-3 bg-primary/20 rounded-full">
          <Lock className="h-6 w-6 text-primary" />
        </div>
      </div>
      <CardTitle className="text-lg mb-2">
        {feature ? `${feature} requires Pro` : 'Pro Feature'}
      </CardTitle>
      <CardDescription className="mb-6 max-w-md mx-auto">
        Upgrade to EVE Gatekeeper Pro for AI route analysis, webhook alerts,
        advanced stats, and higher rate limits.
      </CardDescription>
      <Link href={isAuthenticated ? '/pricing' : '/pricing'}>
        <Button className="glow-primary">
          Upgrade to Pro
        </Button>
      </Link>
    </Card>
  );
}
