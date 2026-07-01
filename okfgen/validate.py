"""OKF v0.1 conformance validator.

Implements the SPEC.md conformance rules:
  * every non-reserved `.md` file has parseable YAML frontmatter,
  * every frontmatter block has a non-empty `type` field.

Everything else (missing optional fields, unknown types, unknown keys, broken
cross-links) is reported as a WARNING, never an error — consumers "MUST NOT
reject a bundle" for those.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List
from urllib.parse import urlparse

from .model import RESERVED_FILENAMES
from . import yamlfm

RECOMMENDED_FIELDS = ("title", "description", "resource", "tags", "timestamp")


@dataclass
class Issue:
    level: str  # "error" | "warning"
    file: str
    message: str


@dataclass
class ValidationResult:
    bundle_dir: str
    issues: List[Issue] = field(default_factory=list)
    concept_count: int = 0

    @property
    def errors(self) -> List[Issue]:
        return [i for i in self.issues if i.level == "error"]

    @property
    def warnings(self) -> List[Issue]:
        return [i for i in self.issues if i.level == "warning"]

    @property
    def conformant(self) -> bool:
        return not self.errors


def _iter_md(root: Path):
    for p in sorted(root.rglob("*.md")):
        if p.is_file():
            yield p


def _link_targets(body: str) -> List[str]:
    """Extract markdown link targets (very small parser; good enough)."""
    import re
    return [m.group(1) for m in re.finditer(r"\]\(([^)]+)\)", body)]


def validate_bundle(bundle_dir: str) -> ValidationResult:
    root = Path(bundle_dir)
    result = ValidationResult(bundle_dir=str(root))

    if not root.is_dir():
        result.issues.append(Issue("error", str(root), "Bundle directory does not exist."))
        return result

    md_files = list(_iter_md(root))
    if not md_files:
        result.issues.append(Issue("warning", str(root), "No markdown files found in bundle."))

    all_rel = {p.relative_to(root).as_posix() for p in md_files}

    for path in md_files:
        rel = path.relative_to(root).as_posix()
        is_reserved = path.name in RESERVED_FILENAMES
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            result.issues.append(Issue("error", rel, f"Could not read file: {exc}"))
            continue

        raw_fm, body = yamlfm.split_frontmatter(text)

        if is_reserved:
            # Reserved files (index.md, log.md) need not be concepts. Root
            # index.md MAY carry frontmatter with okf_version — that's fine.
            continue

        if raw_fm is None:
            result.issues.append(Issue(
                "error", rel,
                "Missing YAML frontmatter block (concept documents must start with '---').",
            ))
            continue

        try:
            fm = yamlfm.parse(raw_fm)
        except Exception as exc:
            result.issues.append(Issue("error", rel, f"Frontmatter is not parseable YAML: {exc}"))
            continue

        if not isinstance(fm, dict) or not str(fm.get("type", "")).strip():
            result.issues.append(Issue(
                "error", rel, "Frontmatter is missing a non-empty 'type' field.",
            ))
            continue

        result.concept_count += 1

        # --- warnings (never fatal) ----------------------------------------
        for f in RECOMMENDED_FIELDS:
            if f not in fm:
                result.issues.append(Issue("warning", rel, f"Missing recommended field '{f}'."))

        for target in _link_targets(body):
            scheme = urlparse(target).scheme
            if scheme:  # external URL — not our job to resolve
                continue
            if target.startswith("#"):
                continue
            if target.startswith("/"):
                resolved = target.lstrip("/")
            else:
                resolved = (Path(rel).parent / target).as_posix()
            resolved = resolved.split("#")[0]
            if resolved and resolved not in all_rel and not (root / resolved).exists():
                result.issues.append(Issue("warning", rel, f"Broken cross-link: {target}"))

    return result
