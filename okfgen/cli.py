"""okfgen command-line interface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .detect import build_source
from .model import write_bundle
from .sources import REGISTRY, SourceError
from .validate import validate_bundle


def _add_generate_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "generate",
        help="Generate an OKF bundle from a source.",
        description="Generate a conformant OKF v0.1 bundle from a git repo, "
                    "BigQuery/Firebase project, local directory, or web docs site.",
    )
    p.add_argument("input", help="Source input: git URL, path, https URL, bq:PROJECT, firebase:PROJECT")
    p.add_argument("-o", "--out", default=None,
                   help="Output bundle directory (default: ./<name>-okf).")
    p.add_argument("-t", "--type", choices=sorted(REGISTRY.keys()), default=None,
                   help="Force the source type instead of auto-detecting.")
    p.add_argument("--title", default=None, help="Override the bundle title.")
    p.add_argument("--overwrite", action="store_true",
                   help="Overwrite a non-empty output directory.")
    p.add_argument("--no-validate", action="store_true",
                   help="Skip validating the bundle after generation.")
    # Source-specific knobs (ignored by sources that don't use them).
    p.add_argument("--max-pages", type=int, default=25, help="[web] max pages to crawl.")
    p.add_argument("--max-depth", type=int, default=2, help="[web] max crawl depth.")
    p.add_argument("--dataset", default=None, help="[bigquery] limit to one dataset id.")
    p.add_argument("--sample", type=int, default=50, help="[firebase] docs to sample per collection.")
    p.set_defaults(func=_cmd_generate)


def _add_enrich_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "enrich",
        help="Enrichment agent (pass 2): infer join paths + backlinks in a bundle.",
        description="Enrich a drafted bundle by inferring foreign-key join paths "
                    "between tables and wiring backlinks. With --llm, also rewrite "
                    "concept descriptions using the Claude API.",
    )
    p.add_argument("bundle", help="Path to the bundle directory to enrich.")
    p.add_argument("-o", "--out", default=None,
                   help="Write enriched bundle to a new directory (default: in place).")
    p.add_argument("--llm", action="store_true",
                   help="Also rewrite descriptions via the Claude API (needs ANTHROPIC_API_KEY).")
    p.set_defaults(func=_cmd_enrich)


def _add_visualize_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "visualize",
        help="Consumer: render a bundle as a self-contained interactive HTML graph.",
    )
    p.add_argument("bundle", help="Path to the bundle directory.")
    p.add_argument("-o", "--out", default=None, help="Output HTML file (default: <bundle>/graph.html).")
    p.add_argument("--title", default=None, help="Override the page title.")
    p.set_defaults(func=_cmd_visualize)


def _add_search_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "search",
        help="Consumer: full-text search over a bundle (search-index reference).",
    )
    p.add_argument("bundle", help="Path to the bundle directory.")
    p.add_argument("query", nargs="*", help="Search terms.")
    p.add_argument("-n", "--limit", type=int, default=10, help="Max results.")
    p.add_argument("--export", default=None, help="Write a portable JSON search index to this path.")
    p.set_defaults(func=_cmd_search)


def _add_ask_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "ask",
        help="Consumer: reasoning agent that answers questions over a bundle.",
    )
    p.add_argument("bundle", help="Path to the bundle directory.")
    p.add_argument("question", nargs="+", help="The question to answer.")
    p.add_argument("-k", "--top-k", type=int, default=3, help="Concepts to retrieve.")
    p.add_argument("--llm", action="store_true",
                   help="Phrase the answer with the Claude API (retrieval stays deterministic).")
    p.set_defaults(func=_cmd_ask)


def _add_validate_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "validate",
        help="Validate an existing OKF bundle for conformance.",
    )
    p.add_argument("bundle", help="Path to the bundle directory to validate.")
    p.add_argument("--strict", action="store_true",
                   help="Exit non-zero if there are any warnings.")
    p.add_argument("-q", "--quiet", action="store_true", help="Only print the summary line.")
    p.set_defaults(func=_cmd_validate)


def _default_out(input_value: str, title: str) -> str:
    from .model import slugify
    base = slugify(title) or "bundle"
    return f"{base}-okf"


def _cmd_generate(args: argparse.Namespace) -> int:
    options = {
        "title": args.title,
        "max_pages": args.max_pages,
        "max_depth": args.max_depth,
        "dataset": args.dataset,
        "sample": args.sample,
    }
    try:
        source = build_source(args.input, kind=args.type, options=options)
    except SourceError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"[okfgen] source type: {source.kind}", file=sys.stderr)
    print(f"[okfgen] ingesting: {args.input}", file=sys.stderr)
    try:
        bundle = source.build()
    except SourceError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    out = args.out or _default_out(args.input, bundle.title)
    try:
        stats = write_bundle(bundle, Path(out), overwrite=args.overwrite)
    except FileExistsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"[okfgen] wrote {stats['concepts']} concept(s) to {out}", file=sys.stderr)

    if not args.no_validate:
        result = validate_bundle(out)
        _print_validation(result, quiet=True)
        if not result.conformant:
            print("warning: generated bundle failed conformance (see above).", file=sys.stderr)
            return 1

    print(out)  # stdout: the path, so the command is scriptable
    return 0


def _print_validation(result, quiet: bool = False) -> None:
    if not quiet:
        for issue in result.issues:
            marker = "ERROR" if issue.level == "error" else "warn "
            print(f"  [{marker}] {issue.file}: {issue.message}", file=sys.stderr)
    status = "CONFORMANT" if result.conformant else "NON-CONFORMANT"
    print(
        f"[okfgen] {status}: {result.concept_count} concept(s), "
        f"{len(result.errors)} error(s), {len(result.warnings)} warning(s).",
        file=sys.stderr,
    )


def _cmd_enrich(args: argparse.Namespace) -> int:
    from .enrich import enrich_bundle
    try:
        report = enrich_bundle(args.bundle, out_dir=args.out, use_llm=args.llm)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except FileExistsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    target = args.out or args.bundle
    print(
        f"[okfgen] enriched {report.concepts_changed} concept(s): "
        f"{report.joins_added} join(s), {report.backlinks_added} backlink(s)"
        + (f", {report.descriptions_rewritten} description(s) rewritten" if report.descriptions_rewritten else ""),
        file=sys.stderr,
    )
    print(target)
    return 0


def _cmd_visualize(args: argparse.Namespace) -> int:
    from .visualize import visualize
    out = args.out or str(Path(args.bundle) / "graph.html")
    try:
        visualize(args.bundle, out, title=args.title)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"[okfgen] wrote interactive graph to {out}", file=sys.stderr)
    print(out)
    return 0


def _cmd_search(args: argparse.Namespace) -> int:
    from .searchindex import build_index, export_index
    if args.export:
        export_index(args.bundle, args.export)
        print(f"[okfgen] wrote search index to {args.export}", file=sys.stderr)
        if not args.query:
            print(args.export)
            return 0
    query = " ".join(args.query)
    if not query:
        print("error: provide search terms (or --export to only write the index).", file=sys.stderr)
        return 2
    index = build_index(args.bundle)
    hits = index.search(query, limit=args.limit)
    if not hits:
        print("No matches.", file=sys.stderr)
        return 1
    for h in hits:
        print(f"{h.score:6.1f}  [{h.concept.type}] {h.concept.title}  ({h.concept.path})")
        if h.snippet:
            print(f"        {h.snippet}")
    return 0


def _cmd_ask(args: argparse.Namespace) -> int:
    from .agent import ask
    answer = ask(args.bundle, " ".join(args.question), top_k=args.top_k, use_llm=args.llm)
    print(answer.render())
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    result = validate_bundle(args.bundle)
    _print_validation(result, quiet=args.quiet)
    if not result.conformant:
        return 1
    if args.strict and result.warnings:
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="okfgen",
        description="Deterministically generate Open Knowledge Format (OKF) bundles.",
    )
    parser.add_argument("--version", action="version", version=f"okfgen {__version__}")
    sub = parser.add_subparsers(dest="command")
    _add_generate_parser(sub)
    _add_enrich_parser(sub)
    _add_visualize_parser(sub)
    _add_search_parser(sub)
    _add_ask_parser(sub)
    _add_validate_parser(sub)
    return parser


def _force_utf8_streams() -> None:
    # Bundles routinely contain arrows/ellipses; the default Windows console
    # codec (cp1252) can't encode them. Reconfigure to UTF-8 where supported.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass


def main(argv=None) -> int:
    _force_utf8_streams()
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help(sys.stderr)
        return 1
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
