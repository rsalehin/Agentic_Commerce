import { STATE_LABEL_DE, STATE_SPINE } from "../theme";

const BRANCH = ["CUSTOMER_REQUIRED", "REVIEW_REQUIRED", "RECONCILING"];
const NEGATIVE = ["REJECTED", "EXPIRED", "CANCELLED"];

export function StateRibbon({ state }: { state: string | null }) {
  const spineIndex = state ? STATE_SPINE.indexOf(state as (typeof STATE_SPINE)[number]) : -1;
  const onBranch = state && BRANCH.includes(state);
  const rejected = state && NEGATIVE.includes(state);

  return (
    <div className="card">
      <div className="title">Zustandsmaschine</div>
      <div className="ribbon">
        {STATE_SPINE.map((s, i) => {
          const done = spineIndex >= 0 && i < spineIndex;
          const current = s === state;
          const cls = current ? "current" : done ? "done" : "";
          return (
            <span key={s} className={`step ${cls}`} title={s}>
              {STATE_LABEL_DE[s] ?? s}
            </span>
          );
        })}
        {onBranch && <span className="step blocked">{STATE_LABEL_DE[state] ?? state}</span>}
        {rejected && <span className="step rejected">{STATE_LABEL_DE[state] ?? state}</span>}
      </div>
    </div>
  );
}
