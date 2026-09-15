"""Deterministic, law-citing rules engine (ADR-04).

Loads `rules.yaml` (v1.1.0) and evaluates the rules applicable to a step against
a per-call context. Guards (`guard: true`) are evaluated first and short-circuit
to `ERROR`; the remaining outcomes aggregate by precedence
(`DENY > REQUIRE_REVIEW > REQUIRE_CUSTOMER > ALLOW_WITH_WARNING > ALLOW`).
Confidential (`AML_*`) reason codes are masked to `IN_REVIEW` for the agent
(GwG § 47); the real codes are kept for the audit log.

`when` is a Python expression over `ctx` evaluated in a restricted namespace
(no builtins except a small allow-list). The LLM never runs here — this is the
policy, in code, with a paragraph per rule.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import yaml

RULES_PATH = Path(__file__).resolve().parent / "rules.yaml"

# Aggregation precedence (most restrictive first). ERROR is handled separately.
_PRECEDENCE = ["DENY", "REQUIRE_REVIEW", "REQUIRE_CUSTOMER", "ALLOW_WITH_WARNING", "ALLOW"]
_ALLOWED_NAMES: dict[str, Any] = {
    "any": any,
    "all": all,
    "abs": abs,
    "len": len,
    "min": min,
    "max": max,
}
_MASKED_CODE = "IN_REVIEW"
_MASKED_MESSAGE_DE = "Ihr Antrag wird geprüft."


class EngineError(Exception):
    """A rule's `when` could not be evaluated against the context."""


@dataclass(frozen=True)
class RuleResult:
    id: str
    outcome: str
    law: str
    reason_code: str | None
    message_de: str | None
    confidential: bool = False
    informational: bool = False


@dataclass(frozen=True)
class PolicyDecision:
    outcome: str
    reason_codes: list[str]  # real codes (for the audit log)
    rules: list[RuleResult]  # the rules that FIRED (non-ALLOW)
    policy_version: str
    confidential: bool = False
    message_de: str | None = None
    sets: dict[str, bool] = field(default_factory=dict)
    # Every applicable rule with its actual outcome (ALLOW if it passed) — the
    # per-step audit/Nachweis record (P2-05).
    evaluated: list[RuleResult] = field(default_factory=list)

    def agent_reason_codes(self) -> list[str]:
        """Codes shown to the agent/customer: masked for confidential reviews."""
        return [_MASKED_CODE] if self.confidential else list(self.reason_codes)

    def agent_message_de(self) -> str | None:
        return _MASKED_MESSAGE_DE if self.confidential else self.message_de


def _namespace(obj: Any) -> Any:
    if isinstance(obj, dict):
        return SimpleNamespace(**{k: _namespace(v) for k, v in obj.items()})
    if isinstance(obj, list):
        return [_namespace(v) for v in obj]
    return obj


class RulesEngine:
    def __init__(self, rules_path: Path = RULES_PATH) -> None:
        data = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
        self.version: str = data["version"]
        self.rules: list[dict[str, Any]] = data["rules"]

    def reason_codes(self) -> set[str]:
        return {r["reason_code"] for r in self.rules if "reason_code" in r}

    def _applies(self, rule: dict[str, Any], step: str) -> bool:
        return rule["step"] in (step, "any")

    def _fires(self, rule: dict[str, Any], ns: Any) -> bool:
        try:
            return bool(eval(rule["when"], {"__builtins__": {}, "ctx": ns, **_ALLOWED_NAMES}))  # noqa: S307
        except Exception as exc:  # noqa: BLE001 - surface a clear engine error
            raise EngineError(f"{rule['id']}: {rule['when']!r} -> {exc}") from exc

    def _result(self, rule: dict[str, Any]) -> RuleResult:
        return RuleResult(
            id=rule["id"],
            outcome=rule["outcome"],
            law=rule["law"],
            reason_code=rule.get("reason_code"),
            message_de=rule.get("message_de"),
            confidential=bool(rule.get("confidential", False)),
            informational=bool(rule.get("informational", False)),
        )

    def _evaluated(self, rule: dict[str, Any], fired: bool) -> RuleResult:
        """A rule's record with its actual outcome (ALLOW when it passed)."""
        return RuleResult(
            id=rule["id"],
            outcome=rule["outcome"] if fired else "ALLOW",
            law=rule["law"],
            reason_code=rule.get("reason_code") if fired else None,
            message_de=rule.get("message_de") if fired else None,
            confidential=bool(rule.get("confidential", False)),
            informational=bool(rule.get("informational", False)),
        )

    def evaluate(self, step: str, ctx: dict[str, Any]) -> PolicyDecision:
        ns = _namespace(ctx)
        applicable = [r for r in self.rules if self._applies(r, step)]
        fired_map = {r["id"]: self._fires(r, ns) for r in applicable}
        # Every applicable check with its result (for the audit/Nachweis).
        evaluated = [self._evaluated(r, fired_map[r["id"]]) for r in applicable]

        # 1. Guards first — any firing guard short-circuits to ERROR.
        guard_hits = [self._result(r) for r in applicable if r.get("guard") and fired_map[r["id"]]]
        if guard_hits:
            return PolicyDecision(
                outcome="ERROR",
                reason_codes=[g.reason_code for g in guard_hits if g.reason_code],
                rules=guard_hits,
                policy_version=self.version,
                message_de=guard_hits[0].message_de,
                evaluated=evaluated,
            )

        # 2. Non-guard rules.
        fired = [self._result(r) for r in applicable if not r.get("guard") and fired_map[r["id"]]]
        sets = {r.id: True for r in fired if r.informational}
        gating = [r for r in fired if not r.informational and r.outcome != "ALLOW"]

        if not gating:
            return PolicyDecision(
                outcome="ALLOW",
                reason_codes=[],
                rules=fired,
                policy_version=self.version,
                sets=sets,
                evaluated=evaluated,
            )

        winner_outcome = min(gating, key=lambda r: _PRECEDENCE.index(r.outcome)).outcome
        winner = next(r for r in gating if r.outcome == winner_outcome)
        return PolicyDecision(
            outcome=winner_outcome,
            reason_codes=[r.reason_code for r in gating if r.reason_code],
            rules=fired,
            policy_version=self.version,
            confidential=any(r.confidential for r in gating),
            message_de=winner.message_de,
            sets=sets,
            evaluated=evaluated,
        )
