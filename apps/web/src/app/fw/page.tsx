'use client';

import dynamic from 'next/dynamic';
import { Swords } from 'lucide-react';

// SSR-safe dynamic import for canvas component
const FWMap = dynamic(() => import('@/components/fw/FWMap').then((m) => ({ default: m.FWMap })), {
  ssr: false,
  loading: () => (
    <div className="w-full h-64 bg-card rounded-lg border border-border flex items-center justify-center">
      <span className="text-text-secondary text-sm">Loading FW Map...</span>
    </div>
  ),
});

export default function FWPage() {
  return (
    <div className="space-y-4">
      <div>
        <div className="flex items-center gap-2">
          <Swords className="h-6 w-6 text-primary" />
          <h1 className="text-2xl font-bold text-text">Faction Warfare Map</h1>
        </div>
        <p className="text-text-secondary text-sm mt-1">
          Live occupancy and contested status across all faction warfare zones.
          Systems sized by victory point progress. Click a system for details.
        </p>
      </div>

      <FWMap />
    </div>
  );
}
