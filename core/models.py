"""SQLModel tables for the mock Depotbank core.

`Depot.operation_id` is UNIQUE — the business idempotency key that guarantees at
most one Depot per opening operation (ADR-11).
"""

from __future__ import annotations

from sqlmodel import Field, SQLModel


class Customer(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    holder_did: str = Field(unique=True)
    given_name: str
    family_name: str
    birth_date: str
    nationality: str
    created_at: str


class Application(SQLModel, table=True):
    id: str = Field(primary_key=True)  # = session_id
    customer_id: int | None = Field(default=None, foreign_key="customer.id")
    origin_channel: str = "agent"
    servicing_partner_id: str | None = None
    current_channel: str = "agent"
    commercial_attribution_ref: str | None = None
    referral_receipt: str | None = None
    revision: int = 1
    status: str = "DRAFT"
    created_at: str


class KycRecord(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    application_id: str = Field(foreign_key="application.id")
    assurance_level: str
    issuer: str
    sanctions: str  # clear | hit
    pep: str  # clear | hit
    created_at: str


class AppropriatenessProfile(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    application_id: str = Field(foreign_key="application.id")
    service_mode: str
    unlocked_classes: str  # JSON-encoded list
    blocked_classes: str  # JSON-encoded list
    created_at: str


class Contract(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    application_id: str = Field(foreign_key="application.id")
    snapshot_digest: str
    signed: bool = False
    signed_at: str | None = None


class Depot(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    operation_id: str = Field(unique=True)  # idempotency key (ADR-11)
    application_id: str = Field(foreign_key="application.id")
    depot_number: str = Field(unique=True)
    verrechnungskonto_iban: str
    custodian: str
    opened_at: str
