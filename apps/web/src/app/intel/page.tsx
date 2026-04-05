'use client';

import { useState } from 'react';
import { Radar, MessageSquareText, Users, Bell, AlertTriangle, Search, Lock } from 'lucide-react';
import IntelFeed from '@/components/intel/IntelFeed';
import { ThreatsTab } from '@/components/intel/ThreatsTab';
import { PilotLookupTab } from '@/components/intel/PilotLookupTab';
import IntelParsePage from '@/app/intel-parse/page';
import FleetPage from '@/app/fleet/page';
import AlertsPage from '@/app/alerts/page';
import { ProGate } from '@/components/ProGate';
import { useAuth } from '@/contexts/AuthContext';

type Tab = 'kill-feed' | 'threats' | 'pilot' | 'intel-parser' | 'fleet' | 'alerts';

/** Tabs that require Pro subscription */
const PRO_TABS = new Set<Tab>(['kill-feed', 'threats']);

const tabs: { key: Tab; label: string; icon: React.ComponentType<{ className?: string }>; pro?: boolean }[] = [
  { key: 'kill-feed', label: 'Kill Feed', icon: Radar, pro: true },
  { key: 'threats', label: 'Threats', icon: AlertTriangle, pro: true },
  { key: 'pilot', label: 'Lookup / Pin', icon: Search },
  { key: 'intel-parser', label: 'Intel Parser', icon: MessageSquareText },
  { key: 'fleet', label: 'Fleet', icon: Users },
  { key: 'alerts', label: 'Alerts', icon: Bell },
];

export default function IntelPage() {
  const [activeTab, setActiveTab] = useState<Tab>('kill-feed');
  const { isPro } = useAuth();

  const content = (() => {
    switch (activeTab) {
      case 'kill-feed':
        return <IntelFeed />;
      case 'threats':
        return <ThreatsTab />;
      case 'pilot':
        return <PilotLookupTab />;
      case 'intel-parser':
        return <IntelParsePage />;
      case 'fleet':
        return <FleetPage />;
      case 'alerts':
        return <AlertsPage />;
    }
  })();

  const needsGate = PRO_TABS.has(activeTab) && !isPro;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-text">Intel</h1>
        <p className="text-text-secondary mt-1">
          Kill feed, intel parsing, fleet analysis, and alert subscriptions
        </p>
      </div>

      {/* Tab Bar */}
      <div className="flex border-b border-border">
        {tabs.map(({ key, label, icon: Icon, pro }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium transition-colors relative ${
              activeTab === key
                ? 'text-primary'
                : 'text-text-secondary hover:text-text'
            }`}
          >
            <Icon className="h-4 w-4" />
            {label}
            {pro && !isPro && <Lock className="h-3 w-3 text-primary/60" />}
            {activeTab === key && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary" />
            )}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {needsGate ? (
        <ProGate feature={activeTab === 'kill-feed' ? 'Kill Feed' : 'Threat Intel'}>
          {content}
        </ProGate>
      ) : (
        content
      )}
    </div>
  );
}
