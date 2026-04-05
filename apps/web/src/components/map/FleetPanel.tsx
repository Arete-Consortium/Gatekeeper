'use client';

import React, { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { GatekeeperAPI } from '@/lib/api';
import type { FleetMember } from '@/lib/types';
import { Users, Copy, Check, LogOut, Plus, ArrowRight, Loader2 } from 'lucide-react';

// Same palette as FleetOverlay for visual consistency
const FLEET_COLORS = [
  '#f59e0b', '#10b981', '#f43f5e', '#8b5cf6', '#06b6d4',
  '#ec4899', '#84cc16', '#f97316', '#6366f1', '#14b8a6',
];

interface FleetPanelProps {
  /** Current fleet code (null = not in a fleet) */
  fleetCode: string | null;
  onFleetChange: (code: string | null) => void;
  /** Current user's character ID (to highlight self in member list) */
  currentCharacterId?: number;
}

export function FleetPanel({
  fleetCode,
  onFleetChange,
  currentCharacterId,
}: FleetPanelProps) {
  const [joinInput, setJoinInput] = useState('');
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const queryClient = useQueryClient();

  // Poll fleet members every 15s when in a fleet
  const { data: fleetData } = useQuery({
    queryKey: ['fleetMembers', fleetCode],
    queryFn: () => GatekeeperAPI.getFleetMembers(fleetCode!),
    refetchInterval: 15_000,
    enabled: !!fleetCode,
    retry: 1,
  });

  const createMutation = useMutation({
    mutationFn: () => GatekeeperAPI.createFleetSession(),
    onSuccess: (data) => {
      onFleetChange(data.code);
      setError(null);
    },
    onError: (err: Error) => setError(err.message),
  });

  const joinMutation = useMutation({
    mutationFn: (code: string) => GatekeeperAPI.joinFleetSession(code),
    onSuccess: (data) => {
      onFleetChange(data.code);
      setJoinInput('');
      setError(null);
    },
    onError: (err: Error) => setError(err.message),
  });

  const leaveMutation = useMutation({
    mutationFn: () => GatekeeperAPI.leaveFleetSession(fleetCode!),
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: ['fleetMembers', fleetCode] });
      onFleetChange(null);
      setError(null);
    },
    onError: (err: Error) => setError(err.message),
  });

  const handleCopyCode = useCallback(async () => {
    if (!fleetCode) return;
    try {
      await navigator.clipboard.writeText(fleetCode);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for non-HTTPS
      setError('Failed to copy — try selecting the code manually');
    }
  }, [fleetCode]);

  const handleJoin = useCallback(() => {
    const code = joinInput.trim().toUpperCase();
    if (code.length < 4) {
      setError('Share code must be at least 4 characters');
      return;
    }
    joinMutation.mutate(code);
  }, [joinInput, joinMutation]);

  const isLoading = createMutation.isPending || joinMutation.isPending || leaveMutation.isPending;

  // Not in a fleet — show create/join controls
  if (!fleetCode) {
    return (
      <div className="space-y-3">
        <button
          onClick={() => createMutation.mutate()}
          disabled={isLoading}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-primary/20 hover:bg-primary/30 text-primary rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
        >
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Plus className="h-4 w-4" />
          )}
          Create Fleet
        </button>

        <div className="flex gap-2">
          <input
            type="text"
            value={joinInput}
            onChange={(e) => setJoinInput(e.target.value.toUpperCase())}
            onKeyDown={(e) => e.key === 'Enter' && handleJoin()}
            placeholder="Share code"
            maxLength={6}
            className="flex-1 px-2.5 py-1.5 bg-card border border-border rounded-lg text-sm text-text font-mono uppercase tracking-wider focus:outline-none focus:ring-2 focus:ring-primary placeholder:text-text-secondary/50"
          />
          <button
            onClick={handleJoin}
            disabled={isLoading || !joinInput.trim()}
            className="px-3 py-1.5 bg-card-hover hover:bg-border text-text rounded-lg text-sm transition-colors disabled:opacity-50"
          >
            <ArrowRight className="h-4 w-4" />
          </button>
        </div>

        {error && (
          <p className="text-xs text-red-400">{error}</p>
        )}
      </div>
    );
  }

  // In a fleet — show code, members, and leave button
  const members = fleetData?.members ?? [];
  let colorIndex = 0;

  return (
    <div className="space-y-3">
      {/* Fleet code header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Users className="h-4 w-4 text-primary" />
          <span className="font-mono text-sm font-bold text-primary tracking-wider">
            {fleetCode}
          </span>
          <button
            onClick={handleCopyCode}
            className="p-1 rounded hover:bg-card-hover text-text-secondary hover:text-text transition-colors"
            title="Copy share code"
          >
            {copied ? (
              <Check className="h-3.5 w-3.5 text-green-400" />
            ) : (
              <Copy className="h-3.5 w-3.5" />
            )}
          </button>
        </div>
        <button
          onClick={() => leaveMutation.mutate()}
          disabled={isLoading}
          className="flex items-center gap-1 px-2 py-1 text-xs text-red-400 hover:text-red-300 hover:bg-red-400/10 rounded transition-colors"
        >
          <LogOut className="h-3 w-3" />
          Leave
        </button>
      </div>

      {/* Member list */}
      <div className="space-y-1.5 max-h-48 overflow-y-auto">
        {members.length === 0 && (
          <div className="flex items-center gap-2 text-xs text-text-secondary">
            <Loader2 className="h-3 w-3 animate-spin" />
            Loading members...
          </div>
        )}
        {members.map((member: FleetMember) => {
          const isSelf = member.character_id === currentCharacterId;
          const color = FLEET_COLORS[colorIndex % FLEET_COLORS.length];
          colorIndex++;

          return (
            <div
              key={member.character_id}
              className="flex items-center gap-2 px-2 py-1 rounded text-xs"
              style={{ backgroundColor: isSelf ? 'rgba(34,211,238,0.08)' : undefined }}
            >
              <div
                className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                style={{
                  backgroundColor: isSelf ? '#22d3ee' : color,
                  opacity: member.online ? 1 : 0.3,
                }}
              />
              <span className={`truncate ${isSelf ? 'text-cyan-400 font-medium' : 'text-text'}`}>
                {member.character_name}
              </span>
              {member.system_name && (
                <span className="text-text-secondary ml-auto flex-shrink-0">
                  {member.system_name}
                </span>
              )}
            </div>
          );
        })}
      </div>

      <div className="text-[10px] text-text-secondary/50">
        {members.length} member{members.length !== 1 ? 's' : ''} — updates every 15s
      </div>

      {error && (
        <p className="text-xs text-red-400">{error}</p>
      )}
    </div>
  );
}

export default FleetPanel;
