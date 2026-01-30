'use client';

import { Card, CardTitle, Badge } from '@/components/ui';
import type { FittingAnalysisResponse } from '@/lib/types';
import {
  Shield,
  AlertTriangle,
  Lightbulb,
  Ship,
  Eye,
  Zap,
  Navigation,
} from 'lucide-react';

interface FittingAnalyzerProps {
  analysis: FittingAnalysisResponse;
}

export function FittingResult({ analysis }: FittingAnalyzerProps) {
  const { fitting, travel } = analysis;

  return (
    <div className="space-y-4">
      {/* Ship Info Card */}
      <Card>
        <div className="flex items-center gap-4 mb-4">
          <div className="p-3 bg-primary/20 rounded-lg">
            <Ship className="h-6 w-6 text-primary" />
          </div>
          <div>
            <CardTitle>{fitting.ship_name}</CardTitle>
            <p className="text-sm text-text-secondary">{fitting.ship_category}</p>
          </div>
        </div>

        {/* Capabilities */}
        <div className="flex flex-wrap gap-2 mb-4">
          {fitting.is_cloak_capable && (
            <Badge variant="success">
              <Eye className="h-3 w-3 mr-1" />
              Cloak Capable
            </Badge>
          )}
          {fitting.is_covert_capable && (
            <Badge variant="success">
              <Eye className="h-3 w-3 mr-1" />
              Covert Ops
            </Badge>
          )}
          {fitting.is_bubble_immune && (
            <Badge variant="success">
              <Shield className="h-3 w-3 mr-1" />
              Bubble Immune
            </Badge>
          )}
          {fitting.has_warp_stabs && (
            <Badge variant="warning">
              <Zap className="h-3 w-3 mr-1" />
              Warp Stabs
            </Badge>
          )}
          {fitting.has_align_mods && (
            <Badge variant="info">
              <Navigation className="h-3 w-3 mr-1" />
              Align Mods
            </Badge>
          )}
          {fitting.has_warp_speed_mods && (
            <Badge variant="info">
              <Zap className="h-3 w-3 mr-1" />
              Warp Speed
            </Badge>
          )}
        </div>

        {/* Jump Capability */}
        {fitting.jump_capability !== 'none' && (
          <div className="p-3 bg-background rounded-lg">
            <p className="text-sm text-text-secondary">Jump Capability</p>
            <p className="font-medium text-text capitalize">
              {fitting.jump_capability}
            </p>
          </div>
        )}
      </Card>

      {/* Travel Recommendations */}
      <Card>
        <CardTitle className="mb-4">Travel Recommendations</CardTitle>

        {/* Route Profile */}
        <div className="p-3 bg-background rounded-lg mb-4">
          <p className="text-sm text-text-secondary">Recommended Profile</p>
          <p className="font-medium text-primary capitalize">
            {travel.recommended_profile}
          </p>
        </div>

        {/* Capabilities Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-4">
          <div className="p-3 bg-background rounded-lg text-center">
            <p className="text-xs text-text-secondary mb-1">Gates</p>
            <Badge variant={travel.can_use_gates ? 'success' : 'danger'}>
              {travel.can_use_gates ? 'Yes' : 'No'}
            </Badge>
          </div>
          <div className="p-3 bg-background rounded-lg text-center">
            <p className="text-xs text-text-secondary mb-1">Jump Bridges</p>
            <Badge variant={travel.can_use_jump_bridges ? 'success' : 'danger'}>
              {travel.can_use_jump_bridges ? 'Yes' : 'No'}
            </Badge>
          </div>
          <div className="p-3 bg-background rounded-lg text-center">
            <p className="text-xs text-text-secondary mb-1">Jump Drive</p>
            <Badge variant={travel.can_jump ? 'success' : 'default'}>
              {travel.can_jump ? 'Yes' : 'No'}
            </Badge>
          </div>
          <div className="p-3 bg-background rounded-lg text-center">
            <p className="text-xs text-text-secondary mb-1">Bridge Others</p>
            <Badge variant={travel.can_bridge_others ? 'success' : 'default'}>
              {travel.can_bridge_others ? 'Yes' : 'No'}
            </Badge>
          </div>
          <div className="p-3 bg-background rounded-lg text-center">
            <p className="text-xs text-text-secondary mb-1">Covert Bridge</p>
            <Badge variant={travel.can_covert_bridge ? 'success' : 'default'}>
              {travel.can_covert_bridge ? 'Yes' : 'No'}
            </Badge>
          </div>
        </div>
      </Card>

      {/* Warnings */}
      {travel.warnings.length > 0 && (
        <Card className="border-risk-orange bg-risk-orange/10">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-risk-orange flex-shrink-0 mt-0.5" />
            <div>
              <CardTitle className="text-risk-orange mb-2">Warnings</CardTitle>
              <ul className="space-y-1">
                {travel.warnings.map((warning, index) => (
                  <li key={index} className="text-sm text-text">
                    {warning}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </Card>
      )}

      {/* Tips */}
      {travel.tips.length > 0 && (
        <Card className="border-primary bg-primary/10">
          <div className="flex items-start gap-3">
            <Lightbulb className="h-5 w-5 text-primary flex-shrink-0 mt-0.5" />
            <div>
              <CardTitle className="text-primary mb-2">Tips</CardTitle>
              <ul className="space-y-1">
                {travel.tips.map((tip, index) => (
                  <li key={index} className="text-sm text-text">
                    {tip}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
