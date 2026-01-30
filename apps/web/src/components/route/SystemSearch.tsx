'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { GatekeeperAPI } from '@/lib/api';
import { Input } from '@/components/ui';
import { SecurityBadge } from '@/components/system';
import { cn, debounce } from '@/lib/utils';
import type { System } from '@/lib/types';

interface SystemSearchProps {
  label?: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  error?: string;
}

export function SystemSearch({
  label,
  value,
  onChange,
  placeholder = 'Enter system name...',
  error,
}: SystemSearchProps) {
  const [inputValue, setInputValue] = useState(value);
  const [isOpen, setIsOpen] = useState(false);
  const [highlightIndex, setHighlightIndex] = useState(-1);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const { data: systems } = useQuery<System[]>({
    queryKey: ['systems'],
    queryFn: () => GatekeeperAPI.getSystems(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  const filteredSystems =
    systems && inputValue.length >= 2
      ? systems
          .filter((s) =>
            s.name.toLowerCase().startsWith(inputValue.toLowerCase())
          )
          .slice(0, 8)
      : [];

  // Update input when value prop changes
  useEffect(() => {
    setInputValue(value);
  }, [value]);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        wrapperRef.current &&
        !wrapperRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = (system: System) => {
    setInputValue(system.name);
    onChange(system.name);
    setIsOpen(false);
    setHighlightIndex(-1);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setInputValue(val);
    setIsOpen(true);
    setHighlightIndex(-1);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen || filteredSystems.length === 0) {
      if (e.key === 'Enter') {
        onChange(inputValue);
      }
      return;
    }

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setHighlightIndex((prev) =>
          prev < filteredSystems.length - 1 ? prev + 1 : 0
        );
        break;
      case 'ArrowUp':
        e.preventDefault();
        setHighlightIndex((prev) =>
          prev > 0 ? prev - 1 : filteredSystems.length - 1
        );
        break;
      case 'Enter':
        e.preventDefault();
        if (highlightIndex >= 0) {
          handleSelect(filteredSystems[highlightIndex]);
        } else {
          onChange(inputValue);
          setIsOpen(false);
        }
        break;
      case 'Escape':
        setIsOpen(false);
        break;
    }
  };

  return (
    <div ref={wrapperRef} className="relative">
      <Input
        ref={inputRef}
        label={label}
        value={inputValue}
        onChange={handleInputChange}
        onFocus={() => inputValue.length >= 2 && setIsOpen(true)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        error={error}
        autoComplete="off"
      />

      {isOpen && filteredSystems.length > 0 && (
        <div className="absolute z-50 w-full mt-1 bg-card border border-border rounded-lg shadow-lg overflow-hidden">
          {filteredSystems.map((system, index) => (
            <button
              key={system.system_id}
              type="button"
              className={cn(
                'w-full px-4 py-2 text-left flex items-center justify-between',
                'hover:bg-card-hover transition-colors',
                highlightIndex === index && 'bg-card-hover'
              )}
              onClick={() => handleSelect(system)}
            >
              <span className="text-text font-medium">{system.name}</span>
              <SecurityBadge security={system.security_status} size="sm" />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
