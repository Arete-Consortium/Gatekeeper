'use client';

import { useEffect } from 'react';
import { getLoginUrl } from '@/lib/auth';
import { Card, Button } from '@/components/ui';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import { LogIn } from 'lucide-react';

export default function LoginPage() {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.replace('/');
    }
  }, [isAuthenticated, isLoading, router]);

  const handleLogin = () => {
    window.location.href = getLoginUrl();
  };

  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <Card className="max-w-md w-full text-center py-12 px-8">
        <div className="flex justify-center mb-6">
          <div className="w-16 h-16 bg-primary rounded-2xl flex items-center justify-center">
            <LogIn className="h-8 w-8 text-white" />
          </div>
        </div>
        <h1 className="text-2xl font-bold text-text mb-2">
          Sign in to EVE Gatekeeper
        </h1>
        <p className="text-text-secondary mb-8">
          Log in with your EVE Online account via SSO to unlock saved routes,
          alerts, and Pro features.
        </p>
        <Button size="lg" className="glow-primary w-full" onClick={handleLogin}>
          <LogIn className="mr-2 h-5 w-5" />
          Log in with EVE Online
        </Button>
        <p className="text-xs text-text-secondary mt-4">
          Uses CCP&apos;s official EVE SSO. We never see your password.
        </p>
      </Card>
    </div>
  );
}
