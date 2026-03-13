import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SovereigntyOverlay } from './SovereigntyOverlay';
import { TheraOverlay } from './TheraOverlay';
import { FWOverlay } from './FWOverlay';
import { LandmarksOverlay } from './LandmarksOverlay';
import { SovStructuresOverlay } from './SovStructuresOverlay';
import { MarketHubsOverlay } from './MarketHubsOverlay';
import type { MapSystem, MapViewport } from './types';
import type { TheraConnection, FWSystem, SovStructure, Landmark, MarketHub } from '@/lib/types';

// === Shared Fixtures ===

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

const SYSTEM_A = makeSystem({ systemId: 100, x: 10, y: 10 });
const SYSTEM_B = makeSystem({ systemId: 200, x: 50, y: 50 });
const SYSTEMS = makeSystemMap(SYSTEM_A, SYSTEM_B);

// === SovereigntyOverlay ===

describe('SovereigntyOverlay', () => {
  const defaultProps = {
    sovereignty: {},
    alliances: {},
    systems: SYSTEMS,
    viewport: VIEWPORT,
    factions: {},
  };

  it('renders nothing when no sovereignty data', () => {
    const { container } = render(<SovereigntyOverlay {...defaultProps} />);
    expect(container.querySelector('svg')).toBeNull();
  });

  it('renders nothing for NPC-only sovereignty (no alliance_id)', () => {
    const { container } = render(
      <SovereigntyOverlay
        {...defaultProps}
        sovereignty={{ '100': { alliance_id: null, faction_id: 500001 } }}
      />
    );
    expect(container.querySelector('svg')).toBeNull();
  });

  it('renders sovereignty ring for alliance-held system', () => {
    const { container } = render(
      <SovereigntyOverlay
        {...defaultProps}
        sovereignty={{ '100': { alliance_id: 99000001, faction_id: null } }}
        alliances={{ '99000001': { name: 'Test Alliance' } }}
      />
    );
    const svg = container.querySelector('svg');
    expect(svg).toBeTruthy();
    const circles = svg!.querySelectorAll('circle');
    expect(circles.length).toBe(1);
    expect(circles[0]).toHaveAttribute('fill', 'none');
    expect(circles[0]).toHaveAttribute('stroke');
  });

  it('skips systems not in system map', () => {
    const { container } = render(
      <SovereigntyOverlay
        {...defaultProps}
        sovereignty={{ '999': { alliance_id: 1, faction_id: null } }}
        alliances={{ '1': { name: 'Missing' } }}
      />
    );
    expect(container.querySelector('svg')).toBeNull();
  });

  it('skips systems outside viewport', () => {
    const farSystem = makeSystem({ systemId: 300, x: 5000, y: 5000 });
    const { container } = render(
      <SovereigntyOverlay
        {...defaultProps}
        systems={makeSystemMap(farSystem)}
        sovereignty={{ '300': { alliance_id: 1, faction_id: null } }}
        alliances={{ '1': { name: 'Far' } }}
      />
    );
    expect(container.querySelector('svg')).toBeNull();
  });
});

// === TheraOverlay ===

