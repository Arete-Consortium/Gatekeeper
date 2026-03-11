'use client';

import { useState } from 'react';
import { Card, Button } from '@/components/ui';
import type { LinkedCharacter } from '@/lib/types';
import { MapPin, Ship, Star, Trash2, CheckCircle } from 'lucide-react';

interface CharacterCardProps {
  character: LinkedCharacter;
  isActiveCharacter: boolean;
  onSetActive: (characterId: number) => void;
  onRemove: (characterId: number) => void;
  isSettingActive?: boolean;
  isRemoving?: boolean;
}

export function CharacterCard({
  character,
  isActiveCharacter,
  onSetActive,
  onRemove,
  isSettingActive = false,
  isRemoving = false,
}: CharacterCardProps) {
  const [confirmRemove, setConfirmRemove] = useState(false);

  const portraitUrl = `https://images.evetech.net/characters/${character.character_id}/portrait?size=128`;

  const handleRemoveClick = () => {
    if (confirmRemove) {
      onRemove(character.character_id);
      setConfirmRemove(false);
    } else {
      setConfirmRemove(true);
    }
  };

  const handleCancelRemove = () => {
    setConfirmRemove(false);
  };

  return (
    <Card
      className={`p-4 relative ${
        isActiveCharacter ? 'ring-2 ring-primary border-primary' : ''
      }`}
      data-testid={`character-card-${character.character_id}`}
    >
      {/* Active indicator */}
      {isActiveCharacter && (
        <div className="absolute top-2 right-2">
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold bg-primary/20 text-primary">
            <Star className="h-3 w-3" />
            Active
          </span>
        </div>
      )}

      <div className="flex gap-4">
        {/* Portrait */}
        <div className="flex-shrink-0">
          <img
            src={portraitUrl}
            alt={`${character.character_name} portrait`}
            width={80}
            height={80}
            className="rounded-lg border border-border"
            loading="lazy"
          />
        </div>

        {/* Character info */}
        <div className="flex-1 min-w-0">
          <h3 className="text-lg font-bold text-text truncate">
            {character.character_name}
          </h3>

          <p className="text-sm text-text-secondary mt-0.5">
            ID: {character.character_id}
          </p>

          {/* Location */}
          {character.location && character.location.solar_system_name && (
            <div className="flex items-center gap-1.5 mt-2 text-sm text-text-secondary">
              <MapPin className="h-3.5 w-3.5 flex-shrink-0" />
              <span className="truncate">
                {character.location.solar_system_name}
                {character.location.region_name && (
                  <span className="text-text-secondary/60">
                    {' '}({character.location.region_name})
                  </span>
                )}
              </span>
            </div>
          )}

          {/* Auth status */}
          <div className="flex items-center gap-1.5 mt-1 text-sm">
            {character.is_active ? (
              <span className="text-risk-green flex items-center gap-1">
                <CheckCircle className="h-3.5 w-3.5" />
                Authenticated
              </span>
            ) : (
              <span className="text-risk-orange">Token expired</span>
            )}
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-2 mt-4 pt-3 border-t border-border">
        {!isActiveCharacter && (
          <Button
            size="sm"
            onClick={() => onSetActive(character.character_id)}
            loading={isSettingActive}
            disabled={!character.is_active}
          >
            <Star className="mr-1.5 h-3.5 w-3.5" />
            Set Active
          </Button>
        )}

        {confirmRemove ? (
          <div className="flex gap-2 ml-auto">
            <Button size="sm" variant="secondary" onClick={handleCancelRemove}>
              Cancel
            </Button>
            <Button
              size="sm"
              variant="secondary"
              className="text-risk-red border-risk-red/30 hover:bg-risk-red/10"
              onClick={handleRemoveClick}
              loading={isRemoving}
            >
              Confirm Remove
            </Button>
          </div>
        ) : (
          <Button
            size="sm"
            variant="secondary"
            className="ml-auto text-risk-red/70 hover:text-risk-red"
            onClick={handleRemoveClick}
          >
            <Trash2 className="mr-1.5 h-3.5 w-3.5" />
            Remove
          </Button>
        )}
      </div>
    </Card>
  );
}
