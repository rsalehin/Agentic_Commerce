"""Mock BZSt KiStAM lookup (church-tax attribute)."""

from __future__ import annotations

from core.fixtures import stubs


def lookup(tax_id: str) -> str:
    """Return the KiStAM result for a tax id: 'ev' | 'rk' | 'none'."""
    table: dict[str, str] = stubs().get("kistam", {})
    return table.get(tax_id, "none")
