'use client';

import { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import { useMutation } from '@tanstack/react-query';
import { GatekeeperAPI } from '@/lib/api';
import { Card, Button } from '@/components/ui';
import { PilotThreatCard } from './PilotThreatCard';
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

export function PilotLookupTab() {
  // ── Pilot search state ──
  const [pilotName, setPilotName] = useState('');
  const [resolvedId, setResolvedId] = useState<number | null>(null);
  const [pilotSuggestions, setPilotSuggestions] = useState<SearchSuggestion[]>([]);
  const [isPilotDropdownOpen, setIsPilotDropdownOpen] = useState(false);
  const [pilotActiveIndex, setPilotActiveIndex] = useState(0);
  const [isPilotSearching, setIsPilotSearching] = useState(false);
  const pilotDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pilotInputRef = useRef<HTMLInputElement>(null);
  const pilotListRef = useRef<HTMLDivElement>(null);

  // ── System search state ──
  const [systemQuery, setSystemQuery] = useState('');
  const [resolvedSystem, setResolvedSystem] = useState<{ id: number; name: string } | null>(null);
  const [systemSuggestions, setSystemSuggestions] = useState<SearchSuggestion[]>([]);
  const [isSystemDropdownOpen, setIsSystemDropdownOpen] = useState(false);
  const [systemActiveIndex, setSystemActiveIndex] = useState(0);
  const [isSystemSearching, setIsSystemSearching] = useState(false);
  const systemDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const systemListRef = useRef<HTMLDivElement>(null);

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

  // ── Pilot autocomplete ──
  const handlePilotInputChange = useCallback((value: string) => {
    setPilotName(value);
    if (resolvedId) { setResolvedId(null); resetPilot(); }
    if (pilotDebounceRef.current) clearTimeout(pilotDebounceRef.current);

    if (value.trim().length < 3) {
      setPilotSuggestions([]); setIsPilotDropdownOpen(false); return;
    }
    setIsPilotSearching(true);
    pilotDebounceRef.current = setTimeout(async () => {
      try {
        const data = await GatekeeperAPI.searchCharacters(value.trim());
        setPilotSuggestions(data.results);
        setIsPilotDropdownOpen(data.results.length > 0);
        setPilotActiveIndex(0);
      } catch { setPilotSuggestions([]); setIsPilotDropdownOpen(false); }
      finally { setIsPilotSearching(false); }
    }, 300);
  }, [resolvedId, resetPilot]);

  const handleSelectPilot = useCallback((s: SearchSuggestion) => {
    setPilotName(s.name);
    setPilotSuggestions([]); setIsPilotDropdownOpen(false);
    setResolvedId(null); resetPilot();
    lookupPilot({ name: s.name, id: s.id });
  }, [lookupPilot, resetPilot]);

  const handlePilotSearch = () => {
    const trimmed = pilotName.trim();
    if (!trimmed) return;
    setResolvedId(null); setIsPilotDropdownOpen(false); resetPilot();
    lookupPilot({ name: trimmed });
  };

  const handlePilotKeyDown = (e: React.KeyboardEvent) => {
    if (isPilotDropdownOpen && pilotSuggestions.length > 0) {
      if (e.key === 'ArrowDown') { e.preventDefault(); setPilotActiveIndex((p) => Math.min(p + 1, pilotSuggestions.length - 1)); return; }
      if (e.key === 'ArrowUp') { e.preventDefault(); setPilotActiveIndex((p) => Math.max(p - 1, 0)); return; }
      if (e.key === 'Enter') { e.preventDefault(); if (pilotSuggestions[pilotActiveIndex]) handleSelectPilot(pilotSuggestions[pilotActiveIndex]); return; }
      if (e.key === 'Escape') { e.preventDefault(); setIsPilotDropdownOpen(false); return; }
    }
    if (e.key === 'Enter') handlePilotSearch();
  };

  // ── System autocomplete ──
  const handleSystemInputChange = useCallback((value: string) => {
    setSystemQuery(value);
    if (resolvedSystem) setResolvedSystem(null);
    if (systemDebounceRef.current) clearTimeout(systemDebounceRef.current);

    if (value.trim().length < 3) {
      setSystemSuggestions([]); setIsSystemDropdownOpen(false); return;
    }
    setIsSystemSearching(true);
    systemDebounceRef.current = setTimeout(async () => {
      try {
        const data = await GatekeeperAPI.searchSystemsESI(value.trim());
        setSystemSuggestions(data.results);
        setIsSystemDropdownOpen(data.results.length > 0);
        setSystemActiveIndex(0);
      } catch { setSystemSuggestions([]); setIsSystemDropdownOpen(false); }
      finally { setIsSystemSearching(false); }
    }, 300);
  }, [resolvedSystem]);

  const handleSelectSystem = useCallback((s: SearchSuggestion) => {
    setSystemQuery(s.name);
    setSystemSuggestions([]); setIsSystemDropdownOpen(false);
    setResolvedSystem(s);
  }, []);

  const handleSystemKeyDown = (e: React.KeyboardEvent) => {
    if (isSystemDropdownOpen && systemSuggestions.length > 0) {
      if (e.key === 'ArrowDown') { e.preventDefault(); setSystemActiveIndex((p) => Math.min(p + 1, systemSuggestions.length - 1)); return; }
      if (e.key === 'ArrowUp') { e.preventDefault(); setSystemActiveIndex((p) => Math.max(p - 1, 0)); return; }
      if (e.key === 'Enter') { e.preventDefault(); if (systemSuggestions[systemActiveIndex]) handleSelectSystem(systemSuggestions[systemActiveIndex]); return; }
      if (e.key === 'Escape') { e.preventDefault(); setIsSystemDropdownOpen(false); return; }
    }
  };

  // Scroll active items into view
  useEffect(() => {
    if (pilotListRef.current) {
      const el = pilotListRef.current.children[pilotActiveIndex] as HTMLElement | undefined;
      el?.scrollIntoView({ block: 'nearest' });
    }
  }, [pilotActiveIndex]);

  useEffect(() => {
    if (systemListRef.current) {
      const el = systemListRef.current.children[systemActiveIndex] as HTMLElement | undefined;
      el?.scrollIntoView({ block: 'nearest' });
    }
  }, [systemActiveIndex]);

  // Cleanup debounce on unmount
  useEffect(() => {
    return () => {
      if (pilotDebounceRef.current) clearTimeout(pilotDebounceRef.current);
      if (systemDebounceRef.current) clearTimeout(systemDebounceRef.current);
    };
  }, []);

  return (
    <div className="space-y-6">
      {/* Search Forms - side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Pilot Search */}
        <Card>
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <UserSearch className="h-4 w-4 text-text-secondary" />
              <span className="text-sm font-medium text-text">Pilot Lookup</span>
            </div>
            <div className="flex gap-2">
              <div className="flex-1 relative">
                <input
                  ref={pilotInputRef}
                  type="text"
                  role="combobox"
                  value={pilotName}
                  onChange={(e) => handlePilotInputChange(e.target.value)}
                  onKeyDown={handlePilotKeyDown}
                  onFocus={() => { if (pilotSuggestions.length > 0) setIsPilotDropdownOpen(true); }}
                  onBlur={() => setTimeout(() => setIsPilotDropdownOpen(false), 150)}
                  placeholder="Search pilot name..."
                  className="w-full px-3 py-2 bg-card border border-border rounded-lg text-sm text-text placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary"
                  aria-autocomplete="list"
                  aria-expanded={isPilotDropdownOpen}
                />
                {isPilotSearching && (
                  <Loader2 className="absolute right-2 top-1/2 -translate-y-1/2 h-4 w-4 text-text-secondary animate-spin" />
                )}
                {isPilotDropdownOpen && pilotSuggestions.length > 0 && (
                  <div ref={pilotListRef} className="absolute z-50 w-full mt-1 bg-card border border-border rounded-lg shadow-lg max-h-60 overflow-y-auto" role="listbox">
                    {pilotSuggestions.map((s, i) => (
                      <button
                        key={s.id}
                        onClick={() => handleSelectPilot(s)}
                        onMouseEnter={() => setPilotActiveIndex(i)}
                        className={`w-full px-3 py-2 text-left text-sm flex items-center gap-2 transition-colors ${i === pilotActiveIndex ? 'bg-primary/20 text-text' : 'hover:bg-card-hover text-text'}`}
                        role="option"
                        aria-selected={i === pilotActiveIndex}
                      >
                        <UserSearch className="h-3 w-3 text-text-secondary shrink-0" />
                        <span className="truncate">{s.name}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
              <Button onClick={handlePilotSearch} disabled={!pilotName.trim() || isPilotPending} loading={isPilotPending}>
                <Search className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </Card>

        {/* System Search */}
        <Card>
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <MapPin className="h-4 w-4 text-text-secondary" />
              <span className="text-sm font-medium text-text">System Lookup</span>
            </div>
            <div className="flex gap-2">
              <div className="flex-1 relative">
                <input
                  type="text"
                  role="combobox"
                  value={systemQuery}
                  onChange={(e) => handleSystemInputChange(e.target.value)}
                  onKeyDown={handleSystemKeyDown}
                  onFocus={() => { if (systemSuggestions.length > 0) setIsSystemDropdownOpen(true); }}
                  onBlur={() => setTimeout(() => setIsSystemDropdownOpen(false), 150)}
                  placeholder="Search system name..."
                  className="w-full px-3 py-2 bg-card border border-border rounded-lg text-sm text-text placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary"
                  aria-autocomplete="list"
                  aria-expanded={isSystemDropdownOpen}
                />
                {isSystemSearching && (
                  <Loader2 className="absolute right-2 top-1/2 -translate-y-1/2 h-4 w-4 text-text-secondary animate-spin" />
                )}
                {isSystemDropdownOpen && systemSuggestions.length > 0 && (
                  <div ref={systemListRef} className="absolute z-50 w-full mt-1 bg-card border border-border rounded-lg shadow-lg max-h-60 overflow-y-auto" role="listbox">
                    {systemSuggestions.map((s, i) => (
                      <button
                        key={s.id}
                        onClick={() => handleSelectSystem(s)}
                        onMouseEnter={() => setSystemActiveIndex(i)}
                        className={`w-full px-3 py-2 text-left text-sm flex items-center gap-2 transition-colors ${i === systemActiveIndex ? 'bg-primary/20 text-text' : 'hover:bg-card-hover text-text'}`}
                        role="option"
                        aria-selected={i === systemActiveIndex}
                      >
                        <MapPin className="h-3 w-3 text-text-secondary shrink-0" />
                        <span className="truncate">{s.name}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Pilot Error */}
      {pilotError && (
        <ErrorMessage
          title="Pilot lookup failed"
          message={getUserFriendlyError(pilotError)}
          onRetry={handlePilotSearch}
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
          />
        )}

        {/* System Result */}
        {resolvedSystem && (
          <SystemSummaryCard
            systemName={resolvedSystem.name}
            systemId={resolvedSystem.id}
            onClose={() => { setResolvedSystem(null); setSystemQuery(''); }}
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
