'use client';

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { GatekeeperAPI } from '@/lib/api';
import { Card, Button, Textarea } from '@/components/ui';
import { FittingResult } from '@/components/fitting';
import type { FittingAnalysisResponse } from '@/lib/types';
import { Wrench, Clipboard } from 'lucide-react';
import { ErrorMessage, getUserFriendlyError } from '@/components/ui';

const EXAMPLE_FITTING = `[Heron, Explorer]

Nanofiber Internal Structure II
Nanofiber Internal Structure II

5MN Y-T8 Compact Microwarpdrive
Data Analyzer I
Relic Analyzer I
Cargo Scanner I

Core Probe Launcher I
Prototype Cloaking Device I

Small Gravity Capacitor Upgrade I
Small Gravity Capacitor Upgrade I
`;

export default function FittingPage() {
  const [eftText, setEftText] = useState('');
  const [clipboardError, setClipboardError] = useState(false);

  const {
    mutate: analyzeFitting,
    data: analysis,
    isPending,
    error,
    reset,
  } = useMutation<FittingAnalysisResponse, Error, string>({
    mutationFn: (text) => GatekeeperAPI.analyzeFitting(text),
  });

  const handleAnalyze = () => {
    if (eftText.trim()) {
      analyzeFitting(eftText);
    }
  };

  const handlePaste = async () => {
    try {
      setClipboardError(false);
      const text = await navigator.clipboard.readText();
      setEftText(text);
      reset();
    } catch {
      setClipboardError(true);
    }
  };

  const handleLoadExample = () => {
    setEftText(EXAMPLE_FITTING);
    reset();
  };

  const handleClear = () => {
    setEftText('');
    reset();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-text">Fitting Analyzer</h1>
        <p className="text-text-secondary mt-1">
          Analyze ship fittings for travel recommendations
        </p>
      </div>

      {/* Input Form */}
      <Card>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <label className="block text-sm font-medium text-text-secondary">
              EFT Fitting
            </label>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={handlePaste}
                className="text-xs text-primary hover:text-primary-hover flex items-center gap-1 rounded px-1 py-0.5 focus:outline-none focus:ring-2 focus:ring-primary"
                aria-label="Paste fitting from clipboard"
              >
                <Clipboard className="h-3 w-3" aria-hidden="true" />
                Paste
              </button>
              <button
                type="button"
                onClick={handleLoadExample}
                className="text-xs text-text-secondary hover:text-text rounded px-1 py-0.5 focus:outline-none focus:ring-2 focus:ring-primary"
                aria-label="Load example fitting"
              >
                Load Example
              </button>
              {eftText && (
                <button
                  type="button"
                  onClick={handleClear}
                  className="text-xs text-text-secondary hover:text-text rounded px-1 py-0.5 focus:outline-none focus:ring-2 focus:ring-primary"
                  aria-label="Clear fitting text"
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
            value={eftText}
            onChange={(e) => {
              setEftText(e.target.value);
              reset();
            }}
            placeholder="Paste your EFT fitting here...

[Ship Name, Fit Name]

Low Slot Module
...

Mid Slot Module
...

High Slot Module
..."
            className="min-h-[200px]"
          />

          <Button
            onClick={handleAnalyze}
            disabled={!eftText.trim() || isPending}
            loading={isPending}
          >
            <Wrench className="mr-2 h-4 w-4" />
            Analyze Fitting
          </Button>
        </div>
      </Card>

      {/* Error State */}
      {error && (
        <ErrorMessage
          title="Unable to analyze fitting"
          message={getUserFriendlyError(error)}
          onRetry={handleAnalyze}
        />
      )}

      {/* Results */}
      {analysis && <FittingResult analysis={analysis} />}

      {/* Empty State */}
      {!analysis && !isPending && !error && (
        <Card className="text-center py-12">
          <Wrench className="h-12 w-12 text-text-secondary mx-auto mb-4" />
          <p className="text-text-secondary mb-2">
            Paste an EFT fitting to analyze travel capabilities
          </p>
          <p className="text-xs text-text-secondary">
            Copy a fitting from EVE Online (Alt+Shift+C) or use the Fitting
            window export
          </p>
        </Card>
      )}
    </div>
  );
}
