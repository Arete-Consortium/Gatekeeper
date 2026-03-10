'use client';

import { useState, useCallback } from 'react';
import { Card, Button, Select } from '@/components/ui';
import { ErrorMessage, getUserFriendlyError } from '@/components/ui';
import { GatekeeperAPI } from '@/lib/api';
import type { CapitalShipType, FuelType, JumpRouteResponse } from '@/lib/types';
import { Rocket, Loader2, Fuel, Clock, Navigation } from 'lucide-react';

function formatIsk(value: number): string {
  if (value >= 1e12) return `${(value / 1e12).toFixed(2)}T`;
  if (value >= 1e9) return `${(value / 1e9).toFixed(2)}B`;
  if (value >= 1e6) return `${(value / 1e6).toFixed(2)}M`;
  if (value >= 1e3) return `${(value / 1e3).toFixed(1)}K`;
  return value.toFixed(2);
}

function formatMinutes(minutes: number): string {
  if (minutes < 1) return '< 1m';
  const hrs = Math.floor(minutes / 60);
  const mins = Math.round(minutes % 60);
  if (hrs === 0) return `${mins}m`;
  return `${hrs}h ${mins}m`;
}

const SHIP_NAMES: Record<CapitalShipType, string> = {
  jump_freighter: 'Jump Freighter',
  carrier: 'Carrier',
  dreadnought: 'Dreadnought',
  force_auxiliary: 'Force Auxiliary',
  supercarrier: 'Supercarrier',
  titan: 'Titan',
  rorqual: 'Rorqual',
  black_ops: 'Black Ops',
};

const FUEL_NAMES: Record<FuelType, string> = {
  nitrogen: 'Nitrogen Isotopes',
  helium: 'Helium Isotopes',
  oxygen: 'Oxygen Isotopes',
  hydrogen: 'Hydrogen Isotopes',
};

const DEFAULT_FUEL: Record<CapitalShipType, FuelType> = {
  jump_freighter: 'nitrogen',
  carrier: 'helium',
  dreadnought: 'helium',
  force_auxiliary: 'helium',
  supercarrier: 'helium',
  titan: 'helium',
  rorqual: 'oxygen',
  black_ops: 'hydrogen',
};

const SHIP_OPTIONS = Object.entries(SHIP_NAMES).map(([value, label]) => ({
  value,
  label,
}));

const FUEL_OPTIONS = Object.entries(FUEL_NAMES).map(([value, label]) => ({
  value,
  label,
}));

const SKILL_OPTIONS = Array.from({ length: 6 }, (_, i) => ({
  value: i.toString(),
  label: `Level ${i}`,
}));

