"""Shared fixture access for the core mock and its stubs."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
PERSONAS_PATH = REPO_ROOT / "fixtures" / "personas.json"


@lru_cache(maxsize=1)
def personas_file() -> dict[str, Any]:
    return json.loads(PERSONAS_PATH.read_text(encoding="utf-8"))


def stubs() -> dict[str, Any]:
    return personas_file()["stubs"]


def provider() -> dict[str, Any]:
    return personas_file()["provider"]