describe('TheraOverlay', () => {
  const makeConnection = (overrides: Partial<TheraConnection> = {}): TheraConnection => ({
    id: 1,
    system_id: 100,
    system_name: 'Jita',
    region_name: 'The Forge',
    wh_type: 'Q003',
    max_ship_size: 'medium',
    remaining_hours: 12,
    signature_id: 'ABC-123',
    completed: true,
    ...overrides,
  });

  it('renders nothing with empty connections', () => {
    const { container } = render(
      <TheraOverlay connections={[]} systems={SYSTEMS} viewport={VIEWPORT} />
    );
    expect(container.querySelector('svg')).toBeNull();
  });

  it('renders nothing for incomplete connections', () => {
    const { container } = render(
      <TheraOverlay
        connections={[makeConnection({ completed: false })]}
        systems={SYSTEMS}
        viewport={VIEWPORT}
      />
    );
    expect(container.querySelector('svg')).toBeNull();
  });

  it('renders marker for valid connection', () => {
    const { container } = render(
      <TheraOverlay
        connections={[makeConnection()]}
        systems={SYSTEMS}
        viewport={VIEWPORT}
      />
    );
    const svg = container.querySelector('svg');
    expect(svg).toBeTruthy();
    // Pulsing ring + inner dot = 2 circles, "T" text + label text
    const circles = svg!.querySelectorAll('circle');
    expect(circles.length).toBe(2);
  });

  it('shows Thera label at sufficient zoom', () => {
    const { container } = render(
      <TheraOverlay
        connections={[makeConnection({ remaining_hours: 8 })]}
        systems={SYSTEMS}
        viewport={{ ...VIEWPORT, zoom: 2 }}
      />
    );
    const texts = container.querySelectorAll('text');
    // "T" marker + "Thera (8h)" label
    expect(texts.length).toBe(2);
    expect(texts[1]!.textContent).toContain('Thera');
    expect(texts[1]!.textContent).toContain('8h');
  });

  it('hides label at low zoom', () => {
    const { container } = render(
      <TheraOverlay
        connections={[makeConnection()]}
        systems={SYSTEMS}
        viewport={{ ...VIEWPORT, zoom: 0.5 }}
      />
    );
    const texts = container.querySelectorAll('text');
    // Only "T" marker, no label
    expect(texts.length).toBe(1);
  });
});

// === FWOverlay ===

describe('FWOverlay', () => {
  const makeFW = (overrides: Partial<FWSystem> = {}): FWSystem => ({
    occupier_faction_id: 500001,
    owner_faction_id: 500003,
    contested: 'uncontested',
    victory_points: 0,
    victory_points_threshold: 3000,
    ...overrides,
  });

  it('renders nothing with empty fwSystems', () => {
    const { container } = render(
      <FWOverlay fwSystems={{}} systems={SYSTEMS} viewport={VIEWPORT} />
    );
    expect(container.querySelector('svg')).toBeNull();
  });

  it('renders markers for FW system', () => {
    const { container } = render(
      <FWOverlay
        fwSystems={{ '100': makeFW() }}
        systems={SYSTEMS}
        viewport={VIEWPORT}
      />
    );
    const svg = container.querySelector('svg');
    expect(svg).toBeTruthy();
    // Occupier fill circle + owner border circle = 2 circles (uncontested)
    const circles = svg!.querySelectorAll('circle');
    expect(circles.length).toBe(2);
  });

  it('renders contested ring for contested systems', () => {
    const { container } = render(
      <FWOverlay
        fwSystems={{ '100': makeFW({ contested: 'contested' }) }}
        systems={SYSTEMS}
        viewport={VIEWPORT}
      />
    );
    const svg = container.querySelector('svg');
    const circles = svg!.querySelectorAll('circle');
    // fill + border + contested dashed ring = 3
    expect(circles.length).toBe(3);
    const dashed = circles[2];
    expect(dashed).toHaveAttribute('stroke-dasharray', '3 3');
  });

  it('skips unknown faction IDs', () => {
    const { container } = render(
      <FWOverlay
        fwSystems={{ '100': makeFW({ owner_faction_id: 999999, occupier_faction_id: 999998 }) }}
        systems={SYSTEMS}
        viewport={VIEWPORT}
      />
    );
    expect(container.querySelector('svg')).toBeNull();
  });
});

// === LandmarksOverlay ===

