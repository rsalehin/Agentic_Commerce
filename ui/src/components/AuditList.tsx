import type { AuditEvent } from "../types";

export function AuditList({ events, chainOk }: { events: AuditEvent[]; chainOk: boolean | null }) {
  return (
    <div className="card">
      <div className="title" style={{ display: "flex", justifyContent: "space-between" }}>
        <span>Audit-Trail ({events.length})</span>
        {chainOk !== null && (
          <span className={`badge ${chainOk ? "ok" : "danger"}`}>
            {chainOk ? "✓ Kette gültig" : "✗ Kette gebrochen"}
          </span>
        )}
      </div>
      {events.length === 0 ? (
        <div className="empty">Noch keine Ereignisse.</div>
      ) : (
        <div className="audit">
          {events.map((e) => {
            const noop = e.from_state === e.to_state;
            return (
              <div className="event" key={`${e.session_id}-${e.seq}`}>
                <div className="head">
                  <span className="transition">
                    {noop ? `⚠ ${e.to_state}` : `${e.from_state} → ${e.to_state}`}
                  </span>
                  <span className="actor">
                    #{e.seq} · {e.actor}
                    {e.tool ? ` · ${e.tool}` : ""}
                  </span>
                </div>
                {e.reason_codes.length > 0 && (
                  <div className="codes">{e.reason_codes.join(", ")}</div>
                )}
                <div className="hash">{e.hash}</div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
