'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardTitle, Badge } from '@/components/ui';
import { RiskBadge } from '@/components/system';
import { RouteHopRow } from './RouteHopRow';
import { RouteStrip } from './RouteStrip';
import { ROUTE_PROFILES } from '@/lib/utils';
import type { RouteResponse, HotzoneResponse, HotzoneSystemData } from '@/lib/types';
import { Gauge, Route, Zap, MapPin, Navigation, Loader2, AlertTriangle, Flame, Map as MapIcon } from 'lucide-react';
import { GatekeeperAPI } from '@/lib/api';
import Link from 'next/link';

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
  const profile = ROUTE_PROFILES[route.profile] ?? { label: route.profile, description: '', color: 'text-text-secondary', borderColor: 'border-border' };
  const [waypointStatus, setWaypointStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [waypointMessage, setWaypointMessage] = useState('');

  // Fetch hotzones to warn about dangerous systems on route
  const { data: hotzoneData } = useQuery<HotzoneResponse>({
    queryKey: ['hotzones-route-check'],
    queryFn: () => GatekeeperAPI.getHotzones(1, 50),
    staleTime: 60_000,
    refetchInterval: 60_000,
  });

  // Match route systems against current hotzones
  const routeSystemNames = new Set(route.path.map((h) => h.system_name));
  const hotzoneWarnings = (hotzoneData?.systems ?? []).filter(
    (hz) => routeSystemNames.has(hz.system_name) && (hz.kills_current + hz.pods_current) >= 3
  );

  // Build hotzone lookup by system name for per-hop gate warnings
  const hotzoneBySystem = new Map<string, HotzoneSystemData>();
  for (const hz of hotzoneData?.systems ?? []) {
    hotzoneBySystem.set(hz.system_name, hz);
  }

  const handleSetInGameRoute = async () => {
    if (route.path.length === 0) return;
    setWaypointStatus('loading');
    setWaypointMessage('');
    try {
      const systemNames = route.path.map((hop) => hop.system_name);
      const result = await GatekeeperAPI.setWaypoints(systemNames);
      if (result.success) {
        setWaypointStatus('success');
        setWaypointMessage(`Set ${result.waypoints_set} waypoint${result.waypoints_set !== 1 ? 's' : ''} in-game`);
      } else {
        setWaypointStatus('error');
        setWaypointMessage('Failed to set waypoints');
      }
    } catch (err) {
      setWaypointStatus('error');
      setWaypointMessage(err instanceof Error ? err.message : 'Failed to set waypoints');
    }
    setTimeout(() => {
      setWaypointStatus('idle');
      setWaypointMessage('');
    }, 4000);
  };

  return (
    <div className="space-y-4">
      {/* Summary Card */}
      <Card>
        <div className="flex flex-wrap items-center gap-4 mb-4">
          <CardTitle className="flex-1">Route Summary</CardTitle>
          {route.path.length > 0 && (
            <>
              <Link
                href={`/map?from=${encodeURIComponent(route.from_system)}&to=${encodeURIComponent(route.to_system)}&profile=${route.profile}`}
                className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium rounded-lg
                  bg-primary/20 text-primary border border-primary/30
                  hover:bg-primary/30 hover:border-primary/50
                  transition-colors"
              >
                <MapIcon className="h-4 w-4" />
                View on Map
              </Link>
              <button
                onClick={handleSetInGameRoute}
                disabled={waypointStatus === 'loading'}
                className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium rounded-lg
                  bg-cyan-600/20 text-cyan-400 border border-cyan-500/30
                  hover:bg-cyan-600/30 hover:border-cyan-500/50
                  disabled:opacity-50 disabled:cursor-not-allowed
                  transition-colors"
              >
                {waypointStatus === 'loading' ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Navigation className="h-4 w-4" />
                )}
                Set In-Game Route
              </button>
            </>
          )}
          <Badge variant="info" size="md">
            {profile.label}
          </Badge>
        </div>
        {waypointMessage && (
          <div className={`text-sm mb-3 px-3 py-1.5 rounded ${
            waypointStatus === 'success' ? 'text-green-400 bg-green-500/10' :
            waypointStatus === 'error' ? 'text-red-400 bg-red-500/10' :
            'text-text-secondary'
          }`}>
            {waypointMessage}
          </div>
        )}

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

      {/* Pirate insurgency warning */}
      {route.path.some((hop) => hop.pirate_suppressed) && (
        <div className="flex items-start gap-3 bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3">
          <AlertTriangle className="h-5 w-5 text-red-400 shrink-0 mt-0.5" />
          <div>
            <div className="text-sm font-medium text-red-400">Pirate Insurgency — Security Suppressed</div>
            <div className="text-xs text-text-secondary mt-1">
              This route passes through systems under pirate occupation where security status is suppressed to nullsec levels.
              Gate guns are disabled, bubbles may be anchored, and combat rules change.
            </div>
            <div className="flex flex-wrap gap-1 mt-2">
              {route.path
                .filter((hop) => hop.pirate_suppressed)
                .map((hop) => (
                  <Badge key={hop.system_name} variant="danger" size="sm">
                    {hop.system_name}
                  </Badge>
                ))}
            </div>
          </div>
        </div>
      )}

      {/* Hotzone warning */}
      {hotzoneWarnings.length > 0 && (
        <div className="flex items-start gap-3 bg-orange-500/10 border border-orange-500/30 rounded-lg px-4 py-3">
          <Flame className="h-5 w-5 text-orange-400 shrink-0 mt-0.5" />
          <div>
            <div className="text-sm font-medium text-orange-400">
              Active Hotzones on Route
            </div>
            <div className="text-xs text-text-secondary mt-1">
              {hotzoneWarnings.length === 1
                ? 'A system on your route has significant recent kill activity.'
                : `${hotzoneWarnings.length} systems on your route have significant recent kill activity.`}
            </div>
            <div className="flex flex-wrap gap-1.5 mt-2">
              {hotzoneWarnings.map((hz) => (
                <Badge key={hz.system_name} variant="warning" size="sm">
                  {hz.system_name} — {hz.kills_current + hz.pods_current} kills
                  {hz.gate_camp_likely ? ' (gate camp)' : ''}
                </Badge>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Route Strip — subway-line visualization */}
      <RouteStrip hops={route.path} />

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
              hotzone={hotzoneBySystem.get(hop.system_name)}
              isFirst={index === 0}
              isLast={index === route.path.length - 1}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
