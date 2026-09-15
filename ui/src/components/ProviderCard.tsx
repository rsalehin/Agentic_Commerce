import type { AgentCard } from "../types";

export function ProviderCard({ card }: { card: AgentCard | null }) {
  if (!card) {
    return (
      <div className="card">
        <div className="title">Anbieter</div>
        <div className="empty">Kein Agent Card geladen.</div>
      </div>
    );
  }
  const signed = (card.signatures?.length ?? 0) > 0;
  return (
    <div className="card">
      <div className="title" style={{ display: "flex", justifyContent: "space-between" }}>
        <span>Anbieter</span>
        <span className={`badge ${signed ? "ok" : "danger"}`}>
          {signed ? "✓ verifiziert" : "nicht verifiziert"}
        </span>
      </div>
      <div className="kv">
        <span className="k">Organisation</span>
        <span>{card.provider.organization}</span>
        <span className="k">Domain</span>
        <span>{card.provider.url}</span>
        {card.provider.custodian && (
          <>
            <span className="k">Depotbank</span>
            <span>{card.provider.custodian}</span>
          </>
        )}
        {card.provider.bafin_id && (
          <>
            <span className="k">BaFin-ID</span>
            <span>{card.provider.bafin_id}</span>
          </>
        )}
        {card.provider.lei && (
          <>
            <span className="k">LEI</span>
            <span>{card.provider.lei}</span>
          </>
        )}
      </div>
    </div>
  );
}
