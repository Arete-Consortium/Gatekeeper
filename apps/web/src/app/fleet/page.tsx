'use client';

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { GatekeeperAPI } from '@/lib/api';
import { Card, Button, Textarea } from '@/components/ui';
import { FleetResult } from '@/components/fleet';
import type { FleetAnalysisResponse } from '@/lib/types';
import { Users, Clipboard } from 'lucide-react';
import { ErrorMessage, getUserFriendlyError } from '@/components/ui';

const EXAMPLE_FLEET = `3x Muninn
2x Scimitar
2x Sabre
1x Loki
1x Huginn
1x Falcon
1x Stiletto`;

export default function FleetPage() {
  const [fleetText, setFleetText] = useState('');
  const [clipboardError, setClipboardError] = useState(false);

  const {
    mutate: analyzeFleet,
    data: analysis,
    isPending,
    error,
    reset,
  } = useMutation<FleetAnalysisResponse, Error, string>({
    mutationFn: (text) => GatekeeperAPI.analyzeFleet(text),
  });

  const handleAnalyze = () => {
    if (fleetText.trim()) {
      analyzeFleet(fleetText);
    }
  };

  const handlePaste = async () => {
    try {
      setClipboardError(false);
      const text = await navigator.clipboard.readText();
      setFleetText(text);
      reset();
    } catch {
      setClipboardError(true);
    }
  };

  const handleLoadExample = () => {
    setFleetText(EXAMPLE_FLEET);
    reset();
  };

  const handleClear = () => {
    setFleetText('');
    reset();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-text">Fleet Analyzer</h1>
        <p className="text-text-secondary mt-1">
          Paste a fleet composition to get a threat assessment
        </p>
      </div>

      {/* Input Form */}
      <Card>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <label className="block text-sm font-medium text-text-secondary">
              Fleet Composition
            </label>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={handlePaste}
                className="text-xs text-primary hover:text-primary-hover flex items-center gap-1 rounded px-1 py-0.5 focus:outline-none focus:ring-2 focus:ring-primary"
                aria-label="Paste fleet from clipboard"
              >
                <Clipboard className="h-3 w-3" aria-hidden="true" />
                Paste
              </button>
              <button
                type="button"
                onClick={handleLoadExample}
                className="text-xs text-text-secondary hover:text-text rounded px-1 py-0.5 focus:outline-none focus:ring-2 focus:ring-primary"
                aria-label="Load example fleet"
              >
                Load Example
              </button>
              {fleetText && (
                <button
                  type="button"
                  onClick={handleClear}
                  className="text-xs text-text-secondary hover:text-text rounded px-1 py-0.5 focus:outline-none focus:ring-2 focus:ring-primary"
                  aria-label="Clear fleet text"
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
              reset();
            }}
            placeholder={`Paste fleet composition here...

Supported formats:
  3x Muninn
  2x Scimitar
  1x Sabre

Or tab-separated from EVE fleet window:
  PilotName\\tShipType\\tSystem\\tPosition`}
            className="min-h-[200px]"
          />

          <Button
            onClick={handleAnalyze}
            disabled={!fleetText.trim() || isPending}
            loading={isPending}
          >
            <Users className="mr-2 h-4 w-4" />
            Analyze Fleet
          </Button>
        </div>
      </Card>

      {/* Error State */}
      {error && (
        <ErrorMessage
          title="Unable to analyze fleet"
          message={getUserFriendlyError(error)}
          onRetry={handleAnalyze}
        />
      )}

      {/* Results */}
      {analysis && <FleetResult analysis={analysis} />}

      {/* Empty State */}
      {!analysis && !isPending && !error && (
        <Card className="text-center py-12">
          <Users className="h-12 w-12 text-text-secondary mx-auto mb-4" />
          <p className="text-text-secondary mb-2">
            Paste a fleet composition to analyze threats
          </p>
          <p className="text-xs text-text-secondary">
            Copy from EVE fleet window or type ship counts manually
          </p>
        </Card>
      )}
    </div>
  );
}
