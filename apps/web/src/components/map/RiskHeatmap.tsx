'use client';

import { useMemo } from 'react';
import type { RiskHeatmapProps, SystemRisk, MapSystem, MapViewport } from './types';
import { RISK_COLORS, getRiskColor } from './types';

/**
 * Transform world coordinates to screen coordinates
 */
function worldToScreen(
  worldX: number,
  worldY: number,
  viewport: MapViewport
): { x: number; y: number } {
  const x = (worldX - viewport.x) * viewport.zoom + viewport.width / 2;
  const y = (worldY - viewport.y) * viewport.zoom + viewport.height / 2;
  return { x, y };
}

/**
 * Check if a point is visible in the viewport (with margin for glow effects)
 */
function isVisible(
  screenX: number,
  screenY: number,
  viewport: MapViewport,
  margin: number = 100
): boolean {
  return (
    screenX >= -margin &&
    screenX <= viewport.width + margin &&
    screenY >= -margin &&
    screenY <= viewport.height + margin
  );
}

/**
 * Calculate glow intensity based on risk score and zoom
 */
function getGlowIntensity(riskScore: number, zoom: number): number {
  // Higher risk = larger glow
  // Lower zoom = larger glow to maintain visibility
  const baseIntensity = 20 + riskScore * 8;
  const zoomFactor = Math.max(0.5, 1 / Math.sqrt(zoom));
  return baseIntensity * zoomFactor;
}

/**
 * Get gradient stops for risk color
 */
function getGradientStops(color: string, opacity: number): string {
  return `radial-gradient(circle, ${color}${Math.round(opacity * 255).toString(16).padStart(2, '0')} 0%, ${color}40 30%, transparent 70%)`;
}

interface RiskGlowProps {
  risk: SystemRisk;
  system: MapSystem;
  viewport: MapViewport;
  opacity: number;
}

/**
 * Individual risk glow indicator for a system
 */
function RiskGlow({ risk, system, viewport, opacity }: RiskGlowProps) {
  const screenPos = worldToScreen(system.x, system.y, viewport);

  // Skip if not visible
  if (!isVisible(screenPos.x, screenPos.y, viewport)) {
    return null;
  }

  const color = getRiskColor(risk.riskColor);
  const intensity = getGlowIntensity(risk.riskScore, viewport.zoom);
  const size = intensity * 2;

  // Scale intensity by risk score (0-10 -> 0.3-1.0)
  const riskOpacity = 0.3 + (risk.riskScore / 10) * 0.7;
  const finalOpacity = opacity * riskOpacity;

  return (
    <div
      className="absolute pointer-events-none animate-fade-in"
      style={{
        left: screenPos.x - size / 2,
        top: screenPos.y - size / 2,
        width: size,
        height: size,
        background: getGradientStops(color, finalOpacity),
        filter: `blur(${intensity * 0.3}px)`,
      }}
      key={risk.systemId}
    />
  );
}

/**
 * Risk heatmap overlay for the map
 *
 * Renders colored glows around systems based on their risk level.
 * Green = safe, Yellow = caution, Orange = danger, Red = critical
 *
 * Usage:
 * ```tsx
 * <RiskHeatmap
 *   risks={risks}
 *   systems={systemsMap}
 *   viewport={viewport}
 *   opacity={0.7}
 * />
 * ```
 */
export function RiskHeatmap({
  risks,
  systems,
  viewport,
  opacity = 0.7,
}: RiskHeatmapProps) {
  // Filter risks that have valid systems
  const visibleRisks = useMemo(() => {
    return risks.filter((risk) => systems.has(risk.systemId));
  }, [risks, systems]);

  // Sort by risk score so higher risks render on top
  const sortedRisks = useMemo(() => {
    return [...visibleRisks].sort((a, b) => a.riskScore - b.riskScore);
  }, [visibleRisks]);

  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden">
      {/* Render glows */}
      {sortedRisks.map((risk) => {
        const system = systems.get(risk.systemId);
        if (!system) return null;

        return (
          <RiskGlow
            key={risk.systemId}
            risk={risk}
            system={system}
            viewport={viewport}
            opacity={opacity}
          />
        );
      })}
    </div>
  );
}

/**
 * Legend component for the risk heatmap
 */
export function RiskHeatmapLegend() {
  const levels = [
    { color: 'green', label: 'Safe', range: '0-2' },
    { color: 'yellow', label: 'Caution', range: '2-4' },
    { color: 'orange', label: 'Danger', range: '4-7' },
    { color: 'red', label: 'Critical', range: '7-10' },
  ] as const;

  return (
    <div className="flex flex-col gap-1.5">
      <div className="text-xs font-medium text-text-secondary uppercase tracking-wide">
        Risk Level
      </div>
      {levels.map(({ color, label, range }) => (
        <div key={color} className="flex items-center gap-2">
          <div
            className="w-3 h-3 rounded-full"
            style={{
              backgroundColor: RISK_COLORS[color],
              boxShadow: `0 0 6px ${RISK_COLORS[color]}`,
            }}
          />
          <span className="text-sm text-text">{label}</span>
          <span className="text-xs text-text-secondary">({range})</span>
        </div>
      ))}
    </div>
  );
}

export default RiskHeatmap;