describe('LandmarksOverlay', () => {
  const makeLandmark = (overrides: Partial<Landmark> = {}): Landmark => ({
    id: 1,
    name: 'Eve Gate',
    description: 'The legendary wormhole collapse site',
    system_id: 100,
    icon_id: null,
    ...overrides,
  });

  it('renders nothing with empty landmarks', () => {
    const { container } = render(
      <LandmarksOverlay landmarks={[]} systems={SYSTEMS} viewport={VIEWPORT} />
    );
    // The container div is not rendered when markers are empty
    expect(container.children[0]?.children.length ?? 0).toBe(0);
  });

  it('renders diamond marker for landmark', () => {
    const { container } = render(
      <LandmarksOverlay
        landmarks={[makeLandmark()]}
        systems={SYSTEMS}
        viewport={VIEWPORT}
      />
    );
    const diamond = container.querySelector('.rotate-45');
    expect(diamond).toBeTruthy();
  });

  it('shows label at high zoom', () => {
    render(
      <LandmarksOverlay
        landmarks={[makeLandmark()]}
        systems={SYSTEMS}
        viewport={{ ...VIEWPORT, zoom: 3 }}
      />
    );
    expect(screen.getByText('Eve Gate')).toBeInTheDocument();
  });

  it('hides label at low zoom', () => {
    render(
      <LandmarksOverlay
        landmarks={[makeLandmark()]}
        systems={SYSTEMS}
        viewport={{ ...VIEWPORT, zoom: 1 }}
      />
    );
    expect(screen.queryByText('Eve Gate')).toBeNull();
  });

  it('shows tooltip on hover', () => {
    render(
      <LandmarksOverlay
        landmarks={[makeLandmark()]}
        systems={SYSTEMS}
        viewport={VIEWPORT}
      />
    );
    const marker = document.querySelector('.pointer-events-auto');
    expect(marker).toBeTruthy();
    fireEvent.mouseEnter(marker!);
    expect(screen.getByText('Eve Gate')).toBeInTheDocument();
    expect(screen.getByText('The legendary wormhole collapse site')).toBeInTheDocument();
  });

  it('hides tooltip on mouse leave', () => {
    render(
      <LandmarksOverlay
        landmarks={[makeLandmark()]}
        systems={SYSTEMS}
        viewport={VIEWPORT}
      />
    );
    const marker = document.querySelector('.pointer-events-auto');
    fireEvent.mouseEnter(marker!);
    fireEvent.mouseLeave(marker!);
    expect(screen.queryByText('The legendary wormhole collapse site')).toBeNull();
  });

  it('skips landmarks without system_id', () => {
    const { container } = render(
      <LandmarksOverlay
        landmarks={[makeLandmark({ system_id: null })]}
        systems={SYSTEMS}
        viewport={VIEWPORT}
      />
    );
    expect(container.querySelector('.rotate-45')).toBeNull();
  });
});

// === SovStructuresOverlay ===

