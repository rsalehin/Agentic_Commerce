"""`python -m agent.runner` entrypoint for the interactive run service (P3-07)."""

from __future__ import annotations

from agent.runner_service import app, create_runner_app, main

__all__ = ["app", "create_runner_app", "main"]
