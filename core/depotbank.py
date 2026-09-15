"""Mock Depotbank core: idempotent Depot provisioning + reconciliation (ADR-11).

`create_depot` is keyed by `operation_id` (unique). A duplicate call returns the
stored Depot (same number, count stays one). An `uncertain=True` call models a
lost provisioning acknowledgement: the Depot IS written, but the result is
`PROVISIONING_UNCERTAIN` so the caller enters `RECONCILING`; `get_opening_status`
then reads the truth by `operation_id` — never a second create.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import Engine
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from core.db import init_db
from core.fixtures import provider
from core.models import Depot

STATE_OPENED = "DEPOT_OPENED"
STATE_UNCERTAIN = "PROVISIONING_UNCERTAIN"


@dataclass(frozen=True)
class OpeningResult:
    state: str  # DEPOT_OPENED | PROVISIONING_UNCERTAIN
    operation_id: str
    depot: Depot | None


def _now() -> str:
    return datetime.now(UTC).isoformat()


class DepotbankCore:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        init_db(engine)
        self._custodian = provider().get("custodian_de", "Fonds AG Depotbank (Mock)")

    def _find(self, session: Session, operation_id: str) -> Depot | None:
        return session.exec(select(Depot).where(Depot.operation_id == operation_id)).first()

    def create_depot(
        self, *, operation_id: str, application_id: str, uncertain: bool = False
    ) -> OpeningResult:
        with Session(self._engine) as session:
            existing = self._find(session, operation_id)
            if existing is not None:  # idempotent replay
                return OpeningResult(STATE_OPENED, operation_id, existing)

            depot = Depot(
                operation_id=operation_id,
                application_id=application_id,
                depot_number="pending",
                verrechnungskonto_iban="pending",
                custodian=self._custodian,
                opened_at=_now(),
            )
            session.add(depot)
            try:
                session.flush()  # assign id; enforce UNIQUE(operation_id)
            except IntegrityError:
                session.rollback()
                stored = self._find(session, operation_id)
                assert stored is not None
                return OpeningResult(STATE_OPENED, operation_id, stored)

            depot.depot_number = f"{1_000_000_000 + int(depot.id or 0)}"
            depot.verrechnungskonto_iban = f"DE89{depot.depot_number}00000000"
            session.add(depot)
            session.commit()
            session.refresh(depot)

            if uncertain:
                # The write happened, but we "did not get the ack".
                return OpeningResult(STATE_UNCERTAIN, operation_id, None)
            return OpeningResult(STATE_OPENED, operation_id, depot)

    def get_opening_status(self, operation_id: str) -> OpeningResult:
        with Session(self._engine) as session:
            depot = self._find(session, operation_id)
            if depot is not None:
                return OpeningResult(STATE_OPENED, operation_id, depot)
            return OpeningResult(STATE_UNCERTAIN, operation_id, None)

    def depot_count(self) -> int:
        with Session(self._engine) as session:
            return len(session.exec(select(Depot)).all())
