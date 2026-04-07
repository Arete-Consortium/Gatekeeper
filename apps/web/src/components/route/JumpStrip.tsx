'use client';

import { useRef, useEffect, useCallback, useState, useMemo, memo } from 'react';
import type { JumpLegResponse } from '@/lib/types';

interface JumpStripProps {
  legs: JumpLegResponse[];
  fuelTypeName?: string;
  hoveredIndex?: number | null;
  onLegHover?: (index: number | null) => void;
  onLegClick?: (index: number) => void;
}

const NODE_RADIUS = 10;
const NODE_SPACING = 100;
const STRIP_HEIGHT = 135;
const BASELINE_Y = 50;

// Fatigue → arc color
function getFatigueColor(fatigue: number): string {
  if (fatigue < 10) return '#22c55e';
  if (fatigue < 30) return '#eab308';
  if (fatigue < 60) return '#f97316';
  return '#ef4444';
}

// Security status → node color (matches SecurityBadge palette)
function getSecurityNodeColor(sec: number): string {
  if (sec >= 0.5) return '#00ff00'; // highsec
  if (sec > 0) return '#ffaa00';    // lowsec
  return '#ff4444';                  // nullsec
}

// Risk score → arc glow color
function getRiskArcColor(score: number): string {
  if (score < 25) return '#32d74b';
  if (score < 50) return '#ffd60a';
  if (score < 75) return '#ff9f0a';
  return '#ff453a';
}

/**
 * JumpStrip — arc-style jump route visualization for capital ships
 * Shows jump legs as arcs with fuel/fatigue/distance inline
 */
