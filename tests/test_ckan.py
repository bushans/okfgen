"""Offline tests for the CKAN source (API calls are stubbed)."""

from __future__ import annotations

import pytest

from okfgen.sources.ckan import CkanSource
from okfgen.sources import SourceError
from okfgen.detect import build_source


_PACKAGE = {
    "title": "Toronto Beaches Water Quality",
    "notes": "Daily E. coli sampling at Toronto's public beaches.",
    "organization": {"title": "City of Toronto"},
    "license_title": "Open Government Licence",
    "metadata_modified": "2026-04-15T21:06:39",
    "tags": [{"name": "beaches"}, {"name": "water quality"}],
    "resources": [
        {"id": "abc", "name": "water-quality", "format": "CSV",
         "description": "The tabular data.", "datastore_active": True,
         "url": "https://portal/datastore/dump/abc"},
        {"id": "def", "name": "readme", "format": "PDF",
         "datastore_active": False, "url": "https://portal/readme.pdf"},
    ],
}

_DATASTORE = {
    "fields": [
        {"id": "_id", "type": "int"},  # internal, must be dropped
        {"id": "beachName", "type": "text"},
        {"id": "collectionDate", "type": "date"},
        {"id": "eColi", "type": "int4"},
    ],
    "records": [
        {"beachName": "Sunnyside", "collectionDate": "2025-07-01", "eColi": 42},
        {"beachName": "Cherry", "collectionDate": "2025-07-01", "eColi": 8},
    ],
    "total": 108284,
}


class _StubCkan(CkanSource):
    def _api(self, action, **params):
        if action == "package_show":
            return _PACKAGE
        if action == "datastore_search":
            return _DATASTORE
        raise AssertionError(action)


def test_matches_and_detect():
    assert CkanSource.matches("ckan:https://portal/dataset/x")
    assert not CkanSource.matches("https://portal/dataset/x")
    s = build_source("ckan:https://portal/dataset/x")
    assert isinstance(s, CkanSource)


def test_parse_input_from_dataset_url():
    src = _StubCkan("ckan:https://portal/dataset/toronto-beaches-water-quality")
    src._base = ""
    slug = src._parse_input()
    assert slug == "toronto-beaches-water-quality"
    assert src._base == "https://portal"


def test_parse_input_requires_slug():
    src = _StubCkan("ckan:https://portal")
    src._base = ""
    with pytest.raises(SourceError):
        src._parse_input()


def test_parse_input_with_dataset_option():
    src = _StubCkan("ckan:https://portal", options={"dataset": "my-set"})
    src._base = ""
    assert src._parse_input() == "my-set"


def test_build_produces_dataset_and_resource_concepts():
    src = _StubCkan("ckan:https://portal/dataset/toronto-beaches-water-quality")
    bundle = src.build()
    paths = {c.path for c in bundle.concepts}
    assert "overview.md" in paths
    assert "resources/water-quality.md" in paths
    assert "resources/readme.md" in paths

    overview = next(c for c in bundle.concepts if c.path == "overview.md")
    assert overview.type == "Dataset"
    assert "City of Toronto" in overview.body
    assert "beaches" in overview.tags

    res = next(c for c in bundle.concepts if c.path == "resources/water-quality.md")
    assert res.type == "Data Resource"
    # live schema rendered, internal _id dropped, example rows + total present
    assert "`beachName`" in res.body and "`eColi`" in res.body
    assert "_id" not in res.body
    assert "Sunnyside" in res.body
    assert "108,284" in res.body


def test_non_https_input_rejected():
    src = _StubCkan("ckan:not-a-url")
    src._base = ""
    with pytest.raises(SourceError):
        src._parse_input()
