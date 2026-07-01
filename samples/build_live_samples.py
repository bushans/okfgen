#!/usr/bin/env python3
"""Build the LIVE public-dataset sample bundle (requires network).

Unlike build_samples.py (fully offline + reproducible), this script fetches a
real, publicly available dataset from a live CKAN open-data portal and turns it
into an OKF bundle. Default: **Toronto Beaches Water Quality** — daily E. coli
readings at Toronto's public beaches. Easy to read, no API key, no cloud account.

    python samples/build_live_samples.py
    python samples/build_live_samples.py ckan:https://<portal>/dataset/<slug>

The committed snapshot under samples/bundles/toronto-beaches/ is just that — a
snapshot. Re-run to refresh it against the live source.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
sys.path.insert(0, str(REPO))

from okfgen.detect import build_source          # noqa: E402
from okfgen.model import write_bundle            # noqa: E402
from okfgen.enrich import enrich_bundle          # noqa: E402
from okfgen.visualize import visualize           # noqa: E402
from okfgen.validate import validate_bundle      # noqa: E402
from okfgen.sources import SourceError           # noqa: E402

DEFAULT_INPUT = (
    "ckan:https://ckan0.cf.opendata.inter.prod-toronto.ca"
    "/dataset/toronto-beaches-water-quality"
)
OUT = ROOT / "bundles" / "toronto-beaches"


def main(argv) -> int:
    source_input = argv[1] if len(argv) > 1 else DEFAULT_INPUT
    print(f"Fetching live dataset: {source_input}")
    try:
        source = build_source(source_input, kind="ckan")
        bundle = source.build()
    except SourceError as exc:
        print(f"error: {exc}", file=sys.stderr)
        print("(This sample needs network access to the live portal.)", file=sys.stderr)
        return 2

    write_bundle(bundle, OUT, overwrite=True)
    report = enrich_bundle(str(OUT))
    visualize(str(OUT), str(OUT / "graph.html"))
    result = validate_bundle(str(OUT))
    status = "CONFORMANT" if result.conformant else "NON-CONFORMANT"
    print(f"toronto-beaches  {status}  ({result.concept_count} concepts, "
          f"{report.backlinks_added} backlink(s) added)")
    print("Written to", OUT)
    return 0 if result.conformant else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
