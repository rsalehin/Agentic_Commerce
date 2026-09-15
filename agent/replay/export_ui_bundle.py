"""Export a self-contained UI bundle from a recorded run (P3-03 offline fallback).

Replays a recorded run in-process and writes {card, events, snapshot, escalations,
rules} to ui/src/replay/<persona>.json, so the UI can render the demo with the
network disabled (interview fallback, ADR-09).

    uv run python -m agent.replay.export_ui_bundle
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent.replay.runner import RUNS_DIR, build_local_harness, load_run, replay
from gateway.card import signed_card

REPO_ROOT = Path(__file__).resolve().parents[2]
UI_REPLAY_DIR = REPO_ROOT / "ui" / "src" / "replay"


def build_bundle(persona: str) -> dict[str, Any]:
    run = load_run(RUNS_DIR / f"{persona}.json")
    gateway, wallet, discover = build_local_harness(persona)
    result = replay(run, gateway=gateway, wallet=wallet, discover=discover)
    service = gateway.service
    return {
        "persona": persona,
        "card": signed_card(),
        "events": service.event_log,
        "snapshot": service.session_snapshot(result.session_id),
        "escalations": service.list_escalations(),
        "rules": service.rules_catalogue(),
    }


def main() -> None:
    UI_REPLAY_DIR.mkdir(parents=True, exist_ok=True)
    for persona in ("lena", "marco"):
        bundle = build_bundle(persona)
        path = UI_REPLAY_DIR / f"{persona}.json"
        path.write_text(json.dumps(bundle, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"[export] {persona}: {bundle['snapshot']['state']} -> {path}")


if __name__ == "__main__":
    main()
