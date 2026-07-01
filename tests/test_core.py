"""Tests for the deterministic core: yaml, model, scan, detect, validate."""

from __future__ import annotations

from pathlib import Path

import pytest

from okfgen import yamlfm
from okfgen.model import Concept, Bundle, write_bundle, slugify
from okfgen.detect import build_source
from okfgen.sources import GitSource, WebDocsSource, LocalDirSource
from okfgen.sources.bigquery import BigQuerySource
from okfgen.sources.firebase import FirebaseSource
from okfgen.sources.scan import scan_directory
from okfgen.validate import validate_bundle


# --- yaml frontmatter -------------------------------------------------------

def test_yaml_roundtrip_scalars_and_lists():
    fm = {"type": "Thing", "title": "Hello: World", "tags": ["a", "b"]}
    doc = yamlfm.dump_document(fm, "# Body\ntext")
    assert doc.startswith("---\n")
    raw, body = yamlfm.split_frontmatter(doc)
    parsed = yamlfm.parse(raw)
    assert parsed["type"] == "Thing"
    assert parsed["title"] == "Hello: World"  # colon value was quoted + parsed back
    assert parsed["tags"] == ["a", "b"]
    assert "# Body" in body


def test_split_frontmatter_none_when_absent():
    raw, body = yamlfm.split_frontmatter("no frontmatter here")
    assert raw is None
    assert body == "no frontmatter here"


def test_type_field_ordering_first():
    out = yamlfm.dump({"timestamp": "x", "type": "T", "title": "n"})
    assert out.splitlines()[0].startswith("type:")


# --- slugify ----------------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("Hello World", "hello-world"),
    ("my_table.NAME", "my-table-name"),
    ("   ", "concept"),
    ("Über Cool!!", "ber-cool"),
])
def test_slugify(raw, expected):
    assert slugify(raw) == expected


# --- bundle writing + reserved files ---------------------------------------

def test_write_bundle_creates_index_and_concept(tmp_path):
    b = Bundle(title="Demo", description="A demo bundle", source="test")
    b.add(Concept(path="overview.md", type="Project", title="Demo", description="d"))
    out = tmp_path / "out"
    stats = write_bundle(b, out)
    assert stats["concepts"] == 1
    assert (out / "index.md").exists()
    assert (out / "overview.md").exists()
    index = (out / "index.md").read_text(encoding="utf-8")
    assert 'okf_version: "0.1"' in index or "okf_version: 0.1" in index
    assert "[Demo](/overview.md)" in index


def test_write_bundle_refuses_nonempty_without_overwrite(tmp_path):
    (tmp_path / "existing.txt").write_text("x", encoding="utf-8")
    b = Bundle(title="Demo")
    b.add(Concept(path="c.md", type="T"))
    with pytest.raises(FileExistsError):
        write_bundle(b, tmp_path)
    # overwrite=True should succeed
    write_bundle(b, tmp_path, overwrite=True)


def test_unique_path_avoids_collision():
    b = Bundle(title="x")
    p1 = b.unique_path("docs", "readme")
    b.add(Concept(path=p1, type="Document"))
    p2 = b.unique_path("docs", "readme")
    assert p1 != p2
    assert p1 == "docs/readme.md"
    assert p2 == "docs/readme-1.md"


# --- scan a synthetic project ----------------------------------------------