describe('SovStructuresOverlay', () => {
  const makeStruct = (overrides: Partial<SovStructure> = {}): SovStructure => ({
    alliance_id: 99000001,
    structure_type_id: 32458, // iHub
    vulnerability_occupancy_level: 4,
    vulnerable_start_time: null,
    vulnerable_end_time: null,
    ...overrides,
  });

  const highZoom: MapViewport = { ...VIEWPORT, zoom: 2 };

  it('renders nothing at low zoom', () => {
    const { container } = render(
      <SovStructuresOverlay
        structures={{ '100': [makeStruct()] }}
        systems={SYSTEMS}
        viewport={{ ...VIEWPORT, zoom: 1 }}
      />
    );
    expect(container.querySelector('svg')).toBeNull();
  });

  it('renders indicator dots at high zoom', () => {
    const { container } = render(
      <SovStructuresOverlay
        structures={{ '100': [makeStruct()] }}
        systems={SYSTEMS}
        viewport={highZoom}
      />
    );
    const svg = container.querySelector('svg');
    expect(svg).toBeTruthy();
    // ADM dot + invisible hit area = 2 circles per system
    const circles = svg!.querySelectorAll('circle');
    expect(circles.length).toBeGreaterThanOrEqual(2);
  });

  it('uses green dot color for high ADM', () => {
    const { container } = render(
      <SovStructuresOverlay
        structures={{ '100': [makeStruct({ vulnerability_occupancy_level: 5 })] }}
        systems={SYSTEMS}
        viewport={highZoom}
      />
    );
    const circles = container.querySelectorAll('circle');
    // First circle is the ADM indicator dot
    expect(circles[0]).toHaveAttribute('fill', '#22c55e');
  });

  it('uses red dot color for low ADM', () => {
    const { container } = render(
      <SovStructuresOverlay
        structures={{ '100': [makeStruct({ vulnerability_occupancy_level: 1 })] }}
        systems={SYSTEMS}
        viewport={highZoom}
      />
    );
    const circles = container.querySelectorAll('circle');
    expect(circles[0]).toHaveAttribute('fill', '#ef4444');
  });

  it('uses yellow dot color for medium ADM', () => {
    const { container } = render(
      <SovStructuresOverlay
        structures={{ '100': [makeStruct({ vulnerability_occupancy_level: 3 })] }}
        systems={SYSTEMS}
        viewport={highZoom}
      />
    );
    const circles = container.querySelectorAll('circle');
    expect(circles[0]).toHaveAttribute('fill', '#eab308');
  });

  it('renders nothing for empty structures', () => {
    const { container } = render(
      <SovStructuresOverlay
        structures={{}}
        systems={SYSTEMS}
        viewport={highZoom}
      />
    );
    expect(container.querySelector('svg')).toBeNull();
  });

  it('renders skyhook-only system with sky-blue dot', () => {
    const { container } = render(
      <SovStructuresOverlay
        structures={{ '100': [makeStruct({ structure_type_id: 81826, vulnerability_occupancy_level: null })] }}
        systems={SYSTEMS}
        viewport={highZoom}
      />
    );
    const circles = container.querySelectorAll('circle');
    // ADM dot (gray for null) + skyhook dot + hit area
    expect(circles.length).toBeGreaterThanOrEqual(3);
    // Skyhook dot is the second circle
    expect(circles[1]).toHaveAttribute('fill', '#7dd3fc');
  });

  it('renders both ADM and skyhook dots', () => {
    const { container } = render(
      <SovStructuresOverlay
        structures={{ '100': [
          makeStruct({ structure_type_id: 32458, vulnerability_occupancy_level: 5 }),
          makeStruct({ structure_type_id: 81826, vulnerability_occupancy_level: null }),
        ] }}
        systems={SYSTEMS}
        viewport={highZoom}
      />
    );
    const circles = container.querySelectorAll('circle');
    // ADM dot + skyhook dot + hit area = 3
    expect(circles.length).toBeGreaterThanOrEqual(3);
    // ADM dot green
    expect(circles[0]).toHaveAttribute('fill', '#22c55e');
    // Skyhook dot sky-blue
    expect(circles[1]).toHaveAttribute('fill', '#7dd3fc');
  });

  it('scales dot size with zoom', () => {
    const { container: c1 } = render(
      <SovStructuresOverlay
        structures={{ '100': [makeStruct()] }}
        systems={SYSTEMS}
        viewport={{ ...VIEWPORT, zoom: 2 }}
      />
    );
    const { container: c2 } = render(
      <SovStructuresOverlay
        structures={{ '100': [makeStruct()] }}
        systems={SYSTEMS}
        viewport={{ ...VIEWPORT, zoom: 4 }}
      />
    );
    const r1 = Number(c1.querySelector('circle')!.getAttribute('r'));
    const r2 = Number(c2.querySelector('circle')!.getAttribute('r'));
    expect(r2).toBeGreaterThanOrEqual(r1);
  });
});

// === MarketHubsOverlay ===

