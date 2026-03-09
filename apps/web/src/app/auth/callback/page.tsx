'use client';

import { Suspense, useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { Card } from '@/components/ui';

export default function AuthCallbackPage() {
  return (
    <Suspense fallback={<div className="text-center py-8 text-text-secondary">Authenticating...</div>}>
      <AuthCallbackContent />
    </Suspense>
  );
}

/**
 * OAuth callback handler.
 *
 * After ESI SSO redirects here, we exchange the state for a JWT by calling
 * the backend's /api/v1/auth/jwt endpoint, then store it and redirect home.
 */
function AuthCallbackContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { login } = useAuth();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function handleCallback() {
      const characterId = searchParams.get('character_id');
      if (!characterId) {
        setError('Missing character_id from OAuth callback.');
        return;
      }

      const apiUrl =
        localStorage.getItem('gatekeeper_api_url') ||
        process.env.NEXT_PUBLIC_API_URL ||
        'http://localhost:8000';

      try {
        const response = await fetch(
          `${apiUrl}/api/v1/auth/token?character_id=${encodeURIComponent(characterId)}`,
          { method: 'POST' }
        );
        if (!response.ok) {
          const body = await response.json().catch(() => ({}));
          throw new Error(body.detail || `Auth failed: ${response.status}`);
        }
        const data = await response.json();
        login(data.access_token);
        router.replace('/');
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Authentication failed');
      }
    }

    handleCallback();
  }, [searchParams, login, router]);

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Card className="max-w-md w-full text-center py-8 px-8">
          <h1 className="text-xl font-bold text-risk-red mb-2">Login Failed</h1>
          <p className="text-text-secondary mb-4">{error}</p>
          <a href="/login" className="text-primary hover:underline">
            Try again
          </a>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <Card className="max-w-md w-full text-center py-8">
        <div className="animate-pulse">
          <p className="text-text-secondary">Authenticating...</p>
        </div>
      </Card>
    </div>
  );
}
