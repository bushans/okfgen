"""Tests for the `okfgen skill` consumer (SKILL.md generation)."""

from __future__ import annotations

from pathlib import Path

import pytest

from okfgen import yamlfm
from okfgen.skill import build_skill
from okfgen.mcp_server import make_skill

SCHEMA = (
    '{"project":"acme","title":"Acme Sales","console_url":"https://c/acme",'
    '"datasets":[{"id":"sales","tables":['
    '{"name":"customers","columns":[{"name":"customer_id","type":"STRING"}]},'
    '{"name":"orders","columns":[{"name":"order_id","type":"STRING"},'
    '{"name":"customer_id","type":"STRING"}]}]}]}'
)


def _write_schema(tmp_path) -> str:
    p = tmp_path / "s.json"
    p.write_text(SCHEMA, encoding="utf-8")
    return f"schema:{p}"


def test_build_skill_from_source(tmp_path):
    out = tmp_path / "skill"
    result = build_skill(_write_schema(tmp_path), str(out))

    skill_md = out / "SKILL.md"
    assert skill_md.exists()
    assert (out / "reference" / "index.md").exists()
    assert (out / "reference" / "overview.md").exists()

    text = skill_md.read_text(encoding="utf-8")
    raw_fm, body = yamlfm.split_frontmatter(text)
    fm = yamlfm.parse(raw_fm)
    # Required Agent Skill frontmatter.
    assert fm.get("name") == "acme-sales"
    assert fm.get("description") and len(str(fm["description"])) > 20
    assert "Use when" in fm["description"]
    # Body points into reference files (progressive disclosure).
    assert "reference/overview.md" in body
    assert "## How to use this skill" in body
    assert result.concept_count >= 3


def test_build_skill_from_existing_bundle(tmp_path):
    # First generate a bundle, then build a skill from that directory.
    from okfgen.detect import build_source
    from okfgen.model import write_bundle
    bundle = build_source(_write_schema(tmp_path)).build()
    bdir = tmp_path / "bundle"
    write_bundle(bundle, bdir)

    out = tmp_path / "skill2"
    result = build_skill(str(bdir), str(out), name="my-catalog")
    assert result.name == "my-catalog"
    assert (out / "SKILL.md").exists()
    assert (out / "reference" / "overview.md").exists()


def test_build_skill_refuses_nonempty(tmp_path):
    out = tmp_path / "skill3"
    out.mkdir()
    (out / "x").write_text("x", encoding="utf-8")
    with pytest.raises(FileExistsError):
        build_skill(_write_schema(tmp_path), str(out))


def test_mcp_make_skill(tmp_path):
    out = str(tmp_path / "mskill")
    msg = make_skill(_write_schema(tmp_path), out_dir=out)
    assert "Wrote skill" in msg and "description:" in msg
    assert (Path(out) / "SKILL.md").exists()
