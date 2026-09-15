"""Mock reference-account name check (Referenzkontoprinzip, R-ID-04).

No real Open Banking: a small registry (built from the personas' reference
accounts) maps IBAN → registered holder name. `check(iban, name)` reports whether
the identified person matches. An unknown IBAN cannot be confirmed → no match.
"""

from __future__ import annotations

from functools import lru_cache

from core.fixtures import personas_file


@lru_cache(maxsize=1)
def _iban_holders() -> dict[str, str]:
    registry: dict[str, str] = {}
    for persona in personas_file()["personas"]:
        ref = persona.get("reference_account")
        if ref:
            registry[ref["iban"]] = ref["holder"]
    return registry


def check(iban: str, name: str) -> dict[str, bool]:
    """Return `{"name_match": bool, "known": bool}` for the IBAN/name pair."""
    holder = _iban_holders().get(iban)
    if holder is None:
        return {"name_match": False, "known": False}
    return {"name_match": holder.casefold() == name.casefold(), "known": True}