export default function JumpPlannerPage() {
  const [fromSystem, setFromSystem] = useState('');
  const [toSystem, setToSystem] = useState('');
  const [shipType, setShipType] = useState<CapitalShipType>('jump_freighter');
  const [fuelType, setFuelType] = useState<FuelType>('nitrogen');
  const [fuelOverride, setFuelOverride] = useState(false);
  const [jdc, setJdc] = useState(5);
  const [jfc, setJfc] = useState(5);
  const [result, setResult] = useState<JumpRouteResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const handleShipChange = useCallback((newShip: CapitalShipType) => {
    setShipType(newShip);
    if (!fuelOverride) {
      setFuelType(DEFAULT_FUEL[newShip]);
    }
  }, [fuelOverride]);

  const handleFuelChange = useCallback((newFuel: FuelType) => {
    setFuelType(newFuel);
    setFuelOverride(true);
  }, []);

  const handleCalculate = useCallback(async () => {
    if (!fromSystem.trim() || !toSystem.trim()) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await GatekeeperAPI.getJumpRoute(
        fromSystem.trim(),
        toSystem.trim(),
        shipType,
        jdc,
        jfc,
        fuelType
      );
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Route calculation failed'));
    } finally {
      setIsLoading(false);
    }
  }, [fromSystem, toSystem, shipType, jdc, jfc, fuelType]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        handleCalculate();
      }
    },
    [handleCalculate]
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-text flex items-center gap-2">
          <Rocket className="h-6 w-6 text-primary" />
          Jump Route Planner
        </h1>
        <p className="text-text-secondary mt-1">
          Plan capital ship jump drive routes with fuel, fatigue, and cost calculations
        </p>
      </div>

      {/* Main layout: two columns on desktop */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left panel — Options */}
        <div className="lg:col-span-1 space-y-4">
          {/* Origin / Destination */}
          <Card>
            <div className="space-y-3">
              <div className="text-sm font-semibold text-text uppercase tracking-wide mb-2">
                Route
              </div>
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-1.5">
                  Origin System
                </label>
                <input
                  type="text"
                  value={fromSystem}
                  onChange={(e) => setFromSystem(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="e.g. Jita"
                  className="w-full px-4 py-2 bg-card border border-border rounded-lg text-text placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary transition-all duration-200"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-1.5">
                  Destination System
                </label>
                <input
                  type="text"
                  value={toSystem}
                  onChange={(e) => setToSystem(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="e.g. HED-GP"
                  className="w-full px-4 py-2 bg-card border border-border rounded-lg text-text placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary transition-all duration-200"
                />
              </div>
            </div>
          </Card>

          {/* Ship & Fuel */}
          <Card>
            <div className="space-y-3">
              <div className="text-sm font-semibold text-text uppercase tracking-wide mb-2">
                Jump Options
              </div>
              <Select
                label="Ship Type"
                options={SHIP_OPTIONS}
                value={shipType}
                onChange={(e) => handleShipChange(e.target.value as CapitalShipType)}
              />
              <Select
                label="Fuel Type"
                options={FUEL_OPTIONS}
                value={fuelType}
                onChange={(e) => handleFuelChange(e.target.value as FuelType)}
              />
              <div className="grid grid-cols-2 gap-3">
                <Select
                  label="JDC Level"
                  options={SKILL_OPTIONS}
                  value={jdc.toString()}
                  onChange={(e) => setJdc(Number(e.target.value))}
                />
                <Select
                  label="JFC Level"
                  options={SKILL_OPTIONS}
                  value={jfc.toString()}
                  onChange={(e) => setJfc(Number(e.target.value))}
                />
              </div>
            </div>
          </Card>

          {/* Calculate */}
          <Button
            onClick={handleCalculate}
            disabled={!fromSystem.trim() || !toSystem.trim() || isLoading}
            loading={isLoading}
            className="w-full"
          >
            {isLoading ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Navigation className="mr-2 h-4 w-4" />
            )}
            Calculate Route
          </Button>
        </div>

        {/* Right panel — Results */}
        <div className="lg:col-span-2 space-y-4">
          {/* Error */}
          {error && (
            <ErrorMessage
              title="Route calculation failed"
              message={getUserFriendlyError(error)}
              onRetry={handleCalculate}
            />
          )}

          {/* Results */}
          {result && (
            <div className="space-y-4">
              {/* Summary cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <Card className="text-center">
                  <div className="text-xs text-text-secondary uppercase mb-1">Jumps</div>
                  <div className="text-xl font-bold text-text">{result.total_jumps}</div>
                </Card>
                <Card className="text-center">
                  <div className="text-xs text-text-secondary uppercase mb-1">Distance</div>
                  <div className="text-xl font-bold text-blue-400">
                    {result.total_distance_ly.toFixed(2)} LY
                  </div>
                </Card>
                <Card className="text-center">
                  <div className="text-xs text-text-secondary uppercase mb-1">
                    <Fuel className="h-3 w-3 inline mr-1" />
                    Fuel
                  </div>
                  <div className="text-xl font-bold text-yellow-400">
                    {result.total_fuel.toLocaleString()}
                  </div>
                  <div className="text-xs text-text-secondary mt-0.5">
                    {result.fuel_type_name}
                  </div>
                </Card>
                <Card className="text-center">
                  <div className="text-xs text-text-secondary uppercase mb-1">
                    <Clock className="h-3 w-3 inline mr-1" />
                    Travel Time
                  </div>
                  <div className="text-xl font-bold text-text">
                    {formatMinutes(result.total_travel_time_minutes)}
                  </div>
                </Card>
              </div>

              {/* Fuel cost card */}
              <Card>
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm text-text-secondary">Fuel Cost Estimate</div>
                    <div className="text-xs text-text-secondary mt-0.5">
                      {result.total_fuel.toLocaleString()} x{' '}
                      {formatIsk(result.fuel_unit_cost)} per unit
                    </div>
                  </div>
                  <div className="text-xl font-bold text-green-400">
                    {formatIsk(result.total_fuel_cost)} ISK
                  </div>
                </div>
              </Card>

              {/* Fatigue warning */}
              {result.total_fatigue_minutes > 60 && (
                <div className="bg-risk-orange/10 border border-risk-orange/30 rounded-lg px-3 py-2">
                  <div className="text-xs font-medium text-risk-orange">
                    High Jump Fatigue Warning
                  </div>
                  <div className="text-xs text-text-secondary mt-0.5">
                    Total accumulated fatigue: {formatMinutes(result.total_fatigue_minutes)}.
                    Plan rest stops accordingly.
                  </div>
                </div>
              )}

              {/* Per-leg table */}
              {result.legs.length > 0 && (
                <div className="border border-border rounded-lg overflow-x-auto">
                  {/* Header */}
                  <div className="grid grid-cols-12 gap-2 px-3 py-2.5 bg-card text-xs text-text-secondary uppercase font-semibold min-w-[700px]">
                    <div className="col-span-1 text-center">#</div>
                    <div className="col-span-3">From</div>
                    <div className="col-span-3">To</div>
                    <div className="col-span-1 text-right">LY</div>
                    <div className="col-span-1 text-right">Fuel</div>
                    <div className="col-span-1 text-right">Fatigue</div>
                    <div className="col-span-2 text-right">Wait</div>
                  </div>

                  {/* Rows */}
                  {result.legs.map((leg, idx) => (
                    <div
                      key={`${leg.from_system}-${leg.to_system}`}
                      className="grid grid-cols-12 gap-2 px-3 py-2.5 border-t border-border hover:bg-card-hover transition-colors items-center min-w-[700px] text-sm"
                    >
                      <div className="col-span-1 text-center text-text-secondary font-mono">
                        {idx + 1}
                      </div>
                      <div className="col-span-3 text-text font-medium truncate" title={leg.from_system}>
                        {leg.from_system}
                      </div>
                      <div className="col-span-3 text-text font-medium truncate" title={leg.to_system}>
                        {leg.to_system}
                      </div>
                      <div className="col-span-1 text-right text-blue-400 font-mono">
                        {leg.distance_ly.toFixed(2)}
                      </div>
                      <div className="col-span-1 text-right text-yellow-400 font-mono">
                        {leg.fuel_required.toLocaleString()}
                      </div>
                      <div className="col-span-1 text-right text-text-secondary font-mono">
                        {formatMinutes(leg.total_fatigue_minutes)}
                      </div>
                      <div className="col-span-2 text-right font-mono">
                        {leg.wait_time_minutes > 0 ? (
                          <span className="text-risk-orange">
                            {formatMinutes(leg.wait_time_minutes)}
                          </span>
                        ) : (
                          <span className="text-green-400">Ready</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Empty state */}
          {!result && !isLoading && !error && (
            <Card className="text-center py-12">
              <Rocket className="h-12 w-12 text-text-secondary mx-auto mb-4" />
              <p className="text-text-secondary">
                Enter origin and destination systems to calculate a jump route
              </p>
              <p className="text-xs text-text-secondary mt-2">
                Supports jump freighters, carriers, dreadnoughts, supers, titans, and black ops
              </p>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
