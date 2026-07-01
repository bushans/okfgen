"""Consumer-side bundle loader + link graph.

Every consumer (visualizer, search index, reasoning agent, enrichment agent)
reads a bundle back into memory through `load_bundle()`. This is the read half
of the producer/consumer split the OKF spec is built around: consumers depend
only on markdown + frontmatter, never on producer tooling.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

from . import yamlfm
from .model import RESERVED_FILENAMES

_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")


@dataclass
class LoadedConcept:
    path: str  # bundle-relative POSIX path
    type: str
    title: str
    description: str
    resource: str
    tags: List[str]
    timestamp: str
    frontmatter: Dict
    body: str
    # Resolved bundle-relative link targets that point at other concepts.
    links: List[str] = field(default_factory=list)
    # External (http) links found in the body, kept as citations.
    external_links: List[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return f"{self.title}\n{self.description}\n{' '.join(self.tags)}\n{self.body}"


@dataclass
class LoadedBundle:
    directory: Path
    concepts: List[LoadedConcept]
    okf_version: str = ""

    def __post_init__(self) -> None:
        self.by_path: Dict[str, LoadedConcept] = {c.path: c for c in self.concepts}

    def get(self, path: str) -> Optional[LoadedConcept]:
        return self.by_path.get(path)

    def edges(self) -> List[Tuple[str, str]]:
        """Directed (source_path -> target_path) links between concepts."""
        out: List[Tuple[str, str]] = []
        for c in self.concepts:
            for target in c.links:
                if target in self.by_path and target != c.path:
                    out.append((c.path, target))
        return out

    def backlinks(self) -> Dict[str, List[str]]:
        """Reverse index: concept path -> list of paths that link TO it."""
        rev: Dict[str, List[str]] = {c.path: [] for c in self.concepts}
        for src, dst in self.edges():
            rev[dst].append(src)
        return rev

    def types(self) -> List[str]:
        return sorted({c.type for c in self.concepts})


def _resolve_link(from_path: str, target: str) -> Optional[str]:
    """Resolve a markdown link target to a bundle-relative path, or None if external."""
    target = target.strip()
    if not target or target.startswith("#"):
        return None
    if urlparse(target).scheme:  # http(s)://, mailto:, etc.
        return None
    target = target.split("#")[0]
    if not target:
        return None
    if target.startswith("/"):
        resolved = target.lstrip("/")
    else:
        resolved = (Path(from_path).parent / target).as_posix()
    # Normalize ../ segments.
    parts: List[str] = []
    for seg in resolved.split("/"):
        if seg in ("", "."):
            continue
        if seg == "..":
            if parts:
                parts.pop()
            continue
        parts.append(seg)
    return "/".join(parts)


def load_bundle(bundle_dir: str) -> LoadedBundle:
    root = Path(bundle_dir)
    if not root.is_dir():
        raise FileNotFoundError(f"Bundle directory not found: {root}")

    concepts: List[LoadedConcept] = []
    okf_version = ""

    for path in sorted(root.rglob("*.md")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        raw_fm, body = yamlfm.split_frontmatter(text)
        fm = yamlfm.parse(raw_fm) if raw_fm else {}

        if path.name in RESERVED_FILENAMES:
            if path.name == "index.md" and isinstance(fm.get("okf_version"), (str, int, float)):
                okf_version = str(fm.get("okf_version"))
            continue  # reserved files are not concepts

        ctype = str(fm.get("type", "")).strip()
        if not ctype:
            continue  # not a conformant concept; skip for consumer purposes

        internal: List[str] = []
        external: List[str] = []
        for _label, target in _LINK_RE.findall(body):
            if urlparse(target.strip()).scheme in ("http", "https"):
                external.append(target.strip())
                continue
            resolved = _resolve_link(rel, target)
            if resolved:
                internal.append(resolved)

        tags = fm.get("tags") or []
        if isinstance(tags, str):
            tags = [tags]

        concepts.append(LoadedConcept(
            path=rel,
            type=ctype,
            title=str(fm.get("title", rel)),
            description=str(fm.get("description", "")),
            resource=str(fm.get("resource", "")),
            tags=[str(t) for t in tags],
            timestamp=str(fm.get("timestamp", "")),
            frontmatter=fm,
            body=body.strip(),
            links=list(dict.fromkeys(internal)),
            external_links=list(dict.fromkeys(external)),
        ))

    return LoadedBundle(directory=root, concepts=concepts, okf_version=okf_version)
