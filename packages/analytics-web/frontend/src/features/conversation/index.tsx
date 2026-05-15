import { useState, useEffect, useMemo } from "react";
import type { ConversationTurn, ContentPart } from "@/lib/api";
import { getConversation, formatTime } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Search, MessageSquare, RefreshCw, Bot, User } from "lucide-react";
import { ThinkBlock, ToolCallCard, ToolResultDisplay } from "./think-block";

interface Props {
  hash: string;
  id: string;
}

export function ConversationView({ hash, id }: Props) {
  const [turns, setTurns] = useState<ConversationTurn[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [expandedTurns, setExpandedTurns] = useState<Set<number>>(new Set());

  useEffect(() => {
    loadConversation();
  }, [hash, id]);

  async function loadConversation() {
    setLoading(true);
    try {
      const data = await getConversation(hash, id);
      setTurns(data);
      // Auto-expand all turns
      setExpandedTurns(new Set(data.map((_, i) => i)));
    } catch (e) {
      console.error("Failed to load conversation", e);
    } finally {
      setLoading(false);
    }
  }

  const filtered = useMemo(() => {
    if (!search.trim()) return turns;
    const q = search.toLowerCase();
    return turns.filter((t) => {
      if (t.user_input.toLowerCase().includes(q)) return true;
      for (const s of t.steps) {
        for (const p of s.content_parts) {
          if ((p.text && p.text.toLowerCase().includes(q)) ||
              (p.think && p.think.toLowerCase().includes(q))) return true;
        }
        for (const tc of s.tool_calls) {
          if (tc.name.toLowerCase().includes(q)) return true;
        }
      }
      return false;
    });
  }, [turns, search]);

  const toggleTurn = (idx: number) => {
    const next = new Set(expandedTurns);
    if (next.has(idx)) next.delete(idx);
    else next.add(idx);
    setExpandedTurns(next);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-muted-foreground animate-pulse">Loading conversation...</div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search conversation..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8"
          />
        </div>
        <Button variant="ghost" size="icon" onClick={loadConversation}>
          <RefreshCw className="h-4 w-4" />
        </Button>
      </div>

      <div className="space-y-4">
        {filtered.map((turn, ti) => (
          <Card key={ti} className="overflow-hidden">
            <button
              onClick={() => toggleTurn(ti)}
              className="w-full flex items-center gap-2 p-3 text-left hover:bg-accent/30 transition-colors cursor-pointer border-b border-border/50"
            >
              <div className="flex items-center gap-2 min-w-0 flex-1">
                <Badge variant="secondary" className="shrink-0">
                  <MessageSquare className="h-3 w-3 mr-1" />
                  Turn {turn.turn_index + 1}
                </Badge>
                <span className="text-xs text-muted-foreground shrink-0">
                  {formatTime(turn.timestamp)}
                </span>
                <span className="text-sm truncate text-muted-foreground">
                  {turn.user_input.slice(0, 100)}
                </span>
              </div>
              {turn.token_usage && (
                <Badge variant="outline" className="shrink-0 text-[10px]">
                  {turn.token_usage.input.toLocaleString()} in / {turn.token_usage.output.toLocaleString()} out
                </Badge>
              )}
            </button>

            {expandedTurns.has(ti) && (
              <div className="divide-y divide-border/30">
                {/* User Message */}
                <div className="p-3 bg-muted/20">
                  <div className="flex items-start gap-2">
                    <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10">
                      <User className="h-3 w-3 text-primary" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="text-xs font-medium text-muted-foreground mb-1">User</div>
                      <div className="text-sm whitespace-pre-wrap break-words">
                        {turn.user_input || "(no input)"}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Assistant Response Steps */}
                {turn.steps.length === 0 && (
                  <div className="p-3 bg-muted/10">
                    <div className="flex items-start gap-2">
                      <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-violet-500/10">
                        <Bot className="h-3 w-3 text-violet-500" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="text-xs font-medium text-muted-foreground mb-1">Assistant</div>
                        <div className="text-sm text-muted-foreground italic">
                          No response recorded
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {turn.steps.map((step, si) => (
                  <div key={si} className="p-3">
                    <div className="flex items-start gap-2">
                      <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-violet-500/10">
                        <Bot className="h-3 w-3 text-violet-500" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="text-xs font-medium text-muted-foreground mb-1">
                          Step {step.step_index + 1}
                          {step.tool_calls.length > 0 && (
                            <Badge variant="secondary" className="ml-2 text-[10px]">
                              {step.tool_calls.length} tool{step.tool_calls.length > 1 ? "s" : ""}
                            </Badge>
                          )}
                        </div>

                        {/* Content Parts */}
                        {step.content_parts.map((part, pi) => (
                          <ContentPartRenderer key={pi} part={part} />
                        ))}

                        {/* Tool Calls */}
                        {step.tool_calls.map((tc, tci) => (
                          <ToolCallCard key={tci} tc={tc} />
                        ))}

                        {/* Tool Results */}
                        {step.tool_results.map((tr, tri) => (
                          <ToolResultDisplay key={tri} result={tr} />
                        ))}

                        {step.content_parts.length === 0 &&
                         step.tool_calls.length === 0 &&
                         step.tool_results.length === 0 && (
                          <div className="text-xs text-muted-foreground italic">(empty step)</div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        ))}

        {filtered.length === 0 && (
          <div className="text-center text-muted-foreground py-12">
            {search ? "No turns match your search" : "No conversation data"}
          </div>
        )}
      </div>
    </div>
  );
}

function ContentPartRenderer({ part }: { part: ContentPart }) {
  if (part.type === "think" && part.think) {
    return <ThinkBlock text={part.think} />;
  }
  if (part.type === "text" && part.text) {
    return (
      <div className="text-sm whitespace-pre-wrap break-words my-1">
        {part.text}
      </div>
    );
  }
  return null;
}
