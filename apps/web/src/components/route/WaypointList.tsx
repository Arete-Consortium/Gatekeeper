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
  onInsertAfter,
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
  onInsertAfter: (index: number) => void;
  onDragStart: (index: number) => void;
  onDragOver: (e: React.DragEvent, index: number) => void;
  onDragEnd: () => void;
  onDrop: (index: number) => void;
  isDragTarget: boolean;
  isDragging: boolean;
}) {
  const isOrigin = index === 0;
  const isDestination = index === total - 1;
  const canDrag = total > 2; // Can drag any row if 3+ waypoints
  const canRemove = total > 2; // Can remove if more than origin+dest

  const label = isOrigin ? 'Origin' : isDestination ? 'Destination' : `Via ${index}`;
  const placeholder = isOrigin
    ? 'Origin system...'
    : isDestination
      ? 'Destination system...'
      : 'Via system...';

  return (
    <div className="group relative">
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
          flex items-center gap-2 sm:gap-3 p-2 sm:p-3 rounded-lg transition-all
          ${isDragTarget ? 'ring-2 ring-primary ring-offset-1 ring-offset-background' : ''}
          ${isDragging ? 'opacity-40' : ''}
          bg-card border border-border
          ${canDrag ? 'cursor-grab active:cursor-grabbing' : ''}
        `}
      >
        {/* Drag handle */}
        <div className={`flex-shrink-0 touch-none ${canDrag ? 'text-text-secondary' : 'text-border'}`}>
          <GripVertical className="h-5 w-5" />
        </div>

        {/* Index indicator */}
        <div className={`
          flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold
          ${isOrigin ? 'bg-green-500/20 text-green-400' : ''}
          ${isDestination ? 'bg-red-500/20 text-red-400' : ''}
          ${!isOrigin && !isDestination ? 'bg-primary/20 text-primary' : ''}
        `}>
          {isOrigin ? 'A' : isDestination ? 'B' : index}
        </div>

        {/* System search */}
        <div className="flex-1 min-w-0">
          <SystemSearch
            label={label}
            value={waypoint.system}
            onChange={(val) => onSystemChange(waypoint.id, val)}
            placeholder={placeholder}
          />
        </div>

        {/* Remove button */}
        {canRemove && (
          <button
            type="button"
            onClick={() => onRemove(waypoint.id)}
            className="flex-shrink-0 p-2 text-text-secondary hover:text-red-400 active:text-red-300 transition-colors rounded-lg"
            aria-label={`Remove ${label}`}
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Insert-between button — appears on hover between rows */}
      {!isDestination && (
        <button
          type="button"
          onClick={() => onInsertAfter(index)}
          className="absolute -bottom-3 left-1/2 -translate-x-1/2 z-10 opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity bg-primary text-white rounded-full w-6 h-6 flex items-center justify-center text-xs shadow-lg hover:scale-110"
          aria-label={`Insert waypoint after ${label}`}
        >
          <Plus className="h-3 w-3" />
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

  const handleInsertAfter = useCallback((index: number) => {
    const newWaypoints = [...waypoints];
    newWaypoints.splice(index + 1, 0, {
      id: generateWaypointId(),
      system: '',
    });
    onChange(newWaypoints);
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
    const newWaypoints = systems.map((s) => ({ id: generateWaypointId(), system: s }));
    onChange(newWaypoints);
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

  const handleDragStart = useCallback((index: number) => {
    setDragIndex(index);
  }, []);

  const handleDragOver = useCallback((_e: React.DragEvent, index: number) => {
    if (dragIndex === null || dragIndex === index) return;
    setDropTargetIndex(index);
  }, [dragIndex]);

  const handleDragEnd = useCallback(() => {
    setDragIndex(null);
    setDropTargetIndex(null);
  }, []);

  const handleDrop = useCallback((targetIndex: number) => {
    if (dragIndex === null || dragIndex === targetIndex) {
      handleDragEnd();
      return;
    }

    const newWaypoints = [...waypoints];
    const [moved] = newWaypoints.splice(dragIndex, 1);
    newWaypoints.splice(targetIndex, 0, moved);
    onChange(newWaypoints);
    handleDragEnd();
  }, [dragIndex, waypoints, onChange, handleDragEnd]);

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <span className="text-xs font-medium text-text-secondary uppercase tracking-wider">
          Waypoints · drag to reorder
        </span>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => setShowBulkInput(!showBulkInput)}
            className="p-1.5 rounded text-text-secondary hover:text-primary hover:bg-primary/10 transition-colors"
            title="Paste route (Jita:Amarr:Dodixie)"
          >
            <Type className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={handleReverse}
            className="p-1.5 rounded text-text-secondary hover:text-primary hover:bg-primary/10 transition-colors"
            title="Reverse route"
          >
            <ArrowDownUp className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={handleClearAll}
            className="p-1.5 rounded text-text-secondary hover:text-red-400 hover:bg-red-400/10 transition-colors"
            title="Clear all"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Bulk paste input */}
      {showBulkInput && (
        <div className="bg-background rounded-lg border border-border p-3 space-y-2">
          <label className="text-xs text-text-secondary">
            Paste systems separated by <code className="bg-card px-1 rounded">:</code> <code className="bg-card px-1 rounded">,</code> or newlines
          </label>
          <textarea
            value={bulkText}
            onChange={(e) => setBulkText(e.target.value)}
            placeholder="Jita:Amarr:Dodixie:Rens"
            className="w-full h-20 px-3 py-2 bg-card border border-border rounded-lg text-sm text-text placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary resize-none"
          />
          <div className="flex items-center justify-between">
            <span className="text-xs text-text-secondary">
              {parseSystemList(bulkText).length} systems detected
            </span>
            <button
              type="button"
              onClick={handleBulkImport}
              disabled={parseSystemList(bulkText).length < 2}
              className="px-3 py-1.5 text-xs font-medium bg-primary text-white rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Import Route
            </button>
          </div>
        </div>
      )}

      {/* Waypoint rows */}
      <div className="space-y-4">
        {waypoints.map((wp, index) => (
          <WaypointRow
            key={wp.id}
            waypoint={wp}
            index={index}
            total={waypoints.length}
            onSystemChange={handleSystemChange}
            onRemove={handleRemove}
            onInsertAfter={handleInsertAfter}
            onDragStart={handleDragStart}
            onDragOver={handleDragOver}
            onDragEnd={handleDragEnd}
            onDrop={handleDrop}
            isDragTarget={dropTargetIndex === index}
            isDragging={dragIndex === index}
          />
        ))}
      </div>

      {/* Add Waypoint Button */}
      <button
        type="button"
        onClick={handleAddWaypoint}
        className="w-full flex items-center justify-center gap-2 p-3 rounded-lg border-2 border-dashed border-border text-text-secondary hover:border-primary hover:text-primary active:bg-primary/5 transition-all"
      >
        <Plus className="h-4 w-4" />
        <span className="text-sm font-medium">Add Waypoint</span>
      </button>

      {/* Avoid Systems */}
      <div className="space-y-2">
        <span className="text-xs font-medium text-text-secondary uppercase tracking-wider">
          Avoid Systems
        </span>
        <div className="flex gap-2">
          <div className="flex-1">
            <SystemSearch
              label=""
              value={avoidInput}
              onChange={setAvoidInput}
              placeholder="Add system to avoid..."
            />
          </div>
          <button
            type="button"
            onClick={() => handleAddAvoid(avoidInput)}
            disabled={!avoidInput}
            className="px-3 py-2 text-sm font-medium bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Avoid
          </button>
        </div>
        {avoidSystems.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {avoidSystems.map((s) => (
              <span
                key={s}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-red-500/10 text-red-400 text-xs font-medium border border-red-500/20"
              >
                {s}
                <button
                  type="button"
                  onClick={() => handleRemoveAvoid(s)}
                  className="hover:text-red-300 transition-colors"
                  aria-label={`Stop avoiding ${s}`}
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            ))}
          </div>
        ) : (
          <p className="text-xs text-text-secondary">No systems to avoid</p>
        )}
      </div>
    </div>
  );
}
