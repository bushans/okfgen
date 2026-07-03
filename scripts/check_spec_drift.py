#!/usr/bin/env python3
"""Detect drift between okfgen and the upstream OKF specification.

okfgen is a reference implementation, so it needs to know when Google changes
SPEC.md. This compares the pinned copy under spec/ against the live upstream
file and reports any change (with a short diff), so a scheduled CI job can open
an issue automatically.

    python scripts/check_spec_drift.py            # check; exit 1 on drift
    python scripts/check_spec_drift.py --update    # re-pin to current upstream

Exit codes: 0 = in sync, 1 = drift detected, 2 = fetch/setup error.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import sys
import urllib.request
from pathlib import Path

UPSTREAM = "https://raw.githubusercontent.com/GoogleCloudPlatform/knowledge-catalog/main/okf/SPEC.md"
SPEC_DIR = Path(__file__).resolve().parent.parent / "spec"
VENDORED = SPEC_DIR / "SPEC.md"
SHA_FILE = SPEC_DIR / "SPEC.sha256"


def _fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "okfgen-spec-watch"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def update() -> int:
    data = _fetch(UPSTREAM)
    SPEC_DIR.mkdir(exist_ok=True)
    VENDORED.write_bytes(data)
    SHA_FILE.write_text(_sha(data) + "\n", encoding="utf-8")
    print(f"Re-pinned spec/SPEC.md ({len(data)} bytes, sha256 {_sha(data)}).")
    return 0


def check() -> int:
    if not SHA_FILE.exists() or not VENDORED.exists():
        print("error: no pinned spec found; run with --update first.", file=sys.stderr)
        return 2
    pinned_sha = SHA_FILE.read_text(encoding="utf-8").strip()
    try:
        upstream = _fetch(UPSTREAM)
    except Exception as exc:
        print(f"error: could not fetch upstream spec: {exc}", file=sys.stderr)
        return 2

    if _sha(upstream) == pinned_sha:
        print("OKF spec is in sync with the pinned copy (no drift).")
        return 0

    print("::warning::OKF spec drift detected — upstream SPEC.md has changed.")
    print(f"pinned   sha256: {pinned_sha}")
    print(f"upstream sha256: {_sha(upstream)}")
    print()
    old = VENDORED.read_text(encoding="utf-8", errors="replace").splitlines()
    new = upstream.decode("utf-8", "replace").splitlines()
    diff = list(difflib.unified_diff(old, new, "spec/SPEC.md (pinned)", "upstream SPEC.md", lineterm=""))
    # Keep the printed diff bounded for the issue body.
    print("\n".join(diff[:200]))
    if len(diff) > 200:
        print(f"... ({len(diff) - 200} more diff lines)")
    print()
    print("Review for conformance impact, then re-pin with: "
          "python scripts/check_spec_drift.py --update")
    return 1


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Check for OKF spec drift.")
    p.add_argument("--update", action="store_true", help="Re-pin to current upstream and exit 0.")
    args = p.parse_args(argv)
    return update() if args.update else check()


if __name__ == "__main__":
    raise SystemExit(main())
