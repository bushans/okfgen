"""Enrichment agent (pass 2).

Producers draft concepts (pass 1). This agent enriches a drafted bundle the way
the OKF blog's reference agent does — deterministically inferring **join paths**
between tables from foreign-key naming, wiring **backlinks** so the graph is
navigable both ways, and (optionally, with `--llm`) rewriting descriptions from
authoritative context. Everything it adds is a plain markdown link or section,
so the output stays conformant and diffable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import yamlfm
from .consumer import LoadedBundle, LoadedConcept, load_bundle
from .model import utcnow_iso

_JOINS_HEADING = "# Joins"
_RELATED_HEADING = "# Related"

# Concept types we treat as join-able relations.
_TABLE_TYPES = ("table", "dataset", "collection")

_COL_RE = re.compile(r"^\s*\|\s*`?([A-Za-z_][A-Za-z0-9_]*)`?\s*\|")


@dataclass
class EnrichReport:
    joins_added: int = 0
    backlinks_added: int = 0
    descriptions_rewritten: int = 0
    concepts_changed: int = 0
    notes: List[str] = field(default_factory=list)


def _is_tableish(c: LoadedConcept) -> bool:
    t = c.type.lower()
    return any(k in t for k in _TABLE_TYPES)


def _singular(name: str) -> str:
    if name.endswith("ies"):
        return name[:-3] + "y"
    if name.endswith("ses"):
        return name[:-2]
    if name.endswith("s") and not name.endswith("ss"):
        return name[:-1]
    return name


def _base_name(title: str) -> str:
    """`sales.orders` -> `orders`; used to match FK targets by table name."""
    base = title.split(".")[-1].strip().lower()
    return re.sub(r"[^a-z0-9_]", "", base)


def _columns(body: str) -> List[str]:
    cols: List[str] = []
    in_schema = False
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            in_schema = stripped.lower().startswith("# schema")
            continue
        if not in_schema:
            continue
        m = _COL_RE.match(line)
        if m:
            name = m.group(1).lower()
            if name in ("column", "field"):  # header row
                continue
            cols.append(name)
    return cols


def _build_table_index(bundle: LoadedBundle) -> Dict[str, LoadedConcept]:
    """Map singular table base-names -> concept, for FK resolution."""
    idx: Dict[str, LoadedConcept] = {}
    for c in bundle.concepts:
        if not _is_tableish(c):
            continue
        base = _base_name(c.title)
        if not base:
            continue
        idx.setdefault(_singular(base), c)
        idx.setdefault(base, c)
    return idx


def _infer_joins(concept: LoadedConcept, table_index: Dict[str, LoadedConcept]) -> List[Tuple[str, LoadedConcept]]:
    """Return (column, target_concept) join pairs inferred from FK naming."""
    joins: List[Tuple[str, LoadedConcept]] = []
    self_base = _singular(_base_name(concept.title))
    seen = set()
    for col in _columns(concept.body):
        if not col.endswith("_id") and col != "id":
            continue
        if col == "id":
            continue
        ref = _singular(col[:-3])  # drop `_id`
        if not ref or ref == self_base:
            continue
        target = table_index.get(ref)
        if target and target.path != concept.path and target.path not in seen:
            joins.append((col, target))
            seen.add(target.path)
    return joins


def _rel_link(from_path: str, to_path: str) -> str:
    """Bundle-absolute link (always valid from any depth)."""
    return f"/{to_path}"


def _strip_section(body: str, heading: str) -> str:
    """Remove a previously-generated section so enrichment is idempotent."""
    lines = body.splitlines()
    out: List[str] = []
    skipping = False
    for line in lines:
        if line.strip() == heading:
            skipping = True
            continue
        if skipping and line.startswith("# ") and line.strip() != heading:
            skipping = False
        if not skipping:
            out.append(line)
    return "\n".join(out).rstrip("\n")


def enrich_bundle(
    bundle_dir: str,
    out_dir: Optional[str] = None,
    use_llm: bool = False,
    doc_context: str = "",
) -> EnrichReport:
    bundle = load_bundle(bundle_dir)
    report = EnrichReport()
    table_index = _build_table_index(bundle)

    # --- Pass 2a: infer join paths and inject them as links --------------
    inferred: Dict[str, List[Tuple[str, LoadedConcept]]] = {}
    for c in bundle.concepts:
        if not _is_tableish(c):
            continue
        joins = _infer_joins(c, table_index)
        if joins:
            inferred[c.path] = joins

    # Recompute a link graph that INCLUDES the inferred joins, for backlinks.
    augmented_links: Dict[str, List[str]] = {c.path: list(c.links) for c in bundle.concepts}
    for path, joins in inferred.items():
        for _col, target in joins:
            if target.path not in augmented_links[path]:
                augmented_links[path].append(target.path)

    backlinks: Dict[str, List[str]] = {c.path: [] for c in bundle.concepts}
    for src, targets in augmented_links.items():
        for dst in targets:
            if dst in backlinks and src not in backlinks[dst]:
                backlinks[dst].append(src)

    out_root = Path(out_dir) if out_dir else bundle.directory
    if out_dir and Path(out_dir).resolve() != bundle.directory.resolve():
        _copy_tree(bundle.directory, Path(out_dir))

    for c in bundle.concepts:
        body = _strip_section(_strip_section(c.body, _JOINS_HEADING), _RELATED_HEADING)
        changed = False
        fm = dict(c.frontmatter)

        # Optional LLM description rewrite.
        if use_llm:
            from .llm import enrich_description
            new_desc = enrich_description(c.title, c.type, body, doc_context)
            if new_desc and new_desc != c.description:
                fm["description"] = new_desc
                report.descriptions_rewritten += 1
                changed = True

        # Joins section.
        joins = inferred.get(c.path, [])
        if joins:
            lines = [_JOINS_HEADING, ""]
            for col, target in joins:
                lines.append(f"- `{col}` → [{target.title}]({_rel_link(c.path, target.path)})")
            body = body.rstrip("\n") + "\n\n" + "\n".join(lines)
            report.joins_added += len(joins)
            changed = True

        # Related (backlinks) section — incoming links not already outgoing.
        incoming = [p for p in backlinks.get(c.path, []) if p not in augmented_links[c.path]]
        if incoming:
            lines = [_RELATED_HEADING, "", "Referenced by:"]
            for src_path in sorted(incoming):
                src = bundle.get(src_path)
                if src:
                    lines.append(f"- [{src.title}]({_rel_link(c.path, src.path)})")
            body = body.rstrip("\n") + "\n\n" + "\n".join(lines)
            report.backlinks_added += len(incoming)
            changed = True

        if changed:
            report.concepts_changed += 1
            dest = out_root / c.path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(yamlfm.dump_document(fm, body), encoding="utf-8")

    _append_log(out_root, report)
    report.notes.append(f"table concepts indexed: {len(table_index)}")
    return report


def _copy_tree(src: Path, dst: Path) -> None:
    import shutil
    if dst.exists() and any(dst.iterdir()):
        raise FileExistsError(f"Output directory {dst} is not empty.")
    shutil.copytree(src, dst, dirs_exist_ok=True)


def _append_log(root: Path, report: EnrichReport) -> None:
    log_path = root / "log.md"
    date = utcnow_iso()[:10]
    entry = (
        f"- **Enriched** okfgen pass 2: {report.joins_added} join(s), "
        f"{report.backlinks_added} backlink(s) added across "
        f"{report.concepts_changed} concept(s)."
    )
    if log_path.exists():
        text = log_path.read_text(encoding="utf-8").rstrip("\n")
        if f"## {date}" in text:
            text = text.replace(f"## {date}\n", f"## {date}\n\n{entry}\n", 1)
        else:
            text = text.replace("# Log\n", f"# Log\n\n## {date}\n\n{entry}\n", 1)
        log_path.write_text(text + "\n", encoding="utf-8")
    else:
        log_path.write_text(f"# Log\n\n## {date}\n\n{entry}\n", encoding="utf-8")
