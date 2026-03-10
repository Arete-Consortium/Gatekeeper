'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { GatekeeperAPI } from '@/lib/api';
import type { BookmarkCreate, BookmarkResponse } from '@/lib/types';
import { useAuth } from '@/contexts/AuthContext';

export function useBookmarks() {
  const { isAuthenticated } = useAuth();
  const queryClient = useQueryClient();

  const {
    data,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['bookmarks'],
    queryFn: () => GatekeeperAPI.getBookmarks(),
    staleTime: 60 * 1000,
    enabled: isAuthenticated,
  });

  const createMutation = useMutation({
    mutationFn: (bookmark: BookmarkCreate) => GatekeeperAPI.createBookmark(bookmark),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bookmarks'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => GatekeeperAPI.deleteBookmark(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bookmarks'] });
    },
  });

  return {
    bookmarks: data?.bookmarks ?? [],
    total: data?.total ?? 0,
    isLoading,
    error,
    createBookmark: createMutation.mutateAsync,
    deleteBookmark: deleteMutation.mutateAsync,
    isCreating: createMutation.isPending,
    isDeleting: deleteMutation.isPending,
  };
}
