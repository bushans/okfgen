"""Guards for the pinned OKF spec and the version-compat warning."""

from __future__ import annotations

import hashlib
from pathlib import Path

from okfgen.model import Bundle, Concept, write_bundle
from okfgen.validate import validate_bundle

REPO = Path(__file__).resolve().parent.parent


def test_pinned_spec_hash_matches_file():
    """spec/SPEC.sha256 must match spec/SPEC.md, so the drift pin stays honest."""
    spec = REPO / "spec" / "SPEC.md"
    sha_file = REPO / "spec" / "SPEC.sha256"
    assert spec.is_file() and sha_file.is_file(), "pinned spec files missing"
    actual = hashlib.sha256(spec.read_bytes()).hexdigest()
    assert actual == sha_file.read_text(encoding="utf-8").strip()


def _write_bundle_with_version(tmp_path, version: str) -> Path:
    b = Bundle(title="v", okf_version=version)
    b.add(Concept(path="c.md", type="Thing", title="c"))
    out = tmp_path / "bundle"
    write_bundle(b, out)
    return out


def test_future_okf_version_warns_but_stays_conformant(tmp_path):
    out = _write_bundle_with_version(tmp_path, "9.9")
    result = validate_bundle(str(out))
    assert result.conformant  # never fail on version — reader must tolerate
    assert any("targets OKF 9.9" in w.message for w in result.warnings)


def test_current_okf_version_no_version_warning(tmp_path):
    out = _write_bundle_with_version(tmp_path, "0.1")
    result = validate_bundle(str(out))
    assert not any("targets OKF" in w.message for w in result.warnings)
