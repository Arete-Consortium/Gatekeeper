/**
 * Spatial utilities for efficient system lookup and viewport culling
 * Uses a Quadtree for O(log n) spatial queries on 8000+ systems
 */

import type { MapSystem, MapViewport } from '../types';

// Bounding box for spatial queries
export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

// Quadtree node capacity before splitting
const MAX_OBJECTS = 10;
const MAX_LEVELS = 8;

/**
 * Quadtree for efficient spatial queries
 * Enables viewport culling to only render visible systems
 */
export class Quadtree {
  private bounds: BoundingBox;
  private level: number;
  private objects: MapSystem[];
  private nodes: Quadtree[];

  constructor(bounds: BoundingBox, level = 0) {
    this.bounds = bounds;
    this.level = level;
    this.objects = [];
    this.nodes = [];
  }

  /**
   * Clear all objects from the tree
   */
  clear(): void {
    this.objects = [];
    for (const node of this.nodes) {
      node.clear();
    }
    this.nodes = [];
  }

  /**
   * Split node into 4 quadrants
   */
  private split(): void {
    const subWidth = this.bounds.width / 2;
    const subHeight = this.bounds.height / 2;
    const x = this.bounds.x;
    const y = this.bounds.y;

    // Top-right
    this.nodes[0] = new Quadtree(
      { x: x + subWidth, y, width: subWidth, height: subHeight },
      this.level + 1
    );
    // Top-left
    this.nodes[1] = new Quadtree(
      { x, y, width: subWidth, height: subHeight },
      this.level + 1
    );
    // Bottom-left
    this.nodes[2] = new Quadtree(
      { x, y: y + subHeight, width: subWidth, height: subHeight },
      this.level + 1
    );
    // Bottom-right
    this.nodes[3] = new Quadtree(
      { x: x + subWidth, y: y + subHeight, width: subWidth, height: subHeight },
      this.level + 1
    );
  }

  /**
   * Get index of quadrant that contains the point
   * Returns -1 if point spans multiple quadrants
   */
  private getIndex(system: MapSystem): number {
    const midX = this.bounds.x + this.bounds.width / 2;
    const midY = this.bounds.y + this.bounds.height / 2;

    const inTop = system.y < midY;
    const inBottom = system.y >= midY;
    const inLeft = system.x < midX;
    const inRight = system.x >= midX;

    if (inTop && inRight) return 0;
    if (inTop && inLeft) return 1;
    if (inBottom && inLeft) return 2;
    if (inBottom && inRight) return 3;

    return -1;
  }

  /**
   * Insert a system into the quadtree
   */
  insert(system: MapSystem): void {
    // If we have subnodes, insert into appropriate child
    if (this.nodes.length > 0) {
      const index = this.getIndex(system);
      if (index !== -1) {
        this.nodes[index].insert(system);
        return;
      }
    }

    this.objects.push(system);

    // Split if we exceed capacity and haven't reached max depth
    if (this.objects.length > MAX_OBJECTS && this.level < MAX_LEVELS) {
      if (this.nodes.length === 0) {
        this.split();
      }

      // Redistribute objects to child nodes
      let i = 0;
      while (i < this.objects.length) {
        const index = this.getIndex(this.objects[i]);
        if (index !== -1) {
          const removed = this.objects.splice(i, 1)[0];
          this.nodes[index].insert(removed);
        } else {
          i++;
        }
      }
    }
  }

  /**
   * Query all systems within a bounding box (for viewport culling)
   */
  query(range: BoundingBox, found: MapSystem[] = []): MapSystem[] {
    // If range doesn't intersect this node, return
    if (!this.intersects(range)) {
      return found;
    }

    // Check objects at this level
    for (const system of this.objects) {
      if (this.containsPoint(range, system.x, system.y)) {
        found.push(system);
      }
    }

    // Check child nodes
    for (const node of this.nodes) {
      node.query(range, found);
    }

    return found;
  }

  /**
   * Find the nearest system to a point
   */
  findNearest(x: number, y: number, maxDistance: number): MapSystem | null {
    const range: BoundingBox = {
      x: x - maxDistance,
      y: y - maxDistance,
      width: maxDistance * 2,
      height: maxDistance * 2,
    };

    const candidates = this.query(range);
    let nearest: MapSystem | null = null;
    let minDist = maxDistance * maxDistance;

    for (const system of candidates) {
      const dx = system.x - x;
      const dy = system.y - y;
      const distSq = dx * dx + dy * dy;
      if (distSq < minDist) {
        minDist = distSq;
        nearest = system;
      }
    }

    return nearest;
  }

