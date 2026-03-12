import { describe, it, expect } from 'vitest';

// ── Pure compression algorithm (extracted from UniverseMap.tsx useMemo) ──────
// Groups systems by regionId, computes region centroids, global centroid,
// then shifts each system: newPos = pos + (globalCenter - regionCenter) * (1 - factor)

interface TestSystem {
  id: number;
  x: number;
  y: number;
  regionId: number;
}

function compressRegions(systems: TestSystem[], factor: number): TestSystem[] {
  if (systems.length === 0) return systems;

  // Calculate region centroids
  const regionSums = new Map<number, { sx: number; sy: number; count: number }>();
  for (const s of systems) {
    const acc = regionSums.get(s.regionId) || { sx: 0, sy: 0, count: 0 };
    acc.sx += s.x;
    acc.sy += s.y;
    acc.count += 1;
    regionSums.set(s.regionId, acc);
  }
  const regionCentroids = new Map<number, { cx: number; cy: number }>();
  for (const [rid, { sx, sy, count }] of regionSums) {
    regionCentroids.set(rid, { cx: sx / count, cy: sy / count });
  }

  // Global centroid (average of region centroids)
  let gcx = 0, gcy = 0;
  for (const { cx, cy } of regionCentroids.values()) { gcx += cx; gcy += cy; }
  gcx /= regionCentroids.size;
  gcy /= regionCentroids.size;

  // Compress
  return systems.map((s) => {
    const rc = regionCentroids.get(s.regionId);
    if (!rc) return s;
    const dx = (gcx - rc.cx) * (1 - factor);
    const dy = (gcy - rc.cy) * (1 - factor);
    return { ...s, x: s.x + dx, y: s.y + dy };
  });
}

// ── FW warzone compression (extracted from FWMap.tsx useMemo) ────────────────
// Same algorithm but grouped by warzoneId instead of regionId

interface TestFWSystem {
  id: number;
  x: number;
  y: number;
  warzoneId: number;
}

function compressWarzones(systems: TestFWSystem[], factor: number): TestFWSystem[] {
  if (systems.length === 0) return systems;

  // Calculate warzone centroids
  const wzSums = new Map<number, { sx: number; sy: number; count: number }>();
  for (const s of systems) {
    const acc = wzSums.get(s.warzoneId) || { sx: 0, sy: 0, count: 0 };
    acc.sx += s.x;
    acc.sy += s.y;
    acc.count += 1;
    wzSums.set(s.warzoneId, acc);
  }

  const wzCentroids = new Map<number, { cx: number; cy: number }>();
  for (const [wz, { sx, sy, count }] of wzSums) {
    wzCentroids.set(wz, { cx: sx / count, cy: sy / count });
  }

  // Global centroid
  let gcx = 0, gcy = 0;
  for (const { cx, cy } of wzCentroids.values()) { gcx += cx; gcy += cy; }
  gcx /= wzCentroids.size;
  gcy /= wzCentroids.size;

  // Compress
  return systems.map((s) => {
    const wc = wzCentroids.get(s.warzoneId);
    if (!wc) return s;
    const dx = (gcx - wc.cx) * (1 - factor);
    const dy = (gcy - wc.cy) * (1 - factor);
    return { ...s, x: s.x + dx, y: s.y + dy };
  });
}

// ── Tests: Region Compression ───────────────────────────────────────────────

