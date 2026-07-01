"""Auto-detect which source adapter handles a given input string."""

from __future__ import annotations

from typing import Optional

from .sources import REGISTRY, Source, SourceError

# Priority order for auto-detection. Prefixed cloud sources win first (they use
# unambiguous `bq:` / `firebase:` prefixes), then local dirs, then git, then web.
_DETECT_ORDER = ["bigquery", "firebase", "ckan", "schema", "local", "git", "web"]


def build_source(input_value: str, kind: Optional[str] = None, options: Optional[dict] = None) -> Source:
    options = options or {}
    if kind:
        cls = REGISTRY.get(kind)
        if cls is None:
            raise SourceError(
                f"Unknown source type '{kind}'. Choose from: {', '.join(sorted(REGISTRY))}."
            )
        return cls(input_value, options)

    for name in _DETECT_ORDER:
        cls = REGISTRY[name]
        if cls.matches(input_value):
            return cls(input_value, options)

    raise SourceError(
        f"Could not auto-detect the source type for '{input_value}'.\n"
        "Pass --type explicitly (local, git, web, bigquery, firebase), or prefix "
        "cloud inputs (e.g. bq:my-project, firebase:my-project)."
    )