export const JumpStrip = memo(function JumpStrip({
  legs,
  fuelTypeName,
  hoveredIndex,
  onLegHover,
  onLegClick,
}: JumpStripProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [localHover, setLocalHover] = useState<number | null>(null);
  const activeHover = hoveredIndex ?? localHover;

  // N legs = N+1 nodes (systems)
  const nodeCount = legs.length + 1;
  const totalWidth = Math.max(400, nodeCount * NODE_SPACING + 80);

  const nodeX = useCallback((i: number) => 40 + i * NODE_SPACING, []);

  // Collect unique system names in order
  const systems = useMemo(() => {
    const result: string[] = [];
    if (legs.length > 0) {
      result.push(legs[0].from_system);
      for (const leg of legs) {
        result.push(leg.to_system);
      }
    }
    return result;
  }, [legs]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || legs.length === 0) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = totalWidth * dpr;
    canvas.height = STRIP_HEIGHT * dpr;
    canvas.style.width = `${totalWidth}px`;
    canvas.style.height = `${STRIP_HEIGHT}px`;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.scale(dpr, dpr);

    ctx.clearRect(0, 0, totalWidth, STRIP_HEIGHT);

    // Draw jump arcs
    for (let i = 0; i < legs.length; i++) {
      const leg = legs[i];
      const x1 = nodeX(i);
      const x2 = nodeX(i + 1);
      const midX = (x1 + x2) / 2;
      const isHovered = activeHover === i;
      const arcHeight = 25 + Math.min(leg.distance_ly, 10) * 2;
      // Color arc by destination risk (more actionable than fatigue)
      const arcColor = getRiskArcColor(leg.to_risk_score ?? 0);

      ctx.save();

      // Arc
      ctx.beginPath();
      ctx.moveTo(x1, BASELINE_Y);
      ctx.quadraticCurveTo(midX, BASELINE_Y - arcHeight, x2, BASELINE_Y);
      ctx.strokeStyle = isHovered ? '#22d3ee' : arcColor;
      ctx.lineWidth = isHovered ? 3 : 2;
      ctx.setLineDash([6, 4]);

      if (isHovered) {
        ctx.shadowColor = '#22d3ee';
        ctx.shadowBlur = 8;
      }
      ctx.stroke();
      ctx.restore();

      // Inline labels on arc
      const labelY = BASELINE_Y - arcHeight * 0.6;
      ctx.save();
      ctx.font = `${isHovered ? 'bold ' : ''}9px system-ui, -apple-system, sans-serif`;
      ctx.textAlign = 'center';

      // Distance
      ctx.fillStyle = '#94a3b8';
      ctx.fillText(`${leg.distance_ly.toFixed(1)} LY`, midX, labelY - 8);

      // Fuel
      ctx.fillStyle = '#f59e0b';
      ctx.fillText(`${leg.fuel_required.toLocaleString()} fuel`, midX, labelY + 3);

      // Wait time (if any)
      if (leg.wait_time_minutes > 0) {
        ctx.fillStyle = '#f97316';
        ctx.fillText(`wait ${Math.ceil(leg.wait_time_minutes)}m`, midX, labelY + 14);
      }

      ctx.restore();
    }

    // Draw system nodes
    for (let i = 0; i < systems.length; i++) {
      const x = nodeX(i);
      const isEndpoint = i === 0 || i === systems.length - 1;
      const isHoveredNode = activeHover === i || activeHover === i - 1;
      const r = isHoveredNode ? NODE_RADIUS + 2 : NODE_RADIUS;

      ctx.save();

      // Endpoint ring
      if (isEndpoint) {
        ctx.beginPath();
        ctx.arc(x, BASELINE_Y, r + 4, 0, Math.PI * 2);
        ctx.strokeStyle = i === 0 ? '#33cc55' : '#ee4444';
        ctx.lineWidth = 2;
        ctx.stroke();
      }

      // Determine node color: endpoints keep green/red, intermediates use security
      let nodeColor: string;
      if (isEndpoint) {
        nodeColor = i === 0 ? '#33cc55' : '#ee4444';
      } else {
        // Intermediate node: color by destination security of the leg leading to it
        const legToNode = legs[i - 1];
        nodeColor = legToNode ? getSecurityNodeColor(legToNode.to_security_status ?? 0) : '#f59e0b';
      }

      // Cyno waypoint ring (intermediate) — colored by security
      if (!isEndpoint) {
        ctx.beginPath();
        ctx.arc(x, BASELINE_Y, r + 3, 0, Math.PI * 2);
        ctx.strokeStyle = nodeColor + '40';
        ctx.lineWidth = 2;
        ctx.stroke();
      }

      // Node
      if (isHoveredNode) {
        ctx.shadowColor = '#22d3ee';
        ctx.shadowBlur = 10;
      }

      ctx.beginPath();
      ctx.arc(x, BASELINE_Y, r, 0, Math.PI * 2);
      ctx.fillStyle = nodeColor;
      ctx.fill();

      // Inner dot
      ctx.beginPath();
      ctx.arc(x, BASELINE_Y, r * 0.3, 0, Math.PI * 2);
      ctx.fillStyle = '#0a0e17';
      ctx.fill();

      ctx.restore();

      // System label
      ctx.save();
      ctx.font = `${isEndpoint ? 'bold 11px' : '10px'} system-ui, -apple-system, sans-serif`;
      ctx.textAlign = 'center';
      ctx.fillStyle = isHoveredNode || isEndpoint ? '#ffffff' : '#94a3b8';
      ctx.fillText(systems[i], x, BASELINE_Y + r + 16);

      // Security + fatigue below name
      if (i > 0) {
        const legToNode = legs[i - 1];
        ctx.font = '8px system-ui, -apple-system, sans-serif';
        // Security status label
        const secValue = legToNode.to_security_status ?? 0;
        ctx.fillStyle = getSecurityNodeColor(secValue);
        ctx.fillText(secValue.toFixed(1), x, BASELINE_Y + r + 28);
        // Fatigue below security
        if (legToNode.total_fatigue_minutes > 0) {
          ctx.fillStyle = getFatigueColor(legToNode.total_fatigue_minutes);
          ctx.fillText(`${Math.ceil(legToNode.total_fatigue_minutes)}m`, x, BASELINE_Y + r + 38);
        }
      }
      ctx.restore();
    }
  }, [legs, systems, activeHover, totalWidth, nodeX]);

  // Hit test — detect leg (arc) hover
  const getLegAtPosition = useCallback(
    (clientX: number): number | null => {
      const canvas = canvasRef.current;
      if (!canvas) return null;
      const rect = canvas.getBoundingClientRect();
      const x = clientX - rect.left;

      for (let i = 0; i < legs.length; i++) {
        const x1 = nodeX(i);
        const x2 = nodeX(i + 1);
        if (x >= x1 - 10 && x <= x2 + 10) return i;
      }
      return null;
    },
    [legs.length, nodeX]
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      const idx = getLegAtPosition(e.clientX);
      setLocalHover(idx);
      onLegHover?.(idx);
      const canvas = canvasRef.current;
      if (canvas) canvas.style.cursor = idx !== null ? 'pointer' : 'default';
    },
    [getLegAtPosition, onLegHover]
  );

  const handleClick = useCallback(
    (e: React.MouseEvent) => {
      const idx = getLegAtPosition(e.clientX);
      if (idx !== null) onLegClick?.(idx);
    },
    [getLegAtPosition, onLegClick]
  );

  const handleMouseLeave = useCallback(() => {
    setLocalHover(null);
    onLegHover?.(null);
  }, [onLegHover]);

  if (legs.length === 0) return null;

  return (
    <div
      ref={scrollRef}
      className="overflow-x-auto rounded-lg border border-border bg-[#0a0e17]"
      style={{ WebkitOverflowScrolling: 'touch' }}
    >
      <canvas
        ref={canvasRef}
        onMouseMove={handleMouseMove}
        onClick={handleClick}
        onMouseLeave={handleMouseLeave}
        className="block"
      />
    </div>
  );
});
