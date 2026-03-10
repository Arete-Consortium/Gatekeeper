'use client';

import { PochvenMap } from '@/components/pochven/PochvenMap';

export default function PochvenPage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-text">Pochven Navigation</h1>
        <p className="text-text-secondary text-sm mt-1">
          Internal conduit gate network &middot; 27 systems &middot; 3 Krais.
          Click two systems to find the shortest route.
        </p>
      </div>
      <PochvenMap />
    </div>
  );
}
