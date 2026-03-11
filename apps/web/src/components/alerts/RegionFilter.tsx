'use client';

import { useState, useRef, useEffect, useId } from 'react';
import { cn } from '@/lib/utils';
import { ChevronDown } from 'lucide-react';

/**
 * Hardcoded EVE Online region names with IDs.
 * Using a static list avoids an API call for ~100 entries that rarely change.
 */
export const EVE_REGIONS: { id: number; name: string }[] = [
  { id: 10000001, name: 'Derelik' },
  { id: 10000002, name: 'The Forge' },
  { id: 10000003, name: 'Vale of the Silent' },
  { id: 10000005, name: 'Detorid' },
  { id: 10000006, name: 'Wicked Creek' },
  { id: 10000007, name: 'Cache' },
  { id: 10000008, name: 'Scalding Pass' },
  { id: 10000009, name: 'Insmother' },
  { id: 10000010, name: 'Tribute' },
  { id: 10000011, name: 'Great Wildlands' },
  { id: 10000012, name: 'Curse' },
  { id: 10000013, name: 'Malpais' },
  { id: 10000014, name: 'Catch' },
  { id: 10000015, name: 'Venal' },
  { id: 10000016, name: 'Lonetrek' },
  { id: 10000018, name: 'The Spire' },
  { id: 10000020, name: 'Tash-Murkon' },
  { id: 10000021, name: 'Outer Passage' },
  { id: 10000022, name: 'Stain' },
  { id: 10000023, name: 'Pure Blind' },
  { id: 10000025, name: 'Immensea' },
  { id: 10000027, name: 'Etherium Reach' },
  { id: 10000028, name: 'Molden Heath' },
  { id: 10000029, name: 'Geminate' },
  { id: 10000030, name: 'Heimatar' },
  { id: 10000031, name: 'Impass' },
  { id: 10000032, name: 'Sinq Laison' },
  { id: 10000033, name: 'The Citadel' },
  { id: 10000034, name: 'The Kalevala Expanse' },
  { id: 10000035, name: 'Deklein' },
  { id: 10000036, name: 'Devoid' },
  { id: 10000037, name: 'Everyshore' },
  { id: 10000038, name: 'The Bleak Lands' },
  { id: 10000039, name: 'Esoteria' },
  { id: 10000040, name: 'Oasa' },
  { id: 10000041, name: 'Syndicate' },
  { id: 10000042, name: 'Metropolis' },
  { id: 10000043, name: 'Domain' },
  { id: 10000044, name: 'Solitude' },
  { id: 10000045, name: 'Tenal' },
  { id: 10000046, name: 'Fade' },
  { id: 10000047, name: 'Providence' },
  { id: 10000048, name: 'Placid' },
  { id: 10000049, name: 'Khanid' },
  { id: 10000050, name: 'Querious' },
  { id: 10000051, name: 'Cloud Ring' },
  { id: 10000052, name: 'Kador' },
  { id: 10000053, name: 'Cobalt Edge' },
  { id: 10000054, name: 'Aridia' },
  { id: 10000055, name: 'Branch' },
  { id: 10000056, name: 'Feythabolis' },
  { id: 10000057, name: 'Outer Ring' },
  { id: 10000058, name: 'Fountain' },
  { id: 10000059, name: 'Paragon Soul' },
  { id: 10000060, name: 'Delve' },
  { id: 10000061, name: 'Tenerifis' },
  { id: 10000062, name: 'Omist' },
  { id: 10000063, name: 'Period Basis' },
  { id: 10000064, name: 'Essence' },
  { id: 10000065, name: 'Kor-Azor' },
  { id: 10000066, name: 'Perrigen Falls' },
  { id: 10000067, name: 'Genesis' },
  { id: 10000068, name: 'Verge Vendor' },
  { id: 10000069, name: 'Black Rise' },
  { id: 10000070, name: 'Pochven' },
];

interface RegionFilterProps {
  value: string;
  onChange: (regionName: string) => void;
}

