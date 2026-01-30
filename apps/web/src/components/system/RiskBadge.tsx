'use client';

import { cn } from '@/lib/utils';
import { AlertTriangle, Shield, ShieldAlert, ShieldCheck } from 'lucide-react';

interface RiskBadgeProps {
  riskColor: 'green' | 'yellow' | 'orange' | 'red';
  riskScore?: number;
  showIcon?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export function RiskBadge({
  riskColor,
  riskScore,
  showIcon = true,
  size = 'md',
}: RiskBadgeProps) {
  const colorStyles = {
    green: 'text-risk-green bg-risk-green/20 border-risk-green/30',
    yellow: 'text-risk-yellow bg-risk-yellow/20 border-risk-yellow/30',
    orange: 'text-risk-orange bg-risk-orange/20 border-risk-orange/30',
    red: 'text-risk-red bg-risk-red/20 border-risk-red/30',
  };

  const icons = {
    green: ShieldCheck,
    yellow: Shield,
    orange: ShieldAlert,
    red: AlertTriangle,
  };

  const sizes = {
    sm: 'px-1.5 py-0.5 text-xs gap-1',
    md: 'px-2 py-0.5 text-sm gap-1.5',
    lg: 'px-2.5 py-1 text-base gap-2',
  };

  const iconSizes = {
    sm: 'h-3 w-3',
    md: 'h-3.5 w-3.5',
    lg: 'h-4 w-4',
  };

  const Icon = icons[riskColor];

  const getLabel = () => {
    switch (riskColor) {
      case 'green':
        return 'Safe';
      case 'yellow':
        return 'Caution';
      case 'orange':
        return 'Danger';
      case 'red':
        return 'Critical';
    }
  };

  return (
    <span
      className={cn(
        'inline-flex items-center font-medium rounded border',
        colorStyles[riskColor],
        sizes[size]
      )}
    >
      {showIcon && <Icon className={iconSizes[size]} />}
      <span>{riskScore !== undefined ? riskScore.toFixed(1) : getLabel()}</span>
    </span>
  );
}
