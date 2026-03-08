/**
 * Grid-based spatial index for fast viewport culling and tap detection.
 * Divides world space into a grid of cells, each holding system references.
 */
import type { MapNode, WorldBounds } from '../components/map/types';

const DEFAULT_GRID_SIZE = 100;

export class SpatialIndex {
  private cells: Map<string, MapNode[]>;
  private bounds: WorldBounds;
  private cellWidth: number;
  private cellHeight: number;
  private gridSize: number;

  constructor(nodes: MapNode[], gridSize: number = DEFAULT_GRID_SIZE) {
    this.gridSize = gridSize;
    this.cells = new Map();
    this.bounds = this.computeBounds(nodes);
    this.cellWidth = this.bounds.width / gridSize;
    this.cellHeight = this.bounds.height / gridSize;

    for (const node of nodes) {
      const key = this.cellKey(node.x, node.y);
      const cell = this.cells.get(key);
      if (cell) {
        cell.push(node);
      } else {
        this.cells.set(key, [node]);
      }
    }
  }

  getBounds(): WorldBounds {
    return this.bounds;
  }

  /** Return all nodes within the given world-space rectangle. */
  queryRect(minX: number, minY: number, maxX: number, maxY: number): MapNode[] {
    const result: MapNode[] = [];
    const colMin = Math.max(0, this.cellCol(minX));
    const colMax = Math.min(this.gridSize - 1, this.cellCol(maxX));
    const rowMin = Math.max(0, this.cellRow(minY));
    const rowMax = Math.min(this.gridSize - 1, this.cellRow(maxY));

    for (let col = colMin; col <= colMax; col++) {
      for (let row = rowMin; row <= rowMax; row++) {
        const cell = this.cells.get(`${col}:${row}`);
        if (cell) {
          for (const node of cell) {
            if (node.x >= minX && node.x <= maxX && node.y >= minY && node.y <= maxY) {
              result.push(node);
            }
          }
        }
      }
    }
    return result;
  }

  /** Find the nearest node within a world-space radius of (x, y). */
  findNearest(x: number, y: number, radius: number): MapNode | null {
    const candidates = this.queryRect(x - radius, y - radius, x + radius, y + radius);
    let nearest: MapNode | null = null;
    let nearestDist = Infinity;

    for (const node of candidates) {
      const dx = node.x - x;
      const dy = node.y - y;
      const dist = dx * dx + dy * dy;
      if (dist < nearestDist) {
        nearestDist = dist;
        nearest = node;
      }
    }
    return nearest;
  }

  private computeBounds(nodes: MapNode[]): WorldBounds {
    if (nodes.length === 0) {
      return { minX: 0, maxX: 1, minY: 0, maxY: 1, centerX: 0.5, centerY: 0.5, width: 1, height: 1 };
    }

    let minX = Infinity, maxX = -Infinity;
    let minY = Infinity, maxY = -Infinity;

    for (const node of nodes) {
      if (node.x < minX) minX = node.x;
      if (node.x > maxX) maxX = node.x;
      if (node.y < minY) minY = node.y;
      if (node.y > maxY) maxY = node.y;
    }

    // Add small padding to avoid edge systems landing exactly on boundary
    const padX = (maxX - minX) * 0.02;
    const padY = (maxY - minY) * 0.02;
    minX -= padX;
    maxX += padX;
    minY -= padY;
    maxY += padY;

    return {
      minX,
      maxX,
      minY,
      maxY,
      centerX: (minX + maxX) / 2,
      centerY: (minY + maxY) / 2,
      width: maxX - minX,
      height: maxY - minY,
    };
  }

  private cellCol(x: number): number {
    return Math.floor((x - this.bounds.minX) / this.cellWidth);
  }

  private cellRow(y: number): number {
    return Math.floor((y - this.bounds.minY) / this.cellHeight);
  }

  private cellKey(x: number, y: number): string {
    const col = Math.min(this.gridSize - 1, Math.max(0, this.cellCol(x)));
    const row = Math.min(this.gridSize - 1, Math.max(0, this.cellRow(y)));
    return `${col}:${row}`;
  }
}
