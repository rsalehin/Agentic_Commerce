import type { AgentCard, AuditEvent, SessionSnapshot } from "./types";

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
