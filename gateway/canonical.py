"""JSON canonicalization (JCS, RFC 8785 subset) used for card signing,
`card_fingerprint`, and `snapshot_digest`.

Scope: the values we canonicalize are objects, arrays, strings, booleans, null
and integers — no floats. Under that restriction, sorted-key compact JSON with
no whitespace and UTF-8 output is exactly RFC 8785. Object keys are sorted by
Unicode code point (equivalent to RFC 8785's UTF-16 code-unit order for our
ASCII keys). The point is a byte-stable, deterministic encoding shared by the
signer and every verifier; `float` is rejected so a non-canonical number can
never slip in silently.
"""

from __future__ import annotations

import json
from typing import Any


def _reject_floats(obj: Any) -> None:
    if isinstance(obj, float):
        raise TypeError("jcs_canonicalize does not support float (use int or str)")
    if isinstance(obj, dict):
        for v in obj.values():
            _reject_floats(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _reject_floats(v)


def jcs_canonicalize(obj: Any) -> bytes:
    """Return the canonical UTF-8 bytes of ``obj`` (RFC 8785 subset)."""
    _reject_floats(obj)
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
