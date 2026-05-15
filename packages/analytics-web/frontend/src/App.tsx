import { useState, useEffect, useCallback } from "react";
import type { SessionInfo } from "@/lib/api";
import { listSessions } from "@/lib/api";
import { Layout } from "@/components/layout";
import { SessionList } from "@/features/session-list";
import { SessionDashboard } from "@/features/session-dashboard";
import { AggregateDashboard } from "@/features/aggregate";

export function App() {
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedSession, setSelectedSession] = useState<SessionInfo | null>(null);
  const [view, setView] = useState<"sessions" | "dashboard" | "aggregate">("sessions");

  const fetchSessions = useCallback(async () => {
    try {
      setLoading(true);
      const data = await listSessions();
      setSessions(data);
    } catch (e) {
      console.error("Failed to load sessions", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  const handleSelectSession = (session: SessionInfo) => {
    setSelectedSession(session);
    setView("dashboard");
  };

  const handleBack = () => {
    setView("sessions");
    setSelectedSession(null);
  };

  const handleRefresh = () => {
    fetchSessions();
  };

  return (
    <Layout
      view={view}
      onNavigate={setView}
      selectedSession={selectedSession}
      onBack={handleBack}
      onRefresh={handleRefresh}
    >
      {view === "sessions" && (
        <SessionList
          sessions={sessions}
          loading={loading}
          onSelectSession={handleSelectSession}
          onRefresh={handleRefresh}
        />
      )}
      {view === "dashboard" && selectedSession && (
        <SessionDashboard
          session={selectedSession}
          onBack={handleBack}
        />
      )}
      {view === "aggregate" && (
        <AggregateDashboard />
      )}
    </Layout>
  );
}
