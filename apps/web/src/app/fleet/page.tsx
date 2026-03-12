'use client';

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { GatekeeperAPI } from '@/lib/api';
import { Card, Button, Textarea } from '@/components/ui';
import { FleetResult } from '@/components/fleet';
import { PilotThreatCard } from '@/components/intel/PilotThreatCard';
import { PilotDeepDive } from '@/components/intel/PilotDeepDive';
import type { FleetAnalysisResponse, FleetPilotLookupResponse } from '@/lib/types';
import { Users, Clipboard, UserSearch, Ship } from 'lucide-react';
import { ErrorMessage, getUserFriendlyError, Badge } from '@/components/ui';

const EXAMPLE_FLEET = `3x Muninn
2x Scimitar
2x Sabre
1x Loki
1x Huginn
1x Falcon
1x Stiletto`;

const EXAMPLE_PILOTS = `PilotAlpha
PilotBravo
PilotCharlie`;

type InputMode = 'ships' | 'pilots';

export default function FleetPage() {
  const [inputMode, setInputMode] = useState<InputMode>('ships');
  const [fleetText, setFleetText] = useState('');
  const [clipboardError, setClipboardError] = useState(false);
  const [deepDiveId, setDeepDiveId] = useState<number | null>(null);

  const {
    mutate: analyzeFleet,
    data: analysis,
    isPending: fleetPending,
    error: fleetError,
    reset: resetFleet,
  } = useMutation<FleetAnalysisResponse, Error, string>({
    mutationFn: (text) => GatekeeperAPI.analyzeFleet(text),
  });

  const {
    mutate: lookupPilots,
    data: pilotData,
    isPending: pilotPending,
    error: pilotError,
    reset: resetPilots,
  } = useMutation<FleetPilotLookupResponse, Error, string[]>({
    mutationFn: (names) => GatekeeperAPI.fleetPilotLookup(names),
  });

  const isPending = inputMode === 'ships' ? fleetPending : pilotPending;
  const error = inputMode === 'ships' ? fleetError : pilotError;

  const handleAnalyze = () => {
    if (!fleetText.trim()) return;
    if (inputMode === 'ships') {
      analyzeFleet(fleetText);
    } else {
      const names = fleetText
        .split('\n')
        .map((n) => n.trim())
        .filter(Boolean);
      if (names.length > 0) lookupPilots(names);
    }
  };

  const handlePaste = async () => {
    try {
      setClipboardError(false);
      const text = await navigator.clipboard.readText();
      setFleetText(text);
      resetFleet();
      resetPilots();
    } catch {
      setClipboardError(true);
    }
  };

  const handleLoadExample = () => {
    setFleetText(inputMode === 'ships' ? EXAMPLE_FLEET : EXAMPLE_PILOTS);
    resetFleet();
    resetPilots();
  };

  const handleClear = () => {
    setFleetText('');
    resetFleet();
    resetPilots();
  };

  const handleModeSwitch = (mode: InputMode) => {
    setInputMode(mode);
    setFleetText('');
    resetFleet();
    resetPilots();
  };

  return (
    <div className="space-y-6">
      {/* Deep Dive Panel */}
      {deepDiveId && (
        <PilotDeepDive characterId={deepDiveId} onClose={() => setDeepDiveId(null)} />
      )}

      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-text">Fleet Analyzer</h1>
        <p className="text-text-secondary mt-1">
          Analyze fleet composition or look up pilot threats
        </p>
      </div>

      {/* Input Form */}
      <Card>
        <div className="space-y-4">
          {/* Mode Toggle */}
          <div className="flex items-center gap-1 p-1 bg-background rounded-lg w-fit">
            <button
              onClick={() => handleModeSwitch('ships')}
              className={`flex items-center gap-2 px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                inputMode === 'ships'
                  ? 'bg-primary text-white'
                  : 'text-text-secondary hover:text-text'
              }`}
            >
              <Ship className="h-3.5 w-3.5" />
              Ship Composition
            </button>
            <button
              onClick={() => handleModeSwitch('pilots')}
              className={`flex items-center gap-2 px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                inputMode === 'pilots'
                  ? 'bg-primary text-white'
                  : 'text-text-secondary hover:text-text'
              }`}
            >
              <UserSearch className="h-3.5 w-3.5" />
              Pilot Names
            </button>
          </div>

          <div className="flex items-center justify-between">
            <label className="block text-sm font-medium text-text-secondary">
              {inputMode === 'ships' ? 'Fleet Composition' : 'Pilot Names (one per line)'}
            </label>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={handlePaste}
                className="text-xs text-primary hover:text-primary-hover flex items-center gap-1 rounded px-1 py-0.5 focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <Clipboard className="h-3 w-3" />
                Paste
              </button>
              <button
                type="button"
                onClick={handleLoadExample}
                className="text-xs text-text-secondary hover:text-text rounded px-1 py-0.5 focus:outline-none focus:ring-2 focus:ring-primary"
              >
                Load Example
              </button>
              {fleetText && (
                <button
                  type="button"
                  onClick={handleClear}
                  className="text-xs text-text-secondary hover:text-text rounded px-1 py-0.5 focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  Clear
                </button>
              )}
            </div>
          </div>

          {clipboardError && (
            <p className="text-xs text-risk-orange">
              Clipboard access denied. Try Ctrl+V to paste directly into the text area.
            </p>
          )}

          <Textarea
            value={fleetText}
            onChange={(e) => {
              setFleetText(e.target.value);
              resetFleet();
              resetPilots();
            }}
            placeholder={
              inputMode === 'ships'
                ? `Paste fleet composition here...

Supported formats:
  3x Muninn
  2x Scimitar
  1x Sabre

Or tab-separated from EVE fleet window:
  PilotName\tShipType\tSystem\tPosition`
                : `Paste pilot names here (one per line)...

Copy from EVE local or fleet member list:
  PilotAlpha
  PilotBravo
  PilotCharlie`
            }
            className="min-h-[200px]"
          />

          <Button
            onClick={handleAnalyze}
            disabled={!fleetText.trim() || isPending}
            loading={isPending}
          >
            {inputMode === 'ships' ? (
              <>
                <Users className="mr-2 h-4 w-4" />
                Analyze Fleet
              </>
            ) : (
              <>
                <UserSearch className="mr-2 h-4 w-4" />
                Look Up Pilots
              </>
            )}
          </Button>
        </div>
      </Card>

      {/* Error State */}
      {error && (
        <ErrorMessage
          title={inputMode === 'ships' ? 'Unable to analyze fleet' : 'Unable to look up pilots'}
          message={getUserFriendlyError(error)}
          onRetry={handleAnalyze}
        />
      )}

      {/* Ship Composition Results */}
      {inputMode === 'ships' && analysis && <FleetResult analysis={analysis} />}

      {/* Pilot Lookup Results */}
      {inputMode === 'pilots' && pilotData && (
        <div className="space-y-6">
          {/* Aggregate Summary */}
          <Card>
            <h3 className="text-sm font-semibold text-text-secondary uppercase tracking-wide mb-4">
              Fleet Threat Summary
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-4">
              <div className="text-center p-3 bg-background rounded-lg">
                <div className="text-xs text-text-secondary uppercase mb-1">Resolved</div>
                <div className="text-2xl font-bold text-text">
                  {pilotData.resolved}/{pilotData.total_pilots}
                </div>
              </div>
              <div className="text-center p-3 bg-background rounded-lg">
                <div className="text-xs text-text-secondary uppercase mb-1">Avg K/D</div>
                <div className="text-2xl font-bold text-text">{pilotData.aggregate.avg_kd}</div>
              </div>
              <div className="text-center p-3 bg-background rounded-lg">
                <div className="text-xs text-text-secondary uppercase mb-1">Total Kills</div>
                <div className="text-2xl font-bold text-red-400">
                  {pilotData.aggregate.total_kills.toLocaleString()}
                </div>
              </div>
              <div className="text-center p-3 bg-background rounded-lg">
                <div className="text-xs text-text-secondary uppercase mb-1">Total Losses</div>
                <div className="text-2xl font-bold text-blue-400">
                  {pilotData.aggregate.total_losses.toLocaleString()}
                </div>
              </div>
            </div>

            {/* Threat breakdown */}
            <div className="flex flex-wrap gap-2 mb-3">
              {Object.entries(pilotData.aggregate.threat_breakdown).map(([level, count]) => (
                <Badge
                  key={level}
                  variant={
                    level === 'extreme' || level === 'high' ? 'danger' :
                    level === 'moderate' ? 'warning' :
                    level === 'low' ? 'info' : 'success'
                  }
                  size="md"
                >
                  {count} {level}
                </Badge>
              ))}
            </div>

            {/* TZ breakdown */}
            {Object.keys(pilotData.aggregate.timezone_breakdown).length > 0 && (
              <div className="flex items-center gap-3 text-xs text-text-secondary">
                <span className="font-medium">Active TZ:</span>
                {Object.entries(pilotData.aggregate.timezone_breakdown).map(([tz, count]) => (
                  <span key={tz}>{tz}: {count}</span>
                ))}
              </div>
            )}

            {/* Flag counts */}
            {Object.keys(pilotData.aggregate.flag_counts).length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-2">
                {Object.entries(pilotData.aggregate.flag_counts).map(([flag, count]) => (
                  <Badge key={flag} variant="warning" size="sm">
                    {count}x {flag.replace('_', ' ')}
                  </Badge>
                ))}
              </div>
            )}
          </Card>

          {/* Failed names */}
          {pilotData.failed_names.length > 0 && (
            <Card>
              <div className="text-sm text-text-secondary mb-2">
                Could not resolve {pilotData.failed_names.length} name{pilotData.failed_names.length > 1 ? 's' : ''}:
              </div>
              <div className="flex flex-wrap gap-1.5">
                {pilotData.failed_names.map((name) => (
                  <Badge key={name} variant="danger" size="sm">{name}</Badge>
                ))}
              </div>
            </Card>
          )}

          {/* Individual pilot cards */}
          <div>
            <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-3">
              Individual Pilots ({pilotData.pilots.length})
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {pilotData.pilots.map((pilot) => (
                <PilotThreatCard
                  key={pilot.character_id}
                  characterId={pilot.character_id}
                  onDeepDive={setDeepDiveId}
                />
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Empty State */}
      {!analysis && !pilotData && !isPending && !error && (
        <Card className="text-center py-12">
          <Users className="h-12 w-12 text-text-secondary mx-auto mb-4" />
          <p className="text-text-secondary mb-2">
            {inputMode === 'ships'
              ? 'Paste a fleet composition to analyze threats'
              : 'Paste pilot names to look up their threat profiles'
            }
          </p>
          <p className="text-xs text-text-secondary">
            {inputMode === 'ships'
              ? 'Copy from EVE fleet window or type ship counts manually'
              : 'One name per line — copy from EVE local or fleet member list'
            }
          </p>
        </Card>
      )}
    </div>
  );
}
