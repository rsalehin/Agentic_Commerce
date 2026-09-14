"""Mock PID issuer (mock-bundesdruckerei).

Issues a persona's PID as an SD-JWT VC. The confirmation key (`cnf`) is bound to
that persona's holder key — the same key that signs the mandate — which is what
makes the gateway's R-ID-05 (`did:key(cnf) == mandate.iss`) meaningful.
"""

from __future__ import annotations

import time
from typing import Any

from wallet import sdjwt
from wallet.keys import ISSUER_KID, KeyRegistry, public_jwk

# GwG data set + assurance level carried in the PID.
PID_CLAIMS = (
    "given_name",
    "family_name",
    "birth_date",
    "birth_place",
    "birth_place_country",
    "nationalities",
    "address",
    "national_id_number",
    "tax_id",
    "assurance_level",
)


def issue_pid_for_persona(
    persona: dict[str, Any],
    registry: KeyRegistry,
    *,
    now: int | None = None,
) -> str:
    """Issue the SD-JWT VC for a persona (`persona["pid"]`), cnf = holder key."""
    pid = persona["pid"]
    claims = {name: pid[name] for name in PID_CLAIMS if name in pid}
    holder = registry.holders[persona["id"]]
    holder_jwk = public_jwk(holder.public, holder.kid)
    return sdjwt.issue(
        claims,
        issuer_key=registry.issuer.private,
        issuer_kid=ISSUER_KID,
        holder_jwk=holder_jwk,
        now=int(time.time()) if now is None else now,
    )
