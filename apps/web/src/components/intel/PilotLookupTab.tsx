'use client';

import { useState, useCallback, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import { GatekeeperAPI } from '@/lib/api';
import { Card, Button, Input } from '@/components/ui';
import { PilotThreatCard } from './PilotThreatCard';
import { ErrorMessage, getUserFriendlyError } from '@/components/ui';
import { Search, UserSearch, Pin, X } from 'lucide-react';
import type { PilotThreatStats } from '@/lib/types';

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

export function PilotLookupTab() {
  const [pilotName, setPilotName] = useState('');
  const [resolvedId, setResolvedId] = useState<number | null>(null);
  const [pinnedPilots, setPinnedPilots] = useState<PinnedPilot[]>([]);

  // Load pinned pilots on mount
  useEffect(() => {
    setPinnedPilots(loadPinnedPilots());
  }, []);

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

  const {
    mutate: lookupPilot,
    isPending,
    error,
    reset,
  } = useMutation<{ character_id: number }, Error, string>({
    mutationFn: async (name: string) => {
      // Use fleet lookup with a single name to resolve → get character_id
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

  const handleSearch = () => {
    const trimmed = pilotName.trim();
    if (!trimmed) return;
    setResolvedId(null);
    reset();
    lookupPilot(trimmed);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleSearch();
  };

  const handleClear = () => {
    setPilotName('');
    setResolvedId(null);
    reset();
  };

  return (
    <div className="space-y-6">
      {/* Search Form */}
      <Card>
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <UserSearch className="h-4 w-4 text-text-secondary" />
            <span className="text-sm font-medium text-text">Pilot Threat Lookup</span>
          </div>

          <div className="flex gap-2">
            <div className="flex-1">
              <Input
                value={pilotName}
                onChange={(e) => {
                  setPilotName(e.target.value);
                  if (resolvedId) {
                    setResolvedId(null);
                    reset();
                  }
                }}
                onKeyDown={handleKeyDown}
                placeholder="Enter pilot name..."
              />
            </div>
            <Button
              onClick={handleSearch}
              disabled={!pilotName.trim() || isPending}
              loading={isPending}
            >
              <Search className="mr-2 h-4 w-4" />
              Look Up
            </Button>
            {(pilotName || resolvedId) && (
              <Button variant="secondary" onClick={handleClear}>
                Clear
              </Button>
            )}
          </div>

          <p className="text-xs text-text-secondary">
            Enter an exact EVE character name to view their threat profile, kill stats, and behavior flags.
          </p>
        </div>
      </Card>

      {/* Error */}
      {error && (
        <ErrorMessage
          title="Pilot lookup failed"
          message={getUserFriendlyError(error)}
          onRetry={handleSearch}
        />
      )}

      {/* Result */}
      {resolvedId && (
        <PilotThreatCard
          characterId={resolvedId}
          onPin={handleTogglePin}
          isPinned={pinnedPilots.some((p) => p.characterId === resolvedId)}
        />
      )}

      {/* Pinned Pilots */}
      {pinnedPilots.length > 0 && (
        <div className="space-y-4">
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
              />
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {!resolvedId && !isPending && !error && (
        <Card className="text-center py-12">
          <UserSearch className="h-12 w-12 text-text-secondary mx-auto mb-4" />
          <p className="text-text-secondary mb-2">
            Search for any EVE Online pilot by name
          </p>
          <p className="text-xs text-text-secondary">
            View kills, losses, K/D ratio, threat level, behavior flags, and top ships
          </p>
        </Card>
      )}
    </div>
  );
}
