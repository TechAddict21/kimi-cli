import type { ReactNode } from "react";
import type { SessionInfo } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { BarChart3, List, ArrowLeft, RefreshCw } from "lucide-react";

interface LayoutProps {
  view: string;
  onNavigate: (view: "sessions" | "dashboard" | "aggregate") => void;
  selectedSession: SessionInfo | null;
  onBack: () => void;
  onRefresh: () => void;
  children: ReactNode;
}

export function Layout({
  view,
  onNavigate,
  selectedSession,
  onBack,
  onRefresh,
  children,
}: LayoutProps) {
  return (
    <div className="flex h-screen flex-col">
      <header className="flex h-12 items-center gap-2 border-b px-4 shrink-0">
        {view === "dashboard" && (
          <Button variant="ghost" size="icon" onClick={onBack}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
        )}
        <div className="flex items-center gap-2 font-semibold">
          <BarChart3 className="h-5 w-5 text-primary" />
          <span>Kimi Analytics</span>
        </div>
        <nav className="ml-4 flex gap-1">
          <Button
            variant={view === "sessions" ? "secondary" : "ghost"}
            size="sm"
            onClick={() => onNavigate("sessions")}
          >
            <List className="h-4 w-4 mr-1" />
            Sessions
          </Button>
          <Button
            variant={view === "aggregate" ? "secondary" : "ghost"}
            size="sm"
            onClick={() => onNavigate("aggregate")}
          >
            <BarChart3 className="h-4 w-4 mr-1" />
            Aggregate
          </Button>
        </nav>
        <div className="flex-1" />
        <Button variant="ghost" size="icon" onClick={onRefresh}>
          <RefreshCw className="h-4 w-4" />
        </Button>
        {selectedSession && view === "dashboard" && (
          <span className="text-sm text-muted-foreground truncate max-w-[300px]">
            {selectedSession.title || selectedSession.session_id}
          </span>
        )}
      </header>
      <main className="flex-1 overflow-auto p-4">
        {children}
      </main>
    </div>
  );
}
