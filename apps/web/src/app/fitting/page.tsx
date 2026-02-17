'use client';

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';
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
  const t = useTranslations('fitting');
  const [eftText, setEftText] = useState('');

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
      const text = await navigator.clipboard.readText();
      setEftText(text);
      reset();
    } catch {
      // Clipboard access denied
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
        <h1 className="text-2xl font-bold text-text">{t('title')}</h1>
        <p className="text-text-secondary mt-1">
          {t('subtitle')}
        </p>
      </div>

      {/* Input Form */}
      <Card>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <label className="block text-sm font-medium text-text-secondary">
              {t('eftFitting')}
            </label>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={handlePaste}
                className="text-xs text-primary hover:text-primary-hover flex items-center gap-1 rounded px-1 py-0.5 focus:outline-none focus:ring-2 focus:ring-primary"
                aria-label={t('paste')}
              >
                <Clipboard className="h-3 w-3" aria-hidden="true" />
                {t('paste')}
              </button>
              <button
                type="button"
                onClick={handleLoadExample}
                className="text-xs text-text-secondary hover:text-text rounded px-1 py-0.5 focus:outline-none focus:ring-2 focus:ring-primary"
                aria-label={t('loadExample')}
              >
                {t('loadExample')}
              </button>
              {eftText && (
                <button
                  type="button"
                  onClick={handleClear}
                  className="text-xs text-text-secondary hover:text-text rounded px-1 py-0.5 focus:outline-none focus:ring-2 focus:ring-primary"
                  aria-label={t('clear')}
                >
                  {t('clear')}
                </button>
              )}
            </div>
          </div>

          <Textarea
            value={eftText}
            onChange={(e) => {
              setEftText(e.target.value);
              reset();
            }}
            placeholder={t('placeholder')}
            className="min-h-[200px]"
          />

          <Button
            onClick={handleAnalyze}
            disabled={!eftText.trim() || isPending}
            loading={isPending}
          >
            <Wrench className="mr-2 h-4 w-4" />
            {t('analyzeFitting')}
          </Button>
        </div>
      </Card>

      {/* Error State */}
      {error && (
        <ErrorMessage
          title={t('analyzeError')}
          message={error.message || t('analyzeError')}
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
            {t('emptyState')}
          </p>
          <p className="text-xs text-text-secondary">
            {t('emptyHint')}
          </p>
        </Card>
      )}
    </div>
  );
}
