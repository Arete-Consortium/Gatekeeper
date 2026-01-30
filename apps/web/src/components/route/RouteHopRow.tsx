'use client';

import { SecurityBadge, RiskBadge } from '@/components/system';
import { cn } from '@/lib/utils';
import type { RouteHop } from '@/lib/types';

interface RouteHopRowProps {
  hop: RouteHop;
  index: number;
  isFirst?: boolean;
  isLast?: boolean;
}

function getRiskColor(risk: number): 'green' | 'yellow' | 'orange' | 'red' {
  if (risk < 25) return 'green';
  if (risk < 50) return 'yellow';
  if (risk < 75) return 'orange';
  return 'red';
}

export function RouteHopRow({
  hop,
  index,
  isFirst = false,
  isLast = false,
}: RouteHopRowProps) {
  const riskColor = getRiskColor(hop.risk_score);

  return (
    <div
      className={cn(
        'flex items-center gap-4 px-4 py-3 bg-card border-l-4',
        'hover:bg-card-hover transition-colors',
        riskColor === 'green' && 'border-l-risk-green',
        riskColor === 'yellow' && 'border-l-risk-yellow',
        riskColor === 'orange' && 'border-l-risk-orange',
        riskColor === 'red' && 'border-l-risk-red',
        isFirst && 'rounded-t-lg',
        isLast && 'rounded-b-lg',
        !isFirst && 'border-t border-border'
      )}
    >
      {/* Jump number */}
      <div className="w-8 text-center">
        <span className="text-sm text-text-secondary font-mono">{index}</span>
      </div>

      {/* System name */}
      <div className="flex-1 min-w-0">
        <span className="font-medium text-text truncate">{hop.system_name}</span>
      </div>

      {/* Security badge */}
      <SecurityBadge security={hop.security_status} size="sm" />

      {/* Risk badge */}
      <RiskBadge
        riskColor={riskColor}
        riskScore={hop.risk_score}
        showIcon={false}
        size="sm"
      />
    </div>
  );
}