  /**
   * Check if two bounding boxes intersect
   */
  private intersects(range: BoundingBox): boolean {
    return !(
      range.x > this.bounds.x + this.bounds.width ||
      range.x + range.width < this.bounds.x ||
      range.y > this.bounds.y + this.bounds.height ||
      range.y + range.height < this.bounds.y
    );
  }

  /**
   * Check if a point is within a bounding box
   */
  private containsPoint(box: BoundingBox, x: number, y: number): boolean {
    return (
      x >= box.x &&
      x <= box.x + box.width &&
      y >= box.y &&
      y <= box.y + box.height
    );
  }
}

/**
 * Build a quadtree from an array of systems
 */
export function buildQuadtree(systems: MapSystem[]): Quadtree {
  // Calculate bounds from all systems
  let minX = Infinity;
  let maxX = -Infinity;
  let minY = Infinity;
  let maxY = -Infinity;

  for (const system of systems) {
    minX = Math.min(minX, system.x);
    maxX = Math.max(maxX, system.x);
    minY = Math.min(minY, system.y);
    maxY = Math.max(maxY, system.y);
  }

  // Add padding
  const padding = 1000;
  const bounds: BoundingBox = {
    x: minX - padding,
    y: minY - padding,
    width: maxX - minX + padding * 2,
    height: maxY - minY + padding * 2,
  };

  const tree = new Quadtree(bounds);
  for (const system of systems) {
    tree.insert(system);
  }

  return tree;
}

/**
 * Convert viewport to world-space bounding box
 */
export function viewportToBounds(viewport: MapViewport): BoundingBox {
  const worldWidth = viewport.width / viewport.zoom;
  const worldHeight = viewport.height / viewport.zoom;

  return {
    x: viewport.x - worldWidth / 2,
    y: viewport.y - worldHeight / 2,
    width: worldWidth,
    height: worldHeight,
  };
}

/**
 * Transform world coordinates to screen coordinates
 */
export function worldToScreen(
  worldX: number,
  worldY: number,
  viewport: MapViewport
): { x: number; y: number } {
  const x = (worldX - viewport.x) * viewport.zoom + viewport.width / 2;
  const y = (worldY - viewport.y) * viewport.zoom + viewport.height / 2;
  return { x, y };
}

/**
 * Transform screen coordinates to world coordinates
 */
export function screenToWorld(
  screenX: number,
  screenY: number,
  viewport: MapViewport
): { x: number; y: number } {
  const x = (screenX - viewport.width / 2) / viewport.zoom + viewport.x;
  const y = (screenY - viewport.height / 2) / viewport.zoom + viewport.y;
  return { x, y };
}

/**
 * Calculate zoom level to fit given systems in viewport
 */
export function calculateFitZoom(
  systems: MapSystem[],
  viewportWidth: number,
  viewportHeight: number,
  padding = 50
): { x: number; y: number; zoom: number } {
  if (systems.length === 0) {
    return { x: 0, y: 0, zoom: 1 };
  }

  if (systems.length === 1) {
    return { x: systems[0].x, y: systems[0].y, zoom: 1 };
  }

  let minX = Infinity;
  let maxX = -Infinity;
  let minY = Infinity;
  let maxY = -Infinity;

  for (const system of systems) {
    minX = Math.min(minX, system.x);
    maxX = Math.max(maxX, system.x);
    minY = Math.min(minY, system.y);
    maxY = Math.max(maxY, system.y);
  }

  const centerX = (minX + maxX) / 2;
  const centerY = (minY + maxY) / 2;
  const width = maxX - minX;
  const height = maxY - minY;

  const zoomX = (viewportWidth - padding * 2) / (width || 1);
  const zoomY = (viewportHeight - padding * 2) / (height || 1);
  const zoom = Math.min(zoomX, zoomY, 2); // Cap at 2x zoom

  return { x: centerX, y: centerY, zoom: Math.max(zoom, 0.01) };
}

/**
 * Clamp a value between min and max
 */
export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

/**
 * Linear interpolation
 */
export function lerp(start: number, end: number, t: number): number {
  return start + (end - start) * t;
}

/**
 * Smooth step interpolation (ease in-out)
 */
export function smoothStep(t: number): number {
  return t * t * (3 - 2 * t);
}
