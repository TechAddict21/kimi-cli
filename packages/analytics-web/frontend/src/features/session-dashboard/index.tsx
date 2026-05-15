import { useState, useEffect } from "react";
import type { SessionInfo, SessionSummary, TokenUsagePoint, ToolStat, StepLatencyItem, CostBreakdown, TurnTimeline } from "@/lib/api";
import {
  getSessionSummary,
  getTimeline,
  getTokenUsage,
  getToolStats,
  getLatency,
  getCost,
  formatDuration,
} from "@/lib/api";
import { ConversationView } from "@/features/conversation";
import { WireViewer } from "@/features/wire-viewer";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip as RechartTooltip, Legend,
  ResponsiveContainer, AreaChart, Area,
} from "recharts";
import { ArrowLeft, RefreshCw } from "lucide-react";

const COLORS = ["#6366f1", "#8b5cf6", "#ec4899", "#f59e0b", "#10b981", "#06b6d4", "#f97316", "#84cc16"];

interface Props {
  session: SessionInfo;
  onBack: () => void;
}

export function SessionDashboard({ session, onBack }: Props) {
  const [tab, setTab] = useState("overview");
  const [summary, setSummary] = useState<SessionSummary | null>(null);
  const [timeline, setTimeline] = useState<TurnTimeline[]>([]);
  const [tokenData, setTokenData] = useState<TokenUsagePoint[]>([]);
  const [toolData, setToolData] = useState<ToolStat[]>([]);
  const [latencyData, setLatencyData] = useState<StepLatencyItem[]>([]);
  const [costData, setCostData] = useState<CostBreakdown | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, [session.session_id]);

  async function loadData() {
    setLoading(true);
    try {
      const hash = session.work_dir_hash;
      const id = session.session_id;
      const [s, t, tk, tl, l, c] = await Promise.all([
        getSessionSummary(hash, id),
        getTimeline(hash, id),
        getTokenUsage(hash, id),
        getToolStats(hash, id),
        getLatency(hash, id),
        getCost(hash, id),
      ]);
      setSummary(s);
      setTimeline(t);
      setTokenData(tk);
      setToolData(tl.tools || []);
      setLatencyData(l);
      setCostData(c);
    } catch (e) {
      console.error("Failed to load session data", e);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-muted-foreground animate-pulse">Loading analytics...</div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-4">
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon" onClick={onBack}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-lg font-semibold truncate max-w-[600px]">
            {session.title || session.session_id.slice(0, 16)}
          </h1>
          <p className="text-xs text-muted-foreground">
            {session.session_id} &middot; {session.work_dir_hash}
          </p>
        </div>
        <div className="flex-1" />
        <Button variant="ghost" size="icon" onClick={loadData}>
          <RefreshCw className="h-4 w-4" />
        </Button>
      </div>

      {summary && <SummaryCards summary={summary} />}

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="timeline">Timeline</TabsTrigger>
          <TabsTrigger value="tokens">Tokens</TabsTrigger>
          <TabsTrigger value="tools">Tools</TabsTrigger>
          <TabsTrigger value="latency">Latency</TabsTrigger>
          <TabsTrigger value="cost">Cost</TabsTrigger>
          <TabsTrigger value="conversation">Conversation</TabsTrigger>
          <TabsTrigger value="wire">Wire Events</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <div className="grid gap-4 md:grid-cols-2">
            {tokenData.length > 0 && (
              <Card>
                <CardHeader><CardTitle className="text-sm">Token Usage</CardTitle></CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={200}>
                    <AreaChart data={tokenData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                      <XAxis dataKey="turn_index" tick={{ fontSize: 11 }} />
                      <YAxis tick={{ fontSize: 11 }} />
                      <RechartTooltip />
                      <Area type="monotone" dataKey="cumulative_input" name="Input" stackId="1" fill="#6366f1" stroke="#6366f1" />
                      <Area type="monotone" dataKey="cumulative_output" name="Output" stackId="2" fill="#8b5cf6" stroke="#8b5cf6" />
                    </AreaChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            )}
            {toolData.length > 0 && (
              <Card>
                <CardHeader><CardTitle className="text-sm">Tool Usage</CardTitle></CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={200}>
                    <BarChart data={toolData.slice(0, 8)}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                      <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                      <YAxis tick={{ fontSize: 11 }} />
                      <RechartTooltip />
                      <Bar dataKey="count" name="Calls" fill="#6366f1" radius={[2, 2, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            )}
            {latencyData.length > 0 && (
              <Card>
                <CardHeader><CardTitle className="text-sm">Latency Breakdown</CardTitle></CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={200}>
                    <BarChart data={latencyData.slice(0, 15)} layout="vertical">
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                      <XAxis type="number" tick={{ fontSize: 11 }} />
                      <YAxis dataKey="step_index" type="category" tick={{ fontSize: 10 }} />
                      <RechartTooltip />
                      <Legend />
                      <Bar dataKey="llm_duration_ms" name="LLM (ms)" stackId="1" fill="#6366f1" radius={[0, 0, 0, 0]} />
                      <Bar dataKey="tool_duration_ms" name="Tool (ms)" stackId="1" fill="#f59e0b" radius={[0, 2, 2, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            )}
            {costData && (
              <Card>
                <CardHeader><CardTitle className="text-sm">Cost</CardTitle></CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={200}>
                    <PieChart>
                      <Pie
                        data={[
                          { name: "Input", value: costData.input_cost },
                          { name: "Output", value: costData.output_cost },
                        ]}
                        cx="50%"
                        cy="50%"
                        outerRadius={70}
                        dataKey="value"
                        label={({ name, value }) => `${name}: $${value.toFixed(4)}`}
                      >
                        {[0, 1].map((i) => (
                          <Cell key={i} fill={COLORS[i]} />
                        ))}
                      </Pie>
                      <RechartTooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>

        <TabsContent value="conversation">
          <ConversationView hash={session.work_dir_hash} id={session.session_id} />
        </TabsContent>

        <TabsContent value="wire">
          <WireViewer hash={session.work_dir_hash} id={session.session_id} />
        </TabsContent>

        <TabsContent value="timeline">
          <TimelineView data={timeline} />
        </TabsContent>

        <TabsContent value="tokens">
          <Card>
            <CardHeader><CardTitle>Token Usage Per Turn</CardTitle></CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={350}>
                <BarChart data={tokenData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey="turn_index" label={{ value: "Turn", position: "insideBottom", offset: -5 }} />
                  <YAxis />
                  <RechartTooltip />
                  <Legend />
                  <Bar dataKey="input_tokens" name="Input" fill="#6366f1" radius={[2, 2, 0, 0]} />
                  <Bar dataKey="output_tokens" name="Output" fill="#8b5cf6" radius={[2, 2, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="tools">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader><CardTitle>Tool Call Distribution</CardTitle></CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={toolData.map((t) => ({ name: t.name, value: t.count }))}
                      cx="50%" cy="50%" outerRadius={100}
                      dataKey="value"
                      label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    >
                      {toolData.map((_, i) => (
                        <Cell key={i} fill={COLORS[i % COLORS.length]} />
                      ))}
                    </Pie>
                    <RechartTooltip />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle>Tool Details</CardTitle></CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {toolData.map((t) => (
                    <div key={t.name} className="flex items-center justify-between text-sm">
                      <span className="font-mono text-xs">{t.name}</span>
                      <div className="flex gap-3">
                        <span>{t.count} calls</span>
                        {t.error_count > 0 && (
                          <span className="text-destructive">{t.error_count} errors</span>
                        )}
                        <span className="text-muted-foreground">{t.avg_duration_ms.toFixed(0)}ms avg</span>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="latency">
          <Card>
            <CardHeader><CardTitle>Step Latency: LLM vs Tool</CardTitle></CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={400}>
                <BarChart data={latencyData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis type="number" label={{ value: "Duration (ms)", position: "bottom" }} />
                  <YAxis dataKey="step_index" type="category" width={60} />
                  <RechartTooltip />
                  <Legend />
                  <Bar dataKey="llm_duration_ms" name="LLM" stackId="1" fill="#6366f1" />
                  <Bar dataKey="tool_duration_ms" name="Tool" stackId="1" fill="#f59e0b" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="cost">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader><CardTitle>Cost Per Turn</CardTitle></CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={costData?.per_turn || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                    <XAxis dataKey="turn_index" />
                    <YAxis tickFormatter={(v) => `$${v.toFixed(4)}`} />
                    <RechartTooltip formatter={(v: number) => `$${v.toFixed(6)}`} />
                    <Legend />
                    <Bar dataKey="input_cost" name="Input Cost" fill="#6366f1" stackId="1" />
                    <Bar dataKey="output_cost" name="Output Cost" fill="#8b5cf6" stackId="1" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle>Summary</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Total Input Tokens</span>
                  <span className="font-mono">{costData?.input_tokens.toLocaleString()}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Total Output Tokens</span>
                  <span className="font-mono">{costData?.output_tokens.toLocaleString()}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Input Cost</span>
                  <span className="font-mono">${costData?.input_cost.toFixed(4)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Output Cost</span>
                  <span className="font-mono">${costData?.output_cost.toFixed(4)}</span>
                </div>
                <div className="border-t pt-2 flex justify-between font-semibold">
                  <span>Total Cost</span>
                  <span className="font-mono">${costData?.total_cost.toFixed(4)}</span>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function SummaryCards({ summary }: { summary: SessionSummary }) {
  const cards = [
    { label: "Turns", value: summary.turns.toString() },
    { label: "Steps", value: summary.steps.toString() },
    { label: "Tool Calls", value: summary.tool_calls.toString() },
    { label: "Errors", value: summary.errors.toString(), color: summary.errors > 0 ? "text-destructive" : undefined },
    { label: "Compactions", value: summary.compactions.toString() },
    { label: "Duration", value: formatDuration(summary.duration_sec) },
    { label: "Input Tokens", value: summary.input_tokens.toLocaleString() },
    { label: "Output Tokens", value: summary.output_tokens.toLocaleString() },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
      {cards.map((c) => (
        <Card key={c.label}>
          <CardContent className="p-3 text-center">
            <div className="text-xs text-muted-foreground">{c.label}</div>
            <div className={`text-lg font-semibold ${c.color || ""}`}>{c.value}</div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function TimelineView({ data }: { data: TurnTimeline[] }) {
  return (
    <div className="space-y-2">
      {data.map((turn) => (
        <Card key={turn.turn_index}>
          <CardHeader className="p-3 pb-1">
            <div className="flex items-center gap-2">
              <Badge variant="secondary">Turn {turn.turn_index + 1}</Badge>
              <span className="text-xs text-muted-foreground">
                {formatDuration(turn.duration_ms / 1000)}
              </span>
              <span className="text-xs text-muted-foreground truncate">{turn.user_input.slice(0, 80)}</span>
            </div>
          </CardHeader>
          <CardContent className="p-3 pt-1">
            <div className="flex gap-1 flex-wrap">
              {turn.steps.map((step) => (
                <div
                  key={step.step_index}
                  className={`text-xs px-2 py-0.5 rounded ${
                    step.error ? "bg-destructive/10 text-destructive" : "bg-muted text-muted-foreground"
                  }`}
                >
                  {step.tool_calls?.[0]?.tool_name || "LLM"}
                  {step.error && " !"}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
