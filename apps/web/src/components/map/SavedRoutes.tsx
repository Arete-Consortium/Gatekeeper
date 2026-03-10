'use client';

import { useState, useCallback } from 'react';
import { useBookmarks } from '@/hooks/useBookmarks';
import { useAuth } from '@/contexts/AuthContext';
import { Button, Badge } from '@/components/ui';
import { Bookmark, Trash2, Loader2, Plus, LogIn } from 'lucide-react';
import Link from 'next/link';
import type { BookmarkResponse } from '@/lib/types';

interface SavedRoutesProps {
  /** Current route origin system name */
  currentOrigin?: string;
  /** Current route destination system name */
  currentDestination?: string;
  /** Current route profile */
  currentProfile?: string;
  /** Current avoid systems */
  currentAvoidSystems?: string[];
  /** Current use bridges setting */
  currentUseBridges?: boolean;
  /** Called when user loads a bookmark */
  onLoad?: (bookmark: BookmarkResponse) => void;
}

export function SavedRoutes({
  currentOrigin,
  currentDestination,
  currentProfile,
  currentAvoidSystems = [],
  currentUseBridges = false,
  onLoad,
}: SavedRoutesProps) {
  const { isAuthenticated, isPro } = useAuth();
  const { bookmarks, isLoading, createBookmark, deleteBookmark, isCreating, isDeleting } = useBookmarks();
  const [saveName, setSaveName] = useState('');
  const [showSaveForm, setShowSaveForm] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null);

  const canSave = currentOrigin && currentDestination && saveName.trim().length > 0;

  const handleSave = useCallback(async () => {
    if (!canSave || !currentOrigin || !currentDestination) return;
    try {
      await createBookmark({
        name: saveName.trim(),
        from_system: currentOrigin,
        to_system: currentDestination,
        profile: currentProfile || 'shorter',
        avoid_systems: currentAvoidSystems,
        use_bridges: currentUseBridges,
      });
      setSaveName('');
      setShowSaveForm(false);
    } catch {
      // Error handled by mutation state
    }
  }, [canSave, currentOrigin, currentDestination, currentProfile, currentAvoidSystems, currentUseBridges, saveName, createBookmark]);

  const handleDelete = useCallback(async (id: number) => {
    try {
      await deleteBookmark(id);
      setDeleteConfirm(null);
    } catch {
      // Error handled by mutation state
    }
  }, [deleteBookmark]);

  // Not logged in
  if (!isAuthenticated) {
    return (
      <div className="text-center py-3">
        <Bookmark className="h-5 w-5 text-text-secondary mx-auto mb-2" />
        <p className="text-xs text-text-secondary mb-2">Sign in to save routes</p>
        <Link href="/login">
          <Button variant="secondary" size="sm">
            <LogIn className="h-3 w-3 mr-1" />
            Sign In
          </Button>
        </Link>
      </div>
    );
  }

  // Not Pro
  if (!isPro) {
    return (
      <div className="text-center py-3">
        <Bookmark className="h-5 w-5 text-text-secondary mx-auto mb-2" />
        <p className="text-xs text-text-secondary mb-2">Save routes with Pro</p>
        <Link href="/pricing">
          <Button variant="secondary" size="sm" className="text-primary">
            Upgrade to Pro
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {/* Save current route */}
      {currentOrigin && currentDestination && (
        <>
          {showSaveForm ? (
            <div className="flex gap-1.5">
              <input
                type="text"
                value={saveName}
                onChange={(e) => setSaveName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSave()}
                placeholder="Route name..."
                className="flex-1 px-2 py-1 bg-background border border-border rounded text-sm text-text placeholder:text-text-secondary/50 focus:outline-none focus:ring-1 focus:ring-primary"
                maxLength={100}
                autoFocus
              />
              <Button
                variant="primary"
                size="sm"
                onClick={handleSave}
                disabled={!canSave || isCreating}
                loading={isCreating}
              >
                Save
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => { setShowSaveForm(false); setSaveName(''); }}
              >
                &times;
              </Button>
            </div>
          ) : (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowSaveForm(true)}
              className="w-full justify-center text-xs"
            >
              <Plus className="h-3 w-3 mr-1" />
              Save Current Route
            </Button>
          )}
        </>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="flex justify-center py-2">
          <Loader2 className="h-4 w-4 animate-spin text-text-secondary" />
        </div>
      )}

      {/* Bookmarks list */}
      {!isLoading && bookmarks.length === 0 && (
        <p className="text-xs text-text-secondary text-center py-2">No saved routes yet</p>
      )}

      {bookmarks.map((bm) => (
        <div
          key={bm.id}
          className="group flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-card-hover transition-colors cursor-pointer"
          onClick={() => onLoad?.(bm)}
        >
          <div className="flex-1 min-w-0">
            <div className="text-xs font-medium text-text truncate">{bm.name}</div>
            <div className="text-[10px] text-text-secondary truncate">
              {bm.from_system} &rarr; {bm.to_system}
            </div>
          </div>
          <Badge variant="default" className="text-[9px] px-1 py-0 shrink-0">
            {bm.profile}
          </Badge>
          {deleteConfirm === bm.id ? (
            <div className="flex gap-1">
              <button
                onClick={(e) => { e.stopPropagation(); handleDelete(bm.id); }}
                className="text-risk-red text-[10px] hover:underline"
                disabled={isDeleting}
              >
                {isDeleting ? '...' : 'Yes'}
              </button>
              <button
                onClick={(e) => { e.stopPropagation(); setDeleteConfirm(null); }}
                className="text-text-secondary text-[10px] hover:underline"
              >
                No
              </button>
            </div>
          ) : (
            <button
              onClick={(e) => { e.stopPropagation(); setDeleteConfirm(bm.id); }}
              className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-card text-text-secondary hover:text-risk-red transition-all"
              title="Delete bookmark"
            >
              <Trash2 className="h-3 w-3" />
            </button>
          )}
        </div>
      ))}
    </div>
  );
}