@pytest.fixture
def sample_project(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    (root / "README.md").write_text("# Sample Project\n\nDoes things.", encoding="utf-8")
    (root / "requirements.txt").write_text("requests==2.0\n# comment\nflask>=1.0\n", encoding="utf-8")
    src = root / "src"
    src.mkdir()
    (src / "app.py").write_text("def main():\n    pass\n\nclass Server:\n    pass\n", encoding="utf-8")
    (root / "docs").mkdir()
    (root / "docs" / "guide.md").write_text("# User Guide\n\nHow to use.", encoding="utf-8")
    # ignored dir must be skipped
    (root / "node_modules").mkdir()
    (root / "node_modules" / "junk.js").write_text("var x=1", encoding="utf-8")
    return root


def test_scan_directory_builds_expected_concepts(sample_project):
    bundle = scan_directory(sample_project, title="proj", source_label=str(sample_project))
    paths = {c.path for c in bundle.concepts}
    assert "overview.md" in paths
    assert "dependencies.md" in paths
    assert any(p.startswith("docs/") for p in paths)
    assert any(p.startswith("modules/") for p in paths)

    overview = next(c for c in bundle.concepts if c.path == "overview.md")
    assert overview.type == "Project"
    assert "Python" in overview.tags

    deps = next(c for c in bundle.concepts if c.path == "dependencies.md")
    assert "requests" in deps.body
    assert "flask" in deps.body
    # ignored dir excluded
    assert "junk" not in "".join(c.body for c in bundle.concepts)

    # extracted python defs
    module = next(c for c in bundle.concepts if c.path.startswith("modules/"))
    assert "main" in module.body and "Server" in module.body


def test_generated_bundle_is_conformant(sample_project, tmp_path):
    bundle = scan_directory(sample_project, title="proj", source_label=str(sample_project))
    out = tmp_path / "bundle"
    write_bundle(bundle, out)
    result = validate_bundle(str(out))
    assert result.conformant, [i.message for i in result.errors]
    assert result.concept_count >= 3


# --- validator error paths --------------------------------------------------

def test_validate_flags_missing_type(tmp_path):
    (tmp_path / "bad.md").write_text("---\ntitle: no type\n---\nbody", encoding="utf-8")
    result = validate_bundle(str(tmp_path))
    assert not result.conformant
    assert any("type" in e.message for e in result.errors)


def test_validate_flags_missing_frontmatter(tmp_path):
    (tmp_path / "bad.md").write_text("just text, no frontmatter", encoding="utf-8")
    result = validate_bundle(str(tmp_path))
    assert not result.conformant


def test_validate_reserved_files_not_required_to_be_concepts(tmp_path):
    (tmp_path / "index.md").write_text("# Index\n- item", encoding="utf-8")
    (tmp_path / "log.md").write_text("# Log", encoding="utf-8")
    (tmp_path / "c.md").write_text("---\ntype: T\n---\nok", encoding="utf-8")
    result = validate_bundle(str(tmp_path))
    assert result.conformant


def test_validate_broken_link_is_warning_not_error(tmp_path):
    (tmp_path / "c.md").write_text(
        "---\ntype: T\n---\nSee [x](/nope.md)", encoding="utf-8"
    )
    result = validate_bundle(str(tmp_path))
    assert result.conformant  # broken links never fail conformance
    assert any("Broken cross-link" in w.message for w in result.warnings)


# --- detection --------------------------------------------------------------

def test_detect_git_url():
    s = build_source("https://github.com/foo/bar.git")
    assert isinstance(s, GitSource)


def test_detect_git_ssh():
    assert GitSource.matches("git@github.com:foo/bar.git")


def test_detect_web_url():
    s = build_source("https://docs.example.com/guide")
    assert isinstance(s, WebDocsSource)


def test_detect_local_dir(tmp_path):
    s = build_source(str(tmp_path))
    assert isinstance(s, LocalDirSource)


def test_detect_bigquery_prefix():
    assert BigQuerySource.matches("bq:my-project")
    assert BigQuerySource.matches("bigquery:my-project")


def test_detect_firebase_prefix():
    assert FirebaseSource.matches("firebase:my-project")
    assert FirebaseSource.matches("fb:my-project")


def test_explicit_type_overrides(tmp_path):
    s = build_source(str(tmp_path), kind="local")
    assert isinstance(s, LocalDirSource)


def test_undetectable_input_raises():
    from okfgen.sources import SourceError
    with pytest.raises(SourceError):
        build_source("not-a-real-thing-xyz")