export function RegionFilter({ value, onChange }: RegionFilterProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [highlightIndex, setHighlightIndex] = useState(-1);
  const containerRef = useRef<HTMLDivElement>(null);
  const listboxRef = useRef<HTMLUListElement>(null);
  const inputId = useId();
  const listboxId = useId();

  const filtered = value.trim()
    ? EVE_REGIONS.filter((r) =>
        r.name.toLowerCase().includes(value.toLowerCase())
      )
    : EVE_REGIONS;

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Scroll highlighted option into view
  useEffect(() => {
    if (highlightIndex >= 0 && listboxRef.current) {
      const item = listboxRef.current.children[highlightIndex] as HTMLElement;
      item?.scrollIntoView?.({ block: 'nearest' });
    }
  }, [highlightIndex]);

  function handleInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    onChange(e.target.value);
    setIsOpen(true);
    setHighlightIndex(-1);
  }

  function selectRegion(regionName: string) {
    onChange(regionName);
    setIsOpen(false);
    setHighlightIndex(-1);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (!isOpen && (e.key === 'ArrowDown' || e.key === 'ArrowUp')) {
      setIsOpen(true);
      setHighlightIndex(0);
      e.preventDefault();
      return;
    }

    if (!isOpen) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setHighlightIndex((prev) => Math.min(prev + 1, filtered.length - 1));
        break;
      case 'ArrowUp':
        e.preventDefault();
        setHighlightIndex((prev) => Math.max(prev - 1, 0));
        break;
      case 'Enter':
        e.preventDefault();
        if (highlightIndex >= 0 && highlightIndex < filtered.length) {
          selectRegion(filtered[highlightIndex].name);
        }
        break;
      case 'Escape':
        setIsOpen(false);
        setHighlightIndex(-1);
        break;
    }
  }

  return (
    <div className="w-full" ref={containerRef}>
      <label
        htmlFor={inputId}
        className="block text-sm font-medium text-text-secondary mb-1.5"
      >
        Region (optional)
      </label>
      <div className="relative">
        <input
          id={inputId}
          type="text"
          role="combobox"
          aria-expanded={isOpen}
          aria-controls={listboxId}
          aria-autocomplete="list"
          aria-activedescendant={
            highlightIndex >= 0 ? `${listboxId}-option-${highlightIndex}` : undefined
          }
          value={value}
          onChange={handleInputChange}
          onFocus={() => setIsOpen(true)}
          onKeyDown={handleKeyDown}
          placeholder="Type to filter regions..."
          className={cn(
            'w-full px-4 py-2 bg-card border border-border rounded-lg',
            'text-text placeholder:text-text-secondary',
            'focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary',
            'transition-all duration-200 pr-10'
          )}
        />
        <ChevronDown
          className={cn(
            'absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-secondary transition-transform',
            isOpen && 'rotate-180'
          )}
          aria-hidden="true"
        />

        {isOpen && filtered.length > 0 && (
          <ul
            id={listboxId}
            ref={listboxRef}
            role="listbox"
            aria-label="EVE regions"
            className={cn(
              'absolute z-50 mt-1 w-full max-h-48 overflow-auto',
              'bg-card border border-border rounded-lg shadow-lg'
            )}
          >
            {filtered.map((region, index) => (
              <li
                key={region.id}
                id={`${listboxId}-option-${index}`}
                role="option"
                aria-selected={highlightIndex === index}
                className={cn(
                  'px-4 py-2 text-sm text-text cursor-pointer',
                  highlightIndex === index && 'bg-primary/20',
                  region.name === value && 'font-medium'
                )}
                onMouseDown={(e) => {
                  e.preventDefault();
                  selectRegion(region.name);
                }}
                onMouseEnter={() => setHighlightIndex(index)}
              >
                {region.name}
              </li>
            ))}
          </ul>
        )}

        {isOpen && filtered.length === 0 && value.trim() && (
          <div
            className={cn(
              'absolute z-50 mt-1 w-full',
              'bg-card border border-border rounded-lg shadow-lg',
              'px-4 py-2 text-sm text-text-secondary'
            )}
          >
            No matching regions
          </div>
        )}
      </div>
    </div>
  );
}
