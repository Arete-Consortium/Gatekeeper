import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { PirateInsurgencyOverlay } from './PirateInsurgencyOverlay';
import type { MapSystem, MapViewport } from './types';
import type { PirateOccupiedSystem } from '@/lib/types';

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

const SYS_A = makeSystem({ systemId: 30000001, x: 10, y: 10, name: 'TestSystem' });
const SYS_B = makeSystem({ systemId: 30000002, x: 20, y: 20, name: 'TestSystem2' });
const SYSTEMS = makeSystemMap(SYS_A, SYS_B);

const guristasSystem: PirateOccupiedSystem = {
  system_id: 30000001,
  system_name: 'TestSystem',
  occupier_faction_id: 500010,
  faction_name: 'Guristas Pirates',
};

const angelSystem: PirateOccupiedSystem = {
  system_id: 30000002,
  system_name: 'TestSystem2',
  occupier_faction_id: 500011,
  faction_name: 'Angel Cartel',
};

describe('PirateInsurgencyOverlay', () => {
  it('renders nothing when pirateOccupied array is empty', () => {
    const { container } = render(
      <PirateInsurgencyOverlay pirateOccupied={[]} systems={SYSTEMS} viewport={VIEWPORT} />
    );
    expect(container.querySelector('svg')).toBeNull();
  });

  it('renders SVG when there are pirate-occupied systems', () => {
    const { container } = render(
      <PirateInsurgencyOverlay pirateOccupied={[guristasSystem]} systems={SYSTEMS} viewport={VIEWPORT} />
    );
    expect(container.querySelector('svg')).toBeTruthy();
  });

  it('renders dashed rings for pirate systems', () => {
    const { container } = render(
      <PirateInsurgencyOverlay pirateOccupied={[guristasSystem]} systems={SYSTEMS} viewport={VIEWPORT} />
    );
    const circles = container.querySelectorAll('circle');
    const dashedCircles = Array.from(circles).filter(
      (c) => c.getAttribute('stroke-dasharray') !== null
    );
    // Should have at least outer pulsing dashed ring + inner steady dashed ring
    expect(dashedCircles.length).toBeGreaterThanOrEqual(2);
  });

  it('shows SUPPRESSED label at zoom > 0.6', () => {
    const { container } = render(
      <PirateInsurgencyOverlay pirateOccupied={[guristasSystem]} systems={SYSTEMS} viewport={VIEWPORT} />
    );
    const texts = Array.from(container.querySelectorAll('text'));
    const suppressed = texts.find((t) => t.textContent === 'SUPPRESSED');
    expect(suppressed).toBeTruthy();
  });

  it('hides SUPPRESSED label at low zoom', () => {
    const lowZoom = { ...VIEWPORT, zoom: 0.3 };
    const { container } = render(
      <PirateInsurgencyOverlay pirateOccupied={[guristasSystem]} systems={SYSTEMS} viewport={lowZoom} />
    );
    const texts = Array.from(container.querySelectorAll('text'));
    const suppressed = texts.find((t) => t.textContent === 'SUPPRESSED');
    expect(suppressed).toBeUndefined();
  });

  it('shows faction name at zoom > 1.2', () => {
    const highZoom = { ...VIEWPORT, zoom: 1.5 };
    const { container } = render(
      <PirateInsurgencyOverlay pirateOccupied={[guristasSystem]} systems={SYSTEMS} viewport={highZoom} />
    );
    const texts = Array.from(container.querySelectorAll('text'));
    const factionText = texts.find((t) => t.textContent === 'Guristas Pirates');
    expect(factionText).toBeTruthy();
  });

  it('hides faction name at zoom <= 1.2', () => {
    const { container } = render(
      <PirateInsurgencyOverlay pirateOccupied={[guristasSystem]} systems={SYSTEMS} viewport={VIEWPORT} />
    );
    const texts = Array.from(container.querySelectorAll('text'));
    const factionText = texts.find((t) => t.textContent === 'Guristas Pirates');
    expect(factionText).toBeUndefined();
  });

  it('renders markers for multiple pirate systems', () => {
    const { container } = render(
      <PirateInsurgencyOverlay
        pirateOccupied={[guristasSystem, angelSystem]}
        systems={SYSTEMS}
        viewport={VIEWPORT}
      />
    );
    const groups = container.querySelectorAll('g');
    // Each marker is a <g>, should have at least 2
    expect(groups.length).toBeGreaterThanOrEqual(2);
  });

  it('culls off-screen markers', () => {
    const farSystem = makeSystem({ systemId: 99999, x: 5000, y: 5000 });
    const farMap = makeSystemMap(farSystem);
    const farPirate: PirateOccupiedSystem = {
      system_id: 99999,
      system_name: 'FarSystem',
      occupier_faction_id: 500010,
      faction_name: 'Guristas Pirates',
    };
    const { container } = render(
      <PirateInsurgencyOverlay pirateOccupied={[farPirate]} systems={farMap} viewport={VIEWPORT} />
    );
    expect(container.querySelector('svg')).toBeNull();
  });

  it('skips systems not in the system map', () => {
    const unknownPirate: PirateOccupiedSystem = {
      system_id: 88888,
      system_name: 'UnknownSystem',
      occupier_faction_id: 500011,
      faction_name: 'Angel Cartel',
    };
    const { container } = render(
      <PirateInsurgencyOverlay pirateOccupied={[unknownPirate]} systems={SYSTEMS} viewport={VIEWPORT} />
    );
    expect(container.querySelector('svg')).toBeNull();
  });
});
