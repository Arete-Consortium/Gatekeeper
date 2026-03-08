/**
 * Coordinate transforms between world space and screen space.
 */
import type { MapViewport } from '../components/map/types';

/** Convert world coordinates to screen coordinates. */
export function worldToScreen(
  wx: number,
  wy: number,
  viewport: MapViewport
): { sx: number; sy: number } {
  const sx =
    (wx - viewport.centerX) * viewport.zoom + viewport.screenWidth / 2;
  const sy =
    (wy - viewport.centerY) * viewport.zoom + viewport.screenHeight / 2;
  return { sx, sy };
}

/** Convert screen coordinates to world coordinates. */
export function screenToWorld(
  sx: number,
  sy: number,
  viewport: MapViewport
): { wx: number; wy: number } {
  const wx =
    (sx - viewport.screenWidth / 2) / viewport.zoom + viewport.centerX;
  const wy =
    (sy - viewport.screenHeight / 2) / viewport.zoom + viewport.centerY;
  return { wx, wy };
}

/** Get the visible world-space rectangle for the current viewport. */
export function getVisibleWorldRect(viewport: MapViewport): {
  minX: number;
  minY: number;
  maxX: number;
  maxY: number;
} {
  const halfW = viewport.screenWidth / 2 / viewport.zoom;
  const halfH = viewport.screenHeight / 2 / viewport.zoom;
  return {
    minX: viewport.centerX - halfW,
    minY: viewport.centerY - halfH,
    maxX: viewport.centerX + halfW,
    maxY: viewport.centerY + halfH,
  };
}
