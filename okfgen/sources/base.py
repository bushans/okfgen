"""Base class and shared helpers for source adapters."""

from __future__ import annotations

from typing import Optional

from ..model import Bundle


class SourceError(Exception):
    """Raised when a source cannot be ingested (bad input, missing deps, auth)."""


class Source:
    """A source adapter converts one input string into an OKF Bundle.

    Subclasses set `kind` and implement `matches()` (for auto-detection) and
    `build()` (deterministic extraction — no LLMs, no network beyond what the
    kind inherently requires).
    """

    kind: str = "base"

    def __init__(self, input_value: str, options: Optional[dict] = None):
        self.input_value = input_value
        self.options = options or {}

    @classmethod
    def matches(cls, input_value: str) -> bool:  # pragma: no cover - overridden
        return False

    def build(self) -> Bundle:  # pragma: no cover - overridden
        raise NotImplementedError
