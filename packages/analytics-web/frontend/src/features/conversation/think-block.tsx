import { useState } from "react";
import { ChevronDown, ChevronRight, Brain } from "lucide-react";

export function ThinkBlock({ text }: { text: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="my-2 rounded border border-amber-200 dark:border-amber-800 bg-amber-50/50 dark:bg-amber-950/20">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 px-2 py-1 text-xs text-amber-700 dark:text-amber-400 cursor-pointer hover:bg-amber-100/50 dark:hover:bg-amber-900/30 w-full transition-colors"
      >
        {open ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
        <Brain className="h-3 w-3" />
        <span className="font-medium">Thinking</span>
        <span className="text-amber-500 dark:text-amber-600 ml-auto">{text.length} chars</span>
      </button>
      {open && (
        <pre className="px-2 pb-2 text-xs text-amber-800 dark:text-amber-300 whitespace-pre-wrap font-mono max-h-64 overflow-y-auto">
          {text}
        </pre>
      )}
    </div>
  );
}

export function ToolResultDisplay({ result }: { result: { tool_call_id: string; output: string; is_error: boolean; timestamp: number } }) {
  const [open, setOpen] = useState(false);
  const preview = result.output.slice(0, 120);
  return (
    <div className="my-1 rounded border border-blue-200 dark:border-blue-800 bg-blue-50/30 dark:bg-blue-950/20">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 px-2 py-1 text-xs text-blue-700 dark:text-blue-400 cursor-pointer hover:bg-blue-100/50 dark:hover:bg-blue-900/30 w-full transition-colors"
      >
        {open ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
        <span className="font-mono font-medium">Result: {result.tool_call_id.slice(0, 12)}</span>
        {result.is_error && (
          <span className="bg-destructive/10 text-destructive px-1 rounded text-[10px] font-semibold">ERROR</span>
        )}
        <span className="text-muted-foreground ml-auto text-[10px]">{result.output.length} chars</span>
      </button>
      {open && (
        <pre className={`px-2 pb-2 text-xs whitespace-pre-wrap font-mono max-h-64 overflow-y-auto ${result.is_error ? "text-destructive" : "text-foreground"}`}>
          {result.output}
        </pre>
      )}
    </div>
  );
}

export function ToolCallCard({ tc }: { tc: { id: string; name: string; arguments: Record<string, unknown>; arguments_raw: string } }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="my-1 rounded border border-violet-200 dark:border-violet-800 bg-violet-50/30 dark:bg-violet-950/20">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 px-2 py-1 text-xs text-violet-700 dark:text-violet-400 cursor-pointer hover:bg-violet-100/50 dark:hover:bg-violet-900/30 w-full transition-colors"
      >
        {open ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
        <span className="font-mono font-medium">Tool: {tc.name}</span>
        <span className="text-muted-foreground ml-auto text-[10px]">{tc.id.slice(0, 12)}</span>
      </button>
      {open && (
        <div className="px-2 pb-2">
          <pre className="text-xs text-muted-foreground whitespace-pre-wrap font-mono max-h-48 overflow-y-auto bg-black/[0.03] dark:bg-white/[0.03] p-1 rounded">
            {JSON.stringify(tc.arguments, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
