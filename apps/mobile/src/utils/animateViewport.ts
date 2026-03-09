/**
 * Smooth viewport animation using requestAnimationFrame lerp.
 * Returns a cancel function to abort mid-flight.
 */
import type { MapViewport } from '../components/map/types';

const DURATION_MS = 400;

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

/** Ease-out cubic for deceleration feel */
function easeOut(t: number): number {
  return 1 - Math.pow(1 - t, 3);
}

export function animateViewport(
  setViewport: React.Dispatch<React.SetStateAction<MapViewport>>,
  target: { centerX: number; centerY: number; zoom: number },
  duration: number = DURATION_MS,
): () => void {
  let cancelled = false;
  let startTime: number | null = null;
  let startState: { centerX: number; centerY: number; zoom: number } | null = null;

  function step(timestamp: number) {
    if (cancelled) return;

    if (startTime === null) {
      startTime = timestamp;
      // Capture current state on first frame
      setViewport((prev) => {
        startState = { centerX: prev.centerX, centerY: prev.centerY, zoom: prev.zoom };
        return prev;
      });
      requestAnimationFrame(step);
      return;
    }

    if (!startState) {
      requestAnimationFrame(step);
      return;
    }

    const elapsed = timestamp - startTime;
    const rawT = Math.min(elapsed / duration, 1);
    const t = easeOut(rawT);

    setViewport((prev) => ({
      ...prev,
      centerX: lerp(startState!.centerX, target.centerX, t),
      centerY: lerp(startState!.centerY, target.centerY, t),
      zoom: lerp(startState!.zoom, target.zoom, t),
    }));

    if (rawT < 1) {
      requestAnimationFrame(step);
    }
  }

  requestAnimationFrame(step);

  return () => {
    cancelled = true;
  };
}
