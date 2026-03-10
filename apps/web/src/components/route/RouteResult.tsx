'use client';

import { Card, CardTitle, Badge } from '@/components/ui';
import { RiskBadge } from '@/components/system';
import { RouteHopRow } from './RouteHopRow';
import { ROUTE_PROFILES } from '@/lib/utils';
import type { RouteResponse } from '@/lib/types';
import { Gauge, Route, Zap, MapPin } from 'lucide-react';

interface RouteResultProps {
  route: RouteResponse;
}

function getRiskColor(risk: number): 'green' | 'yellow' | 'orange' | 'red' {
  if (risk < 25) return 'green';
  if (risk < 50) return 'yellow';
  if (risk < 75) return 'orange';
  return 'red';
}

export function RouteResult({ route }: RouteResultProps) {
  const profile = ROUTE_PROFILES[route.profile];

  return (
    <div className="space-y-4">
      {/* Summary Card */}
      <Card>
        <div className="flex flex-wrap items-center gap-4 mb-4">
          <CardTitle className="flex-1">Route Summary</CardTitle>
          <Badge variant="info" size="md">
            {profile.label}
          </Badge>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {/* Total Jumps */}
          <div className="text-center p-3 bg-background rounded-lg">
            <div className="flex items-center justify-center gap-2 mb-1">
              <Route className="h-4 w-4 text-primary" />
              <span className="text-xs text-text-secondary uppercase">Jumps</span>
            </div>
            <span className="text-2xl font-bold text-text">
              {route.total_jumps}
            </span>
          </div>

          {/* Max Risk */}
          <div className="text-center p-3 bg-background rounded-lg">
            <div className="flex items-center justify-center gap-2 mb-1">
              <Gauge className="h-4 w-4 text-risk-orange" />
              <span className="text-xs text-text-secondary uppercase">
                Max Risk
              </span>
            </div>
            <div className="flex justify-center">
              <RiskBadge
                riskColor={getRiskColor(route.max_risk)}
                riskScore={route.max_risk}
                showIcon={false}
                size="lg"
              />
            </div>
          </div>

          {/* Avg Risk */}
          <div className="text-center p-3 bg-background rounded-lg">
            <div className="flex items-center justify-center gap-2 mb-1">
              <Gauge className="h-4 w-4 text-text-secondary" />
              <span className="text-xs text-text-secondary uppercase">
                Avg Risk
              </span>
            </div>
            <div className="flex justify-center">
              <RiskBadge
                riskColor={getRiskColor(route.avg_risk)}
                riskScore={route.avg_risk}
                showIcon={false}
                size="lg"
              />
            </div>
          </div>

          {/* Special Routes */}
          <div className="text-center p-3 bg-background rounded-lg">
            <div className="flex items-center justify-center gap-2 mb-1">
              <Zap className="h-4 w-4 text-risk-yellow" />
              <span className="text-xs text-text-secondary uppercase">
                Special
              </span>
            </div>
            <div className="flex justify-center gap-2">
              {route.bridges_used > 0 && (
                <Badge variant="warning" size="sm">
                  {route.bridges_used} bridge{route.bridges_used > 1 ? 's' : ''}
                </Badge>
              )}
              {route.thera_used > 0 && (
                <Badge variant="info" size="sm">
                  Thera
                </Badge>
              )}
              {route.bridges_used === 0 && route.thera_used === 0 && (
                <span className="text-text-secondary text-sm">None</span>
              )}
            </div>
          </div>
        </div>
      </Card>

      {/* Route Path */}
      <div>
        <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-3">
          Route Path
        </h3>
        <div className="rounded-lg overflow-hidden border border-border">
          {route.path.map((hop, index) => (
            <RouteHopRow
              key={`${hop.system_name}-${index}`}
              hop={hop}
              index={index}
              isFirst={index === 0}
              isLast={index === route.path.length - 1}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
