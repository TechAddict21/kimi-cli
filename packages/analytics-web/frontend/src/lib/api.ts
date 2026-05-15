const BASE = "/api/analytics";

async function fetchJSON<T>(path: string, timeoutMs = 30_000): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${BASE}${path}`, { signal: controller.signal });
    if (!res.ok) {
      throw new Error(`API error: ${res.status} ${res.statusText}`);
    }
    return (await res.json()) as T;
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") {
      throw new Error("Request timed out");
    }
    throw e;
  } finally {
    clearTimeout(timeout);
  }
}

export interface SessionInfo {
  session_id: string;
  work_dir_hash: string;
  work_dir: string | null;
  title: string;
  last_updated: number;
  turns: number;
  wire_size: number;
  context_size: number;
  state_size: number;
  total_size: number;
  subagent_count: number;
  custom_title: string | null;
  archived: boolean;
}

export interface SessionSummary {
  turns: number;
  steps: number;
  tool_calls: number;
  errors: number;
  compactions: number;
  duration_sec: number;
  input_tokens: number;
  output_tokens: number;
}

export interface TurnTimeline {
  turn_index: number;
  timestamp: number;
  user_input: string;
  duration_ms: number;
  steps: StepEvent[];
}

export interface StepEvent {
  step_index: number;
  timestamp: number;
  type: "llm" | "tool";
  duration_ms: number;
  tool_calls: ToolCallEvent[];
  error: string | null;
}

export interface ToolCallEvent {
  tool_name: string;
  timestamp: number;
  duration_ms: number;
  error: string | null;
}

export interface TokenUsagePoint {
  turn_index: number;
  timestamp: number;
  input_tokens: number;
  output_tokens: number;
  cumulative_input: number;
  cumulative_output: number;
}

export interface ToolStat {
  name: string;
  count: number;
  error_count: number;
  avg_duration_ms: number;
}

export interface ToolStatsResponse {
  tools: ToolStat[];
  total_calls: number;
  total_errors: number;
}

export interface StepLatencyItem {
  turn_index: number;
  step_index: number;
  llm_duration_ms: number;
  tool_duration_ms: number;
  tool_name: string | null;
}

export interface ContentPart {
  type: string;
  text?: string;
  think?: string;
  thinking?: string;
  encrypted?: string;
  image_url?: { url: string; id?: string };
  audio_url?: { url: string; id?: string };
  video_url?: { url: string; id?: string };
  [key: string]: unknown;
}

export interface ToolCallItem {
  id: string;
  type: string;
  function: { name: string; arguments: string };
  extras?: Record<string, unknown>;
}

export interface CostBreakdown {
  input_tokens: number;
  output_tokens: number;
  input_cost: number;
  output_cost: number;
  total_cost: number;
  per_turn: CostTurnItem[];
}

export interface CostTurnItem {
  turn_index: number;
  input_tokens: number;
  output_tokens: number;
  input_cost: number;
  output_cost: number;
  total_cost: number;
}

export interface AggregateStats {
  total_sessions: number;
  total_turns: number;
  total_tokens: { input: number; output: number };
  total_duration_sec: number;
  tool_usage: { name: string; count: number; error_count: number }[];
  daily_usage: { date: string; sessions: number; turns: number }[];
  per_project: { work_dir: string; sessions: number; turns: number }[];
}

// Sessions
export function listSessions(): Promise<SessionInfo[]> {
  return fetchJSON<SessionInfo[]>("/sessions", 120_000);
}

export function getSessionSummary(hash: string, id: string): Promise<SessionSummary> {
  return fetchJSON<SessionSummary>(`/sessions/${hash}/${id}/summary`);
}

// Timeline
export function getTimeline(hash: string, id: string): Promise<TurnTimeline[]> {
  return fetchJSON<TurnTimeline[]>(`/sessions/${hash}/${id}/timeline`, 60_000);
}

// Token usage
export function getTokenUsage(hash: string, id: string): Promise<TokenUsagePoint[]> {
  return fetchJSON<TokenUsagePoint[]>(`/sessions/${hash}/${id}/token-usage`, 60_000);
}

// Tool stats
export function getToolStats(hash: string, id: string): Promise<ToolStatsResponse> {
  return fetchJSON<ToolStatsResponse>(`/sessions/${hash}/${id}/tool-stats`, 60_000);
}

// Latency
export function getLatency(hash: string, id: string): Promise<StepLatencyItem[]> {
  return fetchJSON<StepLatencyItem[]>(`/sessions/${hash}/${id}/latency`, 60_000);
}

// Cost
export function getCost(
  hash: string,
  id: string,
  inputRate?: number,
  outputRate?: number,
): Promise<CostBreakdown> {
  let path = `/sessions/${hash}/${id}/cost`;
  const params: string[] = [];
  if (inputRate !== undefined) params.push(`input_rate=${inputRate}`);
  if (outputRate !== undefined) params.push(`output_rate=${outputRate}`);
  if (params.length) path += `?${params.join("&")}`;
  return fetchJSON<CostBreakdown>(path, 60_000);
}

// Aggregate
export function getAggregateStats(): Promise<AggregateStats> {
  return fetchJSON<AggregateStats>("/stats", 120_000);
}

export function getDailyUsage(days = 30): Promise<{ date: string; sessions: number; turns: number }[]> {
  return fetchJSON(`/daily-usage?days=${days}`, 120_000);
}

// Messages & Conversation
export function getMessages(hash: string, id: string): Promise<MessagesResponse> {
  return fetchJSON<MessagesResponse>(`/sessions/${hash}/${id}/messages`, 60_000);
}

export function getConversation(hash: string, id: string): Promise<ConversationTurn[]> {
  return fetchJSON<ConversationTurn[]>(`/sessions/${hash}/${id}/conversation`, 60_000);
}

export function getRawEvents(
  hash: string,
  id: string,
  type?: string,
  search?: string,
  offset = 0,
  limit = 500,
): Promise<RawEventsResponse> {
  let path = `/sessions/${hash}/${id}/raw-events?offset=${offset}&limit=${limit}`;
  if (type) path += `&type=${encodeURIComponent(type)}`;
  if (search) path += `&search=${encodeURIComponent(search)}`;
  return fetchJSON<RawEventsResponse>(path, 60_000);
}

export function getEventTypes(hash: string, id: string): Promise<string[]> {
  return fetchJSON<string[]>(`/sessions/${hash}/${id}/event-types`);
}

export function getPerProject(topN = 10): Promise<{ work_dir: string; sessions: number; turns: number }[]> {
  return fetchJSON(`/per-project?top_n=${topN}`, 120_000);
}

export interface ToolCallItem_Message {
  id: string;
  type: string;
  function: { name: string; arguments: string };
  extras?: Record<string, unknown>;
}

export interface MessageRecord {
  index: number;
  role: string;
  content?: ContentPart[] | string;
  tool_calls?: ToolCallItem_Message[];
  tool_call_id?: string;
  name?: string;
  partial?: boolean;
  token_count?: number;
  id?: number;
}

export interface MessagesResponse {
  total: number;
  system_prompt: string;
  messages: MessageRecord[];
}

export interface ConversationTurn {
  turn_index: number;
  timestamp: number;
  user_input: string;
  duration_ms?: number;
  token_usage?: { input: number; output: number };
  steps: ConversationStep[];
}

export interface ConversationStep {
  step_index: number;
  timestamp: number;
  content_parts: ContentPart[];
  tool_calls: ToolCallInStep[];
  tool_results: ToolResultInStep[];
}

export interface ToolCallInStep {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
  arguments_raw: string;
  timestamp: number;
}

export interface ToolResultInStep {
  tool_call_id: string;
  output: string;
  is_error: boolean;
  timestamp: number;
}

export interface RawEvent {
  index: number;
  timestamp: number;
  type: string;
  payload: Record<string, unknown>;
}

export interface RawEventsResponse {
  total: number;
  filtered_total: number;
  events: RawEvent[];
}

export function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds.toFixed(0)}s`;
  if (seconds < 3600) return `${(seconds / 60).toFixed(1)}m`;
  return `${(seconds / 3600).toFixed(2)}h`;
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatTime(ts: number): string {
  return new Date(ts * 1000).toLocaleString();
}

export function formatDate(ts: number): string {
  return new Date(ts * 1000).toLocaleDateString();
}
