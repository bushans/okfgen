"""Tests for OKF v0.2 `sources` provenance emission."""

from __future__ import annotations

from okfgen import yamlfm
from okfgen.model import Concept, make_source, Bundle, write_bundle
from okfgen.consumer import load_bundle
from okfgen.validate import validate_bundle


def test_make_source_drops_empty_and_truncates_date():
    s = make_source("https://x", id="a", title=None, author="team:z",
                    usage_count=5000, last_modified="2026-05-30T21:06:39.8Z")
    assert s == {
        "resource": "https://x", "id": "a", "author": "team:z",
        "usage_count": 5000, "last_modified": "2026-05-30",
    }
    assert "title" not in s  # None dropped


def test_concept_emits_sources_block():
    c = Concept(path="t.md", type="Table", title="orders",
                sources=[make_source("https://portal/x", title="orders table",
                                     author="City of Toronto", last_modified="2026-04-15")])
    doc = c.render()
    assert "sources:" in doc
    # URLs contain ':' so the emitter quotes them.
    assert '  - resource: "https://portal/x"' in doc
    assert "    author: City of Toronto" in doc
    assert "last_modified: 2026-04-15" in doc


def test_sources_roundtrip_through_yaml():
    fm = {"type": "Table", "sources": [
        {"resource": "https://a", "author": "team:x", "usage_count": 12}]}
    raw, _ = yamlfm.split_frontmatter(yamlfm.dump_document(fm, "body"))
    parsed = yamlfm.parse(raw)
    assert isinstance(parsed["sources"], list)
    assert parsed["sources"][0]["resource"] == "https://a"
    assert parsed["sources"][0]["author"] == "team:x"
    assert parsed["sources"][0]["usage_count"] == 12


def test_bundle_with_sources_is_conformant(tmp_path):
    b = Bundle(title="d")
    b.add(Concept(path="c.md", type="Table", title="c",
                  sources=[make_source("https://a", last_modified="2026-01-01")]))
    out = tmp_path / "b"
    write_bundle(b, out)
    result = validate_bundle(str(out))
    assert result.conformant
    # loader tolerates the new family (unknown-to-old key) without error
    loaded = load_bundle(str(out))
    assert loaded.concepts[0].frontmatter["sources"][0]["resource"] == "https://a"
