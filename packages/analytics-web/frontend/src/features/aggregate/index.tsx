import { useState, useEffect } from "react";
import type { AggregateStats } from "@/lib/api";
import { getAggregateStats, formatDuration } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip as RechartTooltip, Legend,
  ResponsiveContainer, AreaChart, Area,
} from "recharts";

const COLORS = ["#6366f1", "#8b5cf6", "#ec4899", "#f59e0b", "#10b981", "#06b6d4", "#f97316", "#84cc16", "#94a3b8", "#64748b"];

export function AggregateDashboard() {
  const [stats, setStats] = useState<AggregateStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getAggregateStats()
      .then(setStats)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-muted-foreground animate-pulse">Loading aggregate stats...</div>
      </div>
    );
  }

  if (!stats) {
    return <div className="text-center text-muted-foreground py-12">No data available</div>;
  }

  return (
    <div className="max-w-6xl mx-auto space-y-4">
      <h1 className="text-xl font-semibold">Aggregate Analytics</h1>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        <Card>
          <CardContent className="p-3 text-center">
            <div className="text-xs text-muted-foreground">Total Sessions</div>
            <div className="text-2xl font-bold">{stats.total_sessions}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-3 text-center">
            <div className="text-xs text-muted-foreground">Total Turns</div>
            <div className="text-2xl font-bold">{stats.total_turns.toLocaleString()}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-3 text-center">
            <div className="text-xs text-muted-foreground">Total Tokens</div>
            <div className="text-2xl font-bold">{(stats.total_tokens.input + stats.total_tokens.output).toLocaleString()}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-3 text-center">
            <div className="text-xs text-muted-foreground">Total Duration</div>
            <div className="text-2xl font-bold">{formatDuration(stats.total_duration_sec)}</div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader><CardTitle className="text-sm">Daily Usage (30 days)</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={stats.daily_usage}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="date" tick={{ fontSize: 9 }} angle={-45} textAnchor="end" height={60} />
                <YAxis tick={{ fontSize: 11 }} />
                <RechartTooltip />
                <Legend />
                <Bar dataKey="sessions" name="Sessions" fill="#6366f1" radius={[2, 2, 0, 0]} />
                <Bar dataKey="turns" name="Turns" fill="#8b5cf6" radius={[2, 2, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="text-sm">Token Usage by Project</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={stats.per_project.map((p) => ({ name: p.work_dir.slice(0, 12), value: p.sessions }))}
                  cx="50%" cy="50%" outerRadius={80}
                  dataKey="value"
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                >
                  {stats.per_project.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <RechartTooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="text-sm">Top Tools</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={stats.tool_usage.slice(0, 10)} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis dataKey="name" type="category" width={80} tick={{ fontSize: 10 }} />
                <RechartTooltip />
                <Legend />
                <Bar dataKey="count" name="Calls" fill="#6366f1" radius={[0, 2, 2, 0]} />
                <Bar dataKey="error_count" name="Errors" fill="#ef4444" radius={[0, 2, 2, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="text-sm">Per Project</CardTitle></CardHeader>
          <CardContent>
            <div className="space-y-1">
              {stats.per_project.map((p) => (
                <div key={p.work_dir} className="flex items-center justify-between text-sm py-1 border-b border-border/50 last:border-0">
                  <span className="font-mono text-xs truncate max-w-[200px]">{p.work_dir.slice(0, 24)}</span>
                  <div className="flex gap-3 shrink-0">
                    <Badge variant="secondary">{p.sessions} sessions</Badge>
                    <span className="text-muted-foreground text-xs">{p.turns} turns</span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