describe('MarketHubsOverlay', () => {
  const JITA_SYSTEM = makeSystem({ systemId: 30000142, name: 'Jita', x: 10, y: 10 });
  const AMARR_SYSTEM = makeSystem({ systemId: 30002187, name: 'Amarr', x: 50, y: 50 });
  const HUB_SYSTEMS = makeSystemMap(JITA_SYSTEM, AMARR_SYSTEM);

  const makeHub = (overrides: Partial<MarketHub> = {}): MarketHub => ({
    system_id: 30000142,
    system_name: 'Jita',
    region_name: 'The Forge',
    is_primary: true,
    daily_volume_estimate: 50_000_000_000_000,
    ...overrides,
  });

  it('renders nothing with empty hubs', () => {
    const { container } = render(
      <MarketHubsOverlay hubs={[]} systems={HUB_SYSTEMS} viewport={VIEWPORT} />
    );
    expect(container.querySelector('[data-testid="market-hubs-overlay"]')).toBeNull();
  });

  it('renders diamond marker for hub', () => {
    const { container } = render(
      <MarketHubsOverlay
        hubs={[makeHub()]}
        systems={HUB_SYSTEMS}
        viewport={VIEWPORT}
      />
    );
    const diamond = container.querySelector('.rotate-45');
    expect(diamond).toBeTruthy();
  });

  it('applies pulse animation to primary hub (Jita)', () => {
    const { container } = render(
      <MarketHubsOverlay
        hubs={[makeHub({ is_primary: true })]}
        systems={HUB_SYSTEMS}
        viewport={VIEWPORT}
      />
    );
    const diamond = container.querySelector('.animate-pulse');
    expect(diamond).toBeTruthy();
  });

  it('does not apply pulse animation to non-primary hub', () => {
    const { container } = render(
      <MarketHubsOverlay
        hubs={[makeHub({ system_id: 30002187, system_name: 'Amarr', is_primary: false })]}
        systems={HUB_SYSTEMS}
        viewport={VIEWPORT}
      />
    );
    const diamond = container.querySelector('.animate-pulse');
    expect(diamond).toBeNull();
  });

  it('shows label at sufficient zoom', () => {
    render(
      <MarketHubsOverlay
        hubs={[makeHub()]}
        systems={HUB_SYSTEMS}
        viewport={{ ...VIEWPORT, zoom: 1 }}
      />
    );
    expect(screen.getByText('Jita')).toBeInTheDocument();
  });

  it('hides label at low zoom', () => {
    render(
      <MarketHubsOverlay
        hubs={[makeHub()]}
        systems={HUB_SYSTEMS}
        viewport={{ ...VIEWPORT, zoom: 0.5 }}
      />
    );
    expect(screen.queryByText('Jita')).toBeNull();
  });

  it('shows tooltip on hover with region and volume', () => {
    render(
      <MarketHubsOverlay
        hubs={[makeHub()]}
        systems={HUB_SYSTEMS}
        viewport={VIEWPORT}
      />
    );
    const marker = document.querySelector('.pointer-events-auto');
    expect(marker).toBeTruthy();
    fireEvent.mouseEnter(marker!);
    expect(screen.getByText('The Forge')).toBeInTheDocument();
    expect(screen.getByText('Primary Trade Hub')).toBeInTheDocument();
  });

  it('hides tooltip on mouse leave', () => {
    render(
      <MarketHubsOverlay
        hubs={[makeHub()]}
        systems={HUB_SYSTEMS}
        viewport={VIEWPORT}
      />
    );
    const marker = document.querySelector('.pointer-events-auto');
    fireEvent.mouseEnter(marker!);
    fireEvent.mouseLeave(marker!);
    expect(screen.queryByText('Primary Trade Hub')).toBeNull();
  });

  it('skips hubs not in system map', () => {
    const { container } = render(
      <MarketHubsOverlay
        hubs={[makeHub({ system_id: 99999 })]}
        systems={HUB_SYSTEMS}
        viewport={VIEWPORT}
      />
    );
    expect(container.querySelector('[data-testid="market-hubs-overlay"]')).toBeNull();
  });

  it('skips hubs outside viewport', () => {
    const farSystem = makeSystem({ systemId: 30000142, x: 5000, y: 5000 });
    const { container } = render(
      <MarketHubsOverlay
        hubs={[makeHub()]}
        systems={makeSystemMap(farSystem)}
        viewport={VIEWPORT}
      />
    );
    expect(container.querySelector('[data-testid="market-hubs-overlay"]')).toBeNull();
  });

  it('renders multiple hubs', () => {
    const { container } = render(
      <MarketHubsOverlay
        hubs={[
          makeHub(),
          makeHub({ system_id: 30002187, system_name: 'Amarr', is_primary: false, daily_volume_estimate: 15_000_000_000_000 }),
        ]}
        systems={HUB_SYSTEMS}
        viewport={VIEWPORT}
      />
    );
    const diamonds = container.querySelectorAll('.rotate-45');
    expect(diamonds.length).toBe(2);
  });

  it('formats volume in trillions', () => {
    render(
      <MarketHubsOverlay
        hubs={[makeHub({ daily_volume_estimate: 50_000_000_000_000 })]}
        systems={HUB_SYSTEMS}
        viewport={{ ...VIEWPORT, zoom: 1 }}
      />
    );
    expect(screen.getByText('50T ISK/day')).toBeInTheDocument();
  });
});
