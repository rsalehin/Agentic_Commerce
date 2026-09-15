import type { AgentCard, AuditEvent, SessionSnapshot } from "../types";
import { STATE_LABEL_DE } from "../theme";
import { AuditList } from "./AuditList";
import { ProviderCard } from "./ProviderCard";
import { StateRibbon } from "./StateRibbon";

interface Props {
  card: AgentCard | null;
  events: AuditEvent[];
  snapshot: SessionSnapshot | null;
  state: string | null;
}

export function OpsConsole({ card, events, snapshot, state }: Props) {
  return (
    <div className="pane">
      <h2>Ops-Konsole</h2>
      <div className="ops">
        <ProviderCard card={card} />
        <div className="card">
          <div className="title">Sitzung</div>
          <div className="kv">
            <span className="k">Session</span>
            <span>{snapshot?.session_id ?? "—"}</span>
            <span className="k">Status</span>
            <span>{state ? (STATE_LABEL_DE[state] ?? state) : "—"}</span>
            <span className="k">Service-Modus</span>
            <span>{snapshot?.service_mode ?? "—"}</span>
            {snapshot?.blocked_from && (
              <>
                <span className="k">Blockiert bei</span>
                <span>{STATE_LABEL_DE[snapshot.blocked_from] ?? snapshot.blocked_from}</span>
              </>
            )}
          </div>
        </div>
        <StateRibbon state={state} />
        <AuditList events={events} chainOk={snapshot ? snapshot.audit_chain_ok : null} />
      </div>
    </div>
  );
}
