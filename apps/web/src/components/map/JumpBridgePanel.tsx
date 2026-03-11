'use client';

import React, { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { JumpBridgeConnection, JumpBridgeListResponse, JumpBridgeImportResponse } from '@/lib/types';
import { GatekeeperAPI } from '@/lib/api';

const STATUS_COLORS: Record<JumpBridgeConnection['status'], string> = {
  online: '#22c55e',
  offline: '#ef4444',
  unknown: '#a3a3a3',
};

const STATUS_LABELS: Record<JumpBridgeConnection['status'], string> = {
  online: 'Online',
  offline: 'Offline',
  unknown: 'Unknown',
};

export function JumpBridgePanel() {
  const queryClient = useQueryClient();
  const [showAddForm, setShowAddForm] = useState(false);
  const [showImport, setShowImport] = useState(false);
  const [fromSystem, setFromSystem] = useState('');
  const [toSystem, setToSystem] = useState('');
  const [importText, setImportText] = useState('');
  const [importResult, setImportResult] = useState<JumpBridgeImportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { data, isLoading } = useQuery<JumpBridgeListResponse>({
    queryKey: ['jumpbridges'],
    queryFn: () => GatekeeperAPI.getJumpBridges(),
    refetchInterval: 30000,
  });

  const addMutation = useMutation({
    mutationFn: ({ from, to }: { from: string; to: string }) =>
      GatekeeperAPI.addJumpBridge(from, to),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jumpbridges'] });
      setFromSystem('');
      setToSystem('');
      setShowAddForm(false);
      setError(null);
    },
    onError: (err: Error) => {
      setError(err.message);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (bridgeId: string) => GatekeeperAPI.deleteJumpBridge(bridgeId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jumpbridges'] });
    },
  });

  const importMutation = useMutation({
    mutationFn: (text: string) => GatekeeperAPI.importJumpBridges(text),
    onSuccess: (result: JumpBridgeImportResponse) => {
      queryClient.invalidateQueries({ queryKey: ['jumpbridges'] });
      setImportResult(result);
      if (result.imported > 0) {
        setImportText('');
      }
    },
    onError: (err: Error) => {
      setError(err.message);
    },
  });

  const handleAdd = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (!fromSystem.trim() || !toSystem.trim()) return;
      setError(null);
      addMutation.mutate({ from: fromSystem.trim(), to: toSystem.trim() });
    },
    [fromSystem, toSystem, addMutation]
  );

  const handleImport = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (!importText.trim()) return;
      setError(null);
      setImportResult(null);
      importMutation.mutate(importText.trim());
    },
    [importText, importMutation]
  );

  const bridges = data?.bridges ?? [];

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white">
          Jump Bridges
          <span className="ml-2 text-xs text-gray-400">({bridges.length})</span>
        </h3>
        <div className="flex gap-2">
          <button
            onClick={() => {
              setShowAddForm(!showAddForm);
              setShowImport(false);
              setError(null);
            }}
            className="text-xs px-2 py-1 rounded bg-cyan-700 hover:bg-cyan-600 text-white transition-colors"
          >
            {showAddForm ? 'Cancel' : '+ Add'}
          </button>
          <button
            onClick={() => {
              setShowImport(!showImport);
              setShowAddForm(false);
              setError(null);
              setImportResult(null);
            }}
            className="text-xs px-2 py-1 rounded bg-gray-700 hover:bg-gray-600 text-white transition-colors"
          >
            {showImport ? 'Cancel' : 'Import'}
          </button>
        </div>
      </div>

      {error && (
        <div className="text-xs text-red-400 bg-red-900/30 border border-red-800 rounded px-2 py-1">
          {error}
        </div>
      )}

      {/* Add Form */}
      {showAddForm && (
        <form onSubmit={handleAdd} className="space-y-2">
          <input
            type="text"
            value={fromSystem}
            onChange={(e) => setFromSystem(e.target.value)}
            placeholder="From system (e.g. 1DQ1-A)"
            className="w-full text-xs px-2 py-1.5 rounded bg-gray-800 border border-gray-600 text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500"
          />
          <input
            type="text"
            value={toSystem}
            onChange={(e) => setToSystem(e.target.value)}
            placeholder="To system (e.g. 8QT-H4)"
            className="w-full text-xs px-2 py-1.5 rounded bg-gray-800 border border-gray-600 text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500"
          />
          <button
            type="submit"
            disabled={addMutation.isPending || !fromSystem.trim() || !toSystem.trim()}
            className="w-full text-xs px-2 py-1.5 rounded bg-cyan-700 hover:bg-cyan-600 disabled:opacity-50 disabled:cursor-not-allowed text-white transition-colors"
          >
            {addMutation.isPending ? 'Adding...' : 'Add Bridge'}
          </button>
        </form>
      )}

      {/* Import Form */}
      {showImport && (
        <form onSubmit={handleImport} className="space-y-2">
          <textarea
            value={importText}
            onChange={(e) => setImportText(e.target.value)}
            placeholder={'Paste jump bridges, one per line:\n1DQ1-A \u00bb 8QT-H4\n49-U6U \u00bb PUIG-F'}
            rows={5}
            className="w-full text-xs px-2 py-1.5 rounded bg-gray-800 border border-gray-600 text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500 font-mono"
          />
          <button
            type="submit"
            disabled={importMutation.isPending || !importText.trim()}
            className="w-full text-xs px-2 py-1.5 rounded bg-cyan-700 hover:bg-cyan-600 disabled:opacity-50 disabled:cursor-not-allowed text-white transition-colors"
          >
            {importMutation.isPending ? 'Importing...' : 'Import Bridges'}
          </button>
          {importResult && (
            <div className="text-xs space-y-1">
              <div className="text-green-400">
                Imported: {importResult.imported}
                {importResult.skipped > 0 && (
                  <span className="text-yellow-400 ml-2">
                    Skipped: {importResult.skipped}
                  </span>
                )}
              </div>
              {importResult.errors.length > 0 && (
                <div className="text-red-400">
                  {importResult.errors.map((err, i) => (
                    <div key={i}>{err}</div>
                  ))}
                </div>
              )}
            </div>
          )}
        </form>
      )}

      {/* Bridge List */}
      {isLoading ? (
        <div className="text-xs text-gray-400">Loading bridges...</div>
      ) : bridges.length === 0 ? (
        <div className="text-xs text-gray-500 text-center py-2">
          No jump bridges configured. Add bridges or import from text.
        </div>
      ) : (
        <div className="space-y-1 max-h-64 overflow-y-auto">
          {bridges.map((bridge) => (
            <div
              key={bridge.id}
              className="flex items-center justify-between bg-gray-800 rounded px-2 py-1.5 group"
            >
              <div className="flex items-center gap-2 min-w-0">
                <span
                  className="w-2 h-2 rounded-full flex-shrink-0"
                  style={{ backgroundColor: STATUS_COLORS[bridge.status] }}
                  title={STATUS_LABELS[bridge.status]}
                />
                <span className="text-xs text-white truncate">
                  {bridge.from_system}
                  <span className="text-gray-400 mx-1">{'\u00bb'}</span>
                  {bridge.to_system}
                </span>
              </div>
              <button
                onClick={() => deleteMutation.mutate(bridge.id)}
                disabled={deleteMutation.isPending}
                className="text-xs text-gray-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0 ml-2"
                title="Remove bridge"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default JumpBridgePanel;
