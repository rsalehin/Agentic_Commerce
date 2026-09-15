"""Print the rules catalogue as a Markdown table (source for docs/06_rules.md).

    uv run python -m gateway.rules.export_md
"""

from __future__ import annotations

from gateway.rules.engine import RulesEngine


def render() -> str:
    engine = RulesEngine()
    lines = [
        f"# Regelkatalog (rules.yaml v{engine.version})",
        "",
        "| Id | Schritt | Rechtsgrundlage | Ergebnis | Reason code |",
        "|---|---|---|---|---|",
    ]
    for rule in engine.rules:
        flags = []
        if rule.get("guard"):
            flags.append("Guard")
        if rule.get("confidential"):
            flags.append("vertraulich")
        if rule.get("informational"):
            flags.append("informational")
        outcome = rule["outcome"] + (f" ({', '.join(flags)})" if flags else "")
        lines.append(
            f"| {rule['id']} | {rule['step']} | {rule['law']} | {outcome} | "
            f"{rule.get('reason_code', '—')} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    print(render(), end="")


if __name__ == "__main__":
    main()
