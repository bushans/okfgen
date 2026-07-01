#!/usr/bin/env python3
"""Regenerate the three ready-to-browse sample bundles.

Deterministic: a fixed OKFGEN_TIMESTAMP makes the committed bundles reproducible,
so re-running this script produces a clean (empty) git diff. Each sample
exercises a different producer perspective from the OKF blog post:

  1. acme-sales          — a DATABASE (schema:) bundle, then the enrichment agent
                           infers foreign-key join paths.
  2. petclinic-api       — a SOURCE SYSTEM (local repo) bundle.
  3. observability-docs  — a DOCUMENTATION SITE (local markdown) bundle.

Each bundle also gets a self-contained `graph.html` from the visualizer consumer.

Usage:  python samples/build_samples.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("OKFGEN_TIMESTAMP", "2026-07-01T00:00:00+00:00")

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
sys.path.insert(0, str(REPO))

from okfgen.detect import build_source          # noqa: E402
from okfgen.model import write_bundle            # noqa: E402
from okfgen.enrich import enrich_bundle          # noqa: E402
from okfgen.visualize import visualize           # noqa: E402
from okfgen.validate import validate_bundle      # noqa: E402

RECIPES = ROOT / "recipes"
BUNDLES = ROOT / "bundles"


def _generate(input_value: str, kind: str, out_name: str, options=None) -> Path:
    out = BUNDLES / out_name
    source = build_source(input_value, kind=kind, options=options or {})
    bundle = source.build()
    write_bundle(bundle, out, overwrite=True)
    return out


def main() -> int:
    BUNDLES.mkdir(parents=True, exist_ok=True)

    # 1) Database bundle + enrichment (join-path inference).
    acme = _generate(str(RECIPES / "acme_sales.schema.json"), "schema", "acme-sales")
    report = enrich_bundle(str(acme))  # in place
    print(f"acme-sales: enriched {report.joins_added} join(s), "
          f"{report.backlinks_added} backlink(s)")

    # 2) Source-system (repo) bundle.
    petclinic = _generate(str(RECIPES / "petclinic_app"), "local", "petclinic-api",
                          options={"title": "PetClinic API"})

    # 3) Documentation-site bundle.
    docs = _generate(str(RECIPES / "observability_docs"), "local", "observability-docs",
                     options={"title": "Nimbus Docs"})

    # Visualizer output + conformance check for each.
    ok = True
    for path in (acme, petclinic, docs):
        visualize(str(path), str(path / "graph.html"))
        result = validate_bundle(str(path))
        status = "CONFORMANT" if result.conformant else "NON-CONFORMANT"
        print(f"{path.name:22s} {status}  "
              f"({result.concept_count} concepts, {len(result.errors)} errors)")
        ok = ok and result.conformant

    print("\nAll sample bundles written to", BUNDLES)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
