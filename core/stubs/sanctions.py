"""Mock sanctions/PEP screening.

A list match is a *possible* correspondence, resolved by compliance (never an
automatic rejection — see R-AML-01 / GwG § 47). This stub only reports
clear|hit; the decision lives in the rules engine + compliance queue.
"""

from __future__ import annotations

from core.fixtures import stubs


def _matches(entry: dict[str, str], given_name: str, family_name: str, birth_date: str) -> bool:
    return (
        entry.get("given_name", "").casefold() == given_name.casefold()
        and entry.get("family_name", "").casefold() == family_name.casefold()
        and entry.get("birth_date", "") == birth_date
    )


def screen(given_name: str, family_name: str, birth_date: str) -> dict[str, str]:
    """Return `{"sanctions": "clear|hit", "pep": "clear|hit"}`."""
    data = stubs()
    sanctions = any(
        _matches(e, given_name, family_name, birth_date) for e in data.get("sanctions_list", [])
    )
    pep = any(_matches(e, given_name, family_name, birth_date) for e in data.get("pep_list", []))
    return {
        "sanctions": "hit" if sanctions else "clear",
        "pep": "hit" if pep else "clear",
    }
