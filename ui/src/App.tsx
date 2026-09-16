import { useEffect, useMemo, useState } from "react";

import {
  decideEscalation,
  decidePrompt,
  fetchCard,
  fetchEscalations,
  fetchRules,
  fetchRun,
  fetchSession,
  startRun,
  subscribeEvents,
} from "./api";
import { ChatPanel, type RunDecision } from "./components/ChatPanel";
import { OpsConsole } from "./components/OpsConsole";
import { BUNDLES } from "./replay";
import type { AgentCard, AuditEvent, Escalation, RuleInfo, RunStatus, SessionSnapshot } from "./types";

type Decision = "approve" | "request_appointment" | "reject";
type Mode = { kind: "live" } | { kind: "replay"; persona: string };

const PERSONAS: Array<{ id: string; label: string }> = [
  { id: "lena", label: "Lena" },
  { id: "marco", label: "Marco" },
  { id: "sanction_test", label: "Sanktion" },
];
const ENABLE_LIVE = (import.meta.env.VITE_ENABLE_LIVE as string | undefined) === "1";

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
  // Interactive runner (P3-07).
  const [persona, setPersona] = useState<string>("lena");
  const [runId, setRunId] = useState<string | null>(null);
  const [run, setRun] = useState<RunStatus | null>(null);
  const [decisions, setDecisions] = useState<RunDecision[]>([]);

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

  // Poll the runner while a run is active.
  useEffect(() => {
    if (!runId) return;
    let stop = false;
    const tick = async () => {
      const r = await fetchRun(runId);
      if (!stop && r) setRun(r);
    };
    void tick();
    const t = setInterval(tick, 600);
    return () => {
      stop = true;
      clearInterval(t);
    };
  }, [runId]);

  const activeSession = useMemo(() => {
    if (!replaying && run?.session_id) return run.session_id;
    if (pinned && !replaying) return pinned;
    for (let i = events.length - 1; i >= 0; i -= 1) return events[i].session_id;
    return null;
  }, [events, pinned, replaying, run]);

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

  async function onStart(runMode: "script" | "live") {
    setDecisions([]);
    setRun(null);
    setSnapshot(null);
    setRunId(null);
    setMode({ kind: "live" }); // ensure the live data source (resets the view)
    const id = await startRun(persona, runMode);
    setRunId(id);
  }

  function onPromptDecide(promptId: string, approved: boolean) {
    if (!runId) return;
    const purpose = run?.pending_prompt?.purpose ?? null;
    void decidePrompt(runId, promptId, approved);
    setDecisions((prev) => [...prev, { purpose, approved }]);
  }

  function selectMode(target: Mode) {
    setRunId(null);
    setRun(null);
    setMode(target);
  }

  const sessionEvents = useMemo(
    () => events.filter((e) => e.session_id === activeSession),
    [events, activeSession],
  );
  const lastEvent = sessionEvents.length ? sessionEvents[sessionEvents.length - 1] : null;
  const state = snapshot?.state ?? run?.state ?? lastEvent?.to_state ?? null;

  const runnerStatusDe = useMemo<string | null>(() => {
    if (!runId) return null;
    if (!run) return "Läuft";
    if (run.status === "waiting") return "Wartet auf Kunde";
    if (run.status === "running") return "Läuft";
    if (run.status === "error") return "Fehler";
    if (run.status === "finished") {
      if (run.declined) return run.session_id ? "Abgebrochen (storniert)" : "Abgebrochen (kein Antrag)";
      return "Abgeschlossen";
    }
    return null;
  }, [runId, run]);

  const modeButton = (label: string, target: Mode, active: boolean) => (
    <button
      className={`btn ${active ? "primary" : "ghost"}`}
      style={{ padding: "4px 10px", fontSize: 12, cursor: "pointer" }}
      onClick={() => selectMode(target)}
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
        <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
          <select
            value={persona}
            onChange={(e) => setPersona(e.target.value)}
            style={{ padding: "4px 6px", fontSize: 12 }}
          >
            {PERSONAS.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label}
              </option>
            ))}
          </select>
          <button
            className="btn primary"
            style={{ padding: "4px 10px", fontSize: 12, cursor: "pointer" }}
            onClick={() => onStart("script")}
          >
            Start
          </button>
          {ENABLE_LIVE && (
            <button
              className="btn ghost"
              style={{ padding: "4px 10px", fontSize: 12, cursor: "pointer" }}
              onClick={() => onStart("live")}
            >
              Start (LLM)
            </button>
          )}
          <span style={{ width: 1, height: 18, background: "rgba(0,0,0,0.15)", margin: "0 2px" }} />
          {modeButton("Live", { kind: "live" }, mode.kind === "live" && !runId)}
          {modeButton("Replay: Lena", { kind: "replay", persona: "lena" }, replaying && mode.persona === "lena")}
          {modeButton("Replay: Marco", { kind: "replay", persona: "marco" }, replaying && mode.persona === "marco")}
          {modeButton("Replay: Sanktion", { kind: "replay", persona: "sanction_test" }, replaying && mode.persona === "sanction_test")}
        </div>
      </header>
      <div className="split">
        <ChatPanel
          events={sessionEvents}
          interactive={runId != null}
          pendingPrompt={run?.pending_prompt ?? null}
          decisions={decisions}
          declined={run?.declined ?? false}
          declinedSession={Boolean(run?.declined && run?.session_id)}
          onDecide={onPromptDecide}
        />
        <OpsConsole
          card={card}
          events={sessionEvents}
          snapshot={snapshot}
          state={state}
          escalations={escalations}
          rules={rules}
          onDecide={onDecide}
          runnerStatusDe={runnerStatusDe}
        />
      </div>
    </div>
  );
}
