'use client';

import { useRef, useEffect, useCallback, useState, memo } from 'react';
import type { RouteHop } from '@/lib/types';

interface RouteStripProps {
  hops: RouteHop[];
  /** Optional: index of currently hovered hop (from table) */
  hoveredIndex?: number | null;
  onHopHover?: (index: number | null) => void;
  onHopClick?: (index: number) => void;
}

// Security → node color
function getSecColor(sec: number): string {
  if (sec >= 0.9) return '#2fff2f';
  if (sec >= 0.7) return '#00cc00';
  if (sec >= 0.5) return '#339933';
  if (sec >= 0.4) return '#cccc00';
  if (sec >= 0.2) return '#cc6600';
  if (sec >= 0.1) return '#cc0000';
  return '#aa0000';
}

// Risk → line segment color
function getRiskSegColor(risk: number): string {
  if (risk < 25) return '#22c55e';
  if (risk < 50) return '#eab308';
  if (risk < 75) return '#f97316';
  return '#ef4444';
}

// Risk → glow intensity
function getRiskGlow(risk: number): number {
  if (risk < 25) return 0;
  if (risk < 50) return 4;
  if (risk < 75) return 8;
  return 12;
}

const NODE_RADIUS = 8;
const NODE_SPACING = 56; // px between nodes
const STRIP_HEIGHT = 80;
const LABEL_OFFSET = 22;

/**
 * RouteStrip — subway-line style route visualization
 * Horizontal scrollable strip showing each hop as a connected node
 */
export const RouteStrip = memo(function RouteStrip({
  hops,
  hoveredIndex,
  onHopHover,
  onHopClick,
}: RouteStripProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [localHover, setLocalHover] = useState<number | null>(null);
  const activeHover = hoveredIndex ?? localHover;

  const totalWidth = Math.max(300, hops.length * NODE_SPACING + 80);

  // Get node X position
  const nodeX = useCallback(
    (i: number) => 40 + i * NODE_SPACING,
    []
  );

  const nodeY = STRIP_HEIGHT / 2;

  // Draw canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || hops.length === 0) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = totalWidth * dpr;
    canvas.height = STRIP_HEIGHT * dpr;
    canvas.style.width = `${totalWidth}px`;
    canvas.style.height = `${STRIP_HEIGHT}px`;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.scale(dpr, dpr);

    // Clear
    ctx.clearRect(0, 0, totalWidth, STRIP_HEIGHT);

    // Draw line segments (risk-colored)
    for (let i = 0; i < hops.length - 1; i++) {
      const x1 = nodeX(i);
      const x2 = nodeX(i + 1);
      const nextRisk = hops[i + 1].risk_score;
      const segColor = getRiskSegColor(nextRisk);
      const glow = getRiskGlow(nextRisk);

      ctx.save();
      if (glow > 0) {
        ctx.shadowColor = segColor;
        ctx.shadowBlur = glow;
      }
      ctx.strokeStyle = segColor;
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.moveTo(x1, nodeY);
      ctx.lineTo(x2, nodeY);
      ctx.stroke();
      ctx.restore();
    }

    // Draw nodes
    for (let i = 0; i < hops.length; i++) {
      const hop = hops[i];
      const x = nodeX(i);
      const isHovered = activeHover === i;
      const isEndpoint = i === 0 || i === hops.length - 1;
      const r = isHovered ? NODE_RADIUS + 2 : NODE_RADIUS;
      const secColor = getSecColor(hop.security_status);

      ctx.save();

      // Endpoint ring
      if (isEndpoint) {
        ctx.beginPath();
        ctx.arc(x, nodeY, r + 4, 0, Math.PI * 2);
        ctx.strokeStyle = i === 0 ? '#33cc55' : '#ee4444';
        ctx.lineWidth = 2;
        ctx.stroke();
      }

      // Hover glow
      if (isHovered) {
        ctx.shadowColor = secColor;
        ctx.shadowBlur = 10;
      }

      // Node fill
      ctx.beginPath();
      ctx.arc(x, nodeY, r, 0, Math.PI * 2);
      ctx.fillStyle = secColor;
      ctx.fill();

      // Inner dot for readability
      ctx.beginPath();
      ctx.arc(x, nodeY, r * 0.35, 0, Math.PI * 2);
      ctx.fillStyle = '#0a0e17';
      ctx.fill();

      ctx.restore();

      // Labels — show for endpoints, hovered, and every Nth
      const showLabel =
        isEndpoint ||
        isHovered ||
        (hops.length <= 20) ||
        (hops.length <= 40 && i % 2 === 0) ||
        (hops.length > 40 && i % Math.ceil(hops.length / 20) === 0);

      if (showLabel) {
        ctx.save();
        const fontSize = isEndpoint || isHovered ? 11 : 9;
        ctx.font = `${isEndpoint ? 'bold ' : ''}${fontSize}px system-ui, -apple-system, sans-serif`;
        ctx.textAlign = 'center';

        // Alternate labels above/below to avoid overlap
        const above = i % 2 === 0;
        const ly = above ? nodeY - LABEL_OFFSET : nodeY + LABEL_OFFSET + fontSize;

        // Security status text
        const secText = hop.security_status.toFixed(1);
        ctx.fillStyle = isHovered ? '#ffffff' : '#64748b';
        const secY = above ? ly - fontSize - 1 : ly + fontSize + 1;
        ctx.fillText(secText, x, secY);

        // System name
        ctx.fillStyle = isEndpoint || isHovered ? '#ffffff' : '#94a3b8';
        ctx.fillText(hop.system_name, x, ly);

        ctx.restore();
      }
    }
  }, [hops, activeHover, totalWidth, nodeX]);

  // Hit test
  const getHopAtPosition = useCallback(
    (clientX: number): number | null => {
      const canvas = canvasRef.current;
      const scroll = scrollRef.current;
      if (!canvas || !scroll) return null;

      const rect = canvas.getBoundingClientRect();
      const x = clientX - rect.left;
      const hitR = NODE_RADIUS + 10;

      for (let i = 0; i < hops.length; i++) {
        const nx = nodeX(i);
        if (Math.abs(x - nx) <= hitR && Math.abs(nodeY - STRIP_HEIGHT / 2) <= hitR) {
          return i;
        }
      }
      return null;
    },
    [hops.length, nodeX]
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      const idx = getHopAtPosition(e.clientX);
      setLocalHover(idx);
      onHopHover?.(idx);
      const canvas = canvasRef.current;
      if (canvas) canvas.style.cursor = idx !== null ? 'pointer' : 'default';
    },
    [getHopAtPosition, onHopHover]
  );

  const handleClick = useCallback(
    (e: React.MouseEvent) => {
      const idx = getHopAtPosition(e.clientX);
      if (idx !== null) onHopClick?.(idx);
    },
    [getHopAtPosition, onHopClick]
  );

  const handleMouseLeave = useCallback(() => {
    setLocalHover(null);
    onHopHover?.(null);
  }, [onHopHover]);

  if (hops.length === 0) return null;

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
