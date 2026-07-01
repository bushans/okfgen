"""Tests for consumer-side reference implementations + enrichment agent."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from okfgen.model import Bundle, Concept, write_bundle
from okfgen.consumer import load_bundle
from okfgen.searchindex import SearchIndex, build_index, export_index
from okfgen.agent import ask
from okfgen.enrich import enrich_bundle, _infer_joins, _columns
from okfgen.visualize import build_graph_data, render_html
from okfgen.detect import build_source
from okfgen.sources.schema import SchemaSource


# --- a small database-shaped bundle written to disk -------------------------

@pytest.fixture
def db_bundle(tmp_path):
    b = Bundle(title="Shop", source="test")
    b.add(Concept(path="tables/customers.md", type="Table", title="sales.customers",
                  description="One row per customer.",
                  body="# Schema\n\n| Column | Type |\n|---|---|\n| `customer_id` | STRING |\n| `email` | STRING |"))
    b.add(Concept(path="tables/orders.md", type="Table", title="sales.orders",
                  description="One row per order.",
                  body="# Schema\n\n| Column | Type |\n|---|---|\n| `order_id` | STRING |\n| `customer_id` | STRING |"))
    out = tmp_path / "bundle"
    write_bundle(b, out)
    return out


# --- consumer loader --------------------------------------------------------

def test_loader_resolves_links_and_graph(tmp_path):
    b = Bundle(title="X")
    b.add(Concept(path="a.md", type="T", title="A", body="see [B](/b.md) and [ext](https://x.com)"))
    b.add(Concept(path="b.md", type="T", title="B", body="back to [A](a.md)"))
    out = tmp_path / "b"
    write_bundle(b, out)
    loaded = load_bundle(str(out))
    assert len(loaded.concepts) == 2
    edges = set(loaded.edges())
    assert ("a.md", "b.md") in edges
    assert ("b.md", "a.md") in edges
    a = loaded.get("a.md")
    assert "https://x.com" in a.external_links
    assert loaded.backlinks()["b.md"] == ["a.md"]


# --- search index -----------------------------------------------------------

def test_search_ranks_title_over_body(db_bundle):
    idx = build_index(str(db_bundle))
    hits = idx.search("customers")
    assert hits
    assert hits[0].concept.title == "sales.customers"


def test_search_no_match_returns_empty(db_bundle):
    assert build_index(str(db_bundle)).search("zzzznotthere") == []


def test_export_index_roundtrips(db_bundle, tmp_path):
    out = tmp_path / "index.json"
    export_index(str(db_bundle), str(out))
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "documents" in data and "postings" in data
    assert any(d["title"] == "sales.orders" for d in data["documents"])


# --- reasoning agent --------------------------------------------------------

def test_agent_answers_with_citations_and_traversal(db_bundle):
    ans = ask(str(db_bundle), "what tables hold customers", top_k=2)
    assert ans.citations
    assert ans.traversal
    assert "customers" in ans.answer.lower()


def test_agent_handles_no_match(db_bundle):
    ans = ask(str(db_bundle), "quantum chromodynamics")
    assert "No concepts" in ans.answer


# --- enrichment agent -------------------------------------------------------

def test_column_extraction():
    body = "# Schema\n\n| Column | Type |\n|---|---|\n| `order_id` | STRING |\n| `customer_id` | STRING |"
    cols = _columns(body)
    assert "order_id" in cols and "customer_id" in cols
    assert "column" not in cols  # header excluded


def test_enrich_infers_join_paths_and_backlinks(db_bundle):
    report = enrich_bundle(str(db_bundle))
    assert report.joins_added >= 1
    orders = (db_bundle / "tables" / "orders.md").read_text(encoding="utf-8")
    assert "# Joins" in orders
    assert "customers.md" in orders  # customer_id -> customers
    customers = (db_bundle / "tables" / "customers.md").read_text(encoding="utf-8")
    assert "# Related" in customers  # referenced by orders


def test_enrich_is_idempotent(db_bundle):
    r1 = enrich_bundle(str(db_bundle))
    r2 = enrich_bundle(str(db_bundle))
    # Second run must not stack duplicate Joins sections.
    orders = (db_bundle / "tables" / "orders.md").read_text(encoding="utf-8")
    assert orders.count("# Joins") == 1
    assert r1.joins_added == r2.joins_added


def test_enrich_to_new_dir_leaves_source_untouched(db_bundle, tmp_path):
    out = tmp_path / "enriched"
    enrich_bundle(str(db_bundle), out_dir=str(out))
    assert (out / "tables" / "orders.md").exists()
    src_orders = (db_bundle / "tables" / "orders.md").read_text(encoding="utf-8")
    assert "# Joins" not in src_orders  # original not modified


# --- visualizer -------------------------------------------------------------

def test_graph_data_has_nodes_and_edges(db_bundle):
    enrich_bundle(str(db_bundle))  # add join edges
    loaded = load_bundle(str(db_bundle))
    data = build_graph_data(loaded)
    assert len(data["nodes"]) == 2
    assert any(e["source"].endswith("orders.md") for e in data["links"])


def test_render_html_is_self_contained(db_bundle):
    loaded = load_bundle(str(db_bundle))
    html = render_html(loaded)
    assert "<canvas" in html
    assert "application/json" in html
    # no external scripts/styles
    assert "http://" not in html.split("<script id=\"data\"")[0]
    assert "cdn" not in html.lower()


# --- schema (offline database) source ---------------------------------------

def test_schema_source_from_json(tmp_path):
    schema = {
        "project": "p", "title": "P", "datasets": [
            {"id": "ds", "tables": [
                {"name": "t", "description": "d", "columns": [
                    {"name": "id", "type": "STRING", "mode": "REQUIRED"}]}]}]}
    f = tmp_path / "s.json"
    f.write_text(json.dumps(schema), encoding="utf-8")
    assert SchemaSource.matches(str(f))
    src = build_source(str(f))
    assert isinstance(src, SchemaSource)
    bundle = src.build()
    paths = {c.path for c in bundle.concepts}
    assert "overview.md" in paths
    assert "datasets/ds.md" in paths
    assert "tables/ds-t.md" in paths


def test_schema_source_from_sql(tmp_path):
    sql = "CREATE TABLE sales.orders (order_id STRING, customer_id STRING);"
    f = tmp_path / "schema.sql"
    f.write_text(sql, encoding="utf-8")
    src = SchemaSource("schema:" + str(f))
    bundle = src.build()
    table = next(c for c in bundle.concepts if c.type == "Table")
    assert "order_id" in table.body and "customer_id" in table.body


def test_schema_prefix_matches():
    assert SchemaSource.matches("schema:/some/path.json")