describe('compressRegions', () => {
  it('returns empty array for empty input', () => {
    expect(compressRegions([], 0.5)).toEqual([]);
  });

  it('does not move systems when there is only one region', () => {
    const systems: TestSystem[] = [
      { id: 1, x: 10, y: 20, regionId: 100 },
      { id: 2, x: 30, y: 40, regionId: 100 },
      { id: 3, x: 50, y: 60, regionId: 100 },
    ];

    const result = compressRegions(systems, 0.5);

    // With one region, region centroid == global centroid, so dx=dy=0
    for (let i = 0; i < systems.length; i++) {
      expect(result[i].x).toBe(systems[i].x);
      expect(result[i].y).toBe(systems[i].y);
    }
  });

  it('pulls two regions closer together with factor=0.5', () => {
    // Region A centered at (0, 0), Region B centered at (100, 0)
    const systems: TestSystem[] = [
      { id: 1, x: -10, y: 0, regionId: 1 },
      { id: 2, x: 10, y: 0, regionId: 1 },
      { id: 3, x: 90, y: 0, regionId: 2 },
      { id: 4, x: 110, y: 0, regionId: 2 },
    ];

    const result = compressRegions(systems, 0.5);

    // Region A centroid: (0, 0), Region B centroid: (100, 0)
    // Global centroid: (50, 0)
    // Region A shift: (50 - 0) * 0.5 = 25 in x
    // Region B shift: (50 - 100) * 0.5 = -25 in x
    expect(result[0].x).toBeCloseTo(-10 + 25); // 15
    expect(result[1].x).toBeCloseTo(10 + 25);  // 35
    expect(result[2].x).toBeCloseTo(90 - 25);  // 65
    expect(result[3].x).toBeCloseTo(110 - 25); // 85

    // Y unchanged (both centroids have y=0)
    expect(result[0].y).toBeCloseTo(0);
    expect(result[2].y).toBeCloseTo(0);
  });

  it('preserves relative positions within a region', () => {
    const systems: TestSystem[] = [
      { id: 1, x: 0, y: 0, regionId: 1 },
      { id: 2, x: 10, y: 5, regionId: 1 },
      { id: 3, x: 200, y: 200, regionId: 2 },
      { id: 4, x: 210, y: 205, regionId: 2 },
    ];

    const result = compressRegions(systems, 0.5);

    // Within region 1: relative offsets should be identical
    const dx1 = result[1].x - result[0].x;
    const dy1 = result[1].y - result[0].y;
    expect(dx1).toBeCloseTo(10);
    expect(dy1).toBeCloseTo(5);

    // Within region 2: relative offsets should be identical
    const dx2 = result[3].x - result[2].x;
    const dy2 = result[3].y - result[2].y;
    expect(dx2).toBeCloseTo(10);
    expect(dy2).toBeCloseTo(5);
  });

  it('applies no compression when factor=1.0', () => {
    const systems: TestSystem[] = [
      { id: 1, x: 0, y: 0, regionId: 1 },
      { id: 2, x: 100, y: 100, regionId: 2 },
    ];

    const result = compressRegions(systems, 1.0);

    // factor=1.0 → (1 - factor) = 0 → no shift
    expect(result[0].x).toBeCloseTo(0);
    expect(result[0].y).toBeCloseTo(0);
    expect(result[1].x).toBeCloseTo(100);
    expect(result[1].y).toBeCloseTo(100);
  });

  it('collapses all region centroids to global center when factor=0.0', () => {
    const systems: TestSystem[] = [
      { id: 1, x: 0, y: 0, regionId: 1 },
      { id: 2, x: 200, y: 0, regionId: 2 },
    ];

    const result = compressRegions(systems, 0.0);

    // Region 1 centroid: (0, 0), Region 2 centroid: (200, 0)
    // Global centroid: (100, 0)
    // factor=0 → shift = (globalCenter - regionCenter) * 1
    // System 1: 0 + (100 - 0) = 100
    // System 2: 200 + (100 - 200) = 100
    // Both systems end up at global centroid x=100
    expect(result[0].x).toBeCloseTo(100);
    expect(result[1].x).toBeCloseTo(100);
  });

  it('handles three regions symmetrically', () => {
    // Triangle layout: regions at (0,0), (100,0), (50,86.6)
    const systems: TestSystem[] = [
      { id: 1, x: 0, y: 0, regionId: 1 },
      { id: 2, x: 100, y: 0, regionId: 2 },
      { id: 3, x: 50, y: 86.6, regionId: 3 },
    ];

    const result = compressRegions(systems, 0.5);

    // Global centroid: (50, 28.867)
    // Each region gets pulled 50% toward global center
    // Region 1: shift_x = (50 - 0) * 0.5 = 25, shift_y = (28.867 - 0) * 0.5 = 14.433
    expect(result[0].x).toBeCloseTo(25);
    expect(result[0].y).toBeCloseTo(14.433, 0);

    // Region 2: shift_x = (50 - 100) * 0.5 = -25, shift_y = 14.433
    expect(result[1].x).toBeCloseTo(75);
    expect(result[1].y).toBeCloseTo(14.433, 0);

    // Region 3: shift_x = (50 - 50) * 0.5 = 0, shift_y = (28.867 - 86.6) * 0.5 = -28.867
    expect(result[2].x).toBeCloseTo(50);
    expect(result[2].y).toBeCloseTo(86.6 - 28.867, 0);
  });

  it('correctly computes centroid for multi-system regions', () => {
    // Region A: systems at (0,0) and (20,0) → centroid (10, 0)
    // Region B: single system at (100, 0) → centroid (100, 0)
    const systems: TestSystem[] = [
      { id: 1, x: 0, y: 0, regionId: 1 },
      { id: 2, x: 20, y: 0, regionId: 1 },
      { id: 3, x: 100, y: 0, regionId: 2 },
    ];

    const result = compressRegions(systems, 0.5);

    // Region centroids: A=(10,0), B=(100,0)
    // Global centroid: (55, 0)
    // Region A shift: (55 - 10) * 0.5 = 22.5
    // Region B shift: (55 - 100) * 0.5 = -22.5
    expect(result[0].x).toBeCloseTo(0 + 22.5);   // 22.5
    expect(result[1].x).toBeCloseTo(20 + 22.5);   // 42.5
    expect(result[2].x).toBeCloseTo(100 - 22.5);  // 77.5

    // Relative position within region A preserved
    expect(result[1].x - result[0].x).toBeCloseTo(20);
  });

  it('preserves system id and regionId in output', () => {
    const systems: TestSystem[] = [
      { id: 42, x: 0, y: 0, regionId: 7 },
      { id: 99, x: 100, y: 100, regionId: 8 },
    ];

    const result = compressRegions(systems, 0.5);

    expect(result[0].id).toBe(42);
    expect(result[0].regionId).toBe(7);
    expect(result[1].id).toBe(99);
    expect(result[1].regionId).toBe(8);
  });

  it('compresses in both x and y dimensions', () => {
    const systems: TestSystem[] = [
      { id: 1, x: 0, y: 0, regionId: 1 },
      { id: 2, x: 100, y: 200, regionId: 2 },
    ];

    const result = compressRegions(systems, 0.5);

    // Global centroid: (50, 100)
    // Region 1 shift: (50, 100) * 0.5 = (25, 50)
    // Region 2 shift: (-50, -100) * 0.5 = (-25, -50)
    expect(result[0].x).toBeCloseTo(25);
    expect(result[0].y).toBeCloseTo(50);
    expect(result[1].x).toBeCloseTo(75);
    expect(result[1].y).toBeCloseTo(150);
  });

  it('reduces distance between region centroids by factor amount', () => {
    const systems: TestSystem[] = [
      { id: 1, x: 0, y: 0, regionId: 1 },
      { id: 2, x: 200, y: 0, regionId: 2 },
    ];

    // Original distance between centroids: 200
    const factor = 0.5;
    const result = compressRegions(systems, factor);

    const newDist = Math.abs(result[1].x - result[0].x);
    // New distance = 200 * factor = 100
    expect(newDist).toBeCloseTo(200 * factor);
  });
});

