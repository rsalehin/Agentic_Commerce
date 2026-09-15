"""Angemessenheitsprüfung helpers (docs/06 unlock logic, service_mode)."""

from __future__ import annotations

from typing import Any

COMPLEX = ("zertifikate", "derivate")


def unlocked_classes(experience: dict[str, Any]) -> list[str]:
    """A class is unlocked with years>=1 & trades>=1; complex classes need
    years>=2 & trades>=10; `etf` is unlocked if `fonds` is."""
    unlocked: set[str] = set()
    for cls, exp in experience.items():
        years = exp.get("years", 0)
        trades = exp.get("trades_per_year", 0)
        if cls in COMPLEX:
            if years >= 2 and trades >= 10:
                unlocked.add(cls)
        elif years >= 1 and trades >= 1:
            unlocked.add(cls)
    if "fonds" in unlocked:
        unlocked.add("etf")
    return sorted(unlocked)


def service_mode(requested_classes: list[str], advice_requested: bool) -> str:
    if advice_requested:
        return "advised"
    return "non_advised" if requested_classes else "account_only"
