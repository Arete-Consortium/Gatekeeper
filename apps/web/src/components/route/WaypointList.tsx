'use client';

import { useState, useCallback, memo } from 'react';
import { GripVertical, X, Plus, ArrowDownUp, Trash2, Type } from 'lucide-react';
import { SystemSearch } from './SystemSearch';

export interface Waypoint {
  id: string;
  system: string;
}

interface WaypointListProps {
  waypoints: Waypoint[];
  onChange: (waypoints: Waypoint[]) => void;
  avoidSystems: string[];
  onAvoidChange: (systems: string[]) => void;
}

let waypointCounter = 0;
export function generateWaypointId(): string {
  return `wp-${++waypointCounter}-${Date.now()}`;
}

function parseSystemList(text: string): string[] {
  return text
    .split(/[:\n,;>→]+/)
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
}

const WaypointRow = memo(function WaypointRow({
  waypoint,
  index,
  total,
  onSystemChange,
  onRemove,
  onDragStart,
  onDragOver,
  onDragEnd,
  onDrop,
  isDragTarget,
  isDragging,
}: {
  waypoint: Waypoint;
  index: number;
  total: number;
  onSystemChange: (id: string, system: string) => void;
  onRemove: (id: string) => void;
  onDragStart: (index: number) => void;
  onDragOver: (e: React.DragEvent, index: number) => void;
  onDragEnd: () => void;
  onDrop: (index: number) => void;
  isDragTarget: boolean;
  isDragging: boolean;
}) {
  const isOrigin = index === 0;
  const isDestination = index === total - 1;
  const canDrag = total > 2;
  const canRemove = total > 2;

  const placeholder = isOrigin
    ? 'Origin...'
    : isDestination
      ? 'Destination...'
      : 'Via...';

  return (
    <div
      draggable={canDrag}
      onDragStart={(e) => {
        if (!canDrag) { e.preventDefault(); return; }
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', String(index));
        onDragStart(index);
      }}
      onDragOver={(e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        onDragOver(e, index);
      }}
      onDragEnd={onDragEnd}
      onDrop={(e) => {
        e.preventDefault();
        onDrop(index);
      }}
      className={`
        flex items-center gap-2 py-1.5 transition-all
        ${isDragTarget ? 'bg-primary/5 rounded' : ''}
        ${isDragging ? 'opacity-30' : ''}
        ${canDrag ? 'cursor-grab active:cursor-grabbing' : ''}
      `}
    >
      {/* Drag handle */}
      <div className={`flex-shrink-0 ${canDrag ? 'text-text-secondary' : 'text-border'}`}>
        <GripVertical className="h-4 w-4" />
      </div>

      {/* Index badge */}
      <div className={`
        flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold
        ${isOrigin ? 'bg-green-500/20 text-green-400' : ''}
        ${isDestination ? 'bg-red-500/20 text-red-400' : ''}
        ${!isOrigin && !isDestination ? 'bg-primary/20 text-primary' : ''}
      `}>
        {isOrigin ? 'A' : isDestination ? 'B' : index}
      </div>

      {/* System search — compact */}
      <div className="w-48">
        <SystemSearch
          value={waypoint.system}
          onChange={(val) => onSystemChange(waypoint.id, val)}
          placeholder={placeholder}
        />
      </div>

      {/* Remove */}
      {canRemove && (
        <button
          type="button"
          onClick={() => onRemove(waypoint.id)}
          className="flex-shrink-0 p-1 text-text-secondary hover:text-red-400 transition-colors rounded"
          aria-label="Remove"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      )}
    </div>
  );
});

