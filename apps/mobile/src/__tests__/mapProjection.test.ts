import { worldToScreen, screenToWorld, getVisibleWorldRect } from '../utils/mapProjection';
import type { MapViewport } from '../components/map/types';

describe('mapProjection', () => {
  const viewport: MapViewport = {
    centerX: 500,
    centerY: 300,
    zoom: 2,
    screenWidth: 400,
    screenHeight: 800,
  };

  describe('worldToScreen', () => {
    it('maps center of world to center of screen', () => {
      const { sx, sy } = worldToScreen(500, 300, viewport);
      expect(sx).toBe(200); // screenWidth / 2
      expect(sy).toBe(400); // screenHeight / 2
    });

    it('applies zoom scaling', () => {
      const { sx, sy } = worldToScreen(550, 350, viewport);
      // (550-500)*2 + 200 = 300
      expect(sx).toBe(300);
      // (350-300)*2 + 400 = 500
      expect(sy).toBe(500);
    });
  });

  describe('screenToWorld', () => {
    it('maps center of screen to center of world', () => {
      const { wx, wy } = screenToWorld(200, 400, viewport);
      expect(wx).toBe(500);
      expect(wy).toBe(300);
    });

    it('is the inverse of worldToScreen', () => {
      const worldX = 123;
      const worldY = 456;
      const { sx, sy } = worldToScreen(worldX, worldY, viewport);
      const { wx, wy } = screenToWorld(sx, sy, viewport);
      expect(wx).toBeCloseTo(worldX);
      expect(wy).toBeCloseTo(worldY);
    });
  });

  describe('getVisibleWorldRect', () => {
    it('returns correct visible area', () => {
      const rect = getVisibleWorldRect(viewport);
      // halfW = 400/2/2 = 100, halfH = 800/2/2 = 200
      expect(rect.minX).toBe(400); // 500 - 100
      expect(rect.maxX).toBe(600); // 500 + 100
      expect(rect.minY).toBe(100); // 300 - 200
      expect(rect.maxY).toBe(500); // 300 + 200
    });

    it('shows more area at lower zoom', () => {
      const zoomedOut = { ...viewport, zoom: 0.5 };
      const rect = getVisibleWorldRect(zoomedOut);
      // halfW = 400/2/0.5 = 400
      expect(rect.maxX - rect.minX).toBe(800);
    });
  });
});
