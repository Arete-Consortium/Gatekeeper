import { SpatialIndex } from '../utils/SpatialIndex';
import type { MapNode } from '../components/map/types';

function makeNode(overrides: Partial<MapNode> & { name: string; x: number; y: number }): MapNode {
  return {
    systemId: 1,
    security: 0.5,
    category: 'highsec',
    regionId: 10,
    constellationId: 100,
    riskScore: 0,
    riskColor: 'green',
    ...overrides,
  };
}

describe('SpatialIndex', () => {
  const nodes: MapNode[] = [
    makeNode({ name: 'Jita', x: 100, y: 200, systemId: 1 }),
    makeNode({ name: 'Amarr', x: 500, y: 800, systemId: 2 }),
    makeNode({ name: 'Dodixie', x: 300, y: 400, systemId: 3 }),
    makeNode({ name: 'Rens', x: 50, y: 50, systemId: 4, security: -0.5, category: 'nullsec' }),
    makeNode({ name: 'Hek', x: 750, y: 100, systemId: 5, security: 0.3, category: 'lowsec' }),
  ];

  let index: SpatialIndex;

  beforeEach(() => {
    index = new SpatialIndex(nodes, 10);
  });

  describe('getBounds', () => {
    it('computes correct world bounds with padding', () => {
      const bounds = index.getBounds();
      expect(bounds.minX).toBeLessThan(50);
      expect(bounds.maxX).toBeGreaterThan(750);
      expect(bounds.minY).toBeLessThan(50);
      expect(bounds.maxY).toBeGreaterThan(800);
      expect(bounds.centerX).toBeCloseTo((50 + 750) / 2, -1);
      expect(bounds.centerY).toBeCloseTo((50 + 800) / 2, -1);
    });
  });

  describe('queryRect', () => {
    it('returns nodes within the rectangle', () => {
      const result = index.queryRect(0, 0, 200, 300);
      const names = result.map((n) => n.name).sort();
      expect(names).toContain('Jita');
      expect(names).toContain('Rens');
      expect(names).not.toContain('Amarr');
    });

    it('returns empty array for empty region', () => {
      const result = index.queryRect(900, 900, 1000, 1000);
      expect(result).toHaveLength(0);
    });

    it('returns all nodes for world-spanning rectangle', () => {
      const result = index.queryRect(-1000, -1000, 2000, 2000);
      expect(result).toHaveLength(5);
    });
  });

  describe('findNearest', () => {
    it('finds nearest system to a point', () => {
      const nearest = index.findNearest(110, 210, 50);
      expect(nearest?.name).toBe('Jita');
    });

    it('returns null when no system within radius', () => {
      const nearest = index.findNearest(900, 900, 10);
      expect(nearest).toBeNull();
    });

    it('picks the closest when multiple are in range', () => {
      // Point (280, 380) is closer to Dodixie (300,400) than Jita (100,200)
      const nearest = index.findNearest(280, 380, 500);
      expect(nearest?.name).toBe('Dodixie');
    });
  });

  describe('empty index', () => {
    it('handles empty node list', () => {
      const emptyIndex = new SpatialIndex([]);
      expect(emptyIndex.queryRect(0, 0, 100, 100)).toHaveLength(0);
      expect(emptyIndex.findNearest(0, 0, 100)).toBeNull();
      const bounds = emptyIndex.getBounds();
      expect(bounds.width).toBe(1);
    });
  });
});
