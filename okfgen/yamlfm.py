"""Minimal, dependency-free YAML frontmatter emit/parse.

The generator only ever emits a small, well-defined subset of YAML (scalars,
flat lists, and lists of scalars), so we hand-roll a deterministic emitter
instead of pulling in a dependency. For *parsing* (used by the validator, which
must tolerate arbitrary producer frontmatter) we prefer PyYAML when installed
and fall back to a small parser that covers the common OKF cases.
"""

from __future__ import annotations

import datetime as _dt
import re as _re
from typing import Any, Dict, List, Optional, Tuple

_NUMBERISH = _re.compile(r"^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$")

try:  # PyYAML is an optional extra; use it for robust parsing when present.
    import yaml as _pyyaml  # type: ignore
except Exception:  # pragma: no cover - exercised only when PyYAML is absent
    _pyyaml = None

FRONTMATTER_DELIM = "---"

# Ordering used when emitting concept frontmatter so bundles diff cleanly.
_PREFERRED_ORDER = [
    "type",
    "title",
    "description",
    "resource",
    "tags",
    "timestamp",
]


def _needs_quoting(s: str) -> bool:
    if s == "":
        return True
    if s != s.strip():
        return True
    # Characters/prefixes that would confuse a YAML reader.
    if s[0] in "!&*?|>%@`\"'#,[]{}-":
        return True
    if any(c in s for c in [":", "\n", "\t"]):
        return True
    if s.lower() in {"true", "false", "null", "yes", "no", "~"}:
        return True
    # Quote number-looking strings so a stored string (e.g. version "0.1") is
    # not silently coerced to int/float on parse.
    if _NUMBERISH.match(s):
        return True
    return False


def _emit_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, _dt.datetime):
        return value.isoformat()
    s = str(value)
    if _needs_quoting(s):
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return s


def dump(data: Dict[str, Any]) -> str:
    """Serialize a flat-ish dict to a deterministic YAML frontmatter body."""
    keys = [k for k in _PREFERRED_ORDER if k in data]
    keys += [k for k in data if k not in _PREFERRED_ORDER]

    lines: List[str] = []
    for key in keys:
        value = data[key]
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            items = [v for v in value if v is not None]
            if not items:
                continue
            lines.append(f"{key}:")
            for item in items:
                lines.append(f"  - {_emit_scalar(item)}")
        elif isinstance(value, dict):
            lines.append(f"{key}:")
            for sub_k, sub_v in value.items():
                lines.append(f"  {sub_k}: {_emit_scalar(sub_v)}")
        else:
            lines.append(f"{key}: {_emit_scalar(value)}")
    return "\n".join(lines)


def dump_document(frontmatter: Dict[str, Any], body: str) -> str:
    """Return a full markdown document with a frontmatter block + body."""
    fm = dump(frontmatter)
    body = body.rstrip("\n")
    parts = [FRONTMATTER_DELIM, fm, FRONTMATTER_DELIM, "", body, ""]
    return "\n".join(parts)


def split_frontmatter(text: str) -> Tuple[Optional[str], str]:
    """Split a document into (raw_frontmatter, body).

    Returns (None, text) when there is no leading frontmatter block.
    """
    # Tolerate a leading BOM / blank lines before the opening delimiter.
    stripped = text.lstrip("﻿")
    if not stripped.startswith(FRONTMATTER_DELIM):
        return None, text
    lines = stripped.splitlines()
    if not lines or lines[0].strip() != FRONTMATTER_DELIM:
        return None, text
    for i in range(1, len(lines)):
        if lines[i].strip() == FRONTMATTER_DELIM:
            fm = "\n".join(lines[1:i])
            body = "\n".join(lines[i + 1 :])
            return fm, body
    # Opening delimiter but never closed.
    return None, text


def _fallback_parse(fm: str) -> Dict[str, Any]:
    """Tiny YAML subset parser: `key: value`, block lists, `[a, b]` flow lists."""
    result: Dict[str, Any] = {}
    lines = fm.splitlines()
    i = 0
    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            i += 1
            continue
        if ":" not in line:
            i += 1
            continue
        key, _, rest = line.partition(":")
        key = key.strip()
        rest = rest.strip()
        if rest == "":
            # Possible block list on following indented `- item` lines.
            items: List[Any] = []
            j = i + 1
            while j < len(lines) and lines[j].strip().startswith("- "):
                items.append(_coerce(lines[j].strip()[2:].strip()))
                j += 1
            if items:
                result[key] = items
                i = j
                continue
            result[key] = ""
            i += 1
            continue
        if rest.startswith("[") and rest.endswith("]"):
            inner = rest[1:-1].strip()
            result[key] = [_coerce(p.strip()) for p in inner.split(",") if p.strip()] if inner else []
        else:
            result[key] = _coerce(rest)
        i += 1
    return result


def _coerce(token: str) -> Any:
    if len(token) >= 2 and token[0] == token[-1] and token[0] in "\"'":
        return token[1:-1]
    low = token.lower()
    if low in {"true", "false"}:
        return low == "true"
    if low in {"null", "~"}:
        return None
    return token


def parse(fm: Optional[str]) -> Dict[str, Any]:
    """Parse a raw frontmatter string into a dict (best effort)."""
    if not fm or not fm.strip():
        return {}
    if _pyyaml is not None:
        loaded = _pyyaml.safe_load(fm)
        return loaded if isinstance(loaded, dict) else {}
    return _fallback_parse(fm)
