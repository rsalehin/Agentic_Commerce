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
import { BUNDLES } from "./replay";
import type { AgentCard, AuditEvent, Escalation, RuleInfo, SessionSnapshot } from "./types";

type Decision = "approve" | "request_appointment" | "reject";
type Mode = { kind: "live" } | { kind: "replay"; persona: string };

function querySession(): string | null {
  return new URLSearchParams(window.location.search).get("session");
}

export default function App() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [card, setCard] = useState<AgentCard | null>(null);
  const [snapshot, setSnapshot] = useState<SessionSnapshot | null>(null);
  const [escalations, setEscalations] = useState<Escalation[]>([]);
  const [rules, setRules] = useState<RuleInfo[]>([]);
  const [mode, setMode] = useState<Mode>({ kind: "live" });
  const [pinned] = useState<string | null>(querySession());

  const replaying = mode.kind === "replay";

  // Source: live SSE + fetches, or a bundled recording (network disabled).
  useEffect(() => {
    if (mode.kind === "replay") {
      const b = BUNDLES[mode.persona];
      setCard(b.card);
      setEvents(b.events);
      setSnapshot(b.snapshot);
      setEscalations(b.escalations);
      setRules(b.rules);
      return;
    }
    setEvents([]);
    setSnapshot(null);
    setEscalations([]);
    fetchCard().then(setCard);
    fetchRules().then(setRules);
    const unsub = subscribeEvents((e) => setEvents((prev) => [...prev, e]));
    return unsub;
  }, [mode]);

  const activeSession = useMemo(() => {
    if (pinned && !replaying) return pinned;
    for (let i = events.length - 1; i >= 0; i -= 1) return events[i].session_id;
    return null;
  }, [events, pinned, replaying]);

  // Live only: refresh snapshot + escalations as events arrive.
  useEffect(() => {
    if (replaying || !activeSession) return;
    fetchEscalations().then(setEscalations);
    fetchSession(activeSession).then(setSnapshot);
  }, [activeSession, events.length, replaying]);

  async function onDecide(id: string, decision: Decision) {
    if (replaying) return; // decisions are pre-recorded in a bundle
    await decideEscalation(id, decision, "adviser");
    setEscalations(await fetchEscalations());
    if (activeSession) setSnapshot(await fetchSession(activeSession));
  }

  const sessionEvents = useMemo(
    () => events.filter((e) => e.session_id === activeSession),
    [events, activeSession],
  );
  const lastEvent = sessionEvents.length ? sessionEvents[sessionEvents.length - 1] : null;
  const state = snapshot?.state ?? lastEvent?.to_state ?? null;

  const modeButton = (label: string, target: Mode, active: boolean) => (
    <button
      className={`btn ${active ? "primary" : "ghost"}`}
      style={{ padding: "4px 10px", fontSize: 12, cursor: "pointer" }}
      onClick={() => setMode(target)}
    >
      {label}
    </button>
  );

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          TRUST<span>EQ</span> · Agentische Depoteröffnung
        </div>
        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
          {modeButton("Live", { kind: "live" }, mode.kind === "live")}
          {modeButton("Replay: Lena", { kind: "replay", persona: "lena" }, replaying && mode.persona === "lena")}
          {modeButton("Replay: Marco", { kind: "replay", persona: "marco" }, replaying && mode.persona === "marco")}
          {modeButton("Replay: Sanktion", { kind: "replay", persona: "sanction_test" }, replaying && mode.persona === "sanction_test")}
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
