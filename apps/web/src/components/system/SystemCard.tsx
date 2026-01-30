'use client';

import { memo, useCallback } from 'react';
import { Card } from '@/components/ui';
import { SecurityBadge } from './SecurityBadge';
import { RiskBadge } from './RiskBadge';
import { cn } from '@/lib/utils';

interface SystemCardProps {
  systemName: string;
  security: number;
  riskColor?: 'green' | 'yellow' | 'orange' | 'red';
  kills?: number;
  pods?: number;
  onClick?: () => void;
  className?: string;
}

/**
 * SystemCard - Memoized for performance in system lists
 * Only re-renders when system data changes
 */
export const SystemCard = memo(function SystemCard({
  systemName,
  security,
  riskColor,
  kills,
  pods,
  onClick,
  className,
}: SystemCardProps) {
  const getBorderColor = () => {
    if (!riskColor) return 'border-l-border';
    switch (riskColor) {
      case 'green':
        return 'border-l-risk-green';
      case 'yellow':
        return 'border-l-risk-yellow';
      case 'orange':
        return 'border-l-risk-orange';
      case 'red':
        return 'border-l-risk-red';
    }
  };

  return (
    <Card
      hover={!!onClick}
      onClick={onClick}
      className={cn('border-l-4', getBorderColor(), className)}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="font-semibold text-text">{systemName}</span>
          <SecurityBadge security={security} size="sm" />
        </div>
        {riskColor && <RiskBadge riskColor={riskColor} size="sm" />}
      </div>

      {(kills !== undefined || pods !== undefined) && (
        <div className="flex gap-4 mt-2 text-sm">
          {kills !== undefined && (
            <span className="text-risk-red">{kills} kills</span>
          )}
          {pods !== undefined && pods > 0 && (
            <span className="text-risk-orange">{pods} pods</span>
          )}
        </div>
      )}
    </Card>
  );
});
