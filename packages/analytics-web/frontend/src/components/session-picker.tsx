import { useState, useMemo } from "react";
import type { SessionInfo } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { formatDate, formatDuration } from "@/lib/api";

interface SessionPickerProps {
  sessions: SessionInfo[];
  selectedId: string | null;
  onSelect: (session: SessionInfo) => void;
  loading: boolean;
}

export function SessionPicker({ sessions, selectedId, onSelect, loading }: SessionPickerProps) {
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    if (!search.trim()) return sessions;
    const q = search.toLowerCase();
    return sessions.filter(
      (s) =>
        s.title?.toLowerCase().includes(q) ||
        s.session_id.toLowerCase().includes(q) ||
        s.work_dir_hash?.toLowerCase().includes(q),
    );
  }, [sessions, search]);

  if (loading) {
    return <div className="text-sm text-muted-foreground p-4">Loading sessions...</div>;
  }

  return (
    <div className="space-y-2">
      <Input
        placeholder="Search sessions..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />
      <div className="max-h-[300px] overflow-y-auto space-y-1">
        {filtered.map((s) => (
          <button
            key={`${s.work_dir_hash}/${s.session_id}`}
            onClick={() => onSelect(s)}
            className={`w-full text-left p-2 rounded text-sm transition-colors cursor-pointer hover:bg-accent ${
              selectedId === s.session_id ? "bg-accent" : ""
            }`}
          >
            <div className="font-medium truncate">
              {s.title || s.session_id.slice(0, 16)}
            </div>
            <div className="text-xs text-muted-foreground flex gap-2">
              <span>{formatDate(s.last_updated)}</span>
              <span>{s.turns} turns</span>
              {s.total_size > 0 && <span>{(s.total_size / 1024).toFixed(0)} KB</span>}
            </div>
          </button>
        ))}
        {filtered.length === 0 && (
          <div className="text-sm text-muted-foreground p-2">No sessions found</div>
        )}
      </div>
    </div>
  );
}
