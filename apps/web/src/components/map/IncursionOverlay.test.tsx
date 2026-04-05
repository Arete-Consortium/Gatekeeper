import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { IncursionOverlay } from './IncursionOverlay';
import type { MapSystem, MapViewport } from './types';
import type { Incursion } from '@/lib/types';

const VIEWPORT: MapViewport = {
  x: 0,
  y: 0,
  zoom: 1,
  width: 800,
  height: 600,
};

function makeSystem(overrides: Partial<MapSystem> & { systemId: number }): MapSystem {
  return {
    name: `System-${overrides.systemId}`,
    x: 0,
    y: 0,
    security: 0.5,
    regionId: 1,
    constellationId: 1,
    ...overrides,
  };
}

function makeSystemMap(...systems: MapSystem[]): Map<number, MapSystem> {
  const map = new Map<number, MapSystem>();
  for (const s of systems) map.set(s.systemId, s);
  return map;
}

const SYS_STAGING = makeSystem({ systemId: 30000001, x: 10, y: 10, name: 'StagingSystem' });
const SYS_INFESTED_A = makeSystem({ systemId: 30000002, x: 20, y: 20, name: 'InfestedA' });
const SYS_INFESTED_B = makeSystem({ systemId: 30000003, x: 30, y: 30, name: 'InfestedB' });
const SYSTEMS = makeSystemMap(SYS_STAGING, SYS_INFESTED_A, SYS_INFESTED_B);

const baseIncursion: Incursion = {
  type: 'Incursion',
  state: 'established',
  staging_system_id: 30000001,
  constellation_id: 20000001,
  infested_systems: [30000001, 30000002, 30000003],
  has_boss: false,
  influence: 0.75,
};

describe('IncursionOverlay', () => {
  it('renders nothing when incursions array is empty', () => {
    const { container } = render(
      <IncursionOverlay incursions={[]} systems={SYSTEMS} viewport={VIEWPORT} />
    );
    expect(container.querySelector('svg')).toBeNull();
  });

  it('renders SVG when there are active incursions', () => {
    const { container } = render(
      <IncursionOverlay incursions={[baseIncursion]} systems={SYSTEMS} viewport={VIEWPORT} />
    );
    expect(container.querySelector('svg')).toBeTruthy();
  });

  it('renders staging marker with "S" text', () => {
    const { container } = render(
      <IncursionOverlay incursions={[baseIncursion]} systems={SYSTEMS} viewport={VIEWPORT} />
    );
    const texts = container.querySelectorAll('text');
    const sTexts = Array.from(texts).filter((t) => t.textContent === 'S');
    expect(sTexts.length).toBe(1);
  });

  it('renders infested markers as diamonds (rects)', () => {
    const { container } = render(
      <IncursionOverlay incursions={[baseIncursion]} systems={SYSTEMS} viewport={VIEWPORT} />
    );
    // 2 infested systems (staging excluded from infested markers)
    const rects = container.querySelectorAll('rect');
    expect(rects.length).toBe(2);
  });

  it('shows state label at zoom > 0.6', () => {
    const zoomedViewport = { ...VIEWPORT, zoom: 1 };
    const { container } = render(
      <IncursionOverlay incursions={[baseIncursion]} systems={SYSTEMS} viewport={zoomedViewport} />
    );
    const texts = Array.from(container.querySelectorAll('text'));
    const stateText = texts.find((t) => t.textContent === 'Established');
    expect(stateText).toBeTruthy();
  });

  it('hides state label at low zoom', () => {
    const lowZoom = { ...VIEWPORT, zoom: 0.3 };
    const { container } = render(
      <IncursionOverlay incursions={[baseIncursion]} systems={SYSTEMS} viewport={lowZoom} />
    );
    const texts = Array.from(container.querySelectorAll('text'));
    const stateText = texts.find((t) => t.textContent === 'Established');
    expect(stateText).toBeUndefined();
  });

  it('shows BOSS label when has_boss is true', () => {
    const bossIncursion = { ...baseIncursion, has_boss: true };
    const { container } = render(
      <IncursionOverlay incursions={[bossIncursion]} systems={SYSTEMS} viewport={VIEWPORT} />
    );
    const texts = Array.from(container.querySelectorAll('text'));
    const bossText = texts.find((t) => t.textContent?.includes('BOSS'));
    expect(bossText).toBeTruthy();
  });

  it('shows influence percentage', () => {
    const { container } = render(
      <IncursionOverlay incursions={[baseIncursion]} systems={SYSTEMS} viewport={VIEWPORT} />
    );
    const texts = Array.from(container.querySelectorAll('text'));
    const influenceText = texts.find((t) => t.textContent?.includes('75%'));
    expect(influenceText).toBeTruthy();
  });

  it('uses red color for established state', () => {
    const { container } = render(
      <IncursionOverlay incursions={[baseIncursion]} systems={SYSTEMS} viewport={VIEWPORT} />
    );
    // The inner filled circle of the staging marker should be red
    const circles = container.querySelectorAll('circle');
    const filledCircles = Array.from(circles).filter((c) => c.getAttribute('fill') === '#ef4444');
    expect(filledCircles.length).toBeGreaterThan(0);
  });

  it('uses orange color for mobilizing state', () => {
    const mobIncursion = { ...baseIncursion, state: 'mobilizing' };
    const { container } = render(
      <IncursionOverlay incursions={[mobIncursion]} systems={SYSTEMS} viewport={VIEWPORT} />
    );
    const circles = container.querySelectorAll('circle');
    const orangeCircles = Array.from(circles).filter((c) => c.getAttribute('fill') === '#f97316');
    expect(orangeCircles.length).toBeGreaterThan(0);
  });

  it('uses yellow color for withdrawing state', () => {
    const wdIncursion = { ...baseIncursion, state: 'withdrawing' };
    const { container } = render(
      <IncursionOverlay incursions={[wdIncursion]} systems={SYSTEMS} viewport={VIEWPORT} />
    );
    const circles = container.querySelectorAll('circle');
    const yellowCircles = Array.from(circles).filter((c) => c.getAttribute('fill') === '#eab308');
    expect(yellowCircles.length).toBeGreaterThan(0);
  });

  it('culls off-screen markers', () => {
    const farSystem = makeSystem({ systemId: 99999, x: 5000, y: 5000 });
    const farMap = makeSystemMap(farSystem);
    const farIncursion = {
      ...baseIncursion,
      staging_system_id: 99999,
      infested_systems: [99999],
    };
    const { container } = render(
      <IncursionOverlay incursions={[farIncursion]} systems={farMap} viewport={VIEWPORT} />
    );
    expect(container.querySelector('svg')).toBeNull();
  });

  it('handles incursion with unknown staging system gracefully', () => {
    const noStagingIncursion = {
      ...baseIncursion,
      staging_system_id: 99999, // not in system map
    };
    const { container } = render(
      <IncursionOverlay incursions={[noStagingIncursion]} systems={SYSTEMS} viewport={VIEWPORT} />
    );
    // Should still render infested markers — all 3 infested systems since staging (99999) doesn't match any
    const rects = container.querySelectorAll('rect');
    expect(rects.length).toBe(3);
  });
});
