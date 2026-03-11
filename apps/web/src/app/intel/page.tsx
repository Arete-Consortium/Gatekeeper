'use client';

import { useState } from 'react';
import { Radar, MessageSquareText, Users, Bell } from 'lucide-react';
import IntelFeed from '@/components/intel/IntelFeed';
import IntelParsePage from '@/app/intel-parse/page';
import FleetPage from '@/app/fleet/page';
import AlertsPage from '@/app/alerts/page';

type Tab = 'kill-feed' | 'intel-parser' | 'fleet' | 'alerts';

const tabs: { key: Tab; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { key: 'kill-feed', label: 'Kill Feed', icon: Radar },
  { key: 'intel-parser', label: 'Intel Parser', icon: MessageSquareText },
  { key: 'fleet', label: 'Fleet', icon: Users },
  { key: 'alerts', label: 'Alerts', icon: Bell },
];

export default function IntelPage() {
  const [activeTab, setActiveTab] = useState<Tab>('kill-feed');

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
        {tabs.map(({ key, label, icon: Icon }) => (
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
            {activeTab === key && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary" />
            )}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'kill-feed' && <IntelFeed />}
      {activeTab === 'intel-parser' && <IntelParsePage />}
      {activeTab === 'fleet' && <FleetPage />}
      {activeTab === 'alerts' && <AlertsPage />}
    </div>
  );
}
