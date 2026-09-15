"""P1-05 tests: idempotent create_depot, reconciliation, unique constraint."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from core.db import make_engine
from core.depotbank import STATE_OPENED, STATE_UNCERTAIN, DepotbankCore
from core.models import Application, Depot


def _core() -> DepotbankCore:
    core = DepotbankCore(make_engine())  # in-memory
    with Session(core._engine) as s:
        s.add(Application(id="ses_1", created_at=datetime.now(UTC).isoformat()))
        s.commit()
    return core


def test_create_depot_returns_number() -> None:
    core = _core()
    res = core.create_depot(operation_id="ses_1:create_depot", application_id="ses_1")
    assert res.state == STATE_OPENED
    assert res.depot is not None
    assert len(res.depot.depot_number) == 10
    assert res.depot.verrechnungskonto_iban.startswith("DE89")


def test_idempotent_replay_same_number_count_one() -> None:
    core = _core()
    op = "ses_1:create_depot"
    first = core.create_depot(operation_id=op, application_id="ses_1")
    second = core.create_depot(operation_id=op, application_id="ses_1")
    assert first.depot is not None and second.depot is not None
    assert first.depot.depot_number == second.depot.depot_number
    assert core.depot_count() == 1


def test_uncertain_then_reconcile() -> None:
    core = _core()
    op = "ses_1:create_depot"
    res = core.create_depot(operation_id=op, application_id="ses_1", uncertain=True)
    assert res.state == STATE_UNCERTAIN
    assert res.depot is None  # ack "lost", but the write happened
    assert core.depot_count() == 1
    # Reconcile by status, never a second create.
    status = core.get_opening_status(op)
    assert status.state == STATE_OPENED
    assert status.depot is not None


def test_get_opening_status_unknown_is_uncertain() -> None:
    core = _core()
    status = core.get_opening_status("ses_1:create_depot")
    assert status.state == STATE_UNCERTAIN
    assert status.depot is None


def test_unique_operation_id_constraint() -> None:
    core = _core()
    with Session(core._engine) as s:
        s.add(Depot(operation_id="dup", application_id="ses_1", depot_number="1",
                    verrechnungskonto_iban="DE1", custodian="x", opened_at="t"))
        s.commit()
        s.add(Depot(operation_id="dup", application_id="ses_1", depot_number="2",
                    verrechnungskonto_iban="DE2", custodian="x", opened_at="t"))
        with pytest.raises(IntegrityError):
            s.commit()
