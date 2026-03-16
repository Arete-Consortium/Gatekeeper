'use client';

import { memo, useState } from 'react';
import { SecurityBadge, RiskBadge } from '@/components/system';
import { cn } from '@/lib/utils';
import { ChevronDown, Crosshair, Skull, Shield, AlertTriangle, TrendingUp, TrendingDown } from 'lucide-react';
import type { RouteHop, HotzoneSystemData } from '@/lib/types';

interface RouteHopRowProps {
  hop: RouteHop;
  index: number;
  isFirst?: boolean;
  isLast?: boolean;
  hotzone?: HotzoneSystemData;
}

function getRiskColor(risk: number): 'green' | 'yellow' | 'orange' | 'red' {
  if (risk < 25) return 'green';
  if (risk < 50) return 'yellow';
  if (risk < 75) return 'orange';
  return 'red';
}

function BreakdownBar({
  label,
  value,
  total,
  color,
  icon: Icon,
}: {
  label: string;
  value: number;
  total: number;
  color: string;
  icon: React.ElementType;
}) {
  const pct = total > 0 ? (value / total) * 100 : 0;
  return (
    <div className="flex items-center gap-2">
      <Icon className={cn('h-3.5 w-3.5 shrink-0', color)} />
      <span className="text-xs text-text-secondary w-16 shrink-0">{label}</span>
      <div className="flex-1 h-1.5 bg-background rounded-full overflow-hidden">
        <div
          className={cn('h-full rounded-full transition-all', color.replace('text-', 'bg-'))}
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
      </div>
      <span className="text-xs font-mono text-text-secondary w-12 text-right">
        {value.toFixed(1)}
      </span>
      <span className="text-[10px] text-text-secondary/60 w-10 text-right">
        {pct > 0 ? `${pct.toFixed(0)}%` : '—'}
      </span>
    </div>
  );
}

/**
 * RouteHopRow - Expandable row with risk score breakdown
 * Click to expand and see what drives the risk score
 */
export const RouteHopRow = memo(function RouteHopRow({
  hop,
  index,
  isFirst = false,
  isLast = false,
  hotzone,
}: RouteHopRowProps) {
  const [expanded, setExpanded] = useState(false);
  const riskColor = getRiskColor(hop.risk_score);
  const hasBreakdown = hop.risk_breakdown != null || hotzone != null;

  return (
    <div
      className={cn(
        'bg-card border-l-4',
        riskColor === 'green' && 'border-l-risk-green',
        riskColor === 'yellow' && 'border-l-risk-yellow',
        riskColor === 'orange' && 'border-l-risk-orange',
        riskColor === 'red' && 'border-l-risk-red',
        isFirst && 'rounded-t-lg',
        isLast && !expanded && 'rounded-b-lg',
        !isFirst && 'border-t border-border'
      )}
    >
      {/* Main row — always visible */}
      <button
        type="button"
        onClick={() => hasBreakdown && setExpanded(!expanded)}
        className={cn(
          'flex items-center gap-4 px-4 py-3 w-full text-left',
          'hover:bg-card-hover transition-colors',
          hasBreakdown && 'cursor-pointer'
        )}
      >
        {/* Jump number */}
        <div className="w-8 text-center">
          <span className="text-sm text-text-secondary font-mono">{index}</span>
        </div>

        {/* System name */}
        <div className="flex-1 min-w-0 flex items-center gap-2">
          <span className="font-medium text-text truncate">{hop.system_name}</span>
          {hop.pirate_suppressed && (
            <span className="text-[10px] font-medium text-red-400 bg-red-500/15 px-1.5 py-0.5 rounded shrink-0">
              SUPPRESSED
            </span>
          )}
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

        {/* Expand indicator */}
        {hasBreakdown && (
          <ChevronDown
            className={cn(
              'h-4 w-4 text-text-secondary transition-transform shrink-0',
              expanded && 'rotate-180'
            )}
          />
        )}
      </button>

      {/* Expanded breakdown panel */}
      {expanded && hop.risk_breakdown && (
        <div className={cn(
          'px-4 pb-3 pt-0 ml-12 mr-4 space-y-2',
          'border-t border-border/50',
          isLast && 'rounded-b-lg'
        )}>
          <div className="text-[10px] uppercase tracking-wider text-text-secondary/60 font-semibold mt-2">
            Risk Breakdown
          </div>

          <div className="space-y-1.5">
            <BreakdownBar
              label="Security"
              value={hop.risk_breakdown.security_component}
              total={hop.risk_score}
              color="text-cyan-400"
              icon={Shield}
            />
            <BreakdownBar
              label="Kills"
              value={hop.risk_breakdown.kills_component}
              total={hop.risk_score}
              color="text-orange-400"
              icon={Crosshair}
            />
            <BreakdownBar
              label="Pods"
              value={hop.risk_breakdown.pods_component}
              total={hop.risk_score}
              color="text-red-400"
              icon={Skull}
            />
          </div>

          {/* Raw stats */}
          {hop.zkill_stats && (hop.zkill_stats.recent_kills > 0 || hop.zkill_stats.recent_pods > 0) && (
            <div className="flex gap-4 pt-1.5 border-t border-border/30">
              <div className="flex items-center gap-1.5">
                <Crosshair className="h-3 w-3 text-orange-400/70" />
                <span className="text-xs text-text-secondary">
                  <span className="font-mono font-medium text-text">{hop.zkill_stats.recent_kills}</span> kills (24h)
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <Skull className="h-3 w-3 text-red-400/70" />
                <span className="text-xs text-text-secondary">
                  <span className="font-mono font-medium text-text">{hop.zkill_stats.recent_pods}</span> pods (24h)
                </span>
              </div>
            </div>
          )}

          {/* Gate camp + trend from hotzones */}
          {hotzone && (hotzone.kills_current + hotzone.pods_current) > 0 && (
            <div className="flex flex-wrap gap-3 pt-1.5 border-t border-border/30">
              {hotzone.gate_camp_likely && (
                <div className="flex items-center gap-1.5">
                  <AlertTriangle className="h-3 w-3 text-red-400" />
                  <span className="text-xs font-medium text-red-400">Gate Camp Likely</span>
                </div>
              )}
              <div className="flex items-center gap-1.5">
                {hotzone.trend > 1.0 ? (
                  <TrendingUp className="h-3 w-3 text-orange-400" />
                ) : (
                  <TrendingDown className="h-3 w-3 text-green-400" />
                )}
                <span className="text-xs text-text-secondary">
                  {hotzone.trend > 1.0 ? 'Heating up' : 'Cooling down'}
                  <span className="text-text-secondary/60"> ({hotzone.trend.toFixed(1)}x)</span>
                </span>
              </div>
              {hotzone.predicted_1hr > 0 && (
                <span className="text-xs text-text-secondary">
                  ~{hotzone.predicted_1hr} kills predicted (1h)
                </span>
              )}
            </div>
          )}
        </div>
      )}

      {/* Gate camp inline warning — visible without expanding */}
      {!expanded && hotzone?.gate_camp_likely && (
        <div className="flex items-center gap-1.5 px-4 pb-2 ml-12">
          <AlertTriangle className="h-3 w-3 text-red-400" />
          <span className="text-[10px] font-medium text-red-400">Gate camp likely</span>
        </div>
      )}
    </div>
  );
});
