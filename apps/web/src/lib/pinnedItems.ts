/**
 * Shared localStorage persistence for pinned items (systems, corps, alliances).
 * Same pattern as pinned pilots but generalized.
 */

// ── Types ──

export interface PinnedSystem {
  systemId: number;
  name: string;
}

export interface PinnedCorp {
  corporationId: number;
  name: string;
}

export interface PinnedAlliance {
  allianceId: number;
  name: string;
}

// ── Storage Keys ──

const SYSTEMS_KEY = 'gk_pinned_systems';
const CORPS_KEY = 'gk_pinned_corps';
const ALLIANCES_KEY = 'gk_pinned_alliances';

// ── Generic helpers ──

function load<T>(key: string): T[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : [];
  } catch { return []; }
}

function save<T>(key: string, items: T[]) {
  try { localStorage.setItem(key, JSON.stringify(items)); } catch { /* ignore */ }
}

// ── Systems ──

export function loadPinnedSystems(): PinnedSystem[] {
  return load<PinnedSystem>(SYSTEMS_KEY);
}

export function savePinnedSystems(systems: PinnedSystem[]) {
  save(SYSTEMS_KEY, systems);
}

// ── Corporations ──

export function loadPinnedCorps(): PinnedCorp[] {
  return load<PinnedCorp>(CORPS_KEY);
}

export function savePinnedCorps(corps: PinnedCorp[]) {
  save(CORPS_KEY, corps);
}

// ── Alliances ──

export function loadPinnedAlliances(): PinnedAlliance[] {
  return load<PinnedAlliance>(ALLIANCES_KEY);
}

export function savePinnedAlliances(alliances: PinnedAlliance[]) {
  save(ALLIANCES_KEY, alliances);
}
