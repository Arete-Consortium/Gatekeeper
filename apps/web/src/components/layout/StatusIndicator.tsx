'use client';

import { useEffect, useState } from 'react';
import { cn } from '@/lib/utils';
import { GatekeeperAPI } from '@/lib/api';
import { Loader2 } from 'lucide-react';

type ApiStatus = 'checking' | 'online' | 'offline';

export function StatusIndicator() {
  const [status, setStatus] = useState<ApiStatus>('checking');

  useEffect(() => {
    let cancelled = false;

    const checkStatus = async () => {
      const isOnline = await GatekeeperAPI.testConnection();
      if (!cancelled) {
        setStatus(isOnline ? 'online' : 'offline');
      }
    };

    checkStatus();
    const interval = setInterval(checkStatus, 30000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const statusConfig = {
    checking: {
      color: 'bg-text-secondary',
      text: 'Checking...',
      textColor: 'text-text-secondary',
    },
    online: {
      color: 'bg-risk-green',
      text: 'API Online',
      textColor: 'text-risk-green',
    },
    offline: {
      color: 'bg-risk-red',
      text: 'API Offline',
      textColor: 'text-risk-red',
    },
  };

  const config = statusConfig[status];

  return (
    <div className="flex items-center gap-2">
      <div className="relative">
        <div className={cn('h-2 w-2 rounded-full', config.color)} />
        {status === 'online' && (
          <div
            className={cn(
              'absolute inset-0 h-2 w-2 rounded-full animate-ping opacity-75',
              config.color
            )}
          />
        )}
      </div>
      <span className={cn('text-xs font-medium', config.textColor)}>
        {config.text}
      </span>
      {status === 'checking' && (
        <Loader2 className="h-3 w-3 animate-spin text-text-secondary" />
      )}
    </div>
  );
}
