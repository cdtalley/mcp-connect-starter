"""PII redaction applied to every tool output before it leaves the server.

This is a defense-in-depth filter, not a substitute for not collecting PII
in the first place. Patterns are intentionally conservative (optimized for
catching obvious PII in free text) rather than a full PII-detection engine;
swap in a dedicated service (e.g. AWS Comprehend PII, Presidio) for
higher-stakes deployments.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel

# Order matters: more specific patterns (SSN) run before more general ones
# (phone numbers) so a 9-digit SSN isn't partially re-matched as a phone
# number. Each match is replaced with a tag, which then can't accidentally
# match a later pattern (tags contain no digit runs).
_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "SSN",
        re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    ),
    (
        "EMAIL",
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    ),
    (
        "SECRET",
        # key=value / key: value pairs that look like credentials, e.g.
        # "api_key: sk-ABC123..." or "password=hunter2". Redacts only the
        # value, keeping the key name for context.
        re.compile(
            r"(?i)\b(api[_-]?key|secret|password|passwd|token|access[_-]?key)\s*[:=]\s*"
            r"(?P<value>[^\s,;]+)"
        ),
    ),
    (
        "AWS_KEY",
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    ),
    (
        "CARD",
        # 13-19 digits, optionally grouped by spaces or dashes. Validated by
        # Luhn (below) before being treated as a redaction hit, so ordinary
        # long numeric IDs are not falsely redacted.
        re.compile(r"\b(?:\d[ -]?){13,19}\b"),
    ),
    (
        "PHONE",
        re.compile(
            r"(?<!\d)(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}(?!\d)"
        ),
    ),
]


def _luhn_ok(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def redact_text(text: str) -> str:
    """Replace PII-looking substrings in `text` with `[REDACTED_<KIND>]` tags."""
    if not text:
        return text

    for kind, pattern in _PATTERNS:
        if kind == "CARD":

            def _card_sub(match: re.Match[str]) -> str:
                digits = re.sub(r"[ -]", "", match.group(0))
                if 13 <= len(digits) <= 19 and _luhn_ok(digits):
                    return "[REDACTED_CARD]"
                return match.group(0)

            text = pattern.sub(_card_sub, text)
        elif kind == "SECRET":

            def _secret_sub(match: re.Match[str]) -> str:
                key = match.group(1)
                return f"{key}=[REDACTED_SECRET]"

            text = pattern.sub(_secret_sub, text)
        else:
            text = pattern.sub(f"[REDACTED_{kind}]", text)

    return text


def redact_any(value: Any) -> Any:
    """Recursively redact strings nested inside dicts, lists, tuples, and
    Pydantic models, preserving the original structure and types.
    """
    if isinstance(value, BaseModel):
        redacted_data = redact_any(value.model_dump())
        return type(value).model_validate(redacted_data)
    if isinstance(value, dict):
        return {key: redact_any(val) for key, val in value.items()}
    if isinstance(value, list):
        return [redact_any(val) for val in value]
    if isinstance(value, tuple):
        return tuple(redact_any(val) for val in value)
    if isinstance(value, str):
        return redact_text(value)
    return value
