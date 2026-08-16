"""Skill consumer: turn a source or bundle into an Agent Skill folder.

Produces a `SKILL.md` (frontmatter `name` + a triggering `description`, plus a
lean instructions body) alongside the OKF bundle as reference files. This
follows Agent Skill best practices: keep SKILL.md small and push depth into
bundled reference material that the body points into (progressive disclosure).

    okfgen skill ./my-repo -o my-skill      # straight from a source
    okfgen skill ./my-okf  -o my-skill      # from a bundle okfgen already made

Deterministic by default; `--llm` sharpens the `description` (the field that
most affects whether the skill triggers).
"""

from __future__ import annotations

import shutil
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from . import yamlfm
from .consumer import LoadedBundle, load_bundle
from .detect import build_source
from .model import slugify, write_bundle

REFERENCE_DIR = "reference"

# Tags too generic to be useful trigger keywords on their own.
_STOPWORD_TAGS = {"code", "documentation", "resource", "catalog", "project"}


@dataclass
class SkillResult:
    out_dir: Path
    name: str
    description: str
    concept_count: int
    reference_dir: Path
    notes: List[str] = field(default_factory=list)


def _is_bundle(path: str) -> bool:
    p = Path(path)
    return p.is_dir() and (p / "index.md").is_file()


def _obtain_bundle(input_value: str, reference_dir: Path,
                   kind: Optional[str], options: Optional[dict]) -> LoadedBundle:
    """Get an OKF bundle into `reference_dir`: copy an existing one, or generate."""
    reference_dir.mkdir(parents=True, exist_ok=True)
    if _is_bundle(input_value):
        shutil.copytree(input_value, reference_dir, dirs_exist_ok=True)
    else:
        source = build_source(input_value, kind=kind, options=options or {})
        bundle = source.build()
        write_bundle(bundle, reference_dir, overwrite=True)
    return load_bundle(str(reference_dir))


def _keywords(bundle: LoadedBundle, limit: int = 8) -> List[str]:
    """Distinctive trigger terms from tags + table/module names."""
    counter: Counter = Counter()
    for c in bundle.concepts:
        for t in c.tags:
            tl = t.strip().lower()
            if tl and tl not in _STOPWORD_TAGS:
                counter[tl] += 1
    # Prefer tags that appear on more than one concept, then singletons.
    ordered = [t for t, _ in counter.most_common()]
    # Add a few concept titles (table/module names) for specificity.
    titles = [c.title for c in bundle.concepts
              if c.type.lower() not in ("project", "data project", "dataset")][:6]
    out: List[str] = []
    for term in ordered + titles:
        if term and term not in out:
            out.append(term)
        if len(out) >= limit:
            break
    return out


def _overview(bundle: LoadedBundle):
    return bundle.get("overview.md") or (bundle.concepts[0] if bundle.concepts else None)


def synthesize_description(bundle: LoadedBundle, title: str, use_llm: bool = False) -> str:
    ov = _overview(bundle)
    core = (ov.description if ov and ov.description else f"Knowledge about {title}.").rstrip(".")
    kws = _keywords(bundle)
    kw_str = ", ".join(kws) if kws else title
    deterministic = (f"{title} — {core}. Use when answering questions about {kw_str}, "
                     f"or when working with this source's structure, schema, or concepts.")
    if use_llm:
        from .llm import write_skill_description
        polished = write_skill_description(title, core, kws)
        if polished:
            return polished
    return deterministic[:900]


def _render_skill_md(bundle: LoadedBundle, name: str, description: str) -> str:
    ov = _overview(bundle)
    title = ov.title if ov and ov.title else name

    lines: List[str] = [f"# {title}", ""]
    if ov and ov.description:
        lines += [ov.description, ""]
    lines += [
        "This skill packages an Open Knowledge Format (OKF) bundle describing "
        f"**{title}**. Use the reference files below to answer questions "
        "accurately and cite the concept you drew from.",
        "",
        "## How to use this skill",
        "",
        f"- Start with `{REFERENCE_DIR}/overview.md` for the big picture.",
        f"- Open a concept's file under `{REFERENCE_DIR}/` for detail before answering "
        "a specific question about it.",
        "- Every concept records provenance (`generated` = how it was produced, "
        "`sources` = what it derives from, with credibility signals like publisher, "
        "usage_count, and freshness). Prefer higher-credibility, fresher sources and "
        "say so when it matters.",
        "- Do not invent facts that are not in the reference files.",
        "",
        "## Contents",
        "",
    ]

    # Group concepts by type for a scannable map.
    by_type: Dict[str, List] = {}
    for c in sorted(bundle.concepts, key=lambda x: x.path):
        by_type.setdefault(c.type, []).append(c)

    total = len(bundle.concepts)
    shown = 0
    for ctype in sorted(by_type):
        lines.append(f"### {ctype}")
        lines.append("")
        for c in by_type[ctype]:
            if shown >= 80:
                break
            desc = f" — {c.description}" if c.description else ""
            lines.append(f"- **{c.title}** (`{REFERENCE_DIR}/{c.path}`){desc}")
            shown += 1
        lines.append("")
    if shown < total:
        lines.append(f"_…and {total - shown} more concept(s) under `{REFERENCE_DIR}/`._")
        lines.append("")

    body = "\n".join(lines).rstrip("\n") + "\n"
    front = yamlfm.dump({"name": name, "description": description})
    return f"{yamlfm.FRONTMATTER_DELIM}\n{front}\n{yamlfm.FRONTMATTER_DELIM}\n\n{body}"


def build_skill(input_value: str, out_dir: str, *, name: Optional[str] = None,
                kind: Optional[str] = None, use_llm: bool = False,
                options: Optional[dict] = None, overwrite: bool = False) -> SkillResult:
    out = Path(out_dir)
    if out.exists() and any(out.iterdir()) and not overwrite:
        raise FileExistsError(f"Output directory {out} is not empty. Use --overwrite.")
    reference_dir = out / REFERENCE_DIR

    bundle = _obtain_bundle(input_value, reference_dir, kind, options)
    if not bundle.concepts:
        raise ValueError("The source produced no concepts; cannot build a skill.")

    ov = _overview(bundle)
    title = (ov.title if ov and ov.title else Path(input_value).name) or "knowledge"
    skill_name = slugify(name or title)
    description = synthesize_description(bundle, title, use_llm=use_llm)

    (out / "SKILL.md").write_text(_render_skill_md(bundle, skill_name, description),
                                  encoding="utf-8")

    return SkillResult(
        out_dir=out, name=skill_name, description=description,
        concept_count=len(bundle.concepts), reference_dir=reference_dir,
    )
