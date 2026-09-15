import type { AgentCard, AuditEvent, Escalation, RuleInfo, SessionSnapshot } from "./types";

export const API_BASE =
  (import.meta.env.VITE_GATEWAY_URL as string | undefined) ?? "http://localhost:8080";

export async function fetchSession(id: string): Promise<SessionSnapshot | null> {
  const resp = await fetch(`${API_BASE}/sessions/${id}`);
  return resp.ok ? ((await resp.json()) as SessionSnapshot) : null;
}

export async function fetchCard(): Promise<AgentCard | null> {
  try {
    const resp = await fetch(`${API_BASE}/.well-known/agent-card.json`);
    return resp.ok ? ((await resp.json()) as AgentCard) : null;
  } catch {
    return null;
  }
}

export async function fetchEscalations(): Promise<Escalation[]> {
  const resp = await fetch(`${API_BASE}/escalations`);
  if (!resp.ok) return [];
  return ((await resp.json()) as { escalations: Escalation[] }).escalations;
}

export async function fetchRules(): Promise<RuleInfo[]> {
  const resp = await fetch(`${API_BASE}/rules`);
  if (!resp.ok) return [];
  return ((await resp.json()) as { rules: RuleInfo[] }).rules;
}

export async function decideEscalation(
  id: string,
  decision: "approve" | "request_appointment" | "reject",
  actor: string,
  note?: string,
): Promise<void> {
  await fetch(`${API_BASE}/escalations/${id}/decision`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ decision, actor, note }),
  });
}

/** Subscribe to the live audit feed (SSE). Returns an unsubscribe function. */
export function subscribeEvents(onEvent: (e: AuditEvent) => void): () => void {
  const source = new EventSource(`${API_BASE}/events`);
  source.onmessage = (ev) => {
    if (!ev.data || ev.data === "{}") return;
    try {
      onEvent(JSON.parse(ev.data) as AuditEvent);
    } catch {
      /* ignore malformed frames */
    }
  };
  return () => source.close();
}
