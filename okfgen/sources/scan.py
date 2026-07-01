"""Deterministic filesystem scanning shared by the local-dir and git sources.

Extracts a project overview, per-directory summaries, documentation concepts,
and a dependency inventory from a directory tree. No LLM, no invented
"insight" — just structured facts pulled straight from the files.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..model import Bundle, Concept, LogEntry, slugify, utcnow_iso

# Directories that never carry useful knowledge for a bundle.
IGNORE_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "__pycache__", ".venv", "venv",
    "env", ".env", "dist", "build", ".next", ".nuxt", "target", ".idea",
    ".vscode", ".pytest_cache", ".mypy_cache", ".ruff_cache", "coverage",
    ".gradle", "vendor", ".terraform", "bin", "obj", ".cache", "__snapshots__",
}
IGNORE_FILE_SUFFIXES = {
    ".lock", ".log", ".map", ".min.js", ".min.css", ".pyc", ".pyo", ".class",
    ".o", ".so", ".dll", ".dylib", ".exe", ".bin", ".png", ".jpg", ".jpeg",
    ".gif", ".ico", ".pdf", ".zip", ".gz", ".tar", ".woff", ".woff2", ".ttf",
}

# Map extensions to human language names, used for the tech summary.
LANG_BY_EXT = {
    ".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript", ".ts": "TypeScript",
    ".tsx": "TypeScript", ".go": "Go", ".rs": "Rust", ".java": "Java",
    ".kt": "Kotlin", ".rb": "Ruby", ".php": "PHP", ".c": "C", ".h": "C",
    ".cpp": "C++", ".cc": "C++", ".cs": "C#", ".swift": "Swift", ".scala": "Scala",
    ".sh": "Shell", ".sql": "SQL", ".r": "R", ".m": "Objective-C", ".dart": "Dart",
    ".ex": "Elixir", ".clj": "Clojure", ".hs": "Haskell", ".lua": "Lua",
}

README_NAMES = ["README.md", "README.rst", "README.txt", "README", "readme.md"]
DOC_SUFFIXES = {".md", ".markdown", ".mdx", ".rst"}


def _iter_files(root: Path):
    """Yield files under root, pruning ignored directories."""
    for path in sorted(root.rglob("*")):
        rel_parts = path.relative_to(root).parts
        if any(part in IGNORE_DIRS for part in rel_parts):
            continue
        if path.is_file():
            yield path


def _read_text(path: Path, limit: int = 200_000) -> Optional[str]:
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if b"\x00" in data[:4096]:  # binary
        return None
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = data.decode("latin-1")
        except UnicodeDecodeError:
            return None
    return text[:limit]


def _first_heading(md: str) -> Optional[str]:
    for line in md.splitlines():
        line = line.strip()
        if line.startswith("#"):
            return line.lstrip("#").strip() or None
        if line:
            # rST style: a title underlined by === on the next line is common,
            # but the first non-empty line is a reasonable title fallback.
            return line[:120]
    return None


def _find_readme(root: Path) -> Optional[Path]:
    for name in README_NAMES:
        p = root / name
        if p.is_file():
            return p
    # Case-insensitive fallback.
    for child in root.iterdir():
        if child.is_file() and child.name.lower().startswith("readme"):
            return child
    return None


# --- lightweight definition extraction per language -------------------------

_DEF_PATTERNS = {
    "Python": [
        (r"^\s*def\s+([a-zA-Z_]\w*)\s*\(", "function"),
        (r"^\s*class\s+([a-zA-Z_]\w*)", "class"),
    ],
    "JavaScript": [
        (r"^\s*(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z_$][\w$]*)", "function"),
        (r"^\s*(?:export\s+)?class\s+([a-zA-Z_$][\w$]*)", "class"),
    ],
    "TypeScript": [
        (r"^\s*(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z_$][\w$]*)", "function"),
        (r"^\s*(?:export\s+)?(?:abstract\s+)?class\s+([a-zA-Z_$][\w$]*)", "class"),
        (r"^\s*(?:export\s+)?interface\s+([a-zA-Z_$][\w$]*)", "interface"),
    ],
    "Go": [
        (r"^\s*func\s+(?:\([^)]*\)\s*)?([A-Za-z_]\w*)\s*\(", "function"),
        (r"^\s*type\s+([A-Za-z_]\w*)\s+struct", "type"),
    ],
    "Rust": [
        (r"^\s*(?:pub\s+)?fn\s+([a-zA-Z_]\w*)", "function"),
        (r"^\s*(?:pub\s+)?struct\s+([a-zA-Z_]\w*)", "struct"),
    ],
    "Java": [
        (r"^\s*(?:public|private|protected).*\bclass\s+([A-Za-z_]\w*)", "class"),
    ],
}


def _extract_defs(text: str, lang: str, max_defs: int = 40) -> List[Tuple[str, str]]:
    patterns = _DEF_PATTERNS.get(lang)
    if not patterns:
        return []
    out: List[Tuple[str, str]] = []
    for line in text.splitlines():
        for pat, kind in patterns:
            m = re.match(pat, line)
            if m:
                out.append((m.group(1), kind))
                break
        if len(out) >= max_defs:
            break
    return out


# --- dependency manifest parsing --------------------------------------------

def _parse_dependencies(root: Path) -> List[Tuple[str, List[str]]]:
    """Return list of (manifest_name, [dependency strings])."""
    found: List[Tuple[str, List[str]]] = []

    pkg = root / "package.json"
    if pkg.is_file():
        text = _read_text(pkg) or "{}"
        try:
            data = json.loads(text)
            deps = list((data.get("dependencies") or {}).keys())
            deps += list((data.get("devDependencies") or {}).keys())
            if deps:
                found.append(("package.json (npm)", sorted(set(deps))))
        except json.JSONDecodeError:
            pass

    req = root / "requirements.txt"
    if req.is_file():
        text = _read_text(req) or ""
        deps = [
            re.split(r"[<>=!~ \[]", ln.strip())[0]
            for ln in text.splitlines()
            if ln.strip() and not ln.strip().startswith("#")
        ]
        deps = [d for d in deps if d]
        if deps:
            found.append(("requirements.txt (pip)", deps))

    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        text = _read_text(pyproject) or ""
        # Deliberately shallow TOML read to avoid a tomllib dependency on 3.9/3.10.
        deps = re.findall(r'["\']([A-Za-z0-9_.\-]+)\s*(?:[<>=!~;\[].*)?["\']', text)
        # Filter obvious noise by only keeping names that look like packages.
        deps = [d for d in dict.fromkeys(deps) if re.match(r"^[A-Za-z][A-Za-z0-9_.\-]+$", d)]
        if deps:
            found.append(("pyproject.toml", deps[:60]))

    gomod = root / "go.mod"
    if gomod.is_file():
        text = _read_text(gomod) or ""
        deps = re.findall(r"^\s+([^\s]+)\s+v[0-9]", text, re.MULTILINE)
        if deps:
            found.append(("go.mod", sorted(set(deps))))

    cargo = root / "Cargo.toml"
    if cargo.is_file():
        text = _read_text(cargo) or ""
        m = re.search(r"\[dependencies\](.*?)(?:\n\[|\Z)", text, re.DOTALL)
        if m:
            deps = re.findall(r"^\s*([A-Za-z0-9_\-]+)\s*=", m.group(1), re.MULTILINE)
            if deps:
                found.append(("Cargo.toml", deps))

    return found


def scan_directory(
    root: Path,
    title: str,
    source_label: str,
    resource_base: str = "",
    max_code_files_per_dir: int = 200,
) -> Bundle:
    """Scan a directory tree into an OKF bundle."""
    root = Path(root)
    bundle = Bundle(title=title, source=source_label)

    files = list(_iter_files(root))

    # --- Project overview concept from the README ---------------------------
    readme = _find_readme(root)
    overview_desc = f"Overview of {title}."
    overview_body_parts: List[str] = []
    if readme is not None:
        rd = _read_text(readme) or ""
        heading = _first_heading(rd)
        if heading:
            overview_desc = heading[:200]
        overview_body_parts.append(rd.strip())
    else:
        overview_body_parts.append(f"No README was found in `{title}`.")

    # Language / file-type summary.
    lang_counts: Dict[str, int] = {}
    ext_counts: Dict[str, int] = {}
    for f in files:
        ext = f.suffix.lower()
        ext_counts[ext] = ext_counts.get(ext, 0) + 1
        lang = LANG_BY_EXT.get(ext)
        if lang:
            lang_counts[lang] = lang_counts.get(lang, 0) + 1

    tech_lines = ["", "# Schema", "", f"- **Files scanned:** {len(files)}"]
    if lang_counts:
        langs = ", ".join(
            f"{lang} ({n})" for lang, n in sorted(lang_counts.items(), key=lambda kv: -kv[1])
        )
        tech_lines.append(f"- **Languages:** {langs}")
    top_dirs = sorted({f.relative_to(root).parts[0] for f in files if len(f.relative_to(root).parts) > 1})
    if top_dirs:
        tech_lines.append(f"- **Top-level directories:** {', '.join(top_dirs)}")

    bundle.add(Concept(
        path="overview.md",
        type="Project",
        title=title,
        description=overview_desc,
        resource=resource_base or source_label,
        tags=sorted(lang_counts.keys()) or ["project"],
        body="\n".join(overview_body_parts + tech_lines).strip(),
    ))

    # --- Dependency inventory ----------------------------------------------
    deps = _parse_dependencies(root)
    if deps:
        lines = []
        for manifest, items in deps:
            lines.append(f"## {manifest}")
            lines.append("")
            for d in items:
                lines.append(f"- `{d}`")
            lines.append("")
        bundle.add(Concept(
            path="dependencies.md",
            type="Dependencies",
            title=f"{title} — Dependencies",
            description="Declared third-party dependencies parsed from manifest files.",
            tags=["dependencies"],
            body="# Schema\n\n" + "\n".join(lines).strip(),
        ))

    # --- Documentation concepts (markdown/rst files, excluding the README) --
    for f in files:
        if f.suffix.lower() not in DOC_SUFFIXES:
            continue
        if readme is not None and f == readme:
            continue
        rel = f.relative_to(root).as_posix()
        text = _read_text(f) or ""
        heading = _first_heading(text) or f.stem.replace("-", " ").replace("_", " ").title()
        slug = slugify(f.stem)
        path = bundle.unique_path("docs", slug)
        bundle.add(Concept(
            path=path,
            type="Document",
            title=heading,
            description=f"Documentation file `{rel}`.",
            resource=(resource_base.rstrip("/") + "/" + rel) if resource_base else rel,
            tags=["documentation"],
            body=text.strip(),
        ))

    # --- Per-directory code concepts ---------------------------------------
    by_dir: Dict[str, List[Path]] = {}
    for f in files:
        if f.suffix.lower() in IGNORE_FILE_SUFFIXES:
            continue
        if f.suffix.lower() not in LANG_BY_EXT:
            continue
        rel = f.relative_to(root)
        parent = rel.parent.as_posix()
        parent = "." if parent == "" else parent
        by_dir.setdefault(parent, []).append(f)

    for directory in sorted(by_dir):
        code_files = sorted(by_dir[directory])[:max_code_files_per_dir]
        if not code_files:
            continue
        dir_label = directory if directory != "." else "(root)"
        lines = ["# Schema", ""]
        for cf in code_files:
            rel = cf.relative_to(root).as_posix()
            lang = LANG_BY_EXT.get(cf.suffix.lower(), "")
            text = _read_text(cf) or ""
            defs = _extract_defs(text, lang)
            lines.append(f"### `{rel}`")
            if defs:
                for name, kind in defs:
                    lines.append(f"- {kind} `{name}`")
            else:
                nlines = text.count("\n") + 1
                lines.append(f"- {lang} source ({nlines} lines)")
            lines.append("")

        slug = slugify(directory.replace("/", "-")) if directory != "." else "root"
        path = bundle.unique_path("modules", slug)
        primary_langs = sorted({LANG_BY_EXT[cf.suffix.lower()] for cf in code_files})
        bundle.add(Concept(
            path=path,
            type="Code Module",
            title=f"{dir_label}",
            description=f"Source directory `{dir_label}` — {len(code_files)} file(s).",
            resource=(resource_base.rstrip("/") + "/" + directory) if resource_base and directory != "." else directory,
            tags=["code"] + primary_langs,
            body="\n".join(lines).strip(),
        ))

    bundle.log_entries.append(LogEntry(
        date=utcnow_iso()[:10],
        action="Generated",
        text=f"Bundle synthesized from {source_label} by okfgen ({len(bundle.concepts)} concepts).",
    ))
    return bundle
