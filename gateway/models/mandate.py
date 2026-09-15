"""Intent Mandate model (docs/05 §2)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Amount(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: int
    currency: str = "EUR"


class Scope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_classes: list[str]
    monthly_amount_max: Amount
    one_off_amount_max: Amount
    advice_allowed: bool
    data_release: list[str]


class AgentRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    provider: str
    card_fingerprint: str


class Mandate(BaseModel):
    """A parsed, schema-valid mandate payload. Signature/aud/exp/jti are checked
    by the verifier, not here."""

    model_config = ConfigDict(extra="forbid")
    iss: str
    sub: str
    aud: str
    iat: int
    exp: int
    jti: str
    agent: AgentRef
    purpose: str
    scope: Scope
    human_only: list[str]
    revocation_url: str
