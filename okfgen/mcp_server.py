"""okfgen as an MCP server.

Exposes okfgen's producers and consumers as Model Context Protocol tools so that
Claude Desktop, Claude Code, Cursor, and any MCP client can turn their own
sources into Open Knowledge Format bundles and reason over them — without
leaving the agent.

Run it:

    pip install "okfgen[mcp]"
    okfgen-mcp                     # stdio server

Register it (e.g. Claude Desktop `claude_desktop_config.json`):

    {
      "mcpServers": {
        "okfgen": { "command": "okfgen-mcp" }
      }
    }

The tool logic lives in plain module-level functions so this file imports fine
even when the optional `mcp` dependency is absent (tests, entry-point
resolution); the MCP server itself is only constructed in `create_server()`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .detect import build_source
from .model import write_bundle, slugify
from .sources import REGISTRY, SourceError

SERVER_NAME = "okfgen"


# --- tool implementations (framework-agnostic) ------------------------------

def generate_bundle(source: str, out_dir: Optional[str] = None,
                    source_type: Optional[str] = None) -> str:
    """Generate an OKF bundle from a source and write it to disk.

    `source` is a git URL, local path, `schema:FILE`, `bq:PROJECT`,
    `firebase:PROJECT`, `ckan:URL`, `socrata:URL`, or an https docs URL.
    `source_type` optionally forces the adapter (local, git, web, schema,
    bigquery, firebase, ckan, socrata). Returns the output path and a listing
    of the concepts produced.
    """
    try:
        src = build_source(source, kind=source_type, options={})
        bundle = src.build()
    except SourceError as exc:
        return f"error: {exc}"
    out = out_dir or f"{slugify(bundle.title)}-okf"
    stats = write_bundle(bundle, Path(out), overwrite=True)
    lines = [
        f"Generated OKF bundle at '{out}' — {stats['concepts']} concept(s), "
        f"source type: {src.kind}.",
        "",
        "Concepts:",
    ]
    for c in bundle.concepts[:100]:
        desc = f" — {c.description}" if c.description else ""
        lines.append(f"- [{c.type}] {c.title} ({c.path}){desc}")
    return "\n".join(lines)


def search_bundle(bundle_dir: str, query: str, limit: int = 10) -> str:
    """Full-text search a bundle. Returns ranked concepts with snippets."""
    from .searchindex import build_index
    try:
        hits = build_index(bundle_dir).search(query, limit=limit)
    except FileNotFoundError as exc:
        return f"error: {exc}"
    if not hits:
        return "No matches."
    out = []
    for h in hits:
        out.append(f"{h.score:.1f}  [{h.concept.type}] {h.concept.title} ({h.concept.path})")
        if h.snippet:
            out.append(f"     {h.snippet}")
    return "\n".join(out)


def ask_bundle(bundle_dir: str, question: str, top_k: int = 3) -> str:
    """Answer a question over a bundle via retrieval + link-following, with citations."""
    from .agent import ask
    try:
        return ask(bundle_dir, question, top_k=top_k).render()
    except FileNotFoundError as exc:
        return f"error: {exc}"


def validate_bundle_tool(bundle_dir: str) -> str:
    """Validate a bundle for OKF v0.1 conformance. Returns errors + warnings."""
    from .validate import validate_bundle
    result = validate_bundle(bundle_dir)
    lines = [
        f"{'CONFORMANT' if result.conformant else 'NON-CONFORMANT'}: "
        f"{result.concept_count} concept(s), {len(result.errors)} error(s), "
        f"{len(result.warnings)} warning(s)."
    ]
    for issue in result.errors[:50]:
        lines.append(f"  ERROR {issue.file}: {issue.message}")
    return "\n".join(lines)


def visualize_bundle(bundle_dir: str, out_path: Optional[str] = None) -> str:
    """Render a bundle to a self-contained interactive HTML graph. Returns the path."""
    from .visualize import visualize
    out = out_path or str(Path(bundle_dir) / "graph.html")
    try:
        visualize(bundle_dir, out)
    except FileNotFoundError as exc:
        return f"error: {exc}"
    return f"Wrote interactive graph to {out}"


def list_source_types() -> str:
    """List the source types okfgen can ingest."""
    return "okfgen source types: " + ", ".join(sorted(REGISTRY))


# --- MCP wiring -------------------------------------------------------------

def create_server():
    """Build the FastMCP server (imports the optional `mcp` dependency)."""
    try:
        from mcp.server.fastmcp import FastMCP
    except Exception as exc:  # pragma: no cover - only when mcp is absent
        raise SystemExit(
            "The MCP server needs the optional 'mcp' package. Install it with:\n"
            "    pip install 'okfgen[mcp]'\n"
            f"(import error: {exc})"
        )

    server = FastMCP(SERVER_NAME)
    server.tool(name="okfgen_generate")(generate_bundle)
    server.tool(name="okfgen_search")(search_bundle)
    server.tool(name="okfgen_ask")(ask_bundle)
    server.tool(name="okfgen_validate")(validate_bundle_tool)
    server.tool(name="okfgen_visualize")(visualize_bundle)
    server.tool(name="okfgen_list_source_types")(list_source_types)
    return server


def main() -> None:
    create_server().run()


if __name__ == "__main__":  # pragma: no cover
    main()
