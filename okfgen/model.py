"""Core OKF data model: Concept, Bundle, and the on-disk writer."""

from __future__ import annotations

import datetime as _dt
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import OKF_VERSION
from . import yamlfm

RESERVED_FILENAMES = {"index.md", "log.md"}

# Conventional body headings that carry meaning in OKF (SPEC.md).
CONVENTIONAL_HEADINGS = ("Schema", "Examples", "Citations")


def utcnow_iso() -> str:
    # Honor a fixed timestamp so committed sample bundles are reproducible.
    override = __import__("os").environ.get("OKFGEN_TIMESTAMP")
    if override:
        return override
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


def slugify(text: str, fallback: str = "concept") -> str:
    """Produce a filesystem- and URL-safe slug from arbitrary text."""
    text = (text or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text or fallback


@dataclass
class Concept:
    """A single OKF concept document.

    `path` is bundle-relative (POSIX, e.g. "tables/customers.md"). `type` is the
    only required frontmatter field per the spec; everything else is recommended.
    """

    path: str
    type: str
    title: Optional[str] = None
    description: Optional[str] = None
    resource: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    timestamp: Optional[str] = None
    body: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)

    def frontmatter(self) -> Dict[str, Any]:
        fm: Dict[str, Any] = {"type": self.type}
        if self.title:
            fm["title"] = self.title
        if self.description:
            fm["description"] = self.description
        if self.resource:
            fm["resource"] = self.resource
        if self.tags:
            fm["tags"] = list(self.tags)
        fm["timestamp"] = self.timestamp or utcnow_iso()
        for k, v in self.extra.items():
            if k not in fm:
                fm[k] = v
        return fm

    def render(self) -> str:
        return yamlfm.dump_document(self.frontmatter(), self.body or "")


@dataclass
class LogEntry:
    date: str  # ISO date, e.g. "2026-07-01"
    text: str
    action: Optional[str] = None  # optional bold prefix word


@dataclass
class Bundle:
    """An in-memory OKF bundle ready to be written to disk."""

    title: str
    description: str = ""
    concepts: List[Concept] = field(default_factory=list)
    log_entries: List[LogEntry] = field(default_factory=list)
    okf_version: str = OKF_VERSION
    source: str = ""

    def add(self, concept: Concept) -> Concept:
        self.concepts.append(concept)
        return concept

    def used_paths(self) -> set:
        return {c.path for c in self.concepts}

    def unique_path(self, directory: str, slug: str) -> str:
        """Return a bundle-relative .md path that doesn't collide."""
        base = slug or "concept"
        directory = directory.strip("/")
        used = self.used_paths()
        n = 0
        while True:
            name = base if n == 0 else f"{base}-{n}"
            path = f"{directory}/{name}.md" if directory else f"{name}.md"
            if path not in used and Path(path).name not in RESERVED_FILENAMES:
                return path
            n += 1


def render_root_index(bundle: Bundle) -> str:
    """Root index.md: a small frontmatter block declaring okf_version + listing."""
    fm = yamlfm.dump({"okf_version": bundle.okf_version})
    lines: List[str] = [yamlfm.FRONTMATTER_DELIM, fm, yamlfm.FRONTMATTER_DELIM, ""]
    lines.append(f"# {bundle.title}")
    lines.append("")
    if bundle.description:
        lines.append(bundle.description)
        lines.append("")
    if bundle.source:
        lines.append(f"_Source: {bundle.source}_")
        lines.append("")

    # Group concepts by their top-level directory for progressive disclosure.
    groups: Dict[str, List[Concept]] = {}
    for c in sorted(bundle.concepts, key=lambda x: x.path):
        top = c.path.split("/")[0] if "/" in c.path else "."
        groups.setdefault(top, []).append(c)

    for group in sorted(groups):
        heading = "Root" if group == "." else group.replace("-", " ").title()
        lines.append(f"## {heading}")
        lines.append("")
        for c in groups[group]:
            label = c.title or c.path
            desc = f" — {c.description}" if c.description else ""
            lines.append(f"- [{label}](/{c.path}){desc}")
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def render_log(bundle: Bundle) -> str:
    """log.md: entries grouped by ISO date, newest first."""
    lines: List[str] = ["# Log", ""]
    by_date: Dict[str, List[LogEntry]] = {}
    for e in bundle.log_entries:
        by_date.setdefault(e.date, []).append(e)
    for date in sorted(by_date, reverse=True):
        lines.append(f"## {date}")
        lines.append("")
        for e in by_date[date]:
            prefix = f"**{e.action}** " if e.action else ""
            lines.append(f"- {prefix}{e.text}")
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def write_bundle(bundle: Bundle, out_dir: Path, overwrite: bool = False) -> Dict[str, int]:
    """Write the bundle to disk. Returns simple stats."""
    out_dir = Path(out_dir)
    if out_dir.exists() and any(out_dir.iterdir()) and not overwrite:
        raise FileExistsError(
            f"Output directory {out_dir} is not empty. Use --overwrite to replace it."
        )
    out_dir.mkdir(parents=True, exist_ok=True)

    written = 0
    for c in bundle.concepts:
        dest = out_dir / Path(c.path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(c.render(), encoding="utf-8")
        written += 1

    (out_dir / "index.md").write_text(render_root_index(bundle), encoding="utf-8")
    if bundle.log_entries:
        (out_dir / "log.md").write_text(render_log(bundle), encoding="utf-8")

    return {"concepts": written, "files": written + 1 + (1 if bundle.log_entries else 0)}
