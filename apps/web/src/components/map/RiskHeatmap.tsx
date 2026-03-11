'use client';

import React, { useMemo } from 'react';
import type { RiskHeatmapProps, SystemRisk, MapSystem, MapViewport } from './types';
import { RISK_COLORS, getRiskColor } from './types';

export function RiskHeatmap({
  risks,
  systems,
  viewport,
  opacity = 0.8,
}: RiskHeatmapProps) {
  const markers = useMemo(() => {
    const result: Array<{
      x: number;
      y: number;
      color: string;
      radius: number;
      intensity: number;
      systemId: number;
    }> = [];

    for (const risk of risks) {
      const system = systems.get(risk.systemId);
      if (!system) continue;

      const sx = (system.x - viewport.x) * viewport.zoom + viewport.width / 2;
      const sy = (system.y - viewport.y) * viewport.zoom + viewport.height / 2;

      if (sx < -80 || sx > viewport.width + 80 || sy < -80 || sy > viewport.height + 80) continue;

      const color = getRiskColor(risk.riskColor);
      // Radius scales with risk score and zoom
      const baseRadius = 8 + risk.riskScore * 3;
      const radius = baseRadius * Math.max(0.6, Math.min(2, viewport.zoom * 0.5));
      // Intensity: higher risk = more opaque
      const intensity = 0.15 + (risk.riskScore / 10) * 0.55;

      result.push({ x: sx, y: sy, color, radius, intensity, systemId: risk.systemId });
    }

    // Sort so higher risk renders on top
    result.sort((a, b) => a.intensity - b.intensity);
    return result;
  }, [risks, systems, viewport]);

  if (markers.length === 0) return null;

  return (
    <svg
      className="absolute inset-0 pointer-events-none"
      width={viewport.width}
      height={viewport.height}
      style={{ zIndex: 0 }}
    >
      <defs>
        {/* Unique gradient per risk color for sharp, visible glows */}
        {['green', 'yellow', 'orange', 'red'].map((riskColor) => {
          const color = RISK_COLORS[riskColor as keyof typeof RISK_COLORS];
          return (
            <radialGradient key={riskColor} id={`risk-${riskColor}`}>
              <stop offset="0%" stopColor={color} stopOpacity={0.8} />
              <stop offset="40%" stopColor={color} stopOpacity={0.4} />
              <stop offset="100%" stopColor={color} stopOpacity={0} />
            </radialGradient>
          );
        })}
      </defs>
      {markers.map((m) => {
        const riskKey = m.color === RISK_COLORS.green ? 'green'
          : m.color === RISK_COLORS.yellow ? 'yellow'
          : m.color === RISK_COLORS.orange ? 'orange'
          : 'red';
        return (
          <circle
            key={m.systemId}
            cx={m.x}
            cy={m.y}
            r={m.radius}
            fill={`url(#risk-${riskKey})`}
            opacity={opacity * m.intensity}
          />
        );
      })}
    </svg>
  );
}

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
