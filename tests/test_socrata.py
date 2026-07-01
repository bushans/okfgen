"""Offline tests for the Socrata source (HTTP stubbed)."""

from __future__ import annotations

import pytest

from okfgen.sources.socrata import SocrataSource
from okfgen.sources import SourceError
from okfgen.detect import build_source


_META = {
    "name": "311 Service Requests",
    "description": "All 311 service requests from 2010 to present.",
    "category": "Social Services",
    "attribution": "NYC OTI",
    "viewCount": 987654,
    "columns": [
        {"fieldName": ":id", "name": "id", "dataTypeName": "meta_data"},  # dropped
        {"fieldName": "unique_key", "name": "Unique Key", "dataTypeName": "text",
         "description": "Unique id of a request."},
        {"fieldName": "complaint_type", "name": "Complaint Type", "dataTypeName": "text",
         "description": "Topic of the incident."},
        {"fieldName": "borough", "name": "Borough", "dataTypeName": "text"},
    ],
}

_ROWS = [
    {"unique_key": "1", "complaint_type": "Noise", "borough": "BROOKLYN"},
    {"unique_key": "2", "complaint_type": "Heat", "borough": "BRONX"},
]


class _StubSocrata(SocrataSource):
    def _get(self, url):
        if "/api/views/" in url:
            return _META
        if "/resource/" in url:
            return _ROWS
        raise AssertionError(url)


def test_matches_and_detect():
    assert SocrataSource.matches("socrata:https://data.cityofnewyork.us/d/erm2-nwe9")
    assert not SocrataSource.matches("https://data.cityofnewyork.us/d/erm2-nwe9")
    assert isinstance(build_source("socrata:https://x.gov/d/abcd-1234"), SocrataSource)


@pytest.mark.parametrize("inp,domain,ds", [
    ("socrata:https://data.cityofnewyork.us/d/erm2-nwe9", "data.cityofnewyork.us", "erm2-nwe9"),
    ("socrata:data.seattle.gov/kzjm-xkqj", "data.seattle.gov", "kzjm-xkqj"),
    ("socrata:https://data.x.gov/dataset/Foo-Bar/abcd-1234", "data.x.gov", "abcd-1234"),
])
def test_parse_input_variants(inp, domain, ds):
    src = _StubSocrata(inp)
    assert src._parse_input() == (domain, ds)


def test_parse_input_with_option_id():
    src = _StubSocrata("socrata:https://data.x.gov", options={"dataset": "abcd-1234"})
    assert src._parse_input() == ("data.x.gov", "abcd-1234")


def test_parse_input_requires_id():
    with pytest.raises(SourceError):
        _StubSocrata("socrata:https://data.x.gov")._parse_input()


def test_build_produces_dataset_and_table():
    bundle = _StubSocrata("socrata:https://data.cityofnewyork.us/d/erm2-nwe9").build()
    paths = {c.path for c in bundle.concepts}
    assert "overview.md" in paths
    assert "tables/erm2-nwe9.md" in paths

    overview = next(c for c in bundle.concepts if c.path == "overview.md")
    assert overview.type == "Dataset"
    assert "Social Services" in overview.body

    table = next(c for c in bundle.concepts if c.path.startswith("tables/"))
    assert "`unique_key`" in table.body and "`complaint_type`" in table.body
    assert ":id" not in table.body            # system column dropped
    assert "BROOKLYN" in table.body           # example row rendered
