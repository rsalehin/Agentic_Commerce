import type { AuditEvent } from "../types";

interface Bubble {
  key: string;
  role: "agent" | "human" | "system";
  text: string;
  confirm?: "Bestätigen" | "Signieren";
}

// Narrate the audit trail as a German customer conversation (read-only for the
// deck; the interactive confirm/sign wiring lands with the replay UI in P1-13).
function narrate(events: AuditEvent[]): Bubble[] {
  const out: Bubble[] = [];
  for (const e of events) {
    const key = `${e.session_id}-${e.seq}`;
    switch (e.to_state) {
      case "MANDATE_VALID":
        out.push({ key, role: "agent", text: "Anbieter verifiziert. Bitte erteilen Sie das Mandat für die Depoteröffnung." });
        out.push({ key: key + "-h", role: "human", text: "Mandat erteilt.", confirm: "Signieren" });
        break;
      case "IDENTIFIED":
        out.push({ key, role: "agent", text: "Ich weise Ihre Identität über die Wallet nach (SD-JWT / PID)." });
        break;
      case "SCREENED":
        out.push({ key, role: "system", text: "Sanktions-/PEP-Prüfung abgeschlossen." });
        break;
      case "TAX_CONFIRMED":
        out.push({ key, role: "agent", text: "Bitte bestätigen Sie Ihre steuerliche Selbstauskunft." });
        out.push({ key: key + "-h", role: "human", text: "Selbstauskunft bestätigt.", confirm: "Signieren" });
        break;
      case "APPROPRIATENESS_DONE":
        out.push({ key, role: "agent", text: "Angemessenheitsprüfung erledigt — Produktklassen freigeschaltet." });
        break;
      case "INFORMED":
        out.push({ key, role: "agent", text: "Ich habe Ihnen die Vertragsunterlagen bereitgestellt." });
        break;
      case "CUSTOMER_CONFIRMED":
        out.push({ key, role: "human", text: "Vertrag signiert.", confirm: "Signieren" });
        break;
      case "DEPOT_OPENED":
        out.push({ key, role: "agent", text: "Ihr Depot wurde eröffnet. Sie erhalten Ihre Depotnummer." });
        break;
      case "CUSTOMER_REQUIRED":
        out.push({ key, role: "agent", text: "Für diesen Schritt ist Ihre Bestätigung nötig.", confirm: "Bestätigen" });
        break;
      case "REVIEW_REQUIRED":
        out.push({ key, role: "agent", text: "Ihr Antrag wird geprüft. Ein Mitarbeiter meldet sich." });
        break;
      case "ADVISED_HANDOFF":
        out.push({ key, role: "system", text: "An die Partnerbank-Beraterin übergeben." });
        break;
      case "REJECTED":
        out.push({ key, role: "agent", text: "Die Depoteröffnung kann nicht fortgesetzt werden." });
        break;
      default:
        break;
    }
    if (e.from_state === e.to_state && e.reason_codes.length > 0) {
      out.push({ key: key + "-g", role: "system", text: `Abgelehnt (im Rahmen des Mandats): ${e.reason_codes.join(", ")}` });
    }
  }
  return out;
}

export function ChatPanel({ events }: { events: AuditEvent[] }) {
  const bubbles = narrate(events);
  return (
    <div className="pane">
      <h2>Kundenchat</h2>
      <div className="chat">
        {bubbles.length === 0 && <div className="empty">Warte auf den Kundenagenten …</div>}
        {bubbles.map((b) => (
          <div key={b.key} style={{ display: "contents" }}>
            <div className={`bubble ${b.role}`}>{b.text}</div>
            {b.confirm && (
              <div className="confirm-row">
                <button className="btn primary">{b.confirm}</button>
                <button className="btn ghost">Ablehnen</button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
