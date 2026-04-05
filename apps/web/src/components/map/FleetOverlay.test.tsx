import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { FleetOverlay } from './FleetOverlay';
import type { MapSystem, MapViewport } from './types';
import type { FleetMember } from '@/lib/types';

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

const SYS_JITA = makeSystem({ systemId: 30000142, x: 10, y: 10, name: 'Jita' });
const SYS_AMARR = makeSystem({ systemId: 30002187, x: 50, y: 50, name: 'Amarr' });
const SYSTEMS = makeSystemMap(SYS_JITA, SYS_AMARR);

const baseMember: FleetMember = {
  character_id: 1001,
  character_name: 'Fleet Pilot One',
  system_id: 30000142,
  system_name: 'Jita',
  ship_type_id: 587,
  ship_type_name: 'Rifter',
  online: true,
  last_updated: '2026-01-01T00:00:00Z',
};

describe('FleetOverlay', () => {
  it('renders nothing when members array is empty', () => {
    const { container } = render(
      <FleetOverlay members={[]} systems={SYSTEMS} viewport={VIEWPORT} />
    );
    expect(container.querySelector('svg')).toBeNull();
  });

  it('renders nothing when all members lack system_id', () => {
    const members: FleetMember[] = [
      { ...baseMember, system_id: null },
    ];
    const { container } = render(
      <FleetOverlay members={members} systems={SYSTEMS} viewport={VIEWPORT} />
    );
    expect(container.querySelector('svg')).toBeNull();
  });

  it('renders markers for members with valid locations', () => {
    const members: FleetMember[] = [
      baseMember,
      { ...baseMember, character_id: 1002, character_name: 'Fleet Pilot Two', system_id: 30002187 },
    ];
    const { container } = render(
      <FleetOverlay members={members} systems={SYSTEMS} viewport={VIEWPORT} />
    );
    const svg = container.querySelector('svg');
    expect(svg).toBeTruthy();
    // Each member: outer circle + solid dot + hover circle = 3 circles per member
    const circles = svg!.querySelectorAll('circle');
    expect(circles.length).toBe(6); // 2 members * 3 circles each
  });

  it('skips current character when currentCharacterId is set', () => {
    const members: FleetMember[] = [
      baseMember,
      { ...baseMember, character_id: 1002, character_name: 'Fleet Pilot Two', system_id: 30002187 },
    ];
    const { container } = render(
      <FleetOverlay
        members={members}
        systems={SYSTEMS}
        viewport={VIEWPORT}
        currentCharacterId={1001}
      />
    );
    const svg = container.querySelector('svg');
    expect(svg).toBeTruthy();
    // Only 1 member rendered (the non-self one)
    const circles = svg!.querySelectorAll('circle');
    expect(circles.length).toBe(3);
  });

  it('culls off-screen markers', () => {
    // System at position that would be off-screen
    const farSystem = makeSystem({ systemId: 99999, x: 5000, y: 5000 });
    const farMap = makeSystemMap(farSystem);
    const members: FleetMember[] = [
      { ...baseMember, system_id: 99999 },
    ];
    const { container } = render(
      <FleetOverlay members={members} systems={farMap} viewport={VIEWPORT} />
    );
    // Should be culled since system is way off-screen
    expect(container.querySelector('svg')).toBeNull();
  });

  it('shows labels at zoom > 1', () => {
    const zoomedViewport = { ...VIEWPORT, zoom: 2 };
    const members: FleetMember[] = [baseMember];
    const { container } = render(
      <FleetOverlay members={members} systems={SYSTEMS} viewport={zoomedViewport} />
    );
    const text = container.querySelector('text');
    expect(text).toBeTruthy();
    expect(text!.textContent).toBe('Fleet Pilot One');
  });

  it('hides labels at zoom <= 1', () => {
    const members: FleetMember[] = [baseMember];
    const { container } = render(
      <FleetOverlay members={members} systems={SYSTEMS} viewport={VIEWPORT} />
    );
    const text = container.querySelector('text');
    expect(text).toBeNull();
  });

  it('includes ship name in tooltip title', () => {
    const members: FleetMember[] = [baseMember];
    const { container } = render(
      <FleetOverlay members={members} systems={SYSTEMS} viewport={VIEWPORT} />
    );
    const title = container.querySelector('title');
    expect(title).toBeTruthy();
    expect(title!.textContent).toContain('Fleet Pilot One');
    expect(title!.textContent).toContain('Rifter');
  });
});
