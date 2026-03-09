import { animateViewport } from '../utils/animateViewport';
import type { MapViewport } from '../components/map/types';

// Mock requestAnimationFrame for synchronous testing
let rafCallbacks: ((ts: number) => void)[] = [];
let rafId = 0;

beforeEach(() => {
  rafCallbacks = [];
  rafId = 0;
  jest.spyOn(global, 'requestAnimationFrame').mockImplementation((cb) => {
    rafCallbacks.push(cb);
    return ++rafId;
  });
  jest.spyOn(global, 'cancelAnimationFrame').mockImplementation(() => {});
});

afterEach(() => {
  jest.restoreAllMocks();
});

function flushFrames(timestamps: number[]) {
  for (const ts of timestamps) {
    const cbs = [...rafCallbacks];
    rafCallbacks = [];
    for (const cb of cbs) cb(ts);
  }
}

describe('animateViewport', () => {
  it('transitions viewport to target over time', () => {
    let viewport: MapViewport = {
      centerX: 0,
      centerY: 0,
      zoom: 1,
      screenWidth: 400,
      screenHeight: 800,
    };

    const setViewport = jest.fn((updater: any) => {
      if (typeof updater === 'function') {
        viewport = updater(viewport);
      }
    });

    animateViewport(setViewport, { centerX: 100, centerY: 200, zoom: 3 }, 400);

    // Frame 1: captures start state
    flushFrames([0]);
    // Frame 2: t=0, should still be at start
    flushFrames([0]);
    // Frame 3: t=1 (full duration), should be at target
    flushFrames([400]);

    expect(viewport.centerX).toBeCloseTo(100, 0);
    expect(viewport.centerY).toBeCloseTo(200, 0);
    expect(viewport.zoom).toBeCloseTo(3, 0);
  });

  it('can be cancelled mid-animation', () => {
    let viewport: MapViewport = {
      centerX: 0,
      centerY: 0,
      zoom: 1,
      screenWidth: 400,
      screenHeight: 800,
    };

    const setViewport = jest.fn((updater: any) => {
      if (typeof updater === 'function') {
        viewport = updater(viewport);
      }
    });

    const cancel = animateViewport(setViewport, { centerX: 100, centerY: 200, zoom: 3 }, 400);

    flushFrames([0]); // capture start
    cancel();
    flushFrames([200]); // mid-animation frame — should be ignored

    // Should still be at start since we cancelled before any real update
    expect(viewport.centerX).toBe(0);
    expect(viewport.centerY).toBe(0);
  });

  it('reaches target at midpoint with easing', () => {
    let viewport: MapViewport = {
      centerX: 0,
      centerY: 0,
      zoom: 1,
      screenWidth: 400,
      screenHeight: 800,
    };

    const setViewport = jest.fn((updater: any) => {
      if (typeof updater === 'function') {
        viewport = updater(viewport);
      }
    });

    animateViewport(setViewport, { centerX: 100, centerY: 0, zoom: 1 }, 400);

    flushFrames([0]); // capture start
    flushFrames([0]); // first real frame, start state captured
    flushFrames([200]); // halfway

    // With ease-out cubic, t=0.5 → 1-(0.5)^3 = 0.875
    expect(viewport.centerX).toBeCloseTo(87.5, 0);
  });
});
