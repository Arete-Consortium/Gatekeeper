'use client';

import { useState, useRef, useCallback, memo } from 'react';
import { GripVertical, X, Plus } from 'lucide-react';
import { SystemSearch } from './SystemSearch';

export interface Waypoint {
  id: string;
  system: string;
}

interface WaypointListProps {
  waypoints: Waypoint[];
  onChange: (waypoints: Waypoint[]) => void;
}

let waypointCounter = 0;
export function generateWaypointId(): string {
  return `wp-${++waypointCounter}-${Date.now()}`;
}

const WaypointRow = memo(function WaypointRow({
  waypoint,
  index,
  total,
  onSystemChange,
  onRemove,
  onDragStart,
  onDragOver,
  onDrop,
  isDragTarget,
}: {
  waypoint: Waypoint;
  index: number;
  total: number;
  onSystemChange: (id: string, system: string) => void;
  onRemove: (id: string) => void;
  onDragStart: (index: number) => void;
  onDragOver: (e: React.DragEvent, index: number) => void;
  onDrop: (index: number) => void;
  isDragTarget: boolean;
}) {
  const isOrigin = index === 0;
  const isDestination = index === total - 1;
  const isWaypoint = !isOrigin && !isDestination;

  const label = isOrigin ? 'Origin' : isDestination ? 'Destination' : `Waypoint ${index}`;
  const placeholder = isOrigin
    ? 'Origin system...'
    : isDestination
      ? 'Destination system...'
      : 'Via system...';

  return (
    <div
      draggable={isWaypoint}
      onDragStart={(e) => {
        if (!isWaypoint) { e.preventDefault(); return; }
        e.dataTransfer.effectAllowed = 'move';
        onDragStart(index);
      }}
      onDragOver={(e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        onDragOver(e, index);
      }}
      onDrop={(e) => {
        e.preventDefault();
        onDrop(index);
      }}
      className={`
        flex items-center gap-2 sm:gap-3 p-2 sm:p-3 rounded-lg transition-all
        ${isDragTarget ? 'bg-primary/10 border-2 border-dashed border-primary' : 'bg-card border border-border'}
        ${isWaypoint ? 'cursor-grab active:cursor-grabbing' : ''}
      `}
    >
      {/* Drag handle */}
      <div className={`flex-shrink-0 ${isWaypoint ? 'text-text-secondary' : 'text-transparent'}`}>
        <GripVertical className="h-5 w-5" />
      </div>

      {/* Index indicator */}
      <div className={`
        flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold
        ${isOrigin ? 'bg-green-500/20 text-green-400' : ''}
        ${isDestination ? 'bg-red-500/20 text-red-400' : ''}
        ${isWaypoint ? 'bg-primary/20 text-primary' : ''}
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

      {/* Remove button (waypoints only) */}
      {isWaypoint && (
        <button
          type="button"
          onClick={() => onRemove(waypoint.id)}
          className="flex-shrink-0 p-2 text-text-secondary hover:text-red-400 active:text-red-300 transition-colors rounded-lg"
          aria-label={`Remove waypoint ${index}`}
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  );
});

export function WaypointList({ waypoints, onChange }: WaypointListProps) {
  const [dragIndex, setDragIndex] = useState<number | null>(null);
  const [dropTargetIndex, setDropTargetIndex] = useState<number | null>(null);

  const handleSystemChange = useCallback((id: string, system: string) => {
    onChange(waypoints.map((wp) => (wp.id === id ? { ...wp, system } : wp)));
  }, [waypoints, onChange]);

  const handleRemove = useCallback((id: string) => {
    onChange(waypoints.filter((wp) => wp.id !== id));
  }, [waypoints, onChange]);

  const handleAddWaypoint = useCallback(() => {
    // Insert before destination (last item)
    const newWaypoints = [...waypoints];
    newWaypoints.splice(waypoints.length - 1, 0, {
      id: generateWaypointId(),
      system: '',
    });
    onChange(newWaypoints);
  }, [waypoints, onChange]);

  const handleDragStart = useCallback((index: number) => {
    setDragIndex(index);
  }, []);

  const handleDragOver = useCallback((_e: React.DragEvent, index: number) => {
    if (dragIndex === null) return;
    // Only allow dropping on waypoint positions (not origin/destination)
    if (index === 0 || index === waypoints.length - 1) return;
    setDropTargetIndex(index);
  }, [dragIndex, waypoints.length]);

  const handleDrop = useCallback((targetIndex: number) => {
    if (dragIndex === null || dragIndex === targetIndex) {
      setDragIndex(null);
      setDropTargetIndex(null);
      return;
    }

    // Don't allow dropping on origin or destination
    if (targetIndex === 0 || targetIndex === waypoints.length - 1) {
      setDragIndex(null);
      setDropTargetIndex(null);
      return;
    }

    const newWaypoints = [...waypoints];
    const [moved] = newWaypoints.splice(dragIndex, 1);
    newWaypoints.splice(targetIndex, 0, moved);
    onChange(newWaypoints);

    setDragIndex(null);
    setDropTargetIndex(null);
  }, [dragIndex, waypoints, onChange]);

  return (
    <div className="space-y-2">
      <div
        className="space-y-2"
        onDragEnd={() => { setDragIndex(null); setDropTargetIndex(null); }}
      >
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
            onDrop={handleDrop}
            isDragTarget={dropTargetIndex === index}
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
    </div>
  );
}
