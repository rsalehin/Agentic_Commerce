import { STATE_LABEL_DE } from "../theme";
import type { Escalation, RuleInfo } from "../types";

type Decision = "approve" | "request_appointment" | "reject";

interface Props {
  escalations: Escalation[];
  rules: RuleInfo[];
  onDecide: (id: string, decision: Decision) => void;
}

export function AdviserPanel({ escalations, rules, onDecide }: Props) {
  const lawByCode = new Map(rules.filter((r) => r.reason_code).map((r) => [r.reason_code!, r.law]));
  const open = escalations.filter((e) => e.status === "open");

  return (
    <div className="card">
      <div className="title" style={{ display: "flex", justifyContent: "space-between" }}>
        <span>Beraterpanel</span>
        <span style={{ fontSize: 12, color: "#6b7683" }}>Volksbank Leipzig · Frau Weber</span>
      </div>

      {open.length === 0 && <div className="empty">Keine offenen Eskalationen.</div>}

      {open.map((e) => {
        if (e.confidential) {
          return (
            <div className="event" key={e.id} style={{ borderLeftColor: "var(--warn)" }}>
              <div className="head">
                <span className="transition">Compliance-Prüfung</span>
                <span className="actor">{e.id} · vertraulich</span>
              </div>
              <div style={{ fontSize: 12, color: "#6b7683" }}>
                Fall in Compliance-Prüfung (§ 47 GwG) – für die Beraterin nicht einsehbar.
              </div>
            </div>
          );
        }
        if (e.queue === "customer") {
          return (
            <div className="event" key={e.id}>
              <div className="head">
                <span className="transition">Kundenaktion nötig</span>
                <span className="actor">{e.id}</span>
              </div>
              <div className="codes">{e.reasons.join(", ")}</div>
            </div>
          );
        }
        return (
          <div className="event" key={e.id} style={{ borderLeftColor: "var(--gold)" }}>
            <div className="head">
              <span className="transition">Freigabe erforderlich</span>
              <span className="actor">
                {e.id} · blockiert bei {e.blocked_from ? (STATE_LABEL_DE[e.blocked_from] ?? e.blocked_from) : "—"}
              </span>
            </div>
            <ul style={{ margin: "6px 0", paddingLeft: 18, fontSize: 13 }}>
              {e.reasons.map((code) => (
                <li key={code}>
                  <strong>{code}</strong>
                  {lawByCode.get(code) ? <span style={{ color: "#6b7683" }}> — {lawByCode.get(code)}</span> : null}
                </li>
              ))}
            </ul>
            <div className="confirm-row" style={{ alignSelf: "flex-start", gap: 8 }}>
              <button className="btn primary" onClick={() => onDecide(e.id, "approve")}>
                Freigeben
              </button>
              <button className="btn ghost" onClick={() => onDecide(e.id, "request_appointment")}>
                Termin vereinbaren
              </button>
              <button className="btn ghost" onClick={() => onDecide(e.id, "reject")}>
                Ablehnen
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
