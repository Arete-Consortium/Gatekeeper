'use client';

import { Card, CardTitle, Badge } from '@/components/ui';
import type { FleetAnalysisResponse } from '@/lib/types';
import {
  Shield,
  AlertTriangle,
  Lightbulb,
  Users,
  Swords,
  Crosshair,
  Eye,
  Anchor,
} from 'lucide-react';

interface FleetResultProps {
  analysis: FleetAnalysisResponse;
}

const THREAT_CONFIG: Record<
  string,
  { variant: 'default' | 'success' | 'warning' | 'danger' | 'info'; label: string }
> = {
  minimal: { variant: 'success', label: 'Minimal' },
  moderate: { variant: 'info', label: 'Moderate' },
  significant: { variant: 'warning', label: 'Significant' },
  critical: { variant: 'danger', label: 'Critical' },
  overwhelming: { variant: 'danger', label: 'Overwhelming' },
};

const DPS_CONFIG: Record<
  string,
  { variant: 'default' | 'success' | 'warning' | 'danger' | 'info'; label: string }
> = {
  low: { variant: 'success', label: 'Low' },
  medium: { variant: 'info', label: 'Medium' },
  high: { variant: 'warning', label: 'High' },
  extreme: { variant: 'danger', label: 'Extreme' },
};

const ROLE_LABELS: Record<string, string> = {
  dps: 'DPS',
  logistics: 'Logistics',
  tackle: 'Tackle',
  ewar: 'EWAR',
  scout: 'Scout',
  capital: 'Capital',
  support: 'Support',
  unknown: 'Unknown',
};

const ROLE_COLORS: Record<string, string> = {
  dps: 'bg-risk-red/20 text-risk-red border-risk-red/30',
  logistics: 'bg-risk-green/20 text-risk-green border-risk-green/30',
  tackle: 'bg-risk-yellow/20 text-risk-yellow border-risk-yellow/30',
  ewar: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
  scout: 'bg-sky-500/20 text-sky-400 border-sky-500/30',
  capital: 'bg-risk-orange/20 text-risk-orange border-risk-orange/30',
  support: 'bg-primary/20 text-primary border-primary/30',
  unknown: 'bg-card text-text-secondary border-border',
};

export function FleetResult({ analysis }: FleetResultProps) {
  const threat = THREAT_CONFIG[analysis.threat_level] ?? THREAT_CONFIG.minimal;
  const dps = DPS_CONFIG[analysis.estimated_dps_category] ?? DPS_CONFIG.low;

  const sortedRoles = Object.entries(analysis.composition).sort(
    ([, a], [, b]) => b - a
  );

  const maxRoleCount = sortedRoles.length > 0 ? sortedRoles[0][1] : 1;

  return (
    <div className="space-y-4">
      {/* Threat Level Card */}
      <Card>
        <div className="flex items-center gap-4 mb-4">
          <div className="p-3 bg-primary/20 rounded-lg">
            <Shield className="h-6 w-6 text-primary" />
          </div>
          <div className="flex-1">
            <CardTitle>Threat Assessment</CardTitle>
            <div className="flex items-center gap-3 mt-2">
              <Badge variant={threat.variant} size="md">
                {threat.label}
              </Badge>
              <span className="text-sm text-text-secondary">
                {analysis.total_pilots} pilot{analysis.total_pilots !== 1 ? 's' : ''}
              </span>
            </div>
          </div>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="bg-surface rounded-lg p-3 text-center">
            <div className="text-lg font-bold text-text">{analysis.total_ships}</div>
            <div className="text-xs text-text-secondary">Ships</div>
          </div>
          <div className="bg-surface rounded-lg p-3 text-center">
            <Badge variant={dps.variant} size="sm">
              {dps.label} DPS
            </Badge>
          </div>
          <div className="bg-surface rounded-lg p-3 text-center">
            <Badge
              variant={analysis.has_logistics ? 'success' : 'default'}
              size="sm"
            >
              {analysis.has_logistics ? 'Logi' : 'No Logi'}
            </Badge>
          </div>
          <div className="bg-surface rounded-lg p-3 text-center">
            <Badge
              variant={analysis.has_capitals ? 'danger' : 'default'}
              size="sm"
            >
              {analysis.has_capitals ? 'Capitals' : 'No Caps'}
            </Badge>
          </div>
        </div>
      </Card>

      {/* Composition Breakdown */}
      <Card>
        <div className="flex items-center gap-2 mb-4">
          <Users className="h-5 w-5 text-primary" />
          <CardTitle>Composition Breakdown</CardTitle>
        </div>

        {/* Role bars */}
        <div className="space-y-3">
          {sortedRoles.map(([role, count]) => (
            <div key={role}>
              <div className="flex items-center justify-between mb-1">
                <span
                  className={`inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-md border ${ROLE_COLORS[role] ?? ROLE_COLORS.unknown}`}
                >
                  {ROLE_LABELS[role] ?? role}
                </span>
                <span className="text-sm text-text-secondary">{count}</span>
              </div>
              <div className="w-full bg-surface rounded-full h-2">
                <div
                  className={`h-2 rounded-full transition-all ${
                    role === 'capital'
                      ? 'bg-risk-orange'
                      : role === 'dps'
                        ? 'bg-risk-red'
                        : role === 'logistics'
                          ? 'bg-risk-green'
                          : role === 'tackle'
                            ? 'bg-risk-yellow'
                            : 'bg-primary'
                  }`}
                  style={{ width: `${(count / maxRoleCount) * 100}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Ship List */}
      {analysis.ship_list.length > 0 && (
        <Card>
          <div className="flex items-center gap-2 mb-4">
            <Swords className="h-5 w-5 text-primary" />
            <CardTitle>Ship List</CardTitle>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {analysis.ship_list.map((ship) => (
              <div
                key={ship.name}
                className="flex items-center justify-between bg-surface rounded-lg px-3 py-2"
              >
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-text">
                    {ship.name}
                  </span>
                  <span
                    className={`inline-flex items-center px-1.5 py-0.5 text-xs rounded border ${ROLE_COLORS[ship.role] ?? ROLE_COLORS.unknown}`}
                  >
                    {ROLE_LABELS[ship.role] ?? ship.role}
                  </span>
                </div>
                <span className="text-sm font-mono text-text-secondary">
                  x{ship.count}
                </span>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Tactical Advice */}
      {analysis.advice.length > 0 && (
        <Card>
          <div className="flex items-center gap-2 mb-4">
            <Lightbulb className="h-5 w-5 text-risk-yellow" />
            <CardTitle>Tactical Advice</CardTitle>
          </div>

          <ul className="space-y-2">
            {analysis.advice.map((tip, i) => (
              <li key={i} className="flex items-start gap-2">
                <AlertTriangle className="h-4 w-4 text-risk-yellow mt-0.5 shrink-0" />
                <span className="text-sm text-text-secondary">{tip}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}