export function WaypointList({ waypoints, onChange, avoidSystems, onAvoidChange }: WaypointListProps) {
  const [dragIndex, setDragIndex] = useState<number | null>(null);
  const [dropTargetIndex, setDropTargetIndex] = useState<number | null>(null);
  const [showBulkInput, setShowBulkInput] = useState(false);
  const [bulkText, setBulkText] = useState('');
  const [avoidInput, setAvoidInput] = useState('');

  const handleSystemChange = useCallback((id: string, system: string) => {
    onChange(waypoints.map((wp) => (wp.id === id ? { ...wp, system } : wp)));
  }, [waypoints, onChange]);

  const handleRemove = useCallback((id: string) => {
    onChange(waypoints.filter((wp) => wp.id !== id));
  }, [waypoints, onChange]);

  const handleAddWaypoint = useCallback(() => {
    const newWaypoints = [...waypoints];
    newWaypoints.splice(waypoints.length - 1, 0, {
      id: generateWaypointId(),
      system: '',
    });
    onChange(newWaypoints);
  }, [waypoints, onChange]);

  const handleReverse = useCallback(() => {
    onChange([...waypoints].reverse());
  }, [waypoints, onChange]);

  const handleClearAll = useCallback(() => {
    onChange([
      { id: generateWaypointId(), system: '' },
      { id: generateWaypointId(), system: '' },
    ]);
  }, [onChange]);

  const handleBulkImport = useCallback(() => {
    const systems = parseSystemList(bulkText);
    if (systems.length < 2) return;
    onChange(systems.map((s) => ({ id: generateWaypointId(), system: s })));
    setBulkText('');
    setShowBulkInput(false);
  }, [bulkText, onChange]);

  const handleAddAvoid = useCallback((system: string) => {
    if (system && !avoidSystems.includes(system)) {
      onAvoidChange([...avoidSystems, system]);
    }
    setAvoidInput('');
  }, [avoidSystems, onAvoidChange]);

  const handleRemoveAvoid = useCallback((system: string) => {
    onAvoidChange(avoidSystems.filter((s) => s !== system));
  }, [avoidSystems, onAvoidChange]);

  const handleDragStart = useCallback((index: number) => setDragIndex(index), []);
  const handleDragOver = useCallback((_e: React.DragEvent, index: number) => {
    if (dragIndex === null || dragIndex === index) return;
    setDropTargetIndex(index);
  }, [dragIndex]);
  const handleDragEnd = useCallback(() => { setDragIndex(null); setDropTargetIndex(null); }, []);
  const handleDrop = useCallback((targetIndex: number) => {
    if (dragIndex === null || dragIndex === targetIndex) { handleDragEnd(); return; }
    const next = [...waypoints];
    const [moved] = next.splice(dragIndex, 1);
    next.splice(targetIndex, 0, moved);
    onChange(next);
    handleDragEnd();
  }, [dragIndex, waypoints, onChange, handleDragEnd]);

  return (
    <div className="space-y-4">
      {/* Two-column: Waypoints left, Avoid right */}
      <div className="flex flex-col lg:flex-row gap-6">
        {/* Waypoints column */}
        <div className="flex-1 min-w-0">
          {/* Header bar */}
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-text-secondary uppercase tracking-wider">
              Route
            </span>
            <div className="flex items-center gap-0.5">
              <button
                type="button"
                onClick={() => setShowBulkInput(!showBulkInput)}
                className={`p-1.5 rounded text-text-secondary hover:text-primary hover:bg-primary/10 transition-colors ${showBulkInput ? 'text-primary bg-primary/10' : ''}`}
                title="Paste route"
              >
                <Type className="h-3.5 w-3.5" />
              </button>
              <button
                type="button"
                onClick={handleReverse}
                className="p-1.5 rounded text-text-secondary hover:text-primary hover:bg-primary/10 transition-colors"
                title="Reverse route"
              >
                <ArrowDownUp className="h-3.5 w-3.5" />
              </button>
              <button
                type="button"
                onClick={handleClearAll}
                className="p-1.5 rounded text-text-secondary hover:text-red-400 hover:bg-red-400/10 transition-colors"
                title="Clear all"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>

          {/* Bulk paste */}
          {showBulkInput && (
            <div className="mb-3 bg-background rounded-lg border border-border p-2.5 space-y-2">
              <textarea
                value={bulkText}
                onChange={(e) => setBulkText(e.target.value)}
                placeholder="Jita:Amarr:Dodixie:Rens"
                className="w-full h-16 px-2.5 py-1.5 bg-card border border-border rounded text-sm text-text placeholder:text-text-secondary focus:outline-none focus:ring-1 focus:ring-primary resize-none font-mono"
              />
              <div className="flex items-center justify-between">
                <span className="text-[11px] text-text-secondary">
                  {parseSystemList(bulkText).length} systems · separate with <code className="bg-card px-1 rounded">:</code> <code className="bg-card px-1 rounded">,</code> or newline
                </span>
                <button
                  type="button"
                  onClick={handleBulkImport}
                  disabled={parseSystemList(bulkText).length < 2}
                  className="px-2.5 py-1 text-xs font-medium bg-primary text-white rounded hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Import
                </button>
              </div>
            </div>
          )}

          {/* Waypoint rows */}
          <div className="space-y-0.5">
            {waypoints.map((wp, index) => (
              <WaypointRow
                key={wp.id}
                waypoint={wp}
                index={index}
                total={waypoints.length}
                onSystemChange={handleSystemChange}
                onRemove={handleRemove}
                onDragStart={handleDragStart}
                onDragOver={handleDragOver}
                onDragEnd={handleDragEnd}
                onDrop={handleDrop}
                isDragTarget={dropTargetIndex === index}
                isDragging={dragIndex === index}
              />
            ))}
          </div>

          {/* Add Waypoint */}
          <button
            type="button"
            onClick={handleAddWaypoint}
            className="mt-2 flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium text-text-secondary hover:text-primary transition-colors"
          >
            <Plus className="h-3.5 w-3.5" />
            Add Waypoint
          </button>
        </div>

        {/* Avoid column */}
        <div className="lg:w-56">
          <span className="text-xs font-medium text-text-secondary uppercase tracking-wider block mb-2">
            Avoid Systems
          </span>
          <div className="flex gap-1.5 mb-2">
            <div className="flex-1 min-w-0">
              <SystemSearch
                value={avoidInput}
                onChange={setAvoidInput}
                placeholder="System..."
              />
            </div>
            <button
              type="button"
              onClick={() => handleAddAvoid(avoidInput)}
              disabled={!avoidInput}
              className="px-2 py-1.5 text-xs font-medium bg-red-500/20 text-red-400 rounded hover:bg-red-500/30 disabled:opacity-40 disabled:cursor-not-allowed transition-colors whitespace-nowrap"
            >
              Add
            </button>
          </div>
          {avoidSystems.length > 0 ? (
            <div className="flex flex-wrap gap-1.5">
              {avoidSystems.map((s) => (
                <span
                  key={s}
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-red-500/10 text-red-400 text-xs border border-red-500/20"
                >
                  {s}
                  <button
                    type="button"
                    onClick={() => handleRemoveAvoid(s)}
                    className="hover:text-red-300"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
            </div>
          ) : (
            <p className="text-xs text-text-secondary italic">None</p>
          )}
        </div>
      </div>
    </div>
  );
}
