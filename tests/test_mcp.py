"""Tests for the MCP server tool functions (framework-agnostic layer)."""

from __future__ import annotations

import importlib

import pytest

from okfgen import mcp_server


def test_module_imports_without_mcp():
    # Importing must not require the optional `mcp` package.
    assert hasattr(mcp_server, "create_server")
    assert callable(mcp_server.generate_bundle)


def test_list_source_types_mentions_all_adapters():
    out = mcp_server.list_source_types()
    for kind in ["git", "local", "web", "schema", "ckan", "socrata", "bigquery", "firebase"]:
        assert kind in out


def test_generate_search_ask_validate_roundtrip(tmp_path):
    schema = tmp_path / "s.json"
    schema.write_text(
        '{"project":"p","datasets":[{"id":"sales","tables":['
        '{"name":"customers","columns":[{"name":"customer_id","type":"STRING"}]},'
        '{"name":"orders","columns":[{"name":"order_id","type":"STRING"},'
        '{"name":"customer_id","type":"STRING"}]}]}]}',
        encoding="utf-8",
    )
    out = tmp_path / "bundle"

    gen = mcp_server.generate_bundle(f"schema:{schema}", out_dir=str(out))
    assert "Generated OKF bundle" in gen
    assert "customers" in gen

    hits = mcp_server.search_bundle(str(out), "orders", limit=5)
    assert "orders" in hits.lower()

    answer = mcp_server.ask_bundle(str(out), "what tables are there?")
    assert "Q:" in answer and "Citations" in answer

    val = mcp_server.validate_bundle_tool(str(out))
    assert "CONFORMANT" in val

    viz = mcp_server.visualize_bundle(str(out), str(out / "g.html"))
    assert "graph" in viz.lower() and (out / "g.html").exists()


def test_generate_reports_source_errors(tmp_path):
    out = mcp_server.generate_bundle("bq:nonexistent-project", out_dir=str(tmp_path / "x"))
    assert out.startswith("error:")  # missing SDK / creds surfaced, not a crash


def test_create_server_or_graceful_without_mcp():
    try:
        import mcp  # noqa: F401
    except Exception:
        with pytest.raises(SystemExit):
            mcp_server.create_server()
    else:
        server = mcp_server.create_server()
        assert server is not None
