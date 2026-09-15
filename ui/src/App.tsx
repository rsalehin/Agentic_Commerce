import { useEffect, useMemo, useState } from "react";

import { fetchCard, fetchSession, subscribeEvents } from "./api";
import { ChatPanel } from "./components/ChatPanel";
import { OpsConsole } from "./components/OpsConsole";
import type { AgentCard, AuditEvent, SessionSnapshot } from "./types";

function querySession(): string | null {
  return new URLSearchParams(window.location.search).get("session");
}

export default function App() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [card, setCard] = useState<AgentCard | null>(null);
  const [snapshot, setSnapshot] = useState<SessionSnapshot | null>(null);
  const [pinned] = useState<string | null>(querySession());

  useEffect(() => {
    fetchCard().then(setCard);
    const unsub = subscribeEvents((e) => setEvents((prev) => [...prev, e]));
    return unsub;
  }, []);

  // Active session: the pinned one (?session=) or the most recently seen.
  const activeSession = useMemo(() => {
    if (pinned) return pinned;
    for (let i = events.length - 1; i >= 0; i -= 1) return events[i].session_id;
    return null;
  }, [events, pinned]);

  // Refresh the snapshot whenever new events arrive for the active session.
  useEffect(() => {
    if (!activeSession) return;
    fetchSession(activeSession).then(setSnapshot);
  }, [activeSession, events.length]);

  const sessionEvents = useMemo(
    () => events.filter((e) => e.session_id === activeSession),
    [events, activeSession],
  );
  const lastEvent = sessionEvents.length ? sessionEvents[sessionEvents.length - 1] : null;
  const state = snapshot?.state ?? lastEvent?.to_state ?? null;

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          TRUST<span>EQ</span> · Agentische Depoteröffnung
        </div>
        <div className="sub">
          {activeSession ? `Session ${activeSession}` : "keine aktive Sitzung"}
        </div>
      </header>
      <div className="split">
        <ChatPanel events={sessionEvents} />
        <OpsConsole card={card} events={sessionEvents} snapshot={snapshot} state={state} />
      </div>
    </div>
  );
}
