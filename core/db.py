"""SQLite engine factory for the core mock."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, create_engine

import core.models  # noqa: F401  (register tables on SQLModel.metadata)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = REPO_ROOT / "data" / "demo.db"


def make_engine(url: str | None = None) -> Engine:
    """Create an engine. `url=None` → shared in-memory SQLite (for tests)."""
    if url is None:
        return create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    return create_engine(url, connect_args={"check_same_thread": False})


def default_engine() -> Engine:
    DEFAULT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return make_engine(f"sqlite:///{DEFAULT_DB_PATH}")


def init_db(engine: Engine) -> None:
    SQLModel.metadata.create_all(engine)
