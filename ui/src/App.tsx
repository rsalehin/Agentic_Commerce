import { useEffect, useMemo, useState } from "react";

import {
  decideEscalation,
  fetchCard,
  fetchEscalations,
  fetchRules,
  fetchSession,
  subscribeEvents,
} from "./api";
import { ChatPanel } from "./components/ChatPanel";
import { OpsConsole } from "./components/OpsConsole";
import type { AgentCard, AuditEvent, Escalation, RuleInfo, SessionSnapshot } from "./types";

type Decision = "approve" | "request_appointment" | "reject";

function querySession(): string | null {
  return new URLSearchParams(window.location.search).get("session");
}

export default function App() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [card, setCard] = useState<AgentCard | null>(null);
  const [snapshot, setSnapshot] = useState<SessionSnapshot | null>(null);
  const [escalations, setEscalations] = useState<Escalation[]>([]);
  const [rules, setRules] = useState<RuleInfo[]>([]);
  const [pinned] = useState<string | null>(querySession());

  useEffect(() => {
    fetchCard().then(setCard);
    fetchRules().then(setRules);
    const unsub = subscribeEvents((e) => setEvents((prev) => [...prev, e]));
    return unsub;
  }, []);

  async function onDecide(id: string, decision: Decision) {
    await decideEscalation(id, decision, "adviser");
    setEscalations(await fetchEscalations());
    if (activeSession) setSnapshot(await fetchSession(activeSession));
  }

  // Active session: the pinned one (?session=) or the most recently seen.
  const activeSession = useMemo(() => {
    if (pinned) return pinned;
    for (let i = events.length - 1; i >= 0; i -= 1) return events[i].session_id;
    return null;
  }, [events, pinned]);

  // Refresh the snapshot + escalations whenever new events arrive.
  useEffect(() => {
    fetchEscalations().then(setEscalations);
    if (activeSession) fetchSession(activeSession).then(setSnapshot);
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
        <OpsConsole
          card={card}
          events={sessionEvents}
          snapshot={snapshot}
          state={state}
          escalations={escalations}
          rules={rules}
          onDecide={onDecide}
        />
      </div>
    </div>
  );
}
