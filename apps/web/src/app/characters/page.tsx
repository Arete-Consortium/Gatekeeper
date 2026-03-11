'use client';

import { Suspense, useCallback, useEffect, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import { Card, Button } from '@/components/ui';
import { CharacterCard } from '@/components/characters/CharacterCard';
import { GatekeeperAPI } from '@/lib/api';
import type { LinkedCharacter } from '@/lib/types';
import { UserPlus, Users } from 'lucide-react';

export default function CharactersPage() {
  return (
    <Suspense fallback={<div className="text-center py-8 text-text-secondary">Loading...</div>}>
      <CharactersContent />
    </Suspense>
  );
}

function CharactersContent() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const [characters, setCharacters] = useState<LinkedCharacter[]>([]);
  const [activeCharacterId, setActiveCharacterId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [settingActiveId, setSettingActiveId] = useState<number | null>(null);
  const [removingId, setRemovingId] = useState<number | null>(null);

  const sessionId = typeof window !== 'undefined'
    ? (localStorage.getItem('gk_session_id') || createSessionId())
    : 'server';

  const fetchCharacters = useCallback(async () => {
    try {
      setError(null);
      const response = await GatekeeperAPI.getLinkedCharacters(sessionId);
      setCharacters(response.characters);
      setActiveCharacterId(response.active_character_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load characters');
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.replace('/login');
      return;
    }
    if (isAuthenticated) {
      fetchCharacters();
    }
  }, [isAuthenticated, authLoading, router, fetchCharacters]);

  const handleAddCharacter = async () => {
    try {
      const response = await GatekeeperAPI.linkCharacter();
      window.location.href = response.auth_url;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start SSO flow');
    }
  };

  const handleSetActive = async (characterId: number) => {
    setSettingActiveId(characterId);
    try {
      await GatekeeperAPI.setActiveCharacter(characterId, sessionId);
      setActiveCharacterId(characterId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to set active character');
    } finally {
      setSettingActiveId(null);
    }
  };

  const handleRemove = async (characterId: number) => {
    setRemovingId(characterId);
    try {
      await GatekeeperAPI.unlinkCharacter(characterId);
      setCharacters((prev) => prev.filter((c) => c.character_id !== characterId));
      if (activeCharacterId === characterId) {
        setActiveCharacterId(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to remove character');
    } finally {
      setRemovingId(null);
    }
  };

  if (authLoading || loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Card className="max-w-md w-full text-center py-8">
          <div className="animate-pulse">
            <p className="text-text-secondary">Loading characters...</p>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Users className="h-6 w-6 text-primary" />
          <h1 className="text-2xl font-bold text-text">Characters</h1>
          <span className="text-sm text-text-secondary">
            ({characters.length} linked)
          </span>
        </div>
        <Button onClick={handleAddCharacter}>
          <UserPlus className="mr-2 h-4 w-4" />
          Add Character
        </Button>
      </div>

      {/* Error */}
      {error && (
        <Card className="border-risk-red/40 bg-risk-red/10 text-center py-3">
          <p className="text-risk-red text-sm">{error}</p>
        </Card>
      )}

      {/* Character grid */}
      {characters.length === 0 ? (
        <Card className="text-center py-12 px-8">
          <Users className="h-12 w-12 text-text-secondary/40 mx-auto mb-4" />
          <h2 className="text-lg font-bold text-text mb-2">No Characters Linked</h2>
          <p className="text-text-secondary mb-6">
            Add your EVE Online characters to track their locations and switch between alts.
          </p>
          <Button onClick={handleAddCharacter}>
            <UserPlus className="mr-2 h-4 w-4" />
            Add Your First Character
          </Button>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-1 md:grid-cols-2">
          {characters.map((character) => (
            <CharacterCard
              key={character.character_id}
              character={character}
              isActiveCharacter={character.character_id === activeCharacterId}
              onSetActive={handleSetActive}
              onRemove={handleRemove}
              isSettingActive={settingActiveId === character.character_id}
              isRemoving={removingId === character.character_id}
            />
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * Generate and persist a session ID for multi-character tracking.
 */
function createSessionId(): string {
  const id = crypto.randomUUID();
  localStorage.setItem('gk_session_id', id);
  return id;
}
