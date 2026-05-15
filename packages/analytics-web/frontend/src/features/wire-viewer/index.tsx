import { useState, useEffect } from "react";
import type { RawEvent } from "@/lib/api";
import { getRawEvents, getEventTypes, formatTime } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { RefreshCw, Search, ChevronDown, ChevronRight } from "lucide-react";

interface Props {
  hash: string;
  id: string;
}

const TYPE_COLORS: Record<string, string> = {
  TurnBegin: "bg-blue-500/10 text-blue-600 dark:text-blue-400",
  TurnEnd: "bg-blue-500/10 text-blue-600 dark:text-blue-400",
  StepBegin: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
  StepInterrupted: "bg-destructive/10 text-destructive",
  StepRetry: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
  ContentPart: "bg-violet-500/10 text-violet-600 dark:text-violet-400",
  ToolCall: "bg-orange-500/10 text-orange-600 dark:text-orange-400",
  ToolCallPart: "bg-orange-500/10 text-orange-600 dark:text-orange-400",
  ToolResult: "bg-cyan-500/10 text-cyan-600 dark:text-cyan-400",
  StatusUpdate: "bg-gray-500/10 text-gray-600 dark:text-gray-400",
  CompactionBegin: "bg-rose-500/10 text-rose-600 dark:text-rose-400",
  CompactionEnd: "bg-rose-500/10 text-rose-600 dark:text-rose-400",
};

function renderEventSummary(ev: RawEvent): string {
  const p = ev.payload as Record<string, unknown>;
  if (ev.type === "TurnBegin" && typeof p.user_input === "string") return p.user_input.slice(0, 80);
  if (ev.type === "ToolCall") {
    const fn = p.function as Record<string, unknown> | undefined;
    return `→ ${fn?.name || "unknown"}`;
  }
  if (ev.type === "ToolResult") return `← ${String(p.tool_call_id || "").slice(0, 16)}`;
  if (ev.type === "ContentPart") return `[${String(p.type || "")}]`;
  if (ev.type === "StatusUpdate") {
    const usage = p.context_usage as number | undefined;
    return `ctx: ${usage ? (usage * 100).toFixed(1) + "%" : "-"}`;
  }
  return "";
}

export function WireViewer({ hash, id }: Props) {
  const [events, setEvents] = useState<RawEvent[]>([]);
  const [total, setTotal] = useState(0);
  const [eventTypes, setEventTypes] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [typeFilter, setTypeFilter] = useState("");
  const [search, setSearch] = useState("");
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());

  useEffect(() => {
    loadEvents();
    getEventTypes(hash, id).then(setEventTypes).catch(() => {});
  }, [hash, id]);

  async function loadEvents() {
    setLoading(true);
    try {
      const data = await getRawEvents(hash, id, typeFilter || undefined, search || undefined);
      setEvents(data.events);
      setTotal(data.filtered_total);
    } catch (e) {
      console.error("Failed to load raw events", e);
    } finally {
      setLoading(false);
    }
  }

  function handleFilter() {
    setExpandedRows(new Set());
    loadEvents();
  }

  function toggleRow(idx: number) {
    const next = new Set(expandedRows);
    if (next.has(idx)) next.delete(idx);
    else next.add(idx);
    setExpandedRows(next);
  }

  return (
    <div className="space-y-3">
      <div className="flex gap-2 flex-wrap">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search payload..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8"
          />
        </div>
        <Select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="w-[160px]"
        >
          <option value="">All Types</option>
          {eventTypes.filter(Boolean).map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </Select>
        <Button variant="secondary" size="sm" onClick={handleFilter}>Filter</Button>
        <Button variant="ghost" size="icon" onClick={loadEvents}>
          <RefreshCw className="h-4 w-4" />
        </Button>
      </div>

      <div className="text-xs text-muted-foreground">
        {total} events {typeFilter && <span>filtered by type "{typeFilter}"</span>}
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="text-muted-foreground animate-pulse">Loading events...</div>
        </div>
      ) : (
        <div className="space-y-0.5">
          {events.map((ev) => (
            <Card key={ev.index} className="overflow-hidden">
              <button
                onClick={() => toggleRow(ev.index)}
                className="w-full flex items-center gap-2 px-3 py-1.5 text-left hover:bg-accent/30 transition-colors cursor-pointer"
              >
                <span className="text-muted-foreground text-[10px] font-mono w-8 shrink-0">
                  {ev.index}
                </span>
                <Badge className={`text-[10px] font-mono ${TYPE_COLORS[ev.type] || "bg-muted text-muted-foreground"}`}>
                  {expandedRows.has(ev.index) ? <ChevronDown className="h-3 w-3 mr-0.5" /> : <ChevronRight className="h-3 w-3 mr-0.5" />}
                  {ev.type}
                </Badge>
                <span className="text-[10px] text-muted-foreground font-mono shrink-0">
                  {formatTime(ev.timestamp)}
                </span>
                <span className="text-[10px] text-muted-foreground truncate ml-auto">
                  {renderEventSummary(ev)}
                </span>
              </button>
              {expandedRows.has(ev.index) && (
                <CardContent className="px-3 pb-2 pt-1">
                  <pre className="text-[11px] font-mono whitespace-pre-wrap overflow-x-auto max-h-96 overflow-y-auto bg-black/[0.03] dark:bg-white/[0.03] p-2 rounded">
                    {JSON.stringify(ev.payload, null, 2)}
                  </pre>
                </CardContent>
              )}
            </Card>
          ))}
          {events.length === 0 && (
            <div className="text-center text-muted-foreground py-12">No events match your filters</div>
          )}
        </div>
      )}
    </div>
  );
}
