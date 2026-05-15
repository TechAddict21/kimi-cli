import { useState, useMemo } from "react";
import type { SessionInfo } from "@/lib/api";
import { formatTime, formatDuration, formatBytes } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { RefreshCw, Search } from "lucide-react";

interface SessionListProps {
  sessions: SessionInfo[];
  loading: boolean;
  onSelectSession: (session: SessionInfo) => void;
  onRefresh: () => void;
}

export function SessionList({ sessions, loading, onSelectSession, onRefresh }: SessionListProps) {
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState<"date" | "turns" | "size">("date");
  const [filterArchived, setFilterArchived] = useState<"all" | "active" | "archived">("all");

  const filtered = useMemo(() => {
    let result = [...sessions];

    if (filterArchived === "active") result = result.filter((s) => !s.archived);
    else if (filterArchived === "archived") result = result.filter((s) => s.archived);

    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(
        (s) =>
          s.title?.toLowerCase().includes(q) ||
          s.session_id.toLowerCase().includes(q) ||
          s.work_dir_hash?.toLowerCase().includes(q),
      );
    }

    result.sort((a, b) => {
      switch (sortBy) {
        case "turns":
          return b.turns - a.turns;
        case "size":
          return b.total_size - a.total_size;
        case "date":
        default:
          return b.last_updated - a.last_updated;
      }
    });

    return result;
  }, [sessions, search, sortBy, filterArchived]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-muted-foreground animate-pulse">Loading sessions...</div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-4">
      <div className="flex items-center gap-2">
        <h1 className="text-xl font-semibold">Sessions ({sessions.length})</h1>
        <div className="flex-1" />
        <Button variant="ghost" size="icon" onClick={onRefresh}>
          <RefreshCw className="h-4 w-4" />
        </Button>
      </div>

      <div className="flex gap-2 flex-wrap">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search sessions..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8"
          />
        </div>
        <Select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value as "date" | "turns" | "size")}
          className="w-[130px]"
        >
          <option value="date">Sort by Date</option>
          <option value="turns">Sort by Turns</option>
          <option value="size">Sort by Size</option>
        </Select>
        <Select
          value={filterArchived}
          onChange={(e) => setFilterArchived(e.target.value as "all" | "active" | "archived")}
          className="w-[130px]"
        >
          <option value="all">All Sessions</option>
          <option value="active">Active Only</option>
          <option value="archived">Archived Only</option>
        </Select>
      </div>

      <div className="grid gap-2">
        {filtered.map((s) => (
          <Card
            key={`${s.work_dir_hash}/${s.session_id}`}
            className="cursor-pointer hover:bg-accent/50 transition-colors"
            onClick={() => onSelectSession(s)}
          >
            <CardContent className="p-3">
              <div className="flex items-start gap-3">
                <div className="flex-1 min-w-0">
                  <div className="font-medium truncate">
                    {s.title || `Session ${s.session_id.slice(0, 12)}...`}
                  </div>
                  <div className="text-xs text-muted-foreground mt-1 flex flex-wrap gap-x-3 gap-y-1">
                    <span>{formatTime(s.last_updated)}</span>
                    <span>Hash: {s.work_dir_hash.slice(0, 12)}...</span>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <Badge variant="secondary">{s.turns} turns</Badge>
                  <span className="text-xs text-muted-foreground">{formatBytes(s.total_size)}</span>
                  {s.archived && <Badge variant="outline">Archived</Badge>}
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
        {filtered.length === 0 && (
          <div className="text-center text-muted-foreground py-12">
            {search ? "No sessions match your search" : "No sessions found"}
          </div>
        )}
      </div>
    </div>
  );
}
