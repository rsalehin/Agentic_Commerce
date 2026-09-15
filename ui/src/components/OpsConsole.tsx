import type { AgentCard, AuditEvent, Escalation, RuleInfo, SessionSnapshot } from "../types";
import { STATE_LABEL_DE } from "../theme";
import { AdviserPanel } from "./AdviserPanel";
import { AuditList } from "./AuditList";
import { ProviderCard } from "./ProviderCard";
import { StateRibbon } from "./StateRibbon";

type Decision = "approve" | "request_appointment" | "reject";

interface Props {
  card: AgentCard | null;
  events: AuditEvent[];
  snapshot: SessionSnapshot | null;
  state: string | null;
  escalations: Escalation[];
  rules: RuleInfo[];
  onDecide: (id: string, decision: Decision) => void;
}

export function OpsConsole({ card, events, snapshot, state, escalations, rules, onDecide }: Props) {
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
        <AdviserPanel escalations={escalations} rules={rules} onDecide={onDecide} />
        <AuditList events={events} chainOk={snapshot ? snapshot.audit_chain_ok : null} />
      </div>
    </div>
  );
}
