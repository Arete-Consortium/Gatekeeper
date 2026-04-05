'use client';

import Link from 'next/link';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui';
import {
  Route,
  Radar,
  Skull,
  Swords,
  Users,
  ArrowLeftRight,
  Shield,
  Zap,
  ChevronRight,
  Check,
} from 'lucide-react';

const features = [
  {
    icon: Route,
    title: 'Route Planning',
    description:
      'Multi-stop pathfinding with gate, jump drive, and wormhole options across 5400+ systems.',
  },
  {
    icon: Radar,
    title: 'Live Intel',
    description:
      'Real-time kill feed, threat assessment, and pilot deep-dive from zKillboard data.',
  },
  {
    icon: Skull,
    title: 'Kill Feed',
    description:
      'Streaming kill notifications with risk heatmaps, gate camp detection, and hot system alerts.',
  },
  {
    icon: Swords,
    title: 'FW Map',
    description:
      'Faction warfare occupancy map with contested system highlights and warzone overview.',
  },
  {
    icon: Users,
    title: 'Fleet Tracker',
    description:
      'Share fleet position in real-time. See your fleet on the map with live location updates.',
  },
  {
    icon: ArrowLeftRight,
    title: 'Market Arbitrage',
    description:
      'Compare prices across trade hubs. Find profitable hauling routes and market gaps.',
  },
];

const proFeatures = [
  'AI route analysis & danger assessment',
  'Live kill feed & risk heatmaps',
  'Sovereignty & Thera overlays',
  'Webhook alerts (Discord & Slack)',
  'Advanced pilot intel & bulk queries',
  '300 requests/min rate limit',
];

export default function LandingPage() {
  const { isAuthenticated } = useAuth();

  return (
    <div className="min-h-[calc(100vh-theme(spacing.16)-theme(spacing.12))]">
      {/* Hero */}
      <section className="relative py-20 md:py-32 px-4 text-center overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-primary/5 via-transparent to-transparent pointer-events-none" />

        <div className="relative max-w-4xl mx-auto">
          <div className="inline-flex items-center gap-2 px-3 py-1 mb-6 text-xs font-medium text-primary border border-primary/30 rounded-full bg-primary/10">
            <Shield className="h-3.5 w-3.5" />
            Navigate New Eden safely
          </div>

          <h1 className="text-4xl md:text-6xl font-bold text-text tracking-tight">
            Navigate New Eden{' '}
            <span className="text-primary">with Intelligence</span>
          </h1>

          <p className="mt-6 text-lg md:text-xl text-text-secondary max-w-2xl mx-auto leading-relaxed">
            Route planning, live kill intel, risk heatmaps, and market data for
            5400+ systems. Make every jump with confidence.
          </p>

          <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link href="/map">
              <Button className="glow-primary text-base px-8 py-3 h-auto">
                Open Map
                <ChevronRight className="ml-1 h-4 w-4" />
              </Button>
            </Link>
            <Link href="/pricing">
              <Button
                variant="secondary"
                className="text-base px-8 py-3 h-auto"
              >
                View Pricing
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Social Proof */}
      <section className="py-8 border-y border-border/50">
        <div className="max-w-4xl mx-auto px-4 flex flex-wrap items-center justify-center gap-8 md:gap-16 text-text-secondary text-sm">
          <div className="flex items-center gap-2">
            <span className="text-2xl font-bold text-text">5,400+</span>
            <span>Systems</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-2xl font-bold text-text">Real-time</span>
            <span>Intel</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-2xl font-bold text-text">Pro</span>
            <span>Tools</span>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-16 md:py-24 px-4">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-text text-center mb-4">
            Everything you need to fly safe
          </h2>
          <p className="text-text-secondary text-center mb-12 max-w-xl mx-auto">
            From route planning to market arbitrage, Gatekeeper gives you the
            edge.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature) => (
              <div
                key={feature.title}
                className="group p-6 rounded-lg border border-border bg-card hover:border-primary/30 hover:bg-card-hover transition-all duration-200"
              >
                <div className="flex items-center gap-3 mb-3">
                  <div className="p-2 rounded-md bg-primary/10 text-primary group-hover:bg-primary/20 transition-colors">
                    <feature.icon className="h-5 w-5" />
                  </div>
                  <h3 className="font-semibold text-text">{feature.title}</h3>
                </div>
                <p className="text-sm text-text-secondary leading-relaxed">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing CTA */}
      <section className="py-16 md:py-24 px-4">
        <div className="max-w-2xl mx-auto text-center">
          <div className="p-8 md:p-12 rounded-xl border border-primary/30 bg-gradient-to-b from-primary/5 to-transparent">
            <div className="inline-flex items-center gap-2 mb-4">
              <Zap className="h-5 w-5 text-primary" />
              <span className="text-sm font-medium text-primary">
                Gatekeeper Pro
              </span>
            </div>

            <h2 className="text-2xl md:text-3xl font-bold text-text mb-2">
              Upgrade for <span className="text-primary">$3/mo</span>
            </h2>
            <p className="text-text-secondary mb-8">
              Unlock live intel overlays, AI route analysis, and webhook alerts.
            </p>

            <ul className="text-left max-w-sm mx-auto space-y-3 mb-8">
              {proFeatures.map((feat) => (
                <li
                  key={feat}
                  className="flex items-start gap-3 text-sm text-text-secondary"
                >
                  <Check className="h-4 w-4 text-primary mt-0.5 shrink-0" />
                  <span>{feat}</span>
                </li>
              ))}
            </ul>

            <Link href="/pricing">
              <Button className="glow-primary px-8 py-3 h-auto text-base">
                Get Started
                <ChevronRight className="ml-1 h-4 w-4" />
              </Button>
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
