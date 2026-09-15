"""P1-05 tests: BZSt KiStAM, sanctions/PEP, reference-account stubs."""

from __future__ import annotations

from core.stubs import bzst_kistam, reference_account, sanctions


def test_kistam_lookup() -> None:
    assert bzst_kistam.lookup("12345678901") == "ev"  # lena
    assert bzst_kistam.lookup("98765432109") == "none"  # marco
    assert bzst_kistam.lookup("00000000000") == "none"  # unknown default


def test_sanctions_hit_and_clear() -> None:
    hit = sanctions.screen("Test", "Sanktion", "1970-01-01")
    assert hit == {"sanctions": "hit", "pep": "clear"}
    clear = sanctions.screen("Lena", "Schmidt", "1992-03-14")
    assert clear == {"sanctions": "clear", "pep": "clear"}
    # Case-insensitive on names, exact on birth date.
    assert sanctions.screen("test", "sanktion", "1970-01-01")["sanctions"] == "hit"
    assert sanctions.screen("Test", "Sanktion", "1980-01-01")["sanctions"] == "clear"


def test_reference_account_match() -> None:
    assert reference_account.check("DE89370400440532013000", "Lena Schmidt") == {
        "name_match": True,
        "known": True,
    }
    assert reference_account.check("DE89370400440532013000", "Someone Else")["name_match"] is False
    unknown = reference_account.check("DE00000000000000009999", "Whoever")
    assert unknown == {"name_match": False, "known": False}
