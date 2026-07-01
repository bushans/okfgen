"""Web docs source: crawl a documentation site into concept documents.

Standard-library only (urllib + html.parser). Stays on the seed host, honors a
depth/page budget, and extracts a title + readable text + headings per page.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import List, Optional, Set, Tuple
from urllib.parse import urldefrag, urljoin, urlparse
from urllib.request import Request, urlopen

from ..model import Bundle, Concept, LogEntry, slugify, utcnow_iso
from .base import Source, SourceError

_USER_AGENT = "okfgen/0.1 (+https://github.com/GoogleCloudPlatform/knowledge-catalog)"
_SKIP_TAGS = {"script", "style", "noscript", "svg", "nav", "footer", "header"}


class _Extractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title: Optional[str] = None
        self._in_title = False
        self._skip_depth = 0
        self.text_parts: List[str] = []
        self.headings: List[Tuple[int, str]] = []
        self.links: List[str] = []
        self._heading_level: Optional[int] = None
        self._heading_buf: List[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
        elif tag == "title":
            self._in_title = True
        elif tag in ("h1", "h2", "h3"):
            self._heading_level = int(tag[1])
            self._heading_buf = []
        elif tag == "a":
            for k, v in attrs:
                if k == "href" and v:
                    self.links.append(v)

    def handle_endtag(self, tag):
        if tag in _SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        elif tag == "title":
            self._in_title = False
        elif tag in ("h1", "h2", "h3") and self._heading_level is not None:
            text = " ".join("".join(self._heading_buf).split())
            if text:
                self.headings.append((self._heading_level, text))
            self._heading_level = None
            self._heading_buf = []

    def handle_data(self, data):
        if self._skip_depth > 0:
            return
        if self._in_title:
            self.title = (self.title or "") + data
        if self._heading_level is not None:
            self._heading_buf.append(data)
        stripped = data.strip()
        if stripped:
            self.text_parts.append(stripped)


class WebDocsSource(Source):
    kind = "web"

    @classmethod
    def matches(cls, input_value: str) -> bool:
        v = input_value.strip()
        if not v.startswith(("http://", "https://")):
            return False
        # Let the git source claim obvious repo URLs first.
        if v.endswith(".git"):
            return False
        return True

    def _fetch(self, url: str) -> Optional[str]:
        req = Request(url, headers={"User-Agent": _USER_AGENT})
        try:
            with urlopen(req, timeout=self.options.get("timeout", 30)) as resp:
                ctype = resp.headers.get("Content-Type", "")
                if "html" not in ctype and "text" not in ctype:
                    return None
                charset = resp.headers.get_content_charset() or "utf-8"
                data = resp.read(2_000_000)
            return data.decode(charset, errors="replace")
        except Exception as exc:  # network errors, timeouts, 4xx/5xx
            raise SourceError(f"Failed to fetch {url}: {exc}") from exc

    def build(self) -> Bundle:
        seed = self.input_value.strip()
        max_pages = int(self.options.get("max_pages", 25))
        max_depth = int(self.options.get("max_depth", 2))
        parsed_seed = urlparse(seed)
        host = parsed_seed.netloc
        title = self.options.get("title") or (host + parsed_seed.path).strip("/") or host
        bundle = Bundle(title=f"{title} docs", source=seed)

        queue: List[Tuple[str, int]] = [(urldefrag(seed).url, 0)]
        seen: Set[str] = set()
        pages = 0

        while queue and pages < max_pages:
            url, depth = queue.pop(0)
            if url in seen:
                continue
            seen.add(url)
            try:
                html = self._fetch(url)
            except SourceError:
                if pages == 0:
                    raise  # the seed itself failed — surface it
                continue
            if html is None:
                continue

            ext = _Extractor()
            try:
                ext.feed(html)
            except Exception:
                continue

            page_title = (ext.title or "").strip() or url
            body = self._render_body(ext)
            slug = slugify(urlparse(url).path.strip("/").replace("/", "-") or "index")
            path = bundle.unique_path("pages", slug)
            bundle.add(Concept(
                path=path,
                type="Web Page",
                title=page_title[:150],
                description=self._summary(ext),
                resource=url,
                tags=["documentation", host],
                body=body,
            ))
            pages += 1

            if depth < max_depth:
                for link in self._same_host_links(url, ext.links, host):
                    if link not in seen:
                        queue.append((link, depth + 1))

        if pages == 0:
            raise SourceError(f"No HTML pages could be extracted from {seed}")

        bundle.log_entries.append(LogEntry(
            date=utcnow_iso()[:10],
            action="Crawled",
            text=f"Crawled {pages} page(s) from {seed} by okfgen.",
        ))
        return bundle

    def _same_host_links(self, base: str, links: List[str], host: str) -> List[str]:
        out: List[str] = []
        for raw in links:
            if raw.startswith(("mailto:", "javascript:", "#", "tel:")):
                continue
            absolute = urldefrag(urljoin(base, raw)).url
            p = urlparse(absolute)
            if p.scheme not in ("http", "https"):
                continue
            if p.netloc != host:
                continue
            if re.search(r"\.(png|jpe?g|gif|svg|pdf|zip|css|js|ico|woff2?)$", p.path, re.I):
                continue
            out.append(absolute)
        # De-dup while preserving order.
        return list(dict.fromkeys(out))

    def _summary(self, ext: _Extractor) -> str:
        text = " ".join(ext.text_parts)
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            return "Crawled documentation page."
        sentence = re.split(r"(?<=[.!?])\s", text)[0]
        return sentence[:200]

    def _render_body(self, ext: _Extractor) -> str:
        lines: List[str] = []
        if ext.headings:
            lines.append("# Schema")
            lines.append("")
            for level, text in ext.headings[:50]:
                lines.append(f"{'  ' * (level - 1)}- {text}")
            lines.append("")
        text = re.sub(r"\s+", " ", " ".join(ext.text_parts)).strip()
        if text:
            lines.append(text[:8000])
        return "\n".join(lines).strip()