// ── Tests: FW Warzone Compression ───────────────────────────────────────────

describe('compressWarzones', () => {
  it('returns empty array for empty input', () => {
    expect(compressWarzones([], 0.5)).toEqual([]);
  });

  it('does not move systems when there is only one warzone', () => {
    const systems: TestFWSystem[] = [
      { id: 1, x: 10, y: 20, warzoneId: 0 },
      { id: 2, x: 30, y: 40, warzoneId: 0 },
    ];

    const result = compressWarzones(systems, 0.5);

    expect(result[0].x).toBe(10);
    expect(result[0].y).toBe(20);
    expect(result[1].x).toBe(30);
    expect(result[1].y).toBe(40);
  });

  it('pulls two warzones closer by 50%', () => {
    // Warzone 0 (Cal/Gal) centered at (0, 0)
    // Warzone 1 (Amarr/Min) centered at (100, 0)
    const systems: TestFWSystem[] = [
      { id: 1, x: -5, y: 0, warzoneId: 0 },
      { id: 2, x: 5, y: 0, warzoneId: 0 },
      { id: 3, x: 95, y: 0, warzoneId: 1 },
      { id: 4, x: 105, y: 0, warzoneId: 1 },
    ];

    const result = compressWarzones(systems, 0.5);

    // Global centroid: (50, 0)
    // WZ 0 shift: (50 - 0) * 0.5 = 25
    // WZ 1 shift: (50 - 100) * 0.5 = -25
    expect(result[0].x).toBeCloseTo(-5 + 25);  // 20
    expect(result[1].x).toBeCloseTo(5 + 25);   // 30
    expect(result[2].x).toBeCloseTo(95 - 25);  // 70
    expect(result[3].x).toBeCloseTo(105 - 25); // 80
  });

  it('preserves intra-warzone relative positions', () => {
    const systems: TestFWSystem[] = [
      { id: 1, x: 0, y: 0, warzoneId: 0 },
      { id: 2, x: 15, y: 10, warzoneId: 0 },
      { id: 3, x: 200, y: 200, warzoneId: 1 },
      { id: 4, x: 220, y: 215, warzoneId: 1 },
    ];

    const result = compressWarzones(systems, 0.5);

    // Relative offsets within each warzone must be preserved
    expect(result[1].x - result[0].x).toBeCloseTo(15);
    expect(result[1].y - result[0].y).toBeCloseTo(10);
    expect(result[3].x - result[2].x).toBeCloseTo(20);
    expect(result[3].y - result[2].y).toBeCloseTo(15);
  });

  it('applies no compression when factor=1.0', () => {
    const systems: TestFWSystem[] = [
      { id: 1, x: 0, y: 0, warzoneId: 0 },
      { id: 2, x: 300, y: 300, warzoneId: 1 },
    ];

    const result = compressWarzones(systems, 1.0);

    expect(result[0].x).toBeCloseTo(0);
    expect(result[0].y).toBeCloseTo(0);
    expect(result[1].x).toBeCloseTo(300);
    expect(result[1].y).toBeCloseTo(300);
  });

  it('collapses warzone centroids to global center when factor=0.0', () => {
    const systems: TestFWSystem[] = [
      { id: 1, x: 0, y: 0, warzoneId: 0 },
      { id: 2, x: 200, y: 100, warzoneId: 1 },
    ];

    const result = compressWarzones(systems, 0.0);

    // Both collapse to global centroid (100, 50)
    expect(result[0].x).toBeCloseTo(100);
    expect(result[0].y).toBeCloseTo(50);
    expect(result[1].x).toBeCloseTo(100);
    expect(result[1].y).toBeCloseTo(50);
  });

  it('reduces inter-warzone distance proportionally to factor', () => {
    const systems: TestFWSystem[] = [
      { id: 1, x: 0, y: 0, warzoneId: 0 },
      { id: 2, x: 400, y: 0, warzoneId: 1 },
    ];

    const factor = 0.3;
    const result = compressWarzones(systems, factor);

    const newDist = Math.abs(result[1].x - result[0].x);
    // Original distance: 400, compressed to 400 * factor = 120
    expect(newDist).toBeCloseTo(400 * factor);
  });

  it('preserves system id and warzoneId in output', () => {
    const systems: TestFWSystem[] = [
      { id: 30001, x: 0, y: 0, warzoneId: 0 },
      { id: 30002, x: 100, y: 100, warzoneId: 1 },
    ];

    const result = compressWarzones(systems, 0.5);

    expect(result[0].id).toBe(30001);
    expect(result[0].warzoneId).toBe(0);
    expect(result[1].id).toBe(30002);
    expect(result[1].warzoneId).toBe(1);
  });
});
