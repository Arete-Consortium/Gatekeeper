'use client';

import { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import { useMutation } from '@tanstack/react-query';
import { GatekeeperAPI } from '@/lib/api';
import { Card, Button } from '@/components/ui';
import { PilotThreatCard } from './PilotThreatCard';
import { PilotDeepDive } from './PilotDeepDive';
import { SystemSummaryCard } from './SystemSummaryCard';
import { ErrorMessage, getUserFriendlyError } from '@/components/ui';
import { Search, UserSearch, MapPin, Pin, Loader2 } from 'lucide-react';
import {
  loadPinnedSystems, savePinnedSystems, type PinnedSystem,
  loadPinnedCorps, savePinnedCorps, type PinnedCorp,
  loadPinnedAlliances, savePinnedAlliances, type PinnedAlliance,
} from '@/lib/pinnedItems';

const PINNED_STORAGE_KEY = 'gk_pinned_pilots';

export interface PinnedPilot {
  characterId: number;
  name: string;
}

export function loadPinnedPilots(): PinnedPilot[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = localStorage.getItem(PINNED_STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch { return []; }
}

export function savePinnedPilots(pilots: PinnedPilot[]) {
  try { localStorage.setItem(PINNED_STORAGE_KEY, JSON.stringify(pilots)); } catch { /* ignore */ }
}

interface SearchSuggestion {
  id: number;
  name: string;
}

interface UnifiedSuggestion extends SearchSuggestion {
  type: 'pilot' | 'system';
}

export function PilotLookupTab() {
  // ── Unified search state ──
  const [query, setQuery] = useState('');
  const [resolvedId, setResolvedId] = useState<number | null>(null);
  const [resolvedSystem, setResolvedSystem] = useState<{ id: number; name: string } | null>(null);
  const [suggestions, setSuggestions] = useState<UnifiedSuggestion[]>([]);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const [isSearching, setIsSearching] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // ── Deep dive ──
  const [deepDiveId, setDeepDiveId] = useState<number | null>(null);

  // ── Pinned items ──
  const [pinnedPilots, setPinnedPilots] = useState<PinnedPilot[]>([]);
  const [pinnedSystems, setPinnedSystems] = useState<PinnedSystem[]>([]);
  const [pinnedCorps, setPinnedCorps] = useState<PinnedCorp[]>([]);
  const [pinnedAlliances, setPinnedAlliances] = useState<PinnedAlliance[]>([]);

  useEffect(() => {
    setPinnedPilots(loadPinnedPilots());
    setPinnedSystems(loadPinnedSystems());
    setPinnedCorps(loadPinnedCorps());
    setPinnedAlliances(loadPinnedAlliances());
  }, []);

  // ── Pilot pin handlers ──
  const handleTogglePin = useCallback((characterId: number, name: string) => {
    setPinnedPilots((prev) => {
      const exists = prev.some((p) => p.characterId === characterId);
      const next = exists
        ? prev.filter((p) => p.characterId !== characterId)
        : [...prev, { characterId, name }];
      savePinnedPilots(next);
      return next;
    });
  }, []);

  const handleTogglePinSystem = useCallback((systemId: number, name: string) => {
    setPinnedSystems((prev) => {
      const exists = prev.some((s) => s.systemId === systemId);
      const next = exists
        ? prev.filter((s) => s.systemId !== systemId)
        : [...prev, { systemId, name }];
      savePinnedSystems(next);
      return next;
    });
  }, []);

  const handleTogglePinCorp = useCallback((corporationId: number, name: string) => {
    setPinnedCorps((prev) => {
      const exists = prev.some((c) => c.corporationId === corporationId);
      const next = exists
        ? prev.filter((c) => c.corporationId !== corporationId)
        : [...prev, { corporationId, name }];
      savePinnedCorps(next);
      return next;
    });
  }, []);

  const handleTogglePinAlliance = useCallback((allianceId: number, name: string) => {
    setPinnedAlliances((prev) => {
      const exists = prev.some((a) => a.allianceId === allianceId);
      const next = exists
        ? prev.filter((a) => a.allianceId !== allianceId)
        : [...prev, { allianceId, name }];
      savePinnedAlliances(next);
      return next;
    });
  }, []);

  const pinnedCorpIds = useMemo(() => new Set(pinnedCorps.map((c) => c.corporationId)), [pinnedCorps]);
  const pinnedAllianceIds = useMemo(() => new Set(pinnedAlliances.map((a) => a.allianceId)), [pinnedAlliances]);

  // ── Pilot lookup mutation ──
  const {
    mutate: lookupPilot,
    isPending: isPilotPending,
    error: pilotError,
    reset: resetPilot,
  } = useMutation<{ character_id: number }, Error, { name: string; id?: number }>({
    mutationFn: async ({ name, id }) => {
      if (id) return { character_id: id };
      const result = await GatekeeperAPI.fleetPilotLookup([name]);
      if (result.pilots.length === 0) {
        throw new Error(`Could not find pilot "${name}". Check the spelling and try again.`);
      }
      return { character_id: result.pilots[0].character_id };
    },
    onSuccess: (data) => {
      setResolvedId(data.character_id);
    },
  });

  // ── Unified autocomplete — search both pilots and systems in parallel ──
  const handleInputChange = useCallback((value: string) => {
    setQuery(value);
    if (resolvedId) { setResolvedId(null); resetPilot(); }
    if (resolvedSystem) setResolvedSystem(null);
    if (debounceRef.current) clearTimeout(debounceRef.current);

    if (value.trim().length < 2) {
      setSuggestions([]); setIsDropdownOpen(false); return;
    }
    setIsSearching(true);
    debounceRef.current = setTimeout(async () => {
      try {
        const [pilots, systems] = await Promise.all([
          GatekeeperAPI.searchCharacters(value.trim()).catch(() => ({ results: [] })),
          GatekeeperAPI.searchSystemsESI(value.trim()).catch(() => ({ results: [] })),
        ]);
        const merged: UnifiedSuggestion[] = [
          ...systems.results.slice(0, 5).map((s: SearchSuggestion) => ({ ...s, type: 'system' as const })),
          ...pilots.results.slice(0, 5).map((s: SearchSuggestion) => ({ ...s, type: 'pilot' as const })),
        ];
        setSuggestions(merged);
        setIsDropdownOpen(merged.length > 0);
        setActiveIndex(0);
      } catch { setSuggestions([]); setIsDropdownOpen(false); }
      finally { setIsSearching(false); }
    }, 300);
  }, [resolvedId, resolvedSystem, resetPilot]);

  const handleSelect = useCallback((s: UnifiedSuggestion) => {
    setQuery(s.name);
    setSuggestions([]); setIsDropdownOpen(false);
    if (s.type === 'pilot') {
      setResolvedId(null); resetPilot();
      lookupPilot({ name: s.name, id: s.id });
    } else {
      setResolvedSystem(s);
    }
  }, [lookupPilot, resetPilot]);

  const handleSearch = () => {
    const trimmed = query.trim();
    if (!trimmed) return;
    setResolvedId(null); setIsDropdownOpen(false); resetPilot();
    lookupPilot({ name: trimmed });
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (isDropdownOpen && suggestions.length > 0) {
      if (e.key === 'ArrowDown') { e.preventDefault(); setActiveIndex((p) => Math.min(p + 1, suggestions.length - 1)); return; }
      if (e.key === 'ArrowUp') { e.preventDefault(); setActiveIndex((p) => Math.max(p - 1, 0)); return; }
      if (e.key === 'Enter') { e.preventDefault(); if (suggestions[activeIndex]) handleSelect(suggestions[activeIndex]); return; }
      if (e.key === 'Escape') { e.preventDefault(); setIsDropdownOpen(false); return; }
    }
    if (e.key === 'Enter') handleSearch();
  };

  // Scroll active item into view
  useEffect(() => {
    if (listRef.current) {
      const el = listRef.current.children[activeIndex] as HTMLElement | undefined;
      el?.scrollIntoView({ block: 'nearest' });
    }
  }, [activeIndex]);

  // Cleanup debounce on unmount
  useEffect(() => {
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, []);

  return (
    <div className="space-y-6">
      {/* Deep Dive Panel */}
      {deepDiveId && (
        <PilotDeepDive characterId={deepDiveId} onClose={() => setDeepDiveId(null)} />
      )}

      {/* Unified Search */}
      <Card>
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Search className="h-4 w-4 text-text-secondary" />
            <span className="text-sm font-medium text-text">Pilot / System Lookup</span>
          </div>
          <div className="flex gap-2">
            <div className="flex-1 relative">
              <input
                ref={inputRef}
                type="text"
                role="combobox"
                value={query}
                onChange={(e) => handleInputChange(e.target.value)}
                onKeyDown={handleKeyDown}
                onFocus={() => { if (suggestions.length > 0) setIsDropdownOpen(true); }}
                onBlur={() => setTimeout(() => setIsDropdownOpen(false), 150)}
                placeholder="Search pilot or system name..."
                className="w-full px-3 py-2 bg-card border border-border rounded-lg text-sm text-text placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary"
                aria-autocomplete="list"
                aria-expanded={isDropdownOpen}
              />
              {isSearching && (
                <Loader2 className="absolute right-2 top-1/2 -translate-y-1/2 h-4 w-4 text-text-secondary animate-spin" />
              )}
              {isDropdownOpen && suggestions.length > 0 && (
                <div ref={listRef} className="absolute z-50 w-full mt-1 bg-card border border-border rounded-lg shadow-lg max-h-60 overflow-y-auto" role="listbox">
                  {suggestions.map((s, i) => (
                    <button
                      key={`${s.type}-${s.id}`}
                      onClick={() => handleSelect(s)}
                      onMouseEnter={() => setActiveIndex(i)}
                      className={`w-full px-3 py-2 text-left text-sm flex items-center gap-2 transition-colors ${i === activeIndex ? 'bg-primary/20 text-text' : 'hover:bg-card-hover text-text'}`}
                      role="option"
                      aria-selected={i === activeIndex}
                    >
                      {s.type === 'system' ? (
                        <MapPin className="h-3 w-3 text-cyan-400 shrink-0" />
                      ) : (
                        <UserSearch className="h-3 w-3 text-text-secondary shrink-0" />
                      )}
                      <span className="truncate">{s.name}</span>
                      <span className="ml-auto text-[10px] text-text-secondary uppercase tracking-wider">{s.type}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
            <Button onClick={handleSearch} disabled={!query.trim() || isPilotPending} loading={isPilotPending}>
              <Search className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </Card>

      {/* Pilot Error */}
      {pilotError && (
        <ErrorMessage
          title="Pilot lookup failed"
          message={getUserFriendlyError(pilotError)}
          onRetry={handleSearch}
        />
      )}

      {/* Results row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Pilot Result */}
        {resolvedId && (
          <PilotThreatCard
            characterId={resolvedId}
            onPin={handleTogglePin}
            isPinned={pinnedPilots.some((p) => p.characterId === resolvedId)}
            onPinCorp={handleTogglePinCorp}
            onPinAlliance={handleTogglePinAlliance}
            pinnedCorpIds={pinnedCorpIds}
            pinnedAllianceIds={pinnedAllianceIds}
            onDeepDive={setDeepDiveId}
          />
        )}

        {/* System Result */}
        {resolvedSystem && (
          <SystemSummaryCard
            systemName={resolvedSystem.name}
            systemId={resolvedSystem.id}
            onClose={() => { setResolvedSystem(null); setQuery(''); }}
            onPin={handleTogglePinSystem}
            isPinned={pinnedSystems.some((s) => s.systemId === resolvedSystem.id)}
          />
        )}
      </div>

      {/* Pinned Pilots */}
      {pinnedPilots.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Pin className="h-4 w-4 text-cyan-400" />
            <span className="text-sm font-medium text-text">Pinned Pilots ({pinnedPilots.length})</span>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {pinnedPilots.map((p) => (
              <PilotThreatCard
                key={p.characterId}
                characterId={p.characterId}
                onPin={handleTogglePin}
                isPinned
                onClose={() => handleTogglePin(p.characterId, p.name)}
                onPinCorp={handleTogglePinCorp}
                onPinAlliance={handleTogglePinAlliance}
                pinnedCorpIds={pinnedCorpIds}
                pinnedAllianceIds={pinnedAllianceIds}
                onDeepDive={setDeepDiveId}
              />
            ))}
          </div>
        </div>
      )}

      {/* Pinned Systems */}
      {pinnedSystems.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Pin className="h-4 w-4 text-cyan-400" />
            <span className="text-sm font-medium text-text">Pinned Systems ({pinnedSystems.length})</span>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
            {pinnedSystems.map((s) => (
              <SystemSummaryCard
                key={s.systemId}
                systemName={s.name}
                systemId={s.systemId}
                onClose={() => handleTogglePinSystem(s.systemId, s.name)}
                onPin={handleTogglePinSystem}
                isPinned
              />
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {!resolvedId && !resolvedSystem && !isPilotPending && !pilotError && pinnedPilots.length === 0 && pinnedSystems.length === 0 && (
        <Card className="text-center py-12">
          <Search className="h-12 w-12 text-text-secondary mx-auto mb-4" />
          <p className="text-text-secondary mb-2">
            Search for pilots or systems
          </p>
          <p className="text-xs text-text-secondary">
            Look up threat profiles, system intel, and pin items to your watchlist
          </p>
        </Card>
      )}
    </div>
  );
}
