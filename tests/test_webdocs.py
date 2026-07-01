"""Offline tests for the web docs HTML extraction (no network)."""

from __future__ import annotations

from okfgen.sources.webdocs import _Extractor, WebDocsSource


SAMPLE_HTML = """
<html><head><title>Getting Started</title></head>
<body>
<nav>skip me</nav>
<h1>Getting Started</h1>
<p>Install the package. It is easy.</p>
<h2>Configuration</h2>
<p>Set the key.</p>
<a href="/guide/next">Next</a>
<a href="https://other.example.com/x">External</a>
<a href="mailto:a@b.com">Mail</a>
<script>var x = 1;</script>
</body></html>
"""


def test_extractor_pulls_title_headings_text():
    ext = _Extractor()
    ext.feed(SAMPLE_HTML)
    assert ext.title.strip() == "Getting Started"
    headings = [h[1] for h in ext.headings]
    assert "Getting Started" in headings
    assert "Configuration" in headings
    # script content excluded
    joined = " ".join(ext.text_parts)
    assert "var x" not in joined
    assert "Install the package." in joined


def test_summary_first_sentence():
    src = WebDocsSource("https://docs.example.com")
    ext = _Extractor()
    ext.feed(SAMPLE_HTML)
    summary = src._summary(ext)
    assert summary.startswith("Getting Started")


def test_same_host_link_filtering():
    src = WebDocsSource("https://docs.example.com")
    ext = _Extractor()
    ext.feed(SAMPLE_HTML)
    links = src._same_host_links("https://docs.example.com/start", ext.links, "docs.example.com")
    assert "https://docs.example.com/guide/next" in links
    assert all("other.example.com" not in link for link in links)
    assert all("mailto" not in link for link in links)


def test_render_body_has_schema_section():
    src = WebDocsSource("https://docs.example.com")
    ext = _Extractor()
    ext.feed(SAMPLE_HTML)
    body = src._render_body(ext)
    assert "# Schema" in body
    assert "Configuration" in body
