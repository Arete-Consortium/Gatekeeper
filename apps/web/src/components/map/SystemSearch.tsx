'use client';

import React, { useState, useRef, useCallback, useMemo, useEffect } from 'react';
import { Search } from 'lucide-react';
import type { MapSystem } from './types';

interface SystemSearchProps {
  systems: MapSystem[];
  onSelect: (system: MapSystem) => void;
  className?: string;
}

/**
 * System search with fuzzy matching and full keyboard navigation.
 * - Case-insensitive startsWith matching
 * - Up to 8 results in dropdown
 * - Enter selects first/highlighted match
 * - Arrow keys navigate results
 * - Escape closes dropdown
 */
export function SystemSearch({ systems, onSelect, className }: SystemSearchProps) {
  const [query, setQuery] = useState('');
  const [activeIndex, setActiveIndex] = useState(0);
  const [isOpen, setIsOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const results = useMemo(() => {
    if (!query) return [];
    const lowerQuery = query.toLowerCase();
    // startsWith gets priority, then includes
    const startsWith: MapSystem[] = [];
    const includes: MapSystem[] = [];
    for (const s of systems) {
      const lower = s.name.toLowerCase();
      if (lower.startsWith(lowerQuery)) {
        startsWith.push(s);
      } else if (lower.includes(lowerQuery)) {
        includes.push(s);
      }
      // Early exit once we have enough
      if (startsWith.length + includes.length >= 16) break;
    }
    return [...startsWith, ...includes].slice(0, 8);
  }, [systems, query]);

  // Open dropdown when we have results
  useEffect(() => {
    setIsOpen(results.length > 0 && query.length > 0);
    setActiveIndex(0);
  }, [results, query]);

  // Scroll active item into view
  useEffect(() => {
    if (!listRef.current) return;
    const active = listRef.current.children[activeIndex] as HTMLElement | undefined;
    active?.scrollIntoView({ block: 'nearest' });
  }, [activeIndex]);

  const handleSelect = useCallback(
    (system: MapSystem) => {
      setQuery('');
      setIsOpen(false);
      onSelect(system);
    },
    [onSelect]
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (!isOpen) return;

      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setActiveIndex((prev) => Math.min(prev + 1, results.length - 1));
          break;
        case 'ArrowUp':
          e.preventDefault();
          setActiveIndex((prev) => Math.max(prev - 1, 0));
          break;
        case 'Enter':
          e.preventDefault();
          if (results[activeIndex]) {
            handleSelect(results[activeIndex]);
          }
          break;
        case 'Escape':
          e.preventDefault();
          setIsOpen(false);
          setQuery('');
          inputRef.current?.blur();
          break;
      }
    },
    [isOpen, results, activeIndex, handleSelect]
  );

  const secColorClass = (sec: number) =>
    sec >= 0.5 ? 'text-green-400' : sec > 0 ? 'text-yellow-400' : 'text-red-400';

  return (
    <div className={`relative ${className || ''}`}>
      <label htmlFor="system-search" className="sr-only">
        Search for a system
      </label>
      <input
        ref={inputRef}
        id="system-search"
        type="text"
        role="combobox"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={handleKeyDown}
        onFocus={() => {
          if (results.length > 0) setIsOpen(true);
        }}
        onBlur={() => {
          // Delay to allow click on result
          setTimeout(() => setIsOpen(false), 150);
        }}
        placeholder="Search system..."
        className="w-36 sm:w-48 px-3 py-1.5 bg-card border border-border rounded-lg text-sm text-text placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary"
        aria-autocomplete="list"
        aria-expanded={isOpen}
        aria-controls="search-results"
        aria-haspopup="listbox"
        aria-activedescendant={isOpen && results[activeIndex] ? `search-result-${results[activeIndex].systemId}` : undefined}
      />
      <Search
        className="absolute right-2 top-1/2 -translate-y-1/2 h-4 w-4 text-text-secondary pointer-events-none"
        aria-hidden="true"
      />

      {isOpen && (
        <div
          ref={listRef}
          id="search-results"
          className="absolute z-50 w-64 mt-1 bg-card border border-border rounded-lg shadow-lg max-h-60 overflow-y-auto"
          role="listbox"
          aria-label="System search results"
        >
          {results.map((system, index) => (
            <button
              key={system.systemId}
              id={`search-result-${system.systemId}`}
              onClick={() => handleSelect(system)}
              onMouseEnter={() => setActiveIndex(index)}
              className={`w-full px-3 py-2 text-left text-sm flex justify-between items-center transition-colors ${
                index === activeIndex
                  ? 'bg-primary/20 text-text'
                  : 'hover:bg-card-hover text-text'
              }`}
              role="option"
              aria-selected={index === activeIndex}
              aria-label={`${system.name}, security ${system.security.toFixed(1)}${system.regionName ? `, ${system.regionName}` : ''}`}
            >
              <div className="flex flex-col min-w-0">
                <span className="truncate">{system.name}</span>
                {system.regionName && (
                  <span className="text-xs text-text-secondary truncate">{system.regionName}</span>
                )}
              </div>
              <span className={`text-xs font-mono shrink-0 ${secColorClass(system.security)}`}>
                {system.security.toFixed(1)}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default SystemSearch;
