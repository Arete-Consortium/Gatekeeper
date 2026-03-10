'use client';

import { useRef, useEffect, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { GatekeeperAPI } from '@/lib/api';
import type { RouteResponse, MapConfig, MapConfigSystem, Gate } from '@/lib/types';
import { Loader2 } from 'lucide-react';

interface RouteMapProps {
  route: RouteResponse;
}

const PADDING = 60;
const NEARBY_RADIUS = 12; // map units around route bounding box

function getSecColor(sec: number): string {
  if (sec >= 0.9) return '#2fff2f';
  if (sec >= 0.7) return '#00cc00';
  if (sec >= 0.5) return '#339933';
  if (sec >= 0.4) return '#cccc00';
  if (sec >= 0.2) return '#cc6600';
  if (sec >= 0.1) return '#cc0000';
  return '#aa0000';
}

export function RouteMap({ route }: RouteMapProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const { data: mapConfig, isLoading } = useQuery<MapConfig>({
    queryKey: ['mapConfig'],
    queryFn: () => GatekeeperAPI.getMapConfig(),
    staleTime: 5 * 60 * 1000,
  });

  // Compute bounding box, route systems, nearby systems, and relevant gates
  const mapData = useMemo(() => {
    if (!mapConfig || route.path.length === 0) return null;

    const systems = mapConfig.systems;
    const routeNames = route.path.map((h) => h.system_name);
    const routeSet = new Set(routeNames);

    // Get positions of route systems
    const routePositions: { name: string; x: number; y: number; sec: number }[] = [];
    for (const name of routeNames) {
      const sys = systems[name];
      if (sys) {
        routePositions.push({ name, x: sys.position.x, y: sys.position.y, sec: sys.security });
      }
    }
    if (routePositions.length < 2) return null;

    // Bounding box of route
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    for (const p of routePositions) {
      minX = Math.min(minX, p.x);
      maxX = Math.max(maxX, p.x);
      minY = Math.min(minY, p.y);
      maxY = Math.max(maxY, p.y);
    }

    // Expand bounds for context
    minX -= NEARBY_RADIUS;
    maxX += NEARBY_RADIUS;
    minY -= NEARBY_RADIUS;
    maxY += NEARBY_RADIUS;

    // Find all systems within bounds
    const visibleSystems: { name: string; x: number; y: number; sec: number; onRoute: boolean }[] = [];
    for (const [name, sys] of Object.entries(systems)) {
      const { x, y } = sys.position;
      if (x >= minX && x <= maxX && y >= minY && y <= maxY) {
        visibleSystems.push({ name, x, y, sec: sys.security, onRoute: routeSet.has(name) });
      }
    }

    // Find gates between visible systems
    const visibleNames = new Set(visibleSystems.map((s) => s.name));
    const visibleGates: Gate[] = mapConfig.gates.filter(
      (g) => visibleNames.has(g.from_system) && visibleNames.has(g.to_system)
    );

    return { routePositions, visibleSystems, visibleGates, bounds: { minX, maxX, minY, maxY } };
  }, [mapConfig, route]);

  // Draw
  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container || !mapData) return;

    const rect = container.getBoundingClientRect();
    const w = rect.width;
    const h = Math.min(400, Math.max(250, w * 0.5));
    const dpr = window.devicePixelRatio || 1;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    canvas.style.width = `${w}px`;
    canvas.style.height = `${h}px`;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.scale(dpr, dpr);

    const { routePositions, visibleSystems, visibleGates, bounds } = mapData;
    const { minX, maxX, minY, maxY } = bounds;

    // Transform: map coords → canvas coords
    const mapW = maxX - minX || 1;
    const mapH = maxY - minY || 1;
    const scaleX = (w - PADDING * 2) / mapW;
    const scaleY = (h - PADDING * 2) / mapH;
    const scale = Math.min(scaleX, scaleY);
    const offsetX = (w - mapW * scale) / 2;
    const offsetY = (h - mapH * scale) / 2;

    const toScreen = (mx: number, my: number): [number, number] => [
      (mx - minX) * scale + offsetX,
      (my - minY) * scale + offsetY,
    ];

    // Background
    ctx.fillStyle = '#0a0e17';
    ctx.fillRect(0, 0, w, h);

    // Draw gates (background connections)
    ctx.lineWidth = 0.5;
    const sysLookup = new Map(visibleSystems.map((s) => [s.name, s]));
    for (const gate of visibleGates) {
      const from = sysLookup.get(gate.from_system);
      const to = sysLookup.get(gate.to_system);
      if (!from || !to) continue;

      const [x1, y1] = toScreen(from.x, from.y);
      const [x2, y2] = toScreen(to.x, to.y);

      // Dim color for non-route gates
      const minSec = Math.min(from.sec, to.sec);
      if (minSec >= 0.5) ctx.strokeStyle = 'rgba(60, 90, 60, 0.4)';
      else if (minSec > 0) ctx.strokeStyle = 'rgba(120, 90, 30, 0.4)';
      else ctx.strokeStyle = 'rgba(100, 30, 30, 0.4)';

      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.stroke();
    }

    // Draw non-route systems (small dots)
    for (const sys of visibleSystems) {
      if (sys.onRoute) continue;
      const [sx, sy] = toScreen(sys.x, sys.y);
      ctx.fillStyle = getSecColor(sys.sec);
      ctx.globalAlpha = 0.35;
      ctx.beginPath();
      ctx.arc(sx, sy, 2, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.globalAlpha = 1;

    // Draw route path (thick highlighted line)
    if (routePositions.length >= 2) {
      ctx.lineWidth = 3;
      ctx.strokeStyle = '#4488ff';
      ctx.shadowColor = '#4488ff';
      ctx.shadowBlur = 6;
      ctx.beginPath();
      const [startX, startY] = toScreen(routePositions[0].x, routePositions[0].y);
      ctx.moveTo(startX, startY);
      for (let i = 1; i < routePositions.length; i++) {
        const [px, py] = toScreen(routePositions[i].x, routePositions[i].y);
        ctx.lineTo(px, py);
      }
      ctx.stroke();
      ctx.shadowBlur = 0;
    }

    // Draw route systems (larger dots with labels)
    const labelFontSize = Math.max(9, Math.min(12, scale * 1.5));
    ctx.font = `${labelFontSize}px -apple-system, BlinkMacSystemFont, sans-serif`;
    ctx.textBaseline = 'middle';

    for (let i = 0; i < routePositions.length; i++) {
      const sys = routePositions[i];
      const [sx, sy] = toScreen(sys.x, sys.y);
      const isEndpoint = i === 0 || i === routePositions.length - 1;
      const radius = isEndpoint ? 5 : 3.5;

      // System dot
      ctx.fillStyle = isEndpoint ? '#ffffff' : getSecColor(sys.sec);
      ctx.beginPath();
      ctx.arc(sx, sy, radius, 0, Math.PI * 2);
      ctx.fill();

      // Endpoint ring
      if (isEndpoint) {
        ctx.strokeStyle = i === 0 ? '#33cc55' : '#ee4444';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(sx, sy, radius + 3, 0, Math.PI * 2);
        ctx.stroke();
      }

      // Label (show for endpoints and every Nth system)
      const showLabel = isEndpoint || routePositions.length <= 15 || i % Math.ceil(routePositions.length / 12) === 0;
      if (showLabel) {
        const label = sys.name;
        const metrics = ctx.measureText(label);
        const lx = sx + radius + 5;
        const ly = sy;

        // Background
        ctx.fillStyle = 'rgba(10, 14, 23, 0.85)';
        ctx.fillRect(lx - 2, ly - labelFontSize / 2 - 1, metrics.width + 4, labelFontSize + 2);

        // Text
        ctx.fillStyle = isEndpoint ? '#ffffff' : '#aabbcc';
        ctx.fillText(label, lx, ly);
      }
    }

    // Region labels for context
    const regionPositions = new Map<string, { x: number; y: number; count: number }>();
    for (const sys of visibleSystems) {
      const sysData = mapConfig?.systems[sys.name];
      if (!sysData) continue;
      const region = sysData.region_name;
      const existing = regionPositions.get(region);
      if (existing) {
        existing.x += sys.x;
        existing.y += sys.y;
        existing.count++;
      } else {
        regionPositions.set(region, { x: sys.x, y: sys.y, count: 1 });
      }
    }

    ctx.font = `bold ${Math.max(10, labelFontSize + 1)}px -apple-system, BlinkMacSystemFont, sans-serif`;
    ctx.fillStyle = 'rgba(255, 255, 255, 0.12)';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    for (const [name, pos] of regionPositions) {
      if (pos.count < 3) continue; // Only label regions with enough visible systems
      const [rx, ry] = toScreen(pos.x / pos.count, pos.y / pos.count);
      ctx.fillText(name, rx, ry);
    }
    ctx.textAlign = 'start';

  }, [mapData, mapConfig]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8 bg-[#0a0e17] rounded-lg border border-border">
        <Loader2 className="h-5 w-5 animate-spin text-text-secondary" />
      </div>
    );
  }

  if (!mapData) return null;

  return (
    <div ref={containerRef} className="rounded-lg overflow-hidden border border-border">
      <canvas ref={canvasRef} className="w-full block" />
    </div>
  );
}
